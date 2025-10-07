# UAT: CRUD Operations Suite
**Comprehensive CRUD Functionality for All User Roles**

## Document Information
- **Version**: 1.0
- **Date**: October 2025
- **Purpose**: Plan and validate CRUD operations across all entities and user roles
- **Scope**: Create, Read, Update, Delete operations for all database entities
- **Status**: PLANNING (No code written yet)

---

## 📋 Executive Summary

### What This Initiative Delivers
This UAT suite implements and validates complete CRUD (Create, Read, Update, Delete) functionality for all entities in the Course Record Updater system. Currently, data can only enter the system via seed scripts or import files. This initiative adds:

1. **Database Layer**: Complete CRUD methods for all entities
2. **API Layer**: RESTful endpoints for all entities and operations
3. **Access Control**: Role-based permissions enforced at every level
4. **Comprehensive Testing**: Unit → Integration → E2E validation

### Current State
- ✅ Data integrity and access control fully validated (previous UAT)
- ✅ Role-based permissions defined in `auth_service.py`
- ✅ Import/Export functionality complete
- ⚠️ **Gap**: No UI-driven CRUD operations (add institution, create user, update program, etc.)
- ⚠️ **Gap**: Sparse database update/delete methods
- ⚠️ **Gap**: Few API PUT/DELETE endpoints

### Target State
- ✅ Full CRUD at database layer for all entities
- ✅ RESTful API endpoints for all entities
- ✅ Role-based access control enforced
- ✅ 100% test coverage (unit + integration + E2E)
- ✅ Users can perform all operations their role allows

---

## 🎯 Scope Definition

### Entities Covered
1. **Users** - Create, read, update, delete user accounts
2. **Institutions** - Manage institutions (site admin only)
3. **Programs** - Manage academic programs within institutions
4. **Courses** - Manage course catalog
5. **Terms** - Manage academic terms/semesters
6. **Course Offerings** - Manage course offerings for specific terms
7. **Course Sections** - Manage individual sections
8. **Course Outcomes (CLOs)** - Manage learning outcomes
9. **User Invitations** - Manage invitation workflow (bonus: covered by existing invitation_service)

### Operations Covered
For each entity above:
- **Create (C)**: Add new records
- **Read (R)**: List all, get by ID, get by filters (ALREADY MOSTLY DONE)
- **Update (U)**: Modify existing records
- **Delete (D)**: Remove records (with referential integrity)

### User Roles
1. **Site Admin** - Full access to everything
2. **Institution Admin** - Manage institution-scoped data
3. **Program Admin** - Manage program-scoped data
4. **Instructor** - Manage section-scoped data (limited CRUD)

### Out of Scope (For This Phase)
- ❌ Frontend UI components (focus on API functionality - pure API only)
- ❌ Batch operations beyond what's already implemented
- ❌ Soft deletes (hard deletes only for greenfield simplicity)

---

## 🔐 Access Control Matrix

### Who Can Do What?

#### Users (User Management)
| Operation | Site Admin | Inst. Admin | Prog. Admin | Instructor |
|-----------|------------|-------------|-------------|------------|
| Create User | ✅ All | ✅ Institution | ✅ Program | ❌ |
| Read User | ✅ All | ✅ Institution | ✅ Program | ✅ Self |
| Update User | ✅ All | ✅ Institution | ✅ Program (limited) | ✅ Self (profile only) |
| Delete User | ✅ All | ✅ Institution | ❌ | ❌ |

#### Institutions
| Operation | Site Admin | Inst. Admin | Prog. Admin | Instructor |
|-----------|------------|-------------|-------------|------------|
| Create Institution | ✅ | ❌ | ❌ | ❌ |
| Read Institution | ✅ All | ✅ Own | ✅ Own | ✅ Own |
| Update Institution | ✅ All | ✅ Own | ❌ | ❌ |
| Delete Institution | ✅ | ❌ | ❌ | ❌ |

#### Programs
| Operation | Site Admin | Inst. Admin | Prog. Admin | Instructor |
|-----------|------------|-------------|-------------|------------|
| Create Program | ✅ | ✅ | ❌ | ❌ |
| Read Program | ✅ All | ✅ Institution | ✅ Own | ✅ Associated |
| Update Program | ✅ All | ✅ Institution | ✅ Own | ❌ |
| Delete Program | ✅ All | ✅ Institution | ❌ | ❌ |

#### Courses
| Operation | Site Admin | Inst. Admin | Prog. Admin | Instructor |
|-----------|------------|-------------|-------------|------------|
| Create Course | ✅ | ✅ | ✅ | ❌ |
| Read Course | ✅ All | ✅ Institution | ✅ Program | ✅ Assigned |
| Update Course | ✅ All | ✅ Institution | ✅ Program | ❌ |
| Delete Course | ✅ All | ✅ Institution | ✅ Program | ❌ |

#### Terms
| Operation | Site Admin | Inst. Admin | Prog. Admin | Instructor |
|-----------|------------|-------------|-------------|------------|
| Create Term | ✅ | ✅ | ✅ | ❌ |
| Read Term | ✅ All | ✅ Institution | ✅ Program | ✅ All |
| Update Term | ✅ All | ✅ Institution | ✅ Program | ❌ |
| Delete Term | ✅ All | ✅ Institution | ❌ | ❌ |

#### Course Offerings
| Operation | Site Admin | Inst. Admin | Prog. Admin | Instructor |
|-----------|------------|-------------|-------------|------------|
| Create Offering | ✅ | ✅ | ✅ | ❌ |
| Read Offering | ✅ All | ✅ Institution | ✅ Program | ✅ Assigned |
| Update Offering | ✅ All | ✅ Institution | ✅ Program | ❌ |
| Delete Offering | ✅ All | ✅ Institution | ✅ Program | ❌ |

#### Course Sections
| Operation | Site Admin | Inst. Admin | Prog. Admin | Instructor |
|-----------|------------|-------------|-------------|------------|
| Create Section | ✅ | ✅ | ✅ | ❌ |
| Read Section | ✅ All | ✅ Institution | ✅ Program | ✅ Assigned |
| Update Section | ✅ All | ✅ Institution | ✅ Program | ✅ Own (limited) |
| Delete Section | ✅ All | ✅ Institution | ✅ Program | ❌ |

#### Course Outcomes (CLOs)
| Operation | Site Admin | Inst. Admin | Prog. Admin | Instructor |
|-----------|------------|-------------|-------------|------------|
| Create CLO | ✅ | ✅ | ✅ | ❌ |
| Read CLO | ✅ All | ✅ Institution | ✅ Program | ✅ Assigned |
| Update CLO | ✅ All | ✅ Institution | ✅ Program | ✅ Own (assessments) |
| Delete CLO | ✅ All | ✅ Institution | ✅ Program | ❌ |

### Permission Mapping
These operations map to permissions already defined in `auth_service.py`:
- `MANAGE_INSTITUTIONS` → Institution CRUD
- `MANAGE_USERS` / `MANAGE_INSTITUTION_USERS` / `MANAGE_PROGRAM_USERS` → User CRUD
- `MANAGE_PROGRAMS` → Program CRUD
- `MANAGE_COURSES` → Course, Offering, Section CRUD
- `MANAGE_TERMS` → Term CRUD
- `VIEW_*_DATA` → Read operations

---

## 🗄️ Layer 1: Database Operations

### Current State Analysis
**Existing Methods** (via `database_interface.py`):
- ✅ CREATE: `create_institution`, `create_user`, `create_course`, `create_term`, `create_program`, `create_course_offering`, `create_course_section`, `create_course_outcome`
- ✅ READ: Comprehensive get methods for all entities
- ⚠️ UPDATE: `update_user`, `update_program` (SPARSE)
- ⚠️ DELETE: `delete_program` (ONLY ONE)

### Missing Database Methods

#### Users (`database_sqlite.py` + `database_interface.py`)
```python
# Already Exists:
# - create_user(user_data) ✅
# - get_user_by_id(user_id) ✅
# - update_user(user_id, user_data) ✅ (basic)

# Need to Add:
def update_user_profile(user_id: str, profile_data: Dict[str, Any]) -> bool
    """Update user profile fields (first_name, last_name, display_name)"""
    
def update_user_role(user_id: str, new_role: str, program_ids: List[str]) -> bool
    """Update user's role and program associations"""
    
def delete_user(user_id: str) -> bool
    """Delete user (hard delete, check for dependencies)"""
    
def deactivate_user(user_id: str) -> bool
    """Soft delete: set account_status to 'suspended'"""
```

#### Institutions (`database_sqlite.py` + `database_interface.py`)
```python
# Already Exists:
# - create_institution(institution_data) ✅
# - create_new_institution(institution_data, admin_user_data) ✅
# - get_institution_by_id(institution_id) ✅

# Need to Add:
def update_institution(institution_id: str, institution_data: Dict[str, Any]) -> bool
    """Update institution details (name, short_name, settings)"""
    
def delete_institution(institution_id: str) -> bool
    """Delete institution (cascade delete all related data)"""
    # WARNING: This is DESTRUCTIVE - should require confirmation
```

#### Programs (`database_sqlite.py` + `database_interface.py`)
```python
# Already Exists:
# - create_program(program_data) ✅
# - get_program_by_id(program_id) ✅
# - update_program(program_id, program_data) ✅
# - delete_program(program_id) ✅

# Status: COMPLETE ✅ (but verify update_program handles all fields)
```

#### Courses (`database_sqlite.py` + `database_interface.py`)
```python
# Already Exists:
# - create_course(course_data) ✅
# - get_course_by_id(course_id) ✅

# Need to Add:
def update_course(course_id: str, course_data: Dict[str, Any]) -> bool
    """Update course details (title, department, credit_hours, active status)"""
    
def update_course_programs(course_id: str, program_ids: List[str]) -> bool
    """Update course's program associations"""
    
def delete_course(course_id: str) -> bool
    """Delete course (check for offerings/sections first)"""
```

#### Terms (`database_sqlite.py` + `database_interface.py`)
```python
# Already Exists:
# - create_term(term_data) ✅
# - get_term_by_id(term_id) ✅

# Need to Add:
def update_term(term_id: str, term_data: Dict[str, Any]) -> bool
    """Update term details (name, dates, active status)"""
    
def delete_term(term_id: str) -> bool
    """Delete term (check for offerings/sections first)"""
    
def archive_term(term_id: str) -> bool
    """Mark term as archived (soft delete)"""
```

#### Course Offerings (`database_sqlite.py` + `database_interface.py`)
```python
# Already Exists:
# - create_course_offering(offering_data) ✅
# - get_course_offering(offering_id) ✅

# Need to Add:
def update_course_offering(offering_id: str, offering_data: Dict[str, Any]) -> bool
    """Update offering details (status, capacity)"""
    
def delete_course_offering(offering_id: str) -> bool
    """Delete offering (cascade delete sections)"""
```

#### Course Sections (`database_sqlite.py` + `database_interface.py`)
```python
# Already Exists:
# - create_course_section(section_data) ✅
# - get_section_by_id(section_id) ✅

# Need to Add:
def update_course_section(section_id: str, section_data: Dict[str, Any]) -> bool
    """Update section details (instructor, enrollment, status)"""
    
def assign_instructor_to_section(section_id: str, instructor_id: str) -> bool
    """Assign/reassign instructor to section"""
    
def delete_course_section(section_id: str) -> bool
    """Delete section (check for assessment data first)"""
```

#### Course Outcomes (`database_sqlite.py` + `database_interface.py`)
```python
# Already Exists:
# - create_course_outcome(outcome_data) ✅
# - get_course_outcomes(course_id) ✅

# Need to Add:
def update_course_outcome(outcome_id: str, outcome_data: Dict[str, Any]) -> bool
    """Update CLO details (description, assessment_method)"""
    
def update_outcome_assessment_data(outcome_id: str, assessment_data: Dict[str, Any]) -> bool
    """Update assessment results (students_assessed, students_meeting, narrative)"""
    
def delete_course_outcome(outcome_id: str) -> bool
    """Delete CLO (check for assessment data first)"""
```

### Referential Integrity Considerations
When deleting entities, we need to handle dependencies:

**Institution Delete** → Cascade delete ALL related data (users, programs, courses, terms, offerings, sections)
**Program Delete** → Reassign courses to default program (ALREADY IMPLEMENTED ✅)
**Course Delete** → Block if offerings/sections exist (or cascade with warning)
**Term Delete** → Block if offerings/sections exist
**Offering Delete** → Cascade delete sections
**Section Delete** → Block if assessment data exists (or cascade with warning)
**User Delete** → Block if instructor with sections, or reassign sections

---

## 🌐 Layer 2: API Endpoints

### Existing API Endpoints Analysis
**Already Implemented**:
- ✅ `POST /api/institutions` - Create institution
- ✅ `GET /api/institutions` - List institutions
- ✅ `GET /api/institutions/<id>` - Get institution
- ✅ `POST /api/users` - Create user (STUB)
- ✅ `GET /api/users` - List users
- ✅ `GET /api/users/<id>` - Get user
- ✅ `POST /api/courses` - Create course
- ✅ `GET /api/courses` - List courses
- ✅ `POST /api/terms` - Create term
- ✅ `GET /api/terms` - List terms
- ✅ `POST /api/programs` - Create program
- ✅ `GET /api/programs` - List programs
- ✅ `GET /api/programs/<id>` - Get program
- ✅ `PUT /api/programs/<id>` - Update program
- ✅ `DELETE /api/programs/<id>` - Delete program
- ✅ `POST /api/sections` - Create section
- ✅ `GET /api/sections` - List sections

### Missing API Endpoints

#### Users API
```python
# POST /api/users - Already exists (STUB) - needs full implementation
# GET /api/users - Already exists ✅
# GET /api/users/<user_id> - Already exists ✅

# Need to Add:
PUT /api/users/<user_id>
    """Update user profile or role"""
    @permission_required("manage_users")
    # Payload: {first_name, last_name, display_name, role, program_ids}
    
DELETE /api/users/<user_id>
    """Delete user account"""
    @permission_required("manage_users")
    # Query param: ?deactivate=true for soft delete
    
PATCH /api/users/<user_id>/profile
    """Update user's own profile (self-service)"""
    @login_required
    # Payload: {first_name, last_name, display_name}
```

#### Institutions API
```python
# POST /api/institutions - Already exists ✅
# GET /api/institutions - Already exists ✅
# GET /api/institutions/<id> - Already exists ✅

# Need to Add:
PUT /api/institutions/<institution_id>
    """Update institution details"""
    @permission_required("manage_institutions")
    # Payload: {name, short_name, website_url, settings}
    
DELETE /api/institutions/<institution_id>
    """Delete institution (WARNING: DESTRUCTIVE)"""
    @permission_required("manage_institutions")
    # Query param: ?confirm=true required
```

#### Programs API
```python
# POST /api/programs - Already exists ✅
# GET /api/programs - Already exists ✅
# GET /api/programs/<id> - Already exists ✅
# PUT /api/programs/<id> - Already exists ✅
# DELETE /api/programs/<id> - Already exists ✅

# Status: COMPLETE ✅
```

#### Courses API
```python
# POST /api/courses - Already exists ✅
# GET /api/courses - Already exists (via programs endpoints) ✅

# Need to Add:
GET /api/courses/<course_id>
    """Get course details"""
    @permission_required("view_program_data")
    
PUT /api/courses/<course_id>
    """Update course details"""
    @permission_required("manage_courses")
    # Payload: {course_title, department, credit_hours, active, program_ids}
    
DELETE /api/courses/<course_id>
    """Delete course"""
    @permission_required("manage_courses")
    # Check for offerings/sections first
```

#### Terms API
```python
# POST /api/terms - Already exists ✅
# GET /api/terms - Already exists ✅

# Need to Add:
GET /api/terms/<term_id>
    """Get term details"""
    @permission_required("view_program_data")
    
PUT /api/terms/<term_id>
    """Update term details"""
    @permission_required("manage_terms")
    # Payload: {name, start_date, end_date, assessment_due_date, active}
    
DELETE /api/terms/<term_id>
    """Delete term"""
    @permission_required("manage_terms")
    # Check for offerings/sections first
    
POST /api/terms/<term_id>/archive
    """Archive term (soft delete)"""
    @permission_required("manage_terms")
```

#### Course Offerings API
```python
# Need to Add (NEW ENTITY ENDPOINTS):
POST /api/offerings
    """Create course offering"""
    @permission_required("manage_courses")
    # Payload: {course_id, term_id, status, capacity}
    
GET /api/offerings
    """List offerings (filtered by institution/program/term)"""
    @permission_required("view_program_data")
    
GET /api/offerings/<offering_id>
    """Get offering details"""
    @permission_required("view_program_data")
    
PUT /api/offerings/<offering_id>
    """Update offering details"""
    @permission_required("manage_courses")
    # Payload: {status, capacity}
    
DELETE /api/offerings/<offering_id>
    """Delete offering"""
    @permission_required("manage_courses")
```

#### Course Sections API
```python
# POST /api/sections - Already exists ✅
# GET /api/sections - Already exists ✅

# Need to Add:
GET /api/sections/<section_id>
    """Get section details"""
    @permission_required("view_section_data")
    
PUT /api/sections/<section_id>
    """Update section details"""
    @permission_required("manage_courses")
    # Payload: {instructor_id, enrollment, status}
    
PATCH /api/sections/<section_id>/instructor
    """Assign/reassign instructor"""
    @permission_required("manage_courses")
    # Payload: {instructor_id}
    
DELETE /api/sections/<section_id>
    """Delete section"""
    @permission_required("manage_courses")
```

#### Course Outcomes API
```python
# Need to Add (NEW ENTITY ENDPOINTS):
POST /api/courses/<course_id>/outcomes
    """Create CLO for course"""
    @permission_required("manage_courses")
    # Payload: {clo_number, description, assessment_method}
    
GET /api/courses/<course_id>/outcomes
    """List CLOs for course"""
    @permission_required("view_program_data")
    
GET /api/outcomes/<outcome_id>
    """Get CLO details"""
    @permission_required("view_program_data")
    
PUT /api/outcomes/<outcome_id>
    """Update CLO details"""
    @permission_required("manage_courses")
    # Payload: {description, assessment_method}
    
PUT /api/outcomes/<outcome_id>/assessment
    """Update CLO assessment data (instructor can do this)"""
    @permission_required("submit_assessments")
    # Payload: {students_assessed, students_meeting, percentage_meeting, narrative}
    
DELETE /api/outcomes/<outcome_id>
    """Delete CLO"""
    @permission_required("manage_courses")
```

### API Response Standards
All endpoints follow consistent patterns:
```json
// Success (200, 201)
{
  "success": true,
  "data": {...},
  "message": "Operation completed successfully"
}

// Error (400, 403, 404, 500)
{
  "success": false,
  "error": "Error message",
  "details": {...}  // Optional
}
```

---

## 🧪 Layer 3: Unit Tests

### Test Organization
```
tests/unit/
├── test_database_crud_users.py         # User CRUD operations
├── test_database_crud_institutions.py  # Institution CRUD operations
├── test_database_crud_programs.py      # Program CRUD operations (exists, enhance)
├── test_database_crud_courses.py       # Course CRUD operations
├── test_database_crud_terms.py         # Term CRUD operations
├── test_database_crud_offerings.py     # Offering CRUD operations
├── test_database_crud_sections.py      # Section CRUD operations
├── test_database_crud_outcomes.py      # Outcome CRUD operations
└── test_api_crud_*.py                  # API endpoint tests (one per entity)
```

### Unit Test Strategy

#### Database Layer Tests
For each entity, test all CRUD operations:

**Example: `test_database_crud_users.py`**
```python
class TestUserCRUD:
    def test_create_user_success(self):
        """Test creating a user with valid data"""
        
    def test_create_user_duplicate_email(self):
        """Test creating user with duplicate email fails"""
        
    def test_get_user_by_id_success(self):
        """Test retrieving user by ID"""
        
    def test_get_user_by_id_not_found(self):
        """Test retrieving non-existent user returns None"""
        
    def test_update_user_profile_success(self):
        """Test updating user profile fields"""
        
    def test_update_user_role_success(self):
        """Test updating user role and program associations"""
        
    def test_delete_user_success(self):
        """Test deleting user with no dependencies"""
        
    def test_delete_user_with_sections_blocked(self):
        """Test deleting instructor with sections is blocked"""
        
    def test_deactivate_user_success(self):
        """Test soft-deleting user (set status to suspended)"""
```

**Example: `test_database_crud_courses.py`**
```python
class TestCourseCRUD:
    def test_create_course_success(self):
        """Test creating a course with valid data"""
        
    def test_create_course_duplicate_number(self):
        """Test creating course with duplicate number fails"""
        
    def test_update_course_details_success(self):
        """Test updating course title, department, credit hours"""
        
    def test_update_course_programs_success(self):
        """Test updating course's program associations"""
        
    def test_delete_course_no_offerings_success(self):
        """Test deleting course with no offerings"""
        
    def test_delete_course_with_offerings_blocked(self):
        """Test deleting course with offerings is blocked"""
```

**Coverage Target**: 100% for all new database methods

#### API Layer Tests
For each API endpoint, test:
- Success cases (200, 201)
- Validation errors (400)
- Permission errors (403)
- Not found errors (404)
- Database errors (500)

**Example: `test_api_crud_users.py`**
```python
class TestUserAPI:
    def test_create_user_success_site_admin(self):
        """Site admin can create user in any institution"""
        
    def test_create_user_success_institution_admin(self):
        """Institution admin can create user in their institution"""
        
    def test_create_user_forbidden_program_admin(self):
        """Program admin cannot create institution-level users"""
        
    def test_update_user_success(self):
        """Test updating user via API"""
        
    def test_update_user_forbidden_cross_institution(self):
        """Institution admin cannot update users in other institutions"""
        
    def test_delete_user_success(self):
        """Test deleting user via API"""
        
    def test_delete_user_forbidden_insufficient_permissions(self):
        """Instructor cannot delete users"""
```

**Coverage Target**: All endpoints, all permission scenarios

---

## 🔗 Layer 4: Integration Tests

### Test Organization
```
tests/integration/
├── test_crud_workflows_users.py         # User CRUD workflows
├── test_crud_workflows_institutions.py  # Institution CRUD workflows
├── test_crud_workflows_programs.py      # Program CRUD workflows
├── test_crud_workflows_courses.py       # Course CRUD workflows
├── test_crud_workflows_sections.py      # Section management workflows
└── test_crud_workflows_full_cycle.py    # End-to-end entity lifecycle tests
```

### Integration Test Strategy
Test complete workflows that span multiple operations:

**Example: `test_crud_workflows_courses.py`**
```python
class TestCourseManagementWorkflows:
    def test_course_full_lifecycle(self):
        """Test create → read → update → delete course workflow"""
        # 1. Create course via API
        # 2. Verify course in database
        # 3. Update course details via API
        # 4. Verify updates in database
        # 5. Add course to program via API
        # 6. Create offering via API
        # 7. Delete offering via API
        # 8. Delete course via API
        # 9. Verify course removed from database
        
    def test_course_program_associations(self):
        """Test managing course-program relationships"""
        # 1. Create course
        # 2. Add to multiple programs
        # 3. Remove from one program
        # 4. Verify program associations
        
    def test_course_with_offerings_delete_blocked(self):
        """Test that course with offerings cannot be deleted"""
        # 1. Create course
        # 2. Create offering
        # 3. Attempt to delete course → expect 400
        # 4. Delete offering
        # 5. Delete course → success
```

**Example: `test_crud_workflows_sections.py`**
```python
class TestSectionManagementWorkflows:
    def test_instructor_assignment_workflow(self):
        """Test assigning/reassigning instructors to sections"""
        # 1. Create section without instructor
        # 2. Assign instructor via API
        # 3. Verify assignment in database
        # 4. Reassign to different instructor via API
        # 5. Verify reassignment
        
    def test_section_status_progression(self):
        """Test section status changes (assigned → in_progress → completed)"""
        # 1. Create section (status: assigned)
        # 2. Update status to in_progress
        # 3. Add assessment data
        # 4. Update status to completed
        # 5. Attempt to delete → blocked
```

**Example: `test_crud_workflows_full_cycle.py`**
```python
class TestFullEntityLifecycle:
    def test_new_institution_complete_setup(self):
        """Test setting up a new institution from scratch"""
        # 1. Create institution + admin user
        # 2. Create programs (via institution admin)
        # 3. Create courses
        # 4. Add courses to programs
        # 5. Create term
        # 6. Create offerings
        # 7. Create sections
        # 8. Assign instructors
        # 9. Verify dashboard data shows everything
        # 10. Export data and verify
```

**Coverage Target**: All critical workflows validated

---

## 🌐 Layer 5: End-to-End Tests

### Test Organization
```
tests/e2e/
├── test_crud_site_admin.py         # Site admin CRUD workflows
├── test_crud_institution_admin.py  # Institution admin CRUD workflows
├── test_crud_program_admin.py      # Program admin CRUD workflows
└── test_crud_instructor.py         # Instructor limited CRUD workflows
```

### E2E Test Strategy
Test complete user workflows with browser automation (Playwright/Selenium):

**Example: `test_crud_institution_admin.py`**
```python
class TestInstitutionAdminCRUD:
    def test_IA_create_program(self, page):
        """
        TC-CRUD-IA-001: Institution Admin creates new program
        
        Steps:
        1. Login as institution admin (CEI)
        2. Navigate to Programs page
        3. Click "Add Program" button
        4. Fill in form (name, short_name, description)
        5. Click "Save"
        6. Verify success message
        7. Verify program appears in list
        8. Verify program in database
        """
        
    def test_IA_update_course(self, page):
        """
        TC-CRUD-IA-002: Institution Admin updates course details
        
        Steps:
        1. Login as institution admin (CEI)
        2. Navigate to Courses page
        3. Click on existing course
        4. Click "Edit" button
        5. Update course title and credit hours
        6. Click "Save"
        7. Verify success message
        8. Verify updates appear in UI
        9. Verify updates in database
        """
        
    def test_IA_delete_empty_program(self, page):
        """
        TC-CRUD-IA-003: Institution Admin deletes program with no courses
        
        Steps:
        1. Login as institution admin (CEI)
        2. Create empty program via API
        3. Navigate to Programs page
        4. Click delete button on program
        5. Confirm deletion in modal
        6. Verify success message
        7. Verify program removed from list
        8. Verify program removed from database
        """
        
    def test_IA_cannot_delete_program_with_courses(self, page):
        """
        TC-CRUD-IA-004: Institution Admin cannot delete program with courses
        
        Steps:
        1. Login as institution admin (CEI)
        2. Navigate to Programs page with courses
        3. Click delete button on program with courses
        4. See error message about existing courses
        5. Verify program still exists
        """
        
    def test_IA_invite_instructor(self, page):
        """
        TC-CRUD-IA-005: Institution Admin invites new instructor
        
        Steps:
        1. Login as institution admin (CEI)
        2. Navigate to Users page
        3. Click "Invite User" button
        4. Fill in form (email, first_name, last_name, role=instructor)
        5. Click "Send Invitation"
        6. Verify success message
        7. Verify invitation in database
        8. Check invitation email sent (test email)
        """
```

**Example: `test_crud_program_admin.py`**
```python
class TestProgramAdminCRUD:
    def test_PA_create_course(self, page):
        """
        TC-CRUD-PA-001: Program Admin creates new course
        
        Steps:
        1. Login as program admin (Lisa - CS/EE)
        2. Navigate to Courses page
        3. Click "Add Course" button
        4. Fill in form (course_number, title, department)
        5. Select programs (CS, EE)
        6. Click "Save"
        7. Verify success message
        8. Verify course appears in list
        9. Verify course associated with correct programs
        """
        
    def test_PA_update_section_instructor(self, page):
        """
        TC-CRUD-PA-002: Program Admin reassigns instructor to section
        
        Steps:
        1. Login as program admin (Lisa - CS/EE)
        2. Navigate to Sections page
        3. Filter to CS courses
        4. Click on section with instructor
        5. Click "Reassign Instructor"
        6. Select different instructor from dropdown
        7. Click "Save"
        8. Verify success message
        9. Verify instructor updated in UI
        10. Verify instructor updated in database
        """
        
    def test_PA_cannot_delete_institution_user(self, page):
        """
        TC-CRUD-PA-003: Program Admin cannot delete institution admin
        
        Steps:
        1. Login as program admin (Lisa - CS/EE)
        2. Navigate to Users page
        3. Attempt to access delete action for institution admin
        4. Verify delete button not present OR
        5. Click delete → receive 403 Forbidden
        """
```

**Example: `test_crud_instructor.py`**
```python
class TestInstructorCRUD:
    def test_INST_update_own_profile(self, page):
        """
        TC-CRUD-INST-001: Instructor updates own profile
        
        Steps:
        1. Login as instructor (John)
        2. Navigate to Profile page
        3. Click "Edit Profile"
        4. Update first_name, last_name, display_name
        5. Click "Save"
        6. Verify success message
        7. Verify updates appear in UI
        8. Verify updates in database
        """
        
    def test_INST_update_section_assessment(self, page):
        """
        TC-CRUD-INST-002: Instructor updates CLO assessment data
        
        Steps:
        1. Login as instructor (John)
        2. Navigate to My Sections
        3. Click on assigned section
        4. Click on CLO to assess
        5. Fill in assessment data (students_assessed, students_meeting, narrative)
        6. Click "Save"
        7. Verify success message
        8. Verify data appears in UI
        9. Verify data in database
        """
        
    def test_INST_cannot_create_course(self, page):
        """
        TC-CRUD-INST-003: Instructor cannot create courses
        
        Steps:
        1. Login as instructor (John)
        2. Navigate to Courses page (if accessible)
        3. Verify "Add Course" button not present
        4. Attempt to POST /api/courses via console → 403
        """
```

**Coverage Target**: 
- All user roles exercised
- All CRUD operations validated via UI
- All permission boundaries tested
- Positive and negative test cases

---

## 📊 Test Data Strategy

### Test Data Creation
**Approach**: Use programmatic test data creation, not static files

**Fixtures** (`tests/conftest.py`):
```python
@pytest.fixture
def test_institution():
    """Create test institution"""
    return create_institution({
        "name": "Test University",
        "short_name": "TU",
        ...
    })

@pytest.fixture
def test_site_admin():
    """Create site admin user"""
    return create_user({
        "email": "siteadmin@test.local",
        "role": "site_admin",
        ...
    })

@pytest.fixture
def test_institution_admin(test_institution):
    """Create institution admin for test institution"""
    return create_user({
        "email": "admin@test.local",
        "role": "institution_admin",
        "institution_id": test_institution["institution_id"],
        ...
    })

@pytest.fixture
def test_course_with_program(test_institution, test_program):
    """Create test course associated with program"""
    course = create_course({
        "course_number": "TEST-101",
        "course_title": "Test Course",
        "institution_id": test_institution["institution_id"],
        "program_ids": [test_program["program_id"]],
        ...
    })
    return course
```

### Test Isolation
- Each test gets fresh database state (via `reset_database()`)
- No test depends on another test's data
- Cleanup handled by fixtures (no manual cleanup needed)

### Test Data Volume
- **Unit Tests**: Minimal (1-3 records per test)
- **Integration Tests**: Moderate (5-10 records per workflow)
- **E2E Tests**: Realistic (20+ records to simulate real environment)

---

## 📝 Implementation Checklist

### Phase 1: Database Layer (Week 1)
- [ ] **Users**
  - [ ] `update_user_profile()`
  - [ ] `update_user_role()`
  - [ ] `delete_user()`
  - [ ] `deactivate_user()`
  - [ ] Unit tests (8 tests)
  
- [ ] **Institutions**
  - [ ] `update_institution()`
  - [ ] `delete_institution()`
  - [ ] Unit tests (6 tests)
  
- [ ] **Courses**
  - [ ] `update_course()`
  - [ ] `update_course_programs()`
  - [ ] `delete_course()`
  - [ ] Unit tests (8 tests)
  
- [ ] **Terms**
  - [ ] `update_term()`
  - [ ] `delete_term()`
  - [ ] `archive_term()`
  - [ ] Unit tests (6 tests)
  
- [ ] **Course Offerings**
  - [ ] `update_course_offering()`
  - [ ] `delete_course_offering()`
  - [ ] Unit tests (6 tests)
  
- [ ] **Course Sections**
  - [ ] `update_course_section()`
  - [ ] `assign_instructor_to_section()`
  - [ ] `delete_course_section()`
  - [ ] Unit tests (8 tests)
  
- [ ] **Course Outcomes**
  - [ ] `update_course_outcome()`
  - [ ] `update_outcome_assessment_data()`
  - [ ] `delete_course_outcome()`
  - [ ] Unit tests (6 tests)

**Subtotal: ~48 unit tests**

### Phase 2: API Layer (Week 2)
- [ ] **Users API**
  - [ ] `PUT /api/users/<user_id>` (update user)
  - [ ] `DELETE /api/users/<user_id>` (delete user)
  - [ ] `PATCH /api/users/<user_id>/profile` (self-service profile update)
  - [ ] Unit tests (12 tests)
  
- [ ] **Institutions API**
  - [ ] `PUT /api/institutions/<institution_id>` (update institution)
  - [ ] `DELETE /api/institutions/<institution_id>` (delete institution)
  - [ ] Unit tests (8 tests)
  
- [ ] **Courses API**
  - [ ] `GET /api/courses/<course_id>` (get course)
  - [ ] `PUT /api/courses/<course_id>` (update course)
  - [ ] `DELETE /api/courses/<course_id>` (delete course)
  - [ ] Unit tests (12 tests)
  
- [ ] **Terms API**
  - [ ] `GET /api/terms/<term_id>` (get term)
  - [ ] `PUT /api/terms/<term_id>` (update term)
  - [ ] `DELETE /api/terms/<term_id>` (delete term)
  - [ ] `POST /api/terms/<term_id>/archive` (archive term)
  - [ ] Unit tests (12 tests)
  
- [ ] **Offerings API**
  - [ ] `POST /api/offerings` (create offering)
  - [ ] `GET /api/offerings` (list offerings)
  - [ ] `GET /api/offerings/<offering_id>` (get offering)
  - [ ] `PUT /api/offerings/<offering_id>` (update offering)
  - [ ] `DELETE /api/offerings/<offering_id>` (delete offering)
  - [ ] Unit tests (15 tests)
  
- [ ] **Sections API**
  - [ ] `GET /api/sections/<section_id>` (get section)
  - [ ] `PUT /api/sections/<section_id>` (update section)
  - [ ] `PATCH /api/sections/<section_id>/instructor` (assign instructor)
  - [ ] `DELETE /api/sections/<section_id>` (delete section)
  - [ ] Unit tests (12 tests)
  
- [ ] **Outcomes API**
  - [ ] `POST /api/courses/<course_id>/outcomes` (create outcome)
  - [ ] `GET /api/courses/<course_id>/outcomes` (list outcomes)
  - [ ] `GET /api/outcomes/<outcome_id>` (get outcome)
  - [ ] `PUT /api/outcomes/<outcome_id>` (update outcome)
  - [ ] `PUT /api/outcomes/<outcome_id>/assessment` (update assessment)
  - [ ] `DELETE /api/outcomes/<outcome_id>` (delete outcome)
  - [ ] Unit tests (18 tests)

**Subtotal: ~89 unit tests**

### Phase 3: Integration Tests (Week 3)
- [ ] **User Workflows** (5 tests)
  - [ ] User full lifecycle (create → update → delete)
  - [ ] User role change workflow
  - [ ] Instructor with sections delete blocked
  - [ ] User deactivation workflow
  - [ ] Cross-institution permission validation
  
- [ ] **Institution Workflows** (3 tests)
  - [ ] Institution creation with admin
  - [ ] Institution update workflow
  - [ ] Institution delete with cascade
  
- [ ] **Program Workflows** (4 tests)
  - [ ] Program full lifecycle
  - [ ] Program-course associations
  - [ ] Program delete with course reassignment
  - [ ] Program admin assignments
  
- [ ] **Course Workflows** (5 tests)
  - [ ] Course full lifecycle
  - [ ] Course-program associations
  - [ ] Course with offerings delete blocked
  - [ ] Course update propagation
  - [ ] Course catalog management
  
- [ ] **Section Workflows** (4 tests)
  - [ ] Section full lifecycle
  - [ ] Instructor assignment workflow
  - [ ] Section status progression
  - [ ] Section with assessments delete blocked
  
- [ ] **Full Cycle Workflows** (4 tests)
  - [ ] New institution complete setup
  - [ ] Term lifecycle with offerings
  - [ ] Instructor course assignment workflow
  - [ ] Assessment submission workflow

**Subtotal: ~25 integration tests**

### Phase 4: E2E Tests (Week 4)
- [ ] **Site Admin CRUD** (8 tests)
  - [ ] Create institution via UI
  - [ ] Update institution settings
  - [ ] Create institution admin
  - [ ] Manage global users
  - [ ] View all data across institutions
  - [ ] Delete empty institution
  - [ ] System-wide reporting
  - [ ] Multi-institution workflows
  
- [ ] **Institution Admin CRUD** (10 tests)
  - [ ] Create program
  - [ ] Update course details
  - [ ] Delete empty program
  - [ ] Cannot delete program with courses
  - [ ] Invite instructor
  - [ ] Manage institution users
  - [ ] Create term
  - [ ] Create course offerings
  - [ ] Assign instructors to sections
  - [ ] Cannot access other institutions
  
- [ ] **Program Admin CRUD** (6 tests)
  - [ ] Create course
  - [ ] Update section instructor
  - [ ] Cannot delete institution user
  - [ ] Manage program courses
  - [ ] Create sections
  - [ ] Cannot access other programs
  
- [ ] **Instructor CRUD** (4 tests)
  - [ ] Update own profile
  - [ ] Update section assessment
  - [ ] Cannot create courses
  - [ ] Cannot manage users

**Subtotal: ~28 E2E tests**

### Phase 5: Documentation & Review (Week 5)
- [ ] Update `STATUS.md` with implementation details
- [ ] Update `PROJECT_STRUCTURE.md` with new endpoints
- [ ] Update `SITE_MAP.md` with new UI pages (if any)
- [ ] Create `CRUD_API_REFERENCE.md` (comprehensive API docs)
- [ ] Run full test suite (unit + integration + E2E)
- [ ] Run quality gates (`ship_it.py --validation-type PR`)
- [ ] Code review and refinements
- [ ] Prepare for merge to main

---

## 🎯 Success Criteria

### Functional Completeness
- [ ] All 7 entities have full CRUD operations at database layer
- [ ] All 7 entities have RESTful API endpoints
- [ ] All 4 user roles can perform authorized operations
- [ ] All unauthorized operations are properly blocked (403)

### Test Coverage
- [ ] Database layer: 100% coverage on new methods (~48 tests)
- [ ] API layer: 100% coverage on new endpoints (~89 tests)
- [ ] Integration tests: All workflows validated (~25 tests)
- [ ] E2E tests: All user roles validated (~28 tests)
- [ ] **Total**: ~190 tests

### Quality Gates
- [ ] All tests passing (pytest)
- [ ] No linter errors (flake8, pylint)
- [ ] Type checking passes (mypy)
- [ ] Security scan passes (bandit)
- [ ] Coverage ≥ 80% (pytest-cov)
- [ ] SonarCloud quality gate passes

### Documentation
- [ ] All new functions have docstrings
- [ ] API endpoints documented with examples
- [ ] Permission requirements clearly documented
- [ ] UAT test cases documented with steps

---

## ✅ Design Decisions (APPROVED)

### 1. Delete Strategy
**Decision**: Hard delete only (for now)
- Remove records from database permanently
- Cascade delete dependencies where appropriate
- **Future Enhancement**: Database backup/restore system for rollbacks (added to NEXT_BACKLOG.md)

### 2. Referential Integrity on Delete
**Decision**: Block delete by default, allow force delete with warnings
- **Courses with Offerings**: Block delete (use `?force=true` to cascade)
- **Sections with Assessment Data**: Block delete (use `?force=true` to cascade)
- **Users who are Instructors**: Block delete OR reassign sections
- **Programs with Courses**: Keep existing behavior (reassign to default program) ✅

### 3. Instructor Update Permissions
**Decision**: YES - Instructors can update enrollment numbers
- Instructors know the real enrollment count
- Can update assessment data (their primary job)
- Cannot update section status (admin-controlled)
- Cannot add/remove students (admin-controlled)

### 4. Program Admin Scope
**Decision**: YES - Program admins manage ALL their programs
- Can manage courses across all assigned programs
- Can create courses and auto-assign to their programs
- Can reassign instructors between their programs

### 5. Course-Program Associations (Program Delete)
**Decision**: Keep existing behavior (reassign to default program)
- Already implemented in `delete_program()` ✅
- Already tested and validated ✅
- Default "Unclassified" program serves this purpose
- Cleaner than orphaned courses or blocking delete

### 6. Institution Delete Cascade
**Decision**: Site admin only, must type "i know what I'm doing"
- Only site_admin role can delete institutions
- Requires typing exact phrase: "i know what I'm doing"
- Cascade deletes ALL related data (DESTRUCTIVE and IRREVERSIBLE)
- Warning message explains consequences

### 7. API Versioning
**Decision**: NOT YET - No API versioning for now
- Greenfield project with no backward compatibility concerns
- Can add versioning later if needed (e.g., `/api/v1/` prefix)

### 8. Batch Operations Priority
**Decision**: NOT IN THIS PHASE - Defer batch operations
- Focus on core CRUD operations first
- Add batch operations later based on user needs (YAGNI)

### 9. Audit Logging (NEW)
**Decision**: Comprehensive audit logging from ground up
- Audit all CUD operations (Create, Update, Delete) - Read is too noisy
- Store in dedicated `audit_log` table
- UI access via site admin dashboard (panel already exists)
- Export functionality for compliance
- Retain audit logs forever (no deletion)

---

## 📋 Audit Logging System

### Overview
Comprehensive audit logging for all CRUD operations to provide:
- **Data Lineage**: Track where each change originated
- **Compliance**: Full audit trail for institutional requirements
- **Debugging**: Investigate issues and understand system state changes
- **Rollback Context**: Know what changed before implementing backup/restore (future)

### Database Schema

#### `audit_log` Table
```sql
CREATE TABLE audit_log (
    audit_id TEXT PRIMARY KEY,           -- UUID
    timestamp DATETIME NOT NULL,         -- When operation occurred (UTC)
    
    -- Who performed the action
    user_id TEXT,                        -- User who made the change (NULL for system)
    user_email TEXT,                     -- Email for quick reference
    user_role TEXT,                      -- Role at time of action
    
    -- What was done
    operation_type TEXT NOT NULL,        -- CREATE, UPDATE, DELETE
    entity_type TEXT NOT NULL,           -- users, institutions, programs, courses, etc.
    entity_id TEXT NOT NULL,             -- ID of affected entity
    
    -- Change details
    old_values TEXT,                     -- JSON: Previous state (NULL for CREATE)
    new_values TEXT,                     -- JSON: New state (NULL for DELETE)
    changed_fields TEXT,                 -- JSON array: ["field1", "field2"] (UPDATE only)
    
    -- Context
    source_type TEXT NOT NULL,           -- API, IMPORT, SYSTEM, SCRIPT
    source_details TEXT,                 -- Additional context (e.g., "CEI Excel Import", "Manual Edit")
    ip_address TEXT,                     -- Client IP (if from API request)
    user_agent TEXT,                     -- Client user agent (if from API request)
    
    -- Request tracking
    request_id TEXT,                     -- Group related operations in single request
    session_id TEXT,                     -- User session ID
    
    -- Institution context (for multi-tenant filtering)
    institution_id TEXT,                 -- Institution context (NULL for site-wide ops)
    
    -- Indexing for common queries
    INDEX idx_timestamp ON audit_log(timestamp DESC),
    INDEX idx_user_id ON audit_log(user_id),
    INDEX idx_entity ON audit_log(entity_type, entity_id),
    INDEX idx_operation ON audit_log(operation_type),
    INDEX idx_institution ON audit_log(institution_id)
);
```

### Audit Event Types

```python
# audit_service.py

from enum import Enum
from typing import Any, Dict, Optional
import uuid
from datetime import datetime, timezone
import json

class OperationType(Enum):
    """Types of auditable operations"""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

class EntityType(Enum):
    """Types of entities we audit"""
    USER = "users"
    INSTITUTION = "institutions"
    PROGRAM = "programs"
    COURSE = "courses"
    TERM = "terms"
    OFFERING = "course_offerings"
    SECTION = "course_sections"
    OUTCOME = "course_outcomes"
    INVITATION = "user_invitations"

class SourceType(Enum):
    """Where the operation originated"""
    API = "API"           # From API request
    IMPORT = "IMPORT"     # From data import
    SYSTEM = "SYSTEM"     # Automated system action
    SCRIPT = "SCRIPT"     # From management script

class AuditService:
    """Service for creating and querying audit logs"""
    
    @staticmethod
    def log_create(
        entity_type: EntityType,
        entity_id: str,
        new_values: Dict[str, Any],
        user_id: Optional[str] = None,
        institution_id: Optional[str] = None,
        source_type: SourceType = SourceType.API,
        source_details: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log entity creation
        
        Args:
            entity_type: Type of entity created
            entity_id: ID of created entity
            new_values: Complete entity state after creation
            user_id: User who created (NULL for system)
            institution_id: Institution context
            source_type: Where operation originated
            source_details: Additional context
            request_context: Request metadata (IP, user agent, etc.)
            
        Returns:
            audit_id: ID of created audit log entry
        """
        
    @staticmethod
    def log_update(
        entity_type: EntityType,
        entity_id: str,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
        user_id: Optional[str] = None,
        institution_id: Optional[str] = None,
        source_type: SourceType = SourceType.API,
        source_details: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log entity update
        
        Args:
            entity_type: Type of entity updated
            entity_id: ID of updated entity
            old_values: Entity state before update
            new_values: Entity state after update
            user_id: User who updated (NULL for system)
            institution_id: Institution context
            source_type: Where operation originated
            source_details: Additional context
            request_context: Request metadata
            
        Returns:
            audit_id: ID of created audit log entry
        """
        
    @staticmethod
    def log_delete(
        entity_type: EntityType,
        entity_id: str,
        old_values: Dict[str, Any],
        user_id: Optional[str] = None,
        institution_id: Optional[str] = None,
        source_type: SourceType = SourceType.API,
        source_details: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log entity deletion
        
        Args:
            entity_type: Type of entity deleted
            entity_id: ID of deleted entity
            old_values: Entity state before deletion
            user_id: User who deleted (NULL for system)
            institution_id: Institution context
            source_type: Where operation originated
            source_details: Additional context
            request_context: Request metadata
            
        Returns:
            audit_id: ID of created audit log entry
        """
        
    @staticmethod
    def get_entity_history(
        entity_type: EntityType,
        entity_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get audit history for specific entity"""
        
    @staticmethod
    def get_user_activity(
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all activity by specific user"""
        
    @staticmethod
    def get_recent_activity(
        institution_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent system activity (for dashboard)"""
        
    @staticmethod
    def export_audit_log(
        start_date: datetime,
        end_date: datetime,
        entity_type: Optional[EntityType] = None,
        user_id: Optional[str] = None,
        institution_id: Optional[str] = None,
        format: str = "csv"
    ) -> bytes:
        """Export audit logs for compliance/analysis"""
```

### Integration Points

#### Database Layer Integration
Every CRUD method in `database_sqlite.py` calls audit logging:

```python
# Example: database_sqlite.py

def update_course(self, course_id: str, course_data: Dict[str, Any]) -> bool:
    """Update course with audit logging"""
    try:
        # Get old values BEFORE update
        old_course = self.get_course_by_id(course_id)
        if not old_course:
            return False
            
        # Perform update
        session = self.get_session()
        course = session.query(CourseModel).filter_by(course_id=course_id).first()
        if not course:
            return False
            
        # Update fields
        for key, value in course_data.items():
            if hasattr(course, key):
                setattr(course, key, value)
        
        session.commit()
        
        # Get new values AFTER update
        new_course = self.get_course_by_id(course_id)
        
        # LOG THE CHANGE
        from audit_service import AuditService, EntityType, SourceType
        from auth_service import get_current_user_id
        
        AuditService.log_update(
            entity_type=EntityType.COURSE,
            entity_id=course_id,
            old_values=old_course,
            new_values=new_course,
            user_id=get_current_user_id(),  # From Flask session
            institution_id=course_data.get('institution_id'),
            source_type=SourceType.API
        )
        
        return True
        
    except Exception as e:
        session.rollback()
        logger.error(f"Update course failed: {e}")
        return False
```

#### API Layer Integration
API routes extract request context and pass to audit logging:

```python
# Example: api_routes.py

@api.route("/courses/<course_id>", methods=["PUT"])
@permission_required("manage_courses")
def update_course_api(course_id: str):
    """Update course with full audit context"""
    try:
        data = request.get_json()
        
        # Update course (this calls audit logging internally)
        success = update_course(course_id, data)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Course updated successfully"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Course not found"
            }), 404
            
    except Exception as e:
        return handle_api_error(e, "Update course", "Failed to update course")
```

### UI Access (Site Admin Dashboard)

**Existing UI Panel**: `templates/dashboard/site_admin_panels.html` lines 70-95
- Panel already exists with "Recent System Activity" heading
- Has buttons for "View All" and "Filter"
- Currently shows loading spinner (not implemented)

**Implementation Needed**:
```javascript
// static/audit.js

async function loadRecentActivity() {
    const response = await fetch('/api/audit/recent?limit=50');
    const data = await response.json();
    
    const container = document.getElementById('activityTableContainer');
    container.innerHTML = renderActivityTable(data.activities);
}

function renderActivityTable(activities) {
    return `
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Entity</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                ${activities.map(renderActivityRow).join('')}
            </tbody>
        </table>
    `;
}

function renderActivityRow(activity) {
    const icon = getOperationIcon(activity.operation_type);
    const color = getOperationColor(activity.operation_type);
    
    return `
        <tr>
            <td>${formatTimestamp(activity.timestamp)}</td>
            <td>
                <span class="user-badge" data-role="${activity.user_role}">
                    ${activity.user_email || 'System'}
                </span>
            </td>
            <td>
                <span class="badge bg-${color}">
                    ${icon} ${activity.operation_type}
                </span>
            </td>
            <td>
                <a href="#" onclick="viewEntity('${activity.entity_type}', '${activity.entity_id}')">
                    ${activity.entity_type} #${activity.entity_id.substring(0, 8)}
                </a>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-secondary" 
                        onclick="viewAuditDetails('${activity.audit_id}')">
                    View Details
                </button>
            </td>
        </tr>
    `;
}
```

### API Endpoints for Audit Logging

```python
# api_routes.py

@api.route("/audit/recent", methods=["GET"])
@permission_required("view_all_data")  # Site admin only
def get_recent_audit_activity():
    """Get recent system activity for dashboard"""
    try:
        limit = request.args.get('limit', 50, type=int)
        institution_id = get_current_institution_id()  # NULL for site admin
        
        activities = AuditService.get_recent_activity(
            institution_id=institution_id,
            limit=limit
        )
        
        return jsonify({
            "success": True,
            "activities": activities,
            "count": len(activities)
        }), 200
        
    except Exception as e:
        return handle_api_error(e, "Get audit activity", "Failed to retrieve activity")

@api.route("/audit/entity/<entity_type>/<entity_id>", methods=["GET"])
@permission_required("view_program_data")  # Any admin role
def get_entity_audit_history(entity_type: str, entity_id: str):
    """Get audit history for specific entity"""
    try:
        history = AuditService.get_entity_history(
            entity_type=EntityType(entity_type),
            entity_id=entity_id,
            limit=100
        )
        
        return jsonify({
            "success": True,
            "history": history,
            "count": len(history)
        }), 200
        
    except Exception as e:
        return handle_api_error(e, "Get entity history", "Failed to retrieve history")

@api.route("/audit/export", methods=["POST"])
@permission_required("view_all_data")  # Site admin only
def export_audit_log():
    """Export audit logs for compliance"""
    try:
        data = request.get_json()
        start_date = datetime.fromisoformat(data['start_date'])
        end_date = datetime.fromisoformat(data['end_date'])
        
        export_data = AuditService.export_audit_log(
            start_date=start_date,
            end_date=end_date,
            entity_type=data.get('entity_type'),
            user_id=data.get('user_id'),
            institution_id=data.get('institution_id'),
            format=data.get('format', 'csv')
        )
        
        return Response(
            export_data,
            mimetype='text/csv' if data.get('format') == 'csv' else 'application/json',
            headers={
                'Content-Disposition': f'attachment; filename=audit_log_{start_date}_{end_date}.csv'
            }
        ), 200
        
    except Exception as e:
        return handle_api_error(e, "Export audit log", "Failed to export audit log")

@api.route("/audit/user/<user_id>", methods=["GET"])
@permission_required("view_institution_data")  # Institution admin+
def get_user_audit_activity(user_id: str):
    """Get all activity by specific user"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        activity = AuditService.get_user_activity(
            user_id=user_id,
            start_date=datetime.fromisoformat(start_date) if start_date else None,
            end_date=datetime.fromisoformat(end_date) if end_date else None,
            limit=100
        )
        
        return jsonify({
            "success": True,
            "activity": activity,
            "count": len(activity)
        }), 200
        
    except Exception as e:
        return handle_api_error(e, "Get user activity", "Failed to retrieve user activity")
```

### Sensitive Data Exclusion

**Never log sensitive data in audit logs:**
```python
def sanitize_for_audit(entity_data: Dict[str, Any], entity_type: EntityType) -> Dict[str, Any]:
    """Remove sensitive fields before audit logging"""
    sensitive_fields = [
        'password',
        'password_hash',
        'password_reset_token',
        'email_verification_token',
        'oauth_id',
        'oauth_token',
        'api_key',
        'secret_key'
    ]
    
    sanitized = entity_data.copy()
    for field in sensitive_fields:
        if field in sanitized:
            sanitized[field] = '[REDACTED]'
    
    return sanitized
```

### Test Strategy for Audit Logging

#### Unit Tests (`test_audit_service.py`)
```python
class TestAuditService:
    def test_log_create_success(self):
        """Test logging entity creation"""
        
    def test_log_update_tracks_changes(self):
        """Test logging entity update with field changes"""
        
    def test_log_delete_preserves_state(self):
        """Test logging entity deletion with final state"""
        
    def test_get_entity_history(self):
        """Test retrieving entity audit history"""
        
    def test_get_recent_activity_filters_by_institution(self):
        """Test recent activity respects institution context"""
        
    def test_sensitive_data_redacted(self):
        """Test password fields are redacted in audit logs"""
        
    def test_export_audit_log_csv_format(self):
        """Test exporting audit logs as CSV"""
```

#### Integration Tests (`test_crud_workflows_audit.py`)
```python
class TestAuditIntegration:
    def test_course_crud_generates_audit_trail(self):
        """Test creating/updating/deleting course logs to audit"""
        # 1. Create course via API
        # 2. Verify CREATE audit log entry exists
        # 3. Update course via API
        # 4. Verify UPDATE audit log entry exists
        # 5. Delete course via API
        # 6. Verify DELETE audit log entry exists
        # 7. Verify all entries have correct user context
        
    def test_audit_history_shows_entity_lifecycle(self):
        """Test get_entity_history returns complete timeline"""
        # 1. Create entity
        # 2. Update 3 times
        # 3. Get entity history
        # 4. Verify 4 entries (1 create + 3 updates)
        # 5. Verify chronological order
        
    def test_institution_admin_sees_only_their_activity(self):
        """Test audit log filtering by institution"""
        # 1. CEI admin updates CEI course
        # 2. RCC admin updates RCC course
        # 3. CEI admin calls /api/audit/recent
        # 4. Verify only sees CEI activity
```

#### E2E Tests (`test_audit_ui.py`)
```python
class TestAuditUI:
    def test_site_admin_views_recent_activity(self, page):
        """
        TC-AUDIT-001: Site admin views recent system activity
        
        Steps:
        1. Login as site admin
        2. Navigate to dashboard
        3. Click "Recent System Activity" panel
        4. Verify activity table loads
        5. Verify shows activity from all institutions
        6. Verify shows operation types (CREATE, UPDATE, DELETE)
        7. Verify shows user info and timestamps
        """
        
    def test_site_admin_exports_audit_log(self, page):
        """
        TC-AUDIT-002: Site admin exports audit log for compliance
        
        Steps:
        1. Login as site admin
        2. Navigate to Recent System Activity panel
        3. Click "Export" button
        4. Select date range
        5. Select format (CSV)
        6. Click "Download"
        7. Verify CSV file downloads
        8. Verify CSV contains expected columns
        9. Verify sensitive data is redacted
        """
        
    def test_view_entity_audit_history(self, page):
        """
        TC-AUDIT-003: User views audit history for specific entity
        
        Steps:
        1. Login as institution admin
        2. Navigate to Courses page
        3. Click on specific course
        4. Click "History" button
        5. Verify audit history modal opens
        6. Verify shows all changes to course
        7. Verify shows before/after values
        8. Verify shows user who made each change
        """
```

### Audit Log Retention

**Decision**: Retain audit logs forever (no automatic deletion)
- Compliance requirements often mandate long retention
- Storage cost is minimal for text data
- Can implement archival strategy later if needed

**Future Enhancement** (not in this phase):
- Archive old audit logs to separate table/storage
- Compress archived logs
- Implement data lifecycle management

---

## 📅 Estimated Timeline

### 5-Week Implementation Plan

**Week 1: Database Layer**
- Days 1-2: Users, Institutions
- Days 3-4: Courses, Terms
- Day 5: Offerings, Sections, Outcomes

**Week 2: API Layer**
- Days 1-2: Users, Institutions, Courses API
- Days 3-4: Terms, Offerings, Sections API
- Day 5: Outcomes API + API tests

**Week 3: Integration Tests**
- Days 1-2: Entity lifecycle workflows
- Days 3-4: Cross-entity workflows
- Day 5: Full cycle workflows

**Week 4: E2E Tests**
- Days 1-2: Site Admin + Institution Admin flows
- Days 3-4: Program Admin + Instructor flows
- Day 5: Negative testing + permission boundaries

**Week 5: Polish & Ship**
- Days 1-2: Documentation updates
- Days 3-4: Quality gates + code review
- Day 5: Final testing + merge

**Total Effort**: ~5 weeks (assuming full-time focus)

---

## 🚀 Next Steps

1. **User Answers Questions** → Resolve design decisions
2. **Create Todos** → Break down into granular tasks
3. **Start with Database Layer** → Implement all CRUD methods + unit tests
4. **Then API Layer** → Add endpoints + unit tests
5. **Integration Tests** → Validate workflows
6. **E2E Tests** → Full user validation
7. **Ship It** → Quality gates + merge

---

*This is a comprehensive planning document. No code has been written yet. All implementation will follow after user approval and question resolution.*


