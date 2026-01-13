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

  const outcomeId =
    globalThis.currentCLO.id || globalThis.currentCLO.outcome_id;
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
    const outcomeId =
      globalThis.currentCLO.id || globalThis.currentCLO.outcome_id; // Use Section ID, not Template ID

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

// Global variables
let allCLOs = [];
// Expose for testing
if (typeof globalThis !== "undefined") {
  globalThis._getAllCLOs = () => allCLOs;
}

// Assign to globalThis IMMEDIATELY for browser use (not inside DOMContentLoaded)
// This ensures functions are available even if DOM is already loaded
// Note: globalThis is preferred over window for ES2020 cross-environment compatibility
// Register global functions
globalThis.approveCLO = approveCLO;
globalThis.markAsNCI = markAsNCI;
globalThis.approveOutcome = approveOutcome;
globalThis.assignOutcome = assignOutcome;
globalThis.reopenOutcome = reopenOutcome;
globalThis.remindOutcome = remindOutcome;
globalThis.submitReminder = submitReminder;

/**
 * Direct Approve from Table
 */
async function approveOutcome(outcomeId) {
  try {
    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]',
    )?.content;
    const res = await fetch(`/api/outcomes/${outcomeId}/approve`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
    });
    if (res.ok) {
      await globalThis.loadCLOs();
      return true;
    } else {
      const err = await res.json();
      alert("Failed to approve: " + (err.error || "Unknown error"));
      return false;
    }
  } catch (e) {
    alert("Error approving outcome: " + e.message);
    return false;
  }
}

/**
 * Assign Instructor (Native Modal)
 */
let currentAssignSectionId = null;

async function assignOutcome(outcomeId) {
  const clo = allCLOs.find(
    (c) => c.id === outcomeId || c.outcome_id === outcomeId,
  );
  if (!clo) return;

  // Ensure form is bound
  const form = document.getElementById("assignInstructorForm");
  if (form) form.onsubmit = handleAssignSubmit;

  // Use section_id derived from backend
  if (!clo.section_id) {
    alert("Cannot identify section for assignment. Please contact support.");
    return;
  }

  currentAssignSectionId = clo.section_id;

  const modalEl = document.getElementById("assignInstructorModal");
  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  modal.show();

  await loadInstructors();
}

async function loadInstructors() {
  const select = document.getElementById("assignInstructorSelect");
  if (!select || select.dataset.loaded === "true") return;

  try {
    const res = await fetch("/api/instructors");
    const data = await res.json();

    if (data.success) {
      select.innerHTML = '<option value="">Select Instructor...</option>';
      data.instructors.forEach((inst) => {
        const opt = document.createElement("option");
        opt.value = inst.user_id || inst.id;
        opt.textContent = `${inst.last_name}, ${inst.first_name} (${inst.email})`;
        select.appendChild(opt);
      });
      select.dataset.loaded = "true";
    } else {
      select.innerHTML = "<option>Error loading instructors</option>";
    }
  } catch (e) {
    console.error(e);
    select.innerHTML = "<option>Error loading instructors</option>";
  }
}

async function handleAssignSubmit(e) {
  e.preventDefault();
  const select = document.getElementById("assignInstructorSelect");
  const instructorId = select.value;

  if (!instructorId) {
    alert("Please select an instructor");
    return;
  }

  try {
    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]',
    )?.content;
    const res = await fetch(
      `/api/sections/${currentAssignSectionId}/instructor`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken,
        },
        body: JSON.stringify({ instructor_id: instructorId }),
      },
    );

    if (res.ok) {
      const modalEl = document.getElementById("assignInstructorModal");
      bootstrap.Modal.getInstance(modalEl).hide();
      await globalThis.loadCLOs();
      alert("Instructor assigned successfully.");
    } else {
      const json = await res.json();
      alert("Failed to assign: " + (json.error || "Unknown"));
    }
  } catch (err) {
    alert("Error: " + err.message);
  }
}

async function handleInviteInstructorSubmit(event) {
  event.preventDefault();

  const emailInput = document.getElementById("inviteEmail");
  const firstNameInput = document.getElementById("inviteFirstName");
  const lastNameInput = document.getElementById("inviteLastName");
  const alertBox = document.getElementById("inviteInstructorAlert");
  const submitBtn = document.getElementById("sendInviteBtn");

  if (!emailInput || !firstNameInput || !lastNameInput) {
    alert("Invite form is missing required fields.");
    return;
  }

  if (!currentAssignSectionId) {
    alert("Missing section context for this invitation.");
    return;
  }

  const form = event.target;
  if (form && !form.checkValidity()) {
    form.classList.add("was-validated");
    return;
  }

  if (alertBox) {
    alertBox.classList.add("d-none");
    alertBox.classList.remove("alert-success", "alert-danger");
    alertBox.textContent = "";
  }

  if (submitBtn) {
    submitBtn.disabled = true;
  }

  try {
    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]',
    )?.content;

    const response = await fetch("/api/auth/invite", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken && { "X-CSRFToken": csrfToken }),
      },
      body: JSON.stringify({
        invitee_email: emailInput.value.trim(),
        invitee_role: "instructor",
        first_name: firstNameInput.value.trim(),
        last_name: lastNameInput.value.trim(),
        section_id: currentAssignSectionId,
        replace_existing: true,
      }),
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
      throw new Error(result.error || "Failed to send invitation");
    }

    if (alertBox) {
      alertBox.classList.remove("d-none");
      alertBox.classList.add("alert-success");
      alertBox.textContent = result.message || "Invitation sent successfully!";
    }

    const modalEl = document.getElementById("inviteInstructorModal");
    const modal = modalEl ? bootstrap.Modal.getInstance(modalEl) : null;
    if (modal) {
      modal.hide();
    }

    const successModalEl = document.getElementById("inviteSuccessModal");
    if (successModalEl) {
      const successMessage = document.getElementById("inviteSuccessMessage");
      if (successMessage) {
        successMessage.textContent =
          result.message || "Invitation sent successfully.";
      }
      bootstrap.Modal.getOrCreateInstance(successModalEl).show();
    }

    if (form) {
      form.reset();
      form.classList.remove("was-validated");
    }
  } catch (error) {
    if (alertBox) {
      alertBox.classList.remove("d-none");
      alertBox.classList.add("alert-danger");
      alertBox.textContent =
        error.message || "Failed to send invitation. Please try again.";
    } else {
      alert("Failed to send invitation: " + error.message);
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
    }
    // Refresh the list to show the assigned instructor
    if (typeof globalThis.loadCLOs === "function") {
      await globalThis.loadCLOs();
      document.dispatchEvent(new CustomEvent("faculty-invited"));
    }
  }
}

/**
 * Reopen Outcome (Set status to in_progress)
 */
async function reopenOutcome(outcomeId) {
  if (
    !confirm(
      "Are you sure you want to reopen this outcome? Status will be set to 'In Progress'.",
    )
  )
    return;
  try {
    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]',
    )?.content;
    const res = await fetch(`/api/outcomes/${outcomeId}/reopen`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
    });
    if (res.ok) {
      const modalEl = document.getElementById("cloDetailModal");
      const modal = bootstrap.Modal.getInstance(modalEl);
      if (modal) modal.hide();

      await globalThis.loadCLOs();
    } else {
      const err = await res.json();
      alert("Failed to reopen: " + (err.error || "Unknown error"));
    }
  } catch (e) {
    alert("Error reopening outcome: " + e.message);
  }
}

let reminderContext = null;

function formatShortDate(dateString) {
  if (!dateString) return null;
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toLocaleDateString();
}

/**
 * Send Reminder (opens modal and populates message)
 */
async function remindOutcome(outcomeId, instructorId, courseId) {
  if (!confirm("Are you sure you want to send a reminder?")) return;
  if (!instructorId || !courseId) {
    alert("Missing instructor or course information for this outcome.");
    return;
  }

  const clo = allCLOs.find(
    (c) => c.id === outcomeId || c.outcome_id === outcomeId,
  );
  const modalEl = document.getElementById("sendReminderModal");
  if (!modalEl) {
    alert("Reminder modal is not available. Please refresh and try again.");
    return;
  }

  reminderContext = {
    outcomeId,
    instructorId,
    courseId,
    sectionId: clo?.section_id || null,
  };

  const reminderCloDescription = document.getElementById(
    "reminderCloDescription",
  );
  const reminderCourseDescription = document.getElementById(
    "reminderCourseDescription",
  );
  const reminderInstructorEmail = document.getElementById(
    "reminderInstructorEmail",
  );
  const reminderMessage = document.getElementById("reminderMessage");

  const courseNumber = clo?.course_number || "Course";
  const courseTitle = clo?.course_title || "";
  const sectionLabel = clo?.section_number
    ? `Section ${clo.section_number}`
    : "Section";
  const cloLabel = clo?.clo_number ? `CLO #${clo.clo_number}` : "CLO";
  const termLabel = clo?.term_name ? `${clo.term_name} - ` : "";

  const courseDisplay = courseTitle
    ? `${courseNumber} - ${courseTitle}`
    : courseNumber;

  if (reminderCloDescription) {
    reminderCloDescription.textContent = `${courseNumber} • ${sectionLabel} • ${cloLabel}`;
  }
  if (reminderCourseDescription) {
    reminderCourseDescription.textContent = courseDisplay;
  }

  let instructorName = clo?.instructor_name || "Instructor";
  let instructorEmail = clo?.instructor_email || "";
  let dueDateText = null;

  try {
    const instructorResponse = await fetch(`/api/users/${instructorId}`);
    if (instructorResponse.ok) {
      const instructorData = await instructorResponse.json();
      const user = instructorData.user || {};
      instructorName =
        user.display_name ||
        `${user.first_name || ""} ${user.last_name || ""}`.trim() ||
        instructorName;
      instructorEmail = user.email || instructorEmail;
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.warn("Failed to load instructor details:", error);
  }

  if (reminderInstructorEmail) {
    reminderInstructorEmail.textContent =
      instructorEmail || "Instructor email unavailable";
  }

  if (reminderContext.sectionId) {
    try {
      const sectionResponse = await fetch(
        `/api/sections/${reminderContext.sectionId}`,
      );
      if (sectionResponse.ok) {
        const sectionData = await sectionResponse.json();
        const dueDate = sectionData.section?.assessment_due_date;
        if (dueDate) {
          dueDateText = formatShortDate(dueDate);
        }
      }
    } catch (error) {
      // eslint-disable-next-line no-console
      console.warn("Failed to load section due date:", error);
    }
  }

  if (reminderMessage) {
    const dueLine = dueDateText ? `\nSubmission due date: ${dueDateText}` : "";
    reminderMessage.value =
      `Dear ${instructorName},\n\n` +
      `This is a friendly reminder to submit your assessment results for ` +
      `${termLabel}${courseNumber} (${sectionLabel}) ${cloLabel}.` +
      `${dueLine}\n\n` +
      `Thank you.`;
  }

  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  modal.show();
}

/**
 * Submit reminder email
 */
async function submitReminder(event) {
  if (event && typeof event.preventDefault === "function") {
    event.preventDefault();
  }

  if (!reminderContext) {
    alert("Reminder context is missing. Please try again.");
    return;
  }

  const reminderMessage = document.getElementById("reminderMessage");
  const message = reminderMessage?.value?.trim() || "";
  if (!message) {
    alert("Please provide a reminder message.");
    return;
  }

  try {
    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]',
    )?.content;
    const res = await fetch("/api/send-course-reminder", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify({
        instructor_id: reminderContext.instructorId,
        course_id: reminderContext.courseId,
        message,
      }),
    });

    if (res.ok) {
      const modalEl = document.getElementById("sendReminderModal");
      const modal = modalEl ? bootstrap.Modal.getInstance(modalEl) : null;
      if (modal) modal.hide();
      alert("Reminder sent successfully.");
    } else {
      const err = await res.json();
      alert("Failed to send reminder: " + (err.error || "Unknown error"));
    }
  } catch (e) {
    alert("Error sending reminder: " + e.message);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  // DOM elements
  const statusFilter = document.getElementById("statusFilter");
  const sortBy = document.getElementById("sortBy");
  const sortOrder = document.getElementById("sortOrder");
  const programFilter = document.getElementById("programFilter");
  const termFilter = document.getElementById("termFilter");
  const courseFilter = document.getElementById("courseFilter");
  const exportButton = document.getElementById("exportCsvBtn");
  const cloListContainer = document.getElementById("cloListContainer");
  const cloDetailModal = document.getElementById("cloDetailModal");
  const cloReworkSection = document.getElementById("cloReworkSection");
  const cloReworkForm = document.getElementById("cloReworkForm");
  const reworkFeedbackTextarea = document.getElementById(
    "reworkFeedbackComments",
  );
  const reworkSendEmailCheckbox = document.getElementById("reworkSendEmail");
  const reworkAlert = document.getElementById("reworkAlert");
  const sendReminderForm = document.getElementById("sendReminderForm");
  const inviteNewInstructorBtn = document.getElementById(
    "inviteNewInstructorBtn",
  );
  const inviteInstructorModal = document.getElementById(
    "inviteInstructorModal",
  );
  const inviteInstructorForm = document.getElementById("inviteInstructorForm");
  // Removed unused button assignments to fix ESLint no-unused-vars
  const cancelReworkBtn = document.getElementById("cancelReworkBtn");
  const cloDetailActionsStandard = document.getElementById(
    "cloDetailActionsStandard",
  );
  const cloDetailActionsRework = document.getElementById(
    "cloDetailActionsRework",
  );

  // State - use window for global access by extracted functions
  globalThis.currentCLO = null;
  allCLOs = [];

  // Expose functions on window for access by extracted functions (approveCLO, markAsNCI)
  globalThis.loadCLOs = loadCLOs;
  globalThis.updateStats = updateStats;
  globalThis.pendingReworkOutcomeId = null;

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
  if (courseFilter) {
    courseFilter.addEventListener("change", loadCLOs);
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

  if (cloReworkForm) {
    cloReworkForm.addEventListener("submit", submitReworkRequest);
  }
  if (cancelReworkBtn) {
    cancelReworkBtn.addEventListener("click", () => {
      toggleReworkMode(false);
    });
  }
  if (sendReminderForm) {
    sendReminderForm.addEventListener("submit", submitReminder);
  }
  if (inviteNewInstructorBtn && inviteInstructorModal) {
    inviteNewInstructorBtn.addEventListener("click", (event) => {
      event.preventDefault();
      const assignModalEl = document.getElementById("assignInstructorModal");
      const assignModal = assignModalEl
        ? bootstrap.Modal.getInstance(assignModalEl)
        : null;
      if (assignModal) {
        assignModal.hide();
      }
      bootstrap.Modal.getOrCreateInstance(inviteInstructorModal).show();
    });
  }
  if (inviteInstructorForm) {
    inviteInstructorForm.addEventListener(
      "submit",
      handleInviteInstructorSubmit,
    );
  }
  toggleReworkMode(false);

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
      const termResponse = await fetch("/api/terms?all=true");
      if (termResponse.ok) {
        const data = await termResponse.json();
        const terms = data.terms || [];
        if (termFilter) {
          terms.sort((a, b) => new Date(b.start_date) - new Date(a.start_date));

          terms.forEach((term) => {
            const option = document.createElement("option");
            option.value = term.term_id || term.id || "";
            option.textContent = term.term_name || term.name || "Term";
            termFilter.appendChild(option);
          });
        }
      }

      // Load courses
      const courseResponse = await fetch("/api/courses");
      if (courseResponse.ok) {
        const data = await courseResponse.json();
        const courses = data.courses || [];
        if (courseFilter) {
          // Sort by course number
          courses.sort((a, b) =>
            (a.course_number || "").localeCompare(b.course_number || ""),
          );

          courses.forEach((course) => {
            const option = document.createElement("option");
            option.value = course.course_id || course.id;
            option.textContent = `${course.course_number} - ${course.course_title}`;
            courseFilter.appendChild(option);
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
    const previousScroll =
      window.scrollY || document.documentElement.scrollTop || 0;
    globalThis.loadCLOs = loadCLOs;
    try {
      const status = statusFilter.value;
      const programId = programFilter ? programFilter.value : "";
      const termId = termFilter ? termFilter.value : "";
      const courseId = courseFilter ? courseFilter.value : "";

      const params = new URLSearchParams();
      if (status !== "all") params.append("status", status);
      if (programId) params.append("program_id", programId);
      if (termId) params.append("term_id", termId);
      if (courseId) params.append("course_id", courseId);

      const queryString = params.toString();
      const url = queryString
        ? `/api/outcomes/audit?${queryString}`
        : "/api/outcomes/audit";

      const response = await globalThis.fetch(url);
      if (!response.ok) {
        throw new Error("Failed to load CLOs");
      }

      const data = await response.json();
      allCLOs = data.outcomes || [];

      // Update stats
      updateStats();

      // Render list
      renderCLOList();

      // Restore scroll position once the new DOM has painted
      window.requestAnimationFrame(() => {
        window.scrollTo({
          top: previousScroll,
          behavior: "auto",
        });
      });
    } catch (error) {
      // Log error to aid debugging
      // eslint-disable-next-line no-console
      console.error("Error loading CLOs:", error);
      const errorDiv = document.createElement("div");
      errorDiv.className = "alert alert-danger";
      const strong = document.createElement("strong");
      strong.textContent = "Error:";
      errorDiv.appendChild(strong);
      // Add a space and plain-text error message to avoid HTML injection
      errorDiv.appendChild(
        document.createTextNode(
          " Failed to load CLOs. " +
            (error && error.message ? error.message : ""),
        ),
      );
      cloListContainer.prepend(errorDiv);
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
    // Prevent layout shift/scroll jumping by locking the height
    if (cloListContainer.offsetHeight > 0) {
      cloListContainer.style.minHeight = `${cloListContainer.offsetHeight}px`;
    }

    cloListContainer.textContent = ""; // Clear current content

    const tableResp = document.createElement("div");
    tableResp.className = "table-responsive";

    const table = document.createElement("table");
    table.className = "table table-hover align-middle";

    // Header
    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    [
      "Status",
      "Course",
      "Section",
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

    if (allCLOs.length === 0) {
      const emptyRow = document.createElement("tr");
      const emptyCell = document.createElement("td");
      emptyCell.colSpan = 8;
      emptyCell.className = "text-center text-muted py-4";
      emptyCell.textContent = "No CLOs found for the selected filter.";
      emptyRow.appendChild(emptyCell);
      tbody.appendChild(emptyRow);
      table.appendChild(tbody);
      tableResp.appendChild(table);
      cloListContainer.appendChild(tableResp);
      return;
    }

    // Sort CLOs
    const sorted = sortCLOs([...allCLOs]);

    // Grouping Logic
    const groupedData = {};
    sorted.forEach((clo) => {
      const courseKey = `${clo.course_number || "Unknown"} - ${clo.course_title || ""}`;
      if (!groupedData[courseKey]) groupedData[courseKey] = {};

      const sectionKey = clo.section_number
        ? `Section ${clo.section_number}`
        : "Unassigned Section";
      if (!groupedData[courseKey][sectionKey])
        groupedData[courseKey][sectionKey] = [];

      groupedData[courseKey][sectionKey].push(clo);
    });

    Object.keys(groupedData)
      .sort()
      .forEach((courseKey) => {
        const safeKey = courseKey.replace(/[^a-zA-Z0-9]/g, "");

        // Course Header Row
        const courseRow = document.createElement("tr");
        courseRow.className = "table-light";
        const courseCell = document.createElement("td");
        courseCell.colSpan = 8;

        // Build course header using safe DOM construction
        const courseDiv = document.createElement("div");
        courseDiv.className = "d-flex align-items-center";
        courseDiv.style.cursor = "pointer";
        courseDiv.setAttribute("data-bs-toggle", "collapse");
        courseDiv.setAttribute("data-bs-target", `.group-${safeKey}`);

        const chevronIcon = document.createElement("i");
        chevronIcon.className = "fas fa-chevron-down me-2";
        courseDiv.appendChild(chevronIcon);

        const courseStrong = document.createElement("strong");
        courseStrong.textContent = courseKey;
        courseDiv.appendChild(courseStrong);

        courseCell.appendChild(courseDiv);
        courseRow.appendChild(courseCell);
        tbody.appendChild(courseRow);

        const sectionGroups = groupedData[courseKey];
        Object.keys(sectionGroups)
          .sort()
          .forEach((sectionKey) => {
            const sectionSafeKey = `${safeKey}-${sectionKey.replace(/[^a-zA-Z0-9]/g, "")}`;

            // Section Header
            const sectionRow = document.createElement("tr");
            sectionRow.className = `table-secondary group-${safeKey} collapse show`; // Collapsible
            const sectionCell = document.createElement("td");
            sectionCell.colSpan = 8;
            sectionCell.style.paddingLeft = "30px";
            sectionCell.classList.add("fw-semibold");

            // Build section header using safe DOM construction
            const sectionDiv = document.createElement("div");
            sectionDiv.className = "d-flex align-items-center";
            sectionDiv.style.cursor = "pointer";
            sectionDiv.setAttribute("data-bs-toggle", "collapse");
            sectionDiv.setAttribute(
              "data-bs-target",
              `.section-${sectionSafeKey}`,
            );

            const sectionChevron = document.createElement("i");
            sectionChevron.className = "fas fa-chevron-down me-2";
            sectionDiv.appendChild(sectionChevron);

            const sectionStrong = document.createElement("strong");
            sectionStrong.className = "text-secondary";
            sectionStrong.textContent = sectionKey;
            sectionDiv.appendChild(sectionStrong);
            sectionCell.appendChild(sectionDiv);

            sectionRow.appendChild(sectionCell);
            tbody.appendChild(sectionRow);

            // CLO Rows
            sectionGroups[sectionKey].forEach((clo) => {
              const outcomeId = clo.id || clo.outcome_id || "";
              const tr = document.createElement("tr");
              tr.className = `clo-row group-${safeKey} section-${sectionSafeKey} collapse show`; // Collapsible
              tr.style.cursor = "pointer";
              tr.dataset.outcomeId = outcomeId;

              // Status
              const tdStatus = document.createElement("td");
              tdStatus.appendChild(getStatusBadge(clo.status));
              tr.appendChild(tdStatus);

              // Course (Redundant but requested)
              const tdCourse = document.createElement("td");
              tdCourse.textContent = clo.course_number || "N/A";
              tr.appendChild(tdCourse);

              // Section (Requested)
              const tdSection = document.createElement("td");
              tdSection.textContent = clo.section_number || "N/A";
              tr.appendChild(tdSection);

              // CLO #
              const tdCloNum = document.createElement("td");
              tdCloNum.textContent = clo.clo_number || "N/A";
              tr.appendChild(tdCloNum);

              // Description
              const tdDesc = document.createElement("td");
              tdDesc.textContent = truncateText(clo.description, 40);
              tdDesc.title = clo.description;
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

              // Actions (same as before)
              const tdActions = document.createElement("td");
              tdActions.className = "clo-actions";
              const btnGroup = document.createElement("div");
              btnGroup.className = "btn-group btn-group-sm";

              const actionBtns = [];
              if (clo.status === "awaiting_approval") {
                const approveBtn = document.createElement("button");
                approveBtn.type = "button";
                approveBtn.className = "btn btn-success text-white";
                approveBtn.title = "Approve Outcome";
                approveBtn.innerHTML = '<i class="fas fa-check"></i>';
                approveBtn.onclick = (e) => {
                  e.stopPropagation();
                  approveOutcome(clo.id || clo.outcome_id);
                };
                actionBtns.push(approveBtn);

                const reworkBtn = document.createElement("button");
                reworkBtn.type = "button";
                reworkBtn.className = "btn btn-warning text-dark";
                reworkBtn.title = "Request Rework";
                reworkBtn.innerHTML =
                  '<i class="fas fa-exclamation-triangle"></i>';
                reworkBtn.onclick = (e) => {
                  e.stopPropagation();
                  globalThis.pendingReworkOutcomeId =
                    clo.id || clo.outcome_id || null;
                  globalThis.showCLODetails(outcomeId);
                };
                actionBtns.push(reworkBtn);
              } else if (clo.status === "unassigned") {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "btn btn-primary text-white";
                btn.title = "Assign Instructor";
                btn.innerHTML = '<i class="fas fa-user-plus"></i>';
                btn.onclick = (e) => {
                  e.stopPropagation();
                  assignOutcome(clo.id || clo.outcome_id);
                };
                actionBtns.push(btn);
              } else if (
                ["in_progress", "approval_pending", "assigned"].includes(
                  clo.status,
                )
              ) {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "btn btn-info text-white";
                btn.title = "Send Reminder";
                btn.innerHTML = '<i class="fas fa-bell"></i>';
                btn.onclick = (e) => {
                  e.stopPropagation();
                  remindOutcome(outcomeId, clo.instructor_id, clo.course_id);
                };
                actionBtns.push(btn);
              }

              const viewBtn = document.createElement("button");
              viewBtn.type = "button";
              viewBtn.className = "btn btn-outline-secondary";
              viewBtn.dataset.outcomeId = clo.id || clo.outcome_id;
              viewBtn.title = "View Details";
              viewBtn.innerHTML = '<i class="fas fa-eye"></i>';
              viewBtn.onclick = (e) => {
                e.stopPropagation();
                globalThis.showCLODetails(outcomeId);
              };

              actionBtns.forEach((btn) => {
                btnGroup.appendChild(btn);
              });
              btnGroup.appendChild(viewBtn);
              tdActions.appendChild(btnGroup);
              tr.appendChild(tdActions);

              tbody.appendChild(tr);
            });
          });
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
      const cloDetailContainer = document.getElementById(
        "cloDetailContentMain",
      );
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
      const canReopen = ["approved", "never_coming_in"].includes(clo.status);
      const reopenBtn = document.getElementById("reopenBtn");
      if (reopenBtn) {
        reopenBtn.style.display = canReopen ? "inline-block" : "none";
        reopenBtn.onclick = () => reopenOutcome(clo.id);
      }

      const approveBtn = document.getElementById("approveBtn");
      if (approveBtn) {
        approveBtn.style.display = canApprove ? "inline-block" : "none";
        approveBtn.onclick = async () => {
          if (await approveOutcome(clo.id)) {
            bootstrap.Modal.getInstance(
              document.getElementById("cloDetailModal"),
            ).hide();
          }
        };
      }

      const requestReworkBtn = document.getElementById("requestReworkBtn");
      if (requestReworkBtn) {
        requestReworkBtn.style.display = canApprove ? "inline-block" : "none";
        requestReworkBtn.onclick = () => {
          globalThis.pendingReworkOutcomeId = clo.id || clo.outcome_id || null;
          globalThis.openReworkModal();
        };
      }

      const markNCIBtn = document.getElementById("markNCIBtn");
      if (markNCIBtn) {
        markNCIBtn.style.display = canMarkNCI ? "inline-block" : "none";
        markNCIBtn.onclick = () => markAsNCI(clo.id);
      }

      const modal = new bootstrap.Modal(cloDetailModal);
      modal.show();

      toggleReworkMode(false);
      if (
        globalThis.pendingReworkOutcomeId &&
        (clo.id || clo.outcome_id) === globalThis.pendingReworkOutcomeId
      ) {
        globalThis.openReworkModal();
        globalThis.pendingReworkOutcomeId = null;
      }
    } catch (error) {
      alert("Failed to load CLO details: " + error.message);
    }
  };

  /**
   * Activate rework mode inside the detail modal
   */
  globalThis.openReworkModal = function () {
    if (!globalThis.currentCLO) return;
    if (!cloReworkSection || !cloReworkForm) return;

    reworkFeedbackTextarea.value = "";
    reworkSendEmailCheckbox.checked = true;
    reworkAlert.classList.add("d-none");
    const descriptionEl = document.getElementById("reworkCloDescription");
    if (descriptionEl) {
      descriptionEl.textContent = `${globalThis.currentCLO.course_number} - CLO ${globalThis.currentCLO.clo_number}: ${globalThis.currentCLO.description}`;
    }

    enterReworkMode();
  };

  function toggleReworkMode(show) {
    if (cloReworkSection) {
      cloReworkSection.style.display = show ? "block" : "none";
    }
    if (cloDetailActionsStandard) {
      cloDetailActionsStandard.style.display = show ? "none" : "flex";
    }
    if (cloDetailActionsRework) {
      cloDetailActionsRework.style.display = show ? "flex" : "none";
    }
    globalThis.reworkMode = show;
  }

  function enterReworkMode() {
    toggleReworkMode(true);
    if (reworkFeedbackTextarea) {
      reworkFeedbackTextarea.focus();
    }
  }

  /**
   * Submit rework request
   */
  async function submitReworkRequest(event) {
    if (event && typeof event.preventDefault === "function") {
      event.preventDefault();
    }

    if (!globalThis.currentCLO) return;
    if (!reworkFeedbackTextarea) return;

    const comments = reworkFeedbackTextarea.value.trim();
    const sendEmail = reworkSendEmailCheckbox?.checked ?? true;

    if (!comments) {
      showReworkAlert("Please provide feedback comments.", "danger");
      return;
    }

    const outcomeId = globalThis.currentCLO.id;
    if (!outcomeId) {
      showReworkAlert("Error: CLO ID not found.", "danger");
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

      showReworkAlert(
        "Rework request sent successfully!" +
          (sendEmail ? " Email notification sent." : ""),
        "success",
      );

      toggleReworkMode(false);
      const modalInstance = bootstrap.Modal.getInstance(cloDetailModal);
      if (modalInstance) {
        modalInstance.hide();
      }

      await loadCLOs();
    } catch (error) {
      showReworkAlert("Failed to request rework: " + error.message, "danger");
    }
  }

  function showReworkAlert(message, variant = "info") {
    if (!reworkAlert) return;
    reworkAlert.textContent = message;
    reworkAlert.className = `alert alert-${variant}`;
    reworkAlert.classList.remove("d-none");
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
    // DOM interaction functions (for unit testing)
    approveOutcome,
    assignOutcome,
    loadInstructors,
    handleAssignSubmit,
    reopenOutcome,
    remindOutcome,
    submitReminder,
    // Note: sortCLOs and submitReworkRequest are inside DOMContentLoaded
    // and cannot be exported (they depend on DOM element references)
    // Expose internal state accessor for testing
    _getAllCLOs: () => allCLOs,
    _setAllCLOs: (clos) => {
      allCLOs = clos;
    },
  };
}
