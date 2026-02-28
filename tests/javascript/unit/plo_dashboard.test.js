const { setBody } = require("../helpers/dom");

// plo_dashboard.js reads DOM on init via DOMContentLoaded — set up minimal DOM
// before requiring so the IIFE doesn't crash.
beforeAll(() => {
  setBody(`
    <select id="ploTermFilter"></select>
    <select id="ploProgramFilter"></select>
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
  postJson,
  getDisplayMode,
  showLoading,
  renderSummary,
  renderTree,
  attachTreeListeners,
  loadFilters,
  loadTree,
  init,
  _setDomRefs,
  showMapCloAlert,
  hideMapCloAlert,
  renderPickerPanel,
  moveCheckedItems,
  updatePickerCounts,
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
// postJson
// ---------------------------------------------------------------------------

describe("postJson", () => {
  it("is exported as a function", () => {
    expect(typeof postJson).toBe("function");
  });
});

// ---------------------------------------------------------------------------
// getDisplayMode
// ---------------------------------------------------------------------------

describe("getDisplayMode", () => {
  it("returns 'percentage' as default when no select element", () => {
    setBody(""); // clear DOM so displayModeSelect is null
    _setDomRefs();
    expect(getDisplayMode()).toBe("percentage");
  });

  it("returns selected value when DOM element exists", () => {
    setBody(`
      <select id="ploDisplayMode">
        <option value="both">Both</option>
        <option value="percentage" selected>Percentage</option>
        <option value="binary">Binary</option>
      </select>
    `);
    _setDomRefs();
    expect(getDisplayMode()).toBe("percentage");
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
    expect(html).toContain("Score");
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
      <div id="ploTreeContainer"></div>
      <span id="statPrograms"></span>
      <span id="statPlos"></span>
      <span id="statMappedClos"></span>
      <span id="statWithData"></span>
      <span id="statMissingData"></span>
      <select id="ploDisplayMode"><option value="both">Both</option><option value="percentage">Percentage</option><option value="binary">Binary</option></select>
      <button id="createPloBtn"></button>
      <button id="mapCloBtn"></button>
      <button id="expandAllBtn"></button>
      <button id="collapseAllBtn"></button>
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

  // -------------------------------------------------------------------------
  // Map CLO to PLO modal (cherry picker)
  // -------------------------------------------------------------------------

  describe("Map CLO to PLO modal", () => {
    /**
     * Set up DOM with the mapping modal elements matching the template IDs
     * (mapCloModalProgram, mapCloModalPlo, cherry picker panels, etc.).
     */
    function setupMapCloModalDom() {
      setBody(`
        <select id="ploTermFilter"></select>
        <select id="ploProgramFilter">
          <option value="prog-1">Biology</option>
          <option value="prog-2">Zoology</option>
        </select>
        <div id="ploTreeContainer"></div>
        <span id="statPrograms"></span>
        <span id="statPlos"></span>
        <span id="statMappedClos"></span>
        <span id="statWithData"></span>
        <span id="statMissingData"></span>
        <select id="ploDisplayMode"><option value="both">Both</option></select>
        <button id="createPloBtn"></button>
        <button id="mapCloBtn"></button>
        <button id="expandAllBtn"></button>
        <button id="collapseAllBtn"></button>

        <!-- Map CLO to PLO Modal -->
        <div id="mapCloModal">
          <select id="mapCloModalProgram">
            <option value="">Select a program…</option>
          </select>
          <select id="mapCloModalPlo">
            <option value="">Select a PLO…</option>
          </select>
          <div id="mapCloPickerContainer" style="display:none;">
            <div class="list-group list-group-flush" id="mappedCloList"></div>
            <button type="button" id="moveCloLeft"></button>
            <button type="button" id="moveCloRight"></button>
            <div class="list-group list-group-flush" id="availableCloList"></div>
            <span id="mappedCloCount">0</span>
            <span id="availableCloCount">0</span>
          </div>
          <div id="mapCloModalAlert" class="alert d-none"></div>
          <button type="button" id="mapCloSaveBtn">Save Mappings</button>
          <button type="button" id="mapCloPublishBtn">Publish Draft</button>
        </div>
      `);
      const existing = document.querySelector('meta[name="csrf-token"]');
      if (existing) existing.remove();
      const meta = document.createElement("meta");
      meta.setAttribute("name", "csrf-token");
      meta.setAttribute("content", "test-csrf-token");
      document.head.appendChild(meta);
    }

    it("populates program dropdown from filter when modal opens", () => {
      setupMapCloModalDom();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, terms: [], programs: [], data: { programs: [], summary: { total_programs: 0, total_plos: 0, total_mapped_clos: 0, clos_with_data: 0, clos_missing_data: 0 } } }),
      });
      // Mock bootstrap.Modal
      const mockShow = jest.fn();
      global.bootstrap = { Modal: jest.fn(() => ({ show: mockShow })) };

      init();

      const mapBtn = document.getElementById("mapCloBtn");
      mapBtn.click();

      const programDropdown = document.getElementById("mapCloModalProgram");
      const options = Array.from(programDropdown.options);
      // Should have the two programs from ploProgramFilter
      expect(options.length).toBe(2);
      expect(options[0].value).toBe("prog-1");
      expect(options[0].textContent).toBe("Biology");
      expect(options[1].value).toBe("prog-2");
      expect(options[1].textContent).toBe("Zoology");
    });

    it("auto-fetches PLOs when modal opens with pre-selected program", async () => {
      setupMapCloModalDom();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, terms: [], programs: [], plos: [
          { id: "plo-new", plo_number: 1, description: "New PLO" },
        ], data: { programs: [], summary: { total_programs: 0, total_plos: 0, total_mapped_clos: 0, clos_with_data: 0, clos_missing_data: 0 } } }),
      });
      global.bootstrap = { Modal: jest.fn(() => ({ show: jest.fn() })) };
      init();

      const mapBtn = document.getElementById("mapCloBtn");
      mapBtn.click();

      // Wait for the auto-triggered PLO fetch
      await new Promise((r) => setTimeout(r, 50));

      const ploDropdown = document.getElementById("mapCloModalPlo");
      const realOptions = Array.from(ploDropdown.options).filter((o) => o.value !== "");
      expect(realOptions.length).toBeGreaterThanOrEqual(1);
      expect(realOptions[0].value).toBe("plo-new");
    });

    it("loads PLOs when program is selected", async () => {
      setupMapCloModalDom();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, terms: [], programs: [], plos: [], data: { programs: [], summary: { total_programs: 0, total_plos: 0, total_mapped_clos: 0, clos_with_data: 0, clos_missing_data: 0 } } }),
      });
      global.bootstrap = { Modal: jest.fn(() => ({ show: jest.fn() })) };
      init();

      // Simulate selecting a program — add a real option and select it
      const programDropdown = document.getElementById("mapCloModalProgram");
      programDropdown.innerHTML =
        '<option value="">Select…</option>' +
        '<option value="prog-1">Biology</option>';
      programDropdown.value = "prog-1";

      // Set up fetch to return PLOs for this call
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          plos: [
            { id: "plo-1", plo_number: 1, description: "PLO One" },
            { id: "plo-2", plo_number: 2, description: "PLO Two" },
          ],
        }),
      });

      programDropdown.dispatchEvent(new Event("change"));

      // Wait for async fetch
      await new Promise((r) => setTimeout(r, 50));

      // PLO dropdown should be populated
      const ploDropdown = document.getElementById("mapCloModalPlo");
      const ploOptions = Array.from(ploDropdown.options);
      expect(ploOptions.length).toBeGreaterThanOrEqual(2);
      // First option might be placeholder, real options follow
      const realOptions = ploOptions.filter((o) => o.value !== "");
      expect(realOptions.length).toBe(2);
      expect(realOptions[0].value).toBe("plo-1");
    });

    it("loads cherry picker panels when PLO is selected", async () => {
      setupMapCloModalDom();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, terms: [], programs: [], data: { programs: [], summary: { total_programs: 0, total_plos: 0, total_mapped_clos: 0, clos_with_data: 0, clos_missing_data: 0 } } }),
      });
      global.bootstrap = { Modal: jest.fn(() => ({ show: jest.fn() })) };
      init();

      // Set program value so the handler knows which program
      const programDropdown = document.getElementById("mapCloModalProgram");
      programDropdown.innerHTML = '<option value="prog-1">Biology</option>';
      programDropdown.value = "prog-1";

      // Set up fetch to return clo-picker data
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          mapped: [
            { outcome_id: "clo-1", clo_number: 1, description: "CLO One", course: { course_number: "BIO-101" } },
          ],
          available: [
            { outcome_id: "clo-2", clo_number: 2, description: "CLO Two", course: { course_number: "BIO-201" } },
          ],
          course_count: 2,
          total_clo_count: 2,
        }),
      });

      const ploDropdown = document.getElementById("mapCloModalPlo");
      ploDropdown.innerHTML =
        '<option value="">Select a PLO…</option>' +
        '<option value="plo-1">PLO 1</option>';
      ploDropdown.value = "plo-1";
      ploDropdown.dispatchEvent(new Event("change"));

      await new Promise((r) => setTimeout(r, 50));

      // Cherry picker should be visible
      const picker = document.getElementById("mapCloPickerContainer");
      expect(picker.style.display).toBe("");

      // Mapped panel should have 1 CLO
      const mappedItems = document.querySelectorAll('#mappedCloList input[type="checkbox"]');
      expect(mappedItems.length).toBe(1);
      expect(mappedItems[0].value).toBe("clo-1");

      // Available panel should have 1 CLO
      const availableItems = document.querySelectorAll('#availableCloList input[type="checkbox"]');
      expect(availableItems.length).toBe(1);
      expect(availableItems[0].value).toBe("clo-2");
    });

    it("saves mappings via PUT when save button is clicked", async () => {
      setupMapCloModalDom();
      global.bootstrap = {
        Modal: jest.fn(() => ({ show: jest.fn() })),
      };
      global.bootstrap.Modal.getInstance = jest.fn(() => ({ hide: jest.fn() }));

      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, terms: [], programs: [], data: { programs: [], summary: { total_programs: 0, total_plos: 0, total_mapped_clos: 0, clos_with_data: 0, clos_missing_data: 0 } } }),
      });
      init();

      // Set up the dropdowns with values
      const programDropdown = document.getElementById("mapCloModalProgram");
      programDropdown.innerHTML = '<option value="prog-1">Biology</option>';
      programDropdown.value = "prog-1";

      const ploDropdown = document.getElementById("mapCloModalPlo");
      ploDropdown.innerHTML = '<option value="plo-1">PLO 1</option>';
      ploDropdown.value = "plo-1";

      // Populate the mapped panel with CLOs
      renderPickerPanel("mappedCloList", [
        { outcome_id: "clo-1", clo_number: 1, description: "CLO One", course: { course_number: "BIO-101" } },
        { outcome_id: "clo-3", clo_number: 3, description: "CLO Three", course: { course_number: "BIO-301" } },
      ]);

      // Mock fetch for save + tree reload
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          mapping: { id: "draft-1", status: "draft" },
          data: { programs: [], summary: { total_programs: 0, total_plos: 0, total_mapped_clos: 0, clos_with_data: 0, clos_missing_data: 0 } },
        }),
      });

      const saveBtn = document.getElementById("mapCloSaveBtn");
      saveBtn.click();

      await new Promise((r) => setTimeout(r, 100));

      // Should have made a PUT call to clo-mappings
      const putCalls = global.fetch.mock.calls.filter(
        (call) => call[1] && call[1].method === "PUT"
      );
      expect(putCalls.length).toBe(1);
      expect(putCalls[0][0]).toContain("/clo-mappings");

      // Body should contain both CLO IDs
      const body = JSON.parse(putCalls[0][1].body);
      expect(body.clo_ids).toContain("clo-1");
      expect(body.clo_ids).toContain("clo-3");
    });

    it("publish draft button calls publish endpoint", async () => {
      setupMapCloModalDom();
      const mockHide = jest.fn();
      global.bootstrap = {
        Modal: jest.fn(() => ({ show: jest.fn() })),
      };
      global.bootstrap.Modal.getInstance = jest.fn(() => ({ hide: mockHide }));

      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, terms: [], programs: [], data: { programs: [], summary: { total_programs: 0, total_plos: 0, total_mapped_clos: 0, clos_with_data: 0, clos_missing_data: 0 } } }),
      });
      init();

      // Set up program
      const programDropdown = document.getElementById("mapCloModalProgram");
      programDropdown.innerHTML = '<option value="prog-1">Biology</option>';
      programDropdown.value = "prog-1";

      // Mock fetch for draft retrieval + publish
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          mapping: { id: "draft-1", status: "draft" },
          data: { programs: [], summary: { total_programs: 0, total_plos: 0, total_mapped_clos: 0, clos_with_data: 0, clos_missing_data: 0 } },
        }),
      });

      const publishBtn = document.getElementById("mapCloPublishBtn");
      publishBtn.click();

      await new Promise((r) => setTimeout(r, 100));

      // Should have made POST calls for publish
      const postCalls = global.fetch.mock.calls.filter(
        (call) => call[1] && call[1].method === "POST"
      );
      expect(postCalls.length).toBeGreaterThanOrEqual(1);
      // At least one call should contain "publish" in the URL
      const publishCalls = global.fetch.mock.calls.filter(
        (call) => typeof call[0] === "string" && call[0].includes("publish")
      );
      expect(publishCalls.length).toBeGreaterThanOrEqual(1);
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

  describe("postJson", () => {
    it("sends POST request with JSON body and CSRF token", async () => {
      setupDom();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, id: 42 }),
      });

      const result = await postJson("/api/test", { name: "hello" });
      expect(result.success).toBe(true);
      expect(result.id).toBe(42);
      expect(global.fetch).toHaveBeenCalledWith("/api/test", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRFToken": "test-csrf-token",
        },
        body: '{"name":"hello"}',
      });
    });

    it("throws on HTTP error", async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 400,
      });

      await expect(postJson("/api/test", {})).rejects.toThrow("HTTP 400");
    });
  });

  describe("expand and collapse all", () => {
    it("expand all shows all collapsible bodies and adds expanded class to icons", () => {
      setupDom();
      const container = document.getElementById("ploTreeContainer");
      container.innerHTML =
        '<div class="plo-program-body" style="display:none;">A</div>' +
        '<div class="plo-item-body" style="display:none;">B</div>' +
        '<i class="fas plo-expand-icon"></i>' +
        '<i class="fas plo-expand-icon"></i>';

      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, terms: [], programs: [], data: { programs: [], summary: { total_programs: 0, total_plos: 0, total_mapped_clos: 0, clos_with_data: 0, clos_missing_data: 0 } } }),
      });
      init();

      const expandBtn = document.getElementById("expandAllBtn");
      expandBtn.click();

      container.querySelectorAll(".plo-program-body").forEach((el) => {
        expect(el.style.display).toBe("");
      });
      container.querySelectorAll(".plo-item-body").forEach((el) => {
        expect(el.style.display).toBe("");
      });
      container.querySelectorAll(".plo-expand-icon").forEach((el) => {
        expect(el.classList.contains("expanded")).toBe(true);
      });
    });

    it("collapse all hides all collapsible bodies and removes expanded class", () => {
      setupDom();
      const container = document.getElementById("ploTreeContainer");
      container.innerHTML =
        '<div class="plo-program-body">A</div>' +
        '<div class="plo-item-body">B</div>' +
        '<div class="plo-section-row">S</div>' +
        '<div data-toggle="clo" class="expanded">C</div>' +
        '<i class="fas plo-expand-icon expanded"></i>' +
        '<i class="fas plo-expand-icon expanded"></i>';

      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, terms: [], programs: [], data: { programs: [], summary: { total_programs: 0, total_plos: 0, total_mapped_clos: 0, clos_with_data: 0, clos_missing_data: 0 } } }),
      });
      init();

      const collapseBtn = document.getElementById("collapseAllBtn");
      collapseBtn.click();

      container.querySelectorAll(".plo-program-body").forEach((el) => {
        expect(el.style.display).toBe("none");
      });
      container.querySelectorAll(".plo-item-body").forEach((el) => {
        expect(el.style.display).toBe("none");
      });
      container.querySelectorAll(".plo-section-row").forEach((el) => {
        expect(el.style.display).toBe("none");
      });
      container.querySelectorAll(".plo-expand-icon").forEach((el) => {
        expect(el.classList.contains("expanded")).toBe(false);
      });
      container.querySelectorAll('[data-toggle="clo"]').forEach((el) => {
        expect(el.classList.contains("expanded")).toBe(false);
      });
    });
  });

  describe("display mode change", () => {
    it("triggers loadTree when display mode changes", () => {
      setupDom();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, terms: [], programs: [], data: { programs: [], summary: { total_programs: 0, total_plos: 0, total_mapped_clos: 0, clos_with_data: 0, clos_missing_data: 0 } } }),
      });
      init();
      const callsBefore = global.fetch.mock.calls.length;

      const modeSelect = document.getElementById("ploDisplayMode");
      modeSelect.value = "binary";
      modeSelect.dispatchEvent(new Event("change"));

      // fetch should have been called again for the tree reload
      expect(global.fetch.mock.calls.length).toBeGreaterThan(callsBefore);
    });
  });

  // -------------------------------------------------------------------------
  // showMapCloAlert / hideMapCloAlert
  // -------------------------------------------------------------------------

  describe("showMapCloAlert / hideMapCloAlert", () => {
    beforeEach(() => {
      setBody('<div id="mapCloModalAlert" class="alert d-none"></div>');
    });

    it("shows an info alert with the given message", () => {
      showMapCloAlert("Hello world", "info");
      const el = document.getElementById("mapCloModalAlert");
      expect(el.textContent).toBe("Hello world");
      expect(el.className).toBe("alert alert-info");
    });

    it("shows a warning alert", () => {
      showMapCloAlert("Warning!", "warning");
      const el = document.getElementById("mapCloModalAlert");
      expect(el.className).toBe("alert alert-warning");
    });

    it("defaults to info when type is omitted", () => {
      showMapCloAlert("Default type");
      const el = document.getElementById("mapCloModalAlert");
      expect(el.className).toBe("alert alert-info");
    });

    it("hideMapCloAlert resets the alert to hidden", () => {
      showMapCloAlert("Visible", "danger");
      hideMapCloAlert();
      const el = document.getElementById("mapCloModalAlert");
      expect(el.className).toBe("alert d-none");
      expect(el.textContent).toBe("");
    });

    it("does not throw when alert element is missing", () => {
      setBody("<div></div>");
      expect(() => showMapCloAlert("test", "info")).not.toThrow();
      expect(() => hideMapCloAlert()).not.toThrow();
    });
  });

  // -------------------------------------------------------------------------
  // Map CLO modal — empty state diagnostics (cherry picker)
  // -------------------------------------------------------------------------

  describe("Map CLO modal — empty state diagnostics", () => {
    function setupMapCloModalDom() {
      setBody(`
        <select id="ploTermFilter"></select>
        <select id="ploProgramFilter">
          <option value="prog-1">Biology</option>
        </select>
        <div id="ploTreeContainer"></div>
        <span id="statPrograms"></span>
        <span id="statPlos"></span>
        <span id="statMappedClos"></span>
        <span id="statWithData"></span>
        <span id="statMissingData"></span>
        <select id="ploDisplayMode"><option value="both">Both</option></select>
        <button id="createPloBtn"></button>
        <button id="mapCloBtn"></button>
        <button id="expandAllBtn"></button>
        <button id="collapseAllBtn"></button>

        <div id="mapCloModal">
          <select id="mapCloModalProgram">
            <option value="">Select a program…</option>
          </select>
          <select id="mapCloModalPlo">
            <option value="">Select a PLO…</option>
          </select>
          <div id="mapCloPickerContainer" style="display:none;">
            <div class="list-group list-group-flush" id="mappedCloList"></div>
            <button type="button" id="moveCloLeft"></button>
            <button type="button" id="moveCloRight"></button>
            <div class="list-group list-group-flush" id="availableCloList"></div>
            <span id="mappedCloCount">0</span>
            <span id="availableCloCount">0</span>
          </div>
          <div id="mapCloModalAlert" class="alert d-none"></div>
          <button type="button" id="mapCloSaveBtn">Save Mappings</button>
          <button type="button" id="mapCloPublishBtn">Publish Draft</button>
        </div>
      `);
      const existing = document.querySelector('meta[name="csrf-token"]');
      if (existing) existing.remove();
      const meta = document.createElement("meta");
      meta.setAttribute("name", "csrf-token");
      meta.setAttribute("content", "test-csrf-token");
      document.head.appendChild(meta);
    }

    it("shows info alert when program has no PLOs", async () => {
      setupMapCloModalDom();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true, terms: [], programs: [],
          plos: [],
          data: { programs: [], summary: { total_programs: 0, total_plos: 0, total_mapped_clos: 0, clos_with_data: 0, clos_missing_data: 0 } },
        }),
      });
      global.bootstrap = { Modal: jest.fn(() => ({ show: jest.fn() })) };
      init();

      // Set program and trigger change
      const programDropdown = document.getElementById("mapCloModalProgram");
      programDropdown.innerHTML = '<option value="prog-1">Biology</option>';
      programDropdown.value = "prog-1";

      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, plos: [] }),
      });

      programDropdown.dispatchEvent(new Event("change"));
      await new Promise((r) => setTimeout(r, 50));

      const alert = document.getElementById("mapCloModalAlert");
      expect(alert.className).toContain("alert-info");
      expect(alert.textContent).toContain("No PLOs defined");
    });

    it("hides alert when program has PLOs", async () => {
      setupMapCloModalDom();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true, terms: [], programs: [],
          plos: [],
          data: { programs: [], summary: { total_programs: 0, total_plos: 0, total_mapped_clos: 0, clos_with_data: 0, clos_missing_data: 0 } },
        }),
      });
      global.bootstrap = { Modal: jest.fn(() => ({ show: jest.fn() })) };
      init();

      const programDropdown = document.getElementById("mapCloModalProgram");
      programDropdown.innerHTML = '<option value="prog-1">Biology</option>';
      programDropdown.value = "prog-1";

      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          plos: [{ id: "plo-1", plo_number: 1, description: "PLO One" }],
        }),
      });

      programDropdown.dispatchEvent(new Event("change"));
      await new Promise((r) => setTimeout(r, 50));

      const alert = document.getElementById("mapCloModalAlert");
      expect(alert.className).toContain("d-none");
    });

    it("shows warning when no courses linked to program", async () => {
      setupMapCloModalDom();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true, terms: [], programs: [], plos: [],
          data: { programs: [], summary: { total_programs: 0, total_plos: 0, total_mapped_clos: 0, clos_with_data: 0, clos_missing_data: 0 } },
        }),
      });
      global.bootstrap = { Modal: jest.fn(() => ({ show: jest.fn() })) };
      init();

      const programDropdown = document.getElementById("mapCloModalProgram");
      programDropdown.innerHTML = '<option value="prog-1">Biology</option>';
      programDropdown.value = "prog-1";

      const ploDropdown = document.getElementById("mapCloModalPlo");
      ploDropdown.innerHTML =
        '<option value="">Select a PLO…</option>' +
        '<option value="plo-1">PLO 1</option>';
      ploDropdown.value = "plo-1";

      // Return clo-picker data with course_count=0
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          mapped: [],
          available: [],
          course_count: 0,
          total_clo_count: 0,
        }),
      });

      ploDropdown.dispatchEvent(new Event("change"));
      await new Promise((r) => setTimeout(r, 50));

      const alert = document.getElementById("mapCloModalAlert");
      expect(alert.className).toContain("alert-warning");
      expect(alert.textContent).toContain("no courses linked");
    });

    it("shows info when courses have no CLOs defined", async () => {
      setupMapCloModalDom();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true, terms: [], programs: [], plos: [],
          data: { programs: [], summary: { total_programs: 0, total_plos: 0, total_mapped_clos: 0, clos_with_data: 0, clos_missing_data: 0 } },
        }),
      });
      global.bootstrap = { Modal: jest.fn(() => ({ show: jest.fn() })) };
      init();

      const programDropdown = document.getElementById("mapCloModalProgram");
      programDropdown.innerHTML = '<option value="prog-1">Biology</option>';
      programDropdown.value = "prog-1";

      const ploDropdown = document.getElementById("mapCloModalPlo");
      ploDropdown.innerHTML =
        '<option value="">Select a PLO…</option>' +
        '<option value="plo-1">PLO 1</option>';
      ploDropdown.value = "plo-1";

      // Courses exist but no CLOs
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          mapped: [],
          available: [],
          course_count: 3,
          total_clo_count: 0,
        }),
      });

      ploDropdown.dispatchEvent(new Event("change"));
      await new Promise((r) => setTimeout(r, 50));

      const alert = document.getElementById("mapCloModalAlert");
      expect(alert.className).toContain("alert-info");
      expect(alert.textContent).toContain("learning outcomes");
    });

    it("renders cherry picker when CLOs exist (no alert)", async () => {
      setupMapCloModalDom();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true, terms: [], programs: [], plos: [],
          data: { programs: [], summary: { total_programs: 0, total_plos: 0, total_mapped_clos: 0, clos_with_data: 0, clos_missing_data: 0 } },
        }),
      });
      global.bootstrap = { Modal: jest.fn(() => ({ show: jest.fn() })) };
      init();

      const programDropdown = document.getElementById("mapCloModalProgram");
      programDropdown.innerHTML = '<option value="prog-1">Biology</option>';
      programDropdown.value = "prog-1";

      const ploDropdown = document.getElementById("mapCloModalPlo");
      ploDropdown.innerHTML =
        '<option value="">Select a PLO…</option>' +
        '<option value="plo-1">PLO 1</option>';
      ploDropdown.value = "plo-1";

      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          mapped: [
            { outcome_id: "clo-1", clo_number: 1, description: "CLO", course: { course_number: "BIO-101" } },
          ],
          available: [],
          course_count: 1,
          total_clo_count: 1,
        }),
      });

      ploDropdown.dispatchEvent(new Event("change"));
      await new Promise((r) => setTimeout(r, 50));

      const alert = document.getElementById("mapCloModalAlert");
      expect(alert.className).toContain("d-none");

      // Cherry picker should be visible
      const picker = document.getElementById("mapCloPickerContainer");
      expect(picker.style.display).toBe("");
    });
  });

  // -------------------------------------------------------------------------
  // Cherry picker helper functions
  // -------------------------------------------------------------------------

  describe("renderPickerPanel", () => {
    beforeEach(() => {
      setBody('<div class="list-group" id="testList"></div>');
    });

    it("renders CLO items with checkboxes", () => {
      renderPickerPanel("testList", [
        { outcome_id: "clo-1", clo_number: 1, description: "First CLO", course: { course_number: "BIO-101" } },
        { outcome_id: "clo-2", clo_number: 2, description: "Second CLO", course: { course_number: "BIO-201" } },
      ]);

      const list = document.getElementById("testList");
      const checkboxes = list.querySelectorAll('input[type="checkbox"]');
      expect(checkboxes.length).toBe(2);
      expect(checkboxes[0].value).toBe("clo-1");
      expect(checkboxes[1].value).toBe("clo-2");
    });

    it("shows 'No CLOs' placeholder when list is empty", () => {
      renderPickerPanel("testList", []);

      const list = document.getElementById("testList");
      expect(list.textContent).toContain("No CLOs");
      expect(list.querySelectorAll('input[type="checkbox"]').length).toBe(0);
    });

    it("shows 'Mapped to another PLO' badge when mapped_to_plo_id is set", () => {
      renderPickerPanel("testList", [
        { outcome_id: "clo-1", clo_number: 1, description: "CLO One", course: { course_number: "BIO-101" }, mapped_to_plo_id: "plo-99" },
      ]);

      const list = document.getElementById("testList");
      const badge = list.querySelector(".badge.bg-warning");
      expect(badge).not.toBeNull();
      expect(badge.textContent).toContain("Mapped to another PLO");
    });

    it("does not crash when list element is missing", () => {
      expect(() => renderPickerPanel("nonExistent", [])).not.toThrow();
    });
  });

  describe("moveCheckedItems", () => {
    beforeEach(() => {
      setBody(`
        <div class="list-group" id="fromList">
          <label class="list-group-item"><input type="checkbox" value="a" checked>A</label>
          <label class="list-group-item"><input type="checkbox" value="b">B</label>
          <label class="list-group-item"><input type="checkbox" value="c" checked>C</label>
        </div>
        <div class="list-group" id="toList"></div>
      `);
    });

    it("moves only checked items to the target list", () => {
      moveCheckedItems("fromList", "toList");

      const fromList = document.getElementById("fromList");
      const toList = document.getElementById("toList");

      // Only unchecked item 'b' remains in source
      expect(fromList.querySelectorAll('input[type="checkbox"]').length).toBe(1);
      expect(fromList.querySelector('input[type="checkbox"]').value).toBe("b");

      // Checked items 'a' and 'c' moved to target
      const movedCbs = toList.querySelectorAll('input[type="checkbox"]');
      expect(movedCbs.length).toBe(2);
      const movedValues = Array.from(movedCbs).map((cb) => cb.value);
      expect(movedValues).toContain("a");
      expect(movedValues).toContain("c");
    });

    it("unchecks items after moving them", () => {
      moveCheckedItems("fromList", "toList");

      const toList = document.getElementById("toList");
      toList.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
        expect(cb.checked).toBe(false);
      });
    });

    it("shows placeholder when source becomes empty", () => {
      // Check all items
      document.querySelectorAll('#fromList input[type="checkbox"]').forEach((cb) => {
        cb.checked = true;
      });

      moveCheckedItems("fromList", "toList");

      const fromList = document.getElementById("fromList");
      expect(fromList.textContent).toContain("No CLOs");
    });

    it("removes 'Mapped to another PLO' badge when moving", () => {
      // Add a badge to item A
      const itemA = document.querySelector('#fromList .list-group-item');
      const badge = document.createElement("span");
      badge.className = "badge bg-warning text-dark";
      badge.textContent = "Mapped to another PLO";
      itemA.appendChild(badge);

      moveCheckedItems("fromList", "toList");

      const toList = document.getElementById("toList");
      expect(toList.querySelector(".badge.bg-warning")).toBeNull();
    });

    it("does not crash when lists are missing", () => {
      expect(() => moveCheckedItems("nonExistent1", "nonExistent2")).not.toThrow();
    });
  });

  describe("updatePickerCounts", () => {
    beforeEach(() => {
      setBody(`
        <div id="mappedCloList">
          <label><input type="checkbox" value="a">A</label>
          <label><input type="checkbox" value="b">B</label>
        </div>
        <div id="availableCloList">
          <label><input type="checkbox" value="c">C</label>
        </div>
        <span id="mappedCloCount">0</span>
        <span id="availableCloCount">0</span>
      `);
    });

    it("updates mapped and available count badges", () => {
      updatePickerCounts();

      expect(document.getElementById("mappedCloCount").textContent).toBe("2");
      expect(document.getElementById("availableCloCount").textContent).toBe("1");
    });

    it("does not crash when elements are missing", () => {
      setBody("<div></div>");
      expect(() => updatePickerCounts()).not.toThrow();
    });
  });
});
