/**
 * Panel-Based UI JavaScript
 * Handles panel interactions, sorting, stats, and focus mode
 *
 * TODO: Add comprehensive UAT test cases for panel functionality including:
 * - Panel expand/collapse behavior
 * - Interactive stat previews and data loading
 * - Sortable table functionality across all columns
 * - Focus mode toggle and panel isolation
 * - Cross-browser compatibility testing
 * - Mobile responsiveness and touch interactions
 */

// Secure ID generation using crypto API when available
// Counter for fallback uniqueness guarantee
let idCounter = 0;

function generateSecureId(prefix = "id") {
  if (globalThis.crypto?.getRandomValues) {
    const array = new Uint32Array(1);
    globalThis.crypto.getRandomValues(array);
    return `${prefix}-${Date.now()}-${array[0]}`;
  }

  // Fallback for older browsers - use timestamp, performance counter, and monotonic counter
  // Avoids Math.random() to address SonarCloud security concerns
  const timestamp = Date.now();
  const performanceNow = globalThis.performance?.now
    ? globalThis.performance.now()
    : 0;
  const counter = ++idCounter; // Monotonic counter guarantees uniqueness

  // Create unique ID using timestamp, performance counter, and monotonic counter
  // The counter ensures uniqueness even for rapid successive calls
  const entropy = Math.floor(performanceNow * 1000) + counter;
  return `${prefix}-${timestamp}-${entropy}`;
}

class PanelManager {
  constructor() {
    this.panels = new Map();
    this.sortStates = new Map();
    this.focusedPanel = null;
    this.init();
  }

  init() {
    this.initializePanels();
    this.initializeSortableTables();
    this.bindEvents();
  }

  /**
   * Initialize all panels on the page
   */
  initializePanels() {
    const panels = document.querySelectorAll(".dashboard-panel");
    panels.forEach((panel) => {
      const panelId = panel.id || generateSecureId("panel");
      panel.id = panelId;

      const header = panel.querySelector(".panel-header");
      const content = panel.querySelector(".panel-content");
      const toggle = panel.querySelector(".panel-toggle");

      if (header && content && toggle) {
        this.panels.set(panelId, {
          element: panel,
          header,
          content,
          toggle,
          collapsed: content.classList.contains("collapsed"),
        });

        // Set initial state
        this.updatePanelState(panelId);
      }
    });
  }

  /**
   * Initialize sortable tables
   */
  initializeSortableTables() {
    const tables = document.querySelectorAll(".panel-table");
    tables.forEach((table) => {
      const tableId = table.id || generateSecureId("table");
      table.id = tableId;

      const headers = table.querySelectorAll("th.sortable");
      headers.forEach((header, index) => {
        const sortKey = header.dataset.sort || index;
        this.sortStates.set(`${tableId}-${sortKey}`, {
          table,
          header,
          column: index,
          direction: null, // null, 'asc', 'desc'
        });
      });
    });
  }

  /**
   * Bind all event listeners
   */
  bindEvents() {
    // Panel toggle events
    document.addEventListener("click", (e) => {
      const target =
        e.target instanceof Element ? e.target : e.target.parentElement;
      if (target?.closest?.(".panel-header")) {
        const panel = target.closest(".dashboard-panel");
        if (panel && !target.closest(".panel-actions")) {
          this.togglePanel(panel.id);
        }
      }

      // Table sorting events
      if (target?.closest?.("th.sortable")) {
        const header = target.closest("th.sortable");
        const table = header.closest(".panel-table");
        const sortKey =
          header.dataset.sort ||
          Array.from(header.parentElement.children).indexOf(header);
        this.sortTable(`${table.id}-${sortKey}`);
      }

      // Panel focus events
      if (target?.closest?.(".panel-title") && e.detail === 2) {
        // Double click
        const panel = target.closest(".dashboard-panel");
        if (panel) {
          this.focusPanel(panel.id);
        }
      }
    });

    // Keyboard events
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.focusedPanel) {
        this.unfocusPanel();
      }
    });
  }

  /**
   * Toggle panel collapse state
   */
  togglePanel(panelId) {
    const panel = this.panels.get(panelId);
    if (!panel) return;

    panel.collapsed = !panel.collapsed;
    this.updatePanelState(panelId);
  }

  /**
   * Update panel visual state
   */
  updatePanelState(panelId) {
    const panel = this.panels.get(panelId);
    if (!panel) return;

    if (panel.collapsed) {
      panel.content.classList.add("collapsed");
      panel.toggle.classList.add("collapsed");
      panel.toggle.innerHTML = "▶"; // nosemgrep
    } else {
      panel.content.classList.remove("collapsed");
      panel.toggle.classList.remove("collapsed");
      panel.toggle.innerHTML = "▼"; // nosemgrep
    }
  }

  /**
   * Sort table by column
   */
  sortTable(sortStateId) {
    const sortState = this.sortStates.get(sortStateId);
    if (!sortState) return;

    // Update sort direction
    if (sortState.direction === null || sortState.direction === "desc") {
      sortState.direction = "asc";
    } else {
      sortState.direction = "desc";
    }

    // Clear other sort states for this table
    this.sortStates.forEach((state, id) => {
      if (state.table === sortState.table && id !== sortStateId) {
        state.direction = null;
        state.header.classList.remove("sort-asc", "sort-desc");
      }
    });

    // Update header classes
    sortState.header.classList.remove("sort-asc", "sort-desc");
    sortState.header.classList.add(`sort-${sortState.direction}`);

    // Sort the table
    this.performTableSort(sortState);
  }

  /**
   * Perform the actual table sorting
   */
  performTableSort(sortState) {
    const tbody = sortState.table.querySelector("tbody");
    if (!tbody) return;

    const rows = Array.from(tbody.querySelectorAll("tr"));
    const columnIndex = sortState.column;

    rows.sort((a, b) => {
      const aValue = this.getCellValue(a.cells[columnIndex]);
      const bValue = this.getCellValue(b.cells[columnIndex]);

      if (sortState.direction === "asc") {
        return aValue.localeCompare(bValue, undefined, {
          numeric: true,
          sensitivity: "base",
        });
      } else {
        return bValue.localeCompare(aValue, undefined, {
          numeric: true,
          sensitivity: "base",
        });
      }
    });

    // Re-append sorted rows
    rows.forEach((row) => tbody.appendChild(row));
  }

  /**
   * Get cell value for sorting
   */
  getCellValue(cell) {
    // Check for data-sort attribute first
    if (cell.dataset.sort) {
      return cell.dataset.sort;
    }

    // Get text content, stripping HTML
    let value = cell.textContent || cell.innerText || "";
    value = value.trim();

    // Handle special cases
    if (value.includes("/")) {
      // Handle fractions like "4/6"
      const parts = value.split("/");
      if (parts.length === 2) {
        const numerator = Number.parseInt(parts[0]);
        const denominator = Number.parseInt(parts[1]);
        if (
          !Number.isNaN(numerator) &&
          !Number.isNaN(denominator) &&
          denominator > 0
        ) {
          return (numerator / denominator).toString();
        }
      }
    }

    return value;
  }

  /**
   * Focus a panel (full screen mode)
   */
  focusPanel(panelId) {
    const panel = this.panels.get(panelId);
    if (!panel) return;

    this.focusedPanel = panelId;
    panel.element.classList.add("panel-focused");
    document.body.style.overflow = "hidden";

    // Add breadcrumb navigation
    const breadcrumb = document.createElement("div");
    breadcrumb.className = "breadcrumb-nav";
    // nosemgrep
    breadcrumb.innerHTML = `
            <a href="#" onclick="panelManager.unfocusPanel(); return false;">Dashboard</a>
            <span class="breadcrumb-separator">›</span>
            <span>${panel.header.querySelector(".panel-title").textContent}</span>
        `;
    panel.element.insertBefore(breadcrumb, panel.header);
  }

  /**
   * Exit panel focus mode
   */
  unfocusPanel() {
    if (!this.focusedPanel) return;

    const panel = this.panels.get(this.focusedPanel);
    if (panel) {
      panel.element.classList.remove("panel-focused");
      const breadcrumb = panel.element.querySelector(".breadcrumb-nav");
      if (breadcrumb) {
        breadcrumb.remove();
      }
    }

    document.body.style.overflow = "";
    this.focusedPanel = null;
  }

  /**
   * Utility method to create a new panel
   */
  createPanel(config) {
    const panel = document.createElement("div");
    panel.className = "dashboard-panel fade-in";
    panel.id = config.id;
    // nosemgrep
    panel.innerHTML = `
            <div class="panel-header">
                <h5 class="panel-title">
                    <span class="panel-icon">${config.icon}</span>
                    ${config.title}
                </h5>
                <div class="panel-actions">
                    ${
                      config.actions
                        ?.map(
                          (action) => `
                        <button class="btn btn-sm btn-outline-primary" onclick="${action.onclick}">
                            ${action.icon} ${action.label}
                        </button>
                    `,
                        )
                        .join("") || ""
                    }
                </div>
                <button class="panel-toggle">▼</button>
            </div>
            <div class="panel-content ${config.collapsed ? "collapsed" : ""}">
                ${config.content}
            </div>
        `;

    return panel;
  }

  /**
   * Utility method to create a sortable table
   */
  createSortableTable(config) {
    const table = document.createElement("table");
    table.className = "table panel-table";
    table.id = config.id;

    const headerRow = config.columns
      .map(
        (col) => `
            <th class="${col.sortable ? "sortable" : ""}" ${col.sortKey ? `data-sort="${col.sortKey}"` : ""}>
                ${col.label}
            </th>
        `,
      )
      .join("");

    const bodyRows =
      config.data
        ?.map(
          (row) => `
            <tr>
                ${config.columns
                  .map(
                    (col) => `
                    <td ${row[col.key + "_sort"] ? `data-sort="${row[col.key + "_sort"]}"` : ""}>
                        ${row[col.key] || ""}
                    </td>
                `,
                  )
                  .join("")}
            </tr>
        `,
        )
        .join("") || "";
    // nosemgrep
    table.innerHTML = `
            <thead>
                <tr>${headerRow}</tr>
            </thead>
            <tbody>
                ${bodyRows}
            </tbody>
        `;

    return table;
  }

  /**
   * Utility method to create a pipeline view for workflow status
   * @param {Object} config - Pipeline configuration
   * @param {string} config.id - Pipeline container ID
   * @param {string} config.title - Pipeline title
   * @param {Array} config.stages - Array of {label, count} objects
   * @param {Object} config.blocked - Optional {label, count} for blocked items
   * @returns {HTMLElement} Pipeline container element
   */
  createPipelineView(config) {
    const container = document.createElement("div");
    container.className = "clo-pipeline";
    container.id = config.id;

    const title = config.title
      ? `<div class="pipeline-title">${config.title}</div>`
      : "";

    const stageLabels = config.stages.map((s) => s.label).join(" → ");
    const stageCounts = config.stages
      .map((s) => s.count.toString())
      .join("     ");

    let blockedHtml = "";
    if (config.blocked && config.blocked.count > 0) {
      blockedHtml = `<div class="pipeline-blocked">Blocked: ${config.blocked.count} (${config.blocked.label})</div>`;
    }

    // nosemgrep
    container.innerHTML = `
      ${title}
      <div class="pipeline-stages">
        <div class="pipeline-labels">${stageLabels}</div>
        <div class="pipeline-counts">${stageCounts}</div>
      </div>
      ${blockedHtml}
    `;

    return container;
  }
}

// Initialize panel manager when DOM is loaded
let panelManager;
document.addEventListener("DOMContentLoaded", () => {
  panelManager = new PanelManager();
  globalThis.panelManager = panelManager; // Export after initialization
});

if (typeof module !== "undefined" && module.exports) {
  module.exports = { PanelManager };
}

// ============================================================================
// AUDIT LOG FUNCTIONALITY
// ============================================================================

/**
 * Load and display recent audit logs in the System Activity panel
 */
async function loadAuditLogs(limit = 20) {
  const container = document.getElementById("activityTableContainer");
  if (!container) return;

  // Show loading state
  // nosemgrep
  container.innerHTML = `
    <div class="panel-loading">
      <div class="spinner-border spinner-border-sm"></div>
      Loading system activity...
    </div>
  `;

  try {
    const response = await fetch(`/api/audit/recent?limit=${limit}`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    if (data.success) {
      displayAuditLogs(data.logs);
    } else {
      throw new Error(data.error || "Failed to load audit logs");
    }
  } catch (error) {
    console.error("Error loading audit logs:", error); // eslint-disable-line no-console
    // nosemgrep
    container.innerHTML = `
      <div class="alert alert-danger">
        <i class="fas fa-exclamation-triangle"></i>
        Failed to load system activity: ${escapeHtml(error.message)}
      </div>
    `;
  }
}

/**
 * Display audit logs in a table
 */
function displayAuditLogs(logs) {
  const container = document.getElementById("activityTableContainer");
  if (!container) return;

  if (!logs || logs.length === 0) {
    // nosemgrep
    container.innerHTML = `
      <div class="text-center text-muted py-4">
        <i class="fas fa-inbox fa-2x mb-2"></i>
        <p>No recent activity to display</p>
      </div>
    `;
    return;
  }

  const tableResp = document.createElement("div");
  tableResp.className = "table-responsive";
  const table = document.createElement("table");
  table.className = "table table-hover table-sm"; // Changed from table-striped to table-hover to match original

  const thead = document.createElement("thead");
  thead.innerHTML = `
    <tr>
      <th>Timestamp</th>
      <th>User</th>
      <th>Action</th>
      <th>Entity</th>
      <th>Details</th>
    </tr>
  `;
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  logs.forEach((log) => {
    tbody.appendChild(createAuditLogRow(log));
  });
  table.appendChild(tbody);
  tableResp.appendChild(table);

  container.innerHTML = "";
  container.appendChild(tableResp);
}

/**
 * Create a table row for an audit log entry
 */
function createAuditLogRow(log) {
  const tr = document.createElement("tr");

  const timestamp = formatAuditTimestamp(log.timestamp);
  const userDisplay = log.user_email || "System";
  const actionBadge = getActionBadge(log.operation_type);
  const entityDisplay = formatEntityDisplay(log.entity_type, log.entity_id);
  const detailsDisplay = getAuditDetails(log);

  // Timestamp
  const tdTime = document.createElement("td");
  tdTime.className = "text-nowrap";
  const small = document.createElement("small");
  small.textContent = timestamp;
  tdTime.appendChild(small);
  tr.appendChild(tdTime);

  // User
  const tdUser = document.createElement("td");
  tdUser.textContent = userDisplay;
  tr.appendChild(tdUser);

  // Action
  const tdAction = document.createElement("td");
  tdAction.appendChild(actionBadge);
  tr.appendChild(tdAction);

  // Entity
  const tdEntity = document.createElement("td");
  tdEntity.appendChild(entityDisplay);
  tr.appendChild(tdEntity);

  // Details
  const tdDetails = document.createElement("td");
  const smallDetails = document.createElement("small");
  smallDetails.className = "text-muted";
  smallDetails.textContent = detailsDisplay;
  tdDetails.appendChild(smallDetails);
  tr.appendChild(tdDetails);

  return tr;
}

/**
 * Format timestamp for display
 */
function formatAuditTimestamp(timestamp) {
  if (!timestamp) return "-";

  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;

  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Get action badge with color coding
 */
function getActionBadge(operationType) {
  const span = document.createElement("span");
  span.className = "badge";

  const config = {
    CREATE: "bg-success",
    UPDATE: "bg-info",
    DELETE: "bg-danger",
  };

  span.classList.add(config[operationType] || "bg-secondary");
  span.textContent =
    operationType.charAt(0) + operationType.slice(1).toLowerCase();
  return span;
}

/**
 * Format entity display with icon
 */
function formatEntityDisplay(entityType, entityId) {
  const icons = {
    users: "👤",
    institutions: "🏛️",
    programs: "📚",
    courses: "📖",
    terms: "📅",
    course_offerings: "📝",
    course_sections: "👥",
    course_outcomes: "🎯",
  };

  const icon = icons[entityType] || "📄";
  const shortId = entityId ? entityId.substring(0, 8) : "";

  const frag = document.createDocumentFragment();
  frag.appendChild(document.createTextNode(`${icon} `));
  const span = document.createElement("span");
  span.className = "text-muted";
  span.textContent = shortId;
  frag.appendChild(span);

  return frag;
}

/**
 * Get audit details from changed fields
 */
function getAuditDetails(log) {
  if (log.changed_fields) {
    try {
      const fields = JSON.parse(log.changed_fields);
      if (Array.isArray(fields) && fields.length > 0) {
        return `Changed: ${fields.slice(0, 3).join(", ")}${fields.length > 3 ? "..." : ""}`;
      }
    } catch (e) {
      // Ignore JSON parse errors
    }
  }

  if (log.operation_type === "CREATE") {
    return "New entity created";
  } else if (log.operation_type === "DELETE") {
    return "Entity deleted";
  }

  return "Entity modified";
}

/**
 * HTML escape utility (duplicate from admin.js for standalone use)
 */
function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/**
 * View all activity - navigate to detailed audit log page
 */
function viewAllActivity() {
  window.location.href = "/audit-logs";
}

/**
 * Filter activity - navigate to detailed audit log page
 */
function filterActivity() {
  window.location.href = "/audit-logs";
}

// Auto-load audit logs when panel is expanded
document.addEventListener("DOMContentLoaded", () => {
  const activityPanel = document.getElementById("system-activity-panel");
  if (activityPanel) {
    // Load logs on page load
    loadAuditLogs(20);

    // Reload logs when panel is toggled open
    const toggleBtn = activityPanel.querySelector(".panel-toggle");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => {
        // Check if panel is being opened (will be collapsed now, will be expanded after click)
        const panelContent = activityPanel.querySelector(".panel-content");
        if (panelContent?.style.display === "none") {
          // Panel is being opened, reload data
          setTimeout(() => loadAuditLogs(20), 100);
        }
      });
    }

    // Auto-refresh every 30 seconds
    setInterval(() => {
      const panelContent = activityPanel.querySelector(".panel-content");
      if (panelContent?.style.display !== "none") {
        loadAuditLogs(20);
      }
    }, 30000);
  }
});

// Export for global use
globalThis.loadAuditLogs = loadAuditLogs;
globalThis.viewAllActivity = viewAllActivity;
globalThis.filterActivity = filterActivity;
globalThis.createAuditLogRow = createAuditLogRow;
globalThis.formatAuditTimestamp = formatAuditTimestamp;
globalThis.getActionBadge = getActionBadge;
globalThis.formatEntityDisplay = formatEntityDisplay;
globalThis.getAuditDetails = getAuditDetails;
globalThis.escapeHtml = escapeHtml;
