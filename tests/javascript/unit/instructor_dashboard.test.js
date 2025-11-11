// Load dashboard utilities globally (simulates browser <script> tag)
const { setLoadingState, setErrorState, setEmptyState } = require('../../../static/dashboard_utils');
global.setLoadingState = setLoadingState;
global.setErrorState = setErrorState;
global.setEmptyState = setEmptyState;

const InstructorDashboard = require('../../../static/instructor_dashboard');
const { setBody } = require('../helpers/dom');

describe('InstructorDashboard', () => {
  beforeEach(() => {
    setBody(`
      <div id="instructorName"></div>
      <div id="instructorCourseCount"></div>
      <div id="instructorSectionCount"></div>
      <div id="instructorStudentCount"></div>
      <div id="instructorAssessmentProgress"></div>
      <div id="instructorLastUpdated"></div>
      <button id="instructorRefreshButton"></button>
      <div id="instructorTeachingContainer"></div>
      <div id="instructorAssessmentContainer"></div>
      <ul id="instructorActivityList"></ul>
      <div id="instructorSummaryContainer"></div>
    `);

    // Reset InstructorDashboard state
    InstructorDashboard.cache = null;
    InstructorDashboard.lastFetch = 0;

    window.panelManager = {
      createSortableTable: jest.fn(() => {
        const table = document.createElement('table');
        table.innerHTML = '<tbody></tbody>';
        return table;
      })
    };
  });

  const sampleData = {
    summary: { courses: 2, sections: 4, students: 120 },
    assessment_tasks: [
      { status: 'completed', course_number: 'BIO101', due_date: '2024-01-02' },
      { status: 'pending', course_number: 'CHEM201', due_date: '2024-01-03' }
    ],
    teaching_assignments: [
      { course_id: 'c1', course_number: 'BIO101', course_title: 'Biology', sections: [{ status: 'completed' }] }
    ],
    sections: [
      { course_id: 'c1', enrollment: 30, status: 'completed' }
    ],
    metadata: { last_updated: '2024-02-01T12:00:00Z' }
  };

  it('renders instructor metrics and tables', () => {
    InstructorDashboard.render(sampleData);

    expect(document.getElementById('instructorCourseCount').textContent).toBe('2');
    expect(document.getElementById('instructorAssessmentProgress').textContent).toBe('50%');
    expect(document.getElementById('instructorTeachingContainer').querySelector('table')).not.toBeNull();
    expect(document.getElementById('instructorLastUpdated').textContent).toContain('Last updated:');
  });

  it('shows error state for containers', () => {
    InstructorDashboard.showError('instructorTeachingContainer', 'Unable to load');
    expect(document.getElementById('instructorTeachingContainer').textContent).toContain('Unable to load');
  });

  it('handles different data scenarios', () => {
    // Test with minimal data
    const minimalData = {
      instructor_metrics: {
        course_count: 0,
        assessment_progress: 0
      },
      instructor_courses: [],
      metadata: { last_updated: '2024-02-01T12:00:00Z' }
    };

    InstructorDashboard.render(minimalData);

    expect(document.getElementById('instructorCourseCount').textContent).toBe('0');
    expect(document.getElementById('instructorAssessmentProgress').textContent).toBe('0%');
    expect(document.getElementById('instructorLastUpdated').textContent).toContain('Last updated:');
  });

  describe('data loading and refresh functionality', () => {
    beforeEach(() => {
      global.fetch = jest.fn();
      jest.useFakeTimers();
      jest.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
      global.fetch.mockRestore();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      console.error.mockRestore();
    });

    it('handles successful data loading and refresh', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: sampleData
        })
      });

      const renderSpy = jest.spyOn(InstructorDashboard, 'render');

      await InstructorDashboard.refresh();

      expect(fetch).toHaveBeenCalledWith('/api/dashboard/data', {
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        }
      });
      expect(renderSpy).toHaveBeenCalledWith(sampleData);

      renderSpy.mockRestore();
    });

    it('handles network errors during data loading', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'));

      const showErrorSpy = jest.spyOn(InstructorDashboard, 'showError');

      await InstructorDashboard.loadData();

      expect(showErrorSpy).toHaveBeenCalledWith('instructorTeachingContainer', 'Unable to load teaching assignments');
      expect(showErrorSpy).toHaveBeenCalledWith('instructorAssessmentContainer', 'Unable to load assessment tasks');
      expect(showErrorSpy).toHaveBeenCalledWith('instructorSummaryContainer', 'Unable to build summary');

      showErrorSpy.mockRestore();
    });

    it('handles API response errors', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          success: false,
          error: 'Access denied'
        })
      });

      const showErrorSpy = jest.spyOn(InstructorDashboard, 'showError');

      await InstructorDashboard.loadData();

      expect(showErrorSpy).toHaveBeenCalled();

      showErrorSpy.mockRestore();
    });

    it('handles malformed JSON responses', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => { throw new Error('Invalid JSON'); }
      });

      const showErrorSpy = jest.spyOn(InstructorDashboard, 'showError');

      await InstructorDashboard.loadData();

      expect(showErrorSpy).toHaveBeenCalled();

      showErrorSpy.mockRestore();
    });

    it('sets loading states correctly during non-silent operations', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: sampleData
        })
      });

      const setLoadingSpy = jest.spyOn(InstructorDashboard, 'setLoading');

      await InstructorDashboard.loadData({ silent: false });

      expect(setLoadingSpy).toHaveBeenCalledWith('instructorTeachingContainer', 'Loading teaching assignments...');
      expect(setLoadingSpy).toHaveBeenCalledWith('instructorAssessmentContainer', 'Loading assessment tasks...');
      expect(setLoadingSpy).toHaveBeenCalledWith('instructorSummaryContainer', 'Building summary...');

      setLoadingSpy.mockRestore();
    });

    it('skips loading states during silent operations', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: sampleData
        })
      });

      const setLoadingSpy = jest.spyOn(InstructorDashboard, 'setLoading');

      await InstructorDashboard.loadData({ silent: true });

      expect(setLoadingSpy).not.toHaveBeenCalled();

      setLoadingSpy.mockRestore();
    });
  });

  describe('initialization and event handling', () => {
    beforeEach(() => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, data: sampleData })
      });
      jest.useFakeTimers();
      jest.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
      global.fetch.mockRestore();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      console.error.mockRestore();
    });

    it('initializes with correct event listeners and intervals', () => {
      const loadDataSpy = jest.spyOn(InstructorDashboard, 'loadData');
      const setIntervalSpy = jest.spyOn(global, 'setInterval');
      const addEventListenerSpy = jest.spyOn(document, 'addEventListener');

      InstructorDashboard.init();

      // Check that initial loadData was called
      expect(loadDataSpy).toHaveBeenCalledWith();

      // Check that setInterval was called with correct parameters
      expect(setIntervalSpy).toHaveBeenCalledWith(
        expect.any(Function),
        5 * 60 * 1000 // refreshInterval
      );

      // Check that document visibility change listener was added
      expect(addEventListenerSpy).toHaveBeenCalledWith('visibilitychange', expect.any(Function));

      loadDataSpy.mockRestore();
      setIntervalSpy.mockRestore();
      addEventListenerSpy.mockRestore();
    });

    it('handles refresh button clicks', () => {
      const loadDataSpy = jest.spyOn(InstructorDashboard, 'loadData');

      InstructorDashboard.init();

      // Simulate refresh button click
      const refreshButton = document.getElementById('instructorRefreshButton');
      refreshButton.click();

      expect(loadDataSpy).toHaveBeenCalledWith({ silent: false });

      loadDataSpy.mockRestore();
    });

    it('handles visibility change events for auto-refresh', () => {
      const loadDataSpy = jest.spyOn(InstructorDashboard, 'loadData');
      
      // Set lastFetch to an old time to trigger refresh
      InstructorDashboard.lastFetch = Date.now() - (6 * 60 * 1000); // 6 minutes ago

      InstructorDashboard.init();

      // Simulate document becoming visible
      Object.defineProperty(document, 'hidden', {
        writable: true,
        value: false
      });

      const visibilityChangeEvent = new Event('visibilitychange');
      document.dispatchEvent(visibilityChangeEvent);

      expect(loadDataSpy).toHaveBeenCalledWith({ silent: true });

      loadDataSpy.mockRestore();
    });

    it('skips auto-refresh when lastFetch is recent', () => {
      const loadDataSpy = jest.spyOn(InstructorDashboard, 'loadData');
      
      // Set lastFetch to a recent time
      InstructorDashboard.lastFetch = Date.now() - (2 * 60 * 1000); // 2 minutes ago

      InstructorDashboard.init();

      // Simulate document becoming visible
      Object.defineProperty(document, 'hidden', {
        writable: true,
        value: false
      });

      const visibilityChangeEvent = new Event('visibilitychange');
      document.dispatchEvent(visibilityChangeEvent);

      // Should not call loadData for visibility change since lastFetch is recent
      // (but it will be called once for the initial init())
      expect(loadDataSpy).toHaveBeenCalledTimes(1);

      loadDataSpy.mockRestore();
    });
  });

  describe('cache and state management', () => {
    it('updates cache and lastFetch after successful data load', async () => {
      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: sampleData
        })
      });

      const initialLastFetch = InstructorDashboard.lastFetch;

      await InstructorDashboard.loadData();

      expect(InstructorDashboard.cache).toEqual(sampleData);
      expect(InstructorDashboard.lastFetch).toBeGreaterThan(initialLastFetch);
      expect(window.dashboardDataCache).toEqual(sampleData);

      global.fetch.mockRestore();
    });

    it('has correct initial state', () => {
      expect(InstructorDashboard.cache).toBeNull();
      expect(InstructorDashboard.refreshInterval).toBe(5 * 60 * 1000);
      expect(typeof InstructorDashboard.lastFetch).toBe('number');
    });
  });

  describe('loading and error state management', () => {
    it('sets loading state correctly', () => {
      InstructorDashboard.setLoading('instructorTeachingContainer', 'Loading...');
      
      const container = document.getElementById('instructorTeachingContainer');
      expect(container.innerHTML).toContain('Loading...');
      expect(container.innerHTML).toContain('spinner-border');
    });

    it('shows error state correctly', () => {
      InstructorDashboard.showError('instructorAssessmentContainer', 'Error occurred');
      
      const container = document.getElementById('instructorAssessmentContainer');
      expect(container.innerHTML).toContain('Error occurred');
      expect(container.innerHTML).toContain('fa-exclamation-triangle');
      expect(container.innerHTML).toContain('alert-danger');
    });

    it('handles empty state rendering', () => {
      const emptyMessage = InstructorDashboard.renderEmptyState('No data available', 'Refresh');
      
      expect(emptyMessage).toContain('No data available');
      expect(emptyMessage).toContain('Refresh');
      expect(emptyMessage).toContain('panel-empty');
    });
  });

  describe('branch coverage for conditional logic', () => {
    it('handles null/missing timestamp in updateLastUpdated', () => {
      InstructorDashboard.updateLastUpdated(null);
      const target = document.getElementById('instructorLastUpdated');
      expect(target.textContent).toContain('Last updated:');
      // Should show current date when timestamp is null
      expect(target.textContent).not.toBe('Last updated: Invalid Date');
    });

    it('handles missing elements gracefully in renderTeachingAssignments', () => {
      document.body.innerHTML = ''; // Remove all elements
      
      // Should not throw
      expect(() => InstructorDashboard.renderTeachingAssignments([])).not.toThrow();
    });

    it('handles missing elements gracefully in renderAssessmentTasks', () => {
      document.body.innerHTML = ''; // Remove all elements
      
      // Should not throw
      expect(() => InstructorDashboard.renderAssessmentTasks([])).not.toThrow();
    });

    it('handles missing elements gracefully in renderRecentActivity', () => {
      document.body.innerHTML = ''; // Remove all elements
      
      // Should not throw
      expect(() => InstructorDashboard.renderRecentActivity([])).not.toThrow();
    });

    it('handles missing elements gracefully in renderCourseSummary', () => {
      document.body.innerHTML = ''; // Remove all elements
      
      // Should not throw
      expect(() => InstructorDashboard.renderCourseSummary([], [])).not.toThrow();
    });

    it('handles missing elements gracefully in updateLastUpdated', () => {
      document.body.innerHTML = ''; // Remove lastUpdated element
      
      // Should not throw
      expect(() => InstructorDashboard.updateLastUpdated('2024-01-01T12:00:00Z')).not.toThrow();
    });

    it('handles zero assessment tasks correctly in updateHeader', () => {
      const dataWithNoTasks = {
        summary: { courses: 1, sections: 2, students: 50 },
        assessment_tasks: []
      };
      
      InstructorDashboard.updateHeader(dataWithNoTasks);
      expect(document.getElementById('instructorAssessmentProgress').textContent).toBe('0%');
    });

    it('identifies completed tasks with various status strings', () => {
      expect(InstructorDashboard.isTaskComplete('completed')).toBe(true);
      expect(InstructorDashboard.isTaskComplete('COMPLETED')).toBe(true);
      expect(InstructorDashboard.isTaskComplete('complete')).toBe(true);
      expect(InstructorDashboard.isTaskComplete('done')).toBe(true);
      expect(InstructorDashboard.isTaskComplete('DONE')).toBe(true);
      expect(InstructorDashboard.isTaskComplete(null)).toBe(false);
      expect(InstructorDashboard.isTaskComplete('pending')).toBe(false);
      expect(InstructorDashboard.isTaskComplete('in_progress')).toBe(false);
    });

    it('handles sections without courseId in renderCourseSummary', () => {
      setBody(`
        <div id="instructorSummaryContainer"></div>
      `);

      const assignments = [{
        course_id: 'c1',
        course_number: 'BIO101',
        course_title: 'Biology',
        sections: []
      }];
      
      const sections = [
        { enrollment: 30 }, // No course_id
        { course_id: null, enrollment: 20 } // Null course_id
      ];

      window.panelManager = {
        createSortableTable: jest.fn(() => {
          const table = document.createElement('table');
          return table;
        })
      };

      InstructorDashboard.renderCourseSummary(assignments, sections);
      
      // Should not throw and should skip sections without course_id
      const container = document.getElementById('instructorSummaryContainer');
      expect(container).not.toBeNull();
    });

    it('handles missing activityList element during silent load', async () => {
      document.body.innerHTML = ''; // Remove activityList
      
      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, data: sampleData })
      });

      // Should not throw
      await expect(InstructorDashboard.loadData({ silent: true })).resolves.not.toThrow();
      
      global.fetch.mockRestore();
    });

    it('handles missing activityList element during error', async () => {
      document.body.innerHTML = ''; // Remove activityList
      
      global.fetch = jest.fn().mockRejectedValueOnce(new Error('Network error'));
      jest.spyOn(console, 'error').mockImplementation(() => {});

      // Should not throw
      await expect(InstructorDashboard.loadData()).resolves.not.toThrow();
      
      global.fetch.mockRestore();
      console.error.mockRestore();
    });
  });
});
