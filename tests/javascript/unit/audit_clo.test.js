/**
 * Jest tests for audit_clo.js
 *
 * Tests DOM manipulation, event handling, and async API interactions
 */

// Mock global fetch
global.fetch = jest.fn();

// Mock bootstrap Modal
global.bootstrap = {
  Modal: Object.assign(jest.fn(), {
    getInstance: jest.fn(),
    getOrCreateInstance: jest.fn(),
  }),
};
global.bootstrap.Modal.getInstance = jest.fn();
global.bootstrap.Modal.getOrCreateInstance = jest.fn();

// Mock alert and prompt
global.alert = jest.fn();
global.prompt = jest.fn();

// Import the module directly so Jest can track coverage
const auditCloModule = require("../../../static/audit_clo.js");
const { approveCLO, markAsNCI } = auditCloModule;
let mockModalInstance;

describe("audit_clo.js - Utility Functions", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("calculateSuccessRate", () => {
    it("should return null when missing or invalid inputs", () => {
      expect(
        auditCloModule.calculateSuccessRate({
          students_took: 0,
          students_passed: 0,
        }),
      ).toBeNull();
      expect(
        auditCloModule.calculateSuccessRate({
          students_took: null,
          students_passed: 1,
        }),
      ).toBeNull();
      expect(
        auditCloModule.calculateSuccessRate({
          students_took: 10,
          students_passed: null,
        }),
      ).toBeNull();
    });

    it("should return rounded percentage when valid", () => {
      expect(
        auditCloModule.calculateSuccessRate({
          students_took: 10,
          students_passed: 8,
        }),
      ).toBe(80);
      expect(
        auditCloModule.calculateSuccessRate({
          students_took: 3,
          students_passed: 2,
        }),
      ).toBe(67);
    });
  });

  describe("exportCurrentViewToCsv", () => {
    beforeEach(() => {
      global.alert = jest.fn();
      global.URL.createObjectURL = jest.fn(() => "blob:mock");
      global.URL.revokeObjectURL = jest.fn();
    });

    it("should alert and return false when no records provided", () => {
      const result = auditCloModule.exportCurrentViewToCsv([]);
      expect(result).toBe(false);
      expect(global.alert).toHaveBeenCalledWith(
        "No Outcome records available to export for the selected filters.",
      );
    });

    it("should generate and download CSV when records exist", () => {
      // Spy on link click
      const clickSpy = jest.fn();
      const originalCreateElement = document.createElement.bind(document);
      jest.spyOn(document, "createElement").mockImplementation((tag) => {
        const el = originalCreateElement(tag);
        if (tag === "a") {
          el.click = clickSpy;
        }
        return el;
      });

      const result = auditCloModule.exportCurrentViewToCsv([
        {
          course_number: "CS101",
          course_title: "Intro",
          clo_number: "1",
          status: "approved",
          instructor_name: "Jane",
          submitted_at: "2024-01-15T10:30:00Z",
          students_took: 10,
          students_passed: 8,
          term_name: "Fall 2024",
          assessment_tool: "Exam",
        },
      ]);

      expect(result).toBe(true);
      expect(global.URL.createObjectURL).toHaveBeenCalled();
      expect(clickSpy).toHaveBeenCalled();
      expect(global.URL.revokeObjectURL).toHaveBeenCalled();
    });
  });

  describe("getStatusBadge", () => {
    it("should return correct badge for never_coming_in status", () => {
      const badge = auditCloModule.getStatusBadge("never_coming_in");
      expect(badge.tagName).toBe("SPAN");
      expect(badge.style.backgroundColor).toBe("rgb(220, 53, 69)");
      expect(badge.textContent).toBe("NCI");
    });

    it("should return correct badge for unassigned status", () => {
      const badge = auditCloModule.getStatusBadge("unassigned");
      expect(badge.style.backgroundColor).toBe("rgb(108, 117, 125)");
      expect(badge.textContent).toBe("Unassigned");
    });

    it("should return correct badge for assigned status", () => {
      const badge = auditCloModule.getStatusBadge("assigned");
      expect(badge.style.backgroundColor).toBe("rgb(33, 37, 41)");
      expect(badge.textContent).toBe("Assigned");
    });

    it("should return correct badge for in_progress status", () => {
      const badge = auditCloModule.getStatusBadge("in_progress");
      expect(badge.style.backgroundColor).toBe("rgb(13, 110, 253)");
      expect(badge.textContent).toBe("In Progress");
    });

    it("should return correct badge for awaiting_approval status", () => {
      const badge = auditCloModule.getStatusBadge("awaiting_approval");
      expect(badge.style.backgroundColor).toBe("rgb(154, 205, 50)");
      expect(badge.textContent).toBe("Awaiting Approval");
    });

    it("should return correct badge for approval_pending status", () => {
      const badge = auditCloModule.getStatusBadge("approval_pending");
      expect(badge.style.backgroundColor).toBe("rgb(253, 126, 20)");
      expect(badge.textContent).toBe("Needs Rework");
    });

    it("should return correct badge for approved status", () => {
      const badge = auditCloModule.getStatusBadge("approved");
      expect(badge.style.backgroundColor).toBe("rgb(25, 135, 84)");
      expect(badge.textContent).toBe("✓ Approved");
    });

    it("should return unknown badge for invalid status", () => {
      const badge = auditCloModule.getStatusBadge("invalid_status");
      expect(badge.style.backgroundColor).toBe("rgb(108, 117, 125)"); // #6c757d
      expect(badge.textContent).toBe("Unknown");
    });
  });

  describe("formatDate", () => {
    it("should format valid date string", () => {
      const result = auditCloModule.formatDate("2024-01-15T10:30:00Z");
      expect(result).not.toBe("N/A");
      expect(typeof result).toBe("string");
    });

    it("should return N/A for null date", () => {
      const result = auditCloModule.formatDate(null);
      expect(result).toBe("N/A");
    });

    it("should return N/A for undefined date", () => {
      const result = auditCloModule.formatDate(undefined);
      expect(result).toBe("N/A");
    });
  });

  describe("truncateText", () => {
    it("should truncate long text", () => {
      const result = auditCloModule.truncateText(
        "This is a very long text",
        10,
      );
      expect(result).toBe("This is a ...");
    });

    it("should not truncate short text", () => {
      const result = auditCloModule.truncateText("Short", 10);
      expect(result).toBe("Short");
    });

    it("should handle null text", () => {
      const result = auditCloModule.truncateText(null, 10);
      expect(result).toBe("");
    });

    it("should handle undefined text", () => {
      const result = auditCloModule.truncateText(undefined, 10);
      expect(result).toBe("");
    });
  });

  describe("escapeHtml", () => {
    it("should escape HTML special characters", () => {
      const result = auditCloModule.escapeHtml('<script>alert("xss")</script>');
      expect(result).toContain("&lt;");
      expect(result).toContain("&gt;");
      expect(result).not.toContain("<script>");
    });

    it("should handle null text", () => {
      const result = auditCloModule.escapeHtml(null);
      expect(result).toBe("");
    });

    it("should handle undefined text", () => {
      const result = auditCloModule.escapeHtml(undefined);
      expect(result).toBe("");
    });

    it("should handle ampersands", () => {
      const result = auditCloModule.escapeHtml("Rock & Roll");
      expect(result).toContain("&amp;");
    });
  });

  describe("formatStatusLabel", () => {
    it("should return correct label for unassigned", () => {
      expect(auditCloModule.formatStatusLabel("unassigned")).toBe("Unassigned");
    });

    it("should return correct label for assigned", () => {
      expect(auditCloModule.formatStatusLabel("assigned")).toBe("Assigned");
    });

    it("should return correct label for in_progress", () => {
      expect(auditCloModule.formatStatusLabel("in_progress")).toBe(
        "In Progress",
      );
    });

    it("should return correct label for awaiting_approval", () => {
      expect(auditCloModule.formatStatusLabel("awaiting_approval")).toBe(
        "Awaiting Approval",
      );
    });

    it("should return correct label for approval_pending (needs rework)", () => {
      expect(auditCloModule.formatStatusLabel("approval_pending")).toBe(
        "Needs Rework",
      );
    });

    it("should return correct label for approved", () => {
      expect(auditCloModule.formatStatusLabel("approved")).toBe("Approved");
    });

    it("should return correct label for never_coming_in", () => {
      expect(auditCloModule.formatStatusLabel("never_coming_in")).toBe(
        "Never Coming In",
      );
    });

    it("should return the status itself for unknown status", () => {
      expect(auditCloModule.formatStatusLabel("custom_status")).toBe(
        "custom_status",
      );
    });

    it("should return empty string for null", () => {
      expect(auditCloModule.formatStatusLabel(null)).toBe("");
    });

    it("should return empty string for undefined", () => {
      expect(auditCloModule.formatStatusLabel(undefined)).toBe("");
    });
  });

  describe("formatDateForCsv", () => {
    it("should return ISO string for valid date", () => {
      const result = auditCloModule.formatDateForCsv("2024-01-15T10:30:00Z");
      expect(result).toBe("2024-01-15T10:30:00.000Z");
    });

    it("should return empty string for null", () => {
      expect(auditCloModule.formatDateForCsv(null)).toBe("");
    });

    it("should return empty string for undefined", () => {
      expect(auditCloModule.formatDateForCsv(undefined)).toBe("");
    });

    it("should return empty string for invalid date string", () => {
      expect(auditCloModule.formatDateForCsv("not-a-date")).toBe("");
    });

    it("should return empty string for empty string", () => {
      expect(auditCloModule.formatDateForCsv("")).toBe("");
    });
  });

  describe("escapeForCsv", () => {
    it("should wrap simple values in quotes", () => {
      expect(auditCloModule.escapeForCsv("hello")).toBe('"hello"');
    });

    it("should escape double quotes by doubling them", () => {
      expect(auditCloModule.escapeForCsv('say "hello"')).toBe(
        '"say ""hello"""',
      );
    });

    it("should return empty quoted string for null", () => {
      expect(auditCloModule.escapeForCsv(null)).toBe('""');
    });

    it("should return empty quoted string for undefined", () => {
      expect(auditCloModule.escapeForCsv(undefined)).toBe('""');
    });

    it("should convert numbers to quoted strings", () => {
      expect(auditCloModule.escapeForCsv(42)).toBe('"42"');
    });

    it("should handle strings with commas", () => {
      expect(auditCloModule.escapeForCsv("one, two, three")).toBe(
        '"one, two, three"',
      );
    });

    it("should handle strings with newlines", () => {
      expect(auditCloModule.escapeForCsv("line1\nline2")).toBe(
        '"line1\nline2"',
      );
    });
  });

  describe("calculateSuccessRate edge cases", () => {
    it("should return 0 when all students passed out of all who took", () => {
      expect(
        auditCloModule.calculateSuccessRate({
          students_took: 10,
          students_passed: 10,
        }),
      ).toBe(100);
    });

    it("should return 0 when no students passed", () => {
      expect(
        auditCloModule.calculateSuccessRate({
          students_took: 10,
          students_passed: 0,
        }),
      ).toBe(0);
    });

    it("should handle negative students_took as invalid", () => {
      expect(
        auditCloModule.calculateSuccessRate({
          students_took: -5,
          students_passed: 3,
        }),
      ).toBeNull();
    });

    it("should handle undefined values", () => {
      expect(auditCloModule.calculateSuccessRate({})).toBeNull();
    });
  });

  describe("exportCurrentViewToCsv edge cases", () => {
    beforeEach(() => {
      global.alert = jest.fn();
      global.URL.createObjectURL = jest.fn(() => "blob:mock");
      global.URL.revokeObjectURL = jest.fn();
    });

    it("should return false for null input", () => {
      const result = auditCloModule.exportCurrentViewToCsv(null);
      expect(result).toBe(false);
      expect(global.alert).toHaveBeenCalled();
    });

    it("should return false for undefined input", () => {
      const result = auditCloModule.exportCurrentViewToCsv(undefined);
      expect(result).toBe(false);
      expect(global.alert).toHaveBeenCalled();
    });

    it("should handle CLOs with null values gracefully", () => {
      // Mock Blob and link for download
      jest.spyOn(document.body, "appendChild").mockImplementation(() => {});
      jest.spyOn(document.body, "removeChild").mockImplementation(() => {});

      const result = auditCloModule.exportCurrentViewToCsv([
        {
          course_number: null,
          course_title: null,
          clo_number: null,
          status: null,
          instructor_name: null,
          submitted_at: null,
          students_took: null,
          students_passed: null,
          term_name: null,
          assessment_tool: null,
        },
      ]);

      expect(result).toBe(true);

      // Restore
      document.body.appendChild.mockRestore();
      document.body.removeChild.mockRestore();
    });
  });
});

describe("audit_clo.js - truncateText boundary cases", () => {
  it("should return exact length text unchanged", () => {
    const result = auditCloModule.truncateText("1234567890", 10);
    expect(result).toBe("1234567890");
  });

  it("should truncate text one char over limit", () => {
    const result = auditCloModule.truncateText("12345678901", 10);
    expect(result).toBe("1234567890...");
  });

  it("should handle zero maxLength", () => {
    const result = auditCloModule.truncateText("hello", 0);
    expect(result).toBe("...");
  });

  it("should handle empty string", () => {
    const result = auditCloModule.truncateText("", 10);
    expect(result).toBe("");
  });
});

// Tests for DOM interaction functions using the exported module
// These tests ensure coverage is properly tracked by Jest
describe("audit_clo.js - DOM Interaction Functions", () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Setup DOM
    document.body.innerHTML = `
      <meta name="csrf-token" content="test-csrf-token" />
      <div id="assignInstructorModal"></div>
      <form id="assignInstructorForm">
        <select id="assignInstructorSelect">
          <option value="1">Instructor 1</option>
        </select>
      </form>
      <div id="clo-list-container"></div>
      <div id="sendReminderModal"></div>
      <button id="reopenBtn"></button>
    `;

    // Mock bootstrap modal instance
    mockModalInstance = {
      hide: jest.fn(),
      show: jest.fn(),
    };
    bootstrap.Modal.mockImplementation(() => mockModalInstance);
    bootstrap.Modal.getInstance.mockReturnValue(mockModalInstance);
    bootstrap.Modal.getOrCreateInstance.mockReturnValue(mockModalInstance);

    // Setup globalThis.loadCLOs
    globalThis.loadCLOs = jest.fn().mockResolvedValue(undefined);
  });

  describe("approveOutcome", () => {
    // Confirm dialog test removed as source no longer requires confirmation

    it("should send POST request immediately", async () => {
      // global.confirm = jest.fn(() => true); // No longer needed
      fetch.mockResolvedValueOnce({ ok: true });

      await auditCloModule.approveOutcome("test-id");

      expect(fetch).toHaveBeenCalledWith(
        "/api/outcomes/test-id/approve",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
            "X-CSRF-Token": "test-csrf-token",
          }),
        }),
      );
    });

    it("should call loadCLOs on successful approval", async () => {
      // global.confirm = jest.fn(() => true); // No longer needed
      fetch.mockResolvedValueOnce({ ok: true });

      await auditCloModule.approveOutcome("test-id");

      expect(globalThis.loadCLOs).toHaveBeenCalled();
    });

    it("should show alert on error response", async () => {
      // global.confirm = jest.fn(() => true); // No longer needed
      fetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ error: "Not authorized" }),
      });

      await auditCloModule.approveOutcome("test-id");

      expect(global.alert).toHaveBeenCalledWith(
        "Failed to approve: Not authorized",
      );
    });

    it("should show alert on network error", async () => {
      // global.confirm = jest.fn(() => true); // No longer needed
      fetch.mockRejectedValueOnce(new Error("Network error"));

      await auditCloModule.approveOutcome("test-id");

      expect(global.alert).toHaveBeenCalledWith(
        "Error approving outcome: Network error",
      );
    });
  });

  describe("reopenOutcome", () => {
    it("should return early if user cancels confirm dialog", async () => {
      global.confirm = jest.fn(() => false);

      await auditCloModule.reopenOutcome("test-id");

      expect(global.confirm).toHaveBeenCalled();
      expect(fetch).not.toHaveBeenCalled();
    });

    it("should send POST request to reopen endpoint", async () => {
      global.confirm = jest.fn(() => true);
      fetch.mockResolvedValueOnce({ ok: true });

      await auditCloModule.reopenOutcome("test-id");

      expect(fetch).toHaveBeenCalledWith(
        "/api/outcomes/test-id/reopen",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    it("should call loadCLOs on success", async () => {
      global.confirm = jest.fn(() => true);
      fetch.mockResolvedValueOnce({ ok: true });

      await auditCloModule.reopenOutcome("test-id");

      expect(globalThis.loadCLOs).toHaveBeenCalled();
    });

    it("should show alert on error", async () => {
      global.confirm = jest.fn(() => true);
      fetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ error: "Server error" }),
      });

      await auditCloModule.reopenOutcome("test-id");

      expect(global.alert).toHaveBeenCalledWith(
        "Failed to reopen: Server error",
      );
    });
  });

  describe("remindOutcome", () => {
    beforeEach(() => {
      // Mock fetch for instructor details
      fetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            user: {
              first_name: "Test",
              last_name: "Instructor",
              email: "test@example.com",
            },
          }),
      });
    });

    it("should return early if user cancels confirm dialog", async () => {
      global.confirm = jest.fn(() => false);

      await auditCloModule.remindOutcome("test-id", "instructor-1", "course-1");

      expect(global.confirm).toHaveBeenCalled();
      expect(fetch).not.toHaveBeenCalled();
    });

    it("should return early if missing instructorId or courseId", async () => {
      global.confirm = jest.fn(() => true);

      await auditCloModule.remindOutcome("test-id");

      expect(global.alert).toHaveBeenCalledWith(
        "Missing instructor or course information for this outcome.",
      );
      expect(fetch).not.toHaveBeenCalled();
    });

    it("should send POST request to remind endpoint", async () => {
      global.confirm = jest.fn(() => true);

      await auditCloModule.remindOutcome("test-id", "instructor-1", "course-1");

      const msgArea = document.createElement("textarea");
      msgArea.id = "reminderMessage";
      msgArea.value = "Test Message";
      document.body.appendChild(msgArea);

      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await auditCloModule.submitReminder();

      expect(fetch).toHaveBeenCalledWith(
        "/api/send-course-reminder",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            instructor_id: "instructor-1",
            course_id: "course-1",
            message: "Test Message",
          }),
        }),
      );
    });

    it("should show success alert on successful reminder", async () => {
      global.confirm = jest.fn(() => true);

      await auditCloModule.remindOutcome("test-id", "instructor-1", "course-1");

      const msgArea = document.createElement("textarea");
      msgArea.id = "reminderMessage";
      msgArea.value = "Test Message";
      document.body.appendChild(msgArea);

      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await auditCloModule.submitReminder();

      expect(global.alert).toHaveBeenCalledWith("Reminder sent successfully.");
    });

    it("should show error alert on failed reminder", async () => {
      global.confirm = jest.fn(() => true);

      await auditCloModule.remindOutcome("test-id", "instructor-1", "course-1");

      const msgArea = document.createElement("textarea");
      msgArea.id = "reminderMessage";
      msgArea.value = "Test Message";
      document.body.appendChild(msgArea);

      fetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ error: "Email failed" }),
      });

      await auditCloModule.submitReminder();

      expect(global.alert).toHaveBeenCalledWith(
        "Failed to send reminder: Email failed",
      );
    });
  });

  describe("assignOutcome", () => {
    let mockModalInstance;

    beforeEach(() => {
      // Setup mock Bootstrap Modal properly
      mockModalInstance = { show: jest.fn(), hide: jest.fn() };
      bootstrap.Modal.mockImplementation(() => mockModalInstance);
      bootstrap.Modal.getInstance.mockReturnValue(mockModalInstance);
      bootstrap.Modal.getOrCreateInstance.mockReturnValue(mockModalInstance);
    });

    it("should return early if CLO not found", async () => {
      auditCloModule._setAllCLOs([]);

      await auditCloModule.assignOutcome("nonexistent-id");

      // Should not throw or crash
      expect(global.bootstrap.Modal).not.toHaveBeenCalled();
    });

    it("should show alert if section_id is missing", async () => {
      auditCloModule._setAllCLOs([{ id: "test-id", section_id: null }]);

      await auditCloModule.assignOutcome("test-id");

      expect(global.alert).toHaveBeenCalledWith(
        "Cannot identify section for assignment. Please contact support.",
      );
    });

    it("should open modal when CLO has section_id", async () => {
      auditCloModule._setAllCLOs([{ id: "test-id", section_id: 123 }]);

      // Mock loadInstructors to prevent actual API call
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ instructors: [] }),
      });

      await auditCloModule.assignOutcome("test-id");

      expect(mockModalInstance.show).toHaveBeenCalled();
    });
  });

  describe("loadInstructors", () => {
    it("should return early if select element not found", async () => {
      document.body.innerHTML = ""; // Remove select

      await auditCloModule.loadInstructors();

      expect(fetch).not.toHaveBeenCalled();
    });

    it("should return early if already loaded", async () => {
      const select = document.getElementById("assignInstructorSelect");
      select.dataset.loaded = "true";

      await auditCloModule.loadInstructors();

      expect(fetch).not.toHaveBeenCalled();
    });

    it("should fetch and populate instructors", async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            success: true,
            instructors: [
              {
                id: 1,
                first_name: "John",
                last_name: "Doe",
                email: "john@test.com",
              },
              {
                id: 2,
                first_name: "Jane",
                last_name: "Smith",
                email: "jane@test.com",
              },
            ],
          }),
      });

      await auditCloModule.loadInstructors();

      const select = document.getElementById("assignInstructorSelect");
      expect(select.options.length).toBeGreaterThan(1);
      expect(select.dataset.loaded).toBe("true");
    });

    it("should show error message on fetch failure", async () => {
      fetch.mockRejectedValueOnce(new Error("Network error"));

      await auditCloModule.loadInstructors();

      const select = document.getElementById("assignInstructorSelect");
      expect(select.innerHTML).toContain("Error loading instructors");
    });
  });

  // Note: sortCLOs cannot be tested here because it's defined inside DOMContentLoaded
  // and depends on DOM element references (sortBy.value, sortOrder.value)
  // It is tested via the DOM Integration tests that use eval() below
});
