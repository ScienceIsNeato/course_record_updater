# E2E Authentication Debugging Log

## Scientific Method Approach

### Current State
- ✅ Health endpoint test passes (0.99s)
- ✅ Server starts, DB seeds successfully
- ❌ Login form submission fails silently (stays on /login page, no error message)

---

## Hypothesis 1: Login page and form elements load correctly

**Test:** Create E2E test that verifies login page structure without attempting login

**Expected Outcomes:**
- ✅ **Success**: Page loads, email input exists, password input exists, submit button exists, CSRF token exists
  - **Action**: Move to Hypothesis 2 (CSRF token retrieval)
- ❌ **Failure**: Missing form elements or page doesn't load
  - **Action**: Fix page routing or template issues before proceeding

**Test Implementation:**
```python
@pytest.mark.e2e
def test_login_page_loads(page: Page, server_running: bool):
    """Verify login page structure"""
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")
    
    # Check form elements
    assert page.locator('input[name="email"]').count() > 0
    assert page.locator('input[name="password"]').count() > 0
    assert page.locator('button[type="submit"]').count() > 0
    assert page.locator('input[name="csrf_token"]').count() > 0
```

---

## Hypothesis 2: CSRF token can be retrieved from login page

**Test:** Extract CSRF token value and verify it's not empty

**Expected Outcomes:**
- ✅ **Success**: Token exists and is a non-empty string
  - **Action**: Move to Hypothesis 3 (form submission)
- ❌ **Failure**: Token is empty or None
  - **Action**: Check Flask CSRF configuration, verify WTF_CSRF_ENABLED in test mode

---

## Hypothesis 3: Form submission completes without JavaScript errors

**Test:** Submit form and check browser console for errors

**Expected Outcomes:**
- ✅ **Success**: No JavaScript errors, form submits
  - **Action**: Check network response (Hypothesis 4)
- ❌ **Failure**: JavaScript errors prevent submission
  - **Action**: Fix JS errors in login.html or static/script.js

---

## Hypothesis 4: Login endpoint returns success response

**Test:** Capture network response from login submission

**Expected Outcomes:**
- ✅ **Success**: 200 response with success JSON
  - **Action**: Check why redirect doesn't happen (Hypothesis 5)
- ❌ **Failure**: 401/400 response or error message
  - **Action**: Debug backend authentication (password hash, user lookup)

---

## Hypothesis 5: Session cookie is set after successful login

**Test:** Check cookies after login response

**Expected Outcomes:**
- ✅ **Success**: Session cookie exists
  - **Action**: Verify cookie is used in subsequent requests
- ❌ **Failure**: No session cookie
  - **Action**: Check Flask session configuration for E2E tests

---

## Current Test Results

### ✅ Hypothesis 1: CONFIRMED (1.58s)
- **Result**: PASSED - All form elements exist
- **Conclusion**: Page structure is correct

### ✅ Hypothesis 2: CONFIRMED (2.42s)
- **Result**: PASSED - NO API call captured
- **Finding**: Form submits but no `/auth/login` API request
- **Conclusion**: JavaScript form handler not running

### ✅ Hypothesis 3: CONFIRMED (2.08s)
- **Result**: PASSED - auth.js loads, functions defined, BUT listener not attached
- **Critical Findings**:
  - ✅ `auth.js` loads successfully
  - ✅ All functions defined: `handleLogin`, `initializeLoginForm`, `initializePage`, `getCSRFToken`
  - ✅ DOM is ready
  - ✅ Path is `/login` (would trigger `initializeLoginForm()`)
  - ❌ **form.onsubmit is NOT SET** - no event listener attached!
  
**ROOT CAUSE IDENTIFIED**: 
- `auth.js` is loaded at the END of the HTML (after form)
- By the time script executes, `DOMContentLoaded` event has ALREADY FIRED
- The `addEventListener('DOMContentLoaded', ...)` call happens TOO LATE
- `initializePage()` never runs, so no event listener is attached
- Form falls back to traditional HTML submit with `action="/login"` (page reload)

---

## Hypothesis 2: Form submission returns correct response

**Test:** Submit login form and capture network response/console errors

**Implementation:**
```python
@pytest.mark.e2e
def test_login_form_submission(page: Page, server_running: bool):
    """Capture network response and console errors during login"""
    # Listen for console messages (errors/warnings)
    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
    
    # Listen for network responses
    responses = []
    page.on("response", lambda response: responses.append(response))
    
    # Navigate and submit form
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")
    
    # Fill form with KNOWN GOOD credentials
    page.fill('input[name="email"]', "sarah.admin@cei.edu")
    page.fill('input[name="password"]', "InstitutionAdmin123!")
    
    # Submit and wait for response
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    
    # Check for auth API response
    auth_response = [r for r in responses if "/auth/login" in r.url]
    if auth_response:
        status = auth_response[0].status
        print(f"Auth response: {status}")
    
    # Check console for errors
    errors = [log for log in console_logs if "error" in log.lower()]
    print(f"Console errors: {errors}")
```

