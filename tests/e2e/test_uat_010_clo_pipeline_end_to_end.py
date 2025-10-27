"""
UAT-010: CLO Pipeline End-to-End

Test the complete CLO lifecycle from creation to approval.

Full lifecycle test:
1. Create course section with CLOs (UNASSIGNED)
2. Assign instructor (→ ASSIGNED)
3. Instructor edits (→ IN_PROGRESS)
4. Instructor submits (→ AWAITING_APPROVAL)
5. Admin requests rework (→ APPROVAL_PENDING)
6. Instructor addresses and resubmits (→ AWAITING_APPROVAL)
7. Admin approves (→ APPROVED)
8. Verify audit trail in database
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
def test_clo_pipeline_end_to_end(authenticated_institution_admin_page: Page):
    """
    Test complete CLO lifecycle through all states.

    Validates the full workflow from UNASSIGNED to APPROVED with audit trail.
    """
    admin_page = authenticated_institution_admin_page

    # Get institution ID
    institution_id = get_institution_id_from_user(admin_page)

    # Get CSRF token
    csrf_token = admin_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # === STEP 1: Create course section with CLOs (UNASSIGNED) ===

    # Create program
    program_response = admin_page.request.post(
        f"{BASE_URL}/api/programs",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data=json.dumps(
            {
                "name": "UAT-010 Computer Science",
                "short_name": "UAT010-CS",
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
                "course_number": "UAT010-DS101",
                "course_title": "UAT-010 Data Structures",
                "department": "Computer Science",
                "institution_id": institution_id,
                "program_id": program_id,
            }
        ),
    )
    assert course_response.ok
    course_id = course_response.json()["course_id"]

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
    assert term_response.ok
    term_id = term_response.json()["term_id"]

    # Create course section WITHOUT instructor (UNASSIGNED state)
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
                "institution_id": institution_id,
                # Note: No instructor_id - CLOs will be UNASSIGNED
            }
        ),
    )
    assert section_response.ok
    section_id = section_response.json()["offering_id"]

    # Create CLO for the course (will be UNASSIGNED initially)
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
                "description": "Implement and analyze various data structures",
                "status": "unassigned",  # Explicitly UNASSIGNED
            }
        ),
    )
    assert clo_response.ok
    clo_id = clo_response.json()["outcome_id"]

    # Verify CLO is UNASSIGNED via API
    outcome = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{clo_id}/audit-details",
        headers={"X-CSRFToken": csrf_token if csrf_token else ""},
    )
    assert outcome.ok
    assert outcome.json()["outcome"]["status"] == "unassigned"

    # === STEP 2: Assign instructor (→ ASSIGNED) ===

    # Create instructor
    instructor = create_test_user_via_api(
        admin_page=admin_page,
        base_url=BASE_URL,
        email="uat010.instructor@test.com",
        first_name="UAT010",
        last_name="Instructor",
        role="instructor",
        institution_id=institution_id,
        program_ids=[program_id],
    )
    instructor_id = instructor["user_id"]

    # Create a course section with the instructor assigned
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

    # Update CLO status to ASSIGNED
    update_clo = admin_page.request.put(
        f"{BASE_URL}/api/outcomes/{clo_id}",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data=json.dumps({"status": "assigned"}),
    )
    assert update_clo.ok

    # Verify CLO is ASSIGNED
    outcome = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{clo_id}/audit-details",
        headers={"X-CSRFToken": csrf_token if csrf_token else ""},
    )
    assert outcome.ok
    assert outcome.json()["outcome"]["status"] == "assigned"

    # === STEP 3: Instructor edits (→ IN_PROGRESS) ===

    # Create separate browser context for instructor to avoid session conflicts
    instructor_context = admin_page.context.browser.new_context()
    instructor_page = instructor_context.new_page()
    login_as_user(
        instructor_page, BASE_URL, "uat010.instructor@test.com", "TestUser123!"
    )

    instructor_page.goto(f"{BASE_URL}/assessments")
    instructor_page.wait_for_selector("#courseSelect", timeout=5000)
    instructor_page.select_option("#courseSelect", value=course_id)
    instructor_page.wait_for_selector(
        f'button[data-outcome-id="{clo_id}"]', timeout=5000
    )

    # Click "Update Assessment" button to open modal
    instructor_page.click(f'button.update-assessment-btn[data-outcome-id="{clo_id}"]')
    instructor_page.wait_for_selector(
        "#updateAssessmentModal", state="visible", timeout=5000
    )

    # Fill assessment data in modal
    instructor_page.fill("#studentsAssessed", "35")
    instructor_page.fill("#studentsMeetingTarget", "30")
    instructor_page.fill(
        "#assessmentNarrative",
        "Initial narrative: Students completed data structure implementations.",
    )

    # Save changes (triggers auto-mark IN_PROGRESS)
    instructor_page.click("#updateAssessmentModal button:has-text('Save Assessment')")
    instructor_page.wait_for_timeout(
        1000
    )  # Wait for modal to close and alert to appear

    # Verify status is IN_PROGRESS
    outcome = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{clo_id}/audit-details",
        headers={"X-CSRFToken": csrf_token if csrf_token else ""},
    )
    assert outcome.ok
    assert outcome.json()["outcome"]["status"] == "in_progress"

    # === STEP 4: Instructor submits (→ AWAITING_APPROVAL) ===

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
    assert submit_response.ok

    # Verify status is AWAITING_APPROVAL
    outcome = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{clo_id}/audit-details",
        headers={"X-CSRFToken": csrf_token if csrf_token else ""},
    )
    assert outcome.ok
    outcome_data = outcome.json()["outcome"]
    assert outcome_data["status"] == "awaiting_approval"
    assert outcome_data["submitted_at"] is not None
    assert outcome_data["submitted_by_user_id"] == instructor_id

    # === STEP 5: Admin requests rework (→ APPROVAL_PENDING) ===

    admin_page.goto(f"{BASE_URL}/audit-clo")
    admin_page.wait_for_load_state("networkidle")
    admin_page.wait_for_selector("#cloListContainer", timeout=10000)

    # Find CLO and open detail modal
    clo_row = admin_page.locator(f'tr[data-outcome-id="{clo_id}"]')
    clo_row.click()

    modal = admin_page.locator("#cloDetailModal")
    expect(modal).to_be_visible()

    # Request rework
    rework_button = modal.locator('button:has-text("Request Rework")')
    rework_button.click()

    # Wait for rework modal to open
    rework_modal = admin_page.locator("#requestReworkModal")
    expect(rework_modal).to_be_visible()

    # Fill feedback
    feedback_textarea = rework_modal.locator("#feedbackComments")
    feedback_textarea.fill(
        "Please provide more detail about which specific data structures were "
        "implemented and how students analyzed their time/space complexity."
    )

    # Submit rework
    submit_button = rework_modal.locator('button:has-text("Send for Rework")')
    submit_button.click()

    # Wait for success
    admin_page.wait_for_selector(".alert", timeout=5000)

    # Verify status is APPROVAL_PENDING
    outcome = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{clo_id}/audit-details",
        headers={"X-CSRFToken": csrf_token if csrf_token else ""},
    )
    assert outcome.ok
    outcome_data = outcome.json()["outcome"]
    assert outcome_data["status"] == "approval_pending"
    assert outcome_data["approval_status"] == "needs_rework"
    assert outcome_data["feedback_comments"] is not None
    assert outcome_data["feedback_provided_at"] is not None

    # === STEP 6: Instructor addresses and resubmits (→ AWAITING_APPROVAL) ===

    instructor_page.goto(f"{BASE_URL}/assessments")
    instructor_page.wait_for_selector("#courseSelect", timeout=5000)
    instructor_page.select_option("#courseSelect", value=course_id)
    instructor_page.wait_for_selector(
        f'button[data-outcome-id="{clo_id}"]', timeout=5000
    )

    # Verify feedback is visible (it's in an alert div within the list-group-item)
    feedback_alert = instructor_page.locator(
        ".alert-warning:has-text('Feedback Requested')"
    )
    expect(feedback_alert).to_be_visible()

    # Click "Update Assessment" button to open modal and address feedback
    instructor_page.click(f'button.update-assessment-btn[data-outcome-id="{clo_id}"]')
    instructor_page.wait_for_selector(
        "#updateAssessmentModal", state="visible", timeout=5000
    )

    # Address feedback with improved narrative
    instructor_page.fill(
        "#assessmentNarrative",
        "Students implemented arrays, linked lists, stacks, queues, trees, and hash tables. "
        "They analyzed time complexity (O(1), O(n), O(log n)) and space complexity for each "
        "data structure. Performance comparisons were conducted using empirical testing with "
        "various dataset sizes. 86% of students successfully analyzed both time and space "
        "trade-offs in their final projects.",
    )

    # Save changes
    instructor_page.click("#updateAssessmentModal button:has-text('Save Assessment')")
    instructor_page.wait_for_timeout(1000)  # Wait for modal to close

    # Resubmit
    instructor_csrf = instructor_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    resubmit_response = instructor_page.request.post(
        f"{BASE_URL}/api/outcomes/{clo_id}/submit",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": instructor_csrf if instructor_csrf else "",
        },
        data=json.dumps({}),
    )
    assert resubmit_response.ok

    # Verify status is AWAITING_APPROVAL again
    outcome = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{clo_id}/audit-details",
        headers={"X-CSRFToken": csrf_token if csrf_token else ""},
    )
    assert outcome.ok
    assert outcome.json()["outcome"]["status"] == "awaiting_approval"

    # === STEP 7: Admin approves (→ APPROVED) ===

    admin_page.goto(f"{BASE_URL}/audit-clo")
    admin_page.wait_for_load_state("networkidle")
    admin_page.wait_for_selector("#cloListContainer", timeout=10000)

    # Find and open CLO
    clo_row = admin_page.locator(f'tr[data-outcome-id="{clo_id}"]')
    clo_row.click()

    modal = admin_page.locator("#cloDetailModal")
    expect(modal).to_be_visible()

    # Approve
    approve_button = modal.locator('button:has-text("Approve")')
    admin_page.once("dialog", lambda dialog: dialog.accept())
    approve_button.click()

    # Wait for success
    admin_page.wait_for_selector(".alert", timeout=5000)

    # === STEP 8: Verify audit trail in database ===

    outcome = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{clo_id}/audit-details",
        headers={"X-CSRFToken": csrf_token if csrf_token else ""},
    )
    assert outcome.ok
    outcome_data = outcome.json()["outcome"]

    # Verify final state
    assert outcome_data["status"] == "approved"
    assert outcome_data["approval_status"] == "approved"

    # Verify audit trail
    assert outcome_data["submitted_at"] is not None
    assert outcome_data["submitted_by_user_id"] == instructor_id
    assert outcome_data["reviewed_at"] is not None
    assert outcome_data["reviewed_by_user_id"] is not None
    assert outcome_data["feedback_comments"] is not None  # Feedback preserved
    assert outcome_data["feedback_provided_at"] is not None

    # Verify improved narrative is present
    assert "arrays" in outcome_data["narrative"]
    assert "O(1)" in outcome_data["narrative"] or "O(n)" in outcome_data["narrative"]
    assert "86%" in outcome_data["narrative"]

    # === Complete lifecycle verified ===
    # UNASSIGNED → ASSIGNED → IN_PROGRESS → AWAITING_APPROVAL →
    # APPROVAL_PENDING → AWAITING_APPROVAL → APPROVED

    # Cleanup
    instructor_page.close()
