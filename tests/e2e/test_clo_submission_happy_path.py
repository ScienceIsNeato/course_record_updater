"""
E2E: CLO Submission Happy Path

Test the instructor workflow for submitting CLOs for approval.

Workflow:
1. Seed test data: Institution, program, course, section with instructor, CLOs in ASSIGNED status
2. Instructor logs in
3. Navigate to assessments page
4. Edit CLO fields (verify auto-set to IN_PROGRESS)
5. Submit CLO for approval
6. Verify status = AWAITING_APPROVAL, submitted_at set
"""

import json

import pytest
from playwright.sync_api import Page

from src.utils.constants import GENERIC_PASSWORD
from tests.e2e.conftest import BASE_URL
from tests.e2e.test_helpers import (
    create_test_user_via_api,
    get_institution_id_from_user,
    login_as_user,
)

# === Helper Functions for Test Data Setup ===


def _create_test_program(admin_page, csrf_token, institution_id):
    """Create test program via API."""
    program_response = admin_page.request.post(
        f"{BASE_URL}/api/programs",
        headers={"Content-Type": "application/json", "X-CSRFToken": csrf_token or ""},
        data=json.dumps(
            {
                "name": "UAT-007 Computer Science",
                "short_name": "UAT007-CS",
                "institution_id": institution_id,
            }
        ),
    )
    assert program_response.ok, f"Failed to create program: {program_response.text()}"
    return program_response.json()["program_id"]


def _create_test_course(admin_page, csrf_token, institution_id, program_id):
    """Create test course via API."""
    course_response = admin_page.request.post(
        f"{BASE_URL}/api/courses",
        headers={"Content-Type": "application/json", "X-CSRFToken": csrf_token or ""},
        data=json.dumps(
            {
                "course_number": "UAT007-SE101",
                "course_title": "UAT-007 Software Engineering",
                "department": "Computer Science",
                "institution_id": institution_id,
                "program_id": program_id,
            }
        ),
    )
    assert course_response.ok, f"Failed to create course: {course_response.text()}"
    return course_response.json()["course_id"]


def _create_test_term(admin_page, csrf_token, institution_id):
    """Create test term via API."""
    term_response = admin_page.request.post(
        f"{BASE_URL}/api/terms",
        headers={"Content-Type": "application/json", "X-CSRFToken": csrf_token or ""},
        data=json.dumps(
            {
                "name": "Fall 2024",
                "start_date": "2024-08-15",
                "end_date": "2024-12-15",
                "assessment_due_date": "2024-12-20",
                "institution_id": institution_id,
            }
        ),
    )
    assert term_response.ok, f"Failed to create term: {term_response.text()}"
    return term_response.json()["term_id"]


def _create_test_offering(
    admin_page, csrf_token, course_id, term_id, instructor_id, institution_id
):
    """Create test offering via API."""
    section_response = admin_page.request.post(
        f"{BASE_URL}/api/offerings",
        headers={"Content-Type": "application/json", "X-CSRFToken": csrf_token or ""},
        data=json.dumps(
            {
                "course_id": course_id,
                "term_id": term_id,
                "instructor_id": instructor_id,
                "institution_id": institution_id,
            }
        ),
    )
    assert section_response.ok, f"Failed to create offering: {section_response.text()}"
    return section_response.json()["offering_id"]


def _create_test_section(
    admin_page, csrf_token, offering_id, section_number, instructor_id
):
    """Create test section via API."""
    section_response = admin_page.request.post(
        f"{BASE_URL}/api/sections",
        headers={"Content-Type": "application/json", "X-CSRFToken": csrf_token or ""},
        data=json.dumps(
            {
                "offering_id": offering_id,
                "section_number": section_number,
                "instructor_id": instructor_id,
                "status": "open",
            }
        ),
    )
    assert section_response.ok, f"Failed to create section: {section_response.text()}"
    return section_response.json()["section_id"]


def _create_test_clos(admin_page, csrf_token, course_id, section_ids):
    """Create test CLOs for all sections."""
    clo_responses = []
    for section_id in section_ids:
        clo_response = admin_page.request.post(
            f"{BASE_URL}/api/course-outcomes",
            headers={
                "Content-Type": "application/json",
                "X-CSRFToken": csrf_token or "",
            },
            data=json.dumps(
                {
                    "course_id": course_id,
                    "section_id": section_id,
                    "description": "Identify key biological processes and systems in living organisms.",
                    "status": "assigned",
                }
            ),
        )
        assert clo_response.ok, f"Failed to create CLO: {clo_response.text()}"
        clo_responses.append(clo_response.json())
    return clo_responses


def _login_as_instructor(admin_page, instructor_email, csrf_token):
    """Login as instructor."""
    admin_page.goto(f"{BASE_URL}/logout")
    admin_page.wait_for_timeout(500)
    admin_page.goto(f"{BASE_URL}/login")
    admin_page.wait_for_selector("input[name='email']")
    admin_page.fill("input[name='email']", instructor_email)
    admin_page.fill("input[name='password']", "Password123!")
    admin_page.click("#login-form button[type='submit']")
    admin_page.wait_for_selector("text=Dashboard")


def _navigate_to_assessments_and_select_section(instructor_page, section_id):
    """Navigate to assessments page and select specific section."""
    instructor_page.goto(f"{BASE_URL}/assessments")
    instructor_page.wait_for_selector("#courseSelect")
    instructor_page.select_option("#courseSelect", f".*::{section_id}")
    instructor_page.wait_for_selector(".outcomes-list")


@pytest.mark.e2e
@pytest.mark.e2e
def _navigate_and_login(instructor_page, live_server):
    """Helper: Navigate to audit page and login."""
    instructor_page.goto(f"{live_server.url}/audit/clo")
    instructor_page.wait_for_selector('h2:has-text("Outcome Audit")')


def _verify_initial_state(instructor_page):
    """Helper: Verify initial CLO state."""
    row = instructor_page.locator("tr").filter(has_text="Identify key biological").first
    assert row.locator('.badge:has-text("Assigned")').is_visible()


def _fill_assessment_data(instructor_page, students_took, students_passed, tool):
    """Helper: Fill assessment form data."""
    instructor_page.locator('input[name="students_took"]').fill(str(students_took))
    instructor_page.locator('input[name="students_passed"]').fill(str(students_passed))
    instructor_page.locator('input[name="assessment_tool"]').fill(tool)


def _submit_for_approval(instructor_page):
    """Helper: Submit CLO for approval."""
    with instructor_page.expect_response("**/api/outcomes/*/submit") as response_info:
        instructor_page.locator('button:has-text("Submit for Approval")').click()
    response = response_info.value
    assert response.status == 200


def _verify_submitted_state(instructor_page):
    """Helper: Verify CLO is in awaiting approval state."""
    instructor_page.wait_for_selector(
        '.badge:has-text("Awaiting Approval")', timeout=5000
    )
    row = instructor_page.locator("tr").filter(has_text="Identify key biological").first
    assert row.locator('.badge:has-text("Awaiting Approval")').is_visible()


def _execute_clo_submission_workflow(
    admin_page, instructor_page, course_id, section_002_id, clo1_id
):
    """Execute the entire CLO submission workflow."""
    # Navigate to assessments
    instructor_page.goto(f"{BASE_URL}/assessments")
    instructor_page.wait_for_selector("#courseSelect")
    instructor_page.select_option("#courseSelect", f".*::{section_002_id}")
    instructor_page.wait_for_selector(".outcomes-list", timeout=10000)

    # Fill assessment data
    clo_row = instructor_page.locator(f".row[data-course-outcome-id='{clo1_id}']").first
    clo_row.wait_for(state="attached", timeout=5000)

    took_input = clo_row.locator("input[data-field='students_took']")
    passed_input = clo_row.locator("input[data-field='students_passed']")
    tool_input = clo_row.locator("input[data-field='assessment_tool']")

    took_input.fill("30")
    passed_input.fill("27")
    tool_input.fill("Final Project")
    tool_input.blur()
    instructor_page.wait_for_timeout(2000)

    # Verify rate calculated
    rate_span = clo_row.locator(".col-md-1.text-center span.fw-bold")
    assert "90%" in rate_span.text_content()

    # Fill course-level data and submit
    instructor_page.fill("#courseStudentsPassed", "28")
    instructor_page.fill("#courseStudentsDFIC", "2")
    instructor_page.fill("#narrativeCelebrations", "Great engagement")
    instructor_page.fill("#narrativeChallenges", "Time management")
    instructor_page.fill("#narrativeChanges", "More group work")

    submit_btn = instructor_page.locator("#submitCourseBtn")
    with instructor_page.expect_response("**/api/courses/*/submit") as response_info:
        submit_btn.click()

    response = response_info.value
    assert response.status == 200


def _verify_section_isolation(
    admin_page, csrf_token, course_id, section_002_id, section_001_id, section_003_id
):
    """Verify that only section 002 was submitted, not 001 or 003."""
    outcomes_response = admin_page.request.get(
        f"{BASE_URL}/api/courses/{course_id}/outcomes",
        headers={"X-CSRFToken": csrf_token or ""},
    )
    assert outcomes_response.ok
    outcomes_data = outcomes_response.json()

    sec_002_outcomes = [
        o for o in outcomes_data["outcomes"] if o["section_id"] == section_002_id
    ]
    sec_001_outcomes = [
        o for o in outcomes_data["outcomes"] if o["section_id"] == section_001_id
    ]
    sec_003_outcomes = [
        o for o in outcomes_data["outcomes"] if o["section_id"] == section_003_id
    ]

    for outcome in sec_002_outcomes:
        assert (
            outcome["status"] == "awaiting_approval"
        ), f"Section 002: Expected awaiting_approval, got {outcome['status']}"

    for outcome in sec_001_outcomes:
        assert (
            outcome["status"] != "awaiting_approval"
        ), f"Section 001 wrongly submitted!"

    for outcome in sec_003_outcomes:
        assert (
            outcome["status"] != "awaiting_approval"
        ), f"Section 003 wrongly submitted!"


@pytest.mark.skip(reason="Uses non-existent /api/outcomes/{id}/assign endpoint")
def test_clo_submission_happy_path(authenticated_institution_admin_page: Page):
    """
    Test full CLO submission workflow for instructor.

    Steps:
    1. Create test instructor with assigned course section
    2. Create CLOs in ASSIGNED status
    3. Instructor logs in and edits CLO (auto-marks IN_PROGRESS)
    4. Instructor submits CLO
    5. Verify CLO status is AWAITING_APPROVAL
    """
    admin_page = authenticated_institution_admin_page

    # Get institution ID from admin user
    institution_id = get_institution_id_from_user(admin_page)

    # === STEP 1: Create test data via API ===

    # Get CSRF token
    csrf_token = admin_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Create test data using helpers
    program_id = _create_test_program(admin_page, csrf_token, institution_id)
    course_id = _create_test_course(admin_page, csrf_token, institution_id, program_id)

    # Create instructor
    instructor = create_test_user_via_api(
        admin_page=admin_page,
        base_url=BASE_URL,
        email="uat007.instructor@test.com",
        first_name="UAT007",
        last_name="Instructor",
        role="instructor",
        institution_id=institution_id,
        program_ids=[program_id],
    )
    instructor_id = instructor["user_id"]

    # Create term and offering
    term_id = _create_test_term(admin_page, csrf_token, institution_id)
    section_id = _create_test_offering(
        admin_page, csrf_token, course_id, term_id, instructor_id, institution_id
    )

    # Create sections using helper
    section_001_id = _create_test_section(
        admin_page, csrf_token, section_id, "001", instructor_id
    )
    section_002_id = _create_test_section(
        admin_page, csrf_token, section_id, "002", instructor_id
    )
    section_003_id = _create_test_section(
        admin_page, csrf_token, section_id, "003", instructor_id
    )

    # Create CLO for section 002
    clo1_response = admin_page.request.post(
        f"{BASE_URL}/api/courses/{course_id}/outcomes",
        headers={"Content-Type": "application/json", "X-CSRFToken": csrf_token or ""},
        data=json.dumps(
            {
                "course_id": course_id,
                "clo_number": 1,
                "description": "Understand software design patterns",
                "status": "assigned",
            }
        ),
    )
    assert clo1_response.ok
    clo1_id = clo1_response.json()["outcome_id"]

    # Assign CLO to section 002
    assign_response = admin_page.request.post(
        f"{BASE_URL}/api/outcomes/{clo1_id}/assign",
        headers={"Content-Type": "application/json", "X-CSRFToken": csrf_token or ""},
        data=json.dumps({"section_id": section_002_id}),
    )
    assert assign_response.ok

    # Login as instructor and execute workflow
    instructor_page = admin_page.context.new_page()
    login_as_user(
        instructor_page, BASE_URL, "uat007.instructor@test.com", GENERIC_PASSWORD
    )

    # Execute the entire submission workflow
    _execute_clo_submission_workflow(
        admin_page, instructor_page, course_id, section_002_id, clo1_id
    )

    # Verify final status
    instructor_page.goto(f"{BASE_URL}/audit/clo")
    instructor_page.wait_for_selector('tr:has-text("Understand software design")')
    status_badge = instructor_page.locator(
        'tr:has-text("Understand software design") .badge'
    ).first
    assert "Awaiting Approval" in status_badge.text_content()

    # Verify section isolation
    _verify_section_isolation(
        admin_page,
        csrf_token,
        course_id,
        section_002_id,
        section_001_id,
        section_003_id,
    )
    print("\n✅ Test passed: Section isolation verified!")

    # Cleanup
    instructor_page.close()
