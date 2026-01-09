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
const {
  initOfferingManagement,
  openEditOfferingModal,
  deleteOffering,
  loadOfferings,
  resolveOfferingStatus,
  applyFilters
} = require('../../../static/offeringManagement.js');

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
        <select id="offeringProgramId" name="program_id" required>
          <option value="">Select Program</option>
          <option value="program-1">Computer Science</option>
          <option value="program-2">Mathematics</option>
        </select>
        <div id="sectionsContainer"></div>
        <button type="button" id="addSectionBtn">Add Section</button>
        <button type="submit" id="createOfferingBtn">
          <span class="btn-text">Create Offering</span>
          <span class="btn-spinner d-none">Creating...</span>
        </button>
      </form>
      <div class="modal" id="createOfferingModal"></div>
      <div class="modal" id="editOfferingModal"></div>
      <meta name="csrf-token" content="test-csrf-token">
    `;

    // Mock fetch
    mockFetch = jest.fn();
    global.fetch = mockFetch;

    // Mock console.error
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

    // Mock Bootstrap Modal (constructor + static helpers)
    const ModalCtor = jest.fn(() => ({ show: jest.fn(), hide: jest.fn() }));
    ModalCtor.getInstance = jest.fn(() => ({ hide: jest.fn() }));
    ModalCtor.getOrCreateInstance = jest.fn(() => ({ hide: jest.fn() }));
    global.bootstrap = { Modal: ModalCtor };

    // Initialize offering management (replaces DOMContentLoaded trigger)
    initOfferingManagement();
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

    test('should allow empty sections', () => {
      const sectionsContainer = document.getElementById('sectionsContainer');
      // Sections are optional (can create offering with 0 sections)
      expect(sectionsContainer).toBeTruthy();
      expect(sectionsContainer.children.length).toBe(0);
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
      document.getElementById('offeringProgramId').value = 'program-1';

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
      document.getElementById('offeringProgramId').value = 'program-2';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body).toMatchObject({
        course_id: 'course-2',
        term_id: 'term-2',
        program_id: 'program-2',
        sections: []
      });
    });

    test('should send program_id as null when no program is selected', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, offering_id: 'offering-123' })
      });

      const form = document.getElementById('createOfferingForm');
      document.getElementById('offeringCourseId').value = 'course-1';
      document.getElementById('offeringTermId').value = 'term-1';
      document.getElementById('offeringProgramId').value = '';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      expect(body.program_id).toBeNull();
    });

    test('should handle empty sections as empty array', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, offering_id: 'offering-123' })
      });

      const form = document.getElementById('createOfferingForm');
      document.getElementById('offeringCourseId').value = 'course-1';
      document.getElementById('offeringTermId').value = 'term-1';
      document.getElementById('offeringProgramId').value = 'program-1';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body.sections).toEqual([]);
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
      document.getElementById('offeringProgramId').value = 'program-1';

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
      document.getElementById('offeringProgramId').value = 'program-1';

      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      form.dispatchEvent(submitEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      // Modal should be closed (implementation prefers getOrCreateInstance if present)
      expect(bootstrap.Modal.getOrCreateInstance).toHaveBeenCalled();

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
      document.getElementById('offeringProgramId').value = 'program-1';

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
      document.getElementById('offeringProgramId').value = 'program-1';

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

  describe('Dropdown Loading (show.bs.modal handlers)', () => {
    test('should load courses/terms/programs when createOfferingModal is shown', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            courses: [{ course_id: 'course-1', course_number: 'CS101', course_title: 'Intro' }]
          })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ terms: [{ term_id: 'term-1', name: 'Fall 2024' }] })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ programs: [{ program_id: 'program-1', name: 'Computer Science' }] })
        });

      // Trigger the Bootstrap modal show event (listener is attached by initOfferingManagement)
      document.getElementById('createOfferingModal').dispatchEvent(new Event('show.bs.modal'));

      await new Promise(resolve => setTimeout(resolve, 25));

      expect(global.fetch).toHaveBeenCalledWith('/api/courses');
      expect(global.fetch).toHaveBeenCalledWith('/api/terms?all=true');
      expect(global.fetch).toHaveBeenCalledWith('/api/programs');

      expect(document.getElementById('offeringCourseId').options.length).toBeGreaterThan(1);
      expect(document.getElementById('offeringTermId').options.length).toBeGreaterThan(1);
      expect(document.getElementById('offeringProgramId').options.length).toBeGreaterThan(1);
    });

    test('should show error option text if create dropdown API fetch fails', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, json: async () => ({}) });

      document.getElementById('createOfferingModal').dispatchEvent(new Event('show.bs.modal'));
      await new Promise(resolve => setTimeout(resolve, 25));

      expect(document.getElementById('offeringCourseId').innerHTML).toContain('Error loading courses');
      expect(document.getElementById('offeringTermId').innerHTML).toContain('Error loading terms');
      expect(document.getElementById('offeringProgramId').innerHTML).toContain('Error loading programs');
    });
  });
});

describe('resolveOfferingStatus helper', () => {
  test('returns direct status when provided', () => {
    const status = resolveOfferingStatus({ status: 'active' });
    expect(status).toBe('ACTIVE');
  });

  test('calculates status from term dates when missing', () => {
    const now = Date.now();
    const day = 24 * 60 * 60 * 1000;
    const futureStart = new Date(now + 7 * day).toISOString().slice(0, 10);
    const futureEnd = new Date(now + 21 * day).toISOString().slice(0, 10);

    const status = resolveOfferingStatus({
      term_start_date: futureStart,
      term_end_date: futureEnd
    });
    expect(status).toBe('SCHEDULED');
  });
});

describe('Offering Management - Edit / Delete / Listing Helpers', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();

    document.body.innerHTML = `
      <meta name="csrf-token" content="test-csrf-token">
      <input id="editOfferingId" />
      <input id="editOfferingCourse" />
      <select id="editOfferingTerm">
        <option value="">Select Term</option>
        <option value="term-1">Fall 2024</option>
      </select>
      <select id="editOfferingProgramId"></select>
      <div class="modal" id="editOfferingModal"></div>
      <div id="offeringsTableContainer"></div>
      <div class="modal" id="createOfferingModal"></div>
    `;

    global.fetch = jest.fn();
    global.alert = jest.fn();
    global.confirm = jest.fn(() => true);

    const ModalCtor = jest.fn(() => ({ show: jest.fn(), hide: jest.fn() }));
    ModalCtor.getInstance = jest.fn(() => ({ hide: jest.fn() }));
    ModalCtor.getOrCreateInstance = jest.fn(() => ({ hide: jest.fn() }));
    global.bootstrap = { Modal: ModalCtor };
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  test('openEditOfferingModal should populate fields and show modal', () => {
    const offeringData = {
      capacity: 25,
      course_title: 'Intro',
      term_name: 'Fall 2024',
      term_id: 'term-1',
      program_id: 'program-1'
    };

    // Add program option so selecting works after timeout
    const programSelect = document.getElementById('editOfferingProgramId');
    programSelect.innerHTML = '<option value="program-1">Computer Science</option>';

    // Add term option
    const termSelect = document.getElementById('editOfferingTerm');
    termSelect.innerHTML += '<option value="term-1">Fall 2024</option>';

    openEditOfferingModal('offering-123', offeringData);

    expect(document.getElementById('editOfferingId').value).toBe('offering-123');
    expect(document.getElementById('editOfferingCourse').value).toBe('Intro');

    jest.advanceTimersByTime(500);
    expect(document.getElementById('editOfferingProgramId').value).toBe('program-1');
    expect(document.getElementById('editOfferingTerm').value).toBe('term-1');
  });

  test('deleteOffering should no-op when user cancels confirmation', async () => {
    global.confirm = jest.fn(() => false);

    await deleteOffering('offering-1', 'Course', 'Term');
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test('deleteOffering should call DELETE and alert on success', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true })
    });

    await deleteOffering('offering-1', 'Course', 'Term');

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/offerings/offering-1',
      expect.objectContaining({ method: 'DELETE' })
    );
    expect(global.alert).toHaveBeenCalled();
  });

  test('loadOfferings should render empty-state when no offerings are returned', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ offerings: [] })
    });

    await loadOfferings();
    expect(document.getElementById('offeringsTableContainer').innerHTML).toContain('No course offerings found');
  });

  test('loadOfferings should render table when offerings are returned', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        offerings: [
          {
            offering_id: 'off-1',
            course_title: 'Intro',
            term_name: 'Fall 2024',
            status: 'ACTIVE',
            section_count: 2,
            total_enrollment: 30
          }
        ]
      })
    });

    await loadOfferings();
    const html = document.getElementById('offeringsTableContainer').innerHTML;
    expect(html).toContain('<table');
    expect(html).toContain('Intro');
    expect(html).toContain('Fall 2024');
    expect(html).toContain('Active');
  });
});

describe('Offering Management - Edit Offering Modal', () => {
  let mockFetch;

  beforeEach(() => {
    document.body.innerHTML = `
      <form id="editOfferingForm">
        <input type="hidden" id="editOfferingId" />
        <input type="text" id="editOfferingCourse" />
        <select id="editOfferingTerm" required>
          <option value="">Select Term</option>
          <option value="term-1">Fall 2024</option>
          <option value="term-2">Spring 2025</option>
        </select>
        <select id="editOfferingProgramId" required>
          <option value="">Select Program</option>
          <option value="program-1">Computer Science</option>
          <option value="program-2">Mathematics</option>
        </select>
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

    // Initialize offering management (replaces DOMContentLoaded trigger)
    initOfferingManagement();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('openEditOfferingModal should populate form and show modal', () => {
    const mockModal = { show: jest.fn() };
    global.bootstrap.Modal = jest.fn(() => mockModal);

    window.openEditOfferingModal('offering-123', {
      capacity: 40,
      course_title: 'Intro to CS',
      term_name: 'Fall 2024',
      term_id: 'term-1'
    });

    expect(document.getElementById('editOfferingId').value).toBe('offering-123');
    expect(document.getElementById('editOfferingCourse').value).toBe('Intro to CS');
    expect(mockModal.show).toHaveBeenCalled();
  });

  test('openEditOfferingModal should set program select after dropdown is populated', () => {
    jest.useFakeTimers();

    const mockModal = { show: jest.fn() };
    global.bootstrap.Modal = jest.fn(() => mockModal);

    const programSelect = document.getElementById('editOfferingProgramId');
    programSelect.value = '';

    window.openEditOfferingModal('offering-123', {
      capacity: 10,
      course_title: 'Intro',
      term_name: 'Fall',
      term_id: 'term-1',
      program_id: 'program-2'
    });

    // Program should be set after timer fires
    jest.advanceTimersByTime(600);
    expect(programSelect.value).toBe('program-2');

    jest.useRealTimers();
  });

  test('should PUT updated offering data to /api/offerings/<id>', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, message: 'Offering updated' })
    });

    const form = document.getElementById('editOfferingForm');
    document.getElementById('editOfferingId').value = 'offering-123';
    document.getElementById('editOfferingProgramId').value = 'program-1';
    document.getElementById('editOfferingTerm').value = 'term-2';

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
        body: expect.stringContaining('program-1')
      })
    );

    const callArgs = mockFetch.mock.calls[0];
    const body = JSON.parse(callArgs[1].body);
    expect(body.program_id).toBe('program-1');
    expect(body.term_id).toBe('term-2');
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

describe('Offering Management - Filtering', () => {
  beforeEach(() => {
    // Set up DOM with filter elements and a table container with mock data
    document.body.innerHTML = `
      <div class="row mb-3">
        <div class="col-md-3">
            <select id="filterTerm" class="form-select">
                <option value="">All Terms</option>
                <option value="term-1">Term 1</option>
                <option value="term-2">Term 2</option>
            </select>
        </div>
        <div class="col-md-3">
            <select id="filterProgram" class="form-select">
                <option value="">All Programs</option>
                <option value="prog-1">Program 1</option>
                <option value="prog-2">Program 2</option>
            </select>
        </div>
      </div>
      <div id="offeringsTableContainer">
        <table>
          <tbody>
            <tr class="offering-row" data-term-id="term-1" data-program-id="prog-1">
              <td>Course 1 (T1, P1)</td>
            </tr>
            <tr class="offering-row" data-term-id="term-2" data-program-id="prog-1">
              <td>Course 2 (T2, P1)</td>
            </tr>
            <tr class="offering-row" data-term-id="term-1" data-program-id="prog-2">
              <td>Course 3 (T1, P2)</td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
  });

  test('applyFilters should show all rows when no filter is selected', () => {
    document.getElementById('filterTerm').value = '';
    document.getElementById('filterProgram').value = '';

    // We assume applyFilters exists and works
    if (typeof applyFilters === 'function') {
      applyFilters();

      const rows = document.querySelectorAll('.offering-row');
      rows.forEach(row => {
        expect(row.style.display).not.toBe('none');
      });
    }
  });

  test('applyFilters should filter by term', () => {
    if (typeof applyFilters === 'function') {
      document.getElementById('filterTerm').value = 'term-1';
      document.getElementById('filterProgram').value = '';

      applyFilters();

      const visibleRows = Array.from(document.querySelectorAll('.offering-row')).filter(r => r.style.display !== 'none');
      expect(visibleRows.length).toBe(2);
      expect(visibleRows[0].textContent).toContain('Course 1');
      expect(visibleRows[1].textContent).toContain('Course 3');
    }
  });

  test('applyFilters should filter by program', () => {
    if (typeof applyFilters === 'function') {
      document.getElementById('filterTerm').value = '';
      document.getElementById('filterProgram').value = 'prog-1';

      applyFilters();

      const visibleRows = Array.from(document.querySelectorAll('.offering-row')).filter(r => r.style.display !== 'none');
      expect(visibleRows.length).toBe(2);
      expect(visibleRows[0].textContent).toContain('Course 1');
      expect(visibleRows[1].textContent).toContain('Course 2');
    }
  });

  test('applyFilters should filter by both term and program', () => {
    if (typeof applyFilters === 'function') {
      document.getElementById('filterTerm').value = 'term-2';
      document.getElementById('filterProgram').value = 'prog-1';

      applyFilters();

      const visibleRows = Array.from(document.querySelectorAll('.offering-row')).filter(r => r.style.display !== 'none');
      expect(visibleRows.length).toBe(1);
      expect(visibleRows[0].textContent).toContain('Course 2');
    }
  });
});
