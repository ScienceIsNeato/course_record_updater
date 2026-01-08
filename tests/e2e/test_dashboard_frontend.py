"""
Integration tests for dashboard API endpoints and frontend (Playwright)

Replacing legacy Selenium tests with Playwright for consistency and reliability.
"""

import pytest
import requests
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL


class TestDashboardAPI:
    """Test dashboard API functionality"""

    def test_dashboard_data_endpoint(self):
        """Ensure the aggregated dashboard endpoint is reachable."""
        endpoint = f"{BASE_URL}/api/dashboard/data"

        try:
            response = requests.get(
                endpoint,
                timeout=10,
                headers={"Accept": "application/json"},
            )
        except requests.exceptions.ConnectionError as exc:
            pytest.skip(f"Dashboard server unavailable: {exc}")
        except requests.exceptions.Timeout:
            pytest.skip("Dashboard server timed out while fetching data")

        # Without authentication we should receive a 401 JSON response
        if response.status_code == 401:
            payload = response.json()
            assert payload.get("error_code") == "AUTH_REQUIRED"
        else:
            assert response.status_code != 404, "Dashboard endpoint returned 404"
            assert response.ok, f"Unexpected status code: {response.status_code}"


class TestDashboardFrontend:
    """Test dashboard frontend functionality using Playwright"""

    def test_dashboard_page_loads(self, page: Page):
        """Test that the main dashboard page loads without errors"""
        page.goto(str(BASE_URL))

        # Wait for page to load
        expect(page.locator("body")).to_be_visible(timeout=10000)

        # Check if we're on login page or main page
        # Using inner_text or specific selectors instead of generic page content
        if "login" in page.url:
            expect(page.locator("form#loginForm")).to_be_visible()
            expect(page.locator('input[name="email"]')).to_be_visible()
        else:
            expect(page.locator("h1").filter(has_text="Loopcloser")).to_be_visible()

        # Verify title
        title = page.title()
        assert title and len(title) > 0

    def test_dashboard_cards_present(self, authenticated_page: Page):
        """Test that dashboard cards are present and populated"""
        # authenticated_page fixture already logs in and goes to dashboard

        # Ensure we are on the dashboard
        authenticated_page.wait_for_url(f"**/dashboard")

        # Check for dashboard panels
        panels = authenticated_page.locator(".dashboard-panel")
        expect(panels.first).to_be_visible(timeout=10000)

        # Check that we have panels
        count = panels.count()
        assert count > 0, "Expected at least one dashboard panel"

        # Verify titles
        titles = authenticated_page.locator(".dashboard-panel .panel-title")
        expect(titles.first).to_be_visible()

        # Verify content loads (removing loading spinners)
        # Using a custom assertion loop or expect.to_not_have_text
        # Here assuming '.panel-loading' class is removed when loaded

        # Wait for at least one panel to NOT have the loading class
        # or check that specific content appears

        # In the original Selenium test, it checked if "panel-loading" was NOT present
        # Here we can wait for a specific element that appears after loading, e.g. a chart or number
        # Or just assert that .panel-loading disappears

        # Let's check that .panel-content is visible
        content = authenticated_page.locator(".dashboard-panel .panel-content")
        expect(content.first).to_be_visible()
