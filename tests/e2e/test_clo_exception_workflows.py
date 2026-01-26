"""
E2E: CLO Action Workflows (Rework, NCI, Reopen)

Tests the secondary admin workflows for CLOs.
"""

import json

import pytest
from playwright.sync_api import Page, expect

from src.utils.constants import GENERIC_PASSWORD
from tests.e2e.conftest import BASE_URL
from tests.e2e.test_helpers import (
    create_test_user_via_api,
    get_institution_id_from_user,
    login_as_user,
)

# ----------------------------------------------------------------------
# Setup Helper (reused/adapted from approval workflow)
# ----------------------------------------------------------------------


def _setup_clo_data(admin_page, institution_id, clo_status="assigned"):
    """
    Create a complete hierarchy: Program -> Course -> Term -> Offering -> Section -> CLO.

    Args:
        admin_page: Authenticated admin page
        institution_id: ID of the institution
        clo_status: Initial status of the created CLO (default: "assigned")

    Returns:
        dict: A dictionary containing IDs and tokens:
              {
                  "course_id": ...,
                  "term_id": ...,
                  "section_outcome_id": ...,
                  "clo_id": ... (template ID),
                  "csrf_token": ...,
                  "admin_header": ... (headers dict),
                  "instructor_email": ...,
                  "instructor_password": ...
              }
    """
    csrf_token = admin_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )
    headers = {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf_token if csrf_token else "",
    }

    # 1. Create Program
    program_resp = admin_page.request.post(
        f"{BASE_URL}/api/programs",
        headers=headers,
        data=json.dumps(
            {
                "name": "TEST-ACTIONS-PROG",
                "short_name": "TEST-ACT",
                "institution_id": institution_id,
            }
        ),
    )
    assert program_resp.ok, "Failed to create program"
    program_id = program_resp.json()["program_id"]

    # 2. Create Course
    course_resp = admin_page.request.post(
        f"{BASE_URL}/api/courses",
        headers=headers,
        data=json.dumps(
            {
                "course_number": "TEST-101",
                "course_title": "Test Actions 101",
                "department": "Testing",
                "institution_id": institution_id,
                "program_id": program_id,
            }
        ),
    )
    assert course_resp.ok, "Failed to create course"
    course_id = course_resp.json()["course_id"]

    # 3. Create Instructor
    import uuid

    unique_id = str(uuid.uuid4())[:8]
    instructor_email = f"instructor.actions.{unique_id}@test.com"
    instructor_password = GENERIC_PASSWORD
    instructor = create_test_user_via_api(
        admin_page=admin_page,
        base_url=BASE_URL,
        email=instructor_email,
        first_name="Action",
        last_name="Tester",
        role="instructor",
        institution_id=institution_id,
        program_ids=[program_id],
        password=instructor_password,
    )
    instructor_id = instructor["user_id"]

    # 4. Create Term
    term_resp = admin_page.request.post(
        f"{BASE_URL}/api/terms",
        headers=headers,
        data=json.dumps(
            {
                "name": "Action Test Term",
                "start_date": "2025-01-01",
                "end_date": "2025-05-01",
                "assessment_due_date": "2025-05-10",
                "institution_id": institution_id,
            }
        ),
    )
    assert term_resp.ok, "Failed to create term"
    term_id = term_resp.json()["term_id"]

    # 5. Create Offering
    offering_resp = admin_page.request.post(
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
    assert offering_resp.ok, "Failed to create offering"
    offering_id = offering_resp.json()["offering_id"]

    # 6. Create Section
    section_resp = admin_page.request.post(
        f"{BASE_URL}/api/sections",
        headers=headers,
        data=json.dumps(
            {
                "offering_id": offering_id,
                "section_number": "001",
                "instructor_id": instructor_id,
                "status": "open",
            }
        ),
    )
    assert section_resp.ok, "Failed to create section"

    # 7. Create CLO Template (Course Outcome)
    clo_resp = admin_page.request.post(
        f"{BASE_URL}/api/courses/{course_id}/outcomes",
        headers=headers,
        data=json.dumps(
            {
                "course_id": course_id,
                "clo_number": 1,
                "description": "Test Outcome for Actions",
                "status": clo_status,
            }
        ),
    )
    assert clo_resp.ok, "Failed to create CLO"
    clo_id = clo_resp.json()["outcome_id"]

    # 8. Resolve Section Outcome ID
    audit_resp = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/audit?course_id={course_id}",
        headers=headers,
    )
    assert audit_resp.ok
    audit_outcomes = audit_resp.json().get("outcomes", [])
    target = next((o for o in audit_outcomes if o.get("outcome_id") == clo_id), None)
    assert target, "Section outcome not found"
    section_outcome_id = target["id"]

    return {
        "course_id": course_id,
        "term_id": term_id,
        "section_outcome_id": section_outcome_id,
        "clo_id": clo_id,
        "csrf_token": csrf_token,
        "admin_header": headers,
        "instructor_email": instructor_email,
        "instructor_password": instructor_password,
    }


def _submit_clo_as_instructor(admin_page, setup_data):
    """Log in as instructor and submit the CLO to move it to 'awaiting_approval'."""
    # Create new context for instructor
    context = admin_page.context.browser.new_context()
    page = context.new_page()

    login_as_user(
        page,
        BASE_URL,
        setup_data["instructor_email"],
        setup_data["instructor_password"],
    )

    # Get instructor CSRF
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")
    csrf = page.evaluate("document.querySelector('meta[name=\"csrf-token\"]')?.content")

    # Submit API call
    resp = page.request.post(
        f"{BASE_URL}/api/outcomes/{setup_data['section_outcome_id']}/submit",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf if csrf else "",
        },
        data=json.dumps(
            {"assessment_tool": "Test Tool", "students_took": 10, "students_passed": 10}
        ),
    )
    assert resp.ok, f"Instructor submission failed: {resp.text()}"

    context.close()


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


@pytest.mark.e2e
def test_clo_rework_workflow(authenticated_institution_admin_page: Page):
    """
    Test 'Request Rework' workflow.
    1. Setup CLO in 'Awaiting Approval'.
    2. Admin requests rework via modal.
    3. Verify status -> 'needs_rework' (approval_status).
    """
    admin_page = authenticated_institution_admin_page
    inst_id = get_institution_id_from_user(admin_page)

    # Setup Data
    data = _setup_clo_data(admin_page, inst_id)
    _submit_clo_as_instructor(admin_page, data)

    # Go to Audit Page
    admin_page.goto(f"{BASE_URL}/audit-clo")
    admin_page.wait_for_selector(
        f'tr[data-outcome-id="{data["section_outcome_id"]}"]', timeout=5000
    )

    # Open Modal
    admin_page.click(f'tr[data-outcome-id="{data["section_outcome_id"]}"]')
    expect(admin_page.locator("#cloDetailModal")).to_be_visible()

    # Click Request Rework
    admin_page.click("#requestReworkBtn")
    expect(admin_page.locator("#cloReworkSection")).to_be_visible()

    # Fill Form
    admin_page.fill("#reworkFeedbackComments", "Please fix the assessment data.")

    # Submit
    admin_page.click("#cloDetailActionsRework button[type='submit']")

    # Verify Success Alert/Modal Close
    # (Note: Alert handling is implicit in Playwright if not handled, but we check UI state)
    expect(admin_page.locator("#cloReworkSection")).not_to_be_visible()

    # Verify API State
    resp = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{data['section_outcome_id']}/audit-details",
        headers=data["admin_header"],
    )
    outcome = resp.json()["outcome"]
    assert outcome["approval_status"] == "needs_rework"
    assert "Please fix" in outcome["feedback_comments"]


@pytest.mark.e2e
def test_clo_nci_workflow(authenticated_institution_admin_page: Page):
    """
    Test 'Mark as NCI' workflow.
    1. Setup CLO in 'Awaiting Approval'.
    2. Admin marks as NCI via modal.
    3. Verify status -> 'never_coming_in'.
    """
    admin_page = authenticated_institution_admin_page
    inst_id = get_institution_id_from_user(admin_page)

    # Setup Data
    data = _setup_clo_data(admin_page, inst_id)
    _submit_clo_as_instructor(admin_page, data)

    # Go to Audit Page and Open Modal
    admin_page.goto(f"{BASE_URL}/audit-clo")
    admin_page.click(f'tr[data-outcome-id="{data["section_outcome_id"]}"]')
    expect(admin_page.locator("#cloDetailModal")).to_be_visible()

    # Handle Prompt (Playwright handles prompt automatically by returning default if not configured,
    # but we should intercept it to provide a value)
    def handle_prompt(dialog):
        assert "Never Coming In" in dialog.message
        dialog.accept("Instructor unavailable")

    admin_page.once("dialog", handle_prompt)

    # Click Mark NCI
    admin_page.click("#markNCIBtn")

    # Verify Modal Closed & Alert (implicit)
    expect(admin_page.locator("#cloDetailModal")).not_to_be_visible()

    # Verify UI Status
    # Need to switch filter to 'all' or 'never_coming_in' to see it?
    # Usually UI stays but might refresh. Let's check API for reliability.
    resp = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{data['section_outcome_id']}/audit-details",
        headers=data["admin_header"],
    )
    outcome = resp.json()["outcome"]
    assert outcome["status"] == "never_coming_in"


@pytest.mark.e2e
def test_clo_reopen_workflow(authenticated_institution_admin_page: Page):
    """
    Test 'Reopen Outcome' workflow.
    1. Setup CLO and Approve it.
    2. Admin reopens it.
    3. Verify status -> 'in_progress'.
    """
    admin_page = authenticated_institution_admin_page
    inst_id = get_institution_id_from_user(admin_page)

    # Setup Data
    data = _setup_clo_data(admin_page, inst_id)
    _submit_clo_as_instructor(admin_page, data)

    # Fast-forward to Approved state via API to save time
    admin_page.request.post(
        f"{BASE_URL}/api/outcomes/{data['section_outcome_id']}/approve",
        headers=data["admin_header"],
    )

    # Go to Audit Page - Filter by Approved
    admin_page.goto(f"{BASE_URL}/audit-clo")
    admin_page.select_option("#statusFilter", "approved")
    admin_page.click(f'tr[data-outcome-id="{data["section_outcome_id"]}"]')

    # Check Reopen Button Visible
    reopen_btn = admin_page.locator("#reopenBtn")
    expect(reopen_btn).to_be_visible()

    # Handle Confirm Dialog
    admin_page.once("dialog", lambda d: d.accept())

    # Click Reopen (with wait for API response)
    with admin_page.expect_response(
        lambda response: "reopen" in response.url
        and response.request.method == "POST"
        and response.status == 200
    ) as response_info:
        reopen_btn.click()

    # Wait for modal to close (since we added that behavior)
    expect(admin_page.locator("#cloDetailModal")).not_to_be_visible()

    # Verify API State
    resp = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{data['section_outcome_id']}/audit-details",
        headers=data["admin_header"],
    )
    outcome = resp.json()["outcome"]
    # After reopen, status should be awaiting_approval (ready for re-approval)
    # Changed from in_progress to allow immediate approval without requiring edit
    assert outcome["status"] == "awaiting_approval"
    assert outcome["approval_status"] == "pending"
