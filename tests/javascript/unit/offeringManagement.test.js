/**
 * Unit Tests for Course Offering Management UI
 *
 * Tests modal behavior, form validation, and API interactions for:
 * - Create Offering modal
 * - Edit Offering modal
 * - Delete Offering confirmation
 *
 * TDD Approach: Tests written before implementation
 */

// Load the implementation
require('../../../static/offeringManagement.js');

describe('Offering Management - Create Offering Modal', () => {
  let mockFetch;
  let consoleErrorSpy;

  beforeEach(() => {
    // Set up DOM
    document.body.innerHTML = `
      <form id="createOfferingForm">
        <select id="offeringCourseId" name="course_id" required>
          <option value="">Select Course</option>
          <option value="course-1">CS101 - Intro to CS</option>
          <option value="course-2">CS202 - Data Structures</option>
        </select>
        <select id="offeringTermId" name="term_id" required>
          <option value="">Select Term</option>
          <option value="term-1">Fall 2024</option>
          <option value="term-2">Spring 2025</option>
        </select>
        <select id="offeringStatus" name="status" required>
          <option value="active" selected>Active</option>
          <option value="planning">Planning</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <input type="number" id="offeringCapacity" name="capacity" min="0" placeholder="Optional" />
        <button type="submit" id="createOfferingBtn">
          <span class="btn-text">Create Offering</span>
          <span class="btn-spinner d-none">Creating...</span>
        </button>
      </form>
      <div class="modal" id="createOfferingModal"></div>
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
      const courseSelect = document.getElementById('offeringCourseId');

      courseSelect.value = '';
      expect(courseSelect.validity.valid).toBe(false);

      courseSelect.value = 'course-1';
      expect(courseSelect.validity.valid).toBe(true);
    });

    test('should require term selection', () => {
      const termSelect = document.getElementById('offeringTermId');

      termSelect.value = '';
      expect(termSelect.validity.valid).toBe(false);

      termSelect.value = 'term-1';
      expect(termSelect.validity.valid).toBe(true);
    });

    test('should have status default to active', () => {
      const statusSelect = document.getElementById('offeringStatus');
      expect(statusSelect.value).toBe('active');
    });

    test('should allow capacity to be empty', () => {
      const capacityInput = document.getElementById('offeringCapacity');
      capacityInput.value = '';
      // Capacity is not required
      expect(capacityInput.validity.valid).toBe(true);
    });
  });

  describe('Form Submission - API Call', () => {
    test('should POST offering data to /api/offerings on form submit', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          offering_id: 'offering-123',
          message: 'Offering created'
        })
      });

      const form = document.getElementById('createOfferingForm');
      document.getElementById('offeringCourseId').value = 'course-1';
      document.getElementById('offeringTermId').value = 'term-1';
      document.getElementById('offeringStatus').value = 'active';
      document.getElementById('offeringCapacity').value = '30';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/offerings',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'X-CSRFToken': 'test-csrf-token'
          }),
          body: expect.stringContaining('course-1')
        })
      );
    });

    test('should include all offering fields in POST body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, offering_id: 'offering-123' })
      });

      const form = document.getElementById('createOfferingForm');
      document.getElementById('offeringCourseId').value = 'course-2';
      document.getElementById('offeringTermId').value = 'term-2';
      document.getElementById('offeringStatus').value = 'planning';
      document.getElementById('offeringCapacity').value = '50';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body).toMatchObject({
        course_id: 'course-2',
        term_id: 'term-2',
        status: 'planning',
        capacity: 50
      });
    });

    test('should handle empty capacity as null', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, offering_id: 'offering-123' })
      });

      const form = document.getElementById('createOfferingForm');
      document.getElementById('offeringCourseId').value = 'course-1';
      document.getElementById('offeringTermId').value = 'term-1';
      document.getElementById('offeringStatus').value = 'active';
      document.getElementById('offeringCapacity').value = '';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body.capacity).toBeNull();
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

      const form = document.getElementById('createOfferingForm');
      document.getElementById('offeringCourseId').value = 'course-1';
      document.getElementById('offeringTermId').value = 'term-1';

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
          offering_id: 'offering-123',
          message: 'Offering created'
        })
      });

      const form = document.getElementById('createOfferingForm');
      const courseSelect = document.getElementById('offeringCourseId');

      courseSelect.value = 'course-1';
      document.getElementById('offeringTermId').value = 'term-1';

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
        json: async () => ({ error: 'Course already offered in this term' })
      });

      global.alert = jest.fn();

      const form = document.getElementById('createOfferingForm');
      document.getElementById('offeringCourseId').value = 'course-1';
      document.getElementById('offeringTermId').value = 'term-1';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(global.alert).toHaveBeenCalledWith(
        expect.stringContaining('Course already offered in this term')
      );
    });

    test('should handle network errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      global.alert = jest.fn();

      const form = document.getElementById('createOfferingForm');
      document.getElementById('offeringCourseId').value = 'course-1';
      document.getElementById('offeringTermId').value = 'term-1';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(global.alert).toHaveBeenCalledWith(
        expect.stringContaining('Failed to create offering')
      );
      expect(consoleErrorSpy).toHaveBeenCalled();
    });
  });

  describe('CSRF Token Handling', () => {
    test('should include CSRF token in headers', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, offering_id: 'offering-123' })
      });

      const form = document.getElementById('createOfferingForm');
      document.getElementById('offeringCourseId').value = 'course-1';
      document.getElementById('offeringTermId').value = 'term-1';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      expect(callArgs[1].headers['X-CSRFToken']).toBe('test-csrf-token');
    });
  });
});

describe('Offering Management - Edit Offering Modal', () => {
  let mockFetch;

  beforeEach(() => {
    document.body.innerHTML = `
      <form id="editOfferingForm">
        <input type="hidden" id="editOfferingId" />
        <select id="editOfferingStatus" required>
          <option value="active">Active</option>
          <option value="planning">Planning</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <input type="number" id="editOfferingCapacity" min="0" />
        <button type="submit">
          <span class="btn-text">Update</span>
          <span class="btn-spinner d-none">Updating...</span>
        </button>
      </form>
      <div class="modal" id="editOfferingModal"></div>
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

  test('openEditOfferingModal should populate form and show modal', () => {
    const mockModal = { show: jest.fn() };
    global.bootstrap.Modal = jest.fn(() => mockModal);

    window.openEditOfferingModal('offering-123', {
      status: 'planning',
      capacity: 40
    });

    expect(document.getElementById('editOfferingId').value).toBe('offering-123');
    expect(document.getElementById('editOfferingStatus').value).toBe('planning');
    expect(document.getElementById('editOfferingCapacity').value).toBe('40');
    expect(mockModal.show).toHaveBeenCalled();
  });

  test('should PUT updated offering data to /api/offerings/<id>', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, message: 'Offering updated' })
    });

    const form = document.getElementById('editOfferingForm');
    document.getElementById('editOfferingId').value = 'offering-123';
    document.getElementById('editOfferingStatus').value = 'cancelled';
    document.getElementById('editOfferingCapacity').value = '25';

    const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
    form.dispatchEvent(submitEvent);

    await new Promise(resolve => setTimeout(resolve, 100));

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/offerings/offering-123',
      expect.objectContaining({
        method: 'PUT',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'X-CSRFToken': 'test-csrf-token'
        }),
        body: expect.stringContaining('cancelled')
      })
    );

    const callArgs = mockFetch.mock.calls[0];
    const body = JSON.parse(callArgs[1].body);
    expect(body.status).toBe('cancelled');
    expect(body.capacity).toBe(25);
  });
});

describe('Offering Management - Delete Offering', () => {
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

  test('should DELETE offering with confirmation', async () => {
    confirmSpy.mockReturnValue(true);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true })
    });

    await window.deleteOffering('offering-123', 'CS101', 'Fall 2024');

    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringContaining('CS101')
    );
    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringContaining('Fall 2024')
    );
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/offerings/offering-123',
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

    await window.deleteOffering('offering-123', 'CS101', 'Fall 2024');

    expect(mockFetch).not.toHaveBeenCalled();
    expect(alertSpy).not.toHaveBeenCalled();
  });

  test('should handle API errors gracefully', async () => {
    confirmSpy.mockReturnValue(true);
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: 'Offering has sections assigned' })
    });

    await window.deleteOffering('offering-123', 'CS101', 'Fall 2024');

    expect(alertSpy).toHaveBeenCalledWith(
      expect.stringContaining('Offering has sections assigned')
    );
  });
});

