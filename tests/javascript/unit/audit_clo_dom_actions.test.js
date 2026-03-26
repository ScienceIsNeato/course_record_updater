const auditCloModule = require("../../../static/audit_clo.js");
const { approveCLO, markAsNCI } = auditCloModule;
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

describe("audit_clo.js - DOM Integration Actions", () => {
  let exportButton;
  let mockModalInstance;

  beforeEach(() => {
    setupAuditCloDom();
    exportButton = document.getElementById("exportCsvBtn");
    mockModalInstance = createMockModalInstance();
    bootstrap.Modal.mockImplementation(() => mockModalInstance);
    bootstrap.Modal.getInstance.mockReturnValue(mockModalInstance);
    bootstrap.Modal.getOrCreateInstance.mockReturnValue(mockModalInstance);
    jest.clearAllMocks();
    fetch.mockClear();
    alert.mockClear();
    prompt.mockClear();
    installDefaultAuditFetch(fetch);
  });

  test("should wire export button to exportCurrentViewToCsv (alerts when no outcomes)", async () => {
    jest.resetModules();
    require("../../../static/audit_clo.js");
    document.dispatchEvent(new Event("DOMContentLoaded"));
    exportButton.click();
    expect(alert).toHaveBeenCalledWith(
      "No Outcome records available to export for the selected filters.",
    );
  });

  describe("updateStats", () => {
    it("should fetch and update all statistics including NCI", async () => {
      fetch.mockImplementation((url) => {
        if (url.includes("status=all&include_stats=true")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                success: true,
                outcomes: [],
                count: 0,
                stats_by_status: {
                  awaiting_approval: 12,
                  approval_pending: 7,
                  approved: 45,
                  in_progress: 23,
                  never_coming_in: 3,
                  assigned: 10,
                  unassigned: 5,
                },
              }),
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

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("status=all&include_stats=true"),
      );
      expect(document.getElementById("statAwaitingApproval").textContent).toBe(
        "12",
      );
      expect(document.getElementById("statNeedsRework").textContent).toBe("7");
      expect(document.getElementById("statApproved").textContent).toBe("45");
      expect(document.getElementById("statInProgress").textContent).toBe("23");
      expect(document.getElementById("statNCI").textContent).toBe("3");
    });

    it("should handle fetch failures gracefully and show 0 for all stats", async () => {
      const consoleWarnSpy = jest
        .spyOn(console, "warn")
        .mockImplementation(() => {});

      fetch.mockClear();
      fetch.mockImplementation((url) => {
        if (url.includes("status=all&include_stats=true")) {
          return Promise.resolve({
            ok: false,
            status: 500,
            statusText: "Internal Server Error",
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ programs: [], terms: [], courses: [] }),
        });
      });

      loadAuditCloViaEval();
      document.dispatchEvent(new Event("DOMContentLoaded"));
      await new Promise((resolve) => setTimeout(resolve, 150));

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining("Error updating dashboard stats"),
        expect.anything(),
      );
      consoleWarnSpy.mockRestore();
    });
  });

  describe("showCLODetails - Action Button Visibility", () => {
    beforeEach(() => {
      loadAuditCloViaEval();
      document.dispatchEvent(new Event("DOMContentLoaded"));
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
      expect(document.getElementById("markNCIBtn").style.display).toBe(
        "inline-block",
      );
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
      expect(document.getElementById("markNCIBtn").style.display).toBe(
        "inline-block",
      );
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
      expect(document.getElementById("markNCIBtn").style.display).toBe(
        "inline-block",
      );
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
      expect(document.getElementById("markNCIBtn").style.display).toBe(
        "inline-block",
      );
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
      expect(document.getElementById("markNCIBtn").style.display).toBe("none");
    });
  });

  describe("markAsNCI", () => {
    beforeEach(() => {
      global.window.currentCLO = {
        outcome_id: "test-123",
        course_number: "CS101",
        clo_number: 1,
      };
      global.window.loadCLOs = jest.fn(() => Promise.resolve());
      global.window.updateStats = jest.fn(() => Promise.resolve());
      mockModalInstance = createMockModalInstance();
      bootstrap.Modal.mockImplementation(() => mockModalInstance);
      bootstrap.Modal.getInstance.mockReturnValue(mockModalInstance);
      bootstrap.Modal.getOrCreateInstance.mockReturnValue(mockModalInstance);
      jest.clearAllMocks();
      fetch.mockClear();
      alert.mockClear();
      prompt.mockClear();
    });

    it("should mark CLO as NCI with reason", async () => {
      prompt.mockReturnValue("Instructor left institution");
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await markAsNCI();

      expect(prompt).toHaveBeenCalledWith(
        expect.stringContaining("Never Coming In"),
      );
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
      expect(mockModalInstance.hide).toHaveBeenCalled();
      expect(alert).toHaveBeenCalledWith(
        "Outcome marked as Never Coming In (NCI)",
      );
      expect(global.window.loadCLOs).toHaveBeenCalled();
      expect(global.window.updateStats).toHaveBeenCalled();
    });

    it("should mark CLO as NCI without reason (empty string)", async () => {
      prompt.mockReturnValue("");
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await markAsNCI();
      expect(fetch).toHaveBeenCalledWith(
        "/api/outcomes/test-123/mark-nci",
        expect.objectContaining({
          body: JSON.stringify({ reason: null }),
        }),
      );
    });

    it("should not mark CLO as NCI if prompt is cancelled", async () => {
      prompt.mockReturnValue(null);
      await markAsNCI();
      expect(fetch).not.toHaveBeenCalled();
      expect(alert).not.toHaveBeenCalled();
    });

    it("should handle API error when marking as NCI", async () => {
      prompt.mockReturnValue("Test reason");
      fetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ error: "Database error" }),
      });

      await markAsNCI();
      expect(alert).toHaveBeenCalledWith(
        "Failed to mark Outcome as NCI: Database error",
      );
      expect(mockModalInstance.hide).not.toHaveBeenCalled();
    });

    it("should handle network error when marking as NCI", async () => {
      prompt.mockReturnValue("Test reason");
      fetch.mockRejectedValueOnce(new Error("Network error"));

      await markAsNCI();
      expect(alert).toHaveBeenCalledWith(
        "Failed to mark Outcome as NCI: Network error",
      );
    });

    it("should trim whitespace from reason", async () => {
      prompt.mockReturnValue("  Reason with spaces  ");
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await markAsNCI();
      expect(fetch).toHaveBeenCalledWith(
        "/api/outcomes/test-123/mark-nci",
        expect.objectContaining({
          body: JSON.stringify({ reason: "Reason with spaces" }),
        }),
      );
    });

    it("should do nothing if currentCLO is not set", async () => {
      global.window.currentCLO = null;
      await markAsNCI();
      expect(prompt).not.toHaveBeenCalled();
      expect(fetch).not.toHaveBeenCalled();
    });
  });

  describe("approveCLO", () => {
    beforeEach(() => {
      global.window.currentCLO = {
        outcome_id: "test-123",
        course_number: "CS101",
        clo_number: 1,
      };
      global.window.loadCLOs = jest.fn(() => Promise.resolve());
      global.confirm = jest.fn();
      jest.clearAllMocks();
      fetch.mockClear();
      alert.mockClear();
      confirm.mockClear();
    });

    it("should approve CLO successfully", async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await approveCLO();

      expect(fetch).toHaveBeenCalledWith(
        "/api/outcomes/test-123/approve",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
        }),
      );
      expect(mockModalInstance.hide).toHaveBeenCalled();
      expect(global.window.loadCLOs).toHaveBeenCalled();
    });

    it("should handle API error when approving", async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ error: "Database error" }),
      });

      await approveCLO();
      expect(alert).toHaveBeenCalledWith(
        "Failed to approve Outcome: Database error",
      );
      expect(mockModalInstance.hide).not.toHaveBeenCalled();
    });

    it("should handle missing outcome_id", async () => {
      global.window.currentCLO = {
        course_number: "CS101",
        clo_number: 1,
      };

      await approveCLO();
      expect(alert).toHaveBeenCalledWith("Error: Outcome ID not found");
      expect(fetch).not.toHaveBeenCalled();
    });
  });
});
