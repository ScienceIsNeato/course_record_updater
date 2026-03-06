/**
 * Unit tests for static/plo_trend.js.
 *
 * Covers:
 *  - getTrendDirection: trend detection from data points
 *  - getTrendArrow: arrow character + CSS class mapping
 *  - createSparkline: DOM element creation (Chart.js mocked)
 *  - createTrendPanel: panel DOM structure + close button
 *  - PloTrend controller: loadTrend, injectSparklines, toggle panel
 */

// Mock Chart.js globally before requiring the module
global.Chart = jest.fn().mockImplementation(() => ({
  destroy: jest.fn(),
  update: jest.fn(),
  scales: { y: { getPixelForValue: jest.fn().mockReturnValue(50) } },
  ctx: {
    save: jest.fn(),
    restore: jest.fn(),
    beginPath: jest.fn(),
    moveTo: jest.fn(),
    lineTo: jest.fn(),
    stroke: jest.fn(),
    fillText: jest.fn(),
    set strokeStyle(_) {},
    set lineWidth(_) {},
    set fillStyle(_) {},
    set font(_) {},
    setLineDash: jest.fn(),
  },
  chartArea: { left: 0, right: 100 },
}));

// Execute requestAnimationFrame callbacks synchronously so Chart.js
// rendering code is exercised for coverage.
global.requestAnimationFrame = (cb) => cb();

const {
  getTrendDirection,
  getTrendArrow,
  getTrendDelta,
  createSparkline,
  createTrendPanel,
  createCompositionBar,
  computeYRange,
  PloTrend,
} = require("../../../static/plo_trend");

// ---------------------------------------------------------------------------
// getTrendDirection
// ---------------------------------------------------------------------------
describe("getTrendDirection", () => {
  test("returns 'none' for empty array", () => {
    expect(getTrendDirection([])).toBe("none");
  });

  test("returns 'none' for single point", () => {
    expect(getTrendDirection([{ pass_rate: 80 }])).toBe("none");
  });

  test("returns 'none' when all points are null", () => {
    expect(getTrendDirection([null, null, null])).toBe("none");
  });

  test("returns 'none' when all pass_rates are null", () => {
    expect(
      getTrendDirection([{ pass_rate: null }, { pass_rate: null }])
    ).toBe("none");
  });

  test("returns 'up' when last > first by 2–9 pp", () => {
    const points = [{ pass_rate: 70 }, { pass_rate: 75 }];
    expect(getTrendDirection(points)).toBe("up");
  });

  test("returns 'strong-up' when last > first by >= 10 pp", () => {
    const points = [{ pass_rate: 60 }, { pass_rate: 70 }, { pass_rate: 80 }];
    expect(getTrendDirection(points)).toBe("strong-up");
  });

  test("returns 'down' when last < first by 2–9 pp", () => {
    const points = [{ pass_rate: 80 }, { pass_rate: 75 }];
    expect(getTrendDirection(points)).toBe("down");
  });

  test("returns 'strong-down' when last < first by >= 10 pp", () => {
    const points = [{ pass_rate: 90 }, { pass_rate: 70 }, { pass_rate: 60 }];
    expect(getTrendDirection(points)).toBe("strong-down");
  });

  test("returns 'flat' when difference < 2", () => {
    const points = [{ pass_rate: 80 }, { pass_rate: 81 }];
    expect(getTrendDirection(points)).toBe("flat");
  });

  test("returns 'flat' for exact same values", () => {
    const points = [{ pass_rate: 75 }, { pass_rate: 75 }];
    expect(getTrendDirection(points)).toBe("flat");
  });

  test("skips null entries when computing direction", () => {
    const points = [{ pass_rate: 70 }, null, { pass_rate: 78 }];
    expect(getTrendDirection(points)).toBe("up");
  });

  test("skips entries with null pass_rate", () => {
    const points = [
      { pass_rate: 80 },
      { pass_rate: null },
      { pass_rate: 75 },
    ];
    expect(getTrendDirection(points)).toBe("down");
  });
});

// ---------------------------------------------------------------------------
// getTrendArrow
// ---------------------------------------------------------------------------
describe("getTrendArrow", () => {
  test("up → ↑ with trend-up class", () => {
    expect(getTrendArrow("up")).toEqual({ arrow: "↑", cssClass: "trend-up" });
  });

  test("strong-up → ⬆ with trend-strong-up class", () => {
    expect(getTrendArrow("strong-up")).toEqual({
      arrow: "⬆",
      cssClass: "trend-strong-up",
    });
  });

  test("down → ↓ with trend-down class", () => {
    expect(getTrendArrow("down")).toEqual({
      arrow: "↓",
      cssClass: "trend-down",
    });
  });

  test("strong-down → ⬇ with trend-strong-down class", () => {
    expect(getTrendArrow("strong-down")).toEqual({
      arrow: "⬇",
      cssClass: "trend-strong-down",
    });
  });

  test("flat → → with trend-flat class", () => {
    expect(getTrendArrow("flat")).toEqual({
      arrow: "→",
      cssClass: "trend-flat",
    });
  });

  test("none → empty arrow with trend-none class", () => {
    expect(getTrendArrow("none")).toEqual({
      arrow: "",
      cssClass: "trend-none",
    });
  });

  test("unknown direction falls through to default", () => {
    expect(getTrendArrow("sideways")).toEqual({
      arrow: "",
      cssClass: "trend-none",
    });
  });
});

// ---------------------------------------------------------------------------
// getTrendDelta
// ---------------------------------------------------------------------------
describe("getTrendDelta", () => {
  test("returns rounded delta between first and last valid points", () => {
    const pts = [{ pass_rate: 70 }, { pass_rate: 75 }, { pass_rate: 82.6 }];
    expect(getTrendDelta(pts)).toBe(13);
  });

  test("returns negative delta when trending down", () => {
    const pts = [{ pass_rate: 90 }, { pass_rate: 80 }];
    expect(getTrendDelta(pts)).toBe(-10);
  });

  test("returns 0 for flat trend", () => {
    const pts = [{ pass_rate: 70 }, { pass_rate: 70 }];
    expect(getTrendDelta(pts)).toBe(0);
  });

  test("returns null for single data point", () => {
    expect(getTrendDelta([{ pass_rate: 80 }])).toBeNull();
  });

  test("returns null for empty or null input", () => {
    expect(getTrendDelta([])).toBeNull();
    expect(getTrendDelta(null)).toBeNull();
  });

  test("skips null points", () => {
    const pts = [{ pass_rate: 60 }, null, { pass_rate: null }, { pass_rate: 80 }];
    expect(getTrendDelta(pts)).toBe(20);
  });
});

// ---------------------------------------------------------------------------
// createSparkline
// ---------------------------------------------------------------------------
describe("createSparkline", () => {
  const terms = [
    { term_name: "Fall 2024", is_current: false },
    { term_name: "Spring 2025", is_current: true },
  ];
  const points = [{ pass_rate: 80 }, { pass_rate: 65 }];

  test("returns a canvas element", () => {
    const canvas = createSparkline(points, terms, { threshold: 70 });
    expect(canvas.tagName).toBe("CANVAS");
  });

  test("canvas has correct dimensions and class", () => {
    const canvas = createSparkline(points, terms);
    expect(canvas.width).toBe(100);
    expect(canvas.height).toBe(32);
    expect(canvas.className).toBe("plo-sparkline");
  });

  test("canvas has click-hint title", () => {
    const canvas = createSparkline(points, terms);
    expect(canvas.title).toBe("Click to view full trend chart");
  });

  test("returns empty canvas for null/empty points", () => {
    const canvas1 = createSparkline(null, terms);
    expect(canvas1.tagName).toBe("CANVAS");

    const canvas2 = createSparkline([], terms);
    expect(canvas2.tagName).toBe("CANVAS");
  });

  test("accepts selectedTermIndex option without error", () => {
    const multiTerms = [
      { term_name: "Fall 2023", is_current: false },
      { term_name: "Spring 2024", is_current: false },
      { term_name: "Fall 2024", is_current: false },
      { term_name: "Spring 2025", is_current: true },
    ];
    const multiPoints = [
      { pass_rate: 75 },
      { pass_rate: 80 },
      { pass_rate: 72 },
      { pass_rate: 85 },
    ];
    // Select an older term (Fall 2024, index 2)
    const canvas = createSparkline(multiPoints, multiTerms, {
      threshold: 70,
      selectedTermIndex: 2,
    });
    expect(canvas.tagName).toBe("CANVAS");
    expect(canvas.className).toBe("plo-sparkline");
  });

  test("selectedTermIndex -1 uses default behavior", () => {
    const canvas = createSparkline(points, terms, {
      threshold: 70,
      selectedTermIndex: -1,
    });
    expect(canvas.tagName).toBe("CANVAS");
  });
});

// ---------------------------------------------------------------------------
// createTrendPanel
// ---------------------------------------------------------------------------
describe("createTrendPanel", () => {
  const terms = [
    { term_name: "Fall 2024", is_current: false },
    { term_name: "Spring 2025", is_current: false },
  ];
  const points = [{ pass_rate: 80 }, { pass_rate: 90 }];

  test("returns a div with plo-trend-panel class", () => {
    const panel = createTrendPanel(points, terms, { threshold: 70 });
    expect(panel.tagName).toBe("DIV");
    expect(panel.className).toBe("plo-trend-panel");
  });

  test("contains a visibility toggle button", () => {
    const panel = createTrendPanel(points, terms);
    const toggleBtn = panel.querySelector(".plo-trend-panel-toggle");
    expect(toggleBtn).not.toBeNull();
    expect(toggleBtn.tagName).toBe("BUTTON");
    expect(toggleBtn.title).toBe("Hide trend chart");
  });

  test("toggle button hides and shows the panel body", () => {
    const parent = document.createElement("div");
    const panel = createTrendPanel(points, terms);
    parent.appendChild(panel);

    const toggleBtn = panel.querySelector(".plo-trend-panel-toggle");
    const body = panel.querySelector(".plo-trend-panel-body");
    expect(body).not.toBeNull();
    expect(body.style.display).toBe("");

    // First click: hide
    toggleBtn.click();
    expect(body.style.display).toBe("none");
    expect(panel.classList.contains("plo-trend-panel--collapsed")).toBe(true);

    // Second click: show
    toggleBtn.click();
    expect(body.style.display).toBe("");
    expect(panel.classList.contains("plo-trend-panel--collapsed")).toBe(false);
  });

  test("contains a canvas element inside body", () => {
    const panel = createTrendPanel(points, terms);
    const body = panel.querySelector(".plo-trend-panel-body");
    expect(body).not.toBeNull();
    const canvas = body.querySelector("canvas");
    expect(canvas).not.toBeNull();
  });

  test("shows no-data message when points are empty", () => {
    const panel = createTrendPanel([], terms);
    expect(panel.textContent).toContain("No trend data available");
  });

  test("shows no-data message when points are null", () => {
    const panel = createTrendPanel(null, terms);
    expect(panel.textContent).toContain("No trend data available");
  });
});

// ---------------------------------------------------------------------------
// computeYRange
// ---------------------------------------------------------------------------
describe("computeYRange", () => {
  test("returns 0-100 for empty datasets", () => {
    expect(computeYRange([])).toEqual({ min: 0, max: 100 });
  });

  test("returns 0-100 for all-NaN data", () => {
    expect(computeYRange([{ data: [NaN, NaN] }])).toEqual({ min: 0, max: 100 });
  });

  test("zooms into data range with padding", () => {
    const result = computeYRange([{ data: [60, 70, 80] }]);
    expect(result.min).toBeLessThanOrEqual(57);
    expect(result.max).toBeGreaterThanOrEqual(83);
    expect(result.min).toBeGreaterThanOrEqual(0);
    expect(result.max).toBeLessThanOrEqual(100);
  });

  test("clamps to 0-100 bounds", () => {
    const result = computeYRange([{ data: [2, 98] }]);
    expect(result.min).toBeGreaterThanOrEqual(0);
    expect(result.max).toBeLessThanOrEqual(100);
  });

  test("handles multiple datasets", () => {
    const result = computeYRange([
      { data: [60, 70] },
      { data: [50, 90] },
    ]);
    expect(result.min).toBeLessThanOrEqual(44);
    expect(result.max).toBeGreaterThanOrEqual(96);
  });

  test("handles single-value data without zero span", () => {
    const result = computeYRange([{ data: [75] }]);
    expect(result.min).toBeLessThan(75);
    expect(result.max).toBeGreaterThan(75);
  });
});

// ---------------------------------------------------------------------------
// createCompositionBar
// ---------------------------------------------------------------------------
describe("createCompositionBar", () => {
  const terms = [
    { term_name: "Fall 2024", is_current: false },
    { term_name: "Spring 2025", is_current: false },
  ];

  test("returns a div with plo-composition-bar class", () => {
    const bar = createCompositionBar([], terms);
    expect(bar.tagName).toBe("DIV");
    expect(bar.className).toBe("plo-composition-bar");
  });

  test("creates one cell per term", () => {
    const clos = [
      {
        course_number: "CS101",
        trend: [{ pass_rate: 80 }, { pass_rate: 90 }],
      },
    ];
    const bar = createCompositionBar(clos, terms);
    const cells = bar.querySelectorAll(".plo-comp-cell");
    expect(cells.length).toBe(2);
  });

  test("shows empty dots for terms with no data", () => {
    const clos = [
      {
        course_number: "CS101",
        trend: [null, { pass_rate: 90 }],
      },
    ];
    const bar = createCompositionBar(clos, terms);
    const emptyDots = bar.querySelectorAll(".plo-comp-empty");
    expect(emptyDots.length).toBe(1);
  });

  test("shows colored dots for terms with data", () => {
    const clos = [
      {
        course_number: "CS101",
        trend: [{ pass_rate: 80 }, { pass_rate: 90 }],
      },
    ];
    const bar = createCompositionBar(clos, terms);
    const dots = bar.querySelectorAll(".plo-comp-dot:not(.plo-comp-empty)");
    expect(dots.length).toBe(2);
  });

  test("includes legend with course names", () => {
    const clos = [
      {
        course_number: "CS101",
        trend: [{ pass_rate: 80 }, { pass_rate: 90 }],
      },
      {
        course_number: "CS201",
        trend: [{ pass_rate: 70 }, null],
      },
    ];
    const bar = createCompositionBar(clos, terms);
    const legend = bar.querySelector(".plo-comp-legend");
    expect(legend).not.toBeNull();
    expect(legend.textContent).toContain("CS101");
    expect(legend.textContent).toContain("CS201");
  });

  test("handles CLOs with null pass_rate as no data", () => {
    const clos = [
      {
        course_number: "CS101",
        trend: [{ pass_rate: null }, { pass_rate: 80 }],
      },
    ];
    const bar = createCompositionBar(clos, terms);
    const emptyDots = bar.querySelectorAll(".plo-comp-empty");
    expect(emptyDots.length).toBe(1);
  });

  test("handles missing course_number gracefully", () => {
    const clos = [
      {
        trend: [{ pass_rate: 80 }, { pass_rate: 90 }],
      },
    ];
    const bar = createCompositionBar(clos, terms);
    const legend = bar.querySelector(".plo-comp-legend");
    expect(legend.textContent).toContain("?");
  });

  test("no legend when no CLOs provided", () => {
    const bar = createCompositionBar([], terms);
    const legend = bar.querySelector(".plo-comp-legend");
    expect(legend).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// createTrendPanel — CLO overlays, discontinuities, composition bar
// ---------------------------------------------------------------------------
describe("createTrendPanel with CLO overlays", () => {
  const terms = [
    { term_name: "Fall 2024", term_id: "t1", is_current: false },
    { term_name: "Spring 2025", term_id: "t2", is_current: false },
  ];
  const points = [{ pass_rate: 80 }, { pass_rate: 90 }];
  const clos = [
    {
      outcome_id: "clo-1",
      clo_number: 1,
      course_number: "CS101",
      description: "Test CLO",
      trend: [{ pass_rate: 75 }, { pass_rate: 85 }],
    },
    {
      outcome_id: "clo-2",
      clo_number: 2,
      course_number: "CS201",
      description: "Another CLO",
      trend: [{ pass_rate: 70 }, { pass_rate: 95 }],
    },
  ];

  test("renders CLO composition bar inside body when CLOs provided", () => {
    const panel = createTrendPanel(points, terms, { clos });
    const body = panel.querySelector(".plo-trend-panel-body");
    const compBar = body.querySelector(".plo-composition-bar");
    expect(compBar).not.toBeNull();
  });

  test("does not render composition bar when no CLOs", () => {
    const panel = createTrendPanel(points, terms, { clos: [] });
    const compBar = panel.querySelector(".plo-composition-bar");
    expect(compBar).toBeNull();
  });

  test("Chart constructor receives multiple datasets for CLO overlays", () => {
    Chart.mockClear();
    createTrendPanel(points, terms, { clos });
    // Chart should have been called with PLO + 2 CLO datasets = 3
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const datasets = chartCall[1].data.datasets;
    expect(datasets.length).toBe(3); // 1 PLO + 2 CLO
    expect(datasets[0].label).toBe("PLO Pass Rate %");
    expect(datasets[1].label).toBe("CS101 CLO 1");
    expect(datasets[2].label).toBe("CS201 CLO 2");
  });

  test("Chart legend is displayed when CLOs present", () => {
    Chart.mockClear();
    createTrendPanel(points, terms, { clos });
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const legend = chartCall[1].options.plugins.legend;
    expect(legend.display).toBe(true);
  });

  test("Chart legend is hidden when no CLOs", () => {
    Chart.mockClear();
    createTrendPanel(points, terms, { clos: [] });
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const legend = chartCall[1].options.plugins.legend;
    expect(legend.display).toBe(false);
  });

  test("interactive legend: onClick handler solos clicked dataset", () => {
    Chart.mockClear();
    createTrendPanel(points, terms, { clos });
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const legendOnClick = chartCall[1].options.plugins.legend.onClick;
    expect(typeof legendOnClick).toBe("function");
  });

  test("Y-axis uses auto-zoom instead of 0-100", () => {
    Chart.mockClear();
    createTrendPanel(points, terms, { clos });
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const yScale = chartCall[1].options.scales.y;
    // Should NOT be 0/100 since data is 70-95 range
    expect(yScale.min).not.toBe(0);
  });

  test("discontinuityLines plugin renders subtle hairlines without text", () => {
    Chart.mockClear();
    const discs = [
      {
        term_index: 1,
        term_id: "t2",
        type: "clo_change",
        added: [{ clo_id: "c1", label: "CS201/2" }],
        removed: [{ clo_id: "c2", label: "CS101/1" }],
      },
    ];
    createTrendPanel(points, terms, { discontinuities: discs });
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const discPlugin = chartCall[1].plugins.find((p) => p.id === "discontinuityLines");
    expect(discPlugin).toBeDefined();
    // Execute the afterDraw to verify it doesn't call fillText (no text labels)
    const mockCtx = {
      save: jest.fn(),
      restore: jest.fn(),
      beginPath: jest.fn(),
      moveTo: jest.fn(),
      lineTo: jest.fn(),
      stroke: jest.fn(),
      fillText: jest.fn(),
      setLineDash: jest.fn(),
      set strokeStyle(_) {},
      set lineWidth(_) {},
    };
    const mockChart = {
      scales: {
        x: { getPixelForValue: jest.fn().mockReturnValue(50) },
        y: { getPixelForValue: jest.fn().mockReturnValue(50) },
      },
      chartArea: { top: 0, bottom: 100, left: 0, right: 200 },
      ctx: mockCtx,
    };
    discPlugin.afterDraw(mockChart);
    expect(mockCtx.stroke).toHaveBeenCalled();
    // Should NOT render text labels — details are in tooltip afterBody
    expect(mockCtx.fillText).not.toHaveBeenCalled();
  });

  test("tooltip afterBody shows course changes at discontinuity terms", () => {
    Chart.mockClear();
    const discs = [
      {
        term_index: 1,
        term_id: "t2",
        type: "clo_change",
        added: [{ clo_id: "c1", label: "CS201/2" }],
        removed: [{ clo_id: "c2", label: "CS101/1" }],
      },
    ];
    createTrendPanel(points, terms, { discontinuities: discs });
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const afterBody = chartCall[1].options.plugins.tooltip.callbacks.afterBody;

    // At term index 1 (where discontinuity is)
    const result = afterBody([{ dataIndex: 1 }]);
    expect(Array.isArray(result)).toBe(true);
    expect(result.length).toBeGreaterThan(0);
    expect(result.join(" ")).toContain("CS201/2");
    expect(result.join(" ")).toContain("CS101/1");
  });

  test("tooltip afterBody returns empty string at non-discontinuity terms", () => {
    Chart.mockClear();
    const discs = [
      { term_index: 1, added: [], removed: [] },
    ];
    createTrendPanel(points, terms, { discontinuities: discs });
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const afterBody = chartCall[1].options.plugins.tooltip.callbacks.afterBody;

    // At term index 0 (no discontinuity)
    expect(afterBody([{ dataIndex: 0 }])).toBe("");
  });

  test("composition bar is inside panel body div", () => {
    const panel = createTrendPanel(points, terms, { clos });
    const body = panel.querySelector(".plo-trend-panel-body");
    expect(body).not.toBeNull();
    const compBar = body.querySelector(".plo-composition-bar");
    expect(compBar).not.toBeNull();
  });

  test("discontinuityLines plugin is passed to Chart", () => {
    Chart.mockClear();
    const discs = [
      {
        term_index: 1,
        term_id: "t2",
        type: "clo_change",
        added: [{ clo_id: "c1", label: "CS201/2" }],
        removed: [],
      },
    ];
    createTrendPanel(points, terms, { discontinuities: discs });
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const pluginIds = chartCall[1].plugins.map((p) => p.id);
    expect(pluginIds).toContain("discontinuityLines");
    expect(pluginIds).toContain("thresholdLine");
  });

  test("onClick handler sets term filter when data point clicked", () => {
    document.body.innerHTML = `
      <select id="ploTermFilter">
        <option value="">All</option>
        <option value="t1">Fall 2024</option>
        <option value="t2">Spring 2025</option>
      </select>
    `;

    Chart.mockClear();
    createTrendPanel(points, terms, {});
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const onClick = chartCall[1].options.onClick;

    // Simulate click on second data point
    const changeSpy = jest.fn();
    const termFilter = document.getElementById("ploTermFilter");
    termFilter.addEventListener("change", changeSpy);

    onClick({}, [{ index: 1 }]);
    expect(termFilter.value).toBe("t2");
    expect(changeSpy).toHaveBeenCalled();
  });

  test("onClick handler does nothing when no elements clicked", () => {
    Chart.mockClear();
    createTrendPanel(points, terms, {});
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const onClick = chartCall[1].options.onClick;
    // Should not throw
    onClick({}, []);
    onClick({}, null);
  });

  test("tooltip label callback shows PLO data with student counts", () => {
    Chart.mockClear();
    createTrendPanel(points, terms, { clos });
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const labelCb = chartCall[1].options.plugins.tooltip.callbacks.label;

    // PLO dataset (index 0)
    const ploItem = {
      raw: 80,
      dataIndex: 0,
      datasetIndex: 0,
      dataset: { label: "PLO Pass Rate %" },
    };
    // Points have no students_took, so just percentage
    expect(labelCb(ploItem)).toBe("PLO Pass Rate %: 80%");
  });

  test("tooltip label callback shows CLO data", () => {
    Chart.mockClear();
    createTrendPanel(points, terms, { clos });
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const labelCb = chartCall[1].options.plugins.tooltip.callbacks.label;

    // CLO dataset (index 1 = first CLO)
    const cloItem = {
      raw: 75,
      dataIndex: 0,
      datasetIndex: 1,
      dataset: { label: "CS101 CLO 1" },
    };
    expect(labelCb(cloItem)).toBe("CS101 CLO 1: 75%");
  });

  test("tooltip filter removes null/NaN entries", () => {
    Chart.mockClear();
    createTrendPanel(points, terms, {});
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const filterCb = chartCall[1].options.plugins.tooltip.callbacks.filter;

    expect(filterCb({ raw: 80 })).toBe(true);
    expect(filterCb({ raw: NaN })).toBe(false);
    expect(filterCb({ raw: null })).toBe(false);
  });

  test("tooltip label returns null for NaN values", () => {
    Chart.mockClear();
    createTrendPanel(points, terms, { clos });
    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const labelCb = chartCall[1].options.plugins.tooltip.callbacks.label;

    expect(labelCb({ raw: NaN, datasetIndex: 0, dataIndex: 0 })).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// PloTrend controller
// ---------------------------------------------------------------------------
describe("PloTrend controller", () => {
  beforeEach(() => {
    PloTrend.trendData = null;
    PloTrend.selectedTermId = null;
    global.fetch = jest.fn();
    document.body.innerHTML = "";
  });

  afterEach(() => {
    delete global.fetch;
  });

  describe("loadTrend", () => {
    test("does nothing when programId is empty", async () => {
      await PloTrend.loadTrend("");
      expect(global.fetch).not.toHaveBeenCalled();
    });

    test("does nothing when programId is null", async () => {
      await PloTrend.loadTrend(null);
      expect(global.fetch).not.toHaveBeenCalled();
    });

    test("fetches trend data from correct URL", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            success: true,
            terms: [],
            plos: [],
          }),
      });

      await PloTrend.loadTrend("prog-123");
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/programs/prog-123/plo-dashboard/trend",
        expect.objectContaining({
          credentials: "include",
          headers: { Accept: "application/json" },
        })
      );
    });

    test("stores trend data on success", async () => {
      const mockData = {
        success: true,
        terms: [{ term_name: "Fall 2024" }],
        plos: [],
      };
      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      });

      await PloTrend.loadTrend("prog-123");
      expect(PloTrend.trendData).toEqual(mockData);
    });

    test("does not store data on failure response", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: false }),
      });

      await PloTrend.loadTrend("prog-123");
      expect(PloTrend.trendData).toBeNull();
    });

    test("handles fetch error gracefully", async () => {
      const warnSpy = jest.spyOn(console, "warn").mockImplementation();
      global.fetch.mockRejectedValue(new Error("Network error"));

      await PloTrend.loadTrend("prog-123");
      expect(PloTrend.trendData).toBeNull();
      expect(warnSpy).toHaveBeenCalled();
      warnSpy.mockRestore();
    });

    test("does not store data when resp.ok is false", async () => {
      global.fetch.mockResolvedValue({ ok: false });

      await PloTrend.loadTrend("prog-123");
      expect(PloTrend.trendData).toBeNull();
    });

    test("stores selectedTermId when provided", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ success: true, terms: [], plos: [] }),
      });

      await PloTrend.loadTrend("prog-123", "term-42");
      expect(PloTrend.selectedTermId).toBe("term-42");
    });

    test("preserves previous selectedTermId when not provided", async () => {
      PloTrend.selectedTermId = "term-old";
      global.fetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ success: true, terms: [], plos: [] }),
      });

      await PloTrend.loadTrend("prog-123");
      expect(PloTrend.selectedTermId).toBe("term-old");
    });
  });

  describe("injectSparklines", () => {
    test("does nothing when trendData is null", () => {
      PloTrend.trendData = null;
      PloTrend.injectSparklines(); // should not throw
    });

    test("does nothing when fewer than 2 terms", () => {
      PloTrend.trendData = {
        terms: [{ term_name: "Fall 2024" }],
        plos: [],
      };
      PloTrend.injectSparklines(); // should not throw
    });

    test("does nothing when ploTreeContainer is missing", () => {
      PloTrend.trendData = {
        terms: [
          { term_name: "Fall 2024" },
          { term_name: "Spring 2025" },
        ],
        plos: [],
      };
      // No DOM container
      PloTrend.injectSparklines(); // should not throw
    });

    test("injects trend indicator into PLO node", () => {
      document.body.innerHTML = `
        <div id="ploTreeContainer">
          <div data-plo-id="plo-1">
            <div class="plo-tree-header">
              <div class="plo-tree-meta">
                <span class="plo-assessment-badge">90%</span>
              </div>
            </div>
          </div>
        </div>
      `;

      PloTrend.trendData = {
        terms: [
          { term_name: "Fall 2024", is_current: false },
          { term_name: "Spring 2025", is_current: false },
        ],
        plos: [
          {
            id: "plo-1",
            plo_number: 1,
            description: "Test PLO",
            trend: [{ pass_rate: 80 }, { pass_rate: 90 }],
            clos: [],
          },
        ],
      };

      PloTrend.injectSparklines();

      const wrap = document.querySelector(".plo-trend-indicator");
      expect(wrap).not.toBeNull();
      expect(wrap.querySelector(".plo-trend-arrow")).not.toBeNull();
      expect(wrap.querySelector(".plo-trend-delta")).not.toBeNull();
      expect(wrap.querySelector(".plo-trend-delta").textContent).toBe("+10%");
    });

    test("injects trend indicator into CLO node", () => {
      document.body.innerHTML = `
        <div id="ploTreeContainer">
          <div data-plo-id="plo-1">
            <div class="plo-tree-header">
              <div class="plo-tree-meta"></div>
            </div>
            <div data-clo-id="clo-1">
              <div class="plo-tree-header">
                <div class="plo-tree-meta">
                  <span class="plo-assessment-badge">75%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;

      PloTrend.trendData = {
        terms: [
          { term_name: "Fall 2024", is_current: false },
          { term_name: "Spring 2025", is_current: false },
        ],
        plos: [
          {
            id: "plo-1",
            plo_number: 1,
            description: "Test PLO",
            trend: [{ pass_rate: 80 }, { pass_rate: 90 }],
            clos: [
              {
                outcome_id: "clo-1",
                clo_number: 1,
                course_number: "CS101",
                description: "Test CLO",
                trend: [{ pass_rate: 70 }, { pass_rate: 85 }],
              },
            ],
          },
        ],
      };

      PloTrend.injectSparklines();

      const cloNode = document.querySelector('[data-clo-id="clo-1"]');
      const wrap = cloNode.querySelector(".plo-trend-indicator");
      expect(wrap).not.toBeNull();
      expect(wrap.querySelector(".plo-trend-delta").textContent).toBe("+15%");
    });

    test("removes existing trend indicators before re-injecting", () => {
      document.body.innerHTML = `
        <div id="ploTreeContainer">
          <div data-plo-id="plo-1">
            <div class="plo-tree-header">
              <span class="plo-trend-indicator">old</span>
              <div class="plo-tree-meta"></div>
            </div>
            <div class="plo-trend-panel">old panel</div>
          </div>
        </div>
      `;

      PloTrend.trendData = {
        terms: [
          { term_name: "Fall 2024", is_current: false },
          { term_name: "Spring 2025", is_current: false },
        ],
        plos: [
          {
            id: "plo-1",
            plo_number: 1,
            description: "Test PLO",
            trend: [{ pass_rate: 80 }, { pass_rate: 90 }],
            clos: [],
          },
        ],
      };

      PloTrend.injectSparklines();

      // Old trend-indicator with "old" text should be replaced per-node
      const wraps = document.querySelectorAll(".plo-trend-indicator");
      wraps.forEach((w) => {
        expect(w.textContent).not.toBe("old");
      });
      // Old trend panel should also be removed
      const panels = document.querySelectorAll(".plo-trend-panel");
      panels.forEach((p) => {
        expect(p.textContent).not.toBe("old panel");
      });
    });

    test("skips PLO nodes with fewer than 2 trend points", () => {
      document.body.innerHTML = `
        <div id="ploTreeContainer">
          <div data-plo-id="plo-1">
            <div class="plo-tree-header">
              <div class="plo-tree-meta"></div>
            </div>
          </div>
        </div>
      `;

      PloTrend.trendData = {
        terms: [
          { term_name: "Fall 2024", is_current: false },
          { term_name: "Spring 2025", is_current: false },
        ],
        plos: [
          {
            id: "plo-1",
            plo_number: 1,
            description: "Short PLO",
            trend: [{ pass_rate: 80 }], // only 1 data point
            clos: [],
          },
        ],
      };

      PloTrend.injectSparklines();

      const wrap = document.querySelector(".plo-trend-indicator");
      expect(wrap).toBeNull();
    });

    test("injects sparklines into summary bar slots", () => {
      document.body.innerHTML = `
        <div id="ploTreeContainer">
          <div class="plo-summary-bar">
            <div class="plo-summary-row stat-pass">
              <span class="plo-summary-stat">2 satisfactory</span>
              <div class="plo-summary-sparkline-group">
                <span class="plo-summary-sparkline-slot" data-plo-id="plo-1">
                  <span class="plo-summary-sparkline-label">(1)</span>
                </span>
                <span class="plo-summary-sparkline-slot" data-plo-id="plo-2">
                  <span class="plo-summary-sparkline-label">(2)</span>
                </span>
              </div>
            </div>
          </div>
          <div data-plo-id="plo-1">
            <div class="plo-tree-header">
              <div class="plo-tree-meta"></div>
            </div>
          </div>
          <div data-plo-id="plo-2">
            <div class="plo-tree-header">
              <div class="plo-tree-meta"></div>
            </div>
          </div>
        </div>
      `;

      PloTrend.trendData = {
        terms: [
          { term_name: "Fall 2024", is_current: false },
          { term_name: "Spring 2025", is_current: false },
        ],
        plos: [
          {
            id: "plo-1",
            plo_number: 1,
            description: "PLO One",
            trend: [{ pass_rate: 70 }, { pass_rate: 85 }],
            clos: [],
          },
          {
            id: "plo-2",
            plo_number: 2,
            description: "PLO Two",
            trend: [{ pass_rate: 60 }, { pass_rate: 75 }],
            clos: [],
          },
        ],
      };

      PloTrend.injectSparklines();

      // Sparkline canvases should be inserted in the summary bar slots
      const slots = document.querySelectorAll(".plo-summary-sparkline-slot");
      expect(slots.length).toBe(2);
      expect(slots[0].querySelector(".plo-sparkline")).not.toBeNull();
      expect(slots[1].querySelector(".plo-sparkline")).not.toBeNull();
      // Trend badges should be inserted
      const badge0 = slots[0].querySelector(".plo-trend-indicator");
      expect(badge0).not.toBeNull();
      expect(badge0.querySelector(".plo-trend-arrow")).not.toBeNull();
      expect(badge0.querySelector(".plo-trend-delta")).not.toBeNull();
      // Labels preserved
      expect(
        slots[0].querySelector(".plo-summary-sparkline-label").textContent,
      ).toBe("(1)");
    });

    test("skips summary bar slots with insufficient trend data", () => {
      document.body.innerHTML = `
        <div id="ploTreeContainer">
          <div class="plo-summary-bar">
            <div class="plo-summary-row stat-nodata">
              <div class="plo-summary-sparkline-group">
                <span class="plo-summary-sparkline-slot" data-plo-id="plo-3">
                  <span class="plo-summary-sparkline-label">(3)</span>
                </span>
              </div>
            </div>
          </div>
        </div>
      `;

      PloTrend.trendData = {
        terms: [
          { term_name: "Fall 2024", is_current: false },
          { term_name: "Spring 2025", is_current: false },
        ],
        plos: [
          {
            id: "plo-3",
            plo_number: 3,
            description: "No data PLO",
            trend: [{ pass_rate: null }],
            clos: [],
          },
        ],
      };

      PloTrend.injectSparklines();

      const slot = document.querySelector(".plo-summary-sparkline-slot");
      expect(slot.querySelector(".plo-sparkline")).toBeNull();
    });

    test("passes selectedTermIndex based on selectedTermId", () => {
      document.body.innerHTML = `
        <div id="ploTreeContainer">
          <div class="plo-summary-bar">
            <div class="plo-summary-row stat-pass">
              <div class="plo-summary-sparkline-group">
                <span class="plo-summary-sparkline-slot" data-plo-id="plo-1">
                  <span class="plo-summary-sparkline-label">(1)</span>
                </span>
              </div>
            </div>
          </div>
          <div data-plo-id="plo-1">
            <div class="plo-tree-header">
              <div class="plo-tree-meta"></div>
            </div>
          </div>
        </div>
      `;

      PloTrend.selectedTermId = "term-2";
      PloTrend.trendData = {
        terms: [
          { term_id: "term-1", term_name: "Fall 2024", is_current: false },
          { term_id: "term-2", term_name: "Spring 2025", is_current: false },
          { term_id: "term-3", term_name: "Fall 2025", is_current: true },
        ],
        plos: [
          {
            id: "plo-1",
            plo_number: 1,
            description: "PLO One",
            trend: [
              { pass_rate: 70 },
              { pass_rate: 80 },
              { pass_rate: 85 },
            ],
            clos: [],
          },
        ],
      };

      PloTrend.injectSparklines();

      // Sparkline should still be injected
      const slot = document.querySelector(".plo-summary-sparkline-slot");
      expect(slot.querySelector(".plo-sparkline")).not.toBeNull();
      // Tree node indicator also injected
      const indicator = document.querySelector(".plo-trend-indicator");
      expect(indicator).not.toBeNull();
    });

    test("trend badge in tree node reflects data up to selectedTermId only", () => {
      // Trend: 70 → 65 → 80.  Full data = +10% (up).
      // Selected term index 1 (term-2) ⇒ 70 → 65 = -5% (down).
      document.body.innerHTML = `
        <div id="ploTreeContainer">
          <div data-plo-id="plo-1">
            <div class="plo-tree-header">
              <div class="plo-tree-meta">
                <span class="plo-assessment-badge">65%</span>
              </div>
            </div>
          </div>
        </div>
      `;

      PloTrend.selectedTermId = "term-2";
      PloTrend.trendData = {
        terms: [
          { term_id: "term-1", term_name: "Fall 2024", is_current: false },
          { term_id: "term-2", term_name: "Spring 2025", is_current: false },
          { term_id: "term-3", term_name: "Fall 2025", is_current: true },
        ],
        plos: [
          {
            id: "plo-1",
            plo_number: 1,
            description: "PLO One",
            trend: [
              { pass_rate: 70 },
              { pass_rate: 65 },
              { pass_rate: 80 },
            ],
            clos: [],
          },
        ],
      };

      PloTrend.injectSparklines();

      const delta = document.querySelector(".plo-trend-delta");
      expect(delta).not.toBeNull();
      // Should show -5% (70→65), NOT +10% (70→80)
      expect(delta.textContent).toBe("-5%");
      // Arrow should indicate "down"
      const arrow = document.querySelector(".plo-trend-arrow");
      expect(arrow).not.toBeNull();
      expect(arrow.textContent).toBe("↓");
    });

    test("summary bar badge reflects data up to selectedTermId only", () => {
      // Trend: 70 → 65 → 80.  Full data = +10% (up).
      // Selected term index 1 (term-2) ⇒ 70 → 65 = -5% (down).
      document.body.innerHTML = `
        <div id="ploTreeContainer">
          <div class="plo-summary-bar">
            <div class="plo-summary-row stat-pass">
              <div class="plo-summary-sparkline-group">
                <span class="plo-summary-sparkline-slot" data-plo-id="plo-1">
                  <span class="plo-summary-sparkline-label">(1)</span>
                </span>
              </div>
            </div>
          </div>
          <div data-plo-id="plo-1">
            <div class="plo-tree-header">
              <div class="plo-tree-meta">
                <span class="plo-assessment-badge">65%</span>
              </div>
            </div>
          </div>
        </div>
      `;

      PloTrend.selectedTermId = "term-2";
      PloTrend.trendData = {
        terms: [
          { term_id: "term-1", term_name: "Fall 2024", is_current: false },
          { term_id: "term-2", term_name: "Spring 2025", is_current: false },
          { term_id: "term-3", term_name: "Fall 2025", is_current: true },
        ],
        plos: [
          {
            id: "plo-1",
            plo_number: 1,
            description: "PLO One",
            trend: [
              { pass_rate: 70 },
              { pass_rate: 65 },
              { pass_rate: 80 },
            ],
            clos: [],
          },
        ],
      };

      PloTrend.injectSparklines();

      // Check the summary bar badge (not the tree node badge)
      const slot = document.querySelector(".plo-summary-sparkline-slot");
      const badge = slot.querySelector(".plo-trend-indicator");
      expect(badge).not.toBeNull();
      const delta = badge.querySelector(".plo-trend-delta");
      expect(delta).not.toBeNull();
      // Should show -5% (70→65), NOT +10% (70→80)
      expect(delta.textContent).toBe("-5%");
      const arrow = badge.querySelector(".plo-trend-arrow");
      expect(arrow.textContent).toBe("↓");
    });

    test("CLO trend badge reflects data up to selectedTermId only", () => {
      document.body.innerHTML = `
        <div id="ploTreeContainer">
          <div data-plo-id="plo-1">
            <div class="plo-tree-header">
              <div class="plo-tree-meta"></div>
            </div>
            <div data-clo-id="clo-1">
              <div class="plo-tree-header">
                <div class="plo-tree-meta">
                  <span class="plo-assessment-badge">60%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;

      PloTrend.selectedTermId = "term-2";
      PloTrend.trendData = {
        terms: [
          { term_id: "term-1", term_name: "Fall 2024", is_current: false },
          { term_id: "term-2", term_name: "Spring 2025", is_current: false },
          { term_id: "term-3", term_name: "Fall 2025", is_current: true },
        ],
        plos: [
          {
            id: "plo-1",
            plo_number: 1,
            description: "PLO One",
            trend: [
              { pass_rate: 80 },
              { pass_rate: 75 },
              { pass_rate: 90 },
            ],
            clos: [
              {
                outcome_id: "clo-1",
                clo_number: 1,
                course_number: "CS101",
                description: "Test CLO",
                trend: [
                  { pass_rate: 60 },
                  { pass_rate: 50 },
                  { pass_rate: 70 },
                ],
              },
            ],
          },
        ],
      };

      PloTrend.injectSparklines();

      const cloNode = document.querySelector('[data-clo-id="clo-1"]');
      const delta = cloNode.querySelector(".plo-trend-delta");
      expect(delta).not.toBeNull();
      // Should show -10% (60→50), NOT +10% (60→70)
      expect(delta.textContent).toBe("-10%");
    });
  });

  describe("_toggleTrendPanel", () => {
    test("creates panel on first click, removes on second", () => {
      document.body.innerHTML = `
        <div id="testNode">
          <div class="plo-tree-header"></div>
        </div>
      `;
      const nodeEl = document.getElementById("testNode");
      const terms = [
        { term_name: "Fall 2024", is_current: false },
        { term_name: "Spring 2025", is_current: false },
      ];
      const points = [{ pass_rate: 80 }, { pass_rate: 90 }];

      // First call: creates panel
      PloTrend._toggleTrendPanel(nodeEl, points, terms, {});
      expect(nodeEl.querySelector(".plo-trend-panel")).not.toBeNull();

      // Second call: removes panel
      PloTrend._toggleTrendPanel(nodeEl, points, terms, {});
      expect(nodeEl.querySelector(".plo-trend-panel")).toBeNull();
    });
  });
});
