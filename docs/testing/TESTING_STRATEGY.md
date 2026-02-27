# Testing Strategy

## Overview

This document outlines our comprehensive testing approach including automated testing, manual testing, and user acceptance testing.

## Manual User Acceptance Testing

For comprehensive authentication system validation:

- **[UAT_GUIDE.md](UAT_GUIDE.md)**: Complete manual testing protocol with role-based scenarios
- Covers all user roles: Site Admin, Institution Admin, Program Admin, Instructor
- Includes security testing and multi-tenant validation

## Automated Testing Strategy

## Core Testing Principles

### 🎯 NEVER Use Hardcoded Strings in Tests

**Philosophy**: All string comparisons in tests MUST use constants from `constants.py`. This ensures:

- **Consistency**: Single source of truth for all error messages, labels, and text
- **Maintainability**: Change the message once, update all tests automatically
- **SonarCloud Compliance**: Avoids string literal duplication errors
- **Type Safety**: Catch typos at import time, not test runtime

**✅ CORRECT**:

```python
from constants import INVALID_CREDENTIALS_MSG

def test_login_failure(page):
    # Use constant for string comparison
    expect(
        page.locator(f'.alert-danger:has-text("{INVALID_CREDENTIALS_MSG}")')
    ).to_be_visible()
```

**❌ WRONG**:

```python
def test_login_failure(page):
    # Hardcoded string - NEVER do this
    expect(
        page.locator('.alert-danger:has-text("Invalid credentials")')
    ).to_be_visible()
```

**Process**:

1. Check `constants.py` for an existing constant
2. If it doesn't exist, add it to `constants.py` first
3. Import and use the constant in your test
4. Never duplicate strings across test files

**Applies to**:

- Error messages (`INVALID_CREDENTIALS_MSG`)
- Success messages
- Button labels
- Page titles
- API response messages
- Validation messages
- Any user-facing text

## Problem Statement

We discovered that frontend JavaScript errors were only caught through manual testing (clicking buttons and checking browser console). This is inefficient and error-prone. We need automated testing to catch these issues without human intervention.

## Solution: Multi-Layer Testing

### 1. Quick Frontend Check (`./check_frontend.sh`)

**Purpose**: Rapid feedback during development
**Runtime**: ~5 seconds
**When to use**: After every code change, before commits

**Checks**:

- ✅ Server accessibility
- ✅ Required HTML elements present
- ✅ Static assets loading (CSS, JS, images)
- ✅ API health endpoint
- ✅ JavaScript syntax validation

```bash
# Run after making changes
./check_frontend.sh
```

### 2. Comprehensive Smoke Tests (`./run_smoke_tests.sh`)

**Purpose**: Full UI functionality verification
**Runtime**: ~30-60 seconds
**When to use**: Before releases, after major changes

**Checks**:

- ✅ Server startup and accessibility
- ✅ JavaScript initialization without errors
- ✅ Form elements and event listeners
- ✅ Browser console error detection
- ✅ Form validation behavior
- ✅ API endpoint accessibility
- ✅ Static asset loading
- ✅ Dashboard component presence

```bash
# Run for comprehensive testing
./run_smoke_tests.sh
```

### 3. Backend Unit/Integration Tests (`pytest`)

**Purpose**: API and business logic validation
**Runtime**: ~10-30 seconds
**When to use**: Continuously during development

```bash
# Run backend tests
pytest tests/ -v
```

## Development Workflow Integration

### Recommended Workflow

1. **During Development**:

   ```bash
   # Make changes
   ./restart_server.sh    # Non-blocking restart
   ./check_frontend.sh    # Quick validation (~5s)
   ```

2. **Before Committing**:

   ```bash
   ./check_frontend.sh    # Quick check
   pytest tests/ -v       # Backend tests
   ```

3. **Before Releases**:
   ```bash
   ./run_smoke_tests.sh   # Full frontend testing
   pytest tests/ -v       # All backend tests
   ```

### Pre-commit Hook (Optional)

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
echo "Running pre-commit checks..."
./check_frontend.sh && pytest tests/ -v --tb=short
```

## What Each Test Catches

### JavaScript Errors

- **Quick Check**: Syntax errors
- **Smoke Tests**: Runtime errors, console errors, initialization failures

### Missing UI Elements

- **Quick Check**: Basic HTML structure
- **Smoke Tests**: Detailed element presence, event listener setup

### API Issues

- **Quick Check**: Health endpoint accessibility
- **Smoke Tests**: Comprehensive endpoint testing
- **Unit Tests**: Business logic validation

### Static Asset Problems

- **Quick Check**: Asset loading verification
- **Smoke Tests**: Asset integration testing

## Test Dependencies

### Quick Check

- `curl` (standard on most systems)
- `node` (optional, for JS syntax checking)

### Smoke Tests

- `pytest`
- `selenium`
- `requests`
- `chromedriver-autoinstaller`
- Chrome/Chromium browser

### Installation

```bash
pip install pytest selenium requests chromedriver-autoinstaller
```

## Error Examples Caught

### Before Automation

❌ **Manual Discovery**: User clicks button → checks console → finds "Course table body not found!"

### After Automation

✅ **Automated Discovery**:

```bash
./check_frontend.sh
# ✅ JavaScript syntax is valid

./run_smoke_tests.sh
# ❌ JavaScript errors found: ['Course table body not found!']
```

## Future Enhancements

1. **Visual Regression Testing**: Screenshot comparison
2. **Performance Testing**: Load time validation
3. **Accessibility Testing**: WCAG compliance
4. **Cross-browser Testing**: Firefox, Safari support
5. **CI/CD Integration**: GitHub Actions, automated PR checks

## Benefits

- 🚀 **Faster Development**: Immediate feedback on changes
- 🐛 **Early Bug Detection**: Catch issues before they reach users
- 🔄 **Reliable Deployments**: Confidence in release quality
- 📊 **Consistent Quality**: Standardized testing across team
- ⏰ **Time Savings**: No more manual clicking and console checking
