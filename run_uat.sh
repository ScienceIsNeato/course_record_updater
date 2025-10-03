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
SLOWMO=""
VIDEO="off"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --watch|-w)
            MODE="headed"
            SLOWMO="--slowmo=500"
            shift
            ;;
        --headed|-h)
            MODE="headed"
            shift
            ;;
        --test|-t)
            TEST_FILTER="$2"
            shift 2
            ;;
        --video|-v)
            VIDEO="on"
            shift
            ;;
        --help)
            echo "UAT Runner - Automated E2E Testing"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --watch, -w          Run with visible browser (watch mode)"
            echo "  --headed, -h         Run with visible browser"
            echo "  --test, -t <name>    Run specific test (e.g., TC-IE-001)"
            echo "  --video, -v          Record video of test execution"
            echo "  --help               Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                   # Run all tests (headless)"
            echo "  $0 --watch           # Watch tests run in browser"
            echo "  $0 --test TC-IE-001  # Run specific test case"
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

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not active, activating...${NC}"
    source venv/bin/activate
fi

# Restart server to ensure fresh database with test credentials
echo -e "${BLUE}🔄 Restarting server for fresh test environment...${NC}"

# Clear existing database to ensure fresh state
rm -f course_records.db course_records.db-* 2>/dev/null || true

# Seed database BEFORE starting server (so server loads pre-populated DB)
echo -e "${YELLOW}🌱 Seeding database with test data...${NC}"
python scripts/seed_db.py
echo ""

# Use restart_server.sh to handle server restart (blocks until server is ready)
echo -e "${YELLOW}🚀 Starting server...${NC}"
if ! ./restart_server.sh; then
    echo -e "${RED}❌ Server failed to start${NC}"
    echo -e "${YELLOW}Check logs/server.log for details${NC}"
    exit 1
fi
echo ""

# Build pytest command
PYTEST_CMD="pytest tests/e2e/"

# Add test filter if specified
if [ -n "$TEST_FILTER" ]; then
    PYTEST_CMD="$PYTEST_CMD -k $TEST_FILTER"
fi

# Add mode flags
if [ "$MODE" = "headed" ]; then
    PYTEST_CMD="$PYTEST_CMD --headed"
    if [ -n "$SLOWMO" ]; then
        PYTEST_CMD="$PYTEST_CMD $SLOWMO"
    fi
fi

# Add video recording if requested
if [ "$VIDEO" = "on" ]; then
    PYTEST_CMD="$PYTEST_CMD --video=on"
fi

# Add verbose output
PYTEST_CMD="$PYTEST_CMD -v"

# Display test configuration
echo -e "${BLUE}📋 Test Configuration:${NC}"
echo -e "  Mode: ${GREEN}$MODE${NC}"
if [ -n "$TEST_FILTER" ]; then
    echo -e "  Filter: ${GREEN}$TEST_FILTER${NC}"
else
    echo -e "  Filter: ${GREEN}All E2E tests${NC}"
fi
echo -e "  Video: ${GREEN}$VIDEO${NC}"
echo ""

# Run tests
echo -e "${BLUE}🚀 Starting E2E tests...${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🧹 Cleaning up test server...${NC}"
    # Stop any running Flask servers
    pkill -f "python app.py" 2>/dev/null || true
    pkill -f "flask run" 2>/dev/null || true
    sleep 1
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
    echo -e "  Screenshots: ${GREEN}test-results/screenshots/${NC}"
    echo -e "  Videos: ${GREEN}test-results/videos/${NC}"
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
    echo -e "${YELLOW}🎥 Check videos in test-results/videos/${NC}"
    echo -e "${YELLOW}📋 Server logs: ${GREEN}logs/test_server.log${NC}"
    echo ""
    echo -e "${YELLOW}Tip: Run with --watch to see failures in real-time:${NC}"
    echo -e "  $0 --watch"
    echo ""
    
    exit $EXIT_CODE
fi

