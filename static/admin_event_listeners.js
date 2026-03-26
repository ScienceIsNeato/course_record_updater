(function () {
  "use strict";

  function registerFilterListeners(elements, deps) {
    const { searchInput, roleFilter, statusFilter, clearFiltersBtn } = elements;
    const { debounce, handleSearchChange, handleFilterChange, clearFilters } =
      deps;

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
  }

  function initializeAdminEventListeners(deps) {
    const {
      debounce,
      handleBulkResendInvitations,
      handleEditUser,
      handleFilterChange,
      handleInviteUserSubmit,
      handleRoleSelectionChange,
      handleSearchChange,
      handleSelectAllInvitations,
      handleSelectAllUsers,
      hasInvitationsView,
      clearFilters,
      editUser,
      resendInvitation,
      cancelInvitation,
      toggleUserStatus,
    } = deps;

    const searchInput = document.getElementById("searchInput");
    const roleFilter = document.getElementById("roleFilter");
    const statusFilter = document.getElementById("statusFilter");
    const clearFiltersBtn = document.getElementById("clearFilters");
    const selectAllUsers = document.getElementById("selectAllUsers");
    const selectAllInvitations = document.getElementById(
      "selectAllInvitations",
    );
    const bulkResendInvitations = document.getElementById(
      "bulkResendInvitations",
    );
    const editUserForm = document.getElementById("editUserForm");
    const usersTableBody = document.getElementById("usersTableBody");
    const inviteUserForm = document.getElementById("inviteUserForm");
    const inviteRole = document.getElementById("inviteRole");

    registerFilterListeners(
      { searchInput, roleFilter, statusFilter, clearFiltersBtn },
      { debounce, handleSearchChange, handleFilterChange, clearFilters },
    );
    if (selectAllUsers) {
      selectAllUsers.addEventListener("change", handleSelectAllUsers);
    }
    if (selectAllInvitations) {
      selectAllInvitations.addEventListener(
        "change",
        handleSelectAllInvitations,
      );
    }
    if (bulkResendInvitations) {
      bulkResendInvitations.addEventListener(
        "click",
        handleBulkResendInvitations,
      );
    }
    if (inviteUserForm) {
      inviteUserForm.addEventListener("submit", handleInviteUserSubmit);
    }
    if (editUserForm) {
      editUserForm.addEventListener("submit", handleEditUser);
    }
    if (inviteRole) {
      inviteRole.addEventListener("change", handleRoleSelectionChange);
    }
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

    const invitationsTableBody = document.getElementById(
      "invitationsTableBody",
    );
    if (!hasInvitationsView() || !invitationsTableBody) {
      return;
    }
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

  const exportsObj = { initializeAdminEventListeners };
  if (typeof globalThis !== "undefined") {
    globalThis.AdminEventListeners = exportsObj;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = exportsObj;
  }
})();
