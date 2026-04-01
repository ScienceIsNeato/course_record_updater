/**
 * Unit tests for static/plo_detail_panel.js (RED — module doesn't exist yet).
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

// ---------------------------------------------------------------------------
// createDetailPanel — container structure
// ---------------------------------------------------------------------------
describe("createDetailPanel — container", () => {
  test("returns a div.plo-detail-panel", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    expect(panel.tagName).toBe("DIV");
    expect(panel.classList.contains("plo-detail-panel")).toBe(true);
  });

  test("panel has entering animation class", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
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

  test("CLO row shows aggregate pass rate", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const firstClo = panel.querySelector(".plo-detail-clo");
    expect(firstClo.textContent).toContain("80%");
  });

  test("CLO row is collapsible — starts collapsed", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const firstClo = panel.querySelector(".plo-detail-clo");
    expect(firstClo.classList.contains("expanded")).toBe(false);
  });

  test("clicking CLO header expands it", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const firstClo = panel.querySelector(".plo-detail-clo");
    const header = firstClo.querySelector(".plo-detail-clo-header");
    header.click();
    expect(firstClo.classList.contains("expanded")).toBe(true);
  });

  test("clicking expanded CLO header collapses it", () => {
    const panel = createDetailPanel(MOCK_PLO_DATA, MOCK_TERM_LABEL);
    const firstClo = panel.querySelector(".plo-detail-clo");
    const header = firstClo.querySelector(".plo-detail-clo-header");
    header.click(); // expand
    header.click(); // collapse
    expect(firstClo.classList.contains("expanded")).toBe(false);
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
