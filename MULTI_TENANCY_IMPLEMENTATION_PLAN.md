# Multi-Tenancy Implementation Plan
**Project**: Course Record Updater
**Date**: September 13, 2025
**Objective**: Transform single-tenant CEI system into multi-tenant architecture

---

## Executive Summary

The current system is designed exclusively for CEI (College of Eastern Idaho) with all data belonging to a single institution. We need to implement multi-tenancy to support multiple institutions while maintaining backward compatibility and data isolation.

### Key Changes Required:
1. **Data Model**: Add `institution_id` to all entity collections
2. **Authentication**: Add institution context to user sessions
3. **Data Access**: Filter all queries by institution
4. **API Layer**: Enforce institution-based access control
5. **Import System**: Associate imported data with institutions
6. **UI/UX**: Add institution selection and context switching

---

## Current State Analysis

### Database Collections (Current):
- `courses` - No institution association
- `users` - No institution association  
- `terms` - No institution association
- `course_sections` - No institution association
- `course_outcomes` - No institution association

### Authentication (Current):
- Stub implementation returning mock CEI admin user
- No institution context in user sessions
- No institution-based permission checking

### Data Access Patterns (Current):
- `get_all_courses()` returns ALL courses globally
- `get_all_instructors()` returns ALL instructors globally
- No institution filtering in any database queries
- API endpoints return global data without tenant filtering

---

## Updated Implementation Strategy

### Institution Creation Workflow

**Key Decision**: Simplified single-institution-per-user model
- Users belong to exactly one institution
- Institution admins are created during institution setup
- No cross-institution users (keeps pricing and data isolation simple)
- Pricing based on number of instructor seats per institution

**New User Registration Flow**:
1. User visits website → "Create Institution Account" 
2. User enters institution details (name, domain, etc.)
3. System creates new institution record
4. User becomes the first admin for that institution
5. Admin can then invite instructors to their institution
6. Admin can promote instructors to admin status if needed

**Benefits**:
- Simple data isolation (one institution_id per user)
- Clear pricing model (instructor seats per institution)
- No complex cross-institution permission logic
- Easy to understand and implement

### Phase 1: Data Model Foundation (High Priority)
**Duration**: 2-3 days  
**Risk**: High - Requires database schema changes

#### 1.1 Add Institution Collection
```javascript
// New Firestore collection: institutions
{
  institution_id: "cei-12345",
  name: "College of Eastern Idaho", 
  short_name: "CEI",
  domain: "cei.edu",
  timezone: "America/Denver",
  created_at: timestamp,
  is_active: true,
  billing_settings: {
    instructor_seat_limit: 50,
    current_instructor_count: 12,
    subscription_status: "active"
  },
  settings: {
    default_credit_hours: 3,
    academic_year_start_month: 8,
    grading_scale: "traditional"
  }
}
```

#### 1.2 Update All Entity Collections
Add `institution_id` field to every collection:

**Users Collection:**
```javascript
{
  user_id: "uuid",
  institution_id: "cei-12345",  // NEW REQUIRED FIELD - exactly one institution
  email: "john@cei.edu",
  role: "instructor",  // instructor, admin, site_admin
  is_institution_admin: false,  // can manage this institution
  created_by: "admin_user_id",  // who invited this user
  invitation_status: "accepted",  // pending, accepted, expired
  // ... existing fields
}
```

**Courses Collection:**
```javascript
{
  course_id: "uuid", 
  institution_id: "cei-12345",  // NEW REQUIRED FIELD
  course_number: "MATH-101",
  // ... existing fields
}
```

**Apply same pattern to**: `terms`, `course_sections`, `course_outcomes`

#### 1.3 Create Composite Indexes
```javascript
// Required Firestore composite indexes
courses: [institution_id, active]
courses: [institution_id, department] 
users: [institution_id, role]
course_sections: [institution_id, term_id]
course_sections: [institution_id, instructor_id]
terms: [institution_id, active]
```

### Phase 2: Database Service Layer (High Priority)
**Duration**: 2-3 days
**Risk**: Medium - Requires careful query updates

#### 2.1 Add Institution Management Functions
```python
# New functions in database_service.py

def create_institution(institution_data: Dict[str, Any]) -> Optional[str]:
    """Create a new institution"""

def get_institution_by_id(institution_id: str) -> Optional[Dict[str, Any]]:
    """Get institution details"""

def get_institutions_for_user(user_id: str) -> List[Dict[str, Any]]:
    """Get institutions user has access to"""

def get_user_primary_institution(user_id: str) -> Optional[str]:
    """Get user's primary institution ID"""
```

#### 2.2 Update All Query Functions
**CRITICAL**: Every database query must include institution filtering

**Before (Current):**
```python
def get_all_courses() -> List[Dict[str, Any]]:
    docs = db.collection(COURSES_COLLECTION).stream()
    # Returns ALL courses globally - WRONG for multi-tenant
```

**After (Multi-tenant):**
```python
def get_all_courses(institution_id: str) -> List[Dict[str, Any]]:
    query = db.collection(COURSES_COLLECTION).where(
        filter=firestore.FieldFilter("institution_id", "==", institution_id)
    )
    docs = query.stream()
    # Returns only courses for specified institution
```

**Functions to Update:**
- `get_all_courses()` → `get_all_courses(institution_id)`
- `get_all_instructors()` → `get_all_instructors(institution_id)`  
- `get_all_sections()` → `get_all_sections(institution_id)`
- `get_active_terms()` → `get_active_terms(institution_id)`
- `get_courses_by_department()` → `get_courses_by_department(institution_id, department)`
- All create functions must require `institution_id`

#### 2.3 Add Institution Context Helper
```python
def get_current_institution_id() -> Optional[str]:
    """Get current user's active institution from session context"""
    user = get_current_user()
    return user.get("current_institution_id") or user.get("primary_institution_id")

def require_institution_access(institution_id: str) -> bool:
    """Verify current user has access to specified institution"""
    user = get_current_user()
    user_institutions = get_user_institutions(user["user_id"])
    return institution_id in [inst["institution_id"] for inst in user_institutions]
```

### Phase 3: Authentication & Authorization (High Priority)
**Duration**: 2-3 days  
**Risk**: Medium - Critical for data security

#### 3.1 Update User Model
```python
# Updated auth_service.py mock user
def get_current_user(self) -> Optional[Dict[str, Any]]:
    return {
        "user_id": "dev-admin-123",
        "email": "admin@cei.edu", 
        "role": "site_admin",
        "primary_institution_id": "cei-12345",        # NEW
        "current_institution_id": "cei-12345",        # NEW  
        "accessible_institutions": ["cei-12345"],     # NEW
        # ... existing fields
    }
```

#### 3.2 Add Institution-Aware Permission Checking
```python
def has_institution_permission(permission: str, institution_id: str) -> bool:
    """Check if user has permission for specific institution"""
    user = get_current_user()
    
    # Site admins have access to all institutions
    if user["role"] == "site_admin":
        return True
        
    # Check if user has access to this institution
    if institution_id not in user.get("accessible_institutions", []):
        return False
        
    # Check role-based permission
    return has_permission(permission)
```

#### 3.3 Add Institution Context Middleware
```python
@api.before_request
def inject_institution_context():
    """Ensure all API requests have institution context"""
    if request.endpoint and request.endpoint.startswith('api.'):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required"}), 401
            
        # For non-site-admins, require institution context
        if user["role"] != "site_admin":
            institution_id = get_current_institution_id()
            if not institution_id:
                return jsonify({"error": "Institution context required"}), 400
```

### Phase 4: API Layer Updates (High Priority)
**Duration**: 2-3 days
**Risk**: Medium - Affects all API endpoints

#### 4.1 Update All API Endpoints
**Pattern**: Every endpoint must get institution context and pass to database layer

**Before:**
```python
@api.route("/courses", methods=["GET"])
@login_required
def list_courses():
    courses = get_all_courses()  # WRONG - no institution filter
```

**After:**
```python
@api.route("/courses", methods=["GET"]) 
@login_required
def list_courses():
    institution_id = get_current_institution_id()
    if not institution_id:
        return jsonify({"error": "Institution context required"}), 400
        
    if not has_institution_permission("view_courses", institution_id):
        return jsonify({"error": "Access denied"}), 403
        
    courses = get_all_courses(institution_id)  # CORRECT - filtered by institution
```

#### 4.2 Add Institution Management Endpoints
```python
@api.route("/institutions", methods=["GET"])
@login_required  
def list_institutions():
    """Get institutions user has access to"""

@api.route("/institutions/<institution_id>/switch", methods=["POST"])
@login_required
def switch_institution(institution_id: str):
    """Switch user's active institution context"""

@api.route("/institutions", methods=["POST"])
@permission_required("manage_institutions")
def create_institution():
    """Create new institution (site admin only)"""
```

### Phase 5: Import System Updates (Medium Priority)
**Duration**: 1-2 days
**Risk**: Low - Isolated changes

#### 5.1 Update Import Service
```python
# import_service.py changes
def import_excel(file_path: str, institution_id: str, **kwargs):
    """Updated to require institution_id parameter"""
    
    # Validate institution access
    if not has_institution_permission("import_data", institution_id):
        raise PermissionError("No import access for institution")
    
    # Add institution_id to all imported records
    for record in processed_records:
        record["institution_id"] = institution_id
```

#### 5.2 Update Import API Endpoint
```python
@api.route("/import/excel", methods=["POST"])
@permission_required("import_data")
def import_excel_api():
    institution_id = get_current_institution_id()
    # Pass institution_id to import_excel function
    result = import_excel(temp_file_path, institution_id=institution_id, ...)
```

### Phase 6: Data Migration (Critical)
**Duration**: 1 day
**Risk**: Very High - Data integrity critical

#### 6.1 Create CEI Institution Record
```python
def create_default_cei_institution():
    """Create the default CEI institution record"""
    cei_data = {
        "institution_id": "cei-12345",
        "name": "College of Eastern Idaho",
        "short_name": "CEI", 
        "domain": "cei.edu",
        "timezone": "America/Denver",
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    return create_institution(cei_data)
```

#### 6.2 Migrate Existing Data
```python
def migrate_existing_data_to_cei():
    """Add institution_id to all existing records"""
    cei_institution_id = "cei-12345"
    
    # Update all courses
    courses_ref = db.collection("courses")
    for doc in courses_ref.stream():
        doc.reference.update({"institution_id": cei_institution_id})
    
    # Update all users  
    users_ref = db.collection("users")
    for doc in users_ref.stream():
        doc.reference.update({
            "institution_id": cei_institution_id,
            "primary_institution_id": cei_institution_id
        })
        
    # Repeat for all collections...
```

### Phase 7: Frontend Updates (Medium Priority)
**Duration**: 2-3 days
**Risk**: Low - UI improvements

#### 7.1 Add Institution Context Display
- Header showing current institution
- Institution switcher dropdown (for multi-institution users)
- Institution-specific branding/theming

#### 7.2 Update Dashboard JavaScript
```javascript
// Update loadDashboardData to include institution context
async function loadDashboardData() {
    const endpoints = [
        { id: 'coursesData', url: '/api/courses', key: 'courses' },
        // URLs automatically include institution context via session
    ];
}
```

---

## Implementation Order & Dependencies

### Week 1: Foundation (Critical Path)
1. **Day 1-2**: Phase 1 - Data Model Foundation
2. **Day 3-4**: Phase 2 - Database Service Layer  
3. **Day 5**: Phase 6 - Data Migration (CEI data)

### Week 2: API & Security (Critical Path)
1. **Day 1-2**: Phase 3 - Authentication & Authorization
2. **Day 3-4**: Phase 4 - API Layer Updates
3. **Day 5**: Phase 5 - Import System Updates

### Week 3: Polish & Testing
1. **Day 1-2**: Phase 7 - Frontend Updates
2. **Day 3-5**: Testing, bug fixes, documentation

---

## Risk Mitigation

### High Risk: Data Model Changes
- **Mitigation**: Create backup before migration
- **Rollback Plan**: Restore from backup, remove institution_id fields
- **Testing**: Extensive testing in development environment first

### Medium Risk: Breaking API Changes  
- **Mitigation**: Maintain backward compatibility during transition
- **Strategy**: Add new endpoints alongside existing ones initially
- **Gradual Migration**: Update one endpoint at a time

### High Risk: Data Migration
- **Mitigation**: Run migration in maintenance window
- **Validation**: Verify all records updated correctly
- **Backup Strategy**: Full database backup before migration

---

## Success Criteria

### Functional Requirements
✅ All existing CEI data remains accessible
✅ New institutions can be created and managed  
✅ Users can only access their authorized institutions
✅ Import system associates data with correct institution
✅ Dashboard shows institution-specific data only

### Technical Requirements  
✅ All database queries filtered by institution
✅ Composite indexes created for performance
✅ Authentication includes institution context
✅ API endpoints enforce institution access control
✅ No data leakage between institutions

### Performance Requirements
✅ Query performance maintained or improved
✅ Page load times under 2 seconds
✅ Import performance not degraded

---

## Post-Implementation Tasks

1. **Documentation Updates**
   - Update API documentation
   - Create institution management guide
   - Update developer setup instructions

2. **Monitoring & Alerting**
   - Add institution-specific metrics
   - Monitor cross-tenant data access attempts
   - Performance monitoring per institution

3. **Future Enhancements**
   - Institution-specific theming
   - Custom fields per institution
   - Institution-level analytics dashboard

---

This plan transforms the single-tenant CEI system into a robust multi-tenant architecture while maintaining data integrity and backward compatibility.
