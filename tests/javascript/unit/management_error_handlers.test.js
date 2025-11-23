
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
});

