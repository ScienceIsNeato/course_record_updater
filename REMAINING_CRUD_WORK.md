# Remaining CRUD Work - Honest Assessment

**Created:** October 8, 2025  
**Last Updated:** October 8, 2025 (Tech Debt Complete)  
**Status:** Backend Complete - UI Implementation Next

---

## ✅ COMPLETED: All Tech Debt (October 8, 2025)

**5/5 Tech Debt Tasks Complete:**
1. ✅ **Missing Database Functions** - `get_section_by_id`, `get_term_by_id`, `get_course_outcome` implemented
2. ✅ **Site Admin E2E Fixture** - `authenticated_site_admin_page` added, 8 tests enabled
3. ✅ **Multi-Institution Test Data** - `ensure_multiple_institutions` fixture with auto-cleanup
4. ✅ **Parameterized Test Credentials** - Centralized in `tests/conftest.py`, 16 hardcoded strings replaced
5. ✅ **Old Integration Tests** - 41 tests fixed, 136/137 passing (99.3%)

**Impact**: All backend infrastructure complete. E2E tests ready. No blockers except UI.

---

## 🚨 CRITICAL BLOCKERS (E2E Tests Cannot Pass Without These)

### 1. UI Forms for ALL CRUD Operations
**Status:** NONE IMPLEMENTED - Only stub buttons exist

**Current State:**
- Dashboard buttons exist but call placeholder functions:
  - `createInstitution()` → needs modal form
  - `inviteUser()` → needs modal form  
  - `createProgram()` → needs modal form
  - Similar stubs for update/delete across all entities

**What Needs to Be Built:**

#### **Institution Management UI** (Site Admin)
- [ ] Create Institution modal
  - Fields: name, short_name, admin_email, address, phone, website
  - Validation: required fields, email format, unique short_name
  - POST to `/api/institutions`
- [ ] Edit Institution modal
  - Pre-populate fields from GET `/api/institutions/<id>`
  - PUT to `/api/institutions/<id>`
- [ ] Delete Institution confirmation
  - Warning about data deletion
  - Require typing "i know what I'm doing"
  - DELETE to `/api/institutions/<id>`

#### **User Management UI** (Site Admin, Institution Admin)
- [ ] Invite User modal
  - Fields: email, first_name, last_name, role, institution_id, program_ids (conditional)
  - Role dropdown with permissions info
  - POST to `/api/invitations`
- [ ] Edit User modal
  - Fields: first_name, last_name, display_name, role (admin only), program_ids
  - PATCH to `/api/users/<id>/profile` or PUT to `/api/users/<id>` (admin)
- [ ] Deactivate User confirmation
  - POST to `/api/users/<id>/deactivate`
- [ ] Delete User confirmation
  - DELETE to `/api/users/<id>`

#### **Program Management UI** (Site Admin, Institution Admin)
- [ ] Create Program modal
  - Fields: name, short_name, description
  - POST to `/api/programs`
- [ ] Edit Program modal
  - GET `/api/programs/<id>` to pre-populate
  - PUT to `/api/programs/<id>`
- [ ] Delete Program confirmation
  - Check for courses first
  - DELETE to `/api/programs/<id>`

#### **Course Management UI** (Site Admin, Institution Admin, Program Admin)
- [ ] Create Course modal
  - Fields: course_number, title, department, credit_hours, description
  - Program multi-select (based on user permissions)
  - POST to `/api/courses`
- [ ] Edit Course modal
  - GET `/api/courses/<id>` to pre-populate
  - PUT to `/api/courses/<id>`
- [ ] Delete Course confirmation
  - Warning about cascade (offerings, sections, outcomes)
  - DELETE to `/api/courses/<id>`

#### **Term Management UI** (Site Admin, Institution Admin)
- [ ] Create Term modal
  - Fields: term_name, name, start_date, end_date, is_active
  - Date pickers
  - POST to `/api/terms`
- [ ] Edit Term modal
  - GET `/api/terms/<id>` to pre-populate
  - PUT to `/api/terms/<id>`
- [ ] Archive Term button
  - POST to `/api/terms/<id>/archive`
- [ ] Delete Term confirmation
  - Warning about cascade (offerings, sections)
  - DELETE to `/api/terms/<id>`

#### **Course Offering Management UI** (Site Admin, Institution Admin, Program Admin)
- [ ] Create Offering modal
  - Course dropdown (filtered by permissions)
  - Term dropdown
  - Fields: faculty_assigned
  - POST to `/api/offerings`
- [ ] Edit Offering modal
  - GET `/api/offerings/<id>` to pre-populate
  - PUT to `/api/offerings/<id>`
- [ ] Delete Offering confirmation
  - Warning about cascade (sections)
  - DELETE to `/api/offerings/<id>`

#### **Section Management UI** (Site Admin, Institution Admin, Program Admin)
- [ ] Create Section modal
  - Offering dropdown (filtered by permissions)
  - Fields: section_number, capacity, enrolled, schedule_days, schedule_time, location
  - POST to `/api/offerings/<id>/sections`
- [ ] Edit Section modal
  - GET `/api/sections/<id>` to pre-populate
  - PUT to `/api/sections/<id>`
- [ ] Assign/Reassign Instructor
  - Instructor dropdown (filtered by institution)
  - PATCH to `/api/sections/<id>/instructor`
- [ ] Delete Section confirmation
  - DELETE to `/api/sections/<id>`

#### **Course Outcome (CLO) Management UI** (Site Admin, Institution Admin, Program Admin)
- [ ] Create Outcome modal
  - Course selection
  - Fields: code, description, target_percentage
  - POST to `/api/courses/<id>/outcomes`
- [ ] Edit Outcome modal
  - GET `/api/outcomes/<id>` to pre-populate (currently doesn't exist!)
  - PUT to `/api/outcomes/<id>`
- [ ] Update Assessment (Instructor)
  - Fields: students_assessed, students_meeting_target, method, date, narrative
  - PUT to `/api/outcomes/<id>/assessment`
- [ ] Delete Outcome confirmation
  - DELETE to `/api/outcomes/<id>`

**Estimated Forms Needed:** ~35 modals/forms total

**Estimated Effort:** 2-3 weeks of focused UI development

**Why Critical:** E2E tests currently use API calls. Once UI is built, E2E tests need to be rewritten to use actual browser interactions (click buttons, fill forms, submit).

---

## 🔴 HIGH PRIORITY - Database Functions Missing

### 2. Implement Missing get_X_by_id Functions
**Status:** NOT INTENTIONAL - Should be implemented

**Missing Functions:**

#### `database_service.py` + `database_sqlite.py`:
- [ ] `get_section_by_id(section_id: str) -> Optional[Dict[str, Any]]`
  - Currently: Endpoints call `get_all_sections(institution_id)` then filter
  - Should: Direct SQL query by section_id
  - Used by: `/api/sections/<id>` (GET, PUT, DELETE)
  
- [ ] `get_term_by_id(term_id: str) -> Optional[Dict[str, Any]]`
  - Currently: Endpoints call `get_active_terms(institution_id)` then filter
  - Should: Direct SQL query by term_id
  - Used by: `/api/terms/<id>` (GET, PUT, DELETE, archive)
  
- [ ] `get_course_outcome(outcome_id: str) -> Optional[Dict[str, Any]]`
  - Currently: Endpoints call `get_all_courses()` + `get_course_outcomes()` then filter
  - Should: Direct SQL query by outcome_id
  - **CRITICAL**: Must return `assessment_data` and `narrative` fields for verification
  - Used by: `/api/outcomes/<id>` (GET, PUT, DELETE)

**Impact:**
- More efficient API endpoints (single query vs fetch-all-and-filter)
- Proper E2E test verification for outcome assessments
- Consistent patterns across all entity types

**Estimated Effort:** 2-3 hours (straightforward SQL queries + tests)

---

## 🟡 MEDIUM PRIORITY - Test Infrastructure

### 3. Fix 41 Old Integration Tests
**Status:** Failing - likely pre-existing, but should verify

**Files:**
- `tests/integration/test_course_program_api.py` (8 failures)
- `tests/integration/test_login_api.py` (15 failures)
- `tests/integration/test_password_reset_api.py` (13 failures)
- `tests/integration/test_program_api.py` (8 failures)

**Investigation Needed:**
1. Are these tests actually broken, or did our CRUD work break them?
2. Do they need CSRF tokens added?
3. Do they need authentication updates?
4. Should they be updated or deleted?

**Next Steps:**
- [ ] Run each test file individually with verbose output
- [ ] Identify root causes (CSRF? Auth? API changes?)
- [ ] Fix or mark as deprecated
- [ ] Document decision

**Estimated Effort:** 4-6 hours (investigation + fixes)

---

### 4. Site Admin Authentication Fixture
**Status:** 8 E2E tests cannot run

**What's Needed:**

#### In `tests/e2e/conftest.py`:
- [ ] Add `SITE_ADMIN_EMAIL` constant
- [ ] Add `SITE_ADMIN_PASSWORD` constant
- [ ] Create `authenticated_site_admin_page` fixture
  - Login as site admin
  - Return authenticated page
  - Similar pattern to existing `authenticated_page`

#### In seed data:
- [ ] Verify site admin user exists with known credentials
- [ ] Or create site admin user in test setup

#### Enable tests in `tests/e2e/test_crud_site_admin.py`:
- [ ] Remove `@pytest.mark.skip` decorators
- [ ] Implement all 8 test bodies
- [ ] Verify cross-institution access

**Estimated Effort:** 2-3 hours

---

### 5. Multi-Institution Test Data
**Status:** Some tests skip if only one institution exists

**Issue:** Tests that verify multi-tenant boundaries skip if database has only CEI:
- `test_tc_crud_pa_006_cannot_access_other_programs`
- `test_tc_crud_ia_010_cannot_access_other_institutions`

**Fix Options:**
1. Update seed script to create 2+ institutions
2. Have tests create second institution via API (preferred)
3. Accept that some tests skip in single-institution environments

**Recommended:** Option 2 - Tests should be self-contained

**Estimated Effort:** 1 hour

---

## 🟢 NICE TO HAVE (But Not Blocking)

### 6. Parameterize Hardcoded Credentials
**Status:** Hardcoded in multiple test files

**Current Hardcoded Values:**
- `InstructorPass123!` - used in `test_crud_instructor.py`
- `ProgramAdminPass123!` - used in `test_crud_program_admin.py`
- `InstitutionAdmin123!` - used in `conftest.py`

**Proposed:**
```python
# tests/e2e/conftest.py
TEST_CREDENTIALS = {
    "instructor": {
        "password": os.getenv("E2E_INSTRUCTOR_PASSWORD", "InstructorPass123!"),
    },
    "program_admin": {
        "password": os.getenv("E2E_PROGRAM_ADMIN_PASSWORD", "ProgramAdminPass123!"),
    },
    "institution_admin": {
        "password": INSTITUTION_ADMIN_PASSWORD,  # Existing
    },
    "site_admin": {
        "password": os.getenv("E2E_SITE_ADMIN_PASSWORD", "SiteAdmin123!"),
    },
}
```

**Benefits:**
- Single source of truth
- Environment variable override capability
- Easier to maintain
- Better security (can use secrets in CI)

**Estimated Effort:** 1 hour

---

## 📊 EFFORT SUMMARY

| Priority | Item | Estimated Effort |
|----------|------|------------------|
| 🚨 CRITICAL | UI Forms (35 modals) | 2-3 weeks |
| 🔴 HIGH | Missing database functions (3) | 2-3 hours |
| 🟡 MEDIUM | Fix 41 old integration tests | 4-6 hours |
| 🟡 MEDIUM | Site admin E2E fixture + tests | 2-3 hours |
| 🟡 MEDIUM | Multi-institution test data | 1 hour |
| 🟢 NICE | Parameterize test credentials | 1 hour |

**Total Before E2E Can Pass:** 2-3 weeks (UI work dominates)

---

## 🎯 RECOMMENDED APPROACH

### Phase 1: Core Infrastructure (1 day)
1. Implement missing `get_X_by_id` functions
2. Investigate & fix old integration tests
3. Add multi-institution test data handling

### Phase 2: UI Development (2-3 weeks)
1. Start with high-frequency operations:
   - User invitation (most used)
   - Program management
   - Course management
2. Then term/offering/section management
3. Finally institution management (site admin only)
4. Add delete confirmations throughout

### Phase 3: E2E Validation (2-3 days)
1. Add site admin fixture
2. Rewrite E2E tests to use UI interactions (not API calls)
3. Run full E2E suite against live server
4. Fix any issues discovered

---

## 🤔 QUESTIONS FOR DECISION

1. **UI Framework:** Are we using plain JavaScript + Bootstrap modals, or should we introduce a framework (React, Vue, Alpine)?

2. **Form Validation:** Client-side (JS) + server-side (API), or server-side only?

3. **E2E Test Strategy:** Should E2E tests use:
   - UI interactions (slow, realistic)
   - Direct API calls (fast, less realistic)
   - Mix of both (pragmatic)

4. **Old Integration Tests:** Fix them all, or delete/deprecate ones that test deprecated functionality?

5. **Site Admin User:** Should we create one in seed data, or have tests create it programmatically?

---

## ✅ WHAT'S ACTUALLY DONE (For Context)

- Database layer CRUD (all entities)
- API endpoints (all CRUD operations)
- API unit tests (37 tests)
- Integration tests (26 new CRUD tests passing)
- Audit logging (backend + UI display)
- E2E test structure (28 tests ready for UI)

**The code is there. The UI is not.**

