/**
 * Program Management UI - Create, Edit, Delete Programs
 *
 * Handles:
 * - Create program form submission
 * - Edit program form submission
 * - Delete program confirmation
 * - API communication with CSRF protection
 */

/* eslint-disable no-console */
// Initialize when DOM is ready
// Handle case where DOM is already loaded (avoid race condition)
function initProgramManagement() {
  console.log(
    "[programManagement] DEBUG: initProgramManagement called, readyState =",
    document.readyState,
  );
  // Safety check: only initialize if form elements exist
  // (Prevents initialization from running before DOM is ready in test environments)
  if (
    !document.getElementById("createProgramForm") &&
    !document.getElementById("editProgramForm")
  ) {
    console.log("[programManagement] DEBUG: No forms found, skipping init");
    return; // Forms not on page yet, skip initialization
  }

  console.log("[programManagement] DEBUG: Forms found, initializing");
  console.log(
    "[programManagement] DEBUG: About to call initializeCreateProgramModal()",
  );
  initializeCreateProgramModal();
  console.log(
    "[programManagement] DEBUG: About to call initializeEditProgramModal()",
  );
  initializeEditProgramModal();
  console.log("[programManagement] DEBUG: About to call setupModalListeners()");
  setupModalListeners();
  // Fallback: pre-populate institution dropdown on init in case modal event timing misses
  // This is idempotent due to innerHTML reset inside loader
  loadInstitutionsForDropdown();
  console.log("[programManagement] DEBUG: Initialization complete");
}

console.log("[programManagement] DEBUG: Script loaded");
if (document.readyState === "loading") {
  // DOM still loading, wait for it
  console.log("[programManagement] DEBUG: Waiting for DOMContentLoaded");
  document.addEventListener("DOMContentLoaded", initProgramManagement);
} else {
  // DOM already loaded, initialize immediately
  console.log("[programManagement] DEBUG: DOM already loaded, init now");
  initProgramManagement();
}
/* eslint-enable no-console */

// Export for testing (Node.js/Jest environment)
if (typeof module !== "undefined" && module.exports) {
  module.exports = { initProgramManagement, openEditProgramModal };
}

/* eslint-disable no-console */
console.log("[programManagement] DEBUG: About to define setupModalListeners");
/**
 * Setup modal event listeners
 * Loads data when modals are opened
 */
function setupModalListeners() {
  try {
    console.log("[programManagement] DEBUG: setupModalListeners called");
    const createModal = document.getElementById("createProgramModal");
    console.log(
      "[programManagement] DEBUG: createModal element found?",
      !!createModal,
    );

    if (createModal) {
      console.log(
        "[programManagement] DEBUG: Attaching show.bs.modal listener",
      );
      // Use 'shown.bs.modal' so DOM is fully visible and ready
      createModal.addEventListener("shown.bs.modal", async () => {
        console.log("[programManagement] DEBUG: show.bs.modal event FIRED!");
        await loadInstitutionsForDropdown();
      });
    } else {
      console.error("[programManagement] ERROR: createModal not found!");
    }
  } catch (error) {
    console.error(
      "[programManagement] FATAL ERROR in setupModalListeners:",
      error,
    );
  }
}

/**
 * Load institutions into the dropdown
 * For institution admins: uses their institution from userContext
 * For site admins: would need to fetch all institutions (future enhancement)
 */
async function loadInstitutionsForDropdown() {
  const select = document.getElementById("programInstitutionId");

  if (!select) {
    return;
  }

  // Use user's institution from the page context (set in template)
  if (globalThis.userContext?.institutionId) {
    select.innerHTML = '<option value="">Select Institution</option>'; // nosemgrep

    const option = document.createElement("option");
    option.value = globalThis.userContext.institutionId;
    option.textContent = globalThis.userContext.institutionName;
    option.selected = true; // Auto-select user's institution
    select.appendChild(option);
  }
}

/**
 * Initialize Create Program Modal
 * Sets up form submission for new programs
 */
function initializeCreateProgramModal() {
  const form = document.getElementById("createProgramForm");

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const programData = {
      name: document.getElementById("programName").value,
      short_name: document.getElementById("programShortName").value,
      institution_id: document.getElementById("programInstitutionId").value,
      active: document.getElementById("programActive").checked,
    };

    const createBtn = document.getElementById("createProgramBtn");
    const btnText = createBtn.querySelector(".btn-text");
    const btnSpinner = createBtn.querySelector(".btn-spinner");

    // Show loading state
    btnText.classList.add("d-none");
    btnSpinner.classList.remove("d-none");
    createBtn.disabled = true;

    try {
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      const response = await fetch("/api/programs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(csrfToken && { "X-CSRFToken": csrfToken }),
        },
        body: JSON.stringify(programData),
      });

      if (response.ok) {
        const result = await response.json();

        // Success - close modal and reset form
        const modal = bootstrap.Modal.getInstance(
          document.getElementById("createProgramModal"),
        );
        if (modal) {
          modal.hide();
        }

        form.reset();

        alert(result.message || "Program created successfully!");

        // Reload programs list if function exists
        if (typeof globalThis.loadPrograms === "function") {
          globalThis.loadPrograms();
        }
      } else {
        const error = await response.json();
        alert(`Failed to create program: ${error.error || "Unknown error"}`);
      }
    } catch (error) {
      console.error("Error creating program:", error); // eslint-disable-line no-console
      alert(
        "Failed to create program. Please check your connection and try again.",
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
 * Initialize Edit Program Modal
 * Sets up form submission for updating programs
 */
function initializeEditProgramModal() {
  const form = document.getElementById("editProgramForm");

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const programId = document.getElementById("editProgramId").value;
    const updateData = {
      name: document.getElementById("editProgramName").value,
      active: document.getElementById("editProgramActive").checked,
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

      const response = await fetch(`/api/programs/${programId}`, {
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
          document.getElementById("editProgramModal"),
        );
        if (modal) {
          modal.hide();
        }

        alert(result.message || "Program updated successfully!");

        // Reload programs list
        if (typeof globalThis.loadPrograms === "function") {
          globalThis.loadPrograms();
        }
      } else {
        const error = await response.json();
        alert(`Failed to update program: ${error.error || "Unknown error"}`);
      }
    } catch (error) {
      console.error("Error updating program:", error); // eslint-disable-line no-console
      alert(
        "Failed to update program. Please check your connection and try again.",
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
 * Open Edit Program Modal with pre-populated data
 * Called from program list when Edit button is clicked
 */
function openEditProgramModal(programId, programData) {
  document.getElementById("editProgramId").value = programId;
  document.getElementById("editProgramName").value = programData.name || "";
  document.getElementById("editProgramActive").checked =
    programData.active !== undefined ? programData.active : true;

  const modal = new bootstrap.Modal(
    document.getElementById("editProgramModal"),
  );
  modal.show();
}

/**
 * Delete program with confirmation
 * Shows confirmation dialog before deleting
 */
async function deleteProgram(programId, programName) {
  const confirmation = confirm(
    `Are you sure you want to delete the program "${programName}"?\n\n` +
      "This action cannot be undone. All courses associated with this program will be reassigned.",
  );

  if (!confirmation) {
    return;
  }

  try {
    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]',
    )?.content;

    const response = await fetch(`/api/programs/${programId}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken && { "X-CSRFToken": csrfToken }),
      },
    });

    if (response.ok) {
      alert(`${programName} deleted successfully.`);

      // Refresh dashboard data if available
      if (
        globalThis.InstitutionDashboard &&
        typeof globalThis.InstitutionDashboard.refresh === "function"
      ) {
        globalThis.InstitutionDashboard.refresh();
      } else if (typeof globalThis.loadPrograms === "function") {
        globalThis.loadPrograms();
      }
    } else {
      const error = await response.json();
      const errorMessage = error.error || "Unknown error";

      // Special handling for program with courses
      if (response.status === 409 && error.code === "PROGRAM_HAS_COURSES") {
        alert(
          'Cannot delete "' +
            programName +
            '" because it has courses assigned.\n\n' +
            "Please reassign or remove courses from this program first, " +
            "or contact your system administrator for assistance.",
        );
      } else {
        alert(`Failed to delete program: ${errorMessage}`);
      }
    }
  } catch (error) {
    console.error("Error deleting program:", error); // eslint-disable-line no-console
    alert("Failed to delete program. Please try again.");
  }
}

// Expose functions to window for inline onclick handlers and testing
globalThis.openEditProgramModal = openEditProgramModal;
globalThis.deleteProgram = deleteProgram;
