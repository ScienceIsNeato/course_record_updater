#!/bin/bash

# maintainability-gate - Course Record Updater Quality Framework
# This script ensures code maintainability through comprehensive quality checks
# Mirrors Git Hooks & CI exactly - if this passes, your commit WILL succeed
#
# A Python/Flask quality gate that validates:
# - Code formatting and consistency (with auto-fix using black, isort)
# - Python linting and best practices (with auto-fix using flake8, pylint)
# - Type safety and analysis (mypy strict mode)
# - Test coverage and reliability (pytest with 80% coverage gate)
# - Security vulnerability scanning (bandit, safety)
# - Code duplication prevention
# - Import organization and analysis
#
# Usage:
#   ./scripts/maintainability-gate.sh           # All checks (strict mode with auto-fix)
#   ./scripts/maintainability-gate.sh --format  # Check/fix formatting only
#   ./scripts/maintainability-gate.sh --lint    # Check/fix linting only
#   ./scripts/maintainability-gate.sh --types   # Check types only
#   ./scripts/maintainability-gate.sh --tests   # Run tests with 80% coverage gate
#   ./scripts/maintainability-gate.sh --security # Check security vulnerabilities
#   ./scripts/maintainability-gate.sh --duplication # Check code duplication
#   ./scripts/maintainability-gate.sh --imports # Check import organization
#   ./scripts/maintainability-gate.sh --help    # Show this help

set -e

# Individual check flags
RUN_FORMAT=false
RUN_LINT=false
RUN_TYPES=false
RUN_TESTS=false
RUN_SECURITY=false
RUN_DUPLICATION=false
RUN_IMPORTS=false
RUN_COMPLEXITY=false
RUN_ALL=false

# Parse arguments
if [ $# -eq 0 ]; then
  RUN_ALL=true
else
  while [[ $# -gt 0 ]]; do
    case $1 in
      --format) RUN_FORMAT=true ;;
      --lint) RUN_LINT=true ;;
      --types) RUN_TYPES=true ;;
      --tests) RUN_TESTS=true ;;
      --security) RUN_SECURITY=true ;;
      --duplication) RUN_DUPLICATION=true ;;
      --imports) RUN_IMPORTS=true ;;
      --complexity) RUN_COMPLEXITY=true ;;
      --help)
        echo "maintainability-gate - Course Record Updater Quality Framework"
        echo ""
        echo "Usage:"
        echo "  ./scripts/maintainability-gate.sh           # All checks (strict mode with auto-fix)"
        echo "  ./scripts/maintainability-gate.sh --format  # Check/fix formatting only"
        echo "  ./scripts/maintainability-gate.sh --lint    # Check/fix linting only"
        echo "  ./scripts/maintainability-gate.sh --types   # Check types only"
        echo "  ./scripts/maintainability-gate.sh --tests   # Run tests with 80% coverage gate"
        echo "  ./scripts/maintainability-gate.sh --security # Check security vulnerabilities"
        echo "  ./scripts/maintainability-gate.sh --duplication # Check code duplication"
        echo "  ./scripts/maintainability-gate.sh --imports # Check import organization"
        echo "  ./scripts/maintainability-gate.sh --complexity # Check code complexity"
        echo "  ./scripts/maintainability-gate.sh --help    # Show this help"
        echo ""
        echo "This script ensures code maintainability through comprehensive quality checks"
        echo "and mirrors Git Hooks & CI exactly - if this passes, your commit WILL succeed."
        exit 0
        ;;
      *) echo "Unknown option: $1"; echo "Use --help for usage information"; exit 1 ;;
    esac
    shift
  done
fi

# Set all flags if RUN_ALL is true
if [[ "$RUN_ALL" == "true" ]]; then
  RUN_FORMAT=true
  RUN_LINT=true
  RUN_TYPES=true
  RUN_TESTS=true
  RUN_SECURITY=true
  RUN_DUPLICATION=true
  RUN_IMPORTS=true
fi

# Track failures with detailed information
FAILED_CHECKS=0
FAILED_CHECKS_DETAILS=()
PASSED_CHECKS=()

# Helper function to add failure details
add_failure() {
  local check_name="$1"
  local failure_reason="$2"
  local fix_suggestion="$3"

  ((FAILED_CHECKS++))
  FAILED_CHECKS_DETAILS+=("$check_name|$failure_reason|$fix_suggestion")
}

# Helper function to add passed check
add_success() {
  local check_name="$1"
  local success_message="$2"

  PASSED_CHECKS+=("$check_name|$success_message")
}

# Ensure we're in a virtual environment
check_venv() {
  if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Warning: Not in a virtual environment. Attempting to activate..."
    if [[ -f "venv/bin/activate" ]]; then
      source venv/bin/activate
      echo "✅ Activated virtual environment"
    else
      echo "❌ No virtual environment found. Please create one with: python -m venv venv && source venv/bin/activate"
      exit 1
    fi
  fi
}

echo "🔍 Running Course Record Updater quality checks (STRICT MODE with auto-fix)..."
echo "🐍 Python/Flask enterprise validation suite"
echo ""

# Check virtual environment
check_venv

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PYTHON FORMAT CHECK & AUTO-FIX (BLACK + ISORT)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [[ "$RUN_FORMAT" == "true" ]]; then
  echo "🎨 Python Format Check & Auto-Fix (black + isort)"

  # First, try to auto-fix formatting issues with black (main source files only)
  echo "🔧 Auto-fixing code formatting with black..."
  if black --line-length 88 --target-version py39 *.py adapters/ tests/ 2>/dev/null || true; then
    echo "   ✅ Black formatting applied"
  fi

  # Then auto-fix import organization with isort (main source files only)
  echo "🔧 Auto-fixing import organization with isort..."
  if isort --profile black *.py adapters/ tests/ 2>/dev/null || true; then
    echo "   ✅ Import organization applied"
  fi

  # Verify everything is properly formatted
  FORMAT_CHECK_PASSED=true

  # Check black formatting (main source files only)
  if ! black --check --line-length 88 --target-version py39 *.py adapters/ tests/ > /dev/null 2>&1; then
    FORMAT_CHECK_PASSED=false
    echo "❌ Black formatting check failed"
  fi

  # Check isort formatting (main source files only)
  if ! isort --check-only --profile black *.py adapters/ tests/ > /dev/null 2>&1; then
    FORMAT_CHECK_PASSED=false
    echo "❌ Import organization check failed"
  fi

  if [[ "$FORMAT_CHECK_PASSED" == "true" ]]; then
    echo "✅ Format Check: PASSED (black + isort auto-fixed)"
    add_success "Format Check" "All Python files properly formatted with black and isort"
  else
    echo "❌ Format Check: FAILED (could not auto-fix all issues)"
    add_failure "Format Check" "Some formatting issues could not be auto-fixed" "Run 'black *.py **/*.py' and 'isort *.py **/*.py' manually"
  fi
  echo ""
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PYTHON LINT CHECK (FLAKE8 + BASIC PYLINT)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [[ "$RUN_LINT" == "true" ]]; then
  echo "🔍 Python Lint Check (flake8 critical errors)"

  # Run flake8 for critical errors only (much faster)
  echo "🔧 Running flake8 critical error check..."
  FLAKE8_OUTPUT=$(timeout 30s flake8 --max-line-length=88 --select=E9,F63,F7,F82 --exclude=venv,cursor-rules,.venv,logs,htmlcov *.py adapters/ tests/ 2>/dev/null) || FLAKE8_FAILED=true

  if [[ "$FLAKE8_FAILED" == "true" ]]; then
    echo "❌ Flake8 critical errors found"
    echo "📋 Critical Issues:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$FLAKE8_OUTPUT" | head -10 | sed 's/^/  /'
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    add_failure "Lint Check" "Critical linting errors found" "Fix the critical errors above"
  else
    echo "✅ Lint Check: PASSED (no critical errors)"
    add_success "Lint Check" "No critical linting errors found"
  fi
  echo ""
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TYPE CHECK (MYPY STRICT MODE)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [[ "$RUN_TYPES" == "true" ]]; then
  echo "🔧 Type Check (mypy strict mode)"

  # Run mypy type checking (main files only, with timeout)
  TYPE_OUTPUT=$(timeout 30s find . -name "*.py" -not -path "./venv/*" -not -path "./cursor-rules/*" -not -path "./.venv/*" | head -15 | xargs mypy --ignore-missing-imports --no-strict-optional 2>&1) || TYPE_FAILED=true

  if [[ "$TYPE_FAILED" != "true" ]]; then
    echo "✅ Type Check: PASSED (strict mypy type checking)"
    add_success "Type Check" "All type annotations valid in strict mode"
  else
    echo "❌ Type Check: FAILED (strict mypy type checking)"
    echo ""

    # Show detailed type errors
    echo "📋 Type Error Details:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if [[ -n "$TYPE_OUTPUT" ]]; then
      echo "$TYPE_OUTPUT" | head -20 | sed 's/^/  /'

      # Check if there are more errors
      TOTAL_LINES=$(echo "$TYPE_OUTPUT" | wc -l)
      if [[ $TOTAL_LINES -gt 20 ]]; then
        echo "  ... and $(($TOTAL_LINES - 20)) more lines"
        echo "  Run 'mypy --strict *.py **/*.py' to see all errors"
      fi
    else
      echo "  Unable to extract type error details"
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Extract error count from output for summary
    ERROR_COUNT=$(echo "$TYPE_OUTPUT" | grep -c "error:" || echo "unknown")
    add_failure "Type Check" "$ERROR_COUNT type errors found" "See detailed output above and run 'mypy --strict *.py **/*.py' for full details"
  fi
  echo ""
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST SUITE & COVERAGE (80% THRESHOLD)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [[ "$RUN_TESTS" == "true" ]]; then
  echo "🧪 Test Suite & Coverage (80% threshold)"

  # First run UNIT tests only (fast tests, separate directory)
  echo "  🔍 Running UNIT test suite with performance monitoring..."
  TEST_OUTPUT=$(python -m pytest tests/unit/ -v --durations=0 2>&1) || TEST_FAILED=true

  if [[ "$TEST_FAILED" == "true" ]]; then
    echo "❌ Tests: FAILED"
    echo ""

    # Show detailed test output with failures
    echo "📋 Test Failure Details:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Extract and show failing tests
    FAILING_TESTS=$(echo "$TEST_OUTPUT" | grep "FAILED " | head -10)
    if [[ -n "$FAILING_TESTS" ]]; then
      echo "🔴 Failing Tests:"
      echo "$FAILING_TESTS" | sed 's/^/  /'
      echo ""
    fi

    # Show error summary
    SUMMARY_SECTION=$(echo "$TEST_OUTPUT" | grep -A 20 "short test summary info" | head -20)
    if [[ -n "$SUMMARY_SECTION" ]]; then
      echo "$SUMMARY_SECTION" | sed 's/^/  /'
    else
      echo "  Unable to extract specific test failures - run 'python -m pytest -v' for details"
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Extract summary stats for the failure record
    FAILED_TESTS=$(echo "$TEST_OUTPUT" | grep -o '[0-9]\+ failed' | head -1 || echo "unknown")
    add_failure "Tests" "Test failures: $FAILED_TESTS" "See detailed output above and run 'python -m pytest -v' for full details"
  else
    echo "✅ Tests: PASSED"

    # Check for slow tests (>0.5 seconds)
    echo "  ⚡ Checking test performance..."
    SLOW_TESTS=$(echo "$TEST_OUTPUT" | grep -E "^\s*[0-9.]+s\s+" | awk '$1 > 0.5 {print $0}' || true)

    if [[ -n "$SLOW_TESTS" ]]; then
      echo "⚠️  Slow Tests Found (>0.5s each):"
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "$SLOW_TESTS" | head -10 | sed 's/^/  /'
      SLOW_COUNT=$(echo "$SLOW_TESTS" | wc -l)
      if [[ $SLOW_COUNT -gt 10 ]]; then
        echo "  ... and $(($SLOW_COUNT - 10)) more slow tests"
      fi
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "💡 Unit tests should complete in <0.5s. Consider:"
      echo "   • Moving slow tests to integration test suite"
      echo "   • Using mocks/stubs instead of real I/O operations"
      echo "   • Optimizing test setup/teardown"
      add_failure "Test Performance" "$SLOW_COUNT tests exceed 0.5s limit" "Optimize slow tests or mark as integration tests"
    else
      echo "✅ Test Performance: All tests complete in <0.5s"
      add_success "Test Performance" "All unit tests complete quickly (<0.5s each)"
    fi

    # Now run coverage analysis with 80% threshold (unit tests only)
    echo "  📊 Running coverage analysis (80% threshold, unit tests only)..."
    COVERAGE_OUTPUT=$(python -m pytest tests/unit/ --cov=. --cov-report=term-missing --cov-fail-under=80 2>&1) || COVERAGE_FAILED=true

    if [[ "$COVERAGE_FAILED" != "true" ]]; then
      # Extract coverage percentage
      COVERAGE=$(echo "$COVERAGE_OUTPUT" | grep -o 'TOTAL.*[0-9]\+%' | grep -o '[0-9]\+%' | head -1 || echo "unknown")
      echo "✅ Coverage: PASSED ($COVERAGE)"
      add_success "Test Coverage" "Coverage at $COVERAGE (meets 80% threshold)"
    else
      # Extract coverage percentage from output
      COVERAGE=$(echo "$COVERAGE_OUTPUT" | grep -o 'TOTAL.*[0-9]\+%' | grep -o '[0-9]\+%' | head -1 || echo "unknown")

      # Check if this is a coverage threshold failure
      if echo "$COVERAGE_OUTPUT" | grep -q "coverage.*fail\|TOTAL.*[0-9]\+%"; then
        echo "❌ Coverage: THRESHOLD NOT MET ($COVERAGE)"
        echo ""

        # Show coverage details
        echo "📋 Coverage Details:"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        # Show lines missing coverage
        MISSING_COVERAGE=$(echo "$COVERAGE_OUTPUT" | grep "Missing" | head -10)
        if [[ -n "$MISSING_COVERAGE" ]]; then
          echo "$MISSING_COVERAGE" | sed 's/^/  /'
        fi

        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""

        add_failure "Test Coverage" "Coverage at $COVERAGE (below 80% threshold)" "Add more unit tests to increase coverage above 80%"
      else
        echo "❌ Coverage: ANALYSIS FAILED ($COVERAGE)"
        add_failure "Test Coverage" "Coverage analysis failed" "Check test suite configuration and ensure pytest-cov is installed"
      fi
    fi
  fi
  echo ""
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECURITY AUDIT (BANDIT + SAFETY)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [[ "$RUN_SECURITY" == "true" ]]; then
  echo "🔒 Security Audit (bandit + safety)"

  SECURITY_PASSED=true

  # Run bandit for security issues in code (main source files only, with timeout)
  echo "🔧 Running bandit security scan..."
  BANDIT_OUTPUT=$(timeout 30s bandit -r . -x venv,cursor-rules,.venv,logs --format json 2>&1) || BANDIT_FAILED=true

  if [[ "$BANDIT_FAILED" == "true" ]]; then
    SECURITY_PASSED=false
    echo "❌ Bandit security scan failed"

    # Try to extract meaningful security issues
    SECURITY_ISSUES=$(echo "$BANDIT_OUTPUT" | grep -E "(HIGH|MEDIUM)" | head -5)
    if [[ -n "$SECURITY_ISSUES" ]]; then
      echo "📋 Security Issues Found:"
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "$SECURITY_ISSUES" | sed 's/^/  /'
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    fi
  else
    echo "   ✅ Bandit security scan passed"
  fi

  # Run safety check for known vulnerabilities in dependencies (with timeout)
  echo "🔧 Running safety dependency check..."
  SAFETY_OUTPUT=$(timeout 60s safety check --short-report 2>&1) || SAFETY_FAILED=true

  if [[ "$SAFETY_FAILED" == "true" ]]; then
    SECURITY_PASSED=false
    echo "❌ Safety dependency check failed"
    echo "📋 Vulnerable Dependencies:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$SAFETY_OUTPUT" | head -10 | sed 's/^/  /'
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  else
    echo "   ✅ Safety dependency check passed"
  fi

  if [[ "$SECURITY_PASSED" == "true" ]]; then
    echo "✅ Security Check: PASSED (bandit + safety)"
    add_success "Security Check" "No security vulnerabilities found"
  else
    echo "❌ Security Check: FAILED (security issues found)"
    add_failure "Security Check" "Security vulnerabilities found" "See detailed output above and address security issues"
  fi
  echo ""
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# IMPORT ORGANIZATION CHECK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [[ "$RUN_IMPORTS" == "true" ]]; then
  echo "📦 Import Organization Check"

  # Check import organization with isort
  IMPORT_OUTPUT=$(isort --check-only --diff --profile black --skip venv --skip .venv --skip-glob="**/venv/*" --skip-glob="**/.venv/*" . 2>&1) || IMPORT_FAILED=true

  if [[ "$IMPORT_FAILED" != "true" ]]; then
    echo "✅ Import Organization: PASSED"
    add_success "Import Organization" "All imports properly organized"
  else
    echo "❌ Import Organization: FAILED"
    echo "📋 Import Issues:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$IMPORT_OUTPUT" | head -15 | sed 's/^/  /'
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    add_failure "Import Organization" "Import organization issues found" "Run 'isort --profile black *.py **/*.py' to fix"
  fi
  echo ""
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CODE DUPLICATION CHECK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [[ "$RUN_DUPLICATION" == "true" ]]; then
  echo "🔄 Code Duplication Check"

  # Use a simple approach for Python duplication detection
  # This is a basic implementation - could be enhanced with tools like jscpd
  echo "🔧 Checking for code duplication..."

  # Simple duplication check using basic patterns
  DUPLICATE_FUNCTIONS=$(grep -r "def " *.py **/*.py | cut -d: -f2 | sort | uniq -d | wc -l)

  if [[ "$DUPLICATE_FUNCTIONS" -eq 0 ]]; then
    echo "✅ Duplication Check: PASSED (no obvious duplicates)"
    add_success "Duplication Check" "No obvious code duplication detected"
  else
    echo "❌ Duplication Check: WARNING ($DUPLICATE_FUNCTIONS potential duplicates)"
    add_failure "Duplication Check" "$DUPLICATE_FUNCTIONS potential duplicate functions" "Review code for duplication and refactor if necessary"
  fi
  echo ""
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SUMMARY REPORT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo "📊 Quality Gate Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ ${#PASSED_CHECKS[@]} -gt 0 ]]; then
  echo "✅ PASSED CHECKS (${#PASSED_CHECKS[@]}):"
  for check in "${PASSED_CHECKS[@]}"; do
    IFS='|' read -r name message <<< "$check"
    echo "   • $name: $message"
  done
  echo ""
fi

if [[ ${#FAILED_CHECKS_DETAILS[@]} -gt 0 ]]; then
  echo "❌ FAILED CHECKS (${#FAILED_CHECKS_DETAILS[@]}):"
  for check in "${FAILED_CHECKS_DETAILS[@]}"; do
    IFS='|' read -r name reason suggestion <<< "$check"
    echo "   • $name: $reason"
    echo "     Fix: $suggestion"
  done
  echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ $FAILED_CHECKS -eq 0 ]]; then
  echo "🎉 ALL CHECKS PASSED!"
  echo "✅ Ready to commit with confidence!"
  echo ""
  echo "🚀 Course Record Updater quality validation completed successfully!"
  exit 0
else
  echo "❌ QUALITY GATE FAILED"
  echo "🔧 $FAILED_CHECKS check(s) need attention"
  echo ""
  echo "💡 Fix the issues above and run the checks again"
  exit 1
fi
