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
