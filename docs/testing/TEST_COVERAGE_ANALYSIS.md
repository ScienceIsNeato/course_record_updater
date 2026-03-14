# Test Coverage Analysis for PR

## Overview

This PR adds ~20,000 lines of new code including:

- 91 API endpoints
- Audit service (579 lines)
- Database layer expansions (583+ lines)
- 8 frontend JavaScript modules

**Quality Gate Issue**: Coverage on New Code = 70.5% (need 80%)  
**Gap**: 398 uncovered lines need systematic test coverage

---

## Coverage Gaps by File

### 1. api_routes.py (226 uncovered lines)

**New Endpoints (91 total)**

Endpoints WITH tests (37 tests in test_crud_api_endpoints.py):

- ✅ GET /users/<id>
- ✅ PATCH /users/<id>/profile
- ✅ POST /users/<id>/deactivate
- ✅ DELETE /users/<id>
- ✅ PUT /institutions/<id>
- ✅ DELETE /institutions/<id>
- ✅ GET /courses/by-id/<id>
- ✅ PUT /courses/<id>
- ✅ DELETE /courses/<id>
- ✅ GET /terms/<id>
- ✅ PUT /terms/<id>
- ✅ POST /terms/<id>/archive
- ✅ DELETE /terms/<id>
- ✅ POST /offerings
- ✅ GET /offerings/<id>
- ✅ PUT /offerings/<id>
- ✅ DELETE /offerings/<id>
- ✅ GET /sections/<id>
- ✅ PUT /sections/<id>
- ✅ POST /sections/<id>/assign
- ✅ DELETE /sections/<id>
- ✅ POST /outcomes
- ✅ GET /outcomes/<id>
- ✅ PUT /outcomes/<id>
- ✅ PUT /outcomes/<id>/assessment
- ✅ DELETE /outcomes/<id>

Endpoints MISSING comprehensive tests (need validation + error path coverage):

- ❌ GET /dashboard/data
- ❌ GET /institutions
- ❌ POST /institutions
- ❌ POST /institutions/register
- ❌ GET /institutions/<id>
- ❌ GET/POST/DELETE /context/program
- ❌ GET /me
- ❌ GET /users
- ❌ POST /users
- ❌ GET /courses
- ❌ POST /courses
- ❌ GET /courses/<number>
- ❌ GET /courses/unassigned
- ❌ POST /courses/<id>/assign-default
- ❌ GET /instructors
- ❌ GET /terms
- ❌ POST /terms
- ❌ GET /programs (all 9 program endpoints)
- ❌ POST/GET /offerings
- ❌ GET/POST /sections
- ❌ GET /outcomes
- ❌ POST /audit/\* (all audit endpoints)
- ❌ POST /import/excel
- ❌ POST /export/\*

**Strategy**: Focus on validation error paths (400-level errors) - these are quick wins and improve security rating

### 2. database_sqlite.py (144 uncovered lines)

**New/Modified Methods**

Areas with tests (from test_database_service.py):

- ✅ Basic CRUD operations
- ✅ Relationship management

Missing error path coverage:

- ❌ SQLAlchemy exception handling
- ❌ Constraint violation handling
- ❌ Transaction rollback scenarios
- ❌ NULL constraint failures
- ❌ Foreign key constraint violations

**Strategy**: Add targeted error injection tests for each CRUD method

### 3. audit_service.py (12 uncovered lines)

**New Service (579 total lines)**

test_audit_service.py exists with comprehensive tests, but 12 lines uncovered:

- Lines 276-279: Error path in \_validate_log_level
- Lines 319, 322: Error paths in \_filter_events
- Lines 373-376: Error paths in \_format_timestamp
- Lines 415, 418: Error paths in \_paginate_results

**Strategy**: Add error injection tests for these specific helper methods

### 4. database_service.py (9 uncovered lines)

**Facade Layer**

Missing coverage on error pass-through:

- Lines 121, 213, 219, 228, 234, 244, 303, 323, 384

**Strategy**: Add tests that verify exceptions are properly propagated

### 5. app.py (4 uncovered lines)

**Application Initialization**

Lines 209-212: Error handling in app initialization

**Strategy**: Add test for app initialization error scenarios

---

## Systematic Test Plan

### Phase 1: Quick Wins (Target: +5% coverage)

**Focus**: Input validation and 400-level errors

1. Add validation error tests for POST /institutions
2. Add validation error tests for POST /users
3. Add validation error tests for POST /courses
4. Add validation error tests for POST /terms
5. Add validation error tests for POST /programs

**Rationale**: Validation logic is straightforward to test and improves security rating

### Phase 2: Error Paths (Target: +3% coverage)

**Focus**: Database error handling

1. Add constraint violation tests (SQLAlchemy IntegrityError)
2. Add NULL constraint tests
3. Add foreign key violation tests
4. Add transaction rollback tests

**Rationale**: Ensures graceful degradation and proper error messages

### Phase 3: Service Layer (Target: +2% coverage)

**Focus**: audit_service.py and database_service.py

1. Complete audit_service helper method tests
2. Add database_service exception propagation tests

**Rationale**: Completes coverage of new services

### Phase 4: Integration (Verify)

**Focus**: Ensure workflows are covered

1. Review existing integration tests
2. Add missing workflow tests if needed

---

## Success Metrics

**Target**: 70.5% → 80% coverage on new code  
**Required**: ~40 newly covered lines (10% of 398)

**Approach**:

- Phase 1: ~20 lines (validation logic)
- Phase 2: ~15 lines (error handling)
- Phase 3: ~10 lines (service layer)
- Buffer: ~5 lines

**Timeline**: Systematic, one phase at a time

---

## Anti-Patterns to Avoid

❌ **Don't**: Write single-line tests just to hit coverage numbers  
✅ **Do**: Write meaningful tests that verify behavior

❌ **Don't**: Test implementation details  
✅ **Do**: Test public API contracts

❌ **Don't**: Mock everything  
✅ **Do**: Use real collaborators where practical (integration over unit when appropriate)

❌ **Don't**: Skip error scenarios  
✅ **Do**: Ensure every public method handles errors gracefully

---

## Next Steps

1. ✅ Complete this analysis
2. 🔄 Execute Phase 1 (validation tests)
3. ⏳ Execute Phase 2 (error path tests)
4. ⏳ Execute Phase 3 (service tests)
5. ⏳ Verify integration coverage
6. ⏳ Re-run local coverage validation
