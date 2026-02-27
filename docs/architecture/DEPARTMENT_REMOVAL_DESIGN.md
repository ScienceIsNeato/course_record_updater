# Department Field Removal - Design Document

**Status**: Phase 1 (UI Cleanup) - In Progress  
**Date**: 2026-01-18  
**Author**: AI Agent  
**Approved**: User confirmed greenfield cleanup (no deprecations needed)

## Problem Statement

The Courses UI displays both "Department" and "Programs" columns, creating unnecessary confusion:

- **Department**: Auto-derived from course number prefix (BIOL-101 → BIOL)
- **Programs**: Actual organizational unit with RBAC, admins, permissions

**Impact**: Users see redundant information without understanding why both exist.

## Analysis

### Department Field Usage Audit

**Database** (SQLAlchemy model):

- `Course.department` column exists
- Auto-populated from course number prefix during imports
- Not used for JOINs, not used for queries (except one filtering endpoint)

**API Layer**:

- `GET /api/courses?department=BIOL` - Optional filter (low/no usage)
- `get_courses_by_department()` method - Only used by above endpoint

**UI Layer**:

- Courses table: Shows department column
- Add Course modal: Has department input field
- Edit Course modal: Has department input field

**Import Adapters**:

- CEI adapter: Auto-derives department from course number
- Generic CSV: Includes department in export format
- Users: Incorrectly assigns department to users (should only be on courses!)

**Tests**:

- JavaScript: Likely tests department in course forms
- Python: Tests get_courses_by_department endpoint

### Program Field (For Comparison)

**Usage**: 550+ references across 20 files

- RBAC: Program admins have scoped permissions
- Permissions: Used in authorization checks
- Business logic: Course assignments, filtering, notifications
- **This is the meaningful organizational concept**

## Decision: Remove Department (Greenfield Cleanup)

**Rationale**:

- Greenfield project (not yet released)
- No backward compatibility concerns
- YAGNI principle - remove unused complexity
- Department = course number prefix (no independent value)

**Approach**: Phased removal (fail-fast at each phase)

## Phase 1: UI Cleanup (This Issue)

### Goal

Remove department from user-facing UI while keeping backend intact.

### Changes Required

#### 1. Frontend - Course Management (`static/courseManagement.js`)

**Remove department from table**:

```javascript
// Find renderCoursesTable() - remove department column
columns: [
  { key: "course_number", label: "Course Number" },
  { key: "course_title", label: "Title" },
  { key: "credits", label: "Credits" },
  // REMOVE: { key: "department", label: "Department" },
  { key: "programs", label: "Programs" }, // KEEP
  { key: "actions", label: "Actions" },
];
```

**Remove department from Add Course modal**:

- Remove `courseDepartment` input field from modal HTML
- Remove `department:` from `saveCourse()` payload
- Remove validation for department field

**Remove department from Edit Course modal**:

- Remove `editCourseDepartment` input field
- Remove `department:` from `saveEditedCourse()` payload
- Remove `document.getElementById("editCourseDepartment").value` assignment

#### 2. Frontend - Dashboard (`static/institution_dashboard.js`)

Check if dashboard renders courses with department - if yes, remove.

#### 3. Tests - JavaScript

**Files to update**:

- `tests/javascript/unit/courseManagement.test.js`
- Any other tests asserting on department field

**Changes**:

- Remove assertions checking `department` field
- Remove mock data containing `department`
- Update expected payloads to not include `department`

### What We're NOT Changing (Yet)

**Backend** (Phase 2 - separate PR):

- Database column remains
- API still accepts department parameter (silently ignored)
- `get_courses_by_department()` method remains
- Import adapters unchanged

**Why phased?**

- UI is user-facing (immediate value)
- Backend cleanup is internal refactoring (can be done separately)
- Fail-fast: If Phase 1 breaks something, we find out immediately

## Phase 2: Backend Cleanup (Future PR)

**Will remove**:

- `get_courses_by_department()` from database service
- Department filtering from `/api/courses` endpoint
- Department from generic CSV export schema
- Unnecessary department mappings in CEI adapter

**Will deprecate then remove**:

- `Course.department` column (after verifying no import dependencies)

## Testing Strategy

**Phase 1**:

1. Run JavaScript tests: `npm test -- courseManagement`
2. Manual UI test: Add course (no department field)
3. Manual UI test: Edit course (no department field)
4. Manual UI test: View courses table (no department column)
5. Verify programs column still works correctly

**Phase 2** (future):

1. Unit tests for API changes
2. Integration tests for imports
3. Verify exports don't break

## Rollback Plan

**Phase 1** (UI only):

- Git revert the UI changes
- Department still in database, can be re-added to UI if needed

**Phase 2** (backend):

- More complex - database migration reversal
- Keep department column until Phase 2 to maintain rollback option

## Success Criteria

**Phase 1** ✅ :

- No department column in courses table
- No department field in add/edit course modals
- All JavaScript tests passing
- Users see only Program (clear organizational hierarchy)

**Phase 2** (future):

- `get_courses_by_department()` removed
- Department filtering removed from API
- Database column marked for removal (after final verification)

## Risk Assessment

**Phase 1**: LOW

- UI-only changes
- Backend unchanged (safe rollback)
- No data migration needed

**Phase 2**: MEDIUM

- API contract changes
- Database schema changes
- Import adapter dependencies

## Timeline

**Phase 1**: Single PR (this issue)
**Phase 2**: Separate PR after Phase 1 proven stable

---

## Implementation Checklist (Phase 1)

- [ ] Remove department column from `courseManagement.js` table
- [ ] Remove department from Add Course modal
- [ ] Remove department from Edit Course modal
- [ ] Check `institution_dashboard.js` for department references
- [ ] Update JavaScript tests
- [ ] Manual UI testing
- [ ] Commit and verify all tests pass
