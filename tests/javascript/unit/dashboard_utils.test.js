/**
 * Unit Tests for Dashboard Utilities
 *
 * Tests shared dashboard helper functions for loading/error/empty states
 * and timeline status derivation.
 */

const dashboardUtils = require('../../../static/dashboard_utils');

describe('dashboard_utils.js', () => {
  let container;

  beforeEach(() => {
    // Create a fresh container for each test
    document.body.innerHTML = '<div id="testContainer"></div>';
    container = document.getElementById('testContainer');
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  describe('setLoadingState', () => {
    test('displays loading spinner with message', () => {
      dashboardUtils.setLoadingState('testContainer', 'Loading data...');

      expect(container.querySelector('.spinner-border')).toBeTruthy();
      expect(container.textContent).toContain('Loading data...');
      expect(container.querySelector('.text-center')).toBeTruthy();
    });

    test('clears existing content', () => {
      container.innerHTML = '<div>Old content</div>';
      
      dashboardUtils.setLoadingState('testContainer', 'Loading...');

      expect(container.textContent).not.toContain('Old content');
      expect(container.textContent).toContain('Loading...');
    });

    test('handles missing container gracefully', () => {
      // Should not throw
      expect(() => {
        dashboardUtils.setLoadingState('nonexistent', 'Loading...');
      }).not.toThrow();
    });
  });

  describe('setErrorState', () => {
    test('displays error alert with message', () => {
      dashboardUtils.setErrorState('testContainer', 'Failed to load data');

      expect(container.querySelector('.alert-danger')).toBeTruthy();
      expect(container.textContent).toContain('Failed to load data');
      expect(container.querySelector('.fa-exclamation-triangle')).toBeTruthy();
    });

    test('clears existing content', () => {
      container.innerHTML = '<div>Old content</div>';
      
      dashboardUtils.setErrorState('testContainer', 'Error occurred');

      expect(container.textContent).not.toContain('Old content');
      expect(container.textContent).toContain('Error occurred');
    });

    test('handles missing container gracefully', () => {
      expect(() => {
        dashboardUtils.setErrorState('nonexistent', 'Error');
      }).not.toThrow();
    });
  });

  describe('setEmptyState', () => {
    test('displays empty state with message', () => {
      dashboardUtils.setEmptyState('testContainer', 'No data available');

      expect(container.querySelector('.fa-inbox')).toBeTruthy();
      expect(container.textContent).toContain('No data available');
      expect(container.querySelector('.text-center')).toBeTruthy();
    });

    test('clears existing content', () => {
      container.innerHTML = '<div>Old content</div>';
      
      dashboardUtils.setEmptyState('testContainer', 'Empty');

      expect(container.textContent).not.toContain('Old content');
      expect(container.textContent).toContain('Empty');
    });

    test('handles missing container gracefully', () => {
      expect(() => {
        dashboardUtils.setEmptyState('nonexistent', 'Empty');
      }).not.toThrow();
    });
  });

  describe('deriveTimelineStatus', () => {
    test('returns SCHEDULED when before start date', () => {
      const start = '2025-01-01';
      const end = '2025-06-01';
      const ref = new Date('2024-12-01');

      expect(dashboardUtils.deriveTimelineStatus(start, end, ref)).toBe('SCHEDULED');
    });

    test('returns ACTIVE when between start and end', () => {
      const start = '2024-01-01';
      const end = '2025-12-31';
      const ref = new Date('2024-06-01');

      expect(dashboardUtils.deriveTimelineStatus(start, end, ref)).toBe('ACTIVE');
    });

    test('returns PASSED when after end date', () => {
      const start = '2023-01-01';
      const end = '2023-06-01';
      const ref = new Date('2024-01-01');

      expect(dashboardUtils.deriveTimelineStatus(start, end, ref)).toBe('PASSED');
    });

    test('returns UNKNOWN for missing dates', () => {
      expect(dashboardUtils.deriveTimelineStatus(null, '2024-06-01')).toBe('UNKNOWN');
      expect(dashboardUtils.deriveTimelineStatus('2024-01-01', null)).toBe('UNKNOWN');
      expect(dashboardUtils.deriveTimelineStatus(null, null)).toBe('UNKNOWN');
    });

    test('uses current date as default reference', () => {
      const pastDate = '2020-01-01';
      const futureDate = '2030-12-31';

      // Without reference date, should use "now"
      const result = dashboardUtils.deriveTimelineStatus(pastDate, futureDate);
      expect(result).toBe('ACTIVE'); // Assuming tests run between 2020-2030
    });
  });

  describe('resolveTimelineStatus', () => {
    test('returns UNKNOWN for null/undefined record', () => {
      expect(dashboardUtils.resolveTimelineStatus(null)).toBe('UNKNOWN');
      expect(dashboardUtils.resolveTimelineStatus(undefined)).toBe('UNKNOWN');
    });

    test('uses direct status if available', () => {
      const record = { status: 'active', start_date: '2020-01-01', end_date: '2020-06-01' };
      expect(dashboardUtils.resolveTimelineStatus(record)).toBe('ACTIVE');
    });

    test('normalizes direct status to uppercase', () => {
      const record = { status: 'scheduled' };
      expect(dashboardUtils.resolveTimelineStatus(record)).toBe('SCHEDULED');
    });

    test('checks timeline_status field', () => {
      const record = { timeline_status: 'passed' };
      expect(dashboardUtils.resolveTimelineStatus(record)).toBe('PASSED');
    });

    test('checks term_status field', () => {
      const record = { term_status: 'active' };
      expect(dashboardUtils.resolveTimelineStatus(record)).toBe('ACTIVE');
    });

    test('derives ACTIVE from is_active flag', () => {
      const record = { is_active: true };
      expect(dashboardUtils.resolveTimelineStatus(record)).toBe('ACTIVE');
    });

    test('derives ACTIVE from active flag', () => {
      const record = { active: true };
      expect(dashboardUtils.resolveTimelineStatus(record)).toBe('ACTIVE');
    });

    test('derives status from start/end dates when no direct status', () => {
      const record = {
        start_date: '2020-01-01',
        end_date: '2020-06-01',
      };
      const ref = new Date('2024-01-01'); // After end date

      expect(dashboardUtils.resolveTimelineStatus(record, { referenceDate: ref })).toBe('PASSED');
    });

    test('uses custom startKeys option', () => {
      const record = {
        custom_start: '2024-01-01',
        custom_end: '2025-12-31',
      };
      const ref = new Date('2024-06-01');

      const result = dashboardUtils.resolveTimelineStatus(record, {
        startKeys: ['custom_start'],
        endKeys: ['custom_end'],
        referenceDate: ref,
      });

      expect(result).toBe('ACTIVE');
    });

    test('uses custom endKeys option', () => {
      const record = {
        begin: '2023-01-01',
        finish: '2023-06-01',
      };
      const ref = new Date('2024-01-01');

      const result = dashboardUtils.resolveTimelineStatus(record, {
        startKeys: ['begin'],
        endKeys: ['finish'],
        referenceDate: ref,
      });

      expect(result).toBe('PASSED');
    });

    test('tries multiple start keys in order', () => {
      const record = {
        term_start_date: '2024-01-01',
        end_date: '2025-12-31',
      };
      const ref = new Date('2024-06-01');

      // Should find term_start_date from default startKeys
      expect(dashboardUtils.resolveTimelineStatus(record, { referenceDate: ref })).toBe('ACTIVE');
    });

    test('tries multiple end keys in order', () => {
      const record = {
        start_date: '2023-01-01',
        term_end_date: '2023-06-01',
      };
      const ref = new Date('2024-01-01');

      // Should find term_end_date from default endKeys
      expect(dashboardUtils.resolveTimelineStatus(record, { referenceDate: ref })).toBe('PASSED');
    });

    test('returns UNKNOWN when date keys not found', () => {
      const record = {
        name: 'Test Record',
        some_other_field: 'value',
      };

      expect(dashboardUtils.resolveTimelineStatus(record)).toBe('UNKNOWN');
    });
  });
});
