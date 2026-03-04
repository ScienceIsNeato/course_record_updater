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
  createSparkline,
  createTrendPanel,
  createCompositionBar,
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

  test("returns 'up' when last > first by >= 2", () => {
    const points = [{ pass_rate: 60 }, { pass_rate: 70 }, { pass_rate: 80 }];
    expect(getTrendDirection(points)).toBe("up");
  });

  test("returns 'down' when last < first by >= 2", () => {
    const points = [{ pass_rate: 90 }, { pass_rate: 70 }, { pass_rate: 60 }];
    expect(getTrendDirection(points)).toBe("down");
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
    const points = [{ pass_rate: 50 }, null, { pass_rate: 80 }];
    expect(getTrendDirection(points)).toBe("up");
  });

  test("skips entries with null pass_rate", () => {
    const points = [
      { pass_rate: 90 },
      { pass_rate: null },
      { pass_rate: 70 },
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

  test("down → ↓ with trend-down class", () => {
    expect(getTrendArrow("down")).toEqual({
      arrow: "↓",
      cssClass: "trend-down",
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
    expect(canvas.width).toBe(90);
    expect(canvas.height).toBe(28);
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

  test("contains a close button", () => {
    const panel = createTrendPanel(points, terms);
    const closeBtn = panel.querySelector(".plo-trend-panel-close");
    expect(closeBtn).not.toBeNull();
    expect(closeBtn.tagName).toBe("BUTTON");
    expect(closeBtn.title).toBe("Close trend chart");
  });

  test("close button removes the panel from DOM", () => {
    const parent = document.createElement("div");
    const panel = createTrendPanel(points, terms);
    parent.appendChild(panel);
    expect(parent.children.length).toBe(1);

    const closeBtn = panel.querySelector(".plo-trend-panel-close");
    closeBtn.click();
    expect(parent.children.length).toBe(0);
  });

  test("contains a canvas element", () => {
    const panel = createTrendPanel(points, terms);
    const canvas = panel.querySelector("canvas");
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

  test("renders CLO composition bar when CLOs provided", () => {
    const panel = createTrendPanel(points, terms, { clos });
    const compBar = panel.querySelector(".plo-composition-bar");
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
    expect(labelCb(ploItem)).toBe("PLO: 80%");
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

    test("injects sparkline into PLO node", () => {
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

      const wrap = document.querySelector(".plo-sparkline-wrap");
      expect(wrap).not.toBeNull();
      expect(wrap.querySelector(".plo-sparkline")).not.toBeNull();
    });

    test("injects sparkline into CLO node", () => {
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
      const wrap = cloNode.querySelector(".plo-sparkline-wrap");
      expect(wrap).not.toBeNull();
    });

    test("removes existing sparklines before re-injecting", () => {
      document.body.innerHTML = `
        <div id="ploTreeContainer">
          <span class="plo-sparkline-wrap">old</span>
          <div class="plo-trend-panel">old panel</div>
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
            description: "Test PLO",
            trend: [{ pass_rate: 80 }, { pass_rate: 90 }],
            clos: [],
          },
        ],
      };

      PloTrend.injectSparklines();

      // Old sparkline-wrap with "old" text should be gone
      const wraps = document.querySelectorAll(".plo-sparkline-wrap");
      wraps.forEach((w) => {
        expect(w.textContent).not.toBe("old");
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

      const wrap = document.querySelector(".plo-sparkline-wrap");
      expect(wrap).toBeNull();
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
