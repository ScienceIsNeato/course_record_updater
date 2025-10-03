#!/bin/bash

# restart_server.sh - Environment-aware server restart using SQLite backend
# Usage: ./restart_server.sh <env>
#   <env> = dev | e2e | ci
# Returns 0 on success, 1 on failure

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Require environment argument
if [ -z "${1:-}" ]; then
    echo -e "${RED}❌ Error: Environment argument required${NC}" >&2
    echo -e "${YELLOW}Usage: $0 <env>${NC}" >&2
    echo -e "${YELLOW}  <env> = dev | e2e | ci${NC}" >&2
    echo "" >&2
    echo -e "${BLUE}Examples:${NC}" >&2
    echo -e "  ${GREEN}$0 dev${NC}  # Start dev server on port 3001" >&2
    echo -e "  ${GREEN}$0 e2e${NC}  # Start E2E server on port 3002" >&2
    echo -e "  ${GREEN}$0 ci${NC}   # Start CI server on port 3003" >&2
    exit 1
fi

ENV_ARG="$1"

# Validate environment
if [[ ! "$ENV_ARG" =~ ^(dev|e2e|ci)$ ]]; then
    echo -e "${RED}❌ Error: Invalid environment '$ENV_ARG'${NC}" >&2
    echo -e "${YELLOW}Valid environments: dev, e2e, ci${NC}" >&2
    exit 1
fi

# Set environment BEFORE sourcing .envrc
export APP_ENV="$ENV_ARG"

mkdir -p logs

echo -e "${BLUE}🎯 Course Record Updater - Environment-aware Restart${NC}"
echo -e "${BLUE}=====================================================${NC}"

# Load environment configuration
if [ -f ".envrc" ]; then
    # Local development: source .envrc (which sources .envrc.template)
    # shellcheck disable=SC1091
    source .envrc
    echo -e "${GREEN}✅ Loaded $APP_ENV environment from .envrc${NC}"
elif [ -f ".envrc.template" ]; then
    # CI environment: source template directly (secrets from GitHub Secrets)
    # shellcheck disable=SC1091
    source .envrc.template
    echo -e "${GREEN}✅ Loaded $APP_ENV environment from .envrc.template${NC}"
else
    echo -e "${RED}❌ Error: Neither .envrc nor .envrc.template found${NC}" >&2
    exit 1
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
