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

function generateSecureId(prefix = 'id') {
  if (window.crypto?.getRandomValues) {
    const array = new Uint32Array(1);
    window.crypto.getRandomValues(array);
    return `${prefix}-${Date.now()}-${array[0]}`;
  }

  // Fallback for older browsers - use timestamp, performance counter, and monotonic counter
  // Avoids Math.random() to address SonarCloud security concerns
  const timestamp = Date.now();
  const performanceNow = globalThis.performance?.now ? globalThis.performance.now() : 0;
  const counter = ++idCounter; // Monotonic counter guarantees uniqueness

  // Create unique ID using timestamp, performance counter, and monotonic counter
  // The counter ensures uniqueness even for rapid successive calls
  const entropy = Math.floor(performanceNow * 1000) + counter;
  return `${prefix}-${timestamp}-${entropy}`;
}

class PanelManager {
  constructor() {
    this.panels = new Map();
    this.statPreviews = new Map();
    this.sortStates = new Map();
    this.focusedPanel = null;
    this.init();
  }

  init() {
    this.initializePanels();
    this.initializeStatPreviews();
    this.initializeSortableTables();
    this.bindEvents();
  }

  /**
   * Initialize all panels on the page
   */
  initializePanels() {
    const panels = document.querySelectorAll('.dashboard-panel');
    panels.forEach(panel => {
      const panelId = panel.id || generateSecureId('panel');
      panel.id = panelId;

      const header = panel.querySelector('.panel-header');
      const content = panel.querySelector('.panel-content');
      const toggle = panel.querySelector('.panel-toggle');

      if (header && content && toggle) {
        this.panels.set(panelId, {
          element: panel,
          header,
          content,
          toggle,
          collapsed: content.classList.contains('collapsed')
        });

        // Set initial state
        this.updatePanelState(panelId);
      }
    });
  }

  /**
   * Initialize interactive header stats
   */
  initializeStatPreviews() {
    const statItems = document.querySelectorAll('.stat-item');
    statItems.forEach(item => {
      const statId = item.dataset.stat;
      if (statId) {
        this.statPreviews.set(statId, {
          element: item,
          preview: null,
          timeout: null
        });
      }
    });
  }

  /**
   * Initialize sortable tables
   */
  initializeSortableTables() {
    const tables = document.querySelectorAll('.panel-table');
    tables.forEach(table => {
      const tableId = table.id || generateSecureId('table');
      table.id = tableId;

      const headers = table.querySelectorAll('th.sortable');
      headers.forEach((header, index) => {
        const sortKey = header.dataset.sort || index;
        this.sortStates.set(`${tableId}-${sortKey}`, {
          table,
          header,
          column: index,
          direction: null // null, 'asc', 'desc'
        });
      });
    });
  }

  /**
   * Bind all event listeners
   */
  bindEvents() {
    // Panel toggle events
    document.addEventListener('click', e => {
      const target = e.target instanceof Element ? e.target : e.target.parentElement;
      if (target?.closest?.('.panel-header')) {
        const panel = target.closest('.dashboard-panel');
        if (panel && !target.closest('.panel-actions')) {
          this.togglePanel(panel.id);
        }
      }

      // Table sorting events
      if (target?.closest?.('th.sortable')) {
        const header = target.closest('th.sortable');
        const table = header.closest('.panel-table');
        const sortKey =
          header.dataset.sort || Array.from(header.parentElement.children).indexOf(header);
        this.sortTable(`${table.id}-${sortKey}`);
      }

      // Panel focus events
      if (target?.closest?.('.panel-title') && e.detail === 2) {
        // Double click
        const panel = target.closest('.dashboard-panel');
        if (panel) {
          this.focusPanel(panel.id);
        }
      }

      // Close stat previews when clicking outside
      if (!target?.closest?.('.stat-item')) {
        this.hideAllStatPreviews();
      }
    });

    // Stat preview events
    document.addEventListener(
      'mouseenter',
      e => {
        // Ensure we have an Element before calling closest()
        const target = e.target instanceof Element ? e.target : e.target.parentElement;
        if (target?.closest?.('.stat-item')) {
          const statItem = target.closest('.stat-item');
          const statId = statItem.dataset.stat;
          if (statId) {
            this.showStatPreview(statId);
          }
        }
      },
      true
    );

    document.addEventListener(
      'mouseleave',
      e => {
        // Ensure we have an Element before calling closest()
        const target = e.target instanceof Element ? e.target : e.target.parentElement;
        if (target?.closest?.('.stat-item')) {
          const statItem = target.closest('.stat-item');
          const statId = statItem.dataset.stat;
          if (statId) {
            this.scheduleHideStatPreview(statId);
          }
        }
      },
      true
    );

    // Keyboard events
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && this.focusedPanel) {
        this.unfocusPanel();
      }
    });

    // Window resize events
    window.addEventListener('resize', () => {
      this.hideAllStatPreviews();
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
      panel.content.classList.add('collapsed');
      panel.toggle.classList.add('collapsed');
      panel.toggle.innerHTML = '▶';
    } else {
      panel.content.classList.remove('collapsed');
      panel.toggle.classList.remove('collapsed');
      panel.toggle.innerHTML = '▼';
    }
  }

  /**
   * Show stat preview
   */
  async showStatPreview(statId) {
    const stat = this.statPreviews.get(statId);
    if (!stat) return;

    // Clear any pending hide timeout
    if (stat.timeout) {
      clearTimeout(stat.timeout);
      stat.timeout = null;
    }

    // If preview already exists, show it
    if (stat.preview) {
      stat.preview.classList.add('show');
      return;
    }

    // Create preview element
    const preview = document.createElement('div');
    preview.className = 'stat-preview';

    // Load preview data
    try {
      const data = await this.loadStatPreviewData(statId);
      preview.innerHTML = `
                <div class="stat-preview-header">${data.title}</div>
                <div class="stat-preview-content">
                    ${data.items
                      .map(
                        item => `
                        <div class="stat-preview-item">
                            <span>${item.label}</span>
                            <span>${item.value}</span>
                        </div>
                    `
                      )
                      .join('')}
                </div>
            `;
    } catch (error) {
      preview.innerHTML = `
                <div class="stat-preview-header">Error</div>
                <div class="stat-preview-content">
                    <div class="text-danger">Failed to load preview data</div>
                </div>
            `;
    }

    stat.element.appendChild(preview);
    stat.preview = preview;

    // Show with animation
    requestAnimationFrame(() => {
      preview.classList.add('show');
    });
  }

  /**
   * Schedule hiding stat preview
   */
  scheduleHideStatPreview(statId) {
    const stat = this.statPreviews.get(statId);
    if (!stat) return;

    stat.timeout = setTimeout(() => {
      this.hideStatPreview(statId);
    }, 500);
  }

  /**
   * Hide stat preview
   */
  hideStatPreview(statId) {
    const stat = this.statPreviews.get(statId);
    if (!stat?.preview) return;

    stat.preview.classList.remove('show');
    setTimeout(() => {
      if (stat.preview?.remove) {
        stat.preview.remove();
      }
      stat.preview = null;
    }, 300);
  }

  /**
   * Hide all stat previews
   */
  hideAllStatPreviews() {
    this.statPreviews.forEach((stat, statId) => {
      if (stat.timeout) {
        clearTimeout(stat.timeout);
        stat.timeout = null;
      }
      this.hideStatPreview(statId);
    });
  }

  /**
   * Sort table by column
   */
  sortTable(sortStateId) {
    const sortState = this.sortStates.get(sortStateId);
    if (!sortState) return;

    // Update sort direction
    if (sortState.direction === null || sortState.direction === 'desc') {
      sortState.direction = 'asc';
    } else {
      sortState.direction = 'desc';
    }

    // Clear other sort states for this table
    this.sortStates.forEach((state, id) => {
      if (state.table === sortState.table && id !== sortStateId) {
        state.direction = null;
        state.header.classList.remove('sort-asc', 'sort-desc');
      }
    });

    // Update header classes
    sortState.header.classList.remove('sort-asc', 'sort-desc');
    sortState.header.classList.add(`sort-${sortState.direction}`);

    // Sort the table
    this.performTableSort(sortState);
  }

  /**
   * Perform the actual table sorting
   */
  performTableSort(sortState) {
    const tbody = sortState.table.querySelector('tbody');
    if (!tbody) return;

    const rows = Array.from(tbody.querySelectorAll('tr'));
    const columnIndex = sortState.column;

    rows.sort((a, b) => {
      const aValue = this.getCellValue(a.cells[columnIndex]);
      const bValue = this.getCellValue(b.cells[columnIndex]);

      if (sortState.direction === 'asc') {
        return aValue.localeCompare(bValue, undefined, { numeric: true, sensitivity: 'base' });
      } else {
        return bValue.localeCompare(aValue, undefined, { numeric: true, sensitivity: 'base' });
      }
    });

    // Re-append sorted rows
    rows.forEach(row => tbody.appendChild(row));
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
    let value = cell.textContent || cell.innerText || '';
    value = value.trim();

    // Handle special cases
    if (value.includes('/')) {
      // Handle fractions like "4/6"
      const parts = value.split('/');
      if (parts.length === 2) {
        const numerator = parseInt(parts[0]);
        const denominator = parseInt(parts[1]);
        if (!isNaN(numerator) && !isNaN(denominator) && denominator > 0) {
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
    panel.element.classList.add('panel-focused');
    document.body.style.overflow = 'hidden';

    // Add breadcrumb navigation
    const breadcrumb = document.createElement('div');
    breadcrumb.className = 'breadcrumb-nav';
    breadcrumb.innerHTML = `
            <a href="#" onclick="panelManager.unfocusPanel(); return false;">Dashboard</a>
            <span class="breadcrumb-separator">›</span>
            <span>${panel.header.querySelector('.panel-title').textContent}</span>
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
      panel.element.classList.remove('panel-focused');
      const breadcrumb = panel.element.querySelector('.breadcrumb-nav');
      if (breadcrumb) {
        breadcrumb.remove();
      }
    }

    document.body.style.overflow = '';
    this.focusedPanel = null;
  }

  /**
   * Load stat preview data based on stat type
   */
  async loadStatPreviewData(statId) {
    const cache = window.dashboardDataCache;
    if (cache) {
      const cached = this.buildPreviewFromCache(statId, cache);
      if (cached) {
        return cached;
      }
    }

    const statConfigs = {
      institutions: {
        endpoint: '/api/institutions',
        title: 'Institutions',
        transform: data =>
          data.institutions?.map(inst => ({
            label: inst.name,
            value: `${inst.user_count || 0} users`
          })) || []
      },
      programs: {
        endpoint: '/api/programs',
        title: 'Programs',
        transform: data =>
          data.programs?.map(prog => ({
            label: prog.name,
            value: `${prog.course_count || 0} courses`
          })) || []
      },
      courses: {
        endpoint: '/api/courses',
        title: 'Active Courses',
        transform: data =>
          data.courses?.map(course => ({
            label: `${course.course_number}`,
            value: course.title
          })) || []
      },
      faculty: {
        endpoint: '/api/users?role=instructor',
        title: 'Faculty',
        transform: data =>
          data.users?.map(user => ({
            label:
              (user.full_name || `${user.first_name || ''} ${user.last_name || ''}`).trim() ||
              user.email,
            value: (user.department || user.role || 'instructor').replace(/_/g, ' ')
          })) || []
      },
      sections: {
        endpoint: '/api/sections',
        title: 'Sections',
        transform: data =>
          data.sections?.map(section => ({
            label: section.course_number
              ? `${section.course_number} Section ${section.section_number || section.section_id || ''}`
              : `Section ${section.section_number || section.section_id || ''}`,
            value: `${section.enrollment || 0} students`
          })) || []
      },
      users: {
        endpoint: '/api/users',
        title: 'Recent Users',
        transform: data =>
          data.users?.map(user => ({
            label: `${user.first_name} ${user.last_name}`,
            value: user.role.replace('_', ' ')
          })) || []
      }
    };

    const config = statConfigs[statId];
    if (!config) {
      throw new Error(`Unknown stat type: ${statId}`);
    }

    const response = await fetch(config.endpoint, {
      credentials: 'include'
    });

    if (!response.ok) {
      throw new Error(`Failed to load ${statId} data`);
    }

    const data = await response.json();

    return {
      title: config.title,
      items: config.transform(data)
    };
  }

  buildPreviewFromCache(statId, cache) {
    const formatItems = (items, labelFn, valueFn) =>
      items
        .slice(0, 5)
        .map(item => ({ label: labelFn(item), value: valueFn(item) }))
        .filter(entry => entry.label);

    // Configuration for cache preview builders
    const cacheConfigs = {
      institutions: {
        title: 'Institutions',
        getData: cache => cache.institutions || [],
        labelFn: inst => inst.name || inst.institution_id,
        valueFn: inst => `${inst.user_count || 0} users`
      },
      programs: {
        title: 'Programs',
        getData: cache => cache.program_overview || cache.programs || [],
        labelFn: prog => prog.program_name || prog.name || prog.program_id,
        valueFn: prog => `${prog.course_count || 0} courses`
      },
      courses: {
        title: 'Courses',
        getData: cache => cache.courses || [],
        labelFn: course => course.course_number || course.course_id,
        valueFn: course => course.course_title || course.title || '—'
      },
      users: {
        title: 'Users',
        getData: cache => cache.users || cache.faculty || [],
        labelFn: user =>
          (user.full_name || `${user.first_name || ''} ${user.last_name || ''}`).trim() ||
          user.email,
        valueFn: user => (user.role || 'user').replace(/_/g, ' ')
      },
      faculty: {
        title: 'Faculty',
        getData: cache => cache.faculty_assignments || cache.faculty || cache.instructors || [],
        labelFn: member => member.full_name || member.name || 'Instructor',
        valueFn: member => `${member.course_count || 0} courses`
      },
      sections: {
        title: 'Sections',
        getData: cache => cache.sections || [],
        labelFn: section => {
          const courseNumber = section.course_number || '';
          const sectionNumber = section.section_number || section.section_id || 'Section';
          return courseNumber
            ? `${courseNumber} Section ${sectionNumber}`
            : `Section ${sectionNumber}`;
        },
        valueFn: section => `${section.enrollment || 0} students`
      },
      assessments: {
        title: 'Assessments',
        getData: cache => cache.assessment_tasks || [],
        labelFn: task =>
          task.course_number || task.course_title || task.section_number || task.section_id,
        valueFn: task => (task.status || 'pending').replace(/_/g, ' ')
      }
    };

    // Special case for students (different data structure)
    if (statId === 'students') {
      const summary = cache.summary || {};
      if (typeof summary.students === 'undefined') return null;
      return {
        title: 'Students',
        items: [
          { label: 'Total Students', value: summary.students.toString() },
          { label: 'Sections', value: (summary.sections ?? 0).toString() },
          { label: 'Courses', value: (summary.courses ?? 0).toString() }
        ]
      };
    }

    const config = cacheConfigs[statId];
    if (!config) return null;

    const data = config.getData(cache);
    if (!data.length) return null;

    return {
      title: config.title,
      items: formatItems(data, config.labelFn, config.valueFn)
    };
  }

  /**
   * Utility method to create a new panel
   */
  createPanel(config) {
    const panel = document.createElement('div');
    panel.className = 'dashboard-panel fade-in';
    panel.id = config.id;

    panel.innerHTML = `
            <div class="panel-header">
                <h5 class="panel-title">
                    <span class="panel-icon">${config.icon}</span>
                    ${config.title}
                </h5>
                <div class="panel-actions">
                    ${
                      (config.actions &&
                        config.actions
                          .map(
                            action => `
                        <button class="btn btn-sm btn-outline-primary" onclick="${action.onclick}">
                            ${action.icon} ${action.label}
                        </button>
                    `
                          )
                          .join('')) ||
                      ''
                    }
                </div>
                <button class="panel-toggle">▼</button>
            </div>
            <div class="panel-content ${config.collapsed ? 'collapsed' : ''}">
                ${config.content}
            </div>
        `;

    return panel;
  }

  /**
   * Utility method to create a sortable table
   */
  createSortableTable(config) {
    const table = document.createElement('table');
    table.className = 'table panel-table';
    table.id = config.id;

    const headerRow = config.columns
      .map(
        col => `
            <th class="${col.sortable ? 'sortable' : ''}" ${col.sortKey ? `data-sort="${col.sortKey}"` : ''}>
                ${col.label}
            </th>
        `
      )
      .join('');

    const bodyRows =
      (config.data &&
        config.data
          .map(
            row => `
            <tr>
                ${config.columns
                  .map(
                    col => `
                    <td ${row[col.key + '_sort'] ? `data-sort="${row[col.key + '_sort']}"` : ''}>
                        ${row[col.key] || ''}
                    </td>
                `
                  )
                  .join('')}
            </tr>
        `
          )
          .join('')) ||
      '';

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
}

// Initialize panel manager when DOM is loaded
let panelManager;
document.addEventListener('DOMContentLoaded', () => {
  panelManager = new PanelManager();
  window.panelManager = panelManager; // Export after initialization
});

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { PanelManager };
}

// ============================================================================
// AUDIT LOG FUNCTIONALITY
// ============================================================================

/**
 * Load and display recent audit logs in the System Activity panel
 */
async function loadAuditLogs(limit = 20) {
  const container = document.getElementById('activityTableContainer');
  if (!container) return;

  // Show loading state
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
      throw new Error(data.error || 'Failed to load audit logs');
    }
  } catch (error) {
    console.error('Error loading audit logs:', error); // eslint-disable-line no-console
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
  const container = document.getElementById('activityTableContainer');
  if (!container) return;

  if (!logs || logs.length === 0) {
    container.innerHTML = `
      <div class="text-center text-muted py-4">
        <i class="fas fa-inbox fa-2x mb-2"></i>
        <p>No recent activity to display</p>
      </div>
    `;
    return;
  }

  const tableHTML = `
    <div class="table-responsive">
      <table class="table table-hover table-sm">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>User</th>
            <th>Action</th>
            <th>Entity</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          ${logs.map(log => createAuditLogRow(log)).join('')}
        </tbody>
      </table>
    </div>
  `;

  container.innerHTML = tableHTML;
}

/**
 * Create a table row for an audit log entry
 */
function createAuditLogRow(log) {
  const timestamp = formatAuditTimestamp(log.timestamp);
  const userDisplay = log.user_email || 'System';
  const actionBadge = getActionBadge(log.operation_type);
  const entityDisplay = formatEntityDisplay(log.entity_type, log.entity_id);
  const detailsDisplay = getAuditDetails(log);

  return `
    <tr>
      <td class="text-nowrap"><small>${timestamp}</small></td>
      <td>${escapeHtml(userDisplay)}</td>
      <td>${actionBadge}</td>
      <td>${entityDisplay}</td>
      <td><small class="text-muted">${detailsDisplay}</small></td>
    </tr>
  `;
}

/**
 * Format timestamp for display
 */
function formatAuditTimestamp(timestamp) {
  if (!timestamp) return '-';

  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;

  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

/**
 * Get action badge with color coding
 */
function getActionBadge(operationType) {
  const badges = {
    CREATE: '<span class="badge bg-success">Create</span>',
    UPDATE: '<span class="badge bg-info">Update</span>',
    DELETE: '<span class="badge bg-danger">Delete</span>'
  };

  return badges[operationType] || `<span class="badge bg-secondary">${operationType}</span>`;
}

/**
 * Format entity display with icon
 */
function formatEntityDisplay(entityType, entityId) {
  const icons = {
    users: '👤',
    institutions: '🏛️',
    programs: '📚',
    courses: '📖',
    terms: '📅',
    course_offerings: '📝',
    course_sections: '👥',
    course_outcomes: '🎯'
  };

  const icon = icons[entityType] || '📄';
  const shortId = entityId ? entityId.substring(0, 8) : '';

  return `${icon} <span class="text-muted">${shortId}</span>`;
}

/**
 * Get audit details from changed fields
 */
function getAuditDetails(log) {
  if (log.changed_fields) {
    try {
      const fields = JSON.parse(log.changed_fields);
      if (Array.isArray(fields) && fields.length > 0) {
        return `Changed: ${fields.slice(0, 3).join(', ')}${fields.length > 3 ? '...' : ''}`;
      }
    } catch (e) {
      // Ignore JSON parse errors
    }
  }

  if (log.operation_type === 'CREATE') {
    return 'New entity created';
  } else if (log.operation_type === 'DELETE') {
    return 'Entity deleted';
  }

  return 'Entity modified';
}

/**
 * HTML escape utility (duplicate from admin.js for standalone use)
 */
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * View all activity - navigate to detailed audit log page
 */
function viewAllActivity() {
  // TODO: Implement full audit log viewer page
  alert(
    'Full audit log viewer coming soon!\n\nFor now, you can export audit logs via the API:\nPOST /api/audit/export'
  );
}

/**
 * Filter activity - show filter modal
 */
function filterActivity() {
  // TODO: Implement filter modal
  alert(
    'Activity filtering coming soon!\n\nFilters will include:\n- Date range\n- User\n- Action type\n- Entity type'
  );
}

// Auto-load audit logs when panel is expanded
document.addEventListener('DOMContentLoaded', () => {
  const activityPanel = document.getElementById('system-activity-panel');
  if (activityPanel) {
    // Load logs on page load
    loadAuditLogs(20);

    // Reload logs when panel is toggled open
    const toggleBtn = activityPanel.querySelector('.panel-toggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        // Check if panel is being opened (will be collapsed now, will be expanded after click)
        const panelContent = activityPanel.querySelector('.panel-content');
        if (panelContent?.style.display === 'none') {
          // Panel is being opened, reload data
          setTimeout(() => loadAuditLogs(20), 100);
        }
      });
    }

    // Auto-refresh every 30 seconds
    setInterval(() => {
      const panelContent = activityPanel.querySelector('.panel-content');
      if (panelContent?.style.display !== 'none') {
        loadAuditLogs(20);
      }
    }, 30000);
  }
});

// Export for global use
window.loadAuditLogs = loadAuditLogs;
window.viewAllActivity = viewAllActivity;
window.filterActivity = filterActivity;
window.createAuditLogRow = createAuditLogRow;
window.formatAuditTimestamp = formatAuditTimestamp;
window.getActionBadge = getActionBadge;
window.formatEntityDisplay = formatEntityDisplay;
window.getAuditDetails = getAuditDetails;
window.escapeHtml = escapeHtml;
