/**
 * Faculty Invitation Management
 * Handles inviting new instructors to the system with optional course section assignment
 */

// Store dashboard data for populating dropdowns
let dashboardData = null;

function openInviteFacultyModal() {
  const modal = new bootstrap.Modal(document.getElementById('inviteFacultyModal'));

  // Reset form
  document.getElementById('inviteFacultyForm').reset();

  // Get dashboard data from the global cache
  if (window.dashboardDataCache) {
    dashboardData = window.dashboardDataCache;
    populateTermDropdown();
  } else if (window.InstitutionDashboard && window.InstitutionDashboard.cache) {
    dashboardData = window.InstitutionDashboard.cache;
    populateTermDropdown();
  }

  // Reset and disable dependent dropdowns
  resetOfferingDropdown();
  resetSectionDropdown();

  modal.show();
}

function populateTermDropdown() {
  const termSelect = document.getElementById('inviteFacultyTerm');
  termSelect.innerHTML = '<option value="">No course assignment</option>';

  if (!dashboardData || !dashboardData.terms) return;

  // Sort terms by start_date descending (most recent first)
  const terms = dashboardData.terms.sort((a, b) => {
    const dateA = a.start_date || '';
    const dateB = b.start_date || '';
    return dateB.localeCompare(dateA);
  });

  terms.forEach(term => {
    const option = document.createElement('option');
    option.value = term.term_id || term.id;
    option.textContent = term.term_name || term.name;
    termSelect.appendChild(option);
  });
}

function resetOfferingDropdown() {
  const offeringSelect = document.getElementById('inviteFacultyOffering');
  offeringSelect.innerHTML = '<option value="">Select term first</option>';
  offeringSelect.disabled = true;
}

function resetSectionDropdown() {
  const sectionSelect = document.getElementById('inviteFacultySection');
  sectionSelect.innerHTML = '<option value="">Select offering first</option>';
  sectionSelect.disabled = true;
}

function handleTermChange(event) {
  const termId = event.target.value;

  resetSectionDropdown();

  if (!termId) {
    resetOfferingDropdown();
    return;
  }

  populateOfferingDropdown(termId);
}

function populateOfferingDropdown(termId) {
  const offeringSelect = document.getElementById('inviteFacultyOffering');
  offeringSelect.innerHTML = '<option value="">Select an offering</option>';

  if (!dashboardData || !dashboardData.offerings) {
    offeringSelect.disabled = true;
    return;
  }

  // Filter offerings by term
  const offeringsForTerm = dashboardData.offerings.filter(offering => offering.term_id === termId);

  if (offeringsForTerm.length === 0) {
    offeringSelect.innerHTML = '<option value="">No offerings for this term</option>';
    offeringSelect.disabled = true;
    return;
  }

  // Get course lookup for display names
  const courseLookup = new Map();
  if (dashboardData.courses) {
    dashboardData.courses.forEach(course => {
      const courseId = course.course_id || course.id;
      courseLookup.set(courseId, course);
    });
  }

  offeringsForTerm.forEach(offering => {
    const course = courseLookup.get(offering.course_id);
    const courseName = course ? course.course_number : 'Unknown Course';

    const option = document.createElement('option');
    option.value = offering.offering_id || offering.id;
    option.textContent = courseName;
    offeringSelect.appendChild(option);
  });

  offeringSelect.disabled = false;
}

function handleOfferingChange(event) {
  const offeringId = event.target.value;

  if (!offeringId) {
    resetSectionDropdown();
    return;
  }

  populateSectionDropdown(offeringId);
}

function populateSectionDropdown(offeringId) {
  const sectionSelect = document.getElementById('inviteFacultySection');
  sectionSelect.innerHTML = '<option value="">Select a section</option>';

  if (!dashboardData || !dashboardData.sections) {
    sectionSelect.disabled = true;
    return;
  }

  // Filter sections by offering
  const sectionsForOffering = dashboardData.sections.filter(
    section => section.offering_id === offeringId
  );

  if (sectionsForOffering.length === 0) {
    sectionSelect.innerHTML = '<option value="">No sections for this offering</option>';
    sectionSelect.disabled = true;
    return;
  }

  // Get instructor lookup for display
  const instructorLookup = new Map();
  if (dashboardData.instructors) {
    dashboardData.instructors.forEach(instructor => {
      const instructorId = instructor.user_id || instructor.id;
      instructorLookup.set(instructorId, instructor);
    });
  }

  sectionsForOffering.forEach(section => {
    const instructor = instructorLookup.get(section.instructor_id);
    const instructorName = instructor
      ? `${instructor.first_name} ${instructor.last_name}`
      : 'Unassigned';

    const option = document.createElement('option');
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
  const btnText = submitBtn.querySelector('.btn-text');
  const btnSpinner = submitBtn.querySelector('.btn-spinner');

  // Get form data
  const email = document.getElementById('inviteFacultyEmail').value.trim();
  const firstName = document.getElementById('inviteFacultyFirstName').value.trim();
  const lastName = document.getElementById('inviteFacultyLastName').value.trim();
  const sectionId = document.getElementById('inviteFacultySection').value;
  const replaceExisting = document.getElementById('inviteFacultyReplaceExisting').checked;
  const csrfToken = form.querySelector('input[name="csrf_token"]').value;

  // Validate
  if (!email || !firstName || !lastName) {
    alert('Please fill in all required fields');
    return;
  }

  // Show loading state
  btnText.classList.add('d-none');
  btnSpinner.classList.remove('d-none');
  submitBtn.disabled = true;

  try {
    const payload = {
      email,
      role: 'instructor',
      first_name: firstName,
      last_name: lastName
    };

    // Add section assignment if selected
    if (sectionId) {
      payload.section_id = sectionId;
      payload.replace_existing = replaceExisting;
    }

    const response = await fetch('/api/invitations', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (response.ok && data.success) {
      // Close modal
      const modal = bootstrap.Modal.getInstance(document.getElementById('inviteFacultyModal'));
      modal.hide();

      // Show success message
      const assignmentMsg = sectionId
        ? '\n\nThey will be assigned to the selected section upon accepting the invitation.'
        : '';
      alert(
        `✅ Invitation sent to ${email}!${assignmentMsg}\n\nThe instructor will receive an email with instructions to complete their registration.`
      );

      // Reload dashboard to show updated data
      if (window.InstitutionDashboard && window.InstitutionDashboard.loadData) {
        window.InstitutionDashboard.loadData({ silent: true });
      }
    } else {
      alert(`❌ Failed to send invitation: ${data.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error sending invitation:', error); // eslint-disable-line no-console
    alert('❌ Failed to send invitation. Please try again.');
  } finally {
    // Reset button state
    btnText.classList.remove('d-none');
    btnSpinner.classList.add('d-none');
    submitBtn.disabled = false;
  }
}

// Expose function to global scope for inline onclick handlers
window.openInviteFacultyModal = openInviteFacultyModal;

// Attach event handlers when document loads
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('inviteFacultyForm');
  if (form) {
    form.addEventListener('submit', submitFacultyInvitation);
  }

  const termSelect = document.getElementById('inviteFacultyTerm');
  if (termSelect) {
    termSelect.addEventListener('change', handleTermChange);
  }

  const offeringSelect = document.getElementById('inviteFacultyOffering');
  if (offeringSelect) {
    offeringSelect.addEventListener('change', handleOfferingChange);
  }
});
