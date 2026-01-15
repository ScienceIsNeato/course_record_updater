global.location = global.location || { origin: "http://localhost:3000" };

global.document = {
  getElementById: jest.fn(),
  querySelectorAll: jest.fn(() => []),
  createElement: jest.fn(() => ({ style: {} })),
  addEventListener: jest.fn(),
};

global.bootstrap = {
  Modal: jest.fn().mockImplementation(() => ({
    show: jest.fn(),
    hide: jest.fn(),
  })),
};

global.fetch = jest.fn();

require("../../../static/audit_clo.js");

describe.skip("Reminder Message Data Population - TDD Failure Capture", () => {
  beforeEach(() => {
    jest.clearAllMocks();

    globalThis.allCLOs = [
      {
        id: 123,
        outcome_id: 123,
        instructor_name: "Sarah Chen",
        instructor_id: 456,
        course_id: 789,
        course_title: "Genetics",
        course_number: "BIOL-301",
        section_number: "001",
        term_name: "Fall 2025",
      },
    ];

    const mockTextarea = { value: "" };
    const mockInstructorEmail = { textContent: "" };
    const mockIncompleteClOs = { innerHTML: "" };

    global.document.getElementById = jest.fn((id) => {
      if (id === "reminderMessage") return mockTextarea;
      if (id === "reminderInstructorEmail") return mockInstructorEmail;
      if (id === "reminderIncompleteClOs") return mockIncompleteClOs;
      if (id === "sendReminderModal") return document.createElement("div");
      return null;
    });

    global.fetch.mockImplementation((url) => {
      if (url.includes("/api/users/")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            user: {
              display_name: "Sarah Chen",
              first_name: "Sarah",
              last_name: "Chen",
              email: "sarah.chen@example.com",
            },
          }),
        });
      }
      return Promise.reject(new Error("Unknown URL"));
    });
  });

  test("Message includes actual instructor name and instructions", async () => {
    await remindOutcome(123, 456, 789);

    const messageElement = global.document.getElementById("reminderMessage");
    const actualMessage = messageElement.value;

    expect(actualMessage).toContain("Dear Sarah Chen");
    expect(actualMessage).toContain("Please complete your course assessment");
    expect(actualMessage).toContain("If you need assistance");
  });

  test("Message includes direct assessment link for the course", async () => {
    await remindOutcome(123, 456, 789);

    const messageElement = global.document.getElementById("reminderMessage");
    const actualMessage = messageElement.value;

    expect(actualMessage).toContain("/assessments?course=789");
  });
});
