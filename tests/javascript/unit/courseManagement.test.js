/**
 * Unit Tests for Course Management UI
 *
 * Tests modal behavior, form validation, and API interactions for:
 * - Create Course modal
 * - Edit Course modal
 * - Delete Course confirmation
 *
 * TDD Approach: Tests written before implementation
 */

// Load the implementation
require('../../../static/courseManagement.js');

describe('Course Management - Create Course Modal', () => {
  let mockFetch;
  let consoleErrorSpy;

  beforeEach(() => {
    // Set up DOM
    document.body.innerHTML = `
      <form id="createCourseForm">
        <input type="text" id="courseNumber" name="course_number" required />
        <input type="text" id="courseTitle" name="course_title" required />
        <input type="text" id="courseDepartment" name="department" required />
        <input type="number" id="courseCreditHours" name="credit_hours" value="3" min="0" max="12" required />
        <select id="courseProgramIds" name="program_ids" multiple>
          <option value="prog-1">Computer Science</option>
          <option value="prog-2">Engineering</option>
          <option value="prog-3">Business</option>
        </select>
        <div class="form-check">
          <input type="checkbox" id="courseActive" name="active" checked />
          <label for="courseActive">Active</label>
        </div>
        <button type="submit" id="createCourseBtn">
          <span class="btn-text">Create Course</span>
          <span class="btn-spinner d-none">Creating...</span>
        </button>
      </form>
      <div class="modal" id="createCourseModal"></div>
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
    test('should require course number', () => {
      const numberInput = document.getElementById('courseNumber');

      numberInput.value = '';
      expect(numberInput.validity.valid).toBe(false);

      numberInput.value = 'CS101';
      expect(numberInput.validity.valid).toBe(true);
    });

    test('should require course title', () => {
      const titleInput = document.getElementById('courseTitle');

      titleInput.value = '';
      expect(titleInput.validity.valid).toBe(false);

      titleInput.value = 'Introduction to Computer Science';
      expect(titleInput.validity.valid).toBe(true);
    });

    test('should require department', () => {
      const deptInput = document.getElementById('courseDepartment');

      deptInput.value = '';
      expect(deptInput.validity.valid).toBe(false);

      deptInput.value = 'Computer Science';
      expect(deptInput.validity.valid).toBe(true);
    });

    test('should validate credit hours range', () => {
      const creditInput = document.getElementById('courseCreditHours');

      creditInput.value = '-1';
      expect(creditInput.validity.rangeUnderflow).toBe(true);

      creditInput.value = '15';
      expect(creditInput.validity.rangeOverflow).toBe(true);

      creditInput.value = '3';
      expect(creditInput.validity.valid).toBe(true);
    });

    test('should have active checkbox checked by default', () => {
      const activeCheckbox = document.getElementById('courseActive');
      expect(activeCheckbox.checked).toBe(true);
    });

    test('should allow multiple program selection', () => {
      const programSelect = document.getElementById('courseProgramIds');
      expect(programSelect.multiple).toBe(true);
    });
  });

  describe('Form Submission - API Call', () => {
    test('should POST course data to /api/courses on form submit', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          course_id: 'course-123',
          message: 'Course created'
        })
      });

      const form = document.getElementById('createCourseForm');
      document.getElementById('courseNumber').value = 'CS101';
      document.getElementById('courseTitle').value = 'Intro to CS';
      document.getElementById('courseDepartment').value = 'Computer Science';
      document.getElementById('courseCreditHours').value = '3';
      document.getElementById('courseActive').checked = true;

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/courses',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'X-CSRFToken': 'test-csrf-token'
          }),
          body: expect.stringContaining('CS101')
        })
      );
    });

    test('should include all course fields in POST body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, course_id: 'course-123' })
      });

      const form = document.getElementById('createCourseForm');
      document.getElementById('courseNumber').value = 'CS101';
      document.getElementById('courseTitle').value = 'Intro to CS';
      document.getElementById('courseDepartment').value = 'Computer Science';
      document.getElementById('courseCreditHours').value = '4';
      document.getElementById('courseActive').checked = false;

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body).toMatchObject({
        course_number: 'CS101',
        course_title: 'Intro to CS',
        department: 'Computer Science',
        credit_hours: 4,
        active: false
      });
    });

    test('should include selected program IDs in POST body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, course_id: 'course-123' })
      });

      const form = document.getElementById('createCourseForm');
      document.getElementById('courseNumber').value = 'CS101';
      document.getElementById('courseTitle').value = 'Intro to CS';
      document.getElementById('courseDepartment').value = 'Computer Science';

      const programSelect = document.getElementById('courseProgramIds');
      programSelect.options[0].selected = true;
      programSelect.options[2].selected = true;

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body.program_ids).toEqual(['prog-1', 'prog-3']);
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

      const form = document.getElementById('createCourseForm');
      document.getElementById('courseNumber').value = 'CS101';
      document.getElementById('courseTitle').value = 'Test';
      document.getElementById('courseDepartment').value = 'CS';

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
          course_id: 'course-123',
          message: 'Course created'
        })
      });

      const form = document.getElementById('createCourseForm');
      const numberInput = document.getElementById('courseNumber');

      numberInput.value = 'CS101';
      document.getElementById('courseTitle').value = 'Intro to CS';
      document.getElementById('courseDepartment').value = 'Computer Science';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      // Modal should be closed
      expect(bootstrap.Modal.getInstance).toHaveBeenCalled();

      // Form should be reset
      expect(numberInput.value).toBe('');
    });

    test('should display error message on API failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ error: 'Course number already exists' })
      });

      global.alert = jest.fn();

      const form = document.getElementById('createCourseForm');
      document.getElementById('courseNumber').value = 'CS101';
      document.getElementById('courseTitle').value = 'Test';
      document.getElementById('courseDepartment').value = 'CS';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(global.alert).toHaveBeenCalledWith(
        expect.stringContaining('Course number already exists')
      );
    });

    test('should handle network errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      global.alert = jest.fn();

      const form = document.getElementById('createCourseForm');
      document.getElementById('courseNumber').value = 'CS101';
      document.getElementById('courseTitle').value = 'Test';
      document.getElementById('courseDepartment').value = 'CS';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(global.alert).toHaveBeenCalledWith(
        expect.stringContaining('Failed to create course')
      );
      expect(consoleErrorSpy).toHaveBeenCalled();
    });
  });

  describe('CSRF Token Handling', () => {
    test('should include CSRF token in headers', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, course_id: 'course-123' })
      });

      const form = document.getElementById('createCourseForm');
      document.getElementById('courseNumber').value = 'CS101';
      document.getElementById('courseTitle').value = 'Test';
      document.getElementById('courseDepartment').value = 'CS';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      expect(callArgs[1].headers['X-CSRFToken']).toBe('test-csrf-token');
    });
  });
});

describe('Course Management - Edit Course Modal', () => {
  let mockFetch;

  beforeEach(() => {
    document.body.innerHTML = `
      <form id="editCourseForm">
        <input type="hidden" id="editCourseId" />
        <input type="text" id="editCourseNumber" required />
        <input type="text" id="editCourseTitle" required />
        <input type="text" id="editCourseDepartment" required />
        <input type="number" id="editCourseCreditHours" min="0" max="12" required />
        <select id="editCourseProgramIds" multiple>
          <option value="prog-1">Computer Science</option>
          <option value="prog-2">Engineering</option>
        </select>
        <div class="form-check">
          <input type="checkbox" id="editCourseActive" name="active" />
          <label for="editCourseActive">Active</label>
        </div>
        <button type="submit">
          <span class="btn-text">Update</span>
          <span class="btn-spinner d-none">Updating...</span>
        </button>
      </form>
      <div class="modal" id="editCourseModal"></div>
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

  test('openEditCourseModal should populate form and show modal', () => {
    const mockModal = { show: jest.fn() };
    global.bootstrap.Modal = jest.fn(() => mockModal);

    window.openEditCourseModal('course-123', {
      course_number: 'CS101',
      course_title: 'Intro to CS',
      department: 'Computer Science',
      credit_hours: 3,
      program_ids: ['prog-1'],
      active: true
    });

    expect(document.getElementById('editCourseId').value).toBe('course-123');
    expect(document.getElementById('editCourseNumber').value).toBe('CS101');
    expect(document.getElementById('editCourseTitle').value).toBe('Intro to CS');
    expect(document.getElementById('editCourseDepartment').value).toBe('Computer Science');
    expect(document.getElementById('editCourseCreditHours').value).toBe('3');
    expect(document.getElementById('editCourseActive').checked).toBe(true);
    expect(mockModal.show).toHaveBeenCalled();
  });

  test('should PUT updated course data to /api/courses/<id>', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, message: 'Course updated' })
    });

    const form = document.getElementById('editCourseForm');
    document.getElementById('editCourseId').value = 'course-123';
    document.getElementById('editCourseNumber').value = 'CS102';
    document.getElementById('editCourseTitle').value = 'Updated Course';
    document.getElementById('editCourseDepartment').value = 'CS';
    document.getElementById('editCourseCreditHours').value = '4';
    document.getElementById('editCourseActive').checked = false;

    const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
    form.dispatchEvent(submitEvent);

    await new Promise(resolve => setTimeout(resolve, 100));

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/courses/course-123',
      expect.objectContaining({
        method: 'PUT',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'X-CSRFToken': 'test-csrf-token'
        }),
        body: expect.stringContaining('Updated Course')
      })
    );

    const callArgs = mockFetch.mock.calls[0];
    const body = JSON.parse(callArgs[1].body);
    expect(body.active).toBe(false);
    expect(body.credit_hours).toBe(4);
  });
});

describe('Course Management - Delete Course', () => {
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

  test('should DELETE course with confirmation', async () => {
    confirmSpy.mockReturnValue(true);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true })
    });

    await window.deleteCourse('course-123', 'CS101', 'Intro to CS');

    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringContaining('CS101')
    );
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/courses/course-123',
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

    await window.deleteCourse('course-123', 'CS101', 'Intro to CS');

    expect(mockFetch).not.toHaveBeenCalled();
    expect(alertSpy).not.toHaveBeenCalled();
  });

  test('should handle API errors gracefully', async () => {
    confirmSpy.mockReturnValue(true);
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: 'Course has active offerings' })
    });

    await window.deleteCourse('course-123', 'CS101', 'Intro to CS');

    expect(alertSpy).toHaveBeenCalledWith(
      expect.stringContaining('Course has active offerings')
    );
  });
});

