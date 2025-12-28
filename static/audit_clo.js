/**
 * Get status badge HTML with color-coded scheme:
 * Unassigned=grey, Assigned=black, In Progress=blue,
 * Needs Rework=orange, Awaiting Approval=yellow-green, Approved=green, NCI=red
 */
function getStatusBadge(status) {
  const badges = {
    unassigned: '<span class="badge" style="background-color: #6c757d;">Unassigned</span>',
    assigned: '<span class="badge" style="background-color: #212529;">Assigned</span>',
    in_progress: '<span class="badge" style="background-color: #0d6efd;">In Progress</span>',
    awaiting_approval:
      '<span class="badge" style="background-color: #9acd32;">Awaiting Approval</span>',
    approval_pending: '<span class="badge" style="background-color: #fd7e14;">Needs Rework</span>',
    approved: '<span class="badge" style="background-color: #198754;">✓ Approved</span>',
    never_coming_in: '<span class="badge" style="background-color: #dc3545;">NCI</span>'
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
 * Format status for CSV export (plain text)
 */
function formatStatusLabel(status) {
  const labels = {
    unassigned: 'Unassigned',
    assigned: 'Assigned',
    in_progress: 'In Progress',
    awaiting_approval: 'Awaiting Approval',
    approval_pending: 'Needs Rework',
    approved: 'Approved',
    never_coming_in: 'Never Coming In'
  };
  return labels[status] || status || '';
}

/**
 * Format date for CSV export (ISO string)
 */
function formatDateForCsv(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  return date.toISOString();
}

/**
 * Escape CSV value
 */
function escapeForCsv(value) {
  if (value === null || value === undefined) {
    return '""';
  }
  const text = String(value);
  return `"${text.replace(/"/g, '""')}"`;
}

/**
 * Calculate success rate based on students took/passed
 */
function calculateSuccessRate(clo) {
  const took = typeof clo.students_took === 'number' ? clo.students_took : null;
  const passed = typeof clo.students_passed === 'number' ? clo.students_passed : null;
  if (!took || took <= 0 || passed === null || passed === undefined) {
    return null;
  }
  return Math.round((passed / took) * 100);
}

/**
 * Export current CLO list to CSV
 */
function exportCurrentViewToCsv(cloList) {
  if (!Array.isArray(cloList) || cloList.length === 0) {
    alert('No CLO records available to export for the selected filters.');
    return false;
  }

  const headers = [
    'Course',
    'CLO Number',
    'Status',
    'Instructor',
    'Submitted At',
    'Students Took',
    'Students Passed',
    'Success Rate (%)',
    'Term',
    'Assessment Tool'
  ];

  const rows = cloList.map(clo => [
    [clo.course_number || '', clo.course_title || ''].filter(Boolean).join(' - '),
    clo.clo_number || '',
    formatStatusLabel(clo.status),
    clo.instructor_name || '',
    formatDateForCsv(clo.submitted_at),
    clo.students_took ?? '',
    clo.students_passed ?? '',
    calculateSuccessRate(clo),
    clo.term_name || '',
    clo.assessment_tool || ''
  ]);

  const csvLines = [
    headers.map(escapeForCsv).join(','),
    ...rows.map(row => row.map(escapeForCsv).join(','))
  ];
  const csvContent = csvLines.join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `clo_audit_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  return true;
}

/**
 * Approve CLO (extracted for testability)
 */
async function approveCLO() {
  if (!globalThis.currentCLO) return;

  if (
    !confirm(
      `Approve this CLO?\n\n${globalThis.currentCLO.course_number} - CLO ${globalThis.currentCLO.clo_number}`
    )
  ) {
    return;
  }

  const outcomeId = globalThis.currentCLO.outcome_id;
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
    await globalThis.loadCLOs();
  } catch (error) {
    alert('Failed to approve CLO: ' + error.message);
  }
}

/**
 * Mark CLO as Never Coming In (NCI) (extracted for testability)
 */
async function markAsNCI() {
  if (!globalThis.currentCLO) return;

  const reason = prompt(
    `Mark this CLO as "Never Coming In"?\n\n${globalThis.currentCLO.course_number} - CLO ${globalThis.currentCLO.clo_number}\n\nOptional: Provide a reason (e.g., "Instructor left institution", "Non-responsive instructor"):`
  );

  // null means cancelled, empty string is allowed
  if (reason === null) {
    return;
  }

  try {
    const outcomeId = globalThis.currentCLO.outcome_id;

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
    await globalThis.loadCLOs();
    await globalThis.updateStats();
  } catch (error) {
    alert('Failed to mark CLO as NCI: ' + error.message);
  }
}

/**
 * Render CLO details in modal (extracted for testability)
 */
function renderCLODetails(clo) {
  // Use new field names from CEI demo schema changes
  const studentsTook = clo.students_took || 0;
  const studentsPassed = clo.students_passed || 0;
  const percentage = studentsTook > 0 ? Math.round((studentsPassed / studentsTook) * 100) : 0;

  const statusBadge = getStatusBadge(clo.status);

  return `
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

        <div class="row mb-3">
            <div class="col-md-6">
                <strong>Term:</strong> ${escapeHtml(clo.term_name || '—')}
            </div>
            <div class="col-md-6">
                <strong>Assessment Tool:</strong> ${escapeHtml(clo.assessment_tool || '—')}
            </div>
        </div>

        <hr>

        <h6 class="mb-3">Assessment Data</h6>
        <div class="row mb-3">
            <div class="col-md-4">
                <div class="text-center p-3 bg-light rounded">
                    <h4 class="mb-0">${studentsTook}</h4>
                    <small class="text-muted">Students Took</small>
                </div>
            </div>
            <div class="col-md-4">
                <div class="text-center p-3 bg-light rounded">
                    <h4 class="mb-0">${studentsPassed}</h4>
                    <small class="text-muted">Students Passed</small>
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

        ${
          clo.feedback_comments
            ? `
            <div class="mb-3">
                <strong>Admin Feedback:</strong>
                <p class="text-muted">${escapeHtml(clo.feedback_comments)}</p>
            </div>
        `
            : ''
        }

        ${
          clo.reviewed_by_name
            ? `
            <div class="mt-3 text-muted small">
                <em>Reviewed by ${escapeHtml(clo.reviewed_by_name)} on ${formatDate(clo.reviewed_at)}</em>
            </div>
        `
            : ''
        }
    `;
}

// Assign to globalThis IMMEDIATELY for browser use (not inside DOMContentLoaded)
// This ensures functions are available even if DOM is already loaded
// Note: globalThis is preferred over window for ES2020 cross-environment compatibility
globalThis.approveCLO = approveCLO;
globalThis.markAsNCI = markAsNCI;

document.addEventListener('DOMContentLoaded', () => {
  // DOM elements
  const statusFilter = document.getElementById('statusFilter');
  const sortBy = document.getElementById('sortBy');
  const sortOrder = document.getElementById('sortOrder');
  const programFilter = document.getElementById('programFilter');
  const termFilter = document.getElementById('termFilter');
  const exportButton = document.getElementById('exportCsvBtn');
  const cloListContainer = document.getElementById('cloListContainer');
  const cloDetailModal = document.getElementById('cloDetailModal');
  const requestReworkModal = document.getElementById('requestReworkModal');
  const requestReworkForm = document.getElementById('requestReworkForm');

  // State - use window for global access by extracted functions
  globalThis.currentCLO = null;
  let allCLOs = [];

  // Expose functions on window for access by extracted functions (approveCLO, markAsNCI)
  globalThis.loadCLOs = loadCLOs;
  globalThis.updateStats = updateStats;

  // Initialize
  initialize();

  // Event listeners
  statusFilter.addEventListener('change', loadCLOs);
  sortBy.addEventListener('change', renderCLOList);
  sortOrder.addEventListener('change', renderCLOList);
  if (programFilter) {
    programFilter.addEventListener('change', loadCLOs);
  }
  if (termFilter) {
    termFilter.addEventListener('change', loadCLOs);
  }
  if (exportButton) {
    exportButton.addEventListener('click', () => {
      exportCurrentViewToCsv(allCLOs);
    });
  }

  // Event delegation for CLO row clicks
  cloListContainer.addEventListener('click', e => {
    const row = e.target.closest('tr[data-outcome-id]');
    if (row && !e.target.closest('.clo-actions')) {
      const outcomeId = row.dataset.outcomeId;
      if (outcomeId) {
        globalThis.showCLODetails(outcomeId);
      }
      return;
    }

    // Handle View button clicks
    const viewBtn = e.target.closest('button[data-outcome-id]');
    if (viewBtn) {
      e.stopPropagation();
      const outcomeId = viewBtn.dataset.outcomeId;
      if (outcomeId) {
        globalThis.showCLODetails(outcomeId);
      }
    }
  });

  requestReworkForm.addEventListener('submit', async e => {
    e.preventDefault();
    await submitReworkRequest();
  });

  /**
   * Initialize filters (programs, terms)
   */
  async function initialize() {
    try {
      // Load programs
      const progResponse = await fetch('/api/programs');
      if (progResponse.ok) {
        const data = await progResponse.json();
        const programs = data.programs || [];
        if (programFilter) {
          programs.forEach(prog => {
            const option = document.createElement('option');
            option.value = prog.program_id || prog.id; // API returns program_id
            option.textContent = prog.name;
            programFilter.appendChild(option);
          });
        }
      }

      // Load terms
      const termResponse = await fetch('/api/terms');
      if (termResponse.ok) {
        const data = await termResponse.json();
        const terms = data.terms || [];
        if (termFilter) {
          // Sort terms by start date descending (newest first)
          terms.sort((a, b) => new Date(b.start_date) - new Date(a.start_date));

          terms.forEach(term => {
            const option = document.createElement('option');
            option.value = term.term_id;
            option.textContent = term.term_name;
            termFilter.appendChild(option);
          });
        }
      }

      // Initial load of CLOs
      await loadCLOs();
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Failed to initialize filters:', error);
      // Fallback to loading CLOs even if filters fail
      await loadCLOs();
    }
  }

  /**
   * Load CLOs from API
   */
  async function loadCLOs() {
    try {
      // nosemgrep
      cloListContainer.innerHTML = `
                <div class="text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="text-muted mt-2">Loading CLOs...</p>
                </div>
            `;

      const status = statusFilter.value;
      const programId = programFilter ? programFilter.value : '';
      const termId = termFilter ? termFilter.value : '';

      const params = new URLSearchParams();
      if (status !== 'all') params.append('status', status);
      if (programId) params.append('program_id', programId);
      if (termId) params.append('term_id', termId);

      const queryString = params.toString();
      const url = queryString ? `/api/outcomes/audit?${queryString}` : '/api/outcomes/audit';

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
      // nosemgrep
      cloListContainer.innerHTML = `
                <div class="alert alert-danger">
                    <strong>Error:</strong> Failed to load CLOs. ${error.message}
                </div>
            `;
    }
  }

  /**
   * Update summary statistics
   * Top stats are UNFILTERED source of truth for the institution (not affected by filter dropdowns)
   */
  async function updateStats() {
    try {
      // Full CLO lifecycle: Unassigned → Assigned → In Progress → Needs Rework → Awaiting Approval → Approved → NCI
      const statuses = [
        'unassigned',
        'assigned',
        'in_progress',
        'approval_pending',
        'awaiting_approval',
        'approved',
        'never_coming_in'
      ];

      // Top stats are UNFILTERED - no program/term filters applied
      // This provides source of truth totals for the institution

      const promises = statuses.map(status => {
        const params = new URLSearchParams();
        params.append('status', status);
        // No filters - these are institution-wide totals

        return fetch(`/api/outcomes/audit?${params.toString()}`)
          .then(r => {
            if (!r.ok) {
              throw new Error(`HTTP ${r.status}: ${r.statusText}`);
            }
            return r.json();
          })
          .then(d => d.count || 0)
          .catch(err => {
            // Return 0 for individual status failures to allow graceful degradation
            // eslint-disable-next-line no-console
            console.warn(`Failed to fetch stats for status ${status}:`, err.message); // nosemgrep
            return 0;
          });
      });

      const [unassigned, assigned, inProgress, pending, awaiting, approved, nci] =
        await Promise.all(promises);

      if (document.getElementById('statUnassigned')) {
        document.getElementById('statUnassigned').textContent = unassigned;
      }
      if (document.getElementById('statAssigned')) {
        document.getElementById('statAssigned').textContent = assigned;
      }
      document.getElementById('statInProgress').textContent = inProgress;
      document.getElementById('statNeedsRework').textContent = pending;
      document.getElementById('statAwaitingApproval').textContent = awaiting;
      document.getElementById('statApproved').textContent = approved;
      if (document.getElementById('statNCI')) {
        document.getElementById('statNCI').textContent = nci;
      }
    } catch (error) {
      // Log error to aid debugging, but allow graceful degradation
      // Stats are nice-to-have, not critical functionality
      // eslint-disable-next-line no-console
      console.warn('Error updating dashboard stats (non-critical):', error.message || error);
    }
  }

  /**
   * Render CLO list
   */
  function renderCLOList() {
    if (allCLOs.length === 0) {
      // nosemgrep
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

    cloListContainer.innerHTML = html; // nosemgrep
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
  globalThis.showCLODetails = async function (cloId) {
    try {
      const response = await fetch(`/api/outcomes/${cloId}/audit-details`);
      if (!response.ok) {
        throw new Error('Failed to load CLO details');
      }

      const data = await response.json();
      globalThis.currentCLO = data.outcome;
      const clo = globalThis.currentCLO;

      // Render HTML using extracted function
      document.getElementById('cloDetailContent').innerHTML = renderCLODetails(clo); // nosemgrep

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

      const modal = new bootstrap.Modal(cloDetailModal);
      modal.show();
    } catch (error) {
      alert('Failed to load CLO details: ' + error.message);
    }
  };

  /**
   * Open rework modal
   */
  globalThis.openReworkModal = function () {
    if (!globalThis.currentCLO) return;

    document.getElementById('reworkCloDescription').textContent =
      `${globalThis.currentCLO.course_number} - CLO ${globalThis.currentCLO.clo_number}: ${globalThis.currentCLO.description}`;
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
    if (!globalThis.currentCLO) return;

    const comments = document.getElementById('feedbackComments').value.trim();
    const sendEmail = document.getElementById('sendEmailCheckbox').checked;

    if (!comments) {
      alert('Please provide feedback comments');
      return;
    }

    const outcomeId = globalThis.currentCLO.outcome_id;
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
    renderCLODetails,
    approveCLO,
    markAsNCI,
    formatStatusLabel,
    formatDateForCsv,
    escapeForCsv,
    calculateSuccessRate,
    exportCurrentViewToCsv
  };
}
