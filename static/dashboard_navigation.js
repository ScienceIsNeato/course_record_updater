/**
 * Dashboard Navigation Filter - Shared across all dashboard templates
 *
 * Provides panel filtering functionality for dashboard navigation buttons.
 * Dynamically shows/hides panels based on the selected view and manages
 * active button states.
 *
 * Usage:
 *   Call configureDashboardFilter() with a mapping object that defines
 *   which panels should be visible for each view.
 */

/**
 * Configure and initialize dashboard filtering for a specific dashboard type.
 *
 * @param {Object} panelMapping - Maps view names to arrays of panel IDs
 *   Example: {
 *     'teaching': ['instructor-teaching-panel'],
 *     'all': ['instructor-teaching-panel', 'instructor-assessment-panel']
 *   }
 * @param {string[]} allPanelIds - Complete list of all panel IDs for this dashboard
 * @param {Object} [titleMapping] - Optional maps view names to page titles
 */
function configureDashboardFilter(panelMapping, allPanelIds, titleMapping) {
  /**
   * Filter dashboard panels based on the selected view.
   *
   * @param {string} view - The view to display (e.g., 'teaching', 'all')
   */
  function filterDashboard(view) {
    const visiblePanels = panelMapping[view] || panelMapping.all;

    // Scroll to top to ensure user notices the change
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Update page title if mapping provided
    if (titleMapping && titleMapping[view]) {
      const titleEl = document.getElementById('page-title-text');
      if (titleEl) {
        titleEl.textContent = titleMapping[view];
      }
    }

    // Show/hide panels based on current view
    allPanelIds.forEach(panelId => {
      const panel = document.getElementById(panelId);
      if (panel) {
        if (visiblePanels.includes(panelId)) {
          panel.style.display = 'block';
        } else {
          panel.style.display = 'none';
        }
      }
    });

    // Update active states on navigation buttons
    document.querySelectorAll('.navbar-nav button.nav-link').forEach(btn => {
      btn.classList.remove('active');
    });

    const activeButton = document.getElementById(`dashboard-${view === 'all' ? 'view-all' : view}`);
    if (activeButton) {
      activeButton.classList.add('active');
    }
  }

  // Initialize dashboard on page load - show all panels by default
  document.addEventListener('DOMContentLoaded', () => {
    filterDashboard('all');
  });

  // Expose filterDashboard globally for onclick handlers
  globalThis.filterDashboard = filterDashboard;
}

// Export for use in dashboard templates
globalThis.configureDashboardFilter = configureDashboardFilter;
