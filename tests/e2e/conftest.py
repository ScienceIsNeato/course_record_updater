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
from playwright.sync_api import (
    Browser,
    BrowserContext,
)
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import (
    Page,
    Playwright,
)

# Import shared test utilities
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.services.password_service import PasswordService
from src.utils.constants import E2E_TEST_PORT
from tests.conftest import get_worker_id
from tests.test_credentials import (
    INSTITUTION_ADMIN_EMAIL,
    INSTITUTION_ADMIN_PASSWORD,
    PROGRAM_ADMIN_EMAIL,
    PROGRAM_ADMIN_PASSWORD,
    SITE_ADMIN_EMAIL,
    SITE_ADMIN_PASSWORD,
)

# E2E environment runs on dedicated port (worker-aware for parallel execution)


def get_worker_port():
    """Get port number for current worker (3002 + worker_id)"""
    worker_id = get_worker_id()
    if worker_id is None:
        return E2E_TEST_PORT  # Default to 3002 for serial execution
    return E2E_TEST_PORT + worker_id  # 3002, 3003, 3004, etc for parallel workers


BASE_URL = f"http://localhost:{get_worker_port()}"
# Use generic adapter test data (institution-agnostic)
TEST_DATA_DIR = Path(__file__).parent / "fixtures"
TEST_FILE = TEST_DATA_DIR / "generic_test_data.zip"


@pytest.fixture(scope="session", autouse=True)
def setup_worker_environment(tmp_path_factory):
    """
    Setup E2E environment with proper database isolation and server management.

    For SERIAL execution (no pytest-xdist):
    - Creates fresh E2E database
    - Seeds baseline test data
    - Starts dedicated Flask server
    - Cleans up after session

    For PARALLEL execution (pytest-xdist workers):
    - Each worker gets isolated database copy
    - Each worker gets dedicated Flask server on unique port
    """
    worker_id = get_worker_id()
    server_process = None
    worker_db = None
    worker_port = get_worker_port()

    # Import seeding utilities early
    import urllib.error
    import urllib.request

    if worker_id is None:
        # ==============================================
        # SERIAL EXECUTION - Full setup required
        # ==============================================
        print(f"\n🔧 E2E Setup: Configuring test environment on port {worker_port}")

        worker_db = "course_records_e2e.db"

        # Step 1: Create fresh database (remove stale state)
        for db_file in [worker_db, f"{worker_db}-shm", f"{worker_db}-wal"]:
            if os.path.exists(db_file):
                try:
                    os.remove(db_file)
                except Exception as e:
                    print(f"   ⚠️  Could not remove {db_file}: {e}")
        print(f"   ✓ Fresh database: {worker_db}")

        # Step 2: Seed baseline data
        # Run seed_db.py as subprocess to ensure clean import state
        seed_cmd = [
            sys.executable,
            "scripts/seed_db.py",
            "--env",
            "e2e",
            "--manifest",
            "tests/fixtures/e2e_seed_manifest.json",
        ]

        seed_result = subprocess.run(
            seed_cmd,
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
        )
        if seed_result.returncode != 0:
            print(f"   ❌ Database seeding failed: {seed_result.stderr}")
            raise RuntimeError("E2E database seeding failed")
        print(f"   ✓ Baseline data seeded")

        # Step 3: Start Flask server
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{worker_db}"
        env["DATABASE_TYPE"] = "sqlite"
        env["PORT"] = str(worker_port)
        env["BASE_URL"] = f"http://localhost:{worker_port}"
        env["ENV"] = "e2e"
        env["FLASK_ENV"] = "e2e"  # Prevents account lockout in PasswordService
        env["WTF_CSRF_ENABLED"] = "false"  # Disable CSRF for E2E tests
        env.pop("EMAIL_PROVIDER", None)  # Use Ethereal for E2E
        env["EMAIL_WHITELIST"] = (
            "*@ethereal.email,*@mocku.test,*@test.edu,*@test.com,*@test.local,*@example.com,*@loopclosertests.mailtrap.io,*@system.local"
        )

        server_log = open("server.log", "w")
        server_process = subprocess.Popen(
            [sys.executable, "-m", "src.app"],
            env=env,
            stdout=server_log,
            stderr=subprocess.STDOUT,
            cwd=os.getcwd(),
        )

        # Wait for server to be ready
        max_attempts = 30
        for attempt in range(max_attempts):
            # Check if process died
            if server_process.poll() is not None:
                # Process exited early
                raise RuntimeError(
                    f"Server process died immediately (Return Code: {server_process.returncode}). "
                    f"Port {worker_port} might be in use by a stale process. Check server.log."
                )

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
                    raise RuntimeError("E2E server failed to start")
                time.sleep(0.5)

    else:
        # ==============================================
        # PARALLEL EXECUTION - Worker-specific setup
        # ==============================================
        base_db = "course_records_e2e.db"
        worker_db = f"course_records_e2e_worker{worker_id}.db"

        print(f"\n🔧 Worker {worker_id}: Setting up environment on port {worker_port}")

        # Copy base E2E database to worker-specific copy
        # Copy base E2E database to worker-specific copy
        # CRITICAL: Must copy WAL/SHM files if they exist to capture all transactions
        if os.path.exists(base_db):
            for ext in ["", "-wal", "-shm"]:
                src_file = f"{base_db}{ext}"
                dst_file = f"{worker_db}{ext}"
                if os.path.exists(src_file):
                    shutil.copy2(src_file, dst_file)
                    print(f"   ✓ Database copied: {dst_file}")

            env = os.environ.copy()
            env["DATABASE_URL"] = f"sqlite:///{worker_db}"
            env["DATABASE_TYPE"] = "sqlite"
            env["PORT"] = str(worker_port)
            env["BASE_URL"] = f"http://localhost:{worker_port}"
            env["ENV"] = "test"
            env["WTF_CSRF_ENABLED"] = "true"
            env.pop("EMAIL_PROVIDER", None)
            env["EMAIL_WHITELIST"] = (
                "*@ethereal.email,*@mocku.test,*@test.edu,*@test.com,*@test.local,*@example.com,*@loopclosertests.mailtrap.io,*@system.local"
            )

            server_process = subprocess.Popen(
                [sys.executable, "-m", "src.app"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=os.getcwd(),
            )

            max_attempts = 30
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
        else:
            print(f"   ❌ Base database {base_db} not found - run seed_db.py first")
            raise RuntimeError(f"Base E2E database not found: {base_db}")

    yield

    # ==============================================
    # CLEANUP
    # ==============================================
    if worker_id is None:
        print(f"\n🧹 E2E Cleanup: Stopping server...")
    else:
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

    # Remove worker database (parallel mode only - keeps base for debugging)
    if worker_id is not None and worker_db and os.path.exists(worker_db):
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
                "--disable-crashpad",
                "--disable-crash-reporter",
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
                "--disable-crashpad",
                "--disable-crash-reporter",
                "--no-sandbox",
            ],
        }


@pytest.fixture(scope="session")
def browser(
    playwright: Playwright, browser_type_launch_args, pytestconfig
) -> Generator[Browser, None, None]:
    """Launch Playwright browser with graceful fallback when sandboxed."""

    # pytest-playwright registers --browser; default to chromium when absent
    browser_name = pytestconfig.getoption("--browser") or "chromium"
    if isinstance(browser_name, (list, tuple)):
        browser_name = browser_name[0]
    browser_type = getattr(playwright, browser_name)

    def _should_skip(message: str) -> bool:
        lowered = message.lower()
        return "permission denied (1100)" in lowered or "machport" in lowered

    try:
        browser_instance = browser_type.launch(**browser_type_launch_args)
    except PlaywrightError as exc:
        if _should_skip(str(exc)):
            pytest.skip(
                "Playwright browser launch is blocked by the macOS sandbox "
                "(Mach bootstrap permission denied). Skipping UI-driven e2e tests."
            )
        raise

    try:
        yield browser_instance
    finally:
        browser_instance.close()


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
    page.fill('input[name="email"]', INSTITUTION_ADMIN_EMAIL)
    page.fill('input[name="password"]', INSTITUTION_ADMIN_PASSWORD)
    page.click('button[type="submit"]')

    try:
        page.wait_for_url(f"{BASE_URL}/dashboard", timeout=10000)
        page.wait_for_load_state("networkidle")

        # Verify session is properly established with institution context
        # This prevents flaky tests where the session wasn't fully propagated
        page.wait_for_function(
            "window.currentUser && window.currentUser.institutionId && window.currentUser.institutionId.length > 0",
            timeout=15000,
        )

        return page
    except Exception as e:
        pytest.fail(f"Institution admin login failed: {str(e)}")


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
    page.fill('input[name="email"]', SITE_ADMIN_EMAIL)
    page.fill('input[name="password"]', SITE_ADMIN_PASSWORD)
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
    page.fill('input[name="email"]', INSTITUTION_ADMIN_EMAIL)
    page.fill('input[name="password"]', INSTITUTION_ADMIN_PASSWORD)
    page.click('button[type="submit"]')

    try:
        page.wait_for_url(f"{BASE_URL}/dashboard", timeout=10000)
        page.wait_for_load_state("networkidle")

        # Verify session is properly established with institution context
        page.wait_for_function(
            "window.currentUser && window.currentUser.institutionId && window.currentUser.institutionId.length > 0",
            timeout=15000,
        )

        return page
    except Exception as e:
        pytest.fail(f"Institution admin login failed: {str(e)}")


@pytest.fixture(scope="function")
def authenticated_program_admin_page(page: Page) -> Page:
    """
    Provides page with program admin session (MockU).
    """
    page.context.clear_cookies()
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")

    # Use Bob ProgramAdmin (or Lisa) from baseline seed
    # We use credentials from test_credentials which maps to Lisa, but role is same (Program Admin)
    # Note: seed_db.py creates 'bob.programadmin@mocku.test' and 'lisa.prog@mocku.test'
    # We use the imported constant for consistency.
    page.fill('input[name="email"]', PROGRAM_ADMIN_EMAIL)
    page.fill('input[name="password"]', PROGRAM_ADMIN_PASSWORD)
    page.click('button[type="submit"]')

    try:
        page.wait_for_url(f"{BASE_URL}/dashboard", timeout=10000)
        page.wait_for_load_state("networkidle")

        # Verify session is properly established
        page.wait_for_function(
            "window.currentUser && window.currentUser.institutionId && window.currentUser.institutionId.length > 0",
            timeout=15000,
        )

        return page
    except Exception as e:
        pytest.fail(f"Program admin login failed: {str(e)}")


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

    # Use CS program admin from baseline seed (DEFAULT_PASSWORD = InstitutionAdmin123!)
    page.fill('input[name="email"]', "bob.programadmin@mocku.test")
    page.fill('input[name="password"]', "InstitutionAdmin123!")
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
    CRITICAL: Must configure app to use the correct worker DB, as pytest process
    is separate from the running Flask server process.
    """
    from src.app import app

    # Determine correct DB for this worker (same logic as setup_worker_environment)
    worker_id = get_worker_id()
    if worker_id is not None:
        # Parallel mode: Use worker-specific DB
        worker_db = f"course_records_e2e_worker{worker_id}.db"
        # Ensure absolute path to avoid CWD ambiguity
        db_path = os.path.abspath(worker_db)
        db_url = f"sqlite:///{db_path}"
    else:
        # Serial mode: Use default E2E DB
        db_path = os.path.abspath("course_records_e2e.db")
        db_url = f"sqlite:///{db_path}"

    # Force reconfiguration of the app in this process
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url

    # We must push an app context so DB operations work
    with app.app_context():
        # Clear failed login attempts for common test accounts
        test_accounts = [
            "siteadmin@system.local",
            "sarah.admin@mocku.test",
            "mike.admin@riverside.edu",
            "admin@pactech.edu",
            "bob.programadmin@mocku.test",
            PROGRAM_ADMIN_EMAIL,
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
