/**
 * Unit Tests for Term Management UI
 *
 * Tests modal behavior, form validation, and API interactions for:
 * - Create Term modal
 * - Edit Term modal
 * - Delete Term confirmation
 *
 * TDD Approach: Tests written before implementation
 */

// Load the implementation
require('../../../static/termManagement.js');

describe('Term Management - Create Term Modal', () => {
  let mockFetch;
  let consoleErrorSpy;
  let realLoadTerms;
  let realLoadTermsImpl;

  beforeAll(() => {
    // termManagement.js is required at module load time; preserve real implementation once.
    realLoadTermsImpl = global.loadTerms;
  });

  beforeEach(() => {
    // Set up DOM
    document.body.innerHTML = `
      <form id="createTermForm">
        <input type="text" id="termName" name="name" required placeholder="Fall 2024" />
        <input type="date" id="termStartDate" name="start_date" required />
        <input type="date" id="termEndDate" name="end_date" required />
        <input type="date" id="termAssessmentDueDate" name="assessment_due_date" required />
        <div class="form-check">
          <input type="checkbox" id="termActive" name="active" checked />
          <label for="termActive">Active</label>
        </div>
        <button type="submit" id="createTermBtn">
          <span class="btn-text">Create Term</span>
          <span class="btn-spinner d-none">Creating...</span>
        </button>
      </form>
      <div class="modal" id="createTermModal"></div>
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

    // Restore real implementation (prior tests may have replaced it with a mock)
    global.loadTerms = realLoadTermsImpl;

    // Preserve real implementations before tests overwrite globals for assertions
    realLoadTerms = global.loadTerms;
    global.loadTerms = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Form Validation', () => {
    test('should require term name', () => {
      const nameInput = document.getElementById('termName');

      nameInput.value = '';
      expect(nameInput.validity.valid).toBe(false);

      nameInput.value = 'Fall 2024';
      expect(nameInput.validity.valid).toBe(true);
    });

    test('should require start date', () => {
      const startDateInput = document.getElementById('termStartDate');

      startDateInput.value = '';
      expect(startDateInput.validity.valid).toBe(false);

      startDateInput.value = '2024-08-01';
      expect(startDateInput.validity.valid).toBe(true);
    });

    test('should require end date', () => {
      const endDateInput = document.getElementById('termEndDate');

      endDateInput.value = '';
      expect(endDateInput.validity.valid).toBe(false);

      endDateInput.value = '2024-12-15';
      expect(endDateInput.validity.valid).toBe(true);
    });

    test('should require assessment due date', () => {
      const assessmentInput = document.getElementById('termAssessmentDueDate');

      assessmentInput.value = '';
      expect(assessmentInput.validity.valid).toBe(false);

      assessmentInput.value = '2024-12-20';
      expect(assessmentInput.validity.valid).toBe(true);
    });

    test('should have active checkbox checked by default', () => {
      const activeCheckbox = document.getElementById('termActive');
      expect(activeCheckbox.checked).toBe(true);
    });
  });

  describe('Form Submission - API Call', () => {
    test('should allow submit when start/end dates are missing (validation deferred to required fields)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, term_id: 'term-123' })
      });

      const form = document.getElementById('createTermForm');
      document.getElementById('termName').value = 'Fall 2024';
      document.getElementById('termStartDate').value = ''; // missing
      document.getElementById('termEndDate').value = ''; // missing
      document.getElementById('termAssessmentDueDate').value = ''; // missing

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));
      expect(mockFetch).toHaveBeenCalled();
    });

    test('should allow submit when due date is empty (no dueDate warnings)', async () => {
      global.confirm = jest.fn(() => true);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, term_id: 'term-123' })
      });

      const form = document.getElementById('createTermForm');
      document.getElementById('termName').value = 'Fall 2024';
      document.getElementById('termStartDate').value = '2024-08-01';
      document.getElementById('termEndDate').value = '2024-12-15';
      document.getElementById('termAssessmentDueDate').value = ''; // no due date

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));
      expect(mockFetch).toHaveBeenCalled();
    });

    test('should allow submit when term duration is very short and user confirms', async () => {
      global.confirm = jest.fn(() => true);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, term_id: 'term-123' })
      });

      const form = document.getElementById('createTermForm');
      document.getElementById('termName').value = 'Mini Term';
      document.getElementById('termStartDate').value = '2024-08-01';
      document.getElementById('termEndDate').value = '2024-08-05'; // 4 days
      document.getElementById('termAssessmentDueDate').value = '2024-08-06';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));
      expect(global.confirm).toHaveBeenCalled();
      expect(mockFetch).toHaveBeenCalled();
    });

    test('should allow submit when term duration is very long and user confirms', async () => {
      global.confirm = jest.fn(() => true);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, term_id: 'term-123' })
      });

      const form = document.getElementById('createTermForm');
      document.getElementById('termName').value = 'Very Long Term';
      document.getElementById('termStartDate').value = '2024-01-01';
      document.getElementById('termEndDate').value = '2025-06-01'; // > 365 days
      document.getElementById('termAssessmentDueDate').value = '2025-06-10';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));
      expect(global.confirm).toHaveBeenCalled();
      expect(mockFetch).toHaveBeenCalled();
    });

    test('should allow submit when due date is far after end date and user confirms', async () => {
      global.confirm = jest.fn(() => true);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, term_id: 'term-123' })
      });

      const form = document.getElementById('createTermForm');
      document.getElementById('termName').value = 'Fall 2024';
      document.getElementById('termStartDate').value = '2024-08-01';
      document.getElementById('termEndDate').value = '2024-12-15';
      document.getElementById('termAssessmentDueDate').value = '2025-02-20'; // > 30 days after

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));
      expect(global.confirm).toHaveBeenCalled();
      expect(mockFetch).toHaveBeenCalled();
    });

    test('should block submit when end date is not after start date', async () => {
      global.alert = jest.fn();
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) });

      const form = document.getElementById('createTermForm');
      document.getElementById('termName').value = 'Fall 2024';
      document.getElementById('termStartDate').value = '2024-08-01';
      document.getElementById('termEndDate').value = '2024-08-01'; // invalid
      document.getElementById('termAssessmentDueDate').value = '2024-12-20';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 25));

      expect(global.alert).toHaveBeenCalledWith('End date must be after start date.');
      expect(mockFetch).not.toHaveBeenCalled();
    });

    test('should block submit when assessment due date is not after start date', async () => {
      global.alert = jest.fn();
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) });

      const form = document.getElementById('createTermForm');
      document.getElementById('termName').value = 'Fall 2024';
      document.getElementById('termStartDate').value = '2024-08-01';
      document.getElementById('termEndDate').value = '2024-12-15';
      document.getElementById('termAssessmentDueDate').value = '2024-08-01'; // invalid

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 25));

      expect(global.alert).toHaveBeenCalledWith(
        'Assessment due date must be after start date.'
      );
      expect(mockFetch).not.toHaveBeenCalled();
    });

    test('should block submit when term duration is very short and user cancels confirmation', async () => {
      global.confirm = jest.fn(() => false);
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) });

      const form = document.getElementById('createTermForm');
      document.getElementById('termName').value = 'Mini Term';
      document.getElementById('termStartDate').value = '2024-08-01';
      document.getElementById('termEndDate').value = '2024-08-05'; // 4 days
      document.getElementById('termAssessmentDueDate').value = '2024-08-06';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 25));

      expect(global.confirm).toHaveBeenCalled();
      expect(mockFetch).not.toHaveBeenCalled();
    });

    test('should block submit when term duration is very long and user cancels confirmation', async () => {
      global.confirm = jest.fn(() => false);
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) });

      const form = document.getElementById('createTermForm');
      document.getElementById('termName').value = 'Very Long Term';
      document.getElementById('termStartDate').value = '2024-01-01';
      document.getElementById('termEndDate').value = '2025-06-01'; // > 365 days
      document.getElementById('termAssessmentDueDate').value = '2025-06-10';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 25));

      expect(global.confirm).toHaveBeenCalled();
      expect(mockFetch).not.toHaveBeenCalled();
    });

    test('should block submit when assessment due date is far after end date and user cancels confirmation', async () => {
      global.confirm = jest.fn(() => false);
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) });

      const form = document.getElementById('createTermForm');
      document.getElementById('termName').value = 'Fall 2024';
      document.getElementById('termStartDate').value = '2024-08-01';
      document.getElementById('termEndDate').value = '2024-12-15';
      document.getElementById('termAssessmentDueDate').value = '2025-02-20'; // > 30 days after

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 25));

      expect(global.confirm).toHaveBeenCalled();
      expect(mockFetch).not.toHaveBeenCalled();
    });

    test('should POST term data to /api/terms on form submit', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          term_id: 'term-123',
          message: 'Term created'
        })
      });

      const form = document.getElementById('createTermForm');
      document.getElementById('termName').value = 'Fall 2024';
      document.getElementById('termStartDate').value = '2024-08-01';
      document.getElementById('termEndDate').value = '2024-12-15';
      document.getElementById('termAssessmentDueDate').value = '2024-12-20';
      document.getElementById('termActive').checked = true;

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/terms',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'X-CSRFToken': 'test-csrf-token'
          }),
          body: expect.stringContaining('Fall 2024')
        })
      );
    });

    test('should include all term fields in POST body', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, term_id: 'term-123' })
      });

      const form = document.getElementById('createTermForm');
      document.getElementById('termName').value = 'Spring 2025';
      document.getElementById('termStartDate').value = '2025-01-10';
      document.getElementById('termEndDate').value = '2025-05-20';
      document.getElementById('termAssessmentDueDate').value = '2025-05-25';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body).toMatchObject({
        name: 'Spring 2025',
        start_date: '2025-01-10',
        end_date: '2025-05-20',
        assessment_due_date: '2025-05-25'
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

      const form = document.getElementById('createTermForm');
      document.getElementById('termName').value = 'Fall 2024';
      document.getElementById('termStartDate').value = '2024-08-01';
      document.getElementById('termEndDate').value = '2024-12-15';
      document.getElementById('termAssessmentDueDate').value = '2024-12-20';

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
          term_id: 'term-123',
          message: 'Term created'
        })
      });

      const form = document.getElementById('createTermForm');
      const nameInput = document.getElementById('termName');

      nameInput.value = 'Fall 2024';
      document.getElementById('termStartDate').value = '2024-08-01';
      document.getElementById('termEndDate').value = '2024-12-15';
      document.getElementById('termAssessmentDueDate').value = '2024-12-20';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      // Modal should be closed
      expect(bootstrap.Modal.getInstance).toHaveBeenCalled();

      // Form should be reset
      expect(nameInput.value).toBe('');
      expect(global.loadTerms).toHaveBeenCalled();
    });

    test('should display error message on API failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ error: 'Term name already exists' })
      });

      global.alert = jest.fn();

      const form = document.getElementById('createTermForm');
      document.getElementById('termName').value = 'Fall 2024';
      document.getElementById('termStartDate').value = '2024-08-01';
      document.getElementById('termEndDate').value = '2024-12-15';
      document.getElementById('termAssessmentDueDate').value = '2024-12-20';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(global.alert).toHaveBeenCalledWith(
        expect.stringContaining('Term name already exists')
      );
    });

    test('should handle network errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      global.alert = jest.fn();

      const form = document.getElementById('createTermForm');
      document.getElementById('termName').value = 'Fall 2024';
      document.getElementById('termStartDate').value = '2024-08-01';
      document.getElementById('termEndDate').value = '2024-12-15';
      document.getElementById('termAssessmentDueDate').value = '2024-12-20';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(global.alert).toHaveBeenCalledWith(
        expect.stringContaining('Failed to create term')
      );
      expect(consoleErrorSpy).toHaveBeenCalled();
    });
  });

  describe('CSRF Token Handling', () => {
    test('should include CSRF token in headers', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, term_id: 'term-123' })
      });

      const form = document.getElementById('createTermForm');
      document.getElementById('termName').value = 'Fall 2024';
      document.getElementById('termStartDate').value = '2024-08-01';
      document.getElementById('termEndDate').value = '2024-12-15';
      document.getElementById('termAssessmentDueDate').value = '2024-12-20';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      expect(callArgs[1].headers['X-CSRFToken']).toBe('test-csrf-token');
    });
  });

  describe('Load Terms and Helpers', () => {
    beforeEach(() => {
      // Container used by loadTerms()
      document.body.innerHTML += '<div id="termsTableContainer"></div>';
    });

    test('loadTerms should render empty state when no terms', async () => {
      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, terms: [] })
      });

      await realLoadTerms();
      expect(document.getElementById('termsTableContainer').innerHTML).toContain('No terms found');
    });

    test('loadTerms should render table when terms exist', async () => {
      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          terms: [
            {
              term_id: 't1',
              name: 'Fall 2024',
              start_date: '2024-08-01',
              end_date: '2024-12-15',
              active: true,
              offerings_count: 2
            }
          ]
        })
      });

      await realLoadTerms();
      const html = document.getElementById('termsTableContainer').innerHTML;
      expect(html).toContain('Fall 2024');
      expect(html).toContain('Offerings');
      expect(html).toContain('Edit');
    });

    test('loadTerms should render error state when fetch fails', async () => {
      global.fetch = jest.fn().mockResolvedValueOnce({ ok: false });
      await realLoadTerms();
      expect(document.getElementById('termsTableContainer').innerHTML).toContain('Error loading terms');
    });

    test('openCreateTermModal should open modal via bootstrap.Modal', () => {
      const mockModal = { show: jest.fn() };
      global.bootstrap.Modal = jest.fn(() => mockModal);
      global.openCreateTermModal();
      expect(global.bootstrap.Modal).toHaveBeenCalled();
      expect(mockModal.show).toHaveBeenCalled();
    });
  });
});

describe('Term Management - Edit Term Modal', () => {
  let mockFetch;

  beforeEach(() => {
    document.body.innerHTML = `
      <form id="editTermForm">
        <input type="hidden" id="editTermId" />
        <input type="text" id="editTermName" required />
        <input type="date" id="editTermStartDate" required />
        <input type="date" id="editTermEndDate" required />
        <input type="date" id="editTermAssessmentDueDate" required />
        <div class="form-check">
          <input type="checkbox" id="editTermActive" name="active" />
          <label for="editTermActive">Active</label>
        </div>
        <button type="submit">
          <span class="btn-text">Update</span>
          <span class="btn-spinner d-none">Updating...</span>
        </button>
      </form>
      <div class="modal" id="editTermModal"></div>
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

    global.loadTerms = jest.fn();

    // Trigger DOMContentLoaded to initialize event listeners
    document.dispatchEvent(new Event('DOMContentLoaded'));
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('openEditTermModal should populate form and show modal', () => {
    const mockModal = { show: jest.fn() };
    global.bootstrap.Modal = jest.fn(() => mockModal);

    window.openEditTermModal('term-123', {
      name: 'Fall 2024',
      start_date: '2024-08-01',
      end_date: '2024-12-15',
      assessment_due_date: '2024-12-20',
      active: true
    });

    expect(document.getElementById('editTermId').value).toBe('term-123');
    expect(document.getElementById('editTermName').value).toBe('Fall 2024');
    expect(document.getElementById('editTermStartDate').value).toBe('2024-08-01');
    expect(document.getElementById('editTermEndDate').value).toBe('2024-12-15');
    expect(document.getElementById('editTermAssessmentDueDate').value).toBe('2024-12-20');
    expect(mockModal.show).toHaveBeenCalled();
  });

  test('should PUT updated term data to /api/terms/<id>', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, message: 'Term updated' })
    });

    const form = document.getElementById('editTermForm');
    document.getElementById('editTermId').value = 'term-123';
    document.getElementById('editTermName').value = 'Spring 2025';
    document.getElementById('editTermStartDate').value = '2025-01-10';
    document.getElementById('editTermEndDate').value = '2025-05-20';
    document.getElementById('editTermAssessmentDueDate').value = '2025-05-25';

    const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
    form.dispatchEvent(submitEvent);

    await new Promise(resolve => setTimeout(resolve, 100));

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/terms/term-123',
      expect.objectContaining({
        method: 'PUT',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'X-CSRFToken': 'test-csrf-token'
        }),
        body: expect.stringContaining('Spring 2025')
      })
    );

    const callArgs = mockFetch.mock.calls[0];
    const body = JSON.parse(callArgs[1].body);
    expect(body.end_date).toBe('2025-05-20');
    expect(body.name).toBe('Spring 2025');
    expect(global.loadTerms).toHaveBeenCalled();
  });
});

describe('Term Management - Delete Term', () => {
  let mockFetch;
  let confirmSpy;
  let alertSpy;

  beforeEach(() => {
    document.body.innerHTML = '<meta name="csrf-token" content="test-csrf-token">';
    mockFetch = jest.fn();
    global.fetch = mockFetch;
    confirmSpy = jest.spyOn(window, 'confirm');
    alertSpy = jest.spyOn(window, 'alert').mockImplementation();
    global.loadTerms = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('should DELETE term with confirmation', async () => {
    confirmSpy.mockReturnValue(true);
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true })
    });

    await window.deleteTerm('term-123', 'Fall 2024');

    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringContaining('Fall 2024')
    );
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/terms/term-123',
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
    expect(global.loadTerms).toHaveBeenCalled();
  });

  test('should not delete if user cancels confirmation', async () => {
    confirmSpy.mockReturnValue(false);

    await window.deleteTerm('term-123', 'Fall 2024');

    expect(mockFetch).not.toHaveBeenCalled();
    expect(alertSpy).not.toHaveBeenCalled();
  });

  test('should handle API errors gracefully', async () => {
    confirmSpy.mockReturnValue(true);
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ error: 'Term has active offerings' })
    });

    await window.deleteTerm('term-123', 'Fall 2024');

    expect(alertSpy).toHaveBeenCalledWith(
      expect.stringContaining('Term has active offerings')
    );
  });

  test('should handle network errors during delete', async () => {
    confirmSpy.mockReturnValue(true);
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    await window.deleteTerm('term-123', 'Fall 2024');

    expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining('try again'));
  });
});

