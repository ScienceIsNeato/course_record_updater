/**
 * Course Section Management UI - Create, Edit, Delete Sections
 *
 * Handles:
 * - Create section form submission
 * - Edit section form submission
 * - Delete section confirmation
 * - API communication with CSRF protection
 */

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  initializeCreateSectionModal();
  initializeEditSectionModal();
});

/**
 * Initialize Create Section Modal
 * Sets up form submission for new sections
 */
function initializeCreateSectionModal() {
  const form = document.getElementById("createSectionForm");

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const instructorValue = document.getElementById(
      "sectionInstructorId",
    ).value;
    const enrollmentValue = document.getElementById("sectionEnrollment").value;

    const sectionData = {
      offering_id: document.getElementById("sectionOfferingId").value,
      section_number: document.getElementById("sectionNumber").value,
      instructor_id: instructorValue || null,
      enrollment: enrollmentValue ? Number.parseInt(enrollmentValue) : null,
      status: document.getElementById("sectionStatus").value,
    };

    const createBtn = document.getElementById("createSectionBtn");
    const btnText = createBtn.querySelector(".btn-text");
    const btnSpinner = createBtn.querySelector(".btn-spinner");

    // Show loading state
    btnText.classList.add("d-none");
    btnSpinner.classList.remove("d-none");
    createBtn.disabled = true;

    try {
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      const response = await fetch("/api/sections", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(csrfToken && { "X-CSRFToken": csrfToken }),
        },
        body: JSON.stringify(sectionData),
      });

      if (response.ok) {
        const result = await response.json();

        // Success - close modal and reset form
        const modal = bootstrap.Modal.getInstance(
          document.getElementById("createSectionModal"),
        );
        if (modal) {
          modal.hide();
        }

        form.reset();

        alert(result.message || "Section created successfully!");

        // Reload sections list if function exists
        if (typeof globalThis.loadSections === "function") {
          globalThis.loadSections();
        }
      } else {
        const error = await response.json();
        alert(`Failed to create section: ${error.error || "Unknown error"}`);
      }
    } catch (error) {
      console.error("Error creating section:", error); // eslint-disable-line no-console
      alert(
        "Failed to create section. Please check your connection and try again.",
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
 * Initialize Edit Section Modal
 * Sets up form submission for updating sections
 */
function initializeEditSectionModal() {
  const form = document.getElementById("editSectionForm");

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const sectionId = document.getElementById("editSectionId").value;
    const instructorValue = document.getElementById(
      "editSectionInstructorId",
    ).value;
    const enrollmentValue = document.getElementById(
      "editSectionEnrollment",
    ).value;

    const updateData = {
      section_number: document.getElementById("editSectionNumber").value,
      instructor_id: instructorValue || null,
      enrollment: enrollmentValue ? Number.parseInt(enrollmentValue) : null,
      status: document.getElementById("editSectionStatus").value,
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

      const response = await fetch(`/api/sections/${sectionId}`, {
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
          document.getElementById("editSectionModal"),
        );
        if (modal) {
          modal.hide();
        }

        alert(result.message || "Section updated successfully!");

        // Reload sections list
        if (typeof globalThis.loadSections === "function") {
          globalThis.loadSections();
        }
      } else {
        const error = await response.json();
        alert(`Failed to update section: ${error.error || "Unknown error"}`);
      }
    } catch (error) {
      console.error("Error updating section:", error); // eslint-disable-line no-console
      alert(
        "Failed to update section. Please check your connection and try again.",
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
 * Open Edit Section Modal with pre-populated data
 * Called from section list when Edit button is clicked
 */
async function openEditSectionModal(sectionId, sectionData) {
  document.getElementById("editSectionId").value = sectionId;
  document.getElementById("editSectionNumber").value =
    sectionData.section_number || "";
  document.getElementById("editSectionEnrollment").value =
    sectionData.enrollment || "";
  document.getElementById("editSectionStatus").value =
    sectionData.status || "assigned";

  // Populate instructor dropdown
  const instructorSelect = document.getElementById("editSectionInstructorId");
  instructorSelect.innerHTML = '<option value="">Unassigned</option>'; // nosemgrep

  try {
    const response = await fetch("/api/users?role=instructor");
    if (response.ok) {
      const data = await response.json();
      const instructors = data.data || [];

      instructors.forEach((instructor) => {
        const option = document.createElement("option");
        option.value = instructor.user_id || instructor.id;
        option.textContent = `${instructor.first_name} ${instructor.last_name} (${instructor.email})`;
        instructorSelect.appendChild(option);
      });

      // Set selected instructor
      if (sectionData.instructor_id) {
        instructorSelect.value = sectionData.instructor_id;
      }
    }
  } catch (error) {
    console.error("Error loading instructors:", error); // eslint-disable-line no-console
  }

  const modal = new bootstrap.Modal(
    document.getElementById("editSectionModal"),
  );
  modal.show();
}

/**
 * Delete section with confirmation
 * Shows confirmation dialog before deleting
 */
async function deleteSection(sectionId, courseName, sectionNumber) {
  const confirmation = confirm(
    `Are you sure you want to delete section ${sectionNumber} of ${courseName}?\n\n` +
      "This action cannot be undone.",
  );

  if (!confirmation) {
    return;
  }

  try {
    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]',
    )?.content;

    const response = await fetch(`/api/sections/${sectionId}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken && { "X-CSRFToken": csrfToken }),
      },
    });

    if (response.ok) {
      alert(`Section ${sectionNumber} of ${courseName} deleted successfully.`);

      if (typeof globalThis.loadSections === "function") {
        globalThis.loadSections();
      }
    } else {
      const error = await response.json();
      alert(`Failed to delete section: ${error.error || "Unknown error"}`);
    }
  } catch (error) {
    console.error("Error deleting section:", error); // eslint-disable-line no-console
    alert("Failed to delete section. Please try again.");
  }
}

// Expose functions to window for inline onclick handlers and testing
globalThis.openEditSectionModal = openEditSectionModal;
globalThis.deleteSection = deleteSection;
