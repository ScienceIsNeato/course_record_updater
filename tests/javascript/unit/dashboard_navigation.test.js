/**
 * @jest-environment jsdom
 */

describe('Dashboard Navigation', () => {
  let mockDocument;

  beforeEach(() => {
    // Set up DOM
    document.body.innerHTML = `
      <div class="navbar-nav">
        <button class="nav-link" id="dashboard-view-all">All</button>
        <button class="nav-link" id="dashboard-teaching">Teaching</button>
        <button class="nav-link" id="dashboard-assessments">Assessments</button>
      </div>
      <div id="instructor-teaching-panel" style="display: block;">Teaching</div>
      <div id="instructor-assessment-panel" style="display: block;">Assessment</div>
      <div id="instructor-activity-panel" style="display: block;">Activity</div>
      <div id="instructor-summary-panel" style="display: block;">Summary</div>
    `;

    // Load the module
    require('../../../static/dashboard_navigation.js');
  });

  afterEach(() => {
    jest.resetModules();
    delete window.configureDashboardFilter;
    delete window.filterDashboard;
  });

  describe('configureDashboardFilter', () => {
    it('should expose configureDashboardFilter on window', () => {
      expect(typeof window.configureDashboardFilter).toBe('function');
    });

    it('should configure dashboard with panel mappings', () => {
      const panelMapping = {
        teaching: ['instructor-teaching-panel'],
        assessments: ['instructor-assessment-panel'],
        all: [
          'instructor-teaching-panel',
          'instructor-assessment-panel',
          'instructor-activity-panel',
          'instructor-summary-panel'
        ]
      };
      const allPanelIds = [
        'instructor-teaching-panel',
        'instructor-assessment-panel',
        'instructor-activity-panel',
        'instructor-summary-panel'
      ];

      window.configureDashboardFilter(panelMapping, allPanelIds);

      expect(typeof window.filterDashboard).toBe('function');
    });

    it('should show only specified panels when filter is applied', () => {
      const panelMapping = {
        teaching: ['instructor-teaching-panel'],
        all: [
          'instructor-teaching-panel',
          'instructor-assessment-panel',
          'instructor-activity-panel',
          'instructor-summary-panel'
        ]
      };
      const allPanelIds = [
        'instructor-teaching-panel',
        'instructor-assessment-panel',
        'instructor-activity-panel',
        'instructor-summary-panel'
      ];

      window.configureDashboardFilter(panelMapping, allPanelIds);
      window.filterDashboard('teaching');

      expect(document.getElementById('instructor-teaching-panel').style.display).toBe('block');
      expect(document.getElementById('instructor-assessment-panel').style.display).toBe('none');
      expect(document.getElementById('instructor-activity-panel').style.display).toBe('none');
      expect(document.getElementById('instructor-summary-panel').style.display).toBe('none');
    });

    it('should show all panels when "all" filter is applied', () => {
      const panelMapping = {
        teaching: ['instructor-teaching-panel'],
        all: [
          'instructor-teaching-panel',
          'instructor-assessment-panel',
          'instructor-activity-panel',
          'instructor-summary-panel'
        ]
      };
      const allPanelIds = [
        'instructor-teaching-panel',
        'instructor-assessment-panel',
        'instructor-activity-panel',
        'instructor-summary-panel'
      ];

      window.configureDashboardFilter(panelMapping, allPanelIds);
      window.filterDashboard('all');

      expect(document.getElementById('instructor-teaching-panel').style.display).toBe('block');
      expect(document.getElementById('instructor-assessment-panel').style.display).toBe('block');
      expect(document.getElementById('instructor-activity-panel').style.display).toBe('block');
      expect(document.getElementById('instructor-summary-panel').style.display).toBe('block');
    });

    it('should set active class on correct button', () => {
      const panelMapping = {
        teaching: ['instructor-teaching-panel'],
        all: [
          'instructor-teaching-panel',
          'instructor-assessment-panel',
          'instructor-activity-panel',
          'instructor-summary-panel'
        ]
      };
      const allPanelIds = [
        'instructor-teaching-panel',
        'instructor-assessment-panel',
        'instructor-activity-panel',
        'instructor-summary-panel'
      ];

      window.configureDashboardFilter(panelMapping, allPanelIds);
      window.filterDashboard('teaching');

      const teachingBtn = document.getElementById('dashboard-teaching');
      const allBtn = document.getElementById('dashboard-view-all');

      expect(teachingBtn.classList.contains('active')).toBe(true);
      expect(allBtn.classList.contains('active')).toBe(false);
    });

    it('should remove active class from other buttons', () => {
      const panelMapping = {
        teaching: ['instructor-teaching-panel'],
        assessments: ['instructor-assessment-panel'],
        all: [
          'instructor-teaching-panel',
          'instructor-assessment-panel',
          'instructor-activity-panel',
          'instructor-summary-panel'
        ]
      };
      const allPanelIds = [
        'instructor-teaching-panel',
        'instructor-assessment-panel',
        'instructor-activity-panel',
        'instructor-summary-panel'
      ];

      window.configureDashboardFilter(panelMapping, allPanelIds);

      // First click teaching
      window.filterDashboard('teaching');
      expect(document.getElementById('dashboard-teaching').classList.contains('active')).toBe(
        true
      );

      // Then click assessments
      window.filterDashboard('assessments');
      expect(document.getElementById('dashboard-teaching').classList.contains('active')).toBe(
        false
      );
      expect(document.getElementById('dashboard-assessments').classList.contains('active')).toBe(
        true
      );
    });

    it('should handle missing panels gracefully', () => {
      const panelMapping = {
        teaching: ['instructor-teaching-panel', 'non-existent-panel'],
        all: ['instructor-teaching-panel']
      };
      const allPanelIds = ['instructor-teaching-panel', 'non-existent-panel'];

      window.configureDashboardFilter(panelMapping, allPanelIds);

      // Should not throw error for missing panel
      expect(() => window.filterDashboard('teaching')).not.toThrow();
    });

    it('should default to "all" view if unknown view requested', () => {
      const panelMapping = {
        teaching: ['instructor-teaching-panel'],
        all: [
          'instructor-teaching-panel',
          'instructor-assessment-panel',
          'instructor-activity-panel',
          'instructor-summary-panel'
        ]
      };
      const allPanelIds = [
        'instructor-teaching-panel',
        'instructor-assessment-panel',
        'instructor-activity-panel',
        'instructor-summary-panel'
      ];

      window.configureDashboardFilter(panelMapping, allPanelIds);
      window.filterDashboard('unknown-view');

      // Should show all panels when unknown view requested
      expect(document.getElementById('instructor-teaching-panel').style.display).toBe('block');
      expect(document.getElementById('instructor-assessment-panel').style.display).toBe('block');
      expect(document.getElementById('instructor-activity-panel').style.display).toBe('block');
      expect(document.getElementById('instructor-summary-panel').style.display).toBe('block');
    });

    it('should initialize with all panels visible on DOMContentLoaded', () => {
      const panelMapping = {
        teaching: ['instructor-teaching-panel'],
        all: [
          'instructor-teaching-panel',
          'instructor-assessment-panel',
          'instructor-activity-panel',
          'instructor-summary-panel'
        ]
      };
      const allPanelIds = [
        'instructor-teaching-panel',
        'instructor-assessment-panel',
        'instructor-activity-panel',
        'instructor-summary-panel'
      ];

      // Configure first
      window.configureDashboardFilter(panelMapping, allPanelIds);

      // Trigger DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);

      // All panels should be visible after DOMContentLoaded
      expect(document.getElementById('instructor-teaching-panel').style.display).toBe('block');
      expect(document.getElementById('instructor-assessment-panel').style.display).toBe('block');
      expect(document.getElementById('instructor-activity-panel').style.display).toBe('block');
      expect(document.getElementById('instructor-summary-panel').style.display).toBe('block');
    });

    it('should handle missing activeButton gracefully', () => {
      document.body.innerHTML = `
        <div class="navbar-nav">
          <!-- No button with id="dashboard-teaching" -->
        </div>
        <div id="instructor-teaching-panel" style="display: block;">Teaching</div>
      `;

      const panelMapping = {
        teaching: ['instructor-teaching-panel'],
        all: ['instructor-teaching-panel']
      };
      const allPanelIds = ['instructor-teaching-panel'];

      window.configureDashboardFilter(panelMapping, allPanelIds);

      // Should not throw when activeButton doesn't exist
      expect(() => window.filterDashboard('teaching')).not.toThrow();
    });

    it('should handle showing panels when visiblePanels includes them', () => {
      const panelMapping = {
        teaching: ['instructor-teaching-panel'],
        all: ['instructor-teaching-panel', 'instructor-assessment-panel']
      };
      const allPanelIds = ['instructor-teaching-panel', 'instructor-assessment-panel'];

      window.configureDashboardFilter(panelMapping, allPanelIds);

      // Test showing specific panel
      window.filterDashboard('teaching');
      expect(document.getElementById('instructor-teaching-panel').style.display).toBe('block');

      // Test showing all panels
      window.filterDashboard('all');
      expect(document.getElementById('instructor-teaching-panel').style.display).toBe('block');
      expect(document.getElementById('instructor-assessment-panel').style.display).toBe('block');
    });

    it('should handle hiding panels when visiblePanels does not include them', () => {
      const panelMapping = {
        teaching: ['instructor-teaching-panel'],
        all: ['instructor-teaching-panel', 'instructor-assessment-panel']
      };
      const allPanelIds = ['instructor-teaching-panel', 'instructor-assessment-panel'];

      window.configureDashboardFilter(panelMapping, allPanelIds);

      // Filter to teaching - should hide assessment panel
      window.filterDashboard('teaching');
      expect(document.getElementById('instructor-assessment-panel').style.display).toBe('none');
    });
  });
});

