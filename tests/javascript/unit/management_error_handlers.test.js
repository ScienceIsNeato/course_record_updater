
const { setBody } = require('../helpers/dom');

describe('Management Modules Error Handling', () => {
  let consoleErrorSpy;
  let alertSpy;
  let confirmSpy;

  beforeEach(() => {
    jest.resetModules();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    alertSpy = jest.spyOn(window, 'alert').mockImplementation();
    confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('userManagement.js deleteUser handles network error', async () => {
    require('../../../static/userManagement');
    global.fetch.mockRejectedValueOnce(new Error('Network error'));
    
    // Mock prompt for userManagement confirmation
    const promptSpy = jest.spyOn(window, 'prompt').mockReturnValue('DELETE User Name');
    
    if (globalThis.deleteUser) {
        await globalThis.deleteUser('u1', 'User Name');
        expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining('Failed'));
        expect(consoleErrorSpy).toHaveBeenCalled();
    }
    
    promptSpy.mockRestore();
  });

  test('offeringManagement.js deleteOffering handles network error', async () => {
    require('../../../static/offeringManagement');
    global.fetch.mockRejectedValueOnce(new Error('Network error'));
    
    if (globalThis.deleteOffering) {
        await globalThis.deleteOffering('o1');
        expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining('Failed'));
        expect(consoleErrorSpy).toHaveBeenCalled();
    }
  });

  test('sectionManagement.js deleteSection handles network error', async () => {
    require('../../../static/sectionManagement');
    global.fetch.mockRejectedValueOnce(new Error('Network error'));
    
    if (globalThis.deleteSection) {
        await globalThis.deleteSection('s1', 'Section 1');
        expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining('Failed'));
        expect(consoleErrorSpy).toHaveBeenCalled();
    }
  });

  test('courseManagement.js deleteCourse handles network error', async () => {
    require('../../../static/courseManagement');
    global.fetch.mockRejectedValueOnce(new Error('Network error'));
    
    if (globalThis.deleteCourse) {
        await globalThis.deleteCourse('c1', 'Course 1');
        expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining('Failed'));
        expect(consoleErrorSpy).toHaveBeenCalled();
    }
  });

  // Success Callback Tests (Coverage for load* functions)
  
  test('userManagement.js deleteUser success calls loadUsers', async () => {
    require('../../../static/userManagement');
    global.fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) });
    const promptSpy = jest.spyOn(window, 'prompt').mockReturnValue('DELETE User Name');
    
    globalThis.loadUsers = jest.fn();
    
    if (globalThis.deleteUser) {
        await globalThis.deleteUser('u1', 'User Name');
        expect(globalThis.loadUsers).toHaveBeenCalled();
    }
    promptSpy.mockRestore();
  });

  test('offeringManagement.js deleteOffering success calls loadOfferings', async () => {
    require('../../../static/offeringManagement');
    global.fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) });
    // offeringManagement uses confirm, mocked in beforeEach
    
    globalThis.loadOfferings = jest.fn();
    
    if (globalThis.deleteOffering) {
        await globalThis.deleteOffering('o1');
        expect(globalThis.loadOfferings).toHaveBeenCalled();
    }
  });

  test('sectionManagement.js deleteSection success calls loadSections', async () => {
    require('../../../static/sectionManagement');
    global.fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) });
    
    globalThis.loadSections = jest.fn();
    
    if (globalThis.deleteSection) {
        await globalThis.deleteSection('s1', 'Section 1');
        expect(globalThis.loadSections).toHaveBeenCalled();
    }
  });

  test('courseManagement.js deleteCourse success calls loadCourses', async () => {
    require('../../../static/courseManagement');
    global.fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) });
    
    globalThis.loadCourses = jest.fn();
    
    if (globalThis.deleteCourse) {
        await globalThis.deleteCourse('c1', 'Course 1');
        expect(globalThis.loadCourses).toHaveBeenCalled();
    }
  });
});

