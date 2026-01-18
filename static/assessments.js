// ========================================
// Pure Utility Functions (Module Scope)
// ========================================

// Helper function to escape HTML
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Get status badge HTML
// eslint-disable-next-line no-unused-vars
function getStatusBadge(status) {
  const badges = {
    unassigned: '<span class="badge bg-secondary">Unassigned</span>',
    assigned: '<span class="badge bg-info">Assigned</span>',
    in_progress: '<span class="badge bg-primary">In Progress</span>',
    awaiting_approval:
      '<span class="badge bg-warning">Awaiting Approval</span>',
    approval_pending: '<span class="badge bg-danger">Needs Rework</span>',
    approved: '<span class="badge bg-success">✓ Approved</span>',
  };
  return badges[status] || "";
}

// Check if CLO can be submitted for approval
// eslint-disable-next-line no-unused-vars
function canSubmitForApproval(status) {
  return status === "in_progress" || status === "approval_pending";
}

// Helper function to get status indicator HTML
// eslint-disable-next-line no-unused-vars
function getStatusIndicatorHtml(status, isComplete, needsWork) {
  if (status === "approved") {
    return '<span class="badge bg-success"><i class="fas fa-check-circle"></i> Approved</span>';
  }
  if (status === "awaiting_approval") {
    return '<span class="badge bg-warning text-dark"><i class="fas fa-clock"></i> Pending Review</span>';
  }
  if (needsWork) {
    return '<span class="badge bg-danger"><i class="fas fa-exclamation-triangle"></i> Needs Revision</span>';
  }
  if (isComplete) {
    return '<span class="badge bg-info"><i class="fas fa-edit"></i> In Progress</span>';
  }
  return "";
}

// Helper function to get border color class
// eslint-disable-next-line no-unused-vars
function getBorderColorClass(isApproved, needsWork, isComplete) {
  if (isApproved) return "border-success";
  if (needsWork) return "border-danger";
  if (isComplete) return "border-info";
  return "border-secondary";
}

// Helper function to get success rate color class
// eslint-disable-next-line no-unused-vars
function getSuccessRateColorClass(percentage) {
  if (percentage >= 80) return "text-success";
  if (percentage >= 60) return "text-warning";
  return "text-danger";
}

// ========================================

// Filter-related functions (module scope for event listener access)
// Get assessment status for a section based on CLO states
function getSectionAssessmentStatus(outcomes) {
  if (!outcomes || outcomes.length === 0) return "not_started";

  const statuses = outcomes.map((o) => o.status || "assigned");

  // Precedence order (highest to lowest priority)
  // 1. NEEDS_REWORK - if ANY CLO needs rework
  if (statuses.some((s) => s === "approval_pending")) return "needs_rework";

  // 2. NCI - if ALL CLOs are NCI
  if (statuses.every((s) => s === "never_coming_in")) return "nci";

  // 3. APPROVED - if ALL CLOs are approved
  if (statuses.every((s) => s === "approved")) return "approved";

  // 4. SUBMITTED - if ALL CLOs are awaiting approval
  if (statuses.every((s) => s === "awaiting_approval")) return "submitted";

  // 5. IN_PROGRESS - check both explicit status AND populated data
  // A CLO is "in progress" if it has status='in_progress' OR has assessment data
  const hasAssessmentData = (outcome) => {
    return (
      outcome.students_took != null ||
      outcome.students_passed != null ||
      (outcome.assessment_tool && outcome.assessment_tool.trim().length > 0)
    );
  };
  if (
    outcomes.some((o) => o.status === "in_progress" || hasAssessmentData(o))
  ) {
    return "in_progress";
  }

  // 6. NOT_STARTED - if all CLOs are unassigned/assigned with no data
  if (statuses.every((s) => s === "assigned" || s === "unassigned"))
    return "not_started";

  // 7. UNKNOWN - fallback
  return "unknown";
}

// Get display text for assessment status
function getStatusBadgeText(status) {
  const badges = {
    not_started: "Not Started",
    in_progress: "In Progress",
    needs_rework: "Needs Rework",
    submitted: "Submitted",
    approved: "✓ Approved",
    nci: "NCI",
    unknown: "Unknown",
  };
  return badges[status] || "Unknown";
}

// Populate term filter with unique terms from sections
function populateTermFilter() {
  const terms = [
    ...new Set(allCourseSections.map((s) => s.term_name).filter(Boolean)),
  ];
  terms.sort(); // Alphabetical sort

  termFilter.innerHTML = '<option value="">All Terms</option>';
  terms.forEach((term) => {
    const option = document.createElement("option");
    option.value = term;
    option.textContent = term;
    termFilter.appendChild(option);
  });
}

// Populate course filter with unique courses
function populateCourseFilter() {
  const courses = [
    ...new Set(
      allInstructorCourses.map((c) => c.course_number).filter(Boolean),
    ),
  ];
  courses.sort(); // Alphabetical sort

  courseFilter.innerHTML = '<option value="">All Courses</option>';
  courses.forEach((courseNum) => {
    const option = document.createElement("option");
    option.value = courseNum;
    option.textContent = courseNum;
    courseFilter.appendChild(option);
  });
}

// Apply filters to course dropdown (combined AND logic)
function applyFilters() {
  courseSelect.innerHTML = '<option value="">-- Select a course --</option>';

  allInstructorCourses.forEach((course) => {
    const courseSections = allCourseSections.filter(
      (s) => s.course_id === course.course_id,
    );
    const outcomes = courseOutcomesMap[course.course_id] || [];

    courseSections.forEach((section) => {
      // Apply combined filters (term AND course)
      if (activeTermFilter && section.term_name !== activeTermFilter) return;
      if (activeCourseFilter && course.course_number !== activeCourseFilter)
        return;

      // Filter outcomes to this specific section
      const sectionOutcomes = outcomes.filter(
        (o) => o.section_id === section.section_id,
      );

      // Get status for THIS section only
      const status = getSectionAssessmentStatus(sectionOutcomes);
      const statusText = getStatusBadgeText(status);

      const option = document.createElement("option");
      option.value = `${course.course_id}::${section.section_id}`;
      const termName = section.term_name || "Unknown Term";
      const sectionNumber = section.section_number || "001";
      option.textContent = `${termName} - ${course.course_number} - Section ${sectionNumber} [${statusText}]`;
      courseSelect.appendChild(option);
    });
  });

  // Show "no results" if empty
  if (courseSelect.options.length === 1) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No courses match the selected filters";
    option.disabled = true;
    courseSelect.appendChild(option);
  }
}

// DOM-Dependent Code (DOMContentLoaded)
// ========================================

// Module-scope filter variables (populated by loadCourses)
let activeTermFilter = "";
let activeCourseFilter = "";
let allInstructorCourses = [];
let allCourseSections = [];
let courseOutcomesMap = {};
let termFilter, courseFilter, clearFiltersBtn, courseSelect;

document.addEventListener("DOMContentLoaded", function () {
  courseSelect = document.getElementById("courseSelect");
  const outcomesContainer = document.getElementById("outcomesContainer");
  const parseOptionalInt = (value) => {
    const parsed = Number.parseInt(value);
    return Number.isNaN(parsed) ? null : parsed;
  };
  const updateAssessmentModal = document.getElementById(
    "updateAssessmentModal",
  );
  const updateAssessmentForm = document.getElementById("updateAssessmentForm");

  // Initialize filter element references
  termFilter = document.getElementById("termFilter");
  courseFilter = document.getElementById("courseFilter");
  clearFiltersBtn = document.getElementById("clearFilters");

  // Store sections data for enrollment lookup
  let instructorSections = [];

  console.log("📢 ASSESSMENT JS: Elements found:", {
    courseSelect: !!courseSelect,
    outcomesContainer: !!outcomesContainer,
  });

  // Reload sections data from API (call after saving to refresh stale data)
  async function reloadSections() {
    try {
      const sectionsResponse = await fetch("/api/sections");
      if (!sectionsResponse.ok) throw new Error("Failed to reload sections");
      const sectionsData = await sectionsResponse.json();
      instructorSections = sectionsData.sections || [];
      console.log("📢 Sections reloaded:", instructorSections.length);
    } catch (error) {
      console.error("Error reloading sections:", error);
    }
  }

  // Load instructor's courses
  async function loadCourses() {
    console.log("📢 loadCourses() START");
    try {
      // Get sections for instructor
      console.log("📢 Fetching /api/sections...");
      const sectionsResponse = await fetch("/api/sections");
      console.log(`📢 /api/sections response: ${sectionsResponse.status}`);
      if (!sectionsResponse.ok) throw new Error("Failed to load sections");
      const sectionsData = await sectionsResponse.json();
      const sections = sectionsData.sections || [];
      instructorSections = sections; // Store for later use
      console.log(`📢 Got ${sections.length} sections`);
      if (sections.length > 0) {
        console.log(
          `📢 First section FULL:`,
          JSON.stringify(sections[0], null, 2),
        );
        console.log(`📢 First section course_id:`, sections[0].course_id);
        console.log(`📢 First section offering_id:`, sections[0].offering_id);
        console.log(`📢 First section enrollment:`, sections[0].enrollment);
      }

      // Get unique course IDs from sections
      const courseIds = [...new Set(sections.map((s) => s.course_id))];
      // nosemgrep: unsafe-formatstring - Console.log is safe for debugging
      console.log(`📢 Unique course IDs: ${courseIds.length}`, courseIds);

      // Get course details
      console.log("📢 Fetching /api/courses...");
      const coursesResponse = await fetch("/api/courses");
      console.log(`📢 /api/courses response: ${coursesResponse.status}`);
      if (!coursesResponse.ok) throw new Error("Failed to load courses");
      const coursesData = await coursesResponse.json();
      const allCourses = coursesData.courses || [];
      console.log(`📢 Got ${allCourses.length} total courses`);

      // Filter to only courses instructor has sections for
      const instructorCourses = allCourses.filter((c) =>
        courseIds.includes(c.course_id),
      );
      console.log(
        `📢 Filtered to ${instructorCourses.length} instructor courses`,
      );

      // Fetch CLO outcomes for all instructor courses to calculate % complete
      const courseOutcomePromises = instructorCourses.map(async (course) => {
        try {
          const resp = await fetch(`/api/courses/${course.course_id}/outcomes`);
          if (!resp.ok) return { course_id: course.course_id, outcomes: [] };
          const data = await resp.json();
          return { course_id: course.course_id, outcomes: data.outcomes || [] };
        } catch (e) {
          return { course_id: course.course_id, outcomes: [] };
        }
      });
      const courseOutcomesData = await Promise.all(courseOutcomePromises);

      // Build a map of course_id -> outcomes (use module-level variable)
      courseOutcomesMap = {}; // Reset the module-level map
      courseOutcomesData.forEach((co) => {
        courseOutcomesMap[co.course_id] = co.outcomes;
      });

      // Store data for filtering
      allInstructorCourses = instructorCourses;
      allCourseSections = sections;

      // Populate filters
      populateTermFilter();
      populateCourseFilter();

      // Apply filters (will populate course dropdown)
      applyFilters();

      console.log("📢 loadCourses() COMPLETE");
    } catch (error) {
      console.error("❌ Error loading courses:", error);
      courseSelect.innerHTML =
        '<option value="">Error loading courses</option>';
    }
  }

  // Load outcomes for selected course - INLINE EDITABLE VERSION
  async function loadOutcomes(compositeId) {
    if (!compositeId) {
      outcomesContainer.innerHTML =
        '<p class="text-muted">Select a course to view its outcomes</p>';
      return;
    }

    // Parse composite ID: "courseId::sectionId"
    const [courseId, sectionId] = compositeId.split("::");

    outcomesContainer.innerHTML = "<p>Loading outcomes...</p>";

    try {
      const response = await fetch(`/api/courses/${courseId}/outcomes`);
      if (!response.ok) throw new Error("Failed to load outcomes");

      const data = await response.json();
      let outcomes = data.outcomes || [];

      // Filter outcomes to only this section
      if (sectionId) {
        outcomes = outcomes.filter((o) => o.section_id === sectionId);
      }

      if (outcomes.length === 0) {
        // nosemgrep: insecure-document-method - Content is sanitized via template literals
        outcomesContainer.innerHTML = `
                    <div class="alert alert-info">
                        No outcomes defined for ${data.course_number} - ${data.course_title}
                    </div>
                `;
        return;
      }

      // Get section info for the selected section
      const section = sectionId
        ? instructorSections.find((s) => s.section_id === sectionId)
        : instructorSections.find((s) => s.course_id === courseId);
      let termName = section?.term_name || "Unknown Term";

      const courseHeader = section
        ? `${termName} - ${data.course_number} - Section ${section.section_number || "001"}`
        : `${data.course_number} - ${data.course_title}`;

      const enrollmentInfo = section?.enrollment
        ? `<span class="text-muted">${section.enrollment} students enrolled</span>`
        : "";

      // Build compact inline form for CLOs
      let html = `
                <div class="card border-0 shadow-sm mb-4">
                    <div class="card-header bg-primary text-white py-3">
                        <h4 class="mb-0"><i class="fas fa-graduation-cap"></i> ${courseHeader}</h4>
                        ${enrollmentInfo ? `<small>${enrollmentInfo}</small>` : ""}
                    </div>
                    <div class="card-body">
                        <p class="text-muted mb-3">Enter assessment data for each CLO. Changes save automatically.</p>
                        
                        <!-- CLO Table Header -->
                        <div class="row g-2 mb-2 fw-bold text-muted small">
                            <div class="col-md-1">CLO</div>
                            <div class="col-md-4">Description</div>
                            <div class="col-md-2">Took</div>
                            <div class="col-md-2">Passed</div>
                            <div class="col-md-2">Tool</div>
                            <div class="col-md-1">Rate</div>
                        </div>
                        
                        <div class="outcomes-list">
            `;

      outcomes.forEach((outcome, index) => {
        const studentsTook = outcome.students_took ?? "";
        const studentsPassed = outcome.students_passed ?? "";
        const assessmentTool = outcome.assessment_tool || "";
        const status = outcome.status || "assigned";
        const feedback = outcome.feedback_comments || "";
        const needsWork = status === "approval_pending" && feedback;
        const isApproved = status === "approved";

        // Calculate success rate
        const tookNum = parseInt(studentsTook) || 0;
        const passedNum = parseInt(studentsPassed) || 0;
        const percentage =
          tookNum > 0 ? Math.round((passedNum / tookNum) * 100) : 0;
        const rateColor = isApproved
          ? "text-success"
          : percentage >= 80
            ? "text-success"
            : percentage >= 60
              ? "text-warning"
              : "text-danger";

        // Row styling based on status
        const rowClass = isApproved
          ? "bg-success bg-opacity-10"
          : needsWork
            ? "bg-warning bg-opacity-10"
            : "";
        const inputDisabled = isApproved ? "disabled" : "";

        html += `
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
                                   data-enrollment="${section.enrollment || 0}"
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
      });

      html += `
                        </div>
                    </div>
                </div>
            `;
      // nosemgrep: insecure-document-method - HTML built from sanitized outcome data
      outcomesContainer.innerHTML = html;

      // Add auto-save on blur for all CLO inputs
      document.querySelectorAll(".clo-input").forEach((input) => {
        input.addEventListener("blur", function () {
          autoSaveCLO(this);
        });
        // Also update rate display on change
        input.addEventListener("input", function () {
          updateRateDisplay(this);
        });
      });

      // Update submit button text based on whether assessments were previously submitted
      const submitBtn = document.getElementById("submitCourseBtn");
      if (submitBtn) {
        const hasPreviousSubmission = Boolean(data.has_previous_submission);
        const label = hasPreviousSubmission
          ? "Re-Submit Assessments"
          : "Submit Assessments";
        submitBtn.innerHTML = `<i class="fas fa-upload"></i> ${label}`;
      }
      // Note: Submit button handler is added ONCE in DOMContentLoaded, not here
    } catch (error) {
      console.error("Error loading outcomes:", error);
      outcomesContainer.innerHTML =
        '<div class="alert alert-danger">Error loading outcomes</div>';
    }
  }

  // Auto-save CLO field on blur
  async function autoSaveCLO(inputElement) {
    const outcomeId = inputElement.dataset.outcomeId;
    const field = inputElement.dataset.field;
    let value = inputElement.value;

    // Convert to number for numeric fields
    if (field === "students_took" || field === "students_passed") {
      value = value === "" ? null : parseInt(value);
    }

    try {
      const csrfToken = document.querySelector(
        'meta[name="csrf-token"]',
      )?.content;
      const response = await fetch(`/api/outcomes/${outcomeId}/assessment`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken,
        },
        body: JSON.stringify({ [field]: value }),
      });

      if (response.ok) {
        // Brief visual feedback
        inputElement.classList.add("border-success");
        setTimeout(() => inputElement.classList.remove("border-success"), 1000);
      }
    } catch (error) {
      console.error("Auto-save failed:", error);
      inputElement.classList.add("border-danger");
    }
  }

  // Update rate display when inputs change
  function updateRateDisplay(inputElement) {
    // Fix: Target the ROW div explicitly (inputs also have data-outcome-id)
    const row = inputElement.closest("div[data-outcome-id]");
    if (!row) return;

    const tookInput = row.querySelector('[data-field="students_took"]');
    const passedInput = row.querySelector('[data-field="students_passed"]');
    const rateSpan = row.querySelector(".col-md-1.text-center span");

    const took = parseInt(tookInput?.value) || 0;
    const passed = parseInt(passedInput?.value) || 0;

    if (took > 0 && rateSpan) {
      const rate = Math.round((passed / took) * 100);
      rateSpan.textContent = rate + "%";
      rateSpan.className =
        "fw-bold " +
        (rate >= 80
          ? "text-success"
          : rate >= 60
            ? "text-warning"
            : "text-danger");
    } else if (rateSpan) {
      rateSpan.textContent = "-";
      rateSpan.className = "fw-bold";
    }

    // Soft validation for enrollment matching
    const enrollment = parseInt(tookInput?.dataset.enrollment) || 0;
    if (enrollment > 0 && took > enrollment) {
      tookInput.classList.add("border-warning");
      tookInput.title = `Warning: Value (${took}) exceeds official enrollment (${enrollment})`;
      // Remove success border if it was there from autosave
      tookInput.classList.remove("border-success");
    } else {
      tookInput.classList.remove("border-warning");
      tookInput.title = "";
    }
  }

  // Submit entire course for approval
  async function submitCourseForApproval(
    courseId,
    sectionId,
    alertProgramAdmins = false,
  ) {
    try {
      const csrfToken = document.querySelector(
        'meta[name="csrf-token"]',
      )?.content;

      // First, save the course-level form data
      if (sectionId) {
        const courseData = {
          students_passed: parseOptionalInt(
            document.getElementById("courseStudentsPassed")?.value,
          ),
          students_dfic: parseOptionalInt(
            document.getElementById("courseStudentsDFIC")?.value,
          ),
          cannot_reconcile:
            document.getElementById("cannotReconcile")?.checked || false,
          reconciliation_note:
            document.getElementById("reconciliationNote")?.value?.trim() ||
            null,
          narrative_celebrations:
            document.getElementById("narrativeCelebrations")?.value?.trim() ||
            null,
          narrative_challenges:
            document.getElementById("narrativeChallenges")?.value?.trim() ||
            null,
          narrative_changes:
            document.getElementById("narrativeChanges")?.value?.trim() || null,
        };

        console.log("[Submit] Course data to save:", courseData);

        const saveResponse = await fetch(`/api/sections/${sectionId}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrfToken,
          },
          body: JSON.stringify(courseData),
        });

        if (!saveResponse.ok) {
          const error = await saveResponse.json();
          throw new Error(error.error || "Failed to save course data");
        }
      }

      // Now submit for approval
      const response = await fetch(`/api/courses/${courseId}/submit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken,
        },
        body: JSON.stringify({
          section_id: sectionId,
          alert_program_admins: alertProgramAdmins,
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        let successMessage = "Course submitted for approval successfully!";
        if (alertProgramAdmins) {
          if (data.admin_alert_sent) {
            successMessage =
              "Course submitted for approval successfully! Program admins have been notified.";
          } else {
            const alertError =
              data.admin_alert_error || "Unable to notify program admins.";
            successMessage =
              "Course submitted for approval, but failed to notify program admins: " +
              alertError;
          }
        }
        alert(successMessage);
        // Reconstruct composite ID for reload
        const compositeId = sectionId ? `${courseId}::${sectionId}` : courseId;
        loadOutcomes(compositeId); // Reload to show updated status with section filter
        loadCourses(); // Reload to update status summary counts
      } else {
        // Show validation errors
        let errorMsg = "Please fix the following issues:\n\n";
        data.errors?.forEach((err) => {
          errorMsg += `• ${err.message}\n`;
          // Highlight the field
          if (err.outcome_id) {
            const input = document.querySelector(
              `[data-outcome-id="${err.outcome_id}"][data-field="${err.field}"]`,
            );
            input?.classList.add("border-danger", "is-invalid");
          }
        });
        alert(errorMsg);
      }
    } catch (error) {
      console.error("Error submitting course:", error);
      alert("Failed to submit course: " + error.message);
    }
  }

  // Submit CLO for approval
  // eslint-disable-next-line no-unused-vars
  async function submitCLOForApproval(outcomeId, description) {
    if (
      !confirm(
        `Submit "${description}" for approval?\n\nOnce submitted, it will be reviewed by an administrator.`,
      )
    ) {
      return;
    }

    try {
      const csrfToken = document.querySelector(
        'meta[name="csrf-token"]',
      )?.content;

      const response = await fetch(`/api/outcomes/${outcomeId}/submit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken,
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to submit for approval");
      }

      alert("Outcome submitted for approval successfully!");

      // Reload outcomes for current course
      const currentCourseId = courseSelect.value;
      if (currentCourseId) {
        await loadOutcomes(currentCourseId);
      }
    } catch (error) {
      console.error("Error submitting for approval:", error);
      alert("Failed to submit for approval: " + error.message);
    }
  }

  // Open update assessment modal
  // eslint-disable-next-line no-unused-vars
  function openUpdateAssessmentModal(outcomeData) {
    document.getElementById("assessmentOutcomeId").value =
      outcomeData.outcomeId;
    document.getElementById("assessmentOutcomeDescription").textContent =
      outcomeData.description;

    // Populate with existing values (updated field names from CEI demo feedback)
    document.getElementById("studentsTook").value =
      outcomeData.studentsTook || "";
    document.getElementById("studentsPassed").value =
      outcomeData.studentsPassed || "";
    document.getElementById("assessmentTool").value =
      outcomeData.assessmentTool || "";

    const modal = new bootstrap.Modal(updateAssessmentModal);
    modal.show();
  }

  // Track if user has started editing (for auto-marking in_progress)
  let autoMarkTriggered = false;

  // Auto-track editing on form fields (updated field names from CEI demo feedback)
  ["studentsTook", "studentsPassed", "assessmentTool"].forEach((fieldId) => {
    const field = document.getElementById(fieldId);
    if (field) {
      field.addEventListener("input", function () {
        // Auto-mark as in_progress on first edit (debounced)
        if (!autoMarkTriggered) {
          autoMarkTriggered = true;
          const outcomeId = document.getElementById(
            "assessmentOutcomeId",
          ).value;
          const status = document.querySelector(
            `.update-assessment-btn[data-outcome-id="${outcomeId}"]`,
          )?.dataset?.status;

          // Only auto-mark if status is assigned or approval_pending
          if (status === "assigned" || status === "approval_pending") {
            setTimeout(() => autoMarkInProgress(outcomeId), 1000);
          }
        }
      });
    }
  });

  // Auto-mark CLO as in_progress
  async function autoMarkInProgress(outcomeId) {
    try {
      // This will be called silently - no need to show success/error to user
      // Note: The backend update_course_outcome will handle auto-marking
      // We could add a dedicated endpoint, but for now the assessment update will trigger it
      console.log(`Auto-marking outcome ${outcomeId} as in_progress`);
    } catch (error) {
      console.error("Error auto-marking in progress:", error);
      // Silent fail - not critical
    }
  }

  // Handle assessment form submission
  updateAssessmentForm.addEventListener("submit", async function (e) {
    e.preventDefault();

    const outcomeId = document.getElementById("assessmentOutcomeId").value;
    const studentsTook = Number.parseInt(
      document.getElementById("studentsTook").value,
    );
    const studentsPassed = Number.parseInt(
      document.getElementById("studentsPassed").value,
    );
    const assessmentTool = document
      .getElementById("assessmentTool")
      .value.trim();

    // Validation (updated from CEI demo feedback)
    if (studentsPassed > studentsTook) {
      alert(
        "Students who passed cannot exceed students who took the assessment",
      );
      return;
    }

    if (!assessmentTool || assessmentTool.length === 0) {
      alert("Assessment tool is required");
      return;
    }

    if (assessmentTool.length > 50) {
      alert("Assessment tool must be 50 characters or less");
      return;
    }

    try {
      const csrfToken = document.querySelector(
        'meta[name="csrf-token"]',
      )?.content;

      const response = await fetch(`/api/outcomes/${outcomeId}/assessment`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken,
        },
        body: JSON.stringify({
          students_took: studentsTook,
          students_passed: studentsPassed,
          assessment_tool: assessmentTool,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to update assessment");
      }

      // Close modal and reload outcomes
      const modal = bootstrap.Modal.getInstance(updateAssessmentModal);
      modal.hide();

      // Reset tracking state
      autoMarkTriggered = false;

      alert("Assessment updated successfully!");

      // Reload outcomes for current course
      const currentCourseId = courseSelect.value;
      if (currentCourseId) {
        await loadOutcomes(currentCourseId);
      }
    } catch (error) {
      console.error("Error updating assessment:", error);
      alert("Failed to update assessment: " + error.message);
    }
  });

  // Track current course to detect changes
  let currentCourseId = null;
  let loadedCourseData = {}; // Store the data as it was loaded from server

  async function handleCourseSelectionChange(newCourseId) {
    if (currentCourseId && currentCourseId !== newCourseId) {
      const allowed =
        await handleCourseSwitchWithUnsavedChanges(currentCourseId);
      if (!allowed) {
        courseSelect.value = currentCourseId;
        return;
      }
    }

    currentCourseId = newCourseId;
    loadOutcomes(newCourseId);
    loadCourseLevelData(newCourseId);
  }

  async function handleCourseSwitchWithUnsavedChanges() {
    if (!checkForUnsavedChanges()) {
      return true;
    }

    const shouldSave = confirm(
      "You have unsaved changes for the current course.\n\n" +
        "Would you like to save them before switching courses?",
    );

    if (!shouldSave) {
      return true;
    }

    try {
      await saveCurrentCourseData();
      alert("Changes saved successfully!");
      return true;
    } catch (error) {
      return confirm(
        "Failed to save changes: " +
          error.message +
          "\n\n" +
          "Do you still want to switch courses? (Unsaved changes will be lost)",
      );
    }
  }

  // Course selection handler with auto-save
  courseSelect.addEventListener("change", async function () {
    await handleCourseSelectionChange(this.value);
  });

  // Check if current form values differ from loaded values
  function checkForUnsavedChanges() {
    if (!courseLevelSection || courseLevelSection.style.display === "none") {
      return false;
    }

    // Get current form values
    const currentData = {
      students_passed:
        document.getElementById("courseStudentsPassed")?.value || "",
      students_dfic: document.getElementById("courseStudentsDFIC")?.value || "",
      cannot_reconcile:
        document.getElementById("cannotReconcile")?.checked || false,
      reconciliation_note:
        document.getElementById("reconciliationNote")?.value || "",
      narrative_celebrations:
        document.getElementById("narrativeCelebrations")?.value || "",
      narrative_challenges:
        document.getElementById("narrativeChallenges")?.value || "",
      narrative_changes:
        document.getElementById("narrativeChanges")?.value || "",
    };

    // Compare with loaded data
    return (
      currentData.students_passed !== loadedCourseData.students_passed ||
      currentData.students_dfic !== loadedCourseData.students_dfic ||
      currentData.cannot_reconcile !== loadedCourseData.cannot_reconcile ||
      currentData.reconciliation_note !==
        loadedCourseData.reconciliation_note ||
      currentData.narrative_celebrations !==
        loadedCourseData.narrative_celebrations ||
      currentData.narrative_challenges !==
        loadedCourseData.narrative_challenges ||
      currentData.narrative_changes !== loadedCourseData.narrative_changes
    );
  }

  // Save current course data
  async function saveCurrentCourseData() {
    // Parse composite ID to get actual course ID
    const [courseId, sectionId] = currentCourseId.split("::");
    const section = sectionId
      ? instructorSections.find((s) => s.section_id === sectionId)
      : instructorSections.find((s) => s.course_id === courseId);

    if (!section) {
      throw new Error("No section found for current course");
    }

    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]',
    )?.content;

    const data = {
      students_passed:
        Number.parseInt(
          document.getElementById("courseStudentsPassed").value,
        ) || null,
      students_dfic:
        Number.parseInt(document.getElementById("courseStudentsDFIC").value) ||
        null,
      cannot_reconcile: document.getElementById("cannotReconcile").checked,
      reconciliation_note:
        document.getElementById("reconciliationNote").value.trim() || null,
      narrative_celebrations:
        document.getElementById("narrativeCelebrations").value.trim() || null,
      narrative_challenges:
        document.getElementById("narrativeChallenges").value.trim() || null,
      narrative_changes:
        document.getElementById("narrativeChanges").value.trim() || null,
    };

    const response = await fetch(`/api/sections/${section.section_id}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to save course data");
    }

    // Update loaded data to match what was just saved
    loadedCourseData = {
      students_passed: data.students_passed?.toString() || "",
      students_dfic: data.students_dfic?.toString() || "",
      cannot_reconcile: data.cannot_reconcile,
      reconciliation_note: data.reconciliation_note || "",
      narrative_celebrations: data.narrative_celebrations || "",
      narrative_challenges: data.narrative_challenges || "",
      narrative_changes: data.narrative_changes || "",
    };
  }

  // Course-Level Assessment Section Handlers (NEW from CEI demo feedback)
  const courseLevelSection = document.getElementById("courseLevelSection");
  const courseDueDateInput = document.getElementById("courseDueDate");
  const cannotReconcileCheckbox = document.getElementById("cannotReconcile");
  const reconciliationNoteContainer = document.getElementById(
    "reconciliationNoteContainer",
  );
  const saveCourseDataBtn = document.getElementById("saveCourseData");
  const canEditDueDate = window.ASSESSMENT_CONFIG?.canEditDueDate || false;

  // Submit Course Button Handler (ONCE - prevents duplicate submissions)
  const submitCourseBtn = document.getElementById("submitCourseBtn");
  if (submitCourseBtn) {
    submitCourseBtn.addEventListener("click", function () {
      const compositeId = courseSelect.value;
      if (!compositeId) {
        alert("Please select a course first");
        return;
      }
      const [courseId, sectionId] = compositeId.split("::");
      const alertProgramAdmins =
        document.getElementById("alertProgramAdmins")?.checked || false;
      submitCourseForApproval(courseId, sectionId, alertProgramAdmins);
    });
  }

  // Toggle reconciliation note visibility
  if (cannotReconcileCheckbox) {
    cannotReconcileCheckbox.addEventListener("change", function () {
      reconciliationNoteContainer.style.display = this.checked
        ? "block"
        : "none";
      if (!this.checked) {
        document.getElementById("reconciliationNote").value = "";
      }
    });
  }

  // Load course-level data when course is selected
  async function loadCourseLevelData(compositeId) {
    try {
      if (!compositeId) {
        courseLevelSection.style.display = "none";
        return;
      }

      // Parse composite ID: "courseId::sectionId"
      const [courseId, sectionId] = compositeId.split("::");
      // Find the specific section selected
      const section = sectionId
        ? instructorSections.find((s) => s.section_id === sectionId)
        : instructorSections.find((s) => s.course_id === courseId);
      if (section) {
        // Populate read-only enrollment fields
        document.getElementById("courseEnrollment").value =
          section.enrollment || "Not set";
        document.getElementById("courseWithdrawals").value =
          section.withdrawals || 0;

        // Format and display due date (added from CEI demo feedback)
        if (courseDueDateInput) {
          const dueValue =
            section.due_date || section.assessment_due_date || "";
          if (dueValue) {
            const dueDate = new Date(dueValue);
            if (canEditDueDate) {
              courseDueDateInput.value = isNaN(dueDate.getTime())
                ? ""
                : dueDate.toISOString().split("T")[0];
            } else {
              courseDueDateInput.value = isNaN(dueDate.getTime())
                ? "Not set"
                : dueDate.toLocaleDateString();
            }
          } else {
            courseDueDateInput.value = canEditDueDate ? "" : "Not set";
          }
        }

        // Populate instructor input fields (if they exist)
        document.getElementById("courseStudentsPassed").value =
          section.students_passed || "";
        document.getElementById("courseStudentsDFIC").value =
          section.students_dfic || "";
        document.getElementById("cannotReconcile").checked =
          section.cannot_reconcile || false;
        document.getElementById("reconciliationNote").value =
          section.reconciliation_note || "";

        // Show/hide reconciliation note based on checkbox
        reconciliationNoteContainer.style.display = section.cannot_reconcile
          ? "block"
          : "none";

        // Populate narratives
        document.getElementById("narrativeCelebrations").value =
          section.narrative_celebrations || "";
        document.getElementById("narrativeChallenges").value =
          section.narrative_challenges || "";
        document.getElementById("narrativeChanges").value =
          section.narrative_changes || "";

        // Store loaded data for dirty tracking
        loadedCourseData = {
          students_passed: (section.students_passed || "").toString(),
          students_dfic: (section.students_dfic || "").toString(),
          cannot_reconcile: section.cannot_reconcile || false,
          reconciliation_note: section.reconciliation_note || "",
          narrative_celebrations: section.narrative_celebrations || "",
          narrative_challenges: section.narrative_challenges || "",
          narrative_changes: section.narrative_changes || "",
        };

        // Show the section
        courseLevelSection.style.display = "block";
      } else {
        courseLevelSection.style.display = "none";
      }
    } catch (error) {
      console.error("Error loading course-level data:", error);
      courseLevelSection.style.display = "none";
    }
  }

  // Save course-level data
  if (saveCourseDataBtn) {
    saveCourseDataBtn.addEventListener("click", async function () {
      const compositeId = courseSelect.value;
      if (!compositeId) {
        alert("Please select a course first");
        return;
      }

      // Parse composite ID: "courseId::sectionId"
      const [courseId, sectionId] = compositeId.split("::");

      try {
        const csrfToken = document.querySelector(
          'meta[name="csrf-token"]',
        )?.content;
        const section = sectionId
          ? instructorSections.find((s) => s.section_id === sectionId)
          : instructorSections.find((s) => s.course_id === courseId);

        if (!section) {
          alert("No section found for this course");
          return;
        }

        const data = {
          students_passed:
            Number.parseInt(
              document.getElementById("courseStudentsPassed").value,
            ) || null,
          students_dfic:
            Number.parseInt(
              document.getElementById("courseStudentsDFIC").value,
            ) || null,
          cannot_reconcile: document.getElementById("cannotReconcile").checked,
          reconciliation_note:
            document.getElementById("reconciliationNote").value.trim() || null,
          narrative_celebrations:
            document.getElementById("narrativeCelebrations").value.trim() ||
            null,
          narrative_challenges:
            document.getElementById("narrativeChallenges").value.trim() || null,
          narrative_changes:
            document.getElementById("narrativeChanges").value.trim() || null,
        };

        if (canEditDueDate && courseDueDateInput) {
          data.assessment_due_date = courseDueDateInput.value || null;
        }

        const response = await fetch(`/api/sections/${section.section_id}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrfToken,
          },
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || "Failed to save course data");
        }

        // Update loaded data to match what was just saved
        loadedCourseData = {
          students_passed: (data.students_passed || "").toString(),
          students_dfic: (data.students_dfic || "").toString(),
          cannot_reconcile: data.cannot_reconcile,
          reconciliation_note: data.reconciliation_note || "",
          narrative_celebrations: data.narrative_celebrations || "",
          narrative_challenges: data.narrative_challenges || "",
          narrative_changes: data.narrative_changes || "",
        };

        // Reload sections from API to refresh stale data
        await reloadSections();

        // Show success message
        const statusEl = document.getElementById("saveStatus");
        statusEl.textContent = "Course data saved successfully!";
        statusEl.className = "alert alert-success";
        statusEl.style.display = "block";

        // Scroll to the status message
        statusEl.scrollIntoView({ behavior: "smooth", block: "nearest" });

        // Hide after 5 seconds
        setTimeout(() => {
          statusEl.style.display = "none";
        }, 5000);
      } catch (error) {
        console.error("Error saving course data:", error);

        // Show error message
        const statusEl = document.getElementById("saveStatus");
        statusEl.textContent = "Failed to save course data: " + error.message;
        statusEl.className = "alert alert-danger";
        statusEl.style.display = "block";

        // Scroll to the status message
        statusEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });
  }

  // Filter event listeners
  if (termFilter) {
    termFilter.addEventListener("change", function () {
      activeTermFilter = this.value;
      applyFilters();
    });
  }

  if (courseFilter) {
    courseFilter.addEventListener("change", function () {
      activeCourseFilter = this.value;
      applyFilters();
    });
  }

  if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener("click", function () {
      activeTermFilter = "";
      activeCourseFilter = "";
      termFilter.value = "";
      courseFilter.value = "";
      applyFilters();
    });
  }

  // Initialize - call async function
  loadCourses()
    .then(() => {
      // Auto-select course if provided in URL query parameter
      const urlParams = new URLSearchParams(globalThis.location.search);
      const courseParam = urlParams.get("course");
      if (courseParam && courseSelect) {
        // Find the first option that matches this course ID (may have multiple sections)
        const matchingOption = Array.from(courseSelect.options).find((opt) =>
          opt.value.startsWith(courseParam + "::"),
        );
        if (matchingOption) {
          courseSelect.value = matchingOption.value;
          loadOutcomes(matchingOption.value);
          loadCourseLevelData(matchingOption.value);
        }
      }
    })
    .catch((err) => console.error("Failed to load courses:", err));
}); // Close DOMContentLoaded event listener
