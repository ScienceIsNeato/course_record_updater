# API Refactoring Plan - REVISED

## Critical Lessons Learned

1. **NEVER separate source from tests** - Move code AND tests together in the same commit
2. **One domain at a time** - Complete extraction → test migration → commit before moving to next
3. **Maintain backward compatibility** - Keep old routes working until new ones are proven
4. **Test at every step** - Run full test suite after each commit
5. **Small, complete steps** - Each commit should be a working, testable improvement

## Migration Strategy (REVISED)

### Phase 1: Incremental Extraction (One Domain Per Commit)

For EACH domain, follow this exact sequence:

1. **Extract source code** from `api_routes.py` to `api_routes_<domain>.py`
2. **Extract tests** from `test_api_routes.py` to `test_api_routes_<domain>.py`
3. **Update imports** in both source and tests
4. **Keep old routes** in `api_routes.py` (don't delete yet)
5. **Register new blueprint** in `app.py` alongside old one
6. **Run full test suite** - must pass 100%
7. **Commit** with message: "refactor: extract <domain> routes and tests"

### Domain Extraction Order

1. **Health/System** (simplest, no auth)
   - `/health` endpoint
   - Tests: `TestHealthEndpoint`
   - File: `api_routes_system.py`, `test_api_routes_system.py`

2. **Dashboard Data**
   - `/api/dashboard/data` endpoint
   - Tests: `TestDashboardEndpoint`
   - File: `api_routes_dashboard.py`, `test_api_routes_dashboard.py`

3. **Users**
   - All `/api/users/*` endpoints
   - Tests: `TestUserEndpoints`, `TestUserManagementAPI`
   - File: `api_routes_users.py`, `test_api_routes_users.py`

4. **Courses**
   - All `/api/courses/*` endpoints + helpers
   - Tests: `TestCourseEndpoints`, `TestCourseManagementOperations`
   - File: `api_routes_courses.py`, `test_api_routes_courses.py`

5. **Terms**
   - All `/api/terms/*` endpoints
   - Tests: `TestTermEndpoints`
   - File: `api_routes_terms.py`, `test_api_routes_terms.py`

6. **Sections**
   - All `/api/sections/*` endpoints
   - Tests: `TestSectionEndpoints`
   - File: `api_routes_sections.py`, `test_api_routes_sections.py`

7. **Programs**
   - All `/api/programs/*` endpoints + helpers
   - Tests: `TestRemoveCourseHelpers`, `TestBulkManageHelpers`
   - File: `api_routes_programs.py`, `test_api_routes_programs.py`

8. **Institutions**
   - All `/api/institutions/*` endpoints
   - Tests: `TestInstitutionEndpoints`
   - File: `api_routes_institutions.py`, `test_api_routes_institutions.py`

9. **Import/Export**
   - All `/api/import/*`, `/api/export/*`, `/api/adapters` endpoints + helpers
   - Tests: `TestImportEndpoints`, `TestExcelImportHelpers`, `TestExcelImportEdgeCases`
   - File: `api_routes_import_export.py`, `test_api_routes_import_export.py`

10. **Outcomes**
    - All `/api/outcomes/*` endpoints
    - Tests: (if any)
    - File: `api_routes_outcomes.py`, `test_api_routes_outcomes.py`

11. **Offerings**
    - All `/api/offerings/*` endpoints
    - Tests: (if any)
    - File: `api_routes_offerings.py`, `test_api_routes_offerings.py`

12. **Audit**
    - All `/api/audit/*` endpoints
    - Tests: (if any)
    - File: `api_routes_audit.py`, `test_api_routes_audit.py`

### Phase 2: Cleanup (After ALL extractions complete)

Only after ALL domains are extracted and ALL tests pass:

1. Delete old routes from `api_routes.py`
2. Delete old tests from `test_api_routes.py`
3. Rename files: `api_routes_<domain>.py` → `api/routes/<domain>.py`
4. Create `api/` package structure
5. Update all imports
6. Run full test suite - must pass 100%
7. Commit: "refactor: complete API modularization"

## Key Principles

### DO:

- ✅ Move source AND tests together
- ✅ Commit after each domain extraction
- ✅ Keep old code until new code is proven
- ✅ Run full test suite after every change
- ✅ Maintain 80%+ coverage at all times
- ✅ Keep website routes (non-API) untouched

### DON'T:

- ❌ Delete old code before new code is tested
- ❌ Move multiple domains in one commit
- ❌ Skip running tests
- ❌ Let coverage drop below 80%
- ❌ Touch website blueprint routes

## Template for Each Extraction

```bash
# 1. Extract source
# Copy routes from api_routes.py to api_routes_<domain>.py
# Keep original in api_routes.py

# 2. Extract tests
# Copy test classes from test_api_routes.py to test_api_routes_<domain>.py
# Keep original in test_api_routes.py

# 3. Update imports in new files

# 4. Register new blueprint in app.py

# 5. Run tests
python scripts/ship_it.py

# 6. Commit
git add api_routes_<domain>.py test_api_routes_<domain>.py app.py
git commit -F COMMIT_MSG.txt
```

## Success Criteria

- All 35 E2E tests pass
- All unit tests pass
- Coverage stays at 80%+
- No functionality broken
- Each commit is independently deployable
