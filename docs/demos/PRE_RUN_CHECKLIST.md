# Pre-Run Checklist

Use this checklist before your first demo run to ensure everything works!

## ✅ Environment Setup

- [ ] **Virtual environment exists**: `ls venv/bin/activate` should show the file
- [ ] **Dependencies installed**: `pip list | grep requests` should show requests library
- [ ] **Environment variables configured**: `.envrc` file exists with required vars
- [ ] **Database file exists**: `course_records_dev.db` in project root
- [ ] **Server script executable**: `chmod +x restart_server.sh` if needed
- [ ] **advance_demo script exists**: `ls scripts/advance_demo.py` should work

## ✅ Quick Smoke Test

Run these commands from the project root to verify everything:

```bash
# 1. Activate environment
source venv/bin/activate
source .envrc

# 2. Verify Python and dependencies
python --version  # Should be Python 3.x
pip show requests  # Should show installed version

# 3. Test database access
sqlite3 course_records_dev.db "SELECT COUNT(*) FROM users"  # Should return a number

# 4. Test server startup
./restart_server.sh dev  # Should start server on port 3001
sleep 2
curl -s http://localhost:3001/api/health | grep healthy  # Should show "healthy"

# 5. Test demo runner (verify-only mode, doesn't change anything)
cd demos
python run_demo.py --demo full_semester_workflow.json --verify-only
```

## ✅ Expected Output from Verify-Only

You should see:
```
================================================================================
Demo: Full Semester Assessment Workflow
================================================================================

Description: Complete semester lifecycle...
Estimated Duration: 20 minutes
Mode: VERIFY-ONLY (No actions will be executed)

[Step 1/19] Environment Setup: Verify Server Health
...
[Step 19/19] Demo Completion: Demo Complete
```

**No errors** should appear. If you see errors, check the Common Issues section below.

## ✅ Full Automated Test

Once verify-only passes, test the full automation:

```bash
cd /path/to/course_record_updater
source venv/bin/activate
cd demos
python run_demo.py --demo full_semester_workflow.json --auto
```

**Expected**: All steps complete successfully with `✓ Success: 200` (or 201) for each API action.

**Time**: ~2-3 minutes for full automated run

## ⚠️ Common Issues & Fixes

### "python: command not found"
**Problem**: Virtual environment not activated  
**Fix**: `source venv/bin/activate` from project root

### "No such file: course_records_dev.db"
**Problem**: Database needs to be seeded  
**Fix**: `python scripts/seed_db.py --demo --clear --env dev`

### "Connection refused" on API calls
**Problem**: Server not running  
**Fix**: `./restart_server.sh dev` from project root

### "CSRF validation failed"
**Problem**: Should not happen in automation, but if it does...  
**Fix**: Check that `get_csrf_token()` is being called. The token should be fetched from `/login` page.

### "Source course not found" (Step 5)
**Problem**: Database not seeded or BIOL-101 course missing  
**Fix**: Re-run seed script: `python scripts/seed_db.py --demo --clear --env dev`

### "Module not found: requests"
**Problem**: requests library not installed  
**Fix**: `pip install requests` or `pip install -r requirements.txt`

### Hard-coded path issues
**Problem**: JSON has `/Users/pacey/Documents/...` path  
**Fix**: Update `working_directory` in `full_semester_workflow.json` to your path

## ✅ Success Indicators

When everything is working correctly:

1. **Verify-only mode**: Shows all 19 steps with no errors
2. **Automated mode**: All API actions return 200/201 status codes
3. **Step 11**: `advance_demo.py` executes and creates 5 CLOs in various statuses
4. **Final message**: "Demo Complete!" with key takeaways
5. **Artifacts directory**: `demos/artifacts/full_semester_workflow_TIMESTAMP/` created

## 📊 What Each Step Does

Quick reference for debugging specific steps:

| Step | Action | What It Does | Success Code |
|------|--------|-------------|--------------|
| 1 | api_check | Verify server health | 200 |
| 2 | api_post | Admin login | 200 |
| 3 | api_put | Edit program description | 200 |
| 4 | none | UI navigation (auto-skip) | N/A |
| 5 | api_post | Duplicate BIOL-101 course | 201 |
| 6 | api_post | Logout admin | 200 |
| 7 | api_post | Faculty login | 200 |
| 8 | none | UI navigation (auto-skip) | N/A |
| 9 | api_put | Fill assessment form | 200 |
| 10 | api_post | Logout faculty | 200 |
| 11 | run_command | Create CLOs (advance_demo.py) | 0 (exit code) |
| 12 | api_post | Admin login (audit) | 200 |
| 13-19 | none | UI navigation (auto-skip) | N/A |

## 🎯 Ready to Run?

If you can check all boxes above, you're ready for your first demo run!

```bash
cd /path/to/course_record_updater
source venv/bin/activate
cd demos
python run_demo.py --demo full_semester_workflow.json --auto
```

Good luck! 🚀

