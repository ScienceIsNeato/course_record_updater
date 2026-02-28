const { setBody } = require("../helpers/dom");

// plo_dashboard.js reads DOM on init via DOMContentLoaded — set up minimal DOM
// before requiring so the IIFE doesn't crash.
beforeAll(() => {
  setBody(`
    <select id="ploTermFilter"></select>
    <select id="ploProgramFilter"></select>
    <button id="ploRefreshBtn"></button>
    <div id="ploTreeContainer"></div>
    <span id="statPrograms"></span>
    <span id="statPlos"></span>
    <span id="statMappedClos"></span>
    <span id="statWithData"></span>
    <span id="statMissingData"></span>
  `);

  // Stub fetch so init() doesn't make real HTTP calls
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ success: true, data: [] }),
  });
});

const {
  formatAssessment,
  statusBadgeHtml,
  renderEmptyState,
  renderProgramCard,
  renderPloItem,
  renderCloTable,
  escapeHtml,
  csrfToken,
  fetchJson,
  showLoading,
  renderSummary,
  renderTree,
  attachTreeListeners,
  loadFilters,
  loadTree,
  init,
  _setDomRefs,
} = require("../../../static/plo_dashboard");

// ---------------------------------------------------------------------------
// escapeHtml
// ---------------------------------------------------------------------------

describe("escapeHtml", () => {
  it("escapes HTML special characters", () => {
    expect(escapeHtml("<script>alert('xss')</script>")).not.toContain(
      "<script>"
    );
  });

  it("passes plain text through", () => {
    expect(escapeHtml("Hello World")).toBe("Hello World");
  });

  it("handles empty string", () => {
    expect(escapeHtml("")).toBe("");
  });
});

// ---------------------------------------------------------------------------
// formatAssessment
// ---------------------------------------------------------------------------

describe("formatAssessment", () => {
  // Percentage mode (default)
  describe("percentage mode", () => {
    it('returns "N/A" when took is null', () => {
      const result = formatAssessment(null, null, "percentage");
      expect(result.text).toBe("N/A");
      expect(result.cssClass).toBe("rate-na");
    });

    it('returns "N/A" when took is 0', () => {
      const result = formatAssessment(0, 0, "percentage");
      expect(result.text).toBe("N/A");
      expect(result.cssClass).toBe("rate-na");
    });

    it("returns percentage string for valid data", () => {
      const result = formatAssessment(100, 85, "percentage");
      expect(result.text).toBe("85%");
      expect(result.cssClass).toBe("rate-high");
    });

    it("rate-high for >= 80%", () => {
      expect(formatAssessment(10, 8, "percentage").cssClass).toBe("rate-high");
      expect(formatAssessment(10, 10, "percentage").cssClass).toBe("rate-high");
    });

    it("rate-mid for 60-79%", () => {
      expect(formatAssessment(10, 7, "percentage").cssClass).toBe("rate-mid");
      expect(formatAssessment(10, 6, "percentage").cssClass).toBe("rate-mid");
    });

    it("rate-low for < 60%", () => {
      expect(formatAssessment(10, 5, "percentage").cssClass).toBe("rate-low");
      expect(formatAssessment(10, 1, "percentage").cssClass).toBe("rate-low");
    });

    it("rounds to nearest integer", () => {
      expect(formatAssessment(100, 78, "percentage").text).toBe("78%");
      expect(formatAssessment(3, 2, "percentage").text).toBe("67%");
    });
  });

  // Binary mode
  describe("binary mode", () => {
    it('returns "S" when pass rate >= 70%', () => {
      expect(formatAssessment(10, 7, "binary").text).toBe("S");
    });

    it('returns "U" when pass rate < 70%', () => {
      expect(formatAssessment(10, 6, "binary").text).toBe("U");
    });

    it('returns "N/A" for null data', () => {
      expect(formatAssessment(null, null, "binary").text).toBe("N/A");
    });

    it("uses correct css class based on percentage", () => {
      expect(formatAssessment(10, 9, "binary").cssClass).toBe("rate-high");
      expect(formatAssessment(10, 5, "binary").cssClass).toBe("rate-low");
    });
  });

  // Both mode
  describe("both mode", () => {
    it('returns "S (78%)" format for passing rate', () => {
      expect(formatAssessment(100, 78, "both").text).toBe("S (78%)");
    });

    it('returns "U (54%)" format for failing rate', () => {
      expect(formatAssessment(100, 54, "both").text).toBe("U (54%)");
    });

    it('returns "N/A" for null data', () => {
      expect(formatAssessment(null, 5, "both").text).toBe("N/A");
    });

    it("threshold at exactly 70%", () => {
      expect(formatAssessment(10, 7, "both").text).toBe("S (70%)");
    });

    it("just below threshold", () => {
      expect(formatAssessment(100, 69, "both").text).toBe("U (69%)");
    });
  });

  // Edge cases
  describe("edge cases", () => {
    it("100% pass rate", () => {
      const result = formatAssessment(50, 50, "percentage");
      expect(result.text).toBe("100%");
      expect(result.cssClass).toBe("rate-high");
    });

    it("0% pass rate (took > 0)", () => {
      const result = formatAssessment(50, 0, "percentage");
      expect(result.text).toBe("0%");
      expect(result.cssClass).toBe("rate-low");
    });

    it("defaults to percentage for unknown mode", () => {
      expect(formatAssessment(10, 8, "unknown").text).toBe("80%");
    });

    it("treats null passed as 0 when took is valid", () => {
      const result = formatAssessment(30, null, "percentage");
      expect(result.text).toBe("0%");
      expect(result.cssClass).toBe("rate-low");
    });
  });
});

// ---------------------------------------------------------------------------
// statusBadgeHtml
// ---------------------------------------------------------------------------

describe("statusBadgeHtml", () => {
  it("renders approved badge with bg-success", () => {
    const html = statusBadgeHtml("approved");
    expect(html).toContain("bg-success");
    expect(html).toContain("approved");
  });

  it("renders submitted badge with bg-info", () => {
    const html = statusBadgeHtml("submitted");
    expect(html).toContain("bg-info");
    expect(html).toContain("submitted");
  });

  it("renders assigned badge with bg-secondary", () => {
    const html = statusBadgeHtml("assigned");
    expect(html).toContain("bg-secondary");
  });

  it("renders awaiting_approval as human readable", () => {
    const html = statusBadgeHtml("awaiting_approval");
    expect(html).toContain("awaiting approval");
    expect(html).toContain("bg-warning");
  });

  it("renders needs_rework badge", () => {
    const html = statusBadgeHtml("needs_rework");
    expect(html).toContain("bg-danger");
    expect(html).toContain("needs rework");
  });

  it("handles unknown status with bg-secondary", () => {
    const html = statusBadgeHtml("custom_status");
    expect(html).toContain("bg-secondary");
    expect(html).toContain("custom status");
  });

  it("handles null/undefined status", () => {
    const html = statusBadgeHtml(null);
    expect(html).toContain("unknown");
  });

  it("handles in_progress status", () => {
    const html = statusBadgeHtml("in_progress");
    expect(html).toContain("bg-primary");
  });

  it("handles unassigned status", () => {
    const html = statusBadgeHtml("unassigned");
    expect(html).toContain("bg-light");
  });
});

// ---------------------------------------------------------------------------
// renderEmptyState
// ---------------------------------------------------------------------------

describe("renderEmptyState", () => {
  it("renders with icon, title, and subtitle", () => {
    const html = renderEmptyState("fa-sitemap", "No Programs", "Add programs");
    expect(html).toContain("plo-empty-state");
    expect(html).toContain("fa-sitemap");
    expect(html).toContain("No Programs");
    expect(html).toContain("Add programs");
  });

  it("escapes HTML in title", () => {
    const html = renderEmptyState("fa-x", "<b>Bold</b>", "Sub");
    expect(html).not.toContain("<b>");
  });
});

// ---------------------------------------------------------------------------
// renderProgramCard
// ---------------------------------------------------------------------------

describe("renderProgramCard", () => {
  const prog = {
    id: "prog-1",
    name: "Biology",
    short_name: "BIOL",
    plo_count: 3,
    mapped_clo_count: 5,
    mapping_version: 1,
    plos: [],
  };

  it("renders program card with name and short name", () => {
    const html = renderProgramCard(prog);
    expect(html).toContain("BIOL");
    expect(html).toContain("Biology");
    expect(html).toContain("plo-program-card");
  });

  it("shows PLO and CLO count badges", () => {
    const html = renderProgramCard(prog);
    expect(html).toContain("3 PLOs");
    expect(html).toContain("5 CLOs");
  });

  it("shows version badge when mapping exists", () => {
    const html = renderProgramCard(prog);
    expect(html).toContain("v1");
    expect(html).toContain("bg-info");
  });

  it("shows 'No mapping' badge when no version", () => {
    const html = renderProgramCard({ ...prog, mapping_version: null });
    expect(html).toContain("No mapping");
    expect(html).toContain("bg-warning");
  });

  it("renders empty state when no PLOs", () => {
    const html = renderProgramCard({ ...prog, plos: [] });
    expect(html).toContain("No PLOs Defined");
  });

  it("renders PLO items when PLOs exist", () => {
    const progWithPlos = {
      ...prog,
      assessment_display_mode: "percentage",
      plos: [
        {
          id: "plo-1",
          plo_number: 1,
          description: "Critical thinking",
          mapped_clo_count: 2,
          mapped_clos: [],
        },
      ],
    };
    const html = renderProgramCard(progWithPlos);
    expect(html).toContain("plo-number");
    expect(html).toContain("Critical thinking");
  });
});

// ---------------------------------------------------------------------------
// renderPloItem
// ---------------------------------------------------------------------------

describe("renderPloItem", () => {
  const plo = {
    id: "plo-1",
    plo_number: 1,
    description: "Apply scientific reasoning",
    mapped_clo_count: 2,
    mapped_clos: [],
  };

  it("renders PLO number and description", () => {
    const html = renderPloItem(plo, "percentage");
    expect(html).toContain('plo-number">1</span>');
    expect(html).toContain("Apply scientific reasoning");
  });

  it("shows mapped CLO count badge", () => {
    const html = renderPloItem(plo, "percentage");
    expect(html).toContain("2 CLOs");
  });

  it("renders empty state when no mapped CLOs", () => {
    const html = renderPloItem(plo, "percentage");
    expect(html).toContain("No CLO Mappings");
  });

  it("renders CLO table when CLOs exist", () => {
    const ploWithClos = {
      ...plo,
      mapped_clos: [
        {
          id: "clo-1",
          clo_number: 1,
          description: "Test CLO",
          course_code: "BIOL-101",
          course_name: "Intro Biology",
          assessment_method: "exam",
          students_took: 30,
          students_passed: 25,
          status: "submitted",
          sections: [],
        },
      ],
    };
    const html = renderPloItem(ploWithClos, "percentage");
    expect(html).toContain("BIOL-101");
    expect(html).toContain("Test CLO");
  });
});

// ---------------------------------------------------------------------------
// renderCloTable
// ---------------------------------------------------------------------------

describe("renderCloTable", () => {
  const clos = [
    {
      id: "clo-1",
      clo_number: 1,
      description: "Explain the scientific method",
      course_code: "BIOL-101",
      course_name: "Intro Bio",
      assessment_method: "Exam",
      students_took: 30,
      students_passed: 25,
      status: "submitted",
      sections: [
        {
          section_number: "001",
          instructor_name: "Jane Doe",
          students_took: 30,
          students_passed: 25,
          assessment_tool: "Midterm",
          status: "submitted",
        },
      ],
    },
  ];

  it("renders table with correct headers", () => {
    const html = renderCloTable(clos, "percentage");
    expect(html).toContain("<table");
    expect(html).toContain("<th>CLO</th>");
    expect(html).toContain("Course");
    expect(html).toContain("Assessment");
    expect(html).toContain("Success");
    expect(html).toContain("Status");
  });

  it("renders CLO data in table row", () => {
    const html = renderCloTable(clos, "percentage");
    expect(html).toContain("BIOL-101");
    expect(html).toContain("Explain the scientific method");
    expect(html).toContain("Exam");
  });

  it("renders assessment in percentage mode", () => {
    const html = renderCloTable(clos, "percentage");
    expect(html).toContain("83%");
  });

  it("renders assessment in binary mode", () => {
    const html = renderCloTable(clos, "binary");
    // 25/30 = 83% >= 70% → "S"
    expect(html).toMatch(/\bS\b/);
  });

  it("renders assessment in both mode", () => {
    const html = renderCloTable(clos, "both");
    expect(html).toContain("S (83%)");
  });

  it("renders N/A for CLO without data", () => {
    const noDataClos = [
      {
        ...clos[0],
        students_took: null,
        students_passed: null,
        sections: [],
      },
    ];
    const html = renderCloTable(noDataClos, "percentage");
    expect(html).toContain("N/A");
    expect(html).toContain("rate-na");
  });

  it("renders section sub-rows", () => {
    const html = renderCloTable(clos, "percentage");
    expect(html).toContain("Section 001");
    expect(html).toContain("Jane Doe");
    expect(html).toContain("plo-section-row");
  });

  it("renders 'no section data' message when sections empty", () => {
    const emptySections = [{ ...clos[0], sections: [] }];
    const html = renderCloTable(emptySections, "percentage");
    expect(html).toContain("No section data");
  });

  it("renders status badge for CLO", () => {
    const html = renderCloTable(clos, "percentage");
    expect(html).toContain("plo-status-badge");
    expect(html).toContain("submitted");
  });

  it("renders section assessment data", () => {
    const html = renderCloTable(clos, "percentage");
    // Section: 25/30 = 83%
    const sectionRowMatch = html.match(/plo-section-row[\s\S]*?<\/tr>/);
    expect(sectionRowMatch).not.toBeNull();
    expect(sectionRowMatch[0]).toContain("83%");
  });
});

// ---------------------------------------------------------------------------
// DOM-dependent functions (require init() to set closure variables)
// ---------------------------------------------------------------------------

describe("DOM-dependent functions", () => {
  function setupDom() {
    setBody(`
      <select id="ploTermFilter"></select>
      <select id="ploProgramFilter"></select>
      <button id="ploRefreshBtn"></button>
      <div id="ploTreeContainer"></div>
      <span id="statPrograms"></span>
      <span id="statPlos"></span>
      <span id="statMappedClos"></span>
      <span id="statWithData"></span>
      <span id="statMissingData"></span>
    `);
    // Add meta tag for csrfToken tests
    const existing = document.querySelector('meta[name="csrf-token"]');
    if (existing) existing.remove();
    const meta = document.createElement("meta");
    meta.setAttribute("name", "csrf-token");
    meta.setAttribute("content", "test-csrf-token");
    document.head.appendChild(meta);
    _setDomRefs();
  }

  beforeEach(() => {
    setupDom();
  });

  describe("csrfToken", () => {
    it("returns meta tag content", () => {
      expect(csrfToken()).toBe("test-csrf-token");
    });

    it("returns empty string when no meta tag", () => {
      const meta = document.querySelector('meta[name="csrf-token"]');
      meta.remove();
      expect(csrfToken()).toBe("");
      // Restore for other tests
      const newMeta = document.createElement("meta");
      newMeta.setAttribute("name", "csrf-token");
      newMeta.setAttribute("content", "test-csrf-token");
      document.body.appendChild(newMeta);
    });
  });

  describe("showLoading", () => {
    it("renders loading spinner in tree container", () => {
      showLoading();
      const container = document.getElementById("ploTreeContainer");
      expect(container.innerHTML).toContain("spinner-border");
      expect(container.innerHTML).toContain("Loading");
    });
  });

  describe("renderSummary", () => {
    it("updates stat elements with summary data", () => {
      renderSummary({
        total_programs: 5,
        total_plos: 12,
        total_mapped_clos: 30,
        clos_with_data: 25,
        clos_missing_data: 5,
      });
      expect(document.getElementById("statPrograms").textContent).toBe("5");
      expect(document.getElementById("statPlos").textContent).toBe("12");
      expect(document.getElementById("statMappedClos").textContent).toBe("30");
      expect(document.getElementById("statWithData").textContent).toBe("25");
      expect(document.getElementById("statMissingData").textContent).toBe("5");
    });
  });

  describe("renderTree", () => {
    it("renders empty state when no programs", () => {
      renderTree({
        programs: [],
        summary: {
          total_programs: 0,
          total_plos: 0,
          total_mapped_clos: 0,
          clos_with_data: 0,
          clos_missing_data: 0,
        },
      });
      const container = document.getElementById("ploTreeContainer");
      expect(container.innerHTML).toContain("plo-empty-state");
      expect(container.innerHTML).toContain("No Programs Found");
    });

    it("renders program cards when data exists", () => {
      renderTree({
        programs: [
          {
            id: "prog-1",
            name: "Biology",
            short_name: "BIOL",
            plo_count: 3,
            mapped_clo_count: 5,
            mapping_version: 1,
            plos: [],
          },
        ],
        summary: {
          total_programs: 1,
          total_plos: 3,
          total_mapped_clos: 5,
          clos_with_data: 4,
          clos_missing_data: 1,
        },
      });
      const container = document.getElementById("ploTreeContainer");
      expect(container.innerHTML).toContain("plo-program-card");
      expect(container.innerHTML).toContain("Biology");
    });
  });

  describe("fetchJson", () => {
    it("returns parsed JSON on success", async () => {
      const mockData = { success: true, data: [1, 2, 3] };
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => mockData,
      });
      const result = await fetchJson("/api/test");
      expect(result).toEqual(mockData);
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/test",
        expect.objectContaining({
          headers: expect.objectContaining({ Accept: "application/json" }),
        }),
      );
    });

    it("throws on HTTP error", async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 500,
      });
      await expect(fetchJson("/api/fail")).rejects.toThrow("HTTP 500");
    });
  });

  describe("loadFilters", () => {
    it("populates term dropdown with active term selected", async () => {
      global.fetch = jest
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            terms: [
              { id: "t1", name: "Spring 2025", start_date: "2025-01-15" },
              {
                id: "t2",
                name: "Fall 2025",
                start_date: "2025-08-20",
                status: "active",
              },
            ],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ programs: [] }),
        });

      await loadFilters();

      const sel = document.getElementById("ploTermFilter");
      expect(sel.children.length).toBe(2);
      // opt.selected = true sets the property, not the HTML attribute
      const selected = Array.from(sel.options).find((o) => o.selected);
      expect(selected).toBeDefined();
      expect(selected.textContent).toBe("Fall 2025");
    });

    it("shows 'No terms available' when empty", async () => {
      global.fetch = jest
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ terms: [] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ programs: [] }),
        });

      await loadFilters();

      const sel = document.getElementById("ploTermFilter");
      expect(sel.innerHTML).toContain("No terms available");
    });

    it("handles fetch error for terms gracefully", async () => {
      const consoleSpy = jest.spyOn(console, "error").mockImplementation();
      global.fetch = jest
        .fn()
        .mockRejectedValueOnce(new Error("Network error"))
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ programs: [] }),
        });

      await loadFilters();

      const sel = document.getElementById("ploTermFilter");
      expect(sel.innerHTML).toContain("Failed to load terms");
      consoleSpy.mockRestore();
    });

    it("populates program dropdown", async () => {
      global.fetch = jest
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            terms: [{ id: "t1", name: "Fall 2025", status: "active" }],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            programs: [
              { id: "p1", name: "Biology", short_name: "BIOL" },
              { id: "p2", name: "Chemistry", short_name: "CHEM" },
            ],
          }),
        });

      await loadFilters();

      const sel = document.getElementById("ploProgramFilter");
      // "All Programs" + 2 programs
      expect(sel.children.length).toBe(3);
      expect(sel.innerHTML).toContain("All Programs");
      expect(sel.innerHTML).toContain("BIOL");
    });

    it("falls back to most recent term if none active", async () => {
      global.fetch = jest
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            terms: [
              { id: "t1", name: "Spring 2025", start_date: "2025-01-15" },
              { id: "t2", name: "Fall 2025", start_date: "2025-08-20" },
            ],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ programs: [] }),
        });

      await loadFilters();

      const sel = document.getElementById("ploTermFilter");
      // After sorting descending by start_date, t2 (Fall 2025) is first
      const selected = Array.from(sel.options).find((o) => o.selected);
      expect(selected).toBeDefined();
      expect(selected.value).toBe("t2");
    });
  });

  describe("loadTree", () => {
    it("renders tree data on success", async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          data: {
            programs: [
              {
                id: "prog-1",
                name: "Biology",
                short_name: "BIOL",
                plo_count: 2,
                mapped_clo_count: 3,
                mapping_version: 1,
                plos: [],
              },
            ],
            summary: {
              total_programs: 1,
              total_plos: 2,
              total_mapped_clos: 3,
              clos_with_data: 2,
              clos_missing_data: 1,
            },
          },
        }),
      });

      await loadTree();

      const container = document.getElementById("ploTreeContainer");
      expect(container.innerHTML).toContain("Biology");
    });

    it("shows error on fetch failure", async () => {
      const consoleSpy = jest.spyOn(console, "error").mockImplementation();
      global.fetch = jest.fn().mockRejectedValue(new Error("Network error"));

      await loadTree();

      const container = document.getElementById("ploTreeContainer");
      expect(container.innerHTML).toContain("alert-danger");
      expect(container.innerHTML).toContain("Failed to load PLO data");
      consoleSpy.mockRestore();
    });

    it("shows error when success is false", async () => {
      const consoleSpy = jest.spyOn(console, "error").mockImplementation();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ success: false, error: "Not authorized" }),
      });

      await loadTree();

      const container = document.getElementById("ploTreeContainer");
      expect(container.innerHTML).toContain("Failed to load PLO data");
      consoleSpy.mockRestore();
    });
  });

  describe("attachTreeListeners", () => {
    it("toggles program body on click", () => {
      const container = document.getElementById("ploTreeContainer");
      container.innerHTML =
        '<div data-toggle="program">Header</div>' +
        '<div class="body">Body Content</div>';
      attachTreeListeners();

      const toggle = container.querySelector('[data-toggle="program"]');
      const body = toggle.nextElementSibling;

      toggle.click();
      expect(body.style.display).toBe("none");

      toggle.click();
      expect(body.style.display).toBe("");
    });

    it("toggles PLO body on click", () => {
      const container = document.getElementById("ploTreeContainer");
      container.innerHTML =
        '<div data-toggle="plo"><i class="plo-expand-icon"></i></div>' +
        '<div class="plo-body">PLO Content</div>';
      attachTreeListeners();

      const toggle = container.querySelector('[data-toggle="plo"]');
      const body = toggle.nextElementSibling;
      const icon = toggle.querySelector(".plo-expand-icon");

      toggle.click();
      expect(body.style.display).toBe("none");
      expect(icon.classList.contains("expanded")).toBe(false);

      toggle.click();
      expect(body.style.display).toBe("");
      expect(icon.classList.contains("expanded")).toBe(true);
    });

    it("toggles CLO section rows on click", () => {
      const container = document.getElementById("ploTreeContainer");
      container.innerHTML =
        "<table><tbody>" +
        '<tr data-toggle="clo" data-clo-id="clo-1"><td>CLO</td></tr>' +
        '<tr data-parent-clo="clo-1" style="display:none"><td>Section</td></tr>' +
        "</tbody></table>";
      attachTreeListeners();

      const toggle = container.querySelector('[data-toggle="clo"]');
      const sectionRow = container.querySelector('[data-parent-clo="clo-1"]');

      toggle.click();
      expect(toggle.classList.contains("expanded")).toBe(true);
      expect(sectionRow.style.display).toBe("");

      toggle.click();
      expect(toggle.classList.contains("expanded")).toBe(false);
      expect(sectionRow.style.display).toBe("none");
    });
  });

  describe("init", () => {
    it("does not crash when treeContainer is missing", () => {
      setBody("<div></div>");
      expect(() => init()).not.toThrow();
    });

    it("sets up and calls fetch when DOM elements exist", () => {
      setupDom();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          terms: [],
          programs: [],
          data: {
            programs: [],
            summary: {
              total_programs: 0,
              total_plos: 0,
              total_mapped_clos: 0,
              clos_with_data: 0,
              clos_missing_data: 0,
            },
          },
        }),
      });

      expect(() => init()).not.toThrow();
      expect(global.fetch).toHaveBeenCalled();
    });
  });
});
