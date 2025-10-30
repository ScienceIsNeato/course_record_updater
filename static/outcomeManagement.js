/**
 * Course Outcome (CLO) Management UI - Create, Edit, Delete Outcomes
 *
 * Handles:
 * - Create outcome form submission
 * - Edit outcome form submission
 * - Delete outcome confirmation
 * - API communication with CSRF protection
 */

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  initializeCreateOutcomeModal();
  initializeEditOutcomeModal();
});

/**
 * Initialize Create Outcome Modal
 * Sets up form submission for new outcomes
 */
function initializeCreateOutcomeModal() {
  const form = document.getElementById('createOutcomeForm');

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener('submit', async e => {
    e.preventDefault();

    const assessmentValue = document.getElementById('outcomeAssessmentMethod').value;

    const outcomeData = {
      course_id: document.getElementById('outcomeCourseId').value,
      clo_number: document.getElementById('outcomeCloNumber').value,
      description: document.getElementById('outcomeDescription').value,
      assessment_method: assessmentValue || null,
      active: document.getElementById('outcomeActive').checked
    };

    const createBtn = document.getElementById('createOutcomeBtn');
    const btnText = createBtn.querySelector('.btn-text');
    const btnSpinner = createBtn.querySelector('.btn-spinner');

    // Show loading state
    btnText.classList.add('d-none');
    btnSpinner.classList.remove('d-none');
    createBtn.disabled = true;

    try {
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      const response = await fetch('/api/outcomes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(csrfToken && { 'X-CSRFToken': csrfToken })
        },
        body: JSON.stringify(outcomeData)
      });

      if (response.ok) {
        const result = await response.json();

        // Success - close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('createOutcomeModal'));
        if (modal) {
          modal.hide();
        }

        form.reset();

        alert(result.message || 'Outcome created successfully!');

        // Reload outcomes list if function exists
        if (typeof window.loadOutcomes === 'function') {
          window.loadOutcomes();
        }
      } else {
        const error = await response.json();
        alert(`Failed to create outcome: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error creating outcome:', error); // eslint-disable-line no-console
      alert('Failed to create outcome. Please check your connection and try again.');
    } finally {
      // Restore button state
      btnText.classList.remove('d-none');
      btnSpinner.classList.add('d-none');
      createBtn.disabled = false;
    }
  });
}

/**
 * Initialize Edit Outcome Modal
 * Sets up form submission for updating outcomes
 */
function initializeEditOutcomeModal() {
  const form = document.getElementById('editOutcomeForm');

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const outcomeId = document.getElementById('editOutcomeId').value;
    const assessmentValue = document.getElementById('editOutcomeAssessmentMethod').value;

    const updateData = {
      clo_number: document.getElementById('editOutcomeCloNumber').value,
      description: document.getElementById('editOutcomeDescription').value,
      assessment_method: assessmentValue || null,
      active: document.getElementById('editOutcomeActive').checked
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

      const response = await fetch(`/api/outcomes/${outcomeId}`, {
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
        const modal = bootstrap.Modal.getInstance(document.getElementById('editOutcomeModal'));
        if (modal) {
          modal.hide();
        }

        alert(result.message || 'Outcome updated successfully!');

        // Reload outcomes list
        if (typeof window.loadOutcomes === 'function') {
          window.loadOutcomes();
        }
      } else {
        const error = await response.json();
        alert(`Failed to update outcome: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error updating outcome:', error); // eslint-disable-line no-console
      alert('Failed to update outcome. Please check your connection and try again.');
    } finally {
      // Restore button state
      btnText.classList.remove('d-none');
      btnSpinner.classList.add('d-none');
      saveBtn.disabled = false;
    }
  });
}

/**
 * Open Edit Outcome Modal with pre-populated data
 * Called from outcome list when Edit button is clicked
 */
function openEditOutcomeModal(outcomeId, outcomeData) {
  document.getElementById('editOutcomeId').value = outcomeId;
  document.getElementById('editOutcomeCloNumber').value = outcomeData.clo_number || '';
  document.getElementById('editOutcomeDescription').value = outcomeData.description || '';
  document.getElementById('editOutcomeAssessmentMethod').value =
    outcomeData.assessment_method || '';
  document.getElementById('editOutcomeActive').checked =
    outcomeData.active !== undefined ? outcomeData.active : true;

  const modal = new bootstrap.Modal(document.getElementById('editOutcomeModal'));
  modal.show();
}

/**
 * Delete outcome with confirmation
 * Shows confirmation dialog before deleting
 */
async function deleteOutcome(outcomeId, courseName, cloNumber) {
  const confirmation = confirm(
    `Are you sure you want to delete ${cloNumber} for ${courseName}?\n\n` +
      'This action cannot be undone.'
  );

  if (!confirmation) {
    return;
  }

  try {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

    const response = await fetch(`/api/outcomes/${outcomeId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken && { 'X-CSRFToken': csrfToken })
      }
    });

    if (response.ok) {
      alert(`${cloNumber} for ${courseName} deleted successfully.`);

      if (typeof window.loadOutcomes === 'function') {
        window.loadOutcomes();
      }
    } else {
      const error = await response.json();
      alert(`Failed to delete outcome: ${error.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error deleting outcome:', error); // eslint-disable-line no-console
    alert('Failed to delete outcome. Please try again.');
  }
}

// Expose functions to window for inline onclick handlers and testing
window.openEditOutcomeModal = openEditOutcomeModal;
window.deleteOutcome = deleteOutcome;
