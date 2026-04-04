(function () {
  "use strict";

  const SPARK_WIDTH = 100;
  const SPARK_HEIGHT = 32;
  const TREND_LINE_COLOR = "#0d6efd";
  const TREND_LINE_COLOR_FAIL = "#dc3545";
  const TREND_LINE_COLOR_FUTURE = "rgba(160, 170, 180, 0.45)";
  const TREND_FILL_ALPHA_TOP = 0.18;
  const TREND_FILL_ALPHA_BOTTOM = 0.02;
  const TREND_NULL_DASH = [4, 4];
  const THRESHOLD_LINE_COLOR = "rgba(108, 117, 125, 0.3)";

  function buildSparklineInputs(trendPoints, terms, opts) {
    const labels = terms.map((t) => t.term_name || "");
    const data = trendPoints.map((p) =>
      p !== null && p.pass_rate !== null ? p.pass_rate : NaN,
    );
    const currentTermIndices = new Set(
      terms.map((t, i) => (t.is_current ? i : -1)).filter((i) => i >= 0),
    );
    const threshold = (opts && opts.threshold) || 70;
    const selectedTermIndex =
      opts && opts.selectedTermIndex != null && opts.selectedTermIndex >= 0
        ? opts.selectedTermIndex
        : -1;
    const hasFuture =
      selectedTermIndex >= 0 && selectedTermIndex < data.length - 1;
    const lastValid = data.filter((d) => !isNaN(d));
    const lineColor =
      lastValid.length > 0 && lastValid[lastValid.length - 1] < threshold
        ? TREND_LINE_COLOR_FAIL
        : TREND_LINE_COLOR;
    const lastValidIdx = data.reduce((acc, d, i) => (!isNaN(d) ? i : acc), -1);
    const dotIdx =
      selectedTermIndex >= 0 && !isNaN(data[selectedTermIndex])
        ? selectedTermIndex
        : lastValidIdx;
    const pointColors = data.map((_, i) =>
      hasFuture && i > selectedTermIndex ? TREND_LINE_COLOR_FUTURE : lineColor,
    );

    return {
      currentTermIndices,
      data,
      hasFuture,
      labels,
      lineColor,
      pointBorders: pointColors,
      pointColors,
      pointRadii: data.map((_, i) => (i === dotIdx ? 3 : 0)),
      selectedTermIndex,
      threshold,
    };
  }

  function buildSparklineGradients(canvas) {
    const blueRgb = "13, 110, 253";
    const redRgb = "220, 53, 69";
    const ctx2d = canvas.getContext("2d");
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
    return { gradientFillBlue, gradientFillRed };
  }

  function createBelowThresholdFillPlugin(threshold, gradientFillRed) {
    return {
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
        ctx.fillStyle =
          typeof gradientFillRed === "object"
            ? gradientFillRed
            : `rgba(220, 53, 69, ${TREND_FILL_ALPHA_TOP})`;
        ctx.fillRect(left, threshY, right - left, bottom - threshY);
        ctx.restore();
      },
    };
  }

  function createThresholdLinePlugin(threshold) {
    return {
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
    };
  }

  function createSparkDiscontinuityPlugin(labels, opts) {
    return {
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
    };
  }

  function createFutureWashPlugin(hasFuture, selectedTermIndex) {
    return {
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
    };
  }

  function createSparklinePlugins(config) {
    return [
      createBelowThresholdFillPlugin(config.threshold, config.gradientFillRed),
      createThresholdLinePlugin(config.threshold),
      createSparkDiscontinuityPlugin(config.labels, config.opts),
      createFutureWashPlugin(config.hasFuture, config.selectedTermIndex),
    ];
  }

  function createSparkline(trendPoints, terms, opts) {
    const canvas = document.createElement("canvas");
    canvas.width = SPARK_WIDTH;
    canvas.height = SPARK_HEIGHT;
    canvas.className = "plo-sparkline";
    canvas.style.width = SPARK_WIDTH + "px";
    canvas.style.height = SPARK_HEIGHT + "px";
    canvas.title = "Click to view full trend chart";

    if (!trendPoints || trendPoints.length === 0) return canvas;

    const sparkline = buildSparklineInputs(trendPoints, terms, opts);

    requestAnimationFrame(() => {
      if (typeof Chart === "undefined") return;

      const gradients = buildSparklineGradients(canvas);

      new Chart(canvas, {
        type: "line",
        data: {
          labels: sparkline.labels,
          datasets: [
            {
              data: sparkline.data,
              borderColor: sparkline.lineColor,
              backgroundColor: gradients.gradientFillBlue,
              fill: true,
              tension: 0.4,
              pointRadius: sparkline.pointRadii,
              pointBackgroundColor: sparkline.pointColors,
              pointBorderColor: sparkline.pointBorders,
              pointBorderWidth: 1.5,
              borderWidth: 2,
              borderCapStyle: "round",
              borderJoinStyle: "round",
              spanGaps: true,
              segment: {
                borderDash: (ctx) =>
                  sparkline.currentTermIndices.has(ctx.p1DataIndex)
                    ? TREND_NULL_DASH
                    : undefined,
                borderColor: (ctx) => {
                  if (
                    sparkline.hasFuture &&
                    ctx.p0DataIndex >= sparkline.selectedTermIndex
                  ) {
                    return TREND_LINE_COLOR_FUTURE;
                  }
                  const p0 = ctx.p0.parsed.y;
                  const p1 = ctx.p1.parsed.y;
                  if (
                    !isNaN(p0) &&
                    !isNaN(p1) &&
                    p0 < sparkline.threshold &&
                    p1 < sparkline.threshold
                  ) {
                    return TREND_LINE_COLOR_FAIL;
                  }
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
          events: [],
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
        plugins: createSparklinePlugins({
          gradientFillRed: gradients.gradientFillRed,
          hasFuture: sparkline.hasFuture,
          labels: sparkline.labels,
          opts,
          selectedTermIndex: sparkline.selectedTermIndex,
          threshold: sparkline.threshold,
        }),
      });
    });

    return canvas;
  }

  const api = { createSparkline };
  if (typeof globalThis !== "undefined") {
    globalThis.PloTrendSparkline = api;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})();
