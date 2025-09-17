# Authentication System Design & Implementation Plan

## 🎯 Overview

This document outlines the complete design and implementation plan for replacing the current stub authentication system with a production-ready authentication and authorization framework.

## 🏗️ Architecture Decisions

### **Technology Stack**
- **Backend**: Flask with session-based authentication
- **Database**: Firestore (existing) with enhanced User model
- **Frontend**: Server-rendered HTML templates with enhanced JavaScript
- **Session Management**: Flask-Session with secure cookies
- **Password Security**: bcrypt for hashing
- **Future OAuth**: Design prepared for Google/Microsoft integration

### **Key Design Principles**
1. **Greenfield Advantage**: No legacy migration constraints
2. **Single Institution Per User**: V1 simplification (no multi-tenancy per user)
3. **4-Tier Role Hierarchy**: site_admin → institution_admin → program_admin → instructor
4. **Program-Based Organization**: Institution → Program → Course hierarchy
5. **Invite-Based Onboarding**: Controlled user growth
6. **OAuth-Ready**: Foundation laid for future enhancement

---

## 🧪 Smoke Test Strategy

### **Test Categories by Epic**

**Epic 1 (Foundation)**: Model validation, password security, session management
**Epic 2 (Registration)**: Registration flows, email verification, invitation system  
**Epic 3 (Authentication)**: Login/logout, password reset, account lockout
**Epic 4 (Programs)**: Program CRUD, course associations, admin assignments
**Epic 5 (Authorization)**: Role permissions, access control, context filtering

### **Critical Integration Points**
- Complete registration → login → dashboard access flow
- Invitation → acceptance → immediate system access
- Program creation → course assignment → instructor access
- Role-based UI hiding/showing based on permissions
- Institution/program context switching for multi-access users

### **Smoke Test Execution Strategy**
- Add smoke tests incrementally with each story completion
- Run full smoke test suite before epic completion
- Focus on end-to-end user journeys, not just unit functionality
- Test both happy path and critical error scenarios
- Validate security boundaries and unauthorized access prevention

---

## 📊 Data Model Changes

### **Enhanced User Model**
```python
class User(DataModel):
    """Enhanced User model with full authentication support"""
    
    # Identity
    user_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: str  # Primary identifier (username)
    password_hash: Optional[str] = None  # bcrypt hash
    
    # Profile
    first_name: str
    last_name: str
    display_name: Optional[str] = None  # "Dr. Smith" or preferred name
    
    # Authentication State
    account_status: str = "pending"  # pending, active, suspended
    email_verified: bool = False
    email_verification_token: Optional[str] = None
    email_verification_sent_at: Optional[datetime] = None
    
    # Password Reset
    password_reset_token: Optional[str] = None
    password_reset_expires_at: Optional[datetime] = None
    
    # Role & Institution
    role: str  # instructor, program_admin, institution_admin, site_admin
    institution_id: str  # Required (except site_admin)
    program_ids: List[str] = field(default_factory=list)  # Programs user has access to (for program_admin)
    
    # Activity Tracking
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login_at: Optional[datetime] = None
    login_attempts: int = 0
    locked_until: Optional[datetime] = None
    
    # Invitation Tracking
    invited_by: Optional[str] = None  # user_id of inviter
    invited_at: Optional[datetime] = None
    registration_completed_at: Optional[datetime] = None
    
    # Future OAuth Support
    oauth_provider: Optional[str] = None  # google, microsoft, etc.
    oauth_id: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_active(self) -> bool:
        return (
            self.account_status == "active" 
            and self.email_verified 
            and (self.locked_until is None or self.locked_until < datetime.now(timezone.utc))
        )
```

### **New UserInvitation Model**
```python
class UserInvitation(DataModel):
    """Track pending user invitations"""
    
    invitation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    role: str  # instructor, program_admin
    institution_id: str
    
    # Invitation Management
    token: str  # Secure random token
    invited_by: str  # user_id of inviter
    invited_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime  # 7 days from creation
    
    # Status Tracking
    status: str = "pending"  # pending, accepted, expired, cancelled
    accepted_at: Optional[datetime] = None
    
    # Personal Message
    personal_message: Optional[str] = None
    
    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at
```

### **Enhanced Institution Model**
```python
class Institution(DataModel):
    """Enhanced Institution model"""
    
    # Existing fields remain the same
    institution_id: str
    name: str
    short_name: str
    website_url: Optional[str] = None
    
    # New fields for auth system
    created_by: str  # user_id of creator
    admin_email: str  # Primary contact for institution
    
    # Settings
    allow_self_registration: bool = False  # Future feature
    require_email_verification: bool = True
    
    # Activity
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
```

### **New Program Model**
```python
class Program(DataModel):
    """Academic Program/Department within an Institution"""
    
    # Identity
    program_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # "Biology Department", "Computer Science Program"
    short_name: str  # "BIO", "CS"
    description: Optional[str] = None
    
    # Hierarchy
    institution_id: str  # Parent institution
    
    # Management
    created_by: str  # user_id of creator
    program_admins: List[str] = field(default_factory=list)  # user_ids of program admins
    
    # Settings
    is_default: bool = False  # True for "Unclassified" default program
    
    # Activity
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    
    @property
    def admin_count(self) -> int:
        return len(self.program_admins)
```

---

## 🔐 Authentication Flow Design

### **1. User Registration Flow**

#### **Institution Admin Self-Registration**
```
1. User visits /register
2. Selects "I manage an institution"
3. Fills form:
   - Email (becomes username)
   - Password (with strength requirements)
   - First Name, Last Name
   - Institution Name, Website URL
4. Creates pending user + institution + default "Unclassified" program
5. User automatically becomes institution_admin
6. Sends email verification
7. User clicks verification link
8. Account activated, user can login
```

#### **User Invitation Flow**
```
1. Institution/Program Admin visits /users/invite
2. Selects role (program_admin or instructor) and program(s) if applicable
3. Enters user email + optional message
4. System creates UserInvitation record
5. Sends invitation email with secure token
6. User clicks invitation link
7. Redirected to /register/accept/{token}
8. Fills registration form (pre-populated email/role/programs)
9. Account created and immediately activated
10. User can login with appropriate permissions
```

### **2. Authentication Endpoints**

#### **Core Auth Routes**
- `GET /login` - Login form
- `POST /login` - Process login
- `GET /logout` - Logout user
- `GET /register` - Registration form (admin self-registration)
- `POST /register` - Process registration
- `GET /register/accept/{token}` - Accept invitation
- `POST /register/accept/{token}` - Complete invited registration

#### **Password Management**
- `GET /forgot-password` - Request password reset
- `POST /forgot-password` - Send reset email
- `GET /reset-password/{token}` - Reset password form
- `POST /reset-password/{token}` - Process password reset

#### **Account Management**
- `GET /verify-email/{token}` - Email verification
- `GET /profile` - User profile page
- `POST /profile` - Update profile
- `POST /change-password` - Change password

#### **Program Management**
- `GET /programs` - List programs (filtered by user permissions)
- `GET /programs/new` - Create program form
- `POST /programs` - Create new program
- `GET /programs/{id}` - Program details
- `POST /programs/{id}` - Update program
- `DELETE /programs/{id}` - Delete program
- `POST /programs/{id}/admins` - Add program admin
- `DELETE /programs/{id}/admins/{user_id}` - Remove program admin
- `GET /programs/{id}/courses` - List courses in program
- `POST /programs/{id}/courses` - Add course to program
- `DELETE /programs/{id}/courses/{course_id}` - Remove course from program

### **3. Session Management**

```python
# Flask-Session configuration
app.config['SESSION_TYPE'] = 'filesystem'  # Or Redis for production
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'course_app:'
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)  # 8-hour sessions
```

---

## 🛡️ Security Implementation

### **Password Security**
- **Minimum Requirements**: 8 characters, mixed case, numbers
- **Hashing**: bcrypt with cost factor 12
- **Rate Limiting**: 5 failed attempts = 15-minute lockout
- **Password Reset**: Secure tokens, 1-hour expiry

### **Session Security**
- **CSRF Protection**: Flask-WTF tokens on all forms
- **Session Fixation**: New session ID on login
- **Secure Cookies**: HTTPOnly, Secure, SameSite
- **Session Timeout**: 8 hours idle timeout

### **Email Security**
- **Token Generation**: `secrets.token_urlsafe(32)`
- **Token Expiry**: 24 hours for verification, 1 hour for reset
- **Rate Limiting**: 1 email per minute per address

---

## 📋 Implementation Stories

### **Epic 1: Core Authentication Infrastructure**

#### **Story 1.1: Enhanced User Model** ✅ **COMPLETED**
**As a** system administrator  
**I want** an enhanced user data model  
**So that** the system can properly track user authentication state and permissions

**Acceptance Criteria:**
- [x] Update `models.py` with enhanced User model
- [x] Add UserInvitation model
- [x] Update Institution model with auth fields
- [x] Create database migration utilities
- [x] Add model validation methods
- [x] Write comprehensive unit tests for models

**Technical Tasks:**
- Update `models.py` with new User fields
- Add password hashing utilities
- Create model factory methods
- Add data validation methods
- Update database service functions

**Estimate:** 5 story points

**Smoke Tests Added:**
- [x] Test User model creation with all required fields
- [x] Test UserInvitation model creation and expiry logic
- [x] Test Program model creation with institution association
- [x] Test enhanced Institution model with auth fields

---

#### **Story 1.2: Password Management System** ✅ **COMPLETED**
**As a** user  
**I want** secure password creation and management  
**So that** my account is protected and I can recover access if needed

**Acceptance Criteria:**
- [x] Password strength validation (8+ chars, mixed case, numbers)
- [x] Secure bcrypt hashing (cost factor 12)
- [x] Password reset via email with secure tokens
- [x] Rate limiting on password reset requests
- [ ] Password change functionality for logged-in users
- [x] Account lockout after 5 failed login attempts

**Technical Tasks:**
- Install and configure bcrypt
- Create password validation utilities
- Implement password hashing/verification
- Create secure token generation
- Add rate limiting middleware
- Build password reset email templates

**Estimate:** 8 story points

---

#### **Story 1.3: Session Management** ✅ **COMPLETED**
**As a** user  
**I want** secure session management  
**So that** my login state is maintained securely across requests

**Acceptance Criteria:**
- [x] Flask-Session integration with secure configuration
- [x] 8-hour session timeout with idle detection
- [x] Secure cookie configuration (HTTPOnly, Secure, SameSite)
- [x] Session fixation prevention
- [x] "Remember me" functionality (optional)
- [x] Proper session cleanup on logout

**Technical Tasks:**
- Install and configure Flask-Session
- Create session management utilities
- Implement secure cookie settings
- Add session timeout handling
- Create logout functionality
- Add session security middleware

**Estimate:** 5 story points

**Smoke Tests Added:**
- [x] Test password strength validation with various inputs
- [x] Test bcrypt hashing and verification
- [x] Test password reset token generation and validation
- [x] Test account lockout after 5 failed attempts
- [x] Test session creation and timeout handling

---

### **Epic 2: User Registration & Onboarding**

#### **Story 2.1: Admin Self-Registration** ✅ **COMPLETED**
**As a** potential institution administrator  
**I want** to create an account and institution  
**So that** I can start using the system to manage my program

**Acceptance Criteria:**
- [x] Registration form with institution creation
- [x] Email verification required before activation
- [x] Automatic institution creation with admin as owner
- [x] Welcome email with getting started guide
- [x] Proper error handling and validation
- [x] Redirect to dashboard after verification (backend returns proper status)

**Technical Tasks:**
- Create registration form templates
- Build registration route handlers
- Implement email verification system
- Create institution creation logic
- Design welcome email templates
- Add form validation and error handling

**Estimate:** 8 story points

**Smoke Tests Added:**
- [x] Test complete registration flow from form to email verification
- [x] Test institution creation during admin registration
- [x] Test default program creation for new institutions
- [x] Test email verification link and account activation

---

#### **Story 2.2: User Invitation System** ✅ **COMPLETED**
**As an** institution administrator  
**I want** to invite instructors to join my institution  
**So that** they can access the system and manage their courses

**Acceptance Criteria:**
- [x] Invitation form with email and role selection
- [x] Secure invitation tokens with 7-day expiry
- [x] Personalized invitation emails
- [x] Invitation acceptance flow
- [x] Automatic account activation upon acceptance
- [x] Invitation status tracking and management

**Technical Tasks:**
- Create invitation form and routes
- Build secure token generation
- Design invitation email templates
- Implement invitation acceptance flow
- Add invitation management interface
- Create invitation status tracking

**Estimate:** 10 story points

**Smoke Tests Added:**
- [x] Test invitation email sending and token generation
- [x] Test invitation acceptance flow and account creation
- [x] Test invitation expiry and status tracking
- [x] Test role assignment during invitation acceptance

#### **Story 2.3: Login/Logout System** ✅ **COMPLETED**
**As a** user  
**I want** to securely log in and out of the system  
**So that** I can access my account and protect it when finished

**Acceptance Criteria:**
- [x] Login form with email/password
- [x] Secure authentication verification
- [x] Account lockout after failed attempts
- [x] "Remember me" checkbox functionality
- [x] Proper session creation on successful login
- [x] Secure logout with session cleanup
- [x] Redirect to intended page after login

**Technical Tasks:**
- Create login form template
- Build login route handler
- Implement authentication verification
- Add account lockout logic
- Create logout functionality
- Add redirect handling
- Implement "remember me" feature

**Estimate:** 8 story points

**Smoke Tests Added:**
- [x] Test login with valid credentials and session creation
- [x] Test login failure with invalid credentials and account lockout
- [x] Test logout and session cleanup
- [x] Test "remember me" functionality and extended sessions

---

### **Epic 3: Authentication Endpoints**

#### **Story 3.1: Password Reset Flow** ✅ **COMPLETED**
**As a** user who forgot my password  
**I want** to reset my password via email  
**So that** I can regain access to my account

**Acceptance Criteria:**
- [x] "Forgot Password" link on login page (backend API ready)
- [x] Password reset request form
- [x] Secure reset token generation and email
- [x] Password reset form with token validation
- [x] New password strength validation
- [x] Success confirmation and auto-login
- [x] Token expiry and security measures

**Technical Tasks:**
- Create forgot password form
- Build password reset request handler
- Implement secure token system
- Design reset email templates
- Create password reset form
- Add token validation and expiry
- Implement new password processing

**Estimate:** 8 story points

**Smoke Tests Added:**
- [x] Test password reset request and email sending
- [x] Test password reset form with valid token
- [x] Test password reset with expired token
- [x] Test new password validation and account access

---

### **Epic 4: Program Management System**

#### **Story 4.1: Program CRUD Operations** ✅ **COMPLETED**
**As an** institution administrator  
**I want** to create and manage programs within my institution  
**So that** I can organize courses and delegate administration

**Acceptance Criteria:**
- [x] Create new programs with name, short name, description
- [x] Edit existing program details
- [x] Delete programs (with course reassignment to default)
- [x] List all programs in institution
- [x] Assign program administrators
- [x] Default "Unclassified" program created automatically

**Technical Tasks:**
- Create Program model in models.py
- Build program CRUD API endpoints
- Create program management UI templates
- Add program creation during institution setup
- Implement program admin assignment
- Add course-to-program association logic

**Estimate:** 13 story points

**Smoke Tests Added:**
- [x] Test program creation and management by institution admin
- [x] Test program admin assignment and removal
- [x] Test default program creation for new institutions
- [x] Test program deletion with course reassignment

---

#### **Story 4.2: Course-Program Association** ✅ **COMPLETED**
**As a** program administrator  
**I want** to add and remove courses from my program  
**So that** I can organize the curriculum under my responsibility

**Acceptance Criteria:**
- [x] Add existing courses to program
- [x] Remove courses from program (move to default)
- [x] View all courses in a program
- [x] Bulk course management operations
- [x] Course can belong to multiple programs
- [x] Default program for orphaned courses

**Technical Tasks:**
- Update Course model with program associations
- Create course-program association endpoints
- Build course management UI for programs
- Add bulk course operations
- Implement course search and filtering by program
- Update import system to handle program associations

**Estimate:** 10 story points

**Smoke Tests Added:**
- [x] Test adding/removing courses from programs
- [x] Test course visibility based on program access
- [x] Test bulk course operations within programs
- [x] Test course assignment to default program when orphaned

---

### **Epic 5: Authorization & Permissions**

#### **Story 5.1: 4-Tier Role-Based Access Control** ✅ **COMPLETED**
**As a** system  
**I want** to enforce role-based permissions  
**So that** users can only access appropriate functionality

**Acceptance Criteria:**
- [x] Replace stub authentication decorators
- [x] Implement 4-tier role hierarchy (site_admin > institution_admin > program_admin > instructor)
- [x] Implement program-scoped permissions for program_admin
- [x] Update all existing routes with proper decorators
- [x] Add unauthorized access error handling
- [x] Create permission checking utilities for program access

**Technical Tasks:**
- Replace stub decorators in auth_service.py
- Implement role and permission checking logic
- Update all API routes with proper decorators
- Create unauthorized access handlers
- Add permission checking utilities
- Update frontend to hide unauthorized elements

**Estimate:** 10 story points

**Smoke Tests Added:**
- [x] Test role-based access control for all 4 tiers
- [x] Test permission enforcement on API endpoints
- [x] Test unauthorized access handling
- [x] Test program-scoped permissions for program admins

---

#### **Story 5.2: Apply Authorization Decorators to API Routes** ✅ **COMPLETED**
**As a** system administrator  
**I want** all API routes to use proper authorization decorators  
**So that** access control is consistently enforced across the application

**Acceptance Criteria:**
- [x] Update all API routes with appropriate authorization decorators
- [x] Replace generic @login_required with specific permission decorators
- [x] Implement context-aware permissions with context_keys
- [x] Add proper error handling for authorization failures
- [x] Test all routes with different user roles
- [x] Update tests to work with new authorization requirements

**Technical Tasks:**
- Update all API routes in api_routes.py with proper decorators
- Replace @login_required with @permission_required where appropriate
- Add context_keys for institution_id and program_id validation
- Update existing tests to handle authorization contexts
- Test authorization with different user roles

**Estimate:** 8 story points

**Smoke Tests Added:**
- [x] Test all API routes with proper authorization decorators
- [x] Test context-aware permissions with institution and program contexts
- [x] Test authorization failures return proper error codes

---

#### **Story 5.3: Integrate Authorization System with Invitation/Registration Flows** ✅ **COMPLETED**
**As a** system administrator  
**I want** invitation and registration flows to use the centralized authorization system  
**So that** role management is consistent across all user onboarding

**Acceptance Criteria:**
- [x] Update invitation_service.py to use UserRole enum for validation
- [x] Update models.py to validate roles against centralized UserRole enum
- [x] Migrate User.get_permissions() to use ROLE_PERMISSIONS mapping
- [x] Deprecate old ROLES dictionary in favor of auth_service definitions
- [x] Update all role validation to use single source of truth
- [x] Ensure backward compatibility during transition

**Technical Tasks:**
- Update invitation_service.py to import and use UserRole enum
- Update models.py User and UserInvitation schemas for role validation
- Replace User.get_permissions() implementation to use auth_service
- Comment out and deprecate old ROLES dictionary
- Update unit tests to reflect new role validation logic

**Estimate:** 6 story points

**Smoke Tests Added:**
- [x] Test invitation creation with centralized role validation
- [x] Test user registration with UserRole enum validation
- [x] Test permission retrieval uses centralized ROLE_PERMISSIONS

---

#### **Story 5.4: Add Role-Based UI Components and Navigation** ✅ **COMPLETED**
**As a** user  
**I want** the UI to adapt based on my role and permissions  
**So that** I only see functionality I'm authorized to use

**Acceptance Criteria:**
- [x] Create role-specific dashboard templates for all 4 user roles
- [x] Implement dynamic navigation menus based on user role
- [x] Add authentication-aware main template with login/logout
- [x] Create user context display with role badges and dropdowns
- [x] Implement JavaScript-based role detection and UI adaptation
- [x] Update dashboard route to handle all 4 roles

**Technical Tasks:**
- Create dashboard templates for each role (site_admin, institution_admin, program_admin, instructor)
- Implement role-based navigation components
- Add authentication status checking via JavaScript
- Create user context display and logout functionality
- Update main template with dynamic navigation

**Estimate:** 12 story points

**Smoke Tests Added:**
- [x] Test role-specific dashboard templates render correctly
- [x] Test navigation menus adapt based on user role
- [x] Test authentication status detection and UI updates

---

#### **Story 5.5: Test Authorization System with Multi-Tenant Data Access Scenarios** ✅ **COMPLETED**
**As a** system administrator  
**I want** comprehensive testing of multi-tenant data access  
**So that** users can only access data within their institutional/program scope

**Acceptance Criteria:**
- [x] Create integration tests for institution-level data isolation
- [x] Test program-scoped access control for program admins
- [x] Validate cross-tenant access prevention across all user roles
- [x] Test role hierarchy access patterns and inheritance
- [x] Create comprehensive smoke tests for authorization system health
- [x] Test context-aware API endpoint security

**Technical Tasks:**
- Create comprehensive multi-tenant authorization integration tests
- Implement authorization system smoke tests
- Test institution data isolation scenarios
- Test program-scoped access control
- Test cross-tenant access prevention
- Test role hierarchy and permission inheritance

**Estimate:** 10 story points

**Smoke Tests Added:**
- [x] Test multi-tenant data isolation with 34 comprehensive integration tests
- [x] Test institution-level data access restrictions
- [x] Test program-scoped access control validation
- [x] Test cross-tenant access prevention
- [x] Test role hierarchy and security boundaries

---

#### **Story 5.6: Program Context Management**
**As a** user  
**I want** all my actions to be scoped to my institution and programs  
**So that** I only see and can modify data I have access to

**Acceptance Criteria:**
- [ ] Automatic institution/program context from user session
- [ ] All database queries filtered by institution and program access
- [ ] Program switching for program admins with multiple programs
- [ ] Context validation on all operations
- [ ] Error handling for context mismatches
- [ ] Default program handling for unassigned courses

**Technical Tasks:**
- Update get_current_institution_id() function
- Add institution filtering to all database queries
- Create institution context middleware
- Add context validation utilities
- Update API routes with institution scoping
- Create admin institution switching

**Estimate:** 8 story points

**Smoke Tests Added:**
- [ ] Test program context management for all user roles
- [ ] Test automatic context detection from user sessions
- [ ] Test database query filtering by institution/program access
- [ ] Test program switching for multi-program admins
- [ ] Test institution context filtering and validation

---

### **Epic 6: User Interface & Experience**

#### **Story 6.1: Authentication UI Components**
**As a** user  
**I want** intuitive authentication interfaces  
**So that** I can easily manage my account and access

**Acceptance Criteria:**
- [ ] Modern, responsive login/register forms
- [ ] Clear error messaging and validation feedback
- [ ] Loading states for form submissions
- [ ] Password strength indicator
- [ ] User-friendly email verification flow
- [ ] Account management dashboard

**Technical Tasks:**
- Design authentication form templates
- Create responsive CSS for auth pages
- Add JavaScript form validation
- Implement password strength indicator
- Create loading states and feedback
- Build account management interface

**Estimate:** 8 story points

---

#### **Story 6.2: Admin User Management Interface**
**As an** institution administrator  
**I want** to manage users in my institution  
**So that** I can control access and maintain my team

**Acceptance Criteria:**
- [ ] User list with filtering and search
- [ ] Invite new users interface
- [ ] Edit user roles and status
- [ ] Resend invitations functionality
- [ ] User activity and status indicators
- [ ] Bulk user management actions

**Technical Tasks:**
- Create user management templates
- Build user list with pagination
- Implement user search and filtering
- Create user editing interfaces
- Add invitation management
- Implement bulk actions

**Estimate:** 10 story points

---

### **Epic 7: Testing & Security**

#### **Story 7.1: Authentication Testing Suite**
**As a** developer  
**I want** comprehensive authentication tests  
**So that** the auth system is reliable and secure

**Acceptance Criteria:**
- [ ] Unit tests for all auth functions
- [ ] Integration tests for auth flows
- [ ] Security tests for common vulnerabilities
- [ ] Performance tests for auth operations
- [ ] Test coverage above 90%

**Technical Tasks:**
- Write unit tests for models and utilities
- Create integration tests for auth flows
- Add security vulnerability tests
- Implement performance benchmarks
- Set up test coverage reporting

**Estimate:** 8 story points

---

#### **Story 7.2: Security Hardening**
**As a** system administrator  
**I want** the authentication system to be secure  
**So that** user accounts and data are protected

**Acceptance Criteria:**
- [ ] CSRF protection on all forms
- [ ] Rate limiting on sensitive endpoints
- [ ] Input validation and sanitization
- [ ] Security headers configuration
- [ ] Audit logging for auth events
- [ ] Security monitoring and alerting

**Technical Tasks:**
- Implement CSRF protection
- Add rate limiting middleware
- Create input validation utilities
- Configure security headers
- Set up audit logging
- Add security monitoring

**Estimate:** 10 story points

---

## 🚀 Implementation Timeline

### **Phase 1: Foundation (Sprint 1-2)**
- Stories 1.1, 1.2, 1.3 (Core Infrastructure)
- **Goal**: Replace stub auth with working password system

### **Phase 2: Registration (Sprint 3-4)**  
- Stories 2.1, 2.2, 3.1, 3.2 (Registration & Login)
- **Goal**: Full user onboarding and authentication

### **Phase 3: Program Management (Sprint 5-6)**
- Stories 4.1, 4.2 (Program CRUD & Course Association)
- **Goal**: Program hierarchy and course organization

### **Phase 4: Authorization (Sprint 7-8)**
- Stories 5.1, 5.2 (Permissions & Context)
- **Goal**: Proper access control and data isolation

### **Phase 5: Polish (Sprint 9-10)**
- Stories 6.1, 6.2, 7.1, 7.2 (UI, Testing, Security)
- **Goal**: Production-ready system

---

## 📝 Database Schema Setup

### **Initial Collections & Indexes**

Since this is a greenfield project, we'll create the database schema from scratch with all necessary collections and indexes:

```python
def setup_database_schema():
    """Initialize database collections and indexes for auth system"""
    
    # Users collection - enhanced model
    users_collection = db.collection('users')
    users_collection.create_index([('email', 1)], unique=True)
    users_collection.create_index([('institution_id', 1)])
    users_collection.create_index([('role', 1)])
    users_collection.create_index([('account_status', 1)])
    users_collection.create_index([('email_verification_token', 1)])
    users_collection.create_index([('password_reset_token', 1)])
    
    # Institutions collection
    institutions_collection = db.collection('institutions')
    institutions_collection.create_index([('short_name', 1)], unique=True)
    institutions_collection.create_index([('created_by', 1)])
    
    # Programs collection - new
    programs_collection = db.collection('programs')
    programs_collection.create_index([('institution_id', 1)])
    programs_collection.create_index([('short_name', 1)])
    programs_collection.create_index([('program_admins', 1)])
    programs_collection.create_index([('is_default', 1)])
    
    # User invitations collection - new
    invitations_collection = db.collection('user_invitations')
    invitations_collection.create_index([('email', 1)])
    invitations_collection.create_index([('token', 1)], unique=True)
    invitations_collection.create_index([('expires_at', 1)])
    invitations_collection.create_index([('institution_id', 1)])
    invitations_collection.create_index([('status', 1)])
    
    # Courses collection - update with program associations
    courses_collection = db.collection('courses')
    courses_collection.create_index([('institution_id', 1)])
    courses_collection.create_index([('program_ids', 1)])  # New: for program associations
    courses_collection.create_index([('course_number', 1), ('institution_id', 1)], unique=True)
```

### **Development Data Setup**

For development environments, we'll also create default data:

```python
def create_development_data():
    """Create default data for development environment"""
    
    # Create default CEI institution with default program
    cei_institution_id = create_default_cei_institution()
    
    # Create default "Unclassified" program for CEI
    default_program = Program(
        name="Unclassified",
        short_name="UNCL",
        description="Default program for courses without specific program assignment",
        institution_id=cei_institution_id,
        created_by="system",
        is_default=True
    )
    
    # Create development admin user
    dev_admin = User(
        email="admin@cei.edu",
        password_hash=bcrypt.hashpw("devpassword".encode('utf-8'), bcrypt.gensalt()),
        first_name="Dev",
        last_name="Admin",
        role="institution_admin",
        institution_id=cei_institution_id,
        account_status="active",
        email_verified=True
    )
```

---

## 🔮 Future Enhancements (Post-V1)

### **OAuth Integration**
- Google Workspace integration for academic institutions
- Microsoft Office 365 integration
- LinkedIn for professional networking

### **Advanced Security**
- Two-factor authentication (2FA)
- Single Sign-On (SSO) for enterprise clients
- Advanced audit logging and compliance

### **Multi-Institution Support**
- Users belonging to multiple institutions
- Context switching interface
- Cross-institutional permissions

### **Advanced User Management**
- User groups and teams
- Delegated administration
- Advanced permission granularity

---

## ✅ Definition of Done

Each story is complete when:
- [ ] Code implemented and reviewed
- [ ] Unit tests written and passing
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Security review completed
- [ ] UI/UX review completed
- [ ] Deployed to staging and tested
- [ ] Performance benchmarks met
- [ ] Accessibility requirements met

---

### **🔧 Frontend Integration Catch-All**

#### **Story 8.1: Frontend Authentication Integration**
**As a** user  
**I want** complete frontend integration for authentication features  
**So that** I have a seamless user experience

**Frontend Items to Consider Before Merging:**
- [ ] Dashboard page to redirect to after email verification
- [ ] "Forgot Password" link on login page UI
- [ ] Password change functionality for logged-in users (API endpoint needed)
- [ ] Modern, responsive login/register form styling
- [ ] Loading states for form submissions
- [ ] Password strength indicator UI
- [ ] User-friendly email verification flow pages
- [ ] Account management dashboard

**Estimate:** 13 story points

---

*This design document serves as the single source of truth for the authentication system implementation. All stories should be created in JIRA based on this specification.*
