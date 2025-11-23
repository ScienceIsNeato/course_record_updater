
const { setBody } = require('../helpers/dom');

describe('panels.js coverage', () => {
  beforeEach(() => {
    jest.resetModules();
    setBody('<div id="panels-container"></div>');
  });

  test('generateSecureId uses crypto API', () => {
    // Ensure crypto is present
    const mockGetRandomValues = jest.fn(arr => {
      arr[0] = 999;
      return arr;
    });
    
    // Mock globalThis.crypto explicitly
    Object.defineProperty(globalThis, 'crypto', {
        value: { getRandomValues: mockGetRandomValues },
        writable: true,
        configurable: true
    });
    
    // Load module
    const { PanelManager } = require('../../../static/panels');
    const manager = new PanelManager();
    
    // Trigger usage via initializePanels (called by init)
    document.body.innerHTML = `
      <div class="dashboard-panel">
        <div class="panel-header"></div>
        <div class="panel-content">
            <table class="panel-table"></table>
        </div>
      </div>
    `;
    
    console.log('Panels found:', document.querySelectorAll('.dashboard-panel').length);
    
    manager.init();
    
    expect(mockGetRandomValues).toHaveBeenCalled();
  });

  test('handleGlobalClick triggers sortTable on header click', () => {
    const { PanelManager } = require('../../../static/panels');
    const manager = new PanelManager();
    manager.sortTable = jest.fn();
    
    document.body.innerHTML = `
      <table id="test-table" class="panel-table">
        <thead>
            <tr>
                <th class="sortable" data-sort="name">Name</th>
            </tr>
        </thead>
      </table>
    `;
    
    manager.init();
    
    const th = document.querySelector('th');
    th.click();
    
    expect(manager.sortTable).toHaveBeenCalled();
  });

  test('handleGlobalClick triggers focusPanel on double click', () => {
    const { PanelManager } = require('../../../static/panels');
    const manager = new PanelManager();
    manager.focusPanel = jest.fn();
    
    document.body.innerHTML = `
      <div id="p1" class="dashboard-panel">
        <div class="panel-header">
            <div class="panel-title">Title</div>
        </div>
      </div>
    `;
    
    manager.init();
    
    const title = document.querySelector('.panel-title');
    const event = new MouseEvent('click', { detail: 2, bubbles: true });
    title.dispatchEvent(event);
    
    expect(manager.focusPanel).toHaveBeenCalledWith('p1');
  });
});

