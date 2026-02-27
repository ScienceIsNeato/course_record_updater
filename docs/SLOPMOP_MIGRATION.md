# Quality Gate Migration to slop-mop

## Status: COMPLETE ✅

**The migration is complete.** This project now uses slop-mop for all quality gate functionality.
The old `ship_it.py` and `maintAInability-gate.sh` scripts have been removed.

## What's Included

### slop-mop Framework

- Core architecture: registry, executor, reporter, subprocess runner
- Self-validating: passes its own commit check with 80% coverage
- **18 checks implemented** covering all functionality from ship_it.py

#### Python Checks

| Check                      | Description                  |
| -------------------------- | ---------------------------- |
| `python-lint-format`       | black, isort, flake8         |
| `python-tests`             | pytest with coverage data    |
| `python-coverage`          | 80% threshold                |
| `python-static-analysis`   | mypy                         |
| `python-complexity`        | radon complexity analysis    |
| `python-security`          | bandit, safety (CI-only)     |
| `python-security-local`    | bandit only (local dev)      |
| `python-diff-coverage`     | diff-cover for PR changes    |
| `python-new-code-coverage` | New code coverage validation |
| `smoke-tests`              | pytest -m smoke              |
| `integration-tests`        | pytest -m integration        |
| `e2e-tests`                | playwright end-to-end tests  |

#### JavaScript Checks

| Check            | Description                  |
| ---------------- | ---------------------------- |
| `js-lint-format` | eslint, prettier             |
| `js-tests`       | jest                         |
| `js-coverage`    | jest --coverage              |
| `frontend`       | Frontend-specific validation |

#### General Checks

| Check                 | Description              |
| --------------------- | ------------------------ |
| `duplication`         | jscpd code duplication   |
| `template-validation` | Template file validation |

### course_record_updater Integration

- slop-mop installed via `pipx install slopmop` (or `pip install slopmop`)
- Wrapper script `scripts/quality_gate.py` for CI backward compatibility

## Usage

### Recommended: Use `sm` directly (local development)

After installing slop-mop:

```bash
pipx install slopmop   # or: pip install slopmop
```

Use the `sm` command with profiles:

```bash
sm validate commit       # Fast commit validation ← USE THIS
sm validate pr           # Full PR validation
sm validate quick        # Ultra-fast lint only
sm validate python       # Python-only validation
sm validate javascript   # JS-only validation
```

### Alternative: Use wrapper script (CI compatibility)

```bash
# Standard commit validation
python scripts/quality_gate.py --checks commit

# Full PR validation
python scripts/quality_gate.py --checks pr

# Run specific checks
python scripts/quality_gate.py --checks python-lint-format,python-tests
```

## Profiles (Quality Gate Groups)

| Profile      | Use Case               | Included Gates                                                     |
| ------------ | ---------------------- | ------------------------------------------------------------------ |
| `commit`     | Fast commit validation | lint, static-analysis, tests, coverage, complexity, security-local |
| `pr`         | Full PR validation     | All Python + JS gates                                              |
| `quick`      | Ultra-fast lint check  | lint, security-local                                               |
| `python`     | All Python gates       | All python-\* gates                                                |
| `javascript` | All JavaScript gates   | All js-\* gates + frontend                                         |
| `e2e`        | End-to-end tests       | smoke, integration, e2e                                            |

## AI Agent Workflow

When a check fails, slop-mop tells you exactly what to do:

```
┌──────────────────────────────────────────────────────────┐
│ 🤖 AI AGENT ITERATION GUIDANCE                           │
├──────────────────────────────────────────────────────────┤
│ Profile: commit                                          │
│ Failed Gate: python-coverage                             │
├──────────────────────────────────────────────────────────┤
│ NEXT STEPS:                                              │
│                                                          │
│ 1. Fix the issue described above                         │
│ 2. Validate: sm validate python-coverage                 │
│ 3. Resume:   sm validate commit                          │
│                                                          │
│ Keep iterating until all checks pass.                    │
└──────────────────────────────────────────────────────────┘
```

## Installation

```bash
# Install via pipx (recommended, isolated environment)
pipx install slopmop

# Or install via pip
pip install slopmop

# Upgrade to latest
pipx upgrade slopmop
```

## For More Information

- https://pypi.org/project/slopmop/ - PyPI package
- https://github.com/ScienceIsNeato/slop-mop - Source repository
