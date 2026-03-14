const { setBody, flushPromises } = require("../helpers/dom");

describe("courseManagement.js Coverage Boost", () => {
  let mockLoadCourses;

  beforeEach(() => {
    jest.resetModules();
    setBody(`
      <form id="createCourseForm">
        <input id="courseNumber" value="CS101">
        <input id="courseTitle" value="Intro">
        <input id="courseDepartment" value="CS">
        <input id="courseCreditHours" value="3">
        <select id="courseProgramIds" multiple><option value="p1" selected>Program</option></select>
        <input id="courseActive" type="checkbox" checked>
        <button type="submit" id="createCourseBtn">
            <span class="btn-text">Save</span>
            <span class="btn-spinner d-none"></span>
        </button>
      </form>
      <div id="createCourseModal"></div>
      
      <form id="editCourseForm">
        <input id="editCourseId" value="c1">
        <input id="editCourseNumber" value="CS101">
        <input id="editCourseTitle" value="Intro">
        <input id="editCourseDepartment" value="CS">
        <input id="editCourseCreditHours" value="3">
        <select id="editCourseProgramIds" multiple><option value="p1" selected>Program</option></select>
        <input id="editCourseActive" type="checkbox" checked>
        <button type="submit" id="editCourseBtn">
            <span class="btn-text">Save</span>
            <span class="btn-spinner d-none"></span>
        </button>
      </form>
      <div id="editCourseModal"></div>
      
      <meta name="csrf-token" content="token">
    `);

    global.bootstrap = {
      Modal: jest.fn().mockImplementation(() => ({
        show: jest.fn(),
        hide: jest.fn(),
      })),
    };
    global.bootstrap.Modal.getInstance = jest.fn(() => ({ hide: jest.fn() }));

    mockLoadCourses = jest.fn();
    global.loadCourses = mockLoadCourses;

    jest.spyOn(window, "alert").mockImplementation(() => {});
    jest.spyOn(window, "confirm").mockReturnValue(true);
    jest.spyOn(console, "error").mockImplementation(() => {});

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, message: "Success" }),
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
    delete global.loadCourses;
  });

  test("createCourseForm calls loadCourses on success", async () => {
    require("../../../static/courseManagement.js");
    document.dispatchEvent(new Event("DOMContentLoaded"));

    const form = document.getElementById("createCourseForm");
    form.dispatchEvent(new Event("submit"));

    await flushPromises();
    expect(mockLoadCourses).toHaveBeenCalled();
  });

  test("editCourseForm calls loadCourses on success", async () => {
    require("../../../static/courseManagement.js");
    document.dispatchEvent(new Event("DOMContentLoaded"));

    const form = document.getElementById("editCourseForm");
    form.dispatchEvent(new Event("submit"));

    await flushPromises();
    expect(mockLoadCourses).toHaveBeenCalled();
  });

  test("deleteCourse calls loadCourses on success", async () => {
    require("../../../static/courseManagement.js");
    await global.deleteCourse("c1", "Intro");
    await flushPromises();
    expect(mockLoadCourses).toHaveBeenCalled();
  });
});
