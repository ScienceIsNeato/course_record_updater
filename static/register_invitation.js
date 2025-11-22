/**
 * Register via Invitation - Accept invitation and complete registration
 */

document.addEventListener('DOMContentLoaded', () => {
  const token = document.getElementById('invitationToken').value;
  const form = document.getElementById('acceptInvitationForm');

  // Validate invitation on page load
  validateInvitation(token);

  // Handle form submission
  form.addEventListener('submit', async e => {
    e.preventDefault();

    if (!form.checkValidity()) {
      form.classList.add('was-validated');
      return;
    }

    // Check password match
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    if (password !== confirmPassword) {
      showMessage('Passwords do not match', 'danger');
      document.getElementById('confirmPassword').classList.add('is-invalid');
      return;
    }

    // Submit invitation acceptance
    await acceptInvitation();
  });
});

/**
 * Validate invitation token and load invitation details
 */
async function validateInvitation(token) {
  const loadingDiv = document.getElementById('loadingInvitation');
  const form = document.getElementById('acceptInvitationForm');
  const emailInput = document.getElementById('email');
  const roleInput = document.getElementById('role');

  try {
    const response = await fetch(`/api/auth/invitation-status/${token}`);
    const data = await response.json();

    if (!response.ok) {
      showMessage(data.error || 'Invalid or expired invitation', 'danger');
      loadingDiv.classList.add('d-none');
      return;
    }

    // Populate form with invitation details
    emailInput.value = data.invitee_email || '';
    roleInput.value = formatRole(data.invitee_role || '');

    // Pre-fill first and last name if provided in invitation
    const firstNameInput = document.getElementById('firstName');
    const lastNameInput = document.getElementById('lastName');
    if (firstNameInput && data.first_name) {
      firstNameInput.value = data.first_name;
    }
    if (lastNameInput && data.last_name) {
      lastNameInput.value = data.last_name;
    }

    // Populate invitation metadata
    const invitationDetails = document.getElementById('invitationDetails');
    const inviterNameEl = document.getElementById('inviterName');
    const institutionNameEl = document.getElementById('institutionName');
    const personalMessageEl = document.getElementById('personalMessage');
    const personalMessageSection = document.getElementById('personalMessageSection');

    // Display inviter and institution
    inviterNameEl.textContent = data.inviter_name || data.inviter_email || 'A colleague';
    institutionNameEl.textContent = data.institution_name || 'your institution';

    // Display personal message if present
    if (data.personal_message) {
      personalMessageEl.textContent = data.personal_message;
      personalMessageSection.classList.remove('d-none');
    }

    // Show invitation details
    invitationDetails.classList.remove('d-none');

    // Show form, hide loading
    loadingDiv.classList.add('d-none');
    form.classList.remove('d-none');
  } catch (error) {
    console.error('Error validating invitation:', error); // eslint-disable-line no-console
    showMessage('Failed to validate invitation. Please try again.', 'danger');
    loadingDiv.classList.add('d-none');
  }
}

/**
 * Accept invitation and create account
 */
async function acceptInvitation() {
  const token = document.getElementById('invitationToken').value;
  const firstName = document.getElementById('firstName').value;
  const lastName = document.getElementById('lastName').value;
  const password = document.getElementById('password').value;
  const submitBtn = document.getElementById('submitBtn');
  const btnText = submitBtn.querySelector('.btn-text');
  const btnSpinner = submitBtn.querySelector('.btn-spinner');

  // Construct display name from first + last
  const displayName = `${firstName} ${lastName}`.trim();

  // Show loading state
  btnText.classList.add('d-none');
  btnSpinner.classList.remove('d-none');
  submitBtn.disabled = true;

  try {
    // Get CSRF token
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

    const response = await fetch('/api/auth/accept-invitation', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken && { 'X-CSRFToken': csrfToken })
      },
      body: JSON.stringify({
        invitation_token: token,
        password,
        display_name: displayName
      })
    });

    const data = await response.json();

    if (response.ok) {
      showMessage('Account created successfully! Redirecting to login...', 'success');
      // Redirect to login page with success message after 1.5 seconds
      setTimeout(() => {
        globalThis.location.href = '/login?message=Account+created+successfully';
      }, 1500);
    } else {
      showMessage(data.error || 'Failed to create account', 'danger');
      // Restore button state
      btnText.classList.remove('d-none');
      btnSpinner.classList.add('d-none');
      submitBtn.disabled = false;
    }
  } catch (error) {
    console.error('Error accepting invitation:', error); // eslint-disable-line no-console
    showMessage('Failed to create account. Please try again.', 'danger');
    // Restore button state
    btnText.classList.remove('d-none');
    btnSpinner.classList.add('d-none');
    submitBtn.disabled = false;
  }
}

/**
 * Show status message
 */
function showMessage(message, type) {
  const statusMessage = document.getElementById('statusMessage');
  statusMessage.textContent = message;
  statusMessage.className = `alert alert-${type}`;
  statusMessage.classList.remove('d-none');
}

/**
 * Format role for display
 */
function formatRole(role) {
  return role.replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase());
}
