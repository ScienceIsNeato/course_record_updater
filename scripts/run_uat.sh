#!/bin/bash
#
# UAT Runner Script - Run Automated E2E Tests
#
# This script runs the automated User Acceptance Testing (UAT) suite
# that validates import/export functionality end-to-end.
#
# Usage:
#   ./run_uat.sh           # Run all E2E tests (headless mode)
#   ./run_uat.sh --watch   # Run with visible browser (watch mode)
#   ./run_uat.sh --test TC-IE-001  # Run specific test case
#   ./run_uat.sh --help    # Show usage

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Constants
readonly MODE_HEADED="headed"
readonly MODE_HEADLESS="headless"

# Default values
MODE="$MODE_HEADLESS"
TEST_FILTER=""
SAVE_VIDEOS="0"
DEBUG_MODE="0"
PARALLEL_WORKERS="auto"  # Always run in parallel, auto-scale to CPU cores

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --watch|-w)
            MODE="$MODE_HEADED"
            shift
            ;;
        --headed|-h)
            MODE="$MODE_HEADED"
            shift
            ;;
        --debug|-d)
            MODE="$MODE_HEADED"
            DEBUG_MODE="1"
            shift
            ;;
        --test|-t)
            TEST_FILTER="$2"
            shift 2
            ;;
        --save-videos)
            SAVE_VIDEOS="1"
            shift
            ;;
        --help)
            echo "UAT Runner - Automated E2E Testing"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --watch, -w          Run with visible browser (slow-mo 350ms for visibility)"
            echo "  --headed, -h         Same as --watch (visible browser, slow-mo 350ms)"
            echo "  --debug, -d          Debug mode: visible browser + pause at each step + DevTools"
            echo "  --test, -t <name>    Run specific test (e.g., TC-IE-001)"
            echo "  --save-videos        Record video of test execution for debugging"
            echo "  --help               Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                       # Run all tests (parallel auto-scaling, headless)"
            echo "  $0 --watch               # Watch tests run (parallel, visible, slow-mo)"
            echo "  $0 --debug               # Debug mode (parallel, visible, 1s steps, DevTools)"
            echo "  $0 --test TC-IE-001      # Run specific test case (serial, clearer output)"
            echo "  $0 --save-videos         # Record videos for debugging"
            echo ""
            echo "Note: Smart execution mode based on test count:"
            echo "      - Full test suite: parallel with auto-scaling to all CPU cores (~3x speedup)"
            echo "      - Filtered tests: serial execution (1 worker, clearer output)"
            echo ""
            echo "Modes Explained:"
            echo "  Headless (default)   -> CI/fast execution, no browser window"
            echo "  Watch (--watch)      -> Human-friendly: browser visible, 350ms slow-mo"
            echo "  Debug (--debug)      -> Stepwise: browser visible, 1s slow-mo, DevTools open"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Smart worker allocation: disable parallel for filtered tests
# When running a specific test filter, serial execution is clearer and faster
if [[ -n "$TEST_FILTER" ]]; then
    # For single/filtered tests: disable parallel execution
    # This makes output clearer and is faster for small test counts
    PARALLEL_WORKERS=""
fi

# Header
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Course Record Updater - UAT Runner${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if virtual environment is activated (skip in CI where it's already set up)
if [[ -z "$VIRTUAL_ENV" ]] && [[ "${CI:-false}" != "true" ]]; then
    echo -e "${YELLOW}⚠️  Virtual environment not active, activating...${NC}"
    if [[ -f "venv/bin/activate" ]]; then
        source venv/bin/activate
    else
        echo -e "${RED}❌ Virtual environment not found at venv/bin/activate${NC}"
        echo -e "${YELLOW}💡 Run: python -m venv venv && source venv/bin/activate && pip install -r requirements-dev.txt${NC}"
        exit 1
    fi
elif [[ "${CI:-false}" = "true" ]]; then
    echo -e "${BLUE}🔵 CI environment detected, using pre-configured Python environment${NC}"
fi

# Load environment variables from .envrc (skip in CI if credentials already set)
if [[ -f ".envrc" ]]; then
    source .envrc
elif [[ -f ".envrc.template" ]] && [[ -z "$ETHEREAL_USER" ]]; then
    # Only source template if Ethereal credentials not already set (i.e., not in CI with secrets)
    source .envrc.template
elif [[ "${CI:-false}" = "true" ]]; then
    echo -e "${BLUE}🔵 CI detected with credentials already set, skipping .envrc.template${NC}"
fi

# Set ENV to "test" so email factory automatically selects Ethereal
export ENV="test"

# Disable CSRF for E2E tests to avoid token validation issues
# E2E tests focus on functional workflows, not CSRF security
export WTF_CSRF_ENABLED="false"

# Set EMAIL_WHITELIST for E2E tests
# Allow test domains used by E2E test suite
export EMAIL_WHITELIST="*@ethereal.email,*@mocku.test,*@test.edu,*@test.com,*@test.local,*@example.com,*@loopclosertests.mailtrap.io"

# Unset EMAIL_PROVIDER so factory uses ENV-based selection (ENV=test -> ethereal)
# This overrides any EMAIL_PROVIDER=brevo from .envrc.template
unset EMAIL_PROVIDER

# Restart server to ensure fresh database with test credentials
echo -e "${BLUE}🔄 Restarting server for fresh E2E test environment...${NC}"

# Clear E2E database to ensure fresh state (restart_server.sh will select correct DB)
E2E_DB="${DATABASE_URL_E2E:-sqlite:///course_records_e2e.db}"
E2E_DB_FILE="${E2E_DB#sqlite:///}"
echo -e "${BLUE}🗑️  Clearing E2E database: $E2E_DB_FILE${NC}"
rm -f "$E2E_DB_FILE" "${E2E_DB_FILE}-"* 2>/dev/null || true

# Export DATABASE_URL so seed scripts use the E2E database
export DATABASE_URL="$E2E_DB"
export DATABASE_TYPE="sqlite"

# Seed E2E database with baseline shared infrastructure
echo -e "${YELLOW}🌱 Seeding E2E database with baseline data...${NC}"
python scripts/seed_db.py --env e2e --manifest tests/fixtures/e2e_seed_manifest.json
echo ""
echo -e "${BLUE}ℹ️  Tests will create their own users/sections programmatically via API${NC}"
echo ""

# Start server in E2E mode (restart_server.sh determines port from LOOPCLOSER_DEFAULT_PORT_E2E)
E2E_PORT="${LOOPCLOSER_DEFAULT_PORT_E2E:-3002}"
echo -e "${YELLOW}🚀 Starting E2E server on port $E2E_PORT...${NC}"
if ! ./scripts/restart_server.sh e2e; then
    echo -e "${RED}❌ E2E server failed to start${NC}"
    echo -e "${YELLOW}Check logs/test_server.log for details${NC}"
    exit 1
fi
echo ""

# Set video recording flag
export SAVE_VIDEOS="${SAVE_VIDEOS}"

# Set debug/headless flags for Playwright
if [[ "$DEBUG_MODE" = "1" ]]; then
    export PYTEST_DEBUG="1"
    export HEADLESS="0"
else
    if [[ "$MODE" = "$MODE_HEADED" ]]; then
        export HEADLESS="0"
    else
        # Enforce true headless when not in watch/debug
        export HEADLESS="1"
    fi
fi

# Set DATABASE_URL for pytest so it doesn't create a temp database
export DATABASE_URL="${DATABASE_URL_E2E:-sqlite:///course_records_e2e.db}"

# Build pytest command
PYTEST_CMD="pytest tests/e2e/"

# Add parallel execution if specified
if [[ -n "$PARALLEL_WORKERS" ]]; then
    PYTEST_CMD="$PYTEST_CMD -n $PARALLEL_WORKERS"
fi

# Add test filter if specified
if [[ -n "$TEST_FILTER" ]]; then
    PYTEST_CMD="$PYTEST_CMD -k $TEST_FILTER"
fi

# Add mode flags
if [[ "$MODE" = "$MODE_HEADED" ]]; then
    PYTEST_CMD="$PYTEST_CMD --headed"
fi

# Add verbose output with progress indicator
PYTEST_CMD="$PYTEST_CMD -v --tb=short"

# Add live output for parallel execution (shows test names as they complete)
if [[ -n "$PARALLEL_WORKERS" ]] || echo "$PYTEST_CMD" | grep -q "\-n"; then
    # For parallel: show which tests are running
    PYTEST_CMD="$PYTEST_CMD --dist=loadscope"
fi

# Display test configuration
echo -e "${BLUE}📋 Test Configuration:${NC}"
if [[ "$DEBUG_MODE" = "1" ]]; then
    echo -e "  Mode: ${GREEN}Debug (visible, 1s slow-mo, DevTools)${NC}"
elif [[ "$MODE" = "$MODE_HEADED" ]]; then
    echo -e "  Mode: ${GREEN}Watch (visible, 350ms slow-mo)${NC}"
else
    echo -e "  Mode: ${GREEN}Headless (fast, no browser window)${NC}"
fi
if [[ -z "$PARALLEL_WORKERS" ]]; then
    echo -e "  Execution: ${GREEN}Serial (single worker, clearer output)${NC}"
elif [[ "$PARALLEL_WORKERS" = "auto" ]]; then
    echo -e "  Execution: ${GREEN}Parallel (auto-scaling to all CPU cores)${NC}"
else
    echo -e "  Execution: ${GREEN}Parallel (max $PARALLEL_WORKERS workers)${NC}"
fi
if [[ -n "$TEST_FILTER" ]]; then
    echo -e "  Filter: ${GREEN}$TEST_FILTER${NC}"
else
    echo -e "  Filter: ${GREEN}All E2E tests${NC}"
fi
if [[ "$SAVE_VIDEOS" = "1" ]]; then
    echo -e "  Video Recording: ${GREEN}enabled${NC}"
else
    echo -e "  Video Recording: ${GREEN}disabled${NC}"
fi
echo ""

# Run tests
echo -e "${BLUE}🚀 Starting E2E tests...${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🧹 Cleaning up E2E test server...${NC}"
    
    # Kill server on E2E port (from LOOPCLOSER_DEFAULT_PORT_E2E env var)
    local e2e_port="${LOOPCLOSER_DEFAULT_PORT_E2E:-3002}"
    local pids
    pids=$(lsof -ti:$e2e_port 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        for pid in $pids; do
            echo -e "${BLUE}  Stopping E2E server (PID: $pid)${NC}"
            kill $pid 2>/dev/null || kill -9 $pid 2>/dev/null || true
        done
        sleep 1
    fi
    
    echo -e "${GREEN}✅ Cleanup complete${NC}"
    return 0
}

# Register cleanup on script exit
trap cleanup EXIT

if $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  ✅ All UAT tests passed!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    
    # Show results location
    echo -e "${BLUE}📊 Test Results:${NC}"
    if [[ "$SAVE_VIDEOS" = "1" ]]; then
        echo -e "  Videos: ${GREEN}test-results/videos/${NC}"
    fi
    echo ""
    
    exit 0
else
    EXIT_CODE=$?
    echo ""
    echo -e "${RED}============================================${NC}"
    echo -e "${RED}  ❌ UAT tests failed${NC}"
    echo -e "${RED}============================================${NC}"
    echo ""
    
    # Show failure diagnostics with prominent paths
    echo -e "${CYAN}📁 DEBUG ARTIFACTS:${NC}"
    echo -e "   ${GREEN}Server logs:${NC}     logs/test_server.log"
    echo -e "   ${GREEN}Screenshots:${NC}     test-results/screenshots/"
    echo -e "   ${GREEN}Test output:${NC}     test-results/"
    if [[ "$SAVE_VIDEOS" = "1" ]]; then
        echo -e "   ${GREEN}Videos:${NC}          test-results/videos/"
    fi
    echo ""
    
    # Show helpful commands
    echo -e "${CYAN}🔍 HELPFUL COMMANDS:${NC}"
    echo -e "   ${GREEN}View server log:${NC}  tail -100 logs/test_server.log"
    echo -e "   ${GREEN}List screenshots:${NC} ls -lh test-results/screenshots/"
    echo -e "   ${GREEN}Watch mode:${NC}       $0 --watch"
    if [[ "$SAVE_VIDEOS" != "1" ]]; then
        echo -e "   ${GREEN}Record videos:${NC}    $0 --save-videos"
    fi
    echo ""
    
    exit $EXIT_CODE
fi

