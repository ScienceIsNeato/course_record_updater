import re
import time

import pytest
from playwright.sync_api import Page, expect

from src.utils.constants import E2E_TEST_PORT

BASE_URL = f"http://localhost:{E2E_TEST_PORT}"


@pytest.fixture
def test_course_data(authenticated_program_admin_page: Page):
    """
    Creates a unique course for testing offering creation.
    Returns dict with course details.
    """
    page = authenticated_program_admin_page

    timestamp = int(time.time())
    course_number = f"TDD-{timestamp}"
    course_title = "TDD Test Course"

    # Start at Dashboard
    page.goto(f"{BASE_URL}/dashboard")

    # Click "Add Course" button in Course Management panel
    # We use nth(0) if there are multiple "Add Course" buttons (one per panel potentially)
    # but usually "Add Course" specifically targets the course modal.
    page.get_by_role("button", name="Add Course").first.click()

    page.fill("#courseNumber", course_number)
    page.fill("#courseTitle", course_title)
    page.fill("#courseDepartment", "Test Dept")
    page.fill("#courseCreditHours", "3")

    # Select "Computer Science" program (matches Bob's assignment)
    # Bob is program admin for CS, so he must create course in CS to see it later.
    page.locator("#courseProgramIds").select_option(label="Computer Science (CS)")

    # Handle the success alert dialog by auto-dismissing it
    page.on("dialog", lambda dialog: dialog.dismiss())

    page.get_by_role("button", name="Create Course").click()

    # Instead of looking for a toast (which is an alert in courseManagement.js),
    # verify the modal is hidden
    expect(page.locator("#createCourseModal")).to_be_hidden()

    return {"course_number": course_number, "course_title": course_title}


@pytest.mark.e2e
def test_create_offering_with_dynamic_sections(
    authenticated_program_admin_page: Page, test_course_data
):
    """
    TDD Test for "Zoology Department Expansion" and Course Offering UX.
    """
    page = authenticated_program_admin_page
    course_number = test_course_data["course_number"]

    # 1. Start at Dashboard
    page.goto(f"{BASE_URL}/dashboard")

    # 2. Open "Add Offering" modal
    page.get_by_role("button", name="Add Offering").click()
    expect(page.get_by_text("Create New Course Offering")).to_be_visible()

    # 3. Fill basic offering details
    course_select = page.locator("#offeringCourseId")
    expect(course_select).not_to_be_empty()
    course_title = test_course_data["course_title"]

    course_select.select_option(label=f"{course_number} - {course_title}")

    # Select Term (index 1)
    page.locator("#offeringTermId").select_option(index=1)

    # Select Program (Required) - "Computer Science" matches Bob's program
    page.locator("#offeringProgramId").select_option(label="Computer Science")

    # 4. Verify Dynamic Section UI
    expect(page.locator("#sectionsContainer")).to_be_visible()

    # Check for default Section 001
    section_001_row = page.locator(".section-row").first
    expect(section_001_row.locator(".section-number")).to_have_value("001")

    # 5. Add Section 002
    add_section_btn = page.locator("#addSectionBtn")
    expect(add_section_btn).to_be_visible()
    add_section_btn.click()

    # Verify second row appears
    section_002_row = page.locator(".section-row").nth(1)
    expect(section_002_row).to_be_visible()
    expect(section_002_row.locator(".section-number")).to_have_value("002")

    # 6. Submit
    # Handle the success alert dialog by auto-dismissing it
    page.on("dialog", lambda dialog: dialog.dismiss())
    page.locator("#createOfferingBtn").click()

    # 7. Verify Success
    expect(page.locator("#createOfferingModal")).to_be_hidden()

    # 8. Verify Dashboard Update
    page.goto(f"{BASE_URL}/dashboard")
    expect(
        page.locator("#program-courses-table").get_by_role("cell", name=course_number)
    ).to_be_visible()
