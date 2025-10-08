"""
Pytest fixtures for E2E tests

Provides shared setup/teardown logic for browser automation tests including:
- Playwright browser configuration
- Authentication helpers
- Database backup/restore
- Test data management
"""

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Generator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Playwright

# Import database services for verification
from database_service import (
    get_active_terms,
    get_all_courses,
    get_all_sections,
    get_all_users,
)

# Import shared test credentials from root conftest
from tests.conftest import (
    INSTITUTION_ADMIN_EMAIL,
    INSTITUTION_ADMIN_PASSWORD,
    SITE_ADMIN_EMAIL,
    SITE_ADMIN_PASSWORD,
)

# Test configuration
# E2E environment runs on port 3002 (see run_uat.sh and .envrc)
BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:3002")
TEST_DATA_DIR = Path(__file__).parent.parent.parent / "research" / "CEI"
TEST_FILE = TEST_DATA_DIR / "2024FA_test_data.xlsx"


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args, pytestconfig):
    """
    Configure browser launch options for human-friendly watch mode.

    - In CI (headless): Fast execution, no slow-mo
    - With --headed: Shows browser, slow-mo 350ms for visibility
    - With --debug: Shows browser, pauses at each step (debugger mode)
    - Default (watch mode): Shows browser, slow-mo 350ms

    Usage:
        pytest tests/e2e/                    # Watch mode: visible, slow-mo 350
        pytest tests/e2e/ --headed           # Watch mode: visible, slow-mo 350
        pytest tests/e2e/ --headed --debug   # Debug mode: visible, pauses at steps
        HEADLESS=1 pytest tests/e2e/         # CI mode: fast, headless
    """
    config = {**browser_type_launch_args}

    # Check if we're in debug mode (pytest --pdb or custom --debug flag)
    debug_mode = pytestconfig.option.usepdb or os.getenv("PYTEST_DEBUG") == "1"

    # Check if explicitly headless (CI mode)
    explicit_headless = os.getenv("HEADLESS") == "1" or os.getenv("CI") == "true"

    if explicit_headless:
        # CI mode: fast, headless, no slow-mo
        config["headless"] = True
        config["slow_mo"] = 0
    elif debug_mode:
        # Debug mode: visible, very slow for inspection, devtools open
        config["headless"] = False
        config["slow_mo"] = 1000  # 1 second between actions for debugging
        config["devtools"] = True
    else:
        # Watch mode (default): visible with comfortable slow-mo
        config["headless"] = False
        config["slow_mo"] = 350  # 350ms between actions - human-readable speed

    return config


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context with sensible defaults for E2E testing."""
    config = {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
    }

    # Only record videos if SAVE_VIDEOS env var is set
    if os.getenv("SAVE_VIDEOS") == "1":
        config["record_video_dir"] = "test-results/videos"

    return config


@pytest.fixture(scope="function")
def context(
    browser: Browser, browser_context_args
) -> Generator[BrowserContext, None, None]:
    """Create a new browser context for each test (isolated cookies/storage)."""
    context = browser.new_context(**browser_context_args)
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """Create a new page for each test."""
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture(scope="function")
def csrf_token(page: Page) -> str:
    """
    Fixture that retrieves a CSRF token from the login page.

    Returns:
        CSRF token string for authenticated requests
    """
    # Navigate to login page to get CSRF token
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")

    # Extract CSRF token from hidden input
    csrf_token = page.input_value('input[name="csrf_token"]')

    if not csrf_token:
        raise Exception("Failed to extract CSRF token from login page")

    return csrf_token


@pytest.fixture(scope="function")
def authenticated_page(page: Page) -> Page:
    """
    Fixture that provides a page with authenticated session as institution admin.

    Properly handles CSRF token for secure authentication by submitting the actual
    login form (which automatically handles CSRF and session management).

    Usage:
        def test_something(authenticated_page):
            authenticated_page.goto(f"{BASE_URL}/dashboard")
            # Already logged in as sarah.admin@cei.edu
    """
    # Clear any existing session/cookies to ensure clean login
    page.context.clear_cookies()

    # Navigate to login page
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")

    # Fill and submit the actual login form (handles CSRF automatically)
    page.fill('input[name="email"]', INSTITUTION_ADMIN_EMAIL)
    page.fill('input[name="password"]', INSTITUTION_ADMIN_PASSWORD)

    # Submit form and wait for JavaScript to handle login and redirect
    page.click('button[type="submit"]')

    # Wait for either:
    # 1. Navigation to dashboard (success)
    # 2. Error message appears (failure)
    # 3. Timeout (something went wrong)
    try:
        # Wait for URL to change to dashboard (JavaScript redirect)
        # 2s timeout is appropriate now that bcrypt is fast in test environments
        page.wait_for_url(f"{BASE_URL}/dashboard", timeout=2000)
        return page
    except Exception:
        # Check if still on login page with error message
        current_url = page.url
        if "/login" in current_url:
            # Look for error message
            error_elements = page.query_selector_all(
                '.alert-danger, .error-message, [role="alert"]'
            )
            error_text = " | ".join(
                [el.text_content() for el in error_elements if el.text_content()]
            )

            # If no error message, check console for JS errors
            if not error_text:
                error_text = "No error message found. Check if JavaScript is executing."

            raise Exception(
                f"Login failed - still on login page after 10s. Errors: {error_text} URL: {current_url}"
            )


@pytest.fixture(scope="function")
def authenticated_site_admin_page(page: Page) -> Page:
    """
    Fixture that provides a page with authenticated session as site admin.

    Properly handles CSRF token for secure authentication by submitting the actual
    login form (which automatically handles CSRF and session management).

    Usage:
        def test_something(authenticated_site_admin_page):
            authenticated_site_admin_page.goto(f"{BASE_URL}/dashboard")
            # Already logged in as siteadmin@system.local
    """
    # Clear any existing session/cookies to ensure clean login
    page.context.clear_cookies()

    # Navigate to login page
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")

    # Fill and submit the actual login form (handles CSRF automatically)
    page.fill('input[name="email"]', SITE_ADMIN_EMAIL)
    page.fill('input[name="password"]', SITE_ADMIN_PASSWORD)

    # Submit form and wait for JavaScript to handle login and redirect
    page.click('button[type="submit"]')

    # Wait for URL to change to dashboard (JavaScript redirect)
    try:
        page.wait_for_url(f"{BASE_URL}/dashboard", timeout=2000)
        return page
    except Exception:
        # Check if still on login page with error message
        current_url = page.url
        if "/login" in current_url:
            # Look for error message
            error_elements = page.query_selector_all(
                '.alert-danger, .error-message, [role="alert"]'
            )
            error_text = " | ".join(
                [el.text_content() for el in error_elements if el.text_content()]
            )

            # If no error message, check console for JS errors
            if not error_text:
                error_text = "No error message found. Check if JavaScript is executing."

            raise Exception(
                f"Site admin login failed - still on login page after 2s. Errors: {error_text} URL: {current_url}"
            )


@pytest.fixture(scope="function")
def database_backup():
    """
    Backup database before test and provide restore capability.

    Usage:
        def test_destructive_operation(database_backup):
            # Test runs with backup available
            # Database automatically restored after test (on teardown)
    """
    db_path = Path("course_records.db")
    backup_path = Path("course_records_e2e_backup.db")

    # Backup current database
    if db_path.exists():
        shutil.copy2(db_path, backup_path)

    yield

    # Restore database after test
    if backup_path.exists():
        shutil.copy2(backup_path, db_path)
        backup_path.unlink()


@pytest.fixture(scope="function")
def database_baseline():
    """
    Placeholder fixture for database baseline (deprecated for E2E tests).

    E2E tests should verify via UI, not direct database queries.
    Use API calls or UI element counts instead.

    Returns empty dict for backward compatibility with existing tests.
    """
    return {}


@pytest.fixture(scope="session")
def server_running():
    """
    Verify application server is running and seed database before tests.

    This fixture runs once per test session to ensure the server is up
    and the database has test data (including the institution admin user).
    """
    import requests

    # Check server health
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code != 200:
            pytest.fail(
                f"Server health check failed with status {response.status_code}. "
                f"Is the server running on {BASE_URL}?"
            )
    except requests.exceptions.ConnectionError:
        pytest.fail(
            f"Cannot connect to server at {BASE_URL}. "
            f"Please start the server with './restart_server.sh' before running E2E tests."
        )
    except requests.exceptions.Timeout:
        pytest.fail(
            f"Server health check timed out at {BASE_URL}. "
            f"Server may be slow to respond."
        )

    # Database is seeded by run_uat.sh before server starts
    # No need to seed again here - just verify server is responding
    return True


@pytest.fixture(scope="function")
def test_data_file():
    """
    Verify test data file exists and return its path.

    Usage:
        def test_import(authenticated_page, test_data_file):
            page.set_input_files('input[type="file"]', str(test_data_file))
    """
    if not TEST_FILE.exists():
        pytest.skip(
            f"Test data file not found: {TEST_FILE}. "
            f"Please ensure research/CEI/2024FA_test_data.xlsx exists."
        )

    return TEST_FILE


# Helper functions for common E2E operations


@pytest.fixture(scope="function")
def ensure_multiple_institutions():
    """
    Fixture that ensures at least 2 institutions exist for multi-tenancy tests.

    Creates a temporary second institution if only 1 exists, and cleans it up after test.
    Returns tuple: (second_institution_id, cleanup_function)

    Usage:
        def test_something(ensure_multiple_institutions):
            second_inst_id, cleanup = ensure_multiple_institutions
            # Test multi-tenant isolation
            cleanup()  # Or let it auto-cleanup on teardown
    """
    from database_service import (
        create_new_institution,
        delete_institution,
        get_all_institutions,
    )

    institutions = get_all_institutions()
    created_temp_institution = False
    temp_institution_id = None

    # If we only have 1 institution, create a temporary second one
    if len(institutions) < 2:
        # Create minimal institution for testing
        temp_institution_id, _ = create_new_institution(
            institution_data={
                "name": "Temp Test Institution",
                "short_name": "TEMP",
                "address": "123 Test St",
            },
            admin_user_data={
                "email": "temp.admin@test.edu",
                "first_name": "Temp",
                "last_name": "Admin",
                "password": "TempAdmin123!",
            },
        )
        created_temp_institution = True

    # Return the second institution (either existing or newly created)
    institutions = get_all_institutions()
    second_institution = institutions[1] if len(institutions) > 1 else None

    def cleanup():
        """Clean up temporary institution if we created one"""
        if created_temp_institution and temp_institution_id:
            try:
                delete_institution(temp_institution_id)
            except Exception:
                pass  # Best effort cleanup

    yield (
        second_institution["institution_id"] if second_institution else None,
        cleanup,
    )

    # Auto-cleanup on teardown
    cleanup()


def wait_for_modal(page: Page, modal_selector: str = ".modal", timeout: int = 2000):
    """Wait for a modal to appear on the page."""
    page.wait_for_selector(modal_selector, state="visible", timeout=timeout)


def close_modal(page: Page, close_button_selector: str = ".modal button.close"):
    """Close a modal by clicking the close button."""
    page.click(close_button_selector)
    page.wait_for_selector(".modal", state="hidden", timeout=2000)


def wait_for_api_response(page: Page, url_pattern: str, timeout: int = 2000):
    """Wait for a specific API request to complete."""
    with page.expect_response(
        lambda response: url_pattern in response.url and response.status == 200,
        timeout=timeout,
    ) as response_info:
        return response_info.value


def take_screenshot(page: Page, name: str):
    """Save a screenshot for debugging (saved to test-results/)."""
    screenshot_dir = Path("test-results/screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=screenshot_dir / f"{name}.png")


def verify_no_console_errors(page: Page):
    """
    Check page console for JavaScript errors.

    Note: This requires setting up console message listeners before navigation.
    Best used with page.on("console", handler) in test setup.
    """
    errors = []

    def handle_console(msg):
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", handle_console)

    return errors
