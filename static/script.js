// static/script.js
console.log("script.js loaded");

document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM fully loaded and parsed");

    const courseTableBody = document.querySelector('.table tbody'); // Target tbody directly

    // Only set up table event listeners if the table exists (legacy functionality)
    if (courseTableBody) {
        console.log("✅ Course table found, setting up event listeners");
        // --- Event Delegation for Edit/Delete/Save/Cancel ---
        courseTableBody.addEventListener('click', async (event) => {
        const target = event.target;
        const row = target.closest('tr');
        if (!row || !row.dataset.courseId) {
            // Ignore clicks that aren't on a button within a valid course row
            return;
        }
        const courseId = row.dataset.courseId; // Correctly get ID from row

        // --- EDIT Button Click ---
        if (target.classList.contains('edit-btn')) {
            console.log(`Edit clicked for ID: ${courseId}`);
            makeRowEditable(row);
        }
        // --- DELETE Button Click ---
        else if (target.classList.contains('delete-btn')) {
            console.log(`Delete clicked for ID: ${courseId}`);
            const courseNumber = row.cells[0].textContent; // Get course number from first cell
            handleDelete(row, courseId, courseNumber);
        }
        // --- SAVE Button Click ---
        else if (target.classList.contains('save-btn')) {
            console.log(`Save clicked for ID: ${courseId}`);
            await handleSave(row, courseId);
        }
        // --- CANCEL Button Click ---
        else if (target.classList.contains('cancel-btn')) {
            console.log(`Cancel clicked for ID: ${courseId}`);
            cancelEdit(row);
        }
        });
    } else {
        console.log("ℹ️ No course table found - skipping table event listeners (expected in cleaned UI)");
    }

    // --- Helper Functions ---

    function makeRowEditable(row) {
        // Store original values & switch action buttons
        const originalValues = {};
        const actionCellIndex = 10; // Updated index for 'Actions' cell
        const courseId = row.dataset.courseId;

        row.querySelectorAll('td').forEach((cell, index) => {
            if (index === actionCellIndex) return; // Skip actions cell

            const fieldName = getFieldNameByIndex(index); // Helper to map index to field name
            if (!fieldName) return;

            const originalValue = cell.textContent.trim();
            originalValues[fieldName] = originalValue;

            // Replace cell content with appropriate input field
            let input;
            if (fieldName === 'term') {
                input = document.createElement('select');
                input.classList.add('form-select', 'form-select-sm', 'inline-edit-input'); // Bootstrap classes
                // Add options (ideally passed from server or hardcoded if static)
                const allowedTerms = ['FA2024', 'SP2024', 'SU2024', 'FA2025', 'SP2025', 'SU2025']; // Match adapter/template
                allowedTerms.forEach(term => {
                    const option = document.createElement('option');
                    option.value = term;
                    option.text = term;
                    if (term === originalValue) {
                        option.selected = true;
                    }
                    input.appendChild(option);
                });
            } else {
                input = document.createElement('input');
                input.type = (fieldName === 'num_students' || fieldName.startsWith('grade_')) ? 'number' : 'text';
                if (input.type === 'number') {
                    input.min = '0'; // Set min for number inputs
                }
                input.value = (originalValue === 'N/A' || originalValue === '-') ? '' : originalValue; // Handle placeholder display values
                input.classList.add('form-control', 'form-control-sm', 'inline-edit-input'); // Bootstrap classes
            }
            input.name = fieldName;
            cell.innerHTML = ''; // Clear cell
            cell.appendChild(input);
        });

        // Store original values on the row for cancel functionality
        row.dataset.originalValues = JSON.stringify(originalValues);

        // Change buttons in the action cell
        const actionCell = row.cells[actionCellIndex];
        actionCell.innerHTML = `
            <button class="btn btn-sm btn-success save-btn">Save</button>
            <button class="btn btn-sm btn-secondary cancel-btn">Cancel</button>
        `;
    }

    async function handleSave(row, courseId) {
        const inputs = row.querySelectorAll('.inline-edit-input');
        const updatedData = {};
        let hasError = false;
        let validationErrorMsg = "Please fill in all required fields correctly."; // Default message

        // References to specific inputs for validation feedback
        let numStudentsInput = null;
        const gradeInputs = [];

        inputs.forEach(input => {
            const fieldName = input.name;
            const value = input.value.trim();
            updatedData[fieldName] = value; // Send trimmed string value

            // Store references
            if (fieldName === 'num_students') numStudentsInput = input;
            if (fieldName.startsWith('grade_')) gradeInputs.push(input);

            // --- Basic client-side validation ---
            input.classList.remove('is-invalid'); // Reset border first

            if (!value && isFieldRequired(fieldName)) {
                input.classList.add('is-invalid');
                hasError = true;
            }
            // Check number types (including grades)
            if (input.type === 'number' && value && (isNaN(Number(value)) || Number(value) < 0)) {
                 input.classList.add('is-invalid');
                 validationErrorMsg = "Numeric fields must contain valid non-negative numbers.";
                 hasError = true;
            }
        });

        // --- Grade Sum vs Num Students Validation ---
        const numStudentsValue = updatedData['num_students'] ? Number(updatedData['num_students']) : NaN;
        let gradeSum = 0;
        let anyGradeEntered = false;
        const gradeValues = {};

        gradeInputs.forEach(input => {
            const gradeValue = updatedData[input.name] ? Number(updatedData[input.name]) : 0;
            if (!isNaN(gradeValue) && gradeValue > 0) {
                anyGradeEntered = true;
                gradeValues[input.name] = gradeValue;
                gradeSum += gradeValue;
            } else if (isNaN(gradeValue)) {
                // If a grade field has invalid number, error is already caught above
            }
            // Store 0 even if empty for sum logic consistency if needed, but anyGradeEntered tracks actual input
            if (!updatedData[input.name]) gradeValues[input.name] = 0;
        });

        // Only validate sum if num_students is a valid number AND at least one grade > 0 was entered
        if (!isNaN(numStudentsValue) && numStudentsValue >= 0 && anyGradeEntered) {
            if (gradeSum !== numStudentsValue) {
                hasError = true;
                validationErrorMsg = `Sum of grades (${gradeSum}) must equal Number of Students (${numStudentsValue}).`;
                // Mark relevant fields as invalid
                if (numStudentsInput) numStudentsInput.classList.add('is-invalid');
                gradeInputs.forEach(input => input.classList.add('is-invalid'));
            }
        }
        // Also check: if any grade was entered, num_students MUST be provided and valid
        else if (anyGradeEntered && (isNaN(numStudentsValue) || numStudentsValue < 0)) {
             hasError = true;
             validationErrorMsg = "Number of Students is required and must be a valid non-negative number when entering grades.";
             if (numStudentsInput) numStudentsInput.classList.add('is-invalid');
             // Keep grades marked invalid if they individually failed conversion earlier
        }

        // --- Stop if errors found ---
        if (hasError) {
            alert(validationErrorMsg); // Show specific error
            return; // Prevent saving
        }

        // --- Proceed with saving ---
        console.log("Saving data:", updatedData);

        try {
            // Use POST and rely on backend route allowing POST for updates
            const response = await fetch(`/edit_course/${courseId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(updatedData)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                console.log("Update successful");
                // Update cell text content and revert row state
                inputs.forEach(input => {
                    const cell = input.closest('td');
                    let displayValue = input.value.trim();
                    // Handle display for empty optional numbers
                    if (input.type === 'number' && !displayValue) {
                        if (input.name === 'num_students') displayValue = 'N/A';
                        else if (input.name.startsWith('grade_')) displayValue = '-';
                    }
                    cell.textContent = displayValue; // Update display
                });
                revertRowToActionButtons(row);
            } else {
                console.error("Update failed:", result.error || `HTTP ${response.status}`);
                // Try to show backend validation error if available
                let backendError = result.error || 'Server error';
                if (backendError.includes("Sum of grades") || backendError.includes("Number of students is required")){
                    // If backend caught the sum error, highlight fields
                    validationErrorMsg = backendError;
                    if (numStudentsInput) numStudentsInput.classList.add('is-invalid');
                    gradeInputs.forEach(gInput => gInput.classList.add('is-invalid'));
                }
                alert(`Error updating course: ${backendError}`);
                // Leave editable on failure
            }
        } catch (error) {
            console.error("Network or fetch error during save:", error);
            alert("Failed to send update request.");
        }
    }

    function cancelEdit(row) {
        const originalValues = JSON.parse(row.dataset.originalValues || '{}');

        row.querySelectorAll('td').forEach((cell, index) => {
            const input = cell.querySelector('.inline-edit-input');
            if (input) {
                const fieldName = input.name;
                cell.textContent = originalValues[fieldName] !== undefined ? originalValues[fieldName] : '';
            }
        });

        revertRowToActionButtons(row);
    }

    function handleDelete(row, courseId, courseNumber) {
        // Use simple confirm for now, prompt was complex
        const confirmationMessage = `Are you sure you want to delete course ${courseNumber} (ID: ${courseId})?`;

        if (!window.confirm(confirmationMessage)) {
            console.log("Delete cancelled by user.");
            return;
        }

        // Proceed with deletion
        console.log(`Attempting to delete ID: ${courseId}`);
        // Use POST and rely on backend route allowing POST for delete
        fetch(`/delete_course/${courseId}`, {
            method: 'POST'
        })
        .then(response => {
            if (!response.ok) {
                 return response.json().then(err => {
                     throw new Error(err.error || `Server responded with status ${response.status}`);
                 }).catch(() => {
                      throw new Error(`Server responded with status ${response.status}`);
                 });
            }
            return response.json(); // Expect success JSON
        })
        .then(result => {
            if (result.success) {
                console.log("Delete successful");
                row.remove(); // Remove row from table
                alert(`Course ${courseNumber} deleted successfully.`);
            } else {
                 console.error("Delete failed on server:", result.error);
                 alert(`Error deleting course: ${result.error || 'Unknown server error'}`);
            }
        })
        .catch(error => {
            console.error("Network or other error during delete:", error);
            alert(`Failed to delete course: ${error.message}`);
        });
    }

    function revertRowToActionButtons(row) {
        const actionCellIndex = 10; // Updated index for 'Actions' cell
        const actionCell = row.cells[actionCellIndex];
        const courseId = row.dataset.courseId;
        if (actionCell) {
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
            'course_number',   // 0
            'course_title',    // 1
            'instructor_name', // 2
            'term',            // 3
            'num_students',    // 4
            'grade_a',         // 5
            'grade_b',         // 6
            'grade_c',         // 7
            'grade_d',         // 8
            'grade_f',         // 9
            null               // 10 Actions
        ];
        return fieldMap[index] || null;
    }

    function isFieldRequired(fieldName) {
        // Mirror required fields from BaseAdapter (adjust if needed)
         const requiredFields = ['course_title', 'course_number', 'instructor_name', 'term'];
         return requiredFields.includes(fieldName);
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
    loadDashboardData();

});

// Dashboard data loading functions
async function loadDashboardData() {
    const endpoints = [
        { id: 'coursesData', url: '/api/courses', key: 'courses' },
        { id: 'instructorsData', url: '/api/instructors', key: 'instructors' },
        { id: 'sectionsData', url: '/api/sections', key: 'sections' },
        { id: 'termsData', url: '/api/terms', key: 'terms' }
    ];

    for (const endpoint of endpoints) {
        try {
            const response = await fetch(endpoint.url);
            const data = await response.json();
            
            const element = document.getElementById(endpoint.id);
            if (element && data.success) {
                const count = data.count || 0;
                element.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="badge bg-primary">${count} total</span>
                        <small class="text-success">✓ Loaded</small>
                    </div>
                    ${count > 0 ? `<small class="text-muted mt-1 d-block">Last updated: ${new Date().toLocaleTimeString()}</small>` : ''}
                `;
            } else if (element) {
                element.innerHTML = `<small class="text-danger">Failed to load</small>`;
            }
        } catch (error) {
            console.error(`Failed to load ${endpoint.key}:`, error);
            const element = document.getElementById(endpoint.id);
            if (element) {
                element.innerHTML = `<small class="text-danger">Error loading data</small>`;
            }
        }
    }
    
    // Load debug data
    loadDebugData();
}

function initializeImportForm() {
    console.log("🔧 Initializing import form...");
    const importForm = document.getElementById('excelImportForm');
    const validateBtn = document.getElementById('validateImportBtn');
    const executeBtn = document.getElementById('executeImportBtn');
    const importBtnText = document.getElementById('importBtnText');
    const dryRunCheckbox = document.getElementById('dry_run');
    const progressDiv = document.getElementById('importProgress');
    const resultsDiv = document.getElementById('importResults');

    console.log("📋 Form elements found:", {
        importForm: !!importForm,
        validateBtn: !!validateBtn,
        executeBtn: !!executeBtn,
        importBtnText: !!importBtnText,
        dryRunCheckbox: !!dryRunCheckbox
    });

    if (!importForm) {
        console.error("❌ Import form not found!");
        return; // Exit if import form doesn't exist
    }

    // Update button text based on dry run checkbox
    function updateButtonText() {
        if (dryRunCheckbox && dryRunCheckbox.checked) {
            importBtnText.textContent = 'Test Import (Dry Run)';
        } else {
            importBtnText.textContent = 'Execute Import';
        }
    }

    // Initialize button text
    updateButtonText();

    // Update button text when dry run checkbox changes
    if (dryRunCheckbox) {
        dryRunCheckbox.addEventListener('change', updateButtonText);
    }

    // Validate file only
    if (validateBtn) {
        console.log("✅ Adding click event listener to validate button");
        validateBtn.addEventListener('click', async function() {
            console.log("🔍 Validate button clicked!");
            const fileInput = document.getElementById('excel_file');
            const adapterSelect = document.getElementById('import_adapter');

            if (!fileInput.files[0]) {
                alert('Please select an Excel file first.');
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('adapter_name', adapterSelect.value);

            showProgress('Validating file...');

            try {
                const response = await fetch('/api/import/validate', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                hideProgress();

                if (result.success && result.validation) {
                    showValidationResults(result.validation);
                } else {
                    showError('Validation failed: ' + (result.error || 'Unknown error'));
                }
            } catch (error) {
                hideProgress();
                showError('Network error during validation: ' + error.message);
            }
        });
    }

    // Execute import
    if (importForm) {
        console.log("✅ Adding submit event listener to import form");
        importForm.addEventListener('submit', async function(e) {
            console.log("🚀 Form submit event triggered!");
            e.preventDefault();

            const fileInput = document.getElementById('excel_file');
            const adapterSelect = document.getElementById('import_adapter');
            const conflictStrategy = document.querySelector('input[name="conflict_strategy"]:checked');
            const dryRun = document.getElementById('dry_run');
            const verbose = document.getElementById('verbose_output');
            const deleteExistingDb = document.getElementById('delete_existing_db');

            if (!fileInput.files[0]) {
                alert('Please select an Excel file first.');
                return;
            }

            if (!conflictStrategy) {
                alert('Please select a conflict resolution strategy.');
                return;
            }

            // Confirm execution if not dry run
            if (!dryRun.checked) {
                let confirmMsg = `This will ${conflictStrategy.value === 'use_theirs' ? 'modify' : 'potentially modify'} your database.`;

                if (deleteExistingDb && deleteExistingDb.checked) {
                    confirmMsg += ' ⚠️ WARNING: This will DELETE ALL EXISTING DATA first!';
                }

                confirmMsg += ' Are you sure?';

                if (!confirm(confirmMsg)) {
                    return;
                }
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('conflict_strategy', conflictStrategy.value);
            formData.append('dry_run', dryRun.checked ? 'true' : 'false');
            formData.append('adapter_name', adapterSelect.value);
            formData.append('delete_existing_db', deleteExistingDb && deleteExistingDb.checked ? 'true' : 'false');

            const actionText = dryRun.checked ? 'Testing import' : 'Executing import';
            showProgress(actionText + '...');

            try {
                console.log("📤 Sending import request...");
                const response = await fetch('/api/import/excel', {
                    method: 'POST',
                    body: formData
                });

                console.log("📥 Received response:", response.status, response.statusText);
                const result = await response.json();
                console.log("📊 Import result:", result);

                if (result.success && result.progress_id) {
                    console.log("🔄 Import started, tracking progress...");
                    // Start polling for progress
                    await pollImportProgress(result.progress_id, !dryRun.checked);
                } else {
                    hideProgress();
                    showError('Failed to start import: ' + (result.error || 'Unknown error'));
                }
            } catch (error) {
                console.log("💥 Network error:", error);
                hideProgress();
                showError('Network error during import: ' + error.message);
            }
        });
    }

    function showProgress(message) {
        if (progressDiv) {
            progressDiv.style.display = 'block';
            document.getElementById('importStatus').innerHTML = `
                <div class="spinner-border text-info" role="status">
                    <span class="visually-hidden">Processing...</span>
                </div>
                <p class="mt-2">${message}</p>
            `;
        }
        if (resultsDiv) {
            resultsDiv.style.display = 'none';
        }
    }

    function hideProgress() {
        if (progressDiv) {
            progressDiv.style.display = 'none';
        }
    }

    async function pollImportProgress(progressId, shouldAutoRefresh) {
        console.log(`🔄 Starting progress polling for ${progressId}`);
        
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
                console.log('📊 Progress update:', progress);
                
                // Update progress bar
                updateProgressBar(progress);
                
                if (progress.status === 'completed') {
                    console.log('✅ Import completed successfully');
                    hideProgress();
                    
                    // Show final results
                    if (progress.result) {
                        showImportResults(progress.result, true);
                        
                        // Auto-refresh if it was a real import (not dry run)
                        if (shouldAutoRefresh && progress.result && progress.result.records_created > 0) {
                            const successMessage = document.createElement('div');
                            successMessage.className = 'alert alert-success text-center mt-3';
                            successMessage.innerHTML = '<i class="fas fa-check-circle"></i> Import completed successfully! Refreshing page...';
                            
                            const resultsDiv = document.getElementById('importResults');
                            if (resultsDiv) {
                                resultsDiv.appendChild(successMessage);
                            }
                            
                            setTimeout(() => {
                                window.location.reload();
                            }, 3000);
                        }
                    }
                    return; // Stop polling
                } else if (progress.status === 'error') {
                    console.log('❌ Import failed');
                    hideProgress();
                    showError('Import failed: ' + (progress.message || 'Unknown error'));
                    return; // Stop polling
                } else if (progress.status === 'running' || progress.status === 'starting') {
                    // Continue polling
                    if (Date.now() - startTime < maxPollTime) {
                        setTimeout(poll, pollInterval);
                    } else {
                        console.log('⏰ Polling timeout');
                        hideProgress();
                        showError('Import is taking longer than expected. Please check the server logs.');
                    }
                }
            } catch (error) {
                console.log('💥 Progress polling error:', error);
                hideProgress();
                showError('Lost connection to import progress. Import may still be running.');
            }
        };
        
        // Start polling
        setTimeout(poll, 500); // Start after 500ms
    }

    function updateProgressBar(progress) {
        const progressBar = document.querySelector('.progress-bar');
        const statusDiv = document.getElementById('importStatus');
        
        if (progressBar) {
            const percentage = progress.percentage || 0;
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
        }
        
        if (statusDiv) {
            const message = progress.message || 'Processing...';
            const recordsProcessed = progress.records_processed || 0;
            const totalRecords = progress.total_records || 0;
            const recordsInfo = totalRecords > 0 
                ? ` (${recordsProcessed}/${totalRecords} records)`
                : '';
            
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

        const isValid = validation.valid;
        const alertClass = isValid ? 'alert-success' : 'alert-warning';
        const icon = isValid ? 'fas fa-check-circle' : 'fas fa-exclamation-triangle';

        let html = `
            <div class="alert ${alertClass}">
                <h5><i class="${icon}"></i> File Validation Results</h5>
                <p><strong>File:</strong> ${validation.file_info.filename}</p>
                <p><strong>Format:</strong> ${validation.file_info.adapter}</p>
                <p><strong>Records Found:</strong> ${validation.records_found}</p>
                <p><strong>Potential Conflicts:</strong> ${validation.potential_conflicts}</p>
            </div>
        `;

        if (validation.errors && validation.errors.length > 0) {
            html += `
                <div class="alert alert-danger">
                    <h6>Errors:</h6>
                    <ul>
                        ${validation.errors.map(error => `<li>${error}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        if (validation.warnings && validation.warnings.length > 0) {
            html += `
                <div class="alert alert-warning">
                    <h6>Warnings:</h6>
                    <ul>
                        ${validation.warnings.map(warning => `<li>${warning}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        resultsDiv.innerHTML = html;
        resultsDiv.style.display = 'block';
    }

    function showImportResults(result, success) {
        console.log("🎯 showImportResults called:", { result, success, resultsDiv: !!resultsDiv });
        if (!resultsDiv) {
            console.error("❌ Results div not found!");
            return;
        }

        // Access result properties directly (not under statistics)
        const alertClass = success ? 'alert-success' : 'alert-danger';
        const icon = success ? 'fas fa-check-circle' : 'fas fa-exclamation-circle';
        const mode = result.dry_run ? 'DRY RUN' : 'EXECUTED';

        let html = `
            <div class="alert ${alertClass}">
                <h5><i class="${icon}"></i> Import Results (${mode})</h5>
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Records Processed:</strong> ${result.records_processed || 0}</p>
                        <p><strong>Records Created:</strong> ${result.records_created || 0}</p>
                        <p><strong>Records Updated:</strong> ${result.records_updated || 0}</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>Records Skipped:</strong> ${result.records_skipped || 0}</p>
                        <p><strong>Conflicts Detected:</strong> ${result.conflicts_detected || 0}</p>
                        <p><strong>Execution Time:</strong> ${(result.execution_time || 0).toFixed(2)}s</p>
                    </div>
                </div>
            </div>
        `;

        if (result.errors && result.errors.length > 0) {
            html += `
                <div class="alert alert-danger">
                    <h6>Errors (${result.errors.length}):</h6>
                    <ul>
                        ${result.errors.slice(0, 10).map(error => `<li>${error}</li>`).join('')}
                        ${result.errors.length > 10 ? `<li><em>... and ${result.errors.length - 10} more errors</em></li>` : ''}
                    </ul>
                </div>
            `;
        }

        if (result.warnings && result.warnings.length > 0) {
            html += `
                <div class="alert alert-warning">
                    <h6>Warnings (${result.warnings.length}):</h6>
                    <ul>
                        ${result.warnings.slice(0, 5).map(warning => `<li>${warning}</li>`).join('')}
                        ${result.warnings.length > 5 ? `<li><em>... and ${result.warnings.length - 5} more warnings</em></li>` : ''}
                    </ul>
                </div>
            `;
        }

        if (result.conflicts && result.conflicts.length > 0) {
            html += `
                <div class="alert alert-info">
                    <h6>Conflicts Resolved (${result.conflicts.length}):</h6>
                    <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Entity</th>
                                    <th>Key</th>
                                    <th>Field</th>
                                    <th>Existing</th>
                                    <th>Import</th>
                                    <th>Resolution</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${result.conflicts.slice(0, 20).map(conflict => `
                                    <tr>
                                        <td>${conflict.entity_type}</td>
                                        <td>${conflict.entity_key}</td>
                                        <td>${conflict.field_name}</td>
                                        <td>${conflict.existing_value}</td>
                                        <td>${conflict.import_value}</td>
                                        <td><span class="badge bg-secondary">${conflict.resolution}</span></td>
                                    </tr>
                                `).join('')}
                                ${result.conflicts.length > 20 ? `
                                    <tr>
                                        <td colspan="6" class="text-center">
                                            <em>... and ${result.conflicts.length - 20} more conflicts</em>
                                        </td>
                                    </tr>
                                ` : ''}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        console.log("📝 Setting results HTML:", html.substring(0, 100) + "...");
        resultsDiv.innerHTML = html;
        resultsDiv.style.display = 'block';
        console.log("✅ Results displayed successfully");
    }

    function showError(message) {
        if (resultsDiv) {
            resultsDiv.innerHTML = `
                <div class="alert alert-danger">
                    <h5><i class="fas fa-exclamation-circle"></i> Error</h5>
                    <p>${message}</p>
                </div>
            `;
            resultsDiv.style.display = 'block';
        }
    }
}

// Debug data loading function
async function loadDebugData() {
    const debugEndpoints = [
        { id: 'debug-courses', url: '/api/debug/courses', key: 'sample_courses' },
        { id: 'debug-instructors', url: '/api/debug/instructors', key: 'sample_instructors' },
        { id: 'debug-sections', url: '/api/debug/sections', key: 'sample_sections' },
        { id: 'debug-terms', url: '/api/debug/terms', key: 'sample_terms' }
    ];

    for (const endpoint of debugEndpoints) {
        try {
            const response = await fetch(endpoint.url);
            const data = await response.json();
            
            const element = document.getElementById(endpoint.id);
            if (element && data.success) {
                const samples = data[endpoint.key] || [];
                const totalCount = data.total_count || 0;
                
                let html = `<div class="mb-2"><strong>Total: ${totalCount}</strong></div>`;
                
                if (samples.length > 0) {
                    html += '<ul class="list-unstyled">';
                    samples.forEach(item => {
                        let itemText = '';
                        if (endpoint.key === 'sample_courses') {
                            itemText = `${item.course_number} - ${item.title} (${item.department})`;
                        } else if (endpoint.key === 'sample_instructors') {
                            itemText = `${item.first_name} ${item.last_name} - ${item.email} (${item.account_status})`;
                        } else if (endpoint.key === 'sample_sections') {
                            itemText = `Section ${item.section_number} - ${item.course_number} (${item.instructor_email})`;
                        } else if (endpoint.key === 'sample_terms') {
                            itemText = `${item.term_name} - ${item.year} ${item.season}`;
                        }
                        html += `<li class="text-truncate">${itemText}</li>`;
                    });
                    html += '</ul>';
                } else {
                    html += '<div class="text-muted">No items found</div>';
                }
                
                element.innerHTML = html;
            } else if (element) {
                element.innerHTML = `<div class="text-danger">Failed to load debug data</div>`;
            }
        } catch (error) {
            console.error(`Failed to load debug ${endpoint.key}:`, error);
            const element = document.getElementById(endpoint.id);
            if (element) {
                element.innerHTML = `<div class="text-danger">Error loading debug data</div>`;
            }
        }
    }
}
