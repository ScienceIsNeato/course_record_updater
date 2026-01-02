"""
E2E tests for Institution Admin Dashboard workflow.

Tests the complete institution admin dashboard experience including navigation,
panel filtering, and institution-wide functionality.
"""

import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestInstitutionAdminDashboardWorkflow:
    """Test complete Institution Admin dashboard workflow."""

    def test_logo_link_navigates_to_dashboard(
        self, authenticated_institution_admin_page: Page
    ):
        """Test that logo link navigates to dashboard, not API endpoint."""
        page = authenticated_institution_admin_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        logo_link = page.locator("a.navbar-brand")
        href = logo_link.get_attribute("href")
        assert href == "/dashboard", f"Expected /dashboard, got {href}"

        logo_link.click()
        page.wait_for_load_state("networkidle")
        expect(page).to_have_url("http://localhost:3002/dashboard")

    @pytest.mark.skip(
        reason="Institution admin dashboard uses page-link navigation, not button-based panel filtering"
    )
    def test_dashboard_button_shows_all_panels(
        self, authenticated_institution_admin_page: Page
    ):
        """Test that Dashboard button shows all panels."""
        page = authenticated_institution_admin_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        dashboard_btn = page.locator("#dashboard-view-all")
        dashboard_btn.click()
        page.wait_for_timeout(500)

        # Verify all panels are visible
        expect(page.locator("#institution-program-panel")).to_be_visible()
        expect(page.locator("#institution-course-panel")).to_be_visible()
        expect(page.locator("#institution-faculty-panel")).to_be_visible()
        expect(page.locator("#institution-sections-panel")).to_be_visible()
        expect(page.locator("#institution-outcome-panel")).to_be_visible()
        expect(dashboard_btn).to_have_class(re.compile(".*active.*"))

    @pytest.mark.skip(
        reason="Institution admin dashboard uses page-link navigation, not button-based panel filtering"
    )
    def test_programs_button_filters_to_program_panels(
        self, authenticated_institution_admin_page: Page
    ):
        """Test that Programs button shows program-related panels."""
        page = authenticated_institution_admin_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        programs_btn = page.locator("#dashboard-programs")
        programs_btn.click()
        page.wait_for_timeout(500)

        expect(page.locator("#institution-program-panel")).to_be_visible()
        expect(page.locator("#institution-course-panel")).to_be_visible()
        expect(page.locator("#institution-faculty-panel")).not_to_be_visible()
        expect(page.locator("#institution-outcome-panel")).not_to_be_visible()
        expect(programs_btn).to_have_class(re.compile(".*active.*"))

    @pytest.mark.skip(
        reason="Institution admin dashboard uses page-link navigation, not button-based panel filtering"
    )
    def test_faculty_button_filters_to_faculty_panels(
        self, authenticated_institution_admin_page: Page
    ):
        """Test that Faculty button shows faculty-related panels."""
        page = authenticated_institution_admin_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        faculty_btn = page.locator("#dashboard-faculty")
        faculty_btn.click()
        page.wait_for_timeout(500)

        expect(page.locator("#institution-program-panel")).not_to_be_visible()
        expect(page.locator("#institution-faculty-panel")).to_be_visible()
        expect(page.locator("#institution-sections-panel")).to_be_visible()
        expect(page.locator("#institution-outcome-panel")).not_to_be_visible()
        expect(faculty_btn).to_have_class(re.compile(".*active.*"))

    @pytest.mark.skip(
        reason="Institution admin dashboard uses page-link navigation, not button-based panel filtering"
    )
    def test_outcomes_button_filters_to_outcome_panels(
        self, authenticated_institution_admin_page: Page
    ):
        """Test that Outcomes button shows outcome-related panels."""
        page = authenticated_institution_admin_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        outcomes_btn = page.locator("#dashboard-outcomes")
        outcomes_btn.click()
        page.wait_for_timeout(500)

        expect(page.locator("#institution-program-panel")).not_to_be_visible()
        expect(page.locator("#institution-faculty-panel")).not_to_be_visible()
        expect(page.locator("#institution-outcome-panel")).to_be_visible()
        expect(page.locator("#institution-assessment-panel")).to_be_visible()
        expect(page.locator("#institution-clo-audit-panel")).to_be_visible()
        expect(outcomes_btn).to_have_class(re.compile(".*active.*"))

    @pytest.mark.skip(
        reason="Institution admin dashboard uses page-link navigation, not button-based panel filtering"
    )
    def test_navigation_buttons_toggle_active_state(
        self, authenticated_institution_admin_page: Page
    ):
        """Test that navigation buttons properly toggle active state."""
        page = authenticated_institution_admin_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        dashboard_btn = page.locator("#dashboard-view-all")
        programs_btn = page.locator("#dashboard-programs")
        faculty_btn = page.locator("#dashboard-faculty")
        outcomes_btn = page.locator("#dashboard-outcomes")

        # Click through each button and verify active states
        programs_btn.click()
        page.wait_for_timeout(300)
        expect(programs_btn).to_have_class(re.compile(".*active.*"))
        expect(dashboard_btn).not_to_have_class(re.compile(".*active.*"))

        faculty_btn.click()
        page.wait_for_timeout(300)
        expect(faculty_btn).to_have_class(re.compile(".*active.*"))
        expect(programs_btn).not_to_have_class(re.compile(".*active.*"))

        outcomes_btn.click()
        page.wait_for_timeout(300)
        expect(outcomes_btn).to_have_class(re.compile(".*active.*"))
        expect(faculty_btn).not_to_have_class(re.compile(".*active.*"))

        dashboard_btn.click()
        page.wait_for_timeout(300)
        expect(dashboard_btn).to_have_class(re.compile(".*active.*"))
        expect(outcomes_btn).not_to_have_class(re.compile(".*active.*"))
