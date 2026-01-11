"""
E2E tests for Site Admin Dashboard workflow.

Tests the complete site admin dashboard experience including navigation
and site-wide administration functionality.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.header_navigator import HeaderNavigator


@pytest.mark.e2e
class TestSiteAdminDashboardWorkflow:
    """Test complete Site Admin dashboard workflow."""

    def test_logo_link_navigates_to_dashboard(
        self, authenticated_site_admin_page: Page
    ):
        """Test that logo link navigates to dashboard, not API endpoint."""
        page = authenticated_site_admin_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        logo_link = page.locator("a.navbar-brand")
        href = logo_link.get_attribute("href")
        assert href == "/dashboard", f"Expected /dashboard, got {href}"

        logo_link.click()
        page.wait_for_load_state("networkidle")
        expect(page).to_have_url("http://localhost:3002/dashboard")

    def test_users_link_navigates_to_admin_users(
        self, authenticated_site_admin_page: Page
    ):
        """Test that Users button navigates to /admin/users."""
        page = authenticated_site_admin_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        navigator = HeaderNavigator(page)
        users_link = navigator.get_link("Users")
        expect(users_link).to_be_visible()

        href = users_link.get_attribute("href")
        assert href == "/admin/users", f"Expected /admin/users, got {href}"

        users_link.click()
        page.wait_for_load_state("networkidle")
        expect(page).to_have_url("http://localhost:3002/admin/users")

    def test_institutions_button_exists(self, authenticated_site_admin_page: Page):
        """Test that Institutions button exists (planned feature)."""
        page = authenticated_site_admin_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        navigator = HeaderNavigator(page)
        institutions_btn = navigator.get_link("Institutions")
        expect(institutions_btn).to_be_visible()
        expect(institutions_btn).to_contain_text("Institutions")

    def test_system_button_exists(self, authenticated_site_admin_page: Page):
        """Test that System button exists (planned feature)."""
        page = authenticated_site_admin_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        navigator = HeaderNavigator(page)
        system_btn = navigator.get_link("System")
        expect(system_btn).to_be_visible()
        expect(system_btn).to_contain_text("System")
