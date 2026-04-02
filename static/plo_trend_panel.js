(function () {
  "use strict";

  function updateTrendToggleState(toggleBtn, hidden) {
    toggleBtn.textContent = hidden ? "\u{1F441}" : "\u{1F440}";
    toggleBtn.title = hidden ? "Show trend chart" : "Hide trend chart";
    toggleBtn.setAttribute("aria-expanded", String(!hidden));
    toggleBtn.setAttribute(
      "aria-label",
      hidden ? "Show trend chart" : "Hide trend chart",
    );
  }

  function createTrendPanelShell() {
    const panel = document.createElement("div");
    panel.className = "plo-trend-panel";

    const body = document.createElement("div");
    body.className = "plo-trend-panel-body";

    const canvas = document.createElement("canvas");
    canvas.style.width = "100%";
    canvas.style.height = "300px";
    body.appendChild(canvas);
    panel.appendChild(body);

    const toggleBtn = document.createElement("button");
    toggleBtn.type = "button";
    toggleBtn.className = "plo-trend-panel-toggle";
    updateTrendToggleState(toggleBtn, false);
    toggleBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const hidden = body.style.display === "none";
      body.style.display = hidden ? "" : "none";
      updateTrendToggleState(toggleBtn, !hidden);
      panel.classList.toggle("plo-trend-panel--collapsed", !hidden);
    });
    panel.insertBefore(toggleBtn, body);

    return { body, canvas, panel };
  }

  function renderNoTrendData(body) {
    const msg = document.createElement("p");
    msg.className = "text-muted text-center py-3";
    msg.textContent = "No trend data available.";
    body.appendChild(msg);
  }

  function getTrendPanelModel(trendPoints, terms, opts, deps) {
    const { TREND_LINE_COLOR, TREND_LINE_COLOR_FAIL } = deps;
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
    const pointColors = data.map((d) =>
      !isNaN(d) && d < threshold ? TREND_LINE_COLOR_FAIL : TREND_LINE_COLOR,
    );
    const failRadii = data.map((d) => (!isNaN(d) && d < threshold ? 6 : 4));
    const pointBorders = data.map((d) =>
      !isNaN(d) && d < threshold ? TREND_LINE_COLOR_FAIL : TREND_LINE_COLOR,
    );
    const lastValid = data.filter((d) => !isNaN(d));
    const lineColor =
      lastValid.length > 0 && lastValid[lastValid.length - 1] < threshold
        ? TREND_LINE_COLOR_FAIL
        : TREND_LINE_COLOR;

    return {
      clos,
      currentTermIndices,
      data,
      discontinuities,
      failRadii,
      labels,
      lineColor,
      pointBorders,
      pointColors,
      threshold,
      title,
    };
  }

  function buildPrimaryDataset(model, deps, opts) {
    const { TREND_FILL_COLOR, TREND_NULL_DASH } = deps;
    const mainLabel =
      (opts && opts.mainLabel) ||
      (model.clos.length > 0 ? "PLO Pass Rate %" : model.title);

    return {
      label: mainLabel,
      data: model.data,
      borderColor: model.lineColor,
      backgroundColor: TREND_FILL_COLOR,
      fill: true,
      tension: 0.3,
      pointRadius: model.failRadii,
      pointHoverRadius: 6,
      pointBackgroundColor: model.pointColors,
      pointBorderColor: model.pointBorders,
      pointBorderWidth: 1.5,
      borderWidth: 2.5,
      spanGaps: true,
      order: 0,
      segment: {
        borderDash: (ctx) =>
          model.currentTermIndices.has(ctx.p1DataIndex)
            ? TREND_NULL_DASH
            : undefined,
      },
    };
  }

  function buildOverlayDatasets(model, deps) {
    const { CLO_COLORS, cloLabel } = deps;
    return model.clos.map((clo, ci) => {
      const color = CLO_COLORS[ci % CLO_COLORS.length];
      const cloData = (clo.trend || []).map((p) =>
        p !== null && p.pass_rate !== null ? p.pass_rate : NaN,
      );
      return {
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
        order: 1,
      };
    });
  }

  function buildTrendDatasets(model, deps, opts) {
    return [
      buildPrimaryDataset(model, deps, opts),
      ...buildOverlayDatasets(model, deps),
    ];
  }

  function buildTrendTooltipCallbacks(trendPoints, model) {
    return {
      title: (items) => items[0]?.label || "",
      label: (item) => {
        if (item.raw === null || isNaN(item.raw)) return null;
        const dsIndex = item.datasetIndex;
        const pct = `${Math.round(item.raw)}%`;
        if (dsIndex === 0) {
          const point = trendPoints[item.dataIndex];
          if (point && point.students_took) {
            return `${item.dataset.label}: ${pct} (${point.students_passed}/${point.students_took})`;
          }
          return `${item.dataset.label}: ${pct}`;
        }
        const clo = model.clos[dsIndex - 1];
        const cloPoint = clo && (clo.trend || [])[item.dataIndex];
        if (cloPoint && cloPoint.students_took) {
          return `${item.dataset.label}: ${pct} (${cloPoint.students_passed}/${cloPoint.students_took})`;
        }
        return `${item.dataset.label}: ${pct}`;
      },
      afterLabel: (item) => {
        if (item.raw === null || isNaN(item.raw) || item.datasetIndex === 0) {
          return "";
        }
        const clo = model.clos[item.datasetIndex - 1];
        if (!clo || !clo.description) {
          return "";
        }
        const desc = clo.description;
        return `  "${desc.length > 60 ? desc.slice(0, 57) + "…" : desc}"`;
      },
      filter: (item) => item.raw !== null && !isNaN(item.raw),
      afterBody: (items) =>
        buildDiscontinuityTooltip(items, model.discontinuities),
    };
  }

  function buildDiscontinuityTooltip(items, discontinuities) {
    if (!discontinuities || discontinuities.length === 0) {
      return "";
    }
    const idx = items[0] && items[0].dataIndex;
    if (idx == null) return "";
    const disc = discontinuities.find((d) => d.term_index === idx);
    if (!disc) return "";

    const lines = ["\n─── Course changes ───"];
    const prev = (disc.removed || []).map((r) => r.label);
    const curr = (disc.added || []).map((a) => a.label);
    const maxLen = Math.max(prev.length, curr.length);
    for (let i = 0; i < maxLen; i++) {
      const left = prev[i] ? "− " + prev[i] : "";
      const right = curr[i] ? "+ " + curr[i] : "";
      lines.push(
        left && right
          ? left + "  │  " + right
          : left || "          │  " + right,
      );
    }
    return lines;
  }

  function handleLegendClick(legendItem, legend) {
    const chart = legend.chart;
    const ci = legendItem.datasetIndex;
    const allHidden = chart.data.datasets.every(
      (_ds, i) => i === ci || !chart.isDatasetVisible(i),
    );
    chart.data.datasets.forEach((_ds, i) => {
      chart.setDatasetVisibility(i, allHidden || i === ci);
    });
    chart.update();
  }

  function buildTrendOptions(terms, trendPoints, model, datasets, deps, extra) {
    var callbacks = extra || {};
    const { computeYRange } = deps;
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 300 },
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          display: model.clos.length > 0,
          position: "bottom",
          labels: {
            usePointStyle: true,
            pointStyle: "line",
            font: { size: 10 },
            boxWidth: 20,
            padding: 8,
          },
          onClick(_e, legendItem, legend) {
            handleLegendClick(legendItem, legend);
          },
        },
        title: {
          display: true,
          text: model.title,
          font: { size: 13, weight: "normal" },
          color: "#6c757d",
        },
        tooltip: {
          mode: "index",
          intersect: false,
          callbacks: buildTrendTooltipCallbacks(trendPoints, model),
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
      onClick(_event, elements) {
        if (!elements || elements.length === 0) return;
        const idx = elements[0].index;
        const term = terms[idx];
        if (!term) return;
        var handled = false;
        if (callbacks.onPointClick) {
          handled = callbacks.onPointClick(term);
        }
        if (!handled) {
          // Fallback: change term filter (gives user immediate feedback)
          const termFilter = document.getElementById("ploTermFilter");
          if (termFilter) {
            termFilter.value = term.term_id;
            termFilter.dispatchEvent(new Event("change"));
          }
        }
      },
      onHover(event, elements) {
        var canvas = event.native ? event.native.target : null;
        if (canvas) {
          canvas.style.cursor =
            elements && elements.length > 0 ? "pointer" : "default";
        }
      },
    };
  }

  function buildTrendPlugins(model) {
    return [
      {
        id: "thresholdLine",
        afterDraw(chart) {
          const yScale = chart.scales.y;
          if (!yScale) return;
          const y = yScale.getPixelForValue(model.threshold);
          const ctx = chart.ctx;
          ctx.save();
          ctx.strokeStyle = "rgba(220, 53, 69, 0.4)";
          ctx.lineWidth = 1;
          ctx.setLineDash([6, 4]);
          ctx.beginPath();
          ctx.moveTo(chart.chartArea.left, y);
          ctx.lineTo(chart.chartArea.right, y);
          ctx.stroke();
          ctx.fillStyle = "rgba(220, 53, 69, 0.6)";
          ctx.font = "10px sans-serif";
          ctx.fillText(
            `Threshold ${model.threshold}%`,
            chart.chartArea.right - 80,
            y - 4,
          );
          ctx.restore();
        },
      },
      {
        id: "discontinuityLines",
        afterDraw(chart) {
          renderDiscontinuityLines(chart, model);
        },
      },
    ];
  }

  function renderDiscontinuityLines(chart, model) {
    if (!model.discontinuities || model.discontinuities.length === 0) return;
    const xScale = chart.scales.x;
    const yScale = chart.scales.y;
    if (!xScale || !yScale) return;
    const ctx = chart.ctx;

    model.discontinuities.forEach((d) => {
      const ti = d.term_index;
      if (ti < 0 || ti >= model.labels.length) return;
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
    });
  }

  function renderTrendChart(
    canvas,
    terms,
    trendPoints,
    model,
    datasets,
    deps,
    extra,
  ) {
    requestAnimationFrame(() => {
      if (typeof Chart === "undefined") return;
      new Chart(canvas, {
        type: "line",
        data: { labels: model.labels, datasets },
        options: buildTrendOptions(
          terms,
          trendPoints,
          model,
          datasets,
          deps,
          extra,
        ),
        plugins: buildTrendPlugins(model),
      });
    });
  }

  function appendCompositionBar(body, model, terms, createCompositionBar) {
    if (model.clos.length === 0) {
      return;
    }
    const compBar = createCompositionBar(model.clos, terms);
    body.appendChild(compBar);
  }

  function createTrendPanel(trendPoints, terms, opts, deps) {
    const { createCompositionBar } = deps;
    const { body, canvas, panel } = createTrendPanelShell();

    if (!trendPoints || trendPoints.length === 0) {
      renderNoTrendData(body);
      return panel;
    }

    const model = getTrendPanelModel(trendPoints, terms, opts, deps);
    const datasets = buildTrendDatasets(model, deps, opts);
    var extra =
      opts && opts.onPointClick
        ? { onPointClick: opts.onPointClick }
        : undefined;
    renderTrendChart(canvas, terms, trendPoints, model, datasets, deps, extra);
    appendCompositionBar(body, model, terms, createCompositionBar);
    return panel;
  }

  const exportsObj = { buildTrendOptions, createTrendPanel };
  if (typeof globalThis !== "undefined") {
    globalThis.PloTrendPanel = exportsObj;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = exportsObj;
  }
})();
