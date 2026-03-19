/**
 * Tests for offering filtering logic
 *
 * BUG: Filtering by program doesn't work because offerings have program_names (array)
 * but the filter checks program_id (singular, doesn't exist on offerings from API)
 */

const { applyFilters } = require("../../../static/offeringManagement");
const { setBody } = require("../helpers/dom");

describe("offeringManagement filtering", () => {
  beforeEach(() => {
    // Set up a mock offerings table with multiple offerings
    setBody(`
      <select id="filterTerm">
        <option value="">All Terms</option>
        <option value="term-1">Fall 2025</option>
        <option value="term-2">Spring 2025</option>
      </select>
      
      <select id="filterProgram">
        <option value="">All Programs</option>
        <option value="prog-1">Biological Sciences</option>
        <option value="prog-2">Zoology</option>
      </select>
      
      <div id="offeringsTableContainer">
        <table>
          <tbody>
            <!-- Offering 1: BIOL-101 in Fall 2025, belongs to Biological Sciences -->
            <tr class="offering-row" data-term-id="term-1" data-program-ids="prog-1">
              <td>BIOL-101</td>
              <td>Biological Sciences</td>
            </tr>
            
            <!-- Offering 2: ZOOL-101 in Fall 2025, belongs to Zoology -->
            <tr class="offering-row" data-term-id="term-1" data-program-ids="prog-2">
              <td>ZOOL-101</td>
              <td>Zoology</td>
            </tr>
            
            <!-- Offering 3: HIST-101 in Spring 2025, belongs to MULTIPLE programs (Biological Sciences, Zoology) -->
            <tr class="offering-row" data-term-id="term-2" data-program-ids="prog-1,prog-2">
              <td>HIST-101</td>
              <td>Biological Sciences, Zoology</td>
            </tr>
            
            <!-- Offering 4: Course with no program (orphaned) -->
            <tr class="offering-row" data-term-id="term-1" data-program-ids="">
              <td>ORPHAN-101</td>
              <td>-</td>
            </tr>
          </tbody>
        </table>
      </div>
    `);
  });

  describe("term filtering", () => {
    it("shows all offerings when no term is selected", () => {
      document.getElementById("filterTerm").value = "";
      applyFilters();

      const rows = document.querySelectorAll(".offering-row");
      expect(rows[0].style.display).not.toBe("none");
      expect(rows[1].style.display).not.toBe("none");
      expect(rows[2].style.display).not.toBe("none");
      expect(rows[3].style.display).not.toBe("none");
    });

    it("filters offerings by term correctly", () => {
      document.getElementById("filterTerm").value = "term-1";
      applyFilters();

      const rows = document.querySelectorAll(".offering-row");
      expect(rows[0].style.display).not.toBe("none"); // Fall 2025
      expect(rows[1].style.display).not.toBe("none"); // Fall 2025
      expect(rows[2].style.display).toBe("none"); // Spring 2025 - hidden
      expect(rows[3].style.display).not.toBe("none"); // Fall 2025
    });
  });

  describe("program filtering", () => {
    it("shows all offerings when no program is selected", () => {
      document.getElementById("filterProgram").value = "";
      applyFilters();

      const rows = document.querySelectorAll(".offering-row");
      expect(rows[0].style.display).not.toBe("none");
      expect(rows[1].style.display).not.toBe("none");
      expect(rows[2].style.display).not.toBe("none");
      expect(rows[3].style.display).not.toBe("none");
    });

    it("filters offerings by single program correctly", () => {
      document.getElementById("filterProgram").value = "prog-1";
      applyFilters();

      const rows = document.querySelectorAll(".offering-row");
      expect(rows[0].style.display).not.toBe("none"); // Biological Sciences
      expect(rows[1].style.display).toBe("none"); // Zoology - hidden
      expect(rows[2].style.display).not.toBe("none"); // Has Biological Sciences (multi-program)
      expect(rows[3].style.display).toBe("none"); // No program - hidden
    });

    it("shows offerings that belong to multiple programs when filtering by one", () => {
      // BUG REPRODUCTION: This test will FAIL with current code
      // HIST-101 belongs to both Biological Sciences and Zoology
      // When filtering by Zoology, it should appear
      document.getElementById("filterProgram").value = "prog-2";
      applyFilters();

      const rows = document.querySelectorAll(".offering-row");
      expect(rows[0].style.display).toBe("none"); // Biological Sciences only - hidden
      expect(rows[1].style.display).not.toBe("none"); // Zoology
      expect(rows[2].style.display).not.toBe("none"); // Has Zoology (multi-program) - SHOULD BE VISIBLE
      expect(rows[3].style.display).toBe("none"); // No program - hidden
    });
  });

  describe("combined filtering", () => {
    it("filters by both term and program correctly", () => {
      document.getElementById("filterTerm").value = "term-1";
      document.getElementById("filterProgram").value = "prog-1";
      applyFilters();

      const rows = document.querySelectorAll(".offering-row");
      expect(rows[0].style.display).not.toBe("none"); // Fall 2025 + Biological Sciences
      expect(rows[1].style.display).toBe("none"); // Fall 2025 but Zoology - hidden
      expect(rows[2].style.display).toBe("none"); // Spring 2025 - hidden by term
      expect(rows[3].style.display).toBe("none"); // Fall 2025 but no program - hidden
    });
  });

  describe("edge cases", () => {
    it("handles offerings with no program gracefully", () => {
      document.getElementById("filterProgram").value = "prog-1";
      applyFilters();

      const rows = document.querySelectorAll(".offering-row");
      expect(rows[3].style.display).toBe("none"); // No program - should be hidden
    });

    it("handles missing filter elements gracefully", () => {
      // Remove filter elements
      document.getElementById("filterTerm").remove();
      document.getElementById("filterProgram").remove();

      // Should not throw error
      expect(() => applyFilters()).not.toThrow();
    });
  });
});
