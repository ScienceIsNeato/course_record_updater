# PR #39 Resolution Plan - 2026-01-07 (Updated)

## Already Resolved in Step 2 ✅
- [x] **PRRT_kwDOOV6J2s5n9yYG**: Database URL mismatch → Fixed in e925af5, RESOLVED
- [x] **PRRT_kwDOOV6J2s5oKNu6**: CI seeds wrong DB → Fixed in e925af5, RESOLVED  
- [x] **PRRT_kwDOOV6J2s5oUazP**: DB mismatch --env dev → Fixed in e925af5, RESOLVED
- [x] **PRRT_kwDOOV6J2s5n5cfi**: seed_db architecture → Addressed in b7ee2d2, COMMENTED

## High Priority - Fix Now

### 1. Session Date Storage Bug (CRITICAL - Breaks API)
**Threads**: PRRT_kwDOOV6J2s5oJ8Dr, PRRT_kwDOOV6J2s5oRDBi (duplicates)
**File**: data/session/manager.py:108
**Issue**: Stores system_date_override as ISO string, API expects datetime
**Fix**: Store as datetime object, handle serialization properly
**Commit**: fix: store session dates as datetime objects

### 2. Missing build/ Directory (CI Breaking)
**Thread**: PRRT_kwDOOV6J2s5oVAuS
**File**: .github/workflows/quality-gate.yml:505
**Issue**: Coverage writes to build/coverage.xml but build/ may not exist
**Fix**: Add `mkdir -p build` before coverage generation
**Commit**: fix: ensure build directory exists before coverage generation

## Medium Priority

### 3. Unpinned GitHub Actions
**Thread**: PRRT_kwDOOV6J2s5n9X2D
**File**: .github/workflows/quality-gate.yml:534
**Issue**: actions/checkout@v4 not pinned to commit SHA
**Fix**: Pin to specific commit SHAs
**Commit**: fix: pin GitHub Actions to commit SHAs for security

## Low Priority - Demo Tooling (Non-Production)

### 4. Demo Manifest Institution Index Bug
**Threads**: PRRT_kwDOOV6J2s5oTkPu, PRRT_kwDOOV6J2s5oVG6e (duplicate)
**File**: demos/full_semester_manifest.json:22
**Issue**: Mike admin references institution_idx: 1, but only index 0 exists
**Fix**: Remove Mike (demo only has 1 institution) OR add institutions array
**Commit**: fix: correct institution index in demo manifest

### 5. Demo Runner Working Directory Issues (7 comments)
**Threads**: Multiple (PRRT_kwDOOV6J2s5oJ8Dm, ...5oKNu2, ...5oTkPl, ...5oT4Xx, ...5oT4Xy, ...5oUazV, ...5oVAuM)
**File**: demos/run_demo.py
**Issue**: Inconsistent working directory handling and variable substitution
**Fix**: Refactor to use self.working_dir consistently
**Commit**: fix: standardize working directory handling in demo runner

### 6. Hardcoded Absolute Path
**Thread**: PRRT_kwDOOV6J2s5oUazK
**File**: demos/full_semester_workflow.json:11
**Issue**: Hardcoded /Users/pacey/Documents/SourceCode/...
**Fix**: Use relative path or remove
**Commit**: fix: remove hardcoded absolute path from demo workflow

## Local Test Failures (Address After Comments)
- Frontend Check: Server dependency
- Coverage on New Code: Investigate  
- Smoke Tests: Server dependency
- Security Audit: Investigate
- E2E Tests: 3 minor failures (dropdowns, JS console)

## Execution Order:
1. ✅ Resolve stale comments (DONE in Step 2)
2. Fix session date storage (HIGH)
3. Fix build directory (HIGH)
4. Fix unpinned actions (MEDIUM)
5. Fix demo manifest/runner issues (LOW)
6. Address local test failures
7. Push and monitor CI
