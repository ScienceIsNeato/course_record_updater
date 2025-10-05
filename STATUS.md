# Status: Strategic PR Review - Phase 2

## Last Updated
2025-10-05 03:30 AM

## Current Phase
**Phase 1 Complete**: 14 comments addressed and marked as resolved via GitHub review  
**Phase 2 Active**: 17 remaining comments - strategic grouping in progress

## Comments Addressed (Phase 1) ✅

### Commit Sequence (5 commits)
1. Import consolidation (4 Copilot comments)
2. High-priority bug fixes (3 bugs + 1 doc)
3. Datetime revert (E2E fix)
4. SonarCloud issues (2 code quality)
5. PR review response (14 comments total)

### GitHub Review Submitted
Posted resolution summary with cross-references to all fixed comments.

## Remaining Comments (Phase 2) - Strategic Analysis

### Group A: Documentation Maintenance (3 comments) 🟨
**Risk**: Low | **Priority**: 3
- `NEXT_BACKLOG.md:5` - Update completed items
- `RECURRENT_ANTIPATTERN_LOG.md:7` - Move to cursor-rules
- `SCRIPT_OUTPUT_STANDARDS.md:11` - Remove file

**Rationale**: Documentation cleanup, no code impact

### Group B: Export Architecture (3 comments) 🔴
**Risk**: High | **Priority**: 1  
- `api_routes.py:3154` - Adapter should control file type/data types
- `api_routes.py:3158` - Move imports to top of file
- `api_routes.py:3252` - Mimetype should come from adapter

**Rationale**: Architectural improvement - adapters should own format details. This is a **lower-level change that may obviate surface-level issues**.

### Group C: Export UI (1 comment) 🟡
**Risk**: Medium | **Priority**: 2
- `data_management_panel.html:303` - Rename institution-specific method

**Rationale**: Depends on Group B - adapter changes may affect method naming

### Group D: E2E Test Quality (4 comments) 🟡
**Risk**: Medium | **Priority**: 2
- `tests/e2e/test_import_export.py:56` - Remove redundant pytest.mark.e2e
- `tests/e2e/test_import_export.py:59` - Improve docstring wording
- `tests/e2e/test_import_export.py:99` - Remove _debug suffix
- `tests/e2e/test_import_export.py:283` - Address sequential feeling

**Rationale**: Test maintainability improvements

### Group E: E2E Infrastructure (2 comments) 🟢
**Risk**: Low | **Priority**: 3
- `tests/e2e/conftest.py:240` - Reduce timeout to 2s max
- `run_uat.sh:49` - Update docs --save-videos flag

**Rationale**: Minor infrastructure tweaks

### Group F: E2E Test Coverage (1 comment) 🟣
**Risk**: Medium | **Priority**: Deferred
- `tests/e2e/test_import_export.py:1069` - Implement remaining UAT cases

**Rationale**: Scope expansion - discuss with user first

### Group G: Code Style (1 comment) 🟢
**Risk**: Very Low | **Priority**: 4
- `scripts/ship_it.py:93` - [nitpick] Use dataclass for check definitions

**Rationale**: Nice-to-have refactoring

## Recommended Execution Order

1. **Group B** (Export Architecture) - Foundational change
2. **Group C** (Export UI) - Depends on B
3. **Group D** (E2E Test Quality) - Independent improvements
4. **Group E** (E2E Infrastructure) - Quick wins
5. **Group A** (Documentation) - Cleanup
6. **Group G** (Code Style) - Optional polish
7. **Group F** (E2E Coverage) - Discuss scope

## Next Action
Start with Group B (Export Architecture) as it's the highest-risk, lowest-level change that may simplify other issues.
