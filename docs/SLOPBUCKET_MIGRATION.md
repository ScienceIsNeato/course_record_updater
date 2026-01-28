# Quality Gate Migration to slopbucket

## Status: FEATURE PARITY ACHIEVED ✅

**The migration is complete.** The slopbucket framework now has full feature parity with ship_it.py.
The old scripts can be safely removed once CI workflows are updated.

## What's Done

### slopbucket Framework (tools/slopbucket)
- Core architecture: registry, executor, reporter, subprocess runner
- Self-validating: passes its own commit check with 80% coverage
- **18 checks implemented** covering all functionality from ship_it.py:

#### Python Checks
| Check | Description |
|-------|-------------|
| `python-lint-format` | black, isort, flake8 |
| `python-tests` | pytest with coverage data |
| `python-coverage` | 80% threshold |
| `python-static-analysis` | mypy |
| `python-complexity` | radon complexity analysis |
| `python-security` | bandit, safety (CI-only) |
| `python-security-local` | bandit only (local dev) |
| `python-diff-coverage` | diff-cover for PR changes |
| `python-new-code-coverage` | New code coverage validation |
| `smoke-tests` | pytest -m smoke |
| `integration-tests` | pytest -m integration |
| `e2e-tests` | playwright end-to-end tests |

#### JavaScript Checks
| Check | Description |
|-------|-------------|
| `js-lint-format` | eslint, prettier |
| `js-tests` | jest |
| `js-coverage` | jest --coverage |
| `frontend` | Frontend-specific validation |

#### General Checks
| Check | Description |
|-------|-------------|
| `duplication` | jscpd code duplication |
| `template-validation` | Template file validation |

### course_record_updater Integration
- slopbucket added as git submodule at `tools/slopbucket`
- Wrapper script `scripts/quality_gate.py` created

## Remaining Work (Optional Cleanup)

1. **Update CI workflow** to use slopbucket instead of ship_it.py
2. **Delete ship_it.py and maintAInability-gate.sh** (optional - slopbucket is now the preferred tool)

## Current Usage

Use slopbucket for all quality gate needs:

```bash
# Standard commit validation
python scripts/quality_gate.py --checks commit

# Full PR validation
python scripts/quality_gate.py --checks pr

# List available checks
python scripts/quality_gate.py --list-checks

# Run specific checks
python scripts/quality_gate.py --checks python-lint-format,python-tests
```

## Check Aliases

- `commit`: python-lint-format, python-static-analysis, python-tests, python-coverage
- `quick`: python-lint-format, python-static-analysis
- `pr`: All checks including security, complexity, duplication

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
