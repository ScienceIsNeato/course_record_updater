"""
E2E test for UI interactions on the Assessments page.
"""

import json

import pytest
from playwright.sync_api import Page, expect

from src.utils.constants import TEST_USER_PASSWORD
from tests.e2e.conftest import BASE_URL
from tests.e2e.test_helpers import (
    create_test_user_via_api,
    get_institution_id_from_user,
    login_as_user,
)


def _create_test_course(
    admin_page: Page, institution_id: str, csrf_token: str
) -> tuple[str, str]:
    """Create test course for UI test."""
    # Create program
    program_response = admin_page.request.post(
        f"{BASE_URL}/api/programs",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data=json.dumps(
            {
                "name": "TEST UI Program",
                "short_name": "UI-PROG",
                "institution_id": institution_id,
            }
        ),
    )
    assert program_response.ok
    program_id = program_response.json()["program_id"]

    # Create course
    course_response = admin_page.request.post(
        f"{BASE_URL}/api/courses",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data=json.dumps(
            {
                "course_number": "UI-101",
                "course_title": "UI Test Course",
                "department": "Computer Science",
                "institution_id": institution_id,
                "program_id": program_id,
            }
        ),
    )
    assert course_response.ok
    course_id = course_response.json()["course_id"]

    # Create instructor
    instructor = create_test_user_via_api(
        admin_page=admin_page,
        base_url=BASE_URL,
        email="test.ui@test.com",
        first_name="Test",
        last_name="UI",
        role="instructor",
        institution_id=institution_id,
        program_ids=[program_id],
    )
    instructor_id = instructor["user_id"]

    # Create term
    term_response = admin_page.request.post(
        f"{BASE_URL}/api/terms",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data=json.dumps(
            {
                "name": "Fall 2024",
                "start_date": "2024-08-15",
                "end_date": "2024-12-15",
                "institution_id": institution_id,
            }
        ),
    )
    assert term_response.ok
    term_id = term_response.json()["term_id"]

    # Create offering + section
    offering_response = admin_page.request.post(
        f"{BASE_URL}/api/offerings",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data=json.dumps(
            {
                "course_id": course_id,
                "term_id": term_id,
                "instructor_id": instructor_id,
                "institution_id": institution_id,
            }
        ),
    )
    assert offering_response.ok
    offering_id = offering_response.json()["offering_id"]

    section_response = admin_page.request.post(
        f"{BASE_URL}/api/sections",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data=json.dumps(
            {
                "offering_id": offering_id,
                "section_number": "001",
                "instructor_id": instructor_id,
                "status": "open",
                "enrollment": 10,
            }
        ),
    )
    assert section_response.ok

    # Create CLO
    clo_response = admin_page.request.post(
        f"{BASE_URL}/api/courses/{course_id}/outcomes",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data=json.dumps(
            {
                "course_id": course_id,
                "clo_number": 1,
                "description": "Test CLO",
                "status": "assigned",
            }
        ),
    )
    assert clo_response.ok

    return course_id, instructor_id


@pytest.mark.e2e
def test_course_level_section_visibility(authenticated_institution_admin_page: Page):
    """Test that course-level section hides when selection is cleared."""
    admin_page = authenticated_institution_admin_page
    institution_id = get_institution_id_from_user(admin_page)
    csrf_token = admin_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    course_id, _ = _create_test_course(admin_page, institution_id, csrf_token)

    # Login as instructor
    instructor_page = admin_page.context.new_page()
    login_as_user(instructor_page, BASE_URL, "test.ui@test.com", TEST_USER_PASSWORD)
    instructor_page.goto(f"{BASE_URL}/assessments")

    # Select course
    course_select = instructor_page.locator("#courseSelect")
    expect(course_select).to_be_visible()

    # Wait for option and select
    instructor_page.wait_for_selector(
        f"#courseSelect option[value^='{course_id}::']", state="attached"
    )
    option_value = instructor_page.locator(
        f"#courseSelect option[value^='{course_id}::']"
    ).first.get_attribute("value")
    course_select.select_option(value=option_value)

    # Verify section visible
    course_level_section = instructor_page.locator("#courseLevelSection")
    expect(course_level_section).to_be_visible()

    # Clear selection
    course_select.select_option(value="")

    # Verify section hidden
    expect(course_level_section).to_be_hidden()
