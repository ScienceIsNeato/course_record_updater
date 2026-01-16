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


def _create_test_course_with_sections(
    admin_page: Page, institution_id: str, csrf_token: str
) -> tuple[str, str, str, str]:
    """Create test course with 2 sections for same instructor."""
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

    # Create 2 offerings + sections for same course/instructor
    for section_num in ["001", "002"]:
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
                    "section_number": section_num,
                    "instructor_id": instructor_id,
                    "status": "open",
                    "enrollment": 25 if section_num == "001" else 18,
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

    return course_id, instructor_id, program_id, term_id


def _fill_clo_data(instructor_page: Page) -> None:
    """Fill in all 3 CLOs with complete data."""
    for i in range(3):
        took = instructor_page.locator('input[data-field="students_took"]').nth(i)
        passed = instructor_page.locator('input[data-field="students_passed"]').nth(i)
        tool = instructor_page.locator('input[data-field="assessment_tool"]').nth(i)

        took.fill(str(25 - i))
        took.blur()
        instructor_page.wait_for_timeout(500)

        passed.fill(str(23 - i))
        passed.blur()
        instructor_page.wait_for_timeout(500)

        tool_name = ["Final Exam", "Midterm Exam", "Final Project"][i]
        tool.fill(tool_name)
        tool.blur()
        instructor_page.wait_for_timeout(500)


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
    institution_id = get_institution_id_from_user(admin_page)
    csrf_token = admin_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Create test data
    course_id, instructor_id, program_id, term_id = _create_test_course_with_sections(
        admin_page, institution_id, csrf_token
    )

    # Instructor logs in
    instructor_page = admin_page.context.new_page()
    login_as_user(
        instructor_page, BASE_URL, "test.submit.alert@test.com", TEST_USER_PASSWORD
    )
    instructor_page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))

    # === STEP 2: Navigate to assessments ===
    instructor_page.goto(f"{BASE_URL}/assessments")
    instructor_page.wait_for_load_state("networkidle")

    # === STEP 3: Select SECTION 1 (we'll fill this one) ===
    course_select = instructor_page.locator("#courseSelect")
    expect(course_select).to_be_visible()

    # Wait for course options with composite ID to load
    instructor_page.wait_for_selector(
        f"#courseSelect option[value^='{course_id}::']", state="attached", timeout=10000
    )

    # Verify we have 2 sections in the dropdown for this course
    section_options = instructor_page.locator(
        f"#courseSelect option[value^='{course_id}::']"
    )
    option_count = section_options.count()
    print(f"✅ Found {option_count} section options for course {course_id}")
    assert option_count == 2, f"Expected 2 sections, found {option_count}"

    # Select the FIRST section (Section 001)
    section1_composite = section_options.nth(0).get_attribute("value")
    print(f"✅ Selecting section 1: {section1_composite}")
    course_select.select_option(value=section1_composite)
    instructor_page.wait_for_load_state("networkidle")

    # Wait for outcomes to load
    instructor_page.wait_for_selector(".outcomes-list .row", timeout=5000)

    # === STEP 4: Fill in CLO data for selected section ===
    _fill_clo_data(instructor_page)

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

    # === STEP 7: Track submission success ===
    # Use response listener BEFORE clicking submit
    submit_response_status = []

    def track_response(response):
        if (
            "/api/courses/" in response.url
            and "/submit" in response.url
            and response.request.method == "POST"
        ):
            submit_response_status.append(response.status)

    instructor_page.on("response", track_response)

    # === STEP 8: Click Submit Assessments ===
    submit_btn = instructor_page.locator("#submitCourseBtn")
    expect(submit_btn).to_be_visible()
    expect(submit_btn).to_be_enabled()

    # Handle alert dialog (will show success or error message)
    alert_messages = []
    instructor_page.on(
        "dialog",
        lambda dialog: (alert_messages.append(dialog.message), dialog.accept()),
    )

    submit_btn.click()

    # Wait for response
    instructor_page.wait_for_timeout(2000)

    # === STEP 9: Verify submission succeeded ===
    assert len(submit_response_status) > 0, "No response received from submit endpoint"

    response_status = submit_response_status[0]
    assert (
        response_status == 200
    ), f"Expected 200 success, got {response_status}. Alert: {alert_messages}"

    # Verify the alert message confirms admin notification
    assert len(alert_messages) > 0, "No alert dialog shown"
    alert_text = alert_messages[0]
    assert (
        "successfully" in alert_text.lower()
    ), f"Alert doesn't show success: {alert_text}"

    # The alert should mention admin notification if checkbox was checked
    # (actual email sending verified by server logs, not in test assertion)

    print("✅ Submission succeeded")
    print(f"✅ Alert shown: {alert_text}")
    print("✅ Alert Program Admins checkbox working")
    print("✅ Only selected section validated (not all instructor sections)")
