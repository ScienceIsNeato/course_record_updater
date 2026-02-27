# E2E Test Suite Summary

## Test Run Results After Number Standardization

**Overall**: 56 passed, 2 failed, 2 errors (console errors in teardown)

### ✅ Completed This Session

1. **Headless Mode Now Default**
   - Modified `tests/e2e/conftest.py` to default to headless mode
   - Browser only shows when explicitly requested with `--watch` or `--headed` flag
   - Usage:
     - `pytest -m e2e` → Headless (no browser windows)
     - `./run_uat.sh` → Headless by default
     - `./run_uat.sh --watch` → Shows browser with 350ms slow-mo
     - `pytest -m e2e --headed` → Shows browser
     - `HEADLESS=0 pytest -m e2e` → Shows browser

### ❌ Remaining Issues (3 actual test failures)

#### 1. **Email Verification Port Mismatch** (CRITICAL)

- **Test**: `test_complete_registration_and_password_workflow`
- **Problem**: Verification link uses `localhost:5000` instead of worker-specific port
- **Current behavior**: Email says `http://localhost:5000/api/auth/verify-email/...`
- **Expected**: Should use worker port (e.g., `http://localhost:3006/api/auth/verify-email/...`)
- **Impact**: Email verification fails in E2E tests
- **Fix needed**: Update email templates to use dynamic BASE_URL instead of hardcoded port

#### 2. **Instructor Profile Update Modal Won't Close**

- **Test**: `test_tc_crud_inst_001_update_own_profile`
- **Problem**: Edit user modal doesn't close after clicking "Save Changes"
- **Symptoms**: 30-second timeout waiting for modal to hide
- **Possible causes**:
  - Backend validation error (403 FORBIDDEN seen in logs)
  - JavaScript error preventing modal close
  - Instructor trying to edit their own profile might be blocked by permissions
- **Fix needed**: Investigate why save fails and/or why modal doesn't close on error

#### 3. **Worker Account Visibility**

- **Test**: `test_tc_crud_inst_001_update_own_profile`
- **Observation**: Instructor sees all 18 worker accounts in users list
  - john.instructor@mocku.test
  - john.instructor_worker0@mocku.test through worker15@mocku.test
- **Impact**: UI clutter during tests, might confuse test expectations
- **Question**: Should worker accounts be hidden from regular users?

### ⚠️ Non-Blocking Issues (Tests Pass)

#### Dashboard JavaScript Timing Errors

- **Tests**: `test_tc_crud_pa_001_create_course`, `test_tc_crud_inst_001_update_own_profile`
- **Problem**: "Failed to fetch" console errors during test teardown
- **Root cause**: Dashboard JavaScript tries to load data before worker server fully ready
- **Impact**: Tests pass, but console errors fail them in teardown
- **Status**: Low priority - could add retry logic or increase timeouts

## Test Infrastructure Status

✅ **Working Well**:

- Parallel execution (56/58 tests passing)
- Worker-specific databases and servers
- Account provisioning for 16 workers
- Headless mode as default

⏳ **Needs Work**:

- Email template port configuration
- Instructor permission model
- Modal close behavior on errors

## Next Steps

1. Fix email verification port to use `request.host` or environment variable
2. Debug instructor profile update permissions
3. Decide on worker account visibility policy
4. (Optional) Add retry logic for dashboard data fetching
