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
    echo "  --env ENV          Environment: dev, e2e, or uat (default: dev)"
    echo "  -f, --file FILE    Monitor specific log file (overrides --env)"
    echo "  -n, --lines NUM    Show last NUM lines and exit (no follow)"
    echo "  --follow           Force follow mode even with -n"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      # Monitor dev server log (follow mode)"
    echo "  $0 --env e2e            # Monitor E2E test server log"
    echo "  $0 --env e2e -n 50      # Show last 50 E2E log lines"
    echo "  $0 -n 20 --follow       # Show last 20 dev lines then follow"
    echo "  $0 -f logs/database_location.txt  # View specific file"
    echo ""
    echo "Environment Log Files:"
    echo "  dev: logs/server.log"
    echo "  e2e: logs/test_server.log"
    echo "  uat: logs/test_server.log"
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
        echo -e "${BLUE}☁️  Polling logs (press Ctrl+C to stop)...${NC}"
        # Simple polling loop to avoid requiring grpcio for live tail
        LAST_TIMESTAMP=""
        while true; do
            # Construct filter for new logs
            CURRENT_FILTER="$FILTER"
            if [ -n "$LAST_TIMESTAMP" ]; then
                CURRENT_FILTER="$FILTER timestamp > \"$LAST_TIMESTAMP\""
            fi
            
            # Fetch logs
            # Use --format="csv[no-heading](timestamp,textPayload)" to get both for tracking
            # Use order=desc to get NEWEST logs first, then we'll reverse them or just handle timestamps
            gcloud logging read "$CURRENT_FILTER" --limit=20 --format="csv[no-heading](timestamp,textPayload)" --order=desc 2>/dev/null > /tmp/logs_output.csv
            
            if [ -s /tmp/logs_output.csv ]; then
                # Read line by line from temp file
                # Use tac if available to reverse lines (so oldest is first), otherwise just read as is
                if command -v tac &> /dev/null; then
                    CMD="tac /tmp/logs_output.csv"
                else
                    CMD="cat /tmp/logs_output.csv"
                fi

                $CMD | while IFS=, read -r ts payload; do
                    # Check if we've already seen this timestamp to avoid duplicates in tight polling
                    if [[ "$ts" > "$LAST_TIMESTAMP" ]]; then
                        # Normalize output format to look like local logs:
                        # [YYYY-MM-DD HH:MM:SS] Message
                        # Cloud timestamp is ISO8601, just keeping it as is or formatting it would be nice, 
                        # but raw TS is fine for now to match structure.
                        # Also apply colorization logic similar to local logs
                        
                        line="[$ts] $payload"
                        
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

                        LAST_TIMESTAMP="$ts"
                    fi
                done
            fi
            rm -f /tmp/logs_output.csv
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
             echo "[$ts] $payload"
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
