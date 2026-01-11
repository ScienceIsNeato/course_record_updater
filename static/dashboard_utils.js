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

function parseDateInput(raw) {
  if (!raw) return null;
  const parsed = new Date(raw);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function deriveTimelineStatus(startDate, endDate, referenceDate = new Date()) {
  const start = parseDateInput(startDate);
  const end = parseDateInput(endDate);
  const ref = parseDateInput(referenceDate) || new Date();

  if (!start || !end) {
    return "UNKNOWN";
  }

  if (ref < start) {
    return "SCHEDULED";
  }
  if (ref > end) {
    return "PASSED";
  }
  return "ACTIVE";
}

function resolveTimelineStatus(record, options = {}) {
  if (!record) return "UNKNOWN";

  const {
    startKeys = ["start_date", "term_start_date"],
    endKeys = ["end_date", "term_end_date"],
    referenceDate = new Date(),
  } = options;

  const directStatus =
    record.status ||
    record.timeline_status ||
    record.term_status ||
    (record.is_active || record.active ? "ACTIVE" : null);

  if (directStatus) {
    return String(directStatus).toUpperCase();
  }

  const startCandidate = startKeys.find(
    (key) => record[key] !== undefined && record[key] !== null,
  );
  const endCandidate = endKeys.find(
    (key) => record[key] !== undefined && record[key] !== null,
  );

  return deriveTimelineStatus(
    startCandidate ? record[startCandidate] : undefined,
    endCandidate ? record[endCandidate] : undefined,
    referenceDate,
  ).toUpperCase();
}

// Export for use in other dashboard modules (for testing)
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    setLoadingState,
    setErrorState,
    setEmptyState,
    deriveTimelineStatus,
    resolveTimelineStatus,
  };
}
