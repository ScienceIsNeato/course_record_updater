/**
 * Institution Management UI - Create, Edit, Delete Institutions
 *
 * Handles:
 * - Create institution form submission (with admin user creation)
 * - Edit institution form submission
 * - Delete institution confirmation
 * - API communication with CSRF protection
 */

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  initializeCreateInstitutionModal();
  initializeEditInstitutionModal();
});

/**
 * Initialize Create Institution Modal
 * Sets up form submission for new institutions
 */
function initializeCreateInstitutionModal() {
  const form = document.getElementById("createInstitutionForm");

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const institutionData = {
      name: document.getElementById("institutionName").value,
      short_name: document.getElementById("institutionShortName").value,
      address: document.getElementById("institutionAddress").value || "",
      phone: document.getElementById("institutionPhone").value || "",
      website: document.getElementById("institutionWebsite").value || "",
      admin_email: document.getElementById("adminEmail").value,
      admin_first_name: document.getElementById("adminFirstName").value,
      admin_last_name: document.getElementById("adminLastName").value,
    };

    const createBtn = document.getElementById("createInstitutionBtn");
    const btnText = createBtn.querySelector(".btn-text");
    const btnSpinner = createBtn.querySelector(".btn-spinner");

    // Show loading state
    btnText.classList.add("d-none");
    btnSpinner.classList.remove("d-none");
    createBtn.disabled = true;

    try {
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      const response = await fetch("/api/institutions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(csrfToken && { "X-CSRFToken": csrfToken }),
        },
        body: JSON.stringify(institutionData),
      });

      if (response.ok) {
        const result = await response.json();

        // Success - close modal and reset form
        const modal = bootstrap.Modal.getInstance(
          document.getElementById("createInstitutionModal"),
        );
        if (modal) {
          modal.hide();
        }

        form.reset();

        alert(result.message || "Institution created successfully!");

        // Reload institutions list if function exists
        if (typeof globalThis.loadInstitutions === "function") {
          globalThis.loadInstitutions();
        }
      } else {
        const error = await response.json();
        alert(
          `Failed to create institution: ${error.error || "Unknown error"}`,
        );
      }
    } catch (error) {
      console.error("Error creating institution:", error); // eslint-disable-line no-console
      alert(
        "Failed to create institution. Please check your connection and try again.",
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
 * Initialize Edit Institution Modal
 * Sets up form submission for updating institutions
 */
function initializeEditInstitutionModal() {
  const form = document.getElementById("editInstitutionForm");

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const institutionId = document.getElementById("editInstitutionId").value;
    const updateData = {
      name: document.getElementById("editInstitutionName").value,
      short_name: document.getElementById("editInstitutionShortName").value,
      address: document.getElementById("editInstitutionAddress").value || "",
      phone: document.getElementById("editInstitutionPhone").value || "",
      website: document.getElementById("editInstitutionWebsite").value || "",
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

      const response = await fetch(`/api/institutions/${institutionId}`, {
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
          document.getElementById("editInstitutionModal"),
        );
        if (modal) {
          modal.hide();
        }

        alert(result.message || "Institution updated successfully!");

        // Reload institutions list
        if (typeof globalThis.loadInstitutions === "function") {
          globalThis.loadInstitutions();
        }
      } else {
        const error = await response.json();
        alert(
          `Failed to update institution: ${error.error || "Unknown error"}`,
        );
      }
    } catch (error) {
      console.error("Error updating institution:", error); // eslint-disable-line no-console
      alert(
        "Failed to update institution. Please check your connection and try again.",
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
 * Open Edit Institution Modal with pre-populated data
 * Called from institution list when Edit button is clicked
 */
function openEditInstitutionModal(institutionId, institutionData) {
  document.getElementById("editInstitutionId").value = institutionId;
  document.getElementById("editInstitutionName").value =
    institutionData.name || "";
  document.getElementById("editInstitutionShortName").value =
    institutionData.short_name || "";
  document.getElementById("editInstitutionAddress").value =
    institutionData.address || "";

  const phoneInput = document.getElementById("editInstitutionPhone");
  if (phoneInput) {
    phoneInput.value = institutionData.phone || "";
  }

  const websiteInput = document.getElementById("editInstitutionWebsite");
  if (websiteInput) {
    websiteInput.value = institutionData.website || "";
  }

  const modal = new bootstrap.Modal(
    document.getElementById("editInstitutionModal"),
  );
  modal.show();
}

/**
 * Delete institution with typed confirmation
 * Requires typing "i know what I'm doing" to confirm
 */
async function deleteInstitution(institutionId, institutionName) {
  const confirmation = prompt(
    `⚠️ WARNING: This will PERMANENTLY delete ${institutionName} and all its data.\n\n` +
      "This includes all users, programs, courses, and data associated with this institution.\n\n" +
      'Type "i know what I\'m doing" to confirm:',
  );

  if (confirmation !== "i know what I'm doing") {
    alert("Deletion cancelled - confirmation did not match.");
    return;
  }

  try {
    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]',
    )?.content;

    const response = await fetch(`/api/institutions/${institutionId}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken && { "X-CSRFToken": csrfToken }),
      },
    });

    if (response.ok) {
      alert(`${institutionName} has been permanently deleted.`);

      if (typeof globalThis.loadInstitutions === "function") {
        globalThis.loadInstitutions();
      }
    } else {
      const error = await response.json();
      alert(`Failed to delete institution: ${error.error || "Unknown error"}`);
    }
  } catch (error) {
    console.error("Error deleting institution:", error); // eslint-disable-line no-console
    alert("Failed to delete institution. Please try again.");
  }
}

// Expose functions to window for inline onclick handlers and testing
globalThis.openEditInstitutionModal = openEditInstitutionModal;
globalThis.deleteInstitution = deleteInstitution;
