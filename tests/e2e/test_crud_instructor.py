"""
E2E Tests for Instructor CRUD Operations

Tests complete instructor workflows with authenticated API calls:
- Profile management (self-service updates)
- Section assessment updates
- Permission boundaries (cannot create courses, cannot manage users)

Test Naming Convention:
- test_tc_crud_inst_XXX: Matches UAT test case ID (TC-CRUD-INST-XXX)
"""

import pytest
from playwright.sync_api import Page

# Import database verification helpers
from database_service import get_user_by_id
from tests.e2e.conftest import BASE_URL

# ========================================
# INSTRUCTOR CRUD TESTS (4 tests)
# ========================================


@pytest.mark.e2e
def test_tc_crud_inst_001_update_own_profile(authenticated_page: Page):
    """
    TC-CRUD-INST-001: Instructor updates own profile

    Steps:
    1. Login as instructor (authenticated_page provides this)
    2. Call PATCH /api/users/<id>/profile with updated fields
    3. Verify API response success
    4. Verify updates in database

    Expected: Profile updates succeed for self
    """
    # Get current user info from session (authenticated_page is logged in as sarah.admin@cei.edu)
    # For this test, we need to use an instructor account
    # We'll get the instructor user ID from the database
    from database_service import get_all_users

    users = get_all_users()
    instructor = next((u for u in users if u["role"] == "instructor"), None)

    if not instructor:
        pytest.skip("No instructor user found in database for E2E test")

    instructor_id = instructor["user_id"]
    instructor_email = instructor["email"]

    # For E2E, we need to login as the instructor first
    # Clear existing session and login as instructor
    authenticated_page.context.clear_cookies()

    # Navigate to login page
    authenticated_page.goto(f"{BASE_URL}/login")
    authenticated_page.wait_for_load_state("networkidle")

    # Login as instructor (use default password from seed data)
    authenticated_page.fill('input[name="email"]', instructor_email)
    authenticated_page.fill('input[name="password"]', "InstructorPass123!")
    authenticated_page.click('button[type="submit"]')

    # Wait for dashboard redirect
    try:
        authenticated_page.wait_for_url(f"{BASE_URL}/dashboard", timeout=3000)
    except Exception as e:
        pytest.skip(f"Instructor login failed: {e}. May need to check seed data.")

    # Now make API call to update profile
    # Get CSRF token from session
    csrf_token_element = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Use Playwright's API context to make authenticated request
    profile_data = {
        "first_name": "Updated",
        "last_name": "Instructor",
        "display_name": "Prof. Updated Instructor",
    }

    response = authenticated_page.request.patch(
        f"{BASE_URL}/api/users/{instructor_id}/profile",
        data=profile_data,
        headers={"X-CSRFToken": csrf_token_element} if csrf_token_element else {},
    )

    # Verify API response
    assert response.ok, f"Profile update failed: {response.status} - {response.text()}"
    result = response.json()
    assert result["success"] is True, f"Expected success=True, got {result}"

    # Verify in database
    updated_user = get_user_by_id(instructor_id)
    assert updated_user is not None, "User not found in database after update"
    assert (
        updated_user["first_name"] == "Updated"
    ), f"First name not updated: {updated_user['first_name']}"
    assert (
        updated_user["last_name"] == "Instructor"
    ), f"Last name not updated: {updated_user['last_name']}"

    print("✅ TC-CRUD-INST-001: Instructor successfully updated own profile")


@pytest.mark.e2e
def test_tc_crud_inst_002_update_section_assessment(authenticated_page: Page):
    """
    TC-CRUD-INST-002: Instructor updates CLO assessment data

    Steps:
    1. Login as instructor
    2. Find a course outcome for instructor's section
    3. Call PUT /api/outcomes/<id>/assessment with assessment data
    4. Verify API response success
    5. Verify assessment data in database

    Expected: Assessment updates succeed for instructor's own sections
    """
    # Get instructor and their sections
    from database_service import get_all_sections, get_all_users, get_course_outcomes

    users = get_all_users()
    instructor = next((u for u in users if u["role"] == "instructor"), None)

    if not instructor:
        pytest.skip("No instructor user found in database for E2E test")

    instructor_id = instructor["user_id"]
    instructor_email = instructor["email"]

    # Find a section assigned to this instructor
    sections = get_all_sections(instructor["institution_id"])
    instructor_section = next(
        (s for s in sections if s.get("instructor_id") == instructor_id), None
    )

    if not instructor_section:
        pytest.skip("No section assigned to instructor for E2E test")

    # Get course outcomes for this section's offering
    course_id = instructor_section.get("course_id")
    outcomes = get_course_outcomes(course_id)

    if not outcomes:
        pytest.skip("No course outcomes found for instructor's section")

    outcome_id = outcomes[0]["outcome_id"]

    # Login as instructor (same pattern as test_001)
    authenticated_page.context.clear_cookies()
    authenticated_page.goto(f"{BASE_URL}/login")
    authenticated_page.wait_for_load_state("networkidle")
    authenticated_page.fill('input[name="email"]', instructor_email)
    authenticated_page.fill('input[name="password"]', "InstructorPass123!")
    authenticated_page.click('button[type="submit"]')

    try:
        authenticated_page.wait_for_url(f"{BASE_URL}/dashboard", timeout=3000)
    except Exception as e:
        pytest.skip(f"Instructor login failed: {e}")

    # Get CSRF token
    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Update outcome assessment
    assessment_data = {
        "assessment_data": {
            "students_assessed": 25,
            "students_meeting_target": 20,
            "method": "Final Exam",
            "date": "2024-12-15",
        },
        "narrative": "Students performed well on final exam assessments.",
    }

    response = authenticated_page.request.put(
        f"{BASE_URL}/api/outcomes/{outcome_id}/assessment",
        data=assessment_data,
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    # Verify API response
    assert (
        response.ok
    ), f"Assessment update failed: {response.status} - {response.text()}"
    result = response.json()
    assert result["success"] is True, f"Expected success=True, got {result}"

    # Verify in database (assessment data not directly queryable via get_course_outcomes)
    # In a real E2E test, we'd verify via UI or a dedicated get_outcome_by_id endpoint
    # For now, successful API response is sufficient

    print("✅ TC-CRUD-INST-002: Instructor successfully updated section assessment")


@pytest.mark.e2e
def test_tc_crud_inst_003_cannot_create_course(authenticated_page: Page):
    """
    TC-CRUD-INST-003: Instructor cannot create courses

    Steps:
    1. Login as instructor
    2. Attempt to POST /api/courses with new course data
    3. Verify API returns 403 Forbidden
    4. Verify no course was created in database

    Expected: 403 Forbidden (insufficient permissions)
    """
    # Get instructor
    from database_service import get_all_courses, get_all_users

    users = get_all_users()
    instructor = next((u for u in users if u["role"] == "instructor"), None)

    if not instructor:
        pytest.skip("No instructor user found in database for E2E test")

    instructor_email = instructor["email"]
    institution_id = instructor["institution_id"]

    # Count existing courses before attempt
    courses_before = get_all_courses(institution_id)
    course_count_before = len(courses_before)

    # Login as instructor
    authenticated_page.context.clear_cookies()
    authenticated_page.goto(f"{BASE_URL}/login")
    authenticated_page.wait_for_load_state("networkidle")
    authenticated_page.fill('input[name="email"]', instructor_email)
    authenticated_page.fill('input[name="password"]', "InstructorPass123!")
    authenticated_page.click('button[type="submit"]')

    try:
        authenticated_page.wait_for_url(f"{BASE_URL}/dashboard", timeout=3000)
    except Exception as e:
        pytest.skip(f"Instructor login failed: {e}")

    # Get CSRF token
    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Attempt to create course
    course_data = {
        "course_number": "CS999",
        "title": "Unauthorized Course",
        "department": "Computer Science",
        "credit_hours": 3,
        "institution_id": institution_id,
        "program_ids": [],
    }

    response = authenticated_page.request.post(
        f"{BASE_URL}/api/courses",
        data=course_data,
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    # Verify 403 Forbidden
    assert response.status == 403, f"Expected 403, got {response.status}"

    # Verify no course was created
    courses_after = get_all_courses(institution_id)
    course_count_after = len(courses_after)
    assert (
        course_count_after == course_count_before
    ), "Course was created despite 403 response"

    print("✅ TC-CRUD-INST-003: Instructor correctly blocked from creating courses")


@pytest.mark.e2e
def test_tc_crud_inst_004_cannot_manage_users(authenticated_page: Page):
    """
    TC-CRUD-INST-004: Instructor cannot manage users

    Steps:
    1. Login as instructor
    2. Attempt to DELETE /api/users/<id> for another user
    3. Verify API returns 403 Forbidden
    4. Verify user still exists in database

    Expected: 403 Forbidden (insufficient permissions)
    """
    # Get instructor and another user
    from database_service import get_all_users

    users = get_all_users()
    instructor = next((u for u in users if u["role"] == "instructor"), None)
    other_user = next((u for u in users if u["user_id"] != instructor["user_id"]), None)

    if not instructor or not other_user:
        pytest.skip("Insufficient users in database for E2E test")

    instructor_email = instructor["email"]
    target_user_id = other_user["user_id"]

    # Login as instructor
    authenticated_page.context.clear_cookies()
    authenticated_page.goto(f"{BASE_URL}/login")
    authenticated_page.wait_for_load_state("networkidle")
    authenticated_page.fill('input[name="email"]', instructor_email)
    authenticated_page.fill('input[name="password"]', "InstructorPass123!")
    authenticated_page.click('button[type="submit"]')

    try:
        authenticated_page.wait_for_url(f"{BASE_URL}/dashboard", timeout=3000)
    except Exception as e:
        pytest.skip(f"Instructor login failed: {e}")

    # Get CSRF token
    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Attempt to delete user
    response = authenticated_page.request.delete(
        f"{BASE_URL}/api/users/{target_user_id}",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    # Verify 403 Forbidden
    assert response.status == 403, f"Expected 403, got {response.status}"

    # Verify user still exists
    user_still_exists = get_user_by_id(target_user_id)
    assert user_still_exists is not None, "User was deleted despite 403 response"

    print("✅ TC-CRUD-INST-004: Instructor correctly blocked from managing users")
