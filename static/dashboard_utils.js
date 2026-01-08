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
 * Standard loading state setter for dashboard containers
 *
 * @param {string} containerId - ID of the container element
 * @param {string} message - Loading message to display
 */
function setLoadingState(containerId, message) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = "";
  const wrapper = document.createElement("div");
  wrapper.className = "text-center text-muted py-4";

  const spinner = document.createElement("div");
  spinner.className = "spinner-border spinner-border-sm me-2";
  spinner.setAttribute("role", "status");
  const hiddenSpan = document.createElement("span");
  hiddenSpan.className = "visually-hidden";
  hiddenSpan.textContent = "Loading...";
  spinner.appendChild(hiddenSpan);

  wrapper.appendChild(spinner);
  wrapper.appendChild(document.createTextNode(message));
  container.appendChild(wrapper);
}

function setErrorState(containerId, message) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = "";
  const wrapper = document.createElement("div");
  wrapper.className = "alert alert-danger";
  wrapper.setAttribute("role", "alert");

  const icon = document.createElement("i");
  icon.className = "fas fa-exclamation-triangle me-2";

  wrapper.appendChild(icon);
  wrapper.appendChild(document.createTextNode(message));
  container.appendChild(wrapper);
}

function setEmptyState(containerId, message) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = "";
  const wrapper = document.createElement("div");
  wrapper.className = "text-center text-muted py-4";

  const icon = document.createElement("i");
  icon.className = "fas fa-inbox fa-2x mb-3";

  const p = document.createElement("p");
  p.textContent = message;

  wrapper.appendChild(icon);
  wrapper.appendChild(p);
  container.appendChild(wrapper);
}

// Export for use in other dashboard modules (for testing)
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    setLoadingState,
    setErrorState,
    setEmptyState,
  };
}
