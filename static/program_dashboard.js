/* global setLoadingState, setErrorState */
(function () {
  const API_ENDPOINT = "/api/dashboard/data";
  const SELECTORS = {
    title: "programAdminTitle",
    coursesContainer: "programCoursesContainer",
    facultyContainer: "programFacultyContainer",
    cloContainer: "programCloContainer",
    assessmentContainer: "programAssessmentContainer",
    ploContainer: "programPloContainer",
  };

  const ProgramDashboard = {
    cache: null,
    lastFetch: 0,
    refreshInterval: 5 * 60 * 1000,
    intervalId: null,
    refreshDebounceMs: 400,
    refreshTimeoutId: null,
    mutationUnsubscribe: null,

    init() {
      this.registerMutationListener();
      document.addEventListener("visibilitychange", () => {
        if (
          !document.hidden &&
          Date.now() - this.lastFetch > this.refreshInterval
        ) {
          this.loadData({ silent: true });
        }
      });

      // Data auto-refreshes after mutations - no manual refresh button needed

      this.loadData();
      this.intervalId = setInterval(
        () => this.loadData({ silent: true }),
        this.refreshInterval,
      );

      globalThis.addEventListener("beforeunload", () => this.cleanup());
      globalThis.addEventListener("pagehide", () => this.cleanup());
    },

    cleanup() {
      if (this.intervalId) {
        clearInterval(this.intervalId);
        this.intervalId = null;
      }
      if (this.refreshTimeoutId) {
        clearTimeout(this.refreshTimeoutId);
        this.refreshTimeoutId = null;
      }
      if (typeof this.mutationUnsubscribe === "function") {
        this.mutationUnsubscribe();
        this.mutationUnsubscribe = null;
      }
    },

    async refresh() {
      return this.loadData({ silent: false });
    },

    registerMutationListener() {
      if (!globalThis.DashboardEvents?.subscribeToMutations) {
        return;
      }

      if (this.mutationUnsubscribe) {
        this.mutationUnsubscribe();
      }

      this.mutationUnsubscribe =
        globalThis.DashboardEvents.subscribeToMutations((detail) => {
          if (!detail) return;
          this.scheduleRefresh({
            silent: true,
            reason: `${detail.entity || "unknown"}:${detail.action || "change"}`,
          });
        });
    },

    scheduleRefresh(options = {}) {
      const { silent = true } = options;
      if (this.refreshTimeoutId) {
        clearTimeout(this.refreshTimeoutId);
      }
      this.refreshTimeoutId = setTimeout(() => {
        this.refreshTimeoutId = null;
        this.loadData({ silent });
      }, this.refreshDebounceMs);
    },

    async loadData(options = {}) {
      const { silent = false } = options;
      if (!silent) {
        this.setLoading(SELECTORS.coursesContainer, "Loading courses...");
        this.setLoading(
          SELECTORS.facultyContainer,
          "Loading faculty assignments...",
        );
        this.setLoading(SELECTORS.cloContainer, "Loading learning outcomes...");
        this.setLoading(
          SELECTORS.assessmentContainer,
          "Loading assessment results...",
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

        // Handle authentication failure specifically to stop log spam
        if (response.status === 401 || payload.error_code === "AUTH_REQUIRED") {
          this.cleanup(); // Stop polling
          window.location.reload(); // Reload to trigger login redirect
          return;
        }

        if (!response.ok || !payload.success) {
          throw new Error(payload.error || "Unable to load dashboard data");
        }

        this.cache = payload.data || {};
        globalThis.dashboardDataCache = this.cache;
        this.lastFetch = Date.now();
        this.render(this.cache);
      } catch (error) {
        // eslint-disable-next-line no-console
        console.warn("Program dashboard load error:", error);
        this.showError(
          SELECTORS.coursesContainer,
          "Unable to load course data",
        );
        this.showError(
          SELECTORS.facultyContainer,
          "Unable to load faculty data",
        );
        this.showError(
          SELECTORS.cloContainer,
          "Unable to load learning outcomes",
        );
        this.showError(
          SELECTORS.assessmentContainer,
          "Unable to load assessment results",
        );
        this.showError(SELECTORS.ploContainer, "Unable to load PLO data");
      }
    },

    render(data) {
      this.renderCourses(
        data.courses || [],
        data.sections || [],
        data.program_overview || [],
      );
      this.renderFaculty(data.faculty_assignments || []);
      this.renderClos(data.courses || [], data.program_overview || []);
      this.renderAssessment(data.program_overview || []);
      this.renderPlos();
      const lastUpdated =
        data.metadata && data.metadata.last_updated
          ? data.metadata.last_updated
          : null;
      this.updateLastUpdated(lastUpdated);
    },

    renderCourses(courses, sections, programOverview) {
      const container = document.getElementById(SELECTORS.coursesContainer);
      if (!container) return;

      const courseMap = new Map();
      courses.forEach((course) => {
        const id = course.course_id || course.id;
        if (id && !courseMap.has(id)) {
          courseMap.set(id, course);
        }
      });

      if (!courseMap.size) {
        container.innerHTML = "";
        container.appendChild(
          this.renderEmptyState(
            "No courses found for this program",
            "Add Course",
          ),
        );
        return;
      }

      const sectionsByCourse = this.groupBy(
        sections,
        (section) => section.course_id || section.id,
      );
      const progressByProgram = new Map(
        (programOverview || []).map((item) => [
          item.program_id,
          item.assessment_progress,
        ]),
      );

      const table = globalThis.panelManager.createSortableTable({
        id: "program-courses-table",
        columns: [
          { key: "course", label: "Course", sortable: true },
          { key: "sections", label: "Sections", sortable: true },
          { key: "enrollment", label: "Students", sortable: true },
          { key: "program", label: "Program", sortable: true },
          { key: "progress", label: "Progress", sortable: true },
        ],
        data: Array.from(courseMap.values()).map((course) => {
          const courseId = course.course_id || course.id;
          const programIdsFirst =
            course.program_ids && course.program_ids[0]
              ? course.program_ids[0]
              : null;
          const programId = course.program_id || programIdsFirst;
          const programProgress = progressByProgram.get(programId) || {};
          const courseSections = sectionsByCourse.get(courseId) || [];
          const sectionCount = courseSections.length;
          const enrollment = courseSections.reduce(
            (total, section) => total + (Number(section.enrollment) || 0),
            0,
          );
          const percent = programProgress.percent_complete ?? 0;
          const completed = programProgress.completed ?? 0;
          const total = programProgress.total ?? 0;

          return {
            course: `${course.course_number || course.number || ""}`.trim()
              ? `${course.course_number || course.number} — ${course.course_title || course.title || course.name || ""}`
              : course.course_title || course.title || course.name || "Course",
            sections: sectionCount.toString(),
            sections_sort: sectionCount.toString(),
            enrollment: enrollment.toString(),
            enrollment_sort: enrollment.toString(),
            program: course.program_name || course.program || "Program",
            progress: `<div class="progress">
                <div class="progress-bar bg-success" role="progressbar" style="width: ${Math.min(percent, 100)}%">${percent}%</div>
              </div>
              <small class="text-muted">${completed}/${total} complete</small>`,
            progress_sort: percent,
          };
        }),
      });

      container.innerHTML = "";
      container.appendChild(table);
    },

    renderFaculty(assignments) {
      const container = document.getElementById(SELECTORS.facultyContainer);
      if (!container) return;

      if (!assignments.length) {
        container.innerHTML = "";
        container.appendChild(
          this.renderEmptyState("No faculty assignments yet", "Assign Courses"),
        );
        return;
      }

      const table = globalThis.panelManager.createSortableTable({
        id: "program-faculty-table",
        columns: [
          { key: "name", label: "Faculty", sortable: true },
          { key: "courses", label: "Courses", sortable: true },
          { key: "sections", label: "Sections", sortable: true },
          { key: "students", label: "Students", sortable: true },
          { key: "programs", label: "Programs", sortable: true },
        ],
        data: assignments.map((record) => {
          const courseCount = Number(record.course_count ?? 0);
          const sectionCount = Number(record.section_count ?? 0);
          const studentCount = Number(record.enrollment ?? 0);
          return {
            name: record.full_name || record.name || "Instructor",
            courses: courseCount.toString(),
            courses_sort: courseCount.toString(),
            sections: sectionCount.toString(),
            sections_sort: sectionCount.toString(),
            students: studentCount.toString(),
            students_sort: studentCount.toString(),
            programs:
              (record.program_summaries || [])
                .map((program) =>
                  program && program.program_name ? program.program_name : null,
                )
                .filter(Boolean)
                .join(", ") ||
              (record.program_ids || []).join(", ") ||
              "—",
          };
        }),
      });

      container.innerHTML = "";
      container.appendChild(table);
    },

    renderClos(courses, programOverview) {
      const container = document.getElementById(SELECTORS.cloContainer);
      if (!container) return;

      if (!courses.length) {
        container.innerHTML = "";
        container.appendChild(
          this.renderEmptyState(
            "No learning outcomes configured yet",
            "Add Outcome",
          ),
        );
        return;
      }

      const progressByProgram = new Map(
        (programOverview || []).map((item) => [
          item.program_id,
          item.assessment_progress,
        ]),
      );

      const table = globalThis.panelManager.createSortableTable({
        id: "program-clo-table",
        columns: [
          { key: "course", label: "Course", sortable: true },
          { key: "clos", label: "Outcomes", sortable: true },
          { key: "status", label: "Status", sortable: true },
          { key: "progress", label: "Progress", sortable: true },
        ],
        data: courses.map((course) => {
          const programIdsFirst =
            course.program_ids && course.program_ids[0]
              ? course.program_ids[0]
              : null;
          const programId = course.program_id || programIdsFirst;
          const progress = progressByProgram.get(programId) || {};
          const percent = progress.percent_complete ?? 0;
          const cloCount =
            (course.clo_count ?? (course.clos ? course.clos.length : 0)) || 0;
          // Determine status based on completion percentage
          let status;
          if (percent >= 75) {
            status = "On Track";
          } else if (percent >= 30) {
            status = "In Progress";
          } else {
            status = "Needs Attention";
          }
          return {
            course:
              `${course.course_number || course.number || course.course_id || "Course"} — ${course.course_title || course.title || course.name || ""}`.trim(),
            clos: cloCount.toString(),
            clos_sort: cloCount.toString(),
            status,
            progress: `${percent}%`,
            progress_sort: percent,
          };
        }),
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
          this.renderEmptyState(
            "No assessment activity recorded",
            "Open Assessment Report",
          ),
        );
        return;
      }

      const table = globalThis.panelManager.createSortableTable({
        id: "program-assessment-table",
        columns: [
          { key: "program", label: "Program", sortable: true },
          { key: "courses", label: "Courses", sortable: true },
          { key: "sections", label: "Sections", sortable: true },
          { key: "students", label: "Students", sortable: true },
          { key: "progress", label: "Progress", sortable: true },
        ],
        data: programOverview.map((item) => {
          const percentComplete =
            item.assessment_progress &&
            item.assessment_progress.percent_complete !== undefined
              ? item.assessment_progress.percent_complete
              : 0;
          const percent = percentComplete ?? 0;
          const studentCount = item.student_count ?? 0;
          const sectionCount = item.section_count ?? 0;
          return {
            program: item.program_name || "Program",
            courses: (item.course_count ?? 0).toString(),
            courses_sort: (item.course_count ?? 0).toString(),
            sections: sectionCount.toString(),
            sections_sort: sectionCount.toString(),
            students: studentCount.toString(),
            students_sort: studentCount.toString(),
            progress: `${percent}%`,
            progress_sort: percent,
          };
        }),
      });

      container.innerHTML = "";
      container.appendChild(table);
    },

    async renderPlos() {
      const container = document.getElementById(SELECTORS.ploContainer);
      if (!container) return;

      try {
        const resp = await fetch("/api/plo-dashboard/tree", {
          credentials: "include",
          headers: { Accept: "application/json" },
        });
        const json = await resp.json();
        if (!resp.ok || !json.success) {
          throw new Error(json.error || "Failed to load PLO data");
        }

        const programs = (json.data && json.data.programs) || [];
        if (!programs.length) {
          container.innerHTML = "";
          container.appendChild(
            this.renderEmptyState(
              "No program learning outcomes defined yet",
              "Open PLO Dashboard",
            ),
          );
          return;
        }

        // Build a simple summary table
        const rows = [];
        for (const prog of programs) {
          for (const plo of prog.plos || []) {
            rows.push({
              program: prog.short_name || prog.name || "—",
              plo: "PLO " + plo.plo_number,
              description: plo.description || "",
              clos: (plo.mapped_clo_count || 0).toString(),
            });
          }
        }

        if (!rows.length) {
          container.innerHTML = "";
          container.appendChild(
            this.renderEmptyState(
              "No PLOs defined for your programs",
              "Open PLO Dashboard",
            ),
          );
          return;
        }

        const table = globalThis.panelManager.createSortableTable({
          id: "program-plo-table",
          columns: [
            { key: "program", label: "Program", sortable: true },
            { key: "plo", label: "PLO", sortable: true },
            { key: "description", label: "Description", sortable: false },
            { key: "clos", label: "Mapped CLOs", sortable: true },
          ],
          data: rows,
        });

        container.innerHTML = "";
        container.appendChild(table);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn("PLO panel load error:", err);
        this.showError(SELECTORS.ploContainer, "Unable to load PLO data");
      }
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

    groupBy(items, keyFn) {
      const map = new Map();
      items.forEach((item) => {
        const key = keyFn(item);
        if (!key) return;
        const group = map.get(key) || [];
        group.push(item);
        map.set(key, group);
      });
      return map;
    },
  };

  document.addEventListener("DOMContentLoaded", () => {
    // Wait a bit for panelManager to be initialized
    setTimeout(() => {
      if (typeof globalThis.panelManager === "undefined") {
        // eslint-disable-next-line no-console
        console.warn("Panel manager not initialized");
        return;
      }
      ProgramDashboard.init();
      globalThis.ProgramDashboard = ProgramDashboard;
    }, 100);
  });

  if (typeof module !== "undefined" && module.exports) {
    module.exports = ProgramDashboard;
  }
})();
