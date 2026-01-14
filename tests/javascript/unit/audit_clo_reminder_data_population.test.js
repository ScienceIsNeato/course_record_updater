/**
 * TDD Test: Reminder message MUST populate with actual data, not generic placeholders
 * 
 * This test captures the CURRENT FAILURE where reminder messages show:
 * - "Dear Instructor" instead of actual instructor name
 * - "Course" instead of actual course number
 * - No actual section or term information
 */

// Mock DOM and Bootstrap
global.document = {
  getElementById: jest.fn(),
  querySelectorAll: jest.fn(() => []),
  addEventListener: jest.fn(),
};

global.bootstrap = {
  Modal: jest.fn().mockImplementation(() => ({
    show: jest.fn(),
    hide: jest.fn(),
  })),
};

global.fetch = jest.fn();

// Load the actual audit_clo.js code
require('../../../static/audit_clo.js');

describe.skip('Reminder Message Data Population - TDD Failure Capture', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Set up realistic CLO data with ACTUAL instructor and course information
    globalThis.allCLOs = [
      {
        id: 123,
        outcome_id: 123,
        clo_number: 2,
        description: 'Analyze cellular and molecular processes',
        instructor_name: 'Sarah Chen',  // ACTUAL NAME - not "Instructor"
        instructor_id: 456,
        course_id: 789,
        course_title: 'Genetics',
        course_number: 'BIOL-301',  // ACTUAL COURSE - not "Course"
        section_number: '001',
        term_name: 'Fall 2025',
        section_id: 'section-abc-123',
      }
    ];

    // Mock DOM elements
    const mockTextarea = { value: '' };
    const mockCourseDescription = { textContent: '' };
    const mockInstructorEmail = { textContent: '' };
    const mockIncompleteClOs = { innerHTML: '' };
    
    global.document.getElementById = jest.fn((id) => {
      if (id === 'reminderMessage') return mockTextarea;
      if (id === 'reminderCourseDescription') return mockCourseDescription;
      if (id === 'reminderInstructorEmail') return mockInstructorEmail;
      if (id === 'reminderIncompleteClOs') return mockIncompleteClOs;
      if (id === 'sendReminderModal') return document.createElement('div');
      return null;
    });

    // Mock successful API responses
    global.fetch.mockImplementation((url) => {
      // Mock instructor API call
      if (url.includes('/api/users/')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            user: {
              display_name: 'Sarah Chen',
              first_name: 'Sarah',
              last_name: 'Chen',
              email: 'sarah.chen@example.com'
            }
          })
        });
      }
      // Mock section API call
      if (url.includes('/api/sections/')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            section: {
              assessment_due_date: '2025-12-15'
            }
          })
        });
      }
      return Promise.reject(new Error('Unknown URL'));
    });
  });

  test('FAIL: Message must contain ACTUAL instructor name, not generic "Instructor"', async () => {
    await remindOutcome(123, 456, 789);

    const messageElement = global.document.getElementById('reminderMessage');
    const actualMessage = messageElement.value;

    // This test MUST FAIL currently because the message contains "Dear Instructor"
    expect(actualMessage).toContain('Dear Sarah Chen');
    expect(actualMessage).not.toContain('Dear Instructor');
  });

  test('FAIL: Message must contain ACTUAL course number, not generic "Course"', async () => {
    await remindOutcome(123, 456, 789);

    const messageElement = global.document.getElementById('reminderMessage');
    const actualMessage = messageElement.value;

    // This test MUST FAIL currently because the message contains "Course, CLO #2"
    expect(actualMessage).toContain('BIOL-301');
    expect(actualMessage).not.toMatch(/\bCourse,/);  // Should not have "Course," as standalone
  });

  test('FAIL: Message must contain ACTUAL term name', async () => {
    await remindOutcome(123, 456, 789);

    const messageElement = global.document.getElementById('reminderMessage');
    const actualMessage = messageElement.value;

    // Should show "Fall 2025 - BIOL-301" not just "Course"
    expect(actualMessage).toContain('Fall 2025');
  });

  test('FAIL: Message must contain ACTUAL section number', async () => {
    await remindOutcome(123, 456, 789);

    const messageElement = global.document.getElementById('reminderMessage');
    const actualMessage = messageElement.value;

    // Should show "Section 001"
    expect(actualMessage).toContain('Section 001');
  });

  test('FAIL: Message must contain ACTUAL CLO number from data', async () => {
    await remindOutcome(123, 456, 789);

    const messageElement = global.document.getElementById('reminderMessage');
    const actualMessage = messageElement.value;

    // Should show "CLO #2" (from the actual data), not "CLO #?"
    expect(actualMessage).toContain('CLO #2');
    expect(actualMessage).not.toContain('CLO #?');
  });

  test('FAIL: Message must contain ACTUAL due date from API', async () => {
    await remindOutcome(123, 456, 789);

    // Wait for async fetch to complete
    await new Promise(resolve => setTimeout(resolve, 10));

    const messageElement = global.document.getElementById('reminderMessage');
    const actualMessage = messageElement.value;

    // Should show the actual due date (formatted) - may be 12/14 or 12/15 depending on timezone
    expect(actualMessage).toMatch(/12\/(14|15)\/2025/);
  });

  test('FAIL: Complete message format with ALL actual data', async () => {
    await remindOutcome(123, 456, 789);

    // Wait for async fetch
    await new Promise(resolve => setTimeout(resolve, 10));

    const messageElement = global.document.getElementById('reminderMessage');
    const actualMessage = messageElement.value;

    // The COMPLETE expected message with ACTUAL data (date may vary by timezone)
    const expectedPattern = /Dear Sarah Chen.*Fall 2025 - BIOL-301.*Section 001.*CLO #2.*12\/(14|15)\/2025/s;
    
    expect(actualMessage).toMatch(expectedPattern);
    
    // Explicitly verify NO generic placeholders
    expect(actualMessage).not.toContain('Dear Instructor,');
    expect(actualMessage).not.toMatch(/\bCourse,/);
    expect(actualMessage).not.toContain('CLO #?');
  });
});
