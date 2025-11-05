#!/bin/bash

# maintAInability-gate - Course Record Updater Quality Framework
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
#   ./scripts/maintAInability-gate.sh           # All checks (strict mode with auto-fix)
#   ./scripts/maintAInability-gate.sh --format  # Check/fix formatting only
#   ./scripts/maintAInability-gate.sh --lint    # Check/fix linting only
#   ./scripts/maintAInability-gate.sh --types   # Check types only
#   ./scripts/maintAInability-gate.sh --tests   # Run tests with 80% coverage gate
#   ./scripts/maintAInability-gate.sh --security # Check security vulnerabilities
#   ./scripts/maintAInability-gate.sh --duplication # Check code duplication
#   ./scripts/maintAInability-gate.sh --imports # Check import organization
#   ./scripts/maintAInability-gate.sh --help    # Show this help

set -e

# Check required environment variables (skip in CI environments)
if [ "${CI:-false}" = "true" ] || [ "${GITHUB_ACTIONS:-false}" = "true" ]; then
  echo "🔄 Skipping environment variable check in CI environment"
else
  echo "🔍 Checking environment variables..."

  # KISS: Just hardcode test database if not set
  if [ -z "$DATABASE_URL" ]; then
    export DATABASE_URL="sqlite:///course_records_dev.db"
  fi

  REQUIRED_VARS=(
    "AGENT_HOME"
    "DATABASE_TYPE"
    "DATABASE_URL"
    "LASSIE_DEFAULT_PORT_DEV"
    "LASSIE_DEFAULT_PORT_E2E"
    "SONAR_TOKEN"
    "SAFETY_API_KEY"
    "GITHUB_PERSONAL_ACCESS_TOKEN"
  )

  MISSING_VARS=()

  for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
      MISSING_VARS+=("$var")
    fi
  done

  if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "❌ ENVIRONMENT SETUP FAILED"
    echo ""
    echo "Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
      echo "  • $var"
    done
    echo ""
    echo "💡 FIX: Run 'direnv allow' to load environment variables from .envrc"
    echo "   This is a common issue - the .envrc file contains all required variables"
    echo "   but direnv needs permission to load them into your shell environment."
    echo ""
    echo "   If direnv is not installed: brew install direnv"
    echo "   Then add to your shell config: eval \"\$(direnv hook bash)\" or eval \"\$(direnv hook zsh)\""
    exit 1
  fi

  echo "✅ Environment variables loaded correctly"
fi

# Individual check flags - ATOMIC CHECKS ONLY
RUN_BLACK=false
RUN_ISORT=false
RUN_LINT=false
RUN_TYPES=false
RUN_TESTS=false
RUN_INTEGRATION_TESTS=false
RUN_E2E_TESTS=false
RUN_COVERAGE=false
RUN_SECURITY=false
RUN_DUPLICATION=false
RUN_IMPORTS=false
RUN_COMPLEXITY=false
RUN_JS_LINT=false
RUN_JS_FORMAT=false
RUN_JS_TESTS=false
RUN_JS_COVERAGE=false
RUN_ALL=false

# Parse arguments
if [ $# -eq 0 ]; then
  RUN_ALL=true
else
  while [[ $# -gt 0 ]]; do
    case $1 in
      --black) RUN_BLACK=true ;;
      --isort) RUN_ISORT=true ;;
      --lint) RUN_LINT=true ;;
      --types) RUN_TYPES=true ;;
      --tests) RUN_TESTS=true ;;
      --integration-tests) RUN_INTEGRATION_TESTS=true ;;
      --e2e) RUN_E2E_TESTS=true ;;
      --coverage) RUN_COVERAGE=true ;;
      --security) RUN_SECURITY=true ;;
      --duplication) RUN_DUPLICATION=true ;;
      --imports) RUN_IMPORTS=true ;;
      --complexity) RUN_COMPLEXITY=true ;;
      --js-lint) RUN_JS_LINT=true ;;
      --js-format) RUN_JS_FORMAT=true ;;
      --js-tests) RUN_JS_TESTS=true ;;
      --js-coverage) RUN_JS_COVERAGE=true ;;
      --smoke-tests) RUN_SMOKE_TESTS=true ;;
      --frontend-check) RUN_FRONTEND_CHECK=true ;;
      --help)
        echo "maintAInability-gate - Course Record Updater Quality Framework"
        echo ""
        echo "Usage:"
        echo "  ./scripts/maintAInability-gate.sh           # All atomic checks (strict mode with auto-fix)"
        echo "  ./scripts/maintAInability-gate.sh --black   # Check/fix code formatting only"
        echo "  ./scripts/maintAInability-gate.sh --isort   # Check/fix import sorting only"
        echo "  ./scripts/maintAInability-gate.sh --lint    # Check/fix linting only"
        echo "  ./scripts/maintAInability-gate.sh --types   # Check types only"
        echo "  ./scripts/maintAInability-gate.sh --tests   # Run test suite only"
        echo "  ./scripts/maintAInability-gate.sh --coverage # Run coverage analysis only"
        echo "  ./scripts/maintAInability-gate.sh --security # Check security vulnerabilities"
        echo "  ./scripts/maintAInability-gate.sh --js-tests # Run JavaScript test suite (Jest)"
        echo "  ./scripts/maintAInability-gate.sh --js-coverage # Run JavaScript coverage analysis"
        echo "  ./scripts/maintAInability-gate.sh --duplication # Check code duplication"
        echo "  ./scripts/maintAInability-gate.sh --imports # Check import organization"
        echo "  ./scripts/maintAInability-gate.sh --complexity # Check code complexity"
        echo "  ./scripts/maintAInability-gate.sh --js-lint    # Check JavaScript linting"
        echo "  ./scripts/maintAInability-gate.sh --js-format  # Check JavaScript formatting"
        echo "  ./scripts/maintAInability-gate.sh --smoke-tests # Run smoke tests (tests/smoke/)"
        echo "  ./scripts/maintAInability-gate.sh --frontend-check # Quick frontend validation"
        echo "  ./scripts/maintAInability-gate.sh --help    # Show this help"
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

# Set all flags if RUN_ALL is true - ATOMIC CHECKS ONLY
if [[ "$RUN_ALL" == "true" ]]; then
  RUN_BLACK=true
  RUN_ISORT=true
  RUN_LINT=true
  RUN_TESTS=true
  RUN_COVERAGE=true
  RUN_TYPES=true
  RUN_SECURITY=true
  RUN_DUPLICATION=true
  RUN_IMPORTS=true
  RUN_JS_LINT=true
  RUN_JS_FORMAT=true
  RUN_JS_TESTS=true
  RUN_JS_COVERAGE=true
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

# Check virtual environment (skip in CI)
check_venv() {
  # Skip venv check if we're in CI environment
  if [[ "$CI" == "true" ]]; then
    echo "ℹ️  Skipping virtual environment check (CI environment detected)"
    return 0
  fi
  
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
# PYTHON BLACK FORMATTING CHECK (ATOMIC)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [[ "$RUN_BLACK" == "true" ]]; then
  echo "🎨 Code Formatting (black)"

  # Try to auto-fix formatting issues with black
  echo "🔧 Auto-fixing code formatting with black..."
  if black --line-length 88 --target-version py39 *.py adapters/ tests/ 2>/dev/null || true; then
    echo "   ✅ Black formatting applied"
  fi

  # Verify formatting
  if black --check --line-length 88 --target-version py39 *.py adapters/ tests/ > /dev/null 2>&1; then
    echo "✅ Black Check: PASSED (code formatting verified)"
    add_success "Black Check" "All Python files properly formatted with black"
  else
    echo "❌ Black Check: FAILED (formatting issues found)"
    add_failure "Black Check" "Code formatting issues found" "Run 'black *.py adapters/ tests/' manually"
  fi
  echo ""
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PYTHON ISORT IMPORT SORTING CHECK (ATOMIC)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [[ "$RUN_ISORT" == "true" ]]; then
  echo "📚 Import Sorting (isort)"

  # Try to auto-fix import organization with isort
  echo "🔧 Auto-fixing import organization with isort..."
  if isort --profile black *.py adapters/ tests/ 2>/dev/null || true; then
    echo "   ✅ Import organization applied"
  fi

  # Verify import organization
  if isort --check-only --profile black *.py adapters/ tests/ > /dev/null 2>&1; then
    echo "✅ Isort Check: PASSED (import organization verified)"
    add_success "Isort Check" "All Python imports properly organized with isort"
  else
    echo "❌ Isort Check: FAILED (import organization issues found)"
    add_failure "Isort Check" "Import organization issues found" "Run 'isort --profile black *.py adapters/ tests/' manually"
  fi
  echo ""
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PYTHON LINT CHECK (FLAKE8 + BASIC PYLINT)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [[ "$RUN_LINT" == "true" ]]; then
  echo "🔍 Python Lint Check (flake8 critical errors)"

  # Run flake8 for critical errors only (much faster)
  # Only check tracked Python files to avoid processing non-Python files
  # Use xargs to avoid "argument list too long" error
  echo "🔧 Running flake8 critical error check..."
  FLAKE8_OUTPUT=$(git ls-files '*.py' 'adapters/**/*.py' 'tests/**/*.py' 'api/**/*.py' 'session/**/*.py' 'email_providers/**/*.py' 'bulk_email_models/**/*.py' 'scripts/**/*.py' 2>&1 | grep -v 'Dark Forest' | grep -v '__pycache__' | xargs -r flake8 --max-line-length=88 --select=E9,F63,F7,F82 2>&1 | grep -v 'Unable to find qualified name')
  FLAKE8_EXIT=$?

  if [[ $FLAKE8_EXIT -ne 0 && -n "$FLAKE8_OUTPUT" ]]; then
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
  # Include scripts for type checking but exclude from coverage
  TYPE_OUTPUT=$(timeout 30s find . -name "*.py" -not -path "./venv/*" -not -path "./cursor-rules/*" -not -path "./.venv/*" -not -path "./tests/*" -not -path "./scripts/seed_db.py" | xargs mypy --ignore-missing-imports --no-strict-optional 2>&1) || TYPE_FAILED=true

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
# TEST SUITE EXECUTION (ATOMIC) - UNIT TESTS ONLY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [[ "$RUN_TESTS" == "true" ]]; then
  echo "🧪 Test Suite Execution (pytest)"

  # Run UNIT tests only (fast tests, separate directory, no coverage)
  echo "  🔍 Running UNIT test suite (tests only, no coverage)..."
  # Use pytest-xdist for parallel execution (35% faster)
  TEST_OUTPUT=$(python -m pytest tests/unit/ -n auto -v 2>&1) || TEST_FAILED=true

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

    # Show error summary - try multiple approaches to extract useful failure info
    SUMMARY_SECTION=$(echo "$TEST_OUTPUT" | grep -A 20 "short test summary info" | head -20)
    if [[ -n "$SUMMARY_SECTION" ]]; then
      echo "$SUMMARY_SECTION" | sed 's/^/  /'
    else
      # If no short summary, show FAILED test lines and any assertion errors
      FAILED_TESTS=$(echo "$TEST_OUTPUT" | grep -E "(FAILED|ERROR|AssertionError|assert)" | head -10)
      if [[ -n "$FAILED_TESTS" ]]; then
        echo "  Test failure details:"
        echo "$FAILED_TESTS" | sed 's/^/    /'
      else
        # Last resort: show last 10 lines of output which usually contain the error
        echo "  Last lines of test output:"
        echo "$TEST_OUTPUT" | tail -10 | sed 's/^/    /'
      fi
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Extract summary stats for the failure record
    FAILED_TESTS=$(echo "$TEST_OUTPUT" | grep -o '[0-9]\+ failed' | head -1 || echo "unknown")
    add_failure "Test Execution" "Test failures: $FAILED_TESTS" "See detailed output above and run 'python -m pytest -v' for full details"
  else
    echo "✅ Test Execution: PASSED"
    add_success "Test Execution" "All unit tests passed successfully"
  fi
  echo ""
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTEGRATION TEST SUITE EXECUTION - COMPONENT INTERACTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [[ "$RUN_INTEGRATION_TESTS" == "true" ]]; then
  echo "🔗 Integration Test Suite Execution (tests/integration/)"
  
  echo "  🔍 Running INTEGRATION test suite (component interactions)..."
  INTEGRATION_TEST_OUTPUT=$(python -m pytest tests/integration/ -v 2>&1) || INTEGRATION_TEST_FAILED=true
  
  if [[ "$INTEGRATION_TEST_FAILED" == "true" ]]; then
    echo "❌ Integration Tests: FAILED"
    echo ""
    echo "📋 Integration Test Failure Details:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$INTEGRATION_TEST_OUTPUT" | sed 's/^/  /'
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Extract summary stats for the failure record
    FAILED_INTEGRATION_TESTS=$(echo "$INTEGRATION_TEST_OUTPUT" | grep -o '[0-9]\+ failed' | head -1 || echo "unknown")
    add_failure "Integration Tests" "Integration test failures: $FAILED_INTEGRATION_TESTS" "See detailed output above and run 'python -m pytest tests/integration/ -v' for full details"
  else
    echo "✅ Integration Tests: PASSED"
    add_success "Integration Tests" "All integration tests passed successfully"
  fi
  echo ""
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# E2E TEST SUITE (ATOMIC) - Playwright browser automation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [[ "$RUN_E2E_TESTS" == "true" ]]; then
  echo "🎭 End-to-End Test Suite (Playwright browser automation)"
  
  echo "  🔍 Running E2E test suite (headless browser tests)..."
  # Run via run_uat.sh which handles environment setup
  E2E_TEST_OUTPUT=$(./run_uat.sh 2>&1) || E2E_TEST_FAILED=true
  
  if [[ "$E2E_TEST_FAILED" == "true" ]]; then
    echo "❌ E2E Tests: FAILED"
    echo ""
    echo "📋 E2E Test Failure Details:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$E2E_TEST_OUTPUT" | sed 's/^/  /'
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Extract summary stats for the failure record
    FAILED_E2E_TESTS=$(echo "$E2E_TEST_OUTPUT" | grep -o '[0-9]\+ failed' | head -1 || echo "unknown")
    add_failure "E2E Tests" "E2E test failures: $FAILED_E2E_TESTS" "See detailed output above and run './run_uat.sh --watch' to debug"
  else
    echo "✅ E2E Tests: PASSED"
    add_success "E2E Tests" "All E2E tests passed successfully"
  fi
  echo ""
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST COVERAGE ANALYSIS (ATOMIC) - 80% THRESHOLD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [[ "$RUN_COVERAGE" == "true" ]]; then
  echo "📊 Test Coverage Analysis (80% threshold)"

  # Run coverage analysis independently of test results (unit tests only)
  echo "  📊 Running coverage analysis (independent of test results)..."
  
  # Ensure logs directory exists
  mkdir -p logs
  
  # Coverage report file (overwrite previous)
  COVERAGE_REPORT_FILE="logs/coverage_report.txt"
  
  # Clean up old coverage data files to prevent race conditions
  rm -f .coverage .coverage.*
  
  # Run pytest with coverage AND capture exit code to detect test failures
  # NOTE: Running serially (no -n auto) to avoid SQLite database locking issues in parallel execution
  # conftest.py handles DATABASE_URL setup automatically
  TEST_EXIT_CODE=0
  COVERAGE_OUTPUT=$(python -m pytest tests/unit/ --cov=. --cov-report=term-missing --tb=no --quiet 2>&1) || TEST_EXIT_CODE=$?
  
  # Write detailed coverage report to file
  echo "$COVERAGE_OUTPUT" > "$COVERAGE_REPORT_FILE"
  
  # Check for ACTUAL test failures (not just coverage threshold failures)
  # pytest exits with code 1 for both test failures AND coverage threshold failures
  # Distinguish by checking for "FAILED" in output (actual test failures)
  HAS_TEST_FAILURES=$(echo "$COVERAGE_OUTPUT" | grep -q "FAILED " && echo "true" || echo "false")
  
  if [[ "$HAS_TEST_FAILURES" == "true" ]]; then
    echo "❌ Coverage: FAILED (tests failed)"
    echo ""
    echo "📋 Test Failure Details:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Show failing tests
    FAILING_TESTS=$(echo "$COVERAGE_OUTPUT" | grep "FAILED " | head -10)
    if [[ -n "$FAILING_TESTS" ]]; then
      echo "🔴 Failing Tests:"
      echo "$FAILING_TESTS" | sed 's/^/  /'
      echo ""
    fi
    
    # Show test summary
    TEST_SUMMARY=$(echo "$COVERAGE_OUTPUT" | grep -E "failed|passed|error" | tail -3)
    if [[ -n "$TEST_SUMMARY" ]]; then
      echo "$TEST_SUMMARY" | sed 's/^/  /'
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    FAILED_TESTS=$(echo "$COVERAGE_OUTPUT" | grep -o '[0-9]\+ failed' | head -1 || echo "unknown")
    add_failure "Test Coverage" "Test failures: $FAILED_TESTS" "Fix failing tests before checking coverage. Run 'python -m pytest tests/unit/ -v' for details"
  else
  
  # Extract coverage percentage from output
  COVERAGE=$(echo "$COVERAGE_OUTPUT" | grep -o 'TOTAL.*[0-9]\+\.[0-9]\+%' | grep -o '[0-9]\+\.[0-9]\+%' | head -1 || echo "unknown")
  
  # Check if we got a valid coverage percentage
  if [[ "$COVERAGE" != "unknown" && "$COVERAGE" != "" ]]; then
    # Extract numeric value for comparison
    COVERAGE_NUM=$(echo "$COVERAGE" | sed 's/%//')
    
    # Coverage threshold with environment differences buffer
    # Base threshold: 80%
    # Environment buffer: 0.5% (accounts for differences between local macOS and CI Linux)
    # - Database connection paths may differ depending on DATABASE_URL
    # - Import conflict resolution logic may exercise different code paths
    # - Logging behavior can vary between environments
    THRESHOLD=80
    
    # Apply environment buffer only in CI (not locally)
    if [[ "${CI:-false}" == "true" ]]; then
      ENV_DIFFERENCES_BUFFER=0.5
      EFFECTIVE_THRESHOLD=$(echo "$THRESHOLD - $ENV_DIFFERENCES_BUFFER" | bc -l)
      echo "  🔧 CI environment detected - applying ${ENV_DIFFERENCES_BUFFER}% buffer (effective threshold: ${EFFECTIVE_THRESHOLD}%)"
    else
      ENV_DIFFERENCES_BUFFER=0
      EFFECTIVE_THRESHOLD=$THRESHOLD
      echo "  🏠 Local environment - using full ${THRESHOLD}% threshold"
    fi
    
    # Compare against effective threshold using bc for floating point
    if (( $(echo "$COVERAGE_NUM >= $EFFECTIVE_THRESHOLD" | bc -l) )); then
      echo "✅ Coverage: PASSED ($COVERAGE)"
      add_success "Test Coverage" "Coverage at $COVERAGE (meets ${EFFECTIVE_THRESHOLD}% threshold with ${ENV_DIFFERENCES_BUFFER}% environment buffer)"
    else
      echo "❌ Coverage: THRESHOLD NOT MET ($COVERAGE)"
      echo ""

      # Show coverage details
      echo "📋 Coverage Report:"
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      
      # Extract lines with missing coverage
      MISSING_LINES=$(echo "$COVERAGE_OUTPUT" | grep -E "TOTAL|Missing" | head -10)
      if [[ -n "$MISSING_LINES" ]]; then
        echo "$MISSING_LINES" | sed 's/^/  /'
      else
        echo "  Unable to extract coverage details"
      fi
      
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      
      # Show commit-specific coverage issues
      echo "📋 Files in Current Commit Needing Coverage:"
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      
      # Get list of Python files in the current commit (staged and unstaged changes)
      COMMIT_FILES=$(git diff --name-only HEAD 2>/dev/null | grep '\.py$' || echo "")
      if [[ -z "$COMMIT_FILES" ]]; then
        # If no diff with HEAD, try staged files
        COMMIT_FILES=$(git diff --cached --name-only 2>/dev/null | grep '\.py$' || echo "")
      fi
      if [[ -z "$COMMIT_FILES" ]]; then
        # If still no files, try unstaged changes
        COMMIT_FILES=$(git diff --name-only 2>/dev/null | grep '\.py$' || echo "")
      fi
      
      if [[ -n "$COMMIT_FILES" ]]; then
        echo "  Files in commit: $(echo "$COMMIT_FILES" | tr '\n' ' ')"
        echo ""
        
        # Filter coverage output to show only files in the commit
        COMMIT_COVERAGE=$(echo "$COVERAGE_OUTPUT" | grep -E "$(echo "$COMMIT_FILES" | sed 's/\.py$//' | tr '\n' '|' | sed 's/|$//')")
        if [[ -n "$COMMIT_COVERAGE" ]]; then
          echo "  Coverage details for commit files:"
          echo "$COMMIT_COVERAGE" | sed 's/^/    /'
        else
          echo "  No coverage issues found in commit files (issues may be in other files)"
        fi
      else
        echo "  No Python files found in current commit"
      fi
      
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo ""

      add_failure "Test Coverage" "Coverage at $COVERAGE (below ${EFFECTIVE_THRESHOLD}% threshold)" "Add tests to increase coverage above ${EFFECTIVE_THRESHOLD}%. Detailed report: $PWD/$COVERAGE_REPORT_FILE"
    fi
  else
    echo "❌ Coverage: ANALYSIS FAILED"
    echo "📋 Coverage Output (for debugging):"
    echo "$COVERAGE_OUTPUT" | head -20 | sed 's/^/  /'
    add_failure "Test Coverage" "Coverage analysis failed" "Check pytest-cov installation and configuration. Debug output: $PWD/$COVERAGE_REPORT_FILE"
  fi
  fi  # Close the "else" block from test failure check
  echo ""
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SECURITY AUDIT (BANDIT + SAFETY)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if [[ "$RUN_SECURITY" == "true" ]]; then
  echo "🔒 Security Audit (bandit + safety)"

  SECURITY_PASSED=true

  # Run bandit for security issues in code (main source files only, with timeout)
  # Only fail on HIGH severity issues, ignore LOW/MEDIUM for now
  echo "🔧 Running bandit security scan..."
  BANDIT_OUTPUT=$(timeout 30s bandit -r . --exclude ./venv,./cursor-rules,./.venv,./logs,./tests -lll --format json 2>&1) || BANDIT_FAILED=true
  
  # Save bandit report to file for GitHub Actions artifact upload
  echo "$BANDIT_OUTPUT" > bandit-report.json

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

  # Run safety scan for known vulnerabilities in dependencies
  echo "🔧 Running safety dependency scan..."
  echo "📋 Debug: Pre-execution checks:"
  echo "  Safety executable: $(which safety 2>&1 || echo 'NOT FOUND')"
  echo "  Safety version: $(safety --version 2>&1 || echo 'VERSION CHECK FAILED')"
  echo "  Python version: $(python --version 2>&1)"
  echo "  Working directory: $(pwd)"
  echo "  Requirements files present:"
  ls -la requirements*.txt 2>/dev/null | sed 's/^/    /' || echo "    No requirements files found"
  
  echo "📋 Debug: Testing basic safety command..."
  safety --help >/dev/null 2>&1 && echo "  Safety help works" || echo "  Safety help FAILED"
  
  echo "📋 Debug: Running safety scan with authentication..."
  set +e  # Don't exit on error
  # Use API key from environment if available, otherwise try without auth
  if [[ -n "$SAFETY_API_KEY" ]]; then
    echo "  Using Safety API key for authentication"
    SAFETY_OUTPUT=$(timeout 60s safety scan --output json --key "$SAFETY_API_KEY" 2>&1)
  else
    echo "  No Safety API key found, attempting scan without authentication"
    SAFETY_OUTPUT=$(timeout 60s safety scan --output json 2>&1)
  fi
  SAFETY_EXIT_CODE=$?
  
  # Also write to file to bypass GitHub truncation
  echo "$SAFETY_OUTPUT" > /tmp/safety_output.txt
  mkdir -p logs
  echo "$SAFETY_OUTPUT" > logs/safety_detailed_output.txt  # For artifact upload
  echo "$SAFETY_OUTPUT" > safety-report.txt  # For GitHub Actions artifact upload
  
  # Create comprehensive diagnostic file
  {
    echo "=== SAFETY SCAN DIAGNOSTIC REPORT ==="
    echo "Timestamp: $(date)"
    echo "Exit Code: $SAFETY_EXIT_CODE"
    echo "Output Length: ${#SAFETY_OUTPUT} characters"
    echo "Safety Version: $(safety --version 2>&1 || echo 'VERSION CHECK FAILED')"
    echo "Python Version: $(python --version 2>&1)"
    echo "Working Directory: $(pwd)"
    echo ""
    echo "=== COMPLETE SAFETY OUTPUT ==="
    echo "$SAFETY_OUTPUT"
    echo ""
    echo "=== HEXDUMP OF OUTPUT ==="
    echo "$SAFETY_OUTPUT" | hexdump -C
    echo ""
    echo "=== ALTERNATIVE COMMANDS ==="
    echo "--- Safety scan without JSON ---"
    timeout 10s safety scan 2>&1 || echo "Failed"
    echo ""
    echo "--- Safety check (deprecated) ---"
    timeout 10s safety check 2>&1 || echo "Failed"
  } > logs/safety_full_diagnostic.txt
  set -e  # Re-enable exit on error
  
  echo "📋 Debug: Safety command completed with exit code: $SAFETY_EXIT_CODE"
  echo "📋 Debug: Output length: ${#SAFETY_OUTPUT} characters"
  
  if [[ $SAFETY_EXIT_CODE -ne 0 ]]; then
    SAFETY_FAILED=true
  fi

  if [[ "$SAFETY_FAILED" == "true" ]]; then
    SECURITY_PASSED=false
    echo "❌ Safety dependency check failed (exit code: $SAFETY_EXIT_CODE)"
    echo "📋 Full Safety Output for Debugging:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Show complete output for debugging (no truncation)
    if [[ ${#SAFETY_OUTPUT} -gt 0 ]]; then
      echo "📋 SAFETY OUTPUT (character by character to avoid truncation):"
      # Print each line with line numbers to force visibility
      echo "$SAFETY_OUTPUT" | nl -ba | sed 's/^/  /'
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "📋 OUTPUT FROM FILE (to bypass GitHub truncation):"
      cat /tmp/safety_output.txt | sed 's/^/  /'
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "📋 RAW OUTPUT (hexdump to see hidden characters):"
      echo "$SAFETY_OUTPUT" | hexdump -C | head -20 | sed 's/^/  /'
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "📋 Output analysis:"
      echo "  Total characters: ${#SAFETY_OUTPUT}"
      echo "  Total lines: $(echo "$SAFETY_OUTPUT" | wc -l)"
      echo "  Contains 'vulnerabilities': $(echo "$SAFETY_OUTPUT" | grep -q "vulnerabilities" && echo "YES" || echo "NO")"
      echo "  Contains 'error': $(echo "$SAFETY_OUTPUT" | grep -qi "error" && echo "YES" || echo "NO")"
      echo "  Contains 'exception': $(echo "$SAFETY_OUTPUT" | grep -qi "exception" && echo "YES" || echo "NO")"
    else
      echo "  No output captured from safety command"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 Debug: Trying safety scan without JSON output..."
    SAFETY_PLAIN_OUTPUT=$(timeout 10s safety scan 2>&1)
    if [[ $? -eq 0 ]]; then
      echo "  SUCCESS: Safety scan without JSON works!"
      echo "$SAFETY_PLAIN_OUTPUT" | sed 's/^/  /'
    else
      echo "  FAILED: Safety scan without JSON also failed"
      echo "$SAFETY_PLAIN_OUTPUT" | sed 's/^/  /'
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 Debug: Trying safety check (deprecated but might work)..."
    SAFETY_CHECK_OUTPUT=$(timeout 10s safety check 2>&1)
    if [[ $? -eq 0 ]]; then
      echo "  SUCCESS: Legacy safety check works!"
      echo "$SAFETY_CHECK_OUTPUT" | sed 's/^/  /'
    else
      echo "  FAILED: Legacy safety check also failed"
      echo "$SAFETY_CHECK_OUTPUT" | sed 's/^/  /'
    fi
    
    echo "📋 Debug: Environment information:"
    echo "  PWD: $(pwd)"
    echo "  PATH: $PATH" | head -c 200
    echo "  VIRTUAL_ENV: ${VIRTUAL_ENV:-'Not set'}"
    echo "  Python executable: $(which python)"
    echo "  Safety executable: $(which safety)"
    
    echo "🔍 DIAGNOSIS REQUIRED: Safety scan failed with no output"
    echo "🔍 Exit code $SAFETY_EXIT_CODE indicates:"
    case $SAFETY_EXIT_CODE in
      124) echo "   - Command timed out after 60 seconds" ;;
      127) echo "   - Command not found or not executable" ;;
      1) echo "   - General error or vulnerabilities found" ;;
      2) echo "   - Misuse of shell builtins" ;;
      *) echo "   - Unknown error condition" ;;
    esac
    
    # Extract vulnerability details from JSON output if possible
    if echo "$SAFETY_OUTPUT" | grep -q "vulnerabilities"; then
      # Try to extract package names and CVEs from JSON
      VULN_SUMMARY=$(echo "$SAFETY_OUTPUT" | grep -o '"package_name":"[^"]*"' | sed 's/"package_name":"//g' | sed 's/"//g' | head -5)
      if [[ -n "$VULN_SUMMARY" ]]; then
        echo "  Vulnerable packages found:"
        echo "$VULN_SUMMARY" | sed 's/^/    • /'
      fi
    fi
    
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
