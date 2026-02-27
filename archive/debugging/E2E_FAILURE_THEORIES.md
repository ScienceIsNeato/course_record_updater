# E2E Parallel Test Failure Theories

## 🧪 Scientific Approach to Debugging

Each theory below includes:

1. **Hypothesis**: What we think is wrong
2. **Evidence**: What we observed
3. **Root Cause Theory**: Why it's happening
4. **Confirmation Test**: How to prove/disprove it

---

## ❌ Failure 1: Program Admin Has No Programs

**Test**: `test_tc_crud_pa_006_cannot_access_other_programs`  
**Error**: `AssertionError: Program admin should have at least one assigned program, got: []`

### 🔬 Hypothesis

Worker-specific program admin accounts (`lisa.prog_worker0@mocku.test`) are created but never assigned to any programs. The seed script creates the users but doesn't establish the user→program relationship.

### 📊 Evidence

- Base account (`lisa.prog@mocku.test`) works fine (seeded by `seed_db.py`)
- Worker accounts created by `seed_worker_accounts.py` fail
- We added section assignment for instructors but NO program assignment for program admins

### 🎯 Root Cause Theory

`scripts/seed_worker_accounts.py` creates the `lisa.prog_workerN` accounts but doesn't call `assign_user_to_program()` or equivalent. Program admins need explicit program assignments to function.

### ✅ Confirmation Test

```bash
# Check if worker program admin has program assignments
sqlite3 course_records_e2e.db << 'EOF'
SELECT u.email, COUNT(up.program_id) as program_count
FROM users u
LEFT JOIN user_programs up ON u.id = up.user_id
WHERE u.email LIKE 'lisa.prog_worker%'
GROUP BY u.email
ORDER BY u.email;
EOF
```

**Expected if theory is correct**: `program_count = 0` for all worker accounts  
**Expected if theory is wrong**: `program_count > 0` for worker accounts

---

## ❌ Failure 2: Registration Verification Goes to Wrong Port

**Test**: `test_complete_registration_and_password_workflow`  
**Error**: `Page.goto: net::ERR_HTTP_RESPONSE_CODE_FAILURE at http://localhost:5000/api/auth/verify-email/...`

### 🔬 Hypothesis

Email verification links are generated with a hardcoded or incorrectly configured `BASE_URL`. When worker 3 registers a user, the verification email contains `http://localhost:5000` instead of `http://localhost:3005` (worker 3's port).

### 📊 Evidence

- Error shows `localhost:5000` (not a port we use anywhere)
- Worker-specific Flask servers run on ports 3002-3017
- Email generation happens in `email_service.py` which uses `BASE_URL` from environment

### 🎯 Root Cause Theory

One of these:

1. `BASE_URL` environment variable not set for worker-specific Flask servers
2. Email service caching the BASE_URL from initial load (before worker setup)
3. Verification email template using a different URL source

### ✅ Confirmation Test

```python
# Add to tests/e2e/conftest.py temporarily
@pytest.fixture(scope="function", autouse=True)
def log_base_url_for_worker():
    worker_id = get_worker_id()
    expected_port = get_worker_port()
    print(f"\n🔍 Worker {worker_id}: Expected port {expected_port}")

    # Check environment
    import os
    print(f"   DATABASE_URL: {os.environ.get('DATABASE_URL', 'NOT SET')}")
    print(f"   BASE_URL: {os.environ.get('BASE_URL', 'NOT SET')}")
    print(f"   PORT: {os.environ.get('PORT', 'NOT SET')}")
    yield
```

Then run the registration test alone and check output.

**Alternative Quick Test**:

```bash
# Check what BASE_URL is in email_service when worker starts
grep -n "BASE_URL" email_service.py
grep -n "5000" email_service.py
```

---

## ❌ Failure 3: Instructor Profile Modal Won't Close

**Test**: `test_tc_crud_inst_001_update_own_profile`  
**Error**: `TimeoutError: Page.wait_for_selector: Timeout 30000ms exceeded` (waiting for #editUserModal to hide)

### 🔬 Hypothesis

The update profile API call is failing (returning error or hanging), so the modal's success callback never fires to close it. Console error "Failed to fetch" suggests the API endpoint isn't responding.

### 📊 Evidence

- Modal remains visible after 30s
- Console shows: `Program dashboard load error: TypeError: Failed to fetch`
- Happens in parallel but not always (flaky)

### 🎯 Root Cause Theory (Pick One)

**Theory 3A**: Worker-specific instructor making API call to wrong Flask instance (port mismatch)  
**Theory 3B**: Database lock/contention - SQLite can't handle concurrent writes from profile updates  
**Theory 3C**: CSRF token mismatch between page load and API call in parallel workers

### ✅ Confirmation Test

**For Theory 3A (Port Mismatch)**:

```python
# In test_crud_instructor.py, add before the profile update:
current_url = page.url
print(f"🔍 Current page URL: {current_url}")
# Check if page is on correct worker port
```

**For Theory 3B (Database Lock)**:

```bash
# Run test with SQLite logging
PRAGMA busy_timeout = 30000;  # 30 second timeout
# If we see "database is locked" errors, it's 3B
```

**For Theory 3C (CSRF)**:

```python
# Add to test before API call:
csrf_token = page.evaluate("document.querySelector('[name=csrf_token]').value")
print(f"🔍 CSRF token: {csrf_token}")
```

**Quick Confirmation**:
Run the test individually (no parallel):

```bash
./run_uat.sh -t "tc_crud_inst_001"
```

If it passes individually → **Resource contention** (Theory 3B)  
If it fails individually → **Code bug** (Theory 3A or 3C)

---

## ❌ Failure 4: Instructor Has No Courses in Dropdown

**Test**: `test_tc_crud_inst_002_update_section_assessment`  
**Error**: `AssertionError: Expected at least 2 options (empty + courses), got 1` (only empty option)

### 🔬 Hypothesis

Worker-specific instructors have sections assigned, but the API endpoint that fetches "courses I teach" is querying by base instructor email or ID, not finding the worker-specific instructor's assignments.

### 📊 Evidence

- We added section assignment in `seed_worker_accounts.py` (`assign_sections_to_instructor`)
- Test expects dropdown to have courses
- Only getting 1 option (the empty/placeholder option)

### 🎯 Root Cause Theory (Interrelated!)

The API endpoint `/api/instructor/courses` or similar is using the authenticated user's ID to query sections. BUT: the authentication fixture might be using the base email while the database has worker-specific sections.

**Specifically**:

1. Test authenticates as `john.instructor_worker0@mocku.test`
2. Sections are assigned to that user ID
3. API query works correctly
4. BUT: JavaScript might be making request before authentication propagates
5. OR: API is checking against wrong institution_id

### ✅ Confirmation Test

**Direct Database Check**:

```bash
# Verify worker instructor has sections with courses
sqlite3 course_records_e2e.db << 'EOF'
SELECT
    u.email,
    COUNT(DISTINCT cs.section_id) as section_count,
    COUNT(DISTINCT c.course_id) as unique_courses,
    GROUP_CONCAT(DISTINCT c.code) as course_codes
FROM users u
LEFT JOIN course_sections cs ON u.id = cs.instructor_id
LEFT JOIN course_offerings co ON cs.offering_id = co.offering_id
LEFT JOIN courses c ON co.course_id = c.course_id
WHERE u.email LIKE 'john.instructor_worker%'
GROUP BY u.email
ORDER BY u.email
LIMIT 5;
EOF
```

**Expected if theory correct**: `section_count > 0` and `unique_courses > 0`

**API Response Check**:
Add to test before the assertion:

```python
# Check what the API is returning
page.goto(f"{BASE_URL}/api/instructor/courses")
api_response = page.text_content("pre")  # If JSON response
print(f"🔍 API returned: {api_response}")
```

---

## 🔗 Interrelated Root Cause: The Seeding Gap Pattern

### 🎯 Meta-Theory

All 4 failures share a pattern: **Worker accounts are created but relationships aren't established**.

```
✅ seed_db.py creates:
   - Base accounts with full relationships
   - lisa.prog@mocku.test → assigned to programs
   - john.instructor@mocku.test → assigned to sections

❌ seed_worker_accounts.py creates:
   - Worker accounts (users exist)
   - Sections assigned to instructors (✅ we added this)
   - BUT: Programs NOT assigned to program admins (❌ missing)
   - AND: May have other missing relationships
```

### ✅ Master Confirmation Test

```bash
# Compare base vs worker accounts
sqlite3 course_records_e2e.db << 'EOF'
.headers on
.mode column

-- Base accounts relationships
SELECT 'BASE INSTRUCTOR' as type, email,
       (SELECT COUNT(*) FROM course_sections WHERE instructor_id = u.id) as sections
FROM users u WHERE email = 'john.instructor@mocku.test';

-- Worker accounts relationships
SELECT 'WORKER INSTRUCTOR' as type, email,
       (SELECT COUNT(*) FROM course_sections WHERE instructor_id = u.id) as sections
FROM users u WHERE email LIKE 'john.instructor_worker%' LIMIT 3;

-- Base program admin relationships
SELECT 'BASE PROG ADMIN' as type, email,
       (SELECT COUNT(*) FROM user_programs WHERE user_id = u.id) as programs
FROM users u WHERE email = 'lisa.prog@mocku.test';

-- Worker program admin relationships
SELECT 'WORKER PROG ADMIN' as type, email,
       (SELECT COUNT(*) FROM user_programs WHERE user_id = u.id) as programs
FROM users u WHERE email LIKE 'lisa.prog_worker%' LIMIT 3;
EOF
```

This will show us the full scope of the seeding gap.

---

## 📋 Summary: Theories Ranked by Likelihood

1. **HIGH CONFIDENCE** (90%): Failure 1 - Program admins not assigned to programs
2. **MEDIUM-HIGH** (75%): Failure 4 - Related seeding issue or API query bug
3. **MEDIUM** (60%): Failure 2 - BASE_URL not propagating to workers
4. **LOW-MEDIUM** (40%): Failure 3 - Resource contention or port mismatch

All theories point to **incomplete parallel execution infrastructure** rather than the application code being broken.
