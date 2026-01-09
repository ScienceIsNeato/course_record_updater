/**
 * Course Section Management UI - Create, Edit, Delete Sections
 *
 * Handles:
 * - Create section form submission
 * - Edit section form submission
 * - Delete section confirmation
 * - API communication with CSRF protection
 */

const SECTION_API = "/api/sections";
const TERMS_API = "/api/terms?all=true";
const OFFERINGS_API = "/api/offerings";
const INSTRUCTORS_API = "/api/users?role=instructor";

function publishSectionMutation(action, metadata = {}) {
  globalThis.DashboardEvents?.publishMutation({
    entity: "sections",
    action,
    metadata,
    source: "sectionManagement",
  });
}

function populateSelectOptions(
  selectEl,
  items,
  placeholder,
  getValue,
  getLabel,
) {
  if (!selectEl) return;
  selectEl.innerHTML = "";
  const placeholderOpt = document.createElement("option");
  placeholderOpt.value = "";
  placeholderOpt.textContent = placeholder;
  selectEl.appendChild(placeholderOpt);

  items.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = getValue(item);
    opt.textContent = getLabel(item);
    selectEl.appendChild(opt);
  });
}

async function fetchJson(url) {
  const resp = await fetch(url);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.error || `Failed to fetch ${url}`);
  }
  return resp.json();
}

async function loadTerms(termSelect) {
  if (!termSelect) return { terms: [], selected: null };
  termSelect.innerHTML = '<option value="">Loading terms...</option>'; // nosemgrep
  try {
    const data = await fetchJson(TERMS_API);
    const terms = data.terms || [];
    populateSelectOptions(
      termSelect,
      terms,
      "Select Term",
      (t) => t.term_id || t.id,
      (t) => t.name || t.term_name || "Unnamed Term",
    );
    const active =
      terms.find(
        (t) =>
          (t.status && t.status.toLowerCase() === "active") ||
          (t.timeline_status && t.timeline_status.toLowerCase() === "active") ||
          (t.term_status && t.term_status.toLowerCase() === "active"),
      ) || terms[0];
    if (active) {
      const activeId = active.term_id || active.id;
      termSelect.value = activeId || "";
      return { terms, selected: activeId };
    }
    return { terms, selected: null };
  } catch (err) {
    termSelect.innerHTML = '<option value="">Error loading terms</option>'; // nosemgrep
    console.error("Failed to load terms:", err); // eslint-disable-line no-console
    return { terms: [], selected: null };
  }
}

async function loadOfferings(offeringSelect, termId) {
  if (!offeringSelect) return;
  offeringSelect.innerHTML = '<option value="">Loading offerings...</option>'; // nosemgrep
  try {
    const url = termId
      ? `${OFFERINGS_API}?term_id=${encodeURIComponent(termId)}`
      : OFFERINGS_API;
    const data = await fetchJson(url);
    const offerings = data.offerings || [];
    populateSelectOptions(
      offeringSelect,
      offerings,
      "Select offering...",
      (o) => o.offering_id || o.id,
      (o) => {
        const courseNum = o.course_number || "";
        const courseTitle = o.course_title || o.course_name || "Course";
        const termName = o.term_name || "Term";
        const status = o.status || o.timeline_status || "";
        const statusTag = status ? ` (${status})` : "";
        return `${courseNum ? `${courseNum} - ` : ""}${courseTitle} (${termName})${statusTag}`;
      },
    );
  } catch (err) {
    offeringSelect.innerHTML =
      '<option value="">Error loading offerings</option>'; // nosemgrep
    console.error("Failed to load offerings:", err); // eslint-disable-line no-console
  }
}

async function loadInstructors(instructorSelect) {
  if (!instructorSelect) return;
  instructorSelect.innerHTML = '<option value="">Unassigned</option>'; // nosemgrep
  try {
    const data = await fetchJson(INSTRUCTORS_API);
    const instructors = data.users || data.data || [];
    instructors.forEach((instructor) => {
      const option = document.createElement("option");
      option.value = instructor.user_id || instructor.id;
      option.textContent = `${instructor.first_name} ${instructor.last_name} (${instructor.email})`;
      instructorSelect.appendChild(option);
    });
  } catch (err) {
    console.error("Failed to load instructors:", err); // eslint-disable-line no-console
  }
}

// Initialize when DOM is ready (guard for non-browser test environments)
if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    initializeCreateSectionModal();
    initializeEditSectionModal();
  });
}

const sectionTestExports = {
  loadTerms,
  loadOfferings,
  loadInstructors,
  populateSelectOptions,
  fetchJson,
};

if (typeof module !== "undefined" && module.exports) {
  module.exports = sectionTestExports;
}

/**
 * Initialize Create Section Modal
 * Sets up form submission for new sections
 */
function initializeCreateSectionModal() {
  const form = document.getElementById("createSectionForm");

  if (!form) {
    return; // Form not on this page
  }

  const modalEl = document.getElementById("createSectionModal");
  const termSelect = document.getElementById("sectionTermId");
  const offeringSelect = document.getElementById("sectionOfferingId");
  const instructorSelect = document.getElementById("sectionInstructorId");

  // Load dropdowns when modal opens
  if (modalEl) {
    modalEl.addEventListener("show.bs.modal", async () => {
      const { selected } = await loadTerms(termSelect);
      await loadOfferings(offeringSelect, selected);
      await loadInstructors(instructorSelect);
    });
  }

  // Reload offerings when term changes
  if (termSelect) {
    termSelect.addEventListener("change", async (e) => {
      await loadOfferings(offeringSelect, e.target.value);
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const instructorValue = instructorSelect?.value || "";
    const capacityValue = document.getElementById("sectionCapacity")?.value;
    const dueDateValue = document.getElementById("sectionDueDate")?.value;

    const sectionData = {
      offering_id: offeringSelect?.value,
      section_number: document.getElementById("sectionNumber").value,
      instructor_id: instructorValue || null,
      enrollment: 0, // Start with 0 students enrolled
      capacity:
        capacityValue !== undefined && capacityValue !== ""
          ? Number.parseInt(capacityValue, 10)
          : null, // null means no cap on enrollment
      status: document.getElementById("sectionStatus").value,
    };
    if (dueDateValue) {
      sectionData.due_date = dueDateValue;
    }

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

      const response = await fetch(SECTION_API, {
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
        if (termSelect && termSelect.options.length > 0) {
          termSelect.selectedIndex = 0;
        }
        if (offeringSelect && offeringSelect.options.length > 0) {
          offeringSelect.selectedIndex = 0;
        }
        const sectionNumberInput = document.getElementById("sectionNumber");
        if (sectionNumberInput) {
          sectionNumberInput.value = "001";
        }

        alert(result.message || "Section created successfully!");
        publishSectionMutation("create", { sectionId: result.section_id });

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
      enrollment: enrollmentValue ? Number.parseInt(enrollmentValue) : 0, // Default to 0 students
      status: document.getElementById("editSectionStatus").value,
    };
    const capacityInput = document.getElementById("editSectionCapacity");
    if (capacityInput && capacityInput.value !== "") {
      updateData.capacity = Number.parseInt(capacityInput.value) || null; // null means no cap
    } else {
      updateData.capacity = null; // Explicitly set to null if not provided
    }
    const dueDateInput = document.getElementById("editSectionDueDate");
    if (dueDateInput && dueDateInput.value) {
      updateData.due_date = dueDateInput.value;
    }

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
        publishSectionMutation("update", { sectionId });

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
    sectionData.status || "scheduled";
  const capacityInput = document.getElementById("editSectionCapacity");
  if (capacityInput) {
    const capacity =
      sectionData.capacity ??
      sectionData.enrollment_capacity ??
      sectionData.capacity_limit;
    capacityInput.value =
      typeof capacity === "number" && !Number.isNaN(capacity) ? capacity : "";
  }
  const dueDateInput = document.getElementById("editSectionDueDate");
  if (dueDateInput) {
    const dueValue =
      sectionData.due_date ||
      sectionData.assessment_due_date ||
      sectionData.assessmentDueDate;
    dueDateInput.value = dueValue ? dueValue.split("T")[0] : "";
  }

  // Populate instructor dropdown
  const instructorSelect = document.getElementById("editSectionInstructorId");
  instructorSelect.innerHTML = '<option value="">Unassigned</option>'; // nosemgrep

  try {
    const response = await fetch("/api/users?role=instructor");
    if (response.ok) {
      const data = await response.json();
      const instructors = data.users || [];

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
      publishSectionMutation("delete", { sectionId });

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
