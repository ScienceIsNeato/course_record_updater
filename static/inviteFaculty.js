/**
 * Faculty Invitation Management
 * Handles inviting new instructors to the system with optional course section assignment
 */

// Store dashboard data for populating dropdowns
let dashboardData = null;

/**
 * Open the Invite Faculty Modal.
 * @param {Object} options - Optional configuration
 * @param {string} options.sectionId - Pre-select or force this section
 * @param {string} options.sectionName - Display name for the section (if not in data)
 * @param {string} options.termName - Display name for the term (if not in data)
 * @param {string} options.courseName - Display name for the offering/course (if not in data)
 */
function openInviteFacultyModal(options = {}) {
  const modal = new bootstrap.Modal(
    document.getElementById("inviteFacultyModal"),
  );

  // Reset form
  document.getElementById("inviteFacultyForm").reset();

  // Get dashboard data from global cache if available
  if (globalThis.dashboardDataCache) {
    dashboardData = globalThis.dashboardDataCache;
  } else if (globalThis.InstitutionDashboard?.cache) {
    dashboardData = globalThis.InstitutionDashboard.cache;
  }

  // Handle Term Dropdown
  const termSelect = document.getElementById("inviteFacultyTerm");
  termSelect.innerHTML = '<option value="">No course assignment</option>';

  if (options.sectionId) {
    // If a section is pre-selected (e.g. from Sections page)
    // We might not have full dashboard data, so we create "dummy" options to represent the selection
    const termOption = document.createElement("option");
    termOption.value = "preselected_term"; // Placeholder, as we might not know the term ID without data
    termOption.textContent = options.termName || "Current Term";
    termOption.selected = true;
    termSelect.appendChild(termOption);
    termSelect.disabled = true; // Lock it if pre-selected via this flow
  } else if (dashboardData?.terms) {
    // Normal flow: Populate from data
    const terms = dashboardData.terms.sort((a, b) => {
      const dateA = a.start_date || "";
      const dateB = b.start_date || "";
      return dateB.localeCompare(dateA);
    });
    terms.forEach((term) => {
      const option = document.createElement("option");
      option.value = term.term_id || term.id;
      option.textContent = term.term_name || term.name;
      termSelect.appendChild(option);
    });
    termSelect.disabled = false;
  }

  // Reset and disable dependent dropdowns initially
  const offeringSelect = document.getElementById("inviteFacultyOffering");
  offeringSelect.innerHTML = '<option value="">Select term first</option>';
  offeringSelect.disabled = true;

  const sectionSelect = document.getElementById("inviteFacultySection");
  sectionSelect.innerHTML = '<option value="">Select offering first</option>';
  sectionSelect.disabled = true;

  if (options.sectionId) {
    // Pre-fill Offering
    offeringSelect.innerHTML = "";
    const offeringOption = document.createElement("option");
    offeringOption.value = "preselected_offering"; // Placeholder
    offeringOption.textContent = options.courseName || "Select Course"; // We passed 'sectionName' as 'courseDisplay' in sections_list.html
    offeringOption.selected = true;
    offeringSelect.appendChild(offeringOption);
    offeringSelect.disabled = true;

    // Pre-fill Section
    sectionSelect.innerHTML = "";
    const sectionOption = document.createElement("option");
    sectionOption.value = options.sectionId;
    sectionOption.textContent = options.sectionName || "Selected Section";
    sectionOption.selected = true;
    sectionSelect.appendChild(sectionOption);

    // Note: The backend needs the section_id. It doesn't care about term/offering IDs if section_id is valid.
    // However, the form might fail validation if we don't pass them?
    // The original ad-hoc modal only passed section_id.
    // The logic in submitFacultyInvitation uses document.getElementById("inviteFacultySection").value
    // So as long as that has the value, we are good.
  }

  modal.show();
}

// ... existing helper functions for cascading dropdowns (populateTermDropdown, etc) remain,
// but handleTermChange and friends need to be aware they might not run if disabled.

function handleTermChange(event) {
  const termId = event.target.value;
  // ... existing logic ...
  if (termId === "preselected_term") return; // Do nothing for dummy value

  resetSectionDropdown();
  if (!termId) {
    resetOfferingDropdown();
    return;
  }
  populateOfferingDropdown(termId);
}

function populateOfferingDropdown(termId) {
  // ... same logic as before ...
  const offeringSelect = document.getElementById("inviteFacultyOffering");
  offeringSelect.innerHTML = '<option value="">Select an offering</option>';

  if (!dashboardData?.offerings) {
    offeringSelect.disabled = true;
    return;
  }
  // ...
  // Filter offerings ...
  const offeringsForTerm = dashboardData.offerings.filter(
    (offering) => offering.term_id === termId,
  );
  // ... etc
  // (Rest of the function needs to be preserved or I need to overwrite it all carefully)
  // Since I am replacing a chunk, I must be careful.
  // I will rewrite the whole chunk to be safe.

  if (offeringsForTerm.length === 0) {
    offeringSelect.innerHTML =
      '<option value="">No offerings for this term</option>';
    offeringSelect.disabled = true;
    return;
  }

  const courseLookup = new Map();
  if (dashboardData.courses) {
    dashboardData.courses.forEach((course) => {
      const courseId = course.course_id || course.id;
      courseLookup.set(courseId, course);
    });
  }

  offeringsForTerm.forEach((offering) => {
    const course = courseLookup.get(offering.course_id);
    const courseName = course ? course.course_number : "Unknown Course";
    const option = document.createElement("option");
    option.value = offering.offering_id || offering.id;
    option.textContent = courseName;
    offeringSelect.appendChild(option);
  });

  offeringSelect.disabled = false;
}

function resetOfferingDropdown() {
  const offeringSelect = document.getElementById("inviteFacultyOffering");
  offeringSelect.innerHTML = '<option value="">Select term first</option>';
  offeringSelect.disabled = true;
}

function resetSectionDropdown() {
  const sectionSelect = document.getElementById("inviteFacultySection");
  sectionSelect.innerHTML = '<option value="">Select offering first</option>';
  sectionSelect.disabled = true;
}

function handleOfferingChange(event) {
  const offeringId = event.target.value;
  if (offeringId === "preselected_offering") return;

  if (!offeringId) {
    resetSectionDropdown();
    return;
  }
  populateSectionDropdown(offeringId);
}

function populateSectionDropdown(offeringId) {
  const sectionSelect = document.getElementById("inviteFacultySection");
  sectionSelect.innerHTML = '<option value="">Select a section</option>';

  if (!dashboardData?.sections) {
    sectionSelect.disabled = true;
    return;
  }

  const sectionsForOffering = dashboardData.sections.filter(
    (section) => section.offering_id === offeringId,
  );

  if (sectionsForOffering.length === 0) {
    sectionSelect.innerHTML =
      '<option value="">No sections for this offering</option>';
    sectionSelect.disabled = true;
    return;
  }

  const instructorLookup = new Map();
  if (dashboardData.instructors) {
    dashboardData.instructors.forEach((instructor) => {
      const instructorId = instructor.user_id || instructor.id;
      instructorLookup.set(instructorId, instructor);
    });
  }

  sectionsForOffering.forEach((section) => {
    const instructor = instructorLookup.get(section.instructor_id);
    const instructorName = instructor
      ? `${instructor.first_name} ${instructor.last_name}`
      : "Unassigned";

    const option = document.createElement("option");
    option.value = section.section_id || section.id;
    option.textContent = `Section ${section.section_number} (${instructorName})`;
    sectionSelect.appendChild(option);
  });

  sectionSelect.disabled = false;
}

async function submitFacultyInvitation(event) {
  event.preventDefault();

  const form = event.target;
  const submitBtn = form.querySelector('button[type="submit"]');
  const btnText = submitBtn.querySelector(".btn-text");
  const btnSpinner = submitBtn.querySelector(".btn-spinner");

  // Get form data
  const email = document.getElementById("inviteFacultyEmail").value.trim();
  const firstName = document
    .getElementById("inviteFacultyFirstName")
    .value.trim();
  const lastName = document
    .getElementById("inviteFacultyLastName")
    .value.trim();
  const sectionId = document.getElementById("inviteFacultySection").value;
  const replaceExisting = document.getElementById(
    "inviteFacultyReplaceExisting",
  ).checked;
  const csrfToken = form.querySelector('input[name="csrf_token"]').value;

  // Validate
  if (!email || !firstName || !lastName) {
    alert("Please fill in all required fields");
    return;
  }

  // Show loading state
  btnText.classList.add("d-none");
  btnSpinner.classList.remove("d-none");
  submitBtn.disabled = true;

  try {
    const payload = {
      email,
      role: "instructor",
      first_name: firstName,
      last_name: lastName,
    };

    // Add section assignment if selected
    if (sectionId) {
      payload.section_id = sectionId;
      payload.replace_existing = replaceExisting;
    }

    const response = await fetch("/api/invitations", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (response.ok && data.success) {
      // Close modal
      const modal = bootstrap.Modal.getInstance(
        document.getElementById("inviteFacultyModal"),
      );
      modal.hide();

      // Show success message
      const assignmentMsg = sectionId
        ? "\n\nThey will be assigned to the selected section upon accepting the invitation."
        : "";
      alert(
        `✅ Invitation sent to ${email}!${assignmentMsg}\n\nThe instructor will receive an email with instructions to complete their registration.`,
      );

      // Reload dashboard to show updated data
      if (globalThis.InstitutionDashboard?.loadData) {
        globalThis.InstitutionDashboard.loadData({ silent: true });
      }

      // Dispatch event for other listeners (e.g., sections page)
      document.dispatchEvent(
        new CustomEvent("faculty-invited", {
          detail: { email, sectionId },
        }),
      );
    } else {
      alert(`❌ Failed to send invitation: ${data.error || "Unknown error"}`);
    }
  } catch (error) {
    console.error("Error sending invitation:", error); // eslint-disable-line no-console
    alert("❌ Failed to send invitation. Please try again.");
  } finally {
    // Reset button state
    btnText.classList.remove("d-none");
    btnSpinner.classList.add("d-none");
    submitBtn.disabled = false;
  }
}

// Expose function to global scope for inline onclick handlers
globalThis.openInviteFacultyModal = openInviteFacultyModal;

// Attach event handlers when document loads
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("inviteFacultyForm");
  if (form) {
    form.addEventListener("submit", submitFacultyInvitation);
  }

  const termSelect = document.getElementById("inviteFacultyTerm");
  if (termSelect) {
    termSelect.addEventListener("change", handleTermChange);
  }

  const offeringSelect = document.getElementById("inviteFacultyOffering");
  if (offeringSelect) {
    offeringSelect.addEventListener("change", handleOfferingChange);
  }
});
