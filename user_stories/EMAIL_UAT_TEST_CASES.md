# Email System - UAT Test Cases

Comprehensive end-to-end workflow tests for all email functionality. Each test case exercises multiple features to minimize spin-up overhead.

---

## UAT-001: Complete User Registration & Password Management Workflow

**Test Objective:** Validate the entire authentication email lifecycle from registration through password reset.

**User Persona:** Jane Smith, new nursing instructor

### Workflow Steps:

1. **New User Registration**
   - Navigate to registration page
   - Fill form: jane.smith@test.com, password, first name, last name
   - Submit registration
   - Verify: "Check your email for verification link" message displayed
   - Check Mailtrap inbox for jane.smith@test.com
   - Verify email received within 30 seconds
   - Extract verification link from email body
   - Verify email subject: "Welcome! Please verify your email"
   - Verify email contains user's first name
   - Click verification link
   - Verify: Redirected to login page with "Email verified!" message
   - Attempt login with credentials
   - Verify: Successfully logged in, see dashboard

2. **Password Reset Request**
   - Log out
   - Click "Forgot Password"
   - Enter jane.smith@test.com
   - Submit reset request
   - Verify: "Check your email for reset instructions" message
   - Check Mailtrap inbox
   - Verify password reset email received
   - Extract reset link with token
   - Verify token is in link query params
   - Click reset link
   - Verify: Reset form displayed with email pre-filled

3. **Password Reset Completion**
   - Enter new password (twice)
   - Submit reset
   - Verify: "Password reset successful" message
   - Check Mailtrap inbox
   - Verify password reset confirmation email received
   - Verify email includes timestamp
   - Login with NEW password
   - Verify: Login successful
   - Attempt login with OLD password
   - Verify: Login fails with "Invalid credentials"

4. **Security: Expired Token Handling**
   - Log out
   - Request another password reset
   - Extract reset token from email
   - Wait for token expiration (or mock time)
   - Attempt to use expired token
   - Verify: Error message "Reset link has expired"
   - Verify: Link to request new reset shown

**Pass Criteria:**
- ✅ Verification email delivered and functional
- ✅ Password reset email delivered with valid token
- ✅ Confirmation email sent after password change
- ✅ Old password no longer works after reset
- ✅ Expired tokens are rejected
- ✅ All emails contain proper personalization

**Estimated Duration:** 3-4 minutes

---

## UAT-002: Admin Invitation & Multi-Role User Management

**Test Objective:** Validate admin ability to invite users and the complete invitation workflow.

**User Personas:**
- Dr. Sarah Williams, Institution Admin
- Prof. Michael Brown, invited as Instructor
- Dr. Jennifer Lee, invited as Program Admin

### Workflow Steps:

1. **Admin Invites Instructor**
   - Login as Dr. Williams (institution admin)
   - Navigate to user management
   - Click "Invite User"
   - Enter email: michael.brown@test.com
   - Select role: Instructor
   - Add personal message: "Welcome to MockU! Looking forward to working with you."
   - Select institution and program
   - Submit invitation
   - Verify: Success message "Invitation sent to michael.brown@test.com"
   - Check Mailtrap inbox for michael.brown@test.com
   - Verify invitation email received
   - Verify email contains personal message from admin
   - Verify email contains registration link with token
   - Extract invitation token from link

2. **Invited User Completes Registration**
   - Open invitation link (with token)
   - Verify: Registration form displayed
   - Verify: Email field pre-filled and disabled
   - Verify: Role displays as "Instructor"
   - Complete registration: first name, last name, password
   - Submit registration
   - Verify: Account created with "Instructor" role
   - Login as Michael Brown
   - Verify: Dashboard shows instructor view
   - Verify: Can see assigned courses

3. **Admin Invites Program Admin**
   - (Still logged in as Dr. Williams)
   - Invite Dr. Jennifer Lee as Program Admin
   - Check Mailtrap inbox for jennifer.lee@test.com
   - Verify invitation email received
   - Extract registration link
   - Complete registration for Dr. Lee
   - Login as Dr. Lee
   - Verify: Dashboard shows program admin view
   - Verify: Can see "Send Reminders" button (admin privilege)

4. **Permission Boundary: Invitation Scope**
   - Login as Dr. Lee (program admin - Computer Science)
   - Attempt to invite instructor to different program (Nursing)
   - Verify: Only Computer Science program available in dropdown
   - OR if bypassed: Verify API returns 403 Forbidden

5. **Expired Invitation Handling**
   - (As Dr. Williams) Invite another user
   - Mock invitation expiration (or wait 7 days if necessary)
   - Attempt to use expired invitation link
   - Verify: Error message "This invitation has expired"
   - Verify: Contact admin message shown

**Pass Criteria:**
- ✅ Invitation emails delivered with correct content
- ✅ Personal messages from admin appear in emails
- ✅ Invited users complete registration successfully
- ✅ Role assignments work correctly
- ✅ Expired invitations are rejected
- ✅ Permission boundaries enforced

**Estimated Duration:** 4-5 minutes

---

## UAT-003: Bulk Instructor Reminders - Happy Path with Progress Tracking

**Test Objective:** Validate bulk reminder system with real-time progress tracking and successful delivery to multiple instructors.

**User Personas:**
- Dr. Sarah Williams, Program Admin (sender)
- 5 Instructors in Computer Science program (recipients)

### Workflow Steps:

1. **Setup: Seed Test Instructors**
   - Database contains 5 instructors in CS program:
     - Prof. Alice Johnson (alice.j@test.com)
     - Prof. Bob Martinez (bob.m@test.com)
     - Prof. Carol Davis (carol.d@test.com)
     - Prof. David Wilson (david.w@test.com)
     - Prof. Emma Thompson (emma.t@test.com)
   - None have submitted course data for Fall 2025

2. **Admin Opens Reminder Modal**
   - Login as Dr. Williams
   - Navigate to dashboard
   - Click "Send Reminders" button
   - Verify: Modal opens with title "Send Instructor Reminders"
   - Verify: Instructor list loads within 2 seconds
   - Verify: All 5 instructors displayed with names and emails
   - Verify: Selected count shows "0"
   - Verify: "Send Reminders" button disabled

3. **Select Instructors and Compose Message**
   - Click "Select All" button
   - Verify: All checkboxes checked
   - Verify: Selected count shows "5"
   - Verify: "Send Reminders" button enabled
   - Uncheck Bob Martinez
   - Verify: Selected count shows "4"
   - Re-check Bob Martinez
   - Enter Term: "Fall 2025"
   - Enter Deadline: "2025-12-15"
   - Enter Personal Message: "Please submit your course data by the deadline. Contact me if you need help!"
   - Verify: Character count updates (displays X/500)
   - Verify: No character limit exceeded

4. **Initiate Bulk Send**
   - Click "Send Reminders"
   - Verify: UI switches to progress view immediately
   - Verify: Progress bar displays at 0%
   - Verify: Counts show - Sent: 0, Failed: 0, Pending: 5
   - Verify: "Close" button is disabled during sending

5. **Monitor Real-Time Progress**
   - Watch progress bar animate
   - Verify: Status messages appear with timestamps:
     - "[HH:MM:SS] Job started: {job_id}"
     - "[HH:MM:SS] Sending to 5 instructor(s)"
     - "[HH:MM:SS] Sent 1/5 reminders..."
     - "[HH:MM:SS] Sent 2/5 reminders..."
     - ... continue through 5/5
   - Verify: Progress bar updates (approximately 20% per email)
   - Verify: Sent count increments: 1, 2, 3, 4, 5
   - Verify: Pending count decrements: 4, 3, 2, 1, 0
   - Verify: Failed count remains at 0
   - Verify: Messages auto-scroll to bottom

6. **Completion**
   - Verify: Progress bar reaches 100%
   - Verify: Progress bar turns green
   - Verify: Completion message displays: "Complete! Successfully sent 5 reminder(s)."
   - Verify: Final count shows - Sent: 5, Failed: 0, Pending: 0
   - Verify: "Close" button becomes enabled
   - Verify: No failed recipients section displayed

7. **Verify Email Delivery**
   - Check Mailtrap inboxes for all 5 instructors
   - For EACH email, verify:
     - Subject: "Reminder: Please submit your course data for Fall 2025"
     - Recipient name in greeting: "Dear Prof. [Name]"
     - Term mentioned: "Fall 2025"
     - Deadline mentioned: "2025-12-15"
     - Personal message included
     - Link to dashboard included
     - Professional formatting (HTML)
   - Verify emails sent with ~10 second spacing (rate limiting)

8. **Job Status Persistence**
   - Close modal
   - Call API: GET /api/bulk-email/recent-jobs
   - Verify: Job appears in recent jobs list
   - Verify: Job status = "completed"
   - Verify: Recipient count = 5
   - Verify: Emails sent = 5
   - Verify: Emails failed = 0

**Pass Criteria:**
- ✅ Modal loads instructor list correctly
- ✅ Select all/deselect functionality works
- ✅ Progress bar animates smoothly
- ✅ Real-time counts update correctly
- ✅ Status messages appear with timestamps
- ✅ All 5 emails delivered successfully
- ✅ Email content personalized correctly
- ✅ Rate limiting observed (10s between emails)
- ✅ Job completion status accurate
- ✅ Job persisted in database

**Estimated Duration:** 5-6 minutes (includes 50s for rate-limited sending)

---

## UAT-004: Bulk Reminders - Failure Handling, Retry, and Error Recovery

**Test Objective:** Validate system behavior when email sending fails, including retry logic, error reporting, and partial success handling.

**User Personas:**
- Dr. Sarah Williams, Program Admin
- 5 Instructors (2 with invalid emails)

### Workflow Steps:

1. **Setup: Mix of Valid and Invalid Instructors**
   - Database contains 5 instructors:
     - Prof. Alice Johnson (alice.j@test.com) - VALID
     - Prof. Bad Email (invalid-email-format) - INVALID FORMAT
     - Prof. Carol Davis (carol.d@test.com) - VALID
     - Prof. Nonexistent (deleted.user@test.com) - DELETED/NOT IN DB
     - Prof. Emma Thompson (emma.t@test.com) - VALID

2. **Send Bulk Reminders**
   - Login as Dr. Williams
   - Open reminder modal
   - Select all 5 instructors (including invalid ones)
   - Add message: "Please submit your data"
   - Click "Send Reminders"
   - Switch to progress view

3. **Monitor Mixed Success/Failure**
   - Verify: Status messages show attempts:
     - "[HH:MM:SS] Job started"
     - "[HH:MM:SS] Sent 1/5 reminders..." (Alice succeeds)
     - "[HH:MM:SS] Failed to send to invalid-email-format: Invalid email address"
     - "[HH:MM:SS] Sent 2/5 reminders..." (Carol succeeds)
     - "[HH:MM:SS] Failed to send to deleted.user@test.com: Instructor not found"
     - "[HH:MM:SS] Sent 3/5 reminders..." (Emma succeeds)
   - Verify: Progress bar continues despite failures
   - Verify: Counts update:
     - Final: Sent: 3, Failed: 2, Pending: 0

4. **Retry Logic Observation**
   - (For simulated rate limit failure)
   - Mock email provider to return 429 Too Many Requests on 2nd email
   - Verify: Status log shows:
     - "[HH:MM:SS] Rate limit hit, retrying in 5 seconds..."
     - "[HH:MM:SS] Retry attempt 1 of 3"
     - "[HH:MM:SS] Sent 2/5 reminders..." (success after retry)
   - Verify: System uses exponential backoff (5s, 10s, 20s)

5. **Failed Recipients Display**
   - After completion, verify: "Failed Recipients" section appears
   - Verify section shows:
     - "Prof. Bad Email (invalid-email-format): Invalid email address"
     - "Prof. Nonexistent (deleted.user@test.com): Instructor not found"
   - Verify: Failed count displayed in red badge
   - Verify: Each failure shows error reason

6. **Partial Success Completion**
   - Verify: Completion message shows partial success
   - Message: "Complete! Successfully sent 3 reminder(s). 2 email(s) failed to send."
   - Verify: Progress bar yellow/orange (not green - indicates warnings)
   - Verify: Close button enabled

7. **Verify Successful Emails Only**
   - Check Mailtrap inboxes
   - Verify: Alice, Carol, Emma received emails
   - Verify: Invalid/deleted users did NOT receive emails
   - Verify: Email content correct for successful sends

8. **Job History Reflects Failures**
   - Call API: GET /api/bulk-email/recent-jobs
   - Verify: Job shows:
     - Status: "completed" (not "failed" - partial success)
     - Recipient count: 5
     - Emails sent: 3
     - Emails failed: 2
     - Failed recipients array contains 2 entries with errors

9. **Admin Can Review Failures**
   - Call API: GET /api/bulk-email/job-status/{job_id}
   - Verify: Response includes:
     - `failed_recipients` array
     - Each failed recipient has: email, name, error, attempts
   - Verify: Failed recipients show proper error messages

**Pass Criteria:**
- ✅ System gracefully handles invalid emails
- ✅ Failed emails don't stop job execution
- ✅ Retry logic works with exponential backoff
- ✅ Failed recipients section displays correctly
- ✅ Partial success reported accurately
- ✅ Only valid emails receive reminders
- ✅ Job history shows failure details
- ✅ Error messages are specific and actionable

**Estimated Duration:** 3-4 minutes

---

## UAT-005: Permission Boundaries & Cross-Tenant Isolation

**Test Objective:** Validate that admins can only send reminders within their permission scope and cannot access other admins' data.

**User Personas:**
- Dr. Sarah Williams, Program Admin (Computer Science)
- Dr. Robert Chen, Program Admin (Nursing)
- Ms. Lisa Anderson, Institution Admin (all programs)

### Workflow Steps:

1. **Setup: Multi-Program Environment**
   - Institution: California Engineering Institute
   - Programs:
     - Computer Science (3 instructors)
     - Nursing (3 instructors)
   - Dr. Williams manages Computer Science
   - Dr. Chen manages Nursing
   - Ms. Anderson manages entire institution

2. **Program Admin Sees Only Their Instructors**
   - Login as Dr. Williams (CS Program Admin)
   - Open reminder modal
   - Verify: Instructor list shows ONLY CS instructors:
     - Prof. Alice Johnson (CS)
     - Prof. Bob Martinez (CS)
     - Prof. Carol Davis (CS)
   - Verify: Does NOT show Nursing instructors:
     - Prof. David Lee (Nursing) - NOT VISIBLE
     - Prof. Emma Garcia (Nursing) - NOT VISIBLE
     - Prof. Frank Miller (Nursing) - NOT VISIBLE
   - Select all CS instructors
   - Send bulk reminder
   - Verify: Job created successfully
   - Note job_id for later: `job_1`

3. **Verify Email Scoping**
   - Check Mailtrap inboxes
   - Verify: Only CS instructors received emails
   - Verify: Nursing instructors did NOT receive emails

4. **Cross-Program Admin Cannot View Job**
   - Logout
   - Login as Dr. Chen (Nursing Program Admin)
   - Call API: GET /api/bulk-email/job-status/job_1 (Dr. Williams' job)
   - Verify: Response status 403 Forbidden
   - Verify: Error message: "You do not have permission to view this job"
   - Verify: Dr. Chen cannot see Dr. Williams' job in recent jobs list

5. **Cross-Program Admin Cannot Send to Other Programs**
   - (Still as Dr. Chen)
   - Open reminder modal
   - Verify: Shows ONLY Nursing instructors (not CS)
   - Attempt to manually call API with CS instructor IDs
   - POST /api/bulk-email/send-instructor-reminders
   - Body: { "instructor_ids": ["cs-instructor-1", "cs-instructor-2"] }
   - Verify: Response status 403 Forbidden or 400 Bad Request
   - Verify: No emails sent to CS instructors
   - Verify: Error logged in application logs

6. **Institution Admin Has Full Access**
   - Logout
   - Login as Ms. Anderson (Institution Admin)
   - Open reminder modal
   - Verify: Shows instructors from ALL programs:
     - All CS instructors (3)
     - All Nursing instructors (3)
     - Total: 6 instructors
   - Select instructors from BOTH programs
   - Send bulk reminder
   - Verify: Emails sent to both CS and Nursing instructors
   - Note job_id: `job_2`

7. **Institution Admin Can View All Jobs**
   - Call API: GET /api/bulk-email/job-status/job_1 (Dr. Williams' job)
   - Verify: Response status 200 OK
   - Verify: Job details returned (institution admin can see all)
   - Call API: GET /api/bulk-email/recent-jobs
   - Verify: Response includes jobs from both Dr. Williams and Dr. Chen

8. **Security: API Endpoint Authorization**
   - Logout (no session)
   - Attempt API call: GET /api/bulk-email/recent-jobs
   - Verify: Response status 401 Unauthorized
   - Verify: Error: "Authentication required"
   - Attempt API call: POST /api/bulk-email/send-instructor-reminders
   - Verify: Response status 401 Unauthorized

**Pass Criteria:**
- ✅ Program admins see only their program's instructors
- ✅ Cross-program job access blocked (403)
- ✅ Cross-program email sending blocked
- ✅ Institution admins have full access
- ✅ Unauthenticated requests rejected (401)
- ✅ Permission boundaries enforced at API level
- ✅ No data leakage between programs

**Estimated Duration:** 4-5 minutes

---

## UAT-006: Edge Cases, Validation, and System Resilience

**Test Objective:** Validate system behavior under edge cases, invalid inputs, and boundary conditions.

**User Personas:**
- Dr. Sarah Williams, Program Admin
- Test instructors with various edge case scenarios

### Workflow Steps:

1. **Empty Recipient List Validation**
   - Login as Dr. Williams
   - Open reminder modal
   - Verify: "Send Reminders" button is disabled when count = 0
   - Attempt to enable via browser dev tools (bypass UI)
   - Call API directly with empty array: POST /api/bulk-email/send-instructor-reminders
   - Body: { "instructor_ids": [] }
   - Verify: Response status 400 Bad Request
   - Verify: Error message: "Missing or invalid 'instructor_ids' in request body"

2. **Invalid Request Body Handling**
   - Call API with missing JSON body
   - POST /api/bulk-email/send-instructor-reminders (empty body)
   - Verify: Response status 400 Bad Request
   - Verify: Error message: "Request body must be JSON"
   - Call API with malformed JSON
   - Body: `{ "instructor_ids": "not-an-array" }`
   - Verify: Response status 400 Bad Request

3. **Long Personal Message Handling**
   - Open reminder modal
   - Select 1 instructor
   - Enter personal message > 500 characters
   - Verify: Character count shows "500/500"
   - Verify: Text area prevents further input OR truncates
   - Verify: Error message if limit exceeded
   - Submit with exactly 500 characters
   - Verify: Submission succeeds

4. **Special Characters in Message**
   - Enter message with special characters:
     - "Hello! <script>alert('test')</script> Please submit data by 12/15/2025. Contact me @ sarah@mocku.test or call (555) 123-4567."
   - Submit reminder
   - Verify: Email sent successfully
   - Check email content
   - Verify: Special characters properly escaped (no XSS)
   - Verify: HTML tags displayed as text (not executed)
   - Verify: Email/phone number formatted correctly

5. **Missing Optional Fields**
   - Open reminder modal
   - Select instructors
   - Leave Term, Deadline, Personal Message ALL blank
   - Submit reminder
   - Verify: Job created successfully (optional fields are truly optional)
   - Check email content
   - Verify: Email uses generic text where fields blank:
     - "for the upcoming term" (no specific term)
     - "by the deadline" (no specific date)
     - No personal message section

6. **Single Instructor Selection**
   - Open reminder modal
   - Select exactly 1 instructor
   - Send reminder
   - Verify: Job created (minimum 1 recipient allowed)
   - Verify: Progress shows 1/1
   - Verify: Email delivered successfully

7. **Maximum Instructor Selection**
   - Seed database with 50+ instructors
   - Select all instructors (50+)
   - Verify: No UI errors
   - Verify: Modal remains responsive
   - Send bulk reminder
   - Verify: Job created successfully
   - Verify: Progress tracking works with large numbers
   - Monitor: System handles rate limiting properly
   - (Optionally cancel job after 5-10 emails to avoid long test)

8. **Concurrent Job Handling**
   - Start bulk reminder job (Job A - 10 instructors)
   - Immediately open modal again (without closing)
   - Start another bulk reminder job (Job B - 5 instructors)
   - Verify: Both jobs run independently
   - Verify: Each job has unique job_id
   - Verify: Progress tracking doesn't mix jobs
   - Verify: Both jobs complete successfully
   - Call API: GET /api/bulk-email/recent-jobs
   - Verify: Both jobs appear in history

9. **System Behavior During Email Provider Outage**
   - Mock email provider to return 500 Internal Server Error
   - Send bulk reminder
   - Verify: System retries with exponential backoff
   - Verify: After max retries (3), marks as failed
   - Verify: Status messages show retry attempts
   - Verify: Job marked as "completed" with failures
   - Verify: Error message: "Email service unavailable"

10. **Modal State Persistence During Sending**
    - Start bulk reminder (10 instructors)
    - While sending, attempt to:
      - Click outside modal (verify: modal doesn't close)
      - Press ESC key (verify: modal doesn't close)
      - Click browser back button (verify: stays on page)
    - Verify: Close button remains disabled until completion
    - After completion, verify: Close button enabled
    - Click Close
    - Verify: Modal closes properly
    - Verify: Re-opening modal shows fresh state (no leftover data)

11. **Search and Filter Functionality**
    - Open reminder modal with 20+ instructors
    - Type in search box: "johnson"
    - Verify: Instructor list filters to matching names
    - Verify: Selected count only counts visible instructors
    - Clear search
    - Verify: All instructors reappear
    - Search by email: "alice"
    - Verify: Filters by email address too

**Pass Criteria:**
- ✅ Empty recipient list rejected
- ✅ Invalid request bodies handled gracefully
- ✅ Character limits enforced or handled
- ✅ Special characters escaped properly (no XSS)
- ✅ Optional fields truly optional
- ✅ Single instructor minimum works
- ✅ Large instructor batches handled
- ✅ Concurrent jobs don't interfere
- ✅ Email provider failures handled with retry
- ✅ Modal state managed correctly during sending
- ✅ Search/filter works correctly

**Estimated Duration:** 5-7 minutes

---

## 📊 Test Summary

### Total Test Cases: 6

1. **UAT-001**: Complete Registration & Password Management (3-4 min)
2. **UAT-002**: Admin Invitation & Multi-Role Management (4-5 min)
3. **UAT-003**: Bulk Reminders Happy Path (5-6 min)
4. **UAT-004**: Failure Handling & Retry Logic (3-4 min)
5. **UAT-005**: Permission Boundaries & Isolation (4-5 min)
6. **UAT-006**: Edge Cases & System Resilience (5-7 min)

**Total Estimated Duration:** 24-31 minutes for complete email system validation

### Coverage Summary:

✅ **Registration Emails** (UAT-001)
✅ **Password Reset Emails** (UAT-001)
✅ **Invitation Emails** (UAT-002)
✅ **Bulk Reminder Emails** (UAT-003, UAT-004)
✅ **Progress Tracking** (UAT-003)
✅ **Error Handling** (UAT-004, UAT-006)
✅ **Permission Boundaries** (UAT-005)
✅ **Security** (UAT-005)
✅ **Edge Cases** (UAT-006)
✅ **Rate Limiting** (UAT-003, UAT-004)
✅ **Retry Logic** (UAT-004)
✅ **Email Content Validation** (All tests)

---

## 🔧 Test Infrastructure Requirements

### Before Running UAT Tests:

1. **Email Verification Setup**
   - Mailtrap API integration configured
   - Test inboxes created for each persona
   - Email polling utility functions
   - Token extraction utilities

2. **Test Data Management**
   - Database seed scripts for instructors, programs, institutions
   - Database reset/cleanup between test runs
   - Test user credentials management

3. **Browser Automation**
   - Playwright/Selenium configuration
   - Page object models for modals, forms
   - Wait strategies for async operations

4. **Environment Configuration**
   - Test environment with Mailtrap provider
   - Separate test database
   - Rate limiting configurable (may need faster for tests)
   - Mock time utilities for expiration testing

5. **Utilities**
   - Email inbox verification functions
   - Token/link extraction from email HTML
   - Progress polling helpers
   - Multi-user session management

---

## 🚀 Next Steps

1. **Review test cases** - Do these cover all critical workflows?
2. **Set up test infrastructure** - Playwright, Mailtrap API, test data
3. **Implement UAT-001** - Start with registration workflow
4. **Iterate** - Add remaining test cases incrementally
5. **CI/CD Integration** - Run UAT suite on PR branches

**Ready to start implementing!** 🎯


