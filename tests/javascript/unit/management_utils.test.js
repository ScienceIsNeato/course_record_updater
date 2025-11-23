const { setBody } = require('../helpers/dom');
const managementUtils = require('../../../static/management_utils');

describe('management_utils.js', () => {
  let showMessageSpy;
  let alertSpy;
  let consoleErrorSpy;
  let loadTableDataSpy;
  let locationReloadSpy;

  beforeEach(() => {
    setBody(''); // Reset DOM

    showMessageSpy = jest.fn();
    global.showMessage = showMessageSpy;

    alertSpy = jest.spyOn(window, 'alert').mockImplementation();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

    loadTableDataSpy = jest.fn();
    global.loadTableData = loadTableDataSpy;

    // Mock location.reload
    delete global.location;
    global.location = { reload: jest.fn() };
    locationReloadSpy = global.location.reload;
  });

  afterEach(() => {
    jest.restoreAllMocks();
    delete global.showMessage;
    delete global.loadTableData;
  });

  test('showSuccess uses global.showMessage if available', () => {
    managementUtils.showSuccess('Success!');
    expect(showMessageSpy).toHaveBeenCalledWith('Success!', 'success');
    expect(alertSpy).not.toHaveBeenCalled();
  });

  test('showError uses global.showMessage if available', () => {
    managementUtils.showError('Error!');
    expect(showMessageSpy).toHaveBeenCalledWith('Error!', 'danger');
    expect(alertSpy).not.toHaveBeenCalled();
  });

  test('reloadDataTable uses global.loadTableData if available', () => {
    managementUtils.reloadDataTable();
    expect(loadTableDataSpy).toHaveBeenCalled();
    expect(locationReloadSpy).not.toHaveBeenCalled();
  });

  test('reloadDataTable falls back to location.reload if loadTableData missing', () => {
    delete global.loadTableData;
    managementUtils.reloadDataTable();
    expect(locationReloadSpy).toHaveBeenCalled();
  });
});

