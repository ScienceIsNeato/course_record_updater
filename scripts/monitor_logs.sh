#!/bin/bash

# tail_logs.sh - Monitor server logs in real-time
# Shows server output with timestamps and colored output for better readability

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default log file and environment
LOG_FILE=""
ENVIRONMENT=""

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Monitor LoopCloser server logs in real-time"
    echo ""
    echo "Options:"
    echo "  --env ENV          Environment: dev, local, e2e, or uat (REQUIRED)"
    echo "  -f, --file FILE    Monitor specific log file (overrides --env)"
    echo "  -n, --lines NUM    Show last NUM lines initially (default: 10)"
    echo "  --follow           Enable follow mode (default: true, disable with -n)"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --env local          # Monitor local dev server (follow mode)"
    echo "  $0 --env dev            # Monitor Cloud Run dev logs (follow mode)"
    echo "  $0 --env e2e            # Monitor E2E test server log"
    echo "  $0 --env dev -n 50      # Show last 50 dev logs (no follow)"
    echo "  $0 --env local --follow # Monitor local with explicit follow"
    echo ""
    echo "Environment Log Sources:"
    echo "  local: logs/server.log (local file)"
    echo "  dev: Cloud Run loopcloser-dev (gcloud logs)"
    echo "  e2e: logs/test_server.log (local file)"
    echo "  uat: logs/test_server.log (local file)"
}

# Function to colorize log output
colorize_logs() {
    while IFS= read -r line; do
        # Add timestamp if line doesn't already have one
        if [[ ! $line =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2} ]]; then
            timestamp=$(date '+%Y-%m-%d %H:%M:%S')
            line="[$timestamp] $line"
        fi

        # Colorize based on content
        if [[ $line == *"ERROR"* ]] || [[ $line == *"Error"* ]] || [[ $line == *"error"* ]] || [[ $line == *"Exception"* ]] || [[ $line == *"Traceback"* ]]; then
            echo -e "${RED}$line${NC}"
        elif [[ $line == *"WARNING"* ]] || [[ $line == *"Warning"* ]] || [[ $line == *"warning"* ]]; then
            echo -e "${YELLOW}$line${NC}"
        elif [[ $line == *"INFO"* ]] || [[ $line == *"Starting"* ]] || [[ $line == *"started"* ]] || [[ $line == *"✅"* ]]; then
            echo -e "${GREEN}$line${NC}"
        elif [[ $line == *"DEBUG"* ]] || [[ $line == *"[DB Service"* ]]; then
            echo -e "${CYAN}$line${NC}"
        elif [[ $line == *"127.0.0.1"* ]] || [[ $line == *"GET"* ]] || [[ $line == *"POST"* ]]; then
            echo -e "${BLUE}$line${NC}"
        else
            echo "$line"
        fi
    done
}

# Parse command line arguments
LINES=10
FOLLOW=true
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -f|--file)
            LOG_FILE="$2"
            shift 2
            ;;
        -n|--lines)
            LINES="$2"
            FOLLOW=false  # When -n is specified, don't follow by default
            shift 2
            ;;
        --follow)
            FOLLOW=true   # Explicit follow flag
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}" >&2
            show_usage
            exit 1
            ;;
    esac
done

# Determine log file based on environment if not explicitly provided
# Check that ENVIRONMENT is set (it's required now)
if [ -z "$ENVIRONMENT" ]; then
    echo -e "${RED}❌ Error: --env argument is required.${NC}"
    show_usage
    exit 1
fi

# Determine log file based on environment
case "$ENVIRONMENT" in
    e2e|uat)
        LOG_FILE="logs/test_server.log"
        ;;
    dev)
        # Dev uses Cloud Run logs
        ;;
    local)
        LOG_FILE="logs/server.log"
        ;;
    *)
        echo -e "${RED}❌ Invalid environment: $ENVIRONMENT${NC}" >&2
        echo -e "${YELLOW}Valid environments: dev, local, e2e, uat${NC}"
        exit 1
        ;;
esac

# Check if using Cloud Run logging
if [ "$ENVIRONMENT" == "dev" ]; then
    echo -e "${BLUE}☁️  Fetching logs from Cloud Run (loopcloser-dev)...${NC}"
    echo -e "${BLUE}   (Use Ctrl+C to stop)${NC}"
    echo ""
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}❌ gcloud CLI not found. Please install Google Cloud SDK.${NC}"
        exit 1
    fi

    # Filter for the service
    FILTER="resource.type=\"cloud_run_revision\" resource.labels.service_name=\"loopcloser-dev\""
    
    if [ "$FOLLOW" = true ]; then
        echo -e "${BLUE}☁️  Showing last ${LINES} lines, then polling for new logs...${NC}"
        echo -e "${BLUE}🛑 Press Ctrl+C to stop monitoring${NC}"
        echo ""
        
        # Show initial logs
        gcloud logging read "$FILTER" --limit="$LINES" --format="csv[no-heading](timestamp,textPayload)" --order=desc 2>/dev/null > /tmp/logs_init.csv
        
        LAST_TIMESTAMP=""
        if [ -s /tmp/logs_init.csv ]; then
            if command -v tac &> /dev/null; then
                CMD="tac /tmp/logs_init.csv"
            else
                CMD="cat /tmp/logs_init.csv"
            fi
            
            # Show initial logs and track last timestamp
            while IFS=, read -r ts payload; do
                # Skip empty log entries (Cloud Run heartbeats/metadata with no textPayload)
                if [ -z "$payload" ] || [ "$payload" = '""' ]; then
                    LAST_TIMESTAMP="$ts"
                    continue
                fi
                
                line="[$ts] $payload"
                
                # Colorize
                if [[ $line == *"ERROR"* ]] || [[ $line == *"Error"* ]] || [[ $line == *"error"* ]] || [[ $line == *"Exception"* ]] || [[ $line == *"Traceback"* ]]; then
                    echo -e "${RED}$line${NC}"
                elif [[ $line == *"WARNING"* ]] || [[ $line == *"Warning"* ]] || [[ $line == *"warning"* ]]; then
                    echo -e "${YELLOW}$line${NC}"
                elif [[ $line == *"INFO"* ]] || [[ $line == *"Starting"* ]] || [[ $line == *"started"* ]] || [[ $line == *"✅"* ]]; then
                    echo -e "${GREEN}$line${NC}"
                elif [[ $line == *"DEBUG"* ]] || [[ $line == *"[DB Service"* ]]; then
                    echo -e "${CYAN}$line${NC}"
                elif [[ $line == *"127.0.0.1"* ]] || [[ $line == *"GET"* ]] || [[ $line == *"POST"* ]]; then
                    echo -e "${BLUE}$line${NC}"
                else
                    echo "$line"
                fi
                
                # Update last timestamp (this persists because we're not in a subshell pipe)
                LAST_TIMESTAMP="$ts"
            done < <($CMD)
        fi
        rm -f /tmp/logs_init.csv
        
        echo ""
        echo -e "${BLUE}--- Watching for new logs (2s polling interval) ---${NC}"
        echo ""
        
        # Poll for new logs
        while true; do
            # Only fetch logs AFTER last timestamp
            if [ -n "$LAST_TIMESTAMP" ]; then
                CURRENT_FILTER="$FILTER timestamp > \"$LAST_TIMESTAMP\""
            else
                CURRENT_FILTER="$FILTER"
            fi
            
            # Fetch new logs
            gcloud logging read "$CURRENT_FILTER" --limit=50 --format="csv[no-heading](timestamp,textPayload)" --order=desc 2>/dev/null > /tmp/logs_new.csv
            
            if [ -s /tmp/logs_new.csv ]; then
                # Reverse to show oldest first
                if command -v tac &> /dev/null; then
                    CMD="tac /tmp/logs_new.csv"
                else
                    CMD="cat /tmp/logs_new.csv"
                fi
                
                # Process new logs and update LAST_TIMESTAMP (no subshell!)
                while IFS=, read -r ts payload; do
                    # Skip empty log entries (Cloud Run heartbeats/metadata with no textPayload)
                    if [ -z "$payload" ] || [ "$payload" = '""' ]; then
                        LAST_TIMESTAMP="$ts"
                        continue
                    fi
                    
                    line="[$ts] $payload"
                    
                    # Colorize
                    if [[ $line == *"ERROR"* ]] || [[ $line == *"Error"* ]] || [[ $line == *"error"* ]] || [[ $line == *"Exception"* ]] || [[ $line == *"Traceback"* ]]; then
                        echo -e "${RED}$line${NC}"
                    elif [[ $line == *"WARNING"* ]] || [[ $line == *"Warning"* ]] || [[ $line == *"warning"* ]]; then
                        echo -e "${YELLOW}$line${NC}"
                    elif [[ $line == *"INFO"* ]] || [[ $line == *"Starting"* ]] || [[ $line == *"started"* ]] || [[ $line == *"✅"* ]]; then
                        echo -e "${GREEN}$line${NC}"
                    elif [[ $line == *"DEBUG"* ]] || [[ $line == *"[DB Service"* ]]; then
                        echo -e "${CYAN}$line${NC}"
                    elif [[ $line == *"127.0.0.1"* ]] || [[ $line == *"GET"* ]] || [[ $line == *"POST"* ]]; then
                        echo -e "${BLUE}$line${NC}"
                    else
                        echo "$line"
                    fi
                    
                    # Update last timestamp (persists because not in pipe subshell)
                    LAST_TIMESTAMP="$ts"
                done < <($CMD)
            fi
            rm -f /tmp/logs_new.csv
            sleep 2
        done
    else
        # Non-follow mode (just dump last N lines)
        gcloud logging read "$FILTER" --limit="$LINES" --format="csv[no-heading](timestamp,textPayload)" --order=desc > /tmp/logs_output.csv
        if command -v tac &> /dev/null; then
             CMD="tac /tmp/logs_output.csv"
        else
             CMD="cat /tmp/logs_output.csv"
        fi
        
        $CMD | while IFS=, read -r ts payload; do
             # Skip empty entries
             if [ -n "$payload" ] && [ "$payload" != '""' ]; then
                 echo "[$ts] $payload"
             fi
        done
        rm -f /tmp/logs_output.csv
    fi
    exit 0
fi

# Check if log file exists (for local modes)
if [ ! -f "$LOG_FILE" ]; then
    echo -e "${YELLOW}⚠️  Log file not found: $LOG_FILE${NC}"
    echo -e "${BLUE}💡 Have you started the server? Try running: ./restart_server.sh${NC}"
    echo -e "${BLUE}💡 Available log files:${NC}"
    if [ -d "logs" ]; then
        ls -la logs/ 2>/dev/null || echo "   No log files found"
    else
        echo "   logs/ directory doesn't exist"
    fi
    exit 1
fi

if [ "$FOLLOW" = true ]; then
    echo -e "${BLUE}📊 Showing last $LINES lines, then following...${NC}"
    echo -e "${BLUE}🛑 Press Ctrl+C to stop monitoring${NC}"
    echo ""
    # Show initial lines and then follow
    tail -n "$LINES" -f "$LOG_FILE" | colorize_logs
else
    echo -e "${BLUE}📊 Showing last $LINES lines${NC}"
    echo ""
    # Just show the lines without following
    tail -n "$LINES" "$LOG_FILE" | colorize_logs
fi
