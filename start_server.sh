#!/bin/bash

# Course Record Updater Server Startup Script
# This script helps avoid port conflicts with other applications

echo "🎯 Course Record Updater Server Startup"
echo "========================================"

# Check for demo mode flag
DEMO_MODE=false
if [ "$1" = "--demo" ] || [ "$1" = "-d" ]; then
    DEMO_MODE=true
    shift  # Remove the flag from arguments
    echo "🧪 DEMO MODE: Running without Firestore database"
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check for port conflicts and suggest alternatives
echo "🔍 Checking port availability..."

check_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        echo "❌ Port $port is in use"
        return 1
    else
        echo "✅ Port $port is available"
        return 0
    fi
}

# Default port
DEFAULT_PORT=3001

echo "Port Status:"
check_port 5000 && echo "  - 5000: Available (usually ControlCenter)" || echo "  - 5000: In use (ControlCenter)"
check_port 3000 && echo "  - 3000: Available (common React apps)" || echo "  - 3000: In use"
check_port 3001 && echo "  - 3001: Available (Course Record Updater default)" || echo "  - 3001: In use"
check_port 8080 && echo "  - 8080: Available" || echo "  - 8080: In use (likely FogOfDog)"

echo ""

# Choose which app to run
if [ "$DEMO_MODE" = true ]; then
    APP_FILE="demo_app.py"
    echo "📱 Using demo application (no database required)"
else
    APP_FILE="app.py"
    echo "📱 Using full application (requires Firestore)"
fi

# Use provided port or default
if [ -n "$1" ]; then
    PORT=$1
    echo "🚀 Starting Course Record Updater on port $PORT (user specified)..."
    PORT=$PORT python $APP_FILE
elif check_port $DEFAULT_PORT; then
    echo "🚀 Starting Course Record Updater on default port $DEFAULT_PORT..."
    python $APP_FILE
else
    echo "⚠️  Default port $DEFAULT_PORT is in use. Trying alternative ports..."
    for alt_port in 3002 3003 3004; do
        if check_port $alt_port; then
            echo "🚀 Starting Course Record Updater on port $alt_port..."
            PORT=$alt_port python $APP_FILE
            exit 0
        fi
    done
    echo "❌ No available ports found. Please specify a port manually:"
    echo "   ./start_server.sh 3005"
    echo "   ./start_server.sh --demo 3005"
    exit 1
fi
