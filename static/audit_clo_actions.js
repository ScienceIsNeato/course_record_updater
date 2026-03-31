(function () {
  "use strict";

  let reminderContext = null;
  let currentAssignSectionId = null;

  function formatShortDate(dateString) {
    if (!dateString) return null;
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) {
      return null;
    }
    return date.toLocaleDateString();
  }

  function renderCLODetails(clo, deps) {
    const { formatDate, getStatusBadge } = deps;
    const container = document.createElement("div");
    const rows = [
      [
        "Course:",
        `${clo.course_number || "N/A"} - ${clo.course_title || "N/A"}`,
      ],
      ["Outcome Number:", clo.clo_number || "N/A"],
      ["Instructor:", clo.instructor_name || "N/A"],
      ["Instructor Email:", clo.instructor_email || "N/A"],
      ["Term:", clo.term_name || "—"],
      ["Assessment Tool:", clo.assessment_tool || "—"],
    ];

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

    appendDetailRows(container, rows);
    appendDescription(container, clo.description);
    appendAssessmentSummary(container, clo);
    appendOptionalTextBlock(container, "Narrative:", clo.narrative);
    appendOptionalTextBlock(
      container,
      "Admin Feedback:",
      clo.feedback_comments,
    );
    appendHistoryList(container, clo.history, formatDate);
    appendReviewerInfo(container, clo, formatDate);
    appendAttachmentPlaceholder(container);
    return container;
  }

  function appendDetailRows(container, rows) {
    for (let i = 0; i < rows.length; i += 2) {
      const row = document.createElement("div");
      row.className = "row mb-3";
      rows.slice(i, i + 2).forEach(([label, value]) => {
        const col = document.createElement("div");
        col.className = "col-md-6";
        const strong = document.createElement("strong");
        strong.textContent = label;
        col.appendChild(strong);
        col.appendChild(document.createTextNode(` ${value}`));
        row.appendChild(col);
      });
      container.appendChild(row);
    }
  }

  function appendDescription(container, description) {
    const descRow = document.createElement("div");
    descRow.className = "mb-3";
    const descStrong = document.createElement("strong");
    descStrong.textContent = "Description:";
    const descP = document.createElement("p");
    descP.textContent = description;
    descRow.appendChild(descStrong);
    descRow.appendChild(descP);
    container.appendChild(descRow);
  }

  function appendAttachmentPlaceholder(container) {
    const attachmentRow = document.createElement("div");
    attachmentRow.className = "mb-3";
    const attachmentStrong = document.createElement("strong");
    attachmentStrong.textContent = "Attachments:";
    const attachmentBtn = document.createElement("button");
    attachmentBtn.className = "btn btn-sm btn-outline-secondary";
    attachmentBtn.disabled = true;
    attachmentBtn.innerHTML =
      '<i class="fas fa-paperclip"></i> View Attachments (Coming Soon)';
    attachmentRow.appendChild(attachmentStrong);
    attachmentRow.appendChild(document.createElement("br"));
    attachmentRow.appendChild(attachmentBtn);
    container.appendChild(attachmentRow);
    container.appendChild(document.createElement("hr"));
  }

  function appendAssessmentSummary(container, clo) {
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
    [
      { value: studentsTook, label: "Students Took" },
      { value: studentsPassed, label: "Students Passed" },
      { value: `${percentage}%`, label: "Success Rate" },
    ].forEach((stat) => {
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
  }

  function appendOptionalTextBlock(container, label, text) {
    if (!text) return;
    const row = document.createElement("div");
    row.className = "mb-3";
    const strong = document.createElement("strong");
    strong.textContent = label;
    const p = document.createElement("p");
    p.className = "text-muted";
    p.textContent = text;
    row.appendChild(strong);
    row.appendChild(p);
    container.appendChild(row);
  }

  function appendHistoryList(container, history, formatDate) {
    if (!history || history.length === 0) return;
    const historyRow = document.createElement("div");
    historyRow.className = "mb-3";
    const historyStrong = document.createElement("strong");
    historyStrong.textContent = "History:";
    const historyList = document.createElement("ul");
    historyList.className = "list-unstyled text-muted small mt-2";
    history.forEach((entry) => {
      const li = document.createElement("li");
      li.className = "mb-1";
      const icon = document.createElement("i");
      icon.className = "fas fa-clock me-2";
      li.appendChild(icon);
      li.appendChild(
        document.createTextNode(
          `${entry.event} - ${formatDate(entry.occurred_at)}`,
        ),
      );
      historyList.appendChild(li);
    });
    historyRow.appendChild(historyStrong);
    historyRow.appendChild(historyList);
    container.appendChild(historyRow);
  }

  function appendReviewerInfo(container, clo, formatDate) {
    if (!clo.reviewed_by_name) return;
    const reviewerRow = document.createElement("div");
    reviewerRow.className = "mt-3 text-muted small";
    const em = document.createElement("em");
    em.textContent = `Reviewed by ${clo.reviewed_by_name} on ${formatDate(clo.reviewed_at)}`;
    reviewerRow.appendChild(em);
    container.appendChild(reviewerRow);
  }

  async function approveCLO(deps) {
    if (!globalThis.currentCLO) return;
    const outcomeId =
      globalThis.currentCLO.id || globalThis.currentCLO.outcome_id;
    if (!outcomeId) {
      alert("Error: Outcome ID not found");
      return;
    }
    await postOutcomeAction(
      `/api/outcomes/${outcomeId}/approve`,
      "Failed to approve Outcome",
      async () => {
        const modal = bootstrap.Modal.getInstance(
          document.getElementById("cloDetailModal"),
        );
        modal.hide();
        await globalThis.loadCLOs();
      },
    );
  }

  async function markAsNCI(deps) {
    if (!globalThis.currentCLO) return;
    const reason = prompt(
      `Mark this Outcome as "Never Coming In"?\n\n${globalThis.currentCLO.course_number} - Outcome ${globalThis.currentCLO.clo_number}\n\nOptional: Provide a reason (e.g., "Instructor left institution", "Non-responsive instructor"):`,
    );
    if (reason === null) return;
    const outcomeId =
      globalThis.currentCLO.id || globalThis.currentCLO.outcome_id;
    await postOutcomeAction(
      `/api/outcomes/${outcomeId}/mark-nci`,
      "Failed to mark Outcome as NCI",
      async () => {
        const modal = bootstrap.Modal.getInstance(
          document.getElementById("cloDetailModal"),
        );
        modal.hide();
        alert("Outcome marked as Never Coming In (NCI)");
        await globalThis.loadCLOs();
        await globalThis.updateStats();
      },
      { reason: reason.trim() || null },
    );
  }

  async function approveOutcome(outcomeId) {
    return simpleOutcomeAction(
      `/api/outcomes/${outcomeId}/approve`,
      "Failed to approve",
      async () => {
        await globalThis.loadCLOs();
        return true;
      },
      "Error approving outcome",
    );
  }

  async function reopenOutcome(outcomeId) {
    if (
      !confirm(
        "Are you sure you want to reopen this outcome? Status will be set to 'In Progress'.",
      )
    ) {
      return;
    }
    await simpleOutcomeAction(
      `/api/outcomes/${outcomeId}/reopen`,
      "Failed to reopen",
      async () => {
        const modalEl = document.getElementById("cloDetailModal");
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) {
          modal.hide();
        } else {
          modalEl.classList.remove("show");
          modalEl.style.display = "none";
          modalEl.setAttribute("aria-hidden", "true");
          document.body.classList.remove("modal-open");
          document.querySelector(".modal-backdrop")?.remove();
        }
        await globalThis.loadCLOs();
      },
      "Error reopening outcome",
    );
  }

  async function postOutcomeAction(url, errorPrefix, onSuccess, body) {
    try {
      const csrfToken = document.querySelector(
        'meta[name="csrf-token"]',
      )?.content;
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken,
        },
        ...(body ? { body: JSON.stringify(body) } : {}),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || errorPrefix);
      }
      await onSuccess();
    } catch (error) {
      alert(`${errorPrefix}: ${error.message}`);
    }
  }

  async function simpleOutcomeAction(
    url,
    errorPrefix,
    onSuccess,
    networkErrorPrefix,
  ) {
    try {
      const csrfToken = document.querySelector(
        'meta[name="csrf-token"]',
      )?.content;
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken,
        },
      });
      if (!res.ok) {
        const err = await res.json();
        alert(`${errorPrefix}: ${err.error || "Unknown error"}`);
        return false;
      }
      await onSuccess();
      return true;
    } catch (e) {
      alert(`${networkErrorPrefix || "Error"}: ${e.message}`);
      return false;
    }
  }

  async function assignOutcome(
    outcomeId,
    allCLOs,
    loadInstructors,
    handleAssignSubmit,
  ) {
    const clo = allCLOs.find(
      (c) => c.id === outcomeId || c.outcome_id === outcomeId,
    );
    if (!clo) return;
    const form = document.getElementById("assignInstructorForm");
    if (form) form.onsubmit = handleAssignSubmit;
    if (!clo.section_id) {
      alert("Cannot identify section for assignment. Please contact support.");
      return;
    }
    currentAssignSectionId = clo.section_id;
    const modal = bootstrap.Modal.getOrCreateInstance(
      document.getElementById("assignInstructorModal"),
    );
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
      if (!res.ok) {
        const json = await res.json();
        alert("Failed to assign: " + (json.error || "Unknown"));
        return;
      }
      bootstrap.Modal.getInstance(
        document.getElementById("assignInstructorModal"),
      ).hide();
      await globalThis.loadCLOs();
      alert("Instructor assigned successfully.");
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
    if (submitBtn) submitBtn.disabled = true;

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
        alertBox.textContent =
          result.message || "Invitation sent successfully!";
      }
      const modal = bootstrap.Modal.getInstance(
        document.getElementById("inviteInstructorModal"),
      );
      if (modal) modal.hide();
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
      if (submitBtn) submitBtn.disabled = false;
      if (typeof globalThis.loadCLOs === "function") {
        await globalThis.loadCLOs();
        document.dispatchEvent(new CustomEvent("faculty-invited"));
      }
    }
  }

  async function remindOutcome(outcomeId, instructorId, courseId, allCLOs) {
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
    await populateReminderModal(clo, instructorId);
    bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  async function populateReminderModal(clo, instructorId) {
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
    setText(
      "reminderCloDescription",
      `${courseNumber} • ${sectionLabel} • ${cloLabel}`,
    );
    setText("reminderCourseDescription", courseDisplay);

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
      console.warn("Failed to load instructor details:", error);
    }

    setText(
      "reminderInstructorEmail",
      instructorEmail || "Instructor email unavailable",
    );
    if (reminderContext.sectionId) {
      dueDateText = await fetchReminderDueDate(reminderContext.sectionId);
    }
    const reminderMessage = document.getElementById("reminderMessage");
    if (reminderMessage) {
      const dueLine = dueDateText
        ? `\nSubmission due date: ${dueDateText}`
        : "";
      reminderMessage.value =
        `Dear ${instructorName},\n\n` +
        "This is a friendly reminder to submit your assessment results for " +
        `${termLabel}${courseNumber} (${sectionLabel}) ${cloLabel}.` +
        `${dueLine}\n\nThank you.`;
    }
  }

  async function fetchReminderDueDate(sectionId) {
    try {
      const sectionResponse = await fetch(`/api/sections/${sectionId}`);
      if (!sectionResponse.ok) return null;
      const sectionData = await sectionResponse.json();
      return formatShortDate(sectionData.section?.assessment_due_date);
    } catch (error) {
      console.warn("Failed to load section due date:", error);
      return null;
    }
  }

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = text;
    }
  }

  async function submitReminder(event) {
    if (event?.preventDefault) {
      event.preventDefault();
    }
    if (!reminderContext) {
      alert("Reminder context is missing. Please try again.");
      return;
    }
    const message =
      document.getElementById("reminderMessage")?.value?.trim() || "";
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
      if (!res.ok) {
        const err = await res.json();
        alert("Failed to send reminder: " + (err.error || "Unknown error"));
        return;
      }
      const modal = bootstrap.Modal.getInstance(
        document.getElementById("sendReminderModal"),
      );
      if (modal) modal.hide();
      alert("Reminder sent successfully.");
    } catch (e) {
      alert("Error sending reminder: " + e.message);
    }
  }

  const exportsObj = {
    approveCLO,
    approveOutcome,
    assignOutcome,
    handleAssignSubmit,
    handleInviteInstructorSubmit,
    loadInstructors,
    markAsNCI,
    remindOutcome,
    renderCLODetails,
    reopenOutcome,
    submitReminder,
  };
  if (typeof globalThis !== "undefined") {
    globalThis.AuditCloActions = exportsObj;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = exportsObj;
  }
})();
