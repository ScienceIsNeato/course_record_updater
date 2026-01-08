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
    clos: [
      {
        id: 'clo1',
        course: 'NURS101',
        clo_number: '1',
        description: 'Test CLO',
        status: 'active'
      }
    ],
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
      const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();

      await InstitutionDashboard.refresh();

      expect(consoleWarnSpy).toHaveBeenCalled();
      expect(showErrorSpy).toHaveBeenCalled();

      showErrorSpy.mockRestore();
      consoleWarnSpy.mockRestore();
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

      // Actions column removed - panels are display-only
      const sectionData = callArgs.data[0];
      expect(sectionData.status).toBeDefined();
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

      // Actions column removed - panels are display-only
      expect(sectionData.status).toBeDefined();
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
      // Actions column removed - panels are display-only
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
      expect(() => InstitutionDashboard.renderCourses([{ course_id: 'c1' }])).not.toThrow();
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

  describe('offerings rendering', () => {
    beforeEach(() => {
      setBody(`
        <div id="offeringManagementContainer"></div>
      `);
    });

    it('renders offerings table with course and term lookups', () => {
      const offerings = [
        {
          offering_id: 'off1',
          course_id: 'c1',
          term_id: 't1',
          sections: 2,
          enrollment: 50,
          status: 'active'
        },
        {
          offering_id: 'off2',
          course_id: 'c2',
          term_id: 't2',
          sections: 1,
          enrollment: 25,
          status: 'active'
        }
      ];

      const courses = [
        { course_id: 'c1', course_number: 'CS101', course_title: 'Intro to CS' },
        { course_id: 'c2', course_number: 'MATH201', course_title: 'Calculus' }
      ];

      const terms = [
        { term_id: 't1', name: 'Fall 2024' },
        { term_id: 't2', name: 'Spring 2025' }
      ];

      InstitutionDashboard.renderOfferings(offerings, courses, terms);

      expect(window.panelManager.createSortableTable).toHaveBeenCalled();
      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];

      expect(callArgs.id).toBe('institution-offerings-table');
      expect(callArgs.data).toHaveLength(2);
    });

    it('renders empty state when no offerings', () => {
      InstitutionDashboard.renderOfferings([], [], []);

      const container = document.getElementById('offeringManagementContainer');
      expect(container.innerHTML).toContain('No course offerings scheduled');
      expect(container.innerHTML).toContain('Add Offering');
    });

    it('handles missing container gracefully', () => {
      setBody('<div></div>'); // No offeringManagementContainer

      // Should not throw error
      expect(() => InstitutionDashboard.renderOfferings([{ offering_id: 'o1' }], [], [])).not.toThrow();
      expect(window.panelManager.createSortableTable).not.toHaveBeenCalled();
    });

    it('handles offerings with missing course/term data', () => {
      const offerings = [
        {
          offering_id: 'off1',
          course_id: 'unknown',
          term_id: 'unknown',
          sections: 0,
          enrollment: 0
        }
      ];

      InstitutionDashboard.renderOfferings(offerings, [], []);

      expect(window.panelManager.createSortableTable).toHaveBeenCalled();
      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];
      expect(callArgs.data).toHaveLength(1);
    });
  });

  describe('terms rendering', () => {
    beforeEach(() => {
      setBody(`
        <div id="termManagementContainer"></div>
      `);
    });

    it('renders terms table', () => {
      const terms = [
        {
          term_id: 't1',
          name: 'Fall 2024',
          start_date: '2024-08-01',
          end_date: '2024-12-15',
          active: true,
          offerings_count: 10
        },
        {
          term_id: 't2',
          name: 'Spring 2025',
          start_date: '2025-01-15',
          end_date: '2025-05-15',
          active: false,
          offerings_count: 0
        }
      ];

      InstitutionDashboard.renderTerms(terms);

      expect(window.panelManager.createSortableTable).toHaveBeenCalled();
      const callArgs = window.panelManager.createSortableTable.mock.calls[0][0];

      expect(callArgs.id).toBe('institution-terms-table');
      expect(callArgs.data).toHaveLength(2);
    });

    it('renders empty state when no terms', () => {
      InstitutionDashboard.renderTerms([]);

      const container = document.getElementById('termManagementContainer');
      expect(container.innerHTML).toContain('No terms defined');
      expect(container.innerHTML).toContain('Add Term');
    });

    it('handles missing container gracefully', () => {
      setBody('<div></div>'); // No termManagementContainer

      // Should not throw error
      expect(() => InstitutionDashboard.renderTerms([{ term_id: 't1' }])).not.toThrow();
      expect(window.panelManager.createSortableTable).not.toHaveBeenCalled();
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

    // Refresh button removed from UI - data auto-refreshes after mutations

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
      InstitutionDashboard.intervalId = setInterval(() => { }, 1000);
      const intervalId = InstitutionDashboard.intervalId;

      InstitutionDashboard.cleanup();

      expect(InstitutionDashboard.intervalId).toBeNull();
    });
  });

  describe('Action Handlers', () => {
    beforeEach(() => {
      // Set up a container with event delegation
      setBody(`
        <div id="courseSectionContainer"></div>
        <div id="courseManagementContainer"></div>
        <div id="programManagementContainer"></div>
      `);
    });

    it('handles send-reminder action clicks', () => {
      // Mock sendCourseReminder method
      const sendReminderSpy = jest.spyOn(InstitutionDashboard, 'sendCourseReminder').mockImplementation();

      // Initialize to set up event listeners FIRST
      InstitutionDashboard.init();

      // Create a button with reminder action
      const button = document.createElement('button');
      button.setAttribute('data-action', 'send-reminder');
      button.setAttribute('data-instructor-id', 'inst-123');
      button.setAttribute('data-course-id', 'course-456');
      button.setAttribute('data-instructor', 'Dr. Smith');
      button.setAttribute('data-course-number', 'CS101');

      const container = document.getElementById('courseSectionContainer');
      container.appendChild(button);

      // Dispatch a click event that bubbles
      const clickEvent = new MouseEvent('click', {
        bubbles: true,
        cancelable: true,
        view: window
      });
      button.dispatchEvent(clickEvent);

      // Verify send reminder was called with correct parameters
      expect(sendReminderSpy).toHaveBeenCalledWith('inst-123', 'course-456', 'Dr. Smith', 'CS101');

      sendReminderSpy.mockRestore();
    });

    it('handles edit-section action clicks', () => {
      // Mock handleEditSection method
      const editSectionSpy = jest.spyOn(InstitutionDashboard, 'handleEditSection').mockImplementation();

      // Initialize to set up event listeners FIRST
      InstitutionDashboard.init();

      // Create a button with edit-section action
      const button = document.createElement('button');
      button.setAttribute('data-action', 'edit-section');
      button.setAttribute('data-section-id', 'sect-789');

      const container = document.getElementById('courseSectionContainer');
      container.appendChild(button);

      // Dispatch a click event that bubbles
      const clickEvent = new MouseEvent('click', {
        bubbles: true,
        cancelable: true,
        view: window
      });
      button.dispatchEvent(clickEvent);

      // Verify edit section was called
      expect(editSectionSpy).toHaveBeenCalledWith(button);

      editSectionSpy.mockRestore();
    });

    it('handles edit-course action clicks', () => {
      // Mock handleEditCourse method
      const editCourseSpy = jest.spyOn(InstitutionDashboard, 'handleEditCourse').mockImplementation();

      // Create a button with edit-course action
      const button = document.createElement('button');
      button.setAttribute('data-action', 'edit-course');
      button.setAttribute('data-course-id', 'course-123');

      const container = document.getElementById('courseManagementContainer');
      container.appendChild(button);

      // Initialize to set up event listeners
      InstitutionDashboard.init();

      // Click the button
      button.click();

      // Verify edit course was called
      expect(editCourseSpy).toHaveBeenCalledWith(button);

      editCourseSpy.mockRestore();
    });

    it('handles delete-program action clicks', () => {
      // Mock global deleteProgram function
      window.deleteProgram = jest.fn();

      // Initialize to set up event listeners FIRST
      InstitutionDashboard.init();

      // Create a button with delete-program action
      const button = document.createElement('button');
      button.setAttribute('data-action', 'delete-program');
      button.setAttribute('data-program-id', 'prog-456');
      button.setAttribute('data-program-name', 'Computer Science');

      const container = document.getElementById('programManagementContainer');
      container.appendChild(button);

      // Dispatch a click event that bubbles
      const clickEvent = new MouseEvent('click', {
        bubbles: true,
        cancelable: true,
        view: window
      });
      button.dispatchEvent(clickEvent);

      // Verify delete program was called with correct parameters
      expect(window.deleteProgram).toHaveBeenCalledWith('prog-456', 'Computer Science');

      delete window.deleteProgram;
    });

    it('ignores clicks without action attribute', () => {
      // Mock all handler methods
      const sendReminderSpy = jest.spyOn(InstitutionDashboard, 'sendCourseReminder').mockImplementation();
      const editSectionSpy = jest.spyOn(InstitutionDashboard, 'handleEditSection').mockImplementation();

      // Create a button WITHOUT data-action attribute
      const button = document.createElement('button');
      button.setAttribute('data-course-id', 'course-123');

      const container = document.getElementById('courseSectionContainer');
      container.appendChild(button);

      // Initialize to set up event listeners
      InstitutionDashboard.init();

      // Click the button
      button.click();

      // Verify no handlers were called
      expect(sendReminderSpy).not.toHaveBeenCalled();
      expect(editSectionSpy).not.toHaveBeenCalled();

      sendReminderSpy.mockRestore();
      editSectionSpy.mockRestore();
    });

    it('handles send-reminder with missing parameters gracefully', () => {
      // Mock sendCourseReminder method
      const sendReminderSpy = jest.spyOn(InstitutionDashboard, 'sendCourseReminder').mockImplementation();

      // Create a button with incomplete data
      const button = document.createElement('button');
      button.setAttribute('data-action', 'send-reminder');
      button.setAttribute('data-instructor-id', 'inst-123');
      // Missing other required attributes

      const container = document.getElementById('courseSectionContainer');
      container.appendChild(button);

      // Initialize to set up event listeners
      InstitutionDashboard.init();

      // Click the button
      button.click();

      // Verify send reminder was NOT called due to missing parameters
      expect(sendReminderSpy).not.toHaveBeenCalled();

      sendReminderSpy.mockRestore();
    });

    it('handles delete-program with missing function gracefully', () => {
      // Ensure window.deleteProgram does NOT exist
      delete window.deleteProgram;

      // Create a button with delete-program action
      const button = document.createElement('button');
      button.setAttribute('data-action', 'delete-program');
      button.setAttribute('data-program-id', 'prog-456');
      button.setAttribute('data-program-name', 'Computer Science');

      const container = document.getElementById('programManagementContainer');
      container.appendChild(button);

      // Initialize to set up event listeners
      InstitutionDashboard.init();

      // Should not throw error when clicking
      expect(() => button.click()).not.toThrow();
    });
  });

  describe('Handler Function Details', () => {
    beforeEach(() => {
      setBody('<meta name="csrf-token" content="test-token">');
    });

    it('handleEditSection calls window.openEditSectionModal', () => {
      window.openEditSectionModal = jest.fn();

      const button = {
        dataset: {
          sectionId: 'sect-123',
          sectionData: JSON.stringify({ id: 'sect-123', name: 'Section A' })
        }
      };

      InstitutionDashboard.handleEditSection(button);

      expect(window.openEditSectionModal).toHaveBeenCalledWith(
        'sect-123',
        { id: 'sect-123', name: 'Section A' }
      );

      delete window.openEditSectionModal;
    });

    it('handleEditSection handles missing window function gracefully', () => {
      delete window.openEditSectionModal;

      const button = {
        dataset: {
          sectionId: 'sect-123',
          sectionData: JSON.stringify({ id: 'sect-123' })
        }
      };

      // Should not throw error
      expect(() => InstitutionDashboard.handleEditSection(button)).not.toThrow();
    });

    it('handleEditCourse calls window.openEditCourseModal', () => {
      window.openEditCourseModal = jest.fn();

      const button = {
        dataset: {
          courseId: 'course-456',
          courseData: JSON.stringify({ id: 'course-456', title: 'CS101' })
        }
      };

      InstitutionDashboard.handleEditCourse(button);

      expect(window.openEditCourseModal).toHaveBeenCalledWith(
        'course-456',
        { id: 'course-456', title: 'CS101' }
      );

      delete window.openEditCourseModal;
    });

    it('handleEditCourse handles missing window function gracefully', () => {
      delete window.openEditCourseModal;

      const button = {
        dataset: {
          courseId: 'course-456',
          courseData: JSON.stringify({ id: 'course-456' })
        }
      };

      // Should not throw error
      expect(() => InstitutionDashboard.handleEditCourse(button)).not.toThrow();
    });

    it('sendCourseReminder sends POST request on confirmation', async () => {
      global.confirm = jest.fn().mockReturnValue(true);
      global.alert = jest.fn();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true })
      });

      await InstitutionDashboard.sendCourseReminder('inst-1', 'course-1', 'Dr. Smith', 'CS101');

      expect(global.confirm).toHaveBeenCalledWith('Send assessment reminder to Dr. Smith for CS101?');
      expect(global.fetch).toHaveBeenCalledWith('/api/send-course-reminder', expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'X-CSRFToken': 'test-token'
        }),
        body: JSON.stringify({
          instructor_id: 'inst-1',
          course_id: 'course-1'
        })
      }));
      expect(global.alert).toHaveBeenCalledWith(expect.stringContaining('✅ Reminder sent'));

      delete global.confirm;
      delete global.alert;
    });

    it('sendCourseReminder returns early if user cancels confirmation', async () => {
      global.confirm = jest.fn().mockReturnValue(false);
      global.fetch = jest.fn();

      await InstitutionDashboard.sendCourseReminder('inst-1', 'course-1', 'Dr. Smith', 'CS101');

      expect(global.confirm).toHaveBeenCalled();
      expect(global.fetch).not.toHaveBeenCalled();

      delete global.confirm;
    });

    it('sendCourseReminder handles API error response', async () => {
      global.confirm = jest.fn().mockReturnValue(true);
      global.alert = jest.fn();
      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        json: jest.fn().mockResolvedValue({ error: 'Instructor not found' })
      });

      await InstitutionDashboard.sendCourseReminder('inst-1', 'course-1', 'Dr. Smith', 'CS101');

      expect(global.alert).toHaveBeenCalledWith('❌ Failed to send reminder: Instructor not found');

      delete global.confirm;
      delete global.alert;
    });

    it('sendCourseReminder handles fetch exception', async () => {
      global.confirm = jest.fn().mockReturnValue(true);
      global.alert = jest.fn();
      global.fetch = jest.fn().mockRejectedValue(new Error('Network error'));
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      await InstitutionDashboard.sendCourseReminder('inst-1', 'course-1', 'Dr. Smith', 'CS101');

      expect(consoleErrorSpy).toHaveBeenCalled();
      expect(global.alert).toHaveBeenCalledWith('❌ Failed to send reminder. Please try again.');

      consoleErrorSpy.mockRestore();
      delete global.confirm;
      delete global.alert;
    });

    it('sendCourseReminder handles missing CSRF token', async () => {
      setBody('<div></div>'); // No CSRF meta tag
      global.confirm = jest.fn().mockReturnValue(true);
      global.alert = jest.fn();
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({ success: true })
      });

      await InstitutionDashboard.sendCourseReminder('inst-1', 'course-1', 'Dr. Smith', 'CS101');

      expect(global.fetch).toHaveBeenCalledWith('/api/send-course-reminder', expect.objectContaining({
        headers: expect.objectContaining({
          'X-CSRFToken': null
        })
      }));

      delete global.confirm;
      delete global.alert;
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
      const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();

      await InstitutionDashboard.loadData();

      expect(consoleWarnSpy).toHaveBeenCalledWith(
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

describe('InstitutionDashboard Initialization', () => {
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

    require('../../../static/institution_dashboard');
    document.dispatchEvent(new Event('DOMContentLoaded'));
    jest.advanceTimersByTime(200);

    expect(consoleWarnSpy).toHaveBeenCalledWith(expect.stringContaining('Panel manager not initialized'));
  });
});
