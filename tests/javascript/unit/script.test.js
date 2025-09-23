const { setBody, flushPromises } = require('../helpers/dom');

let consoleLogSpy;
let consoleErrorSpy;

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
  });

  afterEach(() => {
    consoleLogSpy.mockRestore();
    consoleErrorSpy.mockRestore();
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
});
