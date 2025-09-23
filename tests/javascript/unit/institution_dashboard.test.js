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
});
