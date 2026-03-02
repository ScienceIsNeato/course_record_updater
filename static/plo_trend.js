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

  // Chart.js defaults for sparklines
  const SPARK_WIDTH = 90;
  const SPARK_HEIGHT = 28;
  const TREND_LINE_COLOR = "#0d6efd";
  const TREND_LINE_COLOR_FAIL = "#dc3545";
  const TREND_FILL_COLOR = "rgba(13, 110, 253, 0.08)";
  const TREND_NULL_DASH = [4, 4];
  const THRESHOLD_LINE_COLOR = "rgba(108, 117, 125, 0.3)";

  /**
   * Determine trend direction from an array of data points.
   * Returns: "up" | "down" | "flat" | "none"
   */
  function getTrendDirection(trendPoints) {
    // Filter to only non-null points
    const valid = trendPoints.filter((p) => p !== null && p.pass_rate !== null);
    if (valid.length < 2) return "none";

    const first = valid[0].pass_rate;
    const last = valid[valid.length - 1].pass_rate;
    const diff = last - first;

    if (Math.abs(diff) < 2) return "flat";
    return diff > 0 ? "up" : "down";
  }

  /**
   * Get trend arrow character + CSS class.
   */
  function getTrendArrow(direction) {
    switch (direction) {
      case "up":
        return { arrow: "↑", cssClass: "trend-up" };
      case "down":
        return { arrow: "↓", cssClass: "trend-down" };
      case "flat":
        return { arrow: "→", cssClass: "trend-flat" };
      default:
        return { arrow: "", cssClass: "trend-none" };
    }
  }

  /**
   * Create a tiny sparkline canvas element from trend data points.
   * Returns an HTMLCanvasElement ready to insert into the DOM.
   */
  function createSparkline(trendPoints, terms, opts) {
    const canvas = document.createElement("canvas");
    canvas.width = SPARK_WIDTH;
    canvas.height = SPARK_HEIGHT;
    canvas.className = "plo-sparkline";
    canvas.style.width = SPARK_WIDTH + "px";
    canvas.style.height = SPARK_HEIGHT + "px";
    canvas.title = "Click to view full trend chart";

    if (!trendPoints || trendPoints.length === 0) return canvas;

    // Prepare data: map null points to NaN for Chart.js spanGaps
    const labels = terms.map((t) => t.term_name || "");
    const data = trendPoints.map((p) =>
      p !== null && p.pass_rate !== null ? p.pass_rate : NaN,
    );

    // Detect which points are from "current" (in-progress) terms
    const pointStyles = terms.map((t) => (t.is_current ? "rectRot" : "circle"));
    const pointRadii = terms.map((t) => (t.is_current ? 3 : 2));
    // Use a segment-based approach for dashed lines at in-progress terms
    const currentTermIndices = new Set(
      terms.map((t, i) => (t.is_current ? i : -1)).filter((i) => i >= 0),
    );

    const threshold = (opts && opts.threshold) || 70;

    // Per-point colour: red for below threshold, blue for at/above
    const pointColors = data.map((d) =>
      !isNaN(d) && d < threshold ? TREND_LINE_COLOR_FAIL : TREND_LINE_COLOR,
    );
    // Larger radius for fail points so they stand out
    const failRadii = data.map((d, i) =>
      !isNaN(d) && d < threshold ? Math.max(pointRadii[i], 4) : pointRadii[i],
    );
    const pointBorders = data.map((d) =>
      !isNaN(d) && d < threshold ? TREND_LINE_COLOR_FAIL : TREND_LINE_COLOR,
    );

    // Determine line colour based on latest valid point
    const lastValid = data.filter((d) => !isNaN(d));
    const lineColor =
      lastValid.length > 0 && lastValid[lastValid.length - 1] < threshold
        ? TREND_LINE_COLOR_FAIL
        : TREND_LINE_COLOR;

    // Defer rendering until canvas is in the DOM
    requestAnimationFrame(() => {
      if (typeof Chart === "undefined") return;

      new Chart(canvas, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              data,
              borderColor: lineColor,
              backgroundColor: TREND_FILL_COLOR,
              fill: true,
              tension: 0.3,
              pointRadius: failRadii,
              pointStyle: pointStyles,
              pointBackgroundColor: pointColors,
              pointBorderColor: pointBorders,
              pointBorderWidth: 1,
              borderWidth: 1.5,
              spanGaps: true,
              segment: {
                borderDash: (ctx) =>
                  currentTermIndices.has(ctx.p1DataIndex)
                    ? TREND_NULL_DASH
                    : undefined,
              },
            },
          ],
        },
        options: {
          responsive: false,
          maintainAspectRatio: false,
          animation: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              enabled: true,
              callbacks: {
                title: (items) => items[0]?.label || "",
                label: (item) =>
                  item.raw !== null && !isNaN(item.raw)
                    ? `${Math.round(item.raw)}%`
                    : "No data",
              },
            },
            annotation: undefined,
          },
          scales: {
            x: { display: false },
            y: {
              display: false,
              min: 0,
              max: 100,
              // Threshold reference line via afterDraw plugin
            },
          },
          interaction: {
            mode: "index",
            intersect: false,
          },
        },
        plugins: [
          {
            id: "thresholdLine",
            afterDraw(chart) {
              const yScale = chart.scales.y;
              if (!yScale) return;
              const y = yScale.getPixelForValue(threshold);
              const ctx = chart.ctx;
              ctx.save();
              ctx.strokeStyle = THRESHOLD_LINE_COLOR;
              ctx.lineWidth = 1;
              ctx.setLineDash([3, 3]);
              ctx.beginPath();
              ctx.moveTo(chart.chartArea.left, y);
              ctx.lineTo(chart.chartArea.right, y);
              ctx.stroke();
              ctx.restore();
            },
          },
        ],
      });
    });

    return canvas;
  }

  /**
   * Create a full-size trend chart panel for drill-down.
   * Returns a container div with a Chart.js line chart.
   */
  function createTrendPanel(trendPoints, terms, opts) {
    const panel = document.createElement("div");
    panel.className = "plo-trend-panel";

    // Close button
    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "plo-trend-panel-close";
    closeBtn.innerHTML = "&times;";
    closeBtn.title = "Close trend chart";
    closeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      panel.remove();
    });
    panel.appendChild(closeBtn);

    const canvas = document.createElement("canvas");
    canvas.style.width = "100%";
    canvas.style.height = "200px";
    panel.appendChild(canvas);

    if (!trendPoints || trendPoints.length === 0) {
      const msg = document.createElement("p");
      msg.className = "text-muted text-center py-3";
      msg.textContent = "No trend data available.";
      panel.appendChild(msg);
      return panel;
    }

    const labels = terms.map((t) => t.term_name || "");
    const data = trendPoints.map((p) =>
      p !== null && p.pass_rate !== null ? p.pass_rate : NaN,
    );

    const threshold = (opts && opts.threshold) || 70;
    const title = (opts && opts.title) || "Pass Rate Trend";

    const currentTermIndices = new Set(
      terms.map((t, i) => (t.is_current ? i : -1)).filter((i) => i >= 0),
    );

    // Per-point colour: red for below threshold, blue for at/above
    const pointColors = data.map((d) =>
      !isNaN(d) && d < threshold ? TREND_LINE_COLOR_FAIL : TREND_LINE_COLOR,
    );
    // Larger radius for fail points
    const failRadii = data.map((d) => (!isNaN(d) && d < threshold ? 6 : 4));
    const pointBorders = data.map((d) =>
      !isNaN(d) && d < threshold ? TREND_LINE_COLOR_FAIL : TREND_LINE_COLOR,
    );

    // Determine line colour based on latest valid point
    const lastValid = data.filter((d) => !isNaN(d));
    const lineColor =
      lastValid.length > 0 && lastValid[lastValid.length - 1] < threshold
        ? TREND_LINE_COLOR_FAIL
        : TREND_LINE_COLOR;

    requestAnimationFrame(() => {
      if (typeof Chart === "undefined") return;

      new Chart(canvas, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "Pass Rate %",
              data,
              borderColor: lineColor,
              backgroundColor: TREND_FILL_COLOR,
              fill: true,
              tension: 0.3,
              pointRadius: failRadii,
              pointHoverRadius: 6,
              pointBackgroundColor: pointColors,
              pointBorderColor: pointBorders,
              pointBorderWidth: 1.5,
              borderWidth: 2,
              spanGaps: true,
              segment: {
                borderDash: (ctx) =>
                  currentTermIndices.has(ctx.p1DataIndex)
                    ? TREND_NULL_DASH
                    : undefined,
              },
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 300 },
          plugins: {
            legend: { display: false },
            title: {
              display: true,
              text: title,
              font: { size: 13, weight: "normal" },
              color: "#6c757d",
            },
            tooltip: {
              callbacks: {
                title: (items) => items[0]?.label || "",
                label: (item) => {
                  if (item.raw === null || isNaN(item.raw)) return "No data";
                  const point = trendPoints[item.dataIndex];
                  const pct = `${Math.round(item.raw)}%`;
                  if (point && point.students_took) {
                    return `${pct} (${point.students_passed}/${point.students_took})`;
                  }
                  return pct;
                },
              },
            },
          },
          scales: {
            x: {
              grid: { display: false },
              ticks: { font: { size: 11 } },
            },
            y: {
              min: 0,
              max: 100,
              ticks: {
                callback: (v) => v + "%",
                font: { size: 11 },
              },
              grid: { color: "rgba(0,0,0,0.05)" },
            },
          },
        },
        plugins: [
          {
            id: "thresholdLine",
            afterDraw(chart) {
              const yScale = chart.scales.y;
              if (!yScale) return;
              const y = yScale.getPixelForValue(threshold);
              const ctx = chart.ctx;
              ctx.save();
              ctx.strokeStyle = "rgba(220, 53, 69, 0.4)";
              ctx.lineWidth = 1;
              ctx.setLineDash([6, 4]);
              ctx.beginPath();
              ctx.moveTo(chart.chartArea.left, y);
              ctx.lineTo(chart.chartArea.right, y);
              ctx.stroke();
              // Label
              ctx.fillStyle = "rgba(220, 53, 69, 0.6)";
              ctx.font = "10px sans-serif";
              ctx.fillText(
                `Threshold ${threshold}%`,
                chart.chartArea.right - 80,
                y - 4,
              );
              ctx.restore();
            },
          },
        ],
      });
    });

    return panel;
  }

  // -----------------------------------------------------------------------
  // PloTrend controller — fetches data and wires into the existing tree
  // -----------------------------------------------------------------------
  const PloTrend = {
    trendData: null,

    /**
     * Fetch trend data for the given program and inject sparklines
     * into the already-rendered PLO tree.
     */
    async loadTrend(programId) {
      if (!programId) return;

      const url = `/api/programs/${encodeURIComponent(programId)}/plo-dashboard/trend`;
      try {
        const resp = await fetch(url, {
          credentials: "include",
          headers: { Accept: "application/json" },
        });
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data.success) return;
        this.trendData = data;
        this.injectSparklines();
      } catch (err) {
        console.warn("PloTrend: failed to load trend data", err);
      }
    },

    /**
     * Walk the DOM tree and inject sparklines next to assessment badges.
     */
    injectSparklines() {
      if (!this.trendData) return;
      const { terms, plos } = this.trendData;
      if (!terms || terms.length < 2) return; // need ≥2 terms for a trend

      const container = document.getElementById("ploTreeContainer");
      if (!container) return;

      // Remove any previously injected sparklines
      container
        .querySelectorAll(".plo-sparkline-wrap, .plo-trend-panel")
        .forEach((el) => el.remove());

      (plos || []).forEach((plo) => {
        // Find the PLO node in the DOM
        const ploNode = container.querySelector(`[data-plo-id="${plo.id}"]`);
        if (ploNode) {
          this._injectIntoNode(ploNode, plo.trend, terms, {
            title: `PLO-${plo.plo_number}: ${plo.description}`,
          });
        }

        // CLO nodes
        (plo.clos || []).forEach((clo) => {
          const cloNode = container.querySelector(
            `[data-clo-id="${clo.outcome_id}"]`,
          );
          if (cloNode) {
            this._injectIntoNode(cloNode, clo.trend, terms, {
              title: `${clo.course_number || ""} CLO ${clo.clo_number || "?"}: ${clo.description || ""}`,
            });
          }
        });
      });
    },

    /**
     * Inject a sparkline + trend arrow into a tree node's meta area,
     * and wire a click handler to toggle a full trend chart panel.
     */
    _injectIntoNode(nodeEl, trendPoints, terms, opts) {
      if (!trendPoints || trendPoints.length < 2) return;

      const header = nodeEl.querySelector(".plo-tree-header");
      if (!header) return;
      const meta = header.querySelector(".plo-tree-meta");
      if (!meta) return;

      // Trend direction arrow
      const direction = getTrendDirection(trendPoints);
      const { arrow, cssClass } = getTrendArrow(direction);

      // Wrap sparkline + arrow
      const wrap = document.createElement("span");
      wrap.className = "plo-sparkline-wrap";

      if (arrow) {
        const arrowEl = document.createElement("span");
        arrowEl.className = `plo-trend-arrow ${cssClass}`;
        arrowEl.textContent = arrow;
        wrap.appendChild(arrowEl);
      }

      const sparkCanvas = createSparkline(trendPoints, terms, opts);
      wrap.appendChild(sparkCanvas);

      // Insert before the assessment badge
      const badge = meta.querySelector(".plo-assessment-badge");
      if (badge) {
        meta.insertBefore(wrap, badge);
      } else {
        meta.insertBefore(wrap, meta.firstChild);
      }

      // Click handler for drill-down panel
      sparkCanvas.addEventListener("click", (e) => {
        e.stopPropagation();
        this._toggleTrendPanel(nodeEl, trendPoints, terms, opts);
      });
    },

    _toggleTrendPanel(nodeEl, trendPoints, terms, opts) {
      // Check if panel already exists
      const existing = nodeEl.querySelector(".plo-trend-panel");
      if (existing) {
        existing.remove();
        return;
      }

      const panel = createTrendPanel(trendPoints, terms, opts);
      // Insert after the header, before children
      const header = nodeEl.querySelector(".plo-tree-header");
      if (header && header.nextSibling) {
        nodeEl.insertBefore(panel, header.nextSibling);
      } else {
        nodeEl.appendChild(panel);
      }
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
      getTrendDirection,
      getTrendArrow,
    };
  }
})();
