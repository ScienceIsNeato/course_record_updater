"""
End-to-End (E2E) Tests for LoopCloser

This package contains automated browser-based tests that simulate real user
interactions with the application. These tests validate complete workflows
that unit and integration tests cannot catch.

Test Structure:
- test_import_export.py: Import/export UAT automation
- conftest.py: Shared fixtures for authentication, database setup, etc.

Running E2E Tests:
- Watch mode (see browser): pytest tests/e2e/ --headed --slowmo=500
- Headless mode (CI): pytest tests/e2e/
- Specific test: pytest tests/e2e/test_import_export.py::test_dry_run_validation -v
- With video: pytest tests/e2e/ --video=on

Requirements:
- Application server running on localhost:3001
- Clean database state (or use fixtures to manage)
- Test data files in tests/e2e/fixtures/ (generic adapter format)
"""
