"""
E2E tests for Program Admin Dashboard workflow.

Tests the complete program admin dashboard experience including navigation,
panel filtering, and program-specific functionality.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.header_navigator import HeaderNavigator


@pytest.mark.e2e
class TestProgramAdminDashboardWorkflow:
    """Smoke test for the redesigned Program Admin dashboard."""

    def test_logo_link_navigates_to_dashboard(
        self, program_admin_authenticated_page: Page
    ):
        page = program_admin_authenticated_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        logo_link = page.locator("a.navbar-brand")
        href = logo_link.get_attribute("href")
        assert href == "/dashboard", f"Expected /dashboard, got {href}"

        logo_link.click()
        page.wait_for_load_state("networkidle")
        expect(page).to_have_url("http://localhost:3002/dashboard")

    def test_nav_links_reflect_institution_header(
        self, program_admin_authenticated_page: Page
    ):
        page = program_admin_authenticated_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        expected_nav = ["Dashboard", "Courses", "Faculty", "Outcomes"]
        navigator = HeaderNavigator(page)
        labels = navigator.labels()
        assert labels[: len(expected_nav)] == expected_nav
