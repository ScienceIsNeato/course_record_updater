// static/script.js

// --- Helper Functions (Module Scope) ---

function isFieldRequired(fieldName) {
  // Example: For this app, course_number, term, course_title are always required
  return ["course_number", "term", "course_title"].includes(fieldName);
}

function validateFieldInput(input, updatedData) {
  const fieldName = input.name;
  const value = input.value.trim();
  updatedData[fieldName] = value;

  // Reset validation state
  input.classList.remove("is-invalid");

  // Check required fields
  if (!value && isFieldRequired(fieldName)) {
    input.classList.add("is-invalid");
    return {
      hasError: true,
      message: "Please fill in all required fields correctly.",
    };
  }

  // Check numeric fields
  if (
    input.type === "number" &&
    value &&
    (isNaN(Number(value)) || Number(value) < 0)
  ) {
    input.classList.add("is-invalid");
    return {
      hasError: true,
      message: "Numeric fields must contain valid non-negative numbers.",
    };
  }

  return { hasError: false, message: "" };
}

function collectInputReferences(inputs) {
  let numStudentsInput = null;
  const gradeInputs = [];

  inputs.forEach((input) => {
    if (input.name === "num_students") numStudentsInput = input;
    if (input.name.startsWith("grade_")) gradeInputs.push(input);
  });

  return { numStudentsInput, gradeInputs };
}

function validateGradeSum(updatedData, numStudentsInput, gradeInputs) {
  const numStudentsValue = updatedData.num_students
    ? Number(updatedData.num_students)
    : NaN;
  let gradeSum = 0;
  let anyGradeEntered = false;

  // Calculate grade sum and check if any grades were entered
  gradeInputs.forEach((input) => {
    const gradeValue = updatedData[input.name]
      ? Number(updatedData[input.name])
      : 0;
    if (!isNaN(gradeValue) && gradeValue > 0) {
      anyGradeEntered = true;
      gradeSum += gradeValue;
    }
    if (!updatedData[input.name]) updatedData[input.name] = 0;
  });

  // Validate sum if conditions are met
  if (!isNaN(numStudentsValue) && numStudentsValue >= 0 && anyGradeEntered) {
    if (gradeSum !== numStudentsValue) {
      // Mark fields as invalid
      if (numStudentsInput) numStudentsInput.classList.add("is-invalid");
      gradeInputs.forEach((input) => input.classList.add("is-invalid"));
      return {
        hasError: true,
        message: `Sum of grades (${gradeSum}) must equal Number of Students (${numStudentsValue}).`,
      };
    }
  } else if (
    anyGradeEntered &&
    (isNaN(numStudentsValue) || numStudentsValue < 0)
  ) {
    if (numStudentsInput) numStudentsInput.classList.add("is-invalid");
    return {
      hasError: true,
      message:
        "Number of Students is required and must be a valid non-negative number when entering grades.",
    };
  }

  return { hasError: false, message: "" };
}

function updateCellDisplayValues(inputs) {
  inputs.forEach((input) => {
    const cell = input.closest("td");
    let displayValue = input.value.trim();

    // Handle display for empty optional numbers
    if (input.type === "number" && !displayValue) {
      if (input.name === "num_students") displayValue = "N/A";
      else if (input.name.startsWith("grade_")) displayValue = "-";
    }
    cell.textContent = displayValue;
  });
}

function handleBackendError(result, response, numStudentsInput, gradeInputs) {
  const backendError = result.error || "Server error";

  if (
    backendError.includes("Sum of grades") ||
    backendError.includes("Number of students is required")
  ) {
    if (numStudentsInput) numStudentsInput.classList.add("is-invalid");
    gradeInputs.forEach((gInput) => gInput.classList.add("is-invalid"));
  }

  alert(`Error updating course: ${backendError}`);
}

// --- Import Form Helper Functions ---

function validateImportForm(fileInput, conflictStrategy) {
  if (!fileInput.files[0]) {
    alert("Please select an Excel file first.");
    return false;
  }

  if (!conflictStrategy) {
    alert("Please select a conflict resolution strategy.");
    return false;
  }

  return true;
}

function handleCompletedStatus(
  progress,
  shouldAutoRefresh,
  hideProgress,
  showImportResults,
  showSuccessAndRefresh,
) {
  hideProgress();

  // Show final results
  if (!progress.result) {
    return;
  }

  showImportResults(progress.result, true);

  // Auto-refresh if it was a real import (not dry run)
  if (
    shouldAutoRefresh &&
    progress.result &&
    progress.result.records_created > 0
  ) {
    showSuccessAndRefresh();
  }
}

function handleRunningStatus(
  startTime,
  maxPollTime,
  pollInterval,
  poll,
  hideProgress,
  showError,
) {
  if (Date.now() - startTime < maxPollTime) {
    setTimeout(poll, pollInterval);
    return;
  }

  hideProgress();
  showError(
    "Import is taking longer than expected. Please check the server logs.",
  );
}

function buildConfirmationMessage(conflictStrategy, deleteExistingDb) {
  let confirmMsg = `This will ${conflictStrategy.value === "use_theirs" ? "modify" : "potentially modify"} your database.`;

  if (deleteExistingDb?.checked) {
    confirmMsg += " ⚠️ WARNING: This will DELETE ALL EXISTING DATA first!";
  }

  confirmMsg += " Are you sure?";
  return confirmMsg;
}

function buildImportFormData(
  fileInput,
  conflictStrategy,
  dryRun,
  adapterSelect,
  deleteExistingDb,
) {
  const formData = new FormData();

  // Add uploaded file
  formData.append("file", fileInput.files[0]);

  formData.append("conflict_strategy", conflictStrategy.value);
  formData.append("dry_run", dryRun?.checked ? "true" : "false");
  formData.append("adapter_name", adapterSelect.value);
  formData.append(
    "delete_existing_db",
    deleteExistingDb?.checked ? "true" : "false",
  );
  return formData;
}

// Note: handleErrorStatus will be replaced with inline logic in initializeImportForm
// to avoid referencing locally-scoped functions

// --- Helper Functions ---

function handleDelete(row, courseId, courseNumber) {
  // Use simple confirm for now, prompt was complex
  const confirmationMessage = `Are you sure you want to delete course ${courseNumber} (ID: ${courseId})?`;

  if (!globalThis.confirm(confirmationMessage)) {
    return;
  }

  // Proceed with deletion
  // Use POST and rely on backend route allowing POST for delete
  fetch(`/delete_course/${courseId}`, {
    method: "POST",
  })
    .then((response) => {
      if (!response.ok) {
        return response
          .json()
          .then((err) => {
            throw new Error(
              err.error || `Server responded with status ${response.status}`,
            );
          })
          .catch(() => {
            throw new Error(`Server responded with status ${response.status}`);
          });
      }
      return response.json(); // Expect success JSON
    })
    .then((result) => {
      if (result.success) {
        row.remove(); // Remove row from table
        alert(`Course ${courseNumber} deleted successfully.`);
      } else {
        // eslint-disable-next-line no-console
        console.error("Delete failed on server:", result.error);
        alert(
          `Error deleting course: ${result.error || "Unknown server error"}`,
        );
      }
    })
    .catch((error) => {
      // eslint-disable-next-line no-console
      console.error("Network or other error during delete:", error);
      alert(`Failed to delete course: ${error.message}`);
    });
}

function revertRowToActionButtons(row) {
  const actionCellIndex = 10; // Updated index for 'Actions' cell
  const actionCell = row.cells[actionCellIndex];
  if (actionCell) {
    // nosemgrep
    // nosemgrep
    actionCell.innerHTML = `
                <button class="btn btn-sm btn-warning edit-btn">Edit</button>
                <button class="btn btn-sm btn-danger delete-btn">Delete</button>
            `;
  }
  // Clean up dataset
  delete row.dataset.originalValues;
}

function getFieldNameByIndex(index) {
  // Map table column index to field name (must match table structure in index.html)
  const fieldMap = [
    "course_number", // 0
    "course_title", // 1
    "instructor_name", // 2
    "term", // 3
    "num_students", // 4
    "grade_a", // 5
    "grade_b", // 6
    "grade_c", // 7
    "grade_d", // 8
    "grade_f", // 9
    null, // 10 Actions
  ];
  return fieldMap[index] || null;
}

// --- Table Row Editing Functions (Module Scope) ---

function makeRowEditable(row) {
  // Store original values & switch action buttons
  const originalValues = {};
  const actionCellIndex = 10; // Updated index for 'Actions' cell

  row.querySelectorAll("td").forEach((cell, index) => {
    if (index === actionCellIndex) return; // Skip actions cell

    const fieldName = getFieldNameByIndex(index); // Helper to map index to field name
    if (!fieldName) return;

    const originalValue = cell.textContent.trim();
    originalValues[fieldName] = originalValue;

    // Replace cell content with appropriate input field
    let input;
    if (fieldName === "term") {
      input = document.createElement("select");
      input.classList.add("form-select", "form-select-sm", "inline-edit-input"); // Bootstrap classes
      // Add options (ideally passed from server or hardcoded if static)
      const allowedTerms = [
        "FA2024",
        "SP2024",
        "SU2024",
        "FA2025",
        "SP2025",
        "SU2025",
      ]; // Match adapter/template
      allowedTerms.forEach((term) => {
        const option = document.createElement("option");
        option.value = term;
        option.text = term;
        if (term === originalValue) {
          option.selected = true;
        }
        input.appendChild(option);
      });
    } else {
      input = document.createElement("input");
      input.type =
        fieldName === "num_students" || fieldName.startsWith("grade_")
          ? "number"
          : "text";
      if (input.type === "number") {
        input.min = "0"; // Set min for number inputs
      }
      input.value =
        originalValue === "N/A" || originalValue === "-" ? "" : originalValue; // Handle placeholder display values
      input.classList.add(
        "form-control",
        "form-control-sm",
        "inline-edit-input",
      ); // Bootstrap classes
    }
    input.name = fieldName;
    cell.innerHTML = ""; // Clear cell // nosemgrep
    cell.appendChild(input);
  });

  // Store original values on the row for cancel functionality
  row.dataset.originalValues = JSON.stringify(originalValues);

  // Change buttons in the action cell
  const actionCell = row.cells[actionCellIndex];
  // nosemgrep
  actionCell.innerHTML = `
            <button class="btn btn-sm btn-success save-btn">Save</button>
            <button class="btn btn-sm btn-secondary cancel-btn">Cancel</button>
        `;
}

async function handleSave(row, courseId) {
  const inputs = row.querySelectorAll(".inline-edit-input");
  const updatedData = {};
  let hasError = false;
  let validationErrorMsg = "";

  // Collect input references
  const { numStudentsInput, gradeInputs } = collectInputReferences(inputs);

  // Validate all input fields
  inputs.forEach((input) => {
    const validation = validateFieldInput(input, updatedData);
    if (validation.hasError) {
      hasError = true;
      if (!validationErrorMsg) validationErrorMsg = validation.message;
    }
  });

  // Validate grade sum logic
  if (!hasError) {
    const gradeValidation = validateGradeSum(
      updatedData,
      numStudentsInput,
      gradeInputs,
    );
    if (gradeValidation.hasError) {
      hasError = true;
      validationErrorMsg = gradeValidation.message;
    }
  }

  // Stop if validation errors found
  if (hasError) {
    alert(validationErrorMsg);
    return;
  }

  // --- Proceed with saving ---

  try {
    // Use POST and rely on backend route allowing POST for updates
    const response = await fetch(`/edit_course/${courseId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(updatedData),
    });

    const result = await response.json();

    if (response.ok && result.success) {
      updateCellDisplayValues(inputs);
      revertRowToActionButtons(row);
    } else {
      // eslint-disable-next-line no-console
      console.error(
        "Update failed:",
        result.error || `HTTP ${response.status}`,
      );
      handleBackendError(result, response, numStudentsInput, gradeInputs);
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error("Network or fetch error during save:", error);
    alert("Failed to send update request.");
  }
}

function cancelEdit(row) {
  const originalValues = JSON.parse(row.dataset.originalValues || "{}");

  row.querySelectorAll("td").forEach((cell) => {
    const input = cell.querySelector(".inline-edit-input");
    if (input) {
      const fieldName = input.name;
      cell.textContent =
        originalValues[fieldName] !== undefined
          ? originalValues[fieldName]
          : "";
    }
  });

  revertRowToActionButtons(row);
}

// --- DOM Event Listeners ---

document.addEventListener("DOMContentLoaded", () => {
  const courseTableBody = document.querySelector(".table tbody"); // Target tbody directly

  // Only set up table event listeners if the table exists
  if (courseTableBody) {
    // --- Event Delegation for Edit/Delete/Save/Cancel ---
    courseTableBody.addEventListener("click", async (event) => {
      const target = event.target;
      const row = target.closest("tr");
      if (!row?.dataset?.courseId) {
        // Ignore clicks that aren't on a button within a valid course row
        return;
      }
      const courseId = row.dataset.courseId; // Correctly get ID from row

      // --- EDIT Button Click ---
      if (target.classList.contains("edit-btn")) {
        makeRowEditable(row);
      } else if (target.classList.contains("delete-btn")) {
        // --- DELETE Button Click ---
        const courseNumber = row.cells[0].textContent; // Get course number from first cell
        handleDelete(row, courseId, courseNumber);
      } else if (target.classList.contains("save-btn")) {
        // --- SAVE Button Click ---
        await handleSave(row, courseId);
      } else if (target.classList.contains("cancel-btn")) {
        // --- CANCEL Button Click ---
        cancelEdit(row);
      }
    });
  } else {
    // eslint-disable-next-line no-console
    console.log(
      "No course table found - skipping table event listeners (expected in cleaned UI)",
    );
  }

  // Remove the duplicate direct event listener attachment block
  /*
    // --- Delete Button Logic ---
    const deleteButtons = document.querySelectorAll('.delete-btn');
    ...
    // --- Edit Button Logic (Placeholder) ---
    const editButtons = document.querySelectorAll('.edit-btn');
    ...
    */

  // --- Excel Import Form Functionality ---
  initializeImportForm();

  // --- Dashboard Data Loading ---
  // Only load dashboard data if at least one dashboard element exists
  const dashboardElements = [
    "coursesData",
    "instructorsData",
    "sectionsData",
    "termsData",
  ];
  const hasDashboardElements = dashboardElements.some((id) =>
    document.getElementById(id),
  );
  if (hasDashboardElements) {
    loadDashboardData();
  }
});

// Dashboard data loading functions
async function loadDashboardData() {
  const endpoints = [
    { id: "coursesData", url: "/api/courses", key: "courses" },
    { id: "instructorsData", url: "/api/instructors", key: "instructors" },
    { id: "sectionsData", url: "/api/sections", key: "sections" },
    { id: "termsData", url: "/api/terms", key: "terms" },
  ];

  for (const endpoint of endpoints) {
    // Check if element exists BEFORE making API call (avoid unnecessary fetches)
    const element = document.getElementById(endpoint.id);
    if (!element) {
      continue; // Skip endpoints for elements that don't exist on this page
    }

    try {
      const response = await fetch(endpoint.url);
      const data = await response.json();

      if (data.success) {
        const count = data.count || 0;
        // nosemgrep
        element.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="badge bg-primary">${count} total</span>
                        <small class="text-success">✓ Loaded</small>
                    </div>
                    ${count > 0 ? `<small class="text-muted mt-1 d-block">Last updated: ${new Date().toLocaleTimeString()}</small>` : ""}
                `;
      } else {
        element.innerHTML = '<small class="text-danger">Failed to load</small>';
      }
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error(`Failed to load ${endpoint.key}:`, error); // nosemgrep
      // nosemgrep
      element.innerHTML =
        '<small class="text-danger">Error loading data</small>';
    }
  }

  // Debug data loading removed - temporary development tools no longer needed
}

function initializeImportForm() {
  const importForm = document.getElementById("excelImportForm");
  const validateBtn = document.getElementById("validateImportBtn");
  const executeBtn = document.getElementById("executeImportBtn");
  const importBtnText = document.getElementById("importBtnText");
  const dryRunCheckbox = document.getElementById("dry_run");
  const progressDiv = document.getElementById("importProgress");
  const resultsDiv = document.getElementById("importResults");

  // eslint-disable-next-line no-console
  console.log("Import form elements found:", {
    importForm: !!importForm,
    validateBtn: !!validateBtn,
    executeBtn: !!executeBtn,
    importBtnText: !!importBtnText,
    dryRunCheckbox: !!dryRunCheckbox,
  });

  if (!importForm) {
    // eslint-disable-next-line no-console
    console.log(
      "Import form not found on this page - skipping import form initialization",
    );
    return; // Exit if import form doesn't exist
  }

  // Update button text based on dry run checkbox
  function updateButtonText() {
    if (dryRunCheckbox?.checked) {
      importBtnText.textContent = "Test Import (Dry Run)";
    } else {
      importBtnText.textContent = "Execute Import";
    }
  }

  // Initialize button text
  updateButtonText();

  // Update button text when dry run checkbox changes
  if (dryRunCheckbox) {
    dryRunCheckbox.addEventListener("change", updateButtonText);
  }

  // Validate file only
  if (validateBtn) {
    validateBtn.addEventListener("click", async () => {
      const fileInput = document.getElementById("excel_file");
      const adapterSelect = document.getElementById("import_adapter");

      if (!fileInput.files[0]) {
        alert("Please select an Excel file first.");
        return;
      }

      const formData = new FormData();
      formData.append("file", fileInput.files[0]);
      formData.append("adapter_name", adapterSelect.value);

      showProgress("Validating file...");

      try {
        const response = await fetch("/api/import/validate", {
          method: "POST",
          body: formData,
        });

        const result = await response.json();
        hideProgress();

        if (result.success && result.validation) {
          showValidationResults(result.validation);
        } else {
          showError("Validation failed: " + (result.error || "Unknown error"));
        }
      } catch (error) {
        hideProgress();
        showError("Network error during validation: " + error.message);
      }
    });
  }

  async function executeImport(formData, dryRun) {
    const actionText = dryRun.checked ? "Testing import" : "Executing import";
    showProgress(actionText + "...");

    try {
      const response = await fetch("/api/import/excel", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (result.success && result.progress_id) {
        await pollImportProgress(result.progress_id, !dryRun.checked);
      } else {
        hideProgress();
        showError(
          "Failed to start import: " + (result.error || "Unknown error"),
        );
      }
    } catch (error) {
      hideProgress();
      showError("Network error during import: " + error.message);
    }
  }

  // Execute import
  if (importForm) {
    importForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      // Get form elements
      const fileInput = document.getElementById("excel_file");
      const adapterSelect = document.getElementById("import_adapter");
      const conflictStrategy = document.querySelector(
        'input[name="conflict_strategy"]:checked',
      );
      const dryRun = document.getElementById("dry_run");
      const deleteExistingDb = document.getElementById("delete_existing_db");
      // Validate form inputs
      if (!validateImportForm(fileInput, conflictStrategy)) {
        return;
      }

      // Confirm execution if not dry run
      if (!dryRun.checked) {
        const confirmMsg = buildConfirmationMessage(
          conflictStrategy,
          deleteExistingDb,
        );
        if (!confirm(confirmMsg)) {
          return;
        }
      }

      // Build form data and execute import
      const formData = buildImportFormData(
        fileInput,
        conflictStrategy,
        dryRun,
        adapterSelect,
        deleteExistingDb,
      );
      await executeImport(formData, dryRun);
    });
  }

  function showProgress(message) {
    if (progressDiv) {
      progressDiv.style.display = "block";
      // nosemgrep
      document.getElementById("importStatus").innerHTML = `
                <div class="spinner-border text-info" role="status">
                    <span class="visually-hidden">Processing...</span>
                </div>
                <p class="mt-2">${message}</p>
            `;
    }
    if (resultsDiv) {
      resultsDiv.style.display = "none";
    }
  }

  function hideProgress() {
    if (progressDiv) {
      progressDiv.style.display = "none";
    }
  }

  async function pollImportProgress(progressId, shouldAutoRefresh) {
    const pollInterval = 1000; // Poll every second
    const maxPollTime = 300000; // Max 5 minutes
    const startTime = Date.now();

    const poll = async () => {
      try {
        const response = await fetch(`/api/import/progress/${progressId}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const progress = await response.json();
        updateProgressBar(progress);

        // Handle different progress statuses
        if (progress.status === "completed") {
          handleCompletedStatus(
            progress,
            shouldAutoRefresh,
            hideProgress,
            showImportResults,
            showSuccessAndRefresh,
          );
        } else if (progress.status === "error") {
          // Handle error status inline
          hideProgress();
          showError("Import failed: " + (progress.message || "Unknown error"));
        } else if (
          progress.status === "running" ||
          progress.status === "starting"
        ) {
          handleRunningStatus(
            startTime,
            maxPollTime,
            pollInterval,
            poll,
            hideProgress,
            showError,
          );
        }
      } catch (error) {
        hideProgress();
        showError(
          "Lost connection to import progress. Import may still be running.",
        );
      }
    };

    // Start polling
    setTimeout(poll, 500); // Start after 500ms
  }

  function updateProgressBar(progress) {
    const progressBar = document.getElementById("importProgressBar");
    const statusDiv = document.getElementById("importStatus");

    if (progressBar) {
      const percentage = progress.percentage || 0;
      // Update HTML5 progress element value attribute (not style.width)
      progressBar.value = percentage;
      progressBar.textContent = `${percentage}%`; // Update visible percentage text
    }

    if (statusDiv) {
      const message = progress.message || "Processing...";
      const recordsProcessed = progress.records_processed || 0;
      const totalRecords = progress.total_records || 0;
      const recordsInfo =
        totalRecords > 0
          ? ` (${recordsProcessed}/${totalRecords} records)`
          : "";

      // nosemgrep
      // nosemgrep
      statusDiv.innerHTML = `
                <div class="spinner-border text-info" role="status">
                    <span class="visually-hidden">Processing...</span>
                </div>
                <p class="mt-2">${message}${recordsInfo}</p>
                <small class="text-muted">${progress.percentage || 0}% complete</small>
            `;
    }
  }

  function showValidationResults(validation) {
    if (!resultsDiv) return;
    resultsDiv.innerHTML = "";

    const header = document.createElement("div");
    header.className = validation.valid
      ? "alert alert-success"
      : "alert alert-warning";
    const h5 = document.createElement("h5");
    const iconClass = validation.valid
      ? "fas fa-check-circle"
      : "fas fa-exclamation-triangle";
    h5.innerHTML = `<i class="${iconClass}"></i> File Validation Results`;
    header.appendChild(h5);

    const info = [
      { label: "File:", value: validation.file_info.filename },
      { label: "Format:", value: validation.file_info.adapter },
      { label: "Records Found:", value: validation.records_found },
      { label: "Potential Conflicts:", value: validation.potential_conflicts },
    ];

    info.forEach((item) => {
      const p = document.createElement("p");
      p.className = "mb-1";
      const strong = document.createElement("strong");
      strong.textContent = item.label;
      p.appendChild(strong);
      p.appendChild(document.createTextNode(` ${item.value}`));
      header.appendChild(p);
    });
    resultsDiv.appendChild(header);

    if (validation.errors && validation.errors.length > 0) {
      const errorDiv = document.createElement("div");
      errorDiv.className = "alert alert-danger";
      const h6 = document.createElement("h6");
      h6.textContent = "Errors:";
      errorDiv.appendChild(h6);
      const ul = document.createElement("ul");
      validation.errors.forEach((error) => {
        const li = document.createElement("li");
        li.textContent = error;
        ul.appendChild(li);
      });
      errorDiv.appendChild(ul);
      resultsDiv.appendChild(errorDiv);
    }

    if (validation.warnings && validation.warnings.length > 0) {
      const warnDiv = document.createElement("div");
      warnDiv.className = "alert alert-warning";
      const h6 = document.createElement("h6");
      h6.textContent = "Warnings:";
      warnDiv.appendChild(h6);
      const ul = document.createElement("ul");
      validation.warnings.forEach((warning) => {
        const li = document.createElement("li");
        li.textContent = warning;
        ul.appendChild(li);
      });
      warnDiv.appendChild(ul);
      resultsDiv.appendChild(warnDiv);
    }

    resultsDiv.style.display = "block";
  }

  function showImportResults(result, success) {
    if (!resultsDiv) {
      // eslint-disable-next-line no-console
      console.error("Results div not found!");
      return;
    }

    resultsDiv.innerHTML = "";

    // Build header
    const header = document.createElement("div");
    header.className = success ? "alert alert-success" : "alert alert-danger";
    const h4 = document.createElement("h4");
    h4.textContent = success ? "Import Successful" : "Import Failed";
    if (success) {
      const icon = document.createElement("i");
      icon.className = "fas fa-check-circle me-2";
      h4.prepend(icon);
    }
    header.appendChild(h4);
    if (result.dry_run) {
      const badge = document.createElement("span");
      badge.className = "badge bg-warning text-dark ms-2";
      badge.textContent = "DRY RUN";
      h4.appendChild(badge);
    }

    if (result.message) {
      const p = document.createElement("p");
      p.textContent = result.message;
      header.appendChild(p);
    }
    resultsDiv.appendChild(header);

    // Errors
    if (result.errors && result.errors.length > 0) {
      const div = document.createElement("div");
      div.className = "alert alert-danger";
      const h6 = document.createElement("h6");
      h6.textContent = `Errors (${result.errors.length}):`;
      div.appendChild(h6);
      const ul = document.createElement("ul");
      const displayErrors = result.errors.slice(0, 10);
      displayErrors.forEach((err) => {
        const li = document.createElement("li");
        li.textContent = err;
        ul.appendChild(li);
      });
      div.appendChild(ul);
      if (result.errors.length > 10) {
        const p = document.createElement("p");
        p.className = "small mb-0";
        p.textContent = `...and ${result.errors.length - 10} more errors`;
        div.appendChild(p);
      }
      resultsDiv.appendChild(div);
    }

    // Warnings
    if (result.warnings && result.warnings.length > 0) {
      const div = document.createElement("div");
      div.className = "alert alert-warning";
      const h6 = document.createElement("h6");
      h6.textContent = `Warnings (${result.warnings.length}):`;
      div.appendChild(h6);
      const ul = document.createElement("ul");
      const displayWarnings = result.warnings.slice(0, 5);
      displayWarnings.forEach((warn) => {
        const li = document.createElement("li");
        li.textContent = warn;
        ul.appendChild(li);
      });
      div.appendChild(ul);
      if (result.warnings.length > 5) {
        const p = document.createElement("p");
        p.className = "small mb-0";
        p.textContent = `...and ${result.warnings.length - 5} more warnings`;
        div.appendChild(p);
      }
      resultsDiv.appendChild(div);
    }

    // Conflicts
    if (result.conflicts && result.conflicts.length > 0) {
      const div = document.createElement("div");
      div.className = "alert alert-info";
      const h6 = document.createElement("h6");
      h6.textContent = `Conflicts Resolved (${result.conflicts.length}):`;
      div.appendChild(h6);

      const scrollDiv = document.createElement("div");
      scrollDiv.style.maxHeight = "200px";
      scrollDiv.style.overflowY = "auto";

      const ul = document.createElement("ul");
      ul.className = "small mb-0";
      result.conflicts.slice(0, 20).forEach((conflict) => {
        const li = document.createElement("li");
        li.textContent = `${conflict.entity_type} ${
          conflict.entity_key
        }: ${conflict.field_name} kept ${conflict.resolution.replace(
          "kept_",
          "",
        )}`;
        if (
          conflict.existing_value !== undefined &&
          conflict.import_value !== undefined
        ) {
          li.textContent += ` (${conflict.existing_value} vs ${conflict.import_value})`;
        }
        ul.appendChild(li);
      });
      scrollDiv.appendChild(ul);
      div.appendChild(scrollDiv);

      if (result.conflicts.length > 20) {
        const more = document.createElement("p");
        more.className = "small mt-2 mb-0";
        more.textContent = `and ${result.conflicts.length - 20} more conflicts`;
        div.appendChild(more);
      }

      resultsDiv.appendChild(div);
    }

    resultsDiv.style.display = "block";
  }

  function showError(message) {
    if (resultsDiv) {
      resultsDiv.innerHTML = "";
      const alert = document.createElement("div");
      alert.className = "alert alert-danger";
      const h5 = document.createElement("h5");
      h5.innerHTML = '<i class="fas fa-exclamation-circle"></i> Error';
      const p = document.createElement("p");
      p.textContent = message;
      alert.appendChild(h5);
      alert.appendChild(p);
      resultsDiv.appendChild(alert);
      resultsDiv.style.display = "block";
    }
  }
}

// Debug functionality removed - temporary development tools no longer needed

// Helper function to show success message and refresh
function showSuccessAndRefresh() {
  // Reload immediately - the refreshed page with updated data IS the success indicator
  // Flash messages will show import results if needed
  globalThis.location.reload();
}
