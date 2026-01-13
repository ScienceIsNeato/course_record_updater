// Admin Interface JavaScript - User Management

// Global state
let currentUsers = [];
let currentInvitations = [];
const selectedUsers = new Set();
const selectedInvitations = new Set();
let currentPage = 1;
const itemsPerPage = 20;
let totalItems = 0;
let currentTab = "users";
let filters = {
  search: "",
  role: "",
  status: "",
};

function hasUserManagementView() {
  return document.getElementById("usersTableBody") !== null;
}

function hasInvitationsView() {
  return document.getElementById("invitationsTableBody") !== null;
}

const inviteModalWorkflows = new Map();
const DEFAULT_INVITE_WORKFLOW = "default";
const INVITATION_EMAIL_FAILED_MESSAGE =
  "Invitation created but email failed to send";

function registerInviteModalWorkflow(name, { reset, setup } = {}) {
  inviteModalWorkflows.set(name, {
    reset: typeof reset === "function" ? reset : () => {},
    setup: typeof setup === "function" ? setup : () => {},
  });
}

function _getInviteModalWorkflow(name) {
  return (
    inviteModalWorkflows.get(name) ||
    inviteModalWorkflows.get(DEFAULT_INVITE_WORKFLOW) || {
      reset: () => {},
      setup: () => {},
    }
  );
}

function __resetInviteModalWorkflows() {
  inviteModalWorkflows.clear();
}

function __getInviteModalWorkflows() {
  return Array.from(inviteModalWorkflows.keys());
}

// DOM Content Loaded
document.addEventListener("DOMContentLoaded", () => {
  initializeAdminInterface();
});

// Initialize Admin Interface
function initializeAdminInterface() {
  // Check if we're on the user management page
  const isUserManagementPage = hasUserManagementView();

  initializeEventListeners();

  // Only initialize user management features if on that page
  if (isUserManagementPage) {
    initializeFilters();
    initializeTabs();

    // Load initial data
    loadUsers();
    loadInvitations();
  }

  // Initialize modals (available on all pages with admin.js)
  initializeModals();

  // Load programs (needed for invite modal on all pages)
  loadPrograms();
}

// Event Listeners
function initializeEventListeners() {
  // Only initialize user management page elements if they exist
  const searchInput = document.getElementById("searchInput");
  const roleFilter = document.getElementById("roleFilter");
  const statusFilter = document.getElementById("statusFilter");
  const clearFiltersBtn = document.getElementById("clearFilters");
  const selectAllUsers = document.getElementById("selectAllUsers");
  const selectAllInvitations = document.getElementById("selectAllInvitations");
  const bulkResendInvitations = document.getElementById(
    "bulkResendInvitations",
  );

  const editUserForm = document.getElementById("editUserForm");
  const usersTableBody = document.getElementById("usersTableBody");

  // Search and filters (only on user management page)
  if (searchInput) {
    searchInput.addEventListener("input", debounce(handleSearchChange, 300));
  }
  if (roleFilter) {
    roleFilter.addEventListener("change", handleFilterChange);
  }
  if (statusFilter) {
    statusFilter.addEventListener("change", handleFilterChange);
  }
  if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener("click", clearFilters);
  }

  // Bulk selection (only on user management page)
  if (selectAllUsers) {
    selectAllUsers.addEventListener("change", handleSelectAllUsers);
  }
  if (selectAllInvitations) {
    selectAllInvitations.addEventListener("change", handleSelectAllInvitations);
  }

  // Bulk actions (only on user management page)
  if (bulkResendInvitations) {
    bulkResendInvitations.addEventListener(
      "click",
      handleBulkResendInvitations,
    );
  }

  // Forms - inviteUserForm should exist on all pages with the modal
  const inviteUserForm = document.getElementById("inviteUserForm");
  if (inviteUserForm) {
    inviteUserForm.addEventListener("submit", handleInviteUser);
  }

  if (editUserForm) {
    editUserForm.addEventListener("submit", handleEditUser);
  }

  // Role selection for program assignment (in invite modal)
  const inviteRole = document.getElementById("inviteRole");
  if (inviteRole) {
    inviteRole.addEventListener("change", handleRoleSelectionChange);
  }

  // Event delegation for user action buttons (only on user management page)
  if (usersTableBody) {
    usersTableBody.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-action]");
      if (!button) return;

      const action = button.dataset.action;
      const userId = button.dataset.userId;

      if (action === "edit-user") {
        editUser(userId);
      } else if (action === "toggle-user-status") {
        toggleUserStatus(userId);
      }
    });
  }

  // Event delegation for invitation action buttons
  const invitationsTableBody = document.getElementById("invitationsTableBody");
  if (invitationsTableBody) {
    invitationsTableBody.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-action]");
      if (!button) return;

      const action = button.dataset.action;
      const invitationId = button.dataset.invitationId;

      if (action === "resend-invitation") {
        resendInvitation(invitationId);
      } else if (action === "cancel-invitation") {
        cancelInvitation(invitationId);
      }
    });
  }
}

// Initialize Filters
function initializeFilters() {
  const searchInput = document.getElementById("searchInput");
  const roleFilter = document.getElementById("roleFilter");
  const statusFilter = document.getElementById("statusFilter");

  if (!searchInput || !roleFilter || !statusFilter) {
    return; // Not on user management page
  }

  const urlParams = new URLSearchParams(globalThis.location.search);
  filters.search = urlParams.get("search") || "";
  filters.role = urlParams.get("role") || "";
  filters.status = urlParams.get("status") || "";

  searchInput.value = filters.search;
  roleFilter.value = filters.role;
  statusFilter.value = filters.status;
}

// Initialize Tabs
function initializeTabs() {
  const tabElements = document.querySelectorAll(
    '#userTabs button[data-bs-toggle="tab"]',
  );
  tabElements.forEach((tab) => {
    tab.addEventListener("shown.bs.tab", (event) => {
      const target = event.target.dataset.bsTarget;
      currentTab = target.includes("users") ? "users" : "invitations";
      currentPage = 1;
      updateDisplay();
    });
  });
}

// Initialize Modals
function initializeModals() {
  const inviteUserModalEl = document.getElementById("inviteUserModal");
  const inviteUserFormEl = document.getElementById("inviteUserForm");
  if (inviteUserModalEl && inviteUserFormEl) {
    inviteUserModalEl.addEventListener("hidden.bs.modal", () => {
      inviteUserFormEl.reset();
      inviteUserFormEl.classList.remove("was-validated");
    });
  }

  const editUserModalEl = document.getElementById("editUserModal");
  const editUserFormEl = document.getElementById("editUserForm");
  if (editUserModalEl && editUserFormEl) {
    editUserModalEl.addEventListener("hidden.bs.modal", () => {
      editUserFormEl.reset();
      editUserFormEl.classList.remove("was-validated");
    });
  }
}

// Load Users
async function loadUsers() {
  try {
    showLoading("users");

    const response = await fetch("/api/users");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    if (data.success) {
      currentUsers = data.users || [];
      document.getElementById("usersCount").textContent = currentUsers.length;
      updateDisplay();
    } else {
      throw new Error(data.error || "Failed to load users");
    }
  } catch (error) {
    console.error("Error loading users:", error); // eslint-disable-line no-console
    showError("Failed to load users: " + error.message);
    showEmpty("users");
  }
}

// Load Invitations
async function loadInvitations() {
  if (!hasInvitationsView()) {
    return;
  }

  try {
    showLoading("invitations");

    const response = await fetch("/api/auth/invitations");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    if (data.success) {
      currentInvitations = data.invitations || [];
      const invitationsCountEl = document.getElementById("invitationsCount");
      if (invitationsCountEl) {
        invitationsCountEl.textContent = currentInvitations.length;
      }
      updateDisplay();
    } else {
      throw new Error(data.error || "Failed to load invitations");
    }
  } catch (error) {
    console.error("Error loading invitations:", error); // eslint-disable-line no-console
    showError("Failed to load invitations: " + error.message);
    showEmpty("invitations");
  }
}

// Load Programs for invitation form
async function loadPrograms() {
  try {
    const response = await fetch("/api/programs");
    if (response.ok) {
      const data = await response.json();
      if (data.success) {
        const programSelect = document.getElementById("invitePrograms");
        if (!programSelect) return;
        programSelect.innerHTML = ""; // nosemgrep

        data.programs.forEach((program) => {
          const option = document.createElement("option");
          option.value = program.id;
          option.textContent = program.name;
          programSelect.appendChild(option);
        });
      }
    }
  } catch (error) {
    console.warn("Error loading programs:", error); // eslint-disable-line no-console
  }
}

// Filter and Search Functions
function handleSearchChange(event) {
  filters.search = event.target.value;
  currentPage = 1;
  updateDisplay();
  updateURL();
}

function handleFilterChange() {
  filters.role = document.getElementById("roleFilter").value;
  filters.status = document.getElementById("statusFilter").value;
  currentPage = 1;
  updateDisplay();
  updateURL();
}

function clearFilters() {
  filters = { search: "", role: "", status: "" };
  document.getElementById("searchInput").value = "";
  document.getElementById("roleFilter").value = "";
  document.getElementById("statusFilter").value = "";
  currentPage = 1;
  updateDisplay();
  updateURL();
}

function getFilteredData() {
  const data = currentTab === "users" ? currentUsers : currentInvitations;
  return data.filter((item) => applyAllFilters(item));
}

function applyAllFilters(item) {
  return (
    applySearchFilter(item) && applyRoleFilter(item) && applyStatusFilter(item)
  );
}

function applySearchFilter(item) {
  if (!filters.search) {
    return true;
  }

  const searchTerm = filters.search.toLowerCase();
  const searchableText = buildSearchableText(item);
  return searchableText.includes(searchTerm);
}

function buildSearchableText(item) {
  if (currentTab === "users") {
    return `${item.first_name} ${item.last_name} ${item.email}`.toLowerCase();
  } else {
    return `${item.email} ${item.invited_by || ""}`.toLowerCase();
  }
}

function applyRoleFilter(item) {
  if (!filters.role) {
    return true;
  }
  return item.role === filters.role;
}

function applyStatusFilter(item) {
  if (!filters.status) {
    return true;
  }

  if (currentTab === "users") {
    return applyUserStatusFilter(item);
  } else {
    return item.status === filters.status;
  }
}

function applyUserStatusFilter(item) {
  switch (filters.status) {
    case "active":
      return item.account_status === "active";
    case "pending":
      return item.account_status === "pending_verification";
    case "inactive":
      return item.account_status === "inactive";
    default:
      return true;
  }
}

// Display Functions
function updateDisplay() {
  const filteredData = getFilteredData();
  totalItems = filteredData.length;

  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const pageData = filteredData.slice(startIndex, endIndex);

  if (currentTab === "users") {
    displayUsers(pageData);
  } else {
    displayInvitations(pageData);
  }

  updatePagination();
  updateBulkActions();
  updateCounts();
}

function displayUsers(users) {
  const tbody = document.getElementById("usersTableBody");

  hideLoading("users");

  if (users.length === 0) {
    showEmpty("users");
    return;
  }

  hideEmpty("users");

  tbody.innerHTML = users // nosemgrep
    .map(
      (user) => `
        <tr data-user-id="${user.id}">
            <td>
                <div class="form-check">
                    <input class="form-check-input user-checkbox" type="checkbox" value="${user.id}" 
                           onchange="handleUserSelection('${user.id}', this.checked)">
                </div>
            </td>
            <td>
                <div class="user-info">
                    <div class="user-avatar">
                        ${getInitials(user.first_name, user.last_name)}
                    </div>
                    <div class="user-details">
                        <h6>${escapeHtml(user.first_name)} ${escapeHtml(user.last_name)}</h6>
                        <div class="text-muted">${escapeHtml(user.email)}</div>
                    </div>
                </div>
            </td>
            <td>
                <span class="role-badge role-${user.role}">${formatRole(user.role)}</span>
            </td>
            <td>
                <span class="status-badge status-${getDisplayStatus(user)}">${formatStatus(getDisplayStatus(user))}</span>
            </td>
            <td>
                <div class="last-active">
                    <span class="activity-indicator ${getActivityStatus(user.last_login)}"></span>
                    <span class="time">${formatLastActive(user.last_login)}</span>
                </div>
            </td>
            <td>
                <div class="program-tags">
                    ${
                      (user.programs || user.program_names || [])
                        .map(
                          (name) => `<span class="program-tag">${name}</span>`,
                        )
                        .join("") ||
                      (user.program_ids || [])
                        .map(() => '<span class="program-tag">Program</span>')
                        .join("")
                    }
                    ${!user.programs && !user.program_names && (!user.program_ids || user.program_ids.length === 0) ? '<span class="text-muted">No programs</span>' : ""}
                </div>
            </td>
            <td>
                <div class="action-buttons">
                    <button class="action-btn btn-edit" data-user-id="${user.id}" data-action="edit-user" title="Edit User">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="action-btn btn-deactivate" data-user-id="${user.id}" data-action="toggle-user-status" title="${user.account_status === "active" ? "Deactivate" : "Activate"} User">
                        <i class="fas fa-${user.account_status === "active" ? "user-slash" : "user-check"}"></i>
                    </button>
                </div>
            </td>
        </tr>
    `,
    )
    .join("");
}

function displayInvitations(invitations) {
  const tbody = document.getElementById("invitationsTableBody");

  hideLoading("invitations");

  if (invitations.length === 0) {
    showEmpty("invitations");
    return;
  }

  hideEmpty("invitations");

  tbody.innerHTML = invitations // nosemgrep
    .map(
      (invitation) => `
        <tr data-invitation-id="${invitation.id}">
            <td>
                <div class="form-check">
                    <input class="form-check-input invitation-checkbox" type="checkbox" value="${invitation.id}" 
                           onchange="handleInvitationSelection('${invitation.id}', this.checked)">
                </div>
            </td>
            <td>
                <div class="user-details">
                    <h6>${escapeHtml(invitation.email)}</h6>
                    ${invitation.personal_message ? `<div class="text-muted small">${escapeHtml(invitation.personal_message)}</div>` : ""}
                </div>
            </td>
            <td>
                <span class="role-badge role-${invitation.role}">${formatRole(invitation.role)}</span>
            </td>
            <td>
                <span class="status-badge status-${invitation.status}">${formatStatus(invitation.status)}</span>
            </td>
            <td>
                <div class="text-muted small">${escapeHtml(invitation.invited_by || "Unknown")}</div>
            </td>
            <td>
                <div class="text-muted small">${formatDate(invitation.invited_at)}</div>
            </td>
            <td>
                <div class="text-muted small">
                    ${invitation.status === "pending" && invitation.expires_at ? formatExpiryDate(invitation.expires_at) : "-"}
                </div>
            </td>
            <td>
                <div class="action-buttons">
                    ${
                      invitation.status === "pending"
                        ? `
                        <button class="action-btn btn-resend" data-invitation-id="${invitation.id}" data-action="resend-invitation" title="Resend Invitation">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                        <button class="action-btn btn-cancel" data-invitation-id="${invitation.id}" data-action="cancel-invitation" title="Cancel Invitation">
                            <i class="fas fa-times"></i>
                        </button>
                    `
                        : `
                        <span class="text-muted small">No actions</span>
                    `
                    }
                </div>
            </td>
        </tr>
    `,
    )
    .join("");
}

// Selection Handlers
function handleSelectAllUsers(event) {
  const isChecked = event.target.checked;
  const checkboxes = document.querySelectorAll(".user-checkbox");

  checkboxes.forEach((checkbox) => {
    checkbox.checked = isChecked;
    handleUserSelection(checkbox.value, isChecked);
  });
}

function handleSelectAllInvitations(event) {
  const isChecked = event.target.checked;
  const checkboxes = document.querySelectorAll(".invitation-checkbox");

  checkboxes.forEach((checkbox) => {
    checkbox.checked = isChecked;
    handleInvitationSelection(checkbox.value, isChecked);
  });
}

function handleUserSelection(userId, isSelected) {
  if (isSelected) {
    selectedUsers.add(userId);
  } else {
    selectedUsers.delete(userId);
  }
  updateBulkActions();
}

function handleInvitationSelection(invitationId, isSelected) {
  if (isSelected) {
    selectedInvitations.add(invitationId);
  } else {
    selectedInvitations.delete(invitationId);
  }
  updateBulkActions();
}

// Bulk Actions
function updateBulkActions() {
  const bulkActionsBtn = document.getElementById("bulkActionsDropdown");
  const hasSelection =
    (currentTab === "users" && selectedUsers.size > 0) ||
    (currentTab === "invitations" && selectedInvitations.size > 0);

  bulkActionsBtn.disabled = !hasSelection;
}

async function handleBulkResendInvitations() {
  if (selectedInvitations.size === 0) return;

  const confirmed = await showConfirmation(
    "Resend Invitations",
    `Are you sure you want to resend ${selectedInvitations.size} invitation(s)?`,
  );

  if (confirmed) {
    for (const invitationId of selectedInvitations) {
      await resendInvitation(invitationId, false);
    }
    selectedInvitations.clear();
    if (hasInvitationsView()) {
      loadInvitations();
    }
    showSuccess(`Successfully resent ${selectedInvitations.size} invitations.`);
  }
}

// User Management Functions
async function handleInviteUser(event) {
  event.preventDefault();

  const form = event.target;
  const formData = new FormData(form);
  const submitBtn = document.getElementById("sendInviteBtn");

  if (!form.checkValidity()) {
    form.classList.add("was-validated");
    return;
  }

  setButtonLoadingState(submitBtn, true);

  try {
    const data = {
      invitee_email: formData.get("invitee_email"),
      invitee_role: formData.get("invitee_role"),
      personal_message: formData.get("personal_message") || undefined,
    };
    const firstName = formData.get("first_name");
    const lastName = formData.get("last_name");
    if (firstName) {
      data.first_name = firstName;
    }
    if (lastName) {
      data.last_name = lastName;
    }

    // Add program IDs if role is program_admin
    if (data.invitee_role === "program_admin") {
      const programIds = Array.from(
        document.getElementById("invitePrograms").selectedOptions,
      ).map((option) => option.value);
      if (programIds.length > 0) {
        data.program_ids = programIds;
      }
    }

    // Add section ID if provided (for section assignment)
    const sectionId = formData.get("section_id");
    if (sectionId) {
      data.section_id = sectionId;
    }

    // Get CSRF token
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

    const response = await fetch("/api/auth/invite", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken && { "X-CSRFToken": csrfToken }),
      },
      body: JSON.stringify(data),
    });

    const result = await response.json();

    if (response.ok && result.success) {
      const successMessage = result.message || "Invitation sent successfully!";
      displayInvitationResult(successMessage, result.email_error);
      bootstrap.Modal.getInstance(
        document.getElementById("inviteUserModal"),
      ).hide();
      if (hasInvitationsView()) {
        loadInvitations();
      }

      // Notify other components that a faculty member has been invited/assigned
      document.dispatchEvent(new CustomEvent("faculty-invited"));
    } else {
      throw new Error(result.error || "Failed to send invitation");
    }
  } catch (error) {
    console.error("Error sending invitation:", error); // eslint-disable-line no-console
    showError("Failed to send invitation: " + error.message);
  } finally {
    setButtonLoadingState(submitBtn, false);
  }
}

/**
 * Unified function to open the invite user modal with optional pre-population
 * @param {Object} options - Configuration options
 * @param {string} options.sectionId - Section ID to assign instructor to (optional)
 * @param {string} options.prefillRole - Role to pre-select (optional)
 * @param {string} options.programId - Program ID to pre-select for program_admin (optional)
 */
function openInviteModal(options = {}) {
  const modalElement = document.getElementById("inviteUserModal");
  if (!modalElement) {
    console.warn("Invite modal is not present in the current DOM.");
    return;
  }

  const workflowName = options.workflow || DEFAULT_INVITE_WORKFLOW;
  const workflow = _getInviteModalWorkflow(workflowName);
  const context = {
    modal: modalElement,
    form: document.getElementById("inviteUserForm"),
    sectionGroup: document.getElementById("sectionAssignmentGroup"),
    sectionIdField: document.getElementById("inviteSectionId"),
    roleSelect: document.getElementById("inviteRole"),
    firstNameField: document.getElementById("inviteFirstName"),
    lastNameField: document.getElementById("inviteLastName"),
    programSelection: document.getElementById("programSelection"),
    inviteProgramsSelect: document.getElementById("invitePrograms"),
    options,
  };

  workflow.reset(context);
  workflow.setup(context);
  const modal = new bootstrap.Modal(modalElement);
  modal.show();
}

// Make function globally available for onclick handlers
globalThis.openInviteModal = openInviteModal;

function handleRoleSelectionChange(event) {
  const selectedRole = event.target.value;

  setProgramSelectionVisibility(selectedRole);
}

function setProgramSelectionVisibility(role) {
  const programSelection = document.getElementById("programSelection");
  const invitePrograms = document.getElementById("invitePrograms");
  if (!programSelection || !invitePrograms) return;

  if (role === "program_admin") {
    programSelection.style.display = "block";
    invitePrograms.required = true;
  } else {
    programSelection.style.display = "none";
    invitePrograms.required = false;
  }
}

registerInviteModalWorkflow(DEFAULT_INVITE_WORKFLOW, {
  reset({ form, sectionGroup, sectionIdField, roleSelect }) {
    if (form) {
      form.reset();
      form.classList.remove("was-validated");
    }
    if (sectionGroup) {
      sectionGroup.style.display = "none";
    }
    if (sectionIdField) {
      sectionIdField.value = "";
    }
    if (roleSelect) {
      roleSelect.value = "instructor";
      setProgramSelectionVisibility("instructor");
    }
  },
  setup({
    options = {},
    sectionGroup,
    sectionIdField,
    roleSelect,
    inviteProgramsSelect,
    firstNameField,
    lastNameField,
  }) {
    const hasSection = Boolean(options.sectionId);
    if (hasSection && sectionGroup) {
      sectionGroup.style.display = "block";
      if (sectionIdField) {
        sectionIdField.value = options.sectionId;
      }
    }

    const roleToApply =
      options.prefillRole ||
      (hasSection ? "instructor" : roleSelect?.value) ||
      "instructor";
    if (roleSelect) {
      roleSelect.value = roleToApply;
    }
    setProgramSelectionVisibility(roleToApply);

    if (firstNameField) {
      firstNameField.value = options.firstName || "";
    }
    if (lastNameField) {
      lastNameField.value = options.lastName || "";
    }

    if (
      options.programId &&
      roleToApply === "program_admin" &&
      inviteProgramsSelect
    ) {
      const applySelection = () => {
        Array.from(inviteProgramsSelect.options).forEach((opt) => {
          opt.selected = opt.value === options.programId;
        });
      };
      if (inviteProgramsSelect.options.length === 0) {
        setTimeout(applySelection, 50);
      } else {
        applySelection();
      }
    }
  },
});

registerInviteModalWorkflow("sectionAssignment", {
  reset: _getInviteModalWorkflow(DEFAULT_INVITE_WORKFLOW).reset,
  setup(context) {
    const defaultWorkflow = _getInviteModalWorkflow(DEFAULT_INVITE_WORKFLOW);
    defaultWorkflow.setup(context);
    if (context.modal) {
      context.modal.dataset.workflow = "sectionAssignment";
    }
  },
});

async function editUser(userId) {
  const user = currentUsers.find((u) => u.id === userId);
  if (!user) return;

  // Populate form
  document.getElementById("editUserId").value = user.id;
  document.getElementById("editFirstName").value = user.first_name || "";
  document.getElementById("editLastName").value = user.last_name || "";
  document.getElementById("editEmail").value = user.email || "";
  document.getElementById("editRole").value = user.role || "";
  document.getElementById("editStatus").value = user.account_status || "";

  // Show modal
  const modal = new bootstrap.Modal(document.getElementById("editUserModal"));
  modal.show();
}

async function handleEditUser(event) {
  event.preventDefault();

  const form = event.target;
  const formData = new FormData(form);
  const submitBtn = document.getElementById("saveUserBtn");

  if (!form.checkValidity()) {
    form.classList.add("was-validated");
    return;
  }

  setButtonLoadingState(submitBtn, true);

  try {
    const userId = formData.get("user_id");
    const data = {
      first_name: formData.get("first_name"),
      last_name: formData.get("last_name"),
      role: formData.get("role"),
      status: formData.get("status"),
    };

    // Note: This would need to be implemented in the API
    const response = await fetch(`/api/users/${userId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    const result = await response.json();

    if (response.ok && result.success) {
      showSuccess("User updated successfully!");
      bootstrap.Modal.getInstance(
        document.getElementById("editUserModal"),
      ).hide();
      loadUsers();
    } else {
      throw new Error(result.error || "Failed to update user");
    }
  } catch (error) {
    console.error("Error updating user:", error); // eslint-disable-line no-console
    showError("Failed to update user: " + error.message);
  } finally {
    setButtonLoadingState(submitBtn, false);
  }
}

async function toggleUserStatus(userId) {
  const user = currentUsers.find((u) => u.id === userId);
  if (!user) return;

  const newStatus = user.account_status === "active" ? "inactive" : "active";
  const action = newStatus === "active" ? "activate" : "deactivate";

  const confirmed = await showConfirmation(
    `${action.charAt(0).toUpperCase() + action.slice(1)} User`,
    `Are you sure you want to ${action} ${user.first_name} ${user.last_name}?`,
  );

  if (confirmed) {
    try {
      // Implementation would go here
      showSuccess(`User ${action}d successfully!`);
      loadUsers();
    } catch (error) {
      showError(`Failed to ${action} user: ` + error.message);
    }
  }
}

// Invitation Management
async function resendInvitation(invitationId, showFeedback = true) {
  try {
    const response = await fetch(
      `/api/auth/resend-invitation/${invitationId}`,
      {
        method: "POST",
      },
    );

    const result = await response.json();

    if (response.ok && result.success) {
      if (showFeedback) {
        if (showFeedback) {
          showSuccess("Invitation resent successfully!");
          if (hasInvitationsView()) {
            loadInvitations();
          }
        }
      }
      return true;
    } else {
      throw new Error(result.error || "Failed to resend invitation");
    }
  } catch (error) {
    if (showFeedback) {
      showError("Failed to resend invitation: " + error.message);
    }
    return false;
  }
}

async function cancelInvitation(invitationId, showFeedback = true) {
  try {
    const response = await fetch(
      `/api/auth/cancel-invitation/${invitationId}`,
      {
        method: "DELETE",
      },
    );

    const result = await response.json();

    if (response.ok && result.success) {
      if (showFeedback) {
        if (showFeedback) {
          showSuccess("Invitation cancelled successfully!");
          if (hasInvitationsView()) {
            loadInvitations();
          }
        }
      }
      return true;
    } else {
      throw new Error(result.error || "Failed to cancel invitation");
    }
  } catch (error) {
    if (showFeedback) {
      showError("Failed to cancel invitation: " + error.message);
    }
    return false;
  }
}

// Pagination
function updatePagination() {
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  const pagination = document.getElementById("pagination");

  if (totalPages <= 1) {
    pagination.innerHTML = ""; // nosemgrep
    return;
  }

  let paginationHTML = "";

  // Previous button
  paginationHTML += `
        <li class="page-item ${currentPage === 1 ? "disabled" : ""}">
            <a class="page-link" href="#" onclick="changePage(${currentPage - 1})" aria-label="Previous">
                <span aria-hidden="true">&laquo;</span>
            </a>
        </li>
    `;

  // Page numbers
  const startPage = Math.max(1, currentPage - 2);
  const endPage = Math.min(totalPages, currentPage + 2);

  if (startPage > 1) {
    paginationHTML +=
      '<li class="page-item"><a class="page-link" href="#" onclick="changePage(1)">1</a></li>';
    if (startPage > 2) {
      paginationHTML +=
        '<li class="page-item disabled"><span class="page-link">...</span></li>';
    }
  }

  for (let i = startPage; i <= endPage; i++) {
    paginationHTML += `
            <li class="page-item ${i === currentPage ? "active" : ""}">
                <a class="page-link" href="#" onclick="changePage(${i})">${i}</a>
            </li>
        `;
  }

  if (endPage < totalPages) {
    if (endPage < totalPages - 1) {
      paginationHTML +=
        '<li class="page-item disabled"><span class="page-link">...</span></li>';
    }
    paginationHTML += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(${totalPages})">${totalPages}</a></li>`;
  }

  // Next button
  paginationHTML += `
        <li class="page-item ${currentPage === totalPages ? "disabled" : ""}">
            <a class="page-link" href="#" onclick="changePage(${currentPage + 1})" aria-label="Next">
                <span aria-hidden="true">&raquo;</span>
            </a>
        </li>
    `;

  pagination.innerHTML = paginationHTML; // nosemgrep
}

function changePage(page) {
  if (page < 1 || page > Math.ceil(totalItems / itemsPerPage)) return;
  currentPage = page;
  updateDisplay();
}

// Utility Functions
function updateCounts() {
  const filteredData = getFilteredData();
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = Math.min(startIndex + itemsPerPage, filteredData.length);

  document.getElementById("showingCount").textContent =
    filteredData.length > 0 ? `${startIndex + 1}-${endIndex}` : "0";
  document.getElementById("totalCount").textContent = filteredData.length;
}

function updateURL() {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.role) params.set("role", filters.role);
  if (filters.status) params.set("status", filters.status);

  const newURL =
    globalThis.location.pathname +
    (params.toString() ? "?" + params.toString() : "");
  globalThis.history.replaceState({}, "", newURL);
}

function showLoading(type) {
  const loadingEl = document.getElementById(`${type}Loading`);
  if (loadingEl) {
    loadingEl.style.display = "block";
  }
  const emptyEl = document.getElementById(`${type}Empty`);
  if (emptyEl) {
    emptyEl.classList.add("d-none");
  }
}

function hideLoading(type) {
  const loadingEl = document.getElementById(`${type}Loading`);
  if (loadingEl) {
    loadingEl.style.display = "none";
  }
}

function showEmpty(type) {
  const emptyEl = document.getElementById(`${type}Empty`);
  if (emptyEl) {
    emptyEl.classList.remove("d-none");
  }
}

function hideEmpty(type) {
  const emptyEl = document.getElementById(`${type}Empty`);
  if (emptyEl) {
    emptyEl.classList.add("d-none");
  }
}

function setButtonLoadingState(button, loading) {
  if (!button) {
    return;
  }
  if (loading) {
    button.classList.add("loading");
    button.disabled = true;
  } else {
    button.classList.remove("loading");
    button.disabled = false;
  }
}

// Formatting Functions
function getInitials(firstName, lastName) {
  return (
    (firstName || "").charAt(0) + (lastName || "").charAt(0)
  ).toUpperCase();
}

function formatRole(role) {
  return role.replaceAll("_", " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

function formatStatus(status) {
  return status.replaceAll("_", " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

function getDisplayStatus(user) {
  if (user.account_status === "pending_verification") return "pending";
  return user.account_status;
}

function getActivityStatus(lastLogin) {
  if (!lastLogin) return "inactive";

  const lastLoginDate = new Date(lastLogin);
  const now = new Date();
  const hoursDiff = (now - lastLoginDate) / (1000 * 60 * 60);

  if (hoursDiff < 1) return "online";
  if (hoursDiff < 24) return "recent";
  return "inactive";
}

function formatLastActive(lastLogin) {
  if (!lastLogin) return "Never";

  const date = new Date(lastLogin);
  const now = new Date();
  const diffMs = now - date;
  const diffHours = diffMs / (1000 * 60 * 60);
  const diffDays = diffMs / (1000 * 60 * 60 * 24);

  if (diffHours < 1) return "Just now";
  if (diffHours < 24) return `${Math.floor(diffHours)}h ago`;
  if (diffDays < 7) return `${Math.floor(diffDays)}d ago`;

  return date.toLocaleDateString();
}

function formatDate(dateString) {
  if (!dateString) return "-";
  return new Date(dateString).toLocaleDateString();
}

function formatExpiryDate(dateString) {
  if (!dateString) return "-";

  const expiryDate = new Date(dateString);
  const now = new Date();
  const diffMs = expiryDate - now;
  const diffDays = diffMs / (1000 * 60 * 60 * 24);

  if (diffDays < 0) return "Expired";
  if (diffDays < 1) return "Today";
  if (diffDays < 2) return "Tomorrow";

  return `${Math.ceil(diffDays)} days`;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// UI Helper Functions
function showSuccess(message) {
  showMessage(message, "success");
}

function showWarning(message) {
  showMessage(message, "warning");
}

function showError(message) {
  showMessage(message, "error");
}

function showMessage(message, type) {
  // Remove existing messages
  const existingMessages = document.querySelectorAll(".admin-message-dynamic");
  existingMessages.forEach((msg) => msg.remove());

  // Create new message
  const messageDiv = document.createElement("div");
  const alertType =
    type === "error" ? "danger" : type === "warning" ? "warning" : "success";
  messageDiv.className = `alert alert-${alertType} alert-dismissible fade show admin-message-dynamic`;
  // nosemgrep
  messageDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

  // Insert at top of container
  const container = document.querySelector(".container-fluid");
  const targetContainer = container || document.body;
  const firstChild =
    container && container.children.length > 1
      ? container.children[1]
      : container
        ? container.firstElementChild
        : null;

  if (firstChild) {
    firstChild.before(messageDiv);
  } else {
    targetContainer.prepend(messageDiv);
  }

  messageDiv.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function isInvitationDeliveryFailedMessage(message) {
  return message === INVITATION_EMAIL_FAILED_MESSAGE;
}

function displayInvitationResult(message, detail) {
  if (isInvitationDeliveryFailedMessage(message)) {
    showWarning(message);
  } else {
    showSuccess(message);
  }

  if (detail) {
    const alert = document.querySelector(".admin-message-dynamic");
    if (alert) {
      const detailEl = document.createElement("div");
      detailEl.className = "text-muted small mt-1";
      detailEl.textContent = `Reason: ${detail}`;
      alert.appendChild(detailEl);
    }
  }
}

async function showConfirmation(title, message) {
  return new Promise((resolve) => {
    const modal = document.getElementById("confirmModal");
    const modalTitle = document.getElementById("confirmModalLabel");
    const modalBody = document.getElementById("confirmModalBody");
    const confirmBtn = document.getElementById("confirmActionBtn");

    modalTitle.textContent = title;
    modalBody.textContent = message;

    const handleConfirm = () => {
      modal.removeEventListener("hidden.bs.modal", handleCancel);
      confirmBtn.removeEventListener("click", handleConfirm);
      bootstrap.Modal.getInstance(modal).hide();
      resolve(true);
    };

    const handleCancel = () => {
      modal.removeEventListener("hidden.bs.modal", handleCancel);
      confirmBtn.removeEventListener("click", handleConfirm);
      resolve(false);
    };

    modal.addEventListener("hidden.bs.modal", handleCancel, { once: true });
    confirmBtn.addEventListener("click", handleConfirm, { once: true });

    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
  });
}

// Debounce function
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Export functions for global use
globalThis.changePage = changePage;
globalThis.editUser = editUser;
globalThis.toggleUserStatus = toggleUserStatus;
globalThis.resendInvitation = resendInvitation;
globalThis.cancelInvitation = cancelInvitation;
globalThis.handleUserSelection = handleUserSelection;
globalThis.handleInvitationSelection = handleInvitationSelection;

function __setAdminState(state = {}) {
  if (Object.hasOwn(state, "currentUsers")) {
    currentUsers = state.currentUsers;
  }
  if (Object.hasOwn(state, "currentInvitations")) {
    currentInvitations = state.currentInvitations;
  }
  if (Object.hasOwn(state, "selectedUsers")) {
    selectedUsers.clear();
    state.selectedUsers.forEach((id) => selectedUsers.add(id));
  }
  if (Object.hasOwn(state, "selectedInvitations")) {
    selectedInvitations.clear();
    state.selectedInvitations.forEach((id) => selectedInvitations.add(id));
  }
  if (Object.hasOwn(state, "currentPage")) {
    currentPage = state.currentPage;
  }
  if (Object.hasOwn(state, "totalItems")) {
    totalItems = state.totalItems;
  }
  if (Object.hasOwn(state, "currentTab")) {
    currentTab = state.currentTab;
  }
  if (Object.hasOwn(state, "filters")) {
    filters = {
      search: state.filters.search || "",
      role: state.filters.role || "",
      status: state.filters.status || "",
    };
  }
}

function __resetAdminState() {
  currentUsers = [];
  currentInvitations = [];
  selectedUsers.clear();
  selectedInvitations.clear();
  currentPage = 1;
  totalItems = 0;
  currentTab = "users";
  filters = {
    search: "",
    role: "",
    status: "",
  };
}

function __getAdminState() {
  return {
    currentUsers,
    currentInvitations,
    selectedUsers,
    selectedInvitations,
    currentPage,
    itemsPerPage,
    totalItems,
    currentTab,
    filters,
  };
}

const adminTestExports = {
  __setAdminState,
  __resetAdminState,
  __getAdminState,
  initializeAdminInterface,
  initializeEventListeners,
  initializeFilters,
  initializeTabs,
  initializeModals,
  loadUsers,
  loadInvitations,
  loadPrograms,
  getFilteredData,
  updateDisplay,
  displayUsers,
  displayInvitations,
  changePage,
  updatePagination,
  handleSelectAllUsers,
  handleSelectAllInvitations,
  handleUserSelection,
  handleInvitationSelection,
  updateBulkActions,
  handleBulkResendInvitations,
  toggleUserStatus,
  resendInvitation,
  cancelInvitation,
  handleInviteUser,
  openInviteModal,
  editUser,
  handleEditUser,
  handleRoleSelectionChange,
  setProgramSelectionVisibility,
  showSuccess,
  showError,
  showMessage,
  showConfirmation,
  setButtonLoadingState,
  showLoading,
  hideLoading,
  showEmpty,
  hideEmpty,
  getInitials,
  formatRole,
  formatStatus,
  getDisplayStatus,
  getActivityStatus,
  formatLastActive,
  formatDate,
  formatExpiryDate,
  escapeHtml,
  debounce,
  registerInviteModalWorkflow,
  __resetInviteModalWorkflows,
  __getInviteModalWorkflows,
  _getInviteModalWorkflow,
  DEFAULT_INVITE_WORKFLOW,
  showWarning,
  INVITATION_EMAIL_FAILED_MESSAGE,
  displayInvitationResult,
  isInvitationDeliveryFailedMessage,
  applyUserStatusFilter,
};

if (typeof module !== "undefined" && module.exports) {
  module.exports = adminTestExports;
}
