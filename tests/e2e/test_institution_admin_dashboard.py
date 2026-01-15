"""
E2E tests for Institution Admin Dashboard workflow.

Tests the complete institution admin dashboard experience including navigation,
panel filtering, and institution-wide functionality.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.header_navigator import HeaderNavigator


@pytest.mark.e2e
class TestInstitutionAdminDashboardWorkflow:
    """Test the top-level Institution Admin dashboard experience."""

    def test_logo_link_navigates_to_dashboard(
        self, authenticated_institution_admin_page: Page
    ):
        page = authenticated_institution_admin_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        logo_link = page.locator("a.navbar-brand")
        href = logo_link.get_attribute("href")
        assert href == "/dashboard", f"Expected /dashboard, got {href}"

        logo_link.click()
        page.wait_for_load_state("networkidle")
        expect(page).to_have_url("http://localhost:3002/dashboard")

    def test_nav_items_reflect_dashboard_navigation(
        self, authenticated_institution_admin_page: Page
    ):
        page = authenticated_institution_admin_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        expected_nav = [
            "Dashboard",
            "Audit",
            "Assessments",
            "Outcomes",
            "Users",
            "Courses",
            "Offerings",
            "Sections",
        ]
        navigator = HeaderNavigator(page)
        labels = navigator.labels()
        assert labels[: len(expected_nav)] == expected_nav
