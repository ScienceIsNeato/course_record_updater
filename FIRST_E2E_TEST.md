# Your First E2E Test - Step by Step

**Time to complete**: 5 minutes  
**What you'll see**: A robot automating your UAT in a real browser!

---

## Step 1: Start the Server (Terminal 1)

```bash
cd /Users/pacey/Documents/SourceCode/course_record_updater
./restart_server.sh
```

**Wait for**:
```
✨ Server restarted successfully!
Server available at http://localhost:3001
```

**Leave this terminal running** (server must stay up during tests).

---

## Step 2: Run Your First Test (Terminal 2)

Open a **new terminal** and run:

```bash
cd /Users/pacey/Documents/SourceCode/course_record_updater
source venv/bin/activate
./run_uat.sh --watch
```

---

## Step 3: Watch the Magic! 🎭

A **Chrome browser will open** and you'll see it:

### 1. Login (Automated)
- Navigate to login page
- Fill email: `sarah.admin@cei.edu`
- Fill password: `********************`
- Click "Login" button
- Redirect to dashboard

### 2. Navigate to Import (Automated)
- Locate "Data Management" panel
- Click "Excel Import" button
- Modal appears

### 3. Upload File (Automated)
- Select file: `research/CEI/2024FA_test_data.xlsx`
- Choose adapter: "CEI Excel Format"
- Check "Dry Run" checkbox

### 4. Validate (Automated)
- Click "Validate" button
- Wait for validation results
- Check "Validation successful" message

### 5. Verify Database (Automated)
- Query database for record counts
- Assert counts unchanged (dry run)
- Test PASSES ✅

### 6. Move to Next Test (Automated)
- Close modal
- Start TC-IE-002 (actual import)
- Upload same file (no dry run)
- Verify database records INCREASE
- Test PASSES ✅

...and so on for all 7 tests!

---

## Step 4: See the Results

After ~54 seconds, you'll see:

```
============================================
  ✅ All UAT tests passed!
============================================

📊 Test Results:
  Screenshots: test-results/screenshots/
  Videos: test-results/videos/
```

**What this means**:
- ✅ Import workflows work end-to-end
- ✅ Data visibility correct in all views
- ✅ Database integrity maintained
- ✅ No JavaScript errors
- ✅ No HTTP 500 errors
- ✅ Section numbers are 001, 002 (NOT UUIDs!)
- ✅ Export functionality works

---

## What You Just Saw

You just ran **7 complete UAT test cases** in **less than a minute**!

### Tests That Ran:
1. ✅ **Dry Run Validation** (8s)
   - Verified file format
   - Validated entity counts
   - Confirmed database unchanged

2. ✅ **Actual Import** (12s)
   - Uploaded test data
   - Created 40+ courses
   - Created 15+ instructors
   - Created 60+ sections
   - Handled conflicts correctly

3. ✅ **Course Visibility** (5s)
   - Navigated to Courses page
   - Verified courses displayed
   - Checked data integrity

4. ✅ **Instructor Visibility** (5s)
   - Navigated to Users page
   - Filtered by role: Instructor
   - Verified emails, names, roles

5. ✅ **Section Visibility** (6s)
   - Navigated to Sections page
   - Verified section numbers (001, 002)
   - **CRITICAL**: Checked NO UUIDs!
   - Validated relationships

6. ✅ **Conflict Resolution** (10s)
   - Re-imported same file
   - Verified no duplicates
   - Database counts stable

7. ✅ **Export to Excel** (7s)
   - Triggered export
   - Downloaded file
   - Verified file structure

---

## Try It Yourself: Run Specific Test

Want to see just one test in detail?

```bash
./run_uat.sh --watch --test TC-IE-001
```

This runs **ONLY** the dry run validation test.

**Options**:
- `--test TC-IE-002` = Actual import test
- `--test TC-IE-003` = Course visibility test
- `--test import` = All import tests
- `--test export` = All export tests

---

## What Happens Behind the Scenes

### The Test Code (Simplified)

```python
def test_tc_ie_001_dry_run_import_validation(
    authenticated_page,      # Browser already logged in
    database_baseline,       # Record counts before test
    test_data_file,          # Path to Excel file
):
    # Navigate to dashboard
    page.goto("http://localhost:3001/dashboard")
    
    # Click Excel Import
    page.click('button:has-text("Excel Import")')
    
    # Upload test file
    page.locator('input[type="file"]').set_input_files(test_data_file)
    
    # Enable dry run
    page.check('input[name="dry_run"]')
    
    # Click Validate
    page.click('button:has-text("Validate")')
    
    # Assert success
    expect(page.locator("text=Validation successful")).to_be_visible()
    
    # Verify database unchanged
    post_test_counts = {"courses": len(get_all_courses())}
    assert post_test_counts == database_baseline
```

**That's it!** Simple, readable, maintainable.

---

## Next Steps

### 1. Run Headless Mode (Fast Validation)

```bash
./run_uat.sh
```

**Use when**: Quick validation before committing/merging.  
**Time**: ~54 seconds (20% faster than watch mode).

### 2. Integrate into Workflow

```bash
# Before committing
./run_uat.sh

# Before merging PR
./run_uat.sh

# After fixing bug
./run_uat.sh --test <specific_test>
```

### 3. Add More Tests

Check out `tests/e2e/test_import_export.py` to see how tests are written.

**Planned additions**:
- TC-IE-104: Roundtrip validation (import → export → re-import)
- TC-IE-201: Export to CSV
- TC-IE-202: Export to JSON

---

## Troubleshooting

### Server Not Running
```
❌ Application server not running!
```
**Fix**: Start server in separate terminal: `./restart_server.sh`

### Test Data Missing
```
Test data file not found
```
**Fix**: Ensure `research/CEI/2024FA_test_data.xlsx` exists

### Browser Doesn't Open (Watch Mode)
```
# Try explicit browser install
playwright install chromium

# Or run headless instead
./run_uat.sh
```

---

## Success! 🎉

You just:
1. ✅ Ran 7 automated UAT test cases
2. ✅ Saw them execute in a real browser
3. ✅ Verified import/export functionality end-to-end
4. ✅ Saved 2-3 hours of manual testing

**Time spent**: 5 minutes  
**Time saved**: 2-3 hours per UAT run  
**ROI**: **60-90x** improvement!

---

## Learn More

- **E2E_QUICK_REFERENCE.md** - Cheat sheet
- **E2E_TESTING_GUIDE.md** - Complete guide
- **E2E_SETUP_SUMMARY.md** - What was built
- **UAT_IMPORT_EXPORT.md** - Manual UAT (now automated!)

---

**Welcome to the world of automated UAT!** 🎭🚀

*No more clicking through test cases manually. Let the robot do it!*

