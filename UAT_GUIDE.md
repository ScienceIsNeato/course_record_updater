# User Acceptance Testing (UAT) Guide
## Authentication System Manual Testing Protocol

### Document Information
- **Version**: 1.0
- **Date**: January 2025
- **Purpose**: Comprehensive manual testing guide for authentication system validation
- **Target Audience**: Product owners, stakeholders, QA team, development team

---

## 📋 Testing Overview

### Scope
This UAT guide covers the complete authentication and authorization system including:
- Multi-tenant user registration and onboarding
- 4-tier role-based access control (Site Admin → Institution Admin → Program Admin → Instructor)
- Session management and security features
- User invitation workflows
- Dashboard functionality and role-specific features

### Test Environment Requirements
- **Application Server**: Flask development server
- **Database**: Firestore (development instance)
- **Email**: Development email service (console output or SMTP)
- **Browser**: Modern web browser (Chrome, Firefox, Safari)

### Pre-Test Setup
1. **Seed the database with test data**:
   ```bash
   cd /path/to/course_record_updater
   source venv/bin/activate
   python seed_db.py --clear  # Clear existing data and create full test dataset
   ```

2. **Start the application server**:
   ```bash
   python app.py
   ```

3. **Test accounts created by seeding**:
   - **Site Admin**: `siteadmin@system.local` / `SiteAdmin123!`
   - **Institution Admins**: 
     - CEI: `sarah.admin@cei.edu` / `InstitutionAdmin123!`
     - RCC: `mike.admin@riverside.edu` / `InstitutionAdmin123!`
     - PTU: `admin@pactech.edu` / `InstitutionAdmin123!`
   - **Program Admins**: 
     - CEI: `lisa.prog@cei.edu` / `TestUser123!`
     - RCC: `robert.prog@riverside.edu` / `TestUser123!`
   - **Instructors**: 
     - CEI: `john.instructor@cei.edu` / `TestUser123!`
     - RCC: `susan.instructor@riverside.edu` / `TestUser123!`
     - PTU: `david.instructor@pactech.edu` / `TestUser123!`

4. **Note**: Some features show "coming soon" alerts - these are documented in each scenario

### Database Seeding Options
- `python seed_db.py` - Create full realistic dataset
- `python seed_db.py --minimal` - Create minimal dataset for basic testing
- `python seed_db.py --clear` - Clear existing data first
- `python seed_db.py --help` - Show all options

---

## 🎭 Test Personas

### Primary Test Users
- **Sarah (Site Admin)**: System administrator managing multiple institutions
- **Mike (Institution Admin)**: University administrator managing programs and faculty
- **Lisa (Program Admin)**: Department head managing courses and instructors
- **John (Instructor)**: Faculty member managing sections and assessments

---

## 🏢 SCENARIO 1: Site Administrator Journey

### Test Objective
Validate the highest-privilege user experience for system-wide management capabilities.

#### **TC-SA-001: Site Admin Login and Dashboard**
**Prerequisites**: Database seeded with test data

**Steps**:
1. Navigate to application login page
2. Login with site admin credentials: `siteadmin@system.local` / `SiteAdmin123!`
3. Verify redirect to Site Administrator Dashboard
4. Check that dashboard shows statistics for all institutions

**Expected Results**:
- ✅ **SHOULD WORK**: Login authentication and session creation
- ✅ **SHOULD WORK**: Dashboard displays with system-wide statistics (3 institutions, multiple users, programs, courses)
- ✅ **SHOULD WORK**: Navigation shows site admin menu items
- ✅ **SHOULD WORK**: Statistics load showing realistic numbers from seeded data

#### **TC-SA-002: Institution Management**
**Prerequisites**: Logged in as site admin

**Steps**:
1. View institutions list on dashboard
2. Click "New Institution" button
3. Attempt to create new institution
4. Try editing existing institution

**Expected Results**:
- ✅ **SHOULD WORK**: Institution list loads and displays
- ❌ **STUB**: "Create Institution feature coming soon!" alert
- ❌ **STUB**: "Edit Institution feature coming soon!" alert

#### **TC-SA-003: System User Management**
**Prerequisites**: Logged in as site admin

**Steps**:
1. View users list on dashboard
2. Click "Invite User" button
3. Navigate to Users menu item
4. Attempt user management operations

**Expected Results**:
- ✅ **SHOULD WORK**: Users list loads with role badges
- ❌ **STUB**: "Invite User feature coming soon!" alert
- ❌ **STUB**: "Users management feature coming soon!" alert

#### **TC-SA-004: System Overview and Reports**
**Prerequisites**: Logged in as site admin

**Steps**:
1. Check system statistics (institutions, users, programs, courses)
2. Click "Export Data" button
3. Click "View Logs" button
4. Navigate to System Settings

**Expected Results**:
- ✅ **SHOULD WORK**: Statistics load via API calls
- ❌ **STUB**: "Export System Data feature coming soon!" alert
- ❌ **STUB**: "System Logs feature coming soon!" alert
- ❌ **STUB**: "System Settings feature coming soon!" alert

---

## 🎓 SCENARIO 2: Institution Administrator Journey

### Test Objective
Validate institution-level management capabilities and user onboarding flow.

#### **TC-IA-001: Institution Admin Login and Dashboard**
**Prerequisites**: Database seeded with test data

**Steps**:
1. Navigate to application login page
2. Login with CEI admin credentials: `sarah.admin@cei.edu` / `InstitutionAdmin123!`
3. Verify redirect to Institution Administrator Dashboard
4. Check that dashboard shows only CEI institution data
5. Verify institution name and context displayed correctly

**Expected Results**:
- ✅ **SHOULD WORK**: Login authentication and session creation
- ✅ **SHOULD WORK**: Dashboard displays with institution-specific statistics
- ✅ **SHOULD WORK**: Shows CEI programs (Computer Science, Electrical Engineering, Unclassified)
- ✅ **SHOULD WORK**: Statistics filtered to CEI institution only
- ✅ **SHOULD WORK**: Institution context clearly displayed

#### **TC-IA-002: Program Management**
**Prerequisites**: Logged in as institution admin

**Steps**:
1. View programs list on dashboard
2. Click "New Program" button
3. Attempt to edit existing program
4. Navigate to Programs menu

**Expected Results**:
- ✅ **SHOULD WORK**: Programs list loads (including default "Unclassified" program)
- ❌ **STUB**: "Create Program feature coming soon!" alert
- ❌ **STUB**: "Edit Program feature coming soon!" alert
- ❌ **STUB**: "Programs management feature coming soon!" alert

#### **TC-IA-003: Faculty Invitation**
**Prerequisites**: Logged in as institution admin

**Steps**:
1. Click "Invite User" button on dashboard
2. Navigate to Users menu
3. Attempt to invite instructor
4. Attempt to invite program admin

**Expected Results**:
- ❌ **STUB**: "Invite User feature coming soon!" alert
- ❌ **STUB**: "Users management feature coming soon!" alert

#### **TC-IA-004: Data Import Operations**
**Prerequisites**: Logged in as institution admin

**Steps**:
1. Click "Import Excel" button
2. Click "Download Template" button
3. Click "Import History" button

**Expected Results**:
- ✅ **SHOULD WORK**: "Import Excel" redirects to main import page
- ❌ **STUB**: "Download Template feature coming soon!" alert
- ❌ **STUB**: "Import History feature coming soon!" alert

#### **TC-IA-005: Institution Reports**
**Prerequisites**: Logged in as institution admin

**Steps**:
1. Click report buttons (Enrollment, Course, Faculty)
2. Navigate to Reports menu

**Expected Results**:
- ❌ **STUB**: All report buttons show "feature coming soon!" alerts
- ❌ **STUB**: "Reports feature coming soon!" alert

---

## 🎯 SCENARIO 3: Program Administrator Journey

### Test Objective
Validate program-level management and instructor oversight capabilities.

#### **TC-PA-001: Program Admin Invitation and Setup**
**Prerequisites**: Institution admin account exists

**Steps**:
1. Institution admin creates invitation for program admin role
2. Program admin receives invitation email
3. Click invitation link
4. Complete registration with pre-populated data
5. Login and access Program Admin dashboard

**Expected Results**:
- ✅ **SHOULD WORK**: Invitation creation and email delivery
- ✅ **SHOULD WORK**: Invitation acceptance flow
- ✅ **SHOULD WORK**: Account activation upon acceptance
- ✅ **SHOULD WORK**: Program-specific dashboard access

#### **TC-PA-002: Course Management**
**Prerequisites**: Logged in as program admin

**Steps**:
1. View courses list on dashboard
2. Click "New Course" button
3. Attempt to edit existing course
4. Navigate to Courses menu

**Expected Results**:
- ✅ **SHOULD WORK**: Courses list loads (filtered by program)
- ❌ **STUB**: "Create Course feature coming soon!" alert
- ❌ **STUB**: "Edit Course feature coming soon!" alert
- ❌ **STUB**: "Courses management feature coming soon!" alert

#### **TC-PA-003: Instructor Management**
**Prerequisites**: Logged in as program admin

**Steps**:
1. View instructors list on dashboard
2. Click "Invite Instructor" button
3. Navigate to Instructors menu

**Expected Results**:
- ✅ **SHOULD WORK**: Instructors list loads (program-scoped)
- ❌ **STUB**: "Invite Instructor feature coming soon!" alert
- ❌ **STUB**: "Instructors management feature coming soon!" alert

#### **TC-PA-004: Section Management**
**Prerequisites**: Logged in as program admin

**Steps**:
1. View sections table with filters
2. Use term, course, and status filters
3. Click "New Section" button
4. Click "Terms" button
5. Navigate to Sections menu

**Expected Results**:
- ✅ **SHOULD WORK**: Sections table loads with filtering
- ✅ **SHOULD WORK**: Filter dropdowns populate from API
- ❌ **STUB**: "Create Section feature coming soon!" alert
- ❌ **STUB**: "Manage Terms feature coming soon!" alert
- ❌ **STUB**: "Sections management feature coming soon!" alert

#### **TC-PA-005: Multi-Program Context**
**Prerequisites**: Program admin with access to multiple programs

**Steps**:
1. View program dropdown (if multiple programs)
2. Attempt to switch between programs
3. Verify data filtering per program context

**Expected Results**:
- ✅ **SHOULD WORK**: Program dropdown appears for multi-program admins
- ❌ **STUB**: "Switch to Program feature coming soon!" alert
- 🔍 **PARTIAL**: Context filtering may be partially implemented

---

## 👨‍🏫 SCENARIO 4: Instructor Journey

### Test Objective
Validate instructor-level access and section management capabilities.

#### **TC-IN-001: Instructor Invitation and Onboarding**
**Prerequisites**: Program admin or institution admin account

**Steps**:
1. Admin creates instructor invitation
2. Instructor receives invitation email
3. Click invitation link and complete registration
4. Login and access Instructor dashboard

**Expected Results**:
- ✅ **SHOULD WORK**: Complete invitation and registration flow
- ✅ **SHOULD WORK**: Role-appropriate dashboard access
- ✅ **SHOULD WORK**: Limited permissions compared to admin roles

#### **TC-IN-002: My Sections View**
**Prerequisites**: Logged in as instructor with assigned sections

**Steps**:
1. View "My Sections" statistics
2. Navigate through sections list
3. Click "My Sections" menu item

**Expected Results**:
- ✅ **SHOULD WORK**: Section count and list (instructor-scoped)
- ❌ **STUB**: "My Sections management feature coming soon!" alert

#### **TC-IN-003: Assessment Management**
**Prerequisites**: Logged in as instructor

**Steps**:
1. View pending assessments count
2. Click "Assessments" menu item
3. Attempt assessment operations

**Expected Results**:
- ✅ **SHOULD WORK**: Assessment statistics load
- ❌ **STUB**: "Assessments feature coming soon!" alert

#### **TC-IN-004: Profile Management**
**Prerequisites**: Logged in as instructor

**Steps**:
1. Click "Edit Profile" button
2. Navigate to profile page
3. Attempt to change password

**Expected Results**:
- ❌ **STUB**: "Edit Profile feature coming soon!" alert
- 🔍 **UNKNOWN**: Profile page functionality may exist

---

## 🔐 SCENARIO 5: Authentication Security Features

### Test Objective
Validate security features and edge cases.

#### **TC-SEC-001: Password Security**
**Prerequisites**: Registration or password change form

**Steps**:
1. Attempt weak passwords (< 8 chars, no mixed case, no numbers)
2. Test password strength validation
3. Verify bcrypt hashing (developer verification)

**Expected Results**:
- ✅ **SHOULD WORK**: Password strength validation
- ✅ **SHOULD WORK**: Secure password hashing

#### **TC-SEC-002: Account Lockout**
**Prerequisites**: User account

**Steps**:
1. Attempt login with wrong password 5 times
2. Verify account lockout
3. Wait for lockout period to expire

**Expected Results**:
- ✅ **SHOULD WORK**: Account locks after 5 failed attempts
- ✅ **SHOULD WORK**: Lockout duration enforced

#### **TC-SEC-003: Session Management**
**Prerequisites**: Any user account

**Steps**:
1. Login and verify session creation
2. Test session timeout (8 hours)
3. Test "remember me" functionality
4. Logout and verify session cleanup

**Expected Results**:
- ✅ **SHOULD WORK**: Secure session management
- ✅ **SHOULD WORK**: Proper logout and cleanup

#### **TC-SEC-004: Password Reset Flow**
**Prerequisites**: User account

**Steps**:
1. Navigate to "Forgot Password" (may need direct URL)
2. Request password reset
3. Check email for reset link
4. Complete password reset process

**Expected Results**:
- ✅ **SHOULD WORK**: Password reset request and email
- ✅ **SHOULD WORK**: Reset token validation and new password setting
- ❌ **UI MISSING**: "Forgot Password" link may not be visible on login page

---

## 🔍 SCENARIO 6: Multi-Tenant Data Isolation

### Test Objective
Validate that users can only access data within their institutional/program scope.

#### **TC-MT-001: Institution Data Isolation**
**Prerequisites**: Multiple institutions with data

**Steps**:
1. Login as admin from Institution A
2. Verify only Institution A data is visible
3. Login as admin from Institution B
4. Verify only Institution B data is visible

**Expected Results**:
- ✅ **SHOULD WORK**: Institution-level data isolation
- ✅ **SHOULD WORK**: API endpoints filter by institution context

#### **TC-MT-002: Program Data Isolation**
**Prerequisites**: Multiple programs within institution

**Steps**:
1. Login as Program Admin for Program A
2. Verify only Program A courses/sections visible
3. Login as Program Admin for Program B
4. Verify only Program B courses/sections visible

**Expected Results**:
- ✅ **SHOULD WORK**: Program-level data filtering
- 🔍 **VERIFY**: Program context switching functionality

---

## 📊 Test Execution Checklist

### Pre-Execution
- [ ] Application server running
- [ ] Database accessible
- [ ] Email service configured
- [ ] Test data prepared (if needed)

### During Execution
- [ ] Document actual vs. expected results
- [ ] Screenshot any errors or unexpected behavior
- [ ] Note performance issues
- [ ] Record "coming soon" stub encounters

### Post-Execution
- [ ] Summarize findings
- [ ] Categorize issues (bugs vs. incomplete features)
- [ ] Prioritize any critical issues
- [ ] Document suggestions for improvement

---

## 🚨 Known Limitations and Stubs

### Complete Feature Stubs (Show "Coming Soon" Alerts)
- Institution creation/editing (Site Admin)
- User invitation UI (All admin roles)
- Program creation/editing (Institution Admin)
- Course creation/editing (Program Admin)
- Section creation/editing (Program Admin)
- Term management (Program Admin)
- All reporting features
- Profile editing (All users)
- System settings and logs (Site Admin)
- Import history and templates

### Partial Implementations
- Multi-program context switching (UI exists, functionality stubbed)
- Password reset (Backend complete, UI link may be missing)
- Data import (Redirects to existing import page)

### Fully Functional Features
- User registration and email verification
- User invitation system (backend)
- Authentication and session management
- Role-based access control
- Dashboard statistics and data loading
- Multi-tenant data isolation
- Password security and account lockout

---

## 📝 Test Report Template

### Test Session Information
- **Date**: ___________
- **Tester**: ___________
- **Environment**: ___________
- **Browser**: ___________

### Scenario Results
| Test Case | Status | Notes |
|-----------|--------|-------|
| TC-SA-001 | ✅❌🔍 | |
| TC-SA-002 | ✅❌🔍 | |
| ... | | |

### Issues Found
| Priority | Description | Steps to Reproduce | Expected | Actual |
|----------|-------------|-------------------|----------|--------|
| High/Med/Low | | | | |

### Overall Assessment
- **Authentication System**: ___________
- **User Experience**: ___________
- **Security Features**: ___________
- **Readiness for CEI Demo**: ___________

### Recommendations
1. ___________
2. ___________
3. ___________

---

*This UAT guide serves as a comprehensive manual testing protocol for the authentication system. Update as features are completed or requirements change.*
