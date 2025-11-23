const { setBody, flushPromises } = require('../helpers/dom');

describe('offeringManagement.js Coverage Boost', () => {
  let mockLoadOfferings;

  beforeEach(() => {
    jest.resetModules();
    setBody(`
      <form id="createOfferingForm">
        <select id="offeringCourseId"><option value="c1">Course</option></select>
        <select id="offeringTermId"><option value="t1">Term</option></select>
        <input id="offeringCapacity" value="30">
        <input id="offeringStatus" type="checkbox">
        <button type="submit" id="createOfferingBtn">
            <span class="btn-text">Save</span>
            <span class="btn-spinner d-none"></span>
        </button>
      </form>
      <div id="createOfferingModal"></div>
      
      <form id="editOfferingForm">
        <input id="editOfferingId" value="o1">
        <select id="editOfferingCourseId"><option value="c1">Course</option></select>
        <select id="editOfferingTermId"><option value="t1">Term</option></select>
        <input id="editOfferingCapacity" value="30">
        <input id="editOfferingStatus" type="checkbox">
        <button type="submit" id="editOfferingBtn">
            <span class="btn-text">Save</span>
            <span class="btn-spinner d-none"></span>
        </button>
            <span class="btn-text">Save</span>
            <span class="btn-spinner d-none"></span>
        </button>
      </form>
      <div id="editOfferingModal"></div>
      
      <meta name="csrf-token" content="token">
    `);

    global.bootstrap = {
      Modal: jest.fn().mockImplementation(() => ({
        show: jest.fn(),
        hide: jest.fn()
      }))
    };
    global.bootstrap.Modal.getInstance = jest.fn(() => ({ hide: jest.fn() }));

    mockLoadOfferings = jest.fn();
    global.loadOfferings = mockLoadOfferings;
    
    jest.spyOn(window, 'alert').mockImplementation(() => {});
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    jest.spyOn(console, 'error').mockImplementation(() => {});

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, message: 'Success' })
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
    delete global.loadOfferings;
  });

  test('createOfferingForm calls loadOfferings on success', async () => {
    require('../../../static/offeringManagement.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
    
    const form = document.getElementById('createOfferingForm');
    form.dispatchEvent(new Event('submit'));
    
    await flushPromises();
    expect(mockLoadOfferings).toHaveBeenCalled();
  });

  test('editOfferingForm calls loadOfferings on success', async () => {
    require('../../../static/offeringManagement.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
    
    const form = document.getElementById('editOfferingForm');
    form.dispatchEvent(new Event('submit'));
    
    await flushPromises();
    expect(mockLoadOfferings).toHaveBeenCalled();
  });

  test('deleteOffering calls loadOfferings on success', async () => {
    require('../../../static/offeringManagement.js');
    await global.deleteOffering('o1');
    await flushPromises();
    expect(mockLoadOfferings).toHaveBeenCalled();
  });
});

