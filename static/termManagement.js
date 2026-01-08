/**
 * Term Management UI - Create, Edit, Delete Terms
 *
 * Handles:
 * - Create term form submission
 * - Edit term form submission
 * - Delete term confirmation
 * - API communication with CSRF protection
 */

let currentTerms = []; // Global state to store terms for edit access

const TERM_STATUS_BADGE_MAP = {
  ACTIVE: { label: "Active", className: "bg-success" },
  SCHEDULED: { label: "Scheduled", className: "bg-info text-dark" },
  PASSED: { label: "Passed", className: "bg-secondary" },
  UNKNOWN: { label: "Unknown", className: "bg-dark" },
};

function renderTermStatusBadge(status) {
  const normalized = (status || "UNKNOWN").toUpperCase();
  const config =
    TERM_STATUS_BADGE_MAP[normalized] || TERM_STATUS_BADGE_MAP.UNKNOWN;
  return `<span class="badge ${config.className}">${config.label}</span>`;
}

function publishTermMutation(action, metadata = {}) {
  globalThis.DashboardEvents?.publishMutation({
    entity: "terms",
    action,
    metadata,
    source: "termManagement",
  });
}

async function refreshTermsTableIfPresent() {
  const container = document.getElementById("termsTableContainer");
  if (!container) {
    return false;
  }

  await renderTermsTable();
  return true;
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  initializeCreateTermModal();
  initializeEditTermModal();
});

/**
 * Validate term dates
 * Enforces sane date logic:
 * - End > Start
 * - Due > Start
 * - Warnings for short/long terms or distant due dates
 */
function validateTermDates(start, end, due) {
  if (!start || !end) return true; // Let required field check handle empty

  const parsed = parseTermDates(start, end, due);

  const errorMessage = getTermDateErrorMessage(parsed);
  if (errorMessage) {
    alert(errorMessage);
    return false;
  }

  const warningMessage = getTermDateWarningMessage(parsed);
  if (warningMessage && !confirm(warningMessage)) {
    return false;
  }

  return true;
}

function parseTermDates(start, end, due) {
  const startDate = new Date(start);
  const endDate = new Date(end);
  const dueDate = due ? new Date(due) : null;
  return { startDate, endDate, dueDate };
}

function getTermDateErrorMessage({ startDate, endDate, dueDate }) {
  if (endDate <= startDate) {
    return "End date must be after start date.";
  }
  if (dueDate && dueDate <= startDate) {
    return "Assessment due date must be after start date.";
  }
  return null;
}

function getTermDateWarningMessage({ startDate, endDate, dueDate }) {
  const oneDay = 24 * 60 * 60 * 1000;
  const durationDays = Math.round((endDate - startDate) / oneDay);

  if (durationDays < 10) {
    return `Term duration is very short (${durationDays} days). Is this correct?`;
  }

  if (durationDays > 365) {
    return `Term duration is very long (${durationDays} days). Is this correct?`;
  }

  if (!dueDate) {
    return null;
  }

  const daysAfterEnd = Math.round((dueDate - endDate) / oneDay);
  if (daysAfterEnd > 30) {
    return `Assessment due date is more than a month (${daysAfterEnd} days) after the term ends. Is this correct?`;
  }

  return null;
}

/**
 * Initialize Create Term Modal
 * Sets up form submission for new terms
 */
function initializeCreateTermModal() {
  const form = document.getElementById("createTermForm");

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = document.getElementById("termName").value;
    const startDate = document.getElementById("termStartDate").value;
    const endDate = document.getElementById("termEndDate").value;
    const assessmentDueDate =
      document.getElementById("termAssessmentDueDate")?.value || "";

    // Validate dates
    if (!validateTermDates(startDate, endDate, assessmentDueDate)) {
      return;
    }

    const termData = {
      name,
      term_name: name,
      start_date: startDate,
      end_date: endDate,
    };

    // Only include assessment_due_date if provided
    if (assessmentDueDate) {
      termData.assessment_due_date = assessmentDueDate;
    }

    const createBtn = document.getElementById("createTermBtn");
    const btnText = createBtn.querySelector(".btn-text");
    const btnSpinner = createBtn.querySelector(".btn-spinner");

    // Show loading state
    btnText.classList.add("d-none");
    btnSpinner.classList.remove("d-none");
    createBtn.disabled = true;

    try {
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      const response = await fetch("/api/terms", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(csrfToken && { "X-CSRFToken": csrfToken }),
        },
        body: JSON.stringify(termData),
      });

      if (response.ok) {
        const result = await response.json();

        // Success - close modal and reset form
        const modal = bootstrap.Modal.getInstance(
          document.getElementById("createTermModal"),
        );
        if (modal) {
          modal.hide();
        }

        form.reset();

        alert(result.message || "Term created successfully!");

        await refreshTermsTableIfPresent();
        publishTermMutation("create", { termId: result.term_id });
      } else {
        const error = await response.json();
        alert(`Failed to create term: ${error.error || "Unknown error"}`);
      }
    } catch (error) {
      console.error("Error creating term:", error); // eslint-disable-line no-console
      alert(
        "Failed to create term. Please check your connection and try again.",
      );
    } finally {
      // Restore button state
      btnText.classList.remove("d-none");
      btnSpinner.classList.add("d-none");
      createBtn.disabled = false;
    }
  });
}

/**
 * Initialize Edit Term Modal
 * Sets up form submission for updating terms
 */
function initializeEditTermModal() {
  const form = document.getElementById("editTermForm");

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const termId = document.getElementById("editTermId").value;
    const name = document.getElementById("editTermName").value;
    const startDate = document.getElementById("editTermStartDate").value;
    const endDate = document.getElementById("editTermEndDate").value;
    const assessmentDueDate =
      document.getElementById("editTermAssessmentDueDate")?.value || "";

    // Validate dates
    if (!validateTermDates(startDate, endDate, assessmentDueDate)) {
      return;
    }

    const updateData = {
      name,
      term_name: name,
      start_date: startDate,
      end_date: endDate,
    };

    // Only include assessment_due_date if provided
    if (assessmentDueDate) {
      updateData.assessment_due_date = assessmentDueDate;
    }

    const saveBtn = this.querySelector('button[type="submit"]');
    const btnText = saveBtn.querySelector(".btn-text");
    const btnSpinner = saveBtn.querySelector(".btn-spinner");

    // Show loading state
    btnText.classList.add("d-none");
    btnSpinner.classList.remove("d-none");
    saveBtn.disabled = true;

    try {
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      const response = await fetch(`/api/terms/${termId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...(csrfToken && { "X-CSRFToken": csrfToken }),
        },
        body: JSON.stringify(updateData),
      });

      if (response.ok) {
        const result = await response.json();

        // Success - close modal
        const modal = bootstrap.Modal.getInstance(
          document.getElementById("editTermModal"),
        );
        if (modal) {
          modal.hide();
        }

        alert(result.message || "Term updated successfully!");

        // Reload terms list
        await refreshTermsTableIfPresent();
        publishTermMutation("update", { termId });
      } else {
        const error = await response.json();
        alert(`Failed to update term: ${error.error || "Unknown error"}`);
      }
    } catch (error) {
      console.error("Error updating term:", error); // eslint-disable-line no-console
      alert(
        "Failed to update term. Please check your connection and try again.",
      );
    } finally {
      // Restore button state
      btnText.classList.remove("d-none");
      btnSpinner.classList.add("d-none");
      saveBtn.disabled = false;
    }
  });
}

/**
 * Open Edit Term Modal with pre-populated data
 * Called from term list when Edit button is clicked
 * Uses global currentTerms array to avoid passing JSON in HTML
 */
function openEditTermModal(termId, termDataOverride) {
  // Use override if provided (for tests), otherwise find in currentTerms
  const termData =
    termDataOverride ||
    currentTerms.find((t) => (t.term_id || t.id) === termId);

  if (!termData) {
    console.error("Term not found:", termId); // eslint-disable-line no-console
    return;
  }

  document.getElementById("editTermId").value = termId;
  document.getElementById("editTermName").value =
    termData.term_name || termData.name || "";
  document.getElementById("editTermStartDate").value =
    termData.start_date || "";
  document.getElementById("editTermEndDate").value = termData.end_date || "";

  const dueDateInput = document.getElementById("editTermAssessmentDueDate");
  if (dueDateInput) {
    dueDateInput.value = termData.assessment_due_date || "";
  }

  const modal = new bootstrap.Modal(document.getElementById("editTermModal"));
  modal.show();
}

/**
 * Delete term with confirmation
 * Shows confirmation dialog before deleting
 */
async function deleteTerm(termId, termName) {
  const confirmation = confirm(
    `Are you sure you want to delete "${termName}"?\n\n` +
      "This action cannot be undone. All course offerings in this term will be deleted.",
  );

  if (!confirmation) {
    return;
  }

  try {
    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]',
    )?.content;

    const response = await fetch(`/api/terms/${termId}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken && { "X-CSRFToken": csrfToken }),
      },
    });

    if (response.ok) {
      alert(`${termName} deleted successfully.`);

      await refreshTermsTableIfPresent();
      publishTermMutation("delete", { termId });
    } else {
      const error = await response.json();
      alert(`Failed to delete term: ${error.error || "Unknown error"}`);
    }
  } catch (error) {
    console.error("Error deleting term:", error); // eslint-disable-line no-console
    alert("Failed to delete term. Please try again.");
  }
}

/**
 * Load and display all terms in a table
 */
async function renderTermsTable() {
  const container = document.getElementById("termsTableContainer");
  if (!container) {
    return;
  }
  // nosemgrep
  container.innerHTML = `
    <output class="d-flex justify-content-center align-items-center" style="min-height: 200px;" aria-live="polite">
      <div class="spinner-border" aria-hidden="true">
        <span class="visually-hidden">Loading terms...</span>
      </div>
    </output>
  `;

  try {
    const response = await fetch(`/api/terms?all=true&t=${Date.now()}`, {
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new Error("Failed to load terms");
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || "Failed to load terms");
    }

    // Update global state
    currentTerms = data.terms || [];

    if (currentTerms.length === 0) {
      // nosemgrep
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

    currentTerms.forEach((term) => {
      const statusValue = (
        term.status || (term.active ? "ACTIVE" : "UNKNOWN")
      ).toUpperCase();
      const statusBadge = renderTermStatusBadge(statusValue);
      const offeringsCount = term.offerings_count || 0;
      const termId = term.term_id || term.id;
      const termName = escapeHtml(term.term_name || term.name || "-");

      // Note: passing just the ID to openEditTermModal now
      html += `
        <tr>
          <td><strong>${termName}</strong></td>
          <td>${formatDate(term.start_date)}</td>
          <td>${formatDate(term.end_date)}</td>
          <td>${statusBadge}</td>
          <td>${offeringsCount}</td>
          <td>
            <button class="btn btn-sm btn-outline-secondary" onclick='openEditTermModal("${termId}")'>
              <i class="fas fa-edit"></i> Edit
            </button>
            <button class="btn btn-sm btn-outline-danger mt-1 mt-lg-0" onclick='deleteTerm("${termId}", "${termName.replace(/'/g, "\\'")}")'>
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

    container.innerHTML = html; // nosemgrep
  } catch (error) {
    console.error("Error loading terms:", error); // eslint-disable-line no-console
    // nosemgrep
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
  const modal = new bootstrap.Modal(document.getElementById("createTermModal"));
  modal.show();
}

/**
 * Format date for display
 */
function formatDate(dateString) {
  if (!dateString) return "-";
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateString;
  }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Expose functions to window for inline onclick handlers and testing
globalThis.openEditTermModal = openEditTermModal;
globalThis.deleteTerm = deleteTerm;
globalThis.openCreateTermModal = openCreateTermModal;

// Smart loadTerms wrapper: use dashboard refresh if available, otherwise table loader
// This prevents clobbering the dashboard's refresh function
if (!globalThis.loadTerms) {
  // No existing loadTerms function - use our table loader
  globalThis.loadTerms = renderTermsTable;
} else {
  // Dashboard or other page already set up loadTerms - preserve it
  // Store our table loader under a different name for direct access if needed
  globalThis.loadTermsTable = renderTermsTable;
}
