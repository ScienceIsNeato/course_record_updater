// Authentication JavaScript - Form validation, password strength, and API integration

// Constants for input types to avoid hard-coded strings
const INPUT_TYPES = {
  PASSWORD: "password", // pragma: allowlist secret
  TEXT: "text",
};

const CONFIRM_PASSWORD_TARGETS = {
  confirmPassword: "password", // pragma: allowlist secret
  confirmNewPassword: "newPassword",
};

// CSRF Token Helper
function getCSRFToken() {
  // Try to get from form first
  const csrfInput = document.querySelector('input[name="csrf_token"]');
  if (csrfInput) {
    return csrfInput.value;
  }

  // Fallback to meta tag if available
  const csrfMeta = document.querySelector('meta[name="csrf-token"]');
  if (csrfMeta) {
    return csrfMeta.getAttribute("content");
  }

  return null;
}

// DOM Content Loaded
// Check if DOM is already loaded (script at end of body)
if (document.readyState === "loading") {
  // DOM hasn't loaded yet, wait for it
  document.addEventListener("DOMContentLoaded", () => {
    initializePage();
  });
} else {
  // DOM is already loaded (common when script is at end of body)
  initializePage();
}

// Page Initialization
function initializePage() {
  const currentPath = globalThis.location.pathname;

  // Check for URL parameter messages (e.g., ?message=Account+created+successfully)
  const urlParams = new URLSearchParams(globalThis.location.search);
  const messageParam = urlParams.get("message");
  if (messageParam) {
    showMessage(decodeURIComponent(messageParam), "success");
    // Clean up URL without reloading
    const url = new URL(globalThis.location);
    url.searchParams.delete("message");
    globalThis.history.replaceState({}, "", url);
  }

  // Check for login page (including /reminder-login)
  if (
    currentPath.includes("/login") ||
    currentPath.includes("/reminder-login")
  ) {
    initializeLoginForm();
  } else if (currentPath.includes("/register")) {
    initializeRegisterForm();
  } else if (currentPath.includes("/forgot-password")) {
    initializeForgotPasswordForm();
  } else if (currentPath.includes("/profile")) {
    initializeProfileForm();
  }

  // Initialize common features
  initializePasswordToggles();
  initializeFormValidation();
}

// Login Form
function initializeLoginForm() {
  const form = document.getElementById("loginForm");
  if (!form) return;

  // Prevent form from submitting normally (critical!)
  form.addEventListener("submit", handleLogin, { capture: true });

  // Also add a safety net to prevent any GET submissions
  form.method = "post";
  form.action = "#";

  // Real-time validation
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");

  if (emailInput) {
    emailInput.addEventListener("blur", validateEmail);
    emailInput.addEventListener("input", clearValidation);
  }

  if (passwordInput) {
    passwordInput.addEventListener("blur", validateRequired);
    passwordInput.addEventListener("input", clearValidation);
  }
}

// Register Form
function initializeRegisterForm() {
  const form = document.getElementById("registerForm");
  if (!form) return;

  form.addEventListener("submit", handleRegister);

  // --- MutationObserver for password field ---
  const attachPasswordListeners = () => {
    const passwordInput = document.getElementById("password");
    if (!passwordInput) return;
    // Remove previous listeners by cloning (safe for idempotency)
    const clone = passwordInput.cloneNode(true);
    passwordInput.parentNode.replaceChild(clone, passwordInput);
    clone.addEventListener("input", updatePasswordStrength);
    clone.addEventListener("blur", validatePassword);
    clone.addEventListener("change", updatePasswordStrength);
    clone.addEventListener("animationstart", (event) => {
      if (event.animationName === "authAutoFill") {
        updatePasswordStrength();
      }
    });
    monitorPasswordAutofill(clone);
  };
  attachPasswordListeners();

  // Observe for password field replacement
  const passwordFieldParent = document.getElementById("password")?.parentNode;
  if (passwordFieldParent) {
    const observer = new MutationObserver(() => {
      attachPasswordListeners();
    });
    observer.observe(passwordFieldParent, { childList: true, subtree: false });
  }

  // Confirm password validation
  const confirmPasswordInput = document.getElementById("confirmPassword");
  if (confirmPasswordInput) {
    confirmPasswordInput.addEventListener("input", validatePasswordMatch);
    confirmPasswordInput.addEventListener("blur", validatePasswordMatch);
  }

  // Terms checkbox validation
  const agreeTerms = document.getElementById("agreeTerms");
  const submitBtn = document.getElementById("registerBtn");
  if (agreeTerms && submitBtn) {
    agreeTerms.addEventListener("change", function () {
      submitBtn.disabled = !this.checked;
    });
  }

  // Real-time validation for all fields
  const inputs = form.querySelectorAll("input[required]");
  inputs.forEach((input) => {
    input.addEventListener("blur", function () {
      if (this.type === "email") {
        validateEmail.call(this);
      } else if (this.type === "url") {
        validateUrl.call(this);
      } else {
        validateRequired.call(this);
      }
    });
    input.addEventListener("input", clearValidation);
  });

  // Re-evaluate password state for pre-filled or auto-complete values
  updatePasswordStrength();
}

function monitorPasswordAutofill(input) {
  if (!input) return;

  let previousValue = input.value;
  let attempts = 0;

  const checkValue = () => {
    if (!input) return;

    const currentValue = input.value;
    if (currentValue && currentValue !== previousValue) {
      previousValue = currentValue;
      updatePasswordStrength(input.id);
    }

    attempts += 1;
    if (attempts < 6 && !currentValue) {
      setTimeout(checkValue, 120 * attempts);
    }
  };

  checkValue();
}

// Forgot Password Form
function initializeForgotPasswordForm() {
  const form = document.getElementById("forgotPasswordForm");
  if (!form) return;

  form.addEventListener("submit", handleForgotPassword);

  const emailInput = document.getElementById("email");
  if (emailInput) {
    emailInput.addEventListener("blur", validateEmail);
    emailInput.addEventListener("input", clearValidation);
  }
}

// Profile Form
function initializeProfileForm() {
  const profileForm = document.getElementById("profileForm");
  const passwordForm = document.getElementById("changePasswordForm");

  if (profileForm) {
    profileForm.addEventListener("submit", handleUpdateProfile);
  }

  if (passwordForm) {
    passwordForm.addEventListener("submit", handleChangePassword);

    // Password strength for new password
    const newPasswordInput = document.getElementById("newPassword");
    if (newPasswordInput) {
      newPasswordInput.addEventListener("input", function () {
        updatePasswordStrength.call(this, "newPassword");
      });
    }

    // Confirm password validation
    const confirmNewPasswordInput =
      document.getElementById("confirmNewPassword");
    if (confirmNewPasswordInput) {
      confirmNewPasswordInput.addEventListener("input", function () {
        validatePasswordMatch.call(this, "newPassword", "confirmNewPassword");
      });
    }
  }
}

// Password Toggle Functionality
function initializePasswordToggles() {
  const toggleButtons = document.querySelectorAll('[id^="toggle"]');

  toggleButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();

      const targetId = this.id.replace("toggle", "").toLowerCase();
      const passwordInput =
        document.getElementById(targetId) ||
        document.getElementById(targetId.replace("password", "Password"));
      const icon = this.querySelector("i");

      if (passwordInput && icon) {
        if (passwordInput.type === INPUT_TYPES.PASSWORD) {
          passwordInput.type = INPUT_TYPES.TEXT;
          icon.className = "fas fa-eye-slash";
        } else {
          passwordInput.type = INPUT_TYPES.PASSWORD;
          icon.className = "fas fa-eye";
        }
      }
    });
  });
}

// Form Validation
function initializeFormValidation() {
  // Disable HTML5 validation, use custom validation
  const forms = document.querySelectorAll("form[novalidate]");
  forms.forEach((form) => {
    form.addEventListener("submit", function (e) {
      if (!this.checkValidity()) {
        e.preventDefault();
        e.stopPropagation();
      }
      this.classList.add("was-validated");
    });
  });
}

// Validation Functions
function validateEmail() {
  const email = this.value.trim();
  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

  if (!email) {
    setValidationState(this, false, "Email is required");
    return false;
  } else if (!emailRegex.test(email)) {
    setValidationState(this, false, "Please enter a valid email address");
    return false;
  } else {
    setValidationState(this, true);
    return true;
  }
}

function validateRequired() {
  const value = this.value.trim();
  const fieldName = this.getAttribute("name") || this.getAttribute("id");

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
    setValidationState(this, false, "Please enter a valid URL");
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
    setValidationState(this, false, "Password is required");
    return false;
  } else if (strength.score < 3) {
    setValidationState(this, false, "Password is too weak");
    return false;
  } else {
    setValidationState(this, true);
    return true;
  }
}

function validatePasswordMatch(
  primaryId = "password",
  confirmId = "confirmPassword",
) {
  const primaryPassword = document.getElementById(primaryId);
  const confirmPassword = document.getElementById(confirmId);

  if (!primaryPassword || !confirmPassword) return false;

  if (
    confirmPassword.value &&
    confirmPassword.value !== primaryPassword.value
  ) {
    setValidationState(confirmPassword, false, "Passwords do not match");
    return false;
  } else if (confirmPassword.value) {
    setValidationState(confirmPassword, true);
    return true;
  }
  return false;
}

function setValidationState(input, isValid, message = "") {
  const feedback = input.parentNode.querySelector(".invalid-feedback");

  input.classList.remove("is-valid", "is-invalid");
  input.classList.add(isValid ? "is-valid" : "is-invalid");

  if (feedback) {
    feedback.textContent = message;
  }
}

function clearValidation() {
  this.classList.remove("is-valid", "is-invalid");
}

// Password Strength
function updatePasswordStrength(inputId = "password") {
  const passwordInput = document.getElementById(inputId);
  if (!passwordInput) {
    return;
  }
  const password = passwordInput.value;
  const strength = getPasswordStrength(password);

  const fillElement =
    document.getElementById(inputId + "StrengthFill") ||
    document.getElementById("passwordStrengthFill");
  const labelElement =
    document.getElementById(inputId + "StrengthLabel") ||
    document.getElementById("passwordStrengthLabel");

  if (fillElement) {
    fillElement.className = `password-strength-fill ${strength.level}`;
  }

  if (labelElement) {
    labelElement.textContent = strength.label;
    labelElement.className = `strength-${strength.level}`;
  }

  updatePasswordRequirements(password);
}

// Update password requirements checklist (for UI and tests)
function updatePasswordRequirements(password) {
  // Map of requirement id to test function
  const requirements = {
    "req-length": (pw) => pw && pw.length >= 8,
    "req-uppercase": (pw) => /[A-Z]/.test(pw),
    "req-lowercase": (pw) => /[a-z]/.test(pw),
    "req-number": (pw) => /[0-9]/.test(pw),
    "req-special": (pw) => /[^A-Za-z0-9]/.test(pw),
  };
  Object.entries(requirements).forEach(([id, test]) => {
    const el = document.getElementById(id);
    if (el) {
      if (test(password)) {
        el.classList.add("met");
        el.classList.remove("unmet");
      } else {
        el.classList.remove("met");
        el.classList.add("unmet");
      }
    }
  });
}

// Password strength indicator initialization on page load
document.addEventListener("DOMContentLoaded", () => {
  // Initialize password strength for all relevant fields
  const passwordFields = ["password", "newPassword"];
  passwordFields.forEach((fieldId) => {
    const field = document.getElementById(fieldId);
    if (field) {
      updatePasswordStrength(fieldId);
    }
  });
});

function getPasswordStrength(password) {
  if (!password) {
    return { score: 0, level: "weak", label: "Enter password" };
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
    0: { level: "weak", label: "Too weak" },
    1: { level: "weak", label: "Weak" },
    2: { level: "weak", label: "Weak" },
    3: { level: "fair", label: "Fair" },
    4: { level: "fair", label: "Fair" },
    5: { level: "good", label: "Good" },
    6: { level: "good", label: "Good" },
    7: { level: "strong", label: "Strong" },
    8: { level: "strong", label: "Very Strong" },
  };

  return { score, ...levels[Math.min(score, 8)] };
}

// Generic async form submission handler to reduce duplication
async function submitAuthForm(config) {
  const {
    form,
    submitBtn,
    endpoint,
    requestData,
    onSuccess,
    onError = null,
  } = config;
  if (!validateForm(form)) {
    return;
  }

  setLoadingState(submitBtn, true);

  try {
    const csrfToken = getCSRFToken();
    if (!csrfToken) {
      showError(
        "Security token missing. Please refresh the page and try again.",
      );
      setLoadingState(submitBtn, false);
      return;
    }

    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify(requestData),
    });

    let result;
    try {
      result = await response.json();
    } catch (parseError) {
      console.error("Failed to parse response:", parseError); // eslint-disable-line no-console
      showError("Server returned an invalid response. Please try again.");
      setLoadingState(submitBtn, false);
      return;
    }

    if (response.ok && result.success) {
      onSuccess(result);
    } else if (onError) {
      onError(response, result);
    } else {
      const errorMsg =
        result.error ||
        result.message ||
        `Request failed with status ${response.status}`;
      showError(errorMsg);
    }
  } catch (error) {
    // nosemgrep
    console.error(`${endpoint} error:`, error); // eslint-disable-line no-console
    showError(
      `Network error: ${error.message || "Please check your connection and try again."}`,
    );
  } finally {
    setLoadingState(submitBtn, false);
  }
}

// Form Submission Handlers
async function handleLogin(e) {
  e.preventDefault();
  e.stopPropagation();

  const form = e.target;
  const submitBtn = document.getElementById("loginBtn");
  const formData = new FormData(form);

  await submitAuthForm({
    form,
    submitBtn,
    endpoint: "/api/auth/login",
    requestData: {
      email: formData.get("email"),
      password: formData.get("password"),
      remember_me: formData.get("rememberMe") === "on",
    },
    onSuccess: (result) => {
      // Redirect immediately - being on the dashboard IS the success indicator
      // No need to show message and force user to wait
      const redirectUrl = result.next_url || "/dashboard";
      globalThis.location.href = redirectUrl;
    },
    onError: (response, result) => {
      if (response.status === 423) {
        showAccountLockout();
      } else {
        // More detailed error messages
        const errorMsg =
          result.error ||
          result.message ||
          "Login failed. Please check your credentials and try again.";
        console.error("Login error:", response.status, result); // eslint-disable-line no-console
        showError(errorMsg);
      }
    },
  });
}

async function handleRegister(e) {
  e.preventDefault();

  const form = e.target;
  const submitBtn = document.getElementById("registerBtn");
  const formData = new FormData(form);

  await submitAuthForm({
    form,
    submitBtn,
    endpoint: "/api/auth/register",
    requestData: {
      email: formData.get("email"),
      password: formData.get("password"),
      first_name: formData.get("firstName"),
      last_name: formData.get("lastName"),
      institution_name: formData.get("institutionName"),
      institution_website: formData.get("institutionWebsite") || null,
    },
    onSuccess: () => {
      // Redirect immediately with success message as query parameter
      // The login page will display the message
      const message = encodeURIComponent(
        "Account created! Please check your email for the verification link before attempting to log in.",
      );
      globalThis.location.href = `/login?message=${message}`;
    },
    onError: (response, result) => {
      // Show backend error message if available, else fallback to status message
      let errorMsg = null;
      if (result && (result.error || result.message)) {
        errorMsg = result.error || result.message;
      } else {
        errorMsg = `Request failed with status ${response.status}`;
      }
      showError(errorMsg);
    },
  });
}

async function handleForgotPassword(e) {
  e.preventDefault();

  const form = e.target;
  const submitBtn = document.getElementById("resetBtn");
  const formData = new FormData(form);
  const successState = document.getElementById("successState");

  if (!validateForm(form)) {
    return;
  }

  setLoadingState(submitBtn, true);

  try {
    const response = await fetch("/api/auth/forgot-password", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({
        email: formData.get("email"),
      }),
    });

    const result = await response.json();

    if (response.ok && result.success) {
      form.style.display = "none";
      if (successState) {
        successState.classList.remove("d-none");
        successState.classList.add("fade-in");
      }
    } else {
      showError(
        result.error || "Failed to send reset instructions. Please try again.",
      );
    }
  } catch (error) {
    console.error("Forgot password error:", error); // eslint-disable-line no-console
    showError("Network error. Please try again.");
  } finally {
    setLoadingState(submitBtn, false);
  }
}

// Utility Functions
function validateForm(form) {
  const inputs = form.querySelectorAll("input[required]");
  let isValid = true;

  inputs.forEach((input) => {
    let fieldValid = false;

    if (input.type === "email") {
      fieldValid = validateEmail.call(input);
    } else if (input.type === "password" && input.id === "password") {
      fieldValid = validatePassword.call(input);
    } else if (
      input.type === "password" &&
      input.id.toLowerCase().includes("confirm")
    ) {
      const primaryId =
        CONFIRM_PASSWORD_TARGETS[input.id] ||
        input.dataset.primaryPassword ||
        "password";
      fieldValid = validatePasswordMatch(primaryId, input.id);
    } else if (input.type === "url") {
      fieldValid = validateUrl.call(input);
    } else if (input.type === "checkbox") {
      fieldValid = input.checked;
      if (!fieldValid) {
        setValidationState(input, false, "This field is required");
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
    button.classList.add("loading");
    button.disabled = true;
  } else {
    button.classList.remove("loading");
    button.disabled = false;
  }
}

function showError(message) {
  showMessage(message, "error");
}

function showSuccess(message) {
  showMessage(message, "success");
}

function showMessage(message, type) {
  // Remove existing messages
  const existingMessages = document.querySelectorAll(".auth-message-dynamic");
  existingMessages.forEach((msg) => msg.remove());

  // Create new message
  const messageDiv = document.createElement("div");
  messageDiv.className = `alert alert-${type === "error" ? "danger" : "success"} alert-dismissible fade show auth-message-dynamic`;

  // Use textContent to prevent XSS attacks
  const messageText = document.createTextNode(message);
  messageDiv.appendChild(messageText);

  // Add close button safely
  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.className = "btn-close";
  closeButton.dataset.bsDismiss = "alert";
  closeButton.ariaLabel = "Close";
  messageDiv.appendChild(closeButton);

  // Insert at top of form
  const form = document.querySelector(".auth-form");
  if (form) {
    form.insertBefore(messageDiv, form.firstChild);
    messageDiv.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function showAccountLockout() {
  const modal = document.getElementById("lockoutModal");
  if (modal) {
    // eslint-disable-next-line no-new
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
  } else {
    showError(
      "Account is temporarily locked due to multiple failed login attempts. Please try again later.",
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
  if (confirm("Are you sure you want to sign out?")) {
    fetch("/api/auth/logout", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
    })
      .then(() => {
        globalThis.location.href = "/login";
      })
      .catch(() => {
        globalThis.location.href = "/login";
      });
  }
}

// Show login modal function for main page
function showLogin() {
  globalThis.location.href = "/login";
}

// Profile management functions
// Profile management functions
async function handleUpdateProfile(event) {
  event.preventDefault();

  const form = document.getElementById("profileForm");
  const btn = document.getElementById("updateProfileBtn");
  const btnText = btn.querySelector(".btn-text");
  const btnSpinner = btn.querySelector(".btn-spinner");

  // Validate form
  if (!validateForm(form)) {
    return;
  }

  // Disable button and show spinner
  btn.disabled = true;
  btnText.classList.add("d-none");
  btnSpinner.classList.remove("d-none");

  const firstName = document.getElementById("firstName").value;
  const lastName = document.getElementById("lastName").value;

  try {
    const response = await fetch("/api/auth/profile", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({
        first_name: firstName,
        last_name: lastName,
      }),
    });

    const data = await response.json();

    if (response.ok && data.success) {
      showMessage(data.message || "Profile updated successfully", "success");
      // Update displayed name if present in navbar
      const navbarName = document.querySelector(
        ".navbar .nav-link i.fa-user-circle",
      )?.nextSibling;
      if (navbarName) {
        navbarName.textContent = ` ${firstName} ${lastName}`;
      }
    } else {
      showMessage(data.error || "Failed to update profile", "error");
    }
  } catch (error) {
    console.error("Profile update error:", error);
    showMessage("An unexpected error occurred. Please try again.", "error");
  } finally {
    // Reset button state
    btn.disabled = false;
    btnText.classList.remove("d-none");
    btnSpinner.classList.add("d-none");
  }
}

async function handleChangePassword(event) {
  event.preventDefault();

  const form = document.getElementById("changePasswordForm");
  const btn = document.getElementById("changePasswordBtn");
  const btnText = btn.querySelector(".btn-text");
  const btnSpinner = btn.querySelector(".btn-spinner");

  // Validate form
  if (!validateForm(form)) {
    return;
  }

  // Validate password match
  const newPassword = document.getElementById("newPassword");
  const confirmNewPassword = document.getElementById("confirmNewPassword");

  if (newPassword.value !== confirmNewPassword.value) {
    setValidationState(confirmNewPassword, false, "Passwords do not match");
    return;
  }

  // Disable button and show spinner
  btn.disabled = true;
  btnText.classList.add("d-none");
  btnSpinner.classList.remove("d-none");

  try {
    const response = await fetch("/api/auth/change-password", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({
        current_password: document.getElementById("currentPassword").value,
        new_password: newPassword.value,
      }),
    });

    const data = await response.json();

    if (response.ok && data.success) {
      showMessage(data.message || "Password changed successfully", "success");
      form.reset();
      // Reset strength indicator
      const strengthFill = document.getElementById("newPasswordStrengthFill");
      const strengthLabel = document.getElementById("newPasswordStrengthLabel");
      if (strengthFill) strengthFill.className = "password-strength-fill";
      if (strengthLabel) strengthLabel.textContent = "Enter password";
    } else {
      showMessage(data.error || "Failed to change password", "error");
    }
  } catch (error) {
    console.error("Password change error:", error);
    showMessage("An unexpected error occurred. Please try again.", "error");
  } finally {
    // Reset button state
    btn.disabled = false;
    btnText.classList.remove("d-none");
    btnSpinner.classList.add("d-none");
  }
}

// System Date Override handlers (admin-only feature)
function initializeDateOverride() {
  const setBtn = document.getElementById("setDateOverrideBtn");
  const clearBtn = document.getElementById("clearDateOverrideBtn");
  const dateInput = document.getElementById("systemDateOverride");
  const overrideBanner = document.getElementById("activeOverrideDisplay");
  const overrideBannerBody = overrideBanner?.querySelector(
    ".override-banner-body",
  );
  const overridePrefix =
    overrideBanner?.dataset?.prefix || "Date Override Mode";

  if (setBtn && dateInput) {
    setBtn.addEventListener("click", async () => {
      const dateValue = dateInput.value;
      if (!dateValue) {
        showError("Please select a date and time");
        return;
      }

      try {
        setLoadingState(setBtn, true);
        const response = await fetch("/api/profile/system-date", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
          },
          body: JSON.stringify({ date: new Date(dateValue).toISOString() }),
        });

        const result = await response.json();
        if (response.ok && result.success) {
          showSuccess("System date override set. Refreshing...");

          if (overrideBanner && overrideBannerBody) {
            const formattedDate = new Intl.DateTimeFormat(undefined, {
              year: "numeric",
              month: "long",
              day: "2-digit",
              hour: "2-digit",
              minute: "2-digit",
              timeZoneName: "short",
            }).format(new Date(dateValue));

            overrideBanner.classList.remove("d-none");
            overrideBannerBody.textContent = "";

            const prefixEl = document.createElement("strong");
            prefixEl.textContent = `${overridePrefix}:`;
            overrideBannerBody.appendChild(prefixEl);

            const textEl = document.createElement("span");
            textEl.textContent = ` Viewing data as of ${formattedDate}.`;
            overrideBannerBody.appendChild(textEl);
          }

          if (clearBtn) {
            clearBtn.disabled = false;
          }

          if (result.force_refresh) {
            setTimeout(() => window.location.reload(), 1000);
          }
        } else {
          showError(result.error || "Failed to set date override");
        }
      } catch (err) {
        showError("Network error: " + err.message);
      } finally {
        setLoadingState(setBtn, false);
      }
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", async () => {
      try {
        setLoadingState(clearBtn, true);
        const response = await fetch("/api/profile/system-date", {
          method: "DELETE",
          headers: {
            "X-CSRFToken": getCSRFToken(),
          },
        });

        const result = await response.json();
        if (response.ok && result.success) {
          showSuccess("System date reset to live. Refreshing...");

          if (overrideBanner && overrideBannerBody) {
            overrideBanner.classList.add("d-none");
            overrideBannerBody.textContent = "";

            const prefixEl = document.createElement("strong");
            prefixEl.textContent = `${overridePrefix}:`;
            overrideBannerBody.appendChild(prefixEl);

            const textEl = document.createElement("span");
            textEl.textContent = " Using the current system time.";
            overrideBannerBody.appendChild(textEl);
          }

          if (dateInput) {
            dateInput.value = "";
          }

          if (clearBtn) {
            clearBtn.disabled = true;
          }

          if (result.force_refresh) {
            setTimeout(() => window.location.reload(), 1000);
          }
        } else {
          showError(result.error || "Failed to clear date override");
        }
      } catch (err) {
        showError("Network error: " + err.message);
      } finally {
        setLoadingState(clearBtn, false);
      }
    });
  }
}

// Add date override initialization to page init
const originalInitializePage =
  typeof globalThis.initializePage === "function"
    ? globalThis.initializePage.bind(globalThis)
    : () => {};

function enhancedInitializePage() {
  originalInitializePage();
  initializeDateOverride();
}

globalThis.initializePage = enhancedInitializePage;

// Export functions for global use
globalThis.logout = logout;
globalThis.showLogin = showLogin;

const authTestExports = {
  initializePage,
  initializeLoginForm,
  initializeRegisterForm,
  initializeForgotPasswordForm,
  initializeProfileForm,
  initializePasswordToggles,
  initializeFormValidation,
  validateEmail,
  validateRequired,
  validateUrl,
  validatePassword,
  validatePasswordMatch,
  setValidationState,
  clearValidation,
  updatePasswordStrength,
  getPasswordStrength,
  handleLogin,
  handleRegister,
  handleForgotPassword,
  validateForm,
  setLoadingState,
  showError,
  showSuccess,
  showMessage,
  showAccountLockout,
  isValidUrl,
  logout,
  showLogin,
};

if (typeof module !== "undefined" && module.exports) {
  // Add updatePasswordRequirements for test access
  authTestExports.updatePasswordRequirements = updatePasswordRequirements;
  module.exports = authTestExports;
}
