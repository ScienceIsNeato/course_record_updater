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

    # 4. Create Offering
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
                "status": "open",
            }
        ),
    )
    assert section_resp.ok
    section_id = section_resp.json()["section_id"]

    # 6. Create CLO Template
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

    return {
        "course_id": course_id,
        "section_id": section_id,
        "clo_id": clo_id,
        "section_outcome_id": target["id"] if target else None,
    }


@pytest.mark.e2e
def test_clo_invite_button_opens_modal(authenticated_institution_admin_page: Page):
    admin_page = authenticated_institution_admin_page
    admin_page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
    inst_id = get_institution_id_from_user(admin_page)

    data = _setup_unassigned_clo(admin_page, inst_id)
    assert data["section_outcome_id"], "Failed to generate section outcome"

    admin_page.goto(f"{BASE_URL}/audit-clo")
    admin_page.select_option("#courseFilter", value=data["course_id"])

    row_selector = f"tr[data-outcome-id='{data['section_outcome_id']}']"
    admin_page.wait_for_selector(row_selector, timeout=5000)

    invite_btn = admin_page.locator(f"{row_selector} button[title='Assign Instructor']")
    expect(invite_btn).to_be_visible()
    invite_btn.click()

    admin_page.wait_for_timeout(1000)
    modal = admin_page.locator("#assignInstructorModal")
    expect(modal).to_be_visible()


@pytest.mark.e2e
def test_clo_scroll_regression_on_reload(
    authenticated_institution_admin_page: Page,
):
    """
    Verifies that the table can be scrolled and that reloading the table
    (mimicking an update like 'faculty-invited') preserves the scroll position.
    """
    admin_page = authenticated_institution_admin_page
    admin_page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))

    inst_id = get_institution_id_from_user(admin_page)
    data = _setup_unassigned_clo(admin_page, inst_id)

    # Simplified mock to force a long table
    def handle_route(route):
        url = route.request.url
        # Match Audit API for this test setup
        if "/api/outcomes/audit" in url:
            mock_data = []
            target_item = {
                "id": data["section_outcome_id"],
                "outcome_id": data["section_outcome_id"],
                "status": "unassigned",
                "course_number": "TEST-101",
                "course_id": data["course_id"],
                "course_title": "E2E Test Course",
                "section_number": "001",
                "clo_number": "1",
                "description": "Target CLO for Assignment",
                "instructor_name": None,
                "submitted_at": "2025-01-01",
            }
            mock_data.append(target_item)
            # Add 50 dummies to ensure scrollability
            for i in range(50):
                dummy = target_item.copy()
                dummy["id"] = f"dummy-{i}"
                dummy["outcome_id"] = f"dummy-{i}"
                dummy["section_number"] = f"99{i}"
                dummy["description"] = f"Dummy CLO {i}"
                mock_data.append(dummy)

            # Return list wrapped in outcomes object
            route.fulfill(json={"outcomes": mock_data})
        else:
            route.continue_()

    admin_page.route("**/api/outcomes/audit*", handle_route)

    # Go to Audit Page
    admin_page.goto(f"{BASE_URL}/audit-clo")
    admin_page.select_option("#courseFilter", value=data["course_id"])

    row_selector = f"tr[data-outcome-id='{data['section_outcome_id']}']"
    admin_page.wait_for_selector(row_selector)

    # Scroll down to verify page is long
    admin_page.evaluate("window.scrollTo(0, 200)")
    admin_page.wait_for_timeout(200)

    initial_scroll = admin_page.evaluate("window.scrollY")
    body_height = admin_page.evaluate("document.body.scrollHeight")

    assert (
        initial_scroll > 50 or body_height > 1000
    ), f"Failed to scroll. scrollY: {initial_scroll} (expected > 50)"

    # Trigger table reload by calling loadCLOs() directly
    # (The faculty-invited event is only listened to by institution_dashboard.js, not audit_clo.js)
    admin_page.evaluate("window.loadCLOs ? window.loadCLOs() : null")

    # Wait for async loadCLOs to complete and scroll restoration
    admin_page.wait_for_timeout(1500)

    # Check scroll
    final_scroll = admin_page.evaluate("window.scrollY")

    assert (
        abs(final_scroll - initial_scroll) < 50
    ), f"Scroll regression! Initial: {initial_scroll}, Final: {final_scroll}. Content should stay stable."
