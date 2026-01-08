/* global setLoadingState, setErrorState */
(function () {
  const API_ENDPOINT = "/api/dashboard/data";
  const SELECTORS = {
    institutionName: "institutionName",
    currentTerm: "currentTermName",
    programCount: "programCount",
    courseCount: "courseCount",
    facultyCount: "facultyCount",
    sectionCount: "sectionCount",
    programContainer: "programManagementContainer",
    facultyContainer: "facultyOverviewContainer",
    sectionContainer: "courseSectionContainer",
    assessmentContainer: "assessmentProgressContainer",
  };

  /**
   * Escape HTML to prevent XSS
   */
  // eslint-disable-next-line no-unused-vars
  function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  const InstitutionDashboard = {
    cache: null,
    lastFetch: 0,
    refreshInterval: 5 * 60 * 1000,
    intervalId: null,

    init() {
      document.addEventListener("visibilitychange", () => {
        if (
          !document.hidden &&
          Date.now() - this.lastFetch > this.refreshInterval
        ) {
          this.loadData({ silent: true });
        }
      });

      // Data auto-refreshes after mutations - no manual refresh button needed

      // Event delegation for action buttons
      document.addEventListener("click", (e) => {
        const target = e.target.closest("[data-action]");
        if (!target) return;

        const action = target.getAttribute("data-action");
        if (action === "edit-section") {
          e.preventDefault();
          e.stopPropagation();
          this.handleEditSection(target);
        } else if (action === "send-reminder") {
          e.preventDefault();
          e.stopPropagation();
          const instructorId = target.getAttribute("data-instructor-id");
          const courseId = target.getAttribute("data-course-id");
          const instructor = target.getAttribute("data-instructor");
          const courseNumber = target.getAttribute("data-course-number");
          if (instructorId && courseId && instructor && courseNumber) {
            this.sendCourseReminder(
              instructorId,
              courseId,
              instructor,
              courseNumber,
            );
          }
        } else if (action === "edit-course") {
          e.preventDefault();
          e.stopPropagation();
          this.handleEditCourse(target);
        } else if (action === "edit-program") {
          e.preventDefault();
          e.stopPropagation();
          const programId = target.getAttribute("data-program-id");
          const programName = target.getAttribute("data-program-name");
          if (
            programId &&
            typeof globalThis.openEditProgramModal === "function"
          ) {
            globalThis.openEditProgramModal(programId, { name: programName });
          }
        } else if (action === "delete-program") {
          e.preventDefault();
          e.stopPropagation();
          const programId = target.getAttribute("data-program-id");
          const programName = target.getAttribute("data-program-name");
          if (
            programId &&
            programName &&
            typeof globalThis.deleteProgram === "function"
          ) {
            globalThis.deleteProgram(programId, programName);
          }
        }
      });

      this.loadData();
      this.intervalId = setInterval(
        () => this.loadData({ silent: true }),
        this.refreshInterval,
      );

      // Cleanup on page unload
      globalThis.addEventListener("beforeunload", () => this.cleanup());
      globalThis.addEventListener("pagehide", () => this.cleanup());
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
        this.setLoading(SELECTORS.programContainer, "Loading programs...");
        this.setLoading("termManagementContainer", "Loading terms...");
        this.setLoading("offeringManagementContainer", "Loading offerings...");
        this.setLoading("outcomeManagementContainer", "Loading outcomes...");
        this.setLoading(SELECTORS.facultyContainer, "Loading faculty...");
        this.setLoading(SELECTORS.sectionContainer, "Loading sections...");
        this.setLoading(
          SELECTORS.assessmentContainer,
          "Loading assessment data...",
        );
        this.setLoading(
          "institutionCloAuditContainer",
          "Loading audit data...",
        );
      }

      try {
        const response = await fetch(API_ENDPOINT, {
          credentials: "include",
          headers: {
            Accept: "application/json",
            "X-Requested-With": "XMLHttpRequest",
          },
        });

        const payload = await response.json();
        if (!response.ok || !payload.success) {
          throw new Error(payload.error || "Unable to load dashboard data");
        }

        this.cache = payload.data || {};
        globalThis.dashboardDataCache = this.cache;
        this.lastFetch = Date.now();
        this.render(this.cache);
      } catch (error) {
        // eslint-disable-next-line no-console
        console.warn("Institution dashboard load error:", error);
        this.showError(
          SELECTORS.programContainer,
          "Unable to load program data",
        );
        this.showError(
          SELECTORS.facultyContainer,
          "Unable to load faculty data",
        );
        this.showError(
          SELECTORS.sectionContainer,
          "Unable to load section data",
        );
        this.showError(
          SELECTORS.assessmentContainer,
          "Unable to load assessment progress",
        );
      }
    },

    render(data) {
      this.updateHeader(data);
      this.renderPrograms(data.program_overview || [], data.programs || []);
      this.renderCourses(data.courses || []);
      this.renderTerms(data.terms || []);
      this.renderOfferings(
        data.offerings || [],
        data.courses || [],
        data.terms || [],
      );
      this.renderCLOs(data.clos || []);
      this.renderFaculty(data.faculty_assignments || [], data.faculty || []);
      this.renderSections(
        data.sections || [],
        data.courses || [],
        data.terms || [],
      );
      this.renderAssessment(data.program_overview || []);
      this.renderCLOAudit(data.clos || []);
      const lastUpdated =
        data.metadata && data.metadata.last_updated
          ? data.metadata.last_updated
          : null;
      this.updateLastUpdated(lastUpdated);
    },

    updateHeader(data) {
      const summary = data.summary || {};
      document.getElementById(SELECTORS.programCount).textContent =
        summary.programs ?? 0;
      document.getElementById(SELECTORS.courseCount).textContent =
        summary.courses ?? 0;
      document.getElementById(SELECTORS.facultyCount).textContent =
        summary.faculty ?? 0;
      document.getElementById(SELECTORS.sectionCount).textContent =
        summary.sections ?? 0;

      const institutionName =
        (data.institutions &&
          data.institutions[0] &&
          data.institutions[0].name) ||
        document.getElementById(SELECTORS.institutionName).textContent;
      document.getElementById(SELECTORS.institutionName).textContent =
        institutionName || "Institution Overview";

      const term =
        (data.terms || []).find((item) => item && item.active) ||
        (data.terms || [])[0];
      const termName = term && term.name ? term.name : "--";
      document.getElementById(SELECTORS.currentTerm).textContent = termName;
    },

    renderPrograms(programOverview, rawPrograms) {
      const container = document.getElementById(SELECTORS.programContainer);
      if (!container) return;

      if (!programOverview.length && !rawPrograms.length) {
        container.innerHTML = "";
        container.appendChild(
          this.renderEmptyState("No programs found", "Add Program"),
        );
        return;
      }

      const programs = programOverview.length
        ? programOverview
        : rawPrograms.map((program) => ({
            program_id: program.program_id || program.id,
            program_name: program.name,
            course_count: program.course_count || 0,
            faculty_count: program.faculty_count || 0,
            student_count: program.student_count || 0,
            section_count: program.section_count || 0,
            assessment_progress: program.assessment_progress || {
              percent_complete: 0,
              completed: 0,
              total: 0,
            },
          }));

      const table = globalThis.panelManager.createSortableTable({
        id: "institution-programs-table",
        columns: [
          { key: "program", label: "Program", sortable: true },
          { key: "courses", label: "Courses", sortable: true },
          { key: "faculty", label: "Faculty", sortable: true },
          { key: "students", label: "Students", sortable: true },
          { key: "sections", label: "Sections", sortable: true },
          { key: "progress", label: "Progress", sortable: true },
        ],
        data: programs.map((program) => {
          const progress = program.assessment_progress || {};
          const percent =
            typeof progress.percent_complete === "number"
              ? progress.percent_complete
              : 0;
          const completed = progress.completed ?? 0;
          const total = progress.total ?? 0;
          const coursesLength =
            program.courses && program.courses.length
              ? program.courses.length
              : 0;
          const courseCount = Number(
            program.course_count ?? coursesLength ?? 0,
          );
          const facultyCount = Number(
            program.faculty_count ??
              (program.faculty ? program.faculty.length : 0),
          );
          const studentCount = Number(program.student_count ?? 0);
          const sectionCount = Number(program.section_count ?? 0);

          return {
            program: program.program_name || program.name || "Unnamed Program",
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
          };
        }),
      });

      container.innerHTML = "";
      container.appendChild(table);
    },

    renderFaculty(assignments, fallbackFaculty) {
      const container = document.getElementById(SELECTORS.facultyContainer);
      if (!container) return;

      const facultyRecords = assignments.length
        ? assignments
        : fallbackFaculty.map((member) => ({
            user_id: member.user_id,
            full_name:
              member.full_name ||
              [member.first_name, member.last_name].filter(Boolean).join(" ") ||
              member.email,
            program_ids: member.program_ids || [],
            course_count: member.course_count || 0,
            section_count: member.section_count || 0,
            enrollment: member.enrollment || 0,
            role: member.role || "instructor",
          }));

      if (!facultyRecords.length) {
        container.innerHTML = "";
        container.appendChild(
          this.renderEmptyState("No faculty assigned yet", "Invite Faculty"),
        );
        return;
      }

      const table = globalThis.panelManager.createSortableTable({
        id: "institution-faculty-table",
        columns: [
          { key: "name", label: "Faculty Name", sortable: true },
          { key: "programs", label: "Programs", sortable: true },
          { key: "courses", label: "Courses", sortable: true },
          { key: "sections", label: "Sections", sortable: true },
          { key: "students", label: "Students", sortable: true },
          { key: "role", label: "Role", sortable: true },
        ],
        data: facultyRecords.map((record) => {
          const courseCount = Number(record.course_count ?? 0);
          const sectionCount = Number(record.section_count ?? 0);
          const studentCount = Number(record.enrollment ?? 0);

          return {
            name: record.full_name || record.name || "Instructor",
            programs:
              (record.program_summaries || [])
                .map((program) =>
                  program && program.program_name ? program.program_name : null,
                )
                .filter(Boolean)
                .join(", ") ||
              (record.program_ids || []).join(", ") ||
              "—",
            courses: courseCount.toString(),
            courses_sort: courseCount.toString(),
            sections: sectionCount.toString(),
            sections_sort: sectionCount.toString(),
            students: studentCount.toString(),
            students_sort: studentCount.toString(),
            role: this.formatRole(record.role || "instructor"),
          };
        }),
      });

      container.innerHTML = "";
      container.appendChild(table);
    },

    renderSections(sections, courses) {
      const container = document.getElementById(SELECTORS.sectionContainer);
      if (!container) return;

      if (!sections.length) {
        container.innerHTML = "";
        container.appendChild(
          this.renderEmptyState("No sections scheduled", "Add Section"),
        );
        return;
      }

      const courseLookup = new Map();
      courses.forEach((course) => {
        const courseId = course.course_id || course.id;
        if (courseId) {
          courseLookup.set(courseId, course);
        }
      });

      const table = globalThis.panelManager.createSortableTable({
        id: "institution-sections-table",
        columns: [
          { key: "course", label: "Course", sortable: true },
          { key: "section", label: "Section", sortable: true },
          { key: "faculty", label: "Faculty", sortable: true },
          { key: "enrollment", label: "Enrollment", sortable: true },
          { key: "status", label: "Status", sortable: true },
        ],
        data: sections.map((section) => {
          const course = courseLookup.get(section.course_id) || {};
          const title =
            course.course_title ||
            course.title ||
            course.name ||
            section.course_name;
          const number = course.course_number || course.number || "";
          const instructor =
            section.instructor_name || section.instructor || "Unassigned";
          const enrollment = section.enrollment ?? 0;
          const status = (section.status || "scheduled").replace(/_/g, " ");

          return {
            course: number ? `${number} — ${title || ""}` : title || "Course",
            section: section.section_number || section.section_id || "—",
            faculty: instructor,
            enrollment: enrollment.toString(),
            enrollment_sort: enrollment.toString(),
            status: status.charAt(0).toUpperCase() + status.slice(1),
          };
        }),
      });

      container.innerHTML = "";
      container.appendChild(table);
    },

    renderCourses(courses) {
      // Reuse program container area for a simple courses table if present
      // If the program container is not on this page, skip rendering courses
      const coursesContainer = document.getElementById(
        "courseManagementContainer",
      );
      if (!coursesContainer) return;

      if (!courses.length) {
        coursesContainer.innerHTML = "";
        coursesContainer.appendChild(
          this.renderEmptyState("No courses found", "Add Course"),
        );
        return;
      }

      const table = globalThis.panelManager.createSortableTable({
        id: "institution-courses-table",
        columns: [
          { key: "number", label: "Course Number", sortable: true },
          { key: "title", label: "Title", sortable: true },
          { key: "credits", label: "Credits", sortable: true },
          { key: "sections", label: "Sections", sortable: true },
          { key: "department", label: "Department", sortable: true },
        ],
        data: courses.map((course) => {
          return {
            number: course.course_number || "-",
            title: course.course_title || course.title || "-",
            credits: (course.credit_hours ?? "-").toString(),
            credits_sort: (course.credit_hours ?? 0).toString(),
            sections: (course.section_count ?? 0).toString(),
            sections_sort: (course.section_count ?? 0).toString(),
            department: course.department || "-",
          };
        }),
      });

      coursesContainer.innerHTML = "";
      coursesContainer.appendChild(table);
    },

    renderTerms(terms) {
      const container = document.getElementById("termManagementContainer");
      if (!container) return;

      if (!terms || !terms.length) {
        container.innerHTML = "";
        container.appendChild(
          this.renderEmptyState("No terms defined", "Add Term"),
        );
        return;
      }

      const table = globalThis.panelManager.createSortableTable({
        id: "institution-terms-table",
        columns: [
          { key: "name", label: "Name", sortable: true },
          { key: "programs", label: "Programs", sortable: true },
          { key: "courses", label: "Courses", sortable: true },
          { key: "sections", label: "Course Sections", sortable: true },
          { key: "start_date", label: "Start Date", sortable: true },
          { key: "end_date", label: "End Date", sortable: true },
          { key: "status", label: "Status", sortable: true },
        ],
        data: terms.map((term) => {
          // Format dates nicely
          const startDate = term.start_date
            ? new Date(term.start_date).toLocaleDateString()
            : "N/A";
          const endDate = term.end_date
            ? new Date(term.end_date).toLocaleDateString()
            : "N/A";

          return {
            name: term.name || term.term_name || "Unnamed Term",
            name_sort: term.name || term.term_name || "",
            programs: (term.program_count ?? 0).toString(),
            programs_sort: (term.program_count ?? 0).toString(),
            courses: (term.course_count ?? 0).toString(),
            courses_sort: (term.course_count ?? 0).toString(),
            sections: (term.section_count ?? 0).toString(),
            sections_sort: (term.section_count ?? 0).toString(),
            start_date: startDate,
            start_date_sort: term.start_date || "",
            end_date: endDate,
            end_date_sort: term.end_date || "",
            status:
              term.active || term.is_active
                ? '<span class="badge bg-success">Active</span>'
                : '<span class="badge bg-secondary">Inactive</span>',
            status_sort: term.active || term.is_active ? "1" : "0",
          };
        }),
      });

      container.innerHTML = "";
      container.appendChild(table);
    },

    renderOfferings(offerings, courses, terms) {
      const container = document.getElementById("offeringManagementContainer");
      if (!container) return;

      if (!offerings || !offerings.length) {
        container.innerHTML = "";
        container.appendChild(
          this.renderEmptyState(
            "No course offerings scheduled",
            "Add Offering",
          ),
        );
        return;
      }

      const courseLookup = new Map();
      courses.forEach((course) => {
        const courseId = course.course_id || course.id;
        if (courseId) {
          courseLookup.set(courseId, course);
        }
      });

      const termLookup = new Map();
      terms.forEach((term) => {
        const termId = term.term_id || term.id;
        if (termId) {
          termLookup.set(termId, term);
        }
      });

      const table = globalThis.panelManager.createSortableTable({
        id: "institution-offerings-table",
        columns: [
          { key: "course", label: "Course", sortable: true },
          { key: "program", label: "Program", sortable: true },
          { key: "term", label: "Term", sortable: true },
          { key: "sections", label: "Sections", sortable: true },
          { key: "enrollment", label: "Enrollment", sortable: true },
          { key: "status", label: "Status", sortable: true },
        ],
        data: offerings.map((offering) => {
          const course = courseLookup.get(offering.course_id) || {};
          const term = termLookup.get(offering.term_id) || {};
          const sectionCount = offering.section_count || 0;
          const enrollmentCount = offering.total_enrollment || 0;
          // Get program names from offering (enriched from course) or fall back to course data
          const programNames =
            offering.program_names || course.program_names || [];
          const programDisplay =
            programNames.length > 0 ? programNames.join(", ") : "-";

          return {
            course: course.course_number || "Unknown Course",
            program: programDisplay,
            term: term.term_name || term.name || "Unknown Term",
            sections: sectionCount.toString(),
            sections_sort: sectionCount.toString(),
            enrollment: enrollmentCount.toString(),
            enrollment_sort: enrollmentCount.toString(),
            status:
              offering.status === "active"
                ? '<span class="badge bg-success">Active</span>'
                : '<span class="badge bg-secondary">Inactive</span>',
            status_sort: offering.status === "active" ? "1" : "0",
          };
        }),
      });

      container.innerHTML = "";
      container.appendChild(table);
    },

    renderCLOs(clos) {
      const container = document.getElementById("outcomeManagementContainer");
      if (!container) return;

      if (!clos || !clos.length) {
        container.innerHTML = "";
        container.appendChild(
          this.renderEmptyState("No CLOs defined", "Add Outcome"),
        );
        return;
      }

      const table = globalThis.panelManager.createSortableTable({
        id: "institution-clos-table",
        columns: [
          { key: "course", label: "Course", sortable: true },
          { key: "clo_number", label: "CLO #", sortable: true },
          { key: "description", label: "Description", sortable: true },
          { key: "status", label: "Status", sortable: true },
        ],
        data: clos.map((clo) => {
          return {
            course: clo.course_number || "Unknown",
            clo_number: clo.clo_number || "?",
            clo_number_sort: clo.clo_number || "0",
            description: clo.description || "No description",
            status: clo.active
              ? '<span class="badge bg-success">Active</span>'
              : '<span class="badge bg-secondary">Inactive</span>',
            status_sort: clo.active ? "1" : "0",
          };
        }),
      });

      container.innerHTML = "";
      container.appendChild(table);
    },

    renderCLOAudit(clos) {
      const container = document.getElementById("institutionCloAuditContainer");
      if (!container) return;

      if (!clos || !clos.length) {
        container.innerHTML = "";
        container.appendChild(
          this.renderEmptyState("No CLOs pending audit", "Review Submissions"),
        );
        return;
      }

      // Group CLOs by program and status
      const programStats = new Map();

      clos.forEach((clo) => {
        const programName =
          clo.program_name || clo.program || "Unknown Program";
        const status = clo.status || "unassigned";

        if (!programStats.has(programName)) {
          programStats.set(programName, {
            program: programName,
            unassigned: 0,
            assigned: 0,
            in_progress: 0,
            approval_pending: 0,
            awaiting_approval: 0,
            approved: 0,
          });
        }

        const stats = programStats.get(programName);
        if (status in stats) {
          stats[status]++;
        }
      });

      // Convert to table data
      const tableData = Array.from(programStats.values()).map((stats) => ({
        program: stats.program,
        unassigned: stats.unassigned.toString(),
        unassigned_sort: stats.unassigned.toString(),
        assigned: stats.assigned.toString(),
        assigned_sort: stats.assigned.toString(),
        inProgress: stats.in_progress.toString(),
        inProgress_sort: stats.in_progress.toString(),
        needsRework: stats.approval_pending.toString(),
        needsRework_sort: stats.approval_pending.toString(),
        awaitingApproval: stats.awaiting_approval.toString(),
        awaitingApproval_sort: stats.awaiting_approval.toString(),
        approved: stats.approved.toString(),
        approved_sort: stats.approved.toString(),
      }));

      const table = globalThis.panelManager.createSortableTable({
        id: "institution-clo-audit-table",
        columns: [
          { key: "program", label: "Program", sortable: true },
          { key: "unassigned", label: "Unassigned", sortable: true },
          { key: "assigned", label: "Assigned", sortable: true },
          { key: "inProgress", label: "In Progress", sortable: true },
          { key: "needsRework", label: "Needs Rework", sortable: true },
          {
            key: "awaitingApproval",
            label: "Awaiting Approval",
            sortable: true,
          },
          { key: "approved", label: "Approved", sortable: true },
        ],
        data: tableData,
      });

      container.innerHTML = "";
      container.appendChild(table);
    },

    renderAssessment(programOverview) {
      const container = document.getElementById(SELECTORS.assessmentContainer);
      if (!container) return;

      if (!programOverview.length) {
        container.innerHTML = "";
        container.appendChild(
          this.renderEmptyState("No assessment data available", "View Details"),
        );
        return;
      }

      const table = globalThis.panelManager.createSortableTable({
        id: "institution-assessment-table",
        columns: [
          { key: "program", label: "Program", sortable: true },
          { key: "courses", label: "Courses", sortable: true },
          { key: "sections", label: "Sections", sortable: true },
          { key: "totalClos", label: "Total CLOs", sortable: true },
          { key: "percent", label: "Percent Complete", sortable: true },
        ],
        data: programOverview.map((program) => {
          const progress = program.assessment_progress || {};
          const total = progress.total ?? 0;
          const percent = progress.percent_complete ?? 0;
          const sectionCount = program.section_count ?? 0;
          return {
            program: program.program_name || program.name || "Program",
            courses: (program.course_count ?? 0).toString(),
            courses_sort: (program.course_count ?? 0).toString(),
            sections: sectionCount.toString(),
            sections_sort: sectionCount.toString(),
            totalClos: total.toString(),
            totalClos_sort: total.toString(),
            percent: `${percent}%`,
            percent_sort: percent,
          };
        }),
      });

      container.innerHTML = "";
      container.appendChild(table);
    },

    updateLastUpdated(timestamp) {
      const target = document.getElementById(SELECTORS.lastUpdated);
      if (!target) return;
      const value = timestamp
        ? new Date(timestamp).toLocaleString()
        : new Date().toLocaleString();
      target.textContent = `Last updated: ${value}`;
    },

    setLoading(containerId, message) {
      setLoadingState(containerId, message);
    },

    showError(containerId, message) {
      setErrorState(containerId, message);
    },

    renderEmptyState(message, actionLabel) {
      const wrapper = document.createElement("div");
      wrapper.className = "panel-empty";
      const icon = document.createElement("div");
      icon.className = "panel-empty-icon";
      icon.textContent = "📌";
      const p = document.createElement("p");
      p.textContent = message;
      const button = document.createElement("button");
      button.className = "btn btn-primary btn-sm";
      button.textContent = actionLabel;
      button.onclick = () => false;
      wrapper.appendChild(icon);
      wrapper.appendChild(p);
      wrapper.appendChild(button);
      return wrapper;
    },

    formatRole(role) {
      const roleMap = {
        instructor: "Instructor",
        program_admin: "Program Admin",
        institution_admin: "Institution Admin",
        site_admin: "Site Admin",
      };
      return (
        roleMap[role] ||
        role.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())
      );
    },

    handleEditSection(button) {
      const sectionId = button.dataset.sectionId;
      const sectionData = JSON.parse(button.dataset.sectionData);
      if (typeof globalThis.openEditSectionModal === "function") {
        globalThis.openEditSectionModal(sectionId, sectionData);
      }
    },

    handleEditCourse(button) {
      const courseId = button.dataset.courseId;
      const courseData = JSON.parse(button.dataset.courseData);
      if (typeof globalThis.openEditCourseModal === "function") {
        globalThis.openEditCourseModal(courseId, courseData);
      }
    },

    async sendCourseReminder(
      instructorId,
      courseId,
      instructorName,
      courseNumber,
    ) {
      if (
        !confirm(
          `Send assessment reminder to ${instructorName} for ${courseNumber}?`,
        )
      ) {
        return;
      }

      try {
        const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

        const response = await fetch("/api/send-course-reminder", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({
            instructor_id: instructorId,
            course_id: courseId,
          }),
        });

        const data = await response.json();

        if (response.ok && data.success) {
          alert(
            `✅ Reminder sent to ${instructorName}!\n\nThey will receive an email with a direct link to complete their assessment for ${courseNumber}.`,
          );
        } else {
          alert(`❌ Failed to send reminder: ${data.error || "Unknown error"}`);
        }
      } catch (error) {
        console.error("Error sending reminder:", error); // eslint-disable-line no-console
        alert("❌ Failed to send reminder. Please try again.");
      }
    },
  };

  // Expose InstitutionDashboard to window immediately so onclick handlers work
  globalThis.InstitutionDashboard = InstitutionDashboard;

  // Expose loadTerms globally for termManagement.js to call after term creation
  globalThis.loadTerms = function () {
    InstitutionDashboard.loadData({ silent: true });
  };

  document.addEventListener("DOMContentLoaded", () => {
    // Wait a bit for panelManager to be initialized
    setTimeout(() => {
      if (typeof globalThis.panelManager === "undefined") {
        // eslint-disable-next-line no-console
        console.warn("Panel manager not initialized");
        return;
      }
      InstitutionDashboard.init();
    }, 100);
  });

  if (typeof module !== "undefined" && module.exports) {
    module.exports = InstitutionDashboard;
  }
})();
