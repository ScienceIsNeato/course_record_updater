# Quality Gate Migration to slopbucket

## Status: IN PROGRESS

**The migration is partially complete.** The slopbucket framework has been created with core checks, but does NOT yet have feature parity with ship_it.py. The old scripts are retained until parity is achieved.

## What's Done

### slopbucket Framework (tools/slopbucket)
- Core architecture: registry, executor, reporter, subprocess runner
- Self-validating: passes its own commit check with 80% coverage (191 tests)
- 6 checks implemented and passing:
  - `python-lint-format` (black, isort, flake8)
  - `python-tests` (pytest with coverage data)
  - `python-coverage` (80% threshold)
  - `python-static-analysis` (mypy)
  - `js-lint-format` (eslint, prettier)
  - `js-tests` (jest)

### course_record_updater Integration
- slopbucket added as git submodule at `tools/slopbucket`
- Wrapper script `scripts/quality_gate.py` created
- **ship_it.py RETAINED** (not deleted - parity not yet achieved)
- **maintAInability-gate.sh RETAINED** (not deleted - parity not yet achieved)

## What's NOT Done - Missing Checks

The following checks exist in ship_it.py but are NOT YET implemented in slopbucket. These MUST be implemented before ship_it.py can be safely deleted:

| Check | ship_it.py | slopbucket | Gap |
|-------|-----------|------------|-----|
| python-lint-format | black, isort, flake8 | black, isort, flake8 | None |
| python-tests | pytest | pytest | None |
| python-coverage | 80% threshold | 80% threshold | None |
| python-static-analysis | mypy | mypy | None |
| js-lint-format | eslint, prettier | eslint, prettier | None |
| js-tests | jest | jest | None |
| **security** | bandit, semgrep, safety | **NOT IMPLEMENTED** | **MISSING** |
| **duplication** | jscpd, custom | **NOT IMPLEMENTED** | **MISSING** |
| **complexity** | radon, xenon | **NOT IMPLEMENTED** | **MISSING** |
| **smoke** | pytest -m smoke | **NOT IMPLEMENTED** | **MISSING** |
| **integration** | pytest -m integration | **NOT IMPLEMENTED** | **MISSING** |
| **e2e** | playwright | **NOT IMPLEMENTED** | **MISSING** |
| **python-new-code-coverage** | diff-cover | **NOT IMPLEMENTED** | **MISSING** |
| **js-coverage** | jest --coverage | **NOT IMPLEMENTED** | **MISSING** |

## Remaining Work to Achieve Parity

1. **Implement missing checks** (8 checks listed above)
2. **Verify fail-fast behavior** matches ship_it.py
3. **Verify execution order** matches ship_it.py
4. **Verify auto-fix behavior** matches ship_it.py
5. **Update CI workflow** to use slopbucket instead of ship_it.py
6. **Delete ship_it.py and maintAInability-gate.sh** only after all above complete

## Current Usage

Until parity is achieved, continue using ship_it.py:

```bash
# Standard commit validation (use this!)
python scripts/ship_it.py

# Full PR validation
python scripts/ship_it.py --checks PR
```

The new slopbucket can be tested in parallel:

```bash
# Test slopbucket (limited checks only)
python scripts/quality_gate.py --checks commit

# List available checks
python scripts/quality_gate.py --list-checks
```

## Available slopbucket Checks (Current)

| Check | Status | Description |
|-------|--------|-------------|
| python-lint-format | Implemented | black, isort, flake8 |
| python-tests | Implemented | pytest with coverage |
| python-coverage | Implemented | 80% threshold |
| python-static-analysis | Implemented | mypy |
| js-lint-format | Implemented | eslint, prettier |
| js-tests | Implemented | jest |

## Check Aliases

- `commit`: python-lint-format, python-static-analysis, python-tests, python-coverage
- `quick`: python-lint-format, python-static-analysis
- `pr`: All checks (currently same as commit until more checks added)

## Submodule Management

```bash
# Initialize submodule (first time)
git submodule update --init --recursive

# Update submodule to latest
git submodule update --remote tools/slopbucket

# See submodule status
git submodule status
```

## For More Information

- `tools/slopbucket/README.md` - Usage guide
- `tools/slopbucket/MIGRATION_AND_REFACTOR_PLANNING.md` - Detailed migration plan
