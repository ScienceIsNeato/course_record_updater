/**
 * Shared Management Utilities for CRUD Operations
 *
 * Common patterns used across courseManagement.js, offeringManagement.js,
 * termManagement.js, programManagement.js, etc.
 */

/**
 * Generic function to load options into a select element
 * @param {string} selectId - ID of the select element
 * @param {string} apiEndpoint - API endpoint to fetch data from
 * @param {Function} mapFn - Function to map API data to {value, label} objects
 * @param {string} emptyText - Text to show when no options available
 */
async function loadSelectOptions(
  selectId,
  apiEndpoint,
  mapFn,
  emptyText = "No options available",
) {
  const select = document.getElementById(selectId);
  if (!select) return;

  select.innerHTML = '<option value="">Loading...</option>'; // nosemgrep
  select.disabled = true;

  try {
    const response = await fetch(apiEndpoint, {
      credentials: "include",
      headers: {
        Accept: "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to load data from ${apiEndpoint}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || "Failed to load data");
    }

    // Get the array from the response (might be in different keys)
    const items = Object.values(data).find(Array.isArray) || [];

    if (items.length === 0) {
      select.innerHTML = `<option value="">${emptyText}</option>`; // nosemgrep
    } else {
      const options = items.map(mapFn);
      select.innerHTML = // nosemgrep
        '<option value="">-- Select --</option>' +
        options
          .map((opt) => `<option value="${opt.value}">${opt.label}</option>`)
          .join("");
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(`Error loading ${selectId}:`, error); // nosemgrep
    select.innerHTML = '<option value="">Error loading options</option>'; // nosemgrep
  } finally {
    select.disabled = false;
  }
}

/**
 * Generic CRUD form submission handler
 * @param {Object} config - Configuration object
 * @param {HTMLFormElement} config.form - The form element
 * @param {string} config.endpoint - API endpoint
 * @param {string} config.method - HTTP method (POST, PUT, PATCH, DELETE)
 * @param {Object} config.data - Data to send
 * @param {Function} config.onSuccess - Success callback
 * @param {Function} config.onError - Optional error callback
 */
async function submitCRUDForm(config) {
  const { endpoint, method = "POST", data, onSuccess, onError = null } = config;

  try {
    const response = await fetch(endpoint, {
      method,
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "include",
      body: JSON.stringify(data),
    });

    const result = await response.json();

    if (response.ok && result.success) {
      onSuccess(result);
    } else if (onError) {
      onError(response, result);
    } else {
      showError(result.error || "Operation failed. Please try again.");
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(`${endpoint} error:`, error); // nosemgrep
    if (onError) {
      onError(null, { error: error.message });
    } else {
      showError("Network error. Please try again.");
    }
  }
}

/**
 * Get CSRF token from page meta tag or cookie
 * @returns {string} CSRF token
 */
function getCSRFToken() {
  // Try meta tag first
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta) {
    return meta.getAttribute("content");
  }

  // Fallback to cookie
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  return match ? match[1] : "";
}

/**
 * Show success message (requires Bootstrap toast or similar)
 * @param {string} message - Success message
 */
function showSuccess(message) {
  // Try to use existing showMessage if available
  if (typeof globalThis.showMessage === "function") {
    globalThis.showMessage(message, "success");
    return;
  }

  // Fallback to basic alert
  // eslint-disable-next-line no-alert
  alert(message);
}

/**
 * Show error message (requires Bootstrap toast or similar)
 * @param {string} message - Error message
 */
function showError(message) {
  // Try to use existing showMessage if available
  if (typeof globalThis.showMessage === "function") {
    globalThis.showMessage(message, "danger");
    return;
  }

  // Fallback to console + alert
  // eslint-disable-next-line no-console
  console.error(message);
  // eslint-disable-next-line no-alert
  alert(`Error: ${message}`);
}

/**
 * Reload the current page's data table
 * Common pattern after create/update/delete operations
 */
function reloadDataTable() {
  if (typeof globalThis.loadTableData === "function") {
    globalThis.loadTableData();
  } else {
    // Fallback to page reload
    globalThis.location.reload();
  }
}

/**
 * Close a Bootstrap modal by ID
 * @param {string} modalId - ID of the modal to close
 */
function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal && typeof bootstrap !== "undefined") {
    const bsModal = bootstrap.Modal.getInstance(modal);
    if (bsModal) {
      bsModal.hide();
    }
  }
}

/**
 * Reset a form and clear validation states
 * @param {string} formId - ID of the form to reset
 */
function resetForm(formId) {
  const form = document.getElementById(formId);
  if (form) {
    form.reset();
    // Clear Bootstrap validation classes
    form.classList.remove("was-validated");
    form
      .querySelectorAll(".is-invalid")
      .forEach((el) => el.classList.remove("is-invalid"));
    form
      .querySelectorAll(".is-valid")
      .forEach((el) => el.classList.remove("is-valid"));
  }
}

// Export functions for ES6 modules or global access
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    loadSelectOptions,
    submitCRUDForm,
    getCSRFToken,
    showSuccess,
    showError,
    reloadDataTable,
    closeModal,
    resetForm,
  };
} else {
  // Expose to global scope for browser environments
  globalThis.ManagementUtils = {
    loadSelectOptions,
    submitCRUDForm,
    getCSRFToken,
    showSuccess,
    showError,
    reloadDataTable,
    closeModal,
    resetForm,
  };
}
