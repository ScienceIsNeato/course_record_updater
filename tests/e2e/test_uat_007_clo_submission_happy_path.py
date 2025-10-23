"""
UAT-007: CLO Submission Happy Path

Test the instructor workflow for submitting CLOs for approval.

Workflow:
1. Seed test data: Institution, program, course, section with instructor, CLOs in ASSIGNED status
2. Instructor logs in
3. Navigate to assessments page
4. Edit CLO fields (verify auto-set to IN_PROGRESS)
5. Submit CLO for approval
6. Verify status = AWAITING_APPROVAL, submitted_at set
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
def test_clo_submission_happy_path(authenticated_institution_admin_page: Page):
    """
    Test full CLO submission workflow for instructor.

    Steps:
    1. Create test instructor with assigned course section
    2. Create CLOs in ASSIGNED status
    3. Instructor logs in and edits CLO (auto-marks IN_PROGRESS)
    4. Instructor submits CLO
    5. Verify CLO status is AWAITING_APPROVAL
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
                "name": "UAT-007 Computer Science",
                "short_name": "UAT007-CS",
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
                "course_number": "UAT007-SE101",
                "course_title": "UAT-007 Software Engineering",
                "department": "Computer Science",
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
        email="uat007.instructor@test.com",
        first_name="UAT007",
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

    # Create CLOs for the course in ASSIGNED status
    clo1_response = admin_page.request.post(
        f"{BASE_URL}/api/courses/{course_id}/outcomes",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data=json.dumps(
            {
                "course_id": course_id,
                "clo_number": 1,
                "description": "Understand software design patterns",
                "status": "assigned",  # ASSIGNED status
            }
        ),
    )
    assert clo1_response.ok, f"Failed to create CLO 1: {clo1_response.text()}"
    clo1_data = clo1_response.json()
    clo1_id = clo1_data["outcome_id"]

    # === STEP 2: Instructor logs in ===
    instructor_page = admin_page.context.new_page()
    login_as_user(
        instructor_page, BASE_URL, "uat007.instructor@test.com", "TestUser123!"
    )

    # === STEP 3: Navigate to assessments page ===
    instructor_page.goto(f"{BASE_URL}/assessments")
    expect(instructor_page).to_have_url(f"{BASE_URL}/assessments")

    # Find the course in the dropdown
    instructor_page.select_option("#courseSelect", value=course_id)

    # Wait for CLO data to load
    instructor_page.wait_for_selector(
        f"button[data-outcome-id='{clo1_id}']", timeout=5000
    )

    # Verify CLO status is ASSIGNED initially
    status_badge = instructor_page.locator(f"#clo-status-{clo1_id}")
    expect(status_badge).to_have_text("Assigned")

    # === STEP 4: Edit CLO fields (auto-marks IN_PROGRESS) ===
    # Fill in assessment data
    instructor_page.fill(f"#students_assessed_{clo1_id}", "30")
    instructor_page.fill(f"#students_meeting_target_{clo1_id}", "27")
    instructor_page.fill(
        f"#narrative_{clo1_id}",
        "Students demonstrated strong understanding of design patterns.",
    )

    # Click save (triggers auto-mark as in_progress)
    instructor_page.click("button:has-text('Save Changes')")

    # Wait for success message
    instructor_page.wait_for_selector(".alert-success", timeout=5000)

    # Reload page to see updated status
    instructor_page.reload()
    instructor_page.select_option("#sectionSelect", value=section_id)
    instructor_page.wait_for_selector(f"#outcome-{clo1_id}", timeout=5000)

    # Verify status changed to IN_PROGRESS
    status_badge = instructor_page.locator(f"#clo-status-{clo1_id}")
    expect(status_badge).to_have_text("In Progress")

    # === STEP 5: Submit CLO for approval ===
    # Click submit button
    submit_button = instructor_page.locator(f"#submit-clo-{clo1_id}")
    expect(submit_button).to_be_visible()
    submit_button.click()

    # Confirm submission
    instructor_page.once("dialog", lambda dialog: dialog.accept())

    # Wait for success message
    instructor_page.wait_for_selector(".alert-success", timeout=5000)

    # === STEP 6: Verify status is AWAITING_APPROVAL ===
    # Reload page to see updated status
    instructor_page.reload()
    instructor_page.select_option("#sectionSelect", value=section_id)
    instructor_page.wait_for_selector(f"#outcome-{clo1_id}", timeout=5000)

    # Verify status is now AWAITING_APPROVAL
    status_badge = instructor_page.locator(f"#clo-status-{clo1_id}")
    expect(status_badge).to_have_text("Awaiting Approval")

    # Verify submit button is no longer visible (can't submit twice)
    submit_button = instructor_page.locator(f"#submit-clo-{clo1_id}")
    expect(submit_button).not_to_be_visible()

    # === STEP 7: Verify via API that submission timestamp is set ===
    # Use admin page to check API
    outcome_response = admin_page.request.get(
        f"{BASE_URL}/api/outcomes/{clo1_id}/audit-details",
        headers={
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
    )
    assert outcome_response.ok, f"Failed to get outcome: {outcome_response.text()}"
    outcome_data = outcome_response.json()

    assert outcome_data["status"] == "awaiting_approval"
    assert outcome_data["submitted_at"] is not None
    assert outcome_data["submitted_by_user_id"] == instructor_id
    assert outcome_data["approval_status"] == "pending"

    # Cleanup
    instructor_page.close()
