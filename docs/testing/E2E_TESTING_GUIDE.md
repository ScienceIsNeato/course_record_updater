# E2E Testing Guide
**Automated User Acceptance Testing with Playwright**

## Overview

E2E tests automate real user interactions in a browser, replacing manual UAT. They catch UI bugs, integration issues, and real-world workflow problems that unit tests miss.

**Test Coverage**: 7 critical UAT scenarios covering import validation, data visibility, and export functionality.

---

## Quick Start

### Run Tests
```bash
# Headless (CI/local quick check)
./run_uat.sh

# Watch mode (see the browser)
./run_uat.sh --watch

# Save videos on failure
./run_uat.sh --save-videos
```

### Prerequisites
- Server running: `./restart_server.sh e2e`
- Virtual environment: `source venv/bin/activate`
- Playwright browsers installed (auto-installed if missing)

---

## Test Data

**Current**: Uses `tests/e2e/fixtures/generic_test_data.zip` (Generic CSV Adapter format)  
**Format**: ZIP file containing normalized CSV files (institution-agnostic)

The test file contains 7 course records, 3 programs, 3 users, and other entities used to validate import/export functionality. Edge cases include duplicates, conflicts, and inactive records.

**Note**: CEI-specific test data remains in `research/CEI/` for manual testing only.

---

## Test Structure

### Automated UAT Test Cases
```
tests/e2e/test_import_export.py
├── test_login_success_after_fix          # Auth verification
├── test_tc_ie_001_dry_run_import         # Dry run validation
├── test_tc_ie_002_import_with_conflicts  # Conflict resolution
├── test_tc_ie_003_course_visibility      # Course data visibility
├── test_tc_ie_004_instructor_visibility  # Instructor data visibility
├── test_tc_ie_005_section_visibility     # Section data visibility
├── test_tc_ie_007_duplicate_import       # Duplicate handling
└── test_tc_ie_101_export_courses         # Export functionality
```

### Fixtures (`tests/e2e/conftest.py`)
- `authenticated_page`: Browser already logged in
- `database_baseline`: Snapshot for validation
- `test_data_file`: Path to generic CSV adapter test data ZIP file

---

## CI Integration

E2E tests run automatically on every PR via GitHub Actions:
- Separate E2E environment (port 3002, dedicated database)
- Playwright browsers pre-installed in CI
- Test artifacts (screenshots, videos) uploaded on failure
- Full workflow in `.github/workflows/quality-gate.yml`

---

## Debugging

### Common Issues

**Login failures**:
```bash
# Check server logs
tail -f logs/test_server.log

# Verify database seeding
sqlite3 course_records_e2e.db "SELECT email FROM users WHERE email LIKE '%admin%';"
```

**Import failures**:
- Verify test file exists: `ls -la tests/e2e/fixtures/generic_test_data.zip`
- Check file format matches Generic CSV Adapter expectations
- Review import results in UI screenshots: `test-results/screenshots/`

**Timeout errors**:
- Increase timeout in test: `page.wait_for_url(url, timeout=10000)`
- Check if server is responsive: `curl http://localhost:3002/login`

### Debug Artifacts
- **Screenshots**: `test-results/screenshots/` (auto-captured on failure)
- **Videos**: `test-results/videos/` (when using `--save-videos`)
- **Server logs**: `logs/test_server.log`
- **Browser console**: Captured in Playwright trace files

---

## Writing New Tests

### Example Test Structure
```python
def test_my_feature(authenticated_page: Page):
    """Test description matching UAT document."""
    page = authenticated_page
    
    # Navigate
    page.goto(f"{BASE_URL}/dashboard")
    
    # Interact
    page.click("button:text('My Feature')")
    
    # Assert
    expect(page.locator(".result")).to_contain_text("Expected Result")
    
    # Screenshot for documentation
    take_screenshot(page, "my_feature_result")
```

### Best Practices
1. **Use semantic selectors**: `button:text('Login')` over `#button-123`
2. **Wait for network idle**: `page.wait_for_load_state('networkidle')`
3. **Descriptive test names**: Match UAT test case IDs
4. **Screenshot key states**: Use `take_screenshot()` helper
5. **Database validation**: Use `database_baseline` fixture to verify data changes

---

## Environment Separation

E2E tests use isolated environment to prevent interference with development:

| Environment | Port | Database | Purpose |
|-------------|------|----------|---------|
| dev | 3001 | `course_records_dev.db` | Local development |
| e2e | 3002 | `course_records_e2e.db` | E2E tests (local & CI) |

Environment managed via `APP_ENV` variable and `.envrc` file.

---

## Performance

**Typical execution times**:
- Full suite (7 tests): ~90 seconds
- Single test: ~10-15 seconds
- Parallel execution: Not yet enabled (see Playwright config)

---

## Maintenance

### When to Update Tests
- New features with UI interactions
- Changes to existing workflows
- Bug fixes that need regression prevention
- UAT test case additions

### Test Health Checks
```bash
# Quick smoke test
./run_uat.sh --filter test_login

# Full validation
python scripts/ship_it.py --checks e2e
```

---

## Resources

- **UAT Documentation**: `UAT_IMPORT_EXPORT.md`
- **Playwright Docs**: https://playwright.dev/python/
- **Test Configuration**: `pytest.ini` (e2e marker)
- **CI Workflow**: `.github/workflows/quality-gate.yml`
