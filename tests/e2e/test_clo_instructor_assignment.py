import json
import uuid

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL
from tests.e2e.test_helpers import (
    create_test_user_via_api,
    get_institution_id_from_user,
)


def _setup_unassigned_clo(admin_page, institution_id):
    """
    Sets up an unassigned CLO for testing.
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
                "name": "TEST-INVITE-PROG",
                "short_name": "TEST-INV",
                "institution_id": institution_id,
            }
        ),
    )
    assert program_resp.ok
    program_id = program_resp.json()["program_id"]

    # 2. Create Course
    course_resp = admin_page.request.post(
        f"{BASE_URL}/api/courses",
        headers=headers,
        data=json.dumps(
            {
                "course_number": "TEST-INV-101",
                "course_title": "Test Invite 101",
                "department": "Testing",
                "institution_id": institution_id,
                "program_id": program_id,
            }
        ),
    )
    assert course_resp.ok
    course_id = course_resp.json()["course_id"]

    # 3. Create Term
    term_resp = admin_page.request.post(
        f"{BASE_URL}/api/terms",
        headers=headers,
        data=json.dumps(
            {
                "name": "Invite Test Term",
                "start_date": "2025-01-01",
                "end_date": "2025-05-01",
                "assessment_due_date": "2025-05-10",
                "institution_id": institution_id,
            }
        ),
    )
    assert term_resp.ok
    term_id = term_resp.json()["term_id"]

    # 4. Create Offering (NO Instructor to ensure unassigned or assignable?)
    # Actually, usually offering has an instructor, but we want to assign a NEW one or replace?
    # Or maybe the CLO is unassigned because the SECTION has no instructor?
    # In audit_clo.js, unassigned status is checked.
    # We'll create an instructor for the offering but maybe not the section?
    # Or create an outcome that is specifically unassigned.

    # Create valid instructor first
    unique_id = str(uuid.uuid4())[:8]
    instructor_email = f"instructor.invite.{unique_id}@test.com"
    instructor = create_test_user_via_api(
        admin_page=admin_page,
        base_url=BASE_URL,
        email=instructor_email,
        first_name="Invite",
        last_name="Tester",
        role="instructor",
        institution_id=institution_id,
        program_ids=[program_id],
    )
    instructor_id = instructor["user_id"]

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
    assert offering_resp.ok
    offering_id = offering_resp.json()["offering_id"]

    # 5. Create Section
    section_resp = admin_page.request.post(
        f"{BASE_URL}/api/sections",
        headers=headers,
        data=json.dumps(
            {
                "offering_id": offering_id,
                "section_number": "001",
                # We explicitly want it unassigned?
                # If we don't provide instructor_id, it might default to offering's?
                # Let's provide None or omit.
                "status": "open",
            }
        ),
    )
    assert section_resp.ok
    section_id = section_resp.json()["section_id"]

    # 6. Create CLO Template
    # We set status="unassigned"
    clo_resp = admin_page.request.post(
        f"{BASE_URL}/api/courses/{course_id}/outcomes",
        headers=headers,
        data=json.dumps(
            {
                "course_id": course_id,
                "clo_number": 1,
                "description": "Test Outcome for Invite",
                "status": "unassigned",
            }
        ),
    )
    assert clo_resp.ok
    clo_id = clo_resp.json()["outcome_id"]

    # 7. Get Section Outcome ID
    audit_resp = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/audit?course_id={course_id}",
        headers=headers,
    )
    assert audit_resp.ok
    outcomes = audit_resp.json().get("outcomes", [])
    target = next((o for o in outcomes if o.get("outcome_id") == clo_id), None)

    # If not found, it might mean section outcome wasn't generated automatically?
    # Logic usually generates it.

    if not target:
        # Retry or check if we need to manually trigger sync?
        # Use existing logic from other tests which seems to rely on auto-generation.
        # But if we pass status='unassigned', does it generate?
        pass

    return {
        "course_id": course_id,
        "section_id": section_id,
        "clo_id": clo_id,
        "section_outcome_id": target["id"] if target else None,
    }


@pytest.mark.e2e
def test_clo_invite_button_opens_modal(authenticated_institution_admin_page: Page):
    admin_page = authenticated_institution_admin_page
    # Capture console logs and dialogs for debugging
    admin_page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
    admin_page.on("dialog", lambda dialog: print(f"Browser Dialog: {dialog.message}"))
    inst_id = get_institution_id_from_user(admin_page)

    data = _setup_unassigned_clo(admin_page, inst_id)
    assert data["section_outcome_id"], "Failed to generate section outcome"

    # Go to Audit Page
    admin_page.goto(f"{BASE_URL}/audit-clo")

    # Filter by Course to find our row easily
    admin_page.select_option("#courseFilter", value=data["course_id"])

    # Wait for row
    row_selector = f"tr[data-outcome-id='{data['section_outcome_id']}']"
    admin_page.wait_for_selector(row_selector, timeout=5000)

    # Find Invite Button
    invite_btn = admin_page.locator(f"{row_selector} button[title='Assign Instructor']")
    expect(invite_btn).to_be_visible()

    # Click
    invite_btn.click()

    # Wait a bit for transition
    admin_page.wait_for_timeout(1000)

    # Assert Modal
    modal = admin_page.locator("#assignInstructorModal")
    is_visible = modal.is_visible()
    if not is_visible:
        print(f"MODAL NOT VISIBLE. Classes: {modal.get_attribute('class')}")
        style = admin_page.evaluate(
            "(id) => { const el = document.getElementById(id); return JSON.stringify(window.getComputedStyle(el)); }",
            "assignInstructorModal",
        )
        print(f"MODAL COMPUTED STYLE: {style}")
        admin_page.screenshot(path="/tmp/modal_failure.png")
        print("Screenshot saved to /tmp/modal_failure.png")

    expect(modal).to_be_visible()
