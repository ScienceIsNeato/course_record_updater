# API Routes Refactoring Plan

## Goal
Break up the 5,361-line `api_routes.py` God Object into focused, domain-specific route modules for better testability and maintainability.

## Benefits
- ✅ Smaller, focused files (easier to test and understand)
- ✅ Clear separation of concerns
- ✅ Better coverage metrics per domain
- ✅ Reduced merge conflicts
- ✅ Easier to achieve 80% coverage per file

## Target Structure

```
api/
├── __init__.py                 # Blueprint registration
├── routes/
│   ├── __init__.py
│   ├── dashboard.py           # Dashboard data endpoint
│   ├── institutions.py        # Institution CRUD
│   ├── users.py               # User CRUD + profile
│   ├── courses.py             # Course CRUD
│   ├── terms.py               # Term CRUD
│   ├── programs.py            # Program CRUD + course relationships
│   ├── sections.py            # Section CRUD + instructor assignment
│   ├── offerings.py           # Course offering CRUD
│   ├── outcomes.py            # Learning outcome CRUD
│   ├── audit.py               # Audit log endpoints
│   └── import_export.py       # Data import/export
└── utils.py                   # Shared helpers (error handling, etc.)

tests/unit/api/
├── __init__.py
├── routes/
│   ├── __init__.py
│   ├── test_dashboard.py
│   ├── test_institutions.py
│   ├── test_users.py
│   ├── test_courses.py
│   ├── test_terms.py
│   ├── test_programs.py
│   ├── test_sections.py
│   ├── test_offerings.py
│   ├── test_outcomes.py
│   ├── test_audit.py
│   └── test_import_export.py
└── test_utils.py
```

## Refactoring Strategy

### Phase 1: Setup Infrastructure
1. Create `api/` directory structure
2. Create `api/__init__.py` with blueprint registration
3. Extract shared utilities to `api/utils.py`:
   - Error handling functions (`handle_api_error`)
   - Common decorators
   - Shared constants

### Phase 2: Extract Routes (One Domain at a Time)
**Order: Simplest to Most Complex**

1. **Dashboard** (1 endpoint)
   - Extract: `GET /dashboard/data`
   - Test: Basic dashboard data retrieval
   
2. **Audit** (~10 endpoints)
   - Extract: All `/audit/*` endpoints
   - Test: Log creation, retrieval, filtering
   
3. **Terms** (5 endpoints)
   - Extract: All `/terms/*` endpoints
   - Test: CRUD + archive functionality
   
4. **Outcomes** (5 endpoints)
   - Extract: All `/outcomes/*` endpoints
   - Test: CRUD + assessment updates
   
5. **Offerings** (5 endpoints)
   - Extract: All `/offerings/*` endpoints
   - Test: CRUD operations
   
6. **Sections** (6 endpoints)
   - Extract: All `/sections/*` endpoints
   - Test: CRUD + instructor assignment
   
7. **Courses** (8 endpoints)
   - Extract: All `/courses/*` endpoints
   - Test: CRUD + program relationships
   
8. **Programs** (9 endpoints)
   - Extract: All `/programs/*` endpoints
   - Test: CRUD + course relationships + bulk operations
   
9. **Users** (8 endpoints)
   - Extract: All `/users/*` endpoints
   - Test: CRUD + profile + deactivation
   
10. **Institutions** (7 endpoints)
    - Extract: All `/institutions/*` endpoints
    - Test: CRUD + registration
    
11. **Import/Export** (remaining endpoints)
    - Extract: Import and export endpoints
    - Test: File handling + adapters

### Phase 3: Verification
1. Run full test suite after each extraction
2. Ensure 100% of existing tests still pass
3. Verify no regression in functionality
4. Run E2E tests to confirm UI still works

## Per-File Refactoring Process

For each domain:

1. **Extract Routes**
   ```python
   # api/routes/terms.py
   from flask import Blueprint, jsonify, request
   from auth_service import permission_required
   from api.utils import handle_api_error
   
   terms_bp = Blueprint('terms', __name__, url_prefix='/api/terms')
   
   @terms_bp.route('', methods=['GET'])
   @permission_required('view_program_data')
   def list_terms():
       # ... existing logic
   ```

2. **Register Blueprint**
   ```python
   # api/__init__.py
   from flask import Blueprint
   from api.routes.terms import terms_bp
   
   def register_routes(app):
       app.register_blueprint(terms_bp)
   ```

3. **Update app.py**
   ```python
   # app.py
   from api import register_routes
   register_routes(app)
   ```

4. **Create Test File**
   ```python
   # tests/unit/api/routes/test_terms.py
   """Tests for term API endpoints."""
   import pytest
   from app import app
   
   @pytest.fixture
   def client():
       app.config['TESTING'] = True
       with app.test_client() as client:
           yield client
   
   def test_list_terms_success(client):
       # ... test implementation
   ```

5. **Add Missing Tests**
   - Validation errors (400)
   - Permission errors (403)
   - Not found errors (404)
   - Success paths (200/201)

## Expected Outcomes

### Before Refactor
- api_routes.py: 5,361 lines, 70.5% coverage (226 uncovered lines)
- 1 giant test file: 893 lines

### After Refactor
- 11 route files: ~400-500 lines each, **target 80%+ coverage per file**
- 11 test files: ~100-150 lines each, focused tests
- Shared utils: ~200 lines, 90%+ coverage

### Coverage Goals Per File
Each route file should achieve:
- ✅ 100% coverage on happy paths
- ✅ 100% coverage on validation errors
- ✅ 80%+ coverage on edge cases
- ⚠️  Lower priority: Complex permission matrix tests (use integration tests)

## Rollout Plan

### Week 1: Infrastructure + Simple Domains
- Day 1: Setup infrastructure (api/ directory, __init__.py, utils.py)
- Day 2: Extract Dashboard + Audit routes
- Day 3: Extract Terms + Outcomes routes
- Day 4: Extract Offerings + Sections routes
- Day 5: Verify all tests pass, measure coverage

### Week 2: Complex Domains
- Day 1: Extract Courses routes
- Day 2: Extract Programs routes
- Day 3: Extract Users routes
- Day 4: Extract Institutions routes
- Day 5: Extract Import/Export routes

### Week 3: Test Coverage + Cleanup
- Day 1-3: Add missing tests to reach 80% per file
- Day 4: Final verification (E2E, integration tests)
- Day 5: Documentation + cleanup

## Success Criteria

✅ All existing tests pass  
✅ No functional regressions  
✅ Each route file has 80%+ coverage  
✅ SonarCloud quality gate passes  
✅ E2E tests pass  
✅ Code is more maintainable (subjective but measurable via PR review)

## Risk Mitigation

**Risk**: Breaking existing functionality  
**Mitigation**: 
- Extract one domain at a time
- Run tests after each extraction
- Keep `api_routes.py` as a backup until fully migrated

**Risk**: Import/dependency issues  
**Mitigation**:
- Use relative imports within api/ package
- Keep shared dependencies in utils.py
- Test imports explicitly

**Risk**: Coverage measurement issues  
**Mitigation**:
- Update pytest coverage config to include api/ directory
- Verify coverage reports after each extraction

## Next Steps

1. Create infrastructure (api/ directory, __init__.py)
2. Start with Dashboard (simplest, 1 endpoint)
3. Iterate through domains systematically
4. Measure and report progress after each domain

---

**Ready to begin!** Starting with infrastructure setup.

