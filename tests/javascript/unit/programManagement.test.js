/**
 * Unit Tests for Program Management UI
 *
 * Tests modal behavior, form validation, and API interactions for:
 * - Create Program modal
 * - Edit Program modal
 * - Delete Program confirmation
 *
 * TDD Approach: Tests written before implementation
 */

// Load the implementation
require('../../../static/programManagement.js');

describe('Program Management - Create Program Modal', () => {
  let mockFetch;
  let consoleErrorSpy;

  beforeEach(() => {
    // Set up DOM
    document.body.innerHTML = `
      <form id="createProgramForm">
        <input type="text" id="programName" name="name" required />
        <input type="text" id="programShortName" name="short_name" required maxlength="10" />
        <select id="programInstitutionId" name="institution_id" required>
          <option value="">Select Institution</option>
          <option value="inst-1">Test University</option>
          <option value="inst-2">Another College</option>
        </select>
        <div class="form-check">
          <input type="checkbox" id="programActive" name="active" checked />
          <label for="programActive">Active</label>
        </div>
        <button type="submit" id="createProgramBtn">
          <span class="btn-text">Create Program</span>
          <span class="btn-spinner d-none">Creating...</span>
        </button>
      </form>
      <div class="modal" id="createProgramModal"></div>
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
    test('should require program name', () => {
      const nameInput = document.getElementById('programName');

      nameInput.value = '';
      expect(nameInput.validity.valid).toBe(false);

      nameInput.value = 'Computer Science';
      expect(nameInput.validity.valid).toBe(true);
    });

    test('should require institution selection', () => {
      const institutionSelect = document.getElementById('programInstitutionId');

      institutionSelect.value = '';
      expect(institutionSelect.validity.valid).toBe(false);

      institutionSelect.value = 'inst-1';
      expect(institutionSelect.validity.valid).toBe(true);
    });

    test('should have active checkbox checked by default', () => {
      const activeCheckbox = document.getElementById('programActive');
      expect(activeCheckbox.checked).toBe(true);
    });
  });

  describe('Form Submission - API Call', () => {
    test('should POST program data to /api/programs on form submit', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          program_id: 'prog-123',
          message: 'Program created'
        })
      });

      const form = document.getElementById('createProgramForm');
      document.getElementById('programName').value = 'Computer Science';
      document.getElementById('programShortName').value = 'CS';
      document.getElementById('programInstitutionId').value = 'inst-1';
      document.getElementById('programActive').checked = true;

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/programs',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'X-CSRFToken': 'test-csrf-token'
          }),
          body: expect.stringContaining('Computer Science')
        })
      );
    });

    test('should include all program fields in POST body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, program_id: 'prog-123' })
      });

      const form = document.getElementById('createProgramForm');
      document.getElementById('programName').value = 'Computer Science';
      document.getElementById('programShortName').value = 'CS';
      document.getElementById('programInstitutionId').value = 'inst-1';
      document.getElementById('programActive').checked = false;

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body).toMatchObject({
        name: 'Computer Science',
        institution_id: 'inst-1',
        active: false
      });
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

      const form = document.getElementById('createProgramForm');
      document.getElementById('programName').value = 'Test';
      document.getElementById('programShortName').value = 'TEST';
      document.getElementById('programInstitutionId').value = 'inst-1';

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
          program_id: 'prog-123',
          message: 'Program created'
        })
      });

      const form = document.getElementById('createProgramForm');
      const nameInput = document.getElementById('programName');

      nameInput.value = 'Computer Science';
      document.getElementById('programInstitutionId').value = 'inst-1';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      // Modal should be closed
      expect(bootstrap.Modal.getInstance).toHaveBeenCalled();

      // Form should be reset
      expect(nameInput.value).toBe('');
    });

    test('should display error message on API failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ error: 'Program name already exists' })
      });

      global.alert = jest.fn();

      const form = document.getElementById('createProgramForm');
      document.getElementById('programName').value = 'Existing';
      document.getElementById('programShortName').value = 'EXIST';
      document.getElementById('programInstitutionId').value = 'inst-1';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(global.alert).toHaveBeenCalledWith(
        expect.stringContaining('Program name already exists')
      );
    });

    test('should handle network errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      global.alert = jest.fn();

      const form = document.getElementById('createProgramForm');
      document.getElementById('programName').value = 'Test';
      document.getElementById('programShortName').value = 'TEST';
      document.getElementById('programInstitutionId').value = 'inst-1';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(global.alert).toHaveBeenCalledWith(
        expect.stringContaining('Failed to create program')
      );
      expect(consoleErrorSpy).toHaveBeenCalled();
    });
  });

  describe('CSRF Token Handling', () => {
    test('should include CSRF token in headers', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, program_id: 'prog-123' })
      });

      const form = document.getElementById('createProgramForm');
      document.getElementById('programName').value = 'Test';
      document.getElementById('programShortName').value = 'TEST';
      document.getElementById('programInstitutionId').value = 'inst-1';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      expect(callArgs[1].headers['X-CSRFToken']).toBe('test-csrf-token');
    });
  });
});

describe('Program Management - Edit Program Modal', () => {
  let mockFetch;

  beforeEach(() => {
    document.body.innerHTML = `
      <form id="editProgramForm">
        <input type="hidden" id="editProgramId" />
        <input type="text" id="editProgramName" required />
        <div class="form-check">
          <input type="checkbox" id="editProgramActive" name="active" />
          <label for="editProgramActive">Active</label>
        </div>
        <button type="submit">
          <span class="btn-text">Update</span>
          <span class="btn-spinner d-none">Updating...</span>
        </button>
      </form>
      <div class="modal" id="editProgramModal"></div>
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

  test('openEditProgramModal should populate form and show modal', () => {
    const mockModal = { show: jest.fn() };
    global.bootstrap.Modal = jest.fn(() => mockModal);

    window.openEditProgramModal('prog-123', {
      name: 'Computer Science',
      active: true
    });

    expect(document.getElementById('editProgramId').value).toBe('prog-123');
    expect(document.getElementById('editProgramName').value).toBe('Computer Science');
    expect(document.getElementById('editProgramActive').checked).toBe(true);
    expect(mockModal.show).toHaveBeenCalled();
  });

  test('should PUT updated program data to /api/programs/<id>', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, message: 'Program updated' })
    });

    const form = document.getElementById('editProgramForm');
    document.getElementById('editProgramId').value = 'prog-123';
    document.getElementById('editProgramName').value = 'Updated Program';
    document.getElementById('editProgramActive').checked = false;

    const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
    form.dispatchEvent(submitEvent);

    await new Promise(resolve => setTimeout(resolve, 100));

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/programs/prog-123',
      expect.objectContaining({
        method: 'PUT',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'X-CSRFToken': 'test-csrf-token'
        }),
        body: expect.stringContaining('Updated Program')
      })
    );

    const callArgs = mockFetch.mock.calls[0];
    const body = JSON.parse(callArgs[1].body);
    expect(body.active).toBe(false);
  });
});

describe('Program Management - Delete Program', () => {
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

  test('should DELETE program with confirmation', async () => {
    confirmSpy.mockReturnValue(true);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true })
    });

    await window.deleteProgram('prog-123', 'Computer Science');

    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringContaining('Computer Science')
    );
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/programs/prog-123',
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

    await window.deleteProgram('prog-123', 'Computer Science');

    expect(mockFetch).not.toHaveBeenCalled();
    expect(alertSpy).not.toHaveBeenCalled();
  });

  test('should handle API errors gracefully', async () => {
    confirmSpy.mockReturnValue(true);
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: 'Program has active courses' })
    });

    await window.deleteProgram('prog-123', 'Computer Science');

    expect(alertSpy).toHaveBeenCalledWith(
      expect.stringContaining('Program has active courses')
    );
  });

  test('should handle network errors gracefully', async () => {
    confirmSpy.mockReturnValue(true);
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

    await window.deleteProgram('prog-123', 'Computer Science');

    expect(alertSpy).toHaveBeenCalledWith(
      expect.stringContaining('Failed to delete program')
    );
    expect(consoleErrorSpy).toHaveBeenCalled();

    consoleErrorSpy.mockRestore();
  });
});

