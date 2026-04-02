/**
 * Characterization tests for static/plo_trend_panel.js.
 *
 * Locks down the existing DOM contract before we extend the onClick
 * handler with drill-down detail panel support.
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

const _chartInstances = new Map();
const _origImpl = global.Chart.getMockImplementation();
global.Chart.mockImplementation((canvas, ...args) => {
  const inst = _origImpl(canvas, ...args);
  _chartInstances.set(canvas, inst);
  return inst;
});
global.Chart.getChart = jest.fn(
  (canvas) => _chartInstances.get(canvas) || null,
);
global.requestAnimationFrame = (cb) => cb();

const {
  createTrendPanel,
  buildTrendOptions,
} = require("../../../static/plo_trend_panel");
const { setBody } = require("../helpers/dom");
const {
  MOCK_TERMS,
  MOCK_TREND_POINTS,
  MOCK_OPTS,
  MOCK_OPTS_NO_CLOS,
  makeMockDeps,
} = require("./helpers/plo_trend_panel_fixtures");

// ---------------------------------------------------------------------------
// createTrendPanel — DOM structure
// ---------------------------------------------------------------------------
describe("createTrendPanel — DOM structure", () => {
  test("returns a div.plo-trend-panel", () => {
    const deps = makeMockDeps();
    const panel = createTrendPanel(
      MOCK_TREND_POINTS,
      MOCK_TERMS,
      MOCK_OPTS,
      deps,
    );
    expect(panel.tagName).toBe("DIV");
    expect(panel.classList.contains("plo-trend-panel")).toBe(true);
  });

  test("panel contains a canvas element", () => {
    const deps = makeMockDeps();
    const panel = createTrendPanel(
      MOCK_TREND_POINTS,
      MOCK_TERMS,
      MOCK_OPTS,
      deps,
    );
    const canvas = panel.querySelector("canvas");
    expect(canvas).not.toBeNull();
  });

  test("panel has a toggle button", () => {
    const deps = makeMockDeps();
    const panel = createTrendPanel(
      MOCK_TREND_POINTS,
      MOCK_TERMS,
      MOCK_OPTS,
      deps,
    );
    const btn = panel.querySelector("button.plo-trend-panel-toggle");
    expect(btn).not.toBeNull();
    expect(btn.getAttribute("aria-expanded")).toBe("true");
  });

  test("toggle button hides/shows the panel body", () => {
    const deps = makeMockDeps();
    const panel = createTrendPanel(
      MOCK_TREND_POINTS,
      MOCK_TERMS,
      MOCK_OPTS,
      deps,
    );
    const btn = panel.querySelector("button.plo-trend-panel-toggle");
    const body = panel.querySelector(".plo-trend-panel-body");

    // Initially visible
    expect(body.style.display).not.toBe("none");

    // Click to hide
    btn.click();
    expect(body.style.display).toBe("none");
    expect(btn.getAttribute("aria-expanded")).toBe("false");
    expect(panel.classList.contains("plo-trend-panel--collapsed")).toBe(true);

    // Click to show
    btn.click();
    expect(body.style.display).toBe("");
    expect(btn.getAttribute("aria-expanded")).toBe("true");
    expect(panel.classList.contains("plo-trend-panel--collapsed")).toBe(false);
  });

  test("with CLOs, composition bar is appended", () => {
    const deps = makeMockDeps();
    createTrendPanel(MOCK_TREND_POINTS, MOCK_TERMS, MOCK_OPTS, deps);
    expect(deps.createCompositionBar).toHaveBeenCalledWith(
      MOCK_OPTS.clos,
      MOCK_TERMS,
    );
  });

  test("without CLOs, composition bar is NOT created", () => {
    const deps = makeMockDeps();
    createTrendPanel(MOCK_TREND_POINTS, MOCK_TERMS, MOCK_OPTS_NO_CLOS, deps);
    expect(deps.createCompositionBar).not.toHaveBeenCalled();
  });

  test("Chart constructor is called with correct type and labels", () => {
    global.Chart.mockClear();
    const deps = makeMockDeps();
    createTrendPanel(MOCK_TREND_POINTS, MOCK_TERMS, MOCK_OPTS, deps);

    expect(global.Chart).toHaveBeenCalledTimes(1);
    const callArgs = global.Chart.mock.calls[0];
    expect(callArgs[1].type).toBe("line");
    expect(callArgs[1].data.labels).toEqual([
      "Fall 2024",
      "Spring 2025",
      "Fall 2025",
    ]);
  });
});

// ---------------------------------------------------------------------------
// createTrendPanel — empty / no data
// ---------------------------------------------------------------------------
describe("createTrendPanel — no data", () => {
  test("null trendPoints renders no-data message", () => {
    const deps = makeMockDeps();
    const panel = createTrendPanel(null, MOCK_TERMS, MOCK_OPTS, deps);
    const msg = panel.querySelector("p.text-muted");
    expect(msg).not.toBeNull();
    expect(msg.textContent).toBe("No trend data available.");
  });

  test("empty trendPoints array renders no-data message", () => {
    const deps = makeMockDeps();
    const panel = createTrendPanel([], MOCK_TERMS, MOCK_OPTS, deps);
    const msg = panel.querySelector("p.text-muted");
    expect(msg).not.toBeNull();
    expect(msg.textContent).toBe("No trend data available.");
  });

  test("no-data panel does NOT create a Chart", () => {
    global.Chart.mockClear();
    const deps = makeMockDeps();
    createTrendPanel(null, MOCK_TERMS, MOCK_OPTS, deps);
    expect(global.Chart).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// buildTrendOptions — onClick
// ---------------------------------------------------------------------------
describe("buildTrendOptions — onClick handler", () => {
  beforeEach(() => {
    setBody(`<select id="ploTermFilter">
      <option value="">All Terms</option>
      <option value="t-fa24">Fall 2024</option>
      <option value="t-sp25">Spring 2025</option>
      <option value="t-fa25">Fall 2025</option>
    </select>`);
  });

  test("onClick with elements sets term filter and dispatches change", () => {
    const deps = makeMockDeps();
    const model = {
      clos: [],
      currentTermIndices: new Set(),
      data: [72, 78, 85],
      discontinuities: [],
      failRadii: [4, 4, 4],
      labels: ["Fall 2024", "Spring 2025", "Fall 2025"],
      lineColor: "#0d6efd",
      pointBorders: ["#0d6efd", "#0d6efd", "#0d6efd"],
      pointColors: ["#0d6efd", "#0d6efd", "#0d6efd"],
      threshold: 70,
      title: "Test",
    };
    const datasets = [];

    const opts = buildTrendOptions(
      MOCK_TERMS,
      MOCK_TREND_POINTS,
      model,
      datasets,
      deps,
    );

    const changeSpy = jest.fn();
    const termFilter = document.getElementById("ploTermFilter");
    termFilter.addEventListener("change", changeSpy);

    // Simulate Chart.js onClick with element at index 1 (Spring 2025)
    opts.onClick({}, [{ index: 1 }]);

    expect(termFilter.value).toBe("t-sp25");
    expect(changeSpy).toHaveBeenCalledTimes(1);
  });

  test("onClick with empty elements array does nothing", () => {
    const deps = makeMockDeps();
    const model = {
      clos: [],
      currentTermIndices: new Set(),
      data: [72],
      discontinuities: [],
      failRadii: [4],
      labels: ["Fall 2024"],
      lineColor: "#0d6efd",
      pointBorders: ["#0d6efd"],
      pointColors: ["#0d6efd"],
      threshold: 70,
      title: "Test",
    };
    const datasets = [];

    const opts = buildTrendOptions(
      MOCK_TERMS,
      MOCK_TREND_POINTS,
      model,
      datasets,
      deps,
    );
    const termFilter = document.getElementById("ploTermFilter");
    const origValue = termFilter.value;

    opts.onClick({}, []);
    expect(termFilter.value).toBe(origValue);
  });

  test("onClick with no elements does nothing", () => {
    const deps = makeMockDeps();
    const model = {
      clos: [],
      currentTermIndices: new Set(),
      data: [72],
      discontinuities: [],
      failRadii: [4],
      labels: ["Fall 2024"],
      lineColor: "#0d6efd",
      pointBorders: ["#0d6efd"],
      pointColors: ["#0d6efd"],
      threshold: 70,
      title: "Test",
    };
    const datasets = [];

    const opts = buildTrendOptions(
      MOCK_TERMS,
      MOCK_TREND_POINTS,
      model,
      datasets,
      deps,
    );
    // null elements — should not throw
    expect(() => opts.onClick({}, null)).not.toThrow();
  });

  test("onClick invokes onPointClick callback with term when provided", () => {
    const deps = makeMockDeps();
    const onPointClick = jest.fn();
    const model = {
      clos: [],
      currentTermIndices: new Set(),
      data: [72, 78, 85],
      discontinuities: [],
      failRadii: [4, 4, 4],
      labels: ["Fall 2024", "Spring 2025", "Fall 2025"],
      lineColor: "#0d6efd",
      pointBorders: ["#0d6efd", "#0d6efd", "#0d6efd"],
      pointColors: ["#0d6efd", "#0d6efd", "#0d6efd"],
      threshold: 70,
      title: "Test",
    };
    const datasets = [];
    const optsWithCb = buildTrendOptions(
      MOCK_TERMS,
      MOCK_TREND_POINTS,
      model,
      datasets,
      deps,
      { onPointClick },
    );

    optsWithCb.onClick({}, [{ index: 1 }]);
    expect(onPointClick).toHaveBeenCalledTimes(1);
    expect(onPointClick).toHaveBeenCalledWith(MOCK_TERMS[1]);
  });

  test("onClick with onPointClick does NOT change term filter", () => {
    const deps = makeMockDeps();
    const onPointClick = jest.fn().mockReturnValue(true);
    const model = {
      clos: [],
      currentTermIndices: new Set(),
      data: [72, 78, 85],
      discontinuities: [],
      failRadii: [4, 4, 4],
      labels: ["Fall 2024", "Spring 2025", "Fall 2025"],
      lineColor: "#0d6efd",
      pointBorders: ["#0d6efd", "#0d6efd", "#0d6efd"],
      pointColors: ["#0d6efd", "#0d6efd", "#0d6efd"],
      threshold: 70,
      title: "Test",
    };
    const datasets = [];
    const optsWithCb = buildTrendOptions(
      MOCK_TERMS,
      MOCK_TREND_POINTS,
      model,
      datasets,
      deps,
      { onPointClick },
    );

    const termFilter = document.getElementById("ploTermFilter");
    const changeSpy = jest.fn();
    termFilter.addEventListener("change", changeSpy);
    const origValue = termFilter.value;

    optsWithCb.onClick({}, [{ index: 1 }]);
    // Term filter must NOT be touched — re-render would destroy the panel
    expect(termFilter.value).toBe(origValue);
    expect(changeSpy).not.toHaveBeenCalled();
  });

  test("onClick without onPointClick callback does not throw", () => {
    const deps = makeMockDeps();
    const model = {
      clos: [],
      currentTermIndices: new Set(),
      data: [72],
      discontinuities: [],
      failRadii: [4],
      labels: ["Fall 2024"],
      lineColor: "#0d6efd",
      pointBorders: ["#0d6efd"],
      pointColors: ["#0d6efd"],
      threshold: 70,
      title: "Test",
    };
    const datasets = [];
    const optsNoCb = buildTrendOptions(
      MOCK_TERMS,
      MOCK_TREND_POINTS,
      model,
      datasets,
      deps,
      {},
    );

    expect(() => optsNoCb.onClick({}, [{ index: 0 }])).not.toThrow();
  });

  test("onHover sets pointer cursor when hovering over elements", () => {
    const deps = makeMockDeps();
    const model = {
      clos: [],
      currentTermIndices: new Set(),
      data: [72],
      discontinuities: [],
      failRadii: [4],
      labels: ["Fall 2024"],
      lineColor: "#0d6efd",
      pointBorders: ["#0d6efd"],
      pointColors: ["#0d6efd"],
      threshold: 70,
      title: "Test",
    };
    const datasets = [];
    const opts = buildTrendOptions(
      MOCK_TERMS,
      MOCK_TREND_POINTS,
      model,
      datasets,
      deps,
    );

    const canvas = document.createElement("canvas");
    opts.onHover({ native: { target: canvas } }, [{ index: 0 }]);
    expect(canvas.style.cursor).toBe("pointer");

    opts.onHover({ native: { target: canvas } }, []);
    expect(canvas.style.cursor).toBe("");
  });
});

// ---------------------------------------------------------------------------
// Integration: createTrendPanel → Chart → onClick → onPointClick
// ---------------------------------------------------------------------------
describe("createTrendPanel integration — onPointClick threading", () => {
  beforeEach(() => {
    global.Chart.mockClear();
    setBody(`<select id="ploTermFilter">
      <option value="">All Terms</option>
      <option value="t-fa24">Fall 2024</option>
      <option value="t-sp25">Spring 2025</option>
      <option value="t-fa25">Fall 2025</option>
    </select>`);
  });

  test("Chart receives onClick when onPointClick is in opts", () => {
    const deps = makeMockDeps();
    const onPointClick = jest.fn();
    const opts = {
      ...MOCK_OPTS,
      onPointClick,
    };

    createTrendPanel(MOCK_TREND_POINTS, MOCK_TERMS, opts, deps);

    // Chart constructor should have been called
    expect(global.Chart).toHaveBeenCalledTimes(1);
    const chartConfig = global.Chart.mock.calls[0][1];
    expect(chartConfig.options.onClick).toBeDefined();

    // Simulate clicking on the second data point (Spring 2025)
    chartConfig.options.onClick({}, [{ index: 1 }]);
    expect(onPointClick).toHaveBeenCalledTimes(1);
    expect(onPointClick).toHaveBeenCalledWith(MOCK_TERMS[1]);
  });

  test("Chart onClick does NOT call onPointClick when opts lacks it", () => {
    const deps = makeMockDeps();
    // No onPointClick in opts
    createTrendPanel(MOCK_TREND_POINTS, MOCK_TERMS, MOCK_OPTS, deps);

    expect(global.Chart).toHaveBeenCalledTimes(1);
    const chartConfig = global.Chart.mock.calls[0][1];

    // Simulate clicking — should change term filter instead
    const termFilter = document.getElementById("ploTermFilter");
    const changeSpy = jest.fn();
    termFilter.addEventListener("change", changeSpy);

    chartConfig.options.onClick({}, [{ index: 1 }]);
    expect(termFilter.value).toBe("t-sp25");
    expect(changeSpy).toHaveBeenCalledTimes(1);
  });

  test("Chart onClick with onPointClick does NOT change term filter", () => {
    const deps = makeMockDeps();
    const onPointClick = jest.fn().mockReturnValue(true);
    const opts = {
      ...MOCK_OPTS,
      onPointClick,
    };

    createTrendPanel(MOCK_TREND_POINTS, MOCK_TERMS, opts, deps);

    const chartConfig = global.Chart.mock.calls[0][1];
    const termFilter = document.getElementById("ploTermFilter");
    const origValue = termFilter.value;
    const changeSpy = jest.fn();
    termFilter.addEventListener("change", changeSpy);

    chartConfig.options.onClick({}, [{ index: 1 }]);
    expect(termFilter.value).toBe(origValue);
    expect(changeSpy).not.toHaveBeenCalled();
    expect(onPointClick).toHaveBeenCalledWith(MOCK_TERMS[1]);
  });

  test("Chart options include onHover cursor handler", () => {
    const deps = makeMockDeps();
    createTrendPanel(MOCK_TREND_POINTS, MOCK_TERMS, MOCK_OPTS, deps);

    const chartConfig = global.Chart.mock.calls[0][1];
    expect(chartConfig.options.onHover).toBeDefined();

    const canvas = document.createElement("canvas");
    chartConfig.options.onHover({ native: { target: canvas } }, [{ index: 0 }]);
    expect(canvas.style.cursor).toBe("pointer");
  });
});
