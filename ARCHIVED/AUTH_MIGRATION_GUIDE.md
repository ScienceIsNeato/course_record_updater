# Auth Migration Guide 🔐

## Overview

This guide documents the incremental migration from mock authentication to real session-based authentication using the `--use-real-auth` flag system.

## Flag System

### Command Usage

```bash
# Run tests with mock auth (default) - should pass
python -m pytest tests/unit/test_api_routes.py

# Run tests with real auth - will show failures that need fixing
python -m pytest tests/unit/test_api_routes.py --use-real-auth

# Run specific test file with real auth
python -m pytest tests/unit/test_program_context_management.py --use-real-auth
```

### How It Works

1. **Default Behavior**: All tests use mock authentication (`USE_REAL_AUTH=False`)
2. **Flag Enabled**: Tests use real session-based authentication (`USE_REAL_AUTH=True`)
3. **Automatic Configuration**: The `conftest.py` file automatically configures the Flask app based on the flag

## Migration Workflow

### Step 1: Identify Target Test File
Choose a test file to migrate (start with smaller files):
```bash
python -m pytest tests/unit/target_file.py --use-real-auth -v --tb=no
```

### Step 2: Fix Failing Tests
For each failing test, apply the proven patterns:

#### Pattern 1: Add setup_method
```python
class TestMyEndpoints:
    def setup_method(self):
        """Set up test fixtures."""
        from app import app
        self.app = app
        self.client = self.app.test_client()
```

#### Pattern 2: Replace client creation patterns
```python
# OLD: 
with app.test_client() as client:
    # test code

# NEW:
# Use self.client instead (set up in setup_method)
```

#### Pattern 3: Create real sessions
```python
# OLD:
# No session setup (relied on mock)

# NEW:
from tests.test_utils import create_test_session

user_data = {
    "user_id": "test-user-123",
    "email": "test@example.com", 
    "role": "site_admin",  # or appropriate role
    "institution_id": "test-inst",
}
create_test_session(self.client, user_data)
```

#### Pattern 4: Fix test data keys
```python
# OLD:
user_data = {"id": "user-123", ...}

# NEW:
user_data = {"user_id": "user-123", ...}
```

#### Pattern 5: Update expected status codes
```python
# For unauthenticated tests:
# OLD: assert response.status_code == 400
# NEW: assert response.status_code == 401
```

### Step 3: Verify Migration
```bash
# Should pass with real auth
python -m pytest tests/unit/target_file.py --use-real-auth -v

# Should still pass with mock auth
python -m pytest tests/unit/target_file.py -v
```

### Step 4: Commit Changes
Once a file is fully migrated and passes both modes:
```bash
git add tests/unit/target_file.py
git commit -m "Migrate target_file.py to support real authentication"
```

## Quality Gates

- **All tests must pass WITHOUT the flag** (ensures no regression)
- **Migrated tests must pass WITH the flag** (ensures real auth works)
- **Coverage and linting must pass** (maintains code quality)

## Test Utilities

### Available Helpers

```python
from tests.test_utils import (
    create_test_session,        # Create Flask session
    ADMIN_USER_DATA,           # Pre-defined admin user
    INSTRUCTOR_USER_DATA,      # Pre-defined instructor user
    is_using_real_auth,        # Check current auth mode
    require_real_auth_session, # Smart session creation
)
```

### Example Usage

```python
def test_my_endpoint(self):
    """Test endpoint with proper authentication"""
    user_data = {
        "user_id": "test-123",
        "email": "test@example.com",
        "role": "institution_admin",
        "institution_id": "inst-123",
    }
    create_test_session(self.client, user_data)
    
    response = self.client.post("/api/my-endpoint", json={"data": "test"})
    assert response.status_code == 200
```

## Migration Scope Analysis

### Overall Statistics
- **Total Tests**: 846
- **Failures with --use-real-auth**: 98 (11.6%)
- **Success Rate**: 88.4% already working with real auth! 🎉

### Strategic Migration Plan

#### **Phase 1: Quick Wins (Estimated: 30 minutes)**
Start with files that have minimal failures:

1. **`test_program_context_management.py`** ✅ (0 failures - ready)
2. **`test_app.py`** (4 failures - LOW complexity)
3. **`test_program_crud.py`** (4 failures - LOW complexity)  
4. **Other clean files** (Most have 0-2 failures each)

#### **Phase 2: Medium Complexity (Estimated: 45 minutes)**
5. **`test_auth_service.py`** (16 failures - MEDIUM complexity)
   - Many `RuntimeError: Working outside of application context`
   - Need to add proper Flask app context setup

#### **Phase 3: High Complexity (Estimated: 90 minutes)**
6. **`test_api_routes.py`** (70 failures - HIGH complexity)
   - Largest file with most failures
   - Mix of 401 Unauthorized and context issues
   - Should be tackled last when patterns are well-established

#### **Already Complete** ✅
- **`test_api_routes_error_handling.py`** (0 failures)
- **Most other unit test files** (0-2 failures each)

### Estimated Timeline
- **Phase 1**: 30 minutes → ~94% success rate
- **Phase 2**: +45 minutes → ~96% success rate  
- **Phase 3**: +90 minutes → 100% success rate
- **Total**: ~2.5 hours for complete migration

### Completion Criteria
- All unit tests pass with `--use-real-auth` flag
- All unit tests still pass without flag (backward compatibility)
- Remove mock auth fallback from `auth_service.py`
- Update default to `USE_REAL_AUTH=True`

## Troubleshooting

### Common Failure Patterns

#### **Pattern 1: 401 Unauthorized (Most Common)**
```
assert 401 == 200  # Expected authenticated response
```
**Solution**: Add `create_test_session()` call with appropriate user data

#### **Pattern 2: RuntimeError: Working outside of application context**
```
RuntimeError: Working outside of application context.
```
**Solution**: Add Flask app context setup in test methods

#### **Pattern 3: Mock Assertion Failures** 
```
AssertionError: Expected 'redirect' to have been called once. Called 0 times.
```
**Solution**: Update test expectations for real auth behavior (401 instead of redirect)

#### **Pattern 4: Permission Level Issues**
```
assert 401 == 403  # Expected forbidden, got unauthorized
```
**Solution**: Create session first, then verify permission logic

### Common Issues

1. **401 Unauthorized**: Test needs `create_test_session()` call
2. **403 Forbidden**: User role in session data insufficient for endpoint
3. **IndentationError**: Check Python indentation after edits
4. **Import Errors**: Ensure `from tests.test_utils import create_test_session`
5. **App Context**: Add `with app.app_context():` for utility function tests

### Debug Commands

```bash
# See detailed failure info
python -m pytest tests/unit/target_file.py --use-real-auth -v --tb=long

# Show print statements and debug output
python -m pytest tests/unit/target_file.py --use-real-auth -v -s

# Run single test for focused debugging
python -m pytest tests/unit/target_file.py::TestClass::test_method --use-real-auth -v
```
