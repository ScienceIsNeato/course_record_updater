"""
E2E: CLO Rework Feedback Workflow

Test the admin rework request workflow with email notification.

Workflow:
1. Seed test data: CLOs in AWAITING_APPROVAL status
2. Admin logs in, navigates to audit interface
3. Select CLO, click "Request Rework"
4. Enter feedback comments
5. Check "Send email notification"
6. Submit
7. Verify:
   - Status = APPROVAL_PENDING
   - Feedback stored
   - Email sent (check via API or email provider)
8. Instructor logs in, sees feedback
9. Makes edits, resubmits
10. Verify status back to AWAITING_APPROVAL
"""

import json

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL
from tests.e2e.test_helpers import (
    create_test_user_via_api,
    get_institution_id_from_user,
    login_as_user,
)


def _setup_rework_test_data(admin_page, institution_id):
    """Create all necessary test data via API."""
    # Get CSRF token
    csrf_token = admin_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )
    headers = {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf_token if csrf_token else "",
    }

    # Create program
    program_response = admin_page.request.post(
        f"{BASE_URL}/api/programs",
        headers=headers,
        data=json.dumps(
            {
                "name": "UAT-009 Engineering",
                "short_name": "UAT009-ENG",
                "institution_id": institution_id,
            }
        ),
    )
    assert program_response.ok, f"Failed to create program: {program_response.text()}"
    program_id = program_response.json()["program_id"]

    # Create course
    course_response = admin_page.request.post(
        f"{BASE_URL}/api/courses",
        headers=headers,
        data=json.dumps(
            {
                "course_number": "UAT009-THERMO101",
                "course_title": "UAT-009 Thermodynamics",
                "department": "Engineering",
                "institution_id": institution_id,
                "program_id": program_id,
            }
        ),
    )
    assert course_response.ok, f"Failed to create course: {course_response.text()}"
    course_id = course_response.json()["course_id"]

    # Create instructor
    instructor_email = "uat009.instructor@test.com"
    instructor = create_test_user_via_api(
        admin_page=admin_page,
        base_url=BASE_URL,
        email=instructor_email,
        first_name="UAT009",
        last_name="Instructor",
        role="instructor",
        institution_id=institution_id,
        program_ids=[program_id],
    )
    instructor_id = instructor["user_id"]

    # Create term
    term_response = admin_page.request.post(
        f"{BASE_URL}/api/terms",
        headers=headers,
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
    term_id = term_response.json()["term_id"]

    # Create offering
    section_response = admin_page.request.post(
        f"{BASE_URL}/api/offerings",
        headers=headers,
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
    section_id = section_response.json()["offering_id"]

    # Create section
    create_section_response = admin_page.request.post(
        f"{BASE_URL}/api/sections",
        headers=headers,
        data=json.dumps(
            {
                "offering_id": section_id,
                "section_number": "001",
                "instructor_id": instructor_id,
                "status": "open",
            }
        ),
    )
    assert create_section_response.ok, "Failed to create section"

    # Create CLO
    clo_response = admin_page.request.post(
        f"{BASE_URL}/api/courses/{course_id}/outcomes",
        headers=headers,
        data=json.dumps(
            {
                "course_id": course_id,
                "clo_number": 1,
                "description": "Apply thermodynamic laws to real-world systems",
                "status": "assigned",
                "students_took": 30,
                "students_passed": 18,
                "assessment_tool": "Lab Report",
            }
        ),
    )
    assert clo_response.ok, f"Failed to create CLO: {clo_response.text()}"
    clo_id = clo_response.json()["outcome_id"]
    section_outcome_ids = clo_response.json().get("section_outcome_ids", [])
    assert len(section_outcome_ids) > 0, "No section outcomes created"
    section_outcome_id = section_outcome_ids[0]  # Use first section outcome

    # Submit CLO via instructor context (using section_outcome_id)
    instructor_context = admin_page.context.browser.new_context()
    instructor_page = instructor_context.new_page()
    login_as_user(instructor_page, BASE_URL, instructor_email, "TestUser123!")

    instructor_page.goto(f"{BASE_URL}/dashboard")
    instructor_page.wait_for_load_state("networkidle")

    instructor_csrf = instructor_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    submit_response = instructor_page.request.post(
        f"{BASE_URL}/api/outcomes/{section_outcome_id}/submit",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": instructor_csrf if instructor_csrf else "",
        },
        data=json.dumps({}),
    )
    assert submit_response.ok, "Failed to submit CLO"
    instructor_context.close()

    return {
        "clo_id": clo_id,
        "section_outcome_id": section_outcome_id,
        "course_id": course_id,
        "instructor_email": instructor_email,
        "csrf_token": csrf_token,
    }


def _step_admin_requests_rework(admin_page, clo_id, section_outcome_id):
    """Admin navigates to audit and requests rework."""
    admin_page.goto(f"{BASE_URL}/audit-clo")
    expect(admin_page).to_have_url(f"{BASE_URL}/audit-clo")

    # Wait for JS render
    admin_page.wait_for_load_state("networkidle")
    admin_page.wait_for_timeout(500)
    admin_page.wait_for_selector("#cloListContainer", timeout=10000)

    # Click CLO row
    clo_row = admin_page.locator(f'tr[data-outcome-id="{section_outcome_id}"]')
    expect(clo_row).to_be_visible()
    clo_row.click()

    # Click Request Rework
    detail_modal = admin_page.locator("#cloDetailModal")
    expect(detail_modal).to_be_visible()
    rework_button = detail_modal.locator('button:has-text("Request Rework")')
    expect(rework_button).to_be_visible()
    rework_button.click()

    # Fill Rework form
    rework_modal = admin_page.locator("#requestReworkModal")
    expect(rework_modal).to_be_visible()

    rework_modal.locator("#feedbackComments").fill(
        "The narrative needs more detail. Please explain how students applied "
        "the second law of thermodynamics to solve practical problems. "
        "Also, consider why only 60% of students met the target."
    )
    rework_modal.locator("#sendEmailCheckbox").set_checked(True)

    # Submit
    rework_modal.locator('button:has-text("Send for Rework")').click()
    expect(rework_modal).not_to_be_visible()
    expect(detail_modal).not_to_be_visible()


def _step_verify_rework_status(admin_page, clo_id, section_outcome_id, csrf_token):
    """Verify status updated to approval_pending/needs_rework."""
    # Check UI list
    filter_select = admin_page.locator("#statusFilter")
    filter_select.select_option("approval_pending")
    admin_page.wait_for_timeout(1000)

    clo_row = admin_page.locator(f'tr[data-outcome-id="{section_outcome_id}"]')
    expect(clo_row).to_be_visible()
    expect(clo_row.locator("td").nth(0)).to_contain_text("Needs Rework")

    # Check API
    outcome_response = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{section_outcome_id}/audit-details",
        headers={"X-CSRFToken": csrf_token if csrf_token else ""},
    )
    assert outcome_response.ok
    outcome_data = outcome_response.json()
    outcome_data = outcome_data.get("outcome", outcome_data)

    assert outcome_data.get("status") == "approval_pending"
    assert outcome_data.get("approval_status") == "needs_rework"
    assert "second law" in (outcome_data.get("feedback_comments") or "")


def _step_instructor_resubmits(page, course_id, clo_id):
    """Instructor sees feedback, edits, and resubmits."""
    page.goto(f"{BASE_URL}/assessments")
    page.wait_for_selector(
        f"#courseSelect option[value='{course_id}']", state="attached", timeout=10000
    )
    page.select_option("#courseSelect", value=course_id)

    page.wait_for_selector(".outcomes-list .row[data-outcome-id]", timeout=10000)

    clo_row = page.locator(f".row[data-outcome-id='{clo_id}']")
    expect(clo_row).to_be_visible()

    # Check warning icon and feedback
    expect(clo_row.locator(".fa-exclamation-triangle")).to_be_visible()
    expect(clo_row.locator(".text-warning.small")).to_contain_text("second law")

    # Update tool
    tool_input = clo_row.locator("input[data-field='assessment_tool']")
    tool_input.fill("Final Exam")
    tool_input.blur()
    page.wait_for_timeout(1000)

    # Submit course
    page.locator("#courseStudentsPassed").fill("18")
    page.locator("#courseStudentsDFIC").fill("2")
    submit_btn = page.locator("#submitCourseBtn")

    page.once("dialog", lambda dialog: dialog.accept())
    submit_btn.click()
    page.wait_for_timeout(2000)

    # Verify status cleared locally
    expect(clo_row.locator(".fa-exclamation-triangle")).not_to_be_visible()
    expect(page.locator(".card-body:has-text('Awaiting Approval') .fs-4")).to_have_text(
        "1"
    )


@pytest.mark.e2e
def test_clo_rework_feedback_workflow(authenticated_institution_admin_page: Page):
    """
    Test admin rework request workflow with feedback and email notification.

    Steps:
    1. Create test CLO in AWAITING_APPROVAL status
    2. Admin requests rework with feedback
    3. Verify status changes to APPROVAL_PENDING
    4. Instructor sees feedback
    5. Instructor addresses feedback and resubmits
    6. Verify status returns to AWAITING_APPROVAL
    """
    admin_page = authenticated_institution_admin_page
    institution_id = get_institution_id_from_user(admin_page)

    # Step 1: Data Setup
    data = _setup_rework_test_data(admin_page, institution_id)
    clo_id = data["clo_id"]
    course_id = data["course_id"]
    csrf_token = data["csrf_token"]

    # Step 2: Request Rework
    section_outcome_id = data["section_outcome_id"]
    _step_admin_requests_rework(admin_page, clo_id, section_outcome_id)

    # Step 3: Verify Status
    _step_verify_rework_status(admin_page, clo_id, section_outcome_id, csrf_token)

    # Step 4: Instructor Resubmit
    instructor_page = admin_page.context.new_page()
    login_as_user(instructor_page, BASE_URL, data["instructor_email"], "TestUser123!")

    _step_instructor_resubmits(instructor_page, course_id, clo_id)

    instructor_page.close()
