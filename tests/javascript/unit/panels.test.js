const { PanelManager } = require('../../../static/panels');
const { setBody } = require('../helpers/dom');

describe('PanelManager', () => {
  beforeEach(() => {
    setBody(`
      <div class="dashboard-panel" id="panel-1">
        <div class="panel-header">
          <h5 class="panel-title">Overview</h5>
          <div class="panel-actions"></div>
          <button class="panel-toggle">▼</button>
        </div>
        <div class="panel-content">Content</div>
      </div>
      <table class="panel-table" id="table-1">
        <thead>
          <tr>
            <th class="sortable" data-sort="name">Name</th>
          </tr>
        </thead>
        <tbody>
          <tr><td data-sort="b">Beta</td></tr>
          <tr><td data-sort="a">Alpha</td></tr>
        </tbody>
      </table>
      <div class="stat-item" data-stat="programs"></div>
      <div class="stat-item" data-stat="students"></div>
    `);
    global.requestAnimationFrame = cb => cb();
  });

  it('toggles panels and sorts tables', () => {
    const manager = new PanelManager();

    manager.togglePanel('panel-1');
    const panel = document.getElementById('panel-1');
    expect(panel.querySelector('.panel-content').classList.contains('collapsed')).toBe(true);

    manager.sortTable('table-1-name');
    const rows = Array.from(document.querySelectorAll('#table-1 tbody tr td')).map(cell => cell.textContent.trim());
    expect(rows).toEqual(['Alpha', 'Beta']);

    manager.sortTable('table-1-name');
    const descRows = Array.from(document.querySelectorAll('#table-1 tbody tr td')).map(cell => cell.textContent.trim());
    expect(descRows).toEqual(['Beta', 'Alpha']);
  });

  it('creates sortable tables from config data', () => {
    const manager = new PanelManager();
    const table = manager.createSortableTable({
      id: 'example-table',
      columns: [
        { key: 'program', label: 'Program', sortable: true },
        { key: 'courses', label: 'Courses', sortable: false }
      ],
      data: [
        { program: 'Nursing', courses: '12', courses_sort: '12' },
        { program: 'Biology', courses: '8', courses_sort: '8' }
      ]
    });

    expect(table.querySelectorAll('tbody tr')).toHaveLength(2);
    expect(table.querySelector('thead th').classList.contains('sortable')).toBe(true);
  });

  it('builds stat previews from cached data', () => {
    const manager = new PanelManager();
    const cache = {
      program_overview: [
        { program_name: 'Chemistry', course_count: 6 }
      ]
    };

    const preview = manager.buildPreviewFromCache('programs', cache);
    expect(preview.title).toBe('Programs');
    expect(preview.items[0]).toEqual({ label: 'Chemistry', value: '6 courses' });
  });

  it('focuses and unfocuses panels', () => {
    const manager = new PanelManager();
    manager.focusPanel('panel-1');

    const panel = document.getElementById('panel-1');
    expect(panel.classList.contains('panel-focused')).toBe(true);

    manager.unfocusPanel();
    expect(panel.classList.contains('panel-focused')).toBe(false);
  });

  it('shows and hides stat previews from cache', async () => {
    jest.useFakeTimers();
    const manager = new PanelManager();
    window.dashboardDataCache = {
      program_overview: [
        { program_name: 'Nursing', course_count: 3 }
      ],
      summary: { students: 120, sections: 10, courses: 5 }
    };

    await manager.showStatPreview('programs');
    expect(document.querySelector('.stat-preview')).not.toBeNull();

    manager.hideStatPreview('programs');
    jest.advanceTimersByTime(300);
    expect(document.querySelector('.stat-preview')).toBeNull();

    const preview = manager.buildPreviewFromCache('students', window.dashboardDataCache);
    expect(preview.items[0].value).toBe('120');
    jest.useRealTimers();
  });

  it('loads stat preview data via fetch when cache missing', async () => {
    const manager = new PanelManager();
    const originalFetch = global.fetch;
    window.dashboardDataCache = null;
    const responsePayload = {
      programs: [{ name: 'History', course_count: 4 }]
    };
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: async () => responsePayload
      })
    );

    const data = await manager.loadStatPreviewData('programs');
    expect(global.fetch).toHaveBeenCalledWith('/api/programs', expect.any(Object));
    expect(data.items[0].label).toBe('History');
    global.fetch = originalFetch;
  });

  it('handles stat preview fetch errors gracefully', async () => {
    const manager = new PanelManager();
    const originalFetch = global.fetch;
    window.dashboardDataCache = null;
    global.fetch = jest.fn(() => Promise.resolve({ ok: false, status: 500 }));

    await expect(manager.loadStatPreviewData('programs')).rejects.toThrow('Failed to load programs data');
    global.fetch = originalFetch;
  });

  it('hides all stat previews and clears pending timers', () => {
    jest.useFakeTimers();
    setBody(`
      <div class="stat-item" data-stat="programs"></div>
      <div class="stat-item" data-stat="users"></div>
    `);
    const manager = new PanelManager();
    manager.statPreviews.set('programs', { preview: document.createElement('div'), timeout: setTimeout(() => {}, 500) });
    manager.statPreviews.set('users', { preview: document.createElement('div'), timeout: setTimeout(() => {}, 500) });

    manager.hideAllStatPreviews();
    jest.runOnlyPendingTimers();
    expect(manager.statPreviews.get('programs').preview).toBeNull();
    expect(manager.statPreviews.get('users').preview).toBeNull();
    jest.useRealTimers();
  });

  it('computes cell values with fractions and dataset overrides', () => {
    const manager = new PanelManager();
    const cellWithData = document.createElement('td');
    cellWithData.dataset.sort = '42';
    expect(manager.getCellValue(cellWithData)).toBe('42');

    const cellFraction = document.createElement('td');
    cellFraction.textContent = '4/8';
    expect(manager.getCellValue(cellFraction)).toBe('0.5');
  });
});
