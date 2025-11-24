
const { setBody } = require('../helpers/dom');
require('../../../static/register_invitation');

describe('register_invitation.js', () => {
  let mockFetch;
  let consoleErrorSpy;

  beforeEach(() => {
    setBody(`
      <input id="invitationToken" value="token-123">
      <input id="firstName" value="First">
      <input id="lastName" value="Last">
      <input id="password" value="password123">
      <input id="confirmPassword" value="password123">
      <form id="acceptInvitationForm"></form>
      <div id="loadingInvitation"></div>
      <input id="email">
      <input id="role">
      <div id="invitationDetails" class="d-none"></div>
      <div id="inviterName"></div>
      <div id="institutionName"></div>
      <div id="personalMessage"></div>
      <div id="personalMessageSection" class="d-none"></div>
      <div id="statusMessage" class="d-none"></div>
      <button id="submitBtn">
        <span class="btn-text">Submit</span>
        <span class="btn-spinner d-none"></span>
      </button>
      <meta name="csrf-token" content="test-csrf-token">
    `);

    mockFetch = jest.fn();
    global.fetch = mockFetch;
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

    // Mock location
    delete global.location;
    global.location = { href: '', pathname: '/register-invitation' };

    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  test('should handle network error during validation', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    await global.validateInvitation('token');

    expect(consoleErrorSpy).toHaveBeenCalledWith(
      expect.stringContaining('Error validating'),
      expect.anything()
    );
    const msg = document.getElementById('statusMessage');
    expect(msg.textContent).toContain('Failed to validate');
  });

  test('should handle network error during acceptance', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    await global.acceptInvitation();

    expect(consoleErrorSpy).toHaveBeenCalledWith(
      expect.stringContaining('Error accepting'),
      expect.anything()
    );
    const msg = document.getElementById('statusMessage');
    expect(msg.textContent).toContain('Failed to create account');
  });

  test('should redirect on success', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    });

    await global.acceptInvitation();

    expect(document.getElementById('statusMessage').textContent).toContain(
      'created successfully'
    );

    // Fast forward
    jest.advanceTimersByTime(2000);

    expect(global.location.href).toContain('/login');
  });

  test('should format role correctly', () => {
    expect(global.formatRole('institution_admin')).toBe('Institution Admin');
  });
});

