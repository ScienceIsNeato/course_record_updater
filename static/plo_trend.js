/* global Chart */
/**
 * PLO Trend — sparklines + expandable trend charts for the PLO dashboard.
 *
 * Fetches multi-term trend data from /api/programs/<id>/plo-dashboard/trend
 * and injects tiny sparkline canvases into existing PLO/CLO tree nodes,
 * plus an expandable full chart panel on click.
 *
 * Exports `PloTrend` on globalThis for integration tests.
 */

(function () {
  "use strict";

  const TREND_LINE_COLOR = "#0d6efd";
  const TREND_LINE_COLOR_FAIL = "#dc3545";
  const TREND_FILL_COLOR = "rgba(13, 110, 253, 0.08)";
  const TREND_NULL_DASH = [4, 4];
  const trendPanelModule =
    typeof module !== "undefined" && module.exports
      ? require("./plo_trend_panel")
      : globalThis.PloTrendPanel;
  const sparklineModule =
    typeof module !== "undefined" && module.exports
      ? require("./plo_trend_sparkline")
      : globalThis.PloTrendSparkline;

  /**
   * Destroy any Chart.js instances attached to canvas elements within an element.
   * Must be called before removing DOM elements to avoid memory leaks.
   */
  function _destroyCharts(el) {
    if (typeof Chart === "undefined" || typeof Chart.getChart !== "function") {
      return;
    }
    el.querySelectorAll("canvas").forEach((canvas) => {
      const chart = Chart.getChart(canvas);
      if (chart && typeof chart.destroy === "function") {
        chart.destroy();
      }
    });
  }

  /**
   * Determine trend direction from an array of data points.
   * Returns: "strong-up" | "up" | "flat" | "down" | "strong-down" | "none"
   *
   * Thresholds (percentage-point change):
   *   |diff| < 2  → flat
   *   2 ≤ diff < 10 → up / down
   *   diff ≥ 10     → strong-up / strong-down
   */
  function getTrendDirection(trendPoints) {
    // Filter to only non-null points
    const valid = trendPoints.filter((p) => p !== null && p.pass_rate !== null);
    if (valid.length < 2) return "none";

    const first = valid[0].pass_rate;
    const last = valid[valid.length - 1].pass_rate;
    const diff = last - first;

    if (Math.abs(diff) < 2) return "flat";
    if (diff >= 10) return "strong-up";
    if (diff > 0) return "up";
    if (diff <= -10) return "strong-down";
    return "down";
  }

  /**
   * Get trend arrow character + CSS class.
   */
  function getTrendArrow(direction) {
    switch (direction) {
      case "strong-up":
        return { arrow: "⬆", cssClass: "trend-strong-up" };
      case "up":
        return { arrow: "↑", cssClass: "trend-up" };
      case "down":
        return { arrow: "↓", cssClass: "trend-down" };
      case "strong-down":
        return { arrow: "⬇", cssClass: "trend-strong-down" };
      case "flat":
        return { arrow: "→", cssClass: "trend-flat" };
      default:
        return { arrow: "", cssClass: "trend-none" };
    }
  }

  /**
   * Compute percentage-point change between first and last valid data points.
   * Returns an integer delta, or null if insufficient data.
   */
  function getTrendDelta(trendPoints) {
    const valid = (trendPoints || []).filter(
      (p) => p !== null && p.pass_rate !== null,
    );
    if (valid.length < 2) return null;
    return Math.round(valid[valid.length - 1].pass_rate - valid[0].pass_rate);
  }

  const createSparkline = (...args) => sparklineModule.createSparkline(...args);

  // Palette for CLO overlay lines (visually distinct, semi-transparent)
  const CLO_COLORS = [
    "rgba(255, 99, 132, 0.55)",
    "rgba(54, 162, 235, 0.55)",
    "rgba(255, 206, 86, 0.65)",
    "rgba(75, 192, 192, 0.55)",
    "rgba(153, 102, 255, 0.55)",
    "rgba(255, 159, 64, 0.55)",
    "rgba(199, 199, 199, 0.6)",
    "rgba(83, 102, 55, 0.55)",
    "rgba(201, 76, 76, 0.55)",
    "rgba(107, 91, 149, 0.55)",
  ];

  // Stable palette for composition-bar course swatches.
  // Each course gets the same colour as its CLO overlay line on the chart.
  const COMP_COLORS = CLO_COLORS;

  /**
   * Compute a nice Y-axis range that zooms into the data.
   * Returns { min, max } with ~10% padding above and below,
   * clamped to [0, 100].
   */
  function computeYRange(datasets) {
    let lo = Infinity;
    let hi = -Infinity;
    datasets.forEach((ds) => {
      (ds.data || []).forEach((v) => {
        if (v !== null && !isNaN(v)) {
          if (v < lo) lo = v;
          if (v > hi) hi = v;
        }
      });
    });
    if (!isFinite(lo) || !isFinite(hi)) return { min: 0, max: 100 };
    const span = hi - lo || 10; // avoid zero span
    const pad = span * 0.15;
    return {
      min: Math.max(0, Math.floor((lo - pad) / 5) * 5),
      max: Math.min(100, Math.ceil((hi + pad) / 5) * 5),
    };
  }

  /**
   * Build a short label for a CLO suitable for chart legends.
   */
  function cloLabel(clo) {
    const course = clo.course_number || "";
    const num = clo.clo_number || "?";
    return `${course} CLO ${num}`;
  }

  /**
   * Create a CLO composition bar element showing which courses
   * contributed data in each term.
   * Returns a div containing colored pills per term.
   */
  function createCompositionBar(clos, terms) {
    const bar = document.createElement("div");
    bar.className = "plo-composition-bar";

    // Collect unique courses and assign colours (same palette as chart lines)
    const courseSet = new Map();
    (clos || []).forEach((clo, ci) => {
      const cn = clo.course_number || "?";
      if (!courseSet.has(cn)) {
        courseSet.set(cn, COMP_COLORS[ci % COMP_COLORS.length]);
      }
    });

    // One cell per term
    terms.forEach((tm, ti) => {
      const cell = document.createElement("div");
      cell.className = "plo-comp-cell";

      // Which courses have data in this term?
      const activeCourses = new Set();
      (clos || []).forEach((clo) => {
        const pt = (clo.trend || [])[ti];
        if (pt && pt.pass_rate !== null) {
          activeCourses.add(clo.course_number || "?");
        }
      });

      if (activeCourses.size === 0) {
        const dot = document.createElement("span");
        dot.className = "plo-comp-dot plo-comp-empty";
        dot.title = `${tm.term_name}: no data`;
        cell.appendChild(dot);
      } else {
        activeCourses.forEach((cn) => {
          const dot = document.createElement("span");
          dot.className = "plo-comp-dot";
          dot.style.backgroundColor = courseSet.get(cn) || "#ccc";
          dot.title = `${tm.term_name}: ${cn}`;
          cell.appendChild(dot);
        });
      }
      bar.appendChild(cell);
    });

    // Legend
    if (courseSet.size > 0) {
      const legend = document.createElement("div");
      legend.className = "plo-comp-legend";
      courseSet.forEach((color, cn) => {
        const item = document.createElement("span");
        item.className = "plo-comp-legend-item";
        const swatch = document.createElement("span");
        swatch.className = "plo-comp-swatch";
        swatch.style.backgroundColor = color;
        item.appendChild(swatch);
        item.appendChild(document.createTextNode(cn));
        legend.appendChild(item);
      });
      bar.appendChild(legend);
    }

    return bar;
  }

  /**
   * Create a full-size trend chart panel for drill-down.
   * Returns a container div with a Chart.js line chart.
   *
   * When opts.clos is provided (PLO-level chart), renders:
   * - Semi-transparent CLO overlay lines
   * - Enriched tooltip showing per-CLO breakdown
   * When opts.discontinuities is provided, renders vertical annotations.
   */
  function createTrendPanel(trendPoints, terms, opts) {
    return trendPanelModule.createTrendPanel(trendPoints, terms, opts, {
      CLO_COLORS,
      TREND_FILL_COLOR,
      TREND_LINE_COLOR,
      TREND_LINE_COLOR_FAIL,
      TREND_NULL_DASH,
      cloLabel,
      computeYRange,
      createCompositionBar,
    });
  }

  // -----------------------------------------------------------------------
  // PloTrend controller — fetches data and wires into the existing tree
  // -----------------------------------------------------------------------
  const PloTrend = {
    trendData: null,
    selectedTermId: null,

    /**
     * Fetch trend data for the given program and inject sparklines
     * into the already-rendered PLO tree.
     * @param {string} programId
     * @param {string} [selectedTermId] - The currently selected term from the filter
     */
    async loadTrend(programId, selectedTermId) {
      if (!programId) return;
      this.programId = programId;
      if (selectedTermId !== undefined) this.selectedTermId = selectedTermId;

      // Track the latest request to ignore stale responses
      const gen = (this._loadTrendGen = (this._loadTrendGen || 0) + 1);

      const url = `/api/programs/${encodeURIComponent(programId)}/plo-dashboard/trend`;
      try {
        const resp = await fetch(url, {
          credentials: "include",
          headers: { Accept: "application/json" },
        });
        if (gen !== this._loadTrendGen) return; // stale response
        if (!resp.ok) return;
        const data = await resp.json();
        if (gen !== this._loadTrendGen) return; // stale response
        if (!data.success) return;
        this.trendData = data;
        this.injectSparklines();
      } catch (err) {
        if (gen !== this._loadTrendGen) return;
        console.warn("PloTrend: failed to load trend data", err);
      }
    },

    /**
     * Walk the DOM tree and inject sparklines next to assessment badges.
     */
    injectSparklines(opts) {
      if (!this.trendData) return;
      const { terms, plos } = this.trendData;
      if (!terms || terms.length < 2) return; // need ≥2 terms for a trend
      const trendProgramId =
        this.trendData.program_id || this.programId || null;

      // Find which term index the user has selected
      const selectedTermIndex = this.selectedTermId
        ? terms.findIndex(
            (t) => String(t.term_id) === String(this.selectedTermId),
          )
        : -1;

      const container = document.getElementById("ploTreeContainer");
      if (!container) return;

      (plos || []).forEach((plo) => {
        // Find the PLO node in the DOM
        const ploNode = Array.from(
          container.querySelectorAll("li[data-plo-id]"),
        ).find((node) => String(node.dataset.ploId) === String(plo.id));
        if (ploNode) {
          // Remove existing trend indicators/panels for THIS node only (avoids
          // wiping indicators from other programs in the All-Programs view)
          ploNode
            .querySelectorAll(
              ":scope > .plo-tree-header .plo-trend-indicator, :scope > .plo-trend-panel",
            )
            .forEach((el) => {
              _destroyCharts(el);
              el.remove();
            });
          this._injectIntoNode(ploNode, plo.trend, terms, {
            title: `PLO-${plo.plo_number}: ${plo.description}`,
            clos: plo.clos || [],
            discontinuities: plo.discontinuities || [],
            programId: trendProgramId,
            selectedTermIndex,
          });
        }

        // CLO nodes
        (plo.clos || []).forEach((clo) => {
          const cloNode = Array.from(
            container.querySelectorAll("[data-clo-id]"),
          ).find(
            (node) => String(node.dataset.cloId) === String(clo.outcome_id),
          );
          if (cloNode) {
            cloNode
              .querySelectorAll(
                ":scope > .plo-tree-header .plo-trend-indicator, :scope > .plo-trend-panel",
              )
              .forEach((el) => {
                _destroyCharts(el);
                el.remove();
              });
            this._injectIntoNode(cloNode, clo.trend, terms, {
              title: `${clo.course_number || ""} CLO ${clo.clo_number || "?"}: ${clo.description || ""}`,
              discontinuities: plo.discontinuities || [],
              selectedTermIndex,
            });
          }
        });
      });

      // Populate summary bar sparklines
      this._injectSummarySparklines(
        container,
        plos,
        terms,
        selectedTermIndex,
        trendProgramId,
      );

      if (!opts || opts.restoreFromHash !== false) {
        this._restoreFromHash();
      }
    },

    /**
     * Inject sparkline canvases into summary bar sparkline slots.
     * Each slot is tagged with data-plo-id matching a PLO in the trend data.
     * Clicking a sparkline toggles a full trend panel below the category row.
     */
    _injectSummarySparklines(
      container,
      plos,
      terms,
      selectedTermIndex,
      programId,
    ) {
      const slots = container.querySelectorAll(".plo-summary-sparkline-slot");
      slots.forEach((slot) => {
        const ploId = slot.dataset.ploId;
        const plo = (plos || []).find((p) => String(p.id) === String(ploId));
        if (!plo || !plo.trend || plo.trend.length < 2) return;

        // Remove existing sparkline / badge if re-injecting
        const existing = slot.querySelector(".plo-sparkline");
        if (existing) {
          _destroyCharts(existing.parentElement || existing);
          existing.remove();
        }
        const existingBadge = slot.querySelector(".plo-trend-indicator");
        if (existingBadge) existingBadge.remove();

        const canvas = createSparkline(plo.trend, terms, {
          threshold: 70,
          discontinuities: plo.discontinuities || [],
          selectedTermIndex: selectedTermIndex != null ? selectedTermIndex : -1,
        });
        slot.insertBefore(canvas, slot.firstChild);

        // When a historical term is selected, compute badge from data up to
        // that term only so the arrow + delta match the visible sparkline.
        const badgeTrend =
          selectedTermIndex != null && selectedTermIndex >= 0
            ? plo.trend.slice(0, selectedTermIndex + 1)
            : plo.trend;

        // Add compact trend badge (arrow + delta) after the sparkline
        const direction = getTrendDirection(badgeTrend);
        const { arrow, cssClass } = getTrendArrow(direction);
        const delta = getTrendDelta(badgeTrend);
        if (arrow) {
          const badge = document.createElement("span");
          badge.className = "plo-trend-indicator plo-trend-indicator--mini";
          if (cssClass) badge.classList.add(cssClass);
          const arrowEl = document.createElement("span");
          arrowEl.className = "plo-trend-arrow " + cssClass;
          arrowEl.textContent = arrow;
          badge.appendChild(arrowEl);
          if (delta !== null) {
            const deltaEl = document.createElement("span");
            deltaEl.className = "plo-trend-delta";
            deltaEl.textContent = (delta >= 0 ? "+" : "") + delta + "%";
            badge.appendChild(deltaEl);
          }
          // Insert badge after sparkline, before the label
          const label = slot.querySelector(".plo-summary-sparkline-label");
          if (label) {
            slot.insertBefore(badge, label);
          } else {
            slot.appendChild(badge);
          }
        }

        // Click / keyboard opens trend panel below the row
        canvas.setAttribute("tabindex", "0");
        canvas.setAttribute("role", "button");
        canvas.setAttribute(
          "aria-label",
          "View trend chart for PLO-" + plo.plo_number,
        );
        canvas.addEventListener("click", (e) => {
          e.stopPropagation();
          this._toggleSummaryTrendPanel(
            slot,
            plo,
            terms,
            programId,
            selectedTermIndex,
          );
        });
        canvas.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            e.stopPropagation();
            this._toggleSummaryTrendPanel(
              slot,
              plo,
              terms,
              programId,
              selectedTermIndex,
            );
          }
        });
      });
    },

    /**
     * Build an onPointClick callback for a PLO trend chart data point.
     * Fetches the PLO detail (CLO → section breakdown) for the clicked term
     * and renders an inline detail panel below the trend chart.
     *
     * @param {string} ploId - PLO to fetch detail for
     * @param {{el: HTMLElement}} ref - object whose .el will be set to the container element after panel creation
     */
    _makePointClickHandler(ploId, ref, programIdOverride) {
      var self = this;
      return function onPointClick(term, chartEvent) {
        if (!term || !term.term_id) return false;
        var DetailPanel =
          typeof globalThis !== "undefined" && globalThis.PloDetailPanel;
        if (!DetailPanel) return false;
        var container = ref && ref.el;
        if (!container) return false;

        var nativeEvt = chartEvent && (chartEvent.native || chartEvent);
        var isShift = nativeEvt && nativeEvt.shiftKey;
        var existingPanel = container.querySelector(".plo-detail-panel");

        if (!isShift || !existingPanel) {
          DetailPanel.destroyDetailPanel(container);
          var cmpWrap = container.querySelector(".plo-detail-compare");
          if (cmpWrap) cmpWrap.remove();
        }

        var programId = programIdOverride || self.programId;
        if (!programId) return false;
        if (!self._detailPanelRequestGen) {
          self._detailPanelRequestGen = new WeakMap();
        }
        var requestGen = (self._detailPanelRequestGen.get(container) || 0) + 1;
        self._detailPanelRequestGen.set(container, requestGen);

        var url =
          "/api/programs/" +
          encodeURIComponent(programId) +
          "/plo-dashboard?plo_id=" +
          encodeURIComponent(ploId) +
          "&term_id=" +
          encodeURIComponent(term.term_id);

        fetch(url, {
          credentials: "include",
          headers: { Accept: "application/json" },
        })
          .then(function (resp) {
            if (!resp.ok) return null;
            return resp.json();
          })
          .then(function (data) {
            if (self._detailPanelRequestGen.get(container) !== requestGen) {
              return;
            }
            if (!data || !data.success) return;
            var plos = data.plos || (data.tree && data.tree.plos);
            if (!plos || plos.length === 0) return;
            var ploData = plos[0];
            var termLabel = term.term_name || term.name || "";
            var detailEl = DetailPanel.createDetailPanel(ploData, termLabel);

            if (self._detailPanelRequestGen.get(container) !== requestGen) {
              return;
            }

            var currentPanel = container.querySelector(".plo-detail-panel");
            if (isShift && currentPanel && currentPanel.parentNode) {
              var cw = container.querySelector(".plo-detail-compare");
              if (!cw) {
                cw = document.createElement("div");
                cw.className = "plo-detail-compare";
                currentPanel.parentNode.insertBefore(cw, currentPanel);
                cw.appendChild(currentPanel);
                self._wireCompareClose(currentPanel, cw);
              }
              if (cw.children.length >= 2) {
                cw.children[1].remove();
              }
              cw.appendChild(detailEl);
              self._wireCompareClose(detailEl, cw);
            } else {
              container.appendChild(detailEl);
            }

            self._updateHash(ploId);
          })
          .catch(function () {
            /* silently ignore network errors */
          });
        return true;
      };
    },

    /**
     * Toggle a trend chart panel below the summary row containing the clicked sparkline.
     */
    _toggleSummaryTrendPanel(slot, plo, terms, programId, selectedTermIndex) {
      const row = slot.closest(".plo-summary-row");
      if (!row) return;

      // Check if this PLO's panel is already open
      const next = row.nextElementSibling;
      if (
        next &&
        next.classList.contains("plo-trend-panel") &&
        next.dataset.ploId === String(plo.id)
      ) {
        _destroyCharts(next);
        next.remove();
        this._clearHash();
        return;
      }

      // Remove any other open panel in this summary bar
      const bar = slot.closest(".plo-summary-bar");
      if (bar) {
        bar.querySelectorAll(".plo-trend-panel").forEach((p) => {
          _destroyCharts(p);
          p.remove();
        });
      }

      var panelRef = { el: null };
      const panel = createTrendPanel(plo.trend, terms, {
        title: "PLO-" + plo.plo_number + ": " + plo.description,
        clos: plo.clos || [],
        discontinuities: plo.discontinuities || [],
        programId,
        selectedTermIndex,
        onPointClick: this._makePointClickHandler(plo.id, panelRef, programId),
      });
      panelRef.el = panel;
      panel.dataset.ploId = String(plo.id);
      row.after(panel);
      this._updateHash(plo.id);
    },

    /**
     * Inject a compact trend indicator into a tree node's meta area,
     * and wire a click handler to toggle a full trend chart panel.
     *
     * The indicator replaces the previous sparkline with an immediately
     * readable badge: arrow + percentage-point change (e.g. "↑ +8%").
     */
    _injectIntoNode(nodeEl, trendPoints, terms, opts) {
      if (!trendPoints || trendPoints.length < 2) return;

      const header = nodeEl.querySelector(".plo-tree-header");
      if (!header) return;
      const meta = header.querySelector(".plo-tree-meta");
      if (!meta) return;

      // Trend direction + delta – scope to selected term when applicable
      const idx = opts && opts.selectedTermIndex;
      const badgeTrend =
        idx != null && idx >= 0 ? trendPoints.slice(0, idx + 1) : trendPoints;
      const direction = getTrendDirection(badgeTrend);
      const { arrow, cssClass } = getTrendArrow(direction);
      const delta = getTrendDelta(badgeTrend);

      // Build compact trend indicator
      const wrap = document.createElement("span");
      wrap.className = "plo-trend-indicator";
      if (cssClass) wrap.classList.add(cssClass);
      wrap.title = "Click to view trend chart";

      if (arrow) {
        const arrowEl = document.createElement("span");
        arrowEl.className = "plo-trend-arrow " + cssClass;
        arrowEl.textContent = arrow;
        wrap.appendChild(arrowEl);
      }

      if (delta !== null) {
        const deltaEl = document.createElement("span");
        deltaEl.className = "plo-trend-delta";
        deltaEl.textContent = (delta >= 0 ? "+" : "") + delta + "%";
        wrap.appendChild(deltaEl);
      }

      // Insert before the assessment badge
      const badge = meta.querySelector(".plo-assessment-badge");
      if (badge) {
        meta.insertBefore(wrap, badge);
      } else {
        meta.insertBefore(wrap, meta.firstChild);
      }

      // Click / keyboard handler for drill-down panel
      wrap.setAttribute("tabindex", "0");
      wrap.setAttribute("role", "button");
      wrap.addEventListener("click", (e) => {
        e.stopPropagation();
        this._toggleTrendPanel(nodeEl, trendPoints, terms, opts);
      });
      wrap.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          e.stopPropagation();
          this._toggleTrendPanel(nodeEl, trendPoints, terms, opts);
        }
      });
    },

    _toggleTrendPanel(nodeEl, trendPoints, terms, opts) {
      // Check if panel already exists
      const existing = nodeEl.querySelector(".plo-trend-panel");
      if (existing) {
        _destroyCharts(existing);
        existing.remove();
        this._clearHash();
        return;
      }

      // For PLO-level nodes, wire the drill-down detail panel
      var mergedOpts = opts;
      var panelRef = null;
      var ploId = nodeEl.dataset && nodeEl.dataset.ploId;
      if (ploId && opts && opts.clos) {
        panelRef = { el: null };
        mergedOpts = Object.assign({}, opts, {
          onPointClick: this._makePointClickHandler(
            ploId,
            panelRef,
            opts.programId,
          ),
        });
      }

      const panel = createTrendPanel(trendPoints, terms, mergedOpts);
      if (panelRef) panelRef.el = panel;

      // Ensure the node is expanded so the CSS rule
      // `.plo-tree-node:not(.expanded) > .plo-trend-panel` doesn't hide it.
      nodeEl.classList.add("expanded");

      // Insert after the header, before children
      const header = nodeEl.querySelector(".plo-tree-header");
      if (header && header.nextSibling) {
        nodeEl.insertBefore(panel, header.nextSibling);
      } else {
        nodeEl.appendChild(panel);
      }

      if (ploId) this._updateHash(ploId);
    },

    /**
     * Re-wire a detail panel's close button to handle compare-wrapper cleanup.
     */
    _wireCompareClose(panel, wrapper) {
      var btn = panel.querySelector(".plo-detail-panel-close");
      if (!btn) return;
      var newBtn = btn.cloneNode(true);
      btn.parentNode.replaceChild(newBtn, btn);
      newBtn.addEventListener("click", function () {
        panel.remove();
        if (wrapper.children.length <= 1 && wrapper.parentNode) {
          var remaining = wrapper.firstElementChild;
          if (remaining) {
            wrapper.parentNode.insertBefore(remaining, wrapper);
          }
          wrapper.remove();
        }
      });
    },

    _updateHash(ploId) {
      if (!ploId) return;
      var ploNumber = null;
      if (this.trendData) {
        var plo = (this.trendData.plos || []).find(function (p) {
          return String(p.id) === String(ploId);
        });
        if (plo && plo.plo_number != null) {
          ploNumber = plo.plo_number;
        }
      }
      if (ploNumber == null) {
        var container = document.getElementById("ploTreeContainer");
        var ploNode = container
          ? Array.from(container.querySelectorAll("li[data-plo-id]")).find(
              (node) => String(node.dataset.ploId) === String(ploId),
            )
          : null;
        if (ploNode && ploNode.dataset && ploNode.dataset.ploNumber) {
          ploNumber = ploNode.dataset.ploNumber;
        }
      }
      if (ploNumber == null) return;
      try {
        history.replaceState(null, "", "#plo=" + ploNumber);
      } catch (_) {
        /* ignore */
      }
    },

    _clearHash() {
      try {
        if (window.location.hash) {
          history.replaceState(
            null,
            "",
            window.location.pathname + window.location.search,
          );
        }
      } catch (_) {
        /* ignore */
      }
    },

    _restoreAllProgramsFromHash(allTrendData) {
      if (this._hashRestored) return;
      var hash = window.location.hash.slice(1);
      if (!hash || !Array.isArray(allTrendData)) return;
      var params;
      try {
        params = new URLSearchParams(hash);
      } catch (_) {
        return;
      }
      var ploNum = params.get("plo");
      if (!ploNum) return;

      var matchingData = allTrendData.find(function (data) {
        return (data && data.plos ? data.plos : []).some(function (plo) {
          return String(plo.plo_number) === String(ploNum) && !!plo.trend;
        });
      });
      if (!matchingData) return;

      var previousTrendData = this.trendData;
      var previousProgramId = this.programId;
      this.trendData = matchingData;
      this.programId = matchingData.program_id || this.programId;
      this._restoreFromHash();
      this.trendData = previousTrendData;
      this.programId = previousProgramId;
    },

    _restoreFromHash() {
      if (this._hashRestored) return;
      var hash = window.location.hash.slice(1);
      if (!hash) return;
      var params;
      try {
        params = new URLSearchParams(hash);
      } catch (_) {
        return;
      }
      var ploNum = params.get("plo");
      if (!ploNum || !this.trendData) return;

      var plo = (this.trendData.plos || []).find(function (p) {
        return String(p.plo_number) === String(ploNum);
      });
      if (!plo || !plo.trend) return;

      var container = document.getElementById("ploTreeContainer");
      if (!container) return;
      var ploNode = Array.from(
        container.querySelectorAll("li[data-plo-id]"),
      ).find((node) => String(node.dataset.ploId) === String(plo.id));
      if (!ploNode) return;

      ploNode.classList.add("expanded");
      this._hashRestored = true;
      var selectedTermIndex = this.selectedTermId
        ? this.trendData.terms.findIndex(
            (t) => String(t.term_id) === String(this.selectedTermId),
          )
        : -1;
      this._toggleTrendPanel(ploNode, plo.trend, this.trendData.terms, {
        title: "PLO-" + plo.plo_number + ": " + plo.description,
        clos: plo.clos || [],
        discontinuities: plo.discontinuities || [],
        programId: this.programId,
        selectedTermIndex,
      });
    },
  };

  // Exports
  if (typeof globalThis !== "undefined") {
    globalThis.PloTrend = PloTrend;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      PloTrend,
      createSparkline,
      createTrendPanel,
      createCompositionBar,
      computeYRange,
      getTrendDirection,
      getTrendArrow,
      getTrendDelta,
    };
  }
})();
