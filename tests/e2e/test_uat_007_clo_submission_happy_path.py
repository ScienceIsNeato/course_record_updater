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

    # Select course
    instructor_page.select_option("#courseSelect", value=course_id)

    # Wait for CLO tile/button to appear, allow rendering time
    instructor_page.wait_for_timeout(500)
    clo_button = instructor_page.locator(f"button[data-outcome-id='{clo1_id}']")
    clo_button.wait_for(timeout=5000)
    # Ensure the update button is bound and rendered with dataset
    instructor_page.wait_for_selector(
        f".update-assessment-btn[data-outcome-id='{clo1_id}']", timeout=5000
    )
    expect(clo_button).to_be_visible()
    expect(clo_button).to_have_attribute("data-status", "assigned")

    # === STEP 4: Edit CLO fields (auto-marks IN_PROGRESS) ===
    # Open assessment modal (Update Assessment modal)
    clo_button.click()
    try:
        instructor_page.wait_for_selector(
            "#updateAssessmentModal", state="visible", timeout=5000
        )
    except Exception:
        # Dump container HTML for debugging and retry explicit button
        try:
            html_dump = instructor_page.evaluate(
                "document.getElementById('outcomesContainer')?.innerHTML || ''"
            )
            print(
                "\n=== DEBUG outcomesContainer HTML (first 2000 chars) ===\n"
                + html_dump[:2000]
            )
        except Exception:
            pass
        instructor_page.locator(
            f".update-assessment-btn[data-outcome-id='{clo1_id}']"
        ).click()
        instructor_page.wait_for_selector(
            "#updateAssessmentModal", state="visible", timeout=5000
        )

    # Fill in assessment data in modal
    instructor_page.fill("#studentsAssessed", "30")
    instructor_page.fill("#studentsMeetingTarget", "27")
    instructor_page.fill(
        "#assessmentNarrative",
        "Students demonstrated strong understanding of design patterns.",
    )

    # Save (auto-marks IN_PROGRESS) - submit the form
    instructor_page.click("#updateAssessmentForm button[type='submit']")
    instructor_page.wait_for_selector(
        "#updateAssessmentModal", state="hidden", timeout=5000
    )

    # Verify status changed to IN_PROGRESS via button attribute
    expect(clo_button).to_have_attribute("data-status", "in_progress")

    # === STEP 5: Submit CLO for approval ===
    # Click submit button
    submit_button = instructor_page.locator(
        f".submit-clo-btn[data-outcome-id='{clo1_id}']"
    )
    expect(submit_button).to_be_visible()
    instructor_page.once("dialog", lambda dialog: dialog.accept())
    submit_button.click()

    # Wait briefly for state to update
    instructor_page.wait_for_timeout(500)

    # === STEP 6: Verify status is AWAITING_APPROVAL ===
    # Verify status is now AWAITING_APPROVAL via button attribute
    expect(clo_button).to_have_attribute("data-status", "awaiting_approval")

    # Verify submit button is no longer visible
    expect(
        instructor_page.locator(f".submit-clo-btn[data-outcome-id='{clo1_id}']")
    ).not_to_be_visible()

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
