#!/bin/bash

# restart_server.sh - Environment-aware LOCAL server restart
# Usage: ./restart_server.sh <env>
#   <env> = local | e2e | smoke
# Returns 0 on success, 1 on failure
#
# NOTE: This script is for LOCAL development servers only.
# Deployed environments (dev, staging, prod) run on Cloud Run, not localhost.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Require environment argument
if [[ -z "${1:-}" ]]; then
    echo -e "${RED}❌ Error: Environment argument required${NC}" >&2
    echo -e "${YELLOW}Usage: $0 <env>${NC}" >&2
    echo -e "${YELLOW}  <env> = local | e2e | smoke${NC}" >&2
    echo "" >&2
    echo -e "${BLUE}Examples:${NC}" >&2
    echo -e "  ${GREEN}$0 local${NC}  # Start local dev server on port 3001" >&2
    echo -e "  ${GREEN}$0 e2e${NC}    # Start E2E test server on port 3002" >&2
    echo "" >&2
    echo -e "${YELLOW}NOTE: Deployed environments (dev, staging, prod) run on Cloud Run.${NC}" >&2
    echo -e "${YELLOW}      Use this script only for LOCAL development and testing.${NC}" >&2
    exit 1
fi

ENV_ARG="$1"

# Validate environment
if [[ ! "$ENV_ARG" =~ ^(local|e2e|smoke)$ ]]; then
    echo -e "${RED}❌ Error: Invalid environment '$ENV_ARG'${NC}" >&2
    echo -e "${YELLOW}Valid environments: local, e2e, smoke${NC}" >&2
    exit 1
fi

# Set environment BEFORE sourcing .envrc
export APP_ENV="$ENV_ARG"

mkdir -p logs

echo -e "${BLUE}🎯 LoopCloser - Environment-aware Restart${NC}"
echo -e "${BLUE}=====================================================${NC}"

# Save any pre-set environment variables that should not be overridden
SAVED_ENV="${ENV:-}"
SAVED_WTF_CSRF_ENABLED="${WTF_CSRF_ENABLED:-}"

# Load environment configuration
if [[ -f ".envrc" ]]; then
    # Local development: source .envrc (which sources .envrc.template)
    # shellcheck disable=SC1091
    source .envrc
    echo -e "${GREEN}✅ Loaded $APP_ENV environment from .envrc${NC}"
elif [[ -f ".envrc.template" ]]; then
    # CI environment: source template directly (secrets from GitHub Secrets)
    # shellcheck disable=SC1091
    source .envrc.template
    echo -e "${GREEN}✅ Loaded $APP_ENV environment from .envrc.template${NC}"
else
    echo -e "${RED}❌ Error: Neither .envrc nor .envrc.template found${NC}" >&2
    exit 1
fi

# Restore pre-set ENV only for E2E/UAT (not for smoke - it needs fresh test env)
if [[ -n "$SAVED_ENV" ]] && [[ "$APP_ENV" =~ ^(e2e|uat)$ ]]; then
    export ENV="$SAVED_ENV"
    echo -e "${BLUE}🔧 Using pre-configured ENV: $ENV${NC}"
fi

# Restore pre-set WTF_CSRF_ENABLED (e.g., from run_uat.sh for E2E tests)
if [[ -n "$SAVED_WTF_CSRF_ENABLED" ]]; then
    export WTF_CSRF_ENABLED="$SAVED_WTF_CSRF_ENABLED"
    echo -e "${BLUE}🔧 CSRF validation disabled for E2E tests${NC}"
fi

# For E2E and smoke tests, unset EMAIL_PROVIDER so factory uses ENV-based selection (ENV=test -> ethereal)
if [[ "$APP_ENV" =~ ^(e2e|uat|smoke)$ ]]; then
    export ENV="test"
    unset EMAIL_PROVIDER
    echo -e "${BLUE}🔧 Unset EMAIL_PROVIDER for $APP_ENV (will auto-select based on ENV)${NC}"
fi

# Determine database and base URL based on environment
case "$APP_ENV" in
    local)
        DATABASE_URL="${DATABASE_URL_LOCAL:-sqlite:///course_records_dev.db}"
        BASE_URL="${BASE_URL_LOCAL:-http://localhost:3001}"
        ;;
    e2e|uat)
        DATABASE_URL="${DATABASE_URL_E2E:-sqlite:///course_records_e2e.db}"
        BASE_URL="${BASE_URL_E2E:-http://localhost:3002}"
        ;;
    smoke)
        export ENV="test"
        DATABASE_URL="${DATABASE_URL_SMOKE:-sqlite:///course_records_smoke.db}"
        BASE_URL="${BASE_URL_SMOKE:-http://localhost:3003}"
        ;;
    *)
        # Default to local environment
        DATABASE_URL="${DATABASE_URL_LOCAL:-sqlite:///course_records_dev.db}"
        BASE_URL="${BASE_URL_LOCAL:-http://localhost:3001}"
        ;;
esac

export DATABASE_URL
DB_PATH="${DATABASE_URL#sqlite:///}"
echo -e "${BLUE}🔧 Using database: ${DB_PATH}${NC}"

echo "SQLite database located at: ${DB_PATH}" > logs/database_location.txt

claim_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port $port occupied; reclaiming...${NC}"
        local pids
        pids=$(lsof -ti :$port || true)
        for pid in $pids; do
            echo -e "${BLUE}🔄 Terminating process on port $port (PID: $pid)${NC}"
            kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
        done
        sleep 1
    fi
    return 0
}

start_flask_app() {
    local port=$1
    
    # Determine log file based on environment
    local log_file="logs/server.log"
    case "$APP_ENV" in
        e2e|uat)
            log_file="logs/test_server.log"
            ;;
        local|*)
            log_file="logs/server.log"
            ;;
    esac

    echo -e "${BLUE}🌐 Starting Flask app on port $port...${NC}"
    echo -e "${BLUE}📋 Server logs: ${log_file}${NC}"

    # Determine Python executable
    # Background processes don't inherit sourced environments, so use venv python directly
    local python_exe="python"
    if [[ -d "venv" ]]; then
        python_exe="./venv/bin/python"
        echo -e "${BLUE}📦 Using virtual environment Python${NC}"
    fi

    # Export environment variables for Flask app
    # Note: Must re-export with value assignment for subprocess inheritance
    export DATABASE_URL="$DATABASE_URL"
    export BASE_URL="$BASE_URL"
    export ENV="$ENV"
    export ETHEREAL_USER="${ETHEREAL_USER:-}"
    export ETHEREAL_PASS="${ETHEREAL_PASS:-}"
    export ETHEREAL_SMTP_HOST="${ETHEREAL_SMTP_HOST:-smtp.ethereal.email}"
    export ETHEREAL_SMTP_PORT="${ETHEREAL_SMTP_PORT:-587}"
    export ETHEREAL_IMAP_HOST="${ETHEREAL_IMAP_HOST:-imap.ethereal.email}"
    export ETHEREAL_IMAP_PORT="${ETHEREAL_IMAP_PORT:-993}"
    export WTF_CSRF_ENABLED="${WTF_CSRF_ENABLED:-true}"
    
    # Debug: Check if env vars are set
    echo -e "${BLUE}📧 Email configuration:${NC}"
    echo -e "   ENV=${ENV}"
    echo -e "   DATABASE_URL=${DATABASE_URL}"
    echo -e "   BASE_URL=${BASE_URL}"
    echo -e "   ETHEREAL_USER=${ETHEREAL_USER}"
    
    # Start Flask app using venv python directly (background processes don't inherit `source`)
    PORT="$port" DATABASE_URL="$DATABASE_URL" ENV="$ENV" BASE_URL="$BASE_URL" "$python_exe" -m src.app > "$log_file" 2>&1 &
    local flask_pid=$!
    for _ in {1..10}; do
        if curl -4 -s "http://localhost:$port" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Flask app started successfully on port $port${NC}"
            echo -e "${GREEN}📱 Access at http://localhost:$port${NC}"
            echo -e "${GREEN}🗄️  SQLite database at ${DB_PATH}${NC}"
            echo -e "${BLUE}📋 Server logs: ${log_file}${NC}"
            echo -e "${BLUE}📋 Use './scripts/monitor_logs.sh' to monitor server output${NC}"
            return 0
        fi
        sleep 1
    done

    echo -e "${RED}❌ Flask app started but is not responding on port $port${NC}" >&2
    echo -e "${RED}❌ Check ${log_file} for details${NC}" >&2
    return 1
}

main() {
    # AGGRESSIVE CLEANUP: Reset all the things
    echo -e "${BLUE}🧹 Aggressive cleanup: Killing stale processes...${NC}"
    pkill -f "python.*src\.app" 2>/dev/null || true
    sleep 0.5
    
    echo -e "${BLUE}🧹 Aggressive cleanup: Clearing Python bytecode cache...${NC}"
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    
    echo -e "${BLUE}🧹 Aggressive cleanup: Clearing SQLite locks and WAL files...${NC}"
    # Kill any processes holding the database file open
    DB_PATH="${DATABASE_URL#sqlite:///}"
    if [[ -f "$DB_PATH" ]]; then
#         # Find and kill processes with the database file open
#         # Use command substitution instead of pipe to avoid hanging when no processes found
#         pids_to_kill=$(lsof "$DB_PATH" 2>/dev/null | awk 'NR>1 {print $2}' | sort -u)
#         if [[ -n "$pids_to_kill" ]]; then
#             for pid in $pids_to_kill; do
#                 echo -e "${YELLOW}  Killing process $pid holding database lock${NC}"
#                 kill -9 "$pid" 2>/dev/null || true
#             done
#         fi
        
        # Remove SQLite WAL and SHM files that can cause locks
        # rm -f "${DB_PATH}-wal" "${DB_PATH}-shm" 2>/dev/null || true
        true
    fi
    
    echo -e "${GREEN}✅ Clean slate ready${NC}"

    # Determine port based on environment
    local port
    case "$APP_ENV" in
        local)
            port="${LOOPCLOSER_DEFAULT_PORT_LOCAL:-3001}"
            ;;
        e2e|uat)
            port="${LOOPCLOSER_DEFAULT_PORT_E2E:-3002}"
            ;;
        smoke)
            export ENV="test"
            port="${LOOPCLOSER_DEFAULT_PORT_SMOKE:-3003}"
            ;;
        *)
            # Default to local port
            port="${LOOPCLOSER_DEFAULT_PORT_LOCAL:-3001}"
            ;;
    esac
    
    echo -e "${BLUE}🌐 Starting Flask app on port $port...${NC}"
    claim_port "$port"
    start_flask_app "$port"
    return $?
}

main "$@"
