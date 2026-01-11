"""
E2E tests for Instructor Dashboard navigation after the header refresh.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.header_navigator import HeaderNavigator


@pytest.mark.e2e
class TestInstructorDashboardWorkflow:
    """Verify the key links and navigation text for instructor dashboards."""

    def test_logo_link_navigates_to_dashboard(
        self, instructor_authenticated_page: Page
    ):
        page = instructor_authenticated_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        logo_anchor = page.locator("a.navbar-brand")
        href = logo_anchor.get_attribute("href")
        assert href == "/dashboard"

        logo_anchor.click()
        page.wait_for_load_state("networkidle")
        expect(page).to_have_url("http://localhost:3002/dashboard")

    def test_navigation_links_exist(self, instructor_authenticated_page: Page):
        page = instructor_authenticated_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        navigator = HeaderNavigator(page)
        expected_texts = [
            "Dashboard",
            "Audit",
            "Progress",
            "CLOs",
            "Users",
            "Courses",
            "Offerings",
            "Sections",
        ]
        labels = navigator.labels()
        assert labels[: len(expected_texts)] == expected_texts
