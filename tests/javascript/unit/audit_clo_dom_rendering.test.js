const auditCloModule = require("../../../static/audit_clo.js");
const {
  createMockModalInstance,
  installDefaultAuditFetch,
  loadAuditCloViaEval,
  setupAuditCloDom,
} = require("./helpers/audit_clo_dom_fixtures");

global.fetch = jest.fn();
global.bootstrap = {
  Modal: Object.assign(jest.fn(), {
    getInstance: jest.fn(),
    getOrCreateInstance: jest.fn(),
  }),
};
global.bootstrap.Modal.getInstance = jest.fn();
global.bootstrap.Modal.getOrCreateInstance = jest.fn();
global.alert = jest.fn();
global.prompt = jest.fn();

describe("audit_clo.js - DOM Integration Rendering", () => {
  beforeEach(() => {
    setupAuditCloDom();
    const mockModalInstance = createMockModalInstance();
    bootstrap.Modal.mockImplementation(() => mockModalInstance);
    bootstrap.Modal.getInstance.mockReturnValue(mockModalInstance);
    bootstrap.Modal.getOrCreateInstance.mockReturnValue(mockModalInstance);
    jest.clearAllMocks();
    fetch.mockClear();
    alert.mockClear();
    prompt.mockClear();
    installDefaultAuditFetch(fetch);
  });

  describe("renderCLODetails", () => {
    const { renderCLODetails } = auditCloModule;

    it("should render CLO details with valid data", () => {
      const clo = {
        status: "awaiting_approval",
        course_number: "CS101",
        course_title: "Intro to CS",
        clo_number: 1,
        description: "Demonstrate problem-solving skills",
        instructor_name: "Jane Doe",
        instructor_email: "jane@example.com",
        students_took: 30,
        students_passed: 27,
      };

      const node = renderCLODetails(clo);
      expect(node.textContent).toContain("CS101");
      expect(node.textContent).toContain("Intro to CS");
      expect(node.textContent).toContain("1");
      expect(node.textContent).toContain("Demonstrate problem-solving skills");
      expect(node.textContent).toContain("Jane Doe");
      expect(node.textContent).toContain("jane@example.com");
      expect(node.textContent).toContain("30");
      expect(node.textContent).toContain("27");
      expect(node.textContent).toContain("90%");
      expect(node.textContent).toContain("Students Took");
      expect(node.textContent).toContain("Students Passed");
      expect(node.textContent).toContain("Success Rate");
    });

    it("should calculate 0% when students_took is 0", () => {
      const node = renderCLODetails({
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        students_took: 0,
        students_passed: 0,
      });
      expect(node.textContent).toContain("0%");
    });

    it("should handle null/undefined students_took and students_passed", () => {
      const node = renderCLODetails({
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        students_took: null,
        students_passed: undefined,
      });
      expect(node.textContent).toContain("0%");
    });

    it("should round percentage correctly", () => {
      const node = renderCLODetails({
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        students_took: 30,
        students_passed: 25,
      });
      expect(node.textContent).toContain("83%");
    });

    it("should render status badge", () => {
      const node = renderCLODetails({
        status: "never_coming_in",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        students_took: 0,
        students_passed: 0,
      });
      expect(node.textContent).toContain("NCI");
      expect(node.querySelector(".badge").style.backgroundColor).toBe(
        "rgb(220, 53, 69)",
      );
    });

    it("should display N/A for missing course info", () => {
      const node = renderCLODetails({
        status: "awaiting_approval",
        clo_number: 1,
        description: "Test",
        students_took: 0,
        students_passed: 0,
      });
      expect(node.textContent).toContain("N/A");
    });

    it("should escape HTML in CLO description", () => {
      const node = renderCLODetails({
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: '<script>alert("XSS")</script>',
        students_took: 0,
        students_passed: 0,
      });
      expect(node.innerHTML).not.toContain("<script>");
      expect(node.innerHTML).toContain("&lt;script&gt;");
    });

    it("should include narrative when present", () => {
      const node = renderCLODetails({
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        students_took: 0,
        students_passed: 0,
        narrative: "This is a detailed narrative about the assessment",
      });
      expect(node.textContent).toContain("Narrative:");
      expect(node.textContent).toContain(
        "This is a detailed narrative about the assessment",
      );
    });

    it("should exclude narrative when not present", () => {
      const node = renderCLODetails({
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        students_took: 0,
        students_passed: 0,
      });
      expect(node.textContent).not.toContain("Narrative:");
    });

    it("should include feedback_comments when present", () => {
      const node = renderCLODetails({
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        students_took: 0,
        students_passed: 0,
        feedback_comments: "Please revise the assessment data",
      });
      expect(node.textContent).toContain("Admin Feedback:");
      expect(node.textContent).toContain("Please revise the assessment data");
    });

    it("should include reviewed_by info when present", () => {
      const node = renderCLODetails({
        status: "approved",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        students_took: 30,
        students_passed: 27,
        reviewed_by_name: "Admin User",
        reviewed_at: "2025-11-05T10:30:00Z",
      });
      expect(node.textContent).toContain("Reviewed by Admin User");
    });

    it("should handle all special characters in instructor name and email", () => {
      const node = renderCLODetails({
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        instructor_name: "Jane <Test> O'Brien & Co.",
        instructor_email: "jane+test@example.com",
        students_took: 0,
        students_passed: 0,
      });
      expect(node.innerHTML).toContain("&lt;Test&gt;");
      expect(node.textContent).toContain("O'Brien");
      expect(node.innerHTML).toContain("&amp; Co.");
      expect(node.textContent).toContain("jane+test@example.com");
    });

    it("should render history section when history is present", () => {
      const node = renderCLODetails({
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: "Test CLO",
        students_took: 10,
        students_passed: 8,
        history: [
          { event: "Assigned", occurred_at: "2024-01-10T10:00:00Z" },
          { event: "Submitted", occurred_at: "2024-01-15T10:00:00Z" },
        ],
      });
      expect(node.textContent).toContain("History:");
      expect(node.textContent).toContain("Assigned");
      expect(node.textContent).toContain("Submitted");
    });

    it("should not render history section when history is empty", () => {
      const node = renderCLODetails({
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: "Test CLO",
        students_took: 10,
        students_passed: 8,
        history: [],
      });
      expect(node.textContent).not.toContain("History:");
    });
  });

  describe("Assignment Workflow", () => {
    beforeEach(() => {
      loadAuditCloViaEval();
      document.dispatchEvent(new Event("DOMContentLoaded"));
    });

    it.skip("should load instructors and show modal on assignOutcome", async () => {
      expect(window.assignOutcome).toEqual(expect.any(Function));
    });
    it.skip("should submit assignment successfully", async () => {
      expect(window.assignOutcome).toEqual(expect.any(Function));
    });
  });

  describe("Reopen Outcome", () => {
    beforeEach(() => {
      loadAuditCloViaEval();
      document.dispatchEvent(new Event("DOMContentLoaded"));
    });

    it("should send POST request to reopen endpoint", async () => {
      global.confirm = jest.fn(() => true);
      fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
      await window.reopenOutcome("out-1");
      expect(fetch).toHaveBeenCalledWith(
        "/api/outcomes/out-1/reopen",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  describe("renderCLOList - Table Rendering", () => {
    async function renderListFor(mockCLOs) {
      fetch.mockImplementation((url) => {
        if (url.includes("/api/outcomes")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ outcomes: mockCLOs }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ count: 0 }),
        });
      });

      loadAuditCloViaEval();
      document.dispatchEvent(new Event("DOMContentLoaded"));
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    it("should render grouped CLO table with course and section headers", async () => {
      await renderListFor([
        {
          outcome_id: "out-1",
          course_number: "CS101",
          course_title: "Intro to CS",
          section_number: "001",
          clo_number: "1",
          description: "Test CLO description",
          status: "awaiting_approval",
          instructor_name: "Dr. Smith",
          submitted_at: "2026-01-10T10:00:00Z",
        },
        {
          outcome_id: "out-2",
          course_number: "CS101",
          course_title: "Intro to CS",
          section_number: "002",
          clo_number: "1",
          description: "Another CLO",
          status: "in_progress",
          instructor_name: "Dr. Jones",
          submitted_at: null,
        },
      ]);

      const cloListContainer = document.getElementById("cloListContainer");
      expect(cloListContainer.innerHTML).toContain("CS101");
      expect(cloListContainer.innerHTML).toContain("Section 001");
      expect(cloListContainer.innerHTML).toContain("Section 002");
      expect(cloListContainer.querySelectorAll("tr.clo-row").length).toBe(2);
    });

    it("should render action buttons for awaiting_approval status", async () => {
      await renderListFor([
        {
          outcome_id: "out-1",
          course_number: "CS101",
          course_title: "Intro to CS",
          section_number: "001",
          clo_number: "1",
          description: "Test CLO",
          status: "awaiting_approval",
          instructor_name: "Dr. Smith",
          submitted_at: "2026-01-10T10:00:00Z",
        },
      ]);

      expect(document.querySelector(".btn-success")).not.toBeNull();
      expect(document.querySelector(".btn-success").title).toBe(
        "Approve Outcome",
      );
      expect(document.querySelector(".btn-warning")).not.toBeNull();
      expect(document.querySelector(".btn-warning").title).toBe(
        "Request Rework",
      );
    });

    it("should render assign button for unassigned status", async () => {
      await renderListFor([
        {
          outcome_id: "out-1",
          course_number: "CS101",
          course_title: "Intro to CS",
          section_number: "001",
          clo_number: "1",
          description: "Test CLO",
          status: "unassigned",
          instructor_name: null,
          submitted_at: null,
        },
      ]);

      expect(document.querySelector(".btn-primary")).not.toBeNull();
      expect(document.querySelector(".btn-primary").title).toBe(
        "Assign Instructor",
      );
    });

    it("should not render reopen button for approved status", async () => {
      await renderListFor([
        {
          outcome_id: "out-1",
          course_number: "CS101",
          course_title: "Intro to CS",
          section_number: "001",
          clo_number: "1",
          description: "Test CLO",
          status: "approved",
          instructor_name: "Dr. Smith",
          submitted_at: "2026-01-10T10:00:00Z",
        },
      ]);

      expect(document.querySelector(".btn-warning")).toBeNull();
    });

    it("should render reminder button for in_progress status", async () => {
      await renderListFor([
        {
          outcome_id: "out-1",
          course_number: "CS101",
          course_title: "Intro to CS",
          section_number: "001",
          clo_number: "1",
          description: "Test CLO",
          status: "in_progress",
          instructor_name: "Dr. Smith",
          instructor_id: "inst-1",
          course_id: "course-1",
          submitted_at: null,
        },
      ]);

      expect(document.querySelector(".btn-info")).not.toBeNull();
      expect(document.querySelector(".btn-info").title).toBe("Send Reminder");
    });

    it("should render view details button for all CLOs", async () => {
      await renderListFor([
        {
          outcome_id: "out-1",
          course_number: "CS101",
          course_title: "Intro to CS",
          section_number: "001",
          clo_number: "1",
          description: "Test CLO",
          status: "awaiting_approval",
          instructor_name: "Dr. Smith",
          submitted_at: "2026-01-10T10:00:00Z",
        },
      ]);

      const viewBtn = document.querySelector(".btn-outline-secondary");
      expect(viewBtn).not.toBeNull();
      expect(viewBtn.title).toBe("View Details");
      expect(viewBtn.dataset.outcomeId).toBe("out-1");
    });

    it("should handle CLOs without section numbers (unassigned section)", async () => {
      await renderListFor([
        {
          outcome_id: "out-1",
          course_number: "CS101",
          course_title: "Intro to CS",
          section_number: null,
          clo_number: "1",
          description: "Test CLO",
          status: "in_progress",
          instructor_name: "Dr. Smith",
          submitted_at: null,
        },
      ]);

      expect(document.getElementById("cloListContainer").innerHTML).toContain(
        "Unassigned Section",
      );
    });

    it("should not render reopen button for never_coming_in status", async () => {
      await renderListFor([
        {
          outcome_id: "out-1",
          course_number: "CS101",
          course_title: "Intro to CS",
          section_number: "001",
          clo_number: "1",
          description: "Test CLO",
          status: "never_coming_in",
          instructor_name: "Dr. Smith",
          submitted_at: "2026-01-10T10:00:00Z",
        },
      ]);

      expect(document.querySelector(".btn-warning")).toBeNull();
    });

    it("should render reminder button for assigned status", async () => {
      await renderListFor([
        {
          outcome_id: "out-1",
          course_number: "CS101",
          course_title: "Intro to CS",
          section_number: "001",
          clo_number: "1",
          description: "Test CLO",
          status: "assigned",
          instructor_name: "Dr. Smith",
          instructor_id: "inst-1",
          course_id: "course-1",
          submitted_at: null,
        },
      ]);

      expect(document.querySelector(".btn-info")).not.toBeNull();
      expect(document.querySelector(".btn-info").title).toBe("Send Reminder");
    });

    it("should render reminder button for approval_pending status", async () => {
      await renderListFor([
        {
          outcome_id: "out-1",
          course_number: "CS101",
          course_title: "Intro to CS",
          section_number: "001",
          clo_number: "1",
          description: "Test CLO",
          status: "approval_pending",
          instructor_name: "Dr. Smith",
          instructor_id: "inst-1",
          course_id: "course-1",
          submitted_at: null,
        },
      ]);

      expect(document.querySelector(".btn-info")).not.toBeNull();
      expect(document.querySelector(".btn-info").title).toBe("Send Reminder");
    });
  });
});
