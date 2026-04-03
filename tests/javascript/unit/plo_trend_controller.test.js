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

const { PloTrend } = require("../../../static/plo_trend");

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
        }),
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
        json: () => Promise.resolve({ success: true, terms: [], plos: [] }),
      });

      await PloTrend.loadTrend("prog-123", "term-42");
      expect(PloTrend.selectedTermId).toBe("term-42");
    });

    test("preserves previous selectedTermId when not provided", async () => {
      PloTrend.selectedTermId = "term-old";
      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true, terms: [], plos: [] }),
      });

      await PloTrend.loadTrend("prog-123");
      expect(PloTrend.selectedTermId).toBe("term-old");
    });
  });

  describe("injectSparklines", () => {
    test("does nothing when trendData is null", () => {
      PloTrend.trendData = null;
      expect(() => PloTrend.injectSparklines()).not.toThrow();
      expect(document.querySelectorAll(".plo-trend-indicator")).toHaveLength(0);
    });

    test("does nothing when fewer than 2 terms", () => {
      PloTrend.trendData = {
        terms: [{ term_name: "Fall 2024" }],
        plos: [],
      };
      expect(() => PloTrend.injectSparklines()).not.toThrow();
      expect(document.querySelectorAll(".plo-trend-indicator")).toHaveLength(0);
    });

    test("does nothing when ploTreeContainer is missing", () => {
      PloTrend.trendData = {
        terms: [{ term_name: "Fall 2024" }, { term_name: "Spring 2025" }],
        plos: [],
      };
      expect(document.getElementById("ploTreeContainer")).toBeNull();
      expect(() => PloTrend.injectSparklines()).not.toThrow();
      expect(document.querySelectorAll(".plo-trend-indicator")).toHaveLength(0);
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

      const wraps = document.querySelectorAll(".plo-trend-indicator");
      wraps.forEach((w) => {
        expect(w.textContent).not.toBe("old");
      });
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
            trend: [{ pass_rate: 80 }],
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

      const slots = document.querySelectorAll(".plo-summary-sparkline-slot");
      expect(slots.length).toBe(2);
      expect(slots[0].querySelector(".plo-sparkline")).not.toBeNull();
      expect(slots[1].querySelector(".plo-sparkline")).not.toBeNull();
      const badge0 = slots[0].querySelector(".plo-trend-indicator");
      expect(badge0).not.toBeNull();
      expect(badge0.querySelector(".plo-trend-arrow")).not.toBeNull();
      expect(badge0.querySelector(".plo-trend-delta")).not.toBeNull();
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
            trend: [{ pass_rate: 70 }, { pass_rate: 80 }, { pass_rate: 85 }],
            clos: [],
          },
        ],
      };

      PloTrend.injectSparklines();

      const slot = document.querySelector(".plo-summary-sparkline-slot");
      expect(slot.querySelector(".plo-sparkline")).not.toBeNull();
      const indicator = document.querySelector(".plo-trend-indicator");
      expect(indicator).not.toBeNull();
    });

    test("trend badge in tree node reflects data up to selectedTermId only", () => {
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
            trend: [{ pass_rate: 70 }, { pass_rate: 65 }, { pass_rate: 80 }],
            clos: [],
          },
        ],
      };

      PloTrend.injectSparklines();

      const delta = document.querySelector(".plo-trend-delta");
      expect(delta).not.toBeNull();
      expect(delta.textContent).toBe("-5%");
      const arrow = document.querySelector(".plo-trend-arrow");
      expect(arrow).not.toBeNull();
      expect(arrow.textContent).toBe("↓");
    });

    test("summary bar badge reflects data up to selectedTermId only", () => {
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
            trend: [{ pass_rate: 70 }, { pass_rate: 65 }, { pass_rate: 80 }],
            clos: [],
          },
        ],
      };

      PloTrend.injectSparklines();

      const slot = document.querySelector(".plo-summary-sparkline-slot");
      const badge = slot.querySelector(".plo-trend-indicator");
      expect(badge).not.toBeNull();
      const delta = badge.querySelector(".plo-trend-delta");
      expect(delta).not.toBeNull();
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
            trend: [{ pass_rate: 80 }, { pass_rate: 75 }, { pass_rate: 90 }],
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

      PloTrend._toggleTrendPanel(nodeEl, points, terms, {});
      expect(nodeEl.querySelector(".plo-trend-panel")).not.toBeNull();

      PloTrend._toggleTrendPanel(nodeEl, points, terms, {});
      expect(nodeEl.querySelector(".plo-trend-panel")).toBeNull();
    });

    test("adds expanded class to node so CSS does not hide panel", () => {
      document.body.innerHTML = `
        <li id="testNode" class="plo-tree-node">
          <div class="plo-tree-header"></div>
        </li>
      `;
      const nodeEl = document.getElementById("testNode");
      expect(nodeEl.classList.contains("expanded")).toBe(false);

      const terms = [
        { term_name: "Fall 2024", is_current: false },
        { term_name: "Spring 2025", is_current: false },
      ];
      const points = [{ pass_rate: 80 }, { pass_rate: 90 }];

      PloTrend._toggleTrendPanel(nodeEl, points, terms, {});

      expect(nodeEl.classList.contains("expanded")).toBe(true);
      expect(nodeEl.querySelector(".plo-trend-panel")).not.toBeNull();
    });

    test("CLO-level node gets expanded so trend panel is visible", () => {
      document.body.innerHTML = `
        <li id="cloNode" class="plo-tree-node">
          <div class="plo-tree-header">
            <span class="plo-tree-meta">
              <span class="plo-assessment-badge">S (100%)</span>
            </span>
          </div>
          <ul><li class="plo-tree-node leaf">Section data</li></ul>
        </li>
      `;
      const nodeEl = document.getElementById("cloNode");

      const terms = [
        { term_name: "Fall 2024", is_current: false },
        { term_name: "Spring 2025", is_current: false },
      ];
      const points = [{ pass_rate: 90 }, { pass_rate: 95 }];

      PloTrend._toggleTrendPanel(nodeEl, points, terms, {});

      // Node must be expanded so the CSS rule
      // .plo-tree-node:not(.expanded) > .plo-trend-panel { display: none }
      // does NOT hide the panel.
      expect(nodeEl.classList.contains("expanded")).toBe(true);
      const panel = nodeEl.querySelector(".plo-trend-panel");
      expect(panel).not.toBeNull();
    });

    test("destroys Chart.js instances before removing panel", () => {
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

      PloTrend._toggleTrendPanel(nodeEl, points, terms, {});
      const panel = nodeEl.querySelector(".plo-trend-panel");
      expect(panel).not.toBeNull();

      const canvas = panel.querySelector("canvas");
      expect(canvas).not.toBeNull();
      const chartInst = Chart.getChart(canvas);

      PloTrend._toggleTrendPanel(nodeEl, points, terms, {});
      expect(nodeEl.querySelector(".plo-trend-panel")).toBeNull();
      if (chartInst) {
        expect(chartInst.destroy).toHaveBeenCalled();
      }
    });
  });

  describe("keyboard accessibility", () => {
    test("trend indicator responds to Enter key", () => {
      document.body.innerHTML = `
        <div id="ploTreeContainer">
          <div data-plo-id="p1">
            <div class="plo-tree-header">
              <span class="plo-tree-meta">
                <span class="plo-assessment-badge">badge</span>
              </span>
            </div>
          </div>
        </div>
      `;
      PloTrend.trendData = {
        terms: [
          { term_name: "F24", term_id: "t1", is_current: false },
          { term_name: "S25", term_id: "t2", is_current: false },
        ],
        plos: [
          {
            id: "p1",
            plo_number: 1,
            description: "Test PLO",
            trend: [{ pass_rate: 70 }, { pass_rate: 80 }],
            clos: [],
          },
        ],
      };
      PloTrend.selectedTermId = null;
      PloTrend.injectSparklines();

      const indicator = document.querySelector(".plo-trend-indicator");
      expect(indicator).not.toBeNull();
      expect(indicator.getAttribute("tabindex")).toBe("0");
      expect(indicator.getAttribute("role")).toBe("button");

      const event = new KeyboardEvent("keydown", {
        key: "Enter",
        bubbles: true,
      });
      indicator.dispatchEvent(event);

      const panel = document.querySelector(".plo-trend-panel");
      expect(panel).not.toBeNull();
    });

    test("summary sparkline responds to Space key", () => {
      document.body.innerHTML = `
        <div id="ploTreeContainer">
          <div class="plo-summary-bar">
            <div class="plo-summary-row">
              <div class="plo-summary-sparkline-slot" data-plo-id="p1">
                <span class="plo-summary-sparkline-label">PLO 1</span>
              </div>
            </div>
          </div>
        </div>
      `;
      PloTrend.trendData = {
        terms: [
          { term_name: "F24", term_id: "t1", is_current: false },
          { term_name: "S25", term_id: "t2", is_current: false },
        ],
        plos: [
          {
            id: "p1",
            plo_number: 1,
            description: "Test PLO",
            trend: [{ pass_rate: 70 }, { pass_rate: 80 }],
            clos: [],
          },
        ],
      };
      PloTrend.selectedTermId = null;
      PloTrend.injectSparklines();

      const canvas = document.querySelector(".plo-sparkline");
      expect(canvas).not.toBeNull();
      expect(canvas.getAttribute("tabindex")).toBe("0");
      expect(canvas.getAttribute("role")).toBe("button");
      expect(canvas.getAttribute("aria-label")).toContain("PLO-1");

      const event = new KeyboardEvent("keydown", {
        key: " ",
        bubbles: true,
      });
      canvas.dispatchEvent(event);

      const panel = document.querySelector(".plo-trend-panel");
      expect(panel).not.toBeNull();
    });
  });

  describe("loadTrend race guard", () => {
    test("ignores stale response when a newer loadTrend is called", async () => {
      let resolveFirst;
      const firstFetch = new Promise((r) => {
        resolveFirst = r;
      });
      let resolveSecond;
      const secondFetch = new Promise((r) => {
        resolveSecond = r;
      });

      let callCount = 0;
      global.fetch = jest.fn(() => {
        callCount++;
        return callCount === 1 ? firstFetch : secondFetch;
      });

      document.body.innerHTML = '<div id="ploTreeContainer"></div>';
      PloTrend.trendData = null;

      const p1 = PloTrend.loadTrend("prog-1");
      const p2 = PloTrend.loadTrend("prog-2");

      resolveSecond({
        ok: true,
        json: async () => ({
          success: true,
          terms: [{ term_name: "T1" }, { term_name: "T2" }],
          plos: [],
        }),
      });
      await p2;

      expect(PloTrend.trendData).not.toBeNull();
      expect(PloTrend.trendData.success).toBe(true);

      const staleTrendData = PloTrend.trendData;
      resolveFirst({
        ok: true,
        json: async () => ({
          success: true,
          terms: [{ term_name: "OLD" }],
          plos: [{ id: "stale" }],
        }),
      });
      await p1;

      expect(PloTrend.trendData).toBe(staleTrendData);

      delete global.fetch;
    });
  });
});
