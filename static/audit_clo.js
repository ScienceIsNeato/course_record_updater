/**
 * CLO Audit & Approval Interface
 *
 * Handles the admin interface for reviewing and approving CLOs
 */

/**
 * Get status badge HTML
 */
function getStatusBadge(status) {
  const badges = {
    unassigned: '<span class="badge bg-secondary">Unassigned</span>',
    assigned: '<span class="badge bg-info">Assigned</span>',
    in_progress: '<span class="badge bg-primary">In Progress</span>',
    awaiting_approval: '<span class="badge bg-warning">Awaiting Approval</span>',
    approval_pending: '<span class="badge bg-danger">Needs Rework</span>',
    approved: '<span class="badge bg-success">✓ Approved</span>',
    never_coming_in: '<span class="badge bg-dark">NCI - Never Coming In</span>'
  };
  return badges[status] || '<span class="badge bg-secondary">Unknown</span>';
}

/**
 * Format date string
 */
function formatDate(dateString) {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleString();
}

/**
 * Truncate text
 */
function truncateText(text, maxLength) {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Approve CLO (extracted for testability)
 */
async function approveCLO() {
  if (!window.currentCLO) return;

  if (
    !confirm(
      `Approve this CLO?\n\n${window.currentCLO.course_number} - CLO ${window.currentCLO.clo_number}`
    )
  ) {
    return;
  }

  const outcomeId = window.currentCLO.outcome_id;
  if (!outcomeId) {
    alert('Error: CLO ID not found');
    return;
  }

  try {
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

    const response = await fetch(`/api/outcomes/${outcomeId}/approve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken
      }
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to approve CLO');
    }

    // Close modal
    const cloDetailModal = document.getElementById('cloDetailModal');
    const modal = bootstrap.Modal.getInstance(cloDetailModal);
    modal.hide();

    // Show success
    alert('CLO approved successfully!');

    // Reload list
    await window.loadCLOs();
  } catch (error) {
    alert('Failed to approve CLO: ' + error.message);
  }
}

/**
 * Mark CLO as Never Coming In (NCI) (extracted for testability)
 */
async function markAsNCI() {
  if (!window.currentCLO) return;

  const reason = prompt(
    `Mark this CLO as "Never Coming In"?\n\n${window.currentCLO.course_number} - CLO ${window.currentCLO.clo_number}\n\nOptional: Provide a reason (e.g., "Instructor left institution", "Non-responsive instructor"):`
  );

  // null means cancelled, empty string is allowed
  if (reason === null) {
    return;
  }

  try {
    const outcomeId = window.currentCLO.outcome_id;

    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

    const response = await fetch(`/api/outcomes/${outcomeId}/mark-nci`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken
      },
      body: JSON.stringify({
        reason: reason.trim() || null
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to mark CLO as NCI');
    }

    // Close modal
    const cloDetailModal = document.getElementById('cloDetailModal');
    const modal = bootstrap.Modal.getInstance(cloDetailModal);
    modal.hide();

    // Show success
    alert('CLO marked as Never Coming In (NCI)');

    // Reload list
    await window.loadCLOs();
    await window.updateStats();
  } catch (error) {
    alert('Failed to mark CLO as NCI: ' + error.message);
  }
}

// Assign to window IMMEDIATELY for browser use (not inside DOMContentLoaded)
// This ensures functions are available even if DOM is already loaded
window.approveCLO = approveCLO;
window.markAsNCI = markAsNCI;

document.addEventListener('DOMContentLoaded', () => {
  // DOM elements
  const statusFilter = document.getElementById('statusFilter');
  const sortBy = document.getElementById('sortBy');
  const sortOrder = document.getElementById('sortOrder');
  const cloListContainer = document.getElementById('cloListContainer');
  const cloDetailModal = document.getElementById('cloDetailModal');
  const requestReworkModal = document.getElementById('requestReworkModal');
  const requestReworkForm = document.getElementById('requestReworkForm');

  // State - use window for global access by extracted functions
  window.currentCLO = null;
  let allCLOs = [];

  // Initialize
  loadCLOs();

  // Event listeners
  statusFilter.addEventListener('change', loadCLOs);
  sortBy.addEventListener('change', renderCLOList);
  sortOrder.addEventListener('change', renderCLOList);

  // Event delegation for CLO row clicks
  cloListContainer.addEventListener('click', e => {
    const row = e.target.closest('tr[data-outcome-id]');
    if (row && !e.target.closest('.clo-actions')) {
      const outcomeId = row.dataset.outcomeId;
      if (outcomeId) {
        window.showCLODetails(outcomeId);
      }
      return;
    }

    // Handle View button clicks
    const viewBtn = e.target.closest('button[data-outcome-id]');
    if (viewBtn) {
      e.stopPropagation();
      const outcomeId = viewBtn.dataset.outcomeId;
      if (outcomeId) {
        window.showCLODetails(outcomeId);
      }
    }
  });

  requestReworkForm.addEventListener('submit', async e => {
    e.preventDefault();
    await submitReworkRequest();
  });

  /**
   * Load CLOs from API
   */
  async function loadCLOs() {
    try {
      cloListContainer.innerHTML = `
                <div class="text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="text-muted mt-2">Loading CLOs...</p>
                </div>
            `;

      const status = statusFilter.value;
      const url = status === 'all' ? '/api/outcomes/audit' : `/api/outcomes/audit?status=${status}`;

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Failed to load CLOs');
      }

      const data = await response.json();
      allCLOs = data.outcomes || [];

      // Update stats
      updateStats();

      // Render list
      renderCLOList();
    } catch (error) {
      // Log error to aid debugging
      // eslint-disable-next-line no-console
      console.error('Error loading CLOs:', error);
      cloListContainer.innerHTML = `
                <div class="alert alert-danger">
                    <strong>Error:</strong> Failed to load CLOs. ${error.message}
                </div>
            `;
    }
  }

  /**
   * Update summary statistics
   */
  async function updateStats() {
    try {
      // Fetch stats for each status (added NCI from CEI demo feedback)
      const statuses = [
        'awaiting_approval',
        'approval_pending',
        'approved',
        'in_progress',
        'never_coming_in'
      ];
      const promises = statuses.map(status =>
        fetch(`/api/outcomes/audit?status=${status}`)
          .then(r => r.json())
          .then(d => d.count || 0)
      );

      const [awaiting, pending, approved, inProgress, nci] = await Promise.all(promises);

      document.getElementById('statAwaitingApproval').textContent = awaiting;
      document.getElementById('statNeedsRework').textContent = pending;
      document.getElementById('statApproved').textContent = approved;
      document.getElementById('statInProgress').textContent = inProgress;
      if (document.getElementById('statNCI')) {
        document.getElementById('statNCI').textContent = nci;
      }
    } catch (error) {
      // Log error to aid debugging, but allow graceful degradation
      // eslint-disable-next-line no-console
      console.error('Error updating stats:', error);
    }
  }

  /**
   * Render CLO list
   */
  function renderCLOList() {
    if (allCLOs.length === 0) {
      cloListContainer.innerHTML = `
                <div class="text-center py-5">
                    <p class="text-muted">No CLOs found for the selected filter.</p>
                </div>
            `;
      return;
    }

    // Sort CLOs
    const sorted = sortCLOs([...allCLOs]);

    // Build table
    let html = `
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Status</th>
                            <th>Course</th>
                            <th>CLO #</th>
                            <th>Description</th>
                            <th>Instructor</th>
                            <th>Submitted</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

    sorted.forEach(clo => {
      const statusBadge = getStatusBadge(clo.status);
      const description = truncateText(clo.description, 60);
      const submittedDate = clo.submitted_at ? formatDate(clo.submitted_at) : 'N/A';
      const outcomeId = escapeHtml(String(clo.outcome_id));

      html += `
                <tr data-outcome-id="${outcomeId}" style="cursor: pointer;" class="clo-row">
                    <td>${statusBadge}</td>
                    <td><strong>${escapeHtml(clo.course_number || 'N/A')}</strong></td>
                    <td>${escapeHtml(clo.clo_number || 'N/A')}</td>
                    <td>${escapeHtml(description)}</td>
                    <td>${escapeHtml(clo.instructor_name || 'N/A')}</td>
                    <td><small>${submittedDate}</small></td>
                    <td class="clo-actions">
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary" data-outcome-id="${outcomeId}">
                                <i class="fas fa-eye"></i> View
                            </button>
                        </div>
                    </td>
                </tr>
            `;
    });

    html += `
                    </tbody>
                </table>
            </div>
        `;

    cloListContainer.innerHTML = html;
  }

  /**
   * Sort CLOs based on current sort settings
   */
  function sortCLOs(clos) {
    const by = sortBy.value;
    const order = sortOrder.value;

    clos.sort((a, b) => {
      let aVal, bVal;

      switch (by) {
        case 'submitted_at':
          aVal = a.submitted_at || '';
          bVal = b.submitted_at || '';
          break;
        case 'course_number':
          aVal = a.course_number || '';
          bVal = b.course_number || '';
          break;
        case 'instructor_name':
          aVal = a.instructor_name || '';
          bVal = b.instructor_name || '';
          break;
        default:
          return 0;
      }

      let comparison;
      if (aVal < bVal) {
        comparison = -1;
      } else if (aVal > bVal) {
        comparison = 1;
      } else {
        comparison = 0;
      }
      return order === 'asc' ? comparison : -comparison;
    });

    return clos;
  }

  /**
   * Show CLO details in modal
   */
  window.showCLODetails = async function (cloId) {
    try {
      const response = await fetch(`/api/outcomes/${cloId}/audit-details`);
      if (!response.ok) {
        throw new Error('Failed to load CLO details');
      }

      const data = await response.json();
      window.currentCLO = data.outcome;

      renderCLODetails(window.currentCLO);

      const modal = new bootstrap.Modal(cloDetailModal);
      modal.show();
    } catch (error) {
      alert('Failed to load CLO details: ' + error.message);
    }
  };

  /**
   * Render CLO details in modal
   */
  function renderCLODetails(clo) {
    const assessment = clo.assessment_data || {};
    const assessed = assessment.students_assessed || 0;
    const meeting = assessment.students_meeting_target || 0;
    const percentage = assessed > 0 ? Math.round((meeting / assessed) * 100) : 0;

    const statusBadge = getStatusBadge(clo.status);

    const html = `
            <div class="mb-3">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h6 class="mb-0">Status</h6>
                    ${statusBadge}
                </div>
            </div>
            
            <div class="row mb-3">
                <div class="col-md-6">
                    <strong>Course:</strong> ${escapeHtml(clo.course_number || 'N/A')} - ${escapeHtml(clo.course_title || 'N/A')}
                </div>
                <div class="col-md-6">
                    <strong>CLO Number:</strong> ${escapeHtml(clo.clo_number || 'N/A')}
                </div>
            </div>
            
            <div class="mb-3">
                <strong>Description:</strong>
                <p>${escapeHtml(clo.description)}</p>
            </div>
            
            <div class="row mb-3">
                <div class="col-md-6">
                    <strong>Instructor:</strong> ${escapeHtml(clo.instructor_name || 'N/A')}
                </div>
                <div class="col-md-6">
                    <strong>Instructor Email:</strong> ${escapeHtml(clo.instructor_email || 'N/A')}
                </div>
            </div>
            
            <hr>
            
            <h6 class="mb-3">Assessment Data</h6>
            <div class="row mb-3">
                <div class="col-md-4">
                    <div class="text-center p-3 bg-light rounded">
                        <h4 class="mb-0">${assessed}</h4>
                        <small class="text-muted">Students Assessed</small>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="text-center p-3 bg-light rounded">
                        <h4 class="mb-0">${meeting}</h4>
                        <small class="text-muted">Meeting Target</small>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="text-center p-3 bg-light rounded">
                        <h4 class="mb-0">${percentage}%</h4>
                        <small class="text-muted">Success Rate</small>
                    </div>
                </div>
            </div>
            
            ${
              clo.narrative
                ? `
                <div class="mb-3">
                    <strong>Narrative:</strong>
                    <p class="text-muted">${escapeHtml(clo.narrative)}</p>
                </div>
            `
                : ''
            }
            
            <hr>
            
            <div class="row mb-3">
                <div class="col-md-6">
                    <strong>Submitted By:</strong> ${escapeHtml(clo.submitted_by_user_id || 'N/A')}<br>
                    <strong>Submitted At:</strong> ${clo.submitted_at ? formatDate(clo.submitted_at) : 'N/A'}
                </div>
                <div class="col-md-6">
                    ${
                      clo.reviewed_by_user_id
                        ? `
                        <strong>Reviewed By:</strong> ${escapeHtml(clo.reviewed_by_user_id)}<br>
                        <strong>Reviewed At:</strong> ${formatDate(clo.reviewed_at)}
                    `
                        : ''
                    }
                </div>
            </div>
            
            ${
              clo.feedback_comments
                ? `
                <div class="alert alert-warning">
                    <strong>Previous Feedback:</strong>
                    <p class="mb-0">${escapeHtml(clo.feedback_comments)}</p>
                    <small class="text-muted">Provided: ${formatDate(clo.feedback_provided_at)}</small>
                </div>
            `
                : ''
            }
        `;

    document.getElementById('cloDetailContent').innerHTML = html;

    // Show/hide action buttons based on status
    const canApprove = ['awaiting_approval', 'approval_pending'].includes(clo.status);
    const canMarkNCI = [
      'awaiting_approval',
      'approval_pending',
      'assigned',
      'in_progress'
    ].includes(clo.status);
    document.getElementById('approveBtn').style.display = canApprove ? 'inline-block' : 'none';
    document.getElementById('requestReworkBtn').style.display = canApprove
      ? 'inline-block'
      : 'none';
    document.getElementById('markNCIBtn').style.display = canMarkNCI ? 'inline-block' : 'none';
  }

  /**
   * Open rework modal
   */
  window.openReworkModal = function () {
    if (!window.currentCLO) return;

    document.getElementById('reworkCloDescription').textContent =
      `${window.currentCLO.course_number} - CLO ${window.currentCLO.clo_number}: ${window.currentCLO.description}`;
    document.getElementById('feedbackComments').value = '';
    document.getElementById('sendEmailCheckbox').checked = true;

    // Hide detail modal
    const detailModalInstance = bootstrap.Modal.getInstance(cloDetailModal);
    if (detailModalInstance) {
      detailModalInstance.hide();
    }

    // Show rework modal
    const modal = new bootstrap.Modal(requestReworkModal);
    modal.show();
  };

  /**
   * Submit rework request
   */
  async function submitReworkRequest() {
    if (!window.currentCLO) return;

    const comments = document.getElementById('feedbackComments').value.trim();
    const sendEmail = document.getElementById('sendEmailCheckbox').checked;

    if (!comments) {
      alert('Please provide feedback comments');
      return;
    }

    const outcomeId = window.currentCLO.outcome_id;
    if (!outcomeId) {
      alert('Error: CLO ID not found');
      return;
    }

    try {
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      const response = await fetch(`/api/outcomes/${outcomeId}/request-rework`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken
        },
        body: JSON.stringify({
          comments,
          send_email: sendEmail
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to request rework');
      }

      // Close modal
      const modal = bootstrap.Modal.getInstance(requestReworkModal);
      modal.hide();

      // Show success
      alert('Rework request sent successfully!' + (sendEmail ? ' Email notification sent.' : ''));

      // Reload list
      await loadCLOs();
    } catch (error) {
      alert('Failed to request rework: ' + error.message);
    }
  }
});

// Export for testing (Node.js environment only)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    getStatusBadge,
    formatDate,
    truncateText,
    escapeHtml,
    approveCLO,
    markAsNCI
  };
}
