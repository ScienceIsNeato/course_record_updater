# CI/CD Setup Guide

## 🚀 Continuous Integration & Quality Gates

This repository uses GitHub Actions to mirror our local quality gate system, ensuring consistent code quality across all environments.

### 📊 CI Workflows

#### 1. **Quality Gate** (`.github/workflows/quality-gate.yml`)
- **Triggers**: Push/PR to `main`, `develop`
- **Matrix**: Python 3.9, 3.11, 3.13
- **Checks**: Format, Lint, Tests (80% coverage), Security, Types
- **Artifacts**: Coverage reports, security scan results

#### 2. **Pre-commit Hooks** (`.github/workflows/pre-commit.yml`)
- **Triggers**: Push/PR to `main`, `develop`
- **Purpose**: Validates pre-commit configuration
- **Tools**: black, isort, flake8, bandit, mypy

#### 3. **Security Scan** (`.github/workflows/security-scan.yml`)
- **Triggers**: Daily at 2 AM UTC, dependency changes
- **Tools**: Safety, Bandit, CodeQL
- **Features**: Automatic issue creation on vulnerabilities

### 🔧 Local Development Setup

#### Install Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Install hooks for this repo
pre-commit install

# Run on all files (optional)
pre-commit run --all-files
```

#### Run Quality Gates Locally
```bash
# Essential checks (mirrors CI)
python scripts/ship_it.py

# Specific checks
python scripts/ship_it.py --checks format lint tests

# Comprehensive validation
python scripts/ship_it.py --checks format lint tests security types
```

### 🎯 Quality Standards

#### **80% Test Coverage Threshold**
- Enforced in both local and CI environments
- Builds fail if coverage drops below 80%
- Coverage reports uploaded to Codecov

#### **Security Standards**
- Daily dependency vulnerability scanning
- Static code analysis with Bandit
- CodeQL security analysis
- Automatic issue creation for vulnerabilities

#### **Code Quality Standards**
- Black formatting (88 char line length)
- Import organization with isort
- Critical lint errors only (E9, F63, F7, F82)
- Type checking with mypy
- Pre-commit hooks for consistency

### 🏷️ Special CI Triggers

#### **Comprehensive Check Label**
Add the `comprehensive-check` label to a PR to trigger full validation:
- All quality checks (format, lint, tests, security, types, imports)
- Extended security scanning
- Performance analysis
- Full artifact collection

#### **Matrix Testing**
- Python 3.9: Minimum supported version
- Python 3.11: Primary development version
- Python 3.13: Latest stable version

### 📈 CI Performance

#### **Parallel Execution**
- Quality checks run in parallel jobs
- Security and type checking as separate jobs
- Matrix builds for multi-Python support

#### **Caching Strategy**
- pip dependencies cached
- Pre-commit hooks cached
- Reduces build time by ~60%

#### **Fail-Fast Strategy**
- Essential checks must pass before security/type checks
- Early failure detection saves CI resources
- Clear failure reporting with artifacts

### 🔍 Monitoring & Reporting

#### **Status Badges**
Add to README.md:
```markdown
[![Quality Gate](https://github.com/ScienceIsNeato/course_record_updater/workflows/Quality%20Gate/badge.svg)](https://github.com/ScienceIsNeato/course_record_updater/actions/workflows/quality-gate.yml)
[![Security Scan](https://github.com/ScienceIsNeato/course_record_updater/workflows/Security%20Scan/badge.svg)](https://github.com/ScienceIsNeato/course_record_updater/actions/workflows/security-scan.yml)
[![codecov](https://codecov.io/gh/ScienceIsNeato/course_record_updater/branch/main/graph/badge.svg)](https://codecov.io/gh/ScienceIsNeato/course_record_updater)
```

#### **Artifact Collection**
- Coverage reports (XML, HTML)
- Security scan results (JSON)
- Type checking reports
- Comprehensive validation results

### 🛡️ Branch Protection

Recommended branch protection rules for `main`:
```yaml
# .github/branch-protection.yml
protection_rules:
  main:
    required_status_checks:
      - "quality-gate (3.11)"
      - "security-audit"
      - "type-checking"
    required_reviews: 1
    dismiss_stale_reviews: true
    require_code_owner_reviews: true
    restrictions:
      users: []
      teams: ["maintainers"]
```

### 📋 Troubleshooting

#### **Common CI Failures**
1. **Coverage Below 80%**: Add more unit tests
2. **Security Vulnerabilities**: Update dependencies with `pip install --upgrade`
3. **Type Errors**: Add type annotations or mypy ignores
4. **Format Errors**: Run `black . && isort .` locally

#### **Local vs CI Differences**
- CI uses clean environment (no local configs)
- Different Python versions may have different behaviors
- Network timeouts may affect dependency installation

#### **Performance Issues**
- Use `--fail-fast` for rapid development
- Cache dependencies locally with pip-tools
- Run specific checks instead of full suite during development

This CI setup ensures that our quality standards are consistently enforced across all contributors and deployment environments.
