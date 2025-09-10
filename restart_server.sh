#!/bin/bash

# restart_server.sh - Non-blocking server restart with proper exit codes
# Returns 0 on success, 1 on failure
# Logs are written to logs/server.log for consistent monitoring

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create logs directory if it doesn't exist
mkdir -p logs

# Load environment variables from .envrc
if [ -f ".envrc" ]; then
    source .envrc
    echo -e "${BLUE}🔧 Loaded environment variables from .envrc${NC}"
else
    # Fallback defaults if .envrc doesn't exist
    export FIRESTORE_EMULATOR_HOST="localhost:8086"
    export COURSE_RECORD_UPDATER_PORT="3001"
    echo -e "${YELLOW}⚠️  No .envrc found, using defaults${NC}"
fi

echo -e "${BLUE}🔧 Set FIRESTORE_EMULATOR_HOST=$FIRESTORE_EMULATOR_HOST${NC}"
echo -e "${BLUE}🔧 Course Record Updater will claim port $COURSE_RECORD_UPDATER_PORT${NC}"

# Function to check if Firestore emulator is running
check_firestore_emulator() {
    if lsof -i :8086 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Firestore emulator already running on localhost:8086${NC}"
        return 0
    else
        echo -e "${YELLOW}🚀 Starting Firestore emulator...${NC}"
        # Start emulator in background, redirect output to log
        firebase emulators:start --only firestore >> logs/firestore.log 2>&1 &
        FIRESTORE_PID=$!
        
        # Wait for emulator to start
        for i in {1..30}; do
            if lsof -i :8086 > /dev/null 2>&1; then
                echo -e "${GREEN}✅ Firestore emulator started successfully${NC}"
                return 0
            fi
            sleep 1
        done
        
        echo -e "${RED}❌ Failed to start Firestore emulator${NC}" >&2
        return 1
    fi
}

# Function to claim our dedicated port
claim_port() {
    local PORT=${1:-$COURSE_RECORD_UPDATER_PORT}
    
    # Check if port is in use and aggressively claim it if it's ours
    if lsof -i :$PORT > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port $PORT is in use. Checking if it's our own process...${NC}"
        
        # Check if it's our own Flask app
        EXISTING_PID=$(lsof -ti :$PORT)
        if ps -p $EXISTING_PID -o comm= 2>/dev/null | grep -q python; then
            if ps -p $EXISTING_PID -o args= 2>/dev/null | grep -q "app.py"; then
                echo -e "${BLUE}🔄 Killing existing Course Record Updater process (PID: $EXISTING_PID)${NC}"
                kill $EXISTING_PID 2>/dev/null || kill -9 $EXISTING_PID 2>/dev/null
                sleep 2
                
                # Double-check it's gone
                if lsof -i :$PORT > /dev/null 2>&1; then
                    echo -e "${YELLOW}💀 Force killing stubborn process...${NC}"
                    EXISTING_PID=$(lsof -ti :$PORT)
                    kill -9 $EXISTING_PID 2>/dev/null
                    sleep 1
                fi
            else
                echo -e "${YELLOW}⚠️  Port $PORT is occupied by another Python process. This app owns port $PORT!${NC}"
                echo -e "${BLUE}🔄 Proceeding to claim our dedicated port anyway...${NC}"
                EXISTING_PID=$(lsof -ti :$PORT)
                kill $EXISTING_PID 2>/dev/null || kill -9 $EXISTING_PID 2>/dev/null
                sleep 1
            fi
        else
            echo -e "${YELLOW}⚠️  Port $PORT is occupied by a non-Python process:${NC}"
            lsof -i :$PORT
            echo -e "${BLUE}💡 This app owns port $PORT. Consider updating the other application.${NC}"
            echo -e "${BLUE}🔄 Attempting to claim our port...${NC}"
            EXISTING_PID=$(lsof -ti :$PORT)
            kill $EXISTING_PID 2>/dev/null || kill -9 $EXISTING_PID 2>/dev/null
            sleep 1
        fi
        
        # Final check - if still occupied, we'll try anyway and let the OS handle it
        if lsof -i :$PORT > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  Port $PORT still occupied, but proceeding anyway...${NC}"
        else
            echo -e "${GREEN}✅ Successfully claimed port $PORT${NC}"
        fi
    fi
    
    return 0
}

# Function to start Flask app
start_flask_app() {
    local PORT=${1:-$COURSE_RECORD_UPDATER_PORT}
    
    echo -e "${BLUE}🌐 Starting Flask app on port $PORT...${NC}"
    
    # Activate virtual environment if it exists
    if [ -d "venv" ]; then
        echo -e "${BLUE}📦 Activating virtual environment...${NC}"
        source venv/bin/activate
    fi
    
    # Start Flask app in background, redirect all output to log file
    PYTHONUNBUFFERED=1 python app.py > logs/server.log 2>&1 &
    FLASK_PID=$!
    
    # Wait a moment to see if the process starts successfully
    sleep 2
    
    # Check if the process is still running
    if ! kill -0 $FLASK_PID 2>/dev/null; then
        echo -e "${RED}❌ Flask app failed to start${NC}" >&2
        echo -e "${RED}❌ Check logs/server.log for details${NC}" >&2
        return 1
    fi
    
    # Wait for the server to be ready
    for i in {1..10}; do
        if curl -s http://localhost:$PORT > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Flask app started successfully on port $PORT${NC}"
            echo -e "${GREEN}📱 Access at http://localhost:$PORT${NC}"
            echo -e "${GREEN}🗄️  Firestore emulator UI at http://localhost:4000${NC}"
            echo -e "${BLUE}📋 Server logs: logs/server.log${NC}"
            echo -e "${BLUE}📋 Use './tail_logs.sh' to monitor server output${NC}"
            return 0
        fi
        sleep 1
    done
    
    echo -e "${RED}❌ Flask app started but is not responding on port $PORT${NC}" >&2
    echo -e "${RED}❌ Check logs/server.log for details${NC}" >&2
    return 1
}

# Main execution
main() {
    echo -e "${BLUE}🎯 Course Record Updater - Non-blocking Restart${NC}"
    echo -e "${BLUE}===============================================${NC}"
    
    # Check Firestore emulator
    if ! check_firestore_emulator; then
        echo -e "${RED}❌ Failed to start/verify Firestore emulator${NC}" >&2
        exit 1
    fi
    
    # Claim our port
    if ! claim_port; then
        echo -e "${RED}❌ Failed to claim port $COURSE_RECORD_UPDATER_PORT${NC}" >&2
        exit 1
    fi
    
    # Start Flask app
    if ! start_flask_app; then
        echo -e "${RED}❌ Failed to start Flask application${NC}" >&2
        exit 1
    fi
    
    echo -e "${GREEN}✅ Server restart completed successfully${NC}"
    exit 0
}

# Run main function
main "$@"
