#!/bin/bash

# check_frontend.sh - Quick frontend validation for development workflow
# This is a lightweight version of smoke tests for rapid feedback

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Quick Frontend Check${NC}"
echo -e "${BLUE}=====================${NC}"

# Check if server is running
if ! curl -s http://localhost:3001 > /dev/null 2>&1; then
    echo -e "${RED}❌ Server not running on port 3001${NC}"
    echo -e "${YELLOW}💡 Start server with: ./restart_server.sh${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Server is running${NC}"

# Check for basic HTML structure (login page since root redirects)
echo -e "${BLUE}🔍 Checking HTML structure...${NC}"
RESPONSE=$(curl -s http://localhost:3001/login)

# Check for required elements (authentication system)
REQUIRED_ELEMENTS=(
    "loginForm"
    "email"
    "password"
    "auth-container"
    "Welcome Back"
    "CEI Course Admin"
)

MISSING_ELEMENTS=()
for element in "${REQUIRED_ELEMENTS[@]}"; do
    if ! echo "$RESPONSE" | grep -q "$element"; then
        MISSING_ELEMENTS+=("$element")
    fi
done

if [ ${#MISSING_ELEMENTS[@]} -gt 0 ]; then
    echo -e "${RED}❌ Missing HTML elements:${NC}"
    for element in "${MISSING_ELEMENTS[@]}"; do
        echo -e "${RED}   - $element${NC}"
    done
    exit 1
fi

echo -e "${GREEN}✅ All required HTML elements found${NC}"

# Check static assets
echo -e "${BLUE}🔍 Checking static assets...${NC}"
STATIC_ASSETS=(
    "/static/script.js"
    "/static/style.css"
    "/static/images/cei_logo.jpg"
)

for asset in "${STATIC_ASSETS[@]}"; do
    if ! curl -s -f "http://localhost:3001$asset" > /dev/null; then
        echo -e "${RED}❌ Static asset not found: $asset${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ All static assets loading${NC}"

# Check API health
echo -e "${BLUE}🔍 Checking API health...${NC}"
if ! curl -s http://localhost:3001/api/health > /dev/null 2>&1; then
    echo -e "${RED}❌ API health check failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ API is healthy${NC}"

# Quick JavaScript syntax check
echo -e "${BLUE}🔍 Checking JavaScript syntax...${NC}"
if command -v node >/dev/null 2>&1; then
    if ! node -c static/script.js 2>/dev/null; then
        echo -e "${RED}❌ JavaScript syntax errors found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ JavaScript syntax is valid${NC}"
else
    echo -e "${YELLOW}⚠️ Node.js not found - skipping JS syntax check${NC}"
fi

echo -e "${GREEN}🎉 Frontend check passed!${NC}"
echo -e "${BLUE}💡 For comprehensive testing, run: ./run_smoke_tests.sh${NC}"
