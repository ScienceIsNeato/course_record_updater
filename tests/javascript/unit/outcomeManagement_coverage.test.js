/**
 * Additional Unit Tests for Course Outcome (CLO) Management UI
 * specifically targeting coverage gaps (loadOutcomes, etc.)
 */
require("../../../static/outcomeManagement.js");

describe("Outcome Management Coverage - Load Outcomes", () => {
  let mockFetch;
  let consoleErrorSpy;

  beforeEach(() => {
    document.body.innerHTML = `
        <div id="outcomesTableContainer"></div>
        <select id="filterProgram"><option value="">All</option></select>
        <select id="filterCourse"><option value="">All</option></select>
        <select id="filterStatus"><option value="">All</option></select>
        <div id="createOutcomeModal"></div>
        <form id="createOutcomeForm"></form>
        <select id="outcomeCourseId">
           <option value="">Select</option>
        </select>
      `;

    mockFetch = jest.fn();
    global.fetch = mockFetch;
    consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();

    // Re-attach in case it was overwritten
    if (window.loadOutcomes) {
      global.loadOutcomes = window.loadOutcomes;
    }
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test("should fetch and render outcomes successfully", async () => {
    const mockOutcomes = [
      {
        outcome_id: "out1",
        course_number: "CS101",
        course_title: "Intro",
        clo_number: "CLO1",
        description: "Desc 1",
        assessment_method: "Test",
        active: true,
      },
      {
        outcome_id: "out2",
        course_id: "course-2-id", // missing course_number/title
        clo_number: "CLO2",
        description: "Desc 2",
        assessment_method: null,
        active: false,
      },
    ];

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ outcomes: mockOutcomes }),
    });

    await window.loadOutcomes();

    expect(mockFetch).toHaveBeenCalledWith("/api/outcomes?");

    const container = document.getElementById("outcomesTableContainer");
    expect(container.innerHTML).toContain("CS101");
    expect(container.innerHTML).toContain("CLO1");
    expect(container.innerHTML).toContain("Desc 1");
    expect(container.innerHTML).toContain("Test");
    expect(container.innerHTML).toContain("Active");

    // Check second item
    expect(container.innerHTML).toContain("Unknown - course-2");
    expect(container.innerHTML).toContain("CLO2");
    expect(container.innerHTML).toContain("Archived");
    expect(container.innerHTML).toContain("-"); // null assessment method
  });

  test("should include filters in API call", async () => {
    // Add options so we can select them
    const progSelect = document.getElementById("filterProgram");
    progSelect.add(new Option("Prog 1", "prog1"));
    progSelect.value = "prog1";

    const courseSelect = document.getElementById("filterCourse");
    courseSelect.add(new Option("Course 1", "course1"));
    courseSelect.value = "course1";

    const statusSelect = document.getElementById("filterStatus");
    statusSelect.add(new Option("Active", "active"));
    statusSelect.value = "active";

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ outcomes: [] }),
    });

    await window.loadOutcomes();

    const url = mockFetch.mock.calls[0][0];
    expect(url).toContain("program_id=prog1");
    expect(url).toContain("course_id=course1");
    expect(url).toContain("status=active");
  });

  test("should render empty state when no outcomes found", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ outcomes: [] }),
    });

    await window.loadOutcomes();

    const container = document.getElementById("outcomesTableContainer");
    expect(container.innerHTML).toContain("No outcomes found");
  });

  test("should handle fetch errors", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Fetch failed"));

    await window.loadOutcomes();

    const container = document.getElementById("outcomesTableContainer");
    // The implementation catches error and shows alert-danger
    expect(container.innerHTML).toContain("Failed to load outcomes");
    expect(consoleErrorSpy).toHaveBeenCalled();
  });

  test("should handle API error response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: "Server Error",
    });

    await window.loadOutcomes();

    const container = document.getElementById("outcomesTableContainer");
    expect(container.innerHTML).toContain("Failed to load outcomes");
  });

  test("renders course name from nested course object if present", async () => {
    const mockOutcomes = [
      {
        outcome_id: "out3",
        course_id: "c3",
        course: { course_number: "CS303" },
        clo_number: "CLO3",
        description: "D3",
        active: true,
      },
    ];

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ outcomes: mockOutcomes }),
    });

    await window.loadOutcomes();
    const container = document.getElementById("outcomesTableContainer");
    expect(container.innerHTML).toContain("CS303");
  });

  test("should do nothing if container does not exist", async () => {
    const container = document.getElementById("outcomesTableContainer");
    container.remove();

    await window.loadOutcomes();
    expect(mockFetch).not.toHaveBeenCalled();
  });
});

describe("Outcome Management Coverage - Course Loading in Modal", () => {
  let mockFetch;
  let consoleErrorSpy;

  beforeEach(() => {
    document.body.innerHTML = `
          <div id="createOutcomeModal"></div>
          <form id="createOutcomeForm"></form>
          <select id="outcomeCourseId">
            <option value="">Select</option>
          </select>
        `;

    mockFetch = jest.fn();
    global.fetch = mockFetch;
    consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();

    // Re-initialize listeners to ensure they attach to the new body
    document.dispatchEvent(new Event("DOMContentLoaded"));
  });

  test("should fetch courses when modal opens if list is empty", async () => {
    const courses = [
      { course_id: "c1", course_number: "CS101", course_title: "Intro" },
      { course_id: "c2", course_number: "CS102", course_title: "Advanced" },
    ];

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ courses }),
    });

    const modal = document.getElementById("createOutcomeModal");
    modal.dispatchEvent(new Event("show.bs.modal"));

    // Wait for async
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(mockFetch).toHaveBeenCalledWith("/api/courses");

    const select = document.getElementById("outcomeCourseId");
    expect(select.options.length).toBe(3); // 1 placeholder + 2 courses
    expect(select.innerHTML).toContain("CS101 - Intro");
    expect(select.innerHTML).toContain("CS102 - Advanced");
  });

  test("should not fetch courses if populated", async () => {
    const select = document.getElementById("outcomeCourseId");
    select.add(new Option("Existing", "exist"));
    select.add(new Option("Existing 2", "exist2"));

    const modal = document.getElementById("createOutcomeModal");
    modal.dispatchEvent(new Event("show.bs.modal"));

    expect(mockFetch).not.toHaveBeenCalled();
  });

  test("should handle course fetch error", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Failed"));

    const modal = document.getElementById("createOutcomeModal");
    modal.dispatchEvent(new Event("show.bs.modal"));

    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(consoleErrorSpy).toHaveBeenCalled();
  });
});

describe("Outcome Management Coverage - Helpers", () => {
  beforeEach(() => {
    document.body.innerHTML = ``;
    // Mock DashboardEvents global
    global.DashboardEvents = { publishMutation: jest.fn() };
  });

  test("test publishOutcomeMutation calls DashboardEvents", async () => {
    // Create necessary DOM for deletion to work
    document.body.innerHTML = '<meta name="csrf-token" content="tok">';

    // Mock deleteOutcome dependencies
    global.fetch = jest
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({}) });
    global.loadOutcomes = jest.fn();

    await window.deleteOutcome("1", "C1", "CLO");

    expect(global.DashboardEvents.publishMutation).toHaveBeenCalledWith(
      expect.objectContaining({
        entity: "outcomes",
        action: "delete",
      }),
    );
  });
});
