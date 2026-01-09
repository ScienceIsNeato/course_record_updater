/**
 * Course Outcome (CLO) Management UI - Create, Edit, Delete Outcomes
 *
 * Handles:
 * - Create outcome form submission
 * - Edit outcome form submission
 * - Delete outcome confirmation
 * - API communication with CSRF protection
 */

function publishOutcomeMutation(action, metadata = {}) {
  globalThis.DashboardEvents?.publishMutation({
    entity: "outcomes",
    action,
    metadata,
    source: "outcomeManagement",
  });
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  initializeCreateOutcomeModal();
  initializeEditOutcomeModal();
});

/**
 * Initialize Create Outcome Modal
 * Sets up form submission for new outcomes
 */
function initializeCreateOutcomeModal() {
  const form = document.getElementById("createOutcomeForm");

  if (!form) {
    return; // Form not on this page
  }

  // Auto-populate courses when modal opens
  const modalEl = document.getElementById("createOutcomeModal");
  if (modalEl) {
    modalEl.addEventListener("show.bs.modal", async () => {
      const select = document.getElementById("outcomeCourseId");
      // Only load if empty or just has placeholder
      if (select && select.options.length <= 1) {
        try {
          const resp = await fetch("/api/courses");
          if (resp.ok) {
            const data = await resp.json();
            const courses = data.courses || [];
            // sort by name
            courses.sort((a, b) =>
              (a.course_number || "").localeCompare(b.course_number || ""),
            );

            courses.forEach((c) => {
              const opt = document.createElement("option");
              opt.value = c.course_id;
              opt.textContent = `${c.course_number} - ${c.course_title}`;
              select.appendChild(opt);
            });
          }
        } catch (e) {
          console.error("Failed to load courses for dropdown", e);
        }
      }
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const assessmentValue = document.getElementById(
      "outcomeAssessmentMethod",
    ).value;

    const outcomeData = {
      course_id: document.getElementById("outcomeCourseId").value,
      clo_number: document.getElementById("outcomeCloNumber").value,
      description: document.getElementById("outcomeDescription").value,
      assessment_method: assessmentValue || null,
      active: document.getElementById("outcomeActive").checked,
    };

    const createBtn = document.getElementById("createOutcomeBtn");
    const btnText = createBtn.querySelector(".btn-text");
    const btnSpinner = createBtn.querySelector(".btn-spinner");

    // Show loading state
    btnText.classList.add("d-none");
    btnSpinner.classList.remove("d-none");
    createBtn.disabled = true;

    try {
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      const response = await fetch("/api/outcomes", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(csrfToken && { "X-CSRFToken": csrfToken }),
        },
        body: JSON.stringify(outcomeData),
      });

      if (response.ok) {
        const result = await response.json();

        // Success - close modal and reset form
        const modal = bootstrap.Modal.getInstance(
          document.getElementById("createOutcomeModal"),
        );
        if (modal) {
          modal.hide();
        }

        form.reset();

        alert(result.message || "Outcome created successfully!");
        publishOutcomeMutation("create", { outcomeId: result.outcome_id });

        // Reload outcomes list if function exists
        if (typeof globalThis.loadOutcomes === "function") {
          globalThis.loadOutcomes();
        }
      } else {
        const error = await response.json();
        alert(`Failed to create outcome: ${error.error || "Unknown error"}`);
      }
    } catch (error) {
      console.error("Error creating outcome:", error); // eslint-disable-line no-console
      alert(
        "Failed to create outcome. Please check your connection and try again.",
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
 * Initialize Edit Outcome Modal
 * Sets up form submission for updating outcomes
 */
function initializeEditOutcomeModal() {
  const form = document.getElementById("editOutcomeForm");

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const outcomeId = document.getElementById("editOutcomeId").value;
    const assessmentValue = document.getElementById(
      "editOutcomeAssessmentMethod",
    ).value;

    const updateData = {
      clo_number: document.getElementById("editOutcomeCloNumber").value,
      description: document.getElementById("editOutcomeDescription").value,
      assessment_method: assessmentValue || null,
      active: document.getElementById("editOutcomeActive").checked,
    };

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

      const response = await fetch(`/api/outcomes/${outcomeId}`, {
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
          document.getElementById("editOutcomeModal"),
        );
        if (modal) {
          modal.hide();
        }

        alert(result.message || "Outcome updated successfully!");
        publishOutcomeMutation("update", { outcomeId });

        // Reload outcomes list
        if (typeof globalThis.loadOutcomes === "function") {
          globalThis.loadOutcomes();
        }
      } else {
        const error = await response.json();
        alert(`Failed to update outcome: ${error.error || "Unknown error"}`);
      }
    } catch (error) {
      console.error("Error updating outcome:", error); // eslint-disable-line no-console
      alert(
        "Failed to update outcome. Please check your connection and try again.",
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
 * Open Edit Outcome Modal with pre-populated data
 * Called from outcome list when Edit button is clicked
 */
function openEditOutcomeModal(outcomeId, outcomeData) {
  document.getElementById("editOutcomeId").value = outcomeId;
  document.getElementById("editOutcomeCloNumber").value =
    outcomeData.clo_number || "";
  document.getElementById("editOutcomeDescription").value =
    outcomeData.description || "";
  document.getElementById("editOutcomeAssessmentMethod").value =
    outcomeData.assessment_method || "";
  document.getElementById("editOutcomeActive").checked =
    outcomeData.active !== undefined ? outcomeData.active : true;

  const modal = new bootstrap.Modal(
    document.getElementById("editOutcomeModal"),
  );
  modal.show();
}

/**
 * Delete outcome with confirmation
 * Shows confirmation dialog before deleting
 */
async function deleteOutcome(outcomeId, courseName, cloNumber) {
  const confirmation = confirm(
    `Are you sure you want to delete ${cloNumber} for ${courseName}?\n\n` +
      "This action cannot be undone.",
  );

  if (!confirmation) {
    return;
  }

  try {
    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]',
    )?.content;

    const response = await fetch(`/api/outcomes/${outcomeId}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken && { "X-CSRFToken": csrfToken }),
      },
    });

    if (response.ok) {
      alert(`${cloNumber} for ${courseName} deleted successfully.`);
      publishOutcomeMutation("delete", { outcomeId });

      if (typeof globalThis.loadOutcomes === "function") {
        globalThis.loadOutcomes();
      }
    } else {
      const error = await response.json();
      alert(`Failed to delete outcome: ${error.error || "Unknown error"}`);
    }
  } catch (error) {
    console.error("Error deleting outcome:", error); // eslint-disable-line no-console
    alert("Failed to delete outcome. Please try again.");
  }
}

// Expose functions to window for inline onclick handlers and testing
globalThis.openEditOutcomeModal = openEditOutcomeModal;
globalThis.deleteOutcome = deleteOutcome;

/**
 * Load outcomes with filters
 * Fetches from /api/outcomes and renders table
 */
async function loadOutcomes() {
  const container = document.getElementById("outcomesTableContainer");
  if (!container) return; // Not on list page

  // Show loading
  container.innerHTML = `
      <div class="d-flex justify-content-center p-5">
          <div class="spinner-border text-primary" role="status">
              <span class="visually-hidden">Loading...</span>
          </div>
      </div>
  `;

  try {
    // Build query params
    const params = new URLSearchParams();
    const programId = document.getElementById("filterProgram")?.value;
    const courseId = document.getElementById("filterCourse")?.value;
    const status = document.getElementById("filterStatus")?.value;

    if (programId) params.append("program_id", programId);
    if (courseId) params.append("course_id", courseId);
    if (status) params.append("status", status);

    const response = await fetch(`/api/outcomes?${params.toString()}`);
    if (!response.ok) throw new Error("Failed to fetch outcomes");

    const data = await response.json();
    const outcomes = data.outcomes || [];

    renderOutcomesTable(outcomes, container);
  } catch (error) {
    console.error("Error loading outcomes:", error);
    container.innerHTML = `
          <div class="alert alert-danger">
              <i class="fas fa-exclamation-circle me-2"></i>
              Failed to load outcomes. Please try again.
          </div>
      `;
  }
}

/**
 * Render the outcomes table
 */
function renderOutcomesTable(outcomes, container) {
  if (outcomes.length === 0) {
    container.innerHTML = `
          <div class="text-center p-5 text-muted">
              <i class="fas fa-clipboard-check mb-3" style="font-size: 2rem;"></i>
              <p>No outcomes found matching the current filters.</p>
          </div>
      `;
    return;
  }

  const tableHtml = `
      <div class="table-responsive">
          <table class="table table-hover align-middle">
              <thead class="table-light">
                  <tr>
                      <th style="width: 15%">Course</th>
                      <th style="width: 10%">CLO #</th>
                      <th style="width: 40%">Description</th>
                      <th style="width: 20%">Assessment Method</th>
                      <th style="width: 10%">Status</th>
                      <th style="width: 5%">Actions</th>
                  </tr>
              </thead>
              <tbody>
                  ${outcomes
                    .map((outcome) => {
                      // Attempt to resolve course name if present, else default
                      // Note: API might need improvement to ensure course data is always eager loaded
                      const courseName =
                        outcome.course_number ||
                        outcome.course?.course_number ||
                        "Unknown - " + outcome.course_id.substring(0, 8);

                      const activeStatus =
                        outcome.active !== false ? "active" : "archived";

                      return `
                      <tr data-outcome-id="${outcome.outcome_id}">
                          <td class="fw-bold text-secondary">
                              ${courseName}
                          </td>
                          <td>${outcome.clo_number}</td>
                          <td>
                              <div class="text-wrap" style="max-width: 500px;">
                                  ${escapeHtml(outcome.description)}
                              </div>
                          </td>
                          <td>${escapeHtml(outcome.assessment_method || "-")}</td>
                          <td>
                              ${getStatusBadge(activeStatus)}
                          </td>
                          <td>
                              <div class="btn-group btn-group-sm">
                                  <button class="btn btn-outline-primary" 
                                          onclick='openEditOutcomeModal("${
                                            outcome.outcome_id
                                          }", ${JSON.stringify(outcome).replace(
                                            /'/g,
                                            "&apos;",
                                          )})'
                                          title="Edit">
                                      <i class="fas fa-edit"></i>
                                  </button>
                                  <button class="btn btn-outline-danger" 
                                          onclick='deleteOutcome("${
                                            outcome.outcome_id
                                          }", "${courseName}", "CLO ${
                                            outcome.clo_number
                                          }")'
                                          title="Delete">
                                      <i class="fas fa-trash"></i>
                                  </button>
                              </div>
                          </td>
                      </tr>
                      `;
                    })
                    .join("")}
              </tbody>
          </table>
      </div>
      <div class="d-flex justify-content-between align-items-center mt-3">
          <small class="text-muted">Showing ${outcomes.length} outcomes</small>
      </div>
  `;

  container.innerHTML = tableHtml;
}

// Helper for status badge
function getStatusBadge(status) {
  if (status === "active")
    return '<span class="badge bg-success">Active</span>';
  if (status === "archived")
    return '<span class="badge bg-secondary">Archived</span>';
  return `<span class="badge bg-light text-dark border">${status}</span>`;
}

// Helper to escape HTML to prevent XSS
function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

globalThis.loadOutcomes = loadOutcomes;
