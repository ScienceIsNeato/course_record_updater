"""
E2E tests for instructor CRUD operations

Tests instructor's ability to manage their own profile and view data.
Each test creates its own test data programmatically.
"""

import time

import pytest
from playwright.sync_api import Page

from tests.e2e.conftest import BASE_URL
from tests.e2e.test_helpers import (
    create_test_user_via_api,
    get_institution_id_from_user,
    login_as_user,
)


@pytest.mark.e2e
def test_tc_crud_inst_001_update_own_profile(
    authenticated_institution_admin_page: Page, page: Page
):
    """
    TC-CRUD-INST-001: Instructor updates own profile via UI

    Steps:
    1. Create test instructor programmatically via API
    2. Login as that instructor
    3. Navigate to users page
    4. Update own profile
    5. Verify changes appear in UI

    Expected: Instructor can update own profile successfully
    """
    # Step 1: Get institution ID from logged-in admin and create test instructor
    mocku_id = get_institution_id_from_user(authenticated_institution_admin_page)

    # Use unique email per test run to avoid conflicts in parallel execution
    test_email = f"john.instructor.{int(time.time() * 1000)}@test.local"
    test_password = "TestUser123!"

    instructor = create_test_user_via_api(
        admin_page=authenticated_institution_admin_page,
        base_url=BASE_URL,
        email=test_email,
        first_name="John",
        last_name="Smith",
        role="instructor",
        institution_id=mocku_id,
        password=test_password,
    )

    print(f"✓ Created test instructor: {test_email} (ID: {instructor['user_id']})")

    # Step 2: Login as the instructor
    instructor_page = login_as_user(page, BASE_URL, test_email, test_password)

    # Verify we're on dashboard
    assert (
        instructor_page.url == f"{BASE_URL}/dashboard"
    ), "Should be on dashboard after login"

    # Step 3: Navigate to users page
    instructor_page.goto(f"{BASE_URL}/users")
    instructor_page.wait_for_load_state("networkidle")
    instructor_page.wait_for_selector("#usersTableContainer", timeout=15000)

    # Step 4: Find own row and click Edit
    instructor_page.wait_for_function(
        f"document.querySelector('#usersTableContainer')?.innerText?.includes('{test_email}')",
        timeout=10000,
    )

    # Click Edit button for own row
    edit_button = instructor_page.locator(
        f"#usersTableContainer table tbody tr:has-text('{test_email}') button:has-text('Edit')"
    )
    edit_button.click()

    # Wait for edit modal to appear
    instructor_page.wait_for_selector("#editUserModal", state="visible")

    # Update first and last name
    instructor_page.fill("#editUserFirstName", "Updated")
    instructor_page.fill("#editUserLastName", "Instructor")

    # Click Save Changes
    instructor_page.click("#editUserModal button:has-text('Save Changes')")

    # Wait for modal to close (can take longer in CI)
    instructor_page.wait_for_selector("#editUserModal", state="hidden", timeout=20000)

    # Step 5: Verify the updated name appears in the table
    instructor_page.wait_for_load_state("networkidle")
    instructor_page.wait_for_function(
        "document.querySelector('#usersTableContainer')?.innerText?.includes('Updated Instructor')",
        timeout=5000,
    )

    # Verify email didn't change
    assert (
        instructor_page.locator(
            f"#usersTableContainer table tbody tr:has-text('{test_email}')"
        ).count()
        == 1
    ), "Should still have original email"


@pytest.mark.e2e
def test_tc_crud_inst_002_cannot_delete_users(
    authenticated_institution_admin_page: Page, page: Page
):
    """
    TC-CRUD-INST-002: Instructor cannot delete other users

    Steps:
    1. Create test instructor and another user
    2. Login as instructor
    3. Attempt to delete another user via API
    4. Verify 403 Forbidden

    Expected: Instructors lack permission to delete users
    """
    # Create test instructor
    mocku_id = get_institution_id_from_user(authenticated_institution_admin_page)

    # Use unique emails per test run to avoid conflicts in parallel execution
    timestamp = int(time.time() * 1000)
    instructor_email = f"test.instructor.{timestamp}@test.local"
    other_user_email = f"other.user.{timestamp}@test.local"

    instructor = create_test_user_via_api(
        admin_page=authenticated_institution_admin_page,
        base_url=BASE_URL,
        email=instructor_email,
        first_name="Test",
        last_name="Instructor",
        role="instructor",
        institution_id=mocku_id,
    )

    # Create another user to attempt deletion
    other_user = create_test_user_via_api(
        admin_page=authenticated_institution_admin_page,
        base_url=BASE_URL,
        email=other_user_email,
        first_name="Other",
        last_name="User",
        role="instructor",
        institution_id=mocku_id,
    )

    # Login as instructor
    instructor_page = login_as_user(page, BASE_URL, instructor_email, "TestUser123!")

    # Get CSRF token
    csrf_token = instructor_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Attempt to delete other user (should fail with 403)
    response = instructor_page.request.delete(
        f"{BASE_URL}/api/users/{other_user['user_id']}",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    # Verify 403 Forbidden
    assert response.status == 403, f"Expected 403, got {response.status}"


@pytest.mark.e2e
def test_tc_crud_inst_003_cannot_edit_other_users(
    authenticated_institution_admin_page: Page, page: Page
):
    """
    TC-CRUD-INST-003: Instructor cannot edit other users' profiles

    Steps:
    1. Create test instructor and another user
    2. Login as instructor
    3. Attempt to update another user's profile via API
    4. Verify 403 Forbidden

    Expected: Instructors can only edit their own profile
    """
    # Create test instructor
    mocku_id = get_institution_id_from_user(authenticated_institution_admin_page)

    # Use unique emails per test run to avoid conflicts in parallel execution
    timestamp = int(time.time() * 1000)
    instructor_email = f"test.instructor2.{timestamp}@test.local"
    other_user_email = f"other.user2.{timestamp}@test.local"

    instructor = create_test_user_via_api(
        admin_page=authenticated_institution_admin_page,
        base_url=BASE_URL,
        email=instructor_email,
        first_name="Test",
        last_name="Instructor",
        role="instructor",
        institution_id=mocku_id,
    )

    # Create another user
    other_user = create_test_user_via_api(
        admin_page=authenticated_institution_admin_page,
        base_url=BASE_URL,
        email=other_user_email,
        first_name="Other",
        last_name="User",
        role="instructor",
        institution_id=mocku_id,
    )

    # Login as instructor
    instructor_page = login_as_user(page, BASE_URL, instructor_email, "TestUser123!")

    # Get CSRF token
    csrf_token = instructor_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Attempt to update other user's profile (should fail with 403)
    response = instructor_page.request.patch(
        f"{BASE_URL}/api/users/{other_user['user_id']}/profile",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data='{"first_name": "Hacked", "last_name": "Name"}',
    )

    # Verify 403 Forbidden
    assert response.status == 403, f"Expected 403, got {response.status}"
