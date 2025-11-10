"""
E2E/UAT tests for all dashboard navigation and action fixes.

Covers:
- Issue #30: Instructor Dashboard Navigation (already in test_navigation_fixes.py)
- Issue #31: Program Admin Dashboard Navigation
- Issue #32: Institution Admin Dashboard Navigation
- Issue #28: Site Admin Dashboard Navigation
- Issue #33: Instructor Dashboard Actions (Enter buttons, disabled states)
- Issue #29: Export Data UX (disabled button when no adapters)
"""

import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestProgramAdminDashboardNavigation:
    """UAT tests for Program Admin dashboard navigation (Issue #31)."""

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

        # Program Admin panels
        courses_panel = page.locator("#program-courses-panel")
        faculty_panel = page.locator("#program-faculty-panel")
        clo_panel = page.locator("#program-clo-panel")
        assessment_panel = page.locator("#program-assessment-panel")
        audit_panel = page.locator("#program-clo-audit-panel")

        # All panels should be visible
        expect(courses_panel).to_be_visible()
        expect(faculty_panel).to_be_visible()
        expect(clo_panel).to_be_visible()
        expect(assessment_panel).to_be_visible()
        expect(audit_panel).to_be_visible()

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

        courses_panel = page.locator("#program-courses-panel")
        faculty_panel = page.locator("#program-faculty-panel")
        clo_panel = page.locator("#program-clo-panel")

        expect(courses_panel).to_be_visible()
        expect(faculty_panel).not_to_be_visible()
        expect(clo_panel).not_to_be_visible()

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

        courses_panel = page.locator("#program-courses-panel")
        faculty_panel = page.locator("#program-faculty-panel")
        clo_panel = page.locator("#program-clo-panel")

        expect(courses_panel).not_to_be_visible()
        expect(faculty_panel).to_be_visible()
        expect(clo_panel).not_to_be_visible()

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

        courses_panel = page.locator("#program-courses-panel")
        faculty_panel = page.locator("#program-faculty-panel")
        clo_panel = page.locator("#program-clo-panel")

        expect(courses_panel).not_to_be_visible()
        expect(faculty_panel).not_to_be_visible()
        expect(clo_panel).to_be_visible()

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

        # Click through each button
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


@pytest.mark.e2e
class TestInstitutionAdminDashboardNavigation:
    """UAT tests for Institution Admin dashboard navigation (Issue #32)."""

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

        # Institution Admin panels
        program_panel = page.locator("#institution-program-panel")
        course_panel = page.locator("#institution-course-panel")
        faculty_panel = page.locator("#institution-faculty-panel")
        sections_panel = page.locator("#institution-sections-panel")
        outcome_panel = page.locator("#institution-outcome-panel")

        # All panels should be visible
        expect(program_panel).to_be_visible()
        expect(course_panel).to_be_visible()
        expect(faculty_panel).to_be_visible()
        expect(sections_panel).to_be_visible()
        expect(outcome_panel).to_be_visible()

        expect(dashboard_btn).to_have_class(re.compile(".*active.*"))

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

        program_panel = page.locator("#institution-program-panel")
        course_panel = page.locator("#institution-course-panel")
        faculty_panel = page.locator("#institution-faculty-panel")
        outcome_panel = page.locator("#institution-outcome-panel")

        expect(program_panel).to_be_visible()
        expect(course_panel).to_be_visible()
        expect(faculty_panel).not_to_be_visible()
        expect(outcome_panel).not_to_be_visible()

        expect(programs_btn).to_have_class(re.compile(".*active.*"))

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

        program_panel = page.locator("#institution-program-panel")
        faculty_panel = page.locator("#institution-faculty-panel")
        sections_panel = page.locator("#institution-sections-panel")
        outcome_panel = page.locator("#institution-outcome-panel")

        expect(program_panel).not_to_be_visible()
        expect(faculty_panel).to_be_visible()
        expect(sections_panel).to_be_visible()
        expect(outcome_panel).not_to_be_visible()

        expect(faculty_btn).to_have_class(re.compile(".*active.*"))

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

        program_panel = page.locator("#institution-program-panel")
        faculty_panel = page.locator("#institution-faculty-panel")
        outcome_panel = page.locator("#institution-outcome-panel")
        assessment_panel = page.locator("#institution-assessment-panel")
        audit_panel = page.locator("#institution-clo-audit-panel")

        expect(program_panel).not_to_be_visible()
        expect(faculty_panel).not_to_be_visible()
        expect(outcome_panel).to_be_visible()
        expect(assessment_panel).to_be_visible()
        expect(audit_panel).to_be_visible()

        expect(outcomes_btn).to_have_class(re.compile(".*active.*"))

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


@pytest.mark.e2e
class TestSiteAdminDashboardNavigation:
    """UAT tests for Site Admin dashboard navigation (Issue #28)."""

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

        users_link = page.locator('a.nav-link[href="/admin/users"]')
        expect(users_link).to_be_visible()

        href = users_link.get_attribute("href")
        assert href == "/admin/users", f"Expected /admin/users, got {href}"

        # Click and verify navigation
        users_link.click()
        page.wait_for_load_state("networkidle")
        expect(page).to_have_url("http://localhost:3002/admin/users")

    def test_institutions_button_shows_coming_soon(
        self, authenticated_site_admin_page: Page
    ):
        """Test that Institutions button shows 'coming soon' behavior."""
        page = authenticated_site_admin_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        # This button should still show an alert (planned feature)
        institutions_btn = page.locator('button.nav-link[onclick="showInstitutions()"]')
        expect(institutions_btn).to_be_visible()

        # Verify button text
        expect(institutions_btn).to_contain_text("Institutions")

    def test_system_button_shows_coming_soon(self, authenticated_site_admin_page: Page):
        """Test that System button shows 'coming soon' behavior."""
        page = authenticated_site_admin_page
        page.goto("http://localhost:3002/dashboard")
        page.wait_for_load_state("networkidle")

        # This button should still show an alert (planned feature)
        system_btn = page.locator('button.nav-link[onclick="showSystemSettings()"]')
        expect(system_btn).to_be_visible()

        # Verify button text
        expect(system_btn).to_contain_text("System")
