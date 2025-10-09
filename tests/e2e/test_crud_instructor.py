"""
E2E Tests for Instructor CRUD Operations

Tests complete instructor workflows using UI and authenticated API calls:
- Profile management (self-service updates)
- Section assessment updates
- Permission boundaries (cannot create courses, cannot manage users)

All tests are UI-first: no direct database calls.

Test Naming Convention:
- test_tc_crud_inst_XXX: Matches UAT test case ID (TC-CRUD-INST-XXX)
"""

import pytest
from playwright.sync_api import Page

from tests.e2e.conftest import BASE_URL

# ========================================
# INSTRUCTOR CRUD TESTS (4 tests)
# ========================================


@pytest.mark.e2e
def test_tc_crud_inst_001_update_own_profile(instructor_authenticated_page: Page):
    """
    TC-CRUD-INST-001: Instructor updates own profile via UI

    Steps:
    1. Login as instructor (fixture provides this)
    2. Navigate to profile/settings page
    3. Update profile via UI form
    4. Verify changes appear on users page

    Expected: Profile updates succeed for self and are visible in UI
    """
    # Navigate to users list page
    instructor_authenticated_page.goto(f"{BASE_URL}/users")
    instructor_authenticated_page.wait_for_load_state("networkidle")
    instructor_authenticated_page.wait_for_selector(
        "#usersTableContainer", timeout=10000
    )

    # DEBUG: Check what users are actually showing up
    table_text = instructor_authenticated_page.evaluate(
        "document.querySelector('#usersTableContainer')?.innerText"
    )
    print(f"DEBUG: Users table content:\n{table_text}")

    # Find the instructor's own row and click Edit
    # The seeded instructor is "John Smith" (john.instructor@cei.edu)
    instructor_authenticated_page.wait_for_function(
        "document.querySelector('#usersTableContainer')?.innerText?.includes('John Smith')",
        timeout=5000,
    )

    # Click Edit button for John Smith's row
    edit_button = instructor_authenticated_page.locator(
        "#usersTableContainer table tbody tr:has-text('John Smith') button:has-text('Edit')"
    ).first
    edit_button.click()

    # Wait for edit modal to appear
    instructor_authenticated_page.wait_for_selector("#editUserModal", state="visible")

    # Update first and last name
    instructor_authenticated_page.fill("#editUserFirstName", "Updated")
    instructor_authenticated_page.fill("#editUserLastName", "Instructor")

    # Click Save Changes
    instructor_authenticated_page.click(
        "#editUserModal button:has-text('Save Changes')"
    )
    instructor_authenticated_page.wait_for_selector("#editUserModal", state="hidden")

    # Verify the updated name appears in the table
    instructor_authenticated_page.wait_for_load_state("networkidle")
    instructor_authenticated_page.wait_for_function(
        "document.querySelector('#usersTableContainer')?.innerText?.includes('Updated Instructor')",
        timeout=5000,
    )

    print("✅ TC-CRUD-INST-001: Instructor successfully updated own profile via UI")


@pytest.mark.e2e
@pytest.mark.skip(
    reason="Assessment UI not yet implemented (greenfield - build the UI first)"
)
def test_tc_crud_inst_002_update_section_assessment(
    instructor_authenticated_page: Page,
):
    """
    TC-CRUD-INST-002: Instructor updates CLO assessment data via UI

    Steps:
    1. Login as instructor (fixture provides this)
    2. Navigate to section/outcomes page
    3. Click "Update Assessment" for a CLO
    4. Fill assessment form and submit
    5. Verify assessment data appears in UI

    Expected: Assessment updates succeed for instructor's own sections

    TODO: Implement assessment UI before un-skipping this test
    """
    pytest.skip("Assessment UI not yet implemented - build the UI to enable this test")


@pytest.mark.e2e
def test_tc_crud_inst_003_cannot_create_course(instructor_authenticated_page: Page):
    """
    TC-CRUD-INST-003: Instructor cannot create courses (permission boundary test)

    Steps:
    1. Login as instructor (fixture provides this)
    2. Count courses before attempt (via API)
    3. Attempt to POST /api/courses with new course data
    4. Verify API returns 403 Forbidden
    5. Verify course count unchanged (via API)

    Expected: 403 Forbidden (insufficient permissions)
    """
    # Get CSRF token
    csrf_token = instructor_authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Count existing courses before attempt
    courses_before_response = instructor_authenticated_page.request.get(
        f"{BASE_URL}/api/courses",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )
    assert courses_before_response.ok, "Failed to fetch courses for baseline"
    course_count_before = len(courses_before_response.json().get("courses", []))

    # Attempt to create course (should fail with 403)
    course_data = {
        "course_number": "CS999",
        "course_title": "Unauthorized Course",
        "department": "Computer Science",
        "credit_hours": 3,
        "program_ids": [],
    }

    response = instructor_authenticated_page.request.post(
        f"{BASE_URL}/api/courses",
        data=course_data,
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    # Verify 403 Forbidden
    assert response.status == 403, f"Expected 403, got {response.status}"

    # Verify no course was created (count should be unchanged)
    courses_after_response = instructor_authenticated_page.request.get(
        f"{BASE_URL}/api/courses",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )
    assert courses_after_response.ok, "Failed to fetch courses for verification"
    course_count_after = len(courses_after_response.json().get("courses", []))

    assert (
        course_count_after == course_count_before
    ), "Course was created despite 403 response"

    print("✅ TC-CRUD-INST-003: Instructor correctly blocked from creating courses")


@pytest.mark.e2e
def test_tc_crud_inst_004_cannot_manage_users(instructor_authenticated_page: Page):
    """
    TC-CRUD-INST-004: Instructor cannot manage/delete users (permission boundary test)

    Steps:
    1. Login as instructor (fixture provides this)
    2. Get list of users via API to find a target user
    3. Attempt to DELETE /api/users/<id> for another user
    4. Verify API returns 403 Forbidden
    5. Verify user still exists (via API)

    Expected: 403 Forbidden (insufficient permissions)
    """
    # Get CSRF token
    csrf_token = instructor_authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Get list of users to find a target for deletion attempt
    users_response = instructor_authenticated_page.request.get(
        f"{BASE_URL}/api/users",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )
    assert users_response.ok, "Failed to fetch users"
    users = users_response.json().get("users", [])

    # Pick any user that isn't the logged-in instructor (John Smith)
    target_user = next(
        (u for u in users if u.get("email") != "john.instructor@cei.edu"), None
    )
    assert target_user, "No target user found for deletion test"

    target_user_id = target_user["user_id"]

    # Attempt to delete user (should fail with 403)
    response = instructor_authenticated_page.request.delete(
        f"{BASE_URL}/api/users/{target_user_id}",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    # Verify 403 Forbidden
    assert response.status == 403, f"Expected 403, got {response.status}"

    # Verify user still exists (fetch users again and check)
    users_after_response = instructor_authenticated_page.request.get(
        f"{BASE_URL}/api/users",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )
    assert users_after_response.ok, "Failed to fetch users for verification"
    users_after = users_after_response.json().get("users", [])

    user_still_exists = any(u["user_id"] == target_user_id for u in users_after)
    assert user_still_exists, "User was deleted despite 403 response"

    print("✅ TC-CRUD-INST-004: Instructor correctly blocked from managing users")
