#!/bin/bash

# restart_server.sh - Environment-aware server restart using SQLite backend
# Usage: ./restart_server.sh <env>
#   <env> = dev | e2e
# Returns 0 on success, 1 on failure

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
    echo -e "${YELLOW}  <env> = dev | e2e${NC}" >&2
    echo "" >&2
    echo -e "${BLUE}Examples:${NC}" >&2
    echo -e "  ${GREEN}$0 dev${NC}  # Start dev server on port 3001" >&2
    echo -e "  ${GREEN}$0 e2e${NC}  # Start E2E server on port 3002" >&2
    exit 1
fi

ENV_ARG="$1"

# Validate environment
if [[ ! "$ENV_ARG" =~ ^(dev|e2e)$ ]]; then
    echo -e "${RED}❌ Error: Invalid environment '$ENV_ARG'${NC}" >&2
    echo -e "${YELLOW}Valid environments: dev, e2e${NC}" >&2
    exit 1
fi

# Set environment BEFORE sourcing .envrc
export APP_ENV="$ENV_ARG"

mkdir -p logs

echo -e "${BLUE}🎯 Course Record Updater - Environment-aware Restart${NC}"
echo -e "${BLUE}=====================================================${NC}"

# Save any pre-set environment variables that should not be overridden
SAVED_ENV="${ENV:-}"

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

# Restore pre-set ENV (e.g., ENV="test" from run_uat.sh)
if [[ -n "$SAVED_ENV" ]]; then
    export ENV="$SAVED_ENV"
    echo -e "${BLUE}🔧 Using pre-configured ENV: $ENV${NC}"
fi

# For E2E tests, unset EMAIL_PROVIDER so factory uses ENV-based selection (ENV=test -> ethereal)
if [[ "$APP_ENV" = "e2e" ]] || [[ "$APP_ENV" = "uat" ]]; then
    unset EMAIL_PROVIDER
    echo -e "${BLUE}🔧 Unset EMAIL_PROVIDER for E2E (will auto-select Ethereal)${NC}"
fi

# Determine database and base URL based on environment
case "$APP_ENV" in
    dev)
        DATABASE_URL="${DATABASE_URL_DEV:-sqlite:///course_records_dev.db}"
        BASE_URL="${BASE_URL_DEV:-http://localhost:3001}"
        ;;
    e2e|uat)
        DATABASE_URL="${DATABASE_URL_E2E:-sqlite:///course_records_e2e.db}"
        BASE_URL="${BASE_URL_E2E:-http://localhost:3002}"
        ;;
    *)
        # Default to dev environment
        DATABASE_URL="${DATABASE_URL_DEV:-sqlite:///course_records_dev.db}"
        BASE_URL="${BASE_URL_DEV:-http://localhost:3001}"
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
        dev|*)
            log_file="logs/server.log"
            ;;
    esac

    echo -e "${BLUE}🌐 Starting Flask app on port $port...${NC}"
    echo -e "${BLUE}📋 Server logs: ${log_file}${NC}"

    if [[ -d "venv" ]]; then
        echo -e "${BLUE}📦 Activating virtual environment...${NC}"
        # shellcheck disable=SC1091
        source venv/bin/activate
    fi

    # Export environment variables for Flask app
    # Note: Must re-export with value assignment for subprocess inheritance
    export PORT="$port"
    export DATABASE_URL="$DATABASE_URL"
    export BASE_URL="$BASE_URL"
    export ENV="$ENV"
    export ETHEREAL_USER="${ETHEREAL_USER:-}"
    export ETHEREAL_PASS="${ETHEREAL_PASS:-}"
    export ETHEREAL_SMTP_HOST="${ETHEREAL_SMTP_HOST:-smtp.ethereal.email}"
    export ETHEREAL_SMTP_PORT="${ETHEREAL_SMTP_PORT:-587}"
    export ETHEREAL_IMAP_HOST="${ETHEREAL_IMAP_HOST:-imap.ethereal.email}"
    export ETHEREAL_IMAP_PORT="${ETHEREAL_IMAP_PORT:-993}"
    export EMAIL_WHITELIST="${EMAIL_WHITELIST:-*@ethereal.email,*@example.com}"
    
    # Debug: Check if env vars are set
    echo -e "${BLUE}📧 Email configuration:${NC}"
    echo -e "   ENV=${ENV}"
    echo -e "   DATABASE_URL=${DATABASE_URL}"
    echo -e "   BASE_URL=${BASE_URL}"
    echo -e "   ETHEREAL_USER=${ETHEREAL_USER}"
    
    # Start Flask app
    # Explicitly pass DATABASE_URL in the command to ensure subprocess gets it
    DATABASE_URL="$DATABASE_URL" ENV="$ENV" BASE_URL="$BASE_URL" python app.py > "$log_file" 2>&1 &
    local flask_pid=$!
    sleep 2

    if ! kill -0 $flask_pid 2>/dev/null; then
        echo -e "${RED}❌ Flask app failed to start${NC}" >&2
        echo -e "${RED}❌ Check ${log_file} for details${NC}" >&2
        return 1
    fi

    for _ in {1..10}; do
        if curl -s "http://localhost:$port" > /dev/null 2>&1; then
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
    # Determine port based on environment
    local port
    case "$APP_ENV" in
        dev)
            port="${LASSIE_DEFAULT_PORT_DEV:-3001}"
            ;;
        e2e|uat)
            port="${LASSIE_DEFAULT_PORT_E2E:-3002}"
            ;;
        *)
            # Default to dev port
            port="${LASSIE_DEFAULT_PORT_DEV:-3001}"
            ;;
    esac
    
    echo -e "${BLUE}🌐 Starting Flask app on port $port...${NC}"
    claim_port "$port"
    start_flask_app "$port"
    return $?
}

main "$@"
