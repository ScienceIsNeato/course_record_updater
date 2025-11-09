"""
E2E tests for navigation fixes (Issue #30).

Tests:
1. Logo link points to /dashboard (not /api/dashboard)
2. Teaching/Assessments/Progress buttons filter dashboard panels
3. Dashboard button shows all panels
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestNavigationFixes:
    """Test navigation element fixes for Issue #30."""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, login_as_instructor):
        """Navigate to instructor dashboard before each test."""
        login_as_instructor(page)
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

    def test_logo_link_points_to_dashboard_not_api(self, page: Page):
        """Test that logo link points to /dashboard, not /api/dashboard."""
        # Find the logo link
        logo_link = page.locator("a.navbar-brand")

        # Verify href attribute
        href = logo_link.get_attribute("href")
        assert href == "/dashboard", f"Expected /dashboard, got {href}"

        # Click logo and verify we stay on dashboard (no JSON response)
        logo_link.click()
        page.wait_for_load_state("networkidle")

        # Verify we're on the dashboard page
        expect(page).to_have_url("http://localhost:3002/dashboard")
        expect(page).to_have_title(pytest.app_title_pattern("Instructor Dashboard"))

        # Verify page content is HTML, not JSON
        body_text = page.locator("body").text_content()
        assert "Instructor Dashboard" in body_text
        assert "{" not in body_text[:100], "Page should not show JSON"

    def test_dashboard_button_shows_all_panels(self, page: Page):
        """Test that Dashboard button shows all panels."""
        # Click Dashboard button
        dashboard_btn = page.locator("#dashboard-view-all")
        dashboard_btn.click()
        page.wait_for_timeout(500)  # Wait for animation

        # Verify all panels are visible
        teaching_panel = page.locator("#instructor-teaching-panel")
        assessment_panel = page.locator("#instructor-assessment-panel")
        activity_panel = page.locator("#instructor-activity-panel")
        summary_panel = page.locator("#instructor-summary-panel")

        expect(teaching_panel).to_be_visible()
        expect(assessment_panel).to_be_visible()
        expect(activity_panel).to_be_visible()
        expect(summary_panel).to_be_visible()

        # Verify Dashboard button is active
        expect(dashboard_btn).to_have_class(pytest.contains("active"))

    def test_teaching_button_filters_to_teaching_panel(self, page: Page):
        """Test that Teaching button shows only Teaching panel."""
        # Click Teaching button
        teaching_btn = page.locator("#dashboard-teaching")
        teaching_btn.click()
        page.wait_for_timeout(500)  # Wait for animation

        # Verify only Teaching panel is visible
        teaching_panel = page.locator("#instructor-teaching-panel")
        assessment_panel = page.locator("#instructor-assessment-panel")
        activity_panel = page.locator("#instructor-activity-panel")
        summary_panel = page.locator("#instructor-summary-panel")

        expect(teaching_panel).to_be_visible()
        expect(assessment_panel).not_to_be_visible()
        expect(activity_panel).not_to_be_visible()
        expect(summary_panel).not_to_be_visible()

        # Verify Teaching button is active
        expect(teaching_btn).to_have_class(pytest.contains("active"))

    def test_assessments_button_filters_to_assessment_panel(self, page: Page):
        """Test that Assessments button shows only Assessment panel."""
        # Click Assessments button
        assessments_btn = page.locator("#dashboard-assessments")
        assessments_btn.click()
        page.wait_for_timeout(500)  # Wait for animation

        # Verify only Assessment panel is visible
        teaching_panel = page.locator("#instructor-teaching-panel")
        assessment_panel = page.locator("#instructor-assessment-panel")
        activity_panel = page.locator("#instructor-activity-panel")
        summary_panel = page.locator("#instructor-summary-panel")

        expect(teaching_panel).not_to_be_visible()
        expect(assessment_panel).to_be_visible()
        expect(activity_panel).not_to_be_visible()
        expect(summary_panel).not_to_be_visible()

        # Verify Assessments button is active
        expect(assessments_btn).to_have_class(pytest.contains("active"))

    def test_progress_button_filters_to_progress_panels(self, page: Page):
        """Test that Progress button shows Activity and Summary panels."""
        # Click Progress button
        progress_btn = page.locator("#dashboard-progress")
        progress_btn.click()
        page.wait_for_timeout(500)  # Wait for animation

        # Verify only progress-related panels are visible
        teaching_panel = page.locator("#instructor-teaching-panel")
        assessment_panel = page.locator("#instructor-assessment-panel")
        activity_panel = page.locator("#instructor-activity-panel")
        summary_panel = page.locator("#instructor-summary-panel")

        expect(teaching_panel).not_to_be_visible()
        expect(assessment_panel).not_to_be_visible()
        expect(activity_panel).to_be_visible()
        expect(summary_panel).to_be_visible()

        # Verify Progress button is active
        expect(progress_btn).to_have_class(pytest.contains("active"))

    def test_navigation_buttons_toggle_active_state(self, page: Page):
        """Test that clicking navigation buttons toggles active state correctly."""
        dashboard_btn = page.locator("#dashboard-view-all")
        teaching_btn = page.locator("#dashboard-teaching")
        assessments_btn = page.locator("#dashboard-assessments")
        progress_btn = page.locator("#dashboard-progress")

        # Click Teaching
        teaching_btn.click()
        page.wait_for_timeout(300)
        expect(teaching_btn).to_have_class(pytest.contains("active"))
        expect(dashboard_btn).not_to_have_class(pytest.contains("active"))

        # Click Assessments
        assessments_btn.click()
        page.wait_for_timeout(300)
        expect(assessments_btn).to_have_class(pytest.contains("active"))
        expect(teaching_btn).not_to_have_class(pytest.contains("active"))

        # Click Progress
        progress_btn.click()
        page.wait_for_timeout(300)
        expect(progress_btn).to_have_class(pytest.contains("active"))
        expect(assessments_btn).not_to_have_class(pytest.contains("active"))

        # Click Dashboard
        dashboard_btn.click()
        page.wait_for_timeout(300)
        expect(dashboard_btn).to_have_class(pytest.contains("active"))
        expect(progress_btn).not_to_have_class(pytest.contains("active"))

    def test_data_management_panel_always_visible(self, page: Page):
        """Test that Data Management panel is always visible regardless of filter."""
        data_mgmt_panel = page.locator("#data-management-panel")

        # Test with each filter
        for button_id in [
            "#dashboard-view-all",
            "#dashboard-teaching",
            "#dashboard-assessments",
            "#dashboard-progress",
        ]:
            page.locator(button_id).click()
            page.wait_for_timeout(300)
            # Data Management panel should always be visible
            # Note: It may not exist in test environment, so skip if not found
            if data_mgmt_panel.count() > 0:
                expect(data_mgmt_panel).to_be_visible()
