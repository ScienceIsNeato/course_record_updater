"""
E2E: CLO Pipeline End-to-End

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


def _step_1_create_structure(admin_page, institution_id, csrf_token):
    """Create program, course, term, section, and CLO."""
    # Create program
    program_response = admin_page.request.post(
        f"{BASE_URL}/api/programs",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data=json.dumps(
            {
                "name": "E2E test: Computer Science",
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
                "course_title": "E2E test: Data Structures",
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

    return program_id, course_id, section_id, clo_id


def _step_2_assign_instructor(
    admin_page, institution_id, program_id, section_id, clo_id, csrf_token
):
    """Create instructor and assign to section."""
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

    return instructor_id


def _step_3_instructor_edits(
    instructor_page, course_id, clo_id, admin_page, csrf_token
):
    """Instructor edits CLO (IN_PROGRESS)."""
    instructor_page.goto(f"{BASE_URL}/assessments")
    # Select course - wait for option to be present first
    instructor_page.wait_for_selector(
        f"#courseSelect option[value='{course_id}']", state="attached", timeout=10000
    )
    instructor_page.select_option("#courseSelect", value=course_id)

    # Wait for outcomes to load
    instructor_page.wait_for_selector(
        ".outcomes-list .row[data-outcome-id]", timeout=10000
    )

    # Locate CLO row
    clo_row = instructor_page.locator(f".row[data-outcome-id='{clo_id}']")
    expect(clo_row).to_be_visible()

    # Use inline inputs
    # Fill assessment data (updated field names from CEI demo feedback)
    clo_row.locator(f"input[data-field='students_took']").fill("35")
    clo_row.locator(f"input[data-field='students_passed']").fill("30")
    clo_row.locator(f"input[data-field='assessment_tool']").fill(
        "Programming Assignment"
    )

    # Trigger blur to autosave (marks IN_PROGRESS)
    clo_row.locator(f"input[data-field='assessment_tool']").blur()
    instructor_page.wait_for_timeout(2000)

    # Verify status is IN_PROGRESS
    outcome = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{clo_id}/audit-details",
        headers={"X-CSRFToken": csrf_token if csrf_token else ""},
    )
    assert outcome.ok
    assert outcome.json()["outcome"]["status"] == "in_progress"


def _step_4_instructor_submits(
    instructor_page, clo_id, instructor_id, admin_page, csrf_token
):
    """Instructor submits CLO (AWAITING_APPROVAL)."""
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


def _step_5_admin_rework(admin_page, clo_id, csrf_token):
    """Admin requests rework (APPROVAL_PENDING)."""
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

    # Wait for modal to close and list to refresh
    admin_page.wait_for_selector("#cloDetailModal", state="hidden", timeout=5000)
    admin_page.wait_for_timeout(500)

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


def _step_6_instructor_resubmits(
    instructor_page, course_id, clo_id, admin_page, csrf_token
):
    """Instructor addresses feedback and resubmits (AWAITING_APPROVAL)."""
    instructor_page.goto(f"{BASE_URL}/assessments")
    # Robust selection
    instructor_page.wait_for_selector(
        f"#courseSelect option[value='{course_id}']", state="attached", timeout=10000
    )
    instructor_page.select_option("#courseSelect", value=course_id)

    # Wait for outcomes
    instructor_page.wait_for_selector(
        ".outcomes-list .row[data-outcome-id]", timeout=10000
    )
    clo_row = instructor_page.locator(f".row[data-outcome-id='{clo_id}']")
    expect(clo_row).to_be_visible()

    # Verify feedback is visible inline
    feedback_div = clo_row.locator(".text-warning.small")
    expect(feedback_div).to_be_visible()

    # Address feedback - inline update
    tool_input = clo_row.locator(f"input[data-field='assessment_tool']")
    tool_input.fill("Final Project")
    tool_input.blur()
    instructor_page.wait_for_timeout(1000)

    # Resubmit via Course Submission
    # Fill required course level data
    instructor_page.locator("#courseStudentsPassed").fill("30")
    instructor_page.locator("#courseStudentsDFIC").fill("5")

    # Click submit course button
    submit_btn = instructor_page.locator("#submitCourseBtn")
    expect(submit_btn).to_be_visible()

    # Handle confirmation dialog
    instructor_page.once("dialog", lambda dialog: dialog.accept())
    submit_btn.click()

    # Wait for completion
    instructor_page.wait_for_timeout(2000)

    # Verify status is AWAITING_APPROVAL again
    outcome = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{clo_id}/audit-details",
        headers={"X-CSRFToken": csrf_token if csrf_token else ""},
    )
    assert outcome.ok
    assert outcome.json()["outcome"]["status"] == "awaiting_approval"


def _step_7_admin_approves(admin_page, clo_id):
    """Admin approves (APPROVED)."""
    admin_page.goto(f"{BASE_URL}/audit-clo")
    admin_page.wait_for_load_state("networkidle")
    admin_page.wait_for_selector("#cloListContainer", timeout=10000)

    # Find and open CLO
    clo_row = admin_page.locator(f'tr[data-outcome-id="{clo_id}"]')
    clo_row.click()

    modal = admin_page.locator("#cloDetailModal")
    expect(modal).to_be_visible()

    # Approve - no dialogs expected (they were removed per UI request)
    approve_button = modal.locator('button:has-text("Approve")')
    expect(approve_button).to_be_visible()

    approve_button.click()

    # Wait for the API call to complete
    admin_page.wait_for_timeout(1500)

    # Modal should close after approval
    expect(modal).not_to_be_visible(timeout=5000)


def _verify_audit_trail(admin_page, clo_id, instructor_id, csrf_token):
    """Verify final state and audit trail."""
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

    # Verify assessment tool is present (replaces old narrative field)
    assert outcome_data["assessment_tool"] == "Final Project"
    assert outcome_data["students_took"] is not None
    assert outcome_data["students_passed"] is not None


@pytest.mark.e2e
@pytest.mark.e2e
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

    # === STEP 1: Create structure ===
    program_id, course_id, section_id, clo_id = _step_1_create_structure(
        admin_page, institution_id, csrf_token
    )

    # === STEP 2: Assign instructor ===
    instructor_id = _step_2_assign_instructor(
        admin_page, institution_id, program_id, section_id, clo_id, csrf_token
    )

    # === STEP 3: Instructor setup & edits ===
    # Create separate browser context for instructor to avoid session conflicts
    instructor_context = admin_page.context.browser.new_context()
    instructor_page = instructor_context.new_page()
    try:
        login_as_user(
            instructor_page, BASE_URL, "uat010.instructor@test.com", "TestUser123!"
        )

        _step_3_instructor_edits(
            instructor_page, course_id, clo_id, admin_page, csrf_token
        )

        # === STEP 4: Instructor submits ===
        _step_4_instructor_submits(
            instructor_page, clo_id, instructor_id, admin_page, csrf_token
        )

        # === STEP 5: Admin rework ===
        _step_5_admin_rework(admin_page, clo_id, csrf_token)

        # === STEP 6: Instructor resubmits ===
        _step_6_instructor_resubmits(
            instructor_page, course_id, clo_id, admin_page, csrf_token
        )

        # === STEP 7: Admin approves ===
        _step_7_admin_approves(admin_page, clo_id)

        # === STEP 8: Verify audit trail ===
        _verify_audit_trail(admin_page, clo_id, instructor_id, csrf_token)

    finally:
        # Cleanup
        instructor_page.close()
