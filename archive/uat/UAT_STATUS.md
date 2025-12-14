# UAT E2E Test Suite Status

## Current State (October 15, 2025)

### ✅ Fixed Issues
1. **Database Seeding Bug**: Fixed `seed_db.py` program creation
   - Issue: Script was renaming `program_id` to `id` but database expects `program_id`
   - Fix: Removed unnecessary field renaming (lines 360, 344)
   - Result: Seeding now works correctly with 133 entities created

### 🎯 Implemented UAT Tests

#### UAT-001: Complete User Registration & Password Management Workflow
**File**: `tests/e2e/test_uat_001_registration_password.py`

**Status**: ⚠️ **NEEDS UPDATE FOR NEW EMAIL SYSTEM**

**Coverage**:
- ✅ New user registration
- ✅ Email verification (using Ethereal IMAP)
- ✅ Login with verified account
- ✅ Password reset request
- ✅ Password reset completion
- ✅ Password reset confirmation email
- ✅ Login with new password
- ✅ Security: Old password no longer works

**Issues**:
- Uses old Mailtrap-specific email utilities
- Needs update to use new Ethereal/Brevo email provider architecture
- Email verification logic references deprecated `MAILTRAP_INBOX_ID`

**Estimated Duration**: 3-4 minutes

### 📋 Planned UAT Tests (Not Yet Implemented)

Based on user stories in `planning/user_stories/`:

#### From `INSTRUCTOR_USER_STORIES.md`:
- UAT-002: Instructor Dashboard & Section Management
- UAT-003: Course Record Entry & Validation
- UAT-004: Bulk Import/Export Workflows

#### From `PROGRAM_ADMIN_USER_STORIES.md`:
- UAT-005: Program Admin Course Management
- UAT-006: Instructor Assignment & Permissions
- UAT-007: Program-Level Reporting

#### From `SITE_ADMIN_USER_STORIES.md`:
- UAT-008: Institution Management
- UAT-009: User Role Management
- UAT-010: System-Wide Reporting

### 🔧 Email System Integration

**Current Email Architecture**:
- **Brevo**: Production email sending (300/day free tier)
- **Ethereal**: E2E testing with IMAP verification
- **Email Whitelist**: Non-production safety (`EMAIL_WHITELIST` env var)

**E2E Email Utilities** (`tests/e2e/email_utils.py`):
- ✅ Supports Ethereal IMAP for email verification
- ⚠️ Still has legacy Mailtrap API code (can be removed)
- ✅ Environment-aware: Uses `ETHEREAL_USER`/`ETHEREAL_PASS`
- ✅ Provides `wait_for_email_via_imap()` for E2E tests

**Required Updates for UAT-001**:
1. Remove Mailtrap references from test file
2. Update email verification to use Ethereal IMAP exclusively
3. Verify email whitelist includes test email addresses
4. Test end-to-end with new email provider architecture

### 🗄️ Database Seeding

**Script**: `scripts/seed_db.py`

**Entities Created** (Full Seed):
- 3 Institutions (MockU, RCC, PTU)
- 10 Users (1 site admin, 3 institution admins, 2 program admins, 4 instructors)
- 8 Programs (CS, EE, GEN, LA, BUS, EXPL, ME, PRE)
- 15 Courses
- 5 Terms (Fall 2025, Spring 2026)
- 15 Sections
- 35 Course Learning Outcomes
- 2 Invitations
- 52 Course Offerings

**Test Accounts**:
```
Site Admin:
  Email: siteadmin@system.local
  Password: SiteAdmin123!

Institution Admins:
  MockU: sarah.admin@mocku.test / InstitutionAdmin123!
  RCC: mike.admin@riverside.edu / InstitutionAdmin123!
  PTU: admin@pactech.edu / InstitutionAdmin123!

Program Admins:
  MockU CS/EE: lisa.prog@mocku.test / TestUser123!
  RCC Liberal Arts: robert.prog@riverside.edu / TestUser123!

Instructors:
  MockU CS: john.instructor@mocku.test / TestUser123!
  MockU EE: jane.instructor@mocku.test / TestUser123!
  RCC: susan.instructor@riverside.edu / TestUser123!
  PTU ME: david.instructor@pactech.edu / TestUser123!
```

### 🚀 Running UAT Tests

**Command**: `./run_uat.sh`

**What it does**:
1. Restarts server on port 3001
2. Seeds E2E database with test data
3. Runs all E2E tests (including UAT tests)
4. Cleans up server after tests

**Current Test Results**:
- 57/58 E2E tests passing
- 1 test failing: `test_tc_crud_ia_005_invite_instructor` (email-related)
- UAT-001 not yet run (needs email system updates)

### 📝 Next Steps

1. **Update UAT-001 for new email system**:
   - Remove Mailtrap references
   - Use Ethereal IMAP exclusively
   - Verify with new email provider architecture

2. **Fix failing E2E test**:
   - `test_tc_crud_ia_005_invite_instructor` (email-related)
   - Likely needs same email system updates

3. **Implement remaining UAT tests**:
   - UAT-002 through UAT-010 based on user stories
   - Follow workflow-based approach (multiple features per test)
   - Aim for ~6 comprehensive test cases per user story

4. **Clean up email utilities**:
   - Remove legacy Mailtrap API code from `email_utils.py`
   - Simplify to Ethereal IMAP only

### 📚 Documentation

**UAT Guides**:
- `UAT_GUIDE.md`: General UAT testing guide
- `UAT_DATA_INTEGRITY_AND_ACCESS_CONTROL.md`: Data integrity test cases
- `UAT_IMPORT_EXPORT.md`: Import/export test cases

**User Stories**:
- `planning/user_stories/INSTRUCTOR_USER_STORIES.md`
- `planning/user_stories/PROGRAM_ADMIN_USER_STORIES.md`
- `planning/user_stories/SITE_ADMIN_USER_STORIES.md`

**Email System**:
- `planning/EMAIL_SYSTEM_V1_IMPLEMENTATION.md`: Email system design
- `EMAIL_SIMPLIFICATION_SUMMARY.md`: Recent email architecture changes

