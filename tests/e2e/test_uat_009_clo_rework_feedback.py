"""
UAT-009: CLO Rework Feedback Workflow

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


@pytest.mark.e2e
@pytest.mark.uat
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
                "name": "UAT-009 Engineering",
                "short_name": "UAT009-ENG",
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
                "course_number": "UAT009-THERMO101",
                "course_title": "UAT-009 Thermodynamics",
                "department": "Engineering",
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
        email="uat009.instructor@test.com",
        first_name="UAT009",
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

    # Create CLO and submit it
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
                "description": "Apply thermodynamic laws to real-world systems",
                "status": "assigned",
                "students_assessed": 30,
                "students_meeting_target": 18,
                "narrative": "Basic understanding demonstrated.",
            }
        ),
    )
    assert clo_response.ok, f"Failed to create CLO: {clo_response.text()}"
    clo_data = clo_response.json()
    clo_id = clo_data["outcome_id"]

    # Submit CLO via instructor
    instructor_context = admin_page.context.browser.new_context()
    instructor_page = instructor_context.new_page()
    login_as_user(
        instructor_page, BASE_URL, "uat009.instructor@test.com", "TestUser123!"
    )

    # Navigate to dashboard to establish session context for API calls
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
    assert submit_response.ok, f"Failed to submit CLO: {submit_response.text()}"

    # Close instructor context to ensure admin session remains active
    instructor_context.close()

    # === STEP 2: Admin navigates to audit interface ===
    admin_page.goto(f"{BASE_URL}/audit-clo")
    expect(admin_page).to_have_url(f"{BASE_URL}/audit-clo")

    # Sanity-check the audit API first to ensure data is present
    api_check = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/audit?status=awaiting_approval",
        headers={"X-CSRFToken": csrf_token if csrf_token else ""},
    )
    assert api_check.ok, f"Audit API failed: {api_check.text()}"
    api_outcomes = api_check.json().get("outcomes", [])
    assert any(
        o.get("outcome_id") == clo_id or o.get("id") == clo_id for o in api_outcomes
    ), f"Submitted CLO not present in audit list. Outcomes: {api_outcomes}"

    # Wait for page to fully load, then allow time for JS render
    admin_page.wait_for_load_state("networkidle")
    admin_page.wait_for_timeout(500)

    # Wait for CLO list to load
    admin_page.wait_for_selector("#cloListContainer", timeout=10000)

    # === STEP 3: Select CLO and open detail modal ===
    clo_row = admin_page.locator(f'tr[data-outcome-id="{clo_id}"]')
    expect(clo_row).to_be_visible()
    clo_row.click()

    # Wait for detail modal to be visible
    detail_modal = admin_page.locator("#cloDetailModal")
    expect(detail_modal).to_be_visible()

    # === STEP 4: Click "Request Rework" button ===
    rework_button = detail_modal.locator('button:has-text("Request Rework")')
    expect(rework_button).to_be_visible()
    rework_button.click()

    # Wait for rework modal to appear
    rework_modal = admin_page.locator("#requestReworkModal")
    expect(rework_modal).to_be_visible()

    # === STEP 5: Enter feedback comments ===
    feedback_textarea = rework_modal.locator("#feedbackComments")
    feedback_textarea.fill(
        "The narrative needs more detail. Please explain how students applied "
        "the second law of thermodynamics to solve practical problems. "
        "Also, consider why only 60% of students met the target."
    )

    # === STEP 6: Check "Send email notification" ===
    email_checkbox = rework_modal.locator("#sendEmailCheckbox")
    email_checkbox.set_checked(True)

    # === STEP 7: Submit rework request ===
    submit_button = rework_modal.locator('button:has-text("Send for Rework")')
    submit_button.click()

    # Rework modal should close
    expect(rework_modal).not_to_be_visible()

    # Detail modal should be hidden as well
    expect(detail_modal).not_to_be_visible()

    # === STEP 8: Verify CLO status is APPROVAL_PENDING ===
    # Change filter to show approval_pending CLOs
    filter_select = admin_page.locator("#statusFilter")
    filter_select.select_option("approval_pending")

    # Wait for list to update
    admin_page.wait_for_timeout(1000)

    # Find our CLO and verify status shows "Needs Rework" (status is first column)
    clo_row = admin_page.locator(f'tr[data-outcome-id="{clo_id}"]')
    expect(clo_row).to_be_visible()
    status_cell = clo_row.locator("td").nth(0)
    expect(status_cell).to_contain_text("Needs Rework")

    # === STEP 9: Verify feedback is stored via API ===
    outcome_response = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{clo_id}/audit-details",
        headers={
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
    )
    assert outcome_response.ok, f"Failed to get outcome: {outcome_response.text()}"
    outcome_json = outcome_response.json()
    outcome_data = outcome_json.get("outcome", outcome_json)

    assert outcome_data.get("status") == "approval_pending"
    assert outcome_data.get("approval_status") == "needs_rework"
    assert outcome_data.get("feedback_comments") is not None
    assert "second law" in (outcome_data.get("feedback_comments") or "")
    assert outcome_data.get("feedback_provided_at") is not None

    # === STEP 10: Instructor logs in and sees feedback ===
    instructor_page = admin_page.context.new_page()
    login_as_user(
        instructor_page, BASE_URL, "uat009.instructor@test.com", "TestUser123!"
    )

    instructor_page.goto(f"{BASE_URL}/assessments")
    expect(instructor_page).to_have_url(f"{BASE_URL}/assessments")

    # Select course
    instructor_page.select_option("#courseSelect", value=course_id)
    instructor_page.wait_for_selector(
        f"button[data-outcome-id='{clo_id}']", timeout=5000
    )

    # Verify status badge shows "Needs Revision" (the badge is generated inline without an ID)
    clo_card = instructor_page.locator(f'button[data-outcome-id="{clo_id}"]').locator(
        ".."
    )
    status_badge = clo_card.locator('.badge:has-text("Needs Revision")')
    expect(status_badge).to_be_visible()

    # Verify feedback is displayed in the warning alert
    feedback_alert = clo_card.locator('.alert-warning:has-text("Revision Requested")')
    expect(feedback_alert).to_be_visible()
    expect(feedback_alert).to_contain_text("second law")

    # === STEP 11: Instructor addresses feedback and updates narrative ===
    # Click "Update Assessment" button to open modal
    update_button = instructor_page.locator(
        f'button.update-assessment-btn[data-outcome-id="{clo_id}"]'
    )
    update_button.click()
    instructor_page.wait_for_selector(
        "#updateAssessmentModal", state="visible", timeout=5000
    )

    # Update narrative with feedback addressed
    instructor_page.fill(
        "#assessmentNarrative",
        "Students applied the second law of thermodynamics to analyze heat engine "
        "efficiency in practical scenarios. They calculated Carnot efficiency for "
        "various temperature differentials. The 60% target achievement is due to "
        "calculation errors on the final exam, which will be addressed with additional "
        "problem sets next semester.",
    )

    # Save changes (submit the form)
    instructor_page.click("#updateAssessmentForm button[type='submit']")
    instructor_page.wait_for_selector(
        "#updateAssessmentModal", state="hidden", timeout=5000
    )

    # === STEP 12: Instructor resubmits CLO ===
    # Click submit button
    submit_button = instructor_page.locator(
        f'.submit-clo-btn[data-outcome-id="{clo_id}"]'
    )
    expect(submit_button).to_be_visible()
    instructor_page.once("dialog", lambda dialog: dialog.accept())
    submit_button.click()

    # Wait briefly for status to update
    instructor_page.wait_for_timeout(500)

    # === STEP 13: Verify status is back to AWAITING_APPROVAL ===
    # Verify the badge changed back to "Pending Review"
    status_badge = clo_card.locator('.badge:has-text("Pending Review")')
    expect(status_badge).to_be_visible()

    # Verify via API
    outcome_response = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{clo_id}/audit-details",
        headers={
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
    )
    assert outcome_response.ok, f"Failed to get outcome: {outcome_response.text()}"
    outcome_data = outcome_response.json()

    assert outcome_data["status"] == "awaiting_approval"
    assert outcome_data["approval_status"] == "pending"

    # Cleanup
    instructor_page.close()
