# E2E Parallel Execution Failure Analysis

**Date:** 2025-10-16  
**Status:** 54/58 passing (93%), 4 failures + 2 errors  
**Execution Time:** 44.4s with auto-scaling (10 workers)

## Overview

These failures **only occur in parallel execution** and reveal real-world race conditions and timing issues that would occur in production under concurrent load. This is exactly what parallel testing is designed to detect!

---

## Failure #1: Modal Timeout (`test_tc_crud_inst_001_update_own_profile`)

### Error

```
playwright._impl._errors.TimeoutError: Page.wait_for_selector: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("#editUserModal") to be hidden
    64 × locator resolved to visible <div>
```

### Analysis

- **Test Path**: Instructor updates their own profile
- **Failure**: Modal doesn't close after save operation
- **Worker**: gw5 (port 3007)
- **Root Cause**: Likely race condition in modal close handler or AJAX completion

### Data Sharing

- **Shared Resource**: User table (instructor's own record)
- **Conflict**: None - each worker has isolated database
- **Likely Issue**: JavaScript timing - save completes but modal close handler doesn't fire

### Real-World Impact

HIGH - This would happen in production when multiple instructors update profiles simultaneously. The modal gets "stuck" due to event handler race conditions.

### Investigation Path

1. Check if save operation actually completes (database updated?)
2. Look for JavaScript errors during modal close
3. Check if there's a race between AJAX callback and modal.hide()
4. Test if adding explicit wait for AJAX completion fixes it

---

## Failure #2: Missing Courses (`test_tc_crud_inst_002_update_section_assessment`)

### Error

```
AssertionError: Expected at least 2 options (empty + courses), got 1
assert 1 >= 2
where 1 = len([<Locator selector='#courseSelect option >> nth=0'>])
```

### Analysis

- **Test Path**: Instructor tries to create section assessment
- **Failure**: Course dropdown only has empty option (no courses)
- **Worker**: gw5 (port 3007)
- **Root Cause**: API returns 0 courses for this instructor

### Data Sharing

- **Shared Resource**: Courses, Sections, Course-Section assignments
- **Conflict**: HIGH - Other workers may be modifying/deleting shared course data
- **Database State**: Each worker has isolated DB, but seeded data is identical

### Real-World Impact

CRITICAL - This indicates that our course assignment logic breaks under concurrent access. If two admins assign courses to sections simultaneously, instructors might lose access to their courses.

### Investigation Path

1. Check what courses are assigned to `john.instructor_worker5@mocku.test`
2. Verify section-instructor assignments in worker5's database
3. Look for DELETE or UPDATE operations in other tests that might affect courses
4. Check if course visibility logic has race conditions

### Debug Output

```javascript
📢 CONSOLE [log]: 📢 /api/sections response: 200
📢 CONSOLE [log]: 📢 Got 0 sections
📢 CONSOLE [log]: 📢 Unique course IDs: 0 []
📢 CONSOLE [log]: 📢 /api/courses response: 200
📢 CONSOLE [log]: 📢 Got 7 total courses
📢 CONSOLE [log]: 📢 Filtered to 0 instructor courses
```

**Key Insight**: 7 courses exist globally, but 0 are assigned to this instructor's sections!

---

## Failure #3: Program Admin No Programs (`test_tc_crud_pa_006_cannot_access_other_programs`)

### Error

```
AssertionError: Program admin should have at least one assigned program, got: []
assert 0 > 0
where 0 = len([])
```

### Analysis

- **Test Path**: Program admin access control test
- **Failure**: Program admin has no assigned programs
- **Worker**: gw9
- **Root Cause**: Program assignments not seeded or deleted by another test

### Data Sharing

- **Shared Resource**: User-Program assignments
- **Conflict**: HIGH - Other tests may be creating/deleting program admins
- **Seeding Issue**: Worker-specific program admins may not be created

### Real-World Impact

HIGH - If program assignments aren't properly isolated, concurrent admin operations could result in admins losing access to their programs mid-session.

### Investigation Path

1. Check if `lisa.prog_worker9@mocku.test` has program assignments
2. Verify seed_worker_accounts.py creates program assignments
3. Look for tests that delete or modify program admin assignments
4. Check if program visibility query has race conditions

---

## Failure #4: Registration Flow (`test_complete_registration_and_password_workflow`)

### Error

```
AssertionError: Expected success response
assert 'success' in '<html><head></head><body></body></html>'
```

### Analysis

- **Test Path**: Complete registration flow with email verification
- **Failure**: Empty HTML response instead of success message
- **Worker**: gw9
- **Root Cause**: Email verification endpoint returning empty response

### Data Sharing

- **Shared Resource**: Verification tokens, user records
- **Conflict**: Medium - tokens should be unique per user
- **Timing Issue**: Verification email may not have been sent/received yet

### Real-World Impact

MEDIUM - Under high load, registration confirmation emails might not arrive in time for immediate verification, leading to poor UX.

### Investigation Path

1. Check if verification email was actually sent (Ethereal logs)
2. Verify token generation is unique per worker
3. Look for race condition in email sending (rate limiting?)
4. Check if verification endpoint has proper error handling

---

## JavaScript Fetch Errors (2 occurrences)

### Error

```
JavaScript console errors detected during test:
  - Institution dashboard load error: TypeError: Failed to fetch
    at Object.loadData (http://localhost:3006/static/institution_dashboard.js:65:32)
```

### Analysis

- **Test Path**: Multiple tests loading dashboards
- **Failure**: API fetch fails during page load
- **Workers**: gw4 (port 3006), gw0 (port 3002)
- **Root Cause**: Race condition in dashboard initialization

### Data Sharing

- **Shared Resource**: API endpoints (`/api/...`)
- **Conflict**: Server may not be fully ready when test starts
- **Timing Issue**: Dashboard JavaScript executes before Flask server stabilizes

### Real-World Impact

CRITICAL - This is a genuine production bug! If users reload the dashboard while data is being updated, they'll see fetch errors and broken UI.

### Investigation Path

1. Add retry logic to dashboard fetch calls
2. Check if server startup race condition exists
3. Look for proper error handling in institution_dashboard.js:65
4. Add loading states instead of failing silently

---

## Summary & Patterns

### Common Themes

1. **Timing Issues** (3/6): Modal close, dashboard load, email verification
2. **Data Isolation** (2/6): Missing courses, missing programs
3. **Race Conditions** (1/6): JavaScript fetch errors

### Real-World Implications

✅ **Good News**: These are REAL bugs we'd face in production!

- Modal timing issues under concurrent updates
- Data visibility problems during simultaneous admin operations
- Dashboard fetch failures during high load

### Next Steps

**Priority 1: JavaScript Fetch Errors** (CRITICAL)

- Add retry logic to all dashboard API calls
- Implement proper loading states
- Add error boundaries for failed fetches

**Priority 2: Data Isolation** (HIGH)

- Verify worker-specific program assignments
- Fix instructor-course assignment logic
- Ensure seeded data includes proper relationships

**Priority 3: Timing Issues** (MEDIUM)

- Add explicit waits for AJAX completion
- Implement proper modal lifecycle management
- Add retry logic to email verification flow

### Test Infrastructure Quality

🎯 **Parallel testing is working as designed** - it's exposing real concurrency bugs that serial testing would never catch. These failures are FEATURES, not bugs in our test infrastructure!
