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

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Default values
MODE="headless"
TEST_FILTER=""
SAVE_VIDEOS="0"
DEBUG_MODE="0"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --watch|-w)
            MODE="headed"
            shift
            ;;
        --headed|-h)
            MODE="headed"
            shift
            ;;
        --debug|-d)
            MODE="headed"
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
            echo "  $0                       # Run all tests (headless, fast)"
            echo "  $0 --watch               # Watch tests run (visible, slow-mo 350ms)"
            echo "  $0 --debug               # Debug mode (visible, 1s steps, DevTools)"
            echo "  $0 --test TC-IE-001      # Run specific test case"
            echo "  $0 --save-videos         # Record videos for debugging"
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

# Header
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Course Record Updater - UAT Runner${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if virtual environment is activated (skip in CI where it's already set up)
if [ -z "$VIRTUAL_ENV" ] && [ "${CI:-false}" != "true" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not active, activating...${NC}"
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        echo -e "${RED}❌ Virtual environment not found at venv/bin/activate${NC}"
        echo -e "${YELLOW}💡 Run: python -m venv venv && source venv/bin/activate && pip install -r requirements-dev.txt${NC}"
        exit 1
    fi
elif [ "${CI:-false}" = "true" ]; then
    echo -e "${BLUE}🔵 CI environment detected, using pre-configured Python environment${NC}"
fi

# Restart server to ensure fresh database with test credentials
echo -e "${BLUE}🔄 Restarting server for fresh E2E test environment...${NC}"

# Clear E2E database to ensure fresh state
rm -f course_records_e2e.db course_records_e2e.db-* 2>/dev/null || true

# Set E2E environment for database seeding
export APP_ENV="e2e"
if [ -f ".envrc" ]; then
    source .envrc
elif [ -f ".envrc.template" ]; then
    source .envrc.template
fi

# Seed E2E database with test data
echo -e "${YELLOW}🌱 Seeding E2E database with test data...${NC}"
python scripts/seed_db.py
echo ""

# Get E2E port from constants.py (hardcoded, not env var)
E2E_PORT=$(python3 -c "from constants import E2E_TEST_PORT; print(E2E_TEST_PORT)")

# Start server in E2E mode (explicit environment argument)
echo -e "${YELLOW}🚀 Starting E2E server on port $E2E_PORT...${NC}"
if ! PORT=$E2E_PORT ./restart_server.sh e2e; then
    echo -e "${RED}❌ E2E server failed to start${NC}"
    echo -e "${YELLOW}Check logs/server.log for details${NC}"
    exit 1
fi
echo ""

# Set video recording flag
export SAVE_VIDEOS="${SAVE_VIDEOS}"

# Set debug/headless flags for Playwright
if [ "$DEBUG_MODE" = "1" ]; then
    export PYTEST_DEBUG="1"
    export HEADLESS="0"
else
    if [ "$MODE" = "headed" ]; then
        export HEADLESS="0"
    else
        # Enforce true headless when not in watch/debug
        export HEADLESS="1"
    fi
fi

# Build pytest command
PYTEST_CMD="pytest tests/e2e/"

# Add test filter if specified
if [ -n "$TEST_FILTER" ]; then
    PYTEST_CMD="$PYTEST_CMD -k $TEST_FILTER"
fi

# Add mode flags
if [ "$MODE" = "headed" ]; then
    PYTEST_CMD="$PYTEST_CMD --headed"
fi

# Add verbose output
PYTEST_CMD="$PYTEST_CMD -v"

# Display test configuration
echo -e "${BLUE}📋 Test Configuration:${NC}"
if [ "$DEBUG_MODE" = "1" ]; then
    echo -e "  Mode: ${GREEN}Debug (visible, 1s slow-mo, DevTools)${NC}"
elif [ "$MODE" = "headed" ]; then
    echo -e "  Mode: ${GREEN}Watch (visible, 350ms slow-mo)${NC}"
else
    echo -e "  Mode: ${GREEN}Headless (fast, no browser window)${NC}"
fi
if [ -n "$TEST_FILTER" ]; then
    echo -e "  Filter: ${GREEN}$TEST_FILTER${NC}"
else
    echo -e "  Filter: ${GREEN}All E2E tests${NC}"
fi
if [ "$SAVE_VIDEOS" = "1" ]; then
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
    
    # Kill server on E2E port (from constants.py) specifically
    local E2E_PORT=$(python3 -c "from constants import E2E_TEST_PORT; print(E2E_TEST_PORT)" 2>/dev/null || echo "3002")
    local PIDS=$(lsof -ti:$E2E_PORT 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        for PID in $PIDS; do
            echo -e "${BLUE}  Stopping E2E server (PID: $PID)${NC}"
            kill $PID 2>/dev/null || kill -9 $PID 2>/dev/null || true
        done
        sleep 1
    fi
    
    echo -e "${GREEN}✅ Cleanup complete${NC}"
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
    if [ "$SAVE_VIDEOS" = "1" ]; then
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
    
    # Show failure diagnostics
    echo -e "${YELLOW}📸 Check screenshots in test-results/screenshots/${NC}"
    if [ "$SAVE_VIDEOS" = "1" ]; then
        echo -e "${YELLOW}🎥 Check videos in test-results/videos/${NC}"
    fi
    echo -e "${YELLOW}📋 Server logs: ${GREEN}logs/test_server.log${NC}"
    echo ""
    echo -e "${YELLOW}Tip: Run with --watch to see failures in real-time:${NC}"
    echo -e "  $0 --watch"
    echo -e "${YELLOW}     Or with --save-videos to record execution for debugging:${NC}"
    echo -e "  $0 --save-videos"
    echo ""
    
    exit $EXIT_CODE
fi

