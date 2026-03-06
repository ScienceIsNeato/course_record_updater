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
  const SPARK_WIDTH = 100;
  const SPARK_HEIGHT = 32;
  const TREND_LINE_COLOR = "#0d6efd";
  const TREND_LINE_COLOR_FAIL = "#dc3545";
  const TREND_LINE_COLOR_FUTURE = "rgba(160, 170, 180, 0.45)";
  const TREND_FILL_ALPHA_TOP = 0.18;
  const TREND_FILL_ALPHA_BOTTOM = 0.02;
  const TREND_FILL_COLOR = "rgba(13, 110, 253, 0.08)";
  const TREND_NULL_DASH = [4, 4];
  const THRESHOLD_LINE_COLOR = "rgba(108, 117, 125, 0.3)";

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

    // Use a segment-based approach for dashed lines at in-progress terms
    const currentTermIndices = new Set(
      terms.map((t, i) => (t.is_current ? i : -1)).filter((i) => i >= 0),
    );

    const threshold = (opts && opts.threshold) || 70;
    const selectedTermIndex =
      opts && opts.selectedTermIndex != null && opts.selectedTermIndex >= 0
        ? opts.selectedTermIndex
        : -1;
    // Is there a "future" region after the selected term?
    const hasFuture =
      selectedTermIndex >= 0 && selectedTermIndex < data.length - 1;

    // Determine line colour based on latest valid point
    const lastValid = data.filter((d) => !isNaN(d));
    const lineColor =
      lastValid.length > 0 && lastValid[lastValid.length - 1] < threshold
        ? TREND_LINE_COLOR_FAIL
        : TREND_LINE_COLOR;

    // Dot position: selected term if valid, else last valid point
    const lastValidIdx = data.reduce((acc, d, i) => (!isNaN(d) ? i : acc), -1);
    const dotIdx =
      selectedTermIndex >= 0 && !isNaN(data[selectedTermIndex])
        ? selectedTermIndex
        : lastValidIdx;
    const pointRadii = data.map((_, i) => (i === dotIdx ? 3 : 0));
    const pointColors = data.map((_, i) =>
      hasFuture && i > selectedTermIndex ? TREND_LINE_COLOR_FUTURE : lineColor,
    );
    const pointBorders = pointColors;

    // Defer rendering until canvas is in the DOM
    requestAnimationFrame(() => {
      if (typeof Chart === "undefined") return;

      // Build gradient fills (blue above threshold, red below)
      const ctx2d = canvas.getContext("2d");
      const blueRgb = "13, 110, 253";
      const redRgb = "220, 53, 69";
      let gradientFillBlue = `rgba(${blueRgb}, ${TREND_FILL_ALPHA_TOP})`;
      let gradientFillRed = `rgba(${redRgb}, ${TREND_FILL_ALPHA_TOP})`;
      if (ctx2d) {
        const grdB = ctx2d.createLinearGradient(0, 0, 0, SPARK_HEIGHT);
        grdB.addColorStop(0, `rgba(${blueRgb}, ${TREND_FILL_ALPHA_TOP})`);
        grdB.addColorStop(1, `rgba(${blueRgb}, ${TREND_FILL_ALPHA_BOTTOM})`);
        gradientFillBlue = grdB;
        const grdR = ctx2d.createLinearGradient(0, 0, 0, SPARK_HEIGHT);
        grdR.addColorStop(0, `rgba(${redRgb}, ${TREND_FILL_ALPHA_TOP})`);
        grdR.addColorStop(1, `rgba(${redRgb}, ${TREND_FILL_ALPHA_BOTTOM})`);
        gradientFillRed = grdR;
      }

      new Chart(canvas, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              data,
              borderColor: lineColor,
              backgroundColor: gradientFillBlue,
              fill: true,
              tension: 0.4,
              pointRadius: pointRadii,
              pointBackgroundColor: pointColors,
              pointBorderColor: pointBorders,
              pointBorderWidth: 1.5,
              borderWidth: 2,
              borderCapStyle: "round",
              borderJoinStyle: "round",
              spanGaps: true,
              segment: {
                borderDash: (ctx) =>
                  currentTermIndices.has(ctx.p1DataIndex)
                    ? TREND_NULL_DASH
                    : undefined,
                borderColor: (ctx) => {
                  // Grey for segments beyond the selected term
                  if (hasFuture && ctx.p0DataIndex >= selectedTermIndex)
                    return TREND_LINE_COLOR_FUTURE;
                  // Red segment when both endpoints are below threshold
                  const p0 = ctx.p0.parsed.y;
                  const p1 = ctx.p1.parsed.y;
                  if (
                    !isNaN(p0) &&
                    !isNaN(p1) &&
                    p0 < threshold &&
                    p1 < threshold
                  )
                    return TREND_LINE_COLOR_FAIL;
                  return undefined;
                },
              },
            },
          ],
        },
        options: {
          responsive: false,
          maintainAspectRatio: false,
          animation: false,
          events: [], // Disable all hover/tooltip — click handled via DOM
          plugins: {
            legend: { display: false },
            tooltip: { enabled: false },
            annotation: undefined,
          },
          scales: {
            x: { display: false },
            y: {
              display: false,
              min: 0,
              max: 100,
            },
          },
        },
        plugins: [
          {
            id: "belowThresholdFill",
            afterDatasetsDraw(chart) {
              const ds = chart.data.datasets[0];
              if (!ds) return;
              const meta = chart.getDatasetMeta(0);
              const yScale = chart.scales.y;
              if (!yScale || meta.data.length < 2) return;

              const threshY = yScale.getPixelForValue(threshold);
              const { left, right, bottom } = chart.chartArea;
              const ctx = chart.ctx;
              ctx.save();
              ctx.beginPath();
              let started = false;
              for (let i = 0; i < meta.data.length; i++) {
                const pt = meta.data[i];
                const val = ds.data[i];
                if (val === null || val === undefined || isNaN(val)) continue;
                const px = pt.x;
                const py = Math.max(pt.y, threshY);
                if (!started) {
                  ctx.moveTo(px, py);
                  started = true;
                } else {
                  ctx.lineTo(px, py);
                }
              }
              if (!started) {
                ctx.restore();
                return;
              }
              ctx.lineTo(right, bottom);
              ctx.lineTo(left, bottom);
              ctx.closePath();
              ctx.clip();
              if (typeof gradientFillRed === "object") {
                ctx.fillStyle = gradientFillRed;
              } else {
                ctx.fillStyle = `rgba(220, 53, 69, ${TREND_FILL_ALPHA_TOP})`;
              }
              ctx.fillRect(left, threshY, right - left, bottom - threshY);
              ctx.restore();
            },
          },
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
          {
            id: "sparkDiscontinuity",
            afterDraw(chart) {
              const discs = (opts && opts.discontinuities) || [];
              if (discs.length === 0) return;
              const xScale = chart.scales.x;
              if (!xScale) return;
              const ctx = chart.ctx;
              discs.forEach((d) => {
                const ti = d.term_index;
                if (ti < 0 || ti >= labels.length) return;
                const xCurr = xScale.getPixelForValue(ti);
                const xPrev = ti > 0 ? xScale.getPixelForValue(ti - 1) : xCurr;
                const x = (xPrev + xCurr) / 2;
                ctx.save();
                ctx.strokeStyle = "rgba(255, 152, 0, 0.35)";
                ctx.lineWidth = 1;
                ctx.setLineDash([]);
                ctx.beginPath();
                ctx.moveTo(x, chart.chartArea.top);
                ctx.lineTo(x, chart.chartArea.bottom);
                ctx.stroke();
                ctx.restore();
              });
            },
          },
          {
            id: "futureWash",
            afterDraw(chart) {
              if (!hasFuture) return;
              const xScale = chart.scales.x;
              if (!xScale) return;
              const xPos = xScale.getPixelForValue(selectedTermIndex);
              const { top, bottom, right } = chart.chartArea;
              const ctx = chart.ctx;
              ctx.save();
              ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
              ctx.fillRect(xPos, top, right - xPos, bottom - top);
              ctx.restore();
            },
          },
        ],
      });
    });

    return canvas;
  }

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
    const panel = document.createElement("div");
    panel.className = "plo-trend-panel";

    // Visibility toggle button (eyeball icon)
    const toggleBtn = document.createElement("button");
    toggleBtn.type = "button";
    toggleBtn.className = "plo-trend-panel-toggle";
    toggleBtn.innerHTML = "&#128065;"; // 👁 open eye
    toggleBtn.title = "Hide trend chart";
    toggleBtn.setAttribute("aria-label", "Toggle trend chart visibility");
    toggleBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const body = panel.querySelector(".plo-trend-panel-body");
      if (!body) return;
      const hidden = body.style.display === "none";
      body.style.display = hidden ? "" : "none";
      toggleBtn.innerHTML = hidden ? "&#128065;" : "&#128064;"; // 👁 vs 👀
      toggleBtn.title = hidden ? "Hide trend chart" : "Show trend chart";
      panel.classList.toggle("plo-trend-panel--collapsed", !hidden);
    });
    panel.appendChild(toggleBtn);

    // Wrap canvas + composition bar in a body div for show/hide
    const body = document.createElement("div");
    body.className = "plo-trend-panel-body";

    const canvas = document.createElement("canvas");
    canvas.style.width = "100%";
    canvas.style.height = "300px";
    body.appendChild(canvas);
    panel.appendChild(body);

    if (!trendPoints || trendPoints.length === 0) {
      const msg = document.createElement("p");
      msg.className = "text-muted text-center py-3";
      msg.textContent = "No trend data available.";
      body.appendChild(msg);
      return panel;
    }

    const labels = terms.map((t) => t.term_name || "");
    const data = trendPoints.map((p) =>
      p !== null && p.pass_rate !== null ? p.pass_rate : NaN,
    );

    const threshold = (opts && opts.threshold) || 70;
    const title = (opts && opts.title) || "Pass Rate Trend";
    const clos = (opts && opts.clos) || [];
    const discontinuities = (opts && opts.discontinuities) || [];

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

    // --- Build datasets array ---
    // For CLO-level charts (no CLO overlays), use a context-aware label
    const mainLabel =
      (opts && opts.mainLabel) || (clos.length > 0 ? "PLO Pass Rate %" : title);

    const datasets = [
      {
        label: mainLabel,
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
        borderWidth: 2.5,
        spanGaps: true,
        order: 0, // draw on top
        segment: {
          borderDash: (ctx) =>
            currentTermIndices.has(ctx.p1DataIndex)
              ? TREND_NULL_DASH
              : undefined,
        },
      },
    ];

    // --- CLO overlay lines (Feature #1) ---
    if (clos.length > 0) {
      clos.forEach((clo, ci) => {
        const color = CLO_COLORS[ci % CLO_COLORS.length];
        const cloData = (clo.trend || []).map((p) =>
          p !== null && p.pass_rate !== null ? p.pass_rate : NaN,
        );
        datasets.push({
          label: cloLabel(clo),
          data: cloData,
          borderColor: color,
          backgroundColor: "transparent",
          fill: false,
          tension: 0.3,
          pointRadius: 2,
          pointHoverRadius: 4,
          pointBackgroundColor: color,
          pointBorderColor: color,
          borderWidth: 1.5,
          spanGaps: true,
          order: 1, // behind PLO line
        });
      });
    }

    requestAnimationFrame(() => {
      if (typeof Chart === "undefined") return;

      new Chart(canvas, {
        type: "line",
        data: { labels, datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 300 },
          plugins: {
            legend: {
              display: clos.length > 0,
              position: "bottom",
              labels: {
                usePointStyle: true,
                pointStyle: "line",
                font: { size: 10 },
                boxWidth: 20,
                padding: 8,
              },
              onClick(_e, legendItem, legend) {
                const chart = legend.chart;
                const ci = legendItem.datasetIndex;
                const allHidden = chart.data.datasets.every(
                  (ds, i) => i === ci || !chart.isDatasetVisible(i),
                );
                if (allHidden) {
                  // Un-solo: show all
                  chart.data.datasets.forEach((_ds, i) => {
                    chart.setDatasetVisibility(i, true);
                  });
                } else {
                  // Solo: show only clicked
                  chart.data.datasets.forEach((_ds, i) => {
                    chart.setDatasetVisibility(i, i === ci);
                  });
                }
                chart.update();
              },
            },
            title: {
              display: true,
              text: title,
              font: { size: 13, weight: "normal" },
              color: "#6c757d",
            },
            tooltip: {
              mode: "index",
              intersect: false,
              callbacks: {
                title: (items) => items[0]?.label || "",
                label: (item) => {
                  if (item.raw === null || isNaN(item.raw)) return null;
                  const dsIndex = item.datasetIndex;
                  const pct = `${Math.round(item.raw)}%`;
                  if (dsIndex === 0) {
                    // Main line (PLO aggregate or CLO individual)
                    const point = trendPoints[item.dataIndex];
                    if (point && point.students_took) {
                      return `${item.dataset.label}: ${pct} (${point.students_passed}/${point.students_took})`;
                    }
                    return `${item.dataset.label}: ${pct}`;
                  }
                  // CLO overlay line
                  const cloIdx = dsIndex - 1;
                  const clo = clos[cloIdx];
                  const cloPoint = clo && (clo.trend || [])[item.dataIndex];
                  if (cloPoint && cloPoint.students_took) {
                    return `${item.dataset.label}: ${pct} (${cloPoint.students_passed}/${cloPoint.students_took})`;
                  }
                  return `${item.dataset.label}: ${pct}`;
                },
                afterLabel: (item) => {
                  if (item.raw === null || isNaN(item.raw)) return "";
                  const dsIndex = item.datasetIndex;
                  if (dsIndex === 0) return ""; // PLO line — no description
                  const clo = clos[dsIndex - 1];
                  if (clo && clo.description) {
                    const desc = clo.description;
                    // Truncate long descriptions for tooltip readability
                    return `  "${desc.length > 60 ? desc.slice(0, 57) + "…" : desc}"`;
                  }
                  return "";
                },
                // Filter out null entries from tooltip
                filter: (item) => item.raw !== null && !isNaN(item.raw),
                afterBody: (items) => {
                  if (!discontinuities || discontinuities.length === 0)
                    return "";
                  const idx = items[0] && items[0].dataIndex;
                  if (idx == null) return "";
                  // Find any discontinuity AT this term index
                  const disc = discontinuities.find(
                    (d) => d.term_index === idx,
                  );
                  if (!disc) return "";
                  const lines = ["\n─── Course changes ───"];
                  const prev = [];
                  const curr = [];
                  if (disc.removed && disc.removed.length > 0) {
                    disc.removed.forEach((r) => prev.push(r.label));
                  }
                  if (disc.added && disc.added.length > 0) {
                    disc.added.forEach((a) => curr.push(a.label));
                  }
                  if (prev.length > 0 || curr.length > 0) {
                    const maxLen = Math.max(prev.length, curr.length);
                    for (let i = 0; i < maxLen; i++) {
                      const left = prev[i] ? "− " + prev[i] : "";
                      const right = curr[i] ? "+ " + curr[i] : "";
                      if (left && right) {
                        lines.push(left + "  │  " + right);
                      } else {
                        lines.push(left || "          │  " + right);
                      }
                    }
                  }
                  return lines;
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
              ...computeYRange(datasets),
              ticks: {
                callback: (v) => v + "%",
                font: { size: 11 },
              },
              grid: { color: "rgba(0,0,0,0.05)" },
            },
          },
          // Click-to-drill: clicking a data point sets the term filter
          onClick(_event, elements) {
            if (!elements || elements.length === 0) return;
            const idx = elements[0].index;
            const term = terms[idx];
            if (!term) return;

            const termFilter = document.getElementById("ploTermFilter");
            if (termFilter) {
              termFilter.value = term.term_id;
              termFilter.dispatchEvent(new Event("change"));
            }
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
          {
            id: "discontinuityLines",
            afterDraw(chart) {
              if (!discontinuities || discontinuities.length === 0) return;
              const xScale = chart.scales.x;
              const yScale = chart.scales.y;
              if (!xScale || !yScale) return;
              const ctx = chart.ctx;

              discontinuities.forEach((d) => {
                const ti = d.term_index;
                if (ti < 0 || ti >= labels.length) return;

                // Subtle hairline between previous and current term
                const xCurr = xScale.getPixelForValue(ti);
                const xPrev = ti > 0 ? xScale.getPixelForValue(ti - 1) : xCurr;
                const x = (xPrev + xCurr) / 2;

                ctx.save();
                ctx.strokeStyle = "rgba(255, 152, 0, 0.2)";
                ctx.lineWidth = 1;
                ctx.setLineDash([]);
                ctx.beginPath();
                ctx.moveTo(x, chart.chartArea.top);
                ctx.lineTo(x, chart.chartArea.bottom);
                ctx.stroke();
                ctx.restore();
                // Text labels removed — details shown in tooltip afterBody
              });
            },
          },
        ],
      });
    });

    // --- CLO Composition bar (Feature #4) ---
    if (clos.length > 0) {
      const compBar = createCompositionBar(clos, terms);
      body.appendChild(compBar);
    }

    return panel;
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
      if (selectedTermId !== undefined) this.selectedTermId = selectedTermId;

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
        const ploNode = container.querySelector(`[data-plo-id="${plo.id}"]`);
        if (ploNode) {
          // Remove existing trend indicators/panels for THIS node only (avoids
          // wiping indicators from other programs in the All-Programs view)
          ploNode
            .querySelectorAll(
              ":scope > .plo-tree-header .plo-trend-indicator, :scope > .plo-trend-panel",
            )
            .forEach((el) => el.remove());
          this._injectIntoNode(ploNode, plo.trend, terms, {
            title: `PLO-${plo.plo_number}: ${plo.description}`,
            clos: plo.clos || [],
            discontinuities: plo.discontinuities || [],
            selectedTermIndex,
          });
        }

        // CLO nodes
        (plo.clos || []).forEach((clo) => {
          const cloNode = container.querySelector(
            `[data-clo-id="${clo.outcome_id}"]`,
          );
          if (cloNode) {
            cloNode
              .querySelectorAll(
                ":scope > .plo-tree-header .plo-trend-indicator, :scope > .plo-trend-panel",
              )
              .forEach((el) => el.remove());
            this._injectIntoNode(cloNode, clo.trend, terms, {
              title: `${clo.course_number || ""} CLO ${clo.clo_number || "?"}: ${clo.description || ""}`,
              discontinuities: plo.discontinuities || [],
              selectedTermIndex,
            });
          }
        });
      });

      // Populate summary bar sparklines
      this._injectSummarySparklines(container, plos, terms, selectedTermIndex);
    },

    /**
     * Inject sparkline canvases into summary bar sparkline slots.
     * Each slot is tagged with data-plo-id matching a PLO in the trend data.
     * Clicking a sparkline toggles a full trend panel below the category row.
     */
    _injectSummarySparklines(container, plos, terms, selectedTermIndex) {
      const slots = container.querySelectorAll(".plo-summary-sparkline-slot");
      slots.forEach((slot) => {
        const ploId = slot.dataset.ploId;
        const plo = (plos || []).find((p) => String(p.id) === String(ploId));
        if (!plo || !plo.trend || plo.trend.length < 2) return;

        // Remove existing sparkline / badge if re-injecting
        const existing = slot.querySelector(".plo-sparkline");
        if (existing) existing.remove();
        const existingBadge = slot.querySelector(".plo-trend-indicator");
        if (existingBadge) existingBadge.remove();

        const canvas = createSparkline(plo.trend, terms, {
          threshold: 70,
          discontinuities: plo.discontinuities || [],
          selectedTermIndex: selectedTermIndex != null ? selectedTermIndex : -1,
        });
        slot.insertBefore(canvas, slot.firstChild);

        // Add compact trend badge (arrow + delta) after the sparkline
        const direction = getTrendDirection(plo.trend);
        const { arrow, cssClass } = getTrendArrow(direction);
        const delta = getTrendDelta(plo.trend);
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

        // Click opens trend panel below the row
        canvas.addEventListener("click", (e) => {
          e.stopPropagation();
          this._toggleSummaryTrendPanel(slot, plo, terms);
        });
      });
    },

    /**
     * Toggle a trend chart panel below the summary row containing the clicked sparkline.
     */
    _toggleSummaryTrendPanel(slot, plo, terms) {
      const row = slot.closest(".plo-summary-row");
      if (!row) return;

      // Check if this PLO's panel is already open
      const next = row.nextElementSibling;
      if (
        next &&
        next.classList.contains("plo-trend-panel") &&
        next.dataset.ploId === String(plo.id)
      ) {
        next.remove();
        return;
      }

      // Remove any other open panel in this summary bar
      const bar = slot.closest(".plo-summary-bar");
      if (bar) {
        bar.querySelectorAll(".plo-trend-panel").forEach((p) => p.remove());
      }

      const panel = createTrendPanel(plo.trend, terms, {
        title: "PLO-" + plo.plo_number + ": " + plo.description,
        clos: plo.clos || [],
        discontinuities: plo.discontinuities || [],
      });
      panel.dataset.ploId = String(plo.id);
      row.after(panel);
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

      // Trend direction + delta
      const direction = getTrendDirection(trendPoints);
      const { arrow, cssClass } = getTrendArrow(direction);
      const delta = getTrendDelta(trendPoints);

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

      // Click handler for drill-down panel
      wrap.addEventListener("click", (e) => {
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
      createCompositionBar,
      computeYRange,
      getTrendDirection,
      getTrendArrow,
      getTrendDelta,
    };
  }
})();
