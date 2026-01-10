#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  else
    echo "ERROR: Python is required to run the frontend check."
    exit 1
  fi
fi

if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: Node.js is required for JavaScript syntax validation."
  exit 1
fi

echo "[frontend] Verifying key routes and static assets"
PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" - <<'PY'
import sys

from src.app import app

app.testing = True
client = app.test_client()


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    sys.exit(1)


def assert_ok(path: str):
    response = client.get(path)
    if response.status_code != 200:
        fail(f"{path} returned {response.status_code}")
    return response


response = assert_ok("/login")
body = response.get_data(as_text=True)
for marker in ('id="loginForm"', 'id="email"', 'id="password"'):
    if marker not in body:
        fail(f"{marker} missing from /login HTML")

response = assert_ok("/health")
data = response.get_json(silent=True) or {}
if data.get("status") != "ok" or data.get("ready") is not True:
    fail(f"/health returned unexpected payload: {data}")

for path in (
    "/static/style.css",
    "/static/auth.js",
    "/static/script.js",
    "/static/images/loopcloser_wordmark.png",
):
    response = assert_ok(path)
    if not response.data:
        fail(f"{path} returned empty content")

print("[frontend] Flask checks passed")
PY

echo "[frontend] Validating JavaScript syntax"
while IFS= read -r -d '' js_file; do
  node --check "$js_file" >/dev/null
done < <(find "$ROOT_DIR/static" -maxdepth 1 -type f -name "*.js" -print0)

echo "[frontend] Frontend check passed"
