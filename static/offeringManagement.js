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
document.addEventListener('DOMContentLoaded', () => {
  initializeCreateOfferingModal();
  initializeEditOfferingModal();
});

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
      status: document.getElementById('offeringStatus').value,
      capacity: capacityValue ? parseInt(capacityValue) : null
    };

    const createBtn = document.getElementById('createOfferingBtn');
    const btnText = createBtn.querySelector('.btn-text');
    const btnSpinner = createBtn.querySelector('.btn-spinner');

    // Show loading state
    btnText.classList.add('d-none');
    btnSpinner.classList.remove('d-none');
    createBtn.disabled = true;

    try {
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

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
        if (typeof window.loadOfferings === 'function') {
          window.loadOfferings();
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
      status: document.getElementById('editOfferingStatus').value,
      capacity: capacityValue ? parseInt(capacityValue) : null
    };

    const saveBtn = this.querySelector('button[type="submit"]');
    const btnText = saveBtn.querySelector('.btn-text');
    const btnSpinner = saveBtn.querySelector('.btn-spinner');

    // Show loading state
    btnText.classList.add('d-none');
    btnSpinner.classList.remove('d-none');
    saveBtn.disabled = true;

    try {
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

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
        if (typeof window.loadOfferings === 'function') {
          window.loadOfferings();
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

      if (typeof window.loadOfferings === 'function') {
        window.loadOfferings();
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
window.openEditOfferingModal = openEditOfferingModal;
window.deleteOffering = deleteOffering;
