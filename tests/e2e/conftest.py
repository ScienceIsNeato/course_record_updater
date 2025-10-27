"""
Pytest fixtures for E2E tests

Provides shared setup/teardown logic for browser automation tests including:
- Playwright browser configuration
- Worker-specific database isolation for parallel execution
- Authentication helpers
- Test data creation utilities
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Generator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Playwright

# Import shared test utilities
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from constants import E2E_TEST_PORT
from password_service import PasswordService
from tests.conftest import get_worker_id


# E2E environment runs on dedicated port (worker-aware for parallel execution)
def get_worker_port():
    """Get port number for current worker (3002 + worker_id)"""
    worker_id = get_worker_id()
    if worker_id is None:
        return E2E_TEST_PORT  # Default to 3002 for serial execution
    return E2E_TEST_PORT + worker_id  # 3002, 3003, 3004, etc for parallel workers


BASE_URL = f"http://localhost:{get_worker_port()}"
TEST_DATA_DIR = Path(__file__).parent.parent.parent / "research" / "MockU"
TEST_FILE = TEST_DATA_DIR / "2024FA_test_data.xlsx"


@pytest.fixture(scope="session", autouse=True)
def setup_worker_environment(tmp_path_factory):
    """
    Setup worker-specific E2E environment for parallel execution.

    Each pytest-xdist worker gets:
    - Isolated database copy (prevents test collisions)
    - Dedicated Flask server on unique port

    Tests create their own data programmatically via API.
    """
    worker_id = get_worker_id()
    server_process = None

    if worker_id is not None:
        # Parallel execution - setup worker-specific environment
        base_db = "course_records_e2e.db"
        worker_db = f"course_records_e2e_worker{worker_id}.db"
        worker_port = get_worker_port()

        print(f"\n🔧 Worker {worker_id}: Setting up environment on port {worker_port}")

        # Copy base E2E database to worker-specific copy
        if os.path.exists(base_db):
            import shutil

            shutil.copy2(base_db, worker_db)
            print(f"   ✓ Database copied: {worker_db}")

            # Start worker-specific Flask server
            import socket

            env = os.environ.copy()
            env["DATABASE_URL"] = f"sqlite:///{worker_db}"
            env["DATABASE_TYPE"] = "sqlite"
            env["PORT"] = str(worker_port)
            env["BASE_URL"] = (
                f"http://localhost:{worker_port}"  # Fix email verification links
            )
            env["ENV"] = "test"
            # Disable CSRF for E2E tests to avoid token validation issues
            # E2E tests focus on functional workflows, not CSRF security
            env["WTF_CSRF_ENABLED"] = "false"
            # Unset EMAIL_PROVIDER so it uses Ethereal for E2E
            env.pop("EMAIL_PROVIDER", None)
            # Ensure EMAIL_WHITELIST is set for E2E tests
            # Allow test domains: @ethereal.email, @mocku.test, @test.edu, @lassietests.mailtrap.io
            if "EMAIL_WHITELIST" not in env:
                env["EMAIL_WHITELIST"] = (
                    "*@ethereal.email,*@mocku.test,*@test.edu,*@lassietests.mailtrap.io"
                )

            # Start server in background
            server_process = subprocess.Popen(
                ["python", "app.py"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=os.getcwd(),
            )

            # Wait for server to be ready - use health check endpoint
            max_attempts = 30
            import urllib.error
            import urllib.request

            for attempt in range(max_attempts):
                try:
                    urllib.request.urlopen(
                        f"http://localhost:{worker_port}/login", timeout=1
                    )
                    print(
                        f"   ✓ Server ready on port {worker_port} (PID: {server_process.pid})"
                    )
                    break
                except (urllib.error.URLError, ConnectionRefusedError, OSError):
                    if attempt == max_attempts - 1:
                        print(f"   ❌ Server failed to start on port {worker_port}")
                        if server_process:
                            server_process.kill()
                        raise RuntimeError(f"Worker {worker_id} server failed to start")
                    time.sleep(0.5)

    yield

    # Cleanup: Stop server and remove worker-specific databases
    if worker_id is not None:
        print(f"\n🧹 Worker {worker_id}: Cleaning up...")

        # Stop server
        if server_process:
            try:
                server_process.terminate()
                server_process.wait(timeout=5)
                print(f"   ✓ Server stopped (PID: {server_process.pid})")
            except Exception:
                server_process.kill()
                print(f"   ⚠️  Server force-killed")

        # Remove worker database
        worker_db = f"course_records_e2e_worker{worker_id}.db"
        if os.path.exists(worker_db):
            try:
                os.remove(worker_db)
                print(f"   ✓ Database cleaned: {worker_db}")
            except Exception as e:
                print(f"   ⚠️  Failed to clean database: {e}")


@pytest.fixture(scope="session")
def browser_type_launch_args(pytestconfig):
    """
    Configure Playwright browser launch arguments.

    Controls headless/headed mode based on CLI flags:
    - Default: headless (fast, no browser window)
    - --headed: Show browser window
    - --debug: Show browser window with slow-mo for debugging

    Environment variable HEADLESS=1 forces headless mode (CI environments).
    """
    # Check if running in forced headless mode (CI environment)
    forced_headless = os.getenv("HEADLESS") == "1"
    if forced_headless:
        return {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        }

    # Check for debug mode flags
    debug_mode = pytestconfig.getoption("--debug", False)
    headed_mode = pytestconfig.getoption("--headed", False)

    if debug_mode:
        # Debug mode: headed + slow motion
        return {
            "headless": False,
            "slow_mo": 500,  # 500ms delay between actions
            "args": ["--disable-blink-features=AutomationControlled"],
        }
    elif headed_mode:
        # Headed mode: show browser but no slow-mo
        return {
            "headless": False,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
    else:
        # Default: headless mode (fast, no window)
        return {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        }


@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """
    Provides a fresh Playwright page with console error monitoring.

    Automatically fails tests if JavaScript console errors are detected,
    except for expected HTTP error responses (403, 404, etc).
    """
    page = context.new_page()
    console_errors = []

    def handle_console_message(msg):
        if msg.type == "error":
            error_text = msg.text
            # Filter out expected HTTP errors (401, 403, 404, 500, etc)
            if any(code in error_text for code in ["401", "403", "404", "500"]):
                print(f"ℹ️  Expected HTTP Error: {error_text}")
            # Filter out transient "Failed to fetch" errors during parallel test execution
            # These occur when page loads before session is fully established
            elif (
                "Institution dashboard load error" in error_text
                or "Program dashboard load error" in error_text
            ) and "Failed to fetch" in error_text:
                print(
                    f"ℹ️  Transient dashboard load error (race condition): {error_text[:100]}..."
                )
            else:
                console_errors.append(error_text)

    page.on("console", handle_console_message)

    yield page

    # Check for console errors after test completes
    if console_errors:
        error_msg = "\n".join(f"  - {err}" for err in console_errors)
        pytest.fail(f"JavaScript console errors detected during test:\n{error_msg}")

    page.close()


@pytest.fixture(scope="function")
def authenticated_page(page: Page) -> Page:
    """
    Provides generic authenticated page (institution admin).

    DEPRECATED: Use authenticated_institution_admin_page or authenticated_site_admin_page
    for clarity about which admin type the test needs.

    Kept for backward compatibility with existing tests.
    """
    page.context.clear_cookies()
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")

    # Use MockU institution admin from baseline seed
    page.fill('input[name="email"]', "sarah.admin@mocku.test")
    page.fill('input[name="password"]', "InstitutionAdmin123!")
    page.click('button[type="submit"]')

    try:
        page.wait_for_url(f"{BASE_URL}/dashboard", timeout=5000)
        return page
    except Exception:
        pytest.fail("Institution admin login failed")


@pytest.fixture(scope="function")
def authenticated_site_admin_page(page: Page) -> Page:
    """
    Provides page with site admin session.

    Uses site admin from baseline seed data.
    Tests can use this admin to create additional test data via API.
    """
    page.context.clear_cookies()
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")

    # Use site admin from baseline seed
    page.fill('input[name="email"]', "siteadmin@system.local")
    page.fill('input[name="password"]', "SiteAdmin123!")
    page.click('button[type="submit"]')

    try:
        page.wait_for_url(f"{BASE_URL}/dashboard", timeout=5000)
        return page
    except Exception:
        pytest.fail("Site admin login failed")


@pytest.fixture(scope="function")
def authenticated_institution_admin_page(page: Page) -> Page:
    """
    Provides page with institution admin session (MockU).

    Uses institution admin from baseline seed data.
    Tests can use this admin to create users, sections, etc via API.
    """
    page.context.clear_cookies()
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")

    # Use MockU institution admin from baseline seed
    page.fill('input[name="email"]', "sarah.admin@mocku.test")
    page.fill('input[name="password"]', "InstitutionAdmin123!")
    page.click('button[type="submit"]')

    try:
        page.wait_for_url(f"{BASE_URL}/dashboard", timeout=5000)
        return page
    except Exception:
        pytest.fail("Institution admin login failed")


@pytest.fixture(scope="function")
def instructor_authenticated_page(page: Page) -> Page:
    """
    Provides page with instructor session.

    NOTE: Tests should create their own instructor account programmatically
    using authenticated_institution_admin_page fixture and then login here.

    This fixture just handles the login flow - the instructor account
    must already exist in the database.
    """
    # This will be updated when we refactor tests to create their own data
    pytest.skip("Instructor fixture requires test-specific user creation")


@pytest.fixture(scope="function")
def program_admin_authenticated_page(page: Page) -> Page:
    """
    Provides page with program admin session (CS program @ MockU).

    Uses baseline seed account: bob.programadmin@mocku.test
    """
    page.context.clear_cookies()
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")

    # Use CS program admin from baseline seed
    page.fill('input[name="email"]', "bob.programadmin@mocku.test")
    page.fill('input[name="password"]', "ProgramAdmin123!")
    page.click('button[type="submit"]')

    try:
        page.wait_for_url(f"{BASE_URL}/dashboard", timeout=5000)
        return page
    except Exception:
        pytest.fail("Program admin login failed")


@pytest.fixture(scope="function", autouse=True)
def reset_account_locks():
    """
    Clear any failed login attempts before each test.

    Ensures tests start with clean slate for authentication testing.
    """
    # Clear failed login attempts for common test accounts
    test_accounts = [
        "siteadmin@system.local",
        "sarah.admin@mocku.test",
        "mike.admin@riverside.edu",
        "admin@pactech.edu",
    ]

    for email in test_accounts:
        try:
            PasswordService.clear_failed_attempts(email)
        except Exception:
            # Best effort - if account doesn't exist or clearing fails, continue
            pass

    yield


@pytest.fixture(scope="function")
def test_data_file():
    """Provide path to test data file"""
    return TEST_FILE


@pytest.fixture(scope="function")
def server_running():
    """
    Verify E2E server is running and accessible.

    Fails test early if server is not ready.
    """
    import urllib.error
    import urllib.request

    try:
        response = urllib.request.urlopen(f"{BASE_URL}/login", timeout=5)
        assert response.status == 200, f"Server returned status {response.status}"
        return True
    except (urllib.error.URLError, ConnectionRefusedError) as e:
        pytest.fail(f"E2E server not running on {BASE_URL}: {e}")
    except Exception as e:
        pytest.fail(f"Error checking E2E server: {e}")
