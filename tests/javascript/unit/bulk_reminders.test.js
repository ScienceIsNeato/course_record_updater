const { BulkReminderManager } = require("../../../static/bulk_reminders");
const { setBody, flushPromises } = require("../helpers/dom");

describe("BulkReminderManager", () => {
  let bulkReminders;

  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        job_id: "job-123",
        recipient_count: 1,
      }),
    });
    window.dashboardDataCache = null;
    setBody(`
      <meta name="csrf-token" content="test-csrf-token">
      <div id="bulkReminderModal">
        <div id="reminderStep1"></div>
        <div id="reminderStep2" style="display:none;">
          <div id="reminderStatusMessages"></div>
        </div>
        <div id="reminderFooter1"></div>
        <div id="reminderFooter2" style="display:none;"></div>
        <div id="instructorList"></div>
        <div id="selectedInstructorsCount">0</div>
        <input id="reminderTerm" />
        <input id="reminderDeadline" />
        <textarea id="reminderMessage"></textarea>
        <div id="reminderPreview"></div>
        <button id="sendRemindersBtn">Send Reminders</button>
        <button id="closeProgressButton">Close</button>
      </div>
    `);
    bulkReminders = new BulkReminderManager();
    // Mock startPolling to prevent actual polling during tests
    bulkReminders.startPolling = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe("Course ID determination for single instructor", () => {
    it("sets courseId when single instructor with single course is selected", async () => {
      // Setup: Single instructor with single course
      window.dashboardDataCache = {
        sections: [
          {
            id: 1,
            instructor_id: "instructor-123",
            course_id: "course-456",
            section_name: "Section A",
          },
        ],
      };

      // Select the instructor
      bulkReminders.selectedInstructors.add("instructor-123");

      // Trigger sendReminders which contains the courseId logic (lines 294-298)
      await bulkReminders.sendReminders();

      // Verify the fetch was called with the correct courseId
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/bulk-email/send-instructor-reminders",
        expect.objectContaining({
          method: "POST",
        }),
      );

      const requestBody = JSON.parse(global.fetch.mock.calls[0][1].body);
      expect(requestBody.course_id).toBe("course-456"); // courseId should be set
    });

    it("does not set courseId when instructor has multiple courses", async () => {
      // Setup: Single instructor with multiple courses
      window.dashboardDataCache = {
        sections: [
          {
            id: 1,
            instructor_id: "instructor-123",
            course_id: "course-456",
            section_name: "Section A",
          },
          {
            id: 2,
            instructor_id: "instructor-123",
            course_id: "course-789",
            section_name: "Section B",
          },
        ],
      };

      bulkReminders.selectedInstructors.add("instructor-123");

      // Exercise the code path - with multiple courses, courseId should remain null
      await bulkReminders.sendReminders();

      const requestBody = JSON.parse(global.fetch.mock.calls[0][1].body);
      expect(requestBody.course_id).toBeNull(); // courseId should be null
    });

    it("does not set courseId when multiple instructors are selected", async () => {
      // Setup: Multiple instructors
      window.dashboardDataCache = {
        sections: [
          {
            id: 1,
            instructor_id: "instructor-123",
            course_id: "course-456",
            section_name: "Section A",
          },
          {
            id: 2,
            instructor_id: "instructor-999",
            course_id: "course-789",
            section_name: "Section B",
          },
        ],
      };

      bulkReminders.selectedInstructors.add("instructor-123");
      bulkReminders.selectedInstructors.add("instructor-999");

      // With multiple instructors, should not attempt courseId lookup
      await bulkReminders.sendReminders();

      const requestBody = JSON.parse(global.fetch.mock.calls[0][1].body);
      expect(requestBody.course_id).toBeNull(); // courseId should be null
    });

    it("handles missing dashboardDataCache gracefully", async () => {
      // No dashboardDataCache set
      window.dashboardDataCache = null;

      bulkReminders.selectedInstructors.add("instructor-123");

      // Should not crash when cache is missing
      await expect(bulkReminders.sendReminders()).resolves.not.toThrow();

      const requestBody = JSON.parse(global.fetch.mock.calls[0][1].body);
      expect(requestBody.course_id).toBeNull(); // courseId should be null when cache missing
    });
  });

  describe("Event Listener Setup", () => {
    beforeEach(() => {
      setBody(`
        <meta name="csrf-token" content="test-csrf-token">
        <div id="bulkReminderModal">
          <div id="reminderStep1"></div>
          <div id="reminderStep2" style="display:none;"></div>
          <div id="reminderFooter1"></div>
          <div id="reminderFooter2" style="display:none;"></div>
          <div id="instructorList"></div>
          <div id="selectedInstructorsCount">0</div>
          <input id="reminderTerm" />
          <input id="reminderDeadline" />
          <textarea id="reminderMessage"></textarea>
          <span id="messageCharCount">0</span>
          <div id="reminderPreview"></div>
          <button id="sendRemindersButton">Send Reminders</button>
          <button id="closeProgressButton">Close</button>
        </div>
      `);
    });

    it("sendRemindersButton click triggers sendReminders", () => {
      const manager = new BulkReminderManager();
      manager.sendReminders = jest.fn();
      manager.init();

      const button = document.getElementById("sendRemindersButton");
      button.click();

      expect(manager.sendReminders).toHaveBeenCalled();
    });

    it("closeProgressButton click triggers closeModal", () => {
      const manager = new BulkReminderManager();
      manager.closeModal = jest.fn();
      manager.init();

      const button = document.getElementById("closeProgressButton");
      button.click();

      expect(manager.closeModal).toHaveBeenCalled();
    });

    it("bulkReminderModal shown.bs.modal triggers loadInstructors", () => {
      const manager = new BulkReminderManager();
      manager.loadInstructors = jest.fn();
      manager.init();

      const modal = document.getElementById("bulkReminderModal");
      const event = new Event("shown.bs.modal");
      modal.dispatchEvent(event);

      expect(manager.loadInstructors).toHaveBeenCalled();
    });

    it("bulkReminderModal hidden.bs.modal triggers resetModal", () => {
      const manager = new BulkReminderManager();
      manager.resetModal = jest.fn();
      manager.init();

      const modal = document.getElementById("bulkReminderModal");
      const event = new Event("hidden.bs.modal");
      modal.dispatchEvent(event);

      expect(manager.resetModal).toHaveBeenCalled();
    });
  });

  describe("Error Handling", () => {
    it("handles sendReminders network error", async () => {
      global.fetch.mockRejectedValueOnce(new Error("Network error"));
      bulkReminders.selectedInstructors = new Set(["i1"]);

      await bulkReminders.sendReminders();
      await flushPromises();

      const statusMessages = document.getElementById("reminderStatusMessages");
      expect(statusMessages.textContent).toContain("Error: Network error");
    });
  });
});
