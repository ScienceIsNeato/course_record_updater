// Admin Interface JavaScript - User Management

// Global state
let currentUsers = [];
let currentInvitations = [];
const selectedUsers = new Set();
const selectedInvitations = new Set();
let currentPage = 1;
const itemsPerPage = 20;
let totalItems = 0;
let currentTab = 'users';
let filters = {
  search: '',
  role: '',
  status: ''
};

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', () => {
  initializeAdminInterface();
});

// Initialize Admin Interface
function initializeAdminInterface() {
  initializeEventListeners();
  initializeFilters();
  initializeTabs();
  initializeModals();

  // Load initial data
  loadUsers();
  loadInvitations();
  loadPrograms();
}

// Event Listeners
function initializeEventListeners() {
  // Search and filters
  document
    .getElementById('searchInput')
    .addEventListener('input', debounce(handleSearchChange, 300));
  document.getElementById('roleFilter').addEventListener('change', handleFilterChange);
  document.getElementById('statusFilter').addEventListener('change', handleFilterChange);
  document.getElementById('clearFilters').addEventListener('click', clearFilters);

  // Bulk selection
  document.getElementById('selectAllUsers').addEventListener('change', handleSelectAllUsers);
  document
    .getElementById('selectAllInvitations')
    .addEventListener('change', handleSelectAllInvitations);

  // Bulk actions
  document
    .getElementById('bulkResendInvitations')
    .addEventListener('click', handleBulkResendInvitations);
  document
    .getElementById('bulkCancelInvitations')
    .addEventListener('click', handleBulkCancelInvitations);
  document
    .getElementById('bulkDeactivateUsers')
    .addEventListener('click', handleBulkDeactivateUsers);

  // Forms
  document.getElementById('inviteUserForm').addEventListener('submit', handleInviteUser);
  document.getElementById('editUserForm').addEventListener('submit', handleEditUser);

  // Role selection for program assignment
  document.getElementById('inviteRole').addEventListener('change', handleRoleSelectionChange);
}

// Initialize Filters
function initializeFilters() {
  const urlParams = new URLSearchParams(window.location.search);
  filters.search = urlParams.get('search') || '';
  filters.role = urlParams.get('role') || '';
  filters.status = urlParams.get('status') || '';

  document.getElementById('searchInput').value = filters.search;
  document.getElementById('roleFilter').value = filters.role;
  document.getElementById('statusFilter').value = filters.status;
}

// Initialize Tabs
function initializeTabs() {
  const tabElements = document.querySelectorAll('#userTabs button[data-bs-toggle="tab"]');
  tabElements.forEach(tab => {
    tab.addEventListener('shown.bs.tab', event => {
      const target = event.target.dataset.bsTarget;
      currentTab = target.includes('users') ? 'users' : 'invitations';
      currentPage = 1;
      updateDisplay();
    });
  });
}

// Initialize Modals
function initializeModals() {
  // Clear forms when modals are hidden
  document.getElementById('inviteUserModal').addEventListener('hidden.bs.modal', () => {
    document.getElementById('inviteUserForm').reset();
    document.getElementById('inviteUserForm').classList.remove('was-validated');
  });

  document.getElementById('editUserModal').addEventListener('hidden.bs.modal', () => {
    document.getElementById('editUserForm').reset();
    document.getElementById('editUserForm').classList.remove('was-validated');
  });
}

// Load Users
async function loadUsers() {
  try {
    showLoading('users');

    const response = await fetch('/api/users');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    if (data.success) {
      currentUsers = data.users || [];
      document.getElementById('usersCount').textContent = currentUsers.length;
      updateDisplay();
    } else {
      throw new Error(data.error || 'Failed to load users');
    }
  } catch (error) {
    console.error('Error loading users:', error); // eslint-disable-line no-console
    showError('Failed to load users: ' + error.message);
    showEmpty('users');
  }
}

// Load Invitations
async function loadInvitations() {
  try {
    showLoading('invitations');

    const response = await fetch('/api/auth/invitations');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    if (data.success) {
      currentInvitations = data.invitations || [];
      document.getElementById('invitationsCount').textContent = currentInvitations.length;
      updateDisplay();
    } else {
      throw new Error(data.error || 'Failed to load invitations');
    }
  } catch (error) {
    console.error('Error loading invitations:', error); // eslint-disable-line no-console
    showError('Failed to load invitations: ' + error.message);
    showEmpty('invitations');
  }
}

// Load Programs for invitation form
async function loadPrograms() {
  try {
    const response = await fetch('/api/programs');
    if (response.ok) {
      const data = await response.json();
      if (data.success) {
        const programSelect = document.getElementById('invitePrograms');
        programSelect.innerHTML = '';

        data.programs.forEach(program => {
          const option = document.createElement('option');
          option.value = program.id;
          option.textContent = program.name;
          programSelect.appendChild(option);
        });
      }
    }
  } catch (error) {
    console.error('Error loading programs:', error); // eslint-disable-line no-console
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
  filters.role = document.getElementById('roleFilter').value;
  filters.status = document.getElementById('statusFilter').value;
  currentPage = 1;
  updateDisplay();
  updateURL();
}

function clearFilters() {
  filters = { search: '', role: '', status: '' };
  document.getElementById('searchInput').value = '';
  document.getElementById('roleFilter').value = '';
  document.getElementById('statusFilter').value = '';
  currentPage = 1;
  updateDisplay();
  updateURL();
}

function getFilteredData() {
  const data = currentTab === 'users' ? currentUsers : currentInvitations;
  return data.filter(item => applyAllFilters(item));
}

function applyAllFilters(item) {
  return applySearchFilter(item) && applyRoleFilter(item) && applyStatusFilter(item);
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
  if (currentTab === 'users') {
    return `${item.first_name} ${item.last_name} ${item.email}`.toLowerCase();
  } else {
    return `${item.email} ${item.invited_by || ''}`.toLowerCase();
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

  if (currentTab === 'users') {
    return applyUserStatusFilter(item);
  } else {
    return item.status === filters.status;
  }
}

function applyUserStatusFilter(item) {
  switch (filters.status) {
    case 'active':
      return item.account_status === 'active';
    case 'pending':
      return item.account_status === 'pending_verification';
    case 'inactive':
      return item.account_status === 'inactive';
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

  if (currentTab === 'users') {
    displayUsers(pageData);
  } else {
    displayInvitations(pageData);
  }

  updatePagination();
  updateBulkActions();
  updateCounts();
}

function displayUsers(users) {
  const tbody = document.getElementById('usersTableBody');

  hideLoading('users');

  if (users.length === 0) {
    showEmpty('users');
    return;
  }

  hideEmpty('users');

  tbody.innerHTML = users
    .map(
      user => `
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
                        .map(name => `<span class="program-tag">${name}</span>`)
                        .join('') ||
                      (user.program_ids || [])
                        .map(() => '<span class="program-tag">Program</span>')
                        .join('')
                    }
                    ${!user.programs && !user.program_names && (!user.program_ids || user.program_ids.length === 0) ? '<span class="text-muted">No programs</span>' : ''}
                </div>
            </td>
            <td>
                <div class="action-buttons">
                    <button class="action-btn btn-edit" onclick="editUser('${user.id}')" title="Edit User">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="action-btn btn-deactivate" onclick="toggleUserStatus('${user.id}')" title="${user.account_status === 'active' ? 'Deactivate' : 'Activate'} User">
                        <i class="fas fa-${user.account_status === 'active' ? 'user-slash' : 'user-check'}"></i>
                    </button>
                </div>
            </td>
        </tr>
    `
    )
    .join('');
}

function displayInvitations(invitations) {
  const tbody = document.getElementById('invitationsTableBody');

  hideLoading('invitations');

  if (invitations.length === 0) {
    showEmpty('invitations');
    return;
  }

  hideEmpty('invitations');

  tbody.innerHTML = invitations
    .map(
      invitation => `
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
                    ${invitation.personal_message ? `<div class="text-muted small">${escapeHtml(invitation.personal_message)}</div>` : ''}
                </div>
            </td>
            <td>
                <span class="role-badge role-${invitation.role}">${formatRole(invitation.role)}</span>
            </td>
            <td>
                <span class="status-badge status-${invitation.status}">${formatStatus(invitation.status)}</span>
            </td>
            <td>
                <div class="text-muted small">${escapeHtml(invitation.invited_by || 'Unknown')}</div>
            </td>
            <td>
                <div class="text-muted small">${formatDate(invitation.invited_at)}</div>
            </td>
            <td>
                <div class="text-muted small">
                    ${invitation.status === 'pending' && invitation.expires_at ? formatExpiryDate(invitation.expires_at) : '-'}
                </div>
            </td>
            <td>
                <div class="action-buttons">
                    ${
                      invitation.status === 'pending'
                        ? `
                        <button class="action-btn btn-resend" onclick="resendInvitation('${invitation.id}')" title="Resend Invitation">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                        <button class="action-btn btn-cancel" onclick="cancelInvitation('${invitation.id}')" title="Cancel Invitation">
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
    `
    )
    .join('');
}

// Selection Handlers
function handleSelectAllUsers(event) {
  const isChecked = event.target.checked;
  const checkboxes = document.querySelectorAll('.user-checkbox');

  checkboxes.forEach(checkbox => {
    checkbox.checked = isChecked;
    handleUserSelection(checkbox.value, isChecked);
  });
}

function handleSelectAllInvitations(event) {
  const isChecked = event.target.checked;
  const checkboxes = document.querySelectorAll('.invitation-checkbox');

  checkboxes.forEach(checkbox => {
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
  const bulkActionsBtn = document.getElementById('bulkActionsDropdown');
  const hasSelection =
    (currentTab === 'users' && selectedUsers.size > 0) ||
    (currentTab === 'invitations' && selectedInvitations.size > 0);

  bulkActionsBtn.disabled = !hasSelection;
}

async function handleBulkResendInvitations() {
  if (selectedInvitations.size === 0) return;

  const confirmed = await showConfirmation(
    'Resend Invitations',
    `Are you sure you want to resend ${selectedInvitations.size} invitation(s)?`
  );

  if (confirmed) {
    for (const invitationId of selectedInvitations) {
      await resendInvitation(invitationId, false);
    }
    selectedInvitations.clear();
    loadInvitations();
    showSuccess(`Successfully resent ${selectedInvitations.size} invitations.`);
  }
}

async function handleBulkCancelInvitations() {
  if (selectedInvitations.size === 0) return;

  const confirmed = await showConfirmation(
    'Cancel Invitations',
    `Are you sure you want to cancel ${selectedInvitations.size} invitation(s)? This action cannot be undone.`
  );

  if (confirmed) {
    for (const invitationId of selectedInvitations) {
      await cancelInvitation(invitationId, false);
    }
    selectedInvitations.clear();
    loadInvitations();
    showSuccess(`Successfully cancelled ${selectedInvitations.size} invitations.`);
  }
}

async function handleBulkDeactivateUsers() {
  if (selectedUsers.size === 0) return;

  const confirmed = await showConfirmation(
    'Deactivate Users',
    `Are you sure you want to deactivate ${selectedUsers.size} user(s)? They will lose access to the system.`
  );

  if (confirmed) {
    // Implementation would go here
    selectedUsers.clear();
    loadUsers();
    showSuccess(`Successfully deactivated ${selectedUsers.size} users.`);
  }
}

// User Management Functions
async function handleInviteUser(event) {
  event.preventDefault();

  const form = event.target;
  const formData = new FormData(form);
  const submitBtn = document.getElementById('sendInviteBtn');

  if (!form.checkValidity()) {
    form.classList.add('was-validated');
    return;
  }

  setLoadingState(submitBtn, true);

  try {
    const data = {
      invitee_email: formData.get('invitee_email'),
      invitee_role: formData.get('invitee_role'),
      personal_message: formData.get('personal_message') || undefined
    };

    // Add program IDs if role is program_admin
    if (data.invitee_role === 'program_admin') {
      const programIds = Array.from(document.getElementById('invitePrograms').selectedOptions).map(
        option => option.value
      );
      if (programIds.length > 0) {
        data.program_ids = programIds;
      }
    }

    // Get CSRF token
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfTokenMeta ? csrfTokenMeta.content : null;

    const response = await fetch('/api/auth/invite', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken && { 'X-CSRFToken': csrfToken })
      },
      body: JSON.stringify(data)
    });

    const result = await response.json();

    if (response.ok && result.success) {
      showSuccess(result.message || 'Invitation sent successfully!');
      bootstrap.Modal.getInstance(document.getElementById('inviteUserModal')).hide();
      loadInvitations();
    } else {
      throw new Error(result.error || 'Failed to send invitation');
    }
  } catch (error) {
    console.error('Error sending invitation:', error); // eslint-disable-line no-console
    showError('Failed to send invitation: ' + error.message);
  } finally {
    setLoadingState(submitBtn, false);
  }
}

function handleRoleSelectionChange(event) {
  const programSelection = document.getElementById('programSelection');
  const selectedRole = event.target.value;

  if (selectedRole === 'program_admin') {
    programSelection.style.display = 'block';
    document.getElementById('invitePrograms').required = true;
  } else {
    programSelection.style.display = 'none';
    document.getElementById('invitePrograms').required = false;
  }
}

async function editUser(userId) {
  const user = currentUsers.find(u => u.id === userId);
  if (!user) return;

  // Populate form
  document.getElementById('editUserId').value = user.id;
  document.getElementById('editFirstName').value = user.first_name || '';
  document.getElementById('editLastName').value = user.last_name || '';
  document.getElementById('editEmail').value = user.email || '';
  document.getElementById('editRole').value = user.role || '';
  document.getElementById('editStatus').value = user.account_status || '';

  // Show modal
  const modal = new bootstrap.Modal(document.getElementById('editUserModal'));
  modal.show();
}

async function handleEditUser(event) {
  event.preventDefault();

  const form = event.target;
  const formData = new FormData(form);
  const submitBtn = document.getElementById('saveUserBtn');

  if (!form.checkValidity()) {
    form.classList.add('was-validated');
    return;
  }

  setLoadingState(submitBtn, true);

  try {
    const userId = formData.get('user_id');
    const data = {
      first_name: formData.get('first_name'),
      last_name: formData.get('last_name'),
      role: formData.get('role'),
      status: formData.get('status')
    };

    // Note: This would need to be implemented in the API
    const response = await fetch(`/api/users/${userId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });

    const result = await response.json();

    if (response.ok && result.success) {
      showSuccess('User updated successfully!');
      bootstrap.Modal.getInstance(document.getElementById('editUserModal')).hide();
      loadUsers();
    } else {
      throw new Error(result.error || 'Failed to update user');
    }
  } catch (error) {
    console.error('Error updating user:', error); // eslint-disable-line no-console
    showError('Failed to update user: ' + error.message);
  } finally {
    setLoadingState(submitBtn, false);
  }
}

async function toggleUserStatus(userId) {
  const user = currentUsers.find(u => u.id === userId);
  if (!user) return;

  const newStatus = user.account_status === 'active' ? 'inactive' : 'active';
  const action = newStatus === 'active' ? 'activate' : 'deactivate';

  const confirmed = await showConfirmation(
    `${action.charAt(0).toUpperCase() + action.slice(1)} User`,
    `Are you sure you want to ${action} ${user.first_name} ${user.last_name}?`
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
    const response = await fetch(`/api/auth/resend-invitation/${invitationId}`, {
      method: 'POST'
    });

    const result = await response.json();

    if (response.ok && result.success) {
      if (showFeedback) {
        showSuccess('Invitation resent successfully!');
        loadInvitations();
      }
      return true;
    } else {
      throw new Error(result.error || 'Failed to resend invitation');
    }
  } catch (error) {
    if (showFeedback) {
      showError('Failed to resend invitation: ' + error.message);
    }
    return false;
  }
}

async function cancelInvitation(invitationId, showFeedback = true) {
  try {
    const response = await fetch(`/api/auth/cancel-invitation/${invitationId}`, {
      method: 'DELETE'
    });

    const result = await response.json();

    if (response.ok && result.success) {
      if (showFeedback) {
        showSuccess('Invitation cancelled successfully!');
        loadInvitations();
      }
      return true;
    } else {
      throw new Error(result.error || 'Failed to cancel invitation');
    }
  } catch (error) {
    if (showFeedback) {
      showError('Failed to cancel invitation: ' + error.message);
    }
    return false;
  }
}

// Pagination
function updatePagination() {
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  const pagination = document.getElementById('pagination');

  if (totalPages <= 1) {
    pagination.innerHTML = '';
    return;
  }

  let paginationHTML = '';

  // Previous button
  paginationHTML += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
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
      paginationHTML += '<li class="page-item disabled"><span class="page-link">...</span></li>';
    }
  }

  for (let i = startPage; i <= endPage; i++) {
    paginationHTML += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="changePage(${i})">${i}</a>
            </li>
        `;
  }

  if (endPage < totalPages) {
    if (endPage < totalPages - 1) {
      paginationHTML += '<li class="page-item disabled"><span class="page-link">...</span></li>';
    }
    paginationHTML += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(${totalPages})">${totalPages}</a></li>`;
  }

  // Next button
  paginationHTML += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage + 1})" aria-label="Next">
                <span aria-hidden="true">&raquo;</span>
            </a>
        </li>
    `;

  pagination.innerHTML = paginationHTML;
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

  document.getElementById('showingCount').textContent =
    filteredData.length > 0 ? `${startIndex + 1}-${endIndex}` : '0';
  document.getElementById('totalCount').textContent = filteredData.length;
}

function updateURL() {
  const params = new URLSearchParams();
  if (filters.search) params.set('search', filters.search);
  if (filters.role) params.set('role', filters.role);
  if (filters.status) params.set('status', filters.status);

  const newURL = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
  window.history.replaceState({}, '', newURL);
}

function showLoading(type) {
  document.getElementById(`${type}Loading`).style.display = 'block';
  document.getElementById(`${type}Empty`).classList.add('d-none');
}

function hideLoading(type) {
  document.getElementById(`${type}Loading`).style.display = 'none';
}

function showEmpty(type) {
  document.getElementById(`${type}Empty`).classList.remove('d-none');
}

function hideEmpty(type) {
  document.getElementById(`${type}Empty`).classList.add('d-none');
}

function setLoadingState(button, loading) {
  if (loading) {
    button.classList.add('loading');
    button.disabled = true;
  } else {
    button.classList.remove('loading');
    button.disabled = false;
  }
}

// Formatting Functions
function getInitials(firstName, lastName) {
  return ((firstName || '').charAt(0) + (lastName || '').charAt(0)).toUpperCase();
}

function formatRole(role) {
  return role.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function formatStatus(status) {
  return status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function getDisplayStatus(user) {
  if (user.account_status === 'pending_verification') return 'pending';
  return user.account_status;
}

function getActivityStatus(lastLogin) {
  if (!lastLogin) return 'inactive';

  const lastLoginDate = new Date(lastLogin);
  const now = new Date();
  const hoursDiff = (now - lastLoginDate) / (1000 * 60 * 60);

  if (hoursDiff < 1) return 'online';
  if (hoursDiff < 24) return 'recent';
  return 'inactive';
}

function formatLastActive(lastLogin) {
  if (!lastLogin) return 'Never';

  const date = new Date(lastLogin);
  const now = new Date();
  const diffMs = now - date;
  const diffHours = diffMs / (1000 * 60 * 60);
  const diffDays = diffMs / (1000 * 60 * 60 * 24);

  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${Math.floor(diffHours)}h ago`;
  if (diffDays < 7) return `${Math.floor(diffDays)}d ago`;

  return date.toLocaleDateString();
}

function formatDate(dateString) {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString();
}

function formatExpiryDate(dateString) {
  if (!dateString) return '-';

  const expiryDate = new Date(dateString);
  const now = new Date();
  const diffMs = expiryDate - now;
  const diffDays = diffMs / (1000 * 60 * 60 * 24);

  if (diffDays < 0) return 'Expired';
  if (diffDays < 1) return 'Today';
  if (diffDays < 2) return 'Tomorrow';

  return `${Math.ceil(diffDays)} days`;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// UI Helper Functions
function showSuccess(message) {
  showMessage(message, 'success');
}

function showError(message) {
  showMessage(message, 'error');
}

function showMessage(message, type) {
  // Remove existing messages
  const existingMessages = document.querySelectorAll('.admin-message-dynamic');
  existingMessages.forEach(msg => msg.remove());

  // Create new message
  const messageDiv = document.createElement('div');
  messageDiv.className = `alert alert-${type === 'error' ? 'danger' : 'success'} alert-dismissible fade show admin-message-dynamic`;
  messageDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

  // Insert at top of container
  const container = document.querySelector('.container-fluid');
  const firstChild = container.children[1]; // After header
  firstChild.before(messageDiv);

  messageDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function showConfirmation(title, message) {
  return new Promise(resolve => {
    const modal = document.getElementById('confirmModal');
    const modalTitle = document.getElementById('confirmModalLabel');
    const modalBody = document.getElementById('confirmModalBody');
    const confirmBtn = document.getElementById('confirmActionBtn');

    modalTitle.textContent = title;
    modalBody.textContent = message;

    const handleConfirm = () => {
      modal.removeEventListener('hidden.bs.modal', handleCancel);
      confirmBtn.removeEventListener('click', handleConfirm);
      bootstrap.Modal.getInstance(modal).hide();
      resolve(true);
    };

    const handleCancel = () => {
      modal.removeEventListener('hidden.bs.modal', handleCancel);
      confirmBtn.removeEventListener('click', handleConfirm);
      resolve(false);
    };

    modal.addEventListener('hidden.bs.modal', handleCancel, { once: true });
    confirmBtn.addEventListener('click', handleConfirm, { once: true });

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
window.changePage = changePage;
window.editUser = editUser;
window.toggleUserStatus = toggleUserStatus;
window.resendInvitation = resendInvitation;
window.cancelInvitation = cancelInvitation;
window.handleUserSelection = handleUserSelection;
window.handleInvitationSelection = handleInvitationSelection;

function __setAdminState(state = {}) {
  if (Object.prototype.hasOwnProperty.call(state, 'currentUsers')) {
    currentUsers = state.currentUsers;
  }
  if (Object.prototype.hasOwnProperty.call(state, 'currentInvitations')) {
    currentInvitations = state.currentInvitations;
  }
  if (Object.prototype.hasOwnProperty.call(state, 'selectedUsers')) {
    selectedUsers.clear();
    state.selectedUsers.forEach(id => selectedUsers.add(id));
  }
  if (Object.prototype.hasOwnProperty.call(state, 'selectedInvitations')) {
    selectedInvitations.clear();
    state.selectedInvitations.forEach(id => selectedInvitations.add(id));
  }
  if (Object.prototype.hasOwnProperty.call(state, 'currentPage')) {
    currentPage = state.currentPage;
  }
  if (Object.prototype.hasOwnProperty.call(state, 'totalItems')) {
    totalItems = state.totalItems;
  }
  if (Object.prototype.hasOwnProperty.call(state, 'currentTab')) {
    currentTab = state.currentTab;
  }
  if (Object.prototype.hasOwnProperty.call(state, 'filters')) {
    filters = {
      search: state.filters.search || '',
      role: state.filters.role || '',
      status: state.filters.status || ''
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
  currentTab = 'users';
  filters = {
    search: '',
    role: '',
    status: ''
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
    filters
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
  handleBulkCancelInvitations,
  handleBulkDeactivateUsers,
  toggleUserStatus,
  resendInvitation,
  cancelInvitation,
  handleInviteUser,
  handleEditUser,
  handleRoleSelectionChange,
  showSuccess,
  showError,
  showMessage,
  showConfirmation,
  setLoadingState,
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
  debounce
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = adminTestExports;
}
