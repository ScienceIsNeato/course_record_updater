const { setBody, flushPromises } = require('../helpers/dom');

let consoleLogSpy;
let consoleErrorSpy;
let originalReload;

describe('script.js interactions', () => {
  beforeEach(() => {
    jest.resetModules();
    window.alert = jest.fn();
    global.confirm.mockReturnValue(true);
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, count: 0 })
    });
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    originalReload = window.location.reload;
  });

  afterEach(() => {
    consoleLogSpy.mockRestore();
    consoleErrorSpy.mockRestore();
    window.location.reload = originalReload;
  });

const setupTableDom = () => {
  setBody(`
      <table class="table">
        <tbody>
          <tr data-course-id="course-1">
            <td>ENGR101</td>
            <td>Intro Engineering</td>
            <td>Alex Smith</td>
            <td>FA2024</td>
            <td>10</td>
            <td>5</td>
            <td>3</td>
            <td>1</td>
            <td>1</td>
            <td>0</td>
            <td>
              <button class="btn btn-sm btn-warning edit-btn">Edit</button>
              <button class="btn btn-sm btn-danger delete-btn">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    `);
  };

  const setupImportDom = () => {
    setBody(`
      <form id="excelImportForm">
        <input type="file" id="excel_file" />
        <select id="import_adapter">
          <option value="adapter_a">Adapter A</option>
        </select>
        <input type="checkbox" id="dry_run" />
        <input type="checkbox" id="delete_existing_db" />
        <div id="importBtnText"></div>
        <div id="importProgress"></div>
        <div id="importStatus"></div>
        <div id="importResults"></div>
        <div>
          <input type="radio" name="conflict_strategy" value="use_theirs" checked />
        </div>
        <button id="validateImportBtn" type="button"></button>
        <button id="executeImportBtn" type="submit"></button>
      </form>
      <table class="table"><tbody></tbody></table>
    `);
  };

  const loadScript = () => {
    const domReadyHandlers = [];
    const originalAddEventListener = document.addEventListener.bind(document);

    document.addEventListener = function (event, handler, options) {
      if (event === 'DOMContentLoaded') {
        domReadyHandlers.push(handler);
      } else {
        originalAddEventListener(event, handler, options);
      }
    };

    jest.isolateModules(() => {
      require('../../../static/script');
    });

    document.addEventListener = originalAddEventListener;

    const handler = domReadyHandlers.pop();
    if (handler) {
      handler.call(document, new Event('DOMContentLoaded'));
    }
  };

  it('enables editing and cancel restores original values', () => {
    setupTableDom();
    loadScript();

    const editButton = document.querySelector('.edit-btn');
    editButton.click();

    const titleInput = document.querySelector('input[name="course_title"]');
    expect(titleInput).not.toBeNull();
    expect(JSON.parse(document.querySelector('tr').dataset.originalValues).course_title).toBe(
      'Intro Engineering'
    );

    const cancelButton = document.querySelector('.cancel-btn');
    cancelButton.click();

    expect(document.querySelector('input[name="course_title"]')).toBeNull();
    expect(document.querySelector('tr').dataset.originalValues).toBeUndefined();
  });

  it('saves edited rows and updates display', async () => {
    setupTableDom();
    loadScript();

    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });

    document.querySelector('.edit-btn').click();

    document.querySelector('input[name="course_title"]').value = 'Advanced Engineering';
    document.querySelector('input[name="num_students"]').value = '10';
    document.querySelector('input[name="grade_a"]').value = '5';
    document.querySelector('input[name="grade_b"]').value = '3';
    document.querySelector('input[name="grade_c"]').value = '2';
    document.querySelector('input[name="grade_d"]').value = '0';
    document.querySelector('input[name="grade_f"]').value = '0';

    document.querySelector('.save-btn').click();
    await flushPromises();

    const saveCall = global.fetch.mock.calls.find(call => call[0].includes('/edit_course/'));
    expect(saveCall).toBeDefined();
    expect(saveCall[1]).toEqual(expect.objectContaining({ method: 'POST' }));
    const requestPayload = JSON.parse(saveCall[1].body);
    expect(requestPayload.course_title).toBe('Advanced Engineering');
    expect(requestPayload.grade_a).toBe('5');
    expect(document.querySelector('tr').dataset.originalValues).toBeUndefined();
    expect(document.querySelectorAll('.inline-edit-input')).toHaveLength(0);
    expect(document.querySelector('tr').cells[1].textContent).toBe('Advanced Engineering');
  });

  it('deletes rows when confirmed', async () => {
    setupTableDom();
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });
    loadScript();

    document.querySelector('.delete-btn').click();
    await flushPromises();
    await flushPromises();

    expect(global.fetch).toHaveBeenCalledWith('/delete_course/course-1', expect.objectContaining({ method: 'POST' }));
    expect(window.alert).toHaveBeenCalled();
    expect(document.querySelectorAll('tr')).toHaveLength(0);
  });

  it('loads dashboard tiles on startup', async () => {
    setBody(`
      <div id="coursesData"></div>
      <div id="instructorsData"></div>
      <div id="sectionsData"></div>
      <div id="termsData"></div>
      <table class="table"><tbody></tbody></table>
    `);

    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, count: 5 })
    });

    loadScript();
    await flushPromises();
    await flushPromises();

    expect(document.getElementById('coursesData').textContent).toContain('5 total');
  });

  it('prevents saving when grade totals mismatch', () => {
    setupTableDom();
    loadScript();

    document.querySelector('.edit-btn').click();
    document.querySelector('input[name="num_students"]').value = '5';
    document.querySelector('input[name="grade_a"]').value = '2';
    document.querySelector('input[name="grade_b"]').value = '1';
    document.querySelector('input[name="grade_c"]').value = '0';
    document.querySelector('input[name="grade_d"]').value = '0';
    document.querySelector('input[name="grade_f"]').value = '0';

    window.alert.mockClear();
    document.querySelector('.save-btn').click();
    expect(window.alert).toHaveBeenCalledWith(expect.stringContaining('Sum of grades'));
    const editCalls = global.fetch.mock.calls.filter(call => call[0].includes('/edit_course/'));
    expect(editCalls.length).toBe(0);
  });

  it('shows errors when delete fails', async () => {
    setupTableDom();
    global.fetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ error: 'Server error' })
    });
    loadScript();

    window.alert.mockClear();
    document.querySelector('.delete-btn').click();
    await flushPromises();
    await flushPromises();
    await flushPromises();

    expect(window.alert).toHaveBeenCalled();
    expect(window.alert.mock.calls[0][0]).toContain('500');
  });

  it('initializes the import form and validates inputs', async () => {
    setupImportDom();
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, count: 0 })
    });
    loadScript();

    const importText = document.getElementById('importBtnText');
    expect(importText.textContent).toBe('Execute Import');

    const dryRun = document.getElementById('dry_run');
    dryRun.checked = true;
    dryRun.dispatchEvent(new Event('change'));
    expect(importText.textContent).toBe('Test Import (Dry Run)');

    const validateBtn = document.getElementById('validateImportBtn');
    window.alert.mockClear();
    validateBtn.click();
    expect(window.alert).toHaveBeenCalledWith('Please select an Excel file first.');

    const fileInput = document.getElementById('excel_file');
    const fakeFile = { name: 'test.xlsx' };
    Object.defineProperty(fileInput, 'files', {
      value: [fakeFile],
      configurable: true
    });

    const adapterSelect = document.getElementById('import_adapter');
    adapterSelect.value = 'adapter_a';

    window.alert.mockClear();
    const validateResponse = {
      ok: true,
      json: async () => ({ success: true, validation: { rows: 10 } })
    };

    global.fetch.mockResolvedValueOnce(validateResponse);
    validateBtn.click();
    await flushPromises();
    expect(global.fetch).toHaveBeenCalledWith('/api/import/validate', expect.any(Object));
  });

  it('executes import workflow and handles progress completion', async () => {
    jest.useFakeTimers();
    const file = new File(['data'], 'courses.xlsx', { type: 'application/vnd.ms-excel' });

    setBody(`
      <div id="coursesData"></div>
      <div id="instructorsData"></div>
      <div id="sectionsData"></div>
      <div id="termsData"></div>
      <div class="progress"><div class="progress-bar" role="progressbar"></div></div>
      <div id="importResults"></div>
      <div id="importProgress" style="display:none"></div>
      <div id="importStatus"></div>
      <form id="excelImportForm">
        <input type="file" id="excel_file" />
        <select id="import_adapter"><option value="adapter_a" selected>Adapter A</option></select>
        <input type="checkbox" id="dry_run" />
        <input type="checkbox" id="delete_existing_db" />
        <div>
          <input type="radio" name="conflict_strategy" value="use_theirs" checked />
        </div>
        <div id="importBtnText"></div>
        <button id="validateImportBtn" type="button"></button>
        <button id="executeImportBtn" type="submit"></button>
      </form>
      <table class="table"><tbody></tbody></table>
    `);

    const responses = {
      '/api/courses': { success: true, count: 0 },
      '/api/instructors': { success: true, count: 0 },
      '/api/sections': { success: true, count: 0 },
      '/api/terms': { success: true, count: 0 },
      '/api/import/excel': { success: true, progress_id: 'abc123' },
      '/api/import/progress/abc123': {
        status: 'completed',
        percentage: 100,
        message: 'Done',
        records_processed: 10,
        total_records: 10,
        result: {
          success: true,
          records_created: 5,
          errors: Array.from({ length: 12 }).map((_, idx) => `Error ${idx}`),
          warnings: Array.from({ length: 7 }).map((_, idx) => `Warning ${idx}`),
          conflicts: Array.from({ length: 25 }).map((_, idx) => ({
            entity_type: 'Course',
            entity_key: `C-${idx}`,
            field_name: 'name',
            existing_value: 'Old',
            import_value: 'New',
            resolution: 'kept_new'
          }))
        }
      }
    };

    global.fetch.mockImplementation((url, options) => {
      if (responses[url]) {
        return Promise.resolve({ ok: true, json: async () => responses[url] });
      }
      if (url.includes('/api/import/progress/')) {
        return Promise.resolve({ ok: true, json: async () => ({ status: 'running', percentage: 10 }) });
      }
      return Promise.resolve({ ok: true, json: async () => ({ success: true, count: 0 }) });
    });

    loadScript();

    const fileInput = document.getElementById('excel_file');
    Object.defineProperty(fileInput, 'files', {
      value: [file],
      configurable: true
    });

    const dryRunCheckbox = document.getElementById('dry_run');
    dryRunCheckbox.checked = false;

    const form = document.getElementById('excelImportForm');
    global.fetch.mockImplementation(url => {
      if (url === '/api/import/excel') {
        return Promise.resolve({ ok: true, json: async () => responses['/api/import/excel'] });
      }
      if (url === '/api/import/progress/abc123') {
        return Promise.resolve({ ok: true, json: async () => responses['/api/import/progress/abc123'] });
      }
      return Promise.resolve({ ok: true, json: async () => ({ success: true, count: 0 }) });
    });

    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await flushPromises();

    expect(document.getElementById('importProgress').style.display).toBe('block');

    jest.runOnlyPendingTimers();
    await flushPromises();
    expect(document.getElementById('importResults').innerHTML).toContain('Conflicts Resolved');

    jest.advanceTimersByTime(3000);
    expect(document.getElementById('importResults').textContent).toContain('Import completed successfully');

    jest.useRealTimers();
  });

  it('handles import progress error states', async () => {
    jest.useFakeTimers();

    setBody(`
      <div id="importResults"></div>
      <div id="importProgress"></div>
      <div id="importStatus"></div>
      <form id="excelImportForm">
        <input type="file" id="excel_file" />
        <select id="import_adapter"><option value="adapter_a" selected>Adapter A</option></select>
        <input type="checkbox" id="dry_run" />
        <div>
          <input type="radio" name="conflict_strategy" value="use_theirs" checked />
        </div>
        <div id="importBtnText"></div>
        <button id="validateImportBtn" type="button"></button>
        <button id="executeImportBtn" type="submit"></button>
      </form>
      <table class="table"><tbody></tbody></table>
    `);

    const file = new File(['data'], 'courses.xlsx');
    Object.defineProperty(document.getElementById('excel_file'), 'files', {
      value: [file],
      configurable: true
    });

    global.fetch.mockImplementation(url => {
      if (url === '/api/import/excel') {
        return Promise.resolve({ ok: true, json: async () => ({ success: true, progress_id: 'err' }) });
      }
      if (url === '/api/import/progress/err') {
        return Promise.resolve({ ok: true, json: async () => ({ status: 'error', message: 'Import failed' }) });
      }
      return Promise.resolve({ ok: true, json: async () => ({ success: true, count: 0 }) });
    });

    loadScript();

    const form = document.getElementById('excelImportForm');
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await flushPromises();
    jest.runOnlyPendingTimers();
    await flushPromises();

    expect(document.getElementById('importResults').innerHTML).toContain('Import failed');
    jest.useRealTimers();
  });

  describe('additional error handling and edge cases', () => {
    it('handles network errors during save operations', async () => {
      setupTableDom();
      loadScript();
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      // Click edit first to create input fields
      document.querySelector('.edit-btn').click();

      // Fill valid data
      document.querySelector('input[name="num_students"]').value = '25';
      document.querySelector('input[name="grade_a"]').value = '5';
      document.querySelector('input[name="grade_b"]').value = '10';
      document.querySelector('input[name="grade_c"]').value = '8';
      document.querySelector('input[name="grade_d"]').value = '2';
      document.querySelector('input[name="grade_f"]').value = '0';

      window.alert.mockClear();
      document.querySelector('.save-btn').click();
      await flushPromises();

      expect(window.alert).toHaveBeenCalledWith('Failed to send update request.');
    });

    it('handles malformed JSON responses during save', async () => {
      setupTableDom();
      loadScript();
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => { throw new Error('Invalid JSON'); }
      });

      // Click edit first to create input fields
      document.querySelector('.edit-btn').click();

      // Fill valid data
      document.querySelector('input[name="num_students"]').value = '25';
      document.querySelector('input[name="grade_a"]').value = '5';
      document.querySelector('input[name="grade_b"]').value = '10';
      document.querySelector('input[name="grade_c"]').value = '8';
      document.querySelector('input[name="grade_d"]').value = '2';
      document.querySelector('input[name="grade_f"]').value = '0';

      window.alert.mockClear();
      document.querySelector('.save-btn').click();
      await flushPromises();

      expect(window.alert).toHaveBeenCalledWith('Failed to send update request.');
    });

    it('handles edge case grade values correctly', async () => {
      setupTableDom();
      loadScript();
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true })
      });

      // Click edit first to create input fields
      document.querySelector('.edit-btn').click();

      // Test with integer values that sum correctly
      document.querySelector('input[name="num_students"]').value = '25';
      document.querySelector('input[name="grade_a"]').value = '5';
      document.querySelector('input[name="grade_b"]').value = '10';
      document.querySelector('input[name="grade_c"]').value = '8';
      document.querySelector('input[name="grade_d"]').value = '2';
      document.querySelector('input[name="grade_f"]').value = '0';

      window.alert.mockClear();
      document.querySelector('.save-btn').click();
      await flushPromises();

      // Should not show error for valid sum
      expect(window.alert).not.toHaveBeenCalled();
    });

    it('handles basic DOM setup', () => {
      setupTableDom();
      loadScript();

      // Just test that the basic elements exist
      const table = document.querySelector('table');
      const editBtn = document.querySelector('.edit-btn');
      
      expect(table).toBeTruthy();
      expect(editBtn).toBeTruthy();
    });

    it('handles successful data operations', async () => {
      setupTableDom();
      loadScript();
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true })
      });

      // Click edit to create inputs
      document.querySelector('.edit-btn').click();

      // Verify inputs were created
      expect(document.querySelector('input[name="num_students"]')).toBeTruthy();
      expect(document.querySelector('input[name="grade_a"]')).toBeTruthy();
    });
  });
});
