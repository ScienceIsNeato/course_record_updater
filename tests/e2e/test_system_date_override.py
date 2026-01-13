import logging
from datetime import datetime, timedelta

from playwright.sync_api import Page, expect

from src.utils.constants import DATE_OVERRIDE_BANNER_PREFIX
from tests.e2e.conftest import BASE_URL

# Tests for System Date Override functionality (Time Travel)
# Uses 'authenticated_site_admin_page' fixture from conftest.py

logger = logging.getLogger(__name__)


def test_system_date_override_flow(authenticated_site_admin_page: Page):
    """
    Test the full system date override flow:
    1. Login as Site Admin (handled by fixture)
    2. Go to Profile and Set Override to future date.
    3. Verify Dashboard shows updated metadata (via UI toast/banner).
    4. Reset Override.
    """
    page = authenticated_site_admin_page

    # 1. Login handled by fixture

    # 2. Go to Profile and Set Override
    page.goto(f"{BASE_URL}/profile")
    page.wait_for_load_state("networkidle")

    # Calculate a future date (e.g. tomorrow + 1 year)
    future_date = datetime.now() + timedelta(days=365)
    # Format for input type="datetime-local": YYYY-MM-DDTHH:MM
    future_date_str = future_date.strftime("%Y-%m-%dT12:00")

    # Fill override
    page.fill("#systemDateOverride", future_date_str)

    # Click set
    # Note: Javascript reload might happen, so we wait for that.
    with page.expect_navigation():
        page.click("#setDateOverrideBtn")

    page.wait_for_load_state("networkidle")

    # Verify banner
    expect(page.locator("#activeOverrideDisplay")).to_be_visible()
    expect(page.locator("#activeOverrideDisplay")).to_contain_text(
        DATE_OVERRIDE_BANNER_PREFIX
    )

    # Verify date in banner matches roughly (month/day/year)
    expected_date_fragment = future_date.strftime("%B %d, %Y")
    expect(page.locator("#activeOverrideDisplay")).to_contain_text(
        expected_date_fragment
    )

    # 3. Verify Dashboard behavior (Phase 1 checks)
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")

    # As we haven't implemented visible "System Date" on dashboard yet,
    # we just verify the page loads without error under time travel.
    expect(page.locator("h1")).to_contain_text("Dashboard")

    # 4. Reset Override
    page.goto(f"{BASE_URL}/profile")
    with page.expect_navigation():
        page.click("#clearDateOverrideBtn")

    page.wait_for_load_state("networkidle")
    expect(page.locator("#activeOverrideDisplay")).to_be_hidden()
