/**
 * @jest-environment jsdom
 */

const { loadOfferings, applyFilters } = require("../../../static/offeringManagement");
const { setBody } = require("../helpers/dom");

describe("Offering Management - Program Association Validation", () => {
  beforeEach(() => {
    // Set up DOM structure
    setBody(`
      <div id="offeringsTableContainer"></div>
      <select id="filterTerm">
        <option value="">All Terms</option>
      </select>
      <select id="filterProgram">
        <option value="">All Programs</option>
      </select>
    `);

    global.fetch = jest.fn();
    global.console.error = jest.fn();
    global.console.warn = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe("Data Integrity Validation", () => {
    test("should detect offerings with missing program associations", async () => {
      const mockOfferings = [
        {
          offering_id: "offering-1",
          course_name: "Introduction to Biology",
          term_name: "Fall 2024",
          term_id: "term-1",
          program_ids: ["prog-1"], // Valid
          program_names: ["Biological Sciences"],
          status: "active",
          section_count: 2,
          total_enrollment: 45,
        },
        {
          offering_id: "offering-2",
          course_name: "History of Science",
          term_name: "Spring 2025",
          term_id: "term-2",
          program_ids: [], // INVALID - missing program association
          program_names: [],
          status: "scheduled",
          section_count: 1,
          total_enrollment: 0,
        },
        {
          offering_id: "offering-3",
          course_name: "Advanced Chemistry",
          term_name: "Fall 2024",
          term_id: "term-1",
          program_ids: ["prog-2", "prog-3"], // Valid - multiple programs
          program_names: ["Chemistry", "Biochemistry"],
          status: "active",
          section_count: 3,
          total_enrollment: 78,
        },
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, offerings: mockOfferings }),
      });

      await loadOfferings();

      const container = document.getElementById("offeringsTableContainer");

      // Should display error message about orphaned offering
      expect(container.innerHTML).toContain("Data Integrity Issue");
      expect(container.innerHTML).toContain("History of Science");
      expect(container.innerHTML).toContain("no program associations");

      // Should log error for debugging
      expect(console.error).toHaveBeenCalledWith(
        expect.stringContaining("Offerings found with no program associations"),
        expect.arrayContaining([
          expect.objectContaining({
            offering_id: "offering-2",
            course_name: "History of Science",
          }),
        ]),
      );
    });

    test("should display all valid offerings when no orphaned data exists", async () => {
      const mockOfferings = [
        {
          offering_id: "offering-1",
          course_name: "Introduction to Biology",
          term_name: "Fall 2024",
          term_id: "term-1",
          program_ids: ["prog-1"],
          program_names: ["Biological Sciences"],
          status: "active",
          section_count: 2,
          total_enrollment: 45,
        },
        {
          offering_id: "offering-2",
          course_name: "Advanced Chemistry",
          term_name: "Fall 2024",
          term_id: "term-1",
          program_ids: ["prog-2"],
          program_names: ["Chemistry"],
          status: "active",
          section_count: 3,
          total_enrollment: 78,
        },
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, offerings: mockOfferings }),
      });

      await loadOfferings();

      const container = document.getElementById("offeringsTableContainer");

      // Should NOT display error message
      expect(container.innerHTML).not.toContain("Data Integrity Issue");

      // Should display normal table
      expect(container.innerHTML).toContain("<table");
      expect(container.innerHTML).toContain("Introduction to Biology");
      expect(container.innerHTML).toContain("Advanced Chemistry");

      // Should NOT log errors
      expect(console.error).not.toHaveBeenCalled();
    });

    test("should list all orphaned offerings in error message", async () => {
      const mockOfferings = [
        {
          offering_id: "offering-1",
          course_name: "Orphan Course 1",
          term_name: "Fall 2024",
          term_id: "term-1",
          program_ids: [],
          program_names: [],
          status: "active",
          section_count: 1,
          total_enrollment: 20,
        },
        {
          offering_id: "offering-2",
          course_name: "Valid Course",
          term_name: "Fall 2024",
          term_id: "term-1",
          program_ids: ["prog-1"],
          program_names: ["Biology"],
          status: "active",
          section_count: 2,
          total_enrollment: 40,
        },
        {
          offering_id: "offering-3",
          course_name: "Orphan Course 2",
          term_name: "Spring 2025",
          term_id: "term-2",
          program_ids: [],
          program_names: [],
          status: "scheduled",
          section_count: 0,
          total_enrollment: 0,
        },
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, offerings: mockOfferings }),
      });

      await loadOfferings();

      const container = document.getElementById("offeringsTableContainer");

      // Should list both orphaned offerings
      expect(container.innerHTML).toContain("Orphan Course 1");
      expect(container.innerHTML).toContain("Orphan Course 2");

      // Should show count
      expect(container.innerHTML).toContain("2 offerings");
    });

    test("should provide actionable guidance in error message", async () => {
      const mockOfferings = [
        {
          offering_id: "offering-1",
          course_name: "Orphaned Offering",
          term_name: "Fall 2024",
          term_id: "term-1",
          program_ids: [],
          program_names: [],
          status: "active",
          section_count: 1,
          total_enrollment: 20,
        },
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, offerings: mockOfferings }),
      });

      await loadOfferings();

      const container = document.getElementById("offeringsTableContainer");

      // Should provide guidance
      expect(container.innerHTML).toMatch(
        /associate.*course.*with.*program|assign.*program|contact.*administrator/i,
      );
    });
  });

  describe("Filtering with Program Associations", () => {
    test("should only show offerings with matching program when filtered", async () => {
      const mockOfferings = [
        {
          offering_id: "offering-1",
          course_name: "Biology Course",
          term_name: "Fall 2024",
          term_id: "term-1",
          program_ids: ["prog-bio"],
          program_names: ["Biology"],
          status: "active",
          section_count: 2,
          total_enrollment: 45,
        },
        {
          offering_id: "offering-2",
          course_name: "Chemistry Course",
          term_name: "Fall 2024",
          term_id: "term-1",
          program_ids: ["prog-chem"],
          program_names: ["Chemistry"],
          status: "active",
          section_count: 3,
          total_enrollment: 78,
        },
      ];

      // Mock offerings API
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, offerings: mockOfferings }),
      });

      // Mock populateFilters API calls (terms and programs)
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, terms: [] }),
      });
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, programs: [] }),
      });

      await loadOfferings();

      // Simulate selecting Biology program filter
      // Need to add an option first for JSDOM to recognize the value
      const programFilter = document.getElementById("filterProgram");
      const option = document.createElement("option");
      option.value = "prog-bio";
      option.textContent = "Biology";
      programFilter.appendChild(option);
      
      programFilter.value = "prog-bio";

      applyFilters();

      // Re-query rows after applying filter (style changes are in-place)
      const rows = document.querySelectorAll(".offering-row");
      
      expect(rows).toHaveLength(2);

      // Biology row should be visible
      expect(rows[0].style.display).not.toBe("none");
      expect(rows[0].textContent).toContain("Biology Course");

      // Chemistry row should be hidden
      expect(rows[1].style.display).toBe("none");
    });

    test("should handle multi-program offerings correctly", async () => {
      const mockOfferings = [
        {
          offering_id: "offering-1",
          course_name: "Cross-Disciplinary Course",
          term_name: "Fall 2024",
          term_id: "term-1",
          program_ids: ["prog-bio", "prog-chem"],
          program_names: ["Biology", "Chemistry"],
          status: "active",
          section_count: 2,
          total_enrollment: 45,
        },
      ];

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, offerings: mockOfferings }),
      });
      
      // Mock populateFilters API calls
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, terms: [] }),
      });
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, programs: [] }),
      });

      await loadOfferings();

      // Add options to the select for JSDOM to recognize values
      const programFilter = document.getElementById("filterProgram");
      ["prog-bio", "prog-chem", "prog-other"].forEach((progId) => {
        const option = document.createElement("option");
        option.value = progId;
        option.textContent = progId;
        programFilter.appendChild(option);
      });

      // Filter by Biology
      programFilter.value = "prog-bio";
      applyFilters();

      let rows = document.querySelectorAll(".offering-row");
      expect(rows[0].style.display).not.toBe("none"); // Should show

      // Filter by Chemistry
      programFilter.value = "prog-chem";
      applyFilters();

      rows = document.querySelectorAll(".offering-row");
      expect(rows[0].style.display).not.toBe("none"); // Should still show

      // Filter by different program
      programFilter.value = "prog-other";
      applyFilters();

      rows = document.querySelectorAll(".offering-row");
      expect(rows[0].style.display).toBe("none"); // Should hide
    });
  });
});
