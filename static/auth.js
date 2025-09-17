// Authentication JavaScript - Form validation, password strength, and API integration


// DOM Content Loaded
document.addEventListener('DOMContentLoaded', () => {

  // Initialize based on current page
  initializePage();
});

// Page Initialization
function initializePage() {
  const currentPath = window.location.pathname;

  if (currentPath.includes('/login')) {
    initializeLoginForm();
  } else if (currentPath.includes('/register')) {
    initializeRegisterForm();
  } else if (currentPath.includes('/forgot-password')) {
    initializeForgotPasswordForm();
  } else if (currentPath.includes('/profile')) {
    initializeProfileForm();
  }

  // Initialize common features
  initializePasswordToggles();
  initializeFormValidation();
}

// Login Form
function initializeLoginForm() {
  const form = document.getElementById('loginForm');
  if (!form) return;

  form.addEventListener('submit', handleLogin);

  // Real-time validation
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');

  if (emailInput) {
    emailInput.addEventListener('blur', validateEmail);
    emailInput.addEventListener('input', clearValidation);
  }

  if (passwordInput) {
    passwordInput.addEventListener('blur', validateRequired);
    passwordInput.addEventListener('input', clearValidation);
  }
}

// Register Form
function initializeRegisterForm() {
  const form = document.getElementById('registerForm');
  if (!form) return;

  form.addEventListener('submit', handleRegister);

  // Password strength indicator
  const passwordInput = document.getElementById('password');
  if (passwordInput) {
    passwordInput.addEventListener('input', updatePasswordStrength);
    passwordInput.addEventListener('blur', validatePassword);
  }

  // Confirm password validation
  const confirmPasswordInput = document.getElementById('confirmPassword');
  if (confirmPasswordInput) {
    confirmPasswordInput.addEventListener('input', validatePasswordMatch);
    confirmPasswordInput.addEventListener('blur', validatePasswordMatch);
  }

  // Terms checkbox validation
  const agreeTerms = document.getElementById('agreeTerms');
  const submitBtn = document.getElementById('registerBtn');
  if (agreeTerms && submitBtn) {
    agreeTerms.addEventListener('change', function() {
      submitBtn.disabled = !this.checked;
    });
  }

  // Real-time validation for all fields
  const inputs = form.querySelectorAll('input[required]');
  inputs.forEach(input => {
    input.addEventListener('blur', function() {
      if (this.type === 'email') {
        validateEmail.call(this);
      } else if (this.type === 'url') {
        validateUrl.call(this);
      } else {
        validateRequired.call(this);
      }
    });
    input.addEventListener('input', clearValidation);
  });
}

// Forgot Password Form
function initializeForgotPasswordForm() {
  const form = document.getElementById('forgotPasswordForm');
  if (!form) return;

  form.addEventListener('submit', handleForgotPassword);

  const emailInput = document.getElementById('email');
  if (emailInput) {
    emailInput.addEventListener('blur', validateEmail);
    emailInput.addEventListener('input', clearValidation);
  }
}

// Profile Form
function initializeProfileForm() {
  const profileForm = document.getElementById('profileForm');
  const passwordForm = document.getElementById('changePasswordForm');

  if (profileForm) {
    profileForm.addEventListener('submit', handleUpdateProfile);
  }

  if (passwordForm) {
    passwordForm.addEventListener('submit', handleChangePassword);

    // Password strength for new password
    const newPasswordInput = document.getElementById('newPassword');
    if (newPasswordInput) {
      newPasswordInput.addEventListener('input', function() {
        updatePasswordStrength.call(this, 'newPassword');
      });
    }

    // Confirm password validation
    const confirmNewPasswordInput = document.getElementById('confirmNewPassword');
    if (confirmNewPasswordInput) {
      confirmNewPasswordInput.addEventListener('input', function() {
        validatePasswordMatch.call(this, 'newPassword', 'confirmNewPassword');
      });
    }
  }
}

// Password Toggle Functionality
function initializePasswordToggles() {
  const toggleButtons = document.querySelectorAll('[id^="toggle"]');

  toggleButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();

      const targetId = this.id.replace('toggle', '').toLowerCase();
      const passwordInput =
        document.getElementById(targetId) ||
        document.getElementById(targetId.replace('password', 'Password'));
      const icon = this.querySelector('i');

      if (passwordInput && icon) {
        if (passwordInput.type === 'password') {
          passwordInput.type = 'text';
          icon.className = 'fas fa-eye-slash';
        } else {
          passwordInput.type = 'password';
          icon.className = 'fas fa-eye';
        }
      }
    });
  });
}

// Form Validation
function initializeFormValidation() {
  // Disable HTML5 validation, use custom validation
  const forms = document.querySelectorAll('form[novalidate]');
  forms.forEach(form => {
    form.addEventListener('submit', function(e) {
      if (!this.checkValidity()) {
        e.preventDefault();
        e.stopPropagation();
      }
      this.classList.add('was-validated');
    });
  });
}

// Validation Functions
function validateEmail() {
  const email = this.value.trim();
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  if (!email) {
    setValidationState(this, false, 'Email is required');
    return false;
  } else if (!emailRegex.test(email)) {
    setValidationState(this, false, 'Please enter a valid email address');
    return false;
  } else {
    setValidationState(this, true);
    return true;
  }
}

function validateRequired() {
  const value = this.value.trim();
  const fieldName = this.getAttribute('name') || this.getAttribute('id');

  if (!value) {
    setValidationState(this, false, `${fieldName} is required`);
    return false;
  } else {
    setValidationState(this, true);
    return true;
  }
}

function validateUrl() {
  const url = this.value.trim();

  if (url && !isValidUrl(url)) {
    setValidationState(this, false, 'Please enter a valid URL');
    return false;
  } else {
    setValidationState(this, true);
    return true;
  }
}

function validatePassword() {
  const password = this.value;
  const strength = getPasswordStrength(password);

  if (!password) {
    setValidationState(this, false, 'Password is required');
    return false;
  } else if (strength.score < 3) {
    setValidationState(this, false, 'Password is too weak');
    return false;
  } else {
    setValidationState(this, true);
    return true;
  }
}

function validatePasswordMatch(primaryId = 'password', confirmId = 'confirmPassword') {
  const primaryPassword = document.getElementById(primaryId);
  const confirmPassword = document.getElementById(confirmId);

  if (!primaryPassword || !confirmPassword) return false;

  if (confirmPassword.value && confirmPassword.value !== primaryPassword.value) {
    setValidationState(confirmPassword, false, 'Passwords do not match');
    return false;
  } else if (confirmPassword.value) {
    setValidationState(confirmPassword, true);
    return true;
  }
  return false;
}

function setValidationState(input, isValid, message = '') {
  const feedback = input.parentNode.querySelector('.invalid-feedback');

  input.classList.remove('is-valid', 'is-invalid');
  input.classList.add(isValid ? 'is-valid' : 'is-invalid');

  if (feedback) {
    feedback.textContent = message;
  }
}

function clearValidation() {
  this.classList.remove('is-valid', 'is-invalid');
}

// Password Strength
function updatePasswordStrength(inputId = 'password') {
  const passwordInput = document.getElementById(inputId);
  const password = passwordInput.value;
  const strength = getPasswordStrength(password);

  const fillElement =
    document.getElementById(inputId + 'StrengthFill') ||
    document.getElementById('passwordStrengthFill');
  const labelElement =
    document.getElementById(inputId + 'StrengthLabel') ||
    document.getElementById('passwordStrengthLabel');

  if (fillElement) {
    fillElement.className = `password-strength-fill ${strength.level}`;
  }

  if (labelElement) {
    labelElement.textContent = strength.label;
    labelElement.className = `strength-${strength.level}`;
  }

  // Update requirements if on register page
  updatePasswordRequirements(password);
}

function getPasswordStrength(password) {
  if (!password) {
    return { score: 0, level: 'weak', label: 'Enter password' };
  }

  let score = 0;

  // Length check
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;

  // Character variety
  if (/[a-z]/.test(password)) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/[0-9]/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  // Pattern checks
  if (!/(.)\1{2,}/.test(password)) score += 1; // No repeated characters
  if (!/123|abc|qwe/i.test(password)) score += 1; // No common sequences

  const levels = {
    0: { level: 'weak', label: 'Too weak' },
    1: { level: 'weak', label: 'Weak' },
    2: { level: 'weak', label: 'Weak' },
    3: { level: 'fair', label: 'Fair' },
    4: { level: 'fair', label: 'Fair' },
    5: { level: 'good', label: 'Good' },
    6: { level: 'good', label: 'Good' },
    7: { level: 'strong', label: 'Strong' },
    8: { level: 'strong', label: 'Very Strong' }
  };

  return { score, ...levels[Math.min(score, 8)] };
}

function updatePasswordRequirements(password) {
  const requirements = [
    { id: 'req-length', test: password.length >= 8 },
    { id: 'req-uppercase', test: /[A-Z]/.test(password) },
    { id: 'req-lowercase', test: /[a-z]/.test(password) },
    { id: 'req-number', test: /[0-9]/.test(password) }
  ];

  requirements.forEach(req => {
    const element = document.getElementById(req.id);
    if (element) {
      const icon = element.querySelector('i');
      if (req.test) {
        element.classList.add('met');
        if (icon) {
          icon.className = 'fas fa-check text-success';
        }
      } else {
        element.classList.remove('met');
        if (icon) {
          icon.className = 'fas fa-times text-danger';
        }
      }
    }
  });
}

// Form Submission Handlers
async function handleLogin(e) {
  e.preventDefault();

  const form = e.target;
  const submitBtn = document.getElementById('loginBtn');
  const formData = new FormData(form);

  // Validate form
  if (!validateForm(form)) {
    return;
  }

  setLoadingState(submitBtn, true);

  try {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        email: formData.get('email'),
        password: formData.get('password'),
        remember_me: formData.get('rememberMe') === 'on'
      })
    });

    const result = await response.json();

    if (response.ok && result.success) {
      showSuccess('Login successful! Redirecting...');
      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 1000);
    } else {
      if (response.status === 423) {
        showAccountLockout();
      } else {
        showError(result.error || 'Login failed. Please try again.');
      }
    }
  } catch (error) {
    console.error('Login error:', error);
    showError('Network error. Please try again.');
  } finally {
    setLoadingState(submitBtn, false);
  }
}

async function handleRegister(e) {
  e.preventDefault();

  const form = e.target;
  const submitBtn = document.getElementById('registerBtn');
  const formData = new FormData(form);

  // Validate form
  if (!validateForm(form)) {
    return;
  }

  setLoadingState(submitBtn, true);

  try {
    const response = await fetch('/api/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        email: formData.get('email'),
        password: formData.get('password'),
        first_name: formData.get('firstName'),
        last_name: formData.get('lastName'),
        institution_name: formData.get('institutionName'),
        institution_website: formData.get('institutionWebsite') || null
      })
    });

    const result = await response.json();

    if (response.ok && result.success) {
      showSuccess('Account created successfully! Please check your email to verify your account.');
      setTimeout(() => {
        window.location.href = '/login';
      }, 3000);
    } else {
      showError(result.error || 'Registration failed. Please try again.');
    }
  } catch (error) {
    console.error('Registration error:', error);
    showError('Network error. Please try again.');
  } finally {
    setLoadingState(submitBtn, false);
  }
}

async function handleForgotPassword(e) {
  e.preventDefault();

  const form = e.target;
  const submitBtn = document.getElementById('resetBtn');
  const formData = new FormData(form);
  const successState = document.getElementById('successState');

  if (!validateForm(form)) {
    return;
  }

  setLoadingState(submitBtn, true);

  try {
    const response = await fetch('/api/auth/forgot-password', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        email: formData.get('email')
      })
    });

    const result = await response.json();

    if (response.ok && result.success) {
      form.style.display = 'none';
      if (successState) {
        successState.classList.remove('d-none');
        successState.classList.add('fade-in');
      }
    } else {
      showError(result.error || 'Failed to send reset instructions. Please try again.');
    }
  } catch (error) {
    console.error('Forgot password error:', error);
    showError('Network error. Please try again.');
  } finally {
    setLoadingState(submitBtn, false);
  }
}

// Utility Functions
function validateForm(form) {
  const inputs = form.querySelectorAll('input[required]');
  let isValid = true;

  inputs.forEach(input => {
    let fieldValid = false;

    if (input.type === 'email') {
      fieldValid = validateEmail.call(input);
    } else if (input.type === 'password' && input.id === 'password') {
      fieldValid = validatePassword.call(input);
    } else if (input.type === 'password' && input.id.includes('confirm')) {
      fieldValid = validatePasswordMatch();
    } else if (input.type === 'url') {
      fieldValid = validateUrl.call(input);
    } else if (input.type === 'checkbox') {
      fieldValid = input.checked;
      if (!fieldValid) {
        setValidationState(input, false, 'This field is required');
      }
    } else {
      fieldValid = validateRequired.call(input);
    }

    if (!fieldValid) {
      isValid = false;
    }
  });

  return isValid;
}

function setLoadingState(button, loading) {
  if (loading) {
    button.classList.add('loading');
    button.disabled = true;
  } else {
    button.classList.remove('loading');
    button.disabled = false;
  }
}

function showError(message) {
  showMessage(message, 'error');
}

function showSuccess(message) {
  showMessage(message, 'success');
}

function showMessage(message, type) {
  // Remove existing messages
  const existingMessages = document.querySelectorAll('.auth-message-dynamic');
  existingMessages.forEach(msg => msg.remove());

  // Create new message
  const messageDiv = document.createElement('div');
  messageDiv.className = `alert alert-${type === 'error' ? 'danger' : 'success'} alert-dismissible fade show auth-message-dynamic`;
  messageDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

  // Insert at top of form
  const form = document.querySelector('.auth-form');
  if (form) {
    form.insertBefore(messageDiv, form.firstChild);
    messageDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

function showAccountLockout() {
  const modal = document.getElementById('lockoutModal');
  if (modal) {
    // eslint-disable-next-line no-new
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
  } else {
    showError(
      'Account is temporarily locked due to multiple failed login attempts. Please try again later.'
    );
  }
}

function isValidUrl(string) {
  try {
    // eslint-disable-next-line no-new
    new URL(string);
    return true;
  } catch (_) {
    return false;
  }
}

// Global logout function
function logout() {
  if (confirm('Are you sure you want to sign out?')) {
    fetch('/api/auth/logout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })
      .then(() => {
        window.location.href = '/login';
      })
      .catch(() => {
        window.location.href = '/login';
      });
  }
}

// Show login modal function for main page
function showLogin() {
  window.location.href = '/login';
}

// Profile management functions
function handleUpdateProfile(event) {
  event.preventDefault();
  // TODO: Implement profile update
}

function handleChangePassword(event) {
  event.preventDefault();
  // TODO: Implement password change
}

// Export functions for global use
window.logout = logout;
window.showLogin = showLogin;
