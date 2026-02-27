/* global setLoadingState, setErrorState */
(function () {
  const API_ENDPOINT = "/api/dashboard/data";
  const SELECTORS = {
    title: "programAdminTitle",
    coursesContainer: "programCoursesContainer",
    facultyContainer: "programFacultyContainer",
    cloContainer: "programCloContainer",
    ploContainer: "programPloContainer",
    assessmentContainer: "programAssessmentContainer",
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
        this.setLoading(SELECTORS.ploContainer, "Loading program outcomes...");
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
      // PLO summary needs its own per-program fetch (not in /api/dashboard/data).
      // Fire-and-forget so the rest of the dashboard isn't blocked on it.
      this.loadPloSummary(data.program_overview || []);
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

    /**
     * Fetch PLO tree summary per program and render a compact rollup table.
     * Separate from the main /api/dashboard/data fetch because PLO trees are
     * assembled on demand (they walk mappings + section outcomes) — we only
     * pay that cost once the rest of the dashboard is already visible.
     */
    async loadPloSummary(programOverview) {
      const container = document.getElementById(SELECTORS.ploContainer);
      if (!container) return;

      if (!Array.isArray(programOverview) || programOverview.length === 0) {
        container.innerHTML = "";
        container.appendChild(
          this.renderEmptyState(
            "No programs available for PLO rollup",
            "Open PLO Dashboard",
          ),
        );
        return;
      }

      // Fetch tree for each program in parallel; failures fall back to a
      // placeholder row so one bad program doesn't blank the whole panel.
      const fetchOne = async (prog) => {
        const pid = prog.program_id || prog.id;
        if (!pid) return null;
        try {
          const resp = await fetch(
            `/api/programs/${encodeURIComponent(pid)}/plo-dashboard`,
            {
              credentials: "include",
              headers: {
                Accept: "application/json",
                "X-Requested-With": "XMLHttpRequest",
              },
            },
          );
          const body = await resp.json();
          if (!resp.ok || body.success === false) {
            throw new Error(body.error || `HTTP ${resp.status}`);
          }
          return this._summarisePloTree(prog, body);
        } catch (err) {
          // eslint-disable-next-line no-console
          console.warn(`PLO summary fetch failed for ${pid}:`, err);
          return {
            program: prog.program_name || pid,
            plo_count: "—",
            plo_count_sort: -1,
            mapped_clos: "—",
            mapped_clos_sort: -1,
            status: "error",
            pass_rate: "—",
            pass_rate_sort: -1,
          };
        }
      };

      const rows = (await Promise.all(programOverview.map(fetchOne))).filter(
        Boolean,
      );

      if (rows.every((r) => r.plo_count_sort <= 0)) {
        container.innerHTML = "";
        container.appendChild(
          this.renderEmptyState(
            "No Program Learning Outcomes defined yet",
            "Open PLO Dashboard",
          ),
        );
        const btn = container.querySelector("button");
        if (btn) btn.onclick = () => (window.location.href = "/plo-dashboard");
        return;
      }

      const table = globalThis.panelManager.createSortableTable({
        id: "program-plo-table",
        columns: [
          { key: "program", label: "Program", sortable: true },
          { key: "plo_count", label: "PLOs", sortable: true },
          { key: "mapped_clos", label: "Mapped CLOs", sortable: true },
          { key: "status", label: "Mapping", sortable: true },
          { key: "pass_rate", label: "Pass Rate", sortable: true },
        ],
        data: rows,
      });

      container.innerHTML = "";
      container.appendChild(table);
    },

    /**
     * Collapse a full PLO tree response into a single summary row.
     * - mapped CLO count = distinct CLOs across all PLOs
     * - overall pass rate = students_passed / students_took across all PLO aggs
     */
    _summarisePloTree(prog, tree) {
      const plos = Array.isArray(tree.plos) ? tree.plos : [];
      const mappedCloIds = new Set();
      let took = 0;
      let passed = 0;
      plos.forEach((plo) => {
        (plo.clos || []).forEach((clo) => {
          if (clo.outcome_id) mappedCloIds.add(clo.outcome_id);
        });
        const agg = plo.aggregate || {};
        if (typeof agg.students_took === "number") took += agg.students_took;
        if (typeof agg.students_passed === "number")
          passed += agg.students_passed;
      });
      const rate = took > 0 ? Math.round((passed / took) * 100) : null;
      const status = tree.mapping_status || "none";
      return {
        program: prog.program_name || prog.program_id || "—",
        plo_count: plos.length.toString(),
        plo_count_sort: plos.length,
        mapped_clos: mappedCloIds.size.toString(),
        mapped_clos_sort: mappedCloIds.size,
        status,
        pass_rate: rate === null ? "—" : `${rate}%`,
        pass_rate_sort: rate === null ? -1 : rate,
      };
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
