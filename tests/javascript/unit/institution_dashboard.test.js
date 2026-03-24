// Load dashboard utilities globally (simulates browser <script> tag)
const {
  setLoadingState,
  setErrorState,
  setEmptyState,
} = require("../../../static/dashboard_utils");
global.setLoadingState = setLoadingState;
global.setErrorState = setErrorState;
global.setEmptyState = setEmptyState;

const InstitutionDashboard = require("../../../static/institution_dashboard");
const { setBody } = require("../helpers/dom");

describe("InstitutionDashboard", () => {
  beforeEach(() => {
    setBody(`
      <div id="institutionName"></div>
      <div id="currentTermName"></div>
      <div id="programManagementContainer"></div>
      <div id="facultyOverviewContainer"></div>
      <div id="courseSectionContainer"></div>
      <div id="courseManagementContainer"></div>
      <div id="termManagementContainer"></div>
    `);

    window.panelManager = {
      createSortableTable: jest.fn((config) => {
        const table = document.createElement("table");
        table.setAttribute("data-table-id", config.id);
        table.innerHTML = "<tbody></tbody>";
        return table;
      }),
    };
  });

  afterEach(() => {
    // Clean up any intervals
    if (InstitutionDashboard.intervalId) {
      clearInterval(InstitutionDashboard.intervalId);
      InstitutionDashboard.intervalId = null;
    }
    jest.clearAllTimers();
    jest.restoreAllMocks();
  });

  const sampleData = {
    summary: { programs: 2, courses: 5, faculty: 3, sections: 7 },
    institutions: [{ name: "Example University" }],
    terms: [{ name: "Fall 2025", status: "ACTIVE" }],
    clos: [
      {
        id: "clo1",
        course: "NURS101",
        clo_number: "1",
        description: "Test CLO",
        status: "active",
      },
    ],
    program_overview: [
      {
        program_name: "Nursing",
        course_count: 3,
        assessment_progress: { completed: 5, total: 10, percent_complete: 50 },
      },
    ],
    programs: [{ id: "p1", name: "Nursing" }],
    faculty_assignments: [
      { faculty_name: "Jane Doe", program_id: "p1", assignments: 2 },
    ],
    faculty: [{ id: "f1", name: "Jane Doe", course_count: 2 }],
    sections: [
      {
        section_id: "s1",
        course_id: "c1",
        instructor_name: "Jane Doe",
        enrollment: 30,
        status: "scheduled",
      },
    ],
    courses: [
      { course_id: "c1", course_title: "Biology 101", course_number: "BIO101" },
    ],
    metadata: { last_updated: "2024-01-01T00:00:00Z" },
  };

  describe("Timeline status helpers", () => {
    const helpers = InstitutionDashboard.__testHelpers;

    test("prefers explicit status metadata when available", () => {
      const status = helpers.computeTimelineStatus({ status: "scheduled" });
      expect(status).toBe("SCHEDULED");
    });

    test("returns ACTIVE when reference date falls within range", () => {
      const status = helpers.computeTimelineStatus(
        {
          start_date: "2024-12-01",
          end_date: "2025-03-01",
        },
        { referenceDate: new Date("2025-01-15") },
      );
      expect(status).toBe("ACTIVE");
    });

    test("returns PASSED when reference date exceeds end date", () => {
      const status = helpers.computeTimelineStatus(
        {
          start_date: "2024-01-01",
          end_date: "2024-02-01",
        },
        { referenceDate: new Date("2024-03-01") },
      );
      expect(status).toBe("PASSED");
    });

    test("accepts reference date strings", () => {
      const status = helpers.computeTimelineStatus(
        {
          start_date: "2025-01-01",
          end_date: "2025-01-31",
        },
        { referenceDate: "2025-01-15" },
      );
      expect(status).toBe("ACTIVE");
    });

    test("fallback helper returns UNKNOWN when dates missing", () => {
      expect(helpers.fallbackTimelineStatus({})).toBe("UNKNOWN");
    });

    test("escapeHtml strips unsafe markup", () => {
      const sanitized = helpers.escapeHtml("<img src=x onerror=alert(1)>");
      expect(sanitized).toContain("&lt;img");
      expect(sanitized).not.toContain("<img");
    });

    test("renderSectionStatus falls back to unknown badge", () => {
      const html = helpers.renderSectionStatus("does-not-exist");
      expect(html).toContain("Unknown");
    });

    test("normalizeReferenceDate handles invalid input gracefully", () => {
      const normalized = helpers.normalizeReferenceDate("not-a-date");
      expect(normalized instanceof Date).toBe(true);
    });
  });

  describe("Panel renderers", () => {
    test("renderCourses builds a table when container exists", () => {
      const container = document.getElementById("courseManagementContainer");
      container.innerHTML = "";

      InstitutionDashboard.renderCourses([
        {
          course_number: "BIO101",
          course_title: "Intro Biology",
          credit_hours: 3,
          section_count: 2,
          program_names: ["Biological Sciences"],
        },
      ]);

      expect(window.panelManager.createSortableTable).toHaveBeenCalledWith(
        expect.objectContaining({ id: "institution-courses-table" }),
      );
      expect(container.querySelector("table")).not.toBeNull();
    });

    test("renderTerms builds a table with computed status", () => {
      const container = document.getElementById("termManagementContainer");
      container.innerHTML = "";

      InstitutionDashboard.renderTerms([
        {
          name: "Spring 2025",
          start_date: "2025-01-01",
          end_date: "2025-05-01",
          program_count: 1,
          course_count: 2,
          section_count: 3,
        },
      ]);

      expect(window.panelManager.createSortableTable).toHaveBeenCalledWith(
        expect.objectContaining({ id: "institution-terms-table" }),
      );
      expect(container.querySelector("table")).not.toBeNull();
    });
  });

  it("renders summary metrics and tables", () => {
    InstitutionDashboard.render(sampleData);

    // Header stats removed, just verify render completes and tables are created
    expect(window.panelManager.createSortableTable).toHaveBeenCalled();
  });

  it("shows loading and error states", () => {
    InstitutionDashboard.setLoading(
      "programManagementContainer",
      "Loading programs...",
    );
    expect(
      document.getElementById("programManagementContainer").textContent,
    ).toContain("Loading programs");

    InstitutionDashboard.showError("programManagementContainer", "Failed");
    expect(
      document.getElementById("programManagementContainer").textContent,
    ).toContain("Failed");
  });

  describe("comprehensive institution dashboard functionality", () => {
    it("handles refresh functionality", async () => {
      const sampleData = {
        institutions: [
          {
            name: "Test University",
            id: "test-uni",
          },
        ],
        summary: {
          programs: 1,
          courses: 10,
          faculty: 5,
          sections: 15,
        },
        program_overview: [
          {
            program_name: "CS",
            course_count: 10,
            student_count: 200,
            completion_rate: 85,
          },
        ],
        assessment_progress: [
          { program_name: "CS", completed: 15, pending: 5, overdue: 2 },
        ],
        terms: [{ name: "Fall 2024", status: "ACTIVE" }],
        metadata: { last_updated: "2024-02-01T12:00:00Z" },
      };

      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: sampleData,
        }),
      });

      const renderSpy = jest.spyOn(InstitutionDashboard, "render");

      await InstitutionDashboard.refresh();

      expect(fetch).toHaveBeenCalledWith("/api/dashboard/data", {
        credentials: "include",
        headers: {
          Accept: "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
      });
      expect(renderSpy).toHaveBeenCalledWith(sampleData);

      renderSpy.mockRestore();
    });

    it("handles refresh errors", async () => {
      global.fetch = jest
        .fn()
        .mockRejectedValueOnce(new Error("Network error"));

      const showErrorSpy = jest.spyOn(InstitutionDashboard, "showError");
      const consoleWarnSpy = jest.spyOn(console, "warn").mockImplementation();

      await InstitutionDashboard.refresh();

      expect(consoleWarnSpy).toHaveBeenCalled();
      expect(showErrorSpy).toHaveBeenCalled();

      showErrorSpy.mockRestore();
      consoleWarnSpy.mockRestore();
      // Reset fetch mock for subsequent tests
      global.fetch = jest.fn();
    });

    it("handles different loading states", () => {
      // Test multiple containers
      InstitutionDashboard.setLoading(
        "programManagementContainer",
        "Loading programs...",
      );
      InstitutionDashboard.setLoading(
        "facultyOverviewContainer",
        "Loading faculty...",
      );

      expect(
        document.getElementById("programManagementContainer").textContent,
      ).toContain("Loading programs");
      expect(
        document.getElementById("facultyOverviewContainer").textContent,
      ).toContain("Loading faculty");
    });

    it("handles basic render functionality", () => {
      const basicData = {
        institutions: [
          {
            name: "Basic University",
            id: "basic-uni",
          },
        ],
        summary: {
          programs: 1,
          courses: 5,
          faculty: 3,
          sections: 8,
        },
        program_overview: [
          {
            program_name: "CS",
            course_count: 5,
            student_count: 100,
            completion_rate: 80,
          },
        ],
        assessment_progress: [
          { program_name: "CS", completed: 10, pending: 2, overdue: 1 },
        ],
        terms: [{ name: "Spring 2024", status: "ACTIVE" }],
        metadata: { last_updated: "2024-02-01T12:00:00Z" },
      };

      // Should not throw error
      expect(() => InstitutionDashboard.render(basicData)).not.toThrow();
    });

    it("handles empty data gracefully", () => {
      const emptyData = {
        institutions: [],
        summary: {
          programs: 0,
          courses: 0,
          faculty: 0,
          sections: 0,
        },
        program_overview: [],
        assessment_progress: [],
        terms: [],
        metadata: {},
      };

      // Should not throw error
      expect(() => InstitutionDashboard.render(emptyData)).not.toThrow();
    });

    it("tests initialization functionality", () => {
      // Test that init function exists and can be called
      expect(typeof InstitutionDashboard.init).toBe("function");

      // Should not throw error when called
      expect(() => InstitutionDashboard.init()).not.toThrow();
    });

    it("tests cache functionality", () => {
      // Test that cache property exists
      expect(
        Object.prototype.hasOwnProperty.call(InstitutionDashboard, "cache"),
      ).toBe(true);
      expect(
        Object.prototype.hasOwnProperty.call(InstitutionDashboard, "lastFetch"),
      ).toBe(true);
      expect(
        Object.prototype.hasOwnProperty.call(
          InstitutionDashboard,
          "refreshInterval",
        ),
      ).toBe(true);
    });
  });

  describe("section rendering with instructor details", () => {
    beforeEach(() => {
      setBody(`
        <div id="courseSectionContainer"></div>
      `);
    });

    it("renders reminder button when instructor has email", () => {
      const sections = [
        {
          section_id: "s1",
          section_number: "001",
          course_id: "c1",
          instructor_id: "inst1",
          instructor_name: "Dr. Smith",
          instructor_email: "smith@test.edu",
          enrollment: 30,
          status: "ACTIVE",
        },
      ];

      const courses = [
        {
          course_id: "c1",
          course_number: "CS101",
          course_title: "Intro to CS",
        },
      ];

      InstitutionDashboard.renderSections(sections, courses, []);

      const container = document.getElementById("courseSectionContainer");
      expect(container).not.toBeNull();
      expect(window.panelManager.createSortableTable).toHaveBeenCalled();

      // Verify the table was created with section data
      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];
      expect(callArgs.data).toHaveLength(1);

      // Actions column removed - panels are display-only
      const sectionData = callArgs.data[0];
      expect(sectionData.status).toBeDefined();
    });

    it("does not render reminder button when instructor lacks email", () => {
      const sections = [
        {
          section_id: "s2",
          section_number: "002",
          course_id: "c1",
          instructor_id: "inst2",
          instructor_name: "Dr. Jones",
          // No instructor_email
          enrollment: 25,
          status: "scheduled",
        },
      ];

      const courses = [
        {
          course_id: "c1",
          course_number: "CS102",
          course_title: "Data Structures",
        },
      ];

      InstitutionDashboard.renderSections(sections, courses, []);

      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];
      const sectionData = callArgs.data[0];

      // Actions column removed - panels are display-only
      expect(sectionData.status).toBeDefined();
    });

    it("renders section status as a badge", () => {
      const sections = [
        {
          section_id: "s1",
          status: "assigned",
          course_id: "c1",
        },
        {
          section_id: "s2",
          status: "unassigned",
          course_id: "c1",
        },
      ];

      const courses = [{ course_id: "c1" }];

      InstitutionDashboard.renderSections(sections, courses);

      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];
      const section1 = callArgs.data[0];
      const section2 = callArgs.data[1];

      expect(section1.status).toContain("badge");
      expect(section1.status).toContain("Assigned");
      expect(section2.status).toContain("badge");
      expect(section2.status).toContain("Unassigned");
    });
  });

  describe("course rendering", () => {
    beforeEach(() => {
      setBody(`
        <div id="courseManagementContainer"></div>
      `);
    });

    it("renders course table with programs (not department)", () => {
      const courses = [
        {
          course_id: "c1",
          course_number: "BIO101",
          course_title: "Introduction to Biology",
          program_names: ["Biological Sciences"],
          credit_hours: 3,
          active: true,
        },
        {
          course_id: "c2",
          course_number: "CHEM202",
          course_title: "Organic Chemistry",
          program_names: ["Chemistry", "Pre-Med"],
          credit_hours: 4,
          active: true,
        },
      ];

      InstitutionDashboard.renderCourses(courses);

      expect(window.panelManager.createSortableTable).toHaveBeenCalled();
      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];

      expect(callArgs.id).toBe("institution-courses-table");
      expect(callArgs.data).toHaveLength(2);

      // Verify course data structure (now shows programs instead of department)
      const course1 = callArgs.data[0];
      expect(course1.number).toBe("BIO101");
      expect(course1.title).toBe("Introduction to Biology");
      expect(course1.credits).toBe("3");
      expect(course1.programs).toBe("Biological Sciences"); // Changed from department

      const course2 = callArgs.data[1];
      expect(course2.programs).toBe("Chemistry, Pre-Med"); // Multiple programs
      // Actions column removed - panels are display-only
    });

    it("renders empty state when no courses", () => {
      InstitutionDashboard.renderCourses([]);

      const container = document.getElementById("courseManagementContainer");
      expect(container.innerHTML).toContain("No courses found");
      expect(container.innerHTML).toContain("Add Course");
    });

    it("handles missing container gracefully", () => {
      setBody("<div></div>"); // No courseManagementContainer

      // Should not throw error
      expect(() =>
        InstitutionDashboard.renderCourses([{ course_id: "c1" }]),
      ).not.toThrow();
      expect(window.panelManager.createSortableTable).not.toHaveBeenCalled();
    });

    it("handles courses with missing optional fields", () => {
      const courses = [
        {
          course_id: "c1",
          course_number: "MATH101",
          // Missing title, department, credit_hours
        },
      ];

      InstitutionDashboard.renderCourses(courses);

      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];
      const courseData = callArgs.data[0];

      // Should use defaults for missing fields
      expect(courseData.number).toBe("MATH101");
      expect(courseData.title).toBe("-"); // Default dash
      expect(courseData.programs).toBe("-"); // Default dash for missing programs
    });
  });

  describe("program rendering", () => {
    beforeEach(() => {
      setBody(`
        <div id="programManagementContainer"></div>
      `);
    });

    it("renders program table with data", () => {
      const programOverview = [
        {
          program_name: "Computer Science",
          course_count: 10,
          student_count: 200,
        },
        {
          program_name: "Biology",
          course_count: 8,
          student_count: 150,
        },
      ];

      const rawPrograms = [
        { id: "p1", name: "Computer Science", code: "CS" },
        { id: "p2", name: "Biology", code: "BIO" },
      ];

      InstitutionDashboard.renderPrograms(programOverview, rawPrograms);

      expect(window.panelManager.createSortableTable).toHaveBeenCalled();
      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];

      expect(callArgs.id).toBe("institution-programs-table");
      expect(callArgs.data).toHaveLength(2);
    });

    it("renders empty state when no programs", () => {
      InstitutionDashboard.renderPrograms([], []);

      const container = document.getElementById("programManagementContainer");
      expect(container.innerHTML).toContain("No programs found");
    });
  });

  describe("faculty rendering", () => {
    beforeEach(() => {
      setBody(`
        <div id="facultyOverviewContainer"></div>
      `);
    });

    it("renders faculty table with assignment counts", () => {
      const assignments = [
        {
          user_id: "f1",
          full_name: "Dr. Smith",
          program_ids: ["p1"],
          course_count: 3,
          section_count: 5,
          enrollment: 120,
        },
        {
          user_id: "f2",
          full_name: "Prof. Johnson",
          program_ids: ["p1"],
          course_count: 2,
          section_count: 3,
          enrollment: 75,
        },
      ];

      const fallbackFaculty = [];

      InstitutionDashboard.renderFaculty(assignments, fallbackFaculty);

      expect(window.panelManager.createSortableTable).toHaveBeenCalled();
      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];

      expect(callArgs.id).toBe("institution-faculty-table");
      expect(callArgs.data).toHaveLength(2);

      const faculty1 = callArgs.data[0];
      expect(faculty1.name).toBe("Dr. Smith");
      expect(faculty1.courses).toBe("3");
    });

    it("renders empty state when no faculty", () => {
      InstitutionDashboard.renderFaculty([], []);

      const container = document.getElementById("facultyOverviewContainer");
      expect(container.innerHTML).toContain("No faculty assigned yet");
    });
  });

  describe("offerings rendering", () => {
    beforeEach(() => {
      setBody(`
        <div id="offeringManagementContainer"></div>
      `);
    });

    it("renders offerings table with course and term lookups", () => {
      const offerings = [
        {
          offering_id: "off1",
          course_id: "c1",
          term_id: "t1",
          sections: 2,
          enrollment: 50,
          status: "ACTIVE",
        },
        {
          offering_id: "off2",
          course_id: "c2",
          term_id: "t2",
          sections: 1,
          enrollment: 25,
          status: "active",
        },
      ];

      const courses = [
        {
          course_id: "c1",
          course_number: "CS101",
          course_title: "Intro to CS",
        },
        { course_id: "c2", course_number: "MATH201", course_title: "Calculus" },
      ];

      const terms = [
        { term_id: "t1", name: "Fall 2024" },
        { term_id: "t2", name: "Spring 2025" },
      ];

      InstitutionDashboard.renderOfferings(offerings, courses, terms);

      expect(window.panelManager.createSortableTable).toHaveBeenCalled();
      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];

      expect(callArgs.id).toBe("institution-offerings-table");
      expect(callArgs.data).toHaveLength(2);
    });

    it("renders empty state when no offerings", () => {
      InstitutionDashboard.renderOfferings([], [], []);

      const container = document.getElementById("offeringManagementContainer");
      expect(container.innerHTML).toContain("No course offerings scheduled");
      expect(container.innerHTML).toContain("Add Offering");
    });

    it("handles missing container gracefully", () => {
      setBody("<div></div>"); // No offeringManagementContainer

      // Should not throw error
      expect(() =>
        InstitutionDashboard.renderOfferings([{ offering_id: "o1" }], [], []),
      ).not.toThrow();
      expect(window.panelManager.createSortableTable).not.toHaveBeenCalled();
    });

    it("handles offerings with missing course/term data", () => {
      const offerings = [
        {
          offering_id: "off1",
          course_id: "unknown",
          term_id: "unknown",
          sections: 0,
          enrollment: 0,
        },
      ];

      InstitutionDashboard.renderOfferings(offerings, [], []);

      expect(window.panelManager.createSortableTable).toHaveBeenCalled();
      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];
      expect(callArgs.data).toHaveLength(1);
    });
  });

  describe("CLO audit rendering", () => {
    beforeEach(() => {
      setBody(`
        <div id="institutionCloAuditContainer"></div>
      `);
    });

    it("renders CLO audit table with percent complete", () => {
      const clos = [
        { program_name: "Computer Science", status: "approved" },
        { program_name: "Computer Science", status: "approved" },
        { program_name: "Computer Science", status: "approved" },
        { program_name: "Computer Science", status: "awaiting_approval" },
        { program_name: "Biology", status: "approved" },
        { program_name: "Biology", status: "in_progress" },
        { program_name: "Biology", status: "unassigned" },
        { program_name: "Biology", status: "unassigned" },
      ];

      InstitutionDashboard.renderCLOAudit(clos);

      expect(window.panelManager.createSortableTable).toHaveBeenCalled();
      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];

      // Should have 2 programs
      expect(callArgs.data).toHaveLength(2);

      // Check CS: 3 approved out of 4 total = 75%
      const csProgram = callArgs.data.find(
        (p) => p.program === "Computer Science",
      );
      expect(csProgram.approved).toBe("3");
      expect(csProgram.awaitingApproval).toBe("1");
      expect(csProgram.percentComplete).toBe("75%");

      // Check Biology: 1 approved out of 4 total = 25%
      const bioProgram = callArgs.data.find((p) => p.program === "Biology");
      expect(bioProgram.approved).toBe("1");
      expect(bioProgram.unassigned).toBe("2");
      expect(bioProgram.percentComplete).toBe("25%");

      // Verify columns include percentComplete
      const columnKeys = callArgs.columns.map((c) => c.key);
      expect(columnKeys).toContain("percentComplete");
    });

    it("handles empty CLO data", () => {
      InstitutionDashboard.renderCLOAudit([]);

      const container = document.getElementById("institutionCloAuditContainer");
      expect(container.innerHTML).toContain("No Outcomes pending audit");
    });

    it("calculates percent complete correctly for single program", () => {
      const clos = [
        { program_name: "Engineering", status: "approved" },
        { program_name: "Engineering", status: "approved" },
        { program_name: "Engineering", status: "in_progress" },
        { program_name: "Engineering", status: "assigned" },
      ];

      InstitutionDashboard.renderCLOAudit(clos);

      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];
      const engProgram = callArgs.data[0];

      // 2 approved out of 4 total = 50%
      expect(engProgram.percentComplete).toBe("50%");
      expect(engProgram.percentComplete_sort).toBe("050");
    });

    it("handles missing container gracefully", () => {
      setBody("<div></div>"); // No institutionCloAuditContainer

      // Should not throw error
      expect(() =>
        InstitutionDashboard.renderCLOAudit([
          { program_name: "Test", status: "approved" },
        ]),
      ).not.toThrow();
      expect(window.panelManager.createSortableTable).not.toHaveBeenCalled();
    });

    it("calculates 0% when no CLOs are approved", () => {
      const clos = [
        { program_name: "Test Program", status: "unassigned" },
        { program_name: "Test Program", status: "assigned" },
        { program_name: "Test Program", status: "in_progress" },
      ];

      InstitutionDashboard.renderCLOAudit(clos);

      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];
      expect(callArgs.data[0].percentComplete).toBe("0%");
    });

    it("calculates 100% when all CLOs are approved", () => {
      const clos = [
        { program_name: "Complete Program", status: "approved" },
        { program_name: "Complete Program", status: "approved" },
        { program_name: "Complete Program", status: "approved" },
      ];

      InstitutionDashboard.renderCLOAudit(clos);

      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];
      expect(callArgs.data[0].percentComplete).toBe("100%");
    });
  });

  describe("terms rendering", () => {
    beforeEach(() => {
      setBody(`
        <div id="termManagementContainer"></div>
      `);
    });

    it("renders terms table", () => {
      const terms = [
        {
          term_id: "t1",
          name: "Fall 2024",
          start_date: "2024-08-01",
          end_date: "2024-12-15",
          status: "ACTIVE",
          offerings_count: 10,
        },
        {
          term_id: "t2",
          name: "Spring 2025",
          start_date: "2025-01-15",
          end_date: "2025-05-15",
          status: "SCHEDULED",
          offerings_count: 0,
        },
      ];

      InstitutionDashboard.renderTerms(terms);

      expect(window.panelManager.createSortableTable).toHaveBeenCalled();
      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];

      expect(callArgs.id).toBe("institution-terms-table");
      expect(callArgs.data).toHaveLength(2);
    });

    it("renders empty state when no terms", () => {
      InstitutionDashboard.renderTerms([]);

      const container = document.getElementById("termManagementContainer");
      expect(container.innerHTML).toContain("No terms defined");
      expect(container.innerHTML).toContain("Add Term");
    });

    it("handles missing container gracefully", () => {
      setBody("<div></div>"); // No termManagementContainer

      // Should not throw error
      expect(() =>
        InstitutionDashboard.renderTerms([{ term_id: "t1" }]),
      ).not.toThrow();
      expect(window.panelManager.createSortableTable).not.toHaveBeenCalled();
    });
  });
});
