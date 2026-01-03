/**
 * Get status badge HTML with color-coded scheme:
 * Unassigned=grey, Assigned=black, In Progress=blue,
 * Needs Rework=orange, Awaiting Approval=yellow-green, Approved=green, NCI=red
 */
function getStatusBadge(status) {
  const span = document.createElement("span");
  span.className = "badge";

  const config = {
    unassigned: { bg: "#6c757d", text: "Unassigned" },
    assigned: { bg: "#212529", text: "Assigned" },
    in_progress: { bg: "#0d6efd", text: "In Progress" },
    awaiting_approval: { bg: "#9acd32", text: "Awaiting Approval" },
    approval_pending: { bg: "#fd7e14", text: "Needs Rework" },
    approved: { bg: "#198754", text: "✓ Approved" },
    never_coming_in: { bg: "#dc3545", text: "NCI" },
  };

  const setup = config[status] || { bg: "#6c757d", text: "Unknown" };
  span.style.backgroundColor = setup.bg;
  span.textContent = setup.text;
  return span;
}

/**
 * Format date string
 */
function formatDate(dateString) {
  if (!dateString) return "N/A";
  const date = new Date(dateString);
  return date.toLocaleString();
}

/**
 * Truncate text
 */
function truncateText(text, maxLength) {
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + "...";
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Format status for CSV export (plain text)
 */
function formatStatusLabel(status) {
  const labels = {
    unassigned: "Unassigned",
    assigned: "Assigned",
    in_progress: "In Progress",
    awaiting_approval: "Awaiting Approval",
    approval_pending: "Needs Rework",
    approved: "Approved",
    never_coming_in: "Never Coming In",
  };
  return labels[status] || status || "";
}

/**
 * Format date for CSV export (ISO string)
 */
function formatDateForCsv(dateString) {
  if (!dateString) return "";
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toISOString();
}

/**
 * Escape CSV value
 */
function escapeForCsv(value) {
  if (value === null || value === undefined) {
    return '""';
  }
  const text = String(value);
  return `"${text.replace(/"/g, '""')}"`;
}

/**
 * Calculate success rate based on students took/passed
 */
function calculateSuccessRate(clo) {
  const took = typeof clo.students_took === "number" ? clo.students_took : null;
  const passed =
    typeof clo.students_passed === "number" ? clo.students_passed : null;
  if (!took || took <= 0 || passed === null || passed === undefined) {
    return null;
  }
  return Math.round((passed / took) * 100);
}

/**
 * Export current CLO list to CSV
 */
function exportCurrentViewToCsv(cloList) {
  if (!Array.isArray(cloList) || cloList.length === 0) {
    alert("No CLO records available to export for the selected filters.");
    return false;
  }

  const headers = [
    "Course",
    "CLO Number",
    "Status",
    "Instructor",
    "Submitted At",
    "Students Took",
    "Students Passed",
    "Success Rate (%)",
    "Term",
    "Assessment Tool",
  ];

  const rows = cloList.map((clo) => [
    [clo.course_number || "", clo.course_title || ""]
      .filter(Boolean)
      .join(" - "),
    clo.clo_number || "",
    formatStatusLabel(clo.status),
    clo.instructor_name || "",
    formatDateForCsv(clo.submitted_at),
    clo.students_took ?? "",
    clo.students_passed ?? "",
    calculateSuccessRate(clo),
    clo.term_name || "",
    clo.assessment_tool || "",
  ]);

  const csvLines = [
    headers.map(escapeForCsv).join(","),
    ...rows.map((row) => row.map(escapeForCsv).join(",")),
  ];
  const csvContent = csvLines.join("\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `clo_audit_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  return true;
}

/**
 * Approve CLO (extracted for testability)
 */
async function approveCLO() {
  if (!globalThis.currentCLO) return;



  const outcomeId = globalThis.currentCLO.outcome_id;
  if (!outcomeId) {
    alert("Error: CLO ID not found");
    return;
  }

  try {
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

    const response = await fetch(`/api/outcomes/${outcomeId}/approve`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to approve CLO");
    }

    // Close modal
    const cloDetailModal = document.getElementById("cloDetailModal");
    const modal = bootstrap.Modal.getInstance(cloDetailModal);
    modal.hide();

    // Show success
    // Show success - Removed alert per request
    // alert('CLO approved successfully!');

    // Reload list
    await globalThis.loadCLOs();
  } catch (error) {
    alert("Failed to approve CLO: " + error.message);
  }
}

/**
 * Mark CLO as Never Coming In (NCI) (extracted for testability)
 */
async function markAsNCI() {
  if (!globalThis.currentCLO) return;

  const reason = prompt(
    `Mark this CLO as "Never Coming In"?\n\n${globalThis.currentCLO.course_number} - CLO ${globalThis.currentCLO.clo_number}\n\nOptional: Provide a reason (e.g., "Instructor left institution", "Non-responsive instructor"):`,
  );

  // null means cancelled, empty string is allowed
  if (reason === null) {
    return;
  }

  try {
    const outcomeId = globalThis.currentCLO.outcome_id;

    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

    const response = await fetch(`/api/outcomes/${outcomeId}/mark-nci`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify({
        reason: reason.trim() || null,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to mark CLO as NCI");
    }

    // Close modal
    const cloDetailModal = document.getElementById("cloDetailModal");
    const modal = bootstrap.Modal.getInstance(cloDetailModal);
    modal.hide();

    // Show success
    alert("CLO marked as Never Coming In (NCI)");

    // Reload list
    await globalThis.loadCLOs();
    await globalThis.updateStats();
  } catch (error) {
    alert("Failed to mark CLO as NCI: " + error.message);
  }
}

/**
 * Render CLO details in modal (extracted for testability)
 */
function renderCLODetails(clo) {
  const container = document.createElement("div");

  // Header / Status
  const statusRow = document.createElement("div");
  statusRow.className = "mb-3";
  const statusFlex = document.createElement("div");
  statusFlex.className =
    "d-flex justify-content-between align-items-center mb-2";
  const statusH6 = document.createElement("h6");
  statusH6.className = "mb-0";
  statusH6.textContent = "Status";
  statusFlex.appendChild(statusH6);
  statusFlex.appendChild(getStatusBadge(clo.status));
  statusRow.appendChild(statusFlex);
  container.appendChild(statusRow);

  // Course / CLO Number
  const courseRow = document.createElement("div");
  courseRow.className = "row mb-3";

  const courseCol = document.createElement("div");
  courseCol.className = "col-md-6";
  const courseStrong = document.createElement("strong");
  courseStrong.textContent = "Course:";
  courseCol.appendChild(courseStrong);
  courseCol.appendChild(
    document.createTextNode(
      ` ${clo.course_number || "N/A"} - ${clo.course_title || "N/A"}`,
    ),
  );
  courseRow.appendChild(courseCol);

  const cloCol = document.createElement("div");
  cloCol.className = "col-md-6";
  const cloStrong = document.createElement("strong");
  cloStrong.textContent = "CLO Number:";
  cloCol.appendChild(cloStrong);
  cloCol.appendChild(document.createTextNode(` ${clo.clo_number || "N/A"}`));
  courseRow.appendChild(cloCol);

  container.appendChild(courseRow);

  // Description
  const descRow = document.createElement("div");
  descRow.className = "mb-3";
  const descStrong = document.createElement("strong");
  descStrong.textContent = "Description:";
  descRow.appendChild(descStrong);
  const descP = document.createElement("p");
  descP.textContent = clo.description;
  descRow.appendChild(descP);
  container.appendChild(descRow);

  // Instructor
  const instructorRow = document.createElement("div");
  instructorRow.className = "row mb-3";

  const instructorCol = document.createElement("div");
  instructorCol.className = "col-md-6";
  const instructorStrong = document.createElement("strong");
  instructorStrong.textContent = "Instructor:";
  instructorCol.appendChild(instructorStrong);
  instructorCol.appendChild(
    document.createTextNode(` ${clo.instructor_name || "N/A"}`),
  );
  instructorRow.appendChild(instructorCol);

  const instructorEmailCol = document.createElement("div");
  instructorEmailCol.className = "col-md-6";
  const instructorEmailStrong = document.createElement("strong");
  instructorEmailStrong.textContent = "Instructor Email:";
  instructorEmailCol.appendChild(instructorEmailStrong);
  instructorEmailCol.appendChild(
    document.createTextNode(` ${clo.instructor_email || "N/A"}`),
  );
  instructorRow.appendChild(instructorEmailCol);

  container.appendChild(instructorRow);

  // Term / Assessment Tool
  const termRow = document.createElement("div");
  termRow.className = "row mb-3";

  const termCol = document.createElement("div");
  termCol.className = "col-md-6";
  const termStrong = document.createElement("strong");
  termStrong.textContent = "Term:";
  termCol.appendChild(termStrong);
  termCol.appendChild(document.createTextNode(` ${clo.term_name || "—"}`));
  termRow.appendChild(termCol);

  const toolCol = document.createElement("div");
  toolCol.className = "col-md-6";
  const toolStrong = document.createElement("strong");
  toolStrong.textContent = "Assessment Tool:";
  toolCol.appendChild(toolStrong);
  toolCol.appendChild(
    document.createTextNode(` ${clo.assessment_tool || "—"}`),
  );
  termRow.appendChild(toolCol);

  container.appendChild(termRow);

  // Attachments
  const attachmentRow = document.createElement("div");
  attachmentRow.className = "mb-3";
  const attachmentStrong = document.createElement("strong");
  attachmentStrong.textContent = "Attachments:";
  attachmentRow.appendChild(attachmentStrong);
  attachmentRow.appendChild(document.createElement("br"));
  const attachmentBtn = document.createElement("button");
  attachmentBtn.className = "btn btn-sm btn-outline-secondary";
  attachmentBtn.disabled = true;
  attachmentBtn.innerHTML =
    '<i class="fas fa-paperclip"></i> View Attachments (Coming Soon)';
  attachmentRow.appendChild(attachmentBtn);
  container.appendChild(attachmentRow);

  container.appendChild(document.createElement("hr"));

  // Assessment Data
  const dataH6 = document.createElement("h6");
  dataH6.className = "mb-3";
  dataH6.textContent = "Assessment Data";
  container.appendChild(dataH6);

  const assessmentRow = document.createElement("div");
  assessmentRow.className = "row mb-3";

  const studentsTook = clo.students_took || 0;
  const studentsPassed = clo.students_passed || 0;
  const percentage =
    studentsTook > 0 ? Math.round((studentsPassed / studentsTook) * 100) : 0;

  const stats = [
    { value: studentsTook, label: "Students Took" },
    { value: studentsPassed, label: "Students Passed" },
    { value: `${percentage}%`, label: "Success Rate" },
  ];

  stats.forEach((stat) => {
    const col = document.createElement("div");
    col.className = "col-md-4";
    const box = document.createElement("div");
    box.className = "text-center p-3 bg-light rounded";
    const h4 = document.createElement("h4");
    h4.className = "mb-0";
    h4.textContent = stat.value;
    const small = document.createElement("small");
    small.className = "text-muted";
    small.textContent = stat.label;
    box.appendChild(h4);
    box.appendChild(small);
    col.appendChild(box);
    assessmentRow.appendChild(col);
  });
  container.appendChild(assessmentRow);

  // Narrative
  if (clo.narrative) {
    const narrativeRow = document.createElement("div");
    narrativeRow.className = "mb-3";
    const narrativeStrong = document.createElement("strong");
    narrativeStrong.textContent = "Narrative:";
    narrativeRow.appendChild(narrativeStrong);
    const narrativeP = document.createElement("p");
    narrativeP.className = "text-muted";
    narrativeP.textContent = clo.narrative;
    narrativeRow.appendChild(narrativeP);
    container.appendChild(narrativeRow);
  }

  // Admin Feedback
  if (clo.feedback_comments) {
    const feedbackRow = document.createElement("div");
    feedbackRow.className = "mb-3";
    const feedbackStrong = document.createElement("strong");
    feedbackStrong.textContent = "Admin Feedback:";
    feedbackRow.appendChild(feedbackStrong);
    const feedbackP = document.createElement("p");
    feedbackP.className = "text-muted";
    feedbackP.textContent = clo.feedback_comments;
    feedbackRow.appendChild(feedbackP);
    container.appendChild(feedbackRow);
  }

  // Reviewer Info
  if (clo.reviewed_by_name) {
    const reviewerRow = document.createElement("div");
    reviewerRow.className = "mt-3 text-muted small";
    const em = document.createElement("em");
    em.textContent = `Reviewed by ${clo.reviewed_by_name} on ${formatDate(clo.reviewed_at)}`;
    reviewerRow.appendChild(em);
    container.appendChild(reviewerRow);
  }

  return container;
}

// Assign to globalThis IMMEDIATELY for browser use (not inside DOMContentLoaded)
// This ensures functions are available even if DOM is already loaded
// Note: globalThis is preferred over window for ES2020 cross-environment compatibility
globalThis.approveCLO = approveCLO;
globalThis.markAsNCI = markAsNCI;

document.addEventListener("DOMContentLoaded", () => {
  // DOM elements
  const statusFilter = document.getElementById("statusFilter");
  const sortBy = document.getElementById("sortBy");
  const sortOrder = document.getElementById("sortOrder");
  const programFilter = document.getElementById("programFilter");
  const termFilter = document.getElementById("termFilter");
  const exportButton = document.getElementById("exportCsvBtn");
  const cloListContainer = document.getElementById("cloListContainer");
  const cloDetailModal = document.getElementById("cloDetailModal");
  const requestReworkModal = document.getElementById("requestReworkModal");
  const requestReworkForm = document.getElementById("requestReworkForm");

  // State - use window for global access by extracted functions
  globalThis.currentCLO = null;
  let allCLOs = [];

  // Expose functions on window for access by extracted functions (approveCLO, markAsNCI)
  globalThis.loadCLOs = loadCLOs;
  globalThis.updateStats = updateStats;

  // Initialize
  initialize();

  // Event listeners
  statusFilter.addEventListener("change", loadCLOs);
  sortBy.addEventListener("change", renderCLOList);
  sortOrder.addEventListener("change", renderCLOList);
  if (programFilter) {
    programFilter.addEventListener("change", loadCLOs);
  }
  if (termFilter) {
    termFilter.addEventListener("change", loadCLOs);
  }
  if (exportButton) {
    exportButton.addEventListener("click", () => {
      exportCurrentViewToCsv(allCLOs);
    });
  }

  // Event delegation for CLO row clicks
  cloListContainer.addEventListener("click", (e) => {
    const row = e.target.closest("tr[data-outcome-id]");
    if (row && !e.target.closest(".clo-actions")) {
      const outcomeId = row.dataset.outcomeId;
      if (outcomeId) {
        globalThis.showCLODetails(outcomeId);
      }
      return;
    }

    // Handle View button clicks
    const viewBtn = e.target.closest("button[data-outcome-id]");
    if (viewBtn) {
      e.stopPropagation();
      const outcomeId = viewBtn.dataset.outcomeId;
      if (outcomeId) {
        globalThis.showCLODetails(outcomeId);
      }
    }
  });

  requestReworkForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    await submitReworkRequest();
  });

  /**
   * Initialize filters (programs, terms)
   */
  async function initialize() {
    try {
      // Load programs
      const progResponse = await fetch("/api/programs");
      if (progResponse.ok) {
        const data = await progResponse.json();
        const programs = data.programs || [];
        if (programFilter) {
          programs.forEach((prog) => {
            const option = document.createElement("option");
            option.value = prog.program_id || prog.id; // API returns program_id
            option.textContent = prog.name;
            programFilter.appendChild(option);
          });
        }
      }

      // Load terms
      const termResponse = await fetch("/api/terms");
      if (termResponse.ok) {
        const data = await termResponse.json();
        const terms = data.terms || [];
        if (termFilter) {
          // Sort terms by start date descending (newest first)
          terms.sort((a, b) => new Date(b.start_date) - new Date(a.start_date));

          terms.forEach((term) => {
            const option = document.createElement("option");
            option.value = term.term_id;
            option.textContent = term.term_name;
            termFilter.appendChild(option);
          });
        }
      }

      // Initial load of CLOs
      await loadCLOs();
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error("Failed to initialize filters:", error);
      // Fallback to loading CLOs even if filters fail
      await loadCLOs();
    }
  }

  /**
   * Load CLOs from API
   */
  async function loadCLOs() {
    try {
      // nosemgrep
      // nosemgrep
      cloListContainer.innerHTML = `
                <div class="text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="text-muted mt-2">Loading CLOs...</p>
                </div>
            `;

      const status = statusFilter.value;
      const programId = programFilter ? programFilter.value : "";
      const termId = termFilter ? termFilter.value : "";

      const params = new URLSearchParams();
      if (status !== "all") params.append("status", status);
      if (programId) params.append("program_id", programId);
      if (termId) params.append("term_id", termId);

      const queryString = params.toString();
      const url = queryString
        ? `/api/outcomes/audit?${queryString}`
        : "/api/outcomes/audit";

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error("Failed to load CLOs");
      }

      const data = await response.json();
      allCLOs = data.outcomes || [];

      // Update stats
      updateStats();

      // Render list
      renderCLOList();
    } catch (error) {
      // Log error to aid debugging
      // eslint-disable-next-line no-console
      console.error("Error loading CLOs:", error);
      // nosemgrep
      cloListContainer.innerHTML = `
                <div class="alert alert-danger">
                    <strong>Error:</strong> Failed to load CLOs. ${error.message}
                </div>
            `;
    }
  }

  /**
   * Update summary statistics
   * Top stats are UNFILTERED source of truth for the institution (not affected by filter dropdowns)
   */
  async function updateStats() {
    try {
      // Full CLO lifecycle: Unassigned → Assigned → In Progress → Needs Rework → Awaiting Approval → Approved → NCI
      const statuses = [
        "unassigned",
        "assigned",
        "in_progress",
        "approval_pending",
        "awaiting_approval",
        "approved",
        "never_coming_in",
      ];

      // Top stats are UNFILTERED - no program/term filters applied
      // This provides source of truth totals for the institution

      const promises = statuses.map((status) => {
        const params = new URLSearchParams();
        params.append("status", status);
        // No filters - these are institution-wide totals

        return fetch(`/api/outcomes/audit?${params.toString()}`)
          .then((r) => {
            if (!r.ok) {
              throw new Error(`HTTP ${r.status}: ${r.statusText}`);
            }
            return r.json();
          })
          .then((d) => d.count || 0)
          .catch((err) => {
            // Return 0 for individual status failures to allow graceful degradation
            // eslint-disable-next-line no-console
            console.warn(
              "Failed to fetch stats for status:",
              status,
              err.message,
            );
            return 0;
          });
      });

      const [
        unassigned,
        assigned,
        inProgress,
        pending,
        awaiting,
        approved,
        nci,
      ] = await Promise.all(promises);

      if (document.getElementById("statUnassigned")) {
        document.getElementById("statUnassigned").textContent = unassigned;
      }
      if (document.getElementById("statAssigned")) {
        document.getElementById("statAssigned").textContent = assigned;
      }
      document.getElementById("statInProgress").textContent = inProgress;
      document.getElementById("statNeedsRework").textContent = pending;
      document.getElementById("statAwaitingApproval").textContent = awaiting;
      document.getElementById("statApproved").textContent = approved;
      if (document.getElementById("statNCI")) {
        document.getElementById("statNCI").textContent = nci;
      }
    } catch (error) {
      // Log error to aid debugging, but allow graceful degradation
      // Stats are nice-to-have, not critical functionality
      // eslint-disable-next-line no-console
      console.warn(
        "Error updating dashboard stats (non-critical):",
        error.message || error,
      );
    }
  }

  /**
   * Render CLO list
   */
  function renderCLOList() {
    cloListContainer.textContent = ""; // Clear current content

    if (allCLOs.length === 0) {
      const emptyDiv = document.createElement("div");
      emptyDiv.className = "text-center py-5";
      const p = document.createElement("p");
      p.className = "text-muted";
      p.textContent = "No CLOs found for the selected filter.";
      emptyDiv.appendChild(p);
      cloListContainer.appendChild(emptyDiv);
      return;
    }

    // Sort CLOs
    const sorted = sortCLOs([...allCLOs]);

    const tableResp = document.createElement("div");
    tableResp.className = "table-responsive";

    const table = document.createElement("table");
    table.className = "table table-hover";

    // Header
    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    [
      "Status",
      "Course",
      "CLO #",
      "Description",
      "Instructor",
      "Submitted",
      "Actions",
    ].forEach((text) => {
      const th = document.createElement("th");
      th.textContent = text;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Body
    const tbody = document.createElement("tbody");
    sorted.forEach((clo) => {
      const tr = document.createElement("tr");
      tr.className = "clo-row";
      tr.style.cursor = "pointer";
      tr.dataset.outcomeId = clo.outcome_id;

      // Status
      const tdStatus = document.createElement("td");
      tdStatus.appendChild(getStatusBadge(clo.status));
      tr.appendChild(tdStatus);

      // Course
      const tdCourse = document.createElement("td");
      const strong = document.createElement("strong");
      strong.textContent = clo.course_number || "N/A";
      tdCourse.appendChild(strong);
      tr.appendChild(tdCourse);

      // CLO #
      const tdCloNum = document.createElement("td");
      tdCloNum.textContent = clo.clo_number || "N/A";
      tr.appendChild(tdCloNum);

      // Description
      const tdDesc = document.createElement("td");
      tdDesc.textContent = truncateText(clo.description, 60);
      tr.appendChild(tdDesc);

      // Instructor
      const tdInst = document.createElement("td");
      tdInst.textContent = clo.instructor_name || "N/A";
      tr.appendChild(tdInst);

      // Submitted
      const tdSub = document.createElement("td");
      const small = document.createElement("small");
      small.textContent = clo.submitted_at
        ? formatDate(clo.submitted_at)
        : "N/A";
      tdSub.appendChild(small);
      tr.appendChild(tdSub);

      // Actions
      const tdActions = document.createElement("td");
      tdActions.className = "clo-actions";
      const btnGroup = document.createElement("div");
      btnGroup.className = "btn-group btn-group-sm";
      const btn = document.createElement("button");
      btn.className = "btn btn-outline-primary";
      btn.dataset.outcomeId = clo.outcome_id;
      // Using innerHTML for static icon markup is generally accepted by semgrep
      // but we could also use font-awesome class on an 'i' element
      const icon = document.createElement("i");
      icon.className = "fas fa-eye";
      btn.appendChild(icon);
      btn.appendChild(document.createTextNode(" View"));
      btnGroup.appendChild(btn);
      tdActions.appendChild(btnGroup);
      tr.appendChild(tdActions);

      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    tableResp.appendChild(table);
    cloListContainer.appendChild(tableResp);
  }

  /**
   * Sort CLOs based on current sort settings
   */
  function sortCLOs(clos) {
    const by = sortBy.value;
    const order = sortOrder.value;

    clos.sort((a, b) => {
      let aVal, bVal;

      switch (by) {
        case "submitted_at":
          aVal = a.submitted_at || "";
          bVal = b.submitted_at || "";
          break;
        case "course_number":
          aVal = a.course_number || "";
          bVal = b.course_number || "";
          break;
        case "instructor_name":
          aVal = a.instructor_name || "";
          bVal = b.instructor_name || "";
          break;
        default:
          return 0;
      }

      let comparison;
      if (aVal < bVal) {
        comparison = -1;
      } else if (aVal > bVal) {
        comparison = 1;
      } else {
        comparison = 0;
      }
      return order === "asc" ? comparison : -comparison;
    });

    return clos;
  }

  /**
   * Show CLO details in modal
   */
  globalThis.showCLODetails = async function (cloId) {
    try {
      const response = await fetch(`/api/outcomes/${cloId}/audit-details`);
      if (!response.ok) {
        throw new Error("Failed to load CLO details");
      }

      const data = await response.json();
      globalThis.currentCLO = data.outcome;
      const clo = globalThis.currentCLO;

      // Render HTML using extracted function
      // nosemgrep
      const cloDetailContainer = document.getElementById("cloDetailContent");
      cloDetailContainer.replaceChildren(renderCLODetails(clo));

      // Show/hide action buttons based on status
      const canApprove = ["awaiting_approval", "approval_pending"].includes(
        clo.status,
      );
      const canMarkNCI = [
        "awaiting_approval",
        "approval_pending",
        "assigned",
        "in_progress",
      ].includes(clo.status);
      document.getElementById("approveBtn").style.display = canApprove
        ? "inline-block"
        : "none";
      document.getElementById("requestReworkBtn").style.display = canApprove
        ? "inline-block"
        : "none";
      document.getElementById("markNCIBtn").style.display = canMarkNCI
        ? "inline-block"
        : "none";

      const modal = new bootstrap.Modal(cloDetailModal);
      modal.show();
    } catch (error) {
      alert("Failed to load CLO details: " + error.message);
    }
  };

  /**
   * Open rework modal
   */
  globalThis.openReworkModal = function () {
    if (!globalThis.currentCLO) return;

    document.getElementById("reworkCloDescription").textContent =
      `${globalThis.currentCLO.course_number} - CLO ${globalThis.currentCLO.clo_number}: ${globalThis.currentCLO.description}`;
    document.getElementById("feedbackComments").value = "";
    document.getElementById("sendEmailCheckbox").checked = true;

    // Hide detail modal
    const detailModalInstance = bootstrap.Modal.getInstance(cloDetailModal);
    if (detailModalInstance) {
      detailModalInstance.hide();
    }

    // Show rework modal
    const modal = new bootstrap.Modal(requestReworkModal);
    modal.show();
  };

  /**
   * Submit rework request
   */
  async function submitReworkRequest() {
    if (!globalThis.currentCLO) return;

    const comments = document.getElementById("feedbackComments").value.trim();
    const sendEmail = document.getElementById("sendEmailCheckbox").checked;

    if (!comments) {
      alert("Please provide feedback comments");
      return;
    }

    const outcomeId = globalThis.currentCLO.outcome_id;
    if (!outcomeId) {
      alert("Error: CLO ID not found");
      return;
    }

    try {
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      const response = await fetch(
        `/api/outcomes/${outcomeId}/request-rework`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrfToken,
          },
          body: JSON.stringify({
            comments,
            send_email: sendEmail,
          }),
        },
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to request rework");
      }

      // Close modal
      const modal = bootstrap.Modal.getInstance(requestReworkModal);
      modal.hide();

      // Show success
      alert(
        "Rework request sent successfully!" +
        (sendEmail ? " Email notification sent." : ""),
      );

      // Reload list
      await loadCLOs();
    } catch (error) {
      alert("Failed to request rework: " + error.message);
    }
  }
});

// Export for testing (Node.js environment only)
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    getStatusBadge,
    formatDate,
    truncateText,
    escapeHtml,
    renderCLODetails,
    approveCLO,
    markAsNCI,
    formatStatusLabel,
    formatDateForCsv,
    escapeForCsv,
    calculateSuccessRate,
    exportCurrentViewToCsv,
  };
}
