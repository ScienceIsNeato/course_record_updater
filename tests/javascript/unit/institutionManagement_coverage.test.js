const { setBody, flushPromises } = require('../helpers/dom');

describe('institutionManagement.js Coverage Boost', () => {
  let mockLoadInstitutions;

  beforeEach(() => {
    jest.resetModules();
    setBody(`
      <form id="createInstitutionForm">
        <input id="institutionName" value="Test U">
        <input id="institutionShortName" value="TU">
        <input id="institutionAddress" value="123 Main">
        <input id="institutionPhone" value="555-1234">
        <input id="institutionWebsite" value="http://test.edu">
        <input id="adminEmail" value="admin@test.edu">
        <input id="adminFirstName" value="Admin">
        <input id="adminLastName" value="User">
        <button type="submit" id="createInstitutionBtn">
            <span class="btn-text">Save</span>
            <span class="btn-spinner d-none"></span>
        </button>
      </form>
      <div id="createInstitutionModal"></div>
      
      <form id="editInstitutionForm">
        <input id="editInstitutionId" value="i1">
        <input id="editInstitutionName" value="Test U">
        <input id="editInstitutionShortName" value="TU">
        <input id="editInstitutionAddress" value="123 Main">
        <input id="editInstitutionPhone" value="555-1234">
        <input id="editInstitutionWebsite" value="http://test.edu">
        <button type="submit" id="editInstitutionBtn">
            <span class="btn-text">Save</span>
            <span class="btn-spinner d-none"></span>
        </button>
      </form>
      <div id="editInstitutionModal"></div>
      
      <meta name="csrf-token" content="token">
    `);

    global.bootstrap = {
      Modal: jest.fn().mockImplementation(() => ({
        show: jest.fn(),
        hide: jest.fn()
      }))
    };
    global.bootstrap.Modal.getInstance = jest.fn(() => ({ hide: jest.fn() }));

    mockLoadInstitutions = jest.fn();
    global.loadInstitutions = mockLoadInstitutions;
    
    jest.spyOn(window, 'alert').mockImplementation(() => {});
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    jest.spyOn(window, 'prompt').mockReturnValue('i know what I\'m doing');
    jest.spyOn(console, 'error').mockImplementation(() => {});

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, message: 'Success' })
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
    delete global.loadInstitutions;
  });

  test('createInstitutionForm calls loadInstitutions on success', async () => {
    require('../../../static/institutionManagement.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
    
    const form = document.getElementById('createInstitutionForm');
    form.dispatchEvent(new Event('submit'));
    
    await flushPromises();
    expect(mockLoadInstitutions).toHaveBeenCalled();
  });

  test('editInstitutionForm calls loadInstitutions on success', async () => {
    require('../../../static/institutionManagement.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
    
    const form = document.getElementById('editInstitutionForm');
    form.dispatchEvent(new Event('submit'));
    
    await flushPromises();
    expect(mockLoadInstitutions).toHaveBeenCalled();
  });

  test('deleteInstitution calls loadInstitutions on success', async () => {
    require('../../../static/institutionManagement.js');
    await global.deleteInstitution('i1', 'Test U');
    await flushPromises();
    expect(mockLoadInstitutions).toHaveBeenCalled();
  });
});

