/**
 * Focused unit tests for drill-down/controller behavior in static/plo_trend.js.
 */

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

const Chart = global.Chart;
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

const { createTrendPanel, PloTrend } = require("../../../static/plo_trend");

describe("PloTrend._makePointClickHandler guard clauses", () => {
  let trend;
  let originalPloDetailPanel;

  beforeEach(() => {
    trend = Object.create(PloTrend);
    trend.programId = "PROG-123";
    trend.trendData = null;
    trend._loadTrendGen = 0;

    originalPloDetailPanel = globalThis.PloDetailPanel;
    globalThis.PloDetailPanel = {
      createDetailPanel: jest.fn(() => document.createElement("div")),
      destroyDetailPanel: jest.fn(),
    };

    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            success: true,
            plos: [
              {
                id: "PLO-1",
                plo_number: "1",
                description: "Test PLO",
                clos: [],
              },
            ],
          }),
      }),
    );
  });

  afterEach(() => {
    globalThis.PloDetailPanel = originalPloDetailPanel;
    delete global.fetch;
  });

  test("returns a function", () => {
    const ref = { el: document.createElement("div") };
    const handler = trend._makePointClickHandler("PLO-1", ref);
    expect(typeof handler).toBe("function");
  });

  test("returns false when term is missing", () => {
    const ref = { el: document.createElement("div") };
    const handler = trend._makePointClickHandler("PLO-1", ref);
    expect(handler(null)).toBe(false);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("returns false when term.term_id is missing", () => {
    const ref = { el: document.createElement("div") };
    const handler = trend._makePointClickHandler("PLO-1", ref);
    expect(handler({ name: "Fall 2024" })).toBe(false);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("returns false when PloDetailPanel is missing", () => {
    globalThis.PloDetailPanel = undefined;
    const ref = { el: document.createElement("div") };
    const handler = trend._makePointClickHandler("PLO-1", ref);
    expect(handler({ term_id: "FA2024", name: "Fall 2024" })).toBe(false);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("returns false when container (ref.el) is null", () => {
    const ref = { el: null };
    const handler = trend._makePointClickHandler("PLO-1", ref);
    expect(handler({ term_id: "FA2024", name: "Fall 2024" })).toBe(false);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("returns false when programId is not set", () => {
    trend.programId = null;
    const ref = { el: document.createElement("div") };
    const handler = trend._makePointClickHandler("PLO-1", ref);
    expect(handler({ term_id: "FA2024", name: "Fall 2024" })).toBe(false);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("uses explicit programId override when singleton programId is unset", () => {
    trend.programId = null;
    const ref = { el: document.createElement("div") };
    const handler = trend._makePointClickHandler("PLO-1", ref, "PROG-OVERRIDE");

    expect(handler({ term_id: "FA2024", name: "Fall 2024" })).toBe(true);
    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(global.fetch.mock.calls[0][0]).toContain(
      "/api/programs/PROG-OVERRIDE/plo-dashboard",
    );
  });

  test("returns true and fetches when all dependencies present", async () => {
    const container = document.createElement("div");
    const ref = { el: container };
    const handler = trend._makePointClickHandler("PLO-1", ref);
    expect(handler({ term_id: "FA2024", name: "Fall 2024" })).toBe(true);

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const url = global.fetch.mock.calls[0][0];
    expect(url).toContain("/api/programs/PROG-123/plo-dashboard");
    expect(url).toContain("plo_id=PLO-1");
    expect(url).toContain("term_id=FA2024");

    await new Promise((r) => setTimeout(r, 0));

    expect(globalThis.PloDetailPanel.destroyDetailPanel).toHaveBeenCalledWith(
      container,
    );
    expect(globalThis.PloDetailPanel.createDetailPanel).toHaveBeenCalled();
    expect(container.children.length).toBe(1);
  });

  test("ignores stale detail responses when a newer click wins", async () => {
    const container = document.createElement("div");
    const ref = { el: container };
    const handler = trend._makePointClickHandler("PLO-1", ref);

    let resolveFirst;
    let resolveSecond;
    global.fetch = jest
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveFirst = resolve;
          }),
      )
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveSecond = resolve;
          }),
      );

    expect(handler({ term_id: "FA2024", name: "Fall 2024" })).toBe(true);
    expect(handler({ term_id: "SP2025", name: "Spring 2025" })).toBe(true);

    resolveSecond({
      ok: true,
      json: () =>
        Promise.resolve({
          success: true,
          plos: [{ id: "PLO-1", plo_number: 1, description: "Test PLO" }],
        }),
    });
    await Promise.resolve();
    await Promise.resolve();

    resolveFirst({
      ok: true,
      json: () =>
        Promise.resolve({
          success: true,
          plos: [{ id: "PLO-1", plo_number: 1, description: "Test PLO" }],
        }),
    });
    await Promise.resolve();
    await Promise.resolve();

    expect(globalThis.PloDetailPanel.createDetailPanel).toHaveBeenCalledTimes(
      1,
    );
    expect(globalThis.PloDetailPanel.createDetailPanel).toHaveBeenCalledWith(
      expect.objectContaining({ id: "PLO-1" }),
      "Spring 2025",
    );
    expect(container.children.length).toBe(1);
  });

  test("falls back to a single detail panel when shift-compare target is closed mid-flight", async () => {
    const container = document.createElement("div");
    const stalePanel = document.createElement("div");
    stalePanel.className = "plo-detail-panel";
    container.appendChild(stalePanel);
    document.body.appendChild(container);

    const replacementPanel = document.createElement("div");
    replacementPanel.className = "plo-detail-panel";
    globalThis.PloDetailPanel.createDetailPanel.mockReturnValueOnce(
      replacementPanel,
    );

    const ref = { el: container };
    const handler = trend._makePointClickHandler("PLO-1", ref);

    let resolveFetch;
    global.fetch = jest.fn(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve;
        }),
    );

    expect(
      handler(
        { term_id: "SP2025", term_name: "Spring 2025" },
        { native: { shiftKey: true } },
      ),
    ).toBe(true);

    stalePanel.remove();
    expect(container.querySelector(".plo-detail-panel")).toBeNull();

    resolveFetch({
      ok: true,
      json: () =>
        Promise.resolve({
          success: true,
          plos: [{ id: "PLO-1", plo_number: 1, description: "Test PLO" }],
        }),
    });
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(globalThis.PloDetailPanel.createDetailPanel).toHaveBeenCalledTimes(
      1,
    );
    expect(container.querySelectorAll(".plo-detail-panel")).toHaveLength(1);
    expect(container.querySelector(".plo-detail-compare")).toBeNull();
  });
});

describe("PloTrend._restoreFromHash", () => {
  let originalToggleTrendPanel;

  beforeEach(() => {
    originalToggleTrendPanel = PloTrend._toggleTrendPanel;
    PloTrend._toggleTrendPanel = jest.fn();
    PloTrend._hashRestored = false;
    PloTrend.programId = "prog-2";
    PloTrend.selectedTermId = "t2";
    document.body.innerHTML = `
      <div id="ploTreeContainer">
        <li id="target-plo-node" data-plo-id="p'2]">
          <div class="plo-tree-header"></div>
        </li>
      </div>
    `;
    window.location.hash = "#plo=2";
  });

  afterEach(() => {
    PloTrend._toggleTrendPanel = originalToggleTrendPanel;
    PloTrend._hashRestored = false;
    PloTrend.selectedTermId = null;
    window.location.hash = "";
  });

  test("keeps hash restoration pending until the matching PLO is present", () => {
    PloTrend.trendData = {
      terms: [{ term_id: "t1", term_name: "Fall 2024" }],
      plos: [
        {
          id: "p1",
          plo_number: 1,
          description: "Other PLO",
          trend: [{ pass_rate: 70 }, { pass_rate: 80 }],
        },
      ],
    };

    PloTrend._restoreFromHash();

    expect(PloTrend._hashRestored).toBe(false);
    expect(PloTrend._toggleTrendPanel).not.toHaveBeenCalled();

    PloTrend.trendData = {
      terms: [{ term_id: "t2", term_name: "Spring 2025" }],
      plos: [
        {
          id: "p'2]",
          plo_number: 2,
          description: "Matched PLO",
          trend: [{ pass_rate: 75 }, { pass_rate: 82 }],
          clos: [],
          discontinuities: [],
        },
      ],
    };

    PloTrend._restoreFromHash();

    expect(PloTrend._hashRestored).toBe(true);
    expect(PloTrend._toggleTrendPanel).toHaveBeenCalledWith(
      document.getElementById("target-plo-node"),
      [{ pass_rate: 75 }, { pass_rate: 82 }],
      [{ term_id: "t2", term_name: "Spring 2025" }],
      expect.objectContaining({
        programId: "prog-2",
        selectedTermIndex: 0,
      }),
    );
  });
});

describe("PloTrend._updateHash", () => {
  let originalReplaceState;

  beforeEach(() => {
    originalReplaceState = history.replaceState;
    history.replaceState = jest.fn();
  });

  afterEach(() => {
    history.replaceState = originalReplaceState;
    document.body.innerHTML = "";
  });

  test("falls back to DOM plo number when trendData does not include the clicked program's PLO", () => {
    PloTrend.trendData = {
      plos: [{ id: "last-program-plo", plo_number: 9 }],
    };
    document.body.innerHTML = `
      <div id="ploTreeContainer">
        <li data-plo-id="other'program]plo" data-plo-number="3"></li>
      </div>
    `;

    PloTrend._updateHash("other'program]plo");

    expect(history.replaceState).toHaveBeenCalledWith(null, "", "#plo=3");
  });
});

describe("PloTrend._injectSummarySparklines", () => {
  let originalToggleSummaryTrendPanel;

  beforeEach(() => {
    originalToggleSummaryTrendPanel = PloTrend._toggleSummaryTrendPanel;
    PloTrend._toggleSummaryTrendPanel = jest.fn();
    Chart.mockClear();
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
      </div>
    `;
  });

  afterEach(() => {
    PloTrend._toggleSummaryTrendPanel = originalToggleSummaryTrendPanel;
    document.body.innerHTML = "";
  });

  test("forwards selectedTermIndex when opening a summary-bar trend panel", () => {
    const container = document.getElementById("ploTreeContainer");
    const terms = [
      { term_id: "t1", term_name: "Fall 2024" },
      { term_id: "t2", term_name: "Spring 2025" },
      { term_id: "t3", term_name: "Fall 2025" },
    ];
    const plo = {
      id: "plo-1",
      plo_number: 1,
      description: "PLO One",
      trend: [{ pass_rate: 70 }, { pass_rate: 80 }, { pass_rate: 85 }],
      clos: [],
    };

    PloTrend._injectSummarySparklines(container, [plo], terms, 1, "prog-1");

    const canvas = document.querySelector(".plo-summary-sparkline-slot canvas");
    canvas.click();

    expect(PloTrend._toggleSummaryTrendPanel).toHaveBeenCalledWith(
      document.querySelector(".plo-summary-sparkline-slot"),
      plo,
      terms,
      "prog-1",
      1,
    );
  });
});

describe("PloTrend.injectSparklines", () => {
  afterEach(() => {
    document.body.innerHTML = "";
    PloTrend.selectedTermId = null;
    PloTrend.trendData = null;
  });

  test("matches PLO and CLO nodes by dataset value even when ids contain selector-breaking characters", () => {
    document.body.innerHTML = `
      <div id="ploTreeContainer">
        <li data-plo-id="plo'1]">
          <div class="plo-tree-header">
            <div class="plo-tree-meta"></div>
          </div>
          <div data-clo-id="clo'1]">
            <div class="plo-tree-header">
              <div class="plo-tree-meta"></div>
            </div>
          </div>
        </li>
      </div>
    `;

    PloTrend.trendData = {
      terms: [
        { term_id: "t1", term_name: "Fall 2024" },
        { term_id: "t2", term_name: "Spring 2025" },
      ],
      plos: [
        {
          id: "plo'1]",
          plo_number: 1,
          description: "Escaped PLO",
          trend: [{ pass_rate: 70 }, { pass_rate: 82 }],
          clos: [
            {
              outcome_id: "clo'1]",
              clo_number: 1,
              course_number: "CS101",
              description: "Escaped CLO",
              trend: [{ pass_rate: 68 }, { pass_rate: 80 }],
            },
          ],
        },
      ],
    };

    PloTrend.injectSparklines();

    expect(document.querySelectorAll(".plo-trend-indicator")).toHaveLength(2);
  });
});

describe("onClick → onPointClick integration", () => {
  let trend;
  let originalPloDetailPanel;

  const terms = [
    { term_id: "FA2024", name: "Fall 2024" },
    { term_id: "SP2025", name: "Spring 2025" },
  ];
  const points = [{ pass_rate: 80 }, { pass_rate: 85 }];

  beforeEach(() => {
    trend = Object.create(PloTrend);
    trend.programId = "PROG-123";

    originalPloDetailPanel = globalThis.PloDetailPanel;
    globalThis.PloDetailPanel = {
      createDetailPanel: jest.fn(() => document.createElement("div")),
      destroyDetailPanel: jest.fn(),
    };

    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            success: true,
            plos: [{ id: "PLO-1", clos: [] }],
          }),
      }),
    );
  });

  afterEach(() => {
    globalThis.PloDetailPanel = originalPloDetailPanel;
    delete global.fetch;
  });

  test("clicking a data point when all deps present triggers fetch", () => {
    const ref = { el: null };
    const onPointClick = trend._makePointClickHandler("PLO-1", ref);

    Chart.mockClear();
    const panel = createTrendPanel(points, terms, { onPointClick });
    ref.el = panel;

    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const onClick = chartCall[1].options.onClick;

    onClick({}, [{ index: 1 }]);

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(global.fetch.mock.calls[0][0]).toContain("term_id=SP2025");
  });

  test("falls back to term filter when PloDetailPanel missing", () => {
    globalThis.PloDetailPanel = undefined;
    const ref = { el: null };
    const onPointClick = trend._makePointClickHandler("PLO-1", ref);

    const termFilter = document.createElement("select");
    termFilter.id = "ploTermFilter";
    terms.forEach((t) => {
      const opt = document.createElement("option");
      opt.value = t.term_id;
      opt.textContent = t.name;
      termFilter.appendChild(opt);
    });
    document.body.appendChild(termFilter);
    const changeSpy = jest.fn();
    termFilter.addEventListener("change", changeSpy);

    Chart.mockClear();
    const panel = createTrendPanel(points, terms, { onPointClick });
    ref.el = panel;

    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const onClick = chartCall[1].options.onClick;

    onClick({}, [{ index: 0 }]);

    expect(global.fetch).not.toHaveBeenCalled();
    expect(termFilter.value).toBe("FA2024");
    expect(changeSpy).toHaveBeenCalledTimes(1);

    document.body.removeChild(termFilter);
  });

  test("falls back to term filter when programId missing", () => {
    trend.programId = null;
    const ref = { el: null };
    const onPointClick = trend._makePointClickHandler("PLO-1", ref);

    const termFilter = document.createElement("select");
    termFilter.id = "ploTermFilter";
    terms.forEach((t) => {
      const opt = document.createElement("option");
      opt.value = t.term_id;
      opt.textContent = t.name;
      termFilter.appendChild(opt);
    });
    document.body.appendChild(termFilter);
    const changeSpy = jest.fn();
    termFilter.addEventListener("change", changeSpy);

    Chart.mockClear();
    const panel = createTrendPanel(points, terms, { onPointClick });
    ref.el = panel;

    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const onClick = chartCall[1].options.onClick;

    onClick({}, [{ index: 1 }]);

    expect(global.fetch).not.toHaveBeenCalled();
    expect(termFilter.value).toBe("SP2025");
    expect(changeSpy).toHaveBeenCalledTimes(1);

    document.body.removeChild(termFilter);
  });

  test("falls back to term filter when container null", () => {
    const ref = { el: null };
    const onPointClick = trend._makePointClickHandler("PLO-1", ref);

    const termFilter = document.createElement("select");
    termFilter.id = "ploTermFilter";
    terms.forEach((t) => {
      const opt = document.createElement("option");
      opt.value = t.term_id;
      opt.textContent = t.name;
      termFilter.appendChild(opt);
    });
    document.body.appendChild(termFilter);
    const changeSpy = jest.fn();
    termFilter.addEventListener("change", changeSpy);

    Chart.mockClear();
    createTrendPanel(points, terms, { onPointClick });

    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const onClick = chartCall[1].options.onClick;

    onClick({}, [{ index: 0 }]);

    expect(global.fetch).not.toHaveBeenCalled();
    expect(termFilter.value).toBe("FA2024");
    expect(changeSpy).toHaveBeenCalledTimes(1);

    document.body.removeChild(termFilter);
  });

  test("does NOT change term filter when onPointClick succeeds", () => {
    const ref = { el: null };
    const onPointClick = trend._makePointClickHandler("PLO-1", ref);

    const termFilter = document.createElement("select");
    termFilter.id = "ploTermFilter";
    terms.forEach((t) => {
      const opt = document.createElement("option");
      opt.value = t.term_id;
      opt.textContent = t.name;
      termFilter.appendChild(opt);
    });
    document.body.appendChild(termFilter);
    const changeSpy = jest.fn();
    termFilter.addEventListener("change", changeSpy);

    Chart.mockClear();
    const panel = createTrendPanel(points, terms, { onPointClick });
    ref.el = panel;

    const chartCall = Chart.mock.calls[Chart.mock.calls.length - 1];
    const onClick = chartCall[1].options.onClick;

    onClick({}, [{ index: 0 }]);

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(changeSpy).not.toHaveBeenCalled();

    document.body.removeChild(termFilter);
  });
});
