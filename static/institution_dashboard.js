/* global setLoadingState, setErrorState */
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

  /**
   * Escape HTML to prevent XSS
   */
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

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

      // Event delegation for action buttons
      document.addEventListener('click', e => {
        const target = e.target.closest('[data-action]');
        if (!target) return;

        const action = target.getAttribute('data-action');
        if (action === 'edit-section') {
          e.preventDefault();
          e.stopPropagation();
          this.handleEditSection(target);
        } else if (action === 'send-reminder') {
          e.preventDefault();
          e.stopPropagation();
          const instructorId = target.getAttribute('data-instructor-id');
          const courseId = target.getAttribute('data-course-id');
          const instructor = target.getAttribute('data-instructor');
          const courseNumber = target.getAttribute('data-course-number');
          if (instructorId && courseId && instructor && courseNumber) {
            this.sendCourseReminder(instructorId, courseId, instructor, courseNumber);
          }
        } else if (action === 'edit-course') {
          e.preventDefault();
          e.stopPropagation();
          this.handleEditCourse(target);
        } else if (action === 'delete-program') {
          e.preventDefault();
          e.stopPropagation();
          const programId = target.getAttribute('data-program-id');
          const programName = target.getAttribute('data-program-name');
          if (programId && programName && typeof globalThis.deleteProgram === 'function') {
            globalThis.deleteProgram(programId, programName);
          }
        }
      });

      this.loadData();
      this.intervalId = setInterval(() => this.loadData({ silent: true }), this.refreshInterval);

      // Cleanup on page unload
      globalThis.addEventListener('beforeunload', () => this.cleanup());
      globalThis.addEventListener('pagehide', () => this.cleanup());
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
        this.setLoading('termManagementContainer', 'Loading terms...');
        this.setLoading('offeringManagementContainer', 'Loading offerings...');
        this.setLoading('outcomeManagementContainer', 'Loading outcomes...');
        this.setLoading(SELECTORS.facultyContainer, 'Loading faculty...');
        this.setLoading(SELECTORS.sectionContainer, 'Loading sections...');
        this.setLoading(SELECTORS.assessmentContainer, 'Loading assessment data...');
        this.setLoading('institutionCloAuditContainer', 'Loading audit data...');
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
      this.renderTerms(data.terms || []);
      this.renderOfferings(data.offerings || [], data.courses || [], data.terms || []);
      this.renderCLOs(data.clos || []);
      this.renderFaculty(data.faculty_assignments || [], data.faculty || []);
      this.renderSections(data.sections || [], data.courses || [], data.terms || []);
      this.renderAssessment(data.program_overview || []);
      this.renderCLOAudit(data.clos || []);
      const lastUpdated =
        data.metadata && data.metadata.last_updated ? data.metadata.last_updated : null;
      this.updateLastUpdated(lastUpdated);
    },

    updateHeader(data) {
      const summary = data.summary || {};
      document.getElementById(SELECTORS.programCount).textContent = summary.programs ?? 0;
      document.getElementById(SELECTORS.courseCount).textContent = summary.courses ?? 0;
      document.getElementById(SELECTORS.facultyCount).textContent = summary.faculty ?? 0;
      document.getElementById(SELECTORS.sectionCount).textContent = summary.sections ?? 0;

      const institutionName =
        (data.institutions && data.institutions[0] && data.institutions[0].name) ||
        document.getElementById(SELECTORS.institutionName).textContent;
      document.getElementById(SELECTORS.institutionName).textContent =
        institutionName || 'Institution Overview';

      const term = (data.terms || []).find(item => item && item.active) || (data.terms || [])[0];
      const termName = term && term.name ? term.name : '--';
      document.getElementById(SELECTORS.currentTerm).textContent = termName;
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

      const table = globalThis.panelManager.createSortableTable({
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
          const coursesLength =
            program.courses && program.courses.length ? program.courses.length : 0;
          const courseCount = Number(program.course_count ?? coursesLength ?? 0);
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
            actions: `
              <button class="btn btn-sm btn-outline-primary me-1" onclick="return false;">Manage</button>
              <button class="btn btn-sm btn-outline-danger" 
                      data-action="delete-program"
                      data-program-id="${escapeHtml(String(program.program_id))}"
                      data-program-name="${escapeHtml(program.program_name || program.name || 'Unnamed Program')}">
                <i class="fas fa-trash"></i>
              </button>
            `
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

      const table = globalThis.panelManager.createSortableTable({
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
                .map(program => (program && program.program_name ? program.program_name : null))
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
            role: this.formatRole(record.role || 'instructor')
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

      const table = globalThis.panelManager.createSortableTable({
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
          const sectionId = section.section_id || section.id || '';
          const sectionData = {
            section_number: section.section_number || '',
            instructor_id: section.instructor_id || '',
            enrollment: Number(enrollment) || 0,
            status: section.status || 'assigned'
          };
          const sectionDataJson = JSON.stringify(sectionData).replace(/"/g, '&quot;');
          const courseId = section.course_id || '';
          const instructorId = section.instructor_id || '';
          const instructorEmail = section.instructor_email || '';

          // Build action buttons - use data attributes instead of onclick
          const sectionIdEscaped = escapeHtml(String(sectionId));
          const courseIdEscaped = escapeHtml(String(courseId));
          const instructorIdEscaped = escapeHtml(String(instructorId));
          const instructorEscaped = escapeHtml(String(instructor));
          const numberEscaped = escapeHtml(String(number));

          let actionsHtml = `<button class="btn btn-sm btn-outline-primary" data-action="edit-section" data-section-id="${sectionIdEscaped}" data-section-data="${sectionDataJson}">Edit</button>`;

          // Add reminder button if instructor is assigned
          if (instructorId && instructorEmail) {
            actionsHtml += ` <button class="btn btn-sm btn-outline-secondary" 
              data-action="send-reminder" 
              data-instructor-id="${instructorIdEscaped}" 
              data-course-id="${courseIdEscaped}" 
              data-instructor="${instructorEscaped}" 
              data-course-number="${numberEscaped}"
              title="Send reminder to ${instructorEscaped}">
              <i class="fas fa-envelope"></i>
            </button>`;
          }

          return {
            course: number ? `${number} — ${title || ''}` : title || 'Course',
            section: section.section_number || section.section_id || '—',
            faculty: instructor,
            enrollment: enrollment.toString(),
            enrollment_sort: enrollment.toString(),
            status: status.charAt(0).toUpperCase() + status.slice(1),
            actions: actionsHtml
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

      const table = globalThis.panelManager.createSortableTable({
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
          const courseData = {
            course_number: course.course_number || '',
            course_title: course.course_title || course.title || '',
            department: course.department || '',
            credit_hours: Number(course.credit_hours || 0),
            program_ids: course.program_ids || [],
            active: course.active !== false
          };
          const courseDataJson = JSON.stringify(courseData).replace(/"/g, '&quot;');
          return {
            number: course.course_number || '-',
            title: course.course_title || course.title || '-',
            credits: (course.credit_hours ?? '-').toString(),
            credits_sort: (course.credit_hours ?? 0).toString(),
            department: course.department || '-',
            actions: `<button class="btn btn-sm btn-outline-primary" data-action="edit-course" data-course-id="${escapeHtml(String(courseId))}" data-course-data="${courseDataJson}">Edit</button>`
          };
        })
      });

      coursesContainer.innerHTML = '';
      coursesContainer.appendChild(table);
    },

    renderTerms(terms) {
      const container = document.getElementById('termManagementContainer');
      if (!container) return;

      if (!terms || !terms.length) {
        container.innerHTML = this.renderEmptyState('No terms defined', 'Add Term');
        return;
      }

      const table = globalThis.panelManager.createSortableTable({
        id: 'institution-terms-table',
        columns: [
          { key: 'term', label: 'Term Name', sortable: true },
          { key: 'start_date', label: 'Start Date', sortable: true },
          { key: 'end_date', label: 'End Date', sortable: true },
          { key: 'status', label: 'Status', sortable: true },
          { key: 'offerings', label: 'Offerings', sortable: true }
        ],
        data: terms.map(term => {
          // Format dates nicely
          const startDate = term.start_date
            ? new Date(term.start_date).toLocaleDateString()
            : 'N/A';
          const endDate = term.end_date ? new Date(term.end_date).toLocaleDateString() : 'N/A';

          return {
            term: term.term_name || term.name || 'Unnamed Term',
            start_date: startDate,
            start_date_sort: term.start_date || '',
            end_date: endDate,
            end_date_sort: term.end_date || '',
            status:
              term.active || term.is_active
                ? '<span class="badge bg-success">Active</span>'
                : '<span class="badge bg-secondary">Inactive</span>',
            status_sort: term.active || term.is_active ? '1' : '0',
            offerings: (term.offering_count || 0).toString(),
            offerings_sort: (term.offering_count || 0).toString()
          };
        })
      });

      container.innerHTML = '';
      container.appendChild(table);
    },

    renderOfferings(offerings, courses, terms) {
      const container = document.getElementById('offeringManagementContainer');
      if (!container) return;

      if (!offerings || !offerings.length) {
        container.innerHTML = this.renderEmptyState(
          'No course offerings scheduled',
          'Add Offering'
        );
        return;
      }

      const courseLookup = new Map();
      courses.forEach(course => {
        const courseId = course.course_id || course.id;
        if (courseId) {
          courseLookup.set(courseId, course);
        }
      });

      const termLookup = new Map();
      terms.forEach(term => {
        const termId = term.term_id || term.id;
        if (termId) {
          termLookup.set(termId, term);
        }
      });

      const table = globalThis.panelManager.createSortableTable({
        id: 'institution-offerings-table',
        columns: [
          { key: 'course', label: 'Course', sortable: true },
          { key: 'term', label: 'Term', sortable: true },
          { key: 'sections', label: 'Sections', sortable: true },
          { key: 'enrollment', label: 'Enrollment', sortable: true },
          { key: 'status', label: 'Status', sortable: true }
        ],
        data: offerings.map(offering => {
          const course = courseLookup.get(offering.course_id) || {};
          const term = termLookup.get(offering.term_id) || {};
          const sectionCount = offering.section_count || 0;
          const enrollmentCount = offering.total_enrollment || 0;

          return {
            course: course.course_number || 'Unknown Course',
            term: term.term_name || term.name || 'Unknown Term',
            sections: sectionCount.toString(),
            sections_sort: sectionCount.toString(),
            enrollment: enrollmentCount.toString(),
            enrollment_sort: enrollmentCount.toString(),
            status:
              offering.status === 'active'
                ? '<span class="badge bg-success">Active</span>'
                : '<span class="badge bg-secondary">Inactive</span>',
            status_sort: offering.status === 'active' ? '1' : '0'
          };
        })
      });

      container.innerHTML = '';
      container.appendChild(table);
    },

    renderCLOs(clos) {
      const container = document.getElementById('outcomeManagementContainer');
      if (!container) return;

      if (!clos || !clos.length) {
        container.innerHTML = this.renderEmptyState('No CLOs defined', 'Add Outcome');
        return;
      }

      const table = globalThis.panelManager.createSortableTable({
        id: 'institution-clos-table',
        columns: [
          { key: 'course', label: 'Course', sortable: true },
          { key: 'clo_number', label: 'CLO #', sortable: true },
          { key: 'description', label: 'Description', sortable: true },
          { key: 'status', label: 'Status', sortable: true }
        ],
        data: clos.map(clo => {
          return {
            course: clo.course_number || 'Unknown',
            clo_number: clo.clo_number || '?',
            clo_number_sort: clo.clo_number || '0',
            description: clo.description || 'No description',
            status: clo.active
              ? '<span class="badge bg-success">Active</span>'
              : '<span class="badge bg-secondary">Inactive</span>',
            status_sort: clo.active ? '1' : '0'
          };
        })
      });

      container.innerHTML = '';
      container.appendChild(table);
    },

    renderCLOAudit(clos) {
      const container = document.getElementById('institutionCloAuditContainer');
      if (!container) return;

      if (!clos || !clos.length) {
        container.innerHTML = this.renderEmptyState('No CLOs pending audit', 'Review Submissions');
        return;
      }

      // For now, show a summary - full audit workflow is in dedicated audit page
      const summary = `
        <div class="alert alert-info">
          <h6 class="alert-heading"><i class="fas fa-info-circle"></i> CLO Audit Summary</h6>
          <p class="mb-1"><strong>${clos.length}</strong> total CLOs in system</p>
          <p class="mb-0">
            <a href="/audit-clo" class="btn btn-sm btn-primary">
              <i class="fas fa-clipboard-check"></i> Go to Full Audit Page
            </a>
          </p>
        </div>
      `;

      container.innerHTML = summary;
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

      const table = globalThis.panelManager.createSortableTable({
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

    formatRole(role) {
      const roleMap = {
        instructor: 'Instructor',
        program_admin: 'Program Admin',
        institution_admin: 'Institution Admin',
        site_admin: 'Site Admin'
      };
      return roleMap[role] || role.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    },

    handleEditSection(button) {
      const sectionId = button.dataset.sectionId;
      const sectionData = JSON.parse(button.dataset.sectionData);
      if (typeof globalThis.openEditSectionModal === 'function') {
        globalThis.openEditSectionModal(sectionId, sectionData);
      }
    },

    handleEditCourse(button) {
      const courseId = button.dataset.courseId;
      const courseData = JSON.parse(button.dataset.courseData);
      if (typeof globalThis.openEditCourseModal === 'function') {
        globalThis.openEditCourseModal(courseId, courseData);
      }
    },

    async sendCourseReminder(instructorId, courseId, instructorName, courseNumber) {
      if (!confirm(`Send assessment reminder to ${instructorName} for ${courseNumber}?`)) {
        return;
      }

      try {
        const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

        const response = await fetch('/api/send-course-reminder', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({
            instructor_id: instructorId,
            course_id: courseId
          })
        });

        const data = await response.json();

        if (response.ok && data.success) {
          alert(
            `✅ Reminder sent to ${instructorName}!\n\nThey will receive an email with a direct link to complete their assessment for ${courseNumber}.`
          );
        } else {
          alert(`❌ Failed to send reminder: ${data.error || 'Unknown error'}`);
        }
      } catch (error) {
        console.error('Error sending reminder:', error); // eslint-disable-line no-console
        alert('❌ Failed to send reminder. Please try again.');
      }
    }
  };

  // Expose InstitutionDashboard to window immediately so onclick handlers work
  globalThis.InstitutionDashboard = InstitutionDashboard;

  document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for panelManager to be initialized
    setTimeout(() => {
      if (typeof globalThis.panelManager === 'undefined') {
        // eslint-disable-next-line no-console
        console.warn('Panel manager not initialized');
        return;
      }
      InstitutionDashboard.init();
    }, 100);
  });

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = InstitutionDashboard;
  }
})();
