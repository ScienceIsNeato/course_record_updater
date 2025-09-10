#!/bin/bash

# run_smoke_tests.sh - Automated smoke testing for frontend functionality
# This script starts the server, runs smoke tests, and reports results

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
TEST_PORT=3002  # Use a different port for testing to avoid conflicts
TEST_URL="http://localhost:$TEST_PORT"
CHROME_DRIVER_TIMEOUT=30

echo -e "${BLUE}🧪 Course Record Updater - Automated Smoke Tests${NC}"
echo -e "${BLUE}================================================${NC}"

# Function to check if Chrome/Chromium is available
check_chrome() {
    if command -v google-chrome >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Chrome found${NC}"
        return 0
    elif command -v chromium-browser >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Chromium found${NC}"
        return 0
    elif command -v chromium >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Chromium found${NC}"
        return 0
    else
        echo -e "${RED}❌ Chrome/Chromium not found. Please install Chrome or Chromium for frontend tests${NC}"
        echo -e "${YELLOW}💡 On macOS: brew install --cask google-chrome${NC}"
        echo -e "${YELLOW}💡 On Ubuntu: sudo apt-get install chromium-browser${NC}"
        return 1
    fi
}

# Function to check if ChromeDriver is available
check_chromedriver() {
    if command -v chromedriver >/dev/null 2>&1; then
        echo -e "${GREEN}✅ ChromeDriver found${NC}"
        return 0
    else
        echo -e "${RED}❌ ChromeDriver not found${NC}"
        echo -e "${YELLOW}💡 Install ChromeDriver: pip install chromedriver-autoinstaller${NC}"
        echo -e "${YELLOW}💡 Or download from: https://chromedriver.chromium.org/${NC}"
        return 1
    fi
}

# Function to start test server
start_test_server() {
    echo -e "${BLUE}🚀 Starting test server on port $TEST_PORT...${NC}"
    
    # Load environment variables
    if [ -f ".envrc" ]; then
        source .envrc
    fi
    
    # Activate virtual environment if it exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Start server on test port in background
    PORT=$TEST_PORT python app.py > logs/test_server.log 2>&1 &
    SERVER_PID=$!
    
    # Wait for server to start
    echo -e "${BLUE}⏳ Waiting for server to start...${NC}"
    for i in {1..30}; do
        if curl -s "$TEST_URL" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Test server started successfully${NC}"
            return 0
        fi
        sleep 1
    done
    
    echo -e "${RED}❌ Test server failed to start${NC}"
    kill $SERVER_PID 2>/dev/null || true
    return 1
}

# Function to stop test server
stop_test_server() {
    if [ ! -z "$SERVER_PID" ]; then
        echo -e "${BLUE}🛑 Stopping test server...${NC}"
        kill $SERVER_PID 2>/dev/null || true
        
        # Wait for process to terminate
        for i in {1..10}; do
            if ! kill -0 $SERVER_PID 2>/dev/null; then
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        kill -9 $SERVER_PID 2>/dev/null || true
        echo -e "${GREEN}✅ Test server stopped${NC}"
    fi
}

# Function to run smoke tests
run_tests() {
    echo -e "${BLUE}🧪 Running smoke tests...${NC}"
    
    # Install test dependencies if needed
    pip install -q pytest selenium requests chromedriver-autoinstaller 2>/dev/null || true
    
    # Auto-install ChromeDriver if needed
    python -c "
try:
    import chromedriver_autoinstaller
    chromedriver_autoinstaller.install()
    print('✅ ChromeDriver auto-installed')
except ImportError:
    print('⚠️ chromedriver-autoinstaller not available')
" 2>/dev/null || true
    
    # Run the tests
    pytest tests/test_frontend_smoke.py -v --tb=short
    TEST_EXIT_CODE=$?
    
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✅ All smoke tests passed!${NC}"
    else
        echo -e "${RED}❌ Some smoke tests failed${NC}"
    fi
    
    return $TEST_EXIT_CODE
}

# Cleanup function
cleanup() {
    echo -e "${BLUE}🧹 Cleaning up...${NC}"
    stop_test_server
}

# Set trap for cleanup
trap cleanup EXIT

# Main execution
main() {
    # Create logs directory
    mkdir -p logs
    
    # Check prerequisites
    echo -e "${BLUE}🔍 Checking prerequisites...${NC}"
    
    if ! check_chrome; then
        exit 1
    fi
    
    # Start Firestore emulator if not running
    if ! lsof -i :8086 > /dev/null 2>&1; then
        echo -e "${BLUE}🚀 Starting Firestore emulator...${NC}"
        firebase emulators:start --only firestore > logs/test_firestore.log 2>&1 &
        FIRESTORE_PID=$!
        sleep 5
        
        if ! lsof -i :8086 > /dev/null 2>&1; then
            echo -e "${RED}❌ Failed to start Firestore emulator${NC}"
            exit 1
        fi
        echo -e "${GREEN}✅ Firestore emulator started${NC}"
    else
        echo -e "${GREEN}✅ Firestore emulator already running${NC}"
    fi
    
    # Start test server
    if ! start_test_server; then
        exit 1
    fi
    
    # Run tests
    run_tests
    TEST_RESULT=$?
    
    # Report results
    if [ $TEST_RESULT -eq 0 ]; then
        echo -e "${GREEN}🎉 All smoke tests completed successfully!${NC}"
        echo -e "${GREEN}📊 The application UI is working correctly${NC}"
    else
        echo -e "${RED}💥 Smoke tests failed!${NC}"
        echo -e "${RED}🔍 Check test output above for details${NC}"
        echo -e "${YELLOW}💡 Common issues:${NC}"
        echo -e "${YELLOW}   - JavaScript errors in browser console${NC}"
        echo -e "${YELLOW}   - Missing HTML elements${NC}"
        echo -e "${YELLOW}   - API endpoints not responding${NC}"
        echo -e "${YELLOW}   - Static assets not loading${NC}"
    fi
    
    return $TEST_RESULT
}

# Run main function
main "$@"
