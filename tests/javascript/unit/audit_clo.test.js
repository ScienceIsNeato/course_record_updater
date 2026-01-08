/**
 * Jest tests for audit_clo.js
 *
 * Tests DOM manipulation, event handling, and async API interactions
 */

// Mock global fetch
global.fetch = jest.fn();

// Mock bootstrap Modal
global.bootstrap = {
  Modal: {
    getInstance: jest.fn(),
    getOrCreateInstance: jest.fn(),
  },
};

// Mock alert and prompt
global.alert = jest.fn();
global.prompt = jest.fn();

// Import the module directly so Jest can track coverage
const auditCloModule = require("../../../static/audit_clo.js");
const { approveCLO, markAsNCI } = auditCloModule;

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
        "No CLO records available to export for the selected filters.",
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
  });
});

describe("audit_clo.js - DOM Integration", () => {
  let statusFilter, sortBy, sortOrder, cloListContainer;
  let programFilter, termFilter, exportButton;
  let cloDetailModal, requestReworkModal, requestReworkForm;
  let mockModalInstance;

  beforeEach(() => {
    // Reset DOM
    document.body.innerHTML = `
      <meta name="csrf-token" content="test-csrf-token">
      <select id="statusFilter"></select>
      <select id="sortBy"></select>
      <select id="sortOrder"></select>
      <select id="programFilter"></select>
      <select id="termFilter"></select>
      <button id="exportCsvBtn"></button>
      <div id="cloListContainer"></div>
      <div id="cloDetailModal">
        <div id="cloDetailContent"></div>
        <button id="approveBtn" style="display: none;"></button>
        <button id="requestReworkBtn" style="display: none;"></button>
        <button id="markNCIBtn" style="display: none;"></button>
      </div>
      <div id="requestReworkModal">
        <form id="requestReworkForm">
          <div id="reworkCloDescription"></div>
          <textarea id="feedbackComments"></textarea>
          <input type="checkbox" id="sendEmailCheckbox" checked>
        </form>
      </div>
      <span id="statAwaitingApproval">0</span>
      <span id="statNeedsRework">0</span>
      <span id="statApproved">0</span>
      <span id="statInProgress">0</span>
      <span id="statNCI">0</span>
    `;

    statusFilter = document.getElementById("statusFilter");
    sortBy = document.getElementById("sortBy");
    sortOrder = document.getElementById("sortOrder");
    programFilter = document.getElementById("programFilter");
    termFilter = document.getElementById("termFilter");
    exportButton = document.getElementById("exportCsvBtn");
    cloListContainer = document.getElementById("cloListContainer");
    cloDetailModal = document.getElementById("cloDetailModal");
    requestReworkModal = document.getElementById("requestReworkModal");
    requestReworkForm = document.getElementById("requestReworkForm");

    // Mock bootstrap modal instance
    mockModalInstance = {
      hide: jest.fn(),
      show: jest.fn(),
    };
    bootstrap.Modal.getInstance.mockReturnValue(mockModalInstance);
    bootstrap.Modal.getOrCreateInstance.mockReturnValue(mockModalInstance);

    // Clear all mocks
    jest.clearAllMocks();
    fetch.mockClear();
    alert.mockClear();
    prompt.mockClear();

    // Mock successful default fetch responses
    fetch.mockImplementation((url) => {
      if (url === "/api/programs") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ programs: [{ id: "p1", name: "CS" }] }),
        });
      }
      if (url === "/api/terms") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              terms: [
                {
                  term_id: "t1",
                  term_name: "Fall 2024",
                  start_date: "2024-08-01",
                },
              ],
            }),
        });
      }
      if (url.includes("/api/outcomes/audit?status=")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ count: 5, outcomes: [] }),
        });
      }
      if (url.includes("/api/outcomes/")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      });
    });
  });

  test("should wire export button to exportCurrentViewToCsv (alerts when no outcomes)", async () => {
    // Load the script to trigger DOMContentLoaded
    jest.resetModules();
    require("../../../static/audit_clo.js");

    // Trigger DOMContentLoaded
    document.dispatchEvent(new Event("DOMContentLoaded"));

    exportButton.click();
    expect(alert).toHaveBeenCalledWith(
      "No CLO records available to export for the selected filters.",
    );
  });

  describe("updateStats", () => {
    it("should fetch and update all statistics including NCI", async () => {
      // Mock fetch responses for each status
      fetch.mockImplementation((url) => {
        if (url.includes("awaiting_approval")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ count: 12 }),
          });
        }
        if (url.includes("approval_pending")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ count: 7 }),
          });
        }
        if (url.includes("approved")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ count: 45 }),
          });
        }
        if (url.includes("in_progress")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ count: 23 }),
          });
        }
        if (url.includes("never_coming_in")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ count: 3 }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ count: 0 }),
        });
      });

      // Load the script to trigger DOMContentLoaded
      const fs = require("fs");
      const path = require("path");
      const auditCloCode = fs.readFileSync(
        path.join(__dirname, "../../../static/audit_clo.js"),
        "utf8",
      );
      eval(auditCloCode);

      // Trigger DOMContentLoaded
      const event = new Event("DOMContentLoaded");
      document.dispatchEvent(event);

      // Wait for async updateStats to complete
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Verify all fetch calls were made
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("awaiting_approval"),
      );
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("approval_pending"),
      );
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining("approved"));
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("in_progress"),
      );
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("never_coming_in"),
      );

      // Verify DOM updates
      expect(document.getElementById("statAwaitingApproval").textContent).toBe(
        "12",
      );
      expect(document.getElementById("statNeedsRework").textContent).toBe("7");
      expect(document.getElementById("statApproved").textContent).toBe("45");
      expect(document.getElementById("statInProgress").textContent).toBe("23");
      expect(document.getElementById("statNCI").textContent).toBe("3");
    });

    it("should handle individual status fetch failures and show 0", async () => {
      const consoleWarnSpy = jest
        .spyOn(console, "warn")
        .mockImplementation(() => { });

      // Clear previous state
      fetch.mockClear();

      // Mock fetch - some succeed, some fail
      fetch.mockImplementation((url) => {
        if (url.includes("awaiting_approval")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ count: 5 }),
          });
        }
        if (url.includes("approval_pending")) {
          // This one fails with HTTP error
          return Promise.resolve({
            ok: false,
            status: 500,
            statusText: "Internal Server Error",
          });
        }
        if (url.includes("approved")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ count: 10 }),
          });
        }
        // Others succeed with 0
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ count: 0 }),
        });
      });

      // Load the script
      const fs = require("fs");
      const path = require("path");
      const auditCloCode = fs.readFileSync(
        path.join(__dirname, "../../../static/audit_clo.js"),
        "utf8",
      );
      eval(auditCloCode);

      // Trigger DOMContentLoaded
      const event = new Event("DOMContentLoaded");
      document.dispatchEvent(event);

      // Wait for async operations
      await new Promise((resolve) => setTimeout(resolve, 150));

      // Should log warning for failed status
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        "Failed to fetch stats for status:",
        "approval_pending",
        expect.any(String),
      );

      // Successful stats should be updated
      expect(document.getElementById("statAwaitingApproval").textContent).toBe(
        "5",
      );
      expect(document.getElementById("statApproved").textContent).toBe("10");

      // Failed status should show 0
      expect(document.getElementById("statNeedsRework").textContent).toBe("0");

      consoleWarnSpy.mockRestore();
    });
  });

  describe("showCLODetails - Action Button Visibility", () => {
    beforeEach(() => {
      // Setup window.showCLODetails by loading the script
      const fs = require("fs");
      const path = require("path");
      const auditCloCode = fs.readFileSync(
        path.join(__dirname, "../../../static/audit_clo.js"),
        "utf8",
      );
      eval(auditCloCode);

      // Trigger DOMContentLoaded to initialize
      const event = new Event("DOMContentLoaded");
      document.dispatchEvent(event);
    });

    it("should show NCI button for awaiting_approval status", async () => {
      const mockCLO = {
        outcome: {
          outcome_id: "test-123",
          course_number: "CS101",
          clo_number: 1,
          description: "Test CLO",
          status: "awaiting_approval",
          submitted_at: "2024-01-15T10:00:00Z",
          assessment_data: {
            students_assessed: 30,
            students_meeting_target: 25,
          },
        },
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCLO),
      });

      await window.showCLODetails("test-123");

      const markNCIBtn = document.getElementById("markNCIBtn");
      expect(markNCIBtn.style.display).toBe("inline-block");
    });

    it("should show NCI button for approval_pending status", async () => {
      const mockCLO = {
        outcome: {
          outcome_id: "test-123",
          course_number: "CS101",
          clo_number: 1,
          description: "Test CLO",
          status: "approval_pending",
          submitted_at: "2024-01-15T10:00:00Z",
          assessment_data: {
            students_assessed: 30,
            students_meeting_target: 25,
          },
        },
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCLO),
      });

      await window.showCLODetails("test-123");

      const markNCIBtn = document.getElementById("markNCIBtn");
      expect(markNCIBtn.style.display).toBe("inline-block");
    });

    it("should show NCI button for assigned status", async () => {
      const mockCLO = {
        outcome: {
          outcome_id: "test-123",
          course_number: "CS101",
          clo_number: 1,
          description: "Test CLO",
          status: "assigned",
          submitted_at: "2024-01-15T10:00:00Z",
          assessment_data: {
            students_assessed: 30,
            students_meeting_target: 25,
          },
        },
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCLO),
      });

      await window.showCLODetails("test-123");

      const markNCIBtn = document.getElementById("markNCIBtn");
      expect(markNCIBtn.style.display).toBe("inline-block");
    });

    it("should show NCI button for in_progress status", async () => {
      const mockCLO = {
        outcome: {
          outcome_id: "test-123",
          course_number: "CS101",
          clo_number: 1,
          description: "Test CLO",
          status: "in_progress",
          submitted_at: "2024-01-15T10:00:00Z",
          assessment_data: {
            students_assessed: 30,
            students_meeting_target: 25,
          },
        },
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCLO),
      });

      await window.showCLODetails("test-123");

      const markNCIBtn = document.getElementById("markNCIBtn");
      expect(markNCIBtn.style.display).toBe("inline-block");
    });

    it("should hide NCI button for approved status", async () => {
      const mockCLO = {
        outcome: {
          outcome_id: "test-123",
          course_number: "CS101",
          clo_number: 1,
          description: "Test CLO",
          status: "approved",
          submitted_at: "2024-01-15T10:00:00Z",
          approved_at: "2024-01-16T10:00:00Z",
          assessment_data: {
            students_assessed: 30,
            students_meeting_target: 25,
          },
        },
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCLO),
      });

      await window.showCLODetails("test-123");

      const markNCIBtn = document.getElementById("markNCIBtn");
      expect(markNCIBtn.style.display).toBe("none");
    });
  });

  describe("markAsNCI", () => {
    beforeEach(() => {
      // Setup window.currentCLO and mock functions
      global.window.currentCLO = {
        outcome_id: "test-123",
        course_number: "CS101",
        clo_number: 1,
      };
      global.window.loadCLOs = jest.fn(() => Promise.resolve());
      global.window.updateStats = jest.fn(() => Promise.resolve());

      // Clear mocks
      jest.clearAllMocks();
      fetch.mockClear();
      alert.mockClear();
      prompt.mockClear();
    });

    it("should mark CLO as NCI with reason", async () => {
      // Mock prompt to return a reason
      prompt.mockReturnValue("Instructor left institution");

      // Mock successful NCI request
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await markAsNCI();

      // Verify prompt was called
      expect(prompt).toHaveBeenCalledWith(
        expect.stringContaining("Never Coming In"),
      );

      // Verify API call
      expect(fetch).toHaveBeenCalledWith(
        "/api/outcomes/test-123/mark-nci",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
            "X-CSRF-Token": "test-csrf-token",
          }),
          body: JSON.stringify({ reason: "Instructor left institution" }),
        }),
      );

      // Verify modal closed
      expect(mockModalInstance.hide).toHaveBeenCalled();

      // Verify success alert
      expect(alert).toHaveBeenCalledWith("CLO marked as Never Coming In (NCI)");

      // Verify reload functions called
      expect(global.window.loadCLOs).toHaveBeenCalled();
      expect(global.window.updateStats).toHaveBeenCalled();
    });

    it("should mark CLO as NCI without reason (empty string)", async () => {
      // Mock prompt to return empty string
      prompt.mockReturnValue("");

      // Mock successful NCI request
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await markAsNCI();

      // Verify API call with null reason
      expect(fetch).toHaveBeenCalledWith(
        "/api/outcomes/test-123/mark-nci",
        expect.objectContaining({
          body: JSON.stringify({ reason: null }),
        }),
      );
    });

    it("should not mark CLO as NCI if prompt is cancelled", async () => {
      // Mock prompt to return null (cancelled)
      prompt.mockReturnValue(null);

      await markAsNCI();

      // Verify no API call was made
      expect(fetch).not.toHaveBeenCalled();

      // Verify no alert
      expect(alert).not.toHaveBeenCalled();
    });

    it("should handle API error when marking as NCI", async () => {
      // Mock prompt
      prompt.mockReturnValue("Test reason");

      // Mock failed NCI request
      fetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ error: "Database error" }),
      });

      await markAsNCI();

      // Verify error alert
      expect(alert).toHaveBeenCalledWith(
        "Failed to mark CLO as NCI: Database error",
      );

      // Verify modal was not closed
      expect(mockModalInstance.hide).not.toHaveBeenCalled();
    });

    it("should handle network error when marking as NCI", async () => {
      // Mock prompt
      prompt.mockReturnValue("Test reason");

      // Mock network error
      fetch.mockRejectedValueOnce(new Error("Network error"));

      await markAsNCI();

      // Verify error alert
      expect(alert).toHaveBeenCalledWith(
        "Failed to mark CLO as NCI: Network error",
      );
    });

    it("should trim whitespace from reason", async () => {
      // Mock prompt with whitespace
      prompt.mockReturnValue("  Reason with spaces  ");

      // Mock successful NCI request
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await markAsNCI();

      // Verify trimmed reason
      expect(fetch).toHaveBeenCalledWith(
        "/api/outcomes/test-123/mark-nci",
        expect.objectContaining({
          body: JSON.stringify({ reason: "Reason with spaces" }),
        }),
      );
    });

    it("should do nothing if currentCLO is not set", async () => {
      // Clear window.currentCLO
      global.window.currentCLO = null;

      await markAsNCI();

      // Verify no prompt
      expect(prompt).not.toHaveBeenCalled();

      // Verify no API call
      expect(fetch).not.toHaveBeenCalled();
    });
  });

  describe("approveCLO", () => {
    beforeEach(() => {
      // Setup window.currentCLO and mock functions
      global.window.currentCLO = {
        outcome_id: "test-123",
        course_number: "CS101",
        clo_number: 1,
      };
      global.window.loadCLOs = jest.fn(() => Promise.resolve());
      global.confirm = jest.fn();

      // Clear mocks
      jest.clearAllMocks();
      fetch.mockClear();
      alert.mockClear();
      confirm.mockClear();
    });

    it("should approve CLO successfully", async () => {
      // Mock successful approve request
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await approveCLO();

      // Verify API call
      expect(fetch).toHaveBeenCalledWith(
        "/api/outcomes/test-123/approve",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
        }),
      );

      // Verify modal was closed
      expect(mockModalInstance.hide).toHaveBeenCalled();

      // Verify reload called
      expect(global.window.loadCLOs).toHaveBeenCalled();
    });

    it("should handle API error when approving", async () => {
      // Mock API error
      fetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ error: "Database error" }),
      });

      await approveCLO();

      // Verify error alert
      expect(alert).toHaveBeenCalledWith(
        "Failed to approve CLO: Database error",
      );

      // Verify modal was not closed
      expect(mockModalInstance.hide).not.toHaveBeenCalled();
    });

    it("should handle missing outcome_id", async () => {
      // Set currentCLO without outcome_id
      global.window.currentCLO = {
        course_number: "CS101",
        clo_number: 1,
      };

      await approveCLO();

      // Verify error alert
      expect(alert).toHaveBeenCalledWith("Error: CLO ID not found");

      // Verify no API call
      expect(fetch).not.toHaveBeenCalled();
    });
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

      // Verify structure and content
      expect(node.textContent).toContain("CS101");
      expect(node.textContent).toContain("Intro to CS");
      expect(node.textContent).toContain("1");
      expect(node.textContent).toContain("Demonstrate problem-solving skills");
      expect(node.textContent).toContain("Jane Doe");
      expect(node.textContent).toContain("jane@example.com");
      expect(node.textContent).toContain("30"); // students_took
      expect(node.textContent).toContain("27"); // students_passed
      expect(node.textContent).toContain("90%"); // percentage: 27/30 = 90%
      expect(node.textContent).toContain("Students Took");
      expect(node.textContent).toContain("Students Passed");
      expect(node.textContent).toContain("Success Rate");
    });

    it("should calculate 0% when students_took is 0", () => {
      const clo = {
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        students_took: 0,
        students_passed: 0,
      };

      const node = renderCLODetails(clo);

      expect(node.textContent).toContain("0%"); // 0/0 should be 0%
    });

    it("should handle null/undefined students_took and students_passed", () => {
      const clo = {
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        students_took: null,
        students_passed: undefined,
      };

      const node = renderCLODetails(clo);

      // Should default to 0
      expect(node.textContent).toContain("0%");
    });

    it("should round percentage correctly", () => {
      const clo = {
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        students_took: 30,
        students_passed: 25,
      };

      const node = renderCLODetails(clo);

      // 25/30 = 83.333... should round to 83%
      expect(node.textContent).toContain("83%");
    });

    it("should render status badge", () => {
      const clo = {
        status: "never_coming_in",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        students_took: 0,
        students_passed: 0,
      };

      const node = renderCLODetails(clo);

      expect(node.textContent).toContain("NCI");
      expect(node.querySelector(".badge").style.backgroundColor).toBe(
        "rgb(220, 53, 69)",
      );
    });

    it("should display N/A for missing course info", () => {
      const clo = {
        status: "awaiting_approval",
        clo_number: 1,
        description: "Test",
        students_took: 0,
        students_passed: 0,
      };

      const node = renderCLODetails(clo);

      expect(node.textContent).toContain("N/A");
    });

    it("should escape HTML in CLO description", () => {
      const clo = {
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: '<script>alert("XSS")</script>',
        students_took: 0,
        students_passed: 0,
      };

      const node = renderCLODetails(clo);

      // Should be escaped
      expect(node.innerHTML).not.toContain("<script>");
      expect(node.innerHTML).toContain("&lt;script&gt;");
    });

    it("should include narrative when present", () => {
      const clo = {
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        students_took: 0,
        students_passed: 0,
        narrative: "This is a detailed narrative about the assessment",
      };

      const node = renderCLODetails(clo);

      expect(node.textContent).toContain("Narrative:");
      expect(node.textContent).toContain(
        "This is a detailed narrative about the assessment",
      );
    });

    it("should exclude narrative when not present", () => {
      const clo = {
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        students_took: 0,
        students_passed: 0,
      };

      const node = renderCLODetails(clo);

      expect(node.textContent).not.toContain("Narrative:");
    });

    it("should include feedback_comments when present", () => {
      const clo = {
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        students_took: 0,
        students_passed: 0,
        feedback_comments: "Please revise the assessment data",
      };

      const node = renderCLODetails(clo);

      expect(node.textContent).toContain("Admin Feedback:");
      expect(node.textContent).toContain("Please revise the assessment data");
    });

    it("should include reviewed_by info when present", () => {
      const clo = {
        status: "approved",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        students_took: 30,
        students_passed: 27,
        reviewed_by_name: "Admin User",
        reviewed_at: "2025-11-05T10:30:00Z",
      };

      const node = renderCLODetails(clo);

      expect(node.textContent).toContain("Reviewed by Admin User");
    });

    it("should handle all special characters in instructor name and email", () => {
      const clo = {
        status: "awaiting_approval",
        course_number: "CS101",
        clo_number: 1,
        description: "Test",
        instructor_name: "Jane <Test> O'Brien & Co.",
        instructor_email: "jane+test@example.com",
        students_took: 0,
        students_passed: 0,
      };

      const node = renderCLODetails(clo);

      // HTML tags and ampersands should be escaped (textContent escapes <, >, &)
      expect(node.innerHTML).toContain("&lt;Test&gt;");
      expect(node.textContent).toContain("O'Brien"); // Single quotes are NOT escaped by textContent
      expect(node.innerHTML).toContain("&amp; Co.");
      // Email should be present
      expect(node.textContent).toContain("jane+test@example.com");
    });
  });
});

