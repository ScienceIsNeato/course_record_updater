#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

PORT="${1:-${LOOPCLOSER_DEFAULT_PORT_FRONTEND_SANITY:-3011}}"
BASE_URL="http://127.0.0.1:${PORT}"
SERVER_PID=""

stop_frontend_server() {
  if [[ -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}

trap stop_frontend_server EXIT

start_frontend_server_if_needed() {
  if curl -s "$BASE_URL" >/dev/null 2>&1; then
    return 0
  fi

  local python_exe="python"
  if [[ -x "./venv/bin/python" ]]; then
    python_exe="./venv/bin/python"
  fi

  export DATABASE_TYPE="${DATABASE_TYPE:-sqlite}"
  export DATABASE_URL="${DATABASE_URL:-sqlite:///${PROJECT_ROOT}/loopcloser_dev.db}"
  export ENV="${ENV:-test}"
  export BASE_URL="$BASE_URL"

  mkdir -p logs
  PORT="$PORT" "$python_exe" -m src.app > logs/frontend_sanity_server.log 2>&1 &
  SERVER_PID=$!

  for _ in {1..15}; do
    if curl -s "$BASE_URL" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  echo "❌ Frontend sanity server failed to start on port ${PORT}"
  echo "❌ Check logs/frontend_sanity_server.log for details"
  return 1
}

start_frontend_server_if_needed

./scripts/check_frontend.sh "$PORT"