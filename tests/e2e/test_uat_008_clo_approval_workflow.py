"""
UAT-008: CLO Approval Workflow

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


@pytest.mark.e2e
@pytest.mark.uat
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

    # Get institution ID from admin user
    institution_id = get_institution_id_from_user(admin_page)

    # === STEP 1: Create test data via API ===

    # Get CSRF token
    csrf_token = admin_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Create program
    program_response = admin_page.request.post(
        f"{BASE_URL}/api/programs",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data=json.dumps(
            {
                "name": "UAT-008 Business Administration",
                "short_name": "UAT008-BA",
                "institution_id": institution_id,
            }
        ),
    )
    assert program_response.ok, f"Failed to create program: {program_response.text()}"
    program_data = program_response.json()
    program_id = program_data["program_id"]

    # Create course
    course_response = admin_page.request.post(
        f"{BASE_URL}/api/courses",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
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
    course_data = course_response.json()
    course_id = course_data["course_id"]

    # Create instructor
    instructor = create_test_user_via_api(
        admin_page=admin_page,
        base_url=BASE_URL,
        email="uat008.instructor@test.com",
        first_name="UAT008",
        last_name="Instructor",
        role="instructor",
        institution_id=institution_id,
        program_ids=[program_id],
    )
    instructor_id = instructor["user_id"]

    # Create term for the offering
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
                "assessment_due_date": "2024-12-20",
                "institution_id": institution_id,
            }
        ),
    )
    assert term_response.ok, f"Failed to create term: {term_response.text()}"
    term_id = term_response.json()["term_id"]

    # Create course offering
    section_response = admin_page.request.post(
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
    assert section_response.ok, f"Failed to create offering: {section_response.text()}"
    section_data = section_response.json()
    section_id = section_data["offering_id"]

    # Create explicit section linked to offering and instructor
    create_section_response = admin_page.request.post(
        f"{BASE_URL}/api/sections",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data=json.dumps(
            {
                "offering_id": section_id,
                "section_number": "001",
                "instructor_id": instructor_id,
                "status": "open",
            }
        ),
    )
    assert (
        create_section_response.ok
    ), f"Failed to create section: {create_section_response.text()}"

    # Create CLO in ASSIGNED status, then submit it via API
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
                "description": "Understand marketing segmentation strategies",
                "status": "assigned",
                "students_assessed": 25,
                "students_meeting_target": 22,
                "narrative": "Students showed good understanding of segmentation.",
            }
        ),
    )
    assert clo_response.ok, f"Failed to create CLO: {clo_response.text()}"
    clo_data = clo_response.json()
    clo_id = clo_data["outcome_id"]

    # Submit CLO via API to set it to AWAITING_APPROVAL
    # Use separate browser context for instructor to avoid overwriting admin session
    instructor_context = admin_page.context.browser.new_context()
    instructor_page = instructor_context.new_page()
    login_as_user(
        instructor_page, BASE_URL, "uat008.instructor@test.com", "TestUser123!"
    )

    # Navigate to dashboard to establish session context for API calls
    instructor_page.goto(f"{BASE_URL}/dashboard")
    instructor_page.wait_for_load_state("networkidle")

    # Get CSRF token for instructor
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
    assert submit_response.ok, f"Failed to submit CLO: {submit_response.text()}"

    instructor_context.close()

    # === STEP 2: Admin navigates to audit interface ===
    admin_page.goto(f"{BASE_URL}/audit-clo")
    expect(admin_page).to_have_url(f"{BASE_URL}/audit-clo")

    # Sanity check: ensure the audit API returns our submitted CLO before relying on UI
    api_check = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/audit?status=awaiting_approval",
        headers={"X-CSRFToken": csrf_token if csrf_token else ""},
    )
    assert api_check.ok, f"Audit API failed: {api_check.text()}"
    api_outcomes = api_check.json().get("outcomes", [])
    assert any(
        o.get("outcome_id") == clo_id or o.get("id") == clo_id for o in api_outcomes
    ), f"Submitted CLO not present in audit list. Outcomes: {api_outcomes}"

    # Wait for page to fully load, then give JS time to render list
    admin_page.wait_for_load_state("networkidle")
    admin_page.wait_for_timeout(500)

    # Wait for CLO list to load
    admin_page.wait_for_selector("#cloListContainer", timeout=10000)

    # === STEP 3: Verify CLO appears in the list ===
    # Check that our CLO is visible
    clo_row = admin_page.locator(f'tr[data-outcome-id="{clo_id}"]')
    expect(clo_row).to_be_visible()

    # Verify it shows as "Awaiting Approval" (Status is first column)
    status_cell = clo_row.locator("td").nth(0)
    expect(status_cell).to_contain_text("Awaiting Approval")

    # === STEP 5: Click CLO row to open detail modal ===
    clo_row.click()

    # Wait for modal to open
    modal = admin_page.locator("#cloDetailModal")
    expect(modal).to_be_visible()

    # Verify CLO details in modal using visible content
    expect(modal).to_contain_text("UAT008-MKT101")
    expect(modal).to_contain_text("CLO Number: 1")
    expect(modal).to_contain_text("marketing segmentation")

    # === STEP 6: Click "Approve" button ===
    approve_button = modal.locator('button:has-text("Approve")')
    expect(approve_button).to_be_visible()

    # Set up dialog handlers for both confirmation and success alert
    dialog_messages = []

    def handle_dialog(dialog):
        dialog_messages.append(dialog.message)
        dialog.accept()

    admin_page.on("dialog", handle_dialog)
    approve_button.click()

    # Wait briefly for the dialogs to appear and be handled
    admin_page.wait_for_timeout(1000)

    # Verify we got both dialogs (confirmation + success)
    assert (
        len(dialog_messages) >= 2
    ), f"Expected 2 dialogs, got {len(dialog_messages)}: {dialog_messages}"
    assert "Approve this CLO" in dialog_messages[0]
    assert "approved successfully" in dialog_messages[1]

    # Modal should close after approval
    expect(modal).not_to_be_visible()

    # === STEP 7: Verify CLO status is APPROVED ===
    # Reload the audit page
    admin_page.goto(f"{BASE_URL}/audit-clo")
    admin_page.wait_for_selector("#cloListContainer", timeout=5000)

    # Change filter to show approved CLOs
    filter_select = admin_page.locator("#statusFilter")
    filter_select.select_option("approved")

    # Wait for list to update
    admin_page.wait_for_timeout(1000)

    # Find our CLO in the approved list
    clo_row = admin_page.locator(f'tr[data-outcome-id="{clo_id}"]')
    expect(clo_row).to_be_visible()

    # Verify status shows "Approved" (status is column 0)
    status_cell = clo_row.locator("td").nth(0)
    expect(status_cell).to_contain_text("Approved")

    # === STEP 8: Verify via API that review timestamp is set ===
    outcome_response = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{clo_id}/audit-details",
        headers={
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
    )
    assert outcome_response.ok, f"Failed to get outcome: {outcome_response.text()}"
    response_data = outcome_response.json()
    outcome_data = response_data["outcome"]  # API nests data under "outcome" key

    assert outcome_data["status"] == "approved"
    assert outcome_data["reviewed_at"] is not None
    assert outcome_data["reviewed_by_user_id"] is not None
    assert outcome_data["approval_status"] == "approved"
