# Course Record Updater - Current Status

## Last Updated
2025-11-13 03:23 PST

## Current Task
✅ **COMPLETED**: Fixed database persistence issue and security vulnerabilities

## Major Accomplishment: Root Cause Analysis & Fix

### Problem Summary
Data import operations appeared to fail (records not persisting), suspected transaction rollback.

### Root Cause Discovered
**No rollback - wrong database file!**
- `seed_db.py --env dev` wrote to `course_records_dev.db`
- Flask/imports without `DATABASE_URL` set defaulted to `course_records.db`
- Queries checked `course_records_dev.db` → no data visible
- Records were persisting, just to a different file

### Solution Implemented
Added ENV-based `DATABASE_URL` configuration in `.envrc.template`:
```bash
case "${ENV}" in
    development) export DATABASE_URL="${DATABASE_URL_DEV}" ;;
    test)        export DATABASE_URL="${DATABASE_URL_E2E}" ;;
    production)  export DATABASE_URL="${DATABASE_URL:-sqlite:///course_records.db}" ;;
    *)           export DATABASE_URL="${DATABASE_URL_DEV}" ;;
esac
```

This ensures ALL operations (seeding, imports, Flask, tests) use the same database file based on ENV variable.

### Security Hardening (Discovered During Investigation)

**Multi-tenant Isolation Vulnerabilities Fixed:**

1. **Import Service (`import_service.py`)**:
   - ✅ Explicitly override `institution_id` from authenticated user in all entity handlers
   - ✅ Remove primary key fields (id, course_id, user_id) before create/update to prevent conflicts
   - ✅ Add institution_id scoping to `get_course_by_number()` calls
   - ✅ Add cross-institution email conflict detection in `process_user_import()`
   - ✅ Implement actual `update_course()` call in `_resolve_course_conflicts()`
   - ✅ Remove non-updatable fields from `_prepare_user_update_data()`

2. **API Routes (`api_routes.py`)**:
   - ✅ Removed CEI-specific "MockU" hardcoded institution logic
   - ✅ `_determine_target_institution()` now ALWAYS uses authenticated user's institution_id
   - ✅ Added `demo_file_path` support for programmatic imports during demos

### Demo System Improvements

1. **Consolidated Documentation**:
   - ✅ Single `single_term_outcome_management.md` workflow file
   - ✅ Removed separate seed script (use: `python scripts/seed_db.py --demo --env dev`)
   - ✅ Demo users now use `demo2025` prefix for isolation

2. **Interactive Demo Runner** (`run_demo.py`):
   - ✅ Named pipe (FIFO) mechanism for programmatic pause/continue
   - ✅ Parses markdown for setup commands and interactive checkpoints
   - ✅ Works for both humans and AI agents

3. **UI Enhancements**:
   - ✅ "Use Demo Data" checkbox to bypass native file dialog
   - ✅ Pre-populates demo file path for programmatic imports

### Verification
```
✅ 6 courses persisted to course_records_dev.db
✅ 4 users created with proper institution_id
✅ 2 terms created with proper institution_id
✅ Data visible in dashboard after import
✅ Multi-tenant isolation enforced
```

### Test Updates
- ✅ Updated `test_api_routes.py` to reflect new security model
- ✅ Updated `test_import_service.py` to verify institution_id enforcement
- ✅ Removed obsolete MockU-related test cases

## Commit History
- `c12cf5a` - fix: database persistence issue - ENV-based configuration and security hardening

## Next Steps
1. **Continue demo development** - Run through `single_term_outcome_management.md` workflow
2. **Test browser automation** - Verify run_demo.py works end-to-end with browser tools
3. **Document findings** - Update demo documentation with any discovered issues

## Key Files Modified
- `.envrc.template` - Added ENV-based DATABASE_URL switching
- `import_service.py` - Security hardening for multi-tenant isolation
- `api_routes.py` - Removed CEI-specific logic, enforced user institution_id
- `scripts/seed_db.py` - Updated for demo2025 prefix
- `docs/workflow-walkthroughs/single_term_outcome_management.md` - Consolidated demo
- `docs/workflow-walkthroughs/scripts/run_demo.py` - Named pipe interaction
- `templates/components/data_management_panel.html` - Demo data checkbox
- `static/script.js` - Demo file path handling
- `tests/unit/test_api_routes.py` - Security model updates
- `tests/unit/test_import_service.py` - Institution_id enforcement tests

## Environment Status
- Server: Running on port 3001 (dev)
- Database: `course_records_dev.db` (consistent across all operations)
- Demo: Seeded with DEMO2025 institution
- Credentials: `demo2025.admin@example.com` / `Demo2024!`

## Notes
The root cause investigation demonstrated the importance of:
1. Systematic debugging (checking which file is actually being written)
2. Understanding environment variable inheritance across processes
3. Not assuming "records disappeared" means rollback - verify file targets first
4. Using ENV-based configuration for consistent behavior across all operations
