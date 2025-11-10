"""
E2E tests for Program Admin Dashboard workflow.

Tests the complete program admin dashboard experience including navigation,
panel filtering, and program-specific functionality.
"""

import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestProgramAdminDashboardWorkflow:
    """Test complete Program Admin dashboard workflow."""

    def test_logo_link_navigates_to_dashboard(
        self, program_admin_authenticated_page: Page
    ):
        """Test that logo link navigates to dashboard, not API endpoint."""
        page = program_admin_authenticated_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        logo_link = page.locator("a.navbar-brand")
        href = logo_link.get_attribute("href")
        assert href == "/dashboard", f"Expected /dashboard, got {href}"

        logo_link.click()
        page.wait_for_load_state("networkidle")
        expect(page).to_have_url("http://localhost:3002/dashboard")

    def test_dashboard_button_shows_all_panels(
        self, program_admin_authenticated_page: Page
    ):
        """Test that Dashboard button shows all panels."""
        page = program_admin_authenticated_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        dashboard_btn = page.locator("#dashboard-view-all")
        dashboard_btn.click()
        page.wait_for_timeout(500)

        # Verify all panels are visible
        expect(page.locator("#program-courses-panel")).to_be_visible()
        expect(page.locator("#program-faculty-panel")).to_be_visible()
        expect(page.locator("#program-clo-panel")).to_be_visible()
        expect(page.locator("#program-assessment-panel")).to_be_visible()
        expect(page.locator("#program-clo-audit-panel")).to_be_visible()
        expect(dashboard_btn).to_have_class(re.compile(".*active.*"))

    def test_courses_button_filters_to_courses_panel(
        self, program_admin_authenticated_page: Page
    ):
        """Test that Courses button shows only Courses panel."""
        page = program_admin_authenticated_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        courses_btn = page.locator("#dashboard-courses")
        courses_btn.click()
        page.wait_for_timeout(500)

        expect(page.locator("#program-courses-panel")).to_be_visible()
        expect(page.locator("#program-faculty-panel")).not_to_be_visible()
        expect(page.locator("#program-clo-panel")).not_to_be_visible()
        expect(courses_btn).to_have_class(re.compile(".*active.*"))

    def test_faculty_button_filters_to_faculty_panel(
        self, program_admin_authenticated_page: Page
    ):
        """Test that Faculty button shows only Faculty panel."""
        page = program_admin_authenticated_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        faculty_btn = page.locator("#dashboard-faculty")
        faculty_btn.click()
        page.wait_for_timeout(500)

        expect(page.locator("#program-courses-panel")).not_to_be_visible()
        expect(page.locator("#program-faculty-panel")).to_be_visible()
        expect(page.locator("#program-clo-panel")).not_to_be_visible()
        expect(faculty_btn).to_have_class(re.compile(".*active.*"))

    def test_clos_button_filters_to_clo_panel(
        self, program_admin_authenticated_page: Page
    ):
        """Test that CLOs button shows only CLO panel."""
        page = program_admin_authenticated_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        clos_btn = page.locator("#dashboard-clos")
        clos_btn.click()
        page.wait_for_timeout(500)

        expect(page.locator("#program-courses-panel")).not_to_be_visible()
        expect(page.locator("#program-faculty-panel")).not_to_be_visible()
        expect(page.locator("#program-clo-panel")).to_be_visible()
        expect(clos_btn).to_have_class(re.compile(".*active.*"))

    def test_navigation_buttons_toggle_active_state(
        self, program_admin_authenticated_page: Page
    ):
        """Test that navigation buttons properly toggle active state."""
        page = program_admin_authenticated_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        dashboard_btn = page.locator("#dashboard-view-all")
        courses_btn = page.locator("#dashboard-courses")
        faculty_btn = page.locator("#dashboard-faculty")
        clos_btn = page.locator("#dashboard-clos")

        # Click through each button and verify active states
        courses_btn.click()
        page.wait_for_timeout(300)
        expect(courses_btn).to_have_class(re.compile(".*active.*"))
        expect(dashboard_btn).not_to_have_class(re.compile(".*active.*"))

        faculty_btn.click()
        page.wait_for_timeout(300)
        expect(faculty_btn).to_have_class(re.compile(".*active.*"))
        expect(courses_btn).not_to_have_class(re.compile(".*active.*"))

        clos_btn.click()
        page.wait_for_timeout(300)
        expect(clos_btn).to_have_class(re.compile(".*active.*"))
        expect(faculty_btn).not_to_have_class(re.compile(".*active.*"))

        dashboard_btn.click()
        page.wait_for_timeout(300)
        expect(dashboard_btn).to_have_class(re.compile(".*active.*"))
        expect(clos_btn).not_to_have_class(re.compile(".*active.*"))
