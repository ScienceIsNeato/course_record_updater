// static/script.js

document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM fully loaded and parsed");

    const courseTableBody = document.querySelector('#display-section table tbody');

    if (!courseTableBody) {
        console.error("Course table body not found!");
        return;
    }

    // --- Event Delegation for Edit/Delete/Save/Cancel --- 
    courseTableBody.addEventListener('click', async (event) => {
        const target = event.target;
        const row = target.closest('tr');
        if (!row) return;
        const courseId = target.dataset.id;

        // --- EDIT Button Click --- 
        if (target.classList.contains('edit-btn')) {
            console.log(`Edit clicked for ID: ${courseId}`);
            makeRowEditable(row);
        }
        // --- DELETE Button Click --- 
        else if (target.classList.contains('delete-btn')) {
            console.log(`Delete clicked for ID: ${courseId}`);
            const courseNumber = target.dataset.number; 
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

    // --- Helper Functions --- 

    function makeRowEditable(row) {
        // Store original values & switch action buttons
        const originalValues = {};
        const actionCell = row.querySelector('.actions-cell');
        
        row.querySelectorAll('td').forEach((cell, index) => {
            if (cell === actionCell) return; // Skip actions cell

            const fieldName = getFieldNameByIndex(index); // Helper to map index to field name
            if (!fieldName) return; 

            const originalValue = cell.textContent.trim();
            originalValues[fieldName] = originalValue;
            
            // Replace cell content with input field
            const input = document.createElement('input');
            input.type = (fieldName === 'year' || fieldName === 'num_students') ? 'number' : 'text';
            input.name = fieldName;
            input.value = originalValue;
            input.classList.add('inline-edit-input'); // Add class for styling/selection
            cell.innerHTML = ''; // Clear cell
            cell.appendChild(input);
        });

        // Store original values on the row for cancel functionality
        row.dataset.originalValues = JSON.stringify(originalValues);

        // Change buttons
        actionCell.innerHTML = `
            <button class="save-btn" data-id="${row.cells[0].textContent.trim()}">Save</button>
            <button class="cancel-btn" data-id="${row.cells[0].textContent.trim()}">Cancel</button>
        `;
    }

    async function handleSave(row, courseId) {
        const inputs = row.querySelectorAll('input.inline-edit-input');
        const updatedData = {};
        let hasError = false;

        inputs.forEach(input => {
            updatedData[input.name] = input.value.trim();
            // Basic client-side validation example (can be expanded)
            if (!input.value.trim() && isFieldRequired(input.name)) { 
                input.style.borderColor = 'red'; 
                hasError = true;
            } else {
                input.style.borderColor = ''; // Reset border
            }
        });
        
        if (hasError) {
            alert("Please fill in all required fields.");
            return; // Prevent saving
        }

        console.log("Saving data:", updatedData);

        try {
            const response = await fetch(`/edit_course/${courseId}`, {
                method: 'POST', // Or PUT, matching backend route
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
                    cell.textContent = input.value.trim(); // Update display
                });
                revertRowToActionButtons(row, courseId);
            } else {
                console.error("Update failed:", result.error || `HTTP ${response.status}`);
                alert(`Error updating course: ${result.error || 'Server error'}`);
                // Optionally revert changes on failure, or leave editable
                // cancelEdit(row); // Example: revert on failure
            }
        } catch (error) {
            console.error("Network or fetch error during save:", error);
            alert("Failed to send update request.");
        }
    }

    function cancelEdit(row) {
        const originalValues = JSON.parse(row.dataset.originalValues || '{}');
        
        row.querySelectorAll('td').forEach((cell, index) => {
            const input = cell.querySelector('input.inline-edit-input');
            if (input) {
                const fieldName = input.name;
                cell.textContent = originalValues[fieldName] !== undefined ? originalValues[fieldName] : '';
            }
        });

        revertRowToActionButtons(row, row.cells[0].textContent.trim());
    }

    function handleDelete(row, courseId, courseNumber) {
        // Simple confirmation for now - enhance as needed
        const confirmation = prompt(`To delete course ${courseNumber}, please type its number below:`);
        
        if (confirmation === null) { // User pressed cancel
            console.log("Delete cancelled by user.");
            return;
        }

        if (confirmation.trim() !== courseNumber) {
            alert("Incorrect course number entered. Deletion cancelled.");
            return;
        }

        // Proceed with deletion
        console.log(`Attempting to delete ID: ${courseId}`);
        fetch(`/delete_course/${courseId}`, {
            method: 'POST' // Or DELETE, matching backend
        })
        .then(response => {
            if (!response.ok) {
                // Try to get error message from JSON response
                return response.json().then(err => { throw new Error(err.error || `HTTP ${response.status}`) });
            }
            return response.json(); // Expect success JSON
        })
        .then(result => {
            if (result.success) {
                console.log("Delete successful");
                row.remove(); // Remove row from table
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

    function revertRowToActionButtons(row, courseId) {
        const actionCell = row.querySelector('.actions-cell');
        if (actionCell) {
            actionCell.innerHTML = `
                <button class="edit-btn" data-id="${courseId}">Edit</button>
                <button class="delete-btn" data-id="${courseId}" data-number="${row.cells[2].textContent.trim()}">Delete</button>
            `; // Assumes course number is in the 3rd cell (index 2)
        }
         // Clean up dataset
        delete row.dataset.originalValues;
    }

    function getFieldNameByIndex(index) {
        // Map table column index to field name (must match table structure in index.html)
        const fieldMap = [
            'id', // 0 - Assuming ID is first, not editable
            'course_title', // 1
            'course_number', // 2
            'semester', // 3
            'year', // 4
            'professor', // 5
            'num_students' // 6
        ];
        return fieldMap[index] || null;
    }
    
    function isFieldRequired(fieldName) {
        // Mirror required fields from BaseAdapter (adjust if needed)
         const requiredFields = ['course_title', 'course_number', 'semester', 'year', 'professor'];
         return requiredFields.includes(fieldName);
    }

}); 