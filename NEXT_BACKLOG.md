# Next Backlog

## 🚨 IMMEDIATE PRIORITY

### E2E UI Testing for Email Suite (9 User Stories Remaining)
**Status**: Blocked for next PR - CRITICAL NEXT TASK  
**Context**: Part 2 of email service refactoring PR series  
**What's Done**: Completed 1 E2E test for instructor invitation use case  
**What's Left**: 9 user stories for comprehensive email suite UI validation

**🔴 THIS MUST BE THE NEXT PR AFTER CURRENT EMAIL SERVICE PR MERGES**

**Remaining User Stories**:
1. Password reset email flow (UI + verification)
2. Bulk reminder email flow (UI + progress tracking)
3. Course assignment notification flow
4. Program invitation flow
5. Institution admin invitation flow
6. Email template customization (if applicable)
7. Email delivery status monitoring
8. Failed email retry mechanism
9. Email whitelist configuration UI

**Success Criteria**:
- All 9 user stories have E2E tests via Playwright
- Email verification via Ethereal IMAP for each flow
- Full coverage of email-triggered UI workflows
- Documentation of E2E test patterns for future features

**Note**: Current PR (1 of 2) focuses on email service architecture. Next PR (2 of 2) will complete E2E test coverage.

---

## High Priority

### API Refactoring (Incremental Extraction)
**Status**: Plan complete, ready to execute  
**Document**: See `API_REFACTOR_PLAN.md` for detailed strategy  
**Approach**: One domain at a time, source + tests together, commit after each

**Key Principles**:
- Move source AND tests together in same commit
- Keep old routes working until new ones proven
- Run full test suite after each extraction
- Maintain 80%+ coverage throughout
- Each commit is independently deployable

**Extraction Order** (12 domains):
1. Health/System
2. Dashboard Data
3. Users
4. Courses
5. Terms
6. Sections
7. Programs
8. Institutions
9. Import/Export
10. Outcomes
11. Offerings
12. Audit

**Success Criteria**:
- All E2E tests pass
- All unit tests pass
- Coverage stays 80%+
- No functionality broken

---

## Medium Priority

### SonarCloud Quality Issues
- Cognitive complexity in api_routes.py (will be resolved by refactoring)
- String literal constants (may be false positive)
- Accessibility issues in templates (low priority)

### Test Coverage Improvements
- Focus on error paths and edge cases
- Target: Maintain 80%+ throughout refactoring

---

## Low Priority

### Documentation
- Update API documentation after refactoring
- Developer onboarding guide
- Architecture decision records (ADRs)
