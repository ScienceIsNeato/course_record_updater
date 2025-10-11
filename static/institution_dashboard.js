(function () {
  const API_ENDPOINT = '/api/dashboard/data';
  const SELECTORS = {
    institutionName: 'institutionName',
    currentTerm: 'currentTermName',
    programCount: 'programCount',
    courseCount: 'courseCount',
    facultyCount: 'facultyCount',
    sectionCount: 'sectionCount',
    lastUpdated: 'institutionLastUpdated',
    refreshButton: 'institutionRefreshButton',
    programContainer: 'programManagementContainer',
    facultyContainer: 'facultyOverviewContainer',
    sectionContainer: 'courseSectionContainer',
    assessmentContainer: 'assessmentProgressContainer'
  };

  const InstitutionDashboard = {
    cache: null,
    lastFetch: 0,
    refreshInterval: 5 * 60 * 1000,
    intervalId: null,

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
      this.intervalId = setInterval(() => this.loadData({ silent: true }), this.refreshInterval);

      // Cleanup on page unload
      window.addEventListener('beforeunload', () => this.cleanup());
      window.addEventListener('pagehide', () => this.cleanup());
    },

    cleanup() {
      if (this.intervalId) {
        clearInterval(this.intervalId);
        this.intervalId = null;
      }
    },

    async refresh() {
      return this.loadData({ silent: false });
    },

    async loadData(options = {}) {
      const { silent = false } = options;
      if (!silent) {
        this.setLoading(SELECTORS.programContainer, 'Loading programs...');
        this.setLoading(SELECTORS.facultyContainer, 'Loading faculty...');
        this.setLoading(SELECTORS.sectionContainer, 'Loading sections...');
        this.setLoading(SELECTORS.assessmentContainer, 'Loading assessment data...');
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
        console.error('Institution dashboard load error:', error);
        this.showError(SELECTORS.programContainer, 'Unable to load program data');
        this.showError(SELECTORS.facultyContainer, 'Unable to load faculty data');
        this.showError(SELECTORS.sectionContainer, 'Unable to load section data');
        this.showError(SELECTORS.assessmentContainer, 'Unable to load assessment progress');
      }
    },

    render(data) {
      this.updateHeader(data);
      this.renderPrograms(data.program_overview || [], data.programs || []);
      this.renderCourses(data.courses || []);
      this.renderFaculty(data.faculty_assignments || [], data.faculty || []);
      this.renderSections(data.sections || [], data.courses || [], data.terms || []);
      this.renderAssessment(data.program_overview || []);
      this.updateLastUpdated(data.metadata?.last_updated);
    },

    updateHeader(data) {
      const summary = data.summary || {};
      document.getElementById(SELECTORS.programCount).textContent = summary.programs ?? 0;
      document.getElementById(SELECTORS.courseCount).textContent = summary.courses ?? 0;
      document.getElementById(SELECTORS.facultyCount).textContent = summary.faculty ?? 0;
      document.getElementById(SELECTORS.sectionCount).textContent = summary.sections ?? 0;

      const institutionName =
        data.institutions?.[0]?.name ||
        document.getElementById(SELECTORS.institutionName).textContent;
      document.getElementById(SELECTORS.institutionName).textContent =
        institutionName || 'Institution Overview';

      const term = (data.terms || []).find(item => item?.active) || (data.terms || [])[0];
      document.getElementById(SELECTORS.currentTerm).textContent = term?.name || '--';
    },

    renderPrograms(programOverview, rawPrograms) {
      const container = document.getElementById(SELECTORS.programContainer);
      if (!container) return;

      if (!programOverview.length && !rawPrograms.length) {
        container.innerHTML = this.renderEmptyState('No programs found', 'Add Program');
        return;
      }

      const programs = programOverview.length
        ? programOverview
        : rawPrograms.map(program => ({
            program_id: program.program_id || program.id,
            program_name: program.name,
            course_count: program.course_count || 0,
            faculty_count: program.faculty_count || 0,
            student_count: program.student_count || 0,
            section_count: program.section_count || 0,
            assessment_progress: program.assessment_progress || {
              percent_complete: 0,
              completed: 0,
              total: 0
            }
          }));

      const table = window.panelManager.createSortableTable({
        id: 'institution-programs-table',
        columns: [
          { key: 'program', label: 'Program', sortable: true },
          { key: 'courses', label: 'Courses', sortable: true },
          { key: 'faculty', label: 'Faculty', sortable: true },
          { key: 'students', label: 'Students', sortable: true },
          { key: 'sections', label: 'Sections', sortable: true },
          { key: 'progress', label: 'Progress', sortable: true },
          { key: 'actions', label: 'Actions', sortable: false }
        ],
        data: programs.map(program => {
          const progress = program.assessment_progress || {};
          const percent =
            typeof progress.percent_complete === 'number' ? progress.percent_complete : 0;
          const completed = progress.completed ?? 0;
          const total = progress.total ?? 0;
          const courseCount = Number(program.course_count ?? program.courses?.length ?? 0);
          const facultyCount = Number(
            program.faculty_count ?? (program.faculty ? program.faculty.length : 0)
          );
          const studentCount = Number(program.student_count ?? 0);
          const sectionCount = Number(program.section_count ?? 0);

          return {
            program: program.program_name || program.name || 'Unnamed Program',
            courses: courseCount.toString(),
            courses_sort: courseCount.toString(),
            faculty: facultyCount.toString(),
            faculty_sort: facultyCount.toString(),
            students: studentCount.toString(),
            students_sort: studentCount.toString(),
            sections: sectionCount.toString(),
            sections_sort: sectionCount.toString(),
            progress: `<div class="progress">
                <div class="progress-bar" role="progressbar" style="width: ${Math.min(percent, 100)}%">${percent}%</div>
              </div>
              <small class="text-muted">${completed}/${total} complete</small>`,
            progress_sort: percent,
            actions:
              '<button class="btn btn-sm btn-outline-primary" onclick="return false;">Manage</button>'
          };
        })
      });

      container.innerHTML = '';
      container.appendChild(table);
    },

    renderFaculty(assignments, fallbackFaculty) {
      const container = document.getElementById(SELECTORS.facultyContainer);
      if (!container) return;

      const facultyRecords = assignments.length
        ? assignments
        : fallbackFaculty.map(member => ({
            user_id: member.user_id,
            full_name:
              member.full_name ||
              [member.first_name, member.last_name].filter(Boolean).join(' ') ||
              member.email,
            program_ids: member.program_ids || [],
            course_count: member.course_count || 0,
            section_count: member.section_count || 0,
            enrollment: member.enrollment || 0,
            role: member.role || 'instructor'
          }));

      if (!facultyRecords.length) {
        container.innerHTML = this.renderEmptyState('No faculty assigned yet', 'Invite Faculty');
        return;
      }

      const table = window.panelManager.createSortableTable({
        id: 'institution-faculty-table',
        columns: [
          { key: 'name', label: 'Faculty Name', sortable: true },
          { key: 'programs', label: 'Programs', sortable: true },
          { key: 'courses', label: 'Courses', sortable: true },
          { key: 'sections', label: 'Sections', sortable: true },
          { key: 'students', label: 'Students', sortable: true },
          { key: 'role', label: 'Role', sortable: true }
        ],
        data: facultyRecords.map(record => {
          const courseCount = Number(record.course_count ?? 0);
          const sectionCount = Number(record.section_count ?? 0);
          const studentCount = Number(record.enrollment ?? 0);

          return {
            name: record.full_name || record.name || 'Instructor',
            programs:
              (record.program_summaries || [])
                .map(program => program?.program_name)
                .filter(Boolean)
                .join(', ') ||
              (record.program_ids || []).join(', ') ||
              '—',
            courses: courseCount.toString(),
            courses_sort: courseCount.toString(),
            sections: sectionCount.toString(),
            sections_sort: sectionCount.toString(),
            students: studentCount.toString(),
            students_sort: studentCount.toString(),
            role: (record.role || 'instructor').replace(/_/g, ' ')
          };
        })
      });

      container.innerHTML = '';
      container.appendChild(table);
    },

    renderSections(sections, courses, _terms) {
      const container = document.getElementById(SELECTORS.sectionContainer);
      if (!container) return;

      if (!sections.length) {
        container.innerHTML = this.renderEmptyState('No sections scheduled', 'Add Section');
        return;
      }

      const courseLookup = new Map();
      courses.forEach(course => {
        const courseId = course.course_id || course.id;
        if (courseId) {
          courseLookup.set(courseId, course);
        }
      });

      const table = window.panelManager.createSortableTable({
        id: 'institution-sections-table',
        columns: [
          { key: 'course', label: 'Course', sortable: true },
          { key: 'section', label: 'Section', sortable: true },
          { key: 'faculty', label: 'Faculty', sortable: true },
          { key: 'enrollment', label: 'Enrollment', sortable: true },
          { key: 'status', label: 'Status', sortable: true },
          { key: 'actions', label: 'Actions', sortable: false }
        ],
        data: sections.map(section => {
          const course = courseLookup.get(section.course_id) || {};
          const title = course.course_title || course.title || course.name || section.course_name;
          const number = course.course_number || course.number || '';
          const instructor = section.instructor_name || section.instructor || 'Unassigned';
          const enrollment = section.enrollment ?? 0;
          const status = (section.status || 'scheduled').replace(/_/g, ' ');
          const safe = val =>
            val === undefined || val === null ? '' : String(val).replace(/"/g, '&quot;');
          const sectionId = section.section_id || section.id || '';
          const sectionDataLiteral = `{"section_number":"${safe(section.section_number)}","instructor_id":"${safe(section.instructor_id)}","enrollment":${Number(enrollment) || 0},"status":"${safe(section.status || 'assigned')}"}`;
          return {
            course: number ? `${number} — ${title || ''}` : title || 'Course',
            section: section.section_number || section.section_id || '—',
            faculty: instructor,
            enrollment: enrollment.toString(),
            enrollment_sort: enrollment.toString(),
            status: status.charAt(0).toUpperCase() + status.slice(1),
            actions: `<button class="btn btn-sm btn-outline-primary" onclick="window.openEditSectionModal('${safe(sectionId)}', ${sectionDataLiteral}); return false;">Edit</button>`
          };
        })
      });

      container.innerHTML = '';
      container.appendChild(table);
    },

    renderCourses(courses) {
      // Reuse program container area for a simple courses table if present
      // If the program container is not on this page, skip rendering courses
      const coursesContainer = document.getElementById('courseManagementContainer');
      if (!coursesContainer) return;

      if (!courses.length) {
        coursesContainer.innerHTML = this.renderEmptyState('No courses found', 'Add Course');
        return;
      }

      const table = window.panelManager.createSortableTable({
        id: 'institution-courses-table',
        columns: [
          { key: 'number', label: 'Course Number', sortable: true },
          { key: 'title', label: 'Title', sortable: true },
          { key: 'credits', label: 'Credits', sortable: true },
          { key: 'department', label: 'Department', sortable: true },
          { key: 'actions', label: 'Actions', sortable: false }
        ],
        data: courses.map(course => {
          const courseId = course.course_id || course.id || '';
          const safe = val =>
            val === undefined || val === null ? '' : String(val).replace(/"/g, '&quot;');
          const courseDataLiteral = `{"course_number":"${safe(course.course_number)}","course_title":"${safe(course.course_title || course.title)}","department":"${safe(course.department)}","credit_hours":${Number(course.credit_hours || 0)},"program_ids":${JSON.stringify(course.program_ids || [])},"active":${course.active !== false}}`;
          return {
            number: course.course_number || '-',
            title: course.course_title || course.title || '-',
            credits: (course.credit_hours ?? '-').toString(),
            credits_sort: (course.credit_hours ?? 0).toString(),
            department: course.department || '-',
            actions: `<button class="btn btn-sm btn-outline-primary" onclick="window.openEditCourseModal('${safe(courseId)}', ${courseDataLiteral}); return false;">Edit</button>`
          };
        })
      });

      coursesContainer.innerHTML = '';
      coursesContainer.appendChild(table);
    },

    renderAssessment(programOverview) {
      const container = document.getElementById(SELECTORS.assessmentContainer);
      if (!container) return;

      if (!programOverview.length) {
        container.innerHTML = this.renderEmptyState(
          'No assessment data available',
          'Send Reminder'
        );
        return;
      }

      const table = window.panelManager.createSortableTable({
        id: 'institution-assessment-table',
        columns: [
          { key: 'program', label: 'Program', sortable: true },
          { key: 'courses', label: 'Courses', sortable: true },
          { key: 'completed', label: 'Complete', sortable: true },
          { key: 'total', label: 'Total', sortable: true },
          { key: 'percent', label: 'Progress', sortable: true }
        ],
        data: programOverview.map(program => {
          const progress = program.assessment_progress || {};
          const completed = progress.completed ?? 0;
          const total = progress.total ?? 0;
          const percent = progress.percent_complete ?? 0;
          return {
            program: program.program_name || program.name || 'Program',
            courses: (program.course_count ?? 0).toString(),
            courses_sort: (program.course_count ?? 0).toString(),
            completed: completed.toString(),
            completed_sort: completed.toString(),
            total: total.toString(),
            total_sort: total.toString(),
            percent: `${percent}%`,
            percent_sort: percent
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
      InstitutionDashboard.init();
      window.InstitutionDashboard = InstitutionDashboard;
    }, 100);
  });

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = InstitutionDashboard;
  }
})();
