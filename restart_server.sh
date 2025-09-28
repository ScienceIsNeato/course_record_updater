#!/bin/bash

# restart_server.sh - Non-blocking server restart using SQLite backend
# Returns 0 on success, 1 on failure

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p logs

echo -e "${BLUE}🎯 Course Record Updater - Non-blocking Restart${NC}"
echo -e "${BLUE}===============================================${NC}"

if [ -f ".envrc" ]; then
    # shellcheck disable=SC1091
    source .envrc
    echo -e "${BLUE}🔧 Loaded environment variables from .envrc${NC}"
else
    export DATABASE_TYPE="sqlite"
    export DATABASE_URL="sqlite:///course_records.db"
    export COURSE_RECORD_UPDATER_PORT="3001"
    echo -e "${YELLOW}⚠️  No .envrc found, using SQLite defaults${NC}"
fi

DB_PATH="${DATABASE_URL#sqlite:///}"
echo -e "${BLUE}🔧 Using database: ${DB_PATH}${NC}"

echo "SQLite database located at: ${DB_PATH}" > logs/database_location.txt

claim_port() {
    local PORT=${1:-$COURSE_RECORD_UPDATER_PORT}
    if lsof -i :$PORT > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port $PORT occupied; reclaiming...${NC}"
        local PIDS
        PIDS=$(lsof -ti :$PORT || true)
        for PID in $PIDS; do
            echo -e "${BLUE}🔄 Terminating process on port $PORT (PID: $PID)${NC}"
            kill "$PID" 2>/dev/null || kill -9 "$PID" 2>/dev/null || true
        done
        sleep 1
    fi
}

start_flask_app() {
    local PORT=${1:-$COURSE_RECORD_UPDATER_PORT}

    echo -e "${BLUE}🌐 Starting Flask app on port $PORT...${NC}"

    if [ -d "venv" ]; then
        echo -e "${BLUE}📦 Activating virtual environment...${NC}"
        # shellcheck disable=SC1091
        source venv/bin/activate
    fi

    PYTHONUNBUFFERED=1 python app.py > logs/server.log 2>&1 &
    FLASK_PID=$!
    sleep 2

    if ! kill -0 $FLASK_PID 2>/dev/null; then
        echo -e "${RED}❌ Flask app failed to start${NC}" >&2
        echo -e "${RED}❌ Check logs/server.log for details${NC}" >&2
        return 1
    fi

    for _ in {1..10}; do
        if curl -s "http://localhost:$PORT" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Flask app started successfully on port $PORT${NC}"
            echo -e "${GREEN}📱 Access at http://localhost:$PORT${NC}"
            echo -e "${GREEN}🗄️  SQLite database at ${DB_PATH}${NC}"
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

main() {
    claim_port "$COURSE_RECORD_UPDATER_PORT"
    start_flask_app "$COURSE_RECORD_UPDATER_PORT"
}

main "$@"
