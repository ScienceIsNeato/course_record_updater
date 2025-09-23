const ProgramDashboard = require('../../../static/program_dashboard');
const { setBody } = require('../helpers/dom');

describe('ProgramDashboard', () => {
  beforeEach(() => {
    setBody(`
      <div id="programAdminTitle"></div>
      <div id="programCourseCount"></div>
      <div id="programFacultyCount"></div>
      <div id="programStudentCount"></div>
      <div id="programSectionCount"></div>
      <div id="programLastUpdated"></div>
      <button id="programRefreshButton"></button>
      <div id="programCoursesContainer"></div>
      <div id="programFacultyContainer"></div>
      <div id="programCloContainer"></div>
      <div id="programAssessmentContainer"></div>
    `);

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

    expect(document.getElementById('programCourseCount').textContent).toBe('4');
    expect(document.getElementById('programAssessmentContainer').querySelector('table')).not.toBeNull();
    expect(document.getElementById('programLastUpdated').textContent).toContain('Last updated:');
  });

  it('sets loading and error states appropriately', () => {
    ProgramDashboard.setLoading('programCoursesContainer', 'Loading courses...');
    expect(document.getElementById('programCoursesContainer').textContent).toContain('Loading courses');

    ProgramDashboard.showError('programCoursesContainer', 'No data');
    expect(document.getElementById('programCoursesContainer').textContent).toContain('No data');
  });
});
