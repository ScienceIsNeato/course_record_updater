/**
 * Unit Tests for Course Outcome (CLO) Management UI
 *
 * Load the implementation at module level
 */
require('../../../static/outcomeManagement.js');

/**
 * Unit Tests for Course Outcome (CLO) Management UI
 *
 * Tests modal behavior, form validation, and API interactions for:
 * - Create Outcome modal
 * - Edit Outcome modal
 * - Delete Outcome confirmation
 *
 * TDD Approach: Tests written before implementation
 * FINAL ENTITY in TDD UI Implementation!
 */

describe('Outcome Management - Create Outcome Modal', () => {
  let mockFetch;
  let consoleErrorSpy;

  beforeEach(() => {
    // Set up DOM
    document.body.innerHTML = `
      <form id="createOutcomeForm">
        <select id="outcomeCourseId" name="course_id" required>
          <option value="">Select Course</option>
          <option value="course-1">CS101 - Intro to CS</option>
          <option value="course-2">CS202 - Data Structures</option>
        </select>
        <input type="text" id="outcomeCloNumber" name="clo_number" required placeholder="CLO1" />
        <textarea id="outcomeDescription" name="description" required rows="3"></textarea>
        <input type="text" id="outcomeAssessmentMethod" name="assessment_method" placeholder="Optional" />
        <div class="form-check">
          <input type="checkbox" id="outcomeActive" name="active" checked />
          <label for="outcomeActive">Active</label>
        </div>
        <button type="submit" id="createOutcomeBtn">
          <span class="btn-text">Create Outcome</span>
          <span class="btn-spinner d-none">Creating...</span>
        </button>
      </form>
      <div class="modal" id="createOutcomeModal"></div>
      <meta name="csrf-token" content="test-csrf-token">
    `;

    // Mock fetch
    mockFetch = jest.fn();
    global.fetch = mockFetch;

    // Mock console.error
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

    // Mock Bootstrap Modal
    global.bootstrap = {
      Modal: {
        getInstance: jest.fn(() => ({
          hide: jest.fn()
        }))
      }
    };

    // Trigger DOMContentLoaded to initialize event listeners
    document.dispatchEvent(new Event('DOMContentLoaded'));
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Form Validation', () => {
    test('should require course selection', () => {
      const courseSelect = document.getElementById('outcomeCourseId');

      courseSelect.value = '';
      expect(courseSelect.validity.valid).toBe(false);

      courseSelect.value = 'course-1';
      expect(courseSelect.validity.valid).toBe(true);
    });

    test('should require CLO number', () => {
      const cloInput = document.getElementById('outcomeCloNumber');

      cloInput.value = '';
      expect(cloInput.validity.valid).toBe(false);

      cloInput.value = 'CLO1';
      expect(cloInput.validity.valid).toBe(true);
    });

    test('should require description', () => {
      const descInput = document.getElementById('outcomeDescription');

      descInput.value = '';
      expect(descInput.validity.valid).toBe(false);

      descInput.value = 'Students will demonstrate understanding of...';
      expect(descInput.validity.valid).toBe(true);
    });

    test('should have active checkbox checked by default', () => {
      const activeCheckbox = document.getElementById('outcomeActive');
      expect(activeCheckbox.checked).toBe(true);
    });

    test('should allow assessment method to be empty', () => {
      const assessmentInput = document.getElementById('outcomeAssessmentMethod');
      assessmentInput.value = '';
      // Assessment method is not required
      expect(assessmentInput.validity.valid).toBe(true);
    });
  });

  describe('Form Submission - API Call', () => {
    test('should POST outcome data to /api/outcomes on form submit', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          outcome_id: 'outcome-123',
          message: 'Outcome created'
        })
      });

      const form = document.getElementById('createOutcomeForm');
      document.getElementById('outcomeCourseId').value = 'course-1';
      document.getElementById('outcomeCloNumber').value = 'CLO1';
      document.getElementById('outcomeDescription').value = 'Students will analyze...';
      document.getElementById('outcomeAssessmentMethod').value = 'Final Exam';
      document.getElementById('outcomeActive').checked = true;

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/outcomes',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'X-CSRFToken': 'test-csrf-token'
          }),
          body: expect.stringContaining('CLO1')
        })
      );
    });

    test('should include all outcome fields in POST body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, outcome_id: 'outcome-123' })
      });

      const form = document.getElementById('createOutcomeForm');
      document.getElementById('outcomeCourseId').value = 'course-2';
      document.getElementById('outcomeCloNumber').value = 'CLO3';
      document.getElementById('outcomeDescription').value = 'Apply data structures';
      document.getElementById('outcomeAssessmentMethod').value = 'Project';
      document.getElementById('outcomeActive').checked = false;

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body).toMatchObject({
        course_id: 'course-2',
        clo_number: 'CLO3',
        description: 'Apply data structures',
        assessment_method: 'Project',
        active: false
      });
    });

    test('should handle empty assessment method as null', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, outcome_id: 'outcome-123' })
      });

      const form = document.getElementById('createOutcomeForm');
      document.getElementById('outcomeCourseId').value = 'course-1';
      document.getElementById('outcomeCloNumber').value = 'CLO1';
      document.getElementById('outcomeDescription').value = 'Test description';
      document.getElementById('outcomeAssessmentMethod').value = '';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body.assessment_method).toBeNull();
    });

    test('should show loading state during API call', async () => {
      mockFetch.mockImplementationOnce(
        () =>
          new Promise(resolve =>
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: async () => ({ success: true })
                }),
              100
            )
          )
      );

      const form = document.getElementById('createOutcomeForm');
      document.getElementById('outcomeCourseId').value = 'course-1';
      document.getElementById('outcomeCloNumber').value = 'CLO1';
      document.getElementById('outcomeDescription').value = 'Test';

      const btnText = document.querySelector('.btn-text');
      const btnSpinner = document.querySelector('.btn-spinner');

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 10));

      // Loading state should be active
      expect(btnText.classList.contains('d-none')).toBe(true);
      expect(btnSpinner.classList.contains('d-none')).toBe(false);

      // Wait for completion
      await new Promise(resolve => setTimeout(resolve, 150));

      // Should return to normal
      expect(btnText.classList.contains('d-none')).toBe(false);
      expect(btnSpinner.classList.contains('d-none')).toBe(true);
    });

    test('should close modal and reset form on success', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          outcome_id: 'outcome-123',
          message: 'Outcome created'
        })
      });

      const form = document.getElementById('createOutcomeForm');
      const courseSelect = document.getElementById('outcomeCourseId');

      courseSelect.value = 'course-1';
      document.getElementById('outcomeCloNumber').value = 'CLO1';
      document.getElementById('outcomeDescription').value = 'Test';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      // Modal should be closed
      expect(bootstrap.Modal.getInstance).toHaveBeenCalled();

      // Form should be reset
      expect(courseSelect.value).toBe('');
    });

    test('should display error message on API failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ error: 'CLO number already exists for this course' })
      });

      global.alert = jest.fn();

      const form = document.getElementById('createOutcomeForm');
      document.getElementById('outcomeCourseId').value = 'course-1';
      document.getElementById('outcomeCloNumber').value = 'CLO1';
      document.getElementById('outcomeDescription').value = 'Test';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(global.alert).toHaveBeenCalledWith(
        expect.stringContaining('CLO number already exists')
      );
    });

    test('should handle network errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      global.alert = jest.fn();

      const form = document.getElementById('createOutcomeForm');
      document.getElementById('outcomeCourseId').value = 'course-1';
      document.getElementById('outcomeCloNumber').value = 'CLO1';
      document.getElementById('outcomeDescription').value = 'Test';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(global.alert).toHaveBeenCalledWith(
        expect.stringContaining('Failed to create outcome')
      );
      expect(consoleErrorSpy).toHaveBeenCalled();
    });
  });

  describe('CSRF Token Handling', () => {
    test('should include CSRF token in headers', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, outcome_id: 'outcome-123' })
      });

      const form = document.getElementById('createOutcomeForm');
      document.getElementById('outcomeCourseId').value = 'course-1';
      document.getElementById('outcomeCloNumber').value = 'CLO1';
      document.getElementById('outcomeDescription').value = 'Test';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      expect(callArgs[1].headers['X-CSRFToken']).toBe('test-csrf-token');
    });
  });
});

describe('Outcome Management - Edit Outcome Modal', () => {
  let mockFetch;

  beforeEach(() => {
    document.body.innerHTML = `
      <form id="editOutcomeForm">
        <input type="hidden" id="editOutcomeId" />
        <input type="text" id="editOutcomeCloNumber" required />
        <textarea id="editOutcomeDescription" required rows="3"></textarea>
        <input type="text" id="editOutcomeAssessmentMethod" />
        <div class="form-check">
          <input type="checkbox" id="editOutcomeActive" name="active" />
          <label for="editOutcomeActive">Active</label>
        </div>
        <button type="submit">
          <span class="btn-text">Update</span>
          <span class="btn-spinner d-none">Updating...</span>
        </button>
      </form>
      <div class="modal" id="editOutcomeModal"></div>
      <meta name="csrf-token" content="test-csrf-token">
    `;

    mockFetch = jest.fn();
    global.fetch = mockFetch;

    global.bootstrap = {
      Modal: {
        getInstance: jest.fn(() => ({
          hide: jest.fn()
        })),
        prototype: {
          show: jest.fn()
        }
      }
    };

    // Trigger DOMContentLoaded to initialize event listeners
    document.dispatchEvent(new Event('DOMContentLoaded'));
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('openEditOutcomeModal should populate form and show modal', () => {
    const mockModal = { show: jest.fn() };
    global.bootstrap.Modal = jest.fn(() => mockModal);

    window.openEditOutcomeModal('outcome-123', {
      clo_number: 'CLO2',
      description: 'Students will evaluate...',
      assessment_method: 'Midterm',
      active: true
    });

    expect(document.getElementById('editOutcomeId').value).toBe('outcome-123');
    expect(document.getElementById('editOutcomeCloNumber').value).toBe('CLO2');
    expect(document.getElementById('editOutcomeDescription').value).toBe('Students will evaluate...');
    expect(document.getElementById('editOutcomeAssessmentMethod').value).toBe('Midterm');
    expect(document.getElementById('editOutcomeActive').checked).toBe(true);
    expect(mockModal.show).toHaveBeenCalled();
  });

  test('should PUT updated outcome data to /api/outcomes/<id>', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, message: 'Outcome updated' })
    });

    const form = document.getElementById('editOutcomeForm');
    document.getElementById('editOutcomeId').value = 'outcome-123';
    document.getElementById('editOutcomeCloNumber').value = 'CLO3';
    document.getElementById('editOutcomeDescription').value = 'Updated description';
    document.getElementById('editOutcomeAssessmentMethod').value = 'Final Project';
    document.getElementById('editOutcomeActive').checked = false;

    const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
    form.dispatchEvent(submitEvent);

    await new Promise(resolve => setTimeout(resolve, 100));

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/outcomes/outcome-123',
      expect.objectContaining({
        method: 'PUT',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'X-CSRFToken': 'test-csrf-token'
        }),
        body: expect.stringContaining('Updated description')
      })
    );

    const callArgs = mockFetch.mock.calls[0];
    const body = JSON.parse(callArgs[1].body);
    expect(body.active).toBe(false);
    expect(body.assessment_method).toBe('Final Project');
  });
});

describe('Outcome Management - Delete Outcome', () => {
  let mockFetch;
  let confirmSpy;
  let alertSpy;

  beforeEach(() => {
    document.body.innerHTML = '<meta name="csrf-token" content="test-csrf-token">';
    mockFetch = jest.fn();
    global.fetch = mockFetch;
    confirmSpy = jest.spyOn(window, 'confirm');
    alertSpy = jest.spyOn(window, 'alert').mockImplementation();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('should DELETE outcome with confirmation', async () => {
    confirmSpy.mockReturnValue(true);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true })
    });

    await window.deleteOutcome('outcome-123', 'CS101', 'CLO1');

    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringContaining('CLO1')
    );
    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringContaining('CS101')
    );
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/outcomes/outcome-123',
      expect.objectContaining({
        method: 'DELETE',
        headers: expect.objectContaining({
          'X-CSRFToken': 'test-csrf-token'
        })
      })
    );
    expect(alertSpy).toHaveBeenCalledWith(
      expect.stringContaining('deleted successfully')
    );
  });

  test('should not delete if user cancels confirmation', async () => {
    confirmSpy.mockReturnValue(false);

    await window.deleteOutcome('outcome-123', 'CS101', 'CLO1');

    expect(mockFetch).not.toHaveBeenCalled();
    expect(alertSpy).not.toHaveBeenCalled();
  });

  test('should handle API errors gracefully', async () => {
    confirmSpy.mockReturnValue(true);
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: 'Outcome has assessment data' })
    });

    await window.deleteOutcome('outcome-123', 'CS101', 'CLO1');

    expect(alertSpy).toHaveBeenCalledWith(
      expect.stringContaining('Outcome has assessment data')
    );
  });

  test('should handle network errors during delete', async () => {
    confirmSpy.mockReturnValue(true);
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    await window.deleteOutcome('outcome-123', 'CS101', 'CLO1');

    expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining('try again'));
  });
});

