# Complete Email Flow Map - LoopCloser

## 📧 All Email Touchpoints in the Application

This document maps every email sent by the application, organized by user journey.

---

## 🆕 New User Self-Registration Flow

### Flow Diagram

```
User fills registration form → Submit
                              ↓
                    Account created (unverified)
                              ↓
                    📧 VERIFICATION EMAIL sent
                              ↓
                    User clicks verification link
                              ↓
                    Account verified
                              ↓
                    📧 WELCOME EMAIL sent (optional)
```

### Emails Sent

1. **Verification Email** (`send_verification_email`)
   - **Trigger**: User submits registration form
   - **Recipient**: New user's email address
   - **Subject**: "Verify your LoopCloser account"
   - **Content**: Welcome message, verification link with token
   - **Template**: HTML + plain text versions
   - **Action Link**: `{BASE_URL}/verify?token={token}`
   - **Test File**: `test_email_flows_registration.py::TestNewUserRegistrationFlow`

2. **Welcome Email** (`send_welcome_email`) - _Optional/Future_
   - **Trigger**: User verifies account
   - **Recipient**: Newly verified user
   - **Subject**: "Welcome to LoopCloser!"
   - **Content**: Getting started guide, key features, support links
   - **Template**: HTML + plain text versions
   - **Test File**: `test_email_flows_registration.py::TestWelcomeEmailFlow`

---

## 🔐 Password Reset Flow

### Flow Diagram

```
User clicks "Forgot Password" → Enter email → Submit
                                              ↓
                                    📧 RESET EMAIL sent
                                              ↓
                            User clicks reset link
                                              ↓
                            User enters new password → Submit
                                              ↓
                                    Password updated
                                              ↓
                            📧 CONFIRMATION EMAIL sent
```

### Emails Sent

3. **Password Reset Email** (`send_password_reset_email`)
   - **Trigger**: User requests password reset
   - **Recipient**: User's registered email
   - **Subject**: "Reset your LoopCloser password"
   - **Content**: Reset instructions, reset link with token
   - **Template**: HTML + plain text versions
   - **Action Link**: `{BASE_URL}/reset-password?token={token}`
   - **Security**: Token expires after 1 hour
   - **Test File**: `test_email_flows_registration.py::TestPasswordResetFlow`

4. **Password Reset Confirmation Email** (`send_password_reset_confirmation_email`)
   - **Trigger**: User successfully resets password
   - **Recipient**: User's email
   - **Subject**: "Password Reset Successful"
   - **Content**: Confirmation that password was changed, security tips
   - **Template**: HTML + plain text versions
   - **Test File**: `test_email_flows_registration.py::TestPasswordResetFlow`

---

## 📬 User Invitation Flow

### Flow Diagram

```
Admin navigates to user management → Click "Invite User"
                                              ↓
                    Fill invitation form (email, role, message)
                                              ↓
                                    Submit invitation
                                              ↓
                                    📧 INVITATION EMAIL sent
                                              ↓
                            Recipient clicks invitation link
                                              ↓
                    Registration page (pre-filled email, role)
                                              ↓
                            User completes registration
                                              ↓
                    📧 VERIFICATION EMAIL sent (or auto-verified)
```

### Emails Sent

5. **Invitation Email** (`send_invitation_email`)
   - **Trigger**: Admin invites user to join institution/program
   - **Recipient**: Invitee's email address
   - **Subject**: "You're invited to join {institution_name} on LoopCloser"
   - **Content**:
     - Inviter's name and role
     - Institution/program name
     - Role being invited to
     - Personal message (optional)
     - Invitation acceptance link
   - **Template**: HTML + plain text versions
   - **Action Link**: `{BASE_URL}/accept-invitation?token={token}`
   - **Security**: Token expires after 7 days
   - **Variants**:
     - Institution Admin → Instructor
     - Institution Admin → Program Admin
     - Program Admin → Instructor
   - **Test File**: `test_email_flows_registration.py::TestInvitationFlow`

---

## 📋 Admin Instructor Reminder Flow (Phase 4 - Not Yet Implemented)

### Flow Diagram

```
Admin navigates to course management → View pending submissions
                                              ↓
                    Select instructor(s) needing reminder
                                              ↓
                            Click "Send Reminder"
                                              ↓
                    Add optional personal message
                                              ↓
                                    Send reminder
                                              ↓
                            📧 REMINDER EMAIL sent
                                              ↓
                    Instructor clicks link to submission page
                                              ↓
                            Instructor submits course data
```

### Emails Sent

6. **Instructor Reminder Email** (`send_instructor_reminder_email`) - _Phase 4_
   - **Trigger**: Admin sends reminder to instructor to submit course data
   - **Recipient**: Instructor(s) who haven't submitted data
   - **Subject**: "Reminder: Please submit your course data for {term}"
   - **Content**:
     - Instructor's name
     - Admin sender's name and role
     - Term/semester context
     - Personal message (optional)
     - List of missing courses (optional)
     - Deadline (optional)
     - Direct link to course submission page
   - **Template**: HTML + plain text versions (to be created)
   - **Action Link**: `{BASE_URL}/courses/submit?instructor_id={id}&term={term}`
   - **Variants**:
     - Single recipient
     - Bulk send to multiple recipients
   - **Rate Limiting**: Cannot send duplicate reminder within 24 hours
   - **Permissions**:
     - Institution Admin: Can remind any instructor in institution
     - Program Admin: Can remind instructors in their programs only
   - **Test File**: `test_email_flows_admin_reminders.py`

---

## 📊 Email Flow Summary Table

| #   | Email Type          | EmailService Method                      | Trigger                 | Recipients      | Status                                |
| --- | ------------------- | ---------------------------------------- | ----------------------- | --------------- | ------------------------------------- |
| 1   | Verification        | `send_verification_email`                | User registers          | New users       | ✅ Implemented                        |
| 2   | Welcome             | `send_welcome_email`                     | User verifies account   | Verified users  | ⚠️ Method exists, may need activation |
| 3   | Password Reset      | `send_password_reset_email`              | User requests reset     | Existing users  | ✅ Implemented                        |
| 4   | Reset Confirmation  | `send_password_reset_confirmation_email` | User resets password    | Users who reset | ✅ Implemented                        |
| 5   | Invitation          | `send_invitation_email`                  | Admin invites user      | Invitees        | ✅ Implemented                        |
| 6   | Instructor Reminder | `send_instructor_reminder_email`         | Admin pushes instructor | Instructors     | ⏳ Phase 4 (not yet implemented)      |

---

## 🎯 User Personas & Email Touchpoints

### New Instructor (Self-Registration)

**Journey**: Discovers app → Registers → Verifies → Uses app
**Emails Remockuved**:

1. Verification email (immediately after registration)
2. Welcome email (optional, after verification)

### Invited Instructor

**Journey**: Remockuves invitation → Accepts → Registers → Verifies → Uses app
**Emails Remockuved**:

1. Invitation email (sent by admin)
2. Verification email (after accepting invitation) OR auto-verified

### Existing Instructor (Forgot Password)

**Journey**: Forgets password → Requests reset → Resets password → Logs in
**Emails Remockuved**:

1. Password reset email (immediately after request)
2. Password reset confirmation (after successful reset)

### Instructor (Needs Reminder)

**Journey**: Hasn't submitted data → Admin sends reminder → Submits data
**Emails Remockuved**:

1. Instructor reminder email (Phase 4, sent by admin)

### Program Admin

**Journey**: Invited by institution admin → Accepts → Manages program
**Emails Remockuved**:

1. Invitation email (sent by institution admin)
2. Verification email (after accepting) OR auto-verified

### Institution Admin

**Journey**: First user for institution → Self-registers → Creates institution
**Emails Remockuved**:

1. Verification email (after registration)
2. Welcome email (optional)

---

## 🔒 Email Security & Safety Measures

### Protected Domains

Never send emails to these domains in non-production:

- `mocku.test`
- `coastaledu.org`
- `coastal.edu`
- `coastalcarolina.edu`

### Test Account Restrictions (Non-Production)

**Allowed recipients only**:

- `@mailtrap.io` (sandbox testing)
- `lassie.tests@gmail.com` (our test accounts)
- Domains containing "test", "example", or "localhost"

**Blocked recipients**:

- Any other real domain to prevent accidental sends

### Rate Limiting (Planned for Phase 4)

- Instructor reminders: Max 1 per instructor per 24 hours
- Prevents admin spam

---

## 📝 Email Template Requirements

### All Emails Must Include

1. **Personalized greeting** (recipient's name)
2. **Clear purpose** (why they're remockuving this email)
3. **Call-to-action** (what they should do)
4. **Branding** (LoopCloser identity)
5. **Support contact** (help email/link)
6. **HTML + plain text versions** (accessibility)

### Email Template Structure

```
[Logo/Header]

Hi {user_name},

[Purpose paragraph]

[Main content with context]

[Call-to-action button/link]

[Optional: Secondary information]

[Footer with support contact]
```

---

## 🧪 Testing Strategy

### Unit Tests

- Mock SMTP, test email content generation
- Test token generation and embedding
- Test template rendering
- **Status**: ✅ Complete (49 tests passing)

### Integration Tests

- Test with Mailtrap sandbox
- Verify email delivery
- Verify email formatting
- **Status**: ⏳ Waiting for Mailtrap account setup

### E2E Tests

- Full user journeys
- Click links in emails
- Verify end-to-end flows
- **Status**: 📝 Pseudo-code complete, implementation Phase 3

---

## 🚀 Implementation Phases

### Phase 1: Provider Infrastructure ✅ COMPLETE

- Email provider pattern
- Console, Gmail, Mailtrap providers
- Safety measures

### Phase 2: Test Setup ⏳ IN PROGRESS

- Mailtrap account creation
- Bella's Gmail setup (optional)
- Test script verification

### Phase 3: E2E Infrastructure (Next)

- Mailtrap API integration
- Email verification helpers
- E2E test implementation

### Phase 4: Instructor Reminders (Future)

- New email template
- API endpoint
- UI for admin
- Rate limiting
- Tracking

---

## 📚 Related Documentation

- **Implementation Plan**: `planning/EMAIL_SYSTEM_V1_IMPLEMENTATION.md`
- **E2E Test Designs**:
  - `tests/e2e/test_email_flows_registration.py`
  - `tests/e2e/test_email_flows_admin_reminders.py`
- **Unit Tests**:
  - `tests/unit/test_email_service.py`
  - `tests/unit/test_mailtrap_provider.py`
  - `tests/unit/test_console_provider.py`
  - `tests/unit/test_gmail_provider.py`
- **Integration Tests**:
  - `tests/integration/test_gmail_third_party.py`
- **Status Tracking**: `STATUS.md`

---

**Last Updated**: October 14, 2025
**Status**: Phase 2 (Test Infrastructure) - All code complete, waiting for account setup
