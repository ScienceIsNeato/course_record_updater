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

      await InstitutionDashboard.refresh();

      expect(showErrorSpy).toHaveBeenCalled();

      showErrorSpy.mockRestore();
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
});
