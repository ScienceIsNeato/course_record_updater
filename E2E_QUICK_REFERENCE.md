# E2E Testing - Quick Reference Card

## 🚀 Run All UAT Tests
```bash
./run_uat.sh
```
**Time**: ~2-3 minutes  
**Output**: Pass/fail for all 7 automated test cases

---

## 👀 Watch Tests Run (See Browser)
```bash
./run_uat.sh --watch
```
**What you'll see**: Real Chrome browser automating your UAT  
**Use when**: Writing new tests or debugging failures

---

## 🎯 Run Specific Test
```bash
./run_uat.sh --test TC-IE-001
```
**Examples**:
- `--test TC-IE-001` = Dry run validation only
- `--test import` = All import tests
- `--test export` = All export tests

---

## 🎥 Record Video
```bash
./run_uat.sh --video
```
**Saves to**: `test-results/videos/`  
**Use when**: Need to debug failures offline

---

## ❌ When Tests Fail

1. **Check screenshots**: `test-results/screenshots/`
2. **Watch it fail**: `./run_uat.sh --watch --test <failing_test>`
3. **Check server logs**: `./tail_logs.sh`
4. **Verify server running**: `curl http://localhost:3001/api/health`

---

## ✅ What E2E Tests Validate

- ✅ Import workflows (dry run, actual import, conflicts)
- ✅ Data visibility (courses, instructors, sections)
- ✅ Export functionality (Excel, CSV, JSON)
- ✅ Database integrity (no duplicates, referential integrity)
- ✅ UI behavior (modals, buttons, forms)
- ✅ Section numbers (001, 002, NOT UUIDs)

---

## 📋 Test Cases Automated

| ID | Description | Time |
|----|-------------|------|
| TC-IE-001 | Dry run import validation | 8s |
| TC-IE-002 | Successful import | 12s |
| TC-IE-003 | Course visibility | 5s |
| TC-IE-004 | Instructor visibility | 5s |
| TC-IE-005 | Section visibility | 6s |
| TC-IE-007 | Conflict resolution | 10s |
| TC-IE-101 | Export to Excel | 7s |

**Total**: 7 tests in ~54 seconds

---

## 🔧 Prerequisites

```bash
# 1. Start server
./restart_server.sh

# 2. Activate venv (if not already)
source venv/bin/activate

# 3. Verify test data exists
ls research/CEI/2024FA_test_data.xlsx

# 4. Run tests
./run_uat.sh
```

---

## 💡 Pro Tips

- **Use watch mode** when developing new tests
- **Run headless** for quick validation
- **Record video** only when debugging (slower)
- **Test specific cases** instead of full suite during iteration
- **Check database** if tests fail unexpectedly

---

## 📚 Full Documentation

- **Complete Guide**: `E2E_TESTING_GUIDE.md`
- **UAT Test Cases**: `UAT_IMPORT_EXPORT.md`
- **Test Code**: `tests/e2e/test_import_export.py`
- **Runner Script**: `run_uat.sh`

---

**TLDR**: Run `./run_uat.sh --watch` to see your UAT automate itself in a real browser! 🎭

