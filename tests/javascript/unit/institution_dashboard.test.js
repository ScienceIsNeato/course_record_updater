// Load dashboard utilities globally (simulates browser <script> tag)
const { setLoadingState, setErrorState, setEmptyState } = require('../../../static/dashboard_utils');
global.setLoadingState = setLoadingState;
global.setErrorState = setErrorState;
global.setEmptyState = setEmptyState;

const InstitutionDashboard = require('../../../static/institution_dashboard');
const { setBody } = require('../helpers/dom');

describe('InstitutionDashboard', () => {
  beforeEach(() => {
    setBody(`
      <div id="institutionName"></div>
      <div id="currentTermName"></div>
      <div id="programCount"></div>
      <div id="courseCount"></div>
      <div id="facultyCount"></div>
      <div id="sectionCount"></div>
      <div id="institutionLastUpdated"></div>
      <button id="institutionRefreshButton"></button>
      <div id="programManagementContainer"></div>
      <div id="facultyOverviewContainer"></div>
      <div id="courseSectionContainer"></div>
      <div id="assessmentProgressContainer"></div>
    `);

    window.panelManager = {
      createSortableTable: jest.fn(config => {
        const table = document.createElement('table');
        table.setAttribute('data-table-id', config.id);
        table.innerHTML = '<tbody></tbody>';
        return table;
      })
    };
  });

  afterEach(() => {
    // Clean up any intervals
    if (InstitutionDashboard.intervalId) {
      clearInterval(InstitutionDashboard.intervalId);
      InstitutionDashboard.intervalId = null;
    }
    jest.clearAllTimers();
    jest.restoreAllMocks();
  });

  const sampleData = {
    summary: { programs: 2, courses: 5, faculty: 3, sections: 7 },
    institutions: [{ name: 'Example University' }],
    terms: [{ name: 'Fall 2025', active: true }],
    program_overview: [
      {
        program_name: 'Nursing',
        course_count: 3,
        assessment_progress: { completed: 5, total: 10, percent_complete: 50 }
      }
    ],
    programs: [{ id: 'p1', name: 'Nursing' }],
    faculty_assignments: [{ faculty_name: 'Jane Doe', program_id: 'p1', assignments: 2 }],
    faculty: [{ id: 'f1', name: 'Jane Doe', course_count: 2 }],
    sections: [
      {
        section_id: 's1',
        course_id: 'c1',
        instructor_name: 'Jane Doe',
        enrollment: 30,
        status: 'scheduled'
      }
    ],
    courses: [{ course_id: 'c1', course_title: 'Biology 101', course_number: 'BIO101' }],
    metadata: { last_updated: '2024-01-01T00:00:00Z' }
  };

  it('renders summary metrics and tables', () => {
    InstitutionDashboard.render(sampleData);

    expect(document.getElementById('institutionName').textContent).toBe('Example University');
    expect(document.getElementById('programCount').textContent).toBe('2');
    expect(document.getElementById('assessmentProgressContainer').querySelector('table')).not.toBeNull();
    expect(window.panelManager.createSortableTable).toHaveBeenCalled();
    expect(document.getElementById('institutionLastUpdated').textContent).toContain('Last updated:');
  });

  it('shows loading and error states', () => {
    InstitutionDashboard.setLoading('programManagementContainer', 'Loading programs...');
    expect(document.getElementById('programManagementContainer').textContent).toContain('Loading programs');

    InstitutionDashboard.showError('programManagementContainer', 'Failed');
    expect(document.getElementById('programManagementContainer').textContent).toContain('Failed');
  });

  describe('comprehensive institution dashboard functionality', () => {
    it('handles refresh functionality', async () => {
      const sampleData = {
        institutions: [
          {
            name: 'Test University',
            id: 'test-uni'
          }
        ],
        summary: {
          programs: 1,
          courses: 10,
          faculty: 5,
          sections: 15
        },
        program_overview: [
          { program_name: 'CS', course_count: 10, student_count: 200, completion_rate: 85 }
        ],
        assessment_progress: [
          { program_name: 'CS', completed: 15, pending: 5, overdue: 2 }
        ],
        terms: [
          { name: 'Fall 2024', active: true }
        ],
        metadata: { last_updated: '2024-02-01T12:00:00Z' }
      };

      global.fetch = jest.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: sampleData
        })
      });

      const renderSpy = jest.spyOn(InstitutionDashboard, 'render');

      await InstitutionDashboard.refresh();

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

    it('handles refresh errors', async () => {
      global.fetch = jest.fn().mockRejectedValueOnce(new Error('Network error'));

      const showErrorSpy = jest.spyOn(InstitutionDashboard, 'showError');
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      await InstitutionDashboard.refresh();

      expect(consoleErrorSpy).toHaveBeenCalled();
      expect(showErrorSpy).toHaveBeenCalled();

      showErrorSpy.mockRestore();
      consoleErrorSpy.mockRestore();
      // Reset fetch mock for subsequent tests
      global.fetch = jest.fn();
    });

    it('handles different loading states', () => {
      // Test multiple containers
      InstitutionDashboard.setLoading('programManagementContainer', 'Loading programs...');
      InstitutionDashboard.setLoading('assessmentProgressContainer', 'Loading assessments...');

      expect(document.getElementById('programManagementContainer').textContent).toContain('Loading programs');
      expect(document.getElementById('assessmentProgressContainer').textContent).toContain('Loading assessments');
    });

    it('handles basic render functionality', () => {
      const basicData = {
        institutions: [
          {
            name: 'Basic University',
            id: 'basic-uni'
          }
        ],
        summary: {
          programs: 1,
          courses: 5,
          faculty: 3,
          sections: 8
        },
        program_overview: [
          { program_name: 'CS', course_count: 5, student_count: 100, completion_rate: 80 }
        ],
        assessment_progress: [
          { program_name: 'CS', completed: 10, pending: 2, overdue: 1 }
        ],
        terms: [
          { name: 'Spring 2024', active: true }
        ],
        metadata: { last_updated: '2024-02-01T12:00:00Z' }
      };

      // Should not throw error
      expect(() => InstitutionDashboard.render(basicData)).not.toThrow();
    });

    it('handles empty data gracefully', () => {
      const emptyData = {
        institutions: [],
        summary: {
          programs: 0,
          courses: 0,
          faculty: 0,
          sections: 0
        },
        program_overview: [],
        assessment_progress: [],
        terms: [],
        metadata: {}
      };

      // Should not throw error
      expect(() => InstitutionDashboard.render(emptyData)).not.toThrow();
    });

    it('tests initialization functionality', () => {
      // Test that init function exists and can be called
      expect(typeof InstitutionDashboard.init).toBe('function');
      
      // Should not throw error when called
      expect(() => InstitutionDashboard.init()).not.toThrow();
    });

    it('tests cache functionality', () => {
      // Test that cache property exists
      expect(InstitutionDashboard.hasOwnProperty('cache')).toBe(true);
      expect(InstitutionDashboard.hasOwnProperty('lastFetch')).toBe(true);
      expect(InstitutionDashboard.hasOwnProperty('refreshInterval')).toBe(true);
    });
  });

  describe('section rendering with instructor details', () => {
    beforeEach(() => {
      setBody(`
        <div id="courseSectionContainer"></div>
      `);
    });

    it('renders reminder button when instructor has email', () => {
      const sections = [
        {
          section_id: 's1',
          section_number: '001',
          course_id: 'c1',
          instructor_id: 'inst1',
          instructor_name: 'Dr. Smith',
          instructor_email: 'smith@test.edu',
          enrollment: 30,
          status: 'active'
        }
      ];

      const courses = [
        {
          course_id: 'c1',
          course_number: 'CS101',
          course_title: 'Intro to CS'
        }
      ];

      InstitutionDashboard.renderSections(sections, courses, []);

      const container = document.getElementById('courseSectionContainer');
      expect(container).not.toBeNull();
      expect(window.panelManager.createSortableTable).toHaveBeenCalled();

      // Verify the table was created with section data
      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];
      expect(callArgs.data).toHaveLength(1);
      
      // Verify action buttons include reminder button with data-action attribute
      const sectionData = callArgs.data[0];
      expect(sectionData.actions).toContain('btn-outline-secondary');
      expect(sectionData.actions).toContain('data-action="send-reminder"');
      expect(sectionData.actions).toContain('data-instructor-id="inst1"');
      expect(sectionData.actions).toContain('Dr. Smith');
    });

    it('does not render reminder button when instructor lacks email', () => {
      const sections = [
        {
          section_id: 's2',
          section_number: '002',
          course_id: 'c1',
          instructor_id: 'inst2',
          instructor_name: 'Dr. Jones',
          // No instructor_email
          enrollment: 25,
          status: 'scheduled'
        }
      ];

      const courses = [
        {
          course_id: 'c1',
          course_number: 'CS102',
          course_title: 'Data Structures'
        }
      ];

      InstitutionDashboard.renderSections(sections, courses, []);

      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];
      const sectionData = callArgs.data[0];
      
      // Should have Edit button with data-action attribute (not onclick)
      expect(sectionData.actions).toContain('data-action="edit-section"');
      expect(sectionData.actions).not.toContain('send-reminder');
    });
  });

  describe('course rendering', () => {
    beforeEach(() => {
      setBody(`
        <div id="courseManagementContainer"></div>
      `);
    });

    it('renders course table with action buttons', () => {
      const courses = [
        {
          course_id: 'c1',
          course_number: 'BIO101',
          course_title: 'Introduction to Biology',
          department: 'Biology',
          credit_hours: 3,
          active: true
        },
        {
          course_id: 'c2',
          course_number: 'CHEM202',
          course_title: 'Organic Chemistry',
          department: 'Chemistry',
          credit_hours: 4,
          active: true
        }
      ];

      InstitutionDashboard.renderCourses(courses);

      expect(window.panelManager.createSortableTable).toHaveBeenCalled();
      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];
      
      expect(callArgs.id).toBe('institution-courses-table');
      expect(callArgs.data).toHaveLength(2);
      
      // Verify course data structure
      const course1 = callArgs.data[0];
      expect(course1.number).toBe('BIO101');
      expect(course1.title).toBe('Introduction to Biology');
      expect(course1.credits).toBe('3');
      expect(course1.department).toBe('Biology');
      expect(course1.actions).toContain('data-course-id="c1"');
    });

    it('renders empty state when no courses', () => {
      InstitutionDashboard.renderCourses([]);

      const container = document.getElementById('courseManagementContainer');
      expect(container.innerHTML).toContain('No courses found');
      expect(container.innerHTML).toContain('Add Course');
    });

    it('handles missing container gracefully', () => {
      setBody('<div></div>'); // No courseManagementContainer
      
      // Should not throw error
      expect(() => InstitutionDashboard.renderCourses([{course_id: 'c1'}])).not.toThrow();
      expect(window.panelManager.createSortableTable).not.toHaveBeenCalled();
    });

    it('handles courses with missing optional fields', () => {
      const courses = [
        {
          course_id: 'c1',
          course_number: 'MATH101'
          // Missing title, department, credit_hours
        }
      ];

      InstitutionDashboard.renderCourses(courses);

      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];
      const courseData = callArgs.data[0];
      
      // Should use defaults for missing fields
      expect(courseData.number).toBe('MATH101');
      expect(courseData.title).toBe('-'); // Default dash
      expect(courseData.department).toBe('-'); // Default dash
    });
  });

  describe('program rendering', () => {
    beforeEach(() => {
      setBody(`
        <div id="programManagementContainer"></div>
      `);
    });

    it('renders program table with data', () => {
      const programOverview = [
        {
          program_name: 'Computer Science',
          course_count: 10,
          student_count: 200
        },
        {
          program_name: 'Biology',
          course_count: 8,
          student_count: 150
        }
      ];

      const rawPrograms = [
        { id: 'p1', name: 'Computer Science', code: 'CS' },
        { id: 'p2', name: 'Biology', code: 'BIO' }
      ];

      InstitutionDashboard.renderPrograms(programOverview, rawPrograms);

      expect(window.panelManager.createSortableTable).toHaveBeenCalled();
      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];
      
      expect(callArgs.id).toBe('institution-programs-table');
      expect(callArgs.data).toHaveLength(2);
    });

    it('renders empty state when no programs', () => {
      InstitutionDashboard.renderPrograms([], []);

      const container = document.getElementById('programManagementContainer');
      expect(container.innerHTML).toContain('No programs found');
    });
  });

  describe('faculty rendering', () => {
    beforeEach(() => {
      setBody(`
        <div id="facultyOverviewContainer"></div>
      `);
    });

    it('renders faculty table with assignment counts', () => {
      const assignments = [
        {
          user_id: 'f1',
          full_name: 'Dr. Smith',
          program_ids: ['p1'],
          course_count: 3,
          section_count: 5,
          enrollment: 120
        },
        {
          user_id: 'f2',
          full_name: 'Prof. Johnson',
          program_ids: ['p1'],
          course_count: 2,
          section_count: 3,
          enrollment: 75
        }
      ];

      const fallbackFaculty = [];

      InstitutionDashboard.renderFaculty(assignments, fallbackFaculty);

      expect(window.panelManager.createSortableTable).toHaveBeenCalled();
      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];
      
      expect(callArgs.id).toBe('institution-faculty-table');
      expect(callArgs.data).toHaveLength(2);
      
      const faculty1 = callArgs.data[0];
      expect(faculty1.name).toBe('Dr. Smith');
      expect(faculty1.courses).toBe('3');
    });

    it('renders empty state when no faculty', () => {
      InstitutionDashboard.renderFaculty([], []);

      const container = document.getElementById('facultyOverviewContainer');
      expect(container.innerHTML).toContain('No faculty assigned yet');
    });
  });

  describe('assessment rendering', () => {
    beforeEach(() => {
      setBody(`
        <div id="assessmentProgressContainer"></div>
      `);
    });

    it('renders assessment table', () => {
      const programOverview = [
        {
          program_name: 'Computer Science',
          assessment_progress: {
            completed: 15,
            total: 20,
            percent_complete: 75
          }
        },
        {
          program_name: 'Biology',
          assessment_progress: {
            completed: 8,
            total: 12,
            percent_complete: 67
          }
        }
      ];

      InstitutionDashboard.renderAssessment(programOverview);

      expect(window.panelManager.createSortableTable).toHaveBeenCalled();
      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];
      
      expect(callArgs.data).toHaveLength(2);
      
      const prog1 = callArgs.data[0];
      expect(prog1.program).toBe('Computer Science');
    });

    it('handles empty assessment data', () => {
      InstitutionDashboard.renderAssessment([]);

      const container = document.getElementById('assessmentProgressContainer');
      expect(container.innerHTML).toContain('No assessment data available');
    });
  });

  describe('Initialization and Event Handlers', () => {
    beforeEach(() => {
      jest.useFakeTimers();
      global.fetch = jest.fn();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it('init() sets up visibility change listener', async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true, data: sampleData })
      };
      global.fetch.mockResolvedValue(mockResponse);

      // Spy on loadData instead of counting fetch calls
      const loadDataSpy = jest.spyOn(InstitutionDashboard, 'loadData');

      InstitutionDashboard.init();
      await Promise.resolve(); // Let initial loadData complete

      // Clear interval to avoid interference
      clearInterval(InstitutionDashboard.intervalId);
      
      // Reset the spy after init
      loadDataSpy.mockClear();

      // Fast-forward past refresh interval
      InstitutionDashboard.lastFetch = Date.now() - (6 * 60 * 1000);
      
      // Simulate document becoming visible (triggers load)
      Object.defineProperty(document, 'hidden', { value: false, writable: true });
      document.dispatchEvent(new Event('visibilitychange'));

      await Promise.resolve();

      // Verify loadData was called with silent: true
      expect(loadDataSpy).toHaveBeenCalledWith({ silent: true });
    });

    it('init() sets up refresh button click listener', async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true, data: sampleData })
      };
      global.fetch.mockResolvedValue(mockResponse);

      InstitutionDashboard.init();
      await Promise.resolve(); // Let initial loadData complete

      const refreshButton = document.getElementById('institutionRefreshButton');
      refreshButton.click();

      await Promise.resolve();

      // Initial load + button click = 2 calls
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('init() sets up auto-refresh interval', async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true, data: sampleData })
      };
      global.fetch.mockResolvedValue(mockResponse);

      InstitutionDashboard.init();
      await Promise.resolve();

      // Fast-forward past refresh interval (5 minutes)
      jest.advanceTimersByTime(5 * 60 * 1000);
      await Promise.resolve();

      // Initial + one interval refresh
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('init() sets up cleanup listeners for beforeunload', () => {
      const cleanupSpy = jest.spyOn(InstitutionDashboard, 'cleanup');

      InstitutionDashboard.init();

      window.dispatchEvent(new Event('beforeunload'));

      expect(cleanupSpy).toHaveBeenCalled();
    });

    it('init() sets up cleanup listeners for pagehide', () => {
      const cleanupSpy = jest.spyOn(InstitutionDashboard, 'cleanup');

      InstitutionDashboard.init();

      window.dispatchEvent(new Event('pagehide'));

      expect(cleanupSpy).toHaveBeenCalled();
    });

    it('cleanup() clears the interval', () => {
      InstitutionDashboard.intervalId = setInterval(() => {}, 1000);
      const intervalId = InstitutionDashboard.intervalId;

      InstitutionDashboard.cleanup();

      expect(InstitutionDashboard.intervalId).toBeNull();
    });
  });

  describe('Data Loading', () => {
    beforeEach(() => {
      global.fetch = jest.fn();
    });

    it('loadData() makes fetch request to correct endpoint', async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true, data: sampleData })
      };
      global.fetch.mockResolvedValue(mockResponse);

      await InstitutionDashboard.loadData();

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/dashboard/data',
        expect.objectContaining({
          credentials: 'include',
          headers: expect.objectContaining({
            Accept: 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
          })
        })
      );
    });

    it('loadData() updates cache and renders on success', async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true, data: sampleData })
      };
      global.fetch.mockResolvedValue(mockResponse);

      const renderSpy = jest.spyOn(InstitutionDashboard, 'render');

      await InstitutionDashboard.loadData();

      expect(InstitutionDashboard.cache).toEqual(sampleData);
      expect(window.dashboardDataCache).toEqual(sampleData);
      expect(renderSpy).toHaveBeenCalledWith(sampleData);
    });

    it('loadData() shows loading states when not silent', async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true, data: sampleData })
      };
      global.fetch.mockResolvedValue(mockResponse);

      const setLoadingSpy = jest.spyOn(InstitutionDashboard, 'setLoading');

      await InstitutionDashboard.loadData({ silent: false });

      expect(setLoadingSpy).toHaveBeenCalledWith('programManagementContainer', 'Loading programs...');
      expect(setLoadingSpy).toHaveBeenCalledWith('facultyOverviewContainer', 'Loading faculty...');
    });

    it('loadData() does not show loading states when silent', async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true, data: sampleData })
      };
      global.fetch.mockResolvedValue(mockResponse);

      const setLoadingSpy = jest.spyOn(InstitutionDashboard, 'setLoading');

      await InstitutionDashboard.loadData({ silent: true });

      expect(setLoadingSpy).not.toHaveBeenCalled();
    });

    it('loadData() handles fetch errors gracefully', async () => {
      global.fetch.mockRejectedValue(new Error('Network error'));
      const showErrorSpy = jest.spyOn(InstitutionDashboard, 'showError');
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      await InstitutionDashboard.loadData();

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Institution dashboard load error:',
        expect.any(Error)
      );
      expect(showErrorSpy).toHaveBeenCalledWith('programManagementContainer', 'Unable to load program data');
      expect(showErrorSpy).toHaveBeenCalledWith('facultyOverviewContainer', 'Unable to load faculty data');
    });

    it('loadData() handles non-ok HTTP responses', async () => {
      const mockResponse = {
        ok: false,
        json: jest.fn().mockResolvedValue({ success: false, error: 'Unauthorized' })
      };
      global.fetch.mockResolvedValue(mockResponse);

      const showErrorSpy = jest.spyOn(InstitutionDashboard, 'showError');

      await InstitutionDashboard.loadData();

      expect(showErrorSpy).toHaveBeenCalled();
    });

    it('refresh() calls loadData with silent=false', async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true, data: sampleData })
      };
      global.fetch.mockResolvedValue(mockResponse);

      // Spy on loadData but don't replace implementation
      const loadDataSpy = jest.spyOn(InstitutionDashboard, 'loadData');

      await InstitutionDashboard.refresh();

      expect(loadDataSpy).toHaveBeenCalledWith({ silent: false });
      
      loadDataSpy.mockRestore();
    });
  });
});
