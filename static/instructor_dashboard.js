/* global setLoadingState, setErrorState */
(function () {
  const API_ENDPOINT = "/api/dashboard/data";
  const SELECTORS = {
    name: "instructorName",
    courseCount: "instructorCourseCount",
    sectionCount: "instructorSectionCount",
    studentCount: "instructorStudentCount",
    assessmentProgress: "instructorAssessmentProgress",
    teachingContainer: "instructorTeachingContainer",
    assessmentContainer: "instructorAssessmentContainer",
    activityList: "instructorActivityList",
    summaryContainer: "instructorSummaryContainer",
  };

  const InstructorDashboard = {
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
        this.setLoading(
          SELECTORS.assessmentContainer,
          "Loading assessment tasks...",
        );
        this.setLoading(SELECTORS.summaryContainer, "Building summary...");
        const activityList = document.getElementById(SELECTORS.activityList);
        if (activityList) {
          activityList.innerHTML =
            '<li class="text-muted">Fetching recent activity…</li>';
        }
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
        console.warn("Instructor dashboard load error:", error);
        this.showError(
          SELECTORS.assessmentContainer,
          "Unable to load assessment tasks",
        );
        this.showError(SELECTORS.summaryContainer, "Unable to build summary");
        const activityList = document.getElementById(SELECTORS.activityList);
        if (activityList) {
          activityList.innerHTML =
            '<li class="text-danger">Unable to load recent activity</li>';
        }
      }
    },

    render(data) {
      this.updateHeader(data);
      // Teaching panel removed, Assessment panel now uses course assignment data
      this.renderAssessmentTasks(data.teaching_assignments || []);
      this.renderRecentActivity(data.assessment_tasks || []);
      this.renderCourseSummary(
        data.teaching_assignments || [],
        data.sections || [],
      );
      const lastUpdated =
        data.metadata && data.metadata.last_updated
          ? data.metadata.last_updated
          : null;
      this.updateLastUpdated(lastUpdated);
    },

    updateHeader(data) {
      const summary = data.summary || {};
      document.getElementById(SELECTORS.courseCount).textContent =
        summary.courses ?? 0;
      document.getElementById(SELECTORS.sectionCount).textContent =
        summary.sections ?? 0;
      document.getElementById(SELECTORS.studentCount).textContent =
        summary.students ?? 0;

      const tasks = data.assessment_tasks || [];
      if (tasks.length) {
        const completed = tasks.filter((task) =>
          this.isTaskComplete(task.status),
        ).length;
        const percent = Math.round((completed / tasks.length) * 100);
        document.getElementById(SELECTORS.assessmentProgress).textContent =
          `${percent}%`;
      } else {
        document.getElementById(SELECTORS.assessmentProgress).textContent =
          "0%";
      }
    },

    renderAssessmentTasks(assignments) {
      const container = document.getElementById(SELECTORS.assessmentContainer);
      if (!container) return;

      if (!assignments.length) {
        container.innerHTML = "";
        container.appendChild(
          this.renderEmptyState(
            "No teaching assignments found",
            "View Schedule",
          ),
        );
        return;
      }

      const table = globalThis.panelManager.createSortableTable({
        id: "instructor-assessment-table",
        columns: [
          { key: "course", label: "Course", sortable: true },
          { key: "clos", label: "CLOs", sortable: true },
          { key: "progress", label: "Completion", sortable: true },
        ],
        data: assignments.map((assignment) => {
          const courseId = assignment.course_id || "";
          const cloCount = Number(assignment.clo_count ?? 0);
          const percent = Number(assignment.percent_complete ?? 0);
          const completed = Number(assignment.clos_completed ?? 0);

          // Build URL
          const url = courseId
            ? `/assessments?course=${courseId}`
            : "/assessments";

          return {
            course: assignment.course_number
              ? `<a href="${url}" class="text-decoration-none fw-bold">${assignment.course_number} — ${assignment.course_title || ""}</a>`
              : `<a href="${url}" class="text-decoration-none fw-bold">${assignment.course_title || "Course"}</a>`,
            clos: cloCount > 0 ? cloCount.toString() : "None",
            clos_sort: cloCount.toString(),
            progress:
              cloCount > 0
                ? `<div class="d-flex align-items-center">
                <div class="progress flex-grow-1 me-2" style="height: 10px;">
                  <div class="progress-bar" role="progressbar" style="width: ${Math.min(percent, 100)}%;" aria-valuenow="${percent}" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
                <span class="small text-muted">${percent}% (${completed}/${cloCount})</span>
              </div>`
                : '<span class="text-muted small">No defined CLOs</span>',
            progress_sort: cloCount > 0 ? percent : -1,
          };
        }),
      });

      container.innerHTML = "";
      container.appendChild(table);
    },

    renderRecentActivity(tasks) {
      const list = document.getElementById(SELECTORS.activityList);
      if (!list) return;

      list.innerHTML = ""; // Clear existing content

      if (!tasks.length) {
        list.innerHTML = '<li class="text-muted">No recent activity</li>';
        return;
      }

      tasks.slice(0, 5).forEach((task) => {
        const li = document.createElement("li");
        const strong = document.createElement("strong");
        strong.textContent =
          task.course_number || task.course_title || "Course";
        li.appendChild(strong);

        const status = (task.status || "pending").replace(/_/g, " ");
        const due = task.due_date
          ? new Date(task.due_date).toLocaleDateString()
          : "—";

        li.appendChild(document.createTextNode(` — ${status} `));

        const span = document.createElement("span");
        span.className = "text-muted";
        span.textContent = `(Due ${due})`;
        li.appendChild(span);

        list.appendChild(li);
      });
    },

    renderCourseSummary(assignments, sections) {
      const container = document.getElementById(SELECTORS.summaryContainer);
      if (!container) return;

      if (!assignments.length) {
        container.innerHTML = "";
        container.appendChild(
          this.renderEmptyState("No course summary available", "Refresh"),
        );
        return;
      }

      const sectionsByCourse = new Map();
      sections.forEach((section) => {
        const courseId = section.course_id;
        if (!courseId) return;
        const list = sectionsByCourse.get(courseId) || [];
        list.push(section);
        sectionsByCourse.set(courseId, list);
      });

      const table = globalThis.panelManager.createSortableTable({
        id: "instructor-summary-table",
        columns: [
          { key: "course", label: "Course", sortable: true },
          { key: "sections", label: "Sections", sortable: true },
          { key: "students", label: "Students", sortable: true },
          { key: "progress", label: "Progress", sortable: true },
        ],
        data: assignments.map((assignment) => {
          const courseId = assignment.course_id;
          const courseSections = sectionsByCourse.get(courseId) || [];
          const enrollment = courseSections.reduce(
            (total, section) => total + (Number(section.enrollment) || 0),
            0,
          );
          const percent = this.deriveCourseProgress(
            assignment.course_id,
            assignment.sections || [],
          );
          return {
            course:
              `${assignment.course_number || assignment.course_id || "Course"} — ${assignment.course_title || ""}`.trim(),
            sections: (
              assignment.section_count ??
              courseSections.length ??
              0
            ).toString(),
            sections_sort: (
              assignment.section_count ??
              courseSections.length ??
              0
            ).toString(),
            students: enrollment.toString(),
            students_sort: enrollment.toString(),
            progress: `${percent}%`,
            progress_sort: percent,
          };
        }),
      });

      container.innerHTML = "";
      container.appendChild(table);
    },

    deriveCourseProgress(courseId, sections) {
      if (!sections || !sections.length) return 0;
      const completed = sections.filter((section) =>
        this.isTaskComplete(section.status),
      ).length;
      return Math.round((completed / sections.length) * 100);
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

    isTaskComplete(status) {
      if (!status) return false;
      const normalized = status.toLowerCase();
      return (
        normalized === "completed" ||
        normalized === "done" ||
        normalized === "complete"
      );
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
      InstructorDashboard.init();
      globalThis.InstructorDashboard = InstructorDashboard;
    }, 100);
  });

  if (typeof module !== "undefined" && module.exports) {
    module.exports = InstructorDashboard;
  }
})();
