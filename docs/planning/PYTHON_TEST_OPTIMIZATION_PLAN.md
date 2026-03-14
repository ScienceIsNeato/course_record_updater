# Python Unit Test Infrastructure Optimization Plan

## Executive Summary

**Current State**: 1,780+ tests, 50-65s execution time, 85% coverage
**Target State**: Same coverage, 15-25s execution time, better maintainability
**Estimated Total Effort**: 8-12 hours across multiple sessions

---

## Phase 1: Quick Wins (No Code Changes Required)

### 1.1 Install pytest-testmon for Development Cycles

- [ ] `pip install pytest-testmon`
- [ ] Add to `requirements-dev.txt`
- [ ] Test with `pytest --testmon` (first run builds cache, subsequent runs only test affected code)
- [ ] Document usage in README or CONTRIBUTING.md
- **Expected Impact**: 80-90% faster iteration during development
- **Effort**: 15 minutes

### 1.2 Enable Parallel Execution with File Distribution

- [ ] Verify `pytest-xdist` is installed
- [ ] Test `pytest -n auto --dist loadfile` (parallelizes by file, avoids SQLite conflicts)
- [ ] If successful, update `scripts/quality_gate.sh` to use this by default
- [ ] If SQLite conflicts persist, try `--dist loadgroup` with markers
- **Expected Impact**: 40-60% faster full suite runs
- **Effort**: 30 minutes

### 1.3 Profile Test Execution

- [ ] Run `pytest --durations=0 tests/ 2>&1 | head -100` to identify slowest tests
- [ ] Document top 20 slowest tests in this file for targeted optimization
- [ ] Identify any tests taking >1s (candidates for optimization or moving to integration)
- **Expected Impact**: Identifies optimization targets
- **Effort**: 15 minutes

---

## Phase 2: Fixture Optimization (High Impact, Low Risk)

### 2.1 Create Class-Scoped Auth Fixtures

- [ ] Create `tests/fixtures/auth_fixtures.py` with reusable auth fixtures
- [ ] Implement `admin_session` fixture (scope="class")
- [ ] Implement `instructor_session` fixture (scope="class")
- [ ] Implement `institution_admin_session` fixture (scope="class")
- [ ] Each fixture returns `(client, csrf_token)` tuple
- **Expected Impact**: 15-20% speedup (eliminates repeated session creation)
- **Effort**: 1 hour

```python
# Example implementation
@pytest.fixture(scope="class")
def admin_session(client):
    """Class-scoped admin session - created once per test class."""
    create_site_admin_session(client)
    csrf_token = get_csrf_token(client)
    return client, csrf_token
```

### 2.2 Migrate Tests to Use New Fixtures

- [ ] Update `tests/unit/test_crud_api_endpoints.py` (highest test count)
- [ ] Update `test_clo_workflow_service.py`
- [ ] Update remaining unit test files
- [ ] Verify no test isolation issues introduced
- **Expected Impact**: Compounds with 2.1
- **Effort**: 2 hours

---

## Phase 3: Mock Modernization (Medium Impact, Medium Risk)

### 3.1 Switch from @patch Decorators to mocker Fixture

- [ ] Verify `pytest-mock` is installed (provides `mocker` fixture)
- [ ] Create migration guide/example in `tests/README.md`
- [ ] Migrate `tests/unit/test_crud_api_endpoints.py` as pilot
- [ ] Measure before/after timing for migrated file
- [ ] If >10% improvement, continue migration to other files
- **Expected Impact**: 10-15% speedup (less decorator overhead)
- **Effort**: 2-3 hours

```python
# Before (decorator style)
@patch("src.api_routes.get_user_by_id")
@patch("src.api_routes.update_user")
def test_update_user(self, mock_update, mock_get, client):
    mock_get.return_value = {...}
    mock_update.return_value = True

# After (mocker fixture style)
def test_update_user(self, client, mocker):
    mocker.patch("src.api_routes.get_user_by_id", return_value={...})
    mocker.patch("src.api_routes.update_user", return_value=True)
```

---

## Phase 4: Test Consolidation (Medium Impact, Higher Risk)

### 4.1 Create Test Data Factories

- [ ] Create `tests/factories.py` with factory functions
- [ ] Implement `make_user(**overrides)` factory
- [ ] Implement `make_course(**overrides)` factory
- [ ] Implement `make_institution(**overrides)` factory
- [ ] Implement `make_outcome(**overrides)` factory
- [ ] Implement `make_section(**overrides)` factory
- **Expected Impact**: Improved maintainability, slight speedup
- **Effort**: 1 hour

```python
# tests/factories.py
def make_user(**overrides):
    return {
        "user_id": "user-123",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "role": "instructor",
        **overrides
    }

def make_course(**overrides):
    return {
        "course_id": "course-123",
        "course_number": "CS101",
        "course_title": "Intro to CS",
        "institution_id": "inst-1",
        **overrides
    }
```

### 4.2 Parameterize Redundant Test Patterns

- [ ] Identify all "not found returns 404" tests (estimate: ~20)
- [ ] Consolidate into single parameterized test
- [ ] Identify all "permission denied returns 403" tests (estimate: ~15)
- [ ] Consolidate into single parameterized test
- [ ] Identify all "missing field returns 400" tests (estimate: ~10)
- [ ] Consolidate into single parameterized test
- **Expected Impact**: 10% fewer tests, easier maintenance
- **Effort**: 2 hours

```python
# Example consolidated test
@pytest.mark.parametrize("endpoint,mock_target,method", [
    ("/api/users/x", "get_user_by_id", "GET"),
    ("/api/courses/by-id/x", "get_course_by_id", "GET"),
    ("/api/terms/x", "get_term_by_id", "GET"),
    ("/api/offerings/x", "get_course_offering", "GET"),
    ("/api/sections/x", "get_section_by_id", "GET"),
    ("/api/outcomes/x", "get_course_outcome", "GET"),
])
def test_resource_not_found_returns_404(self, endpoint, mock_target, method, client, mocker):
    mocker.patch(f"src.api_routes.{mock_target}", return_value=None)
    response = getattr(client, method.lower())(endpoint)
    assert response.status_code == 404
```

### 4.3 Audit and Remove Truly Redundant Tests

- [ ] Generate test name list: `pytest --collect-only -q > /tmp/all_tests.txt`
- [ ] Review for obvious duplicates (similar names, same file)
- [ ] Flag candidates for removal (document reasoning)
- [ ] Remove only after confirming coverage doesn't drop
- **Expected Impact**: 5-10% fewer tests
- **Effort**: 1 hour

---

## Phase 5: Infrastructure Improvements

### 5.1 Add pytest Markers for Test Categories

- [ ] Add markers to `pytest.ini`: `unit`, `integration`, `slow`, `database`
- [ ] Tag slow tests (>500ms) with `@pytest.mark.slow`
- [ ] Tag database-dependent tests with `@pytest.mark.database`
- [ ] Update CI to run `pytest -m "not slow"` for fast feedback
- **Expected Impact**: Enables selective test runs
- **Effort**: 1 hour

```ini
# pytest.ini additions
[pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    database: marks tests that require database
    unit: pure unit tests with no external dependencies
```

### 5.2 Configure In-Memory SQLite for Parallel Tests

- [ ] Create `tests/conftest.py` fixture for in-memory SQLite per worker
- [ ] Test with `pytest -n 4` to verify no conflicts
- [ ] Document any tests that can't use in-memory DB
- **Expected Impact**: Enables full parallel execution
- **Effort**: 1-2 hours

---

## Progress Tracking

| Phase                     | Status         | Time Spent | Impact Measured |
| ------------------------- | -------------- | ---------- | --------------- |
| 1.1 pytest-testmon        | ⬜ Not Started | -          | -               |
| 1.2 Parallel execution    | ⬜ Not Started | -          | -               |
| 1.3 Profile tests         | ⬜ Not Started | -          | -               |
| 2.1 Class-scoped fixtures | ⬜ Not Started | -          | -               |
| 2.2 Migrate to fixtures   | ⬜ Not Started | -          | -               |
| 3.1 mocker migration      | ⬜ Not Started | -          | -               |
| 4.1 Test factories        | ⬜ Not Started | -          | -               |
| 4.2 Parameterize tests    | ⬜ Not Started | -          | -               |
| 4.3 Remove redundant      | ⬜ Not Started | -          | -               |
| 5.1 Add markers           | ⬜ Not Started | -          | -               |
| 5.2 In-memory SQLite      | ⬜ Not Started | -          | -               |

---

## Baseline Measurements (To Be Filled)

**Before Optimization:**

- Full suite time: \_\_\_s
- Unit tests only: \_\_\_s
- Top 5 slowest tests:
  1. ***
  2. ***
  3. ***
  4. ***
  5. ***

**After Each Phase:**

- Phase 1 complete: **_s (_**% improvement)
- Phase 2 complete: **_s (_**% improvement)
- Phase 3 complete: **_s (_**% improvement)
- Phase 4 complete: **_s (_**% improvement)
- Phase 5 complete: **_s (_**% improvement)

---

## Risk Mitigation

1. **Test Isolation**: Run full suite after each change to catch flaky tests
2. **Coverage Regression**: Check coverage after removing/consolidating tests
3. **Parallel Conflicts**: If SQLite issues persist, fall back to `--dist loadfile`
4. **Rollback Plan**: Git commit after each successful phase for easy revert

---

## Definition of Done

- [ ] Full test suite runs in <25 seconds locally
- [ ] Coverage remains ≥80%
- [ ] No flaky tests introduced
- [ ] Development cycle uses pytest-testmon for instant feedback
- [ ] CI uses parallel execution for faster PR feedback
- [ ] Test infrastructure documented in `tests/README.md`
