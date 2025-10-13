# Next Backlog

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
