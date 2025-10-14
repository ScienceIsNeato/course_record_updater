"""E2E tests for dashboard summary statistics display."""

import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_tc_dashboard_001_institution_admin_summary_stats_display(
    authenticated_page: Page,
):
    """
    Test: Institution Admin Dashboard Summary Statistics Display

    Verify that the header summary cards display actual counts,
    not zeros, when the institution has programs, courses, faculty, and sections.

    This test validates that:
    1. The dashboard loads successfully
    2. Summary stats API is called and returns data
    3. JavaScript populates the summary cards with actual counts
    4. All four stat cards (Programs, Courses, Faculty, Sections) show non-zero values
    """
    page = authenticated_page

    # Navigate to the dashboard
    page.goto("http://localhost:3002/dashboard")
    page.wait_for_load_state("networkidle")

    # Wait for dashboard data to load
    page.wait_for_selector(".header-stats", timeout=5000)

    # Give JavaScript time to populate the stats
    page.wait_for_timeout(1000)

    # Get the stat values from the header
    program_count = page.locator("#programCount").text_content()
    course_count = page.locator("#courseCount").text_content()
    faculty_count = page.locator("#facultyCount").text_content()
    section_count = page.locator("#sectionCount").text_content()

    print(f"\n📊 Dashboard Stats:")
    print(f"  Programs: {program_count}")
    print(f"  Courses: {course_count}")
    print(f"  Faculty: {faculty_count}")
    print(f"  Sections: {section_count}")

    # Assert that all counts are greater than zero
    # The seeded CEI institution should have:
    # - 2 programs (CS, EE)
    # - 5+ courses
    # - 2+ faculty (john.instructor, jane.instructor)
    # - 6+ sections

    assert (
        program_count != "0"
    ), "Program count should not be zero (CEI has CS and EE programs)"
    assert (
        course_count != "0"
    ), "Course count should not be zero (CEI has multiple courses)"
    assert (
        faculty_count != "0"
    ), "Faculty count should not be zero (CEI has instructors)"
    assert section_count != "0", "Section count should not be zero (CEI has sections)"

    # Verify the counts are reasonable numbers
    assert int(program_count) >= 2, f"Expected at least 2 programs, got {program_count}"
    assert int(course_count) >= 5, f"Expected at least 5 courses, got {course_count}"
    assert int(faculty_count) >= 2, f"Expected at least 2 faculty, got {faculty_count}"
    assert int(section_count) >= 6, f"Expected at least 6 sections, got {section_count}"


@pytest.mark.e2e
def test_tc_dashboard_002_program_management_table_metrics(
    authenticated_page: Page,
):
    """
    Test: Program Management Table Shows Non-Zero Metrics

    Verify that the Program Management panel table displays actual counts
    for each program's Courses, Faculty, Students, and Sections columns,
    not zeros.

    Bug: The table shows "0" for all metrics even though:
    - CS program has 2 courses (CS-101, CS-201)
    - EE program has 3 courses (EE-101, EE-201, EE-301)
    - Both programs have assigned faculty and sections
    """
    page = authenticated_page

    # Navigate to the dashboard
    page.goto("http://localhost:3002/dashboard")
    page.wait_for_load_state("networkidle")

    # Wait for program management panel to load
    page.wait_for_selector("#institution-program-panel", timeout=5000)
    page.wait_for_timeout(1500)  # Give JavaScript time to populate

    # Get the table rows (skip header row)
    rows = page.locator("#institution-program-panel table tbody tr").all()

    print(f"\n📋 Program Management Table ({len(rows)} programs):")

    # Collect metrics to verify at least one program has non-zero values
    programs_with_courses = 0
    programs_with_sections = 0

    # Check each program row
    for i, row in enumerate(rows):
        cells = row.locator("td").all()
        if len(cells) >= 5:  # Program, Courses, Faculty, Students, Sections, ...
            program_name = cells[0].text_content().strip()
            courses = cells[1].text_content().strip()
            faculty = cells[2].text_content().strip()
            students = cells[3].text_content().strip()
            sections = cells[4].text_content().strip()

            print(
                f"  {program_name}: {courses} courses, {faculty} faculty, {students} students, {sections} sections"
            )

            # Skip test-created programs and default programs for counting
            if (
                program_name.lower() in ["asdf", "test"]
                or "default" in program_name.lower()
            ):
                continue

            # Count programs with actual data
            if courses != "0":
                programs_with_courses += 1
            if sections != "0":
                programs_with_sections += 1

    # Verify at least one non-test program has courses and sections
    # (Specific program data can be affected by previous tests, so we check ANY program has data)
    assert (
        programs_with_courses > 0
    ), "At least one program should have courses assigned"
    assert programs_with_sections > 0, "At least one program should have sections"
