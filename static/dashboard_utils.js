/**
 * Shared Dashboard Utilities
 *
 * Common helper functions for all dashboard types to reduce code duplication.
 * Extracted from program_dashboard.js, instructor_dashboard.js, and institution_dashboard.js
 *
 * These utilities provide standard UI patterns for loading states, errors, and empty states
 * that are consistent across all dashboard implementations.
 */

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} str - String to escape
 * @returns {string} - Escaped string safe for HTML
 */
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Standard loading state setter for dashboard containers
 *
 * @param {string} containerId - ID of the container element
 * @param {string} message - Loading message to display
 */
function setLoadingState(containerId, message) {
  const container = document.getElementById(containerId);
  if (container) {
    // nosemgrep
    container.innerHTML = `
      <div class="text-center text-muted py-4">
        <div class="spinner-border spinner-border-sm me-2" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        ${escapeHtml(message)}
      </div>
    `;
  }
}

/**
 * Display error message in container
 *
 * @param {string} containerId - ID of the container element
 * @param {string} message - Error message to display
 */
function setErrorState(containerId, message) {
  const container = document.getElementById(containerId);
  if (container) {
    // nosemgrep
    container.innerHTML = `
      <div class="alert alert-danger" role="alert">
        <i class="fas fa-exclamation-triangle me-2"></i>
        ${escapeHtml(message)}
      </div>
    `;
  }
}

/**
 * Display empty state message in container
 *
 * @param {string} containerId - ID of the container element
 * @param {string} message - Empty state message to display
 */
function setEmptyState(containerId, message) {
  const container = document.getElementById(containerId);
  if (container) {
    // nosemgrep
    container.innerHTML = `
      <div class="text-center text-muted py-4">
        <i class="fas fa-inbox fa-2x mb-3"></i>
        <p>${escapeHtml(message)}</p>
      </div>
    `;
  }
}

// Export for use in other dashboard modules (for testing)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    setLoadingState,
    setErrorState,
    setEmptyState
  };
}
