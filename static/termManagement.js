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

/**
 * Load and display all terms in a table
 */
async function loadTerms() {
  const container = document.getElementById('termsTableContainer');
  container.innerHTML = `
    <output class="d-flex justify-content-center align-items-center" style="min-height: 200px;" aria-live="polite">
      <div class="spinner-border" aria-hidden="true">
        <span class="visually-hidden">Loading terms...</span>
      </div>
    </output>
  `;

  try {
    const response = await fetch('/api/terms', {
      headers: { Accept: 'application/json' }
    });

    if (!response.ok) {
      throw new Error('Failed to load terms');
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to load terms');
    }

    const terms = data.terms || [];

    if (terms.length === 0) {
      container.innerHTML = `
        <div class="alert alert-info">
          <i class="fas fa-info-circle me-2"></i>
          No terms found. Create a term to get started.
        </div>
      `;
      return;
    }

    // Build table
    let html = `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>Term Name</th>
              <th>Start Date</th>
              <th>End Date</th>
              <th>Status</th>
              <th>Offerings</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
    `;

    terms.forEach(term => {
      const statusBadge = term.active
        ? '<span class="badge bg-success">Active</span>'
        : '<span class="badge bg-secondary">Inactive</span>';
      const offeringsCount = term.offerings_count || 0;

      html += `
        <tr>
          <td><strong>${escapeHtml(term.term_name || term.name || '-')}</strong></td>
          <td>${formatDate(term.start_date)}</td>
          <td>${formatDate(term.end_date)}</td>
          <td>${statusBadge}</td>
          <td>${offeringsCount}</td>
          <td>
            <button class="btn btn-sm btn-outline-secondary" onclick='openEditTermModal("${term.term_id || term.id}", ${JSON.stringify(term).replaceAll("'", '&apos;')})'>
              <i class="fas fa-edit"></i> Edit
            </button>
            <button class="btn btn-sm btn-outline-danger mt-1 mt-lg-0" onclick='deleteTerm("${term.term_id || term.id}", "${escapeHtml(term.term_name || term.name)}")'>
              <i class="fas fa-trash"></i> Delete
            </button>
          </td>
        </tr>
      `;
    });

    html += `
          </tbody>
        </table>
      </div>
    `;

    container.innerHTML = html;
  } catch (error) {
    console.error('Error loading terms:', error); // eslint-disable-line no-console
    container.innerHTML = `
      <div class="alert alert-danger">
        <i class="fas fa-exclamation-triangle me-2"></i>
        Error loading terms: ${escapeHtml(error.message)}
      </div>
    `;
  }
}

/**
 * Open create term modal
 */
function openCreateTermModal() {
  const modal = new bootstrap.Modal(document.getElementById('createTermModal'));
  modal.show();
}

/**
 * Format date for display
 */
function formatDate(dateString) {
  if (!dateString) return '-';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return dateString;
  }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Expose functions to window for inline onclick handlers and testing
globalThis.openEditTermModal = openEditTermModal;
globalThis.deleteTerm = deleteTerm;
globalThis.loadTerms = loadTerms;
globalThis.openCreateTermModal = openCreateTermModal;
