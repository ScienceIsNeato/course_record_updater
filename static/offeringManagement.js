/* eslint-disable no-console */
/**
 * Course Offering Management UI - Create, Edit, Delete Offerings
 *
 * Handles:
 * - Create offering form submission
 * - Edit offering form submission
 * - Delete offering confirmation
 * - API communication with CSRF protection
 */

function initOfferingManagement() {
  // Only initialize forms if they exist (handling both dashboard and full list page)
  const createForm = document.getElementById("createOfferingForm");
  const editForm = document.getElementById("editOfferingForm");

  if (createForm || editForm) {
    initializeCreateOfferingModal();
    initializeEditOfferingModal();
    setupModalListeners();
  }
}

/**
 * Set up modal event listeners
 * Populate dropdowns when modals are shown
 */
function setupModalListeners() {
  const createModal = document.getElementById("createOfferingModal");
  const editModal = document.getElementById("editOfferingModal");

  if (createModal) {
    createModal.addEventListener("show.bs.modal", () => {
      loadCoursesAndTermsForCreateDropdown();
    });
  }

  if (editModal) {
    editModal.addEventListener("show.bs.modal", () => {
      loadCoursesAndTermsForEditDropdown();
    });
  }
}

/**
 * Load courses and terms for create offering dropdowns
 * Fetches from API and populates both select elements
 */
async function loadCoursesAndTermsForCreateDropdown() {
  const courseSelect = document.getElementById("offeringCourseId");
  const termSelect = document.getElementById("offeringTermId");
  const programSelect = document.getElementById("offeringProgramId");

  if (!courseSelect || !termSelect || !programSelect) {
    return;
  }

  // Set loading state
  courseSelect.innerHTML = '<option value="">Loading courses...</option>'; // nosemgrep
  termSelect.innerHTML = '<option value="">Loading terms...</option>'; // nosemgrep
  programSelect.innerHTML = '<option value="">Loading programs...</option>'; // nosemgrep

  try {
    // Fetch courses, terms, and programs in parallel
    const [coursesResponse, termsResponse, programsResponse] =
      await Promise.all([
        fetch("/api/courses"),
        fetch("/api/terms?all=true"),
        fetch("/api/programs"),
      ]);

    if (!coursesResponse.ok || !termsResponse.ok || !programsResponse.ok) {
      throw new Error("Failed to fetch dropdown data");
    }

    const coursesData = await coursesResponse.json();
    const termsData = await termsResponse.json();
    const programsData = await programsResponse.json();

    const courses = coursesData.courses || [];
    const terms = termsData.terms || [];
    const programs = programsData.programs || [];

    populateSelectOptions(
      courseSelect,
      courses,
      "Select Course",
      (course) => course.course_id,
      (course) => `${course.course_number} - ${course.course_title}`,
      "No courses available",
    );

    populateSelectOptions(
      termSelect,
      terms,
      "Select Term",
      (term) => term.term_id,
      (term) => term.name,
      "No terms available",
    );

    populateSelectOptions(
      programSelect,
      programs,
      "Select Program",
      (program) => program.program_id || program.id,
      (program) => program.name || program.program_name,
      "No programs available",
    );
  } catch (error) {
    console.error("Failed to load dropdown data:", error);
    courseSelect.innerHTML = '<option value="">Error loading courses</option>'; // nosemgrep
    termSelect.innerHTML = '<option value="">Error loading terms</option>'; // nosemgrep
    programSelect.innerHTML =
      '<option value="">Error loading programs</option>'; // nosemgrep
  }
}

/**
 * Load courses and terms for edit offering dropdowns
 * Fetches from API and populates both select elements
 */
async function loadCoursesAndTermsForEditDropdown() {
  const programSelect = document.getElementById("editOfferingProgramId");

  if (!programSelect) {
    return;
  }

  // Set loading state for programs only (course/term are display-only)
  programSelect.innerHTML = '<option value="">Loading programs...</option>'; // nosemgrep

  try {
    // Fetch programs
    const programsResponse = await fetch("/api/programs");

    if (!programsResponse.ok) {
      throw new Error("Failed to fetch programs");
    }

    const programsData = await programsResponse.json();
    const programs = programsData.programs || [];

    populateSelectOptions(
      programSelect,
      programs,
      "Select Program",
      (program) => program.program_id || program.id,
      (program) => program.name || program.program_name,
      "No programs available",
    );
  } catch (error) {
    console.error("Failed to load programs:", error);
    programSelect.innerHTML =
      '<option value="">Error loading programs</option>'; // nosemgrep
  }
}

function populateSelectOptions(
  selectEl,
  items,
  placeholderText,
  getValue,
  getLabel,
  emptyText,
) {
  selectEl.innerHTML = `<option value="">${placeholderText}</option>`; // nosemgrep

  if (!items || items.length === 0) {
    selectEl.innerHTML = `<option value="">${emptyText}</option>`; // nosemgrep
    return;
  }

  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = getValue(item);
    option.textContent = getLabel(item);
    selectEl.appendChild(option);
  });
}

function setButtonLoading(buttonEl, isLoading) {
  const btnText = buttonEl.querySelector(".btn-text");
  const btnSpinner = buttonEl.querySelector(".btn-spinner");

  if (isLoading) {
    btnText.classList.add("d-none");
    btnSpinner.classList.remove("d-none");
    buttonEl.disabled = true;
    return;
  }

  btnText.classList.remove("d-none");
  btnSpinner.classList.add("d-none");
  buttonEl.disabled = false;
}

/**
 * Initialize Create Offering Modal
 * Sets up form submission for new offerings
 */
function initializeCreateOfferingModal() {
  const form = document.getElementById("createOfferingForm");

  if (!form) {
    return; // Form not on this page
  }

  const addBtn = document.getElementById("addSectionBtn");
  const container = document.getElementById("sectionsContainer");

  if (addBtn && container) {
    addBtn.addEventListener("click", () => {
      const rows = container.querySelectorAll(".section-row");
      const nextIndex = rows.length;
      const sectionNum = (nextIndex + 1).toString().padStart(3, "0");

      const row = document.createElement("div");
      row.className = "section-row row mb-2 align-items-end";
      row.dataset.index = nextIndex;

      // Create section number column
      const col1 = document.createElement("div");
      col1.className = "col-md-10";

      const label = document.createElement("label");
      label.className = "form-label small";
      label.textContent = "Section Number";

      const input = document.createElement("input");
      input.type = "text";
      input.className = "form-control form-control-sm section-number";
      input.name = `section-number-${nextIndex}`;
      input.value = sectionNum;
      input.readOnly = true;

      col1.appendChild(label);
      col1.appendChild(input);

      // Create remove button column
      const col2 = document.createElement("div");
      col2.className = "col-md-2";

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "btn btn-sm btn-outline-danger remove-section-btn";

      const icon = document.createElement("i");
      icon.className = "fas fa-trash";
      removeBtn.appendChild(icon);

      col2.appendChild(removeBtn);

      row.appendChild(col1);
      row.appendChild(col2);
      container.appendChild(row);

      row.querySelector(".remove-section-btn").addEventListener("click", () => {
        row.remove();
        reindexSections(container);
      });
    });
  }

  function reindexSections(cont) {
    const rows = cont.querySelectorAll(".section-row");
    rows.forEach((row, idx) => {
      row.dataset.index = idx;
      const sectionNum = (idx + 1).toString().padStart(3, "0");
      row.querySelector(".section-number").value = sectionNum;
      row.querySelector(".section-number").name = `section-number-${idx}`;
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const programIdValue = document.getElementById("offeringProgramId").value;
    const sections = [];
    if (container) {
      container.querySelectorAll(".section-row").forEach((row) => {
        sections.push({
          section_number: row.querySelector(".section-number").value,
        });
      });
    }

    const offeringData = {
      course_id: document.getElementById("offeringCourseId").value,
      term_id: document.getElementById("offeringTermId").value,
      // Treat empty selection as null so API doesn't receive "" (often fails UUID validation)
      program_id: programIdValue || null,
      status: document.getElementById("offeringStatus").value,
      sections: sections,
    };

    const createBtn = document.getElementById("createOfferingBtn");
    setButtonLoading(createBtn, true);

    try {
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      const response = await fetch("/api/offerings", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(csrfToken && { "X-CSRFToken": csrfToken }),
        },
        body: JSON.stringify(offeringData),
      });

      if (response.ok) {
        const result = await response.json();

        // Success - close modal and reset form
        const modalEl = document.getElementById("createOfferingModal");
        if (modalEl && bootstrap?.Modal) {
          const modal =
            typeof bootstrap.Modal.getOrCreateInstance === "function"
              ? bootstrap.Modal.getOrCreateInstance(modalEl)
              : bootstrap.Modal.getInstance(modalEl) ||
              new bootstrap.Modal(modalEl);
          modal.hide();
        }

        form.reset();

        alert(result.message || "Offering created successfully!");

        // Reload offerings list if function exists
        if (typeof globalThis.loadOfferings === "function") {
          globalThis.loadOfferings();
        }
      } else {
        const error = await response.json();
        alert(`Failed to create offering: ${error.error || "Unknown error"}`);
      }
    } catch (error) {
      console.error("Error creating offering:", error);
      alert(
        "Failed to create offering. Please check your connection and try again.",
      );
    } finally {
      setButtonLoading(createBtn, false);
    }
  });
}

/**
 * Initialize Edit Offering Modal
 * Sets up form submission for updating offerings
 */
function initializeEditOfferingModal() {
  const form = document.getElementById("editOfferingForm");

  if (!form) {
    return; // Form not on this page
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const offeringId = document.getElementById("editOfferingId").value;

    const updateData = {
      program_id: document.getElementById("editOfferingProgramId").value,
      status: document.getElementById("editOfferingStatus").value,
    };

    const saveBtn = this.querySelector('button[type="submit"]');
    setButtonLoading(saveBtn, true);

    try {
      const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

      const response = await fetch(`/api/offerings/${offeringId}`, {
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
          document.getElementById("editOfferingModal"),
        );
        if (modal) {
          modal.hide();
        }

        alert(result.message || "Offering updated successfully!");

        // Reload offerings list
        if (typeof globalThis.loadOfferings === "function") {
          globalThis.loadOfferings();
        }
      } else {
        const error = await response.json();
        alert(`Failed to update offering: ${error.error || "Unknown error"}`);
      }
    } catch (error) {
      console.error("Error updating offering:", error);
      alert(
        "Failed to update offering. Please check your connection and try again.",
      );
    } finally {
      setButtonLoading(saveBtn, false);
    }
  });
}

/**
 * Open Edit Offering Modal with pre-populated data
 * Called from offering list when Edit button is clicked
 */
function openEditOfferingModal(offeringId, offeringData) {
  document.getElementById("editOfferingId").value = offeringId;
  document.getElementById("editOfferingStatus").value =
    offeringData.status || "active";

  // Set display-only fields (Course/Term are immutable)
  document.getElementById("editOfferingCourse").value =
    offeringData.course_name || offeringData.course_title || "";
  document.getElementById("editOfferingTerm").value =
    offeringData.term_name || "";

  // Set program (will be populated by loadCoursesAndTermsForEditDropdown)
  const programSelect = document.getElementById("editOfferingProgramId");
  if (programSelect && offeringData.program_id) {
    // Wait a bit for dropdown to populate, then select
    setTimeout(() => {
      programSelect.value = offeringData.program_id;
    }, 500); // Increased timeout to ensure fetch completes
  }

  const modal = new bootstrap.Modal(
    document.getElementById("editOfferingModal"),
  );
  modal.show();
}

/**
 * Handle click on Edit Offering button
 * Extracts offering data from data attribute and opens modal
 */
function handleEditOfferingClick(button) {
  try {
    const offeringData = JSON.parse(button.dataset.offering);
    openEditOfferingModal(
      offeringData.offering_id || offeringData.id,
      offeringData,
    );
  } catch (error) {
    console.error("Error parsing offering data:", error);
    alert("An error occurred. Please try refreshing the page.");
  }
}

/**
 * Delete offering with confirmation
 * Shows confirmation dialog before deleting
 */
async function deleteOffering(offeringId, courseName, termName) {
  const confirmation = confirm(
    `Are you sure you want to delete the offering for ${courseName} in ${termName}?\n\n` +
    "This action cannot be undone. All sections for this offering will be deleted.",
  );

  if (!confirmation) {
    return;
  }

  try {
    const csrfToken = document.querySelector(
      'meta[name="csrf-token"]',
    )?.content;

    const response = await fetch(`/api/offerings/${offeringId}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken && { "X-CSRFToken": csrfToken }),
      },
    });

    if (response.ok) {
      alert(`Offering for ${courseName} in ${termName} deleted successfully.`);

      if (typeof globalThis.loadOfferings === "function") {
        globalThis.loadOfferings();
      }
    } else {
      const error = await response.json();
      alert(`Failed to delete offering: ${error.error || "Unknown error"}`);
    }
  } catch (error) {
    console.error("Error deleting offering:", error);
    alert("Failed to delete offering. Please try again.");
  }
}

/**
 * Load and display offerings in the container
 */
async function loadOfferings() {
  const container = document.getElementById("offeringsTableContainer");
  if (!container) return; // Not on listings page

  // nosemgrep
  container.innerHTML = `
      <output class="d-flex justify-content-center align-items-center" style="min-height: 200px;" aria-live="polite">
        <div class="spinner-border" aria-hidden="true">
          <span class="visually-hidden">Loading offerings...</span>
        </div>
      </output>
    `;

  try {
    const response = await fetch("/api/offerings");
    if (!response.ok) {
      throw new Error("Failed to load offerings");
    }
    const data = await response.json();

    // Look for the offerings list in multiple possible keys for robustness
    const offerings = data.offerings || data || [];

    if (offerings.length === 0) {
      // nosemgrep
      container.innerHTML = `
          <div class="alert alert-info">
            <i class="fas fa-info-circle me-2"></i>
            No course offerings found. Create an offering to get started.
          </div>
        `;
      return;
    }

    let html = `
        <div class="table-responsive">
          <table class="table table-striped table-hover">
            <thead>
              <tr>
                <th>Course</th>
                <th>Program</th>
                <th>Term</th>
                <th>Status</th>
                <th>Sections</th>
                <th>Enrollment</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
      `;

    offerings.forEach((offering) => {
      const courseName =
        offering.course_name ||
        offering.course_title ||
        offering.course_number ||
        "Unknown Course";
      const termName = offering.term_name || offering.term || "Unknown Term";
      const statusBadge =
        offering.status === "active"
          ? '<span class="badge bg-success">Active</span>'
          : `<span class="badge bg-secondary">${offering.status}</span>`;

      // Safe JSON stringify for the edit button
      const offeringJson = JSON.stringify(offering)
        .replace(/'/g, "&apos;")
        .replace(/"/g, "&quot;");

      html += `
          <tr>
            <td><strong>${courseName}</strong></td>
            <td>${(offering.program_names && offering.program_names.length > 0) ? offering.program_names.join(", ") : "-"}</td>
            <td>${termName}</td>
            <td>${statusBadge}</td>
            <td>${offering.section_count || 0}</td>
            <td>${offering.total_enrollment || 0}</td>
            <td>
            <td>
              <button class="btn btn-sm btn-outline-secondary" 
                      data-offering='${offeringJson}'
                      onclick="handleEditOfferingClick(this)">
                <i class="fas fa-edit"></i> Edit
              </button>
              <button class="btn btn-sm btn-outline-danger" onclick='deleteOffering("${offering.offering_id || offering.id}", "${courseName}", "${termName}")'>
                <i class="fas fa-trash"></i> Delete
              </button>
            </td>
          </tr>
        `;
    });

    html += "</tbody></table></div>";
    container.innerHTML = html; // nosemgrep
  } catch (error) {
    console.error("Error loading offerings:", error);
    // nosemgrep
    container.innerHTML = `
        <div class="alert alert-danger">
          <i class="fas fa-exclamation-triangle me-2"></i>
          Error loading offerings: ${error.message}
        </div>
      `;
  }
}

// Expose functions to window for inline onclick handlers and testing
globalThis.openEditOfferingModal = openEditOfferingModal;
globalThis.deleteOffering = deleteOffering;
globalThis.loadOfferings = loadOfferings;
globalThis.openCreateOfferingModal = () => {
  if (typeof loadCoursesAndTermsForCreateDropdown === "function") {
    loadCoursesAndTermsForCreateDropdown();
  }
  const modal = new bootstrap.Modal(
    document.getElementById("createOfferingModal"),
  );
  modal.show();
};

// Initialize when DOM is ready
if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initOfferingManagement);
  } else {
    initOfferingManagement();
  }
}

// Expose on window as well for test environment
if (typeof window !== "undefined") {
  window.openEditOfferingModal = openEditOfferingModal;
  window.handleEditOfferingClick = handleEditOfferingClick;
  window.deleteOffering = deleteOffering;
  window.loadOfferings = loadOfferings;
}

// Export for testing
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    initOfferingManagement,
    openEditOfferingModal,
    deleteOffering,
    loadOfferings,
  };
}
