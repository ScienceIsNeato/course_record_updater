/**
 * Unit Tests for User Management UI
 *
 * Tests modal behavior, form validation, and API interactions for:
 * - Invite User modal
 * - Edit User modal
 * - Deactivate User confirmation
 *
 * TDD Approach: Tests written before implementation
 */

// Load the implementation
require('../../../static/userManagement.js');

describe('User Management - Invite User Modal', () => {
    let mockFetch;
    let consoleErrorSpy;

    beforeEach(() => {
        // Set up DOM
        document.body.innerHTML = `
            <form id="inviteUserForm">
                <input type="email" id="inviteEmail" name="invitee_email" required />
                <select id="inviteRole" name="invitee_role" required>
                    <option value="">Select Role</option>
                    <option value="instructor">Instructor</option>
                    <option value="program_admin">Program Admin</option>
                    <option value="institution_admin">Institution Admin</option>
                </select>
                <div id="programSelection" style="display: none;">
                    <select id="invitePrograms" name="program_ids" multiple></select>
                </div>
                <textarea id="inviteMessage" name="personal_message"></textarea>
                <button type="submit" id="sendInviteBtn">
                    <span class="btn-text">Send Invitation</span>
                    <span class="btn-spinner d-none">Sending...</span>
                </button>
            </form>
            <div class="modal" id="inviteUserModal"></div>
            <meta name="csrf-token" content="test-csrf-token">
        `;

        // Mock fetch
        mockFetch = jest.fn();
        global.fetch = mockFetch;

        // Mock console.error
        consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

        // Mock Bootstrap Modal
        global.bootstrap = {
            Modal: {
                getInstance: jest.fn(() => ({
                    hide: jest.fn()
                }))
            }
        };

        global.loadUsers = jest.fn();

        // Trigger DOMContentLoaded to initialize event listeners
        document.dispatchEvent(new Event('DOMContentLoaded'));
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    describe('Role Selection - Show/Hide Program Selection', () => {
        test('should show program selection when program_admin role is selected', () => {
            const roleSelect = document.getElementById('inviteRole');
            const programSelection = document.getElementById('programSelection');

            // Simulate role change event
            roleSelect.value = 'program_admin';
            const event = new Event('change', { bubbles: true });
            roleSelect.dispatchEvent(event);

            // Program selection should be visible
            expect(programSelection.style.display).not.toBe('none');
        });

        test('should hide program selection when instructor role is selected', () => {
            const roleSelect = document.getElementById('inviteRole');
            const programSelection = document.getElementById('programSelection');

            // First show it
            programSelection.style.display = 'block';

            // Then select instructor
            roleSelect.value = 'instructor';
            const event = new Event('change', { bubbles: true });
            roleSelect.dispatchEvent(event);

            // Program selection should be hidden
            expect(programSelection.style.display).toBe('none');
        });

        test('should hide program selection when institution_admin role is selected', () => {
            const roleSelect = document.getElementById('inviteRole');
            const programSelection = document.getElementById('programSelection');

            // First show it
            programSelection.style.display = 'block';

            // Then select institution admin
            roleSelect.value = 'institution_admin';
            const event = new Event('change', { bubbles: true });
            roleSelect.dispatchEvent(event);

            // Program selection should be hidden
            expect(programSelection.style.display).toBe('none');
        });
    });

    describe('Form Validation', () => {
        test('should validate email format', () => {
            const emailInput = document.getElementById('inviteEmail');

            // Invalid email
            emailInput.value = 'not-an-email';
            expect(emailInput.validity.typeMismatch).toBe(true);

            // Valid email
            emailInput.value = 'test@example.com';
            expect(emailInput.validity.valid).toBe(true);
        });

        test('should require role selection', () => {
            const roleSelect = document.getElementById('inviteRole');

            // Empty role
            roleSelect.value = '';
            expect(roleSelect.validity.valid).toBe(false);

            // Selected role
            roleSelect.value = 'instructor';
            expect(roleSelect.validity.valid).toBe(true);
        });

        test('should require program selection when program_admin role is selected', () => {
            const roleSelect = document.getElementById('inviteRole');
            const programsSelect = document.getElementById('invitePrograms');

            roleSelect.value = 'program_admin';
            
            // No programs selected (should be invalid when role is program_admin)
            expect(programsSelect.selectedOptions.length).toBe(0);
        });
    });

    describe('Form Submission - API Call', () => {
        test('should POST invitation data to /api/auth/invite on successful form submit', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true, message: 'Invitation sent' })
            });

            const form = document.getElementById('inviteUserForm');
            const emailInput = document.getElementById('inviteEmail');
            const roleSelect = document.getElementById('inviteRole');
            const messageInput = document.getElementById('inviteMessage');

            // Fill form
            emailInput.value = 'newuser@example.com';
            roleSelect.value = 'instructor';
            messageInput.value = 'Welcome aboard!';

            // Submit form
            const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
            form.dispatchEvent(submitEvent);

            // Wait for async operations
            await new Promise(resolve => setTimeout(resolve, 100));

            // Verify fetch was called
            expect(mockFetch).toHaveBeenCalledWith(
                '/api/auth/invite',
                expect.objectContaining({
                    method: 'POST',
                    headers: expect.objectContaining({
                        'Content-Type': 'application/json',
                        'X-CSRFToken': 'test-csrf-token'
                    }),
                    body: expect.stringContaining('newuser@example.com')
                })
            );
        });

        test('should include program_ids when program_admin role is selected', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true })
            });

            const form = document.getElementById('inviteUserForm');
            const emailInput = document.getElementById('inviteEmail');
            const roleSelect = document.getElementById('inviteRole');
            const programsSelect = document.getElementById('invitePrograms');

            // Add program options
            programsSelect.innerHTML = `
                <option value="program-1" selected>Program 1</option>
                <option value="program-2" selected>Program 2</option>
            `;

            // Fill form
            emailInput.value = 'admin@example.com';
            roleSelect.value = 'program_admin';

            // Submit form
            const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
            form.dispatchEvent(submitEvent);

            await new Promise(resolve => setTimeout(resolve, 100));

            // Verify fetch was called with program_ids
            const callArgs = mockFetch.mock.calls[0];
            const body = JSON.parse(callArgs[1].body);
            expect(body.program_ids).toEqual(['program-1', 'program-2']);
        });

        test('should show loading state during API call', async () => {
            mockFetch.mockImplementationOnce(() => new Promise(resolve => setTimeout(() => resolve({
                ok: true,
                json: async () => ({ success: true })
            }), 100)));

            const form = document.getElementById('inviteUserForm');
            const emailInput = document.getElementById('inviteEmail');
            const roleSelect = document.getElementById('inviteRole');
            const btnText = document.querySelector('.btn-text');
            const btnSpinner = document.querySelector('.btn-spinner');

            emailInput.value = 'test@example.com';
            roleSelect.value = 'instructor';

            // Submit form
            const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
            form.dispatchEvent(submitEvent);

            // Immediately after submit, loading state should be active
            await new Promise(resolve => setTimeout(resolve, 10));
            
            // Button text should be hidden, spinner should be visible
            expect(btnText.classList.contains('d-none')).toBe(true);
            expect(btnSpinner.classList.contains('d-none')).toBe(false);

            // Wait for completion
            await new Promise(resolve => setTimeout(resolve, 150));

            // After completion, should return to normal state
            expect(btnText.classList.contains('d-none')).toBe(false);
            expect(btnSpinner.classList.contains('d-none')).toBe(true);
        });

        test('should close modal and reset form on successful invitation', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true, message: 'Invitation sent' })
            });

            const form = document.getElementById('inviteUserForm');
            const emailInput = document.getElementById('inviteEmail');
            const roleSelect = document.getElementById('inviteRole');

            emailInput.value = 'test@example.com';
            roleSelect.value = 'instructor';

            const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
            form.dispatchEvent(submitEvent);

            await new Promise(resolve => setTimeout(resolve, 100));

            // Modal should be closed
            expect(bootstrap.Modal.getInstance).toHaveBeenCalled();

            // Form should be reset
            expect(emailInput.value).toBe('');
            expect(roleSelect.value).toBe('');
            expect(global.loadUsers).toHaveBeenCalled();
        });

        test('should display error message on API failure', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: false,
                status: 400,
                json: async () => ({ error: 'Email already exists' })
            });

            // Mock showAlert
            global.showAlert = jest.fn();

            const form = document.getElementById('inviteUserForm');
            const emailInput = document.getElementById('inviteEmail');
            const roleSelect = document.getElementById('inviteRole');

            emailInput.value = 'existing@example.com';
            roleSelect.value = 'instructor';

            const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
            form.dispatchEvent(submitEvent);

            await new Promise(resolve => setTimeout(resolve, 100));

            // Should show error
            expect(global.showAlert).toHaveBeenCalledWith(
                'danger',
                expect.stringContaining('Email already exists')
            );

            // Form should NOT be reset
            expect(emailInput.value).toBe('existing@example.com');
        });

        test('should handle network errors gracefully', async () => {
            mockFetch.mockRejectedValueOnce(new Error('Network error'));

            global.showAlert = jest.fn();

            const form = document.getElementById('inviteUserForm');
            const emailInput = document.getElementById('inviteEmail');
            const roleSelect = document.getElementById('inviteRole');

            emailInput.value = 'test@example.com';
            roleSelect.value = 'instructor';

            const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
            form.dispatchEvent(submitEvent);

            await new Promise(resolve => setTimeout(resolve, 100));

            // Should show generic error
            expect(global.showAlert).toHaveBeenCalledWith(
                'danger',
                expect.stringContaining('Failed to send invitation')
            );

            // Should log error
            expect(consoleErrorSpy).toHaveBeenCalled();
        });
    });

    describe('CSRF Token Handling', () => {
        test('should include CSRF token in API request headers', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true })
            });

            const form = document.getElementById('inviteUserForm');
            const emailInput = document.getElementById('inviteEmail');
            const roleSelect = document.getElementById('inviteRole');

            emailInput.value = 'test@example.com';
            roleSelect.value = 'instructor';

            const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
            form.dispatchEvent(submitEvent);

            await new Promise(resolve => setTimeout(resolve, 100));

            // Verify CSRF token in headers
            const callArgs = mockFetch.mock.calls[0];
            expect(callArgs[1].headers['X-CSRFToken']).toBe('test-csrf-token');
        });

        test('should handle missing CSRF token gracefully', async () => {
            // Remove CSRF token
            document.querySelector('meta[name="csrf-token"]').remove();

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true })
            });

            const form = document.getElementById('inviteUserForm');
            const emailInput = document.getElementById('inviteEmail');
            const roleSelect = document.getElementById('inviteRole');

            emailInput.value = 'test@example.com';
            roleSelect.value = 'instructor';

            const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
            form.dispatchEvent(submitEvent);

            await new Promise(resolve => setTimeout(resolve, 100));

            // Should still make request (server will handle CSRF validation)
            expect(mockFetch).toHaveBeenCalled();
        });
    });
});

describe('User Management - Edit User Modal', () => {
    let mockFetch;

    beforeEach(() => {
        document.body.innerHTML = `
            <form id="editUserForm">
                <input type="hidden" id="editUserId" />
                <input type="email" id="editUserEmail" />
                <input type="text" id="editFirstName" required />
                <input type="text" id="editLastName" required />
                <input type="text" id="editDisplayName" />
                <select id="editUserRole">
                    <option value="instructor">Instructor</option>
                    <option value="program_admin">Program Admin</option>
                </select>
                <button type="submit">
                    <span class="btn-text">Save</span>
                    <span class="btn-spinner d-none">Saving...</span>
                </button>
            </form>
            <div class="modal" id="editUserModal"></div>
            <meta name="csrf-token" content="test-csrf-token">
        `;

        mockFetch = jest.fn();
        global.fetch = mockFetch;

        global.bootstrap = {
            Modal: {
                getInstance: jest.fn(() => ({
                    hide: jest.fn()
                })),
                prototype: {
                    show: jest.fn()
                }
            }
        };

        global.loadUsers = jest.fn();

        document.dispatchEvent(new Event('DOMContentLoaded'));
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    test('openEditUserModal should populate form and show modal', () => {
        const mockModal = { show: jest.fn() };
        global.bootstrap.Modal = jest.fn(() => mockModal);

        window.openEditUserModal('user-123', 'John', 'Doe', 'Johnny');

        expect(document.getElementById('editUserId').value).toBe('user-123');
        expect(document.getElementById('editFirstName').value).toBe('John');
        expect(document.getElementById('editLastName').value).toBe('Doe');
        expect(document.getElementById('editDisplayName').value).toBe('Johnny');
        expect(mockModal.show).toHaveBeenCalled();
    });

    test('should PATCH updated user data to /api/users/<id>/profile on form submit', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ success: true, message: 'User updated' })
        });

        const form = document.getElementById('editUserForm');
        document.getElementById('editUserId').value = 'user-123';
        document.getElementById('editFirstName').value = 'Jane';
        document.getElementById('editLastName').value = 'Smith';

        const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
        form.dispatchEvent(submitEvent);

        await new Promise(resolve => setTimeout(resolve, 100));

        expect(mockFetch).toHaveBeenCalledWith(
            '/api/users/user-123/profile',
            expect.objectContaining({
                method: 'PATCH',
                headers: expect.objectContaining({
                    'Content-Type': 'application/json',
                    'X-CSRFToken': 'test-csrf-token'
                }),
                body: expect.stringContaining('Jane')
            })
        );
        expect(global.loadUsers).toHaveBeenCalled();
    });

    test('should PATCH role when changed and editor has permissions', async () => {
        mockFetch
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true, message: 'User updated' })
            })
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true })
            });

        global.currentUser = { role: 'institution_admin' };

        const form = document.getElementById('editUserForm');
        document.getElementById('editUserId').value = 'user-123';
        document.getElementById('editFirstName').value = 'Jane';
        document.getElementById('editLastName').value = 'Smith';
        const roleSelect = document.getElementById('editUserRole');
        roleSelect.dataset.originalRole = 'instructor';
        roleSelect.value = 'program_admin';

        const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
        form.dispatchEvent(submitEvent);

        await new Promise(resolve => setTimeout(resolve, 100));

        expect(mockFetch).toHaveBeenNthCalledWith(
            1,
            '/api/users/user-123/profile',
            expect.any(Object)
        );
        expect(mockFetch).toHaveBeenNthCalledWith(
            2,
            '/api/users/user-123/role',
            expect.objectContaining({
                method: 'PATCH',
                body: JSON.stringify({ role: 'program_admin' })
            })
        );
        delete global.currentUser;
    });
});

describe('User Management - Deactivate & Delete', () => {
    let mockFetch;
    let confirmSpy;
    let promptSpy;
    let alertSpy;

    beforeEach(() => {
        document.body.innerHTML = '<meta name="csrf-token" content="test-csrf-token">';
        mockFetch = jest.fn();
        global.fetch = mockFetch;
        confirmSpy = jest.spyOn(window, 'confirm');
        promptSpy = jest.spyOn(window, 'prompt');
        alertSpy = jest.spyOn(window, 'alert').mockImplementation();
        global.loadUsers = jest.fn();
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    describe('deactivateUser', () => {
        test('should POST to /api/users/<id>/deactivate on confirmation', async () => {
            confirmSpy.mockReturnValue(true);
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true })
            });

            await window.deactivateUser('user-123', 'John Doe');

            expect(confirmSpy).toHaveBeenCalledWith(
                expect.stringContaining('John Doe')
            );
            expect(mockFetch).toHaveBeenCalledWith(
                '/api/users/user-123/deactivate',
                expect.objectContaining({
                    method: 'POST',
                    headers: expect.objectContaining({
                        'X-CSRFToken': 'test-csrf-token'
                    })
                })
            );
            expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining('deactivated'));
            expect(global.loadUsers).toHaveBeenCalled();
        });

        test('should not deactivate if user cancels confirmation', async () => {
            confirmSpy.mockReturnValue(false);

            await window.deactivateUser('user-123', 'John Doe');

            expect(mockFetch).not.toHaveBeenCalled();
        });

        test('should handle API errors gracefully', async () => {
            confirmSpy.mockReturnValue(true);
            mockFetch.mockResolvedValueOnce({
                ok: false,
                json: async () => ({ error: 'User not found' })
            });

            await window.deactivateUser('user-123', 'John Doe');

            expect(alertSpy).toHaveBeenCalledWith(
                expect.stringContaining('User not found')
            );
        });
    });

    describe('deleteUser', () => {
        test('should DELETE /api/users/<id> with correct confirmation', async () => {
            promptSpy.mockReturnValue('DELETE John Doe');
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true })
            });

            await window.deleteUser('user-123', 'John Doe');

            expect(promptSpy).toHaveBeenCalledWith(
                expect.stringContaining('DELETE John Doe')
            );
            expect(mockFetch).toHaveBeenCalledWith(
                '/api/users/user-123',
                expect.objectContaining({
                    method: 'DELETE',
                    headers: expect.objectContaining({
                        'X-CSRFToken': 'test-csrf-token'
                    })
                })
            );
            expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining('permanently deleted'));
            expect(global.loadUsers).toHaveBeenCalled();
        });

        test('should not delete if confirmation text does not match', async () => {
            promptSpy.mockReturnValue('DELETE wrong-name');

            await window.deleteUser('user-123', 'John Doe');

            expect(mockFetch).not.toHaveBeenCalled();
            expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining('cancelled'));
        });

        test('should not delete if user cancels prompt', async () => {
            promptSpy.mockReturnValue(null);

            await window.deleteUser('user-123', 'John Doe');

            expect(mockFetch).not.toHaveBeenCalled();
            expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining('cancelled'));
        });

        test('should handle API errors gracefully', async () => {
            promptSpy.mockReturnValue('DELETE John Doe');
            mockFetch.mockResolvedValueOnce({
                ok: false,
                json: async () => ({ error: 'Cannot delete admin user' })
            });

            await window.deleteUser('user-123', 'John Doe');

            expect(alertSpy).toHaveBeenCalledWith(
                expect.stringContaining('Cannot delete admin user')
            );
        });
    });
});
