"""
E2E tests for Instructor Dashboard workflow.

Tests the complete instructor dashboard experience including navigation,
panel filtering, and dashboard-specific functionality.
"""

import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestInstructorDashboardWorkflow:
    """Test complete Instructor dashboard workflow."""

    def test_logo_link_navigates_to_dashboard(
        self, instructor_authenticated_page: Page
    ):
        """Test that logo link navigates to dashboard, not API endpoint."""
        page = instructor_authenticated_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        logo_link = page.locator("a.navbar-brand")
        href = logo_link.get_attribute("href")
        assert href == "/dashboard", f"Expected /dashboard, got {href}"

        logo_link.click()
        page.wait_for_load_state("networkidle")
        expect(page).to_have_url("http://localhost:3002/dashboard")
        expect(page).to_have_title(re.compile(".*Instructor Dashboard.*"))

        # Verify page content is HTML, not JSON
        body_text = page.locator("body").text_content()
        assert "Instructor Dashboard" in body_text
        assert "{" not in body_text[:100], "Page should not show JSON"

    def test_dashboard_button_shows_all_panels(
        self, instructor_authenticated_page: Page
    ):
        """Test that Dashboard button shows all panels."""
        page = instructor_authenticated_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        dashboard_btn = page.locator("#dashboard-view-all")
        dashboard_btn.click()
        page.wait_for_timeout(500)

        # Verify all panels are visible
        expect(page.locator("#instructor-teaching-panel")).to_be_visible()
        expect(page.locator("#instructor-assessment-panel")).to_be_visible()
        expect(page.locator("#instructor-activity-panel")).to_be_visible()
        expect(page.locator("#instructor-summary-panel")).to_be_visible()
        expect(dashboard_btn).to_have_class(re.compile(".*active.*"))

    def test_teaching_button_filters_to_teaching_panel(
        self, instructor_authenticated_page: Page
    ):
        """Test that Teaching button shows only Teaching panel."""
        page = instructor_authenticated_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        teaching_btn = page.locator("#dashboard-teaching")
        teaching_btn.click()
        page.wait_for_timeout(500)

        expect(page.locator("#instructor-teaching-panel")).to_be_visible()
        expect(page.locator("#instructor-assessment-panel")).not_to_be_visible()
        expect(page.locator("#instructor-activity-panel")).not_to_be_visible()
        expect(page.locator("#instructor-summary-panel")).not_to_be_visible()
        expect(teaching_btn).to_have_class(re.compile(".*active.*"))

    def test_assessments_button_filters_to_assessment_panel(
        self, instructor_authenticated_page: Page
    ):
        """Test that Assessments button shows only Assessment panel."""
        page = instructor_authenticated_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        assessments_btn = page.locator("#dashboard-assessments")
        assessments_btn.click()
        page.wait_for_timeout(500)

        expect(page.locator("#instructor-teaching-panel")).not_to_be_visible()
        expect(page.locator("#instructor-assessment-panel")).to_be_visible()
        expect(page.locator("#instructor-activity-panel")).not_to_be_visible()
        expect(page.locator("#instructor-summary-panel")).not_to_be_visible()
        expect(assessments_btn).to_have_class(re.compile(".*active.*"))

    def test_progress_button_filters_to_progress_panels(
        self, instructor_authenticated_page: Page
    ):
        """Test that Progress button shows Activity and Summary panels."""
        page = instructor_authenticated_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        progress_btn = page.locator("#dashboard-progress")
        progress_btn.click()
        page.wait_for_timeout(500)

        expect(page.locator("#instructor-teaching-panel")).not_to_be_visible()
        expect(page.locator("#instructor-assessment-panel")).not_to_be_visible()
        expect(page.locator("#instructor-activity-panel")).to_be_visible()
        expect(page.locator("#instructor-summary-panel")).to_be_visible()
        expect(progress_btn).to_have_class(re.compile(".*active.*"))

    def test_navigation_buttons_toggle_active_state(
        self, instructor_authenticated_page: Page
    ):
        """Test that clicking navigation buttons toggles active state correctly."""
        page = instructor_authenticated_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        dashboard_btn = page.locator("#dashboard-view-all")
        teaching_btn = page.locator("#dashboard-teaching")
        assessments_btn = page.locator("#dashboard-assessments")
        progress_btn = page.locator("#dashboard-progress")

        # Click through each button and verify active states
        teaching_btn.click()
        page.wait_for_timeout(300)
        expect(teaching_btn).to_have_class(re.compile(".*active.*"))
        expect(dashboard_btn).not_to_have_class(re.compile(".*active.*"))

        assessments_btn.click()
        page.wait_for_timeout(300)
        expect(assessments_btn).to_have_class(re.compile(".*active.*"))
        expect(teaching_btn).not_to_have_class(re.compile(".*active.*"))

        progress_btn.click()
        page.wait_for_timeout(300)
        expect(progress_btn).to_have_class(re.compile(".*active.*"))
        expect(assessments_btn).not_to_have_class(re.compile(".*active.*"))

        dashboard_btn.click()
        page.wait_for_timeout(300)
        expect(dashboard_btn).to_have_class(re.compile(".*active.*"))
        expect(progress_btn).not_to_have_class(re.compile(".*active.*"))
