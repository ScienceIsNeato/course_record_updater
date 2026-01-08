# PR #39 Loop #3 Resolution Plan

## Current State
- Previous loop resolved 18 comments
- Bot reviewed our commits and added 12 NEW comments
- CI has 4 failures

## New Unresolved Comments (12):

### High Priority - CI Related:
1. **PRRT_kwDOOV6J2s5oVG6k**: Coverage scope excludes session code (.github/workflows/quality-gate.yml:507)
2. **PRRT_kwDOOV6J2s5oVG6n**: Seed script overrides DB URL (.github/workflows/quality-gate.yml:159)

### Medium Priority - Demo/Test Issues:
3. **PRRT_kwDOOV6J2s5oVOpb**: Manifest non-existent institution (demos/full_semester_manifest.json)
4. **PRRT_kwDOOV6J2s5oVOpf**: Working directory inconsistent (demos/run_demo.py:728)
5. **PRRT_kwDOOV6J2s5oVgDW**: Manifest path parsing (demos/run_demo.py:139)
6. **PRRT_kwDOOV6J2s5oVgDY**: Working directory inconsistent (demos/run_demo.py:728)
7. **PRRT_kwDOOV6J2s5oVgDb**: Demo sequence actions (demos/full_semester_workflow.json:331)
8. **PRRT_kwDOOV6J2s5oaYt7**: Manifest institution index (demos/full_semester_manifest.json)
9. **PRRT_kwDOOV6J2s5oaYt8**: Hardcoded absolute path (demos/full_semester_workflow.json:11)
10. **PRRT_kwDOOV6J2s5oaYt_**: Sequence action skipped (demos/full_semester_workflow.json:309)
11. **PRRT_kwDOOV6J2s5oaYuB**: PATCH method missing (conftest.py:110)
12. **PRRT_kwDOOV6J2s5oax3O**: Working directory broken (demos/run_demo.py:728)

## CI Failures (4):
1. **unit-tests-with-coverage**: Exit 143 (timeout/killed) - tee output swallowing issue?
2. **smoke-tests**: Server/DB config mismatch
3. **e2e-tests**: 57 errors - ALL login failures (401 UNAUTHORIZED)
   - Issue: Absolute path fix not working in CI (different env)
   - Same "readonly database" symptom we fixed locally
4. **security-check**: Exit 1 - detect-secrets or other issue

## Root Cause Analysis:

### E2E Login Failures:
- 401 UNAUTHORIZED across all E2E tests
- Same pattern we fixed locally (absolute paths)
- CI environment: Linux, different file system
- Our fix: `os.path.abspath(worker_db)` - should work on Linux too
- **Hypothesis**: CI missing environment variable or different CWD

### Unit Test Output Swallowing:
- Exit 143 suggests timeout or SIGTERM
- Likely the tee changes are hanging or buffering

## Action Plan:
1. Check if comments 8,9 are duplicates of what we already fixed (manifest/workflow)
2. Address NEW legitimate comments
3. Fix CI environment issues
4. THEN verify ALL resolved before pushing

## Step 2 Check: Any Already Fixed?
Checking if recent commits fixed any of these...

