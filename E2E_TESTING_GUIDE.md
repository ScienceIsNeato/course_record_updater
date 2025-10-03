# E2E Testing Guide
**Automated User Acceptance Testing with Playwright**

## What is E2E Testing?

**End-to-End (E2E) Testing** automates real user interactions with your application using a real browser. Instead of manually clicking through 50 test steps, the computer does it for you in ~2-3 minutes.

### What E2E Tests Catch
- **UI bugs**: Buttons that don't work, modals that don't appear
- **Integration issues**: Frontend + backend + database working together
- **Real-world workflows**: Complete user journeys from login to data export
- **Edge cases**: Things that pass unit tests but break in the browser

### What E2E Tests Don't Replace
- **Unit tests**: Fast, isolated function testing
- **Integration tests**: API endpoint validation
- **Security scans**: SonarCloud, Bandit
- **Performance tests**: Load testing, stress testing

---

## Quick Start

### Prerequisites
1. **Server running**: `./restart_server.sh`
2. **Virtual environment active**: `source venv/bin/activate`
3. **Playwright installed**: Already done during setup
4. **Test data file**: `research/CEI/2024FA_test_data.xlsx` must exist

### Run All UAT Tests (Headless)
```bash
./run_uat.sh
```

**Output**:
```
============================================
  Course Record Updater - UAT Runner
============================================

🔍 Checking application server status...
✅ Server is running

📋 Test Configuration:
  Mode: headless
  Filter: All E2E tests
  Video: off

🚀 Starting E2E tests...

tests/e2e/test_import_export.py::test_tc_ie_001_dry_run_import_validation ✅ PASSED (8.2s)
tests/e2e/test_import_export.py::test_tc_ie_002_successful_import ✅ PASSED (12.5s)
tests/e2e/test_import_export.py::test_tc_ie_003_imported_course_visibility ✅ PASSED (5.1s)
tests/e2e/test_import_export.py::test_tc_ie_004_imported_instructor_visibility ✅ PASSED (4.8s)
tests/e2e/test_import_export.py::test_tc_ie_005_imported_section_visibility ✅ PASSED (6.3s)
tests/e2e/test_import_export.py::test_tc_ie_007_conflict_resolution ✅ PASSED (10.2s)
tests/e2e/test_import_export.py::test_tc_ie_101_export_courses_excel ✅ PASSED (7.4s)

======= 7 passed in 54.5s =======

============================================
  ✅ All UAT tests passed!
============================================
```

### Watch Tests Run (Headed Mode)
```bash
./run_uat.sh --watch
```

This opens a **real Chrome browser** and you can WATCH the tests interact with your app:
- Logging in
- Uploading files
- Clicking buttons
- Filling forms
- Verifying data

It's like having a robot QA tester running through your UAT checklist!

---

## Running Specific Tests

### Run Single Test Case
```bash
./run_uat.sh --test TC-IE-001
```

### Run All Import Tests
```bash
./run_uat.sh --test import
```

### Run All Export Tests
```bash
./run_uat.sh --test export
```

### Run with Video Recording
```bash
./run_uat.sh --video
```
Videos saved to `test-results/videos/` for debugging failures.

---

## Test Cases Automated

### ✅ Implemented (7 tests)

| Test ID | Description | Duration |
|---------|-------------|----------|
| **TC-IE-001** | Dry run import validation | ~8s |
| **TC-IE-002** | Successful import with conflict resolution | ~12s |
| **TC-IE-003** | Imported course visibility in courses list | ~5s |
| **TC-IE-004** | Imported instructor visibility in users list | ~5s |
| **TC-IE-005** | Imported section visibility (check UUIDs vs 001) | ~6s |
| **TC-IE-007** | Conflict resolution (re-import same file) | ~10s |
| **TC-IE-101** | Export courses to Excel | ~7s |

### 🚧 Planned (Future Additions)

- TC-IE-006: Term visibility and format validation
- TC-IE-008: Error handling for malformed files
- TC-IE-102: Export users to Excel
- TC-IE-103: Export sections to Excel
- TC-IE-104: Roundtrip validation (import → export → import)
- TC-IE-201: Export to CSV format
- TC-IE-202: Export to JSON format

---

## Understanding Test Results

### When Tests Pass ✅
```
✅ All UAT tests passed!

📊 Test Results:
  Screenshots: test-results/screenshots/
  Videos: test-results/videos/
```

All tests passed means:
- Import workflows work end-to-end
- Data is visible in correct UI views
- Database integrity maintained
- No JavaScript errors
- No HTTP 500 errors

### When Tests Fail ❌
```
❌ UAT tests failed

📸 Check screenshots in test-results/screenshots/
🎥 Check videos in test-results/videos/

Tip: Run with --watch to see failures in real-time:
  ./run_uat.sh --watch
```

**Debugging Steps**:
1. **Check screenshots**: `test-results/screenshots/tc_ie_001_validation_timeout.png`
2. **Watch video**: `test-results/videos/test_tc_ie_001.webm`
3. **Re-run with watch mode**: `./run_uat.sh --watch --test TC-IE-001`
4. **Check browser console**: Playwright captures console errors
5. **Review test code**: `tests/e2e/test_import_export.py`

---

## How E2E Tests Work

### Test Structure

```python
@pytest.mark.e2e
def test_tc_ie_001_dry_run_import_validation(
    authenticated_page: Page,      # Browser page, already logged in
    database_baseline: dict,        # Record counts before test
    test_data_file: Path,           # Path to test Excel file
    server_running: bool,           # Verify server is up
):
    """TC-IE-001: Dry Run Import Validation"""
    page = authenticated_page
    
    # 1. Navigate to dashboard
    page.goto(f"{BASE_URL}/dashboard")
    
    # 2. Click Excel Import button
    page.click('button:has-text("Excel Import")')
    
    # 3. Upload test file
    page.locator('input[type="file"]').set_input_files(str(test_data_file))
    
    # 4. Enable dry run
    page.check('input[name="dry_run"]')
    
    # 5. Click Validate
    page.click('button:has-text("Validate")')
    
    # 6. Assert validation success
    expect(page.locator("text=Validation successful")).to_be_visible()
    
    # 7. Verify database unchanged
    post_test_counts = {"courses": len(get_all_courses() or [])}
    assert post_test_counts == database_baseline
```

### Fixtures Explained

- **`authenticated_page`**: Browser page already logged in as `sarah.admin@cei.edu`
- **`database_baseline`**: Snapshot of database record counts before test
- **`database_backup`**: Automatically backs up and restores database after test
- **`test_data_file`**: Path to `research/CEI/2024FA_test_data.xlsx`
- **`server_running`**: Verifies server is up (fails fast if not)

### Assertions Used

- **UI Assertions**: `expect(page.locator("text=Success")).to_be_visible()`
- **Database Assertions**: `assert len(get_all_courses()) > baseline["courses"]`
- **Data Integrity**: `assert "UUID" not in section_text` (no UUIDs in section numbers)
- **Count Stability**: `assert post_count == pre_count` (conflict resolution)

---

## Advanced Usage

### Run Tests Directly with pytest

```bash
# All E2E tests
pytest tests/e2e/ -v

# Watch mode (see browser)
pytest tests/e2e/ --headed --slowmo=500

# With video recording
pytest tests/e2e/ --video=on

# Specific test
pytest tests/e2e/test_import_export.py::test_tc_ie_001_dry_run_import_validation -v

# Parallel execution (faster)
pytest tests/e2e/ -n auto
```

### Debugging Failed Tests

```bash
# 1. Run with watch mode to see what's happening
./run_uat.sh --watch --test TC-IE-001

# 2. Add breakpoints in test code
import pdb; pdb.set_trace()

# 3. Take screenshots manually in tests
from tests.e2e.conftest import take_screenshot
take_screenshot(page, "debug_state")

# 4. Check browser console errors
errors = page.locator('.console-error').all_text_contents()
print(f"Console errors: {errors}")
```

### CI Integration (Future)

```yaml
# .github/workflows/e2e-tests.yml
jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
          playwright install chromium
      - name: Start server
        run: ./restart_server.sh &
      - name: Run E2E tests
        run: ./run_uat.sh
      - name: Upload test artifacts
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-test-results
          path: test-results/
```

---

## Troubleshooting

### Server Not Running
```
❌ Application server not running!
Please start the server first:
  ./restart_server.sh
```

**Fix**: Start the server in a separate terminal before running E2E tests.

### Test Data File Missing
```
Test data file not found: research/CEI/2024FA_test_data.xlsx
```

**Fix**: Ensure the test data file exists. You can create a minimal test file or use production data.

### Browser Installation Issues
```
playwright._impl._api_types.Error: Executable doesn't exist at /path/to/chromium
```

**Fix**: Re-install Playwright browsers:
```bash
playwright install chromium
```

### Port Conflicts
```
Cannot connect to server at http://localhost:3001
```

**Fix**: Ensure server is running on port 3001 (default). If using a different port, set environment variable:
```bash
export E2E_BASE_URL="http://localhost:8080"
./run_uat.sh
```

### Slow Tests
E2E tests are inherently slower than unit tests (~1-2 minutes total). To speed up:
- Run specific tests instead of full suite
- Use headless mode (default, 20% faster)
- Skip video recording unless debugging

---

## Best Practices

### DO
- ✅ Run E2E tests before merging PRs
- ✅ Use watch mode when writing new tests
- ✅ Keep test data realistic (actual CEI data)
- ✅ Assert both UI and database state
- ✅ Take screenshots on failures
- ✅ Test complete user workflows (login → import → view → export)

### DON'T
- ❌ Run E2E tests during active development (too slow)
- ❌ Skip unit tests in favor of E2E tests
- ❌ Ignore E2E test failures ("works on my machine")
- ❌ Modify tests to pass instead of fixing bugs
- ❌ Run E2E tests without server running

---

## Adding New E2E Tests

### 1. Add Test Case to `test_import_export.py`

```python
@pytest.mark.e2e
def test_tc_ie_new_feature(
    authenticated_page: Page,
    database_baseline: dict,
    server_running: bool,
):
    """TC-IE-XXX: Test New Feature"""
    page = authenticated_page
    
    # Navigate to page
    page.goto(f"{BASE_URL}/new-feature")
    
    # Interact with UI
    page.click('button:has-text("New Feature")')
    
    # Assert expectations
    expect(page.locator(".success-message")).to_be_visible()
    
    # Verify database state
    new_count = len(get_all_records() or [])
    assert new_count > database_baseline["records"]
```

### 2. Update UAT Documentation

Add corresponding test case to `UAT_IMPORT_EXPORT.md` with:
- Test ID (TC-IE-XXX)
- Description
- Steps
- Expected results
- Critical assertions

### 3. Test Locally

```bash
# Watch mode to verify behavior
./run_uat.sh --watch --test TC-IE-XXX

# Headless mode to confirm pass
./run_uat.sh --test TC-IE-XXX
```

### 4. Commit Both Code and Documentation

```bash
git add tests/e2e/test_import_export.py UAT_IMPORT_EXPORT.md
git commit -m "test: add E2E test for TC-IE-XXX new feature"
```

---

## Comparison: Manual UAT vs. Automated E2E

| Aspect | Manual UAT | Automated E2E |
|--------|-----------|---------------|
| **Time** | 2-3 hours | 2-3 minutes |
| **Consistency** | Human error possible | Exactly same every time |
| **Coverage** | Depends on tester | All test cases guaranteed |
| **Repeatability** | Manual re-run needed | One command |
| **Cost** | High (human time) | Low (computer time) |
| **Feedback** | Hours/days | Minutes |
| **Documentation** | Separate document | Code is documentation |
| **CI Integration** | Not feasible | Easy to add |

---

## Next Steps

1. **Run your first E2E test**: `./run_uat.sh --watch`
2. **Watch it work**: See the browser automate your UAT
3. **Add to workflow**: Run before merging PRs
4. **Expand coverage**: Add more test cases as features are built
5. **Integrate with CI**: Run automatically on every push (future)

**You now have automated UAT that runs in 2 minutes instead of 2 hours!** 🎉

---

*This guide corresponds to UAT_IMPORT_EXPORT.md and automates those manual test cases using Playwright browser automation.*

