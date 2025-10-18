/**
 * Bulk Instructor Reminders
 *
 * Handles sending reminder emails to multiple instructors with
 * real-time progress tracking, rate limiting, and job status monitoring.
 *
 * @class BulkReminderManager
 *
 * @example
 * // Initialize on page load
 * const manager = new BulkReminderManager();
 * manager.init();
 *
 * // Open modal from button
 * openBulkReminderModal();
 *
 * @property {bootstrap.Modal|null} modal - Bootstrap modal instance
 * @property {Set<string>} selectedInstructors - Set of selected instructor IDs
 * @property {Array<Object>} allInstructors - Array of all available instructors
 * @property {string|null} currentJobId - ID of currently running job
 * @property {number|null} pollingInterval - Interval ID for status polling
 * @property {number} pollingIntervalMs - Polling interval in milliseconds (2000ms)
 */

class BulkReminderManager {
  constructor() {
    this.modal = null;
    this.selectedInstructors = new Set();
    this.allInstructors = [];
    this.currentJobId = null;
    this.pollingInterval = null;
    this.pollingIntervalMs = 2000; // Poll every 2 seconds
  }

  /**
   * Initialize the bulk reminder system
   * Sets up modal instance and event listeners
   *
   * @returns {void}
   */
  init() {
    // Get modal instance
    const modalEl = document.getElementById('bulkReminderModal');
    if (!modalEl) {
      // eslint-disable-next-line no-console
      console.error('[BulkReminders] Modal not found');
      return;
    }
    this.modal = new bootstrap.Modal(modalEl);

    // Set up event listeners
    this.setupEventListeners();

    // eslint-disable-next-line no-console
    console.log('[BulkReminders] Initialized');
  }

  /**
   * Set up all event listeners
   * Attaches handlers for buttons, modal events, and user input
   *
   * @returns {void}
   */
  setupEventListeners() {
    // Select All / Deselect All
    document.getElementById('selectAllInstructors')?.addEventListener('click', () => {
      this.selectAll();
    });

    document.getElementById('deselectAllInstructors')?.addEventListener('click', () => {
      this.deselectAll();
    });

    // Send Reminders button
    document.getElementById('sendRemindersButton')?.addEventListener('click', () => {
      this.sendReminders();
    });

    // Close button after completion
    document.getElementById('closeProgressButton')?.addEventListener('click', () => {
      this.closeModal();
    });

    // Character count for message
    document.getElementById('reminderMessage')?.addEventListener('input', e => {
      const count = e.target.value.length;
      document.getElementById('messageCharCount').textContent = count;
    });

    // Modal shown event - load instructors
    document.getElementById('bulkReminderModal')?.addEventListener('shown.bs.modal', () => {
      this.loadInstructors();
    });

    // Modal hidden event - reset state
    document.getElementById('bulkReminderModal')?.addEventListener('hidden.bs.modal', () => {
      this.resetModal();
    });
  }

  /**
   * Show the reminder modal
   *
   * @returns {void}
   */
  show() {
    if (this.modal) {
      this.modal.show();
    }
  }

  /**
   * Close the modal
   */
  closeModal() {
    if (this.modal) {
      this.modal.hide();
    }
  }

  /**
   * Load instructors for the current context
   */
  async loadInstructors() {
    const container = document.getElementById('instructorListContainer');
    if (!container) return;

    container.innerHTML = `
            <div class="text-center text-muted py-4">
                <div class="spinner-border spinner-border-sm me-2"></div>
                Loading instructors...
            </div>
        `;

    try {
      const instructors = await this.fetchInstructors();

      this.allInstructors = instructors;
      this.renderInstructorList(instructors);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('[BulkReminders] Error loading instructors:', error);
      container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Failed to load instructors. Please try again.
                </div>
            `;
    }
  }

  /**
   * Fetch instructors from the API
   * Calls GET /api/instructors and transforms response
   *
   * @returns {Promise<Array<{id: string, name: string, email: string, courses: Array}>>}
   * @throws {Error} If API request fails or returns error
   */
  async fetchInstructors() {
    const response = await fetch('/api/instructors');

    if (!response.ok) {
      throw new Error(`Failed to fetch instructors: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to fetch instructors');
    }

    // Transform API response to expected format
    // API returns: { success: true, instructors: [...], count: N }
    // Each instructor has: user_id, first_name, last_name, email, role, etc.
    return data.instructors.map(instructor => ({
      id: instructor.user_id,
      name:
        `${instructor.first_name || ''} ${instructor.last_name || ''}`.trim() || instructor.email,
      email: instructor.email,
      courses: [] // TODO: Add course assignment data when available
    }));
  }

  /**
   * Render the instructor list with checkboxes
   */
  renderInstructorList(instructors) {
    const container = document.getElementById('instructorListContainer');
    if (!container) return;

    if (instructors.length === 0) {
      container.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-users-slash fs-3 mb-2"></i>
                    <div>No instructors found</div>
                </div>
            `;
      return;
    }

    const html = instructors
      .map(
        instructor => `
            <div class="form-check mb-2">
                <input class="form-check-input instructor-checkbox" 
                       type="checkbox" 
                       value="${instructor.id}" 
                       id="instructor-${instructor.id}"
                       data-name="${instructor.name}"
                       data-email="${instructor.email}">
                <label class="form-check-label w-100" for="instructor-${instructor.id}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <strong>${instructor.name}</strong>
                            <br>
                            <small class="text-muted">${instructor.email}</small>
                        </div>
                        <div class="text-end">
                            <small class="text-muted">${instructor.courses.join(', ')}</small>
                        </div>
                    </div>
                </label>
            </div>
        `
      )
      .join('');

    container.innerHTML = html;

    // Add change listeners to checkboxes
    container.querySelectorAll('.instructor-checkbox').forEach(checkbox => {
      checkbox.addEventListener('change', () => {
        this.updateSelection();
      });
    });
  }

  /**
   * Update selection state when checkboxes change
   */
  updateSelection() {
    this.selectedInstructors.clear();

    document.querySelectorAll('.instructor-checkbox:checked').forEach(checkbox => {
      this.selectedInstructors.add(checkbox.value);
    });

    // Update UI
    const count = this.selectedInstructors.size;
    document.getElementById('selectedInstructorCount').textContent = count;
    document.getElementById('sendRemindersButton').disabled = count === 0;
  }

  /**
   * Select all instructors
   */
  selectAll() {
    document.querySelectorAll('.instructor-checkbox').forEach(checkbox => {
      checkbox.checked = true;
    });
    this.updateSelection();
  }

  /**
   * Deselect all instructors
   */
  deselectAll() {
    document.querySelectorAll('.instructor-checkbox').forEach(checkbox => {
      checkbox.checked = false;
    });
    this.updateSelection();
  }

  /**
   * Send reminders to selected instructors
   * Posts to API, switches to progress view, and starts polling
   *
   * @returns {Promise<void>}
   * @throws {Error} If API request fails
   */
  async sendReminders() {
    if (this.selectedInstructors.size === 0) {
      return;
    }

    // Get optional fields
    const term = document.getElementById('reminderTerm').value.trim();
    const deadline = document.getElementById('reminderDeadline').value;
    const personalMessage = document.getElementById('reminderMessage').value.trim();

    // Build request
    const requestData = {
      instructor_ids: Array.from(this.selectedInstructors),
      personal_message: personalMessage || null,
      term: term || null,
      deadline: deadline || null
    };

    try {
      // Switch to progress view
      this.showProgressView();

      // Send request to API
      const response = await fetch('/api/bulk-email/send-instructor-reminders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to start bulk reminder job');
      }

      // Start polling for progress
      this.currentJobId = data.job_id;
      this.addStatusMessage(`Job started: ${data.job_id}`, 'info');
      this.addStatusMessage(`Sending to ${data.recipient_count} instructor(s)`, 'info');

      this.startPolling();
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('[BulkReminders] Error sending reminders:', error);
      this.addStatusMessage(`Error: ${error.message}`, 'danger');

      // Show error and allow closing
      document.getElementById('closeProgressButton').disabled = false;
    }
  }

  /**
   * Switch from selection view to progress view
   */
  showProgressView() {
    document.getElementById('reminderStep1').style.display = 'none';
    document.getElementById('reminderFooter1').style.display = 'none';
    document.getElementById('reminderStep2').style.display = 'block';
    document.getElementById('reminderFooter2').style.display = 'block';
  }

  /**
   * Start polling for job status
   */
  startPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
    }

    this.pollingInterval = setInterval(() => {
      this.checkJobStatus();
    }, this.pollingIntervalMs);

    // Check immediately
    this.checkJobStatus();
  }

  /**
   * Stop polling for job status
   */
  stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  }

  /**
   * Check current job status
   */
  async checkJobStatus() {
    if (!this.currentJobId) return;

    try {
      const response = await fetch(`/api/bulk-email/job-status/${this.currentJobId}`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to get job status');
      }

      this.updateProgress(data.job);

      // Stop polling if job is complete or failed
      if (['completed', 'failed', 'cancelled'].includes(data.job.status)) {
        this.stopPolling();
        this.showCompletion(data.job);
      }
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('[BulkReminders] Error checking job status:', error);
      this.stopPolling();
      this.addStatusMessage(`Error checking status: ${error.message}`, 'danger');
      document.getElementById('closeProgressButton').disabled = false;
    }
  }

  /**
   * Update progress display
   */
  updateProgress(job) {
    // Update progress bar
    const percentage = job.progress_percentage || 0;
    const progressBar = document.getElementById('reminderProgressBar');
    const progressText = document.getElementById('reminderProgressText');

    if (progressBar && progressText) {
      progressBar.style.width = `${percentage}%`;
      progressBar.setAttribute('aria-valuenow', percentage);
      progressText.textContent = `${percentage}%`;
    }

    // Update counts
    document.getElementById('reminderSentCount').textContent = job.emails_sent || 0;
    document.getElementById('reminderFailedCount').textContent = job.emails_failed || 0;
    document.getElementById('reminderPendingCount').textContent = job.emails_pending || 0;

    // Add status message
    if (job.emails_sent > 0) {
      const lastMessage =
        document.querySelector('#reminderStatusMessages div:last-child')?.textContent || '';
      const newMessage = `Sent ${job.emails_sent}/${job.recipient_count} reminders...`;
      if (!lastMessage.includes(newMessage)) {
        this.addStatusMessage(newMessage, 'success');
      }
    }

    // Show failed recipients if any
    if (job.failed_recipients && job.failed_recipients.length > 0) {
      this.showFailedRecipients(job.failed_recipients);
    }
  }

  /**
   * Show completion message
   */
  showCompletion(job) {
    // Update progress bar to 100%
    const progressBar = document.getElementById('reminderProgressBar');
    if (progressBar) {
      progressBar.classList.remove('progress-bar-animated');
      if (job.status === 'completed') {
        progressBar.classList.add('bg-success');
      } else if (job.status === 'failed') {
        progressBar.classList.add('bg-danger');
      }
    }

    // Show completion message
    const completeDiv = document.getElementById('reminderComplete');
    if (completeDiv) {
      if (job.status === 'completed') {
        completeDiv.className = 'mt-3 alert alert-success';
        completeDiv.innerHTML = `
                    <i class="fas fa-check-circle me-2"></i>
                    <strong>Complete!</strong> Successfully sent ${job.emails_sent} reminder(s).
                    ${job.emails_failed > 0 ? `<br><small>${job.emails_failed} email(s) failed to send.</small>` : ''}
                `;
      } else if (job.status === 'failed') {
        completeDiv.className = 'mt-3 alert alert-danger';
        completeDiv.innerHTML = `
                    <i class="fas fa-exclamation-circle me-2"></i>
                    <strong>Failed!</strong> ${job.error_message || 'Job failed to complete.'}
                `;
      }
      completeDiv.style.display = 'block';
    }

    // Enable close button
    document.getElementById('closeProgressButton').disabled = false;

    // Add final status message
    this.addStatusMessage(`Job ${job.status}`, job.status === 'completed' ? 'success' : 'danger');
  }

  /**
   * Show failed recipients
   */
  showFailedRecipients(failedRecipients) {
    const container = document.getElementById('reminderFailedRecipients');
    const list = document.getElementById('reminderFailedList');

    if (!container || !list) return;

    const html = failedRecipients
      .map(
        recipient => `
            <div class="mb-1">
                <strong>${recipient.name || recipient.email}</strong>: ${recipient.error || 'Unknown error'}
            </div>
        `
      )
      .join('');

    list.innerHTML = html;
    container.style.display = 'block';
  }

  /**
   * Add a status message to the log
   * Displays timestamped message with appropriate icon and color
   *
   * @param {string} message - Message text to display
   * @param {string} [type='info'] - Message type: 'info', 'success', 'warning', 'danger'
   * @returns {void}
   */
  addStatusMessage(message, type = 'info') {
    const container = document.getElementById('reminderStatusMessages');
    if (!container) return;

    const icon =
      {
        info: 'fa-info-circle',
        success: 'fa-check-circle',
        warning: 'fa-exclamation-triangle',
        danger: 'fa-times-circle'
      }[type] || 'fa-info-circle';

    const color =
      {
        info: 'text-muted',
        success: 'text-success',
        warning: 'text-warning',
        danger: 'text-danger'
      }[type] || 'text-muted';

    const timestamp = new Date().toLocaleTimeString();
    const messageDiv = document.createElement('div');
    messageDiv.className = `small ${color} mb-1`;
    messageDiv.innerHTML = `
            <i class="fas ${icon} me-1"></i>
            [${timestamp}] ${message}
        `;

    container.appendChild(messageDiv);

    // Auto-scroll to bottom
    container.scrollTop = container.scrollHeight;

    // Limit to last 50 messages
    while (container.children.length > 50) {
      container.firstChild.remove();
    }
  }

  /**
   * Reset modal to initial state
   * Clears all selections, stops polling, and resets UI elements
   *
   * @returns {void}
   */
  resetModal() {
    // Stop any active polling
    this.stopPolling();

    // Clear selections
    this.selectedInstructors.clear();
    this.allInstructors = [];
    this.currentJobId = null;

    // Reset UI
    document.getElementById('selectedInstructorCount').textContent = '0';
    document.getElementById('sendRemindersButton').disabled = true;

    // Clear form fields
    document.getElementById('reminderTerm').value = '';
    document.getElementById('reminderDeadline').value = '';
    document.getElementById('reminderMessage').value = '';
    document.getElementById('messageCharCount').textContent = '0';

    // Reset progress view
    document.getElementById('reminderProgressBar').style.width = '0%';
    document.getElementById('reminderProgressText').textContent = '0%';
    document.getElementById('reminderSentCount').textContent = '0';
    document.getElementById('reminderFailedCount').textContent = '0';
    document.getElementById('reminderPendingCount').textContent = '0';
    document.getElementById('reminderStatusMessages').innerHTML = '';
    document.getElementById('reminderComplete').style.display = 'none';
    document.getElementById('reminderFailedRecipients').style.display = 'none';

    // Reset progress bar classes
    const progressBar = document.getElementById('reminderProgressBar');
    if (progressBar) {
      progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated';
    }

    // Show selection view, hide progress view
    document.getElementById('reminderStep1').style.display = 'block';
    document.getElementById('reminderFooter1').style.display = 'block';
    document.getElementById('reminderStep2').style.display = 'none';
    document.getElementById('reminderFooter2').style.display = 'none';
    document.getElementById('closeProgressButton').disabled = true;
  }
}

// Global instance
let bulkReminderManager = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  bulkReminderManager = new BulkReminderManager();
  bulkReminderManager.init();
});

// Global function to open the modal (called from dashboard buttons)
// eslint-disable-next-line no-unused-vars
function openBulkReminderModal() {
  // In test environment, check global first
  const manager =
    // eslint-disable-next-line no-undef
    (typeof global !== 'undefined' && global.bulkReminderManager) || bulkReminderManager;
  if (manager) {
    manager.show();
  } else {
    // eslint-disable-next-line no-console
    console.error('[BulkReminders] Manager not initialized');
  }
}

// Export for testing (Node.js environment)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { BulkReminderManager, openBulkReminderModal };
}
