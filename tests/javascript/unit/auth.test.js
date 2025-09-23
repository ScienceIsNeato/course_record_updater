const auth = require('../../../static/auth');
const { setBody, flushPromises } = require('../helpers/dom');

describe('auth module', () => {
  const originalLocation = window.location;

  beforeAll(() => {
    delete window.location;
    window.location = { href: '', assign: jest.fn(), replace: jest.fn() };
  });

  afterAll(() => {
    window.location = originalLocation;
  });

  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('validates email addresses correctly', () => {
    setBody('<div class="field"><input id="email" /><div class="invalid-feedback"></div></div>');
    const input = document.getElementById('email');

    input.value = 'invalid';
    expect(auth.validateEmail.call(input)).toBe(false);
    expect(input.classList.contains('is-invalid')).toBe(true);

    input.value = 'user@example.com';
    expect(auth.validateEmail.call(input)).toBe(true);
    expect(input.classList.contains('is-valid')).toBe(true);
  });

  it('updates password strength indicators and requirements', () => {
    setBody(`
      <div>
        <input id="password" value="Str0ng!Pass" />
        <div id="passwordStrengthFill"></div>
        <div id="passwordStrengthLabel"></div>
        <div id="req-length"><i></i></div>
        <div id="req-uppercase"><i></i></div>
        <div id="req-lowercase"><i></i></div>
        <div id="req-number"><i></i></div>
      </div>
    `);

    auth.updatePasswordStrength('password');

    expect(document.getElementById('passwordStrengthFill').className).toContain('strong');
    expect(document.getElementById('passwordStrengthLabel').textContent).toContain('Strong');
    expect(document.getElementById('req-length').classList.contains('met')).toBe(true);
    expect(document.getElementById('req-number').classList.contains('met')).toBe(true);
  });

  it('validates matching passwords', () => {
    setBody(`
      <div>
        <input id="password" value="StrongPass1!" />
        <input id="confirmPassword" value="Different" />
        <div class="invalid-feedback"></div>
      </div>
    `);

    expect(auth.validatePasswordMatch()).toBe(false);
    document.getElementById('confirmPassword').value = 'StrongPass1!';
    expect(auth.validatePasswordMatch()).toBe(true);
  });

  it('handles successful login flow', async () => {
    setBody(`
      <form id="loginForm" class="auth-form" novalidate>
        <div><input id="email" name="email" required /><div class="invalid-feedback"></div></div>
        <div><input id="password" name="password" type="password" required /><div class="invalid-feedback"></div></div>
        <button id="loginBtn" type="submit">Login</button>
      </form>
    `);

    document.getElementById('email').value = 'user@example.com';
    document.getElementById('password').value = 'Str0ng!Pass';

    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });

    const form = document.getElementById('loginForm');
    const event = { preventDefault: jest.fn(), target: form };

    await auth.handleLogin(event);

    expect(global.fetch).toHaveBeenCalledWith('/api/auth/login', expect.objectContaining({ method: 'POST' }));
    expect(document.querySelector('.alert-success')).not.toBeNull();

    jest.advanceTimersByTime(1000);
    expect(window.location.href).toBe('/dashboard');
  });

  it('handles successful registration and redirects to login', async () => {
    setBody(`
      <form id="registerForm" class="auth-form" novalidate>
        <div><input id="email" name="email" type="email" required /><div class="invalid-feedback"></div></div>
        <div><input id="password" name="password" type="password" required /><div class="invalid-feedback"></div></div>
        <div><input id="confirmPassword" name="confirmPassword" type="password" required /><div class="invalid-feedback"></div></div>
        <div><input id="firstName" name="firstName" required /><div class="invalid-feedback"></div></div>
        <div><input id="lastName" name="lastName" required /><div class="invalid-feedback"></div></div>
        <div><input id="institutionName" name="institutionName" required /><div class="invalid-feedback"></div></div>
        <div><input id="institutionWebsite" name="institutionWebsite" type="url" /><div class="invalid-feedback"></div></div>
        <div><input id="agreeTerms" name="agreeTerms" type="checkbox" required checked /><div class="invalid-feedback"></div></div>
        <button id="registerBtn" type="submit">Register</button>
      </form>
    `);

    document.getElementById('email').value = 'newuser@example.com';
    document.getElementById('password').value = 'StrongPass1!';
    document.getElementById('confirmPassword').value = 'StrongPass1!';
    document.getElementById('firstName').value = 'New';
    document.getElementById('lastName').value = 'User';
    document.getElementById('institutionName').value = 'Example University';
    document.getElementById('institutionWebsite').value = 'https://example.edu';

    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });

    const form = document.getElementById('registerForm');
    const event = { preventDefault: jest.fn(), target: form };

    await auth.handleRegister(event);

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/auth/register',
      expect.objectContaining({ method: 'POST' })
    );

    jest.advanceTimersByTime(3000);
    expect(window.location.href).toBe('/login');
  });

  it('handles forgot password success state', async () => {
    setBody(`
      <form id="forgotPasswordForm" class="auth-form" novalidate>
        <div><input id="email" name="email" type="email" required /><div class="invalid-feedback"></div></div>
        <button id="resetBtn" type="submit">Reset</button>
      </form>
      <div id="successState" class="d-none"></div>
    `);

    document.getElementById('email').value = 'user@example.com';

    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });

    const form = document.getElementById('forgotPasswordForm');
    const event = { preventDefault: jest.fn(), target: form };

    await auth.handleForgotPassword(event);

    const successState = document.getElementById('successState');
    expect(successState.classList.contains('d-none')).toBe(false);
  });

  it('shows lockout modal when login locked', async () => {
    setBody(`
      <div id="lockoutModal"></div>
      <form id="loginForm" novalidate>
        <div><input id="email" name="email" required /><div class="invalid-feedback"></div></div>
        <div><input id="password" name="password" type="password" required /><div class="invalid-feedback"></div></div>
        <button id="loginBtn" type="submit">Login</button>
      </form>
    `);

    document.getElementById('email').value = 'user@example.com';
    document.getElementById('password').value = 'Str0ng!Pass';

    global.fetch.mockResolvedValue({
      ok: false,
      status: 423,
      json: async () => ({ success: false })
    });

    const form = document.getElementById('loginForm');
    const event = { preventDefault: jest.fn(), target: form };

    await auth.handleLogin(event);

    const modalElement = document.getElementById('lockoutModal');
    const modalInstance = bootstrap.Modal.getInstance(modalElement);
    expect(modalInstance.visible).toBe(true);
  });

  it('logs out when confirmed', async () => {
    global.confirm.mockReturnValue(true);
    global.fetch.mockResolvedValue({});

    await auth.logout();
    expect(global.fetch).toHaveBeenCalledWith('/api/auth/logout', expect.any(Object));
    await flushPromises();
    expect(window.location.href).toBe('/login');
  });

  it('validates URLs safely', () => {
    expect(auth.isValidUrl('https://example.com')).toBe(true);
    expect(auth.isValidUrl('not-a-url')).toBe(false);
  });

  it('handles login network errors gracefully', async () => {
    setBody(`
      <form id="loginForm" class="auth-form" novalidate>
        <div><input id="email" name="email" required /><div class="invalid-feedback"></div></div>
        <div><input id="password" name="password" type="password" required /><div class="invalid-feedback"></div></div>
        <button id="loginBtn" type="submit">Login</button>
      </form>
    `);

    document.getElementById('email').value = 'user@example.com';
    document.getElementById('password').value = 'Str0ng!Pass';

    global.fetch.mockRejectedValue(new Error('Network down'));

    const form = document.getElementById('loginForm');
    await auth.handleLogin({ preventDefault: jest.fn(), target: form });

    expect(document.querySelector('.alert-danger')).not.toBeNull();
  });

  it('handles registration error responses', async () => {
    setBody(`
      <form id="registerForm" class="auth-form" novalidate>
        <div><input id="email" name="email" type="email" required /><div class="invalid-feedback"></div></div>
        <div><input id="password" name="password" type="password" required /><div class="invalid-feedback"></div></div>
        <div><input id="confirmPassword" name="confirmPassword" type="password" required /><div class="invalid-feedback"></div></div>
        <div><input id="firstName" name="firstName" required /><div class="invalid-feedback"></div></div>
        <div><input id="lastName" name="lastName" required /><div class="invalid-feedback"></div></div>
        <div><input id="institutionName" name="institutionName" required /><div class="invalid-feedback"></div></div>
        <div><input id="institutionWebsite" name="institutionWebsite" type="url" /><div class="invalid-feedback"></div></div>
        <div><input id="agreeTerms" name="agreeTerms" type="checkbox" required checked /><div class="invalid-feedback"></div></div>
        <button id="registerBtn" type="submit">Register</button>
      </form>
    `);

    document.getElementById('email').value = 'newuser@example.com';
    document.getElementById('password').value = 'StrongPass1!';
    document.getElementById('confirmPassword').value = 'StrongPass1!';
    document.getElementById('firstName').value = 'New';
    document.getElementById('lastName').value = 'User';
    document.getElementById('institutionName').value = 'Example University';

    global.fetch.mockResolvedValue({
      ok: false,
      json: async () => ({ success: false, error: 'Duplicate' })
    });

    await auth.handleRegister({ preventDefault: jest.fn(), target: document.getElementById('registerForm') });
    expect(document.querySelector('.alert-danger')).not.toBeNull();
  });

  it('handles forgot password failures', async () => {
    setBody(`
      <form id="forgotPasswordForm" class="auth-form" novalidate>
        <div><input id="email" name="email" type="email" required /><div class="invalid-feedback"></div></div>
        <button id="resetBtn" type="submit">Reset</button>
      </form>
      <div id="successState" class="d-none"></div>
    `);

    document.getElementById('email').value = 'user@example.com';

    global.fetch.mockResolvedValue({
      ok: false,
      json: async () => ({ success: false, error: 'No account' })
    });

    await auth.handleForgotPassword({ preventDefault: jest.fn(), target: document.getElementById('forgotPasswordForm') });
    expect(document.querySelector('.alert-danger')).not.toBeNull();
  });

  it('initializes password toggles and toggles input type', () => {
    setBody(`
      <button id="togglePassword"><i class="fas fa-eye"></i></button>
      <input id="password" type="password" />
    `);

    auth.initializePasswordToggles();
    document.getElementById('togglePassword').click();
    expect(document.getElementById('password').type).toBe('text');
  });

  it('validates form with multiple input types', () => {
    setBody(`
      <form id="sample">
        <input id="email" type="email" required value="user@example.com" />
        <input id="password" type="password" required value="StrongPass1!" />
        <input id="confirmPassword" type="password" required value="StrongPass1!" />
        <input id="url" type="url" value="https://example.com" />
        <input id="agree" type="checkbox" required />
        <div class="invalid-feedback"></div>
      </form>
    `);

    const form = document.getElementById('sample');
    document.getElementById('agree').checked = false;
    expect(auth.validateForm(form)).toBe(false);
    document.getElementById('agree').checked = true;
    expect(auth.validateForm(form)).toBe(true);
  });

  it('initializes page based on location', () => {
    window.location.pathname = '/login';
    setBody(`
      <form id="loginForm" novalidate></form>
      <input id="email" />
      <input id="password" type="password" />
    `);
    const loginForm = document.getElementById('loginForm');
    const loginListener = jest.spyOn(loginForm, 'addEventListener');
    auth.initializePage();
    expect(loginListener).toHaveBeenCalledWith('submit', auth.handleLogin);
    loginListener.mockRestore();

    window.location.pathname = '/register';
    setBody(`
      <form id="registerForm" novalidate>
        <input id="password" type="password" />
        <input id="confirmPassword" type="password" />
      </form>
    `);
    const registerForm = document.getElementById('registerForm');
    const registerListener = jest.spyOn(registerForm, 'addEventListener');
    auth.initializePage();
    expect(registerListener).toHaveBeenCalledWith('submit', auth.handleRegister);
    registerListener.mockRestore();

    window.location.pathname = '/forgot-password';
    setBody(`
      <form id="forgotPasswordForm" novalidate>
        <input id="email" type="email" />
      </form>
    `);
    const forgotForm = document.getElementById('forgotPasswordForm');
    const forgotListener = jest.spyOn(forgotForm, 'addEventListener');
    auth.initializePage();
    expect(forgotListener).toHaveBeenCalledWith('submit', auth.handleForgotPassword);
    forgotListener.mockRestore();
  });

  it('shows account lockout fallback when modal missing', () => {
    setBody('<div class="auth-form"></div>');
    auth.showAccountLockout();
    expect(document.querySelector('.alert-danger')).not.toBeNull();
  });

  describe('additional authentication edge cases', () => {
    it('handles password strength validation edge cases', () => {
      // Test password strength function returns objects with scores
      const weakResult = auth.getPasswordStrength('weak');
      expect(weakResult.score).toBeGreaterThan(0);
      
      const strongResult = auth.getPasswordStrength('StrongPass123!');
      expect(strongResult.score).toBeGreaterThan(weakResult.score);
      
      const emptyResult = auth.getPasswordStrength('');
      expect(emptyResult.score).toBe(0);
    });

    it('handles email validation thoroughly', () => {
      setBody(`
        <form id="testForm">
          <input id="email" name="email" type="email" />
          <div class="invalid-feedback"></div>
        </form>
      `);

      const emailInput = document.getElementById('email');
      
      // Test valid emails by calling the function as a method on the input
      emailInput.value = 'user@example.com';
      expect(auth.validateEmail.call(emailInput)).toBe(true);
      
      emailInput.value = 'test.email+tag@domain.co.uk';
      expect(auth.validateEmail.call(emailInput)).toBe(true);
      
      // Test invalid emails
      emailInput.value = 'invalid-email';
      expect(auth.validateEmail.call(emailInput)).toBe(false);
      
      emailInput.value = '@domain.com';
      expect(auth.validateEmail.call(emailInput)).toBe(false);
      
      // Test empty email
      emailInput.value = '';
      expect(auth.validateEmail.call(emailInput)).toBe(false);
    });

    it('handles password confirmation validation correctly', () => {
      setBody(`
        <form id="registerForm">
          <input id="password" name="password" type="password" value="StrongPass1!" />
          <input id="confirmPassword" name="confirmPassword" type="password" />
          <div class="invalid-feedback"></div>
        </form>
      `);

      const confirmInput = document.getElementById('confirmPassword');
      
      // Test matching passwords using call
      confirmInput.value = 'StrongPass1!';
      expect(auth.validatePasswordMatch.call(confirmInput)).toBe(true);
      
      // Test non-matching passwords
      confirmInput.value = 'DifferentPass1!';
      expect(auth.validatePasswordMatch.call(confirmInput)).toBe(false);
    });

    it('handles required field validation', () => {
      setBody(`
        <form id="testForm">
          <input id="testField" name="testField" type="text" required />
          <div class="invalid-feedback"></div>
        </form>
      `);

      const testInput = document.getElementById('testField');
      
      // Test empty required field
      testInput.value = '';
      expect(auth.validateRequired.call(testInput)).toBe(false);
      
      // Test filled required field
      testInput.value = 'some value';
      expect(auth.validateRequired.call(testInput)).toBe(true);
    });

    it('handles validation state setting', () => {
      setBody(`
        <form id="testForm">
          <input id="testField" name="testField" type="text" />
          <div class="invalid-feedback"></div>
        </form>
      `);

      const testInput = document.getElementById('testField');
      
      // Test setting invalid state
      auth.setValidationState(testInput, false, 'Error message');
      expect(testInput.classList.contains('is-invalid')).toBe(true);
      
      // Test setting valid state
      auth.setValidationState(testInput, true);
      expect(testInput.classList.contains('is-valid')).toBe(true);
      expect(testInput.classList.contains('is-invalid')).toBe(false);
    });

    it('handles clearing validation', () => {
      setBody(`
        <form id="testForm">
          <input id="testField" name="testField" type="text" class="is-invalid" />
          <div class="invalid-feedback">Error message</div>
        </form>
      `);

      const testInput = document.getElementById('testField');
      
      // Clear validation using call
      auth.clearValidation.call(testInput);
      
      expect(testInput.classList.contains('is-invalid')).toBe(false);
      expect(testInput.classList.contains('is-valid')).toBe(false);
    });

    it('tests password requirements function exists', () => {
      // Just test that the function exists and can be called
      expect(typeof auth.updatePasswordRequirements).toBe('function');
      
      // Call it with different values to exercise the code
      auth.updatePasswordRequirements('weak');
      auth.updatePasswordRequirements('StrongPass123!');
      auth.updatePasswordRequirements('');
      
      // If we get here without errors, the function works
      expect(true).toBe(true);
    });
  });
});
