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
});
