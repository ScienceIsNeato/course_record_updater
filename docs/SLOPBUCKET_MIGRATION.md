# Quality Gate Migration to slopbucket

## Status: IN PROGRESS

⚠️ **This migration is incomplete.** The slopbucket framework is functional but does not yet have feature parity with ship_it.py. The old scripts cannot be safely deleted until slopbucket implements all required checks.

## Current State

### What's Done
- ✅ slopbucket framework created with core architecture
- ✅ Added as git submodule at `tools/slopbucket`
- ✅ Wrapper script `scripts/quality_gate.py` created
- ✅ Basic checks working:
  - `python-lint-format` (black, isort, flake8)
  - `python-tests` (pytest with coverage data)
  - `python-coverage` (80% threshold)
  - `python-static-analysis` (mypy)
  - `js-lint-format` (eslint, prettier)
  - `js-tests` (jest)

### What's NOT Done
- ❌ ship_it.py NOT deleted (CI depends on it)
- ❌ maintAInability-gate.sh NOT deleted (CI depends on it)
- ❌ CI workflow NOT updated (still uses ship_it.py)
- ❌ Missing checks needed for feature parity:
  - security (bandit, semgrep, safety)
  - duplication
  - complexity (radon, xenon)
  - smoke tests
  - integration tests
  - e2e tests (Playwright)
  - python-new-code-coverage (diff-cover)
  - js-coverage

## Migration Path

### Phase 1: Current (Coexistence)
Both ship_it.py and slopbucket exist. CI uses ship_it.py.

```bash
# Old way (still works, used by CI)
python scripts/ship_it.py --checks commit

# New way (for manual testing)
python scripts/quality_gate.py --checks quick
```

### Phase 2: Feature Parity (TODO)
Implement remaining checks in slopbucket until it can replace ship_it.py.

### Phase 3: Full Migration (TODO)
1. Update CI workflow to use `scripts/quality_gate.py`
2. Delete `scripts/ship_it.py`
3. Delete `scripts/maintAInability-gate.sh`

## Using the Current Slopbucket

For checks that ARE implemented:

```bash
# Quick lint check
python scripts/quality_gate.py --checks quick

# Python lint + tests + mypy (works)
python scripts/quality_gate.py --checks python-lint-format python-tests python-static-analysis

# List available checks
python scripts/quality_gate.py --list-checks
```

## Check Availability Matrix

| Check | ship_it.py | slopbucket | Notes |
|-------|------------|------------|-------|
| python-lint-format | ✅ | ✅ | Feature parity |
| python-tests | ✅ | ✅ | Feature parity |
| python-coverage | ✅ | ✅ | Feature parity |
| python-static-analysis | ✅ | ✅ | Feature parity |
| js-lint-format | ✅ | ✅ | Feature parity |
| js-tests | ✅ | ✅ | Feature parity |
| security | ✅ | ❌ | Needs implementation |
| duplication | ✅ | ❌ | Needs implementation |
| complexity | ✅ | ❌ | Needs implementation |
| smoke | ✅ | ❌ | Needs implementation |
| integration | ✅ | ❌ | Needs implementation |
| e2e | ✅ | ❌ | Needs implementation |
| python-new-code-coverage | ✅ | ❌ | Needs implementation |
| js-coverage | ✅ | ❌ | Needs implementation |

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
