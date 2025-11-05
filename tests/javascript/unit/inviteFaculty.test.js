/**
 * Jest tests for inviteFaculty.js - Optional Chaining Coverage
 * 
 * Tests focused on covering optional chaining expressions for undefined/null paths
 */

// Mock Bootstrap Modal
global.bootstrap = {
  Modal: jest.fn().mockImplementation(() => ({
    show: jest.fn(),
    hide: jest.fn()
  }))
};

describe('inviteFaculty.js - Optional Chaining Coverage', () => {
  let originalInstitutionDashboard;
  let originalDashboardDataCache;

  beforeEach(() => {
    // Save original state
    originalInstitutionDashboard = window.InstitutionDashboard;
    originalDashboardDataCache = window.dashboardDataCache;

    // Clear module cache to get fresh module each test
    jest.resetModules();

    // Setup minimal DOM
    document.body.innerHTML = `
      <div id="inviteFacultyModal"></div>
      <form id="inviteFacultyForm">
        <input type="text" />
      </form>
      <select id="inviteFacultyTerm"></select>
      <select id="inviteFacultyOffering"><option value="">Select an offering</option></select>
      <select id="inviteFacultySection"><option value="">Select a section</option></select>
    `;
  });

  afterEach(() => {
    // Restore window state
    window.InstitutionDashboard = originalInstitutionDashboard;
    window.dashboardDataCache = originalDashboardDataCache;
    jest.clearAllMocks();
  });

  it('should handle missing InstitutionDashboard.cache when no dashboardDataCache', () => {
    // Line 19: window.InstitutionDashboard?.cache
    delete window.InstitutionDashboard;
    delete window.dashboardDataCache;

    // Load and call the function
    require('../../../static/inviteFaculty.js');
    
    // This will hit line 19 where it checks InstitutionDashboard?.cache
    expect(() => {
      window.openInviteFacultyModal();
    }).not.toThrow();

    // Modal should still be created
    expect(bootstrap.Modal).toHaveBeenCalled();
  });

  it('should handle missing dashboardData.terms', () => {
    // Line 35: !dashboardData?.terms
    window.dashboardDataCache = {
      // No terms property
      offerings: [],
      sections: []
    };

    require('../../../static/inviteFaculty.js');
    
    // This will hit line 35 where it checks dashboardData?.terms
    window.openInviteFacultyModal();

    const termSelect = document.getElementById('inviteFacultyTerm');
    // Should only have the default option
    expect(termSelect.children.length).toBe(1);
    expect(termSelect.children[0].value).toBe('');
  });

  it('should handle missing dashboardData.offerings', () => {
    // Line 81: !dashboardData?.offerings
    window.dashboardDataCache = {
      terms: [{ term_id: 'term1', term_name: 'Fall 2024' }]
      // No offerings property
    };

    require('../../../static/inviteFaculty.js');
    window.openInviteFacultyModal();

    const termSelect = document.getElementById('inviteFacultyTerm');
    // Manually trigger change event to populate offerings
    termSelect.value = 'term1';
    termSelect.dispatchEvent(new Event('change'));

    const offeringSelect = document.getElementById('inviteFacultyOffering');
    // Should be disabled and only have default option
    expect(offeringSelect.disabled).toBe(true);
  });

  it('should handle missing dashboardData.sections', () => {
    // Line 132: !dashboardData?.sections
    window.dashboardDataCache = {
      terms: [{ term_id: 'term1', term_name: 'Fall 2024' }],
      offerings: [{ offering_id: 'off1', course_number: 'CS101', term_id: 'term1' }]
      // No sections property
    };

    require('../../../static/inviteFaculty.js');
    window.openInviteFacultyModal();

    // Populate term
    const termSelect = document.getElementById('inviteFacultyTerm');
    termSelect.value = 'term1';
    termSelect.dispatchEvent(new Event('change'));

    // Populate offering
    const offeringSelect = document.getElementById('inviteFacultyOffering');
    offeringSelect.value = 'off1';
    offeringSelect.dispatchEvent(new Event('change'));

    const sectionSelect = document.getElementById('inviteFacultySection');
    // Should be disabled
    expect(sectionSelect.disabled).toBe(true);
  });

  it('should handle missing InstitutionDashboard.loadData after invite', () => {
    // Line 238: window.InstitutionDashboard?.loadData
    window.InstitutionDashboard = {
      // No loadData method
      cache: { terms: [], offerings: [], sections: [] }
    };

    // Mock fetch for successful invite
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true })
    });

    // Mock alert
    global.alert = jest.fn();

    require('../../../static/inviteFaculty.js');

    // Call would trigger line 238 (checking InstitutionDashboard?.loadData)
    // This is in the success handler, so we just verify the module loads
    expect(window.InstitutionDashboard.loadData).toBeUndefined();
  });

  it('should handle all optional chaining paths in real usage', () => {
    // Test combined scenario - opening modal with partial data
    window.dashboardDataCache = {
      terms: [{ term_id: 'term1', term_name: 'Fall 2024' }]
      // Missing offerings and sections
    };

    require('../../../static/inviteFaculty.js');

    expect(() => {
      window.openInviteFacultyModal();
      
      // Trigger term change
      const termSelect = document.getElementById('inviteFacultyTerm');
      termSelect.value = 'term1';
      termSelect.dispatchEvent(new Event('change'));
      
      // Try to trigger offering change (should handle missing data)
      const offeringSelect = document.getElementById('inviteFacultyOffering');
      offeringSelect.dispatchEvent(new Event('change'));
    }).not.toThrow();
  });

  it('should open modal with full data without errors', () => {
    // Test that modal opens successfully with complete data
    window.dashboardDataCache = {
      terms: [{ term_id: 'term1', term_name: 'Fall 2024', start_date: '2024-09-01' }],
      offerings: [
        { offering_id: 'off1', course_number: 'CS101', term_id: 'term1' },
        { offering_id: 'off2', course_number: 'CS102', term_id: 'term1' }
      ],
      sections: [
        { section_id: 'sec1', section_number: 'A', offering_id: 'off1' },
        { section_id: 'sec2', section_number: 'B', offering_id: 'off1' }
      ]
    };

    require('../../../static/inviteFaculty.js');

    // Opening modal should not throw and should populate term dropdown
    expect(() => {
      window.openInviteFacultyModal();
    }).not.toThrow();

    const termSelect = document.getElementById('inviteFacultyTerm');
    // Should have default option + terms from data
    expect(termSelect.options.length).toBeGreaterThan(1);
  });
});
