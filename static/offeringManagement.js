/**
 * Course Offering Management UI - Create, Edit, Delete Offerings
 *
 * Handles:
 * - Create offering form submission
 * - Edit offering form submission
 * - Delete offering confirmation
 * - API communication with CSRF protection
 */

// Initialize when DOM is ready
// Handle case where DOM is already loaded (avoid race condition)
function initOfferingManagement() {
  // Safety check: only initialize if form elements exist
  if (
    !document.getElementById('createOfferingForm') &&
    !document.getElementById('editOfferingForm')
  ) {
    return; // Forms not on page yet, skip initialization
  }

  initializeCreateOfferingModal();
  initializeEditOfferingModal();
  setupModalListeners();
}

if (document.readyState === 'loading') {
  // DOM still loading, wait for it
  document.addEventListener('DOMContentLoaded', initOfferingManagement);
} else {
  // DOM already loaded, initialize immediately
  initOfferingManagement();
}

/**
 * Set up modal event listeners
 * Populate dropdowns when modals are shown
 */
function setupModalListeners() {
  const createModal = document.getElementById('createOfferingModal');
  const editModal = document.getElementById('editOfferingModal');

  if (createModal) {
    createModal.addEventListener('show.bs.modal', () => {
      loadCoursesAndTermsForCreateDropdown();
    });
  }

  if (editModal) {
    editModal.addEventListener('show.bs.modal', () => {
      loadCoursesAndTermsForEditDropdown();
    });
  }
}

/**
 * Load courses and terms for create offering dropdowns
 * Fetches from API and populates both select elements
 */
async function loadCoursesAndTermsForCreateDropdown() {
  const courseSelect = document.getElementById('offeringCourseId');
  const termSelect = document.getElementById('offeringTermId');
  const programSelect = document.getElementById('offeringProgramId');

  if (!courseSelect || !termSelect || !programSelect) {
    return;
  }

  // Set loading state
  courseSelect.innerHTML = '<option value="">Loading courses...</option>';
  termSelect.innerHTML = '<option value="">Loading terms...</option>';
  programSelect.innerHTML = '<option value="">Loading programs...</option>';

  try {
    // Fetch courses, terms, and programs in parallel
    const [coursesResponse, termsResponse, programsResponse] = await Promise.all([
      fetch('/api/courses'),
      fetch('/api/terms'),
      fetch('/api/management/programs')
    ]);

    if (!coursesResponse.ok || !termsResponse.ok || !programsResponse.ok) {
      throw new Error('Failed to fetch dropdown data');
    }

    const coursesData = await coursesResponse.json();
    const termsData = await termsResponse.json();
    const programsData = await programsResponse.json();

    const courses = coursesData.courses || [];
    const terms = termsData.terms || [];
    const programs = programsData.programs || [];

    // Populate courses dropdown
    courseSelect.innerHTML = '<option value="">Select Course</option>';
    courses.forEach(course => {
      const option = document.createElement('option');
      option.value = course.course_id;
      option.textContent = `${course.course_number} - ${course.course_title}`;
      courseSelect.appendChild(option);
    });

    // Populate terms dropdown
    termSelect.innerHTML = '<option value="">Select Term</option>';
    terms.forEach(term => {
      const option = document.createElement('option');
      option.value = term.term_id;
      option.textContent = term.name;
      termSelect.appendChild(option);
    });

    // Populate programs dropdown
    programSelect.innerHTML = '<option value="">Select Program</option>';
    programs.forEach(program => {
      const option = document.createElement('option');
      option.value = program.program_id || program.id;
      option.textContent = program.name || program.program_name;
      programSelect.appendChild(option);
    });

    if (courses.length === 0) {
      courseSelect.innerHTML = '<option value="">No courses available</option>';
    }
    if (terms.length === 0) {
      termSelect.innerHTML = '<option value="">No terms available</option>';
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Failed to load dropdown data:', error);
    courseSelect.innerHTML = '<option value="">Error loading courses</option>';
    termSelect.innerHTML = '<option value="">Error loading terms</option>';
  }
}

/**
 * Load courses and terms for edit offering dropdowns
 * Fetches from API and populates both select elements
 */
async function loadCoursesAndTermsForEditDropdown() {
  const programSelect = document.getElementById('editOfferingProgramId');

  if (!programSelect) {
    return;
  }

  // Set loading state for programs only (course/term are display-only)
  programSelect.innerHTML = '<option value="">Loading programs...</option>';

  try {
    // Fetch programs
    const programsResponse = await fetch('/api/management/programs');

    if (!programsResponse.ok) {
      throw new Error('Failed to fetch programs');
    }

    const programsData = await programsResponse.json();
    const programs = programsData.programs || [];

    // Populate programs dropdown
    programSelect.innerHTML = '<option value="">Select Program</option>';
    programs.forEach(program => {
      const option = document.createElement('option');
      option.value = program.program_id || program.id;
      option.textContent = program.name || program.program_name;
      programSelect.appendChild(option);
    });

    if (programs.length === 0) {
      programSelect.innerHTML = '<option value="">No programs available</option>';
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Failed to load programs:', error);
    programSelect.innerHTML = '<option value="">Error loading programs</option>';
  }
}

/**
 * Initialize Create Offering Modal
 * Sets up form submission for new offerings
 */
function initializeCreateOfferingModal() {
  const form = document.getElementById('createOfferingForm');

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener('submit', async e => {
    e.preventDefault();

    const capacityValue = document.getElementById('offeringCapacity').value;

    const offeringData = {
      course_id: document.getElementById('offeringCourseId').value,
      term_id: document.getElementById('offeringTermId').value,
      program_id: document.getElementById('offeringProgramId').value,
      status: document.getElementById('offeringStatus').value,
      capacity: capacityValue ? Number.parseInt(capacityValue) : null
    };

    const createBtn = document.getElementById('createOfferingBtn');
    const btnText = createBtn.querySelector('.btn-text');
    const btnSpinner = createBtn.querySelector('.btn-spinner');

    // Show loading state
    btnText.classList.add('d-none');
    btnSpinner.classList.remove('d-none');
    createBtn.disabled = true;

    try {
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      const response = await fetch('/api/offerings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(csrfToken && { 'X-CSRFToken': csrfToken })
        },
        body: JSON.stringify(offeringData)
      });

      if (response.ok) {
        const result = await response.json();

        // Success - close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('createOfferingModal'));
        if (modal) {
          modal.hide();
        }

        form.reset();

        alert(result.message || 'Offering created successfully!');

        // Reload offerings list if function exists
        if (typeof globalThis.loadOfferings === 'function') {
          globalThis.loadOfferings();
        }
      } else {
        const error = await response.json();
        alert(`Failed to create offering: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error creating offering:', error); // eslint-disable-line no-console
      alert('Failed to create offering. Please check your connection and try again.');
    } finally {
      // Restore button state
      btnText.classList.remove('d-none');
      btnSpinner.classList.add('d-none');
      createBtn.disabled = false;
    }
  });
}

/**
 * Initialize Edit Offering Modal
 * Sets up form submission for updating offerings
 */
function initializeEditOfferingModal() {
  const form = document.getElementById('editOfferingForm');

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const offeringId = document.getElementById('editOfferingId').value;
    const capacityValue = document.getElementById('editOfferingCapacity').value;

    const updateData = {
      program_id: document.getElementById('editOfferingProgramId').value,
      status: document.getElementById('editOfferingStatus').value,
      capacity: capacityValue ? Number.parseInt(capacityValue) : null
    };

    const saveBtn = this.querySelector('button[type="submit"]');
    const btnText = saveBtn.querySelector('.btn-text');
    const btnSpinner = saveBtn.querySelector('.btn-spinner');

    // Show loading state
    btnText.classList.add('d-none');
    btnSpinner.classList.remove('d-none');
    saveBtn.disabled = true;

    try {
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      const response = await fetch(`/api/offerings/${offeringId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(csrfToken && { 'X-CSRFToken': csrfToken })
        },
        body: JSON.stringify(updateData)
      });

      if (response.ok) {
        const result = await response.json();

        // Success - close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('editOfferingModal'));
        if (modal) {
          modal.hide();
        }

        alert(result.message || 'Offering updated successfully!');

        // Reload offerings list
        if (typeof globalThis.loadOfferings === 'function') {
          globalThis.loadOfferings();
        }
      } else {
        const error = await response.json();
        alert(`Failed to update offering: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error updating offering:', error); // eslint-disable-line no-console
      alert('Failed to update offering. Please check your connection and try again.');
    } finally {
      // Restore button state
      btnText.classList.remove('d-none');
      btnSpinner.classList.add('d-none');
      saveBtn.disabled = false;
    }
  });
}

/**
 * Open Edit Offering Modal with pre-populated data
 * Called from offering list when Edit button is clicked
 */
function openEditOfferingModal(offeringId, offeringData) {
  document.getElementById('editOfferingId').value = offeringId;
  document.getElementById('editOfferingStatus').value = offeringData.status || 'active';
  document.getElementById('editOfferingCapacity').value = offeringData.capacity || '';

  // Set program (will be populated by loadCoursesAndTermsForEditDropdown)
  const programSelect = document.getElementById('editOfferingProgramId');
  if (programSelect && offeringData.program_id) {
    // Wait a bit for dropdown to populate, then select
    setTimeout(() => {
      programSelect.value = offeringData.program_id;
    }, 100);
  }

  const modal = new bootstrap.Modal(document.getElementById('editOfferingModal'));
  modal.show();
}

/**
 * Delete offering with confirmation
 * Shows confirmation dialog before deleting
 */
async function deleteOffering(offeringId, courseName, termName) {
  const confirmation = confirm(
    `Are you sure you want to delete the offering for ${courseName} in ${termName}?\n\n` +
      'This action cannot be undone. All sections for this offering will be deleted.'
  );

  if (!confirmation) {
    return;
  }

  try {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

    const response = await fetch(`/api/offerings/${offeringId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken && { 'X-CSRFToken': csrfToken })
      }
    });

    if (response.ok) {
      alert(`Offering for ${courseName} in ${termName} deleted successfully.`);

      if (typeof globalThis.loadOfferings === 'function') {
        globalThis.loadOfferings();
      }
    } else {
      const error = await response.json();
      alert(`Failed to delete offering: ${error.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error deleting offering:', error); // eslint-disable-line no-console
    alert('Failed to delete offering. Please try again.');
  }
}

// Expose functions to window for inline onclick handlers and testing
globalThis.openEditOfferingModal = openEditOfferingModal;
globalThis.deleteOffering = deleteOffering;

// Export for testing (Node.js/Jest environment)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { initOfferingManagement, openEditOfferingModal, deleteOffering };
}
