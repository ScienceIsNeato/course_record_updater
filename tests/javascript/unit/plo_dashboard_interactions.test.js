const {
  setLoadingState,
  setErrorState,
  setEmptyState,
} = require("../../../static/dashboard_utils");
global.setLoadingState = setLoadingState;
global.setErrorState = setErrorState;
global.setEmptyState = setEmptyState;

const { PloDashboard } = require("../../../static/plo_dashboard");
const { setBody } = require("../helpers/dom");
const {
  resetDashboardState,
  routeFetch,
  SAMPLE_TREE,
  SKELETON,
} = require("./helpers/plo_dashboard_fixtures");

describe("PloDashboard — expand/collapse + event wiring", () => {
  beforeEach(() => {
    setBody(SKELETON);
    resetDashboardState(PloDashboard);
    PloDashboard._cacheSelectors();
    PloDashboard._bindEvents();
    PloDashboard.programs = [{ program_id: "prog-1", name: "Biology" }];
    PloDashboard.currentProgramId = "prog-1";
  });

  afterEach(() => {
    delete global.fetch;
  });

  test("expandAll / collapseAll toggle .expanded on every node", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => SAMPLE_TREE });
    await PloDashboard.loadTree();

    let expanded = document.querySelectorAll(".plo-tree-node.expanded");
    const initialCount = expanded.length;

    document.getElementById("expandAllBtn").click();
    expanded = document.querySelectorAll(".plo-tree-node.expanded");
    expect(expanded.length).toBeGreaterThan(initialCount);

    document.getElementById("collapseAllBtn").click();
    expanded = document.querySelectorAll(".plo-tree-node.expanded");
    expect(expanded.length).toBe(0);
  });

  test("clicking a PLO header toggles its expanded state", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => SAMPLE_TREE });
    await PloDashboard.loadTree();

    const plo1 = document.querySelector("ul.plo-tree > li.plo-tree-node");
    const header = plo1.querySelector(".plo-tree-header");
    expect(plo1.classList.contains("expanded")).toBe(false);
    header.click();
    expect(plo1.classList.contains("expanded")).toBe(true);
    header.click();
    expect(plo1.classList.contains("expanded")).toBe(false);
  });

  test("term filter change triggers loadTree with new term", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => SAMPLE_TREE });

    const termSel = document.getElementById("ploTermFilter");
    termSel.innerHTML += '<option value="t-spring">Spring</option>';
    termSel.value = "t-spring";
    termSel.dispatchEvent(new Event("change"));

    await Promise.resolve();
    await Promise.resolve();

    expect(PloDashboard.currentTermId).toBe("t-spring");
    expect(global.fetch).toHaveBeenCalled();
    expect(global.fetch.mock.calls[0][0]).toMatch(/term_id=t-spring/);
  });

  test("display-mode change re-renders without re-fetching", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => SAMPLE_TREE });
    await PloDashboard.loadTree();
    expect(global.fetch).toHaveBeenCalledTimes(1);

    const putMock = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({}) });
    global.fetch = putMock;

    const modeSel = document.getElementById("ploDisplayMode");
    modeSel.value = "percentage";
    modeSel.dispatchEvent(new Event("change"));
    await Promise.resolve();

    expect(PloDashboard.displayMode).toBe("percentage");
    expect(putMock).toHaveBeenCalledTimes(1);
    const [putUrl, putOpts] = putMock.mock.calls[0];
    expect(putOpts.method).toBe("PUT");
    expect(putUrl).toMatch(/\/api\/programs\/prog-1$/);
    expect(putOpts.headers["X-CSRFToken"]).toBe("test-csrf-token");
    expect(JSON.parse(putOpts.body)).toEqual({
      assessment_display_mode: "percentage",
    });

    const badges = document.querySelectorAll(".plo-assessment-badge");
    expect(Array.from(badges).some((b) => b.textContent.includes("%"))).toBe(
      true,
    );
  });

  test("program filter change persists to localStorage", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => SAMPLE_TREE });

    const sel = document.getElementById("ploProgramFilter");
    sel.innerHTML = '<option value="prog-X">X</option>';
    sel.value = "prog-X";
    sel.dispatchEvent(new Event("change"));

    expect(localStorage.getItem("ploDashboard.lastProgramId")).toBe("prog-X");
    expect(PloDashboard.currentProgramId).toBe("prog-X");
  });
});

describe("PloDashboard — PLO create/edit modal", () => {
  beforeEach(() => {
    setBody(SKELETON);
    resetDashboardState(PloDashboard);
    PloDashboard._cacheSelectors();
    PloDashboard.currentProgramId = "prog-1";
  });

  afterEach(() => {
    delete global.fetch;
  });

  test('_openPloModal(undefined) prepares for "create" mode', () => {
    PloDashboard._openPloModal();
    expect(document.getElementById("ploModalLabel").textContent).toMatch(
      /new/i,
    );
    expect(document.getElementById("ploModalId").value).toBe("");
    expect(
      document
        .getElementById("ploModalNumberGroup")
        .classList.contains("d-none"),
    ).toBe(true);
    expect(document.getElementById("ploModal").classList.contains("show")).toBe(
      true,
    );
  });

  test('_openPloModal(plo) prefills for "edit" mode', () => {
    PloDashboard._openPloModal({
      id: "plo-abc",
      plo_number: 5,
      description: "Capstone assessment.",
    });
    expect(document.getElementById("ploModalLabel").textContent).toMatch(
      /edit/i,
    );
    expect(document.getElementById("ploModalId").value).toBe("plo-abc");
    expect(document.getElementById("ploModalNumber").value).toBe("5");
    expect(document.getElementById("ploModalDescription").value).toBe(
      "Capstone assessment.",
    );
    expect(
      document
        .getElementById("ploModalNumberGroup")
        .classList.contains("d-none"),
    ).toBe(false);
  });

  test("_submitPloForm POSTs without plo_number (auto-assigned), hides modal on success", async () => {
    document.getElementById("ploModalId").value = "";
    document.getElementById("ploModalNumber").value = "";
    document.getElementById("ploModalDescription").value = "New outcome";

    global.fetch = routeFetch([
      ["/plos", { body: { success: true, plo: { id: "new-id" } } }],
      ["/plo-dashboard", { body: { ...SAMPLE_TREE } }],
    ]);

    const evt = { preventDefault: jest.fn() };
    await PloDashboard._submitPloForm(evt);

    expect(evt.preventDefault).toHaveBeenCalled();
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toMatch(/\/api\/programs\/prog-1\/plos$/);
    expect(opts.method).toBe("POST");
    expect(JSON.parse(opts.body)).toEqual({
      description: "New outcome",
    });
    expect(opts.headers["X-CSRFToken"]).toBe("test-csrf-token");
    expect(document.getElementById("ploModal").classList.contains("show")).toBe(
      false,
    );
  });

  test("_submitPloForm PUTs when ploModalId is set", async () => {
    document.getElementById("ploModalId").value = "existing-plo";
    document.getElementById("ploModalNumber").value = "3";
    document.getElementById("ploModalDescription").value = "edited";

    global.fetch = routeFetch([
      ["/plos/existing-plo", { body: { success: true } }],
      ["/plo-dashboard", { body: SAMPLE_TREE }],
    ]);

    await PloDashboard._submitPloForm({ preventDefault: jest.fn() });
    const [url, opts] = global.fetch.mock.calls[0];
    expect(opts.method).toBe("PUT");
    expect(url).toMatch(/\/plos\/existing-plo$/);
  });

  test("_submitPloForm shows danger alert on API error", async () => {
    document.getElementById("ploModalNumber").value = "1";
    document.getElementById("ploModalDescription").value = "dup";
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({
        success: false,
        error: "PLO number already exists",
      }),
    });

    await PloDashboard._submitPloForm({ preventDefault: jest.fn() });

    const alert = document.getElementById("ploModalAlert");
    expect(alert.className).toContain("alert-danger");
    expect(alert.textContent).toContain("PLO number already exists");
  });

  test("PLO form uses method=dialog to prevent accidental page reload", () => {
    const form = document.getElementById("ploForm");
    expect(form.getAttribute("method")).toBe("dialog");
  });
});

describe("PloDashboard — Map CLO modal + publish", () => {
  beforeEach(() => {
    setBody(SKELETON);
    resetDashboardState(PloDashboard);
    PloDashboard._cacheSelectors();
    PloDashboard.currentProgramId = "prog-1";
    PloDashboard.tree = SAMPLE_TREE;
  });

  afterEach(() => {
    delete global.fetch;
  });

  test("_openMapCloModal populates PLOs + unmapped CLOs", async () => {
    global.fetch = routeFetch([
      [
        "/plo-mappings/draft",
        { body: { success: true, mapping: { id: "draft-1" } } },
      ],
      [
        "/unmapped-clos",
        {
          body: {
            unmapped_clos: [
              {
                outcome_id: "clo-1",
                clo_number: "4",
                description: "Analyze data",
                course: { course_number: "BIOL-201" },
              },
            ],
          },
        },
      ],
    ]);

    await PloDashboard._openMapCloModal("plo-1");

    expect(PloDashboard.draftMappingId).toBe("draft-1");

    const ploSel = document.getElementById("mapCloModalPlo");
    expect(ploSel.options.length).toBe(3);
    expect(ploSel.value).toBe("plo-1");

    const cloSel = document.getElementById("mapCloModalClo");
    expect(cloSel.options.length).toBe(2);
    expect(cloSel.options[1].textContent).toContain("BIOL-201");
  });

  test('_openMapCloModal shows "all mapped" when list is empty', async () => {
    global.fetch = routeFetch([
      ["/plo-mappings/draft", { body: { mapping: { id: "d-2" } } }],
      ["/unmapped-clos", { body: { unmapped_clos: [] } }],
    ]);
    await PloDashboard._openMapCloModal();
    expect(document.getElementById("mapCloModalClo").textContent).toMatch(
      /all clos are already mapped/i,
    );
  });

  test("_submitMapCloForm warns when PLO or CLO missing", async () => {
    PloDashboard.draftMappingId = "draft-x";
    document.getElementById("mapCloModalPlo").innerHTML =
      '<option value="">-</option>';
    document.getElementById("mapCloModalClo").innerHTML =
      '<option value="clo-1">CLO</option>';
    document.getElementById("mapCloModalClo").value = "clo-1";

    global.fetch = jest.fn();
    await PloDashboard._submitMapCloForm({ preventDefault: jest.fn() });

    expect(global.fetch).not.toHaveBeenCalled();
    const alert = document.getElementById("mapCloModalAlert");
    expect(alert.className).toContain("alert-warning");
    expect(alert.textContent).toMatch(/select both/i);
  });

  test("_submitMapCloForm POSTs entry with selected ids", async () => {
    PloDashboard.draftMappingId = "draft-y";
    document.getElementById("mapCloModalPlo").innerHTML =
      '<option value="plo-1">PLO-1</option>';
    document.getElementById("mapCloModalClo").innerHTML =
      '<option value="clo-A">CLO-A</option>';

    global.fetch = routeFetch([
      [
        "/plo-mappings/draft-y/entries",
        { body: { success: true, entry: { id: "e-1" } } },
      ],
      ["/plo-mappings/draft", { body: { mapping: { id: "draft-y" } } }],
      ["/unmapped-clos", { body: { unmapped_clos: [] } }],
    ]);

    await PloDashboard._submitMapCloForm({ preventDefault: jest.fn() });

    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toMatch(/draft-y\/entries$/);
    expect(JSON.parse(opts.body)).toEqual({
      program_outcome_id: "plo-1",
      course_outcome_id: "clo-A",
    });
  });

  test("_publishDraft no-ops without a draft id", async () => {
    PloDashboard.draftMappingId = null;
    global.fetch = jest.fn();
    await PloDashboard._publishDraft();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test("_publishDraft POSTs and refreshes tree on success", async () => {
    PloDashboard.draftMappingId = "draft-z";
    global.fetch = routeFetch([
      [
        "/draft-z/publish",
        { body: { success: true, mapping: { version: 3 } } },
      ],
      ["/plo-dashboard", { body: SAMPLE_TREE }],
    ]);

    await PloDashboard._publishDraft();

    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toMatch(/\/plo-mappings\/draft-z\/publish$/);
    expect(opts.method).toBe("POST");
    expect(
      document.getElementById("mapCloModal").classList.contains("show"),
    ).toBe(false);
    expect(global.fetch.mock.calls[1][0]).toMatch(/\/plo-dashboard/);
  });

  test("_publishDraft shows error alert on API failure", async () => {
    PloDashboard.draftMappingId = "draft-err";
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ success: false, error: "Nothing to publish" }),
    });
    await PloDashboard._publishDraft();
    const alert = document.getElementById("mapCloModalAlert");
    expect(alert.className).toContain("alert-danger");
    expect(alert.textContent).toContain("Nothing to publish");
  });

  test("Map CLO form uses method=dialog to prevent accidental page reload", () => {
    const form = document.getElementById("mapCloForm");
    expect(form.getAttribute("method")).toBe("dialog");
  });
});

describe("PloDashboard — small helpers", () => {
  test("_csrf reads from meta tag", () => {
    setBody('<meta name="csrf-token" content="abc123">');
    PloDashboard._cacheSelectors();
    expect(PloDashboard._csrf()).toBe("abc123");
  });

  test("_csrf returns empty string when meta missing", () => {
    setBody("");
    expect(PloDashboard._csrf()).toBe("");
  });

  test("_modalAlert sets class + text; tolerates null element", () => {
    setBody('<div id="a"></div>');
    const el = document.getElementById("a");
    PloDashboard._modalAlert(el, "hello", "warning");
    expect(el.className).toBe("alert alert-warning");
    expect(el.textContent).toBe("hello");
    expect(() => PloDashboard._modalAlert(null, "x", "info")).not.toThrow();
  });

  test("_showModal/_hideModal use class-toggle fallback when no bootstrap", () => {
    setBody('<div id="m" style="display:none"></div>');
    const m = document.getElementById("m");
    PloDashboard._showModal(m);
    expect(m.classList.contains("show")).toBe(true);
    expect(m.style.display).toBe("block");
    PloDashboard._hideModal(m);
    expect(m.classList.contains("show")).toBe(false);
    expect(m.style.display).toBe("none");
  });
});

describe("PloDashboard — _buildSummaryBar", () => {
  test("renders rows with sparkline slots for mixed PLO statuses", () => {
    const plos = [
      { id: "p1", plo_number: 1, aggregate: { pass_rate: 90 } },
      { id: "p2", plo_number: 2, aggregate: { pass_rate: 85 } },
      { id: "p3", plo_number: 3, aggregate: { pass_rate: 60 } },
      { id: "p4", plo_number: 4, aggregate: { pass_rate: null } },
    ];

    const bar = PloDashboard._buildSummaryBar(plos);
    expect(bar.className).toBe("plo-summary-bar");
    expect(bar.querySelectorAll(".plo-summary-row").length).toBe(3);

    const stats = bar.querySelectorAll(".plo-summary-stat");
    expect(stats.length).toBe(3);
    expect(stats[0].textContent).toContain("2");
    expect(stats[0].textContent).toContain("satisfactory");
    expect(stats[1].textContent).toContain("1");
    expect(stats[1].textContent).toContain("needs attention");
    expect(stats[2].textContent).toContain("1");
    expect(stats[2].textContent).toContain("no data");

    const slots = bar.querySelectorAll(".plo-summary-sparkline-slot");
    expect(slots.length).toBe(4);
    expect(slots[0].dataset.ploId).toBe("p1");
    expect(slots[1].dataset.ploId).toBe("p2");

    const labels = bar.querySelectorAll(".plo-summary-sparkline-label");
    expect(labels[0].textContent).toBe("(1)");

    const segments = bar.querySelectorAll(".plo-summary-segment");
    expect(segments.length).toBe(3);
    expect(segments[0].className).toContain("seg-pass");
    expect(segments[1].className).toContain("seg-fail");
    expect(segments[2].className).toContain("seg-nodata");
  });

  test("omits zero-count categories", () => {
    const plos = [
      { id: "p1", plo_number: 1, aggregate: { pass_rate: 90 } },
      { id: "p2", plo_number: 2, aggregate: { pass_rate: 80 } },
    ];

    const bar = PloDashboard._buildSummaryBar(plos);
    expect(bar.querySelectorAll(".plo-summary-row").length).toBe(1);
    expect(bar.querySelectorAll(".plo-summary-stat").length).toBe(1);
    expect(bar.querySelector(".plo-summary-stat").textContent).toContain(
      "satisfactory",
    );
    expect(bar.querySelectorAll(".plo-summary-segment").length).toBe(1);
  });

  test("returns empty bar for null/empty plos", () => {
    const bar = PloDashboard._buildSummaryBar([]);
    expect(bar.querySelector(".plo-summary-stat")).toBeNull();

    const bar2 = PloDashboard._buildSummaryBar(null);
    expect(bar2.querySelector(".plo-summary-stat")).toBeNull();
  });

  test("summary bar is inserted above tree in renderTree", async () => {
    setBody(SKELETON);
    resetDashboardState(PloDashboard);
    PloDashboard._cacheSelectors();
    PloDashboard.programs = [{ program_id: "prog-1", name: "Biology BS" }];
    PloDashboard.currentProgramId = "prog-1";
    PloDashboard.currentTermId = "t-active";

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => SAMPLE_TREE,
    });
    await PloDashboard.loadTree();
    delete global.fetch;

    const container = document.getElementById("ploTreeContainer");
    const summaryBar = container.querySelector(".plo-summary-bar");
    expect(summaryBar).not.toBeNull();

    const stats = summaryBar.querySelectorAll(".plo-summary-stat");
    expect(stats.length).toBe(2);
    expect(stats[0].textContent).toContain("satisfactory");
    expect(stats[1].textContent).toContain("no data");

    const tree = container.querySelector("ul.plo-tree");
    expect(container.children[0]).toBe(summaryBar);
    expect(container.children[1]).toBe(tree);
  });
});

describe("PloDashboard — _loadAllPrograms", () => {
  beforeEach(() => {
    setBody(SKELETON);
    resetDashboardState(PloDashboard);
    PloDashboard._cacheSelectors();
  });

  afterEach(() => {
    delete global.fetch;
  });

  test("fetches all programs in parallel and renders sections", async () => {
    PloDashboard.programs = [
      { program_id: "prog-1", name: "Biology BS" },
      { program_id: "prog-2", name: "Chemistry BS" },
    ];
    PloDashboard.currentProgramId = "";
    PloDashboard.currentTermId = "";

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => SAMPLE_TREE,
    });

    await PloDashboard._loadAllPrograms();

    const headings = document.querySelectorAll(".plo-all-programs-heading");
    expect(headings.length).toBe(2);
    expect(headings[0].textContent).toContain("Biology BS");
    expect(headings[1].textContent).toContain("Chemistry BS");
  });

  test("handles failed fetch for one program gracefully", async () => {
    PloDashboard.programs = [
      { program_id: "prog-1", name: "Biology BS" },
      { program_id: "prog-2", name: "Chemistry BS" },
    ];
    PloDashboard.currentProgramId = "";

    let callCount = 0;
    global.fetch = jest.fn(() => {
      callCount++;
      if (callCount === 1) {
        return Promise.resolve({
          ok: true,
          json: async () => SAMPLE_TREE,
        });
      }
      return Promise.reject(new Error("Network error"));
    });

    await PloDashboard._loadAllPrograms();

    const headings = document.querySelectorAll(".plo-all-programs-heading");
    expect(headings.length).toBe(1);
    expect(headings[0].textContent).toContain("Biology BS");
  });

  test("ignores stale results when generation counter changes", async () => {
    PloDashboard.programs = [{ program_id: "prog-1", name: "Biology BS" }];
    PloDashboard.currentProgramId = "";

    let resolveFirst;
    global.fetch = jest.fn(
      () =>
        new Promise((resolve) => {
          resolveFirst = resolve;
        }),
    );

    const firstLoad = PloDashboard._loadAllPrograms();
    PloDashboard._allProgramsGen = (PloDashboard._allProgramsGen || 0) + 1;

    resolveFirst({
      ok: true,
      json: async () => SAMPLE_TREE,
    });
    await firstLoad;

    const container = document.getElementById("ploTreeContainer");
    expect(container.querySelectorAll(".plo-all-programs-heading").length).toBe(
      0,
    );
  });

  test("renders version badge when mapping has version", async () => {
    PloDashboard.programs = [{ program_id: "prog-1", name: "Biology BS" }];
    PloDashboard.currentProgramId = "";

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => SAMPLE_TREE,
    });

    await PloDashboard._loadAllPrograms();

    const badge = document.querySelector(".plo-all-programs-heading .badge");
    expect(badge).not.toBeNull();
    expect(badge.textContent).toBe("v2");
  });

  test("collapsible toggle works on heading click", async () => {
    PloDashboard.programs = [{ program_id: "prog-1", name: "Biology BS" }];
    PloDashboard.currentProgramId = "";

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => SAMPLE_TREE,
    });

    await PloDashboard._loadAllPrograms();

    const section = document.querySelector(".plo-program-section");
    const heading = document.querySelector(".plo-all-programs-heading");
    expect(section).not.toBeNull();

    heading.click();
    expect(section.classList.contains("collapsed")).toBe(true);

    heading.click();
    expect(section.classList.contains("collapsed")).toBe(false);
  });

  test('shows "No PLOs defined" for program with empty plos', async () => {
    PloDashboard.programs = [{ program_id: "prog-1", name: "Empty Program" }];
    PloDashboard.currentProgramId = "";

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ...SAMPLE_TREE,
        plos: [],
        mapping: null,
      }),
    });

    await PloDashboard._loadAllPrograms();

    const emptyMsg = document.querySelector(".text-muted.fst-italic");
    expect(emptyMsg).not.toBeNull();
    expect(emptyMsg.textContent).toBe("No PLOs defined.");
  });

  test("saves and restores displayMode per program", async () => {
    PloDashboard.programs = [{ program_id: "prog-1", name: "Biology BS" }];
    PloDashboard.currentProgramId = "";
    PloDashboard.displayMode = "percentage";

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ...SAMPLE_TREE,
        assessment_display_mode: "binary",
      }),
    });

    await PloDashboard._loadAllPrograms();
    expect(PloDashboard.displayMode).toBe("percentage");
  });
});

describe("PloDashboard — _loadAllTrendData", () => {
  beforeEach(() => {
    setBody(SKELETON);
    resetDashboardState(PloDashboard);
    PloDashboard._cacheSelectors();
    delete global.PloTrend;
  });

  afterEach(() => {
    delete global.fetch;
    delete global.PloTrend;
  });

  test("injects sparklines for ALL programs, not just the last", async () => {
    PloDashboard.programs = [
      { program_id: "prog-1", name: "Biology BS" },
      { program_id: "prog-2", name: "Chemistry BS" },
    ];
    PloDashboard.currentTermId = "t-1";

    const injectCalls = [];
    global.PloTrend = {
      trendData: null,
      selectedTermId: null,
      injectSparklines: jest.fn(function () {
        injectCalls.push(this.trendData);
      }),
    };

    const trendProg1 = {
      success: true,
      program_id: "prog-1",
      terms: [{ term_id: "t-1" }, { term_id: "t-2" }],
      plos: [{ id: "plo-1", trend: [70, 80] }],
    };
    const trendProg2 = {
      success: true,
      program_id: "prog-2",
      terms: [{ term_id: "t-1" }, { term_id: "t-2" }],
      plos: [{ id: "plo-2", trend: [60, 75] }],
    };

    global.fetch = jest.fn().mockImplementation((url) => {
      if (url.includes("prog-1")) {
        return Promise.resolve({
          ok: true,
          json: async () => trendProg1,
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => trendProg2,
      });
    });

    await PloDashboard._loadAllTrendData();

    expect(global.PloTrend.injectSparklines).toHaveBeenCalledTimes(2);
    expect(injectCalls[0]).toBe(trendProg1);
    expect(injectCalls[1]).toBe(trendProg2);
    expect(global.PloTrend.selectedTermId).toBe("t-1");
  });

  test("ignores stale results when generation counter changes", async () => {
    PloDashboard.programs = [{ program_id: "prog-1", name: "Biology BS" }];

    global.PloTrend = {
      trendData: null,
      selectedTermId: null,
      injectSparklines: jest.fn(),
    };

    let resolveFirst;
    global.fetch = jest.fn(
      () =>
        new Promise((resolve) => {
          resolveFirst = resolve;
        }),
    );

    const firstLoad = PloDashboard._loadAllTrendData();
    PloDashboard._allTrendGen = (PloDashboard._allTrendGen || 0) + 1;

    resolveFirst({
      ok: true,
      json: async () => ({
        success: true,
        terms: [{ term_id: "t-1" }, { term_id: "t-2" }],
        plos: [],
      }),
    });
    await firstLoad;

    expect(global.PloTrend.injectSparklines).not.toHaveBeenCalled();
  });

  test("skips failed fetches without breaking other programs", async () => {
    PloDashboard.programs = [
      { program_id: "prog-1", name: "Biology BS" },
      { program_id: "prog-2", name: "Chemistry BS" },
    ];

    global.PloTrend = {
      trendData: null,
      selectedTermId: null,
      injectSparklines: jest.fn(),
    };

    global.fetch = jest.fn().mockImplementation((url) => {
      if (url.includes("prog-1")) {
        return Promise.reject(new Error("Network error"));
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({
          success: true,
          terms: [{ term_id: "t-1" }, { term_id: "t-2" }],
          plos: [{ id: "plo-2" }],
        }),
      });
    });

    await PloDashboard._loadAllTrendData();

    expect(global.PloTrend.injectSparklines).toHaveBeenCalledTimes(1);
  });

  test("no-ops when PloTrend is not available", async () => {
    PloDashboard.programs = [{ program_id: "prog-1", name: "Biology BS" }];
    delete global.PloTrend;

    await expect(PloDashboard._loadAllTrendData()).resolves.toBeUndefined();
    expect(PloDashboard.programs).toEqual([
      { program_id: "prog-1", name: "Biology BS" },
    ]);
  });
});
