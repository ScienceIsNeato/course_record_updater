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

    # Create course section with instructor
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
    assert section_response.ok, f"Failed to create section: {section_response.text()}"
    section_data = section_response.json()
    section_id = section_data["offering_id"]

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
    instructor_page = admin_page.context.new_page()
    login_as_user(
        instructor_page, BASE_URL, "uat009.instructor@test.com", "TestUser123!"
    )

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

    # Close instructor page for now
    instructor_page.close()

    # === STEP 2: Admin navigates to audit interface ===
    admin_page.goto(f"{BASE_URL}/audit-clo")
    expect(admin_page).to_have_url(f"{BASE_URL}/audit-clo")

    # Wait for CLO list to load
    admin_page.wait_for_selector("#cloListContainer", timeout=5000)

    # === STEP 3: Select CLO and open detail modal ===
    clo_row = admin_page.locator(f'tr[data-outcome-id="{clo_id}"]')
    expect(clo_row).to_be_visible()
    clo_row.click()

    # Wait for modal
    modal = admin_page.locator("#cloDetailModal")
    expect(modal).to_be_visible()

    # === STEP 4: Click "Request Rework" button ===
    rework_button = modal.locator('button:has-text("Request Rework")')
    expect(rework_button).to_be_visible()
    rework_button.click()

    # Wait for rework feedback form to appear
    feedback_form = modal.locator("#reworkFeedbackForm")
    expect(feedback_form).to_be_visible()

    # === STEP 5: Enter feedback comments ===
    feedback_textarea = modal.locator("#feedbackComments")
    feedback_textarea.fill(
        "The narrative needs more detail. Please explain how students applied "
        "the second law of thermodynamics to solve practical problems. "
        "Also, consider why only 60% of students met the target."
    )

    # === STEP 6: Check "Send email notification" ===
    email_checkbox = modal.locator("#sendEmailNotification")
    email_checkbox.check()

    # === STEP 7: Submit rework request ===
    submit_button = modal.locator('button:has-text("Send for Rework")')
    submit_button.click()

    # Wait for success alert
    admin_page.wait_for_selector(".alert", timeout=5000)
    alert = admin_page.locator(".alert")
    expect(alert).to_contain_text("Rework request sent")

    # Modal should close
    expect(modal).not_to_be_visible()

    # === STEP 8: Verify CLO status is APPROVAL_PENDING ===
    # Change filter to show approval_pending CLOs
    filter_select = admin_page.locator("#statusFilter")
    filter_select.select_option("approval_pending")

    # Wait for list to update
    admin_page.wait_for_timeout(1000)

    # Find our CLO
    clo_row = admin_page.locator(f'tr[data-outcome-id="{clo_id}"]')
    expect(clo_row).to_be_visible()

    # Verify status shows "Needs Rework"
    status_cell = clo_row.locator("td").nth(4)
    expect(status_cell).to_contain_text("Needs Rework")

    # === STEP 9: Verify feedback is stored via API ===
    outcome_response = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{clo_id}/audit-details",
        headers={
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
    )
    assert outcome_response.ok, f"Failed to get outcome: {outcome_response.text()}"
    outcome_data = outcome_response.json()

    assert outcome_data["status"] == "approval_pending"
    assert outcome_data["approval_status"] == "needs_rework"
    assert outcome_data["feedback_comments"] is not None
    assert "second law" in outcome_data["feedback_comments"]
    assert outcome_data["feedback_provided_at"] is not None

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

    # Verify status badge shows "Needs Rework"
    status_badge = instructor_page.locator(f"#clo-status-{clo_id}")
    expect(status_badge).to_have_text("Needs Rework")

    # Verify feedback is displayed
    feedback_alert = instructor_page.locator(f"#feedback-alert-{clo_id}")
    expect(feedback_alert).to_be_visible()
    expect(feedback_alert).to_contain_text("second law")

    # === STEP 11: Instructor addresses feedback and updates narrative ===
    instructor_page.fill(
        f"#narrative_{clo_id}",
        "Students applied the second law of thermodynamics to analyze heat engine "
        "efficiency in practical scenarios. They calculated Carnot efficiency for "
        "various temperature differentials. The 60% target achievement is due to "
        "calculation errors on the final exam, which will be addressed with additional "
        "problem sets next semester.",
    )

    # Save changes
    instructor_page.click("button:has-text('Save Changes')")
    instructor_page.wait_for_selector(".alert-success", timeout=5000)

    # === STEP 12: Instructor resubmits CLO ===
    # Get new CSRF token
    instructor_csrf = instructor_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Click submit button
    submit_button = instructor_page.locator(f"#submit-clo-{clo_id}")
    expect(submit_button).to_be_visible()
    instructor_page.once("dialog", lambda dialog: dialog.accept())
    submit_button.click()

    # Wait for success
    instructor_page.wait_for_selector(".alert-success", timeout=5000)

    # === STEP 13: Verify status is back to AWAITING_APPROVAL ===
    instructor_page.reload()
    instructor_page.select_option("#sectionSelect", value=section_id)
    instructor_page.wait_for_selector(f"#outcome-{clo_id}", timeout=5000)

    status_badge = instructor_page.locator(f"#clo-status-{clo_id}")
    expect(status_badge).to_have_text("Awaiting Approval")

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
