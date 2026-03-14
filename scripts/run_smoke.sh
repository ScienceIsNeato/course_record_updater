#!/bin/bash

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

TEST_PORT="${LOOPCLOSER_DEFAULT_PORT_SMOKE:-3003}"
SERVER_PID=""
SMOKE_DB_PATH="${PROJECT_ROOT}/course_records_smoke.db"
SMOKE_DATABASE_URL="sqlite:///${SMOKE_DB_PATH}"
SMOKE_SESSION_FILE="${PROJECT_ROOT}/.tmp/smoke_session_cookies.json"

stop_test_server() {
  if [[ -n "$SERVER_PID" ]]; then
    echo -e "${BLUE}🛑 Stopping smoke server PID $SERVER_PID...${NC}"
    kill "$SERVER_PID" 2>/dev/null || true
    for _ in {1..10}; do
      if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        break
      fi
      sleep 1
    done
    kill -9 "$SERVER_PID" 2>/dev/null || true
  else
    pkill -f "python.*src.app" 2>/dev/null || true
  fi
  rm -f logs/server_smoke.pid
}

trap stop_test_server EXIT

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo -e "${YELLOW}⚠️  Virtual environment not active, activating...${NC}"
  if [[ -f "venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
  else
    echo -e "${RED}❌ Virtual environment not found at venv/bin/activate${NC}"
    exit 1
  fi
fi

if [[ -f ".envrc" ]]; then
  # shellcheck disable=SC1091
  source .envrc
elif [[ -f ".envrc.template" ]]; then
  # shellcheck disable=SC1091
  source .envrc.template
fi

export APP_ENV="smoke"
export ENV="test"
export DATABASE_TYPE="sqlite"
export DATABASE_URL="$SMOKE_DATABASE_URL"
export DATABASE_URL_SMOKE="$SMOKE_DATABASE_URL"
export BASE_URL="http://localhost:${TEST_PORT}"
export SMOKE_SESSION_FILE="$SMOKE_SESSION_FILE"
export SITE_ADMIN_PASSWORD="${SITE_ADMIN_PASSWORD:-SiteAdmin123!}"
export SMOKE_ADMIN_EMAIL="siteadmin@system.local"
export SMOKE_ADMIN_PASSWORD="$SITE_ADMIN_PASSWORD"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  LoopCloser - Smoke Runner${NC}"
echo -e "${BLUE}============================================${NC}"

mkdir -p logs .tmp

check_chrome() {
  if command -v google-chrome >/dev/null 2>&1; then
    return 0
  elif command -v chromium-browser >/dev/null 2>&1; then
    return 0
  elif command -v chromium >/dev/null 2>&1; then
    return 0
  elif [[ -f "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]]; then
    return 0
  elif [[ -f "/Applications/Chromium.app/Contents/MacOS/Chromium" ]]; then
    return 0
  elif [[ -f "/usr/bin/google-chrome-stable" ]]; then
    return 0
  elif [[ -f "/usr/bin/google-chrome" ]]; then
    return 0
  fi

  echo -e "${RED}❌ Chrome/Chromium not found. Please install Chrome or Chromium for smoke tests${NC}"
  return 1
}

start_test_server() {
  echo -e "${BLUE}🚀 Starting smoke server...${NC}"
  if ./scripts/restart_server.sh smoke; then
    sleep 2
    SERVER_PID="$(pgrep -f "python.*src.app" | head -1)"
    echo -e "${GREEN}✅ Smoke server started successfully${NC}"
    return 0
  fi

  echo -e "${RED}❌ Smoke server failed to start${NC}"
  return 1
}

run_smoke_tests() {
  echo -e "${BLUE}🧪 Running smoke tests...${NC}"
  export TEST_PORT="$TEST_PORT"

  python - <<'PY'
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(options=options)
driver.quit()
print('✅ Selenium WebDriver setup verified')
PY

  python scripts/check_smoke_seeded_data.py
  pytest tests/smoke/test_smoke.py -k "test_api_health or test_basic_authentication_flow" -v --tb=short
}

warm_login_session() {
  echo -e "${BLUE}🔐 Priming smoke login flow...${NC}"
  python - <<'PY'
import json
import os
import re

import requests

base_url = os.environ["BASE_URL"]
email = os.environ["SMOKE_ADMIN_EMAIL"]
password = os.environ["SMOKE_ADMIN_PASSWORD"]

session = requests.Session()
login_page = session.get(f"{base_url}/login", timeout=10)
csrf_match = re.search(
    r'name="csrf_token" value="([^"]+)"', login_page.text, re.IGNORECASE
)
meta_match = re.search(
    r'name="csrf-token" content="([^"]+)"', login_page.text, re.IGNORECASE
)
csrf_token = csrf_match.group(1) if csrf_match else meta_match.group(1) if meta_match else None
if not csrf_token:
    raise SystemExit("Smoke preflight could not find CSRF token")

response = session.post(
    f"{base_url}/api/auth/login",
    json={"email": email, "password": password, "remember_me": False},
    headers={
        "Content-Type": "application/json",
        "X-CSRFToken": csrf_token,
        "Referer": f"{base_url}/login",
    },
    allow_redirects=True,
    timeout=10,
)
if response.status_code != 200:
    raise SystemExit(
        f"Smoke preflight login failed: {response.status_code} {response.text[:300]}"
    )

with open(os.environ["SMOKE_SESSION_FILE"], "w", encoding="utf-8") as handle:
  json.dump(requests.utils.dict_from_cookiejar(session.cookies), handle)

print("✅ Smoke preflight login succeeded")
PY
}

check_chrome

echo -e "${BLUE}🧹 Ensuring clean state before seeding...${NC}"
pkill -f "python.*src.app" 2>/dev/null || true
sleep 1

echo -e "${BLUE}🌱 Seeding smoke database from manifest...${NC}"
python scripts/seed_db.py --demo --clear --env smoke --manifest tests/fixtures/smoke_manifest.json

echo -e "${BLUE}🔧 Normalizing seeded smoke admin account...${NC}"
python - <<'PY'
import os

from src.database import database_service
from src.models.models import User
from src.services.password_service import PasswordService
from src.utils.constants import SITE_ADMIN_INSTITUTION_ID

email = os.environ["SMOKE_ADMIN_EMAIL"]
password = os.environ["SMOKE_ADMIN_PASSWORD"]

database_service.refresh_connection()
user = database_service.get_user_by_email(email)
password_hash = PasswordService.hash_password(password)

if user:
  database_service.update_user(
    user["user_id"],
    {
      "password_hash": password_hash,
      "account_status": "active",
      "email_verified": True,
    },
  )
else:
  schema = User.create_schema(
    email=email,
    first_name="Smoke",
    last_name="Admin",
    role="site_admin",
    institution_id=str(SITE_ADMIN_INSTITUTION_ID),
    password_hash=password_hash,
    account_status="active",
  )
  schema["email_verified"] = True
  database_service.create_user(schema)

print(f"✅ Normalized smoke admin account: {email}")
PY

start_test_server
sleep 2
run_smoke_tests

echo -e "${GREEN}🎉 Smoke tests completed successfully${NC}"