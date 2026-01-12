/**
 * Jest tests for new audit_clo.js features: Reopen from Modal and Send Reminder
 */

// Mock global fetch
global.fetch = jest.fn();

// Mock bootstrap Modal
global.bootstrap = {
    Modal: jest.fn(),
};
global.bootstrap.Modal.getInstance = jest.fn();
global.bootstrap.Modal.getOrCreateInstance = jest.fn();

// Mock alert and confirm
global.alert = jest.fn();
global.confirm = jest.fn();

// Import module
const auditCloModule = require("../../../static/audit_clo.js");

describe("audit_clo.js - Reminder and Reopen Features", () => {
    beforeEach(() => {
        jest.clearAllMocks();
        document.body.innerHTML = `
      <meta name="csrf-token" content="test-csrf">
      <div id="cloDetailModal"></div>
      <button id="reopenBtn"></button>
      
      <div id="sendReminderModal"></div>
      <form id="sendReminderForm">
        <textarea id="reminderMessage"></textarea>
      </form>
      <div id="reminderCourseDescription"></div>
      <div id="reminderInstructorEmail"></div>
      <div id="reminderIncompleteClOs"></div>
    `;

        // Reset global state
        global.currentCLO = null;

        // Mock bootstrap instance
        global.bootstrap.Modal.mockImplementation(() => ({
            show: jest.fn(),
            hide: jest.fn(),
        }));
        global.bootstrap.Modal.getInstance.mockReturnValue({
            hide: jest.fn(),
        });
    });

    describe("reopenCLOFromModal", () => {
        it("should do nothing if currentCLO is null", async () => {
            global.currentCLO = null;
            // We need to spy on window.reopenOutcome if possible, but since it's in the same module 
            // and not exported for internal calls, we rely on side effects like fetch.

            await global.reopenCLOFromModal();
            expect(fetch).not.toHaveBeenCalled();
        });

        it("should call fetch to reopen if confirmed", async () => {
            global.currentCLO = { outcome_id: "test-id" };
            global.confirm.mockReturnValue(true);
            fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });

            // Mock loadCLOs
            global.loadCLOs = jest.fn();

            await global.reopenCLOFromModal();

            expect(fetch).toHaveBeenCalledWith(
                "/api/outcomes/test-id",
                expect.objectContaining({
                    method: "PUT",
                    body: JSON.stringify({
                        status: "in_progress",
                        approval_status: "pending",
                    }),
                })
            );
        });
    });

    describe("remindOutcome", () => {
        it("should alert if missing instructor/course", async () => {
            await global.remindOutcome("id", null, null);
            expect(global.alert).toHaveBeenCalledWith(expect.stringContaining("Missing instructor"));
        });

        it("should open modal and populate message", async () => {
            // Mock allCLOs
            globalThis.allCLOs = [
                {
                    outcome_id: "oid",
                    instructor_name: "John Doe",
                    instructor_id: "iid",
                    course_id: "cid",
                    course_number: "CS101",
                    course_title: "Intro CS",
                    clo_number: 1,
                    description: "Learn JS",
                    section_number: "001",
                    section_id: "section-123",
                    term_name: "Fall 2024",
                    status: "assigned"
                }
            ];

            // Mock fetch for instructor and section
            global.fetch.mockImplementation((url) => {
                if (url.includes('/api/users/')) {
                    return Promise.resolve({
                        ok: true,
                        json: () => Promise.resolve({
                            success: true,
                            user: {
                                display_name: "John Doe",
                                email: "john@example.com"
                            }
                        })
                    });
                }
                if (url.includes('/api/sections/')) {
                    return Promise.resolve({
                        ok: true,
                        json: () => Promise.resolve({
                            success: true,
                            section: {
                                assessment_due_date: "2024-12-15"
                            }
                        })
                    });
                }
                return Promise.reject(new Error('Unknown URL'));
            });

            await global.remindOutcome("oid", "iid", "cid");

            expect(global.bootstrap.Modal).toHaveBeenCalled();
            const message = document.getElementById("reminderMessage").value;
            expect(message).toContain("Dear John Doe");
            expect(message).toContain("Fall 2024 - CS101 (Section 001)");
            expect(message).toContain("CLO #1");
        });
    });

    describe("submitReminder", () => {
        it("should send POST request", async () => {
            // Setup state via remindOutcome first
            globalThis.allCLOs = [
                { 
                    outcome_id: "oid", 
                    instructor_name: "John", 
                    instructor_id: "iid",
                    course_id: "cid",
                    course_number: "CS101", 
                    clo_number: 1, 
                    description: "Desc",
                    section_id: "section-123",
                    status: "assigned"
                }
            ];
            
            // Mock fetch for instructor and section
            fetch.mockImplementation((url) => {
                if (url.includes('/api/users/')) {
                    return Promise.resolve({
                        ok: true,
                        json: () => Promise.resolve({
                            success: true,
                            user: {
                                display_name: "John",
                                email: "john@example.com"
                            }
                        })
                    });
                }
                if (url.includes('/api/sections/')) {
                    return Promise.resolve({
                        ok: true,
                        json: () => Promise.resolve({
                            success: true,
                            section: {}
                        })
                    });
                }
                if (url.includes('/api/send-course-reminder')) {
                    return Promise.resolve({ ok: true });
                }
                return Promise.reject(new Error('Unknown URL'));
            });
            
            await global.remindOutcome("oid", "iid", "cid");

            // Set message
            document.getElementById("reminderMessage").value = "Custom Message";

            // Call handler directly
            await global.submitReminder({ preventDefault: jest.fn() });

            // Wait to verify fetch
            expect(fetch).toHaveBeenCalledWith(
                "/api/send-course-reminder",
                expect.objectContaining({
                    method: "POST",
                    body: expect.stringContaining("Custom Message")
                })
            );

            expect(fetch).toHaveBeenCalledWith(
                "/api/send-course-reminder",
                expect.objectContaining({
                    body: expect.stringContaining('"instructor_id":"iid"')
                })
            );
        });
    });
});
