(function() {
  const API_ENDPOINT = '/api/dashboard/data';
  const SELECTORS = {
    name: 'instructorName',
    courseCount: 'instructorCourseCount',
    sectionCount: 'instructorSectionCount',
    studentCount: 'instructorStudentCount',
    assessmentProgress: 'instructorAssessmentProgress',
    lastUpdated: 'instructorLastUpdated',
    refreshButton: 'instructorRefreshButton',
    teachingContainer: 'instructorTeachingContainer',
    assessmentContainer: 'instructorAssessmentContainer',
    activityList: 'instructorActivityList',
    summaryContainer: 'instructorSummaryContainer'
  };

  const InstructorDashboard = {
    cache: null,
    lastFetch: 0,
    refreshInterval: 5 * 60 * 1000,

    init() {
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden && Date.now() - this.lastFetch > this.refreshInterval) {
          this.loadData({ silent: true });
        }
      });

      const refreshButton = document.getElementById(SELECTORS.refreshButton);
      if (refreshButton) {
        refreshButton.addEventListener('click', () => this.loadData({ silent: false }));
      }

      this.loadData();
      setInterval(() => this.loadData({ silent: true }), this.refreshInterval);
    },

    async loadData(options = {}) {
      const { silent = false } = options;
      if (!silent) {
        this.setLoading(SELECTORS.teachingContainer, 'Loading teaching assignments...');
        this.setLoading(SELECTORS.assessmentContainer, 'Loading assessment tasks...');
        this.setLoading(SELECTORS.summaryContainer, 'Building summary...');
        const activityList = document.getElementById(SELECTORS.activityList);
        if (activityList) {
          activityList.innerHTML = '<li class="text-muted">Fetching recent activity…</li>';
        }
      }

      try {
        const response = await fetch(API_ENDPOINT, {
          credentials: 'include',
          headers: {
            Accept: 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
          }
        });

        const payload = await response.json();
        if (!response.ok || !payload.success) {
          throw new Error(payload.error || 'Unable to load dashboard data');
        }

        this.cache = payload.data || {};
        window.dashboardDataCache = this.cache;
        this.lastFetch = Date.now();
        this.render(this.cache);
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error('Instructor dashboard load error:', error);
        this.showError(SELECTORS.teachingContainer, 'Unable to load teaching assignments');
        this.showError(SELECTORS.assessmentContainer, 'Unable to load assessment tasks');
        this.showError(SELECTORS.summaryContainer, 'Unable to build summary');
        const activityList = document.getElementById(SELECTORS.activityList);
        if (activityList) {
          activityList.innerHTML = '<li class="text-danger">Unable to load recent activity</li>';
        }
      }
    },

    render(data) {
      this.updateHeader(data);
      this.renderTeachingAssignments(data.teaching_assignments || []);
      this.renderAssessmentTasks(data.assessment_tasks || []);
      this.renderRecentActivity(data.assessment_tasks || []);
      this.renderCourseSummary(data.teaching_assignments || [], data.sections || []);
      this.updateLastUpdated(data.metadata && data.metadata.last_updated);
    },

    updateHeader(data) {
      const summary = data.summary || {};
      document.getElementById(SELECTORS.courseCount).textContent = summary.courses ?? 0;
      document.getElementById(SELECTORS.sectionCount).textContent = summary.sections ?? 0;
      document.getElementById(SELECTORS.studentCount).textContent = summary.students ?? 0;

      const tasks = data.assessment_tasks || [];
      if (tasks.length) {
        const completed = tasks.filter(task => this.isTaskComplete(task.status)).length;
        const percent = Math.round((completed / tasks.length) * 100);
        document.getElementById(SELECTORS.assessmentProgress).textContent = `${percent}%`;
      } else {
        document.getElementById(SELECTORS.assessmentProgress).textContent = '0%';
      }
    },

    renderTeachingAssignments(assignments) {
      const container = document.getElementById(SELECTORS.teachingContainer);
      if (!container) return;

      if (!assignments.length) {
        container.innerHTML = this.renderEmptyState(
          'No teaching assignments found',
          'View Schedule'
        );
        return;
      }

      const table = window.panelManager.createSortableTable({
        id: 'instructor-teaching-table',
        columns: [
          { key: 'course', label: 'Course', sortable: true },
          { key: 'sections', label: 'Sections', sortable: true },
          { key: 'students', label: 'Students', sortable: true },
          { key: 'actions', label: 'Actions', sortable: false }
        ],
        data: assignments.map(assignment => {
          const sectionCount = Number(assignment.section_count ?? 0);
          const enrollment = Number(assignment.enrollment ?? 0);
          return {
            course:
              `${assignment.course_number || assignment.course_id || 'Course'} — ${assignment.course_title || ''}`.trim(),
            sections: sectionCount.toString(),
            sections_sort: sectionCount.toString(),
            students: enrollment.toString(),
            students_sort: enrollment.toString(),
            actions:
              '<button class="btn btn-sm btn-outline-primary" onclick="return false;">Gradebook</button>'
          };
        })
      });

      container.innerHTML = '';
      container.appendChild(table);
    },

    renderAssessmentTasks(tasks) {
      const container = document.getElementById(SELECTORS.assessmentContainer);
      if (!container) return;

      if (!tasks.length) {
        container.innerHTML = this.renderEmptyState(
          'No outstanding assessment tasks',
          'Add Assessment'
        );
        return;
      }

      const table = window.panelManager.createSortableTable({
        id: 'instructor-assessment-table',
        columns: [
          { key: 'course', label: 'Course', sortable: true },
          { key: 'section', label: 'Section', sortable: true },
          { key: 'due', label: 'Due Date', sortable: true },
          { key: 'status', label: 'Status', sortable: true },
          { key: 'action', label: 'Action', sortable: false }
        ],
        data: tasks.map(task => {
          const status = (task.status || 'pending').replace(/_/g, ' ');
          const dueDate = task.due_date ? new Date(task.due_date).toLocaleDateString() : '—';
          return {
            course: task.course_number
              ? `${task.course_number} — ${task.course_title || ''}`
              : task.course_title || 'Course',
            section: task.section_id || '—',
            due: dueDate,
            due_sort: task.due_date || '',
            status: status.charAt(0).toUpperCase() + status.slice(1),
            action: `<button class="btn btn-sm btn-outline-success" onclick="return false;">${this.isTaskComplete(task.status) ? 'Review' : 'Enter'}</button>`
          };
        })
      });

      container.innerHTML = '';
      container.appendChild(table);
    },

    renderRecentActivity(tasks) {
      const list = document.getElementById(SELECTORS.activityList);
      if (!list) return;

      if (!tasks.length) {
        list.innerHTML = '<li class="text-muted">No recent activity</li>';
        return;
      }

      const entries = tasks.slice(0, 5).map(task => {
        const status = (task.status || 'pending').replace(/_/g, ' ');
        const due = task.due_date ? new Date(task.due_date).toLocaleDateString() : '—';
        return `<li><strong>${task.course_number || task.course_title || 'Course'}</strong> — ${status} <span class="text-muted">(Due ${due})</span></li>`;
      });

      list.innerHTML = entries.join('');
    },

    renderCourseSummary(assignments, sections) {
      const container = document.getElementById(SELECTORS.summaryContainer);
      if (!container) return;

      if (!assignments.length) {
        container.innerHTML = this.renderEmptyState('No course summary available', 'Refresh');
        return;
      }

      const sectionsByCourse = new Map();
      sections.forEach(section => {
        const courseId = section.course_id;
        if (!courseId) return;
        const list = sectionsByCourse.get(courseId) || [];
        list.push(section);
        sectionsByCourse.set(courseId, list);
      });

      const table = window.panelManager.createSortableTable({
        id: 'instructor-summary-table',
        columns: [
          { key: 'course', label: 'Course', sortable: true },
          { key: 'sections', label: 'Sections', sortable: true },
          { key: 'students', label: 'Students', sortable: true },
          { key: 'progress', label: 'Progress', sortable: true }
        ],
        data: assignments.map(assignment => {
          const courseId = assignment.course_id;
          const courseSections = sectionsByCourse.get(courseId) || [];
          const enrollment = courseSections.reduce(
            (total, section) => total + (Number(section.enrollment) || 0),
            0
          );
          const percent = this.deriveCourseProgress(
            assignment.course_id,
            assignment.sections || []
          );
          return {
            course:
              `${assignment.course_number || assignment.course_id || 'Course'} — ${assignment.course_title || ''}`.trim(),
            sections: (assignment.section_count ?? courseSections.length ?? 0).toString(),
            sections_sort: (assignment.section_count ?? courseSections.length ?? 0).toString(),
            students: enrollment.toString(),
            students_sort: enrollment.toString(),
            progress: `${percent}%`,
            progress_sort: percent
          };
        })
      });

      container.innerHTML = '';
      container.appendChild(table);
    },

    deriveCourseProgress(courseId, sections) {
      if (!sections || !sections.length) return 0;
      const completed = sections.filter(section => this.isTaskComplete(section.status)).length;
      return Math.round((completed / sections.length) * 100);
    },

    updateLastUpdated(timestamp) {
      const target = document.getElementById(SELECTORS.lastUpdated);
      if (!target) return;
      const value = timestamp ? new Date(timestamp).toLocaleString() : new Date().toLocaleString();
      target.textContent = `Last updated: ${value}`;
    },

    setLoading(containerId, message) {
      const container = document.getElementById(containerId);
      if (!container) return;
      container.innerHTML = `
        <div class="panel-loading">
          <div class="spinner-border spinner-border-sm"></div>
          ${message}
        </div>
      `;
    },

    showError(containerId, message) {
      const container = document.getElementById(containerId);
      if (!container) return;
      container.innerHTML = `
        <div class="alert alert-danger mb-0">
          <i class="fas fa-exclamation-triangle me-1"></i>${message}
        </div>
      `;
    },

    renderEmptyState(message, actionLabel) {
      return `
        <div class="panel-empty">
          <div class="panel-empty-icon">📌</div>
          <p>${message}</p>
          <button class="btn btn-primary btn-sm" onclick="return false;">${actionLabel}</button>
        </div>
      `;
    },

    isTaskComplete(status) {
      if (!status) return false;
      const normalized = status.toLowerCase();
      return normalized === 'completed' || normalized === 'done' || normalized === 'complete';
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for panelManager to be initialized
    setTimeout(() => {
      if (typeof window.panelManager === 'undefined') {
        // eslint-disable-next-line no-console
        console.warn('Panel manager not initialized');
        return;
      }
      InstructorDashboard.init();
      window.InstructorDashboard = InstructorDashboard;
    }, 100);
  });
})();
