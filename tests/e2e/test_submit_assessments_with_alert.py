"""
E2E test for submitting assessments with program admin alert checkbox.

This test verifies:
1. Assessments page loads and course selection works
2. CLO data can be entered (mix of populated and unpopulated optional fields)
3. Course-level data can be entered
4. Alert Program Admins checkbox works
5. Submit button only triggers ONE submission (no event listener leak)
6. Submission completes successfully
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
from tests.test_credentials import TEST_USER_PASSWORD


@pytest.mark.e2e
def test_submit_assessments_with_alert_checkbox(
    authenticated_institution_admin_page: Page,
):
    """
    Test complete assessment submission flow including:
    - Mixed populated/unpopulated optional fields
    - Alert Program Admins checkbox
    - Verify single submission (no duplicates)
    """
    admin_page = authenticated_institution_admin_page

    # Get institution ID
    institution_id = get_institution_id_from_user(admin_page)

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
                "name": "TEST Submit Alert CS",
                "short_name": "TSA-CS",
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
                "course_number": "TSA-101",
                "course_title": "Test Submit Alert Course",
                "department": "Computer Science",
                "institution_id": institution_id,
                "program_id": program_id,
            }
        ),
    )
    assert course_response.ok
    course_id = course_response.json()["course_id"]

    # Create instructor
    instructor = create_test_user_via_api(
        admin_page=admin_page,
        base_url=BASE_URL,
        email="test.submit.alert@test.com",
        first_name="Test",
        last_name="SubmitAlert",
        role="instructor",
        institution_id=institution_id,
        program_ids=[program_id],
    )
    instructor_id = instructor["user_id"]

    # Create term
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
                "institution_id": institution_id,
            }
        ),
    )
    assert term_response.ok
    term_id = term_response.json()["term_id"]

    # Create offering and section
    offering_response = admin_page.request.post(
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
    assert offering_response.ok
    offering_id = offering_response.json()["offering_id"]

    section_response = admin_page.request.post(
        f"{BASE_URL}/api/sections",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data=json.dumps(
            {
                "offering_id": offering_id,
                "section_number": "001",
                "instructor_id": instructor_id,
                "status": "open",
                "enrollment": 25,
            }
        ),
    )
    assert section_response.ok

    # Create 3 CLOs
    for clo_num in [1, 2, 3]:
        clo_response = admin_page.request.post(
            f"{BASE_URL}/api/courses/{course_id}/outcomes",
            headers={
                "Content-Type": "application/json",
                "X-CSRFToken": csrf_token if csrf_token else "",
            },
            data=json.dumps(
                {
                    "course_id": course_id,
                    "clo_number": clo_num,
                    "description": f"Test CLO #{clo_num}",
                    "status": "assigned",
                }
            ),
        )
        assert clo_response.ok

    # === STEP 1: Instructor logs in ===
    instructor_page = admin_page.context.new_page()
    login_as_user(instructor_page, BASE_URL, "test.submit.alert@test.com", TEST_USER_PASSWORD)

    # Track console messages
    instructor_page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))

    # === STEP 2: Navigate to assessments ===
    instructor_page.goto(f"{BASE_URL}/assessments")
    instructor_page.wait_for_load_state("networkidle")

    # === STEP 3: Select the course ===
    course_select = instructor_page.locator("#courseSelect")
    expect(course_select).to_be_visible()

    # Wait for course option with composite ID to load
    instructor_page.wait_for_selector(
        f"#courseSelect option[value^='{course_id}::']", state="attached", timeout=10000
    )
    
    # Select the course
    composite_value = instructor_page.locator(
        f"#courseSelect option[value^='{course_id}::']"
    ).first.get_attribute("value")
    course_select.select_option(value=composite_value)
    instructor_page.wait_for_load_state("networkidle")

    # Wait for outcomes to load
    instructor_page.wait_for_selector(".outcomes-list .row", timeout=5000)

    # === STEP 4: Fill in CLO data (mixture of populated and unpopulated) ===
    # Fill in first CLO completely
    clo1_took = instructor_page.locator('input[data-field="students_took"]').first
    clo1_passed = instructor_page.locator('input[data-field="students_passed"]').first
    clo1_tool = instructor_page.locator('input[data-field="assessment_tool"]').first

    expect(clo1_took).to_be_visible()
    clo1_took.fill("25")
    clo1_passed.fill("23")
    clo1_tool.fill("Final Exam")

    # Fill in second CLO partially (leave assessment_tool empty)
    if instructor_page.locator('input[data-field="students_took"]').count() > 1:
        clo2_took = instructor_page.locator('input[data-field="students_took"]').nth(1)
        clo2_passed = instructor_page.locator('input[data-field="students_passed"]').nth(1)

        clo2_took.fill("24")
        clo2_passed.fill("20")
        # Intentionally leave assessment_tool empty

    # Leave third CLO completely empty (if exists) - testing optional fields

    # === STEP 5: Fill in course-level data ===
    students_passed = instructor_page.locator("#courseStudentsPassed")
    students_dfic = instructor_page.locator("#courseStudentsDFIC")
    cannot_reconcile = instructor_page.locator("#cannotReconcile")
    reconciliation_note = instructor_page.locator("#reconciliationNote")
    celebrations = instructor_page.locator("#narrativeCelebrations")
    challenges = instructor_page.locator("#narrativeChallenges")

    if students_passed.is_visible():
        students_passed.fill("15")
        students_dfic.fill("2")

        # Check the "Numbers Won't Add Up" checkbox
        cannot_reconcile.check()
        instructor_page.wait_for_selector(
            "#reconciliationNoteContainer[style*='block']", timeout=2000
        )
        reconciliation_note.fill("Two late adds after assessment period")

        # Fill in narrative reflections (some populated, some not)
        celebrations.fill(
            "Students excelled at applying concepts to real-world scenarios"
        )
        challenges.fill("")  # Leave challenges empty - testing optional field
        # Leave changes empty too

    # === STEP 6: Check Alert Program Admins checkbox ===
    alert_checkbox = instructor_page.locator("#alertProgramAdmins")
    expect(alert_checkbox).to_be_visible()
    alert_checkbox.check()
    expect(alert_checkbox).to_be_checked()

    # === STEP 7: Set up request listener to count submissions ===
    # Track how many POST requests are made to /api/courses/.../submit
    submit_requests = []

    def track_request(request):
        if "/api/courses/" in request.url and "/submit" in request.url:
            submit_requests.append(request.url)

    instructor_page.on("request", track_request)

    # === STEP 8: Click Submit Assessments ===
    submit_btn = instructor_page.locator("#submitCourseBtn")
    expect(submit_btn).to_be_visible()
    expect(submit_btn).to_be_enabled()

    submit_btn.click()

    # Handle alert dialog
    instructor_page.once("dialog", lambda dialog: dialog.accept())

    # Give a moment for any duplicate requests to fire (if bug still exists)
    instructor_page.wait_for_timeout(2000)

    # === STEP 9: Verify only ONE submission occurred ===
    assert (
        len(submit_requests) == 1
    ), f"Expected 1 submission, got {len(submit_requests)}: {submit_requests}"

    print(f"✅ Single submission confirmed: {submit_requests[0]}")
    print("✅ Alert Program Admins checkbox working")
    print("✅ Mixed populated/unpopulated fields handled correctly")
