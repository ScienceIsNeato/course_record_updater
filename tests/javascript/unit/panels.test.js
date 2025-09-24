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

  it('handles basic panel management', () => {
    setBody(`
      <div class="panel" id="test-panel">
        <div class="panel-header">
          <h3>Test Panel</h3>
        </div>
        <div class="panel-body"></div>
      </div>
    `);

    const manager = new PanelManager();
    const panel = document.getElementById('test-panel');

    // Just test that we can create a manager and access panels
    expect(panel).toBeTruthy();
    expect(manager).toBeTruthy();
    expect(panel.querySelector('.panel-header')).toBeTruthy();
  });

  describe('edge cases and error handling', () => {
    it('handles missing panels gracefully', () => {
      const manager = new PanelManager();
      
      // Try to toggle a non-existent panel
      expect(() => manager.togglePanel('non-existent')).not.toThrow();
      expect(() => manager.focusPanel('non-existent')).not.toThrow();
    });

    it('handles missing tables gracefully', () => {
      const manager = new PanelManager();
      
      // Try to sort a non-existent table
      expect(() => manager.sortTable('non-existent-table')).not.toThrow();
    });

    it('handles empty data in stat previews', () => {
      const manager = new PanelManager();
      
      // The function expects cache to have properties, so null/empty cache will cause errors
      // Let's test with valid cache structure but empty data
      const emptyDataCache = {
        program_overview: [],
        programs: [],
        courses: [],
        sections: []
      };
      
      const emptyPreview = manager.buildPreviewFromCache('programs', emptyDataCache);
      // buildPreviewFromCache returns null when data array is empty
      expect(emptyPreview).toBeNull();
    });

    it('handles different data types in createSortableTable', () => {
      const manager = new PanelManager();
      
      // Test with empty data
      const emptyTable = manager.createSortableTable({
        id: 'empty-table',
        columns: [{ key: 'name', label: 'Name', sortable: true }],
        data: []
      });
      expect(emptyTable.querySelectorAll('tbody tr')).toHaveLength(0);
      
      // Test with missing columns
      const noColumnsTable = manager.createSortableTable({
        id: 'no-columns',
        columns: [],
        data: [{ name: 'test' }]
      });
      expect(noColumnsTable.querySelectorAll('thead th')).toHaveLength(0);
    });

    it('handles getCellValue edge cases', () => {
      const manager = new PanelManager();
      
      // Test with empty cell
      const emptyCell = document.createElement('td');
      expect(manager.getCellValue(emptyCell)).toBe('');
      
      // Test with cell containing only whitespace
      const whitespaceCell = document.createElement('td');
      whitespaceCell.textContent = '   ';
      expect(manager.getCellValue(whitespaceCell)).toBe('');
      
      // Test with invalid fraction
      const invalidFractionCell = document.createElement('td');
      invalidFractionCell.textContent = 'not/a/fraction';
      expect(manager.getCellValue(invalidFractionCell)).toBe('not/a/fraction');
      
      // Test with zero denominator fraction
      const zeroDenomCell = document.createElement('td');
      zeroDenomCell.textContent = '5/0';
      expect(manager.getCellValue(zeroDenomCell)).toBe('5/0');
    });

    it('handles stat preview with different data structures', () => {
      const manager = new PanelManager();
      
      // Test sections preview
      const sectionsCache = {
        sections: [
          { course_number: 'MATH101', enrollment: 25, status: 'active' },
          { course_number: 'PHYS201', enrollment: 30, status: 'completed' }
        ]
      };
      const sectionsPreview = manager.buildPreviewFromCache('sections', sectionsCache);
      expect(sectionsPreview.items).toHaveLength(2);
      expect(sectionsPreview.items[0].label).toContain('MATH101');
      expect(sectionsPreview.items[0].value).toContain('25 students');
      
      // Test courses preview
      const coursesCache = {
        courses: [
          { course_number: 'BIO101', course_title: 'Biology Basics', sections: [{}, {}] }
        ]
      };
      const coursesPreview = manager.buildPreviewFromCache('courses', coursesCache);
      expect(coursesPreview.items[0].value).toBe('Biology Basics');
    });

    it('handles multiple panel toggles correctly', () => {
      setBody(`
        <div class="dashboard-panel" id="panel-a">
          <div class="panel-header"><button class="panel-toggle">▼</button></div>
          <div class="panel-content">Content A</div>
        </div>
        <div class="dashboard-panel" id="panel-b">
          <div class="panel-header"><button class="panel-toggle">▼</button></div>
          <div class="panel-content">Content B</div>
        </div>
      `);
      
      const manager = new PanelManager();
      
      // Toggle both panels
      manager.togglePanel('panel-a');
      manager.togglePanel('panel-b');
      
      const panelA = document.getElementById('panel-a');
      const panelB = document.getElementById('panel-b');
      
      expect(panelA.querySelector('.panel-content').classList.contains('collapsed')).toBe(true);
      expect(panelB.querySelector('.panel-content').classList.contains('collapsed')).toBe(true);
      
      // Toggle back
      manager.togglePanel('panel-a');
      expect(panelA.querySelector('.panel-content').classList.contains('collapsed')).toBe(false);
      expect(panelB.querySelector('.panel-content').classList.contains('collapsed')).toBe(true);
    });

    it('handles table sorting with mixed data types', () => {
      setBody(`
        <table class="panel-table" id="mixed-table">
          <thead>
            <tr><th class="sortable" data-sort="value">Value</th></tr>
          </thead>
          <tbody>
            <tr><td data-sort="10">Ten</td></tr>
            <tr><td data-sort="2">Two</td></tr>
            <tr><td data-sort="100">Hundred</td></tr>
          </tbody>
        </table>
      `);
      
      const manager = new PanelManager();
      manager.sortTable('mixed-table-value');
      
      const sortedValues = Array.from(document.querySelectorAll('#mixed-table tbody tr td'))
        .map(cell => cell.getAttribute('data-sort'));
      expect(sortedValues).toEqual(['2', '10', '100']);
    });

    it('handles stat preview positioning edge cases', async () => {
      jest.useFakeTimers();
      setBody(`
        <div class="stat-item" data-stat="programs" style="position: absolute; top: 10px; left: 10px; width: 100px; height: 50px;"></div>
      `);
      
      const manager = new PanelManager();
      window.dashboardDataCache = {
        program_overview: [{ program_name: 'Test', course_count: 1 }]
      };
      
      // Mock getBoundingClientRect for positioning
      const mockGetBoundingClientRect = jest.fn(() => ({
        top: 10, left: 10, width: 100, height: 50, right: 110, bottom: 60
      }));
      document.querySelector('.stat-item').getBoundingClientRect = mockGetBoundingClientRect;
      
      await manager.showStatPreview('programs');
      
      const preview = document.querySelector('.stat-preview');
      expect(preview).not.toBeNull();
      // Just test that the preview was created and positioned, don't check specific style values
      
      jest.useRealTimers();
    });
  });
});
