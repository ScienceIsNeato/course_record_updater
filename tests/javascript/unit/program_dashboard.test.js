// Load dashboard utilities globally (simulates browser <script> tag)
const { setLoadingState, setErrorState, setEmptyState } = require('../../../static/dashboard_utils');
global.setLoadingState = setLoadingState;
global.setErrorState = setErrorState;
global.setEmptyState = setEmptyState;

const ProgramDashboard = require('../../../static/program_dashboard');
const { setBody } = require('../helpers/dom');

describe('ProgramDashboard', () => {
  beforeAll(() => {
    jest.useFakeTimers();
  });

  beforeEach(() => {
    setBody(`
      <div id="programAdminTitle"></div>
      <div id="programCoursesContainer"></div>
      <div id="programFacultyContainer"></div>
      <div id="programCloContainer"></div>
      <div id="programAssessmentContainer"></div>
    `);

    // Reset ProgramDashboard state
    ProgramDashboard.cache = null;
    ProgramDashboard.lastFetch = 0;

    window.panelManager = {
      createSortableTable: jest.fn(() => {
        const table = document.createElement('table');
        table.innerHTML = '<tbody></tbody>';
        return table;
      })
    };
  });

  const sampleData = {
    summary: { courses: 4, faculty: 5, students: 200, sections: 10 },
    programs: [{ id: 'p1', name: 'Engineering' }],
    courses: [
      {
        course_id: 'c1',
        course_number: 'ENGR101',
        course_title: 'Intro Engineering',
        outcomes: [{ label: 'Outcome A', status: 'met' }]
      }
    ],
    sections: [{ course_id: 'c1', enrollment: 40, status: 'completed' }],
    faculty_assignments: [{ instructor_name: 'Alex', assignments: 2, course_load: 3 }],
    program_overview: [
      {
        program_name: 'Engineering',
        course_count: 4,
        assessment_progress: { completed: 8, total: 10, percent_complete: 80 }
      }
    ],
    metadata: { last_updated: '2024-03-05T08:00:00Z' }
  };

  it('renders program metrics and tables', () => {
    ProgramDashboard.render(sampleData);

    const result = document.getElementById('programAssessmentContainer').querySelector('table');
    expect(result).not.toBeNull();
  });

  it('loadData success renders and sets cache', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: sampleData })
    });

    await ProgramDashboard.loadData();
    expect(global.fetch).toHaveBeenCalled();
    expect(ProgramDashboard.cache).toEqual(sampleData);
  });

  it('loadData failure calls setErrorState', async () => {
    const errorSpy = jest.spyOn(global, 'setErrorState');
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ error: 'boom' })
    });
    await ProgramDashboard.loadData();
    expect(errorSpy).toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it('scheduleRefresh sets interval and cleanup clears it', () => {
    const clearIntervalSpy = jest.spyOn(global, 'clearInterval');
    const loadDataSpy = jest.spyOn(ProgramDashboard, 'loadData').mockResolvedValue();

    ProgramDashboard.init(); // This sets intervalId via setInterval
    ProgramDashboard.cleanup();

    expect(clearIntervalSpy).toHaveBeenCalled();
    clearIntervalSpy.mockRestore();
    loadDataSpy.mockRestore();
  });

  it('handles null and undefined programs in assessment results', () => {
    const dataWithNullPrograms = {
      ...sampleData,
      program_overview: [
        {
          program_name: 'Engineering',
          program_summaries: [
            { program_name: 'Valid Program' },
            null,  // null program
            {},   // program without program_name
            undefined  // undefined program
          ],
          course_count: 4,
          assessment_progress: { completed: 8, total: 10, percent_complete: 80 }
        }
      ]
    };

    ProgramDashboard.render(dataWithNullPrograms);
    // Should render without crashing and filter out null/undefined
    expect(document.getElementById('programAssessmentContainer').querySelector('table')).not.toBeNull();
  });

  it('sets loading and error states appropriately', () => {
    ProgramDashboard.setLoading('programCoursesContainer', 'Loading courses...');
    expect(document.getElementById('programCoursesContainer').textContent).toContain('Loading courses');

    ProgramDashboard.showError('programCoursesContainer', 'No data');
    expect(document.getElementById('programCoursesContainer').textContent).toContain('No data');
  });

  describe('data loading and refresh functionality', () => {
    beforeEach(() => {
      global.fetch = jest.fn();
      jest.useFakeTimers();
      jest.spyOn(console, 'error').mockImplementation(() => { });
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

      const renderSpy = jest.spyOn(ProgramDashboard, 'render');

      await ProgramDashboard.refresh();

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

      const showErrorSpy = jest.spyOn(ProgramDashboard, 'showError');

      await ProgramDashboard.loadData();

      expect(showErrorSpy).toHaveBeenCalledWith('programCoursesContainer', 'Unable to load course data');
      expect(showErrorSpy).toHaveBeenCalledWith('programFacultyContainer', 'Unable to load faculty data');
      expect(showErrorSpy).toHaveBeenCalledWith('programCloContainer', 'Unable to load learning outcomes');
      expect(showErrorSpy).toHaveBeenCalledWith('programAssessmentContainer', 'Unable to load assessment results');

      showErrorSpy.mockRestore();
    });

    it('handles API response errors', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          success: false,
          error: 'Unauthorized access'
        })
      });

      const showErrorSpy = jest.spyOn(ProgramDashboard, 'showError');

      await ProgramDashboard.loadData();

      expect(showErrorSpy).toHaveBeenCalled();

      showErrorSpy.mockRestore();
    });

    it('handles malformed JSON responses', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => { throw new Error('Invalid JSON'); }
      });

      const showErrorSpy = jest.spyOn(ProgramDashboard, 'showError');

      await ProgramDashboard.loadData();

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

      const setLoadingSpy = jest.spyOn(ProgramDashboard, 'setLoading');

      await ProgramDashboard.loadData({ silent: false });

      expect(setLoadingSpy).toHaveBeenCalledWith('programCoursesContainer', 'Loading courses...');
      expect(setLoadingSpy).toHaveBeenCalledWith('programFacultyContainer', 'Loading faculty assignments...');
      expect(setLoadingSpy).toHaveBeenCalledWith('programCloContainer', 'Loading learning outcomes...');
      expect(setLoadingSpy).toHaveBeenCalledWith('programAssessmentContainer', 'Loading assessment results...');

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

      const setLoadingSpy = jest.spyOn(ProgramDashboard, 'setLoading');

      await ProgramDashboard.loadData({ silent: true });

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
      jest.spyOn(console, 'error').mockImplementation(() => { });
    });

    afterEach(() => {
      global.fetch.mockRestore();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      console.error.mockRestore();
    });

    it('initializes with correct event listeners and intervals', () => {
      const loadDataSpy = jest.spyOn(ProgramDashboard, 'loadData');
      const setIntervalSpy = jest.spyOn(global, 'setInterval');
      const addEventListenerSpy = jest.spyOn(document, 'addEventListener');

      ProgramDashboard.init();

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

    // Refresh button removed from UI - data auto-refreshes after mutations

    it('handles visibility change events for auto-refresh', () => {
      const loadDataSpy = jest.spyOn(ProgramDashboard, 'loadData');

      // Set lastFetch to an old time to trigger refresh
      ProgramDashboard.lastFetch = Date.now() - (6 * 60 * 1000); // 6 minutes ago

      ProgramDashboard.init();

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
      const loadDataSpy = jest.spyOn(ProgramDashboard, 'loadData');

      // Set lastFetch to a recent time
      ProgramDashboard.lastFetch = Date.now() - (2 * 60 * 1000); // 2 minutes ago

      ProgramDashboard.init();

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

      const initialLastFetch = ProgramDashboard.lastFetch;

      await ProgramDashboard.loadData();

      expect(ProgramDashboard.cache).toEqual(sampleData);
      expect(ProgramDashboard.lastFetch).toBeGreaterThan(initialLastFetch);
      expect(window.dashboardDataCache).toEqual(sampleData);

      global.fetch.mockRestore();
    });

    it('has correct initial state', () => {
      expect(ProgramDashboard.cache).toBeNull();
      expect(ProgramDashboard.refreshInterval).toBe(5 * 60 * 1000);
      expect(typeof ProgramDashboard.lastFetch).toBe('number');
    });
  });
});

describe('ProgramDashboard Initialization', () => {
  beforeEach(() => {
    jest.resetModules();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('should warn if panelManager is missing', () => {
    delete global.panelManager;
    delete window.panelManager;
    const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();

    require('../../../static/program_dashboard');
    document.dispatchEvent(new Event('DOMContentLoaded'));
    jest.advanceTimersByTime(200);

    expect(consoleWarnSpy).toHaveBeenCalledWith(expect.stringContaining('Panel manager not initialized'));
  });
});
