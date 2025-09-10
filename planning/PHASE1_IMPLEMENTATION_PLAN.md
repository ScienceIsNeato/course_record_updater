# Phase 1 Implementation Plan: Data Model & Authentication

**Objective:** Expand current flat course system to relational enterprise model while maintaining backward compatibility

**Timeline:** 2-3 weeks

---

## Overview: Evolutionary Architecture

**Strategy:** Extend existing system components rather than rebuild from scratch

**Key Principle:** Maintain backward compatibility during transition - current system must continue working while we add new capabilities

---

## 1. Data Model Evolution

### Current State Analysis
```python
# Current flat model (works, but limited)
course_record = {
    'course_number': 'ACC-201',
    'course_title': 'Accounting Principles', 
    'instructor_name': 'John Smith',
    'term': '2024 Fall',
    'num_students': 25,
    'grade_a': 5, 'grade_b': 8, # ... etc
}
```

### Target Relational Model
```python
# New entity structure
User = {
    'user_id': 'uuid',
    'email': 'john.smith@cei.edu',
    'first_name': 'John',
    'last_name': 'Smith', 
    'role': 'instructor',  # instructor, program_admin, site_admin
    'department': 'Business',
    'active': True,
    'created_at': timestamp,
    'last_login': timestamp
}

Course = {
    'course_id': 'uuid',
    'course_number': 'ACC-201',
    'course_title': 'Accounting Principles',
    'department': 'Business',
    'credit_hours': 3,
    'active': True
}

Term = {
    'term_id': 'uuid', 
    'name': '2024 Fall',
    'start_date': '2024-08-26',
    'end_date': '2024-12-13',
    'assessment_due_date': '2024-12-20',
    'active': True
}

CourseSection = {
    'section_id': 'uuid',
    'course_id': 'uuid',      # FK to Course
    'instructor_id': 'uuid',   # FK to User
    'term_id': 'uuid',        # FK to Term
    'section_number': '001',
    'enrollment': 25,
    'status': 'assigned',     # assigned, in_progress, completed
    'grade_distribution': {
        'grade_a': 5, 'grade_b': 8, # ... etc
    },
    'assigned_date': timestamp,
    'completed_date': timestamp,
    'last_modified': timestamp
}

CourseOutcome = {
    'outcome_id': 'uuid',
    'course_id': 'uuid',      # FK to Course  
    'clo_number': '1',
    'description': 'Students will demonstrate...',
    'assessment_method': 'Exam',
    'assessment_data': {
        'students_assessed': 25,
        'students_meeting': 22,
        'percentage_meeting': 88.0
    },
    'narrative': 'Most students performed well...',
    'active': True
}
```

### Migration Strategy
1. **Dual-model support**: New collections alongside existing `courses` collection
2. **Backward compatibility**: Keep current API working during transition
3. **Data bridging**: Functions to convert between flat and relational models
4. **Gradual migration**: Move features incrementally to new model

---

## 2. Database Service Extensions

### Current `database_service.py` Strengths
- ✅ Clean abstraction pattern
- ✅ Error handling framework
- ✅ Firestore client management
- ✅ Duplicate detection logic

### Required Extensions

**New Entity Collections:**
```python
# Add to database_service.py
USERS_COLLECTION = 'users'
COURSES_COLLECTION_NEW = 'courses_v2' 
TERMS_COLLECTION = 'terms'
COURSE_SECTIONS_COLLECTION = 'course_sections'
COURSE_OUTCOMES_COLLECTION = 'course_outcomes'

# Keep existing for backward compatibility
COURSES_COLLECTION = 'courses'  # Legacy flat model
```

**New Service Functions:**
```python
# User management
def create_user(user_data: dict) -> str
def get_user_by_email(email: str) -> dict
def get_users_by_role(role: str) -> List[dict]
def update_user(user_id: str, update_data: dict) -> bool

# Course management  
def create_course(course_data: dict) -> str
def get_course_by_number(course_number: str) -> dict
def get_courses_by_department(department: str) -> List[dict]

# Term management
def create_term(term_data: dict) -> str
def get_active_terms() -> List[dict]
def get_current_term() -> dict

# Course section management
def create_course_section(section_data: dict) -> str
def get_sections_by_instructor(instructor_id: str) -> List[dict]
def get_sections_by_term(term_id: str) -> List[dict]
def assign_instructor_to_section(section_id: str, instructor_id: str) -> bool

# Course outcome management
def create_course_outcome(outcome_data: dict) -> str
def get_outcomes_by_course(course_id: str) -> List[dict]
def update_outcome_assessment(outcome_id: str, assessment_data: dict) -> bool
```

---

## 3. Authentication & Authorization

### Authentication Strategy
**Option A: Firebase Auth Integration** (Recommended)
- ✅ Integrates seamlessly with Firestore
- ✅ Handles email/password, SSO, MFA
- ✅ Session management built-in
- ✅ CEI can use existing institutional email

**Option B: Custom JWT Implementation**
- More control but more complexity
- Would need separate session management

### Role-Based Access Control
```python
ROLES = {
    'instructor': {
        'permissions': [
            'view_own_sections',
            'edit_own_assessments', 
            'submit_assessments',
            'view_own_courses'
        ]
    },
    'program_admin': {
        'permissions': [
            'view_all_sections',
            'assign_instructors',
            'manage_courses',
            'manage_terms',
            'send_notifications',
            'view_reports'
        ]
    },
    'site_admin': {
        'permissions': [
            'manage_users',
            'manage_system_settings',
            'import_data',
            'full_access'
        ]
    }
}
```

### Flask Integration
```python
# Add to app.py
from functools import wraps
from flask import session, redirect, url_for

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user or user['role'] != required_role:
                return redirect(url_for('unauthorized'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

---

## 4. API Structure Evolution

### Current Single-Page App → REST API

**Current Routes:**
```python
GET  /                    # Single page with forms and table
POST /add                 # Manual course entry  
POST /add_course_automatic # File upload
PUT  /edit_course/<id>    # Edit course
DELETE /delete_course/<id> # Delete course
```

**Target REST API Structure:**
```python
# Authentication
GET  /login              # Login page
POST /login              # Process login
POST /logout             # Logout

# Dashboard (role-based)
GET  /dashboard          # Main dashboard (role-dependent view)

# Users API
GET    /api/users        # List users (admin only)
POST   /api/users        # Create user (admin only)  
GET    /api/users/<id>   # Get user details
PUT    /api/users/<id>   # Update user
DELETE /api/users/<id>   # Delete user (admin only)

# Courses API
GET    /api/courses      # List courses
POST   /api/courses      # Create course
GET    /api/courses/<id> # Get course details
PUT    /api/courses/<id> # Update course
DELETE /api/courses/<id> # Delete course

# Course Sections API  
GET    /api/sections                    # List sections (filtered by role)
POST   /api/sections                    # Create section
GET    /api/sections/<id>               # Get section details
PUT    /api/sections/<id>               # Update section
DELETE /api/sections/<id>               # Delete section
POST   /api/sections/<id>/assign        # Assign instructor

# Course Outcomes API
GET    /api/outcomes                    # List outcomes
POST   /api/outcomes                    # Create outcome
GET    /api/outcomes/<id>               # Get outcome details  
PUT    /api/outcomes/<id>               # Update outcome
PUT    /api/outcomes/<id>/assessment    # Update assessment data

# Import API (existing pattern extended)
POST   /api/import/cei-excel            # CEI data import
GET    /api/import/status/<import_id>   # Import status
```

---

## 5. Implementation Sequence

### Week 1: Data Model & Database Service
**Days 1-2:**
- [ ] Design and document complete data model
- [ ] Extend `database_service.py` with new entity functions
- [ ] Create migration utilities for backward compatibility
- [ ] Add comprehensive unit tests for new functions

**Days 3-5:**
- [ ] Implement User management functions
- [ ] Implement Course and Term management
- [ ] Implement CourseSection management
- [ ] Test all new database operations

### Week 2: Authentication & Authorization  
**Days 1-3:**
- [ ] Set up Firebase Auth integration
- [ ] Implement login/logout functionality
- [ ] Add role-based access control decorators
- [ ] Create user registration/management UI

**Days 4-5:**
- [ ] Integrate authentication with existing routes
- [ ] Add session management
- [ ] Test authentication flow end-to-end

### Week 3: API Restructuring & UI Evolution
**Days 1-3:**
- [ ] Create new REST API endpoints
- [ ] Maintain backward compatibility with existing routes
- [ ] Add role-based dashboard views
- [ ] Test API endpoints

**Days 4-5:**
- [ ] Begin UI transformation (instructor dashboard)
- [ ] Add basic course section assignment interface
- [ ] Integration testing with new data model
- [ ] Prepare for CEI import adapter development

---

## 6. Success Criteria

### Technical Milestones
- [ ] All new database functions working with comprehensive tests
- [ ] Authentication system functional with role-based access
- [ ] REST API endpoints responding correctly
- [ ] Backward compatibility maintained (current system still works)
- [ ] New relational data model supports CEI requirements

### Business Validation
- [ ] Can create users with different roles
- [ ] Can assign instructors to course sections
- [ ] Can track course outcomes separately from sections
- [ ] Data model supports CEI's 1,543 CLO records structure
- [ ] Ready for CEI import adapter implementation

---

## 7. Risk Mitigation

### Technical Risks
- **Database migration complexity**: Use dual-model approach, test extensively
- **Authentication integration issues**: Start with simple email/password, add SSO later
- **Backward compatibility breaks**: Maintain existing routes during transition

### Timeline Risks  
- **Scope creep**: Focus on core entities first, defer advanced features
- **Testing overhead**: Build tests incrementally, not all at end
- **Integration complexity**: Test each component independently first

This plan provides a solid foundation for scaling your current system to meet CEI's enterprise requirements while maintaining the architectural strengths you've already built.
