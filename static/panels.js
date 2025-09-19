/**
 * Panel-Based UI JavaScript
 * Handles panel interactions, sorting, stats, and focus mode
 */

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
      const panelId = panel.id || `panel-${Date.now()}-${Math.random()}`;
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
      const tableId = table.id || `table-${Date.now()}-${Math.random()}`;
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
      if (target && target.closest && target.closest('.panel-header')) {
        const panel = target.closest('.dashboard-panel');
        if (panel && !target.closest('.panel-actions')) {
          this.togglePanel(panel.id);
        }
      }

      // Table sorting events
      if (target && target.closest && target.closest('th.sortable')) {
        const header = target.closest('th.sortable');
        const table = header.closest('.panel-table');
        const sortKey =
          header.dataset.sort || Array.from(header.parentElement.children).indexOf(header);
        this.sortTable(`${table.id}-${sortKey}`);
      }

      // Panel focus events
      if (target && target.closest && target.closest('.panel-title') && e.detail === 2) {
        // Double click
        const panel = target.closest('.dashboard-panel');
        if (panel) {
          this.focusPanel(panel.id);
        }
      }

      // Close stat previews when clicking outside
      if (!target || !target.closest || !target.closest('.stat-item')) {
        this.hideAllStatPreviews();
      }
    });

    // Stat preview events
    document.addEventListener(
      'mouseenter',
      e => {
        // Ensure we have an Element before calling closest()
        const target = e.target instanceof Element ? e.target : e.target.parentElement;
        if (target && target.closest && target.closest('.stat-item')) {
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
        if (target && target.closest && target.closest('.stat-item')) {
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
    if (!stat || !stat.preview) return;

    stat.preview.classList.remove('show');
    setTimeout(() => {
      if (stat.preview && stat.preview.parentNode) {
        stat.preview.parentNode.removeChild(stat.preview);
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
          data.institutions?.slice(0, 5).map(inst => ({
            label: inst.name,
            value: `${inst.user_count || 0} users`
          })) || []
      },
      programs: {
        endpoint: '/api/programs',
        title: 'Programs',
        transform: data =>
          data.programs?.slice(0, 5).map(prog => ({
            label: prog.name,
            value: `${prog.course_count || 0} courses`
          })) || []
      },
      courses: {
        endpoint: '/api/courses',
        title: 'Active Courses',
        transform: data =>
          data.courses?.slice(0, 5).map(course => ({
            label: `${course.course_number}`,
            value: course.title
          })) || []
      },
      users: {
        endpoint: '/api/users',
        title: 'Recent Users',
        transform: data =>
          data.users?.slice(0, 5).map(user => ({
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

    switch (statId) {
    case 'institutions': {
      const institutions = cache.institutions || [];
      if (!institutions.length) return null;
      return {
        title: 'Institutions',
        items: formatItems(
          institutions,
          inst => inst.name || inst.institution_id,
          inst => `${inst.user_count || 0} users`
        )
      };
    }
    case 'programs': {
      const programs = cache.program_overview || cache.programs || [];
      if (!programs.length) return null;
      return {
        title: 'Programs',
        items: formatItems(
          programs,
          prog => prog.program_name || prog.name || prog.program_id,
          prog => `${prog.course_count || 0} courses`
        )
      };
    }
    case 'courses': {
      const courses = cache.courses || [];
      if (!courses.length) return null;
      return {
        title: 'Courses',
        items: formatItems(
          courses,
          course => course.course_number || course.course_id,
          course => course.course_title || course.title || '—'
        )
      };
    }
    case 'users': {
      const users = cache.users || cache.faculty || [];
      if (!users.length) return null;
      return {
        title: 'Users',
        items: formatItems(
          users,
          user =>
            (user.full_name || `${user.first_name || ''} ${user.last_name || ''}`).trim() ||
              user.email,
          user => (user.role || 'user').replace(/_/g, ' ')
        )
      };
    }
    case 'faculty': {
      const faculty = cache.faculty_assignments || cache.faculty || cache.instructors || [];
      if (!faculty.length) return null;
      return {
        title: 'Faculty',
        items: formatItems(
          faculty,
          member => member.full_name || member.name || 'Instructor',
          member => `${member.course_count || 0} courses`
        )
      };
    }
    case 'sections': {
      const sections = cache.sections || [];
      if (!sections.length) return null;
      return {
        title: 'Sections',
        items: formatItems(
          sections,
          section => section.section_number || section.section_id || 'Section',
          section => `${section.enrollment || 0} students`
        )
      };
    }
    case 'students': {
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
    case 'assessments': {
      const tasks = cache.assessment_tasks || [];
      if (!tasks.length) return null;
      return {
        title: 'Assessments',
        items: formatItems(
          tasks,
          task =>
            task.course_number || task.course_title || task.section_number || task.section_id,
          task => (task.status || 'pending').replace(/_/g, ' ')
        )
      };
    }
    default:
      return null;
    }
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
  config.actions
    ?.map(
      action => `
                        <button class="btn btn-sm btn-outline-primary" onclick="${action.onclick}">
                            ${action.icon} ${action.label}
                        </button>
                    `
    )
    .join('') || ''
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
      config.data
        ?.map(
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
        .join('') || '';

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
