/**
 * Unit tests for static/plo_detail_panel.js.
 *
 * Tests define the DOM contract for the drill-down detail panel that
 * appears below the PLO trend chart when a user clicks a data point.
 */

const { setBody } = require("../helpers/dom");
const {
  MOCK_PLO_DATA,
  MOCK_PLO_NO_CLOS,
  MOCK_TERM_LABEL,
} = require("./helpers/plo_detail_panel_fixtures");

// Module under test — will fail until plo_detail_panel.js is created
const {
  createDetailPanel,
  destroyDetailPanel,
} = require("../../../static/plo_detail_panel");

let originalRequestAnimationFrame;
let queuedAnimationFrames;

function flushAnimationFrames() {
  while (queuedAnimationFrames.length > 0) {
    const callbacks = queuedAnimationFrames.slice();
    queuedAnimationFrames = [];
    callbacks.forEach((cb) => cb());
  }
}

beforeEach(() => {
  originalRequestAnimationFrame = global.requestAnimationFrame;
  queuedAnimationFrames = [];
  global.requestAnimationFrame = (cb) => {
    queuedAnimationFrames.push(cb);
    return queuedAnimationFrames.length;
  };
});

afterEach(() => {
  if (typeof originalRequestAnimationFrame === "undefined") {
    delete global.requestAnimationFrame;
  } else {
    global.requestAnimationFrame = originalRequestAnimationFrame;
  }
});

// ---------------------------------------------------------------------------
// createDetailPanel — container structure
// ---------------------------------------------------------------------------
describe("createDetailPanel — container", () => {
  test("returns a div.plo-detail-panel", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    expect(panel.tagName).toBe("DIV");
    expect(panel.classList.contains("plo-detail-panel")).toBe(true);
  });

  test("panel adds entering animation class after insertion", () => {
    setBody("<div id='host'></div>");
    const host = document.getElementById("host");
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    expect(panel.classList.contains("plo-detail-panel--entering")).toBe(false);
    host.appendChild(panel);
    flushAnimationFrames();
    expect(panel.classList.contains("plo-detail-panel--entering")).toBe(true);
  });

  test("panel has a close button", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const btn = panel.querySelector(".plo-detail-panel-close");
    expect(btn).not.toBeNull();
    expect(btn.getAttribute("aria-label")).toBe("Close detail panel");
  });

  test("panel header shows PLO number, description, and term", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const header = panel.querySelector(".plo-detail-panel-header");
    expect(header).not.toBeNull();
    expect(header.textContent).toContain("PLO 1");
    expect(header.textContent).toContain("Fall 2025");
  });

  test("panel shows a drill-through context block with selected term badge", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const context = panel.querySelector(".plo-detail-panel-context");
    const hint = panel.querySelector(".plo-detail-panel-context-hint");
    const eyebrow = panel.querySelector(".plo-detail-panel-term-eyebrow");
    const badge = panel.querySelector(".plo-detail-panel-term-badge");
    const metrics = Array.from(
      panel.querySelectorAll(".plo-detail-panel-metric"),
    ).map((el) => el.textContent);

    expect(context).not.toBeNull();
    expect(context.textContent).toContain("Chart drill-through");
    expect(hint.textContent).toContain("2 mapped CLOs");
    expect(hint.textContent).toContain("3 assessed sections");
    expect(hint.textContent).toContain("80 students assessed");
    expect(hint.textContent).toContain("80% meeting target");
    expect(eyebrow).not.toBeNull();
    expect(eyebrow.textContent).toBe("Selected term");
    expect(badge).not.toBeNull();
    expect(badge.textContent).toBe("Fall 2025");
    expect(metrics).toContain("2 CLOs");
    expect(metrics).toContain("3 sections");
    expect(metrics).toContain("2 sections with notes");
    expect(metrics).toContain("1 reviewer comment");
  });

  test("panel includes expand-all toggle when CLO data exists", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const toggle = panel.querySelector(".plo-detail-panel-toggle-all");
    expect(toggle).not.toBeNull();
    expect(toggle.textContent).toBe("Collapse all CLOs");
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
  });
});

// ---------------------------------------------------------------------------
// createDetailPanel — CLO rows
// ---------------------------------------------------------------------------
describe("createDetailPanel — CLO rows", () => {
  test("renders one CLO row per CLO in data", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const cloRows = panel.querySelectorAll(".plo-detail-clo");
    expect(cloRows.length).toBe(2);
  });

  test("CLO row shows course number and description", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const firstClo = panel.querySelector(".plo-detail-clo");
    expect(firstClo.textContent).toContain("BIOL-301");
    expect(firstClo.textContent).toContain("CLO 3");
  });

  test("CLO row shows course title when available", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const firstClo = panel.querySelector(".plo-detail-clo");
    expect(firstClo.textContent).toContain("Biology Lab");
  });

  test("CLO row shows aggregate pass rate", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const firstClo = panel.querySelector(".plo-detail-clo");
    expect(firstClo.textContent).toContain("80%");
  });

  test("CLO rows start expanded", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const firstClo = panel.querySelector(".plo-detail-clo");
    expect(firstClo.classList.contains("expanded")).toBe(true);
  });

  test("clicking CLO header toggles expanded", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const firstClo = panel.querySelector(".plo-detail-clo");
    const header = firstClo.querySelector(".plo-detail-clo-header");
    header.click(); // collapse
    expect(firstClo.classList.contains("expanded")).toBe(false);
    expect(header.getAttribute("aria-expanded")).toBe("false");
    header.click(); // expand again
    expect(firstClo.classList.contains("expanded")).toBe(true);
    expect(header.getAttribute("aria-expanded")).toBe("true");
  });

  test("CLO header supports keyboard toggle", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const firstClo = panel.querySelector(".plo-detail-clo");
    const header = firstClo.querySelector(".plo-detail-clo-header");

    expect(header.getAttribute("aria-expanded")).toBe("true");

    header.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Enter", bubbles: true }),
    );
    expect(firstClo.classList.contains("expanded")).toBe(false);
    expect(header.getAttribute("aria-expanded")).toBe("false");

    header.dispatchEvent(
      new KeyboardEvent("keydown", { key: " ", bubbles: true }),
    );
    expect(firstClo.classList.contains("expanded")).toBe(true);
    expect(header.getAttribute("aria-expanded")).toBe("true");
  });

  test("expand-all toggle expands and collapses every CLO row", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const toggle = panel.querySelector(".plo-detail-panel-toggle-all");
    const cloRows = panel.querySelectorAll(".plo-detail-clo");

    toggle.click();
    cloRows.forEach((row) => {
      expect(row.classList.contains("expanded")).toBe(false);
    });
    expect(toggle.textContent).toBe("Expand all CLOs");
    expect(toggle.getAttribute("aria-expanded")).toBe("false");

    toggle.click();
    cloRows.forEach((row) => {
      expect(row.classList.contains("expanded")).toBe(true);
    });
    expect(toggle.textContent).toBe("Collapse all CLOs");
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
  });

  test("toggle label updates when individual CLO rows change", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const toggle = panel.querySelector(".plo-detail-panel-toggle-all");
    const headers = panel.querySelectorAll(".plo-detail-clo-header");

    headers[0].click();
    expect(toggle.textContent).toBe("Expand all CLOs");
    expect(toggle.getAttribute("aria-expanded")).toBe("false");

    headers[0].click();
    expect(toggle.textContent).toBe("Collapse all CLOs");
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
  });
});

// ---------------------------------------------------------------------------
// createDetailPanel — section rows
// ---------------------------------------------------------------------------
describe("createDetailPanel — section rows", () => {
  test("section rows are inside CLO children container", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const firstClo = panel.querySelector(".plo-detail-clo");
    const children = firstClo.querySelector(".plo-detail-clo-children");
    expect(children).not.toBeNull();
    const sectionRows = children.querySelectorAll(".plo-detail-section");
    expect(sectionRows.length).toBe(2);
  });

  test("section row shows instructor name", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const sections = panel.querySelectorAll(".plo-detail-section");
    expect(sections[0].textContent).toContain("Ada Lovelace");
  });

  test("section row shows assessment tool", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const sections = panel.querySelectorAll(".plo-detail-section");
    expect(sections[0].textContent).toContain("Lab Report");
  });

  test("section row shows student counts", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const sections = panel.querySelectorAll(".plo-detail-section");
    expect(sections[0].textContent).toContain("27/30");
  });

  test("section row shows enrollment count", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const sections = panel.querySelectorAll(".plo-detail-section");
    expect(sections[0].textContent).toContain("enrolled: 32");
  });

  test("section row has a pass/fail badge", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const badge = panel.querySelector(
      ".plo-detail-section .plo-assessment-badge",
    );
    expect(badge).not.toBeNull();
  });

  test("section row has link to sections page with offering_id", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const link = panel.querySelector(".plo-detail-section a");
    expect(link).not.toBeNull();
    expect(link.getAttribute("href")).toContain("/sections");
    expect(link.getAttribute("href")).toContain("off-1");
  });

  test("section row shows assessment method from template", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const method = panel.querySelector(".plo-detail-section-method");
    expect(method).not.toBeNull();
    expect(method.textContent).toContain("Lab Report Rubric");
  });

  test("section row shows instructor narratives when available", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const narratives = panel.querySelectorAll(".plo-detail-narrative");
    // First section has celebrations, challenges, changes (3) + feedback_comments (1) = 4
    expect(narratives.length).toBeGreaterThanOrEqual(3);
    const texts = Array.from(narratives).map((n) => n.textContent);
    expect(texts.some((t) => t.includes("excellent collaboration"))).toBe(true);
    expect(texts.some((t) => t.includes("Time management"))).toBe(true);
    expect(texts.some((t) => t.includes("mid-project checkpoint"))).toBe(true);
  });

  test("section row shows reviewer feedback when present", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const narratives = panel.querySelectorAll(".plo-detail-narrative");
    const texts = Array.from(narratives).map((n) => n.textContent);
    expect(texts.some((t) => t.includes("Strong methodological rigor"))).toBe(
      true,
    );
  });

  test("section row omits narratives when null", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    // Third section (STAT-201) has all null narratives
    const allClos = panel.querySelectorAll(".plo-detail-clo");
    const statClo = allClos[1]; // second CLO is STAT-201
    const statNarr = statClo.querySelectorAll(".plo-detail-narrative");
    expect(statNarr.length).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// createDetailPanel — empty / no CLOs
// ---------------------------------------------------------------------------
describe("createDetailPanel — no CLO data", () => {
  test("empty CLOs array shows no-data message", () => {
    const panel = createDetailPanel(MOCK_PLO_NO_CLOS, MOCK_TERM_LABEL);
    const msg = panel.querySelector(".plo-detail-empty");
    expect(msg).not.toBeNull();
    expect(msg.textContent).toContain("No CLO data");
  });

  test("no CLO rows rendered for empty CLOs", () => {
    const panel = createDetailPanel(MOCK_PLO_NO_CLOS, MOCK_TERM_LABEL);
    const cloRows = panel.querySelectorAll(".plo-detail-clo");
    expect(cloRows.length).toBe(0);
  });

  test("no expand-all toggle is rendered when CLO list is empty", () => {
    const panel = createDetailPanel(MOCK_PLO_NO_CLOS, MOCK_TERM_LABEL);
    expect(panel.querySelector(".plo-detail-panel-toggle-all")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// destroyDetailPanel
// ---------------------------------------------------------------------------
describe("destroyDetailPanel", () => {
  test("removes panel from container", () => {
    setBody("<div id='host'></div>");
    const host = document.getElementById("host");
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    host.appendChild(panel);

    expect(host.querySelector(".plo-detail-panel")).not.toBeNull();
    destroyDetailPanel(host);
    expect(host.querySelector(".plo-detail-panel")).toBeNull();
  });

  test("is safe to call when no panel exists", () => {
    setBody("<div id='host'></div>");
    const host = document.getElementById("host");
    expect(() => destroyDetailPanel(host)).not.toThrow();
  });
});
