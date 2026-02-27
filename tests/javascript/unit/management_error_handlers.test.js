const { setBody, flushPromises } = require("../helpers/dom");

describe("Management Modules Error Handling", () => {
  let consoleErrorSpy;
  let alertSpy;
  let confirmSpy;
  let promptSpy;

  beforeEach(() => {
    jest.resetModules();
    consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();
    alertSpy = jest.spyOn(window, "alert").mockImplementation();
    confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(true);
    promptSpy = jest
      .spyOn(window, "prompt")
      .mockReturnValue("DELETE User Name");
    global.fetch = jest.fn();

    // Mock Bootstrap
    global.bootstrap = {
      Modal: jest.fn().mockImplementation(() => ({
        show: jest.fn(),
        hide: jest.fn(),
      })),
      Tooltip: jest.fn(),
    };
    // Mock static getInstance
    global.bootstrap.Modal.getInstance = jest.fn(() => ({
      hide: jest.fn(),
    }));

    // Setup comprehensive DOM for all forms
    setBody(`
      <!-- User Management -->
      <form id="inviteUserForm">
        <input id="inviteEmail" value="test@test.com" required>
        <select id="inviteRole"><option value="instructor" selected>Instructor</option></select>
        <textarea id="inviteMessage"></textarea>
        <select id="invitePrograms" multiple></select>
        <button type="submit" id="sendInviteBtn"><span class="btn-text">S</span><span class="btn-spinner"></span></button>
        <div id="programSelection"></div>
      </form>
      <form id="editUserForm">
        <input id="editUserId" value="u1">
        <input id="editFirstName" value="First" required>
        <input id="editLastName" value="Last" required>
        <input id="editEmail" value="edit@test.com" required>
        <input id="editDisplayName" value="Display">
        <select id="editRole"><option value="instructor" selected>Instructor</option></select>
        <button type="submit" id="saveUserBtn"><span class="btn-text">S</span><span class="btn-spinner"></span></button>
      </form>
      
      <!-- Offering Management -->
      <form id="createOfferingForm">
        <select id="offeringTermId" required><option value="t1" selected>Term</option></select>
        <select id="offeringCourseId" required><option value="c1" selected>Course</option></select>
        <select id="offeringProgramId" required><option value="p1" selected>Program</option></select>
        <input id="offeringCapacity" value="30">
        <button type="submit" id="createOfferingBtn"><span class="btn-text">S</span><span class="btn-spinner"></span></button>
      </form>
      <form id="editOfferingForm">
        <input id="editOfferingId" value="o1">
        <select id="editOfferingProgramId" required><option value="p1" selected>Program</option></select>
        <select id="editOfferingTerm" required><option value="t1" selected>Term</option></select>
        <input id="editOfferingCapacity" value="30">
        <button type="submit" id="updateOfferingBtn"><span class="btn-text">S</span><span class="btn-spinner"></span></button>
      </form>
      
      <!-- Section Management -->
      <form id="createSectionForm">
        <select id="sectionOfferingId" required><option value="o1" selected>Offering</option></select>
        <input id="sectionNumber" value="001" required>
        <select id="sectionInstructorId"><option value="i1">Instructor</option></select>
        <input id="sectionEnrollment" value="0">
        <select id="sectionStatus"><option value="active" selected>Active</option></select>
        <button type="submit" id="createSectionBtn"><span class="btn-text">S</span><span class="btn-spinner"></span></button>
      </form>
      <form id="editSectionForm">
        <input id="editSectionId" value="s1">
        <input id="editSectionNumber" value="001" required>
        <select id="editSectionInstructorId"><option value="i1">Instructor</option></select>
        <input id="editSectionEnrollment" value="0">
        <select id="editSectionStatus"><option value="active" selected>Active</option></select>
        <button type="submit" id="updateSectionBtn"><span class="btn-text">S</span><span class="btn-spinner"></span></button>
      </form>
      
      <!-- Course Management -->
      <form id="createCourseForm">
        <input id="courseNumber" value="CS101" required>
        <input id="courseTitle" value="Intro" required>
        <input id="courseDepartment" value="CS">
        <input id="courseCreditHours" value="3">
        <input type="checkbox" id="courseActive" checked>
        <select id="courseProgramIds" multiple><option value="p1" selected>Prog</option></select>
        <button type="submit" id="createCourseBtn"><span class="btn-text">S</span><span class="btn-spinner"></span></button>
      </form>
      <form id="editCourseForm">
        <input id="editCourseId" value="c1">
        <input id="editCourseNumber" value="CS101" required>
        <input id="editCourseTitle" value="Intro" required>
        <input id="editCourseDepartment" value="CS">
        <input id="editCourseCreditHours" value="3">
        <input type="checkbox" id="editCourseActive" checked>
        <select id="editCourseProgramIds" multiple><option value="p1" selected>Prog</option></select>
        <button type="submit" id="updateCourseBtn"><span class="btn-text">S</span><span class="btn-spinner"></span></button>
      </form>
      
      <meta name="csrf-token" content="test-token">
    `);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  const loadAndInit = (path) => {
    require(path);
    document.dispatchEvent(new Event("DOMContentLoaded"));
  };

  // --- User Management ---
  test("userManagement createUser handles network error", async () => {
    loadAndInit("../../../static/userManagement");
    global.fetch.mockRejectedValueOnce(new Error("Network error"));

    const form = document.getElementById("inviteUserForm");
    form.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await flushPromises();

    expect(consoleErrorSpy).toHaveBeenCalled();
    // User management uses custom showAlert helper
    const alerts = document.querySelectorAll(".alert-danger");
    expect(alerts.length).toBeGreaterThan(0);
    expect(alerts[0].textContent).toContain("Failed");
  });

  test("userManagement updateUser handles network error", async () => {
    loadAndInit("../../../static/userManagement");
    global.fetch.mockRejectedValueOnce(new Error("Network error"));

    const form = document.getElementById("editUserForm");
    form.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await flushPromises();

    expect(consoleErrorSpy).toHaveBeenCalled();
    // User management uses custom showAlert helper
    const alerts = document.querySelectorAll(".alert-danger");
    expect(alerts.length).toBeGreaterThan(0);
    expect(alerts[0].textContent).toContain("Failed");
  });

  test("userManagement deactivateUser handles network error", async () => {
    loadAndInit("../../../static/userManagement");
    global.fetch.mockRejectedValueOnce(new Error("Network error"));

    if (globalThis.deactivateUser) {
      await globalThis.deactivateUser("u1", "User");
      expect(consoleErrorSpy).toHaveBeenCalled();
      expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("Failed"));
    }
  });

  test("userManagement deleteUser handles network error", async () => {
    require("../../../static/userManagement");
    global.fetch.mockRejectedValueOnce(new Error("Network error"));

    // Mock prompt for userManagement confirmation
    promptSpy.mockReturnValue("DELETE User Name");

    if (globalThis.deleteUser) {
      await globalThis.deleteUser("u1", "User Name");
      expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("Failed"));
      expect(consoleErrorSpy).toHaveBeenCalled();
    }
  });

  test("userManagement deleteUser success calls loadUsers", async () => {
    require("../../../static/userManagement");
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    });
    promptSpy.mockReturnValue("DELETE User Name");

    globalThis.loadUsers = jest.fn();

    if (globalThis.deleteUser) {
      await globalThis.deleteUser("u1", "User Name");
      expect(globalThis.loadUsers).toHaveBeenCalled();
    }
  });

  // --- Offering Management ---
  test("offeringManagement createOffering handles network error", async () => {
    loadAndInit("../../../static/offeringManagement");
    global.fetch.mockRejectedValueOnce(new Error("Network error"));

    const form = document.getElementById("createOfferingForm");
    form.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await flushPromises();

    expect(consoleErrorSpy).toHaveBeenCalled();
    expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("Failed"));
  });

  test("offeringManagement updateOffering handles network error", async () => {
    loadAndInit("../../../static/offeringManagement");
    global.fetch.mockRejectedValueOnce(new Error("Network error"));

    const form = document.getElementById("editOfferingForm");
    form.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await flushPromises();

    expect(consoleErrorSpy).toHaveBeenCalled();
    expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("Failed"));
  });

  test("offeringManagement deleteOffering handles network error", async () => {
    loadAndInit("../../../static/offeringManagement");
    global.fetch.mockRejectedValueOnce(new Error("Network error"));

    if (globalThis.deleteOffering) {
      await globalThis.deleteOffering("o1");
      expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("Failed"));
      expect(consoleErrorSpy).toHaveBeenCalled();
    }
  });

  test("offeringManagement deleteOffering success calls loadOfferings", async () => {
    require("../../../static/offeringManagement");
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    });

    globalThis.loadOfferings = jest.fn();

    if (globalThis.deleteOffering) {
      await globalThis.deleteOffering("o1");
      expect(globalThis.loadOfferings).toHaveBeenCalled();
    }
  });

  // --- Section Management ---
  test("sectionManagement createSection handles network error", async () => {
    loadAndInit("../../../static/sectionManagement");
    global.fetch.mockRejectedValueOnce(new Error("Network error"));

    const form = document.getElementById("createSectionForm");
    form.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await flushPromises();

    expect(consoleErrorSpy).toHaveBeenCalled();
    expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("Failed"));
  });

  test("sectionManagement updateSection handles network error", async () => {
    loadAndInit("../../../static/sectionManagement");
    global.fetch.mockRejectedValueOnce(new Error("Network error"));

    const form = document.getElementById("editSectionForm");
    form.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await flushPromises();

    expect(consoleErrorSpy).toHaveBeenCalled();
    expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("Failed"));
  });

  test("sectionManagement deleteSection handles network error", async () => {
    loadAndInit("../../../static/sectionManagement");
    global.fetch.mockRejectedValueOnce(new Error("Network error"));

    if (globalThis.deleteSection) {
      await globalThis.deleteSection("s1", "Section 1");
      expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("Failed"));
      expect(consoleErrorSpy).toHaveBeenCalled();
    }
  });

  test("sectionManagement deleteSection success calls loadSections", async () => {
    loadAndInit("../../../static/sectionManagement");
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    });

    globalThis.loadSections = jest.fn();

    if (globalThis.deleteSection) {
      await globalThis.deleteSection("s1", "Section 1");
      expect(globalThis.loadSections).toHaveBeenCalled();
    }
  });

  // --- Course Management ---
  test("courseManagement createCourse handles network error", async () => {
    loadAndInit("../../../static/courseManagement");
    global.fetch.mockRejectedValueOnce(new Error("Network error"));

    const form = document.getElementById("createCourseForm");
    form.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await flushPromises();

    expect(consoleErrorSpy).toHaveBeenCalled();
    expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("Failed"));
  });

  test("courseManagement updateCourse handles network error", async () => {
    loadAndInit("../../../static/courseManagement");
    global.fetch.mockRejectedValueOnce(new Error("Network error"));

    const form = document.getElementById("editCourseForm");
    form.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
    await flushPromises();

    expect(consoleErrorSpy).toHaveBeenCalled();
    expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("Failed"));
  });

  test("courseManagement deleteCourse handles network error", async () => {
    loadAndInit("../../../static/courseManagement");
    global.fetch.mockRejectedValueOnce(new Error("Network error"));

    if (globalThis.deleteCourse) {
      await globalThis.deleteCourse("c1", "Course 1");
      expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("Failed"));
      expect(consoleErrorSpy).toHaveBeenCalled();
    }
  });

  test("courseManagement deleteCourse success calls loadCourses", async () => {
    loadAndInit("../../../static/courseManagement");
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    });

    globalThis.loadCourses = jest.fn();

    if (globalThis.deleteCourse) {
      await globalThis.deleteCourse("c1", "Course 1");
      expect(globalThis.loadCourses).toHaveBeenCalled();
    }
  });
});
