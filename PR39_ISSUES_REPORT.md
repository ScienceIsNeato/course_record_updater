# PR #39 Issues Report - Generated 2026-01-07

## Current Status

### ✅ CI Failures Fixed Locally (Ready to Push)
- **Complexity**: ✅ Fixed (`_get_current_term_from_db` refactored, 17→8)
- **Integration Tests**: ✅ Fixed (fixture name corrected)
- **Smoke Tests**: ✅ Passing locally (E2E server verified)

### 📋 PR Bot Comments (30 total)

## High Severity - CI Breaking Issues

### 1. ❌ Database URL Mismatch in Smoke Tests Workflow
**File**: `.github/workflows/quality-gate.yml`
**Issue**: Lines 147, 154 seed to `course_records_ci.db` but lines 164, 184 use `course_records.db`
**Fix**: Standardize all steps to use `course_records.db` (consistent naming)

### 2. ✅ Coverage XML Path - Already Correct
**File**: `.github/workflows/quality-gate.yml:505`
**Status**: False alarm - workflow generates to `build/coverage.xml` (line 505), diff-cover reads from `build/coverage.xml` (line 511) ✅

### 3. ❌ Coverage File Path Mismatch in SonarCloud
**Files**: `config/sonar-project.properties`, `.github/workflows/quality-gate.yml`
**Issue**: Sonar expects `build/coverage.xml` but workflow might generate to wrong location
**Action**: Verify sonar-project.properties location and paths

## Medium Severity - Functionality Issues

### 4. ❌ JavaScript Coverage Paths in Analysis Scripts
**Files**: `scripts/analyze_pr_coverage.py:553`, `scripts/analyze_pr_coverage_simple.py:258`
**Issue**: Looking for `coverage/lcov.info` instead of `build/coverage/lcov.info`
**Fix**: Update both scripts to use `build/coverage/` prefix

### 5. ❌ audit_clo.js DOM Issues
**File**: `static/audit_clo.js`
**Issues**:
  - Lines 21-22: Conflicting styling (class vs inline style)
  - `renderCLODetails` returns DOM element but assigned to innerHTML
**Fix**: Use `replaceChildren()` instead of innerHTML

## User-Requested Cleanups

### Scripts to Remove (Obsolete Migration/Shim Files):
- ❌ `scripts/configure_security_quality_gate.py` - Sonar-related, we're moving away
- ❌ `scripts/create_database_shims.py` - Migration script (greenfield = no migrations)
- ❌ `scripts/create_service_shims.py` - Migration script (greenfield = no migrations)
- ❌ `scripts/fix_src_imports.py` - One-off migration script
- ❌ `scripts/update_all_imports.py` - Migration script
- ❌ `scripts/update_imports.py` - Migration script

### Scripts to Consolidate/Fix:
- ❌ `scripts/analyze_pr_coverage_simple.py` - Duplicate of analyze_pr_coverage.py, remove or merge
- ❌ `scripts/link_courses_to_programs.py` - Should be library code in src/, not a script
- ⚠️ `scripts/seed_db.py` - Demo data mangled into generic seeding (CRITICAL ISSUE)

### File Moves:
- ❌ Move `config/.eslintrc.json` → `.eslintrc.json` (root level)

### Documentation Cleanup:
- ❌ `docs/REPOSITORY_REORGANIZATION_PLAN.md` - Remove (PR is done)
- ❌ `AGENTS.md:323` - Remove stray "res" text

### Code Quality:
- ❌ `scripts/advance_demo.py:318` - Duplicate import (database_service twice)
- ❌ `scripts/maintAInability-gate.sh` - Exit immediately if tool missing (don't skip)
- ❌ `conftest.py` - Two locations with "ignoring errors during tests" smell
- ❌ `static/audit_clo.js` - Remove obsolete comments
- ⚠️ `tests/integration/helper_csv_export.py:20` - Determine if still needed

## Current Local Changes (Uncommitted)

**Commit Ready**:
- `src/app.py` - Complexity refactoring ✅
- `tests/integration/test_database_service_integration.py` - Fixture fix ✅

## Recommended Action Plan

### Phase 1: Critical CI Fixes (Do First)
1. Fix database URL mismatch in smoke tests workflow
2. Verify/fix SonarCloud coverage paths
3. Update coverage analysis scripts for build/ prefix

### Phase 2: Cleanup Obsolete Files
1. Remove 6 migration/shim scripts
2. Remove/consolidate analyze_pr_coverage_simple.py
3. Move .eslintrc.json to root
4. Remove REPOSITORY_REORGANIZATION_PLAN.md

### Phase 3: Code Quality
1. Fix audit_clo.js DOM issues
2. Fix duplicate import in advance_demo.py
3. Fix maintAInability-gate.sh exit behavior
4. Clean up conftest.py error handling
5. Fix AGENTS.md stray text

### Phase 4: Architectural Issues (Bigger)
1. **CRITICAL**: Untangle seed_db.py demo data mess
2. Move link_courses_to_programs logic to src/ libraries
3. Review test file organization (scripts vs tests/)

## Next Steps

Would you like me to:
A. Start with Phase 1 (CI fixes) to get the build green?
B. Address all issues systematically in order?
C. Focus on the seed_db.py architectural issue first?

