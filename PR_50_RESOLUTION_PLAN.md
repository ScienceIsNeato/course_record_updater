# PR #50 Resolution Plan

**Created**: 2026-01-18  
**PR**: https://github.com/ScienceIsNeato/course_record_updater/pull/50  
**Strategy**: Group by concept, resolve as we fix

## Already Resolved (Files Deleted by User) ✅

- [x] Comment #1: Hardcoded API key in `MANUAL_STEPS_REQUIRED.md`  
      → File deleted by user ✅
- [x] Comment #1: Hardcoded API key in `docs/setup/EMAIL_SETUP_CHECKLIST.md`  
      → File deleted by user ✅

## High Severity Issues (Fix First)

- [ ] **Comment #2**: SECRET_KEY missing from deploy.yml
      → File: `.github/workflows/deploy.yml` line 101-102
      → Fix: Add SECRET_KEY back to --update-secrets
      → Impact: Flask sessions won't work securely without it

- [ ] **Comment #5**: seed_remote_db.sh targets wrong database
      → File: `scripts/seed_remote_db.sh` line 227-244  
      → Fix: Set DATABASE_URL to local file before calling seed_db.py
      → Impact: Seeds Neon instead of downloaded file

## Medium Severity Issues

- [ ] **Comment #6**: Demo runner incompatible with restart_server.sh
      → Files: `demos/run_demo.py`, `demos/full_semester_workflow.json`
      → Fix: Demo only uses `local` env (not dev/staging/prod)
      → Impact: Demo fails when non-local env selected

- [ ] **Comment #9**: DEMO_PASSWORD undefined in workflow
      → File: `demos/full_semester_workflow.json` line 422-423
      → Fix: Add DEMO_PASSWORD to context_vars or use hardcoded value
      → Impact: Auth fails in demo

## Low Severity / Questions

- [ ] **Comment #3**: Duplicate code in demos/run_demo.py
      → File: `demos/run_demo.py` line 177-181
      → Fix: Remove duplicate lines

- [ ] **Comment #4**: Duplicate main() in seed_db.py
      → File: `scripts/seed_db.py` line 1700-1706
      → Fix: Remove duplicate main execution block

- [ ] **Comment #7**: Archive create_missing_indexes.py?
      → User question: "should we archive this?"
      → Decision: Keep it - useful diagnostic for future Neon setups

- [ ] **Comment #8**: Is seed_remote_db.sh still used?
      → User question: "is this still being used?"
      → Decision: YES - it's the proper way to seed GCS-backed databases

## Resolution Order

1. Fix HIGH severity first (SECRET_KEY, seed_remote_db.sh)
2. Fix MEDIUM severity (demo runner issues)
3. Fix LOW severity (duplicates)
4. Reply to questions with decisions
5. Commit and push when ALL resolved
6. Monitor CI

## Commit Strategy

Will make 3 thematic commits:
1. `fix: security issues (SECRET_KEY, seed_remote_db.sh)`
2. `fix: demo runner compatibility with local-only restart`
3. `chore: remove duplicate code blocks`
