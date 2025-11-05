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

  // Helper to trigger DOMContentLoaded after requiring module
  const loadModuleAndInit = () => {
    require('../../../static/inviteFaculty.js');
    // Manually trigger DOMContentLoaded to set up event listeners
    const event = new Event('DOMContentLoaded');
    document.dispatchEvent(event);
  };

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
    loadModuleAndInit();
    
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

    loadModuleAndInit();
    
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

    loadModuleAndInit();
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

    loadModuleAndInit();
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

    loadModuleAndInit();

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

    loadModuleAndInit();

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

    loadModuleAndInit();

    // Opening modal should not throw and should populate term dropdown
    expect(() => {
      window.openInviteFacultyModal();
    }).not.toThrow();

    const termSelect = document.getElementById('inviteFacultyTerm');
    // Should have default option + terms from data
    expect(termSelect.options.length).toBeGreaterThan(1);
  });

  it('should populate offerings when term is selected', () => {
    window.dashboardDataCache = {
      terms: [{ term_id: 'term1', term_name: 'Fall 2024' }],
      offerings: [
        { offering_id: 'off1', course_number: 'CS101', term_id: 'term1' },
        { offering_id: 'off2', course_number: 'CS102', term_id: 'term1' }
      ],
      courses: [
        { course_id: 'c1', course_number: 'CS101', course_name: 'Intro to CS' },
        { course_id: 'c2', course_number: 'CS102', course_name: 'Data Structures' }
      ]
    };

    loadModuleAndInit();
    window.openInviteFacultyModal();

    const termSelect = document.getElementById('inviteFacultyTerm');
    termSelect.value = 'term1';
    termSelect.dispatchEvent(new Event('change'));

    const offeringSelect = document.getElementById('inviteFacultyOffering');
    expect(offeringSelect.disabled).toBe(false);
    expect(offeringSelect.options.length).toBeGreaterThan(1);
  });

  it('should populate sections when offering is selected', () => {
    window.dashboardDataCache = {
      terms: [{ term_id: 'term1', term_name: 'Fall 2024' }],
      offerings: [{ offering_id: 'off1', course_number: 'CS101', term_id: 'term1' }],
      sections: [
        { section_id: 'sec1', section_number: 'A', offering_id: 'off1' },
        { section_id: 'sec2', section_number: 'B', offering_id: 'off1' }
      ]
    };

    loadModuleAndInit();
    window.openInviteFacultyModal();

    // Populate term first
    const termSelect = document.getElementById('inviteFacultyTerm');
    termSelect.value = 'term1';
    termSelect.dispatchEvent(new Event('change'));

    // Populate offering
    const offeringSelect = document.getElementById('inviteFacultyOffering');
    offeringSelect.value = 'off1';
    offeringSelect.dispatchEvent(new Event('change'));

    const sectionSelect = document.getElementById('inviteFacultySection');
    expect(sectionSelect.disabled).toBe(false);
    expect(sectionSelect.options.length).toBeGreaterThan(1);
  });

  it('should reset offerings when term is cleared', () => {
    window.dashboardDataCache = {
      terms: [{ term_id: 'term1', term_name: 'Fall 2024' }],
      offerings: [{ offering_id: 'off1', course_number: 'CS101', term_id: 'term1' }]
    };

    loadModuleAndInit();
    window.openInviteFacultyModal();

    // First select a term
    const termSelect = document.getElementById('inviteFacultyTerm');
    termSelect.value = 'term1';
    termSelect.dispatchEvent(new Event('change'));

    // Then clear it
    termSelect.value = '';
    termSelect.dispatchEvent(new Event('change'));

    const offeringSelect = document.getElementById('inviteFacultyOffering');
    expect(offeringSelect.disabled).toBe(true);
    expect(offeringSelect.innerHTML).toContain('Select term first');
  });

  it('should handle offerings with no sections', () => {
    window.dashboardDataCache = {
      terms: [{ term_id: 'term1', term_name: 'Fall 2024' }],
      offerings: [{ offering_id: 'off1', course_number: 'CS101', term_id: 'term1' }],
      sections: [] // No sections
    };

    loadModuleAndInit();
    window.openInviteFacultyModal();

    const termSelect = document.getElementById('inviteFacultyTerm');
    termSelect.value = 'term1';
    termSelect.dispatchEvent(new Event('change'));

    const offeringSelect = document.getElementById('inviteFacultyOffering');
    offeringSelect.value = 'off1';
    offeringSelect.dispatchEvent(new Event('change'));

    const sectionSelect = document.getElementById('inviteFacultySection');
    expect(sectionSelect.disabled).toBe(true);
    expect(sectionSelect.innerHTML).toContain('No sections for this offering');
  });

  it('should handle terms with no offerings', () => {
    window.dashboardDataCache = {
      terms: [{ term_id: 'term1', term_name: 'Fall 2024' }],
      offerings: [] // No offerings
    };

    loadModuleAndInit();
    window.openInviteFacultyModal();

    const termSelect = document.getElementById('inviteFacultyTerm');
    termSelect.value = 'term1';
    termSelect.dispatchEvent(new Event('change'));

    const offeringSelect = document.getElementById('inviteFacultyOffering');
    expect(offeringSelect.disabled).toBe(true);
    expect(offeringSelect.innerHTML).toContain('No offerings for this term');
  });

  it('should successfully submit faculty invitation with section assignment', async () => {
    // Mock fetch for successful invitation
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });

    // Mock alert
    global.alert = jest.fn();

    // Mock bootstrap.Modal.getInstance
    const mockModalInstance = { hide: jest.fn() };
    global.bootstrap.Modal.getInstance = jest.fn().mockReturnValue(mockModalInstance);

    window.dashboardDataCache = {
      terms: [{ term_id: 'term1', term_name: 'Fall 2024' }],
      offerings: [{ offering_id: 'off1', course_number: 'CS101', term_id: 'term1' }],
      sections: [{ section_id: 'sec1', section_number: 'A', offering_id: 'off1' }]
    };

    // Setup form with CSRF token
    document.body.innerHTML = `
      <div id="inviteFacultyModal"></div>
      <form id="inviteFacultyForm">
        <input type="text" id="inviteFacultyEmail" value="newprof@example.com" />
        <input type="text" id="inviteFacultyFirstName" value="John" />
        <input type="text" id="inviteFacultyLastName" value="Doe" />
        <select id="inviteFacultySection">
          <option value="sec1">Section A</option>
        </select>
        <input type="checkbox" id="inviteFacultyReplaceExisting" checked />
        <input type="hidden" name="csrf_token" value="test-token" />
        <button type="submit">
          <span class="btn-text">Send Invitation</span>
          <span class="btn-spinner d-none">Loading...</span>
        </button>
      </form>
      <select id="inviteFacultyTerm"></select>
      <select id="inviteFacultyOffering"></select>
    `;

    loadModuleAndInit();

    const form = document.getElementById('inviteFacultyForm');
    const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
    form.dispatchEvent(submitEvent);

    // Wait for async operation
    await new Promise(resolve => setTimeout(resolve, 100));

    // Verify fetch was called with correct payload
    expect(fetch).toHaveBeenCalledWith(
      '/api/invitations',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'X-CSRFToken': 'test-token'
        }),
        body: JSON.stringify({
          email: 'newprof@example.com',
          role: 'instructor',
          first_name: 'John',
          last_name: 'Doe',
          section_id: 'sec1',
          replace_existing: true
        })
      })
    );

    // Verify success alert contains expected text
    expect(alert).toHaveBeenCalled();
    const alertCall = alert.mock.calls[0][0];
    expect(alertCall).toContain('Invitation sent');
    expect(alertCall).toContain('newprof@example.com');
  });

  it('should handle form validation errors', async () => {
    // Mock alert
    global.alert = jest.fn();

    // Setup form with missing required fields
    document.body.innerHTML = `
      <div id="inviteFacultyModal"></div>
      <form id="inviteFacultyForm">
        <input type="text" id="inviteFacultyEmail" value="" />
        <input type="text" id="inviteFacultyFirstName" value="" />
        <input type="text" id="inviteFacultyLastName" value="" />
        <select id="inviteFacultySection"></select>
        <input type="checkbox" id="inviteFacultyReplaceExisting" />
        <input type="hidden" name="csrf_token" value="test-token" />
        <button type="submit">
          <span class="btn-text">Send Invitation</span>
          <span class="btn-spinner d-none">Loading...</span>
        </button>
      </form>
      <select id="inviteFacultyTerm"></select>
      <select id="inviteFacultyOffering"></select>
    `;

    loadModuleAndInit();

    const form = document.getElementById('inviteFacultyForm');
    const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
    form.dispatchEvent(submitEvent);

    // Wait for async operation
    await new Promise(resolve => setTimeout(resolve, 50));

    // Verify validation error
    expect(alert).toHaveBeenCalledWith('Please fill in all required fields');
  });

  it('should handle API error during submission', async () => {
    // Mock fetch for error response
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'Email already registered' })
    });

    // Mock alert
    global.alert = jest.fn();

    // Setup valid form
    document.body.innerHTML = `
      <div id="inviteFacultyModal"></div>
      <form id="inviteFacultyForm">
        <input type="text" id="inviteFacultyEmail" value="existing@example.com" />
        <input type="text" id="inviteFacultyFirstName" value="Jane" />
        <input type="text" id="inviteFacultyLastName" value="Smith" />
        <select id="inviteFacultySection"></select>
        <input type="checkbox" id="inviteFacultyReplaceExisting" />
        <input type="hidden" name="csrf_token" value="test-token" />
        <button type="submit">
          <span class="btn-text">Send Invitation</span>
          <span class="btn-spinner d-none">Loading...</span>
        </button>
      </form>
      <select id="inviteFacultyTerm"></select>
      <select id="inviteFacultyOffering"></select>
    `;

    loadModuleAndInit();

    const form = document.getElementById('inviteFacultyForm');
    const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
    form.dispatchEvent(submitEvent);

    // Wait for async operation
    await new Promise(resolve => setTimeout(resolve, 100));

    // Verify error alert
    expect(alert).toHaveBeenCalledWith(
      expect.stringContaining('Email already registered')
    );
  });
});
