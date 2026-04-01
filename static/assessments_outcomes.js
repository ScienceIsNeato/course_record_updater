(function () {
  "use strict";

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function getSuccessRateColorClass(percentage, isApproved) {
    if (isApproved || percentage >= 80) return "text-success";
    if (percentage >= 60) return "text-warning";
    return "text-danger";
  }

  function buildNoOutcomesHtml(courseNumber, courseTitle) {
    return `
      <div class="alert alert-info">
        No outcomes defined for ${courseNumber} - ${courseTitle}
      </div>
    `;
  }

  function buildCourseHeader(section, courseNumber, courseTitle) {
    if (!section) {
      return `${courseNumber} - ${courseTitle}`;
    }
    const termName = section.term_name || "Unknown Term";
    const sectionNumber = section.section_number || "001";
    return `${termName} - ${courseNumber} - Section ${sectionNumber}`;
  }

  function buildEnrollmentInfo(section) {
    return section?.enrollment
      ? `<span class="text-muted">${section.enrollment} students enrolled</span>`
      : "";
  }

  function buildOutcomeRow(outcome, index, section) {
    const studentsTook = outcome.students_took ?? "";
    const studentsPassed = outcome.students_passed ?? "";
    const assessmentTool = outcome.assessment_tool || "";
    const status = outcome.status || "assigned";
    const feedback = outcome.feedback_comments || "";
    const needsWork = status === "approval_pending" && feedback;
    const isApproved = status === "approved";
    const tookNum = parseInt(studentsTook, 10) || 0;
    const passedNum = parseInt(studentsPassed, 10) || 0;
    const percentage =
      tookNum > 0 ? Math.round((passedNum / tookNum) * 100) : 0;
    const rateColor = getSuccessRateColorClass(percentage, isApproved);
    const rowClass = isApproved
      ? "bg-success bg-opacity-10"
      : needsWork
        ? "bg-warning bg-opacity-10"
        : "";
    const inputDisabled = isApproved ? "disabled" : "";

    return `
      <div class="row g-2 py-2 align-items-center border-bottom ${rowClass}" data-outcome-id="${outcome.id}" data-course-outcome-id="${outcome.outcome_id}">
        <div class="col-md-1">
          <span class="fw-bold">${index + 1}</span>
          ${isApproved ? '<i class="fas fa-check-circle text-success ms-1" title="Approved"></i>' : ""}
          ${needsWork ? '<i class="fas fa-exclamation-triangle text-warning ms-1" title="Needs Rework"></i>' : ""}
        </div>
        <div class="col-md-4">
          <small class="text-wrap">${escapeHtml(outcome.description)}</small>
          ${needsWork ? `<div class="text-warning small mt-1"><i class="fas fa-comment"></i> ${escapeHtml(feedback)}</div>` : ""}
        </div>
        <div class="col-md-2">
          <input type="number" class="form-control form-control-sm clo-input"
                 data-field="students_took"
                 data-outcome-id="${outcome.id}"
                 data-enrollment="${section?.enrollment || 0}"
                 value="${studentsTook}"
                 min="0"
                 placeholder="0"
                 ${inputDisabled}>
        </div>
        <div class="col-md-2">
          <input type="number" class="form-control form-control-sm clo-input"
                 data-field="students_passed"
                 data-outcome-id="${outcome.id}"
                 value="${studentsPassed}"
                 min="0"
                 placeholder="0"
                 ${inputDisabled}>
        </div>
        <div class="col-md-2">
          <input type="text" class="form-control form-control-sm clo-input"
                 data-field="assessment_tool"
                 data-outcome-id="${outcome.id}"
                 value="${escapeHtml(assessmentTool)}"
                 maxlength="50"
                 placeholder="e.g., Lab 2"
                 ${inputDisabled}>
        </div>
        <div class="col-md-1 text-center">
          <span class="fw-bold ${rateColor}">${studentsTook ? percentage + "%" : "-"}</span>
        </div>
      </div>
    `;
  }

  function buildOutcomesHtml(outcomes, data, section) {
    const courseHeader = buildCourseHeader(
      section,
      data.course_number,
      data.course_title,
    );
    const enrollmentInfo = buildEnrollmentInfo(section);
    const rows = outcomes.map((outcome, index) =>
      buildOutcomeRow(outcome, index, section),
    );

    return `
      <div class="card border-0 shadow-sm mb-4">
        <div class="card-header bg-primary text-white py-3">
          <h4 class="mb-0"><i class="fas fa-graduation-cap"></i> ${courseHeader}</h4>
          ${enrollmentInfo ? `<small>${enrollmentInfo}</small>` : ""}
        </div>
        <div class="card-body">
          <p class="text-muted mb-3">Enter assessment data for each CLO. Changes save automatically.</p>
          <div class="row g-2 mb-2 fw-bold text-muted small">
            <div class="col-md-1">CLO</div>
            <div class="col-md-4">Description</div>
            <div class="col-md-2">Took</div>
            <div class="col-md-2">Passed</div>
            <div class="col-md-2">Tool</div>
            <div class="col-md-1">Rate</div>
          </div>
          <div class="outcomes-list">${rows.join("")}</div>
        </div>
      </div>
    `;
  }

  function bindOutcomeInputs(autoSaveCLO, updateRateDisplay) {
    document.querySelectorAll(".clo-input").forEach((input) => {
      input.addEventListener("blur", function () {
        autoSaveCLO(this);
      });
      input.addEventListener("input", function () {
        updateRateDisplay(this);
      });
    });
  }

  function updateSubmitButtonLabel(hasPreviousSubmission) {
    const submitBtn = document.getElementById("submitCourseBtn");
    if (!submitBtn) {
      return;
    }
    const label = hasPreviousSubmission
      ? "Re-Submit Assessments"
      : "Submit Assessments";
    submitBtn.innerHTML = `<i class="fas fa-upload"></i> ${label}`;
  }

  window.AssessmentOutcomes = {
    bindOutcomeInputs,
    buildNoOutcomesHtml,
    buildOutcomesHtml,
    updateSubmitButtonLabel,
  };
})();
