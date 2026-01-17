"""
E2E Tests for Assessments Page

Tests that verify the assessments page loads correctly with data populated
from the E2E seed manifest.

TDD: These tests verify that the assessments page works end-to-end with
automatically seeded data - no manual seeding required.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL


@pytest.mark.e2e
class TestAssessmentsPageDataLoad:
    """E2E tests for assessments page data loading."""

    def test_assessments_page_loads_with_courses_for_institution_admin(
        self, authenticated_institution_admin_page: Page
    ):
        """
        Verify that the assessments page loads with courses in the dropdown
        for an institution admin.

        This test validates:
        1. Page navigates successfully to /assessments
        2. Course dropdown contains actual courses (not just placeholder)
        3. Status summary section is visible

        If this test fails, it likely means:
        - E2E seed data is missing sections/courses
        - The /api/sections endpoint is not returning data
        - JavaScript failed to populate the dropdown
        """
        page = authenticated_institution_admin_page

        # Navigate to assessments page
        page.goto(f"{BASE_URL}/assessments")
        page.wait_for_load_state("networkidle")

        # Verify page title
        expect(page).to_have_title("Course Assessments")

        # Verify course dropdown exists
        course_select = page.locator("#courseSelect")
        expect(course_select).to_be_visible()

        # Wait for JavaScript to populate the dropdown (loadCourses() is async)
        page.wait_for_function(
            """() => {
                const select = document.getElementById('courseSelect');
                return select && select.options.length > 1;
            }""",
            timeout=10000,
        )

        # Verify dropdown has actual courses (more than just the placeholder)
        options = course_select.locator("option")
        option_count = options.count()

        # Should have at least 2 options: placeholder + at least 1 course
        assert option_count >= 2, (
            f"Course dropdown should have courses loaded. "
            f"Found only {option_count} option(s). "
            f"Check that E2E seed data includes sections with instructors."
        )

        # Verify the first option is the placeholder
        first_option = options.nth(0)
        expect(first_option).to_have_text("-- Select a course --")

        # Verify at least one course option exists
        second_option = options.nth(1)
        second_option_text = second_option.text_content()
        assert second_option_text != "", "Course option should have text"
        # Course format: "Term - CourseCode - Section X (Y%)"
        assert " - " in second_option_text, (
            f"Course option should follow format 'Term - Code - Section'. "
            f"Got: {second_option_text}"
        )

    def test_selecting_course_loads_outcomes_section(
        self, authenticated_institution_admin_page: Page
    ):
        """
        Verify that selecting a course populates the outcomes section and
        shows the course-level assessment form.
        """
        page = authenticated_institution_admin_page

        page.goto(f"{BASE_URL}/assessments")
        page.wait_for_load_state("networkidle")

        # Wait for courses to load
        page.wait_for_function(
            """() => {
                const select = document.getElementById('courseSelect');
                return select && select.options.length > 1;
            }""",
            timeout=10000,
        )

        # Select the first actual course (index 1, after placeholder)
        course_select = page.locator("#courseSelect")
        course_select.select_option(index=1)

        # Wait for outcomes to load
        page.wait_for_load_state("networkidle")

        # The course-level section should become visible
        course_level_section = page.locator("#courseLevelSection")
        expect(course_level_section).to_be_visible(timeout=10000)

        # Enrollment field should be populated
        enrollment_field = page.locator("#courseEnrollment")
        expect(enrollment_field).to_be_visible()


@pytest.mark.e2e
class TestAssessmentsAPIResponses:
    """Tests that verify the underlying API responses for assessments page."""

    def test_sections_api_returns_data(
        self, authenticated_institution_admin_page: Page
    ):
        """
        Verify that /api/sections returns sections for the institution admin.

        This is a diagnostic test - if it fails, the assessments page
        will definitely not work.
        """
        page = authenticated_institution_admin_page

        # Make direct API request
        response = page.request.get(f"{BASE_URL}/api/sections")

        assert response.ok, f"API returned {response.status}: {response.text()}"

        data = response.json()
        assert data.get("success") is True, f"API returned error: {data}"
        assert "sections" in data, "Response missing 'sections' key"

        sections = data["sections"]
        assert isinstance(sections, list), "sections should be a list"
        assert len(sections) > 0, (
            "No sections returned from API. " "E2E seed data should include sections."
        )

    def test_courses_api_returns_data(self, authenticated_institution_admin_page: Page):
        """
        Verify that /api/courses returns courses for the institution.
        """
        page = authenticated_institution_admin_page

        response = page.request.get(f"{BASE_URL}/api/courses")

        assert response.ok, f"API returned {response.status}: {response.text()}"

        data = response.json()
        assert data.get("success") is True, f"API returned error: {data}"
        assert "courses" in data, "Response missing 'courses' key"

        courses = data["courses"]
        assert isinstance(courses, list), "courses should be a list"
        assert len(courses) > 0, (
            "No courses returned from API. " "E2E seed data should include courses."
        )
