const { setBody, flushPromises } = require('../helpers/dom');

describe('panels.js Coverage Boost', () => {
  beforeEach(() => {
    jest.resetModules();
    // Basic DOM for panelManager initialization
    setBody(`
      <div id="system-activity-panel">
        <div class="panel-content">
          <div id="activityTableContainer"></div>
        </div>
        <button class="panel-toggle"></button>
      </div>
    `);
    jest.spyOn(console, 'error').mockImplementation(() => { });
    jest.spyOn(window, 'alert').mockImplementation(() => { });

    // Mock window.location
    delete window.location;
    window.location = { href: '' };

    // Mock fetch for loadAuditLogs
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, logs: [] })
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('initializes panelManager on DOMContentLoaded', () => {
    require('../../../static/panels.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
    expect(global.panelManager).toBeDefined();
  });

  test('createPanel handles missing actions', () => {
    require('../../../static/panels.js');
    // Ensure panelManager is initialized
    document.dispatchEvent(new Event('DOMContentLoaded'));

    const panel = global.panelManager.createPanel({
      id: 'test-panel-1',
      title: 'Test Panel 1',
      content: 'Content 1',
      collapsed: false
    });

    expect(panel.innerHTML).toContain('Test Panel 1');
    expect(panel.querySelector('.panel-actions').innerHTML.trim()).toBe('');
  });

  test('createPanel renders actions', () => {
    require('../../../static/panels.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));

    const panel = global.panelManager.createPanel({
      id: 'test-panel-2',
      title: 'Test Panel 2',
      content: 'Content 2',
      collapsed: true,
      actions: [{ label: 'Action 1', icon: '<i></i>', onclick: 'void(0)' }]
    });

    expect(panel.querySelector('.panel-actions').textContent).toContain('Action 1');
    expect(panel.querySelector('.panel-content.collapsed')).toBeTruthy();
  });

  test('viewAllActivity redirects to audit logs', () => {
    require('../../../static/panels.js');
    global.viewAllActivity();
    expect(window.location.href).toBe('/audit-logs');
  });

  test('filterActivity redirects to audit logs', () => {
    require('../../../static/panels.js');
    global.filterActivity();
    expect(window.location.href).toBe('/audit-logs');
  });

  test('getAuditDetails returns fallback', () => {
    require('../../../static/panels.js');
    const detail = global.getAuditDetails({ operation_type: 'UPDATE' });
    expect(detail).toBe('Entity modified');
  });

  test('getAuditDetails handles JSON parse error', () => {
    require('../../../static/panels.js');
    const detail = global.getAuditDetails({
      operation_type: 'UPDATE',
      changed_fields: '{invalid-json}'
    });
    expect(detail).toBe('Entity modified');
  });

  test('system activity panel auto-load', async () => {
    jest.useFakeTimers();
    require('../../../static/panels.js');

    document.dispatchEvent(new Event('DOMContentLoaded'));

    // Initial load
    if (global.fetch.mock.calls.length === 0) {
      console.log('Console errors:', console.error.mock.calls);
    }
    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/api/audit/recent'));

    // Interval load
    jest.advanceTimersByTime(30000);
    expect(global.fetch.mock.calls.length).toBeGreaterThanOrEqual(2);

    jest.useRealTimers();
  });
});
