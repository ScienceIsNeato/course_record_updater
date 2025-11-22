/**
 * Term Management UI - Create, Edit, Delete Terms
 *
 * Handles:
 * - Create term form submission
 * - Edit term form submission
 * - Delete term confirmation
 * - API communication with CSRF protection
 */

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  initializeCreateTermModal();
  initializeEditTermModal();
});

/**
 * Initialize Create Term Modal
 * Sets up form submission for new terms
 */
function initializeCreateTermModal() {
  const form = document.getElementById('createTermForm');

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener('submit', async e => {
    e.preventDefault();

    const termData = {
      name: document.getElementById('termName').value,
      start_date: document.getElementById('termStartDate').value,
      end_date: document.getElementById('termEndDate').value,
      assessment_due_date: document.getElementById('termAssessmentDueDate').value,
      active: document.getElementById('termActive').checked
    };

    const createBtn = document.getElementById('createTermBtn');
    const btnText = createBtn.querySelector('.btn-text');
    const btnSpinner = createBtn.querySelector('.btn-spinner');

    // Show loading state
    btnText.classList.add('d-none');
    btnSpinner.classList.remove('d-none');
    createBtn.disabled = true;

    try {
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      const response = await fetch('/api/terms', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(csrfToken && { 'X-CSRFToken': csrfToken })
        },
        body: JSON.stringify(termData)
      });

      if (response.ok) {
        const result = await response.json();

        // Success - close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('createTermModal'));
        if (modal) {
          modal.hide();
        }

        form.reset();

        alert(result.message || 'Term created successfully!');

        // Reload terms list if function exists
        if (typeof globalThis.loadTerms === 'function') {
          globalThis.loadTerms();
        }
      } else {
        const error = await response.json();
        alert(`Failed to create term: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error creating term:', error); // eslint-disable-line no-console
      alert('Failed to create term. Please check your connection and try again.');
    } finally {
      // Restore button state
      btnText.classList.remove('d-none');
      btnSpinner.classList.add('d-none');
      createBtn.disabled = false;
    }
  });
}

/**
 * Initialize Edit Term Modal
 * Sets up form submission for updating terms
 */
function initializeEditTermModal() {
  const form = document.getElementById('editTermForm');

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const termId = document.getElementById('editTermId').value;
    const updateData = {
      name: document.getElementById('editTermName').value,
      start_date: document.getElementById('editTermStartDate').value,
      end_date: document.getElementById('editTermEndDate').value,
      assessment_due_date: document.getElementById('editTermAssessmentDueDate').value,
      active: document.getElementById('editTermActive').checked
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

      const response = await fetch(`/api/terms/${termId}`, {
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
        const modal = bootstrap.Modal.getInstance(document.getElementById('editTermModal'));
        if (modal) {
          modal.hide();
        }

        alert(result.message || 'Term updated successfully!');

        // Reload terms list
        if (typeof globalThis.loadTerms === 'function') {
          globalThis.loadTerms();
        }
      } else {
        const error = await response.json();
        alert(`Failed to update term: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error updating term:', error); // eslint-disable-line no-console
      alert('Failed to update term. Please check your connection and try again.');
    } finally {
      // Restore button state
      btnText.classList.remove('d-none');
      btnSpinner.classList.add('d-none');
      saveBtn.disabled = false;
    }
  });
}

/**
 * Open Edit Term Modal with pre-populated data
 * Called from term list when Edit button is clicked
 */
function openEditTermModal(termId, termData) {
  document.getElementById('editTermId').value = termId;
  document.getElementById('editTermName').value = termData.name || '';
  document.getElementById('editTermStartDate').value = termData.start_date || '';
  document.getElementById('editTermEndDate').value = termData.end_date || '';
  document.getElementById('editTermAssessmentDueDate').value = termData.assessment_due_date || '';
  document.getElementById('editTermActive').checked =
    termData.active !== undefined ? termData.active : true;

  const modal = new bootstrap.Modal(document.getElementById('editTermModal'));
  modal.show();
}

/**
 * Delete term with confirmation
 * Shows confirmation dialog before deleting
 */
async function deleteTerm(termId, termName) {
  const confirmation = confirm(
    `Are you sure you want to delete "${termName}"?\n\n` +
      'This action cannot be undone. All course offerings in this term will be deleted.'
  );

  if (!confirmation) {
    return;
  }

  try {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

    const response = await fetch(`/api/terms/${termId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken && { 'X-CSRFToken': csrfToken })
      }
    });

    if (response.ok) {
      alert(`${termName} deleted successfully.`);

      if (typeof globalThis.loadTerms === 'function') {
        globalThis.loadTerms();
      }
    } else {
      const error = await response.json();
      alert(`Failed to delete term: ${error.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error deleting term:', error); // eslint-disable-line no-console
    alert('Failed to delete term. Please try again.');
  }
}

// Expose functions to window for inline onclick handlers and testing
globalThis.openEditTermModal = openEditTermModal;
globalThis.deleteTerm = deleteTerm;
