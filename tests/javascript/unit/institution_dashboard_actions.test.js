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

describe("InstitutionDashboard actions", () => {
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

  describe("Initialization and Event Handlers", () => {
    beforeEach(() => {
      jest.useFakeTimers();
      global.fetch = jest.fn();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it("init() sets up visibility change listener", async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true, data: sampleData }),
      };
      global.fetch.mockResolvedValue(mockResponse);

      const loadDataSpy = jest.spyOn(InstitutionDashboard, "loadData");

      InstitutionDashboard.init();
      await Promise.resolve();

      clearInterval(InstitutionDashboard.intervalId);
      loadDataSpy.mockClear();

      InstitutionDashboard.lastFetch = Date.now() - 6 * 60 * 1000;

      Object.defineProperty(document, "hidden", {
        value: false,
        writable: true,
      });
      document.dispatchEvent(new Event("visibilitychange"));

      await Promise.resolve();

      expect(loadDataSpy).toHaveBeenCalledWith({ silent: true });
    });

    it("init() sets up auto-refresh interval", async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true, data: sampleData }),
      };
      global.fetch.mockResolvedValue(mockResponse);

      InstitutionDashboard.init();
      await Promise.resolve();

      jest.advanceTimersByTime(5 * 60 * 1000);
      await Promise.resolve();

      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it("init() sets up cleanup listeners for beforeunload", () => {
      const cleanupSpy = jest.spyOn(InstitutionDashboard, "cleanup");

      InstitutionDashboard.init();

      window.dispatchEvent(new Event("beforeunload"));

      expect(cleanupSpy).toHaveBeenCalled();
    });

    it("init() sets up cleanup listeners for pagehide", () => {
      const cleanupSpy = jest.spyOn(InstitutionDashboard, "cleanup");

      InstitutionDashboard.init();

      window.dispatchEvent(new Event("pagehide"));

      expect(cleanupSpy).toHaveBeenCalled();
    });

    it("cleanup() clears the interval", () => {
      InstitutionDashboard.intervalId = setInterval(() => {}, 1000);

      InstitutionDashboard.cleanup();

      expect(InstitutionDashboard.intervalId).toBeNull();
    });
  });

  describe("Action Handlers", () => {
    beforeEach(() => {
      setBody(`
        <div id="courseSectionContainer"></div>
        <div id="courseManagementContainer"></div>
        <div id="programManagementContainer"></div>
      `);
    });

    it("handles send-reminder action clicks", () => {
      const sendReminderSpy = jest
        .spyOn(InstitutionDashboard, "sendCourseReminder")
        .mockImplementation();

      InstitutionDashboard.init();

      const button = document.createElement("button");
      button.setAttribute("data-action", "send-reminder");
      button.setAttribute("data-instructor-id", "inst-123");
      button.setAttribute("data-course-id", "course-456");
      button.setAttribute("data-instructor", "Dr. Smith");
      button.setAttribute("data-course-number", "CS101");

      const container = document.getElementById("courseSectionContainer");
      container.appendChild(button);

      const clickEvent = new MouseEvent("click", {
        bubbles: true,
        cancelable: true,
        view: window,
      });
      button.dispatchEvent(clickEvent);

      expect(sendReminderSpy).toHaveBeenCalledWith(
        "inst-123",
        "course-456",
        "Dr. Smith",
        "CS101",
      );

      sendReminderSpy.mockRestore();
    });

    it("handles edit-section action clicks", () => {
      const editSectionSpy = jest
        .spyOn(InstitutionDashboard, "handleEditSection")
        .mockImplementation();

      InstitutionDashboard.init();

      const button = document.createElement("button");
      button.setAttribute("data-action", "edit-section");
      button.setAttribute("data-section-id", "sect-789");

      const container = document.getElementById("courseSectionContainer");
      container.appendChild(button);

      const clickEvent = new MouseEvent("click", {
        bubbles: true,
        cancelable: true,
        view: window,
      });
      button.dispatchEvent(clickEvent);

      expect(editSectionSpy).toHaveBeenCalledWith(button);

      editSectionSpy.mockRestore();
    });

    it("handles edit-course action clicks", () => {
      const editCourseSpy = jest
        .spyOn(InstitutionDashboard, "handleEditCourse")
        .mockImplementation();

      const button = document.createElement("button");
      button.setAttribute("data-action", "edit-course");
      button.setAttribute("data-course-id", "course-123");

      const container = document.getElementById("courseManagementContainer");
      container.appendChild(button);

      InstitutionDashboard.init();

      button.click();

      expect(editCourseSpy).toHaveBeenCalledWith(button);

      editCourseSpy.mockRestore();
    });

    it("handles delete-program action clicks", () => {
      window.deleteProgram = jest.fn();

      InstitutionDashboard.init();

      const button = document.createElement("button");
      button.setAttribute("data-action", "delete-program");
      button.setAttribute("data-program-id", "prog-456");
      button.setAttribute("data-program-name", "Computer Science");

      const container = document.getElementById("programManagementContainer");
      container.appendChild(button);

      const clickEvent = new MouseEvent("click", {
        bubbles: true,
        cancelable: true,
        view: window,
      });
      button.dispatchEvent(clickEvent);

      expect(window.deleteProgram).toHaveBeenCalledWith(
        "prog-456",
        "Computer Science",
      );

      delete window.deleteProgram;
    });

    it("ignores clicks without action attribute", () => {
      const sendReminderSpy = jest
        .spyOn(InstitutionDashboard, "sendCourseReminder")
        .mockImplementation();
      const editSectionSpy = jest
        .spyOn(InstitutionDashboard, "handleEditSection")
        .mockImplementation();

      const button = document.createElement("button");
      button.setAttribute("data-course-id", "course-123");

      const container = document.getElementById("courseSectionContainer");
      container.appendChild(button);

      InstitutionDashboard.init();

      button.click();

      expect(sendReminderSpy).not.toHaveBeenCalled();
      expect(editSectionSpy).not.toHaveBeenCalled();

      sendReminderSpy.mockRestore();
      editSectionSpy.mockRestore();
    });

    it("handles send-reminder with missing parameters gracefully", () => {
      const sendReminderSpy = jest
        .spyOn(InstitutionDashboard, "sendCourseReminder")
        .mockImplementation();

      const button = document.createElement("button");
      button.setAttribute("data-action", "send-reminder");
      button.setAttribute("data-instructor-id", "inst-123");

      const container = document.getElementById("courseSectionContainer");
      container.appendChild(button);

      InstitutionDashboard.init();

      button.click();

      expect(sendReminderSpy).not.toHaveBeenCalled();

      sendReminderSpy.mockRestore();
    });

    it("handles delete-program with missing function gracefully", () => {
      delete window.deleteProgram;

      const button = document.createElement("button");
      button.setAttribute("data-action", "delete-program");
      button.setAttribute("data-program-id", "prog-456");
      button.setAttribute("data-program-name", "Computer Science");

      const container = document.getElementById("programManagementContainer");
      container.appendChild(button);

      InstitutionDashboard.init();

      expect(() => button.click()).not.toThrow();
    });
  });

  describe("Handler Function Details", () => {
    beforeEach(() => {
      setBody('<meta name="csrf-token" content="test-token">');
    });

    it("handleEditSection calls window.openEditSectionModal", () => {
      window.openEditSectionModal = jest.fn();

      const button = {
        dataset: {
          sectionId: "sect-123",
          sectionData: JSON.stringify({ id: "sect-123", name: "Section A" }),
        },
      };

      InstitutionDashboard.handleEditSection(button);

      expect(window.openEditSectionModal).toHaveBeenCalledWith("sect-123", {
        id: "sect-123",
        name: "Section A",
      });

      delete window.openEditSectionModal;
    });

    it("handleEditSection handles missing window function gracefully", () => {
      delete window.openEditSectionModal;

      const button = {
        dataset: {
          sectionId: "sect-123",
          sectionData: JSON.stringify({ id: "sect-123" }),
        },
      };

      expect(() =>
        InstitutionDashboard.handleEditSection(button),
      ).not.toThrow();
    });

    it("handleEditCourse calls window.openEditCourseModal", () => {
      window.openEditCourseModal = jest.fn();

      const button = {
        dataset: {
          courseId: "course-456",
          courseData: JSON.stringify({ id: "course-456", title: "CS101" }),
        },
      };

      InstitutionDashboard.handleEditCourse(button);

      expect(window.openEditCourseModal).toHaveBeenCalledWith("course-456", {
        id: "course-456",
        title: "CS101",
      });

      delete window.openEditCourseModal;
    });

    it("handleEditCourse handles missing window function gracefully", () => {
      delete window.openEditCourseModal;

      const button = {
        dataset: {
          courseId: "course-456",
          courseData: JSON.stringify({ id: "course-456" }),
        },
      };

      expect(() => InstitutionDashboard.handleEditCourse(button)).not.toThrow();
    });

    it("sendCourseReminder sends POST request on confirmation", async () => {
      global.confirm = jest.fn().mockReturnValue(true);
      global.alert = jest.fn();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true }),
      });

      await InstitutionDashboard.sendCourseReminder(
        "inst-1",
        "course-1",
        "Dr. Smith",
        "CS101",
      );

      expect(global.confirm).toHaveBeenCalledWith(
        "Send assessment reminder to Dr. Smith for CS101?",
      );
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/send-course-reminder",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
            "X-CSRFToken": "test-token",
          }),
          body: JSON.stringify({
            instructor_id: "inst-1",
            course_id: "course-1",
          }),
        }),
      );
      expect(global.alert).toHaveBeenCalledWith(
        expect.stringContaining("✅ Reminder sent"),
      );

      delete global.confirm;
      delete global.alert;
    });

    it("sendCourseReminder returns early if user cancels confirmation", async () => {
      global.confirm = jest.fn().mockReturnValue(false);
      global.fetch = jest.fn();

      await InstitutionDashboard.sendCourseReminder(
        "inst-1",
        "course-1",
        "Dr. Smith",
        "CS101",
      );

      expect(global.confirm).toHaveBeenCalled();
      expect(global.fetch).not.toHaveBeenCalled();

      delete global.confirm;
    });

    it("sendCourseReminder handles API error response", async () => {
      global.confirm = jest.fn().mockReturnValue(true);
      global.alert = jest.fn();
      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        json: jest.fn().mockResolvedValue({ error: "Instructor not found" }),
      });

      await InstitutionDashboard.sendCourseReminder(
        "inst-1",
        "course-1",
        "Dr. Smith",
        "CS101",
      );

      expect(global.alert).toHaveBeenCalledWith(
        "❌ Failed to send reminder: Instructor not found",
      );

      delete global.confirm;
      delete global.alert;
    });

    it("sendCourseReminder handles fetch exception", async () => {
      global.confirm = jest.fn().mockReturnValue(true);
      global.alert = jest.fn();
      global.fetch = jest.fn().mockRejectedValue(new Error("Network error"));
      const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();

      await InstitutionDashboard.sendCourseReminder(
        "inst-1",
        "course-1",
        "Dr. Smith",
        "CS101",
      );

      expect(consoleErrorSpy).toHaveBeenCalled();
      expect(global.alert).toHaveBeenCalledWith(
        "❌ Failed to send reminder. Please try again.",
      );

      consoleErrorSpy.mockRestore();
      delete global.confirm;
      delete global.alert;
    });

    it("sendCourseReminder handles missing CSRF token", async () => {
      setBody("<div></div>");
      global.confirm = jest.fn().mockReturnValue(true);
      global.alert = jest.fn();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true }),
      });

      await InstitutionDashboard.sendCourseReminder(
        "inst-1",
        "course-1",
        "Dr. Smith",
        "CS101",
      );

      expect(global.fetch).toHaveBeenCalledWith(
        "/api/send-course-reminder",
        expect.objectContaining({
          headers: expect.objectContaining({
            "X-CSRFToken": null,
          }),
        }),
      );

      delete global.confirm;
      delete global.alert;
    });
  });

  describe("Data Loading", () => {
    beforeEach(() => {
      global.fetch = jest.fn();
    });

    it("loadData() makes fetch request to correct endpoint", async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true, data: sampleData }),
      };
      global.fetch.mockResolvedValue(mockResponse);

      await InstitutionDashboard.loadData();

      expect(global.fetch).toHaveBeenCalledWith(
        "/api/dashboard/data",
        expect.objectContaining({
          credentials: "include",
          headers: expect.objectContaining({
            Accept: "application/json",
            "X-Requested-With": "XMLHttpRequest",
          }),
        }),
      );
    });

    it("loadData() updates cache and renders on success", async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true, data: sampleData }),
      };
      global.fetch.mockResolvedValue(mockResponse);

      const renderSpy = jest.spyOn(InstitutionDashboard, "render");

      await InstitutionDashboard.loadData();

      expect(InstitutionDashboard.cache).toEqual(sampleData);
      expect(window.dashboardDataCache).toEqual(sampleData);
      expect(renderSpy).toHaveBeenCalledWith(sampleData);
    });

    it("loadData() shows loading states when not silent", async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true, data: sampleData }),
      };
      global.fetch.mockResolvedValue(mockResponse);

      const setLoadingSpy = jest.spyOn(InstitutionDashboard, "setLoading");

      await InstitutionDashboard.loadData({ silent: false });

      expect(setLoadingSpy).toHaveBeenCalledWith(
        "programManagementContainer",
        "Loading programs...",
      );
      expect(setLoadingSpy).toHaveBeenCalledWith(
        "facultyOverviewContainer",
        "Loading faculty...",
      );
    });

    it("loadData() does not show loading states when silent", async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true, data: sampleData }),
      };
      global.fetch.mockResolvedValue(mockResponse);

      const setLoadingSpy = jest.spyOn(InstitutionDashboard, "setLoading");

      await InstitutionDashboard.loadData({ silent: true });

      expect(setLoadingSpy).not.toHaveBeenCalled();
    });

    it("loadData() handles fetch errors gracefully", async () => {
      global.fetch.mockRejectedValue(new Error("Network error"));
      const showErrorSpy = jest.spyOn(InstitutionDashboard, "showError");
      const consoleWarnSpy = jest.spyOn(console, "warn").mockImplementation();

      await InstitutionDashboard.loadData();

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        "Institution dashboard load error:",
        expect.any(Error),
      );
      expect(showErrorSpy).toHaveBeenCalledWith(
        "programManagementContainer",
        "Unable to load program data",
      );
      expect(showErrorSpy).toHaveBeenCalledWith(
        "facultyOverviewContainer",
        "Unable to load faculty data",
      );
    });

    it("loadData() handles non-ok HTTP responses", async () => {
      const mockResponse = {
        ok: false,
        json: jest
          .fn()
          .mockResolvedValue({ success: false, error: "Unauthorized" }),
      };
      global.fetch.mockResolvedValue(mockResponse);

      const showErrorSpy = jest.spyOn(InstitutionDashboard, "showError");

      await InstitutionDashboard.loadData();

      expect(showErrorSpy).toHaveBeenCalled();
    });

    it("refresh() calls loadData with silent=false", async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true, data: sampleData }),
      };
      global.fetch.mockResolvedValue(mockResponse);

      const loadDataSpy = jest.spyOn(InstitutionDashboard, "loadData");

      await InstitutionDashboard.refresh();

      expect(loadDataSpy).toHaveBeenCalledWith({ silent: false });

      loadDataSpy.mockRestore();
    });
  });
});

describe("InstitutionDashboard Initialization", () => {
  beforeEach(() => {
    jest.resetModules();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test("should warn if panelManager is missing", () => {
    delete global.panelManager;
    delete window.panelManager;
    const consoleWarnSpy = jest.spyOn(console, "warn").mockImplementation();

    require("../../../static/institution_dashboard");
    document.dispatchEvent(new Event("DOMContentLoaded"));
    jest.advanceTimersByTime(200);

    expect(consoleWarnSpy).toHaveBeenCalledWith(
      expect.stringContaining("Panel manager not initialized"),
    );
  });
});
