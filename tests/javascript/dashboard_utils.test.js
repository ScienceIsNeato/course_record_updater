/**
 * Unit tests for dashboard_utils.js
 * 
 * Tests shared helper functions used across dashboard implementations
 */

// Load functions from dashboard_utils.js
const {
  setLoadingState,
  setErrorState,
  setEmptyState,
  deriveTimelineStatus,
  resolveTimelineStatus
} = require('../../static/dashboard_utils');

describe('Dashboard Utilities', () => {
  // Mock DOM elements
  let container;

  beforeEach(() => {
    // Create a fresh container for each test
    container = document.createElement('div');
    container.id = 'testContainer';
    document.body.appendChild(container);
  });

  describe('Status Helpers', () => {
    it('deriveTimelineStatus returns ACTIVE when reference is within range', () => {
      const status = deriveTimelineStatus('2024-01-01', '2024-12-31', new Date('2024-06-01'));
      expect(status).toBe('ACTIVE');
    });

    it('deriveTimelineStatus returns SCHEDULED when before start', () => {
      const status = deriveTimelineStatus('2024-05-01', '2024-06-01', new Date('2024-04-01'));
      expect(status).toBe('SCHEDULED');
    });

    it('resolveTimelineStatus honors direct status when provided', () => {
      const status = resolveTimelineStatus({ status: 'active' });
      expect(status).toBe('ACTIVE');
    });

    it('resolveTimelineStatus computes from start/end when status missing', () => {
      const record = { start_date: '2024-01-01', end_date: '2024-02-01' };
      const status = resolveTimelineStatus(record, { referenceDate: new Date('2024-03-01') });
      expect(status).toBe('PASSED');
    });
  });

  afterEach(() => {
    // Clean up DOM after each test
    document.body.removeChild(container);
  });

  describe('setLoadingState', () => {
    it('should display loading spinner with message', () => {
      setLoadingState('testContainer', 'Loading data...');

      expect(container.innerHTML).toContain('spinner-border');
      expect(container.innerHTML).toContain('Loading data...');
      expect(container.innerHTML).toContain('visually-hidden');
    });

    it('should handle non-existent container gracefully', () => {
      // Should not throw error
      expect(() => {
        setLoadingState('nonExistentContainer', 'Loading...');
      }).not.toThrow();
    });

    it('should use text-center and text-muted classes', () => {
      setLoadingState('testContainer', 'Please wait...');

      expect(container.innerHTML).toContain('text-center');
      expect(container.innerHTML).toContain('text-muted');
      expect(container.innerHTML).toContain('py-4');
    });

    it('should include role attribute for accessibility', () => {
      setLoadingState('testContainer', 'Loading...');

      expect(container.innerHTML).toContain('role="status"');
    });

    it('should escape HTML in message to prevent XSS', () => {
      const maliciousMessage = '<script>alert("xss")</script>';
      setLoadingState('testContainer', maliciousMessage);

      // Message should be escaped - check that script tag is NOT executable
      expect(container.querySelector('script')).toBeNull();
      expect(container.innerHTML).toContain('&lt;script&gt;');
    });
  });

  describe('setErrorState', () => {
    it('should display error alert with message', () => {
      setErrorState('testContainer', 'Failed to load data');

      expect(container.innerHTML).toContain('alert-danger');
      expect(container.innerHTML).toContain('Failed to load data');
      expect(container.innerHTML).toContain('fa-exclamation-triangle');
    });

    it('should handle non-existent container gracefully', () => {
      expect(() => {
        setErrorState('nonExistentContainer', 'Error message');
      }).not.toThrow();
    });

    it('should include alert role for accessibility', () => {
      setErrorState('testContainer', 'Error occurred');

      expect(container.innerHTML).toContain('role="alert"');
    });

    it('should include icon with proper spacing', () => {
      setErrorState('testContainer', 'Error message');

      expect(container.innerHTML).toContain('fas fa-exclamation-triangle');
      expect(container.innerHTML).toContain('me-2');
    });

    it('should escape HTML in error message to prevent XSS', () => {
      const maliciousMessage = '<img src=x onerror=alert("xss")>';
      setErrorState('testContainer', maliciousMessage);

      expect(container.querySelector('img')).toBeNull();
      expect(container.innerHTML).toContain('&lt;img');
    });
  });

  describe('setEmptyState', () => {
    it('should display empty state with message', () => {
      setEmptyState('testContainer', 'No items found');

      expect(container.innerHTML).toContain('text-center');
      expect(container.innerHTML).toContain('text-muted');
      expect(container.innerHTML).toContain('No items found');
    });

    it('should include inbox icon', () => {
      setEmptyState('testContainer', 'Nothing here');

      expect(container.innerHTML).toContain('fas fa-inbox');
      expect(container.innerHTML).toContain('fa-2x');
      expect(container.innerHTML).toContain('mb-3');
    });

    it('should handle non-existent container gracefully', () => {
      expect(() => {
        setEmptyState('nonExistentContainer', 'Empty');
      }).not.toThrow();
    });

    it('should wrap message in paragraph tag', () => {
      setEmptyState('testContainer', 'No data available');

      const paragraph = container.querySelector('p');
      expect(paragraph).not.toBeNull();
      expect(paragraph.textContent).toContain('No data available');
    });

    it('should escape HTML in message to prevent XSS', () => {
      const maliciousMessage = '<iframe src="evil.com"></iframe>';
      setEmptyState('testContainer', maliciousMessage);

      expect(container.querySelector('iframe')).toBeNull();
      expect(container.innerHTML).toContain('&lt;iframe');
    });
  });

  describe('Integration: State Transitions', () => {
    it('should correctly transition from loading to error state', () => {
      // Start with loading
      setLoadingState('testContainer', 'Loading...');
      expect(container.innerHTML).toContain('spinner-border');

      // Transition to error
      setErrorState('testContainer', 'Load failed');
      expect(container.innerHTML).not.toContain('spinner-border');
      expect(container.innerHTML).toContain('alert-danger');
      expect(container.innerHTML).toContain('Load failed');
    });

    it('should correctly transition from loading to empty state', () => {
      // Start with loading
      setLoadingState('testContainer', 'Loading items...');
      expect(container.innerHTML).toContain('spinner-border');

      // Transition to empty
      setEmptyState('testContainer', 'No items found');
      expect(container.innerHTML).not.toContain('spinner-border');
      expect(container.innerHTML).toContain('fa-inbox');
      expect(container.innerHTML).toContain('No items found');
    });

    it('should correctly transition from loading to success (manual content)', () => {
      // Start with loading
      setLoadingState('testContainer', 'Loading...');
      expect(container.innerHTML).toContain('spinner-border');

      // Simulate successful load - manually set content
      container.innerHTML = '<div class="success-content">Data loaded!</div>';
      expect(container.innerHTML).not.toContain('spinner-border');
      expect(container.innerHTML).toContain('success-content');
    });
  });

  describe('Module Exports', () => {
    it('should export functions for testing (if module.exports exists)', () => {
      // In Node.js/Jest environment, module.exports should work
      if (typeof module !== 'undefined' && module.exports) {
        const exports = require('../../static/dashboard_utils.js');
        expect(exports.setLoadingState).toBeDefined();
        expect(exports.setErrorState).toBeDefined();
        expect(exports.setEmptyState).toBeDefined();
      }
    });
  });
});
