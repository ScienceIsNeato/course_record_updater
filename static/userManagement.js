/**
 * User Management UI - Invite & Edit User Modals
 *
 * Handles:
 * - Invite user form submission
 * - Role-based conditional field display
 * - Form validation and error handling
 * - API communication with CSRF protection
 */

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  initializeInviteUserModal();
  initializeEditUserModal();
});

/**
 * Initialize Invite User Modal
 * Sets up form submission and role-based field visibility
 */
function initializeInviteUserModal() {
  const form = document.getElementById('inviteUserForm');
  const roleSelect = document.getElementById('inviteRole');
  const programSelection = document.getElementById('programSelection');

  if (!form || !roleSelect) {
    return; // Form not on this page
  }

  // Handle role selection changes
  roleSelect.addEventListener('change', function () {
    if (this.value === 'program_admin') {
      programSelection.style.display = 'block';
    } else {
      programSelection.style.display = 'none';
    }
  });

  // Handle form submission
  form.addEventListener('submit', async e => {
    e.preventDefault();

    const emailInput = document.getElementById('inviteEmail');
    const messageInput = document.getElementById('inviteMessage');
    const programsSelect = document.getElementById('invitePrograms');
    const sendBtn = document.getElementById('sendInviteBtn');
    const btnText = sendBtn.querySelector('.btn-text');
    const btnSpinner = sendBtn.querySelector('.btn-spinner');

    // Collect form data
    const invitationData = {
      invitee_email: emailInput.value,
      invitee_role: roleSelect.value,
      personal_message: messageInput.value || ''
    };

    // Include program_ids if program_admin role
    if (roleSelect.value === 'program_admin') {
      const selectedPrograms = Array.from(programsSelect.selectedOptions).map(opt => opt.value);
      invitationData.program_ids = selectedPrograms;
    }

    // Show loading state
    btnText.classList.add('d-none');
    btnSpinner.classList.remove('d-none');
    sendBtn.disabled = true;

    try {
      // Get CSRF token
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

      // Make API request
      const response = await fetch('/api/invitations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(csrfToken && { 'X-CSRFToken': csrfToken })
        },
        body: JSON.stringify(invitationData)
      });

      if (response.ok) {
        const result = await response.json();

        // Success - close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('inviteUserModal'));
        if (modal) {
          modal.hide();
        }

        // Reset form
        form.reset();
        programSelection.style.display = 'none';

        // Show success message (optional - could use a toast notification)
        alert(result.message || 'Invitation sent successfully!');

        // Reload user list if function exists
        if (typeof window.loadUsers === 'function') {
          window.loadUsers();
        }
      } else {
        // Handle API error
        const error = await response.json();
        alert(`Failed to send invitation: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error sending invitation:', error); // eslint-disable-line no-console
      alert('Failed to send invitation. Please check your connection and try again.');
    } finally {
      // Restore button state
      btnText.classList.remove('d-none');
      btnSpinner.classList.add('d-none');
      sendBtn.disabled = false;
    }
  });
}

/**
 * Initialize Edit User Modal
 * Sets up form submission and pre-populates data
 */
function initializeEditUserModal() {
  const form = document.getElementById('editUserForm');

  if (!form) {
    return; // Form not on this page
  }

  // Handle form submission
  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const userId = document.getElementById('editUserId').value;
    const firstName = document.getElementById('editFirstName').value;
    const lastName = document.getElementById('editLastName').value;
    const displayName = document.getElementById('editDisplayName')?.value;

    const updateData = {
      first_name: firstName,
      last_name: lastName,
      ...(displayName && { display_name: displayName })
    };

    const saveBtn = this.querySelector('button[type="submit"]');
    const btnText = saveBtn.querySelector('.btn-text');
    const btnSpinner = saveBtn.querySelector('.btn-spinner');

    // Show loading state
    btnText.classList.add('d-none');
    btnSpinner.classList.remove('d-none');
    saveBtn.disabled = true;

    try {
      // Get CSRF token
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

      // Make API request - Use profile endpoint for self-service updates
      const response = await fetch(`/api/users/${userId}/profile`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(csrfToken && { 'X-CSRFToken': csrfToken })
        },
        body: JSON.stringify(updateData)
      });

      if (response.ok) {
        const result = await response.json();

        // Success - close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('editUserModal'));
        if (modal) {
          modal.hide();
        }

        // Show success message
        alert(result.message || 'User updated successfully!');

        // Reload user list
        if (typeof window.loadUsers === 'function') {
          window.loadUsers();
        }
      } else {
        const error = await response.json();
        alert(`Failed to update user: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error updating user:', error); // eslint-disable-line no-console
      alert('Failed to update user. Please check your connection and try again.');
    } finally {
      // Restore button state
      btnText.classList.remove('d-none');
      btnSpinner.classList.add('d-none');
      saveBtn.disabled = false;
    }
  });
}

/**
 * Open Edit User Modal with pre-populated data
 * Called from user list when Edit button is clicked
 */
function openEditUserModal(userId, firstName, lastName, displayName) {
  document.getElementById('editUserId').value = userId;
  document.getElementById('editFirstName').value = firstName;
  document.getElementById('editLastName').value = lastName;

  const displayNameInput = document.getElementById('editDisplayName');
  if (displayNameInput) {
    displayNameInput.value = displayName || '';
  }

  const modal = new bootstrap.Modal(document.getElementById('editUserModal'));
  modal.show();
}

/**
 * Deactivate user with confirmation
 * Soft delete - suspends user account
 */
async function deactivateUser(userId, userName) {
  if (
    !confirm(
      `Are you sure you want to deactivate ${userName}? They will not be able to log in until reactivated.`
    )
  ) {
    return;
  }

  try {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

    const response = await fetch(`/api/users/${userId}/deactivate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken && { 'X-CSRFToken': csrfToken })
      }
    });

    if (response.ok) {
      alert(`${userName} has been deactivated.`);

      if (typeof window.loadUsers === 'function') {
        window.loadUsers();
      }
    } else {
      const error = await response.json();
      alert(`Failed to deactivate user: ${error.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error deactivating user:', error); // eslint-disable-line no-console
    alert('Failed to deactivate user. Please try again.');
  }
}

/**
 * Delete user with confirmation
 * Hard delete - permanent removal
 */
async function deleteUser(userId, userName) {
  const confirmation = prompt(
    `⚠️ WARNING: This will PERMANENTLY delete ${userName} and all their data.\n\n` +
      `Type "DELETE ${userName}" to confirm:`
  );

  if (confirmation !== `DELETE ${userName}`) {
    alert('Deletion cancelled - confirmation did not match.');
    return;
  }

  try {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

    const response = await fetch(`/api/users/${userId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken && { 'X-CSRFToken': csrfToken })
      }
    });

    if (response.ok) {
      alert(`${userName} has been permanently deleted.`);

      if (typeof window.loadUsers === 'function') {
        window.loadUsers();
      }
    } else {
      const error = await response.json();
      alert(`Failed to delete user: ${error.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error deleting user:', error); // eslint-disable-line no-console
    alert('Failed to delete user. Please try again.');
  }
}

// Expose functions to window for inline onclick handlers and testing
window.openEditUserModal = openEditUserModal;
window.deactivateUser = deactivateUser;
window.deleteUser = deleteUser;
