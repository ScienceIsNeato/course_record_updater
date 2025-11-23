/* global setLoadingState, setErrorState */
(function () {
  const API_ENDPOINT = '/api/dashboard/data';
  const SELECTORS = {
    title: 'programAdminTitle',
    courseCount: 'programCourseCount',
    facultyCount: 'programFacultyCount',
    studentCount: 'programStudentCount',
    sectionCount: 'programSectionCount',
    lastUpdated: 'programLastUpdated',
    refreshButton: 'programRefreshButton',
    coursesContainer: 'programCoursesContainer',
    facultyContainer: 'programFacultyContainer',
    cloContainer: 'programCloContainer',
    assessmentContainer: 'programAssessmentContainer'
  };

  const ProgramDashboard = {
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

    async refresh() {
      return this.loadData({ silent: false });
    },

    async loadData(options = {}) {
      const { silent = false } = options;
      if (!silent) {
        this.setLoading(SELECTORS.coursesContainer, 'Loading courses...');
        this.setLoading(SELECTORS.facultyContainer, 'Loading faculty assignments...');
        this.setLoading(SELECTORS.cloContainer, 'Loading learning outcomes...');
        this.setLoading(SELECTORS.assessmentContainer, 'Loading assessment results...');
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
        globalThis.dashboardDataCache = this.cache;
        this.lastFetch = Date.now();
        this.render(this.cache);
      } catch (error) {
        // eslint-disable-next-line no-console
        console.warn('Program dashboard load error:', error);
        this.showError(SELECTORS.coursesContainer, 'Unable to load course data');
        this.showError(SELECTORS.facultyContainer, 'Unable to load faculty data');
        this.showError(SELECTORS.cloContainer, 'Unable to load learning outcomes');
        this.showError(SELECTORS.assessmentContainer, 'Unable to load assessment results');
      }
    },

    render(data) {
      this.updateHeader(data);
      this.renderCourses(data.courses || [], data.sections || [], data.program_overview || []);
      this.renderFaculty(data.faculty_assignments || []);
      this.renderClos(data.courses || [], data.program_overview || []);
      this.renderAssessment(data.program_overview || []);
      const lastUpdated =
        data.metadata && data.metadata.last_updated ? data.metadata.last_updated : null;
      this.updateLastUpdated(lastUpdated);
    },

    updateHeader(data) {
      const summary = data.summary || {};
      document.getElementById(SELECTORS.courseCount).textContent = summary.courses ?? 0;
      document.getElementById(SELECTORS.facultyCount).textContent = summary.faculty ?? 0;
      document.getElementById(SELECTORS.studentCount).textContent = summary.students ?? 0;
      document.getElementById(SELECTORS.sectionCount).textContent = summary.sections ?? 0;

      const programs = data.programs || [];
      if (programs.length === 1) {
        const program = programs[0];
        document.getElementById(SELECTORS.title).textContent =
          `${program.name || 'Program'} Administration`;
      } else if (programs.length > 1) {
        const names = programs
          .map(p => p.name)
          .filter(Boolean)
          .slice(0, 3)
          .join(', ');
        document.getElementById(SELECTORS.title).textContent =
          `${programs.length} Programs — ${names}${programs.length > 3 ? '…' : ''}`;
      } else {
        document.getElementById(SELECTORS.title).textContent = 'Program Overview';
      }
    },

    renderCourses(courses, sections, programOverview) {
      const container = document.getElementById(SELECTORS.coursesContainer);
      if (!container) return;

      const courseMap = new Map();
      courses.forEach(course => {
        const id = course.course_id || course.id;
        if (id && !courseMap.has(id)) {
          courseMap.set(id, course);
        }
      });

      if (!courseMap.size) {
        container.innerHTML = this.renderEmptyState(
          'No courses found for this program',
          'Add Course'
        );
        return;
      }

      const sectionsByCourse = this.groupBy(sections, section => section.course_id || section.id);
      const progressByProgram = new Map(
        (programOverview || []).map(item => [item.program_id, item.assessment_progress])
      );

      const table = globalThis.panelManager.createSortableTable({
        id: 'program-courses-table',
        columns: [
          { key: 'course', label: 'Course', sortable: true },
          { key: 'sections', label: 'Sections', sortable: true },
          { key: 'enrollment', label: 'Students', sortable: true },
          { key: 'program', label: 'Program', sortable: true },
          { key: 'progress', label: 'Progress', sortable: true },
          { key: 'actions', label: 'Actions', sortable: false }
        ],
        data: Array.from(courseMap.values()).map(course => {
          const courseId = course.course_id || course.id;
          const programIdsFirst =
            course.program_ids && course.program_ids[0] ? course.program_ids[0] : null;
          const programId = course.program_id || programIdsFirst;
          const programProgress = progressByProgram.get(programId) || {};
          const courseSections = sectionsByCourse.get(courseId) || [];
          const sectionCount = courseSections.length;
          const enrollment = courseSections.reduce(
            (total, section) => total + (Number(section.enrollment) || 0),
            0
          );
          const percent = programProgress.percent_complete ?? 0;
          const completed = programProgress.completed ?? 0;
          const total = programProgress.total ?? 0;

          return {
            course: `${course.course_number || course.number || ''}`.trim()
              ? `${course.course_number || course.number} — ${course.course_title || course.title || course.name || ''}`
              : course.course_title || course.title || course.name || 'Course',
            sections: sectionCount.toString(),
            sections_sort: sectionCount.toString(),
            enrollment: enrollment.toString(),
            enrollment_sort: enrollment.toString(),
            program: course.program_name || course.program || 'Program',
            progress: `<div class="progress">
                <div class="progress-bar bg-success" role="progressbar" style="width: ${Math.min(percent, 100)}%">${percent}%</div>
              </div>
              <small class="text-muted">${completed}/${total} complete</small>`,
            progress_sort: percent,
            actions: `<button class="btn btn-sm btn-outline-primary" onclick="return false;">
                <i class="fas fa-edit"></i>
              </button>`
          };
        })
      });

      container.innerHTML = '';
      container.appendChild(table);
    },

    renderFaculty(assignments) {
      const container = document.getElementById(SELECTORS.facultyContainer);
      if (!container) return;

      if (!assignments.length) {
        container.innerHTML = this.renderEmptyState('No faculty assignments yet', 'Assign Courses');
        return;
      }

      const table = globalThis.panelManager.createSortableTable({
        id: 'program-faculty-table',
        columns: [
          { key: 'name', label: 'Faculty', sortable: true },
          { key: 'courses', label: 'Courses', sortable: true },
          { key: 'sections', label: 'Sections', sortable: true },
          { key: 'students', label: 'Students', sortable: true },
          { key: 'programs', label: 'Programs', sortable: true }
        ],
        data: assignments.map(record => {
          const courseCount = Number(record.course_count ?? 0);
          const sectionCount = Number(record.section_count ?? 0);
          const studentCount = Number(record.enrollment ?? 0);
          return {
            name: record.full_name || record.name || 'Instructor',
            courses: courseCount.toString(),
            courses_sort: courseCount.toString(),
            sections: sectionCount.toString(),
            sections_sort: sectionCount.toString(),
            students: studentCount.toString(),
            students_sort: studentCount.toString(),
            programs:
              (record.program_summaries || [])
                .map(program => (program && program.program_name ? program.program_name : null))
                .filter(Boolean)
                .join(', ') ||
              (record.program_ids || []).join(', ') ||
              '—'
          };
        })
      });

      container.innerHTML = '';
      container.appendChild(table);
    },

    renderClos(courses, programOverview) {
      const container = document.getElementById(SELECTORS.cloContainer);
      if (!container) return;

      if (!courses.length) {
        container.innerHTML = this.renderEmptyState(
          'No learning outcomes configured yet',
          'Add CLO'
        );
        return;
      }

      const progressByProgram = new Map(
        (programOverview || []).map(item => [item.program_id, item.assessment_progress])
      );

      const table = globalThis.panelManager.createSortableTable({
        id: 'program-clo-table',
        columns: [
          { key: 'course', label: 'Course', sortable: true },
          { key: 'clos', label: 'CLOs', sortable: true },
          { key: 'status', label: 'Status', sortable: true },
          { key: 'progress', label: 'Progress', sortable: true },
          { key: 'actions', label: 'Actions', sortable: false }
        ],
        data: courses.map(course => {
          const programIdsFirst =
            course.program_ids && course.program_ids[0] ? course.program_ids[0] : null;
          const programId = course.program_id || programIdsFirst;
          const progress = progressByProgram.get(programId) || {};
          const percent = progress.percent_complete ?? 0;
          const cloCount = (course.clo_count ?? (course.clos ? course.clos.length : 0)) || 0;
          // Determine status based on completion percentage
          let status;
          if (percent >= 75) {
            status = 'On Track';
          } else if (percent >= 30) {
            status = 'In Progress';
          } else {
            status = 'Needs Attention';
          }
          return {
            course:
              `${course.course_number || course.number || course.course_id || 'Course'} — ${course.course_title || course.title || course.name || ''}`.trim(),
            clos: cloCount.toString(),
            clos_sort: cloCount.toString(),
            status,
            progress: `${percent}%`,
            progress_sort: percent,
            actions:
              '<button class="btn btn-sm btn-outline-secondary" onclick="return false;">Manage</button>'
          };
        })
      });

      container.innerHTML = '';
      container.appendChild(table);
    },

    renderAssessment(programOverview) {
      const container = document.getElementById(SELECTORS.assessmentContainer);
      if (!container) return;

      if (!programOverview.length) {
        container.innerHTML = this.renderEmptyState(
          'No assessment activity recorded',
          'Open Assessment Report'
        );
        return;
      }

      const table = globalThis.panelManager.createSortableTable({
        id: 'program-assessment-table',
        columns: [
          { key: 'program', label: 'Program', sortable: true },
          { key: 'courses', label: 'Courses', sortable: true },
          { key: 'sections', label: 'Sections', sortable: true },
          { key: 'students', label: 'Students', sortable: true },
          { key: 'progress', label: 'Progress', sortable: true }
        ],
        data: programOverview.map(item => {
          const percentComplete =
            item.assessment_progress && item.assessment_progress.percent_complete !== undefined
              ? item.assessment_progress.percent_complete
              : 0;
          const percent = percentComplete ?? 0;
          const studentCount = item.student_count ?? 0;
          const sectionCount = item.section_count ?? 0;
          return {
            program: item.program_name || 'Program',
            courses: (item.course_count ?? 0).toString(),
            courses_sort: (item.course_count ?? 0).toString(),
            sections: sectionCount.toString(),
            sections_sort: sectionCount.toString(),
            students: studentCount.toString(),
            students_sort: studentCount.toString(),
            progress: `${percent}%`,
            progress_sort: percent
          };
        })
      });

      container.innerHTML = '';
      container.appendChild(table);
    },

    updateLastUpdated(timestamp) {
      const target = document.getElementById(SELECTORS.lastUpdated);
      if (!target) return;
      const value = timestamp ? new Date(timestamp).toLocaleString() : new Date().toLocaleString();
      target.textContent = `Last updated: ${value}`;
    },

    setLoading(containerId, message) {
      setLoadingState(containerId, message);
    },

    showError(containerId, message) {
      setErrorState(containerId, message);
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

    groupBy(items, keyFn) {
      const map = new Map();
      items.forEach(item => {
        const key = keyFn(item);
        if (!key) return;
        const group = map.get(key) || [];
        group.push(item);
        map.set(key, group);
      });
      return map;
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for panelManager to be initialized
    setTimeout(() => {
      if (typeof globalThis.panelManager === 'undefined') {
        // eslint-disable-next-line no-console
        console.warn('Panel manager not initialized');
        return;
      }
      ProgramDashboard.init();
      globalThis.ProgramDashboard = ProgramDashboard;
    }, 100);
  });

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = ProgramDashboard;
  }
})();
