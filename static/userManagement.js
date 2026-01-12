/**
 * User Management UI - Invite & Edit User Modals
 *
 * Handles:
 * - Invite user form submission
 * - Role-based conditional field display
 * - Form validation and error handling
 * - API communication with CSRF protection
 */

/**
 * Show Bootstrap alert banner at the top of the page
 * @param {string} type - 'success', 'danger', 'warning', or 'info'
 * @param {string} message - Message to display
 */
function showAlert(type, message) {
  // Allow test mocking by checking global first
  // eslint-disable-next-line no-undef
  if (
    typeof global !== "undefined" &&
    global.showAlert &&
    global.showAlert !== showAlert
  ) {
    // eslint-disable-next-line no-undef
    global.showAlert(type, message);
    return;
  }

  // Find or create alert container
  let container = document.querySelector(".alert-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "alert-container";
    const main =
      document.querySelector("main") || document.querySelector(".container");
    if (main) {
      main.insertBefore(container, main.firstChild);
    } else {
      document.body.insertBefore(container, document.body.firstChild);
    }
  }

  // Create alert element
  const alert = document.createElement("div");
  alert.className = `alert alert-${type} alert-dismissible fade show mt-3`;
  alert.setAttribute("role", "alert");
  // nosemgrep
  alert.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;

  // Add to container
  container.appendChild(alert);

  // Auto-dismiss after 5 seconds
  setTimeout(() => {
    alert.classList.remove("show");
    setTimeout(() => alert.remove(), 150);
  }, 5000);
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  initializeInviteUserModal();
  initializeEditUserModal();
  initializeAddUserModal();
});

/**
 * Initialize Invite User Modal
 * Sets up form submission and role-based field visibility
 */
function initializeInviteUserModal() {
  const form = document.getElementById("inviteUserForm");
  const roleSelect = document.getElementById("inviteRole");
  const programSelection = document.getElementById("programSelection");

  if (!form || !roleSelect) {
    return; // Form not on this page
  }

  // Handle role selection changes
  roleSelect.addEventListener("change", function () {
    if (this.value === "program_admin") {
      programSelection.style.display = "block";
    } else {
      programSelection.style.display = "none";
    }
  });

  // Handle form submission
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const emailInput = document.getElementById("inviteEmail");
    const messageInput = document.getElementById("inviteMessage");
    const programsSelect = document.getElementById("invitePrograms");
    const sendBtn = document.getElementById("sendInviteBtn");
    const btnText = sendBtn.querySelector(".btn-text");
    const btnSpinner = sendBtn.querySelector(".btn-spinner");

    // Collect form data
    const invitationData = {
      invitee_email: emailInput.value,
      invitee_role: roleSelect.value,
      personal_message: messageInput.value || "",
    };

    // Include program_ids if program_admin role
    if (roleSelect.value === "program_admin") {
      const selectedPrograms = Array.from(programsSelect.selectedOptions).map(
        (opt) => opt.value,
      );
      invitationData.program_ids = selectedPrograms;
    }

    // Show loading state
    btnText.classList.add("d-none");
    btnSpinner.classList.remove("d-none");
    sendBtn.disabled = true;

    try {
      // Get CSRF token
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      // Make API request
      const response = await fetch("/api/auth/invite", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(csrfToken && { "X-CSRFToken": csrfToken }),
        },
        body: JSON.stringify(invitationData),
      });

      if (response.ok) {
        const result = await response.json();

        // Success - close modal and reset form
        const modal = bootstrap.Modal.getInstance(
          document.getElementById("inviteUserModal"),
        );
        if (modal) {
          modal.hide();
        }

        // Reset form
        form.reset();
        programSelection.style.display = "none";

        // Show success message using Bootstrap alert
        showAlert("success", result.message || "Invitation sent successfully!");

        // Reload user list if function exists
        if (typeof globalThis.loadUsers === "function") {
          globalThis.loadUsers();
        }
      } else {
        // Handle API error
        const error = await response.json();
        showAlert(
          "danger",
          `Failed to send invitation: ${error.error || "Unknown error"}`,
        );
      }
    } catch (error) {
      console.error("Error sending invitation:", error); // eslint-disable-line no-console
      showAlert(
        "danger",
        "Failed to send invitation. Please check your connection and try again.",
      );
    } finally {
      // Restore button state
      btnText.classList.remove("d-none");
      btnSpinner.classList.add("d-none");
      sendBtn.disabled = false;
    }
  });
}

/**
 * Initialize Edit User Modal
 * Sets up form submission and pre-populates data
 */
function initializeEditUserModal() {
  const form = document.getElementById("editUserForm");

  if (!form) {
    return; // Form not on this page
  }

  // Handle form submission
  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const userId = document.getElementById("editUserId").value;
    const firstName = document.getElementById("editFirstName").value;
    const lastName = document.getElementById("editLastName").value;
    const email = document.getElementById("editUserEmail").value;
    const displayName = document.getElementById("editDisplayName")?.value;
    const roleSelect = document.getElementById("editUserRole");
    const newRole = roleSelect?.value;
    const originalRole = roleSelect?.dataset.originalRole || newRole;
    const currentUserRole =
      globalThis.currentUser?.role || document.body.dataset.currentRole || "";
    const canEditRoles =
      currentUserRole === "institution_admin" ||
      currentUserRole === "site_admin";

    const updateData = {
      first_name: firstName,
      last_name: lastName,
      email: email,
      ...(displayName && { display_name: displayName }),
    };

    const saveBtn = this.querySelector('button[type="submit"]');
    const btnText = saveBtn.querySelector(".btn-text");
    const btnSpinner = saveBtn.querySelector(".btn-spinner");

    // Show loading state
    btnText.classList.add("d-none");
    btnSpinner.classList.remove("d-none");
    saveBtn.disabled = true;

    try {
      // Get CSRF token
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      // Make API request - Use profile endpoint for self-service updates
      const response = await fetch(`/api/users/${userId}/profile`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(csrfToken && { "X-CSRFToken": csrfToken }),
        },
        body: JSON.stringify(updateData),
      });

      if (response.ok) {
        const result = await response.json();

        if (roleSelect && canEditRoles && newRole && newRole !== originalRole) {
          const roleResponse = await fetch(`/api/users/${userId}/role`, {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
              ...(csrfToken && { "X-CSRFToken": csrfToken }),
            },
            body: JSON.stringify({ role: newRole }),
          });

          if (!roleResponse.ok) {
            const roleError = await roleResponse.json();
            showAlert(
              "danger",
              `Failed to update role: ${roleError.error || "Unknown error"}`,
            );
            throw new Error("Role update failed");
          }

          roleSelect.dataset.originalRole = newRole;
        }

        // Success - close modal
        const modal = bootstrap.Modal.getInstance(
          document.getElementById("editUserModal"),
        );
        if (modal) {
          modal.hide();
        }

        // Show success message
        showAlert("success", result.message || "User updated successfully!");

        // Reload user list
        if (typeof globalThis.loadUsers === "function") {
          globalThis.loadUsers();
        }
      } else {
        const error = await response.json();
        showAlert(
          "danger",
          `Failed to update user: ${error.error || "Unknown error"}`,
        );
      }
    } catch (error) {
      console.error("Error updating user:", error); // eslint-disable-line no-console
      showAlert(
        "danger",
        "Failed to update user. Please check your connection and try again.",
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
 * Open Edit User Modal with pre-populated data
 * Called from user list when Edit button is clicked
 */
function openEditUserModal(userId, firstName, lastName, displayName) {
  const user =
    userId && typeof userId === "object"
      ? userId
      : {
          user_id: userId,
          first_name: firstName,
          last_name: lastName,
          display_name: displayName,
        };

  document.getElementById("editUserId").value = user.user_id || "";
  document.getElementById("editFirstName").value = user.first_name || "";
  document.getElementById("editLastName").value = user.last_name || "";

  const emailInput = document.getElementById("editUserEmail");
  if (emailInput) {
    emailInput.value = user.email || "";
  }

  const displayNameInput = document.getElementById("editDisplayName");
  if (displayNameInput) {
    displayNameInput.value = user.display_name || "";
  }

  const roleSelect = document.getElementById("editUserRole");
  if (roleSelect) {
    const roleValue = user.role || "instructor";
    roleSelect.value = roleValue;
    roleSelect.dataset.originalRole = roleValue;
    const currentUserRole = globalThis.currentUser?.role || "instructor";
    const canEditRoles =
      currentUserRole === "institution_admin" ||
      currentUserRole === "site_admin";
    roleSelect.disabled = !canEditRoles;
  }

  const modal = new bootstrap.Modal(document.getElementById("editUserModal"));
  modal.show();
}

/**
 * Deactivate user with confirmation
 * Soft delete - suspends user account
 */
async function deactivateUser(userId, userName) {
  if (
    !confirm(
      `Are you sure you want to deactivate ${userName}? They will not be able to log in until reactivated.`,
    )
  ) {
    return;
  }

  try {
    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]',
    )?.content;

    const response = await fetch(`/api/users/${userId}/deactivate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken && { "X-CSRFToken": csrfToken }),
      },
    });

    if (response.ok) {
      alert(`${userName} has been deactivated.`);

      if (typeof globalThis.loadUsers === "function") {
        globalThis.loadUsers();
      }
    } else {
      const error = await response.json();
      alert(`Failed to deactivate user: ${error.error || "Unknown error"}`);
    }
  } catch (error) {
    console.error("Error deactivating user:", error); // eslint-disable-line no-console
    alert("Failed to deactivate user. Please try again.");
  }
}

/**
 * Delete user with confirmation
 * Hard delete - permanent removal
 */
async function deleteUser(userId, userName) {
  const confirmation = prompt(
    `⚠️ WARNING: This will PERMANENTLY delete ${userName} and all their data.\n\n` +
      `Type "DELETE ${userName}" to confirm:`,
  );

  if (confirmation !== `DELETE ${userName}`) {
    alert("Deletion cancelled - confirmation did not match.");
    return;
  }

  try {
    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]',
    )?.content;

    const response = await fetch(`/api/users/${userId}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken && { "X-CSRFToken": csrfToken }),
      },
    });

    if (response.ok) {
      alert(`${userName} has been permanently deleted.`);

      if (typeof globalThis.loadUsers === "function") {
        globalThis.loadUsers();
      }
    } else {
      const error = await response.json();
      alert(`Failed to delete user: ${error.error || "Unknown error"}`);
    }
  } catch (error) {
    console.error("Error deleting user:", error); // eslint-disable-line no-console
    alert("Failed to delete user. Please try again.");
  }
}

/**
 * Open Add User Modal
 */
function openAddUserModal() {
  const modal = new bootstrap.Modal(document.getElementById("addUserModal"));

  // Reset form
  const form = document.getElementById("addUserForm");
  if (form) {
    form.reset();
  }

  modal.show();
}

/**
 * Initialize Add User Modal
 */
function initializeAddUserModal() {
  const form = document.getElementById("addUserForm");

  if (!form) {
    return; // Form not on this page
  }

  // Handle form submission
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const emailInput = document.getElementById("addUserEmail");
    const firstNameInput = document.getElementById("addFirstName");
    const lastNameInput = document.getElementById("addLastName");
    const roleSelect = document.getElementById("addUserRole");

    // Collect form data
    const userData = {
      email: emailInput.value,
      first_name: firstNameInput.value,
      last_name: lastNameInput.value,
      role: roleSelect.value,
    };

    try {
      const csrfToken = document.querySelector(
        'meta[name="csrf-token"]',
      )?.content;

      const response = await fetch("/api/users", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(csrfToken && { "X-CSRFToken": csrfToken }),
        },
        body: JSON.stringify(userData),
      });

      const result = await response.json();

      if (response.ok && result.success) {
        // Close modal
        const modalElement = document.getElementById("addUserModal");
        const modal = bootstrap.Modal.getInstance(modalElement);
        modal.hide();

        // Show success message
        showAlert(
          "success",
          `User ${userData.email} created successfully! Invitation email sent.`,
        );

        // Reload users list
        if (typeof globalThis.loadUsers === "function") {
          globalThis.loadUsers();
        }

        // Reset form
        form.reset();
      } else {
        showAlert(
          "danger",
          `Failed to create user: ${result.error || "Unknown error"}`,
        );
      }
    } catch (error) {
      console.error("Error creating user:", error); // eslint-disable-line no-console
      showAlert("danger", "Failed to create user. Please try again.");
    }
  });
}

// Expose functions to window for inline onclick handlers and testing
globalThis.openAddUserModal = openAddUserModal;
globalThis.openEditUserModal = openEditUserModal;
globalThis.deactivateUser = deactivateUser;
globalThis.deleteUser = deleteUser;
