const admin = require('../../../static/admin');
const { setBody } = require('../helpers/dom');

describe('admin module', () => {
  beforeEach(() => {
    admin.__resetAdminState();
    setBody(`
      <div class="container-fluid"><div></div><div></div></div>
      <div id="usersLoading"></div>
      <div id="usersEmpty" class="d-none"></div>
      <table><tbody id="usersTableBody"></tbody></table>
      <div id="invitationsLoading"></div>
      <div id="invitationsEmpty" class="d-none"></div>
      <table><tbody id="invitationsTableBody"></tbody></table>
      <ul id="pagination"></ul>
      <span id="showingCount"></span>
      <span id="totalCount"></span>
      <button id="bulkActionsDropdown" class="d-none"></button>
      <span id="usersCount"></span>
      <span id="invitationsCount"></span>
      <select id="invitePrograms" multiple></select>
    `);
  });

  it('filters users according to search, role, and status', () => {
    admin.__setAdminState({
      currentTab: 'users',
      currentUsers: [
        { id: '1', first_name: 'Alice', last_name: 'Smith', email: 'alice@example.com', role: 'admin', account_status: 'active' },
        { id: '2', first_name: 'Bob', last_name: 'Faculty', email: 'bob@example.com', role: 'faculty', account_status: 'inactive' }
      ],
      filters: { search: 'alice', role: 'admin', status: 'active' }
    });

    const filtered = admin.getFilteredData();
    expect(filtered).toHaveLength(1);
    expect(filtered[0].email).toBe('alice@example.com');
  });

  it('renders users table and pagination details', () => {
    const users = [
      {
        id: '1',
        first_name: 'Test',
        last_name: 'User',
        email: 'test@example.com',
        role: 'institution_admin',
        account_status: 'active',
        last_login: new Date().toISOString(),
        program_ids: []
      }
    ];

    admin.__setAdminState({ currentTab: 'users', currentUsers: users, filters: { search: '', role: '', status: '' } });
    admin.updateDisplay();

    const rows = document.querySelectorAll('#usersTableBody tr');
    expect(rows).toHaveLength(1);
    expect(document.getElementById('showingCount').textContent).toBe('1-1');
    expect(document.getElementById('totalCount').textContent).toBe('1');
  });

  it('renders invitations table when tab switched', () => {
    admin.__setAdminState({
      currentTab: 'invitations',
      currentInvitations: [
        {
          id: 'inv1',
          email: 'pending@example.com',
          status: 'pending',
          role: 'faculty',
          invited_by: 'Admin',
          sent_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 86400000).toISOString()
        }
      ],
      filters: { search: '', role: '', status: '' }
    });

    admin.updateDisplay();

    const rows = document.querySelectorAll('#invitationsTableBody tr');
    expect(rows).toHaveLength(1);
    expect(rows[0].textContent).toContain('pending@example.com');
  });

  it('updates pagination when changing pages', () => {
    const users = Array.from({ length: 45 }).map((_, idx) => ({
      id: String(idx),
      first_name: 'User',
      last_name: `Number${idx}`,
      email: `user${idx}@example.com`,
      role: 'faculty',
      account_status: 'active',
      last_login: new Date().toISOString(),
      program_ids: []
    }));

    admin.__setAdminState({
      currentTab: 'users',
      currentUsers: users,
      filters: { search: '', role: '', status: '' }
    });

    admin.updateDisplay();

    admin.changePage(2);
    expect(admin.__getAdminState().currentPage).toBe(2);

    admin.changePage(10);
    expect(admin.__getAdminState().currentPage).toBe(2);
  });

  it('shows and hides loading state with messages', () => {
    admin.showLoading('users');
    expect(document.getElementById('usersLoading').style.display).toBe('block');

    admin.hideLoading('users');
    expect(document.getElementById('usersLoading').style.display).toBe('none');

    admin.showError('Problem');
    expect(document.querySelector('.admin-message-dynamic')).not.toBeNull();
  });

  it('escapes HTML safely', () => {
    const escaped = admin.escapeHtml('<script>alert(1)</script>');
    expect(escaped).toBe('&lt;script&gt;alert(1)&lt;/script&gt;');
  });

  it('computes initials and formatted dates', () => {
    expect(admin.getInitials('Great', 'Teacher')).toBe('GT');
    expect(admin.formatDate(null)).toBe('-');
    expect(admin.formatExpiryDate(new Date(Date.now() - 86400000).toISOString())).toBe('Expired');
  });

  it('handles invitation bulk selection via select all', () => {
    setBody(`
      <button id="bulkActionsDropdown"></button>
      <input type="checkbox" class="invitation-checkbox" value="inv1" />
      <input type="checkbox" class="invitation-checkbox" value="inv2" />
    `);

    admin.__setAdminState({ currentTab: 'invitations' });
    admin.handleSelectAllInvitations({ target: { checked: true } });
    const state = admin.__getAdminState();
    expect(state.selectedInvitations.size).toBe(2);
  });

  it('debounces rapid calls', () => {
    jest.useFakeTimers();
    const spy = jest.fn();
    const debounced = admin.debounce(spy, 200);
    debounced();
    debounced();
    jest.advanceTimersByTime(199);
    expect(spy).not.toHaveBeenCalled();
    jest.advanceTimersByTime(1);
    expect(spy).toHaveBeenCalledTimes(1);
    jest.useRealTimers();
  });

  it('loads users data and handles errors', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, users: [{ id: '1', first_name: 'A', last_name: 'B', email: 'a@b.com', role: 'faculty', account_status: 'active' }] })
    });

    await admin.loadUsers();
    expect(admin.__getAdminState().currentUsers).toHaveLength(1);
    expect(document.getElementById('usersCount').textContent).toBe('1');

    global.fetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Oops',
      json: async () => ({})
    });

    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    await admin.loadUsers();
    expect(document.querySelector('.admin-message-dynamic')).not.toBeNull();
    consoleErrorSpy.mockRestore();
  });

  it('resends and cancels invitations with feedback', async () => {
    const successResponse = {
      ok: true,
      json: async () => ({ success: true })
    };

    global.fetch.mockResolvedValue(successResponse);
    expect(await admin.resendInvitation('inv1')).toBe(true);
    const firstCall = global.fetch.mock.calls[0];
    expect(firstCall[0]).toBe('/api/auth/resend-invitation/inv1');

    global.fetch.mockResolvedValue(successResponse);
    expect(await admin.cancelInvitation('inv1')).toBe(true);
    expect(global.fetch.mock.calls.some(call => call[0] === '/api/auth/cancel-invitation/inv1')).toBe(true);

    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    global.fetch.mockRejectedValue(new Error('boom'));
    expect(await admin.resendInvitation('inv1')).toBe(false);
    consoleErrorSpy.mockRestore();
  });

  it('toggles user status after confirmation', async () => {
    admin.__setAdminState({
      currentUsers: [
        {
          id: 'user-1',
          first_name: 'Toggle',
          last_name: 'User',
          email: 'toggle@example.com',
          role: 'faculty',
          account_status: 'active'
        }
      ]
    });

    document.body.insertAdjacentHTML(
      'beforeend',
      `
      <div id="confirmModal"></div>
      <div id="confirmModalLabel"></div>
      <div id="confirmModalBody"></div>
      <button id="confirmActionBtn"></button>
    `
    );

    global.fetch.mockResolvedValue({ ok: true, json: async () => ({ success: true, users: [] }) });

    const promise = admin.toggleUserStatus('user-1');
    document.getElementById('confirmActionBtn').dispatchEvent(new Event('click'));
    await promise;

    expect(document.querySelector('.admin-message-dynamic')).not.toBeNull();
  });

  it('handles bulk user selection via select all', () => {
    setBody(`
      <button id="bulkActionsDropdown" class="d-none"></button>
      <input type="checkbox" class="user-checkbox" value="1" />
      <input type="checkbox" class="user-checkbox" value="2" />
    `);

    admin.__setAdminState({ currentTab: 'users' });

    admin.handleSelectAllUsers({ target: { checked: true } });

    const state = admin.__getAdminState();
    expect(state.selectedUsers.size).toBe(2);
    expect(document.querySelectorAll('.user-checkbox')[0].checked).toBe(true);
    expect(document.getElementById('bulkActionsDropdown').disabled).toBe(false);
  });

  it('formats activity timestamps and statuses', () => {
    const recent = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    const upcoming = new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString();
    expect(admin.formatLastActive(null)).toBe('Never');
    expect(admin.formatLastActive(recent)).toContain('h ago');
    expect(admin.getActivityStatus(recent)).toBe('recent');
    expect(admin.formatExpiryDate(upcoming)).toContain('days');
    expect(admin.formatRole('program_admin')).toBe('Program Admin');
  });

});
