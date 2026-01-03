/**
 * Unit Tests for Course Section Management UI
 *
 * Tests modal behavior, form validation, and API interactions for:
 * - Create Section modal
 * - Edit Section modal
 * - Delete Section confirmation
 *
 * TDD Approach: Tests written before implementation
 */

// Load the implementation
require('../../../static/sectionManagement.js');

describe('Section Management - Create Section Modal', () => {
  let mockFetch;
  let consoleErrorSpy;

  beforeEach(() => {
    // Set up DOM
    document.body.innerHTML = `
      <form id="createSectionForm">
        <select id="sectionOfferingId" name="offering_id" required>
          <option value="">Select Offering</option>
          <option value="offering-1">CS101 - Fall 2024</option>
          <option value="offering-2">CS202 - Fall 2024</option>
        </select>
        <input type="text" id="sectionNumber" name="section_number" value="001" required />
        <select id="sectionInstructorId" name="instructor_id">
          <option value="">Unassigned</option>
          <option value="instr-1">Dr. Smith</option>
          <option value="instr-2">Prof. Jones</option>
        </select>
        <input type="number" id="sectionEnrollment" name="enrollment" min="0" placeholder="Optional" />
        <select id="sectionStatus" name="status" required>
          <option value="assigned" selected>Assigned</option>
          <option value="pending">Pending</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <button type="submit" id="createSectionBtn">
          <span class="btn-text">Create Section</span>
          <span class="btn-spinner d-none">Creating...</span>
        </button>
      </form>
      <div class="modal" id="createSectionModal"></div>
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
    test('should require offering selection', () => {
      const offeringSelect = document.getElementById('sectionOfferingId');

      offeringSelect.value = '';
      expect(offeringSelect.validity.valid).toBe(false);

      offeringSelect.value = 'offering-1';
      expect(offeringSelect.validity.valid).toBe(true);
    });

    test('should require section number', () => {
      const sectionInput = document.getElementById('sectionNumber');

      sectionInput.value = '';
      expect(sectionInput.validity.valid).toBe(false);

      sectionInput.value = '001';
      expect(sectionInput.validity.valid).toBe(true);
    });

    test('should have section number default to 001', () => {
      const sectionInput = document.getElementById('sectionNumber');
      expect(sectionInput.value).toBe('001');
    });

    test('should have status default to assigned', () => {
      const statusSelect = document.getElementById('sectionStatus');
      expect(statusSelect.value).toBe('assigned');
    });

    test('should allow instructor to be unassigned', () => {
      const instructorSelect = document.getElementById('sectionInstructorId');
      instructorSelect.value = '';
      // Instructor is not required
      expect(instructorSelect.value).toBe('');
    });
  });

  describe('Form Submission - API Call', () => {
    test('should POST section data to /api/sections on form submit', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          section_id: 'section-123',
          message: 'Section created'
        })
      });

      const form = document.getElementById('createSectionForm');
      document.getElementById('sectionOfferingId').value = 'offering-1';
      document.getElementById('sectionNumber').value = '002';
      document.getElementById('sectionInstructorId').value = 'instr-1';
      document.getElementById('sectionEnrollment').value = '25';
      document.getElementById('sectionStatus').value = 'assigned';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/sections',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'X-CSRFToken': 'test-csrf-token'
          }),
          body: expect.stringContaining('offering-1')
        })
      );
    });

    test('should include all section fields in POST body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, section_id: 'section-123' })
      });

      const form = document.getElementById('createSectionForm');
      document.getElementById('sectionOfferingId').value = 'offering-2';
      document.getElementById('sectionNumber').value = '003';
      document.getElementById('sectionInstructorId').value = 'instr-2';
      document.getElementById('sectionEnrollment').value = '30';
      document.getElementById('sectionStatus').value = 'pending';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body).toMatchObject({
        offering_id: 'offering-2',
        section_number: '003',
        instructor_id: 'instr-2',
        enrollment: 30,
        status: 'pending'
      });
    });

    test('should handle empty instructor as null', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, section_id: 'section-123' })
      });

      const form = document.getElementById('createSectionForm');
      document.getElementById('sectionOfferingId').value = 'offering-1';
      document.getElementById('sectionNumber').value = '001';
      document.getElementById('sectionInstructorId').value = '';
      document.getElementById('sectionEnrollment').value = '';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body.instructor_id).toBeNull();
      expect(body.enrollment).toBeNull();
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

      const form = document.getElementById('createSectionForm');
      document.getElementById('sectionOfferingId').value = 'offering-1';
      document.getElementById('sectionNumber').value = '001';

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
          section_id: 'section-123',
          message: 'Section created'
        })
      });

      const form = document.getElementById('createSectionForm');
      const offeringSelect = document.getElementById('sectionOfferingId');

      offeringSelect.value = 'offering-1';
      document.getElementById('sectionNumber').value = '002';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      // Modal should be closed
      expect(bootstrap.Modal.getInstance).toHaveBeenCalled();

      // Form should be reset (section number should be back to default 001)
      expect(document.getElementById('sectionNumber').value).toBe('001');
    });

    test('should display error message on API failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ error: 'Section number already exists' })
      });

      global.alert = jest.fn();

      const form = document.getElementById('createSectionForm');
      document.getElementById('sectionOfferingId').value = 'offering-1';
      document.getElementById('sectionNumber').value = '001';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(global.alert).toHaveBeenCalledWith(
        expect.stringContaining('Section number already exists')
      );
    });

    test('should handle network errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      global.alert = jest.fn();

      const form = document.getElementById('createSectionForm');
      document.getElementById('sectionOfferingId').value = 'offering-1';
      document.getElementById('sectionNumber').value = '001';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(global.alert).toHaveBeenCalledWith(
        expect.stringContaining('Failed to create section')
      );
      expect(consoleErrorSpy).toHaveBeenCalled();
    });
  });

  describe('CSRF Token Handling', () => {
    test('should include CSRF token in headers', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, section_id: 'section-123' })
      });

      const form = document.getElementById('createSectionForm');
      document.getElementById('sectionOfferingId').value = 'offering-1';
      document.getElementById('sectionNumber').value = '001';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      expect(callArgs[1].headers['X-CSRFToken']).toBe('test-csrf-token');
    });
  });
});

describe('Section Management - Edit Section Modal', () => {
  let mockFetch;

  beforeEach(() => {
    document.body.innerHTML = `
      <form id="editSectionForm">
        <input type="hidden" id="editSectionId" />
        <input type="text" id="editSectionNumber" required />
        <select id="editSectionInstructorId">
          <option value="">Unassigned</option>
          <option value="instr-1">Dr. Smith</option>
          <option value="instr-2">Prof. Jones</option>
        </select>
        <input type="number" id="editSectionEnrollment" min="0" />
        <select id="editSectionStatus" required>
          <option value="assigned">Assigned</option>
          <option value="pending">Pending</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <button type="submit">
          <span class="btn-text">Update</span>
          <span class="btn-spinner d-none">Updating...</span>
        </button>
      </form>
      <div class="modal" id="editSectionModal"></div>
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

  test('openEditSectionModal should populate form and show modal', async () => {
    const mockModal = { show: jest.fn() };
    global.bootstrap.Modal = jest.fn(() => mockModal);

    // Mock the instructor fetch
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ data: [] })
    });

    await window.openEditSectionModal('section-123', {
      section_number: '002',
      instructor_id: 'instr-1',
      enrollment: 25,
      status: 'pending'
    });

    expect(document.getElementById('editSectionId').value).toBe('section-123');
    expect(document.getElementById('editSectionNumber').value).toBe('002');
    expect(document.getElementById('editSectionEnrollment').value).toBe('25');
    expect(document.getElementById('editSectionStatus').value).toBe('pending');
    expect(mockModal.show).toHaveBeenCalled();
  });

  test('should PUT updated section data to /api/sections/<id>', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, message: 'Section updated' })
    });

    const form = document.getElementById('editSectionForm');
    document.getElementById('editSectionId').value = 'section-123';
    document.getElementById('editSectionNumber').value = '003';
    document.getElementById('editSectionInstructorId').value = 'instr-2';
    document.getElementById('editSectionEnrollment').value = '30';
    document.getElementById('editSectionStatus').value = 'cancelled';

    const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
    form.dispatchEvent(submitEvent);

    await new Promise(resolve => setTimeout(resolve, 100));

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/sections/section-123',
      expect.objectContaining({
        method: 'PUT',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'X-CSRFToken': 'test-csrf-token'
        }),
        body: expect.stringContaining('003')
      })
    );

    const callArgs = mockFetch.mock.calls[0];
    const body = JSON.parse(callArgs[1].body);
    expect(body.status).toBe('cancelled');
    expect(body.enrollment).toBe(30);
  });
});

describe('Section Management - Delete Section', () => {
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

  test('should DELETE section with confirmation', async () => {
    confirmSpy.mockReturnValue(true);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true })
    });

    await window.deleteSection('section-123', 'CS101', '002');

    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringContaining('CS101')
    );
    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringContaining('002')
    );
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/sections/section-123',
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

    await window.deleteSection('section-123', 'CS101', '002');

    expect(mockFetch).not.toHaveBeenCalled();
    expect(alertSpy).not.toHaveBeenCalled();
  });

  test('should handle API errors gracefully', async () => {
    confirmSpy.mockReturnValue(true);
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: 'Section has enrolled students' })
    });

    await window.deleteSection('section-123', 'CS101', '002');

    expect(alertSpy).toHaveBeenCalledWith(
      expect.stringContaining('Section has enrolled students')
    );
  });
});

describe('Section Management - Edit Modal Instructor Loading', () => {
  let mockFetch;
  let consoleErrorSpy;

  beforeEach(() => {
    document.body.innerHTML = `
      <form id="editSectionForm">
        <input type="hidden" id="editSectionId" />
        <input type="text" id="editSectionNumber" required />
        <select id="editSectionInstructorId">
          <option value="">Unassigned</option>
        </select>
        <input type="number" id="editSectionEnrollment" min="0" />
        <select id="editSectionStatus" required>
          <option value="assigned">Assigned</option>
        </select>
        <button type="submit">Update</button>
      </form>
      <div class="modal" id="editSectionModal"></div>
      <meta name="csrf-token" content="test-csrf-token">
    `;

    mockFetch = jest.fn();
    global.fetch = mockFetch;
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

    global.bootstrap = {
      Modal: jest.fn(() => ({
        show: jest.fn()
      }))
    };

    document.dispatchEvent(new Event('DOMContentLoaded'));
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('should populate instructor dropdown from API response', async () => {
    // Mock instructors API response (lines 194-197)
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        users: [
          {
            user_id: 'instructor-1',
            first_name: 'John',
            last_name: 'Doe',
            email: 'john@example.com'
          },
          {
            id: 'instructor-2',
            first_name: 'Jane',
            last_name: 'Smith',
            email: 'jane@example.com'
          }
        ]
      })
    });

    await window.openEditSectionModal('section-123', {
      section_number: '002',
      instructor_id: 'instructor-1',
      enrollment: 25,
      status: 'assigned'
    });

    const instructorSelect = document.getElementById('editSectionInstructorId');
    const options = Array.from(instructorSelect.options);

    // Should have original "Unassigned" option plus 2 instructors
    expect(options.length).toBe(3);

    // Check instructor options were added (lines 194-197)
    expect(options[1].value).toBe('instructor-1');
    expect(options[1].textContent).toBe('John Doe (john@example.com)');

    expect(options[2].value).toBe('instructor-2');
    expect(options[2].textContent).toBe('Jane Smith (jane@example.com)');

    // Should select the section's current instructor
    expect(instructorSelect.value).toBe('instructor-1');
  });

  test('should handle instructor loading errors gracefully (line 206)', async () => {
    // Mock API error
    mockFetch.mockRejectedValueOnce(new Error('Network failure'));

    await window.openEditSectionModal('section-123', {
      section_number: '002',
      instructor_id: null,
      enrollment: 25,
      status: 'assigned'
    });

    // Should log error (line 206)
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'Error loading instructors:',
      expect.any(Error)
    );

    // Modal should still open despite error
    expect(global.bootstrap.Modal).toHaveBeenCalled();
  });

  test('should handle instructor API returning non-ok status', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ error: 'Internal server error' })
    });

    await window.openEditSectionModal('section-123', {
      section_number: '002',
      instructor_id: null,
      enrollment: 25,
      status: 'assigned'
    });

    // Should not crash, modal should still work
    expect(global.bootstrap.Modal).toHaveBeenCalled();
    const instructorSelect = document.getElementById('editSectionInstructorId');
    // Should only have the default "Unassigned" option
    expect(instructorSelect.options.length).toBe(1);
  });
});

