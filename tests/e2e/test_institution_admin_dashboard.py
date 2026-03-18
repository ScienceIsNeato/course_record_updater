"""
E2E tests for Institution Admin Dashboard workflow.

Tests the complete institution admin dashboard experience including navigation,
panel filtering, and institution-wide functionality.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL


@pytest.mark.e2e
class TestInstitutionAdminDashboardWorkflow:
    """Test the top-level Institution Admin dashboard experience."""

    def test_logo_link_navigates_to_dashboard(
        self, authenticated_institution_admin_page: Page
    ) -> None:
        page = authenticated_institution_admin_page
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")

        logo_link = page.locator("a.navbar-brand")
        href = logo_link.get_attribute("href")
        assert href == "/dashboard", f"Expected /dashboard, got {href}"

        logo_link.click()
        page.wait_for_load_state("networkidle")
        expect(page).to_have_url(f"{BASE_URL}/dashboard")

    def test_nav_items_reflect_dashboard_navigation(
        self, authenticated_institution_admin_page: Page
    ) -> None:
        page = authenticated_institution_admin_page
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")

        # Get nav items
        nav_items = page.locator("nav .nav-link").all()
        labels = [item.inner_text().strip() for item in nav_items]

        # These are the current nav items as of the latest UI
        expected_nav = ["Dashboard", "Audit", "Assessments", "Outcomes"]

        # Verify the navigation items match
        assert (
            labels[: len(expected_nav)] == expected_nav
        ), f"Expected nav items {expected_nav}, but got {labels[: len(expected_nav)]}"
