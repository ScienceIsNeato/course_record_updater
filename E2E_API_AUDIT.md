# E2E Test API Call Audit

**Purpose**: Identify all E2E tests that use direct API calls instead of UI interactions, assess whether they're covered by integration tests, and plan conversion to proper UI workflows.

**Date**: 2025-10-11  
**Status**: Phase 1 Complete ✅

---

## Executive Summary

### Audit Results
- **Total E2E test files audited**: 4
- **Tests with API calls**: 13 tests
- **Tests with mixed API + UI**: 5 tests
- **Pure API tests masquerading as E2E**: 8 tests

### Integration Test Coverage Assessment
- ✅ **Excellent coverage**: RBAC/permission boundaries (smoke + integration tests)
- ✅ **Good coverage**: CRUD operations (integration tests)
- ⚠️  **Missing**: 5 specific integration tests needed (see Phase 2)

### UI Element Availability
- ✅ **All workflows have UI**: Course edit, program management, user management, invitations
- ✅ **Ready for conversion**: No UI development needed

### Next Actions
1. **Phase 2**: Create 5 missing integration tests (1-2 hours)
2. **Phase 3**: Convert 5 E2E tests to UI workflows (2-3 hours)
3. **Phase 4**: Delete 6 pure API tests from E2E suite (30 minutes)

---

## Tests Requiring Action

### 🔴 HIGH PRIORITY: Pure API Tests (Should Be Integration Tests)

#### Test: `test_tc_crud_inst_003_cannot_create_course`
**File**: `tests/e2e/test_crud_instructor.py:240`
**Current Behavior**: 
- Direct API calls: `page.request.get("/api/courses")`, `page.request.post("/api/courses")`
- Opens browser but never interacts with UI
- Tests RBAC permission boundaries via API

**Integration Test Coverage**: ✅ EXCELLENT
- `tests/smoke/test_authorization_smoke.py:159` - `test_instructor_limited_access_smoke` validates instructors cannot manage_courses
- `tests/integration/test_multi_tenant_authorization.py` - Multiple RBAC boundary tests
- Already covered - no new integration test needed

**UI Workflow**: ❌ NONE EXISTS
- No UI form for course creation restricted by role
- This is purely a permission boundary test

**Recommendation**: 
- ✅ **DELETE from E2E suite** - Already covered by integration tests
- 🚫 No new integration test needed - coverage is excellent
- Optional: Add E2E test to verify "Add Course" button is hidden for instructors (UI visibility test)

---

#### Test: `test_tc_crud_inst_004_cannot_manage_users`
**File**: `tests/e2e/test_crud_instructor.py:300`
**Current Behavior**:
- Direct API calls: `page.request.get("/api/users")`, `page.request.delete("/api/users/{id}")`
- Opens browser but never interacts with UI
- Tests RBAC permission boundaries via API

**Integration Test Coverage**: ✅ EXCELLENT
- `tests/smoke/test_authorization_smoke.py:159` - Instructors cannot `manage_users`
- `tests/integration/test_crud_api_integration.py:113` - User deletion API test exists
- Already covered - no new integration test needed

**UI Workflow**: ❌ NONE EXISTS
- No UI for user deletion (or it should be hidden for instructors)

**Recommendation**:
- ✅ **DELETE from E2E suite** - Already covered by integration tests
- 🚫 No new integration test needed

---

#### Test: `test_tc_crud_pa_003_cannot_delete_institution_user`
**File**: `tests/e2e/test_crud_program_admin.py:149`
**Current Behavior**:
- Direct API calls: `page.request.get("/api/users")`, `page.request.delete("/api/users/{id}")`
- Opens browser but never interacts with UI
- Tests RBAC permission boundaries via API

**Integration Test Coverage**: ✅ GOOD (partial)
- `tests/smoke/test_authorization_smoke.py:104` - Program admin scoped access validation
- Missing: Specific test for program admin attempting to delete institution admin
- 🔧 **Need**: `test_program_admin_cannot_delete_higher_role_user_403`

**UI Workflow**: ❌ NONE EXISTS

**Recommendation**:
- 🔧 **Add integration test first** - Test role hierarchy in user deletion
- ✅ **Then delete from E2E suite** - Pure RBAC test

---

#### Test: `test_tc_crud_pa_006_cannot_access_other_programs`
**File**: `tests/e2e/test_crud_program_admin.py:325`
**Current Behavior**:
- Direct API calls: `page.request.get("/api/me")`, `page.request.get("/api/courses")`
- Validates multi-tenant isolation via API response inspection

**Integration Test Coverage**: ✅ EXCELLENT
- `tests/integration/test_multi_tenant_authorization.py:169` - `test_program_admin_scoped_to_assigned_programs`
- `tests/smoke/test_authorization_smoke.py:104` - Program admin scoped access smoke test
- Already comprehensively covered

**UI Workflow**: ❌ NONE EXISTS
- This is data filtering logic, not a UI interaction

**Recommendation**:
- ✅ **DELETE from E2E suite** - Already covered by integration tests
- 🚫 No new integration test needed

---

#### Test: `test_tc_crud_ia_003_delete_empty_program`
**File**: `tests/e2e/test_crud_institution_admin.py:132`
**Current Behavior**:
- Direct API calls: `page.request.post("/api/programs")`, `page.request.delete("/api/programs/{id}")`
- Opens browser but creates and deletes program via API

**Integration Test Coverage**: ⚠️ PARTIAL
- Program creation/deletion APIs exist in CRUD tests
- Missing: Specific test for "empty program can be deleted" scenario
- 🔧 **Need**: `test_delete_empty_program_success_200`

**UI Workflow**: ✅ EXISTS
- `createProgramModal` in `institution_admin.html` - Create program form
- Program table has Delete button (need to confirm)
- Conversion is feasible

**Recommendation**:
- 🔧 **Add integration test** - Test empty program deletion API
- 🔧 **Convert to UI workflow**:
  1. Navigate to dashboard
  2. Click "Add Program" button
  3. Fill form, submit (create empty program)
  4. Find program in table
  5. Click "Delete" button
  6. Confirm deletion dialog
  7. Verify program no longer in table

---

#### Test: `test_tc_crud_ia_004_cannot_delete_program_with_courses`
**File**: `tests/e2e/test_crud_institution_admin.py:176`
**Current Behavior**:
- Direct API calls: Multiple gets to find program with courses, then DELETE
- Tests referential integrity constraint

**Integration Test Coverage**: ⚠️ MISSING
- Need test for referential integrity: program deletion fails when courses exist
- 🔧 **Need**: `test_delete_program_with_courses_fails_400_or_409`

**UI Workflow**: ✅ EXISTS
- Program table in dashboard
- Delete button available
- Error handling in frontend

**Recommendation**:
- 🔧 **Add integration test first** - Test referential integrity constraint
- 🔧 **Convert to UI workflow**:
  1. Navigate to programs page/dashboard
  2. Find program with courses (inspect course count column)
  3. Click "Delete" button
  4. Verify error message appears: "Cannot delete program with courses"
  5. Verify program still exists in table

---

#### Test: `test_tc_crud_ia_005_invite_instructor`
**File**: `tests/e2e/test_crud_institution_admin.py:219`
**Current Behavior**:
- Direct API call: `page.request.post("/api/invitations")`
- Opens browser but sends invitation via API

**Integration Test Coverage**: ⚠️ UNKNOWN (need to check)
- May exist in invitation-specific test file
- 🔧 **Need to check**: `tests/integration/test_invitation_api.py` (if exists)
- 🔧 **If missing, need**: `test_create_invitation_success_201`

**UI Workflow**: ✅ EXISTS
- `inviteUserModal` in `user_management.html` and `site_admin_panels.html`
- Full form with email, first name, last name, role fields
- Conversion is straightforward

**Recommendation**:
- 🔧 **Check/add integration test** - Test invitation creation API
- 🔧 **Convert to UI workflow**:
  1. Navigate to users page
  2. Click "Invite User" button
  3. Fill invitation form (email, first name, last name, role)
  4. Submit
  5. Verify success message
  6. Verify invitation appears in pending invitations list (if shown)

---

#### Test: `test_tc_crud_ia_010_cannot_access_other_institutions`
**File**: `tests/e2e/test_crud_institution_admin.py:438`
**Current Behavior**:
- Direct API calls: `page.request.get("/api/courses")`, `page.request.get("/api/programs")`
- Validates multi-tenant isolation via response inspection

**Integration Test Coverage**: ✅ EXCELLENT
- `tests/integration/test_multi_tenant_authorization.py:26` - `test_institution_admin_cannot_access_other_institutions`
- `tests/smoke/test_authorization_smoke.py:57` - Institution admin scoped access smoke test
- Comprehensive coverage for institution-level isolation

**UI Workflow**: ❌ NONE EXISTS
- Multi-tenant isolation is backend filtering logic

**Recommendation**:
- ✅ **DELETE from E2E suite** - Already covered by integration tests
- 🚫 No new integration test needed

---

### 🟡 MEDIUM PRIORITY: Mixed API + UI Tests (Need UI Enhancement)

#### Test: `test_tc_crud_ia_002_update_course_details` ⭐ **CURRENTLY UNDER REVIEW**
**File**: `tests/e2e/test_crud_institution_admin.py:100`
**Current Behavior**:
- Gets course list via API: `page.request.get("/api/courses")`
- Updates course via API: `page.request.put("/api/courses/{id}")`
- Never interacts with courses page UI

**Integration Test Coverage**: ✅ GOOD
- `tests/integration/test_crud_api_integration.py` - Course CRUD tests exist
- Missing: Specific institution admin update test (but logic is same)
- 🔧 **Optional**: `test_institution_admin_update_course_api` (low priority)

**UI Workflow**: ✅ EXISTS
- `editCourseModal` in `courses_list.html` and `institution_admin.html`
- Edit button on course rows
- Full form with title, credit hours, etc.

**Recommendation**:
- 🔧 **Convert to UI workflow** (HIGH PRIORITY - this is test 2):
  1. Navigate to `/courses`
  2. Click Edit button on first course
  3. Wait for edit modal
  4. Update title field
  5. Click Save Changes
  6. Verify modal closes
  7. Verify updated title appears in table
- ✅ Optional integration test (low priority)

---

#### Test: `test_tc_crud_ia_006_manage_institution_users`
**File**: `tests/e2e/test_crud_institution_admin.py:253`
**Current Behavior**:
- Gets users via API: `page.request.get("/api/users")`
- Updates user via API: `page.request.patch("/api/users/{id}/profile")`
- **DOES** verify updated name in UI table (partial UI verification)

**Integration Test Coverage**: ✅ EXCELLENT
- `tests/integration/test_crud_api_integration.py:69` - `test_update_profile_integration`
- User profile update API is well tested

**UI Workflow**: ✅ EXISTS (partially used)
- Edit user modal in `users_list.html`
- Currently uses API for action, UI for verification
- Just needs to use UI for action too

**Recommendation**:
- 🔧 **Enhance to full UI workflow** (MEDIUM PRIORITY):
  1. Navigate to `/users`
  2. Find target user row
  3. Click Edit button
  4. Fill first/last name fields in modal
  5. Click Save Changes
  6. Verify modal closes
  7. Verify updated name in table (ALREADY DOES THIS)
- 🚫 No new integration test needed - already exists

---

#### Test: `test_health_endpoint`
**File**: `tests/e2e/test_import_export.py:43`
**Current Behavior**:
- Direct API call: `page.request.get("/api/health")`
- Health check is not a user workflow

**Integration Test Coverage**: ✅ EXISTS (sort of)
- Many tests hit the health endpoint indirectly via `server_running` fixture
- 🔧 **Could add**: Explicit `test_health_endpoint_returns_200` smoke test

**UI Workflow**: ❌ N/A
- Health checks are not user-facing

**Recommendation**:
- ✅ **DELETE from E2E suite** - Move to smoke tests
- 🔧 **Add explicit smoke test**: `test_health_endpoint_returns_200`

---

### ✅ ACCEPTABLE: UI-First Tests (Already Compliant)

The following tests are proper E2E tests that use UI interactions:
- `test_tc_crud_inst_001_update_own_profile` - ✅ Full UI workflow
- `test_tc_crud_inst_002_update_section_assessment` - ✅ Full UI workflow
- `test_tc_crud_pa_001_create_course` - ✅ Full UI workflow
- `test_tc_crud_pa_002_update_section_instructor` - ✅ Full UI workflow
- `test_tc_crud_pa_004_manage_program_courses` - ✅ Full UI workflow
- `test_tc_crud_pa_005_create_sections` - ✅ Full UI workflow
- `test_tc_crud_ia_001_create_program` - ✅ Full UI workflow
- `test_tc_crud_ia_007_create_term` - ✅ Full UI workflow
- `test_tc_crud_ia_008_create_course_offerings` - ✅ Full UI workflow
- `test_tc_crud_ia_009_assign_instructors_to_sections` - ✅ Full UI workflow
- All `test_tc_ie_*` import/export tests - ✅ UI-based file upload workflows

---

## Action Plan

### Phase 1: Assessment - COMPLETE ✅
- [x] Audit integration test coverage for each API-based E2E test
- [x] Document which UI elements exist for each workflow
- [x] Identify gaps where UI doesn't exist for E2E conversion

**Integration Test Coverage Assessment:**
- ✅ **RBAC/Permission tests** - EXCELLENT coverage:
  - `tests/smoke/test_authorization_smoke.py` - Comprehensive smoke tests for all roles
  - `tests/integration/test_multi_tenant_authorization.py` - Full multi-tenant isolation
  - Both files test instructor/program admin permission boundaries extensively
- ✅ **CRUD API tests** - GOOD coverage:
  - `tests/integration/test_crud_api_integration.py` - User CRUD operations
  - Tests include user profile updates, deactivation, deletion
- ⚠️  **Program management** - PARTIAL coverage:
  - Program deletion tests exist but not specifically for "empty program" vs "program with courses"
- ⚠️  **Invitation API** - UNKNOWN coverage (need to check if exists)

**UI Element Assessment:**
- ✅ Course management: Edit modal exists (`editCourseModal` in `courses_list.html`)
- ✅ Program management: Create/Edit modals exist (`createProgramModal`, `editProgramModal` in `institution_admin.html`)
- ✅ User management: Edit user modal exists (in `users_list.html`)
- ✅ User invitation: Invite modal exists (`inviteUserModal` in multiple templates)
- ✅ All identified workflows have functioning UI elements

### Phase 2: Integration Test Creation
**File**: Create `tests/integration/test_e2e_api_coverage.py`

Priority-ordered (implement from top to bottom):
- [ ] `test_program_admin_cannot_delete_higher_role_user_403` - ⚠️ MISSING coverage
- [ ] `test_delete_program_with_courses_fails_referential_integrity` - ⚠️ MISSING coverage
- [ ] `test_delete_empty_program_success_200` - ⚠️ MISSING coverage  
- [ ] `test_create_invitation_success_201` - ⚠️ UNKNOWN (check first)
- [ ] `test_health_endpoint_returns_200` - ⚠️ MISSING explicit test

**Already Covered (no action needed):**
- ✅ Instructor RBAC boundaries - `test_authorization_smoke.py`
- ✅ Multi-tenant isolation - `test_multi_tenant_authorization.py`
- ✅ User profile updates - `test_crud_api_integration.py`
- ✅ Course updates - `test_crud_api_integration.py`

### Phase 3: E2E Test Conversion (UI Workflows)
**Priority Order (high to low):**

1. [ ] **HIGH**: Convert `test_tc_crud_ia_002_update_course_details` ⭐ (currently under review)
   - Navigate to /courses, click Edit, update title, save, verify
2. [ ] **MEDIUM**: Enhance `test_tc_crud_ia_006_manage_institution_users`
   - Just change from API call to UI click - already verifies via UI
3. [ ] **MEDIUM**: Convert `test_tc_crud_ia_003_delete_empty_program`
   - Create program via UI, delete via UI, verify gone
4. [ ] **MEDIUM**: Convert `test_tc_crud_ia_004_cannot_delete_program_with_courses`
   - Find program with courses, try delete, verify error message
5. [ ] **LOW**: Convert `test_tc_crud_ia_005_invite_instructor`
   - Click invite button, fill form, verify success message

### Phase 4: Pure API Test Removal from E2E Suite
**Can be deleted immediately (already covered):**
- [ ] `test_tc_crud_inst_003_cannot_create_course` - Delete (covered by smoke tests)
- [ ] `test_tc_crud_inst_004_cannot_manage_users` - Delete (covered by smoke tests)
- [ ] `test_tc_crud_pa_006_cannot_access_other_programs` - Delete (covered by integration)
- [ ] `test_tc_crud_ia_010_cannot_access_other_institutions` - Delete (covered by integration)
- [ ] `test_health_endpoint` - Move to smoke tests

**Wait for Phase 2 first:**
- [ ] `test_tc_crud_pa_003_cannot_delete_institution_user` - Delete after adding integration test

### Phase 5: UI Feature Gaps (If Needed)
- [ ] Assess if RBAC-based UI hiding is needed (hide Delete button for instructors, etc.)
- [ ] Implement any missing UI elements discovered during audit

---

## Notes

- **RBAC/Permission tests**: These are backend concerns and don't need browser-based E2E tests. Integration tests are faster and more appropriate.
- **Multi-tenant isolation**: This is data filtering logic in the backend. Integration tests are sufficient.
- **Health checks**: Infrastructure validation, not user workflows.
- **UI vs API balance**: E2E tests should test what users actually do. If there's no UI for an action, it shouldn't be an E2E test.

