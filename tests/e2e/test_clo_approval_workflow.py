"""
E2E: CLO Approval Workflow

Test the admin workflow for approving CLOs.

Workflow:
1. Seed test data: CLOs in AWAITING_APPROVAL status
2. Admin logs in
3. Navigate to audit dashboard panel
4. Open audit interface
5. Select CLO from list
6. Click "Approve"
7. Verify status = APPROVED, reviewed_at set
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


def _setup_approval_test_data(admin_page, institution_id):
    """Create all necessary test data via API."""
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
                "name": "UAT-008 Business Administration",
                "short_name": "UAT008-BA",
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
                "course_number": "UAT008-MKT101",
                "course_title": "UAT-008 Marketing Fundamentals",
                "department": "Business",
                "institution_id": institution_id,
                "program_id": program_id,
            }
        ),
    )
    assert course_response.ok, f"Failed to create course: {course_response.text()}"
    course_id = course_response.json()["course_id"]

    # Create instructor
    instructor_email = "uat008.instructor@test.com"
    instructor = create_test_user_via_api(
        admin_page=admin_page,
        base_url=BASE_URL,
        email=instructor_email,
        first_name="UAT008",
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
                "description": "Understand marketing segmentation strategies",
                "status": "assigned",
                "students_took": 25,
                "students_passed": 22,
                "assessment_tool": "Midterm Exam",
            }
        ),
    )
    assert clo_response.ok, f"Failed to create CLO: {clo_response.text()}"
    clo_id = clo_response.json()["outcome_id"]

    # Submit CLO via instructor context
    instructor_context = admin_page.context.browser.new_context()
    instructor_page = instructor_context.new_page()
    login_as_user(instructor_page, BASE_URL, instructor_email, "TestUser123!")

    instructor_page.goto(f"{BASE_URL}/dashboard")
    instructor_page.wait_for_load_state("networkidle")

    instructor_csrf = instructor_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    submit_response = instructor_page.request.post(
        f"{BASE_URL}/api/outcomes/{clo_id}/submit",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": instructor_csrf if instructor_csrf else "",
        },
        data=json.dumps({}),
    )
    assert submit_response.ok, "Failed to submit CLO"
    instructor_context.close()

    return clo_id, csrf_token


def _step_perform_approval(admin_page, clo_id, csrf_token):
    """Navigate to audit, verify item exists, and approve it."""
    admin_page.goto(f"{BASE_URL}/audit-clo")
    expect(admin_page).to_have_url(f"{BASE_URL}/audit-clo")

    # API check
    api_check = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/audit?status=awaiting_approval",
        headers={"X-CSRFToken": csrf_token if csrf_token else ""},
    )
    assert api_check.ok, f"Audit API failed: {api_check.text()}"
    api_outcomes = api_check.json().get("outcomes", [])
    assert any(
        o.get("outcome_id") == clo_id or o.get("id") == clo_id for o in api_outcomes
    ), f"Submitted CLO not present in audit list: {api_outcomes}"

    # Wait for UI
    admin_page.wait_for_load_state("networkidle")
    admin_page.wait_for_timeout(500)
    admin_page.wait_for_selector("#cloListContainer", timeout=10000)

    # Click CLO row
    clo_row = admin_page.locator(f'tr[data-outcome-id="{clo_id}"]')
    expect(clo_row).to_be_visible()
    expect(clo_row.locator("td").nth(0)).to_contain_text("Awaiting Approval")
    clo_row.click()

    # Approve in modal
    modal = admin_page.locator("#cloDetailModal")
    expect(modal).to_be_visible()
    expect(modal).to_contain_text("UAT008-MKT101")

    approve_button = modal.locator('button:has-text("Approve")')
    expect(approve_button).to_be_visible()
    approve_button.click()

    admin_page.wait_for_timeout(1500)
    expect(modal).not_to_be_visible()


def _step_verify_approval_status(admin_page, clo_id, csrf_token):
    """Verify status updated to APPROVED and timestamp set."""
    # Check UI
    admin_page.goto(f"{BASE_URL}/audit-clo")
    admin_page.wait_for_selector("#cloListContainer", timeout=5000)

    filter_select = admin_page.locator("#statusFilter")
    filter_select.select_option("approved")
    admin_page.wait_for_timeout(1000)

    clo_row = admin_page.locator(f'tr[data-outcome-id="{clo_id}"]')
    expect(clo_row).to_be_visible()
    expect(clo_row.locator("td").nth(0)).to_contain_text("Approved")

    # Check API
    outcome_response = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{clo_id}/audit-details",
        headers={"X-CSRFToken": csrf_token if csrf_token else ""},
    )
    assert outcome_response.ok
    response_data = outcome_response.json()
    outcome_data = response_data["outcome"]

    assert outcome_data["status"] == "approved"
    assert outcome_data["reviewed_at"] is not None
    assert outcome_data["reviewed_by_user_id"] is not None
    assert outcome_data["approval_status"] == "approved"


@pytest.mark.e2e
@pytest.mark.e2e
def test_clo_approval_workflow(authenticated_institution_admin_page: Page):
    """
    Test admin approval workflow for submitted CLOs.

    Steps:
    1. Create test CLO in AWAITING_APPROVAL status
    2. Admin logs in and navigates to audit interface
    3. Admin selects CLO and approves it
    4. Verify CLO status is APPROVED with review timestamp
    """
    admin_page = authenticated_institution_admin_page
    institution_id = get_institution_id_from_user(admin_page)

    # Step 1: Create Data
    clo_id, csrf_token = _setup_approval_test_data(admin_page, institution_id)

    # Step 2: Approve
    _step_perform_approval(admin_page, clo_id, csrf_token)

    # Step 3: Verify
    _step_verify_approval_status(admin_page, clo_id, csrf_token)
