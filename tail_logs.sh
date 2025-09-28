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

# Default log file
LOG_FILE="logs/server.log"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Monitor Course Record Updater server logs in real-time"
    echo ""
    echo "Options:"
    echo "  -f, --file FILE    Monitor specific log file (default: logs/server.log)"
    echo "  -n, --lines NUM    Show last NUM lines and exit (no follow)"
    echo "  --follow           Force follow mode even with -n"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      # Monitor default server log (follow mode)"
    echo "  $0 -n 50              # Show last 50 lines and exit"
    echo "  $0 -n 20 --follow     # Show last 20 lines then follow"
    echo "  $0 -f logs/database_location.txt  # View current SQLite database path"
}

# Parse command line arguments
LINES=10
FOLLOW=true
while [[ $# -gt 0 ]]; do
    case $1 in
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

# Check if log file exists
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

# Main execution
echo -e "${BLUE}📋 Course Record Updater - Log Monitor${NC}"
echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}📁 Monitoring: $LOG_FILE${NC}"

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
