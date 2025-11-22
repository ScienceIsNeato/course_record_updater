/**
 * Course Management UI - Create, Edit, Delete Courses
 *
 * Handles:
 * - Create course form submission
 * - Edit course form submission
 * - Delete course confirmation
 * - API communication with CSRF protection
 */

// Initialize when DOM is ready
// Handle case where DOM is already loaded (avoid race condition)
function initCourseManagement() {
  // Safety check: only initialize if form elements exist
  if (!document.getElementById('createCourseForm') && !document.getElementById('editCourseForm')) {
    return; // Forms not on page yet, skip initialization
  }

  initializeCreateCourseModal();
  initializeEditCourseModal();
  setupModalListeners();
}

if (document.readyState === 'loading') {
  // DOM still loading, wait for it
  document.addEventListener('DOMContentLoaded', initCourseManagement);
} else {
  // DOM already loaded, initialize immediately
  initCourseManagement();
}

/**
 * Set up modal event listeners
 * Populate dropdowns when modals are shown
 */
function setupModalListeners() {
  const createModal = document.getElementById('createCourseModal');
  const editModal = document.getElementById('editCourseModal');

  if (createModal) {
    createModal.addEventListener('show.bs.modal', () => {
      loadProgramsForCreateDropdown();
    });
  }

  if (editModal) {
    editModal.addEventListener('show.bs.modal', () => {
      loadProgramsForEditDropdown();
    });
  }
}

/**
 * Load programs for create course dropdown
 * Fetches programs from API based on user's institution
 */
async function loadProgramsForCreateDropdown() {
  const select = document.getElementById('courseProgramIds');

  if (!select) {
    return;
  }

  // Clear existing options
  select.innerHTML = '<option value="">Loading programs...</option>';

  try {
    const response = await fetch('/api/programs');

    if (!response.ok) {
      throw new Error('Failed to fetch programs');
    }

    const data = await response.json();
    const programs = data.programs || [];

    // Populate dropdown
    select.innerHTML = ''; // Clear loading message

    if (programs.length === 0) {
      select.innerHTML = '<option value="">No programs available</option>';
      return;
    }

    programs.forEach(program => {
      const option = document.createElement('option');
      option.value = program.program_id;
      option.textContent = `${program.name} (${program.short_name})`;
      select.appendChild(option);
    });
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Failed to load programs for dropdown:', error);
    select.innerHTML = '<option value="">Error loading programs</option>';
  }
}

/**
 * Load programs for edit course dropdown
 * Fetches programs from API based on user's institution
 */
async function loadProgramsForEditDropdown() {
  const select = document.getElementById('editCourseProgramIds');

  if (!select) {
    return;
  }

  // Clear existing options
  select.innerHTML = '<option value="">Loading programs...</option>';

  try {
    const response = await fetch('/api/programs');

    if (!response.ok) {
      throw new Error('Failed to fetch programs');
    }

    const data = await response.json();
    const programs = data.programs || [];

    // Populate dropdown
    select.innerHTML = ''; // Clear loading message

    if (programs.length === 0) {
      select.innerHTML = '<option value="">No programs available</option>';
      return;
    }

    programs.forEach(program => {
      const option = document.createElement('option');
      option.value = program.program_id;
      option.textContent = `${program.name} (${program.short_name})`;
      select.appendChild(option);
    });
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Failed to load programs for dropdown:', error);
    select.innerHTML = '<option value="">Error loading programs</option>';
  }
}

/**
 * Initialize Create Course Modal
 * Sets up form submission for new courses
 */
function initializeCreateCourseModal() {
  const form = document.getElementById('createCourseForm');

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener('submit', async e => {
    e.preventDefault();

    // Get selected program IDs from multi-select
    const programSelect = document.getElementById('courseProgramIds');
    const selectedPrograms = Array.from(programSelect.selectedOptions).map(option => option.value);

    const courseData = {
      course_number: document.getElementById('courseNumber').value,
      course_title: document.getElementById('courseTitle').value,
      department: document.getElementById('courseDepartment').value,
      credit_hours: Number.parseInt(document.getElementById('courseCreditHours').value),
      program_ids: selectedPrograms,
      active: (function () {
        const checkbox = document.getElementById('courseActive');
        return checkbox?.checked !== undefined ? checkbox.checked : true;
      })()
    };

    const createBtn = document.getElementById('createCourseBtn');
    const btnText = createBtn.querySelector('.btn-text');
    const btnSpinner = createBtn.querySelector('.btn-spinner');

    // Show loading state
    btnText.classList.add('d-none');
    btnSpinner.classList.remove('d-none');
    createBtn.disabled = true;

    try {
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      const response = await fetch('/api/courses', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(csrfToken && { 'X-CSRFToken': csrfToken })
        },
        body: JSON.stringify(courseData)
      });

      if (response.ok) {
        const result = await response.json();

        // Success - close modal and reset form
        const modalElement = document.getElementById('createCourseModal');
        let modal = bootstrap.Modal.getInstance(modalElement);
        if (!modal) {
          modal = new bootstrap.Modal(modalElement);
        }
        modal.hide();

        form.reset();

        alert(result.message || 'Course created successfully!');

        // Reload courses list if function exists
        if (typeof window.loadCourses === 'function') {
          window.loadCourses();
        }
      } else {
        const error = await response.json();
        alert(`Failed to create course: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error creating course:', error); // eslint-disable-line no-console
      alert('Failed to create course. Please check your connection and try again.');
    } finally {
      // Restore button state
      btnText.classList.remove('d-none');
      btnSpinner.classList.add('d-none');
      createBtn.disabled = false;
    }
  });
}

/**
 * Initialize Edit Course Modal
 * Sets up form submission for updating courses
 */
function initializeEditCourseModal() {
  const form = document.getElementById('editCourseForm');

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const courseId = document.getElementById('editCourseId').value;

    // Get selected program IDs from multi-select
    const programSelect = document.getElementById('editCourseProgramIds');
    const selectedPrograms = Array.from(programSelect.selectedOptions).map(option => option.value);

    const updateData = {
      course_number: document.getElementById('editCourseNumber').value,
      course_title: document.getElementById('editCourseTitle').value,
      department: document.getElementById('editCourseDepartment').value,
      credit_hours: Number.parseInt(document.getElementById('editCourseCreditHours').value),
      program_ids: selectedPrograms,
      active: (function () {
        const checkbox = document.getElementById('editCourseActive');
        return checkbox?.checked !== undefined ? checkbox.checked : true;
      })()
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

      const response = await fetch(`/api/courses/${courseId}`, {
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
        const modalElement = document.getElementById('editCourseModal');
        let modal = bootstrap.Modal.getInstance(modalElement);
        if (!modal) {
          modal = new bootstrap.Modal(modalElement);
        }
        modal.hide();

        alert(result.message || 'Course updated successfully!');

        // Reload courses list
        if (typeof window.loadCourses === 'function') {
          window.loadCourses();
        }
      } else {
        const error = await response.json();
        alert(`Failed to update course: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error updating course:', error); // eslint-disable-line no-console
      alert('Failed to update course. Please check your connection and try again.');
    } finally {
      // Restore button state
      btnText.classList.remove('d-none');
      btnSpinner.classList.add('d-none');
      saveBtn.disabled = false;
    }
  });
}

/**
 * Open Edit Course Modal with pre-populated data
 * Called from course list when Edit button is clicked
 */
function openEditCourseModal(courseId, courseData) {
  document.getElementById('editCourseId').value = courseId;
  document.getElementById('editCourseNumber').value = courseData.course_number || '';
  document.getElementById('editCourseTitle').value = courseData.course_title || '';
  document.getElementById('editCourseDepartment').value = courseData.department || '';
  document.getElementById('editCourseCreditHours').value = courseData.credit_hours || 3;

  // Set active checkbox if it exists in the DOM
  const activeCheckbox = document.getElementById('editCourseActive');
  if (activeCheckbox) {
    activeCheckbox.checked = courseData.active !== undefined ? courseData.active : true;
  }

  // Select program IDs in multi-select
  const programSelect = document.getElementById('editCourseProgramIds');
  if (programSelect && courseData.program_ids) {
    Array.from(programSelect.options).forEach(option => {
      option.selected = courseData.program_ids.includes(option.value);
    });
  }

  const modal = new bootstrap.Modal(document.getElementById('editCourseModal'));
  modal.show();
}

/**
 * Delete course with confirmation
 * Shows confirmation dialog before deleting
 */
async function deleteCourse(courseId, courseNumber, courseTitle) {
  const confirmation = confirm(
    `Are you sure you want to delete ${courseNumber} - ${courseTitle}?\n\n` +
      'This action cannot be undone. All offerings, sections, and outcomes for this course will be deleted.'
  );

  if (!confirmation) {
    return;
  }

  try {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

    const response = await fetch(`/api/courses/${courseId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken && { 'X-CSRFToken': csrfToken })
      }
    });

    if (response.ok) {
      alert(`${courseNumber} deleted successfully.`);

      if (typeof window.loadCourses === 'function') {
        window.loadCourses();
      }
    } else {
      const error = await response.json();
      alert(`Failed to delete course: ${error.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error deleting course:', error); // eslint-disable-line no-console
    alert('Failed to delete course. Please try again.');
  }
}

// Expose functions to window for inline onclick handlers and testing
window.openEditCourseModal = openEditCourseModal;
window.deleteCourse = deleteCourse;

// Export for testing (Node.js/Jest environment)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { initCourseManagement, openEditCourseModal, deleteCourse };
}
