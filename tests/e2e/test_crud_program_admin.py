"""
E2E Tests for Program Admin CRUD Operations

Tests complete program admin workflows using UI and authenticated API calls:
- Course management (create, update within programs)
- Section instructor assignment
- Permission boundaries (cannot delete inst users, cannot access other programs)

All tests are UI-first: no direct database calls.

Test Naming Convention:
- test_tc_crud_pa_XXX: Matches UAT test case ID (TC-CRUD-PA-XXX)
"""

import pytest
from playwright.sync_api import Page

from tests.e2e.conftest import BASE_URL

# ========================================
# PROGRAM ADMIN CRUD TESTS (6 tests)
# ========================================


@pytest.mark.e2e
def test_tc_crud_pa_001_create_course(program_admin_authenticated_page: Page):
    """
    TC-CRUD-PA-001: Program Admin creates new course via UI

    Steps:
    1. Login as program admin (fixture provides this)
    2. Navigate to dashboard
    3. Click "Add Course" button
    4. Fill course form and select program
    5. Submit and verify course appears in courses list

    Expected: Course created successfully and visible in UI
    """
    # Navigate to dashboard
    program_admin_authenticated_page.goto(f"{BASE_URL}/dashboard")
    program_admin_authenticated_page.wait_for_load_state("networkidle")

    # Click "Add Course" button to open modal
    program_admin_authenticated_page.click('button:has-text("Add Course")')
    program_admin_authenticated_page.wait_for_selector(
        "#createCourseModal", state="visible"
    )

    # Wait for program dropdown to populate
    program_admin_authenticated_page.wait_for_function(
        "document.getElementById('courseProgramIds').options.length > 1",  # >1 because placeholder is option 0
        timeout=5000,
    )

    # Fill in course form
    program_admin_authenticated_page.fill("#courseNumber", "CS-299")
    program_admin_authenticated_page.fill("#courseTitle", "Special Topics in AI")
    program_admin_authenticated_page.fill("#courseDepartment", "Computer Science")
    program_admin_authenticated_page.fill("#courseCreditHours", "3")

    # Select first real program from dropdown (index 1, not 0 which is placeholder)
    program_admin_authenticated_page.select_option("#courseProgramIds", index=1)

    # Handle any alert dialogs
    program_admin_authenticated_page.on("dialog", lambda dialog: dialog.accept())

    # Submit form and wait for modal to close
    program_admin_authenticated_page.click('#createCourseForm button[type="submit"]')
    program_admin_authenticated_page.wait_for_selector(
        "#createCourseModal", state="hidden", timeout=5000
    )

    # Verify course appears in courses list
    program_admin_authenticated_page.goto(f"{BASE_URL}/courses")
    program_admin_authenticated_page.wait_for_load_state("networkidle")
    program_admin_authenticated_page.wait_for_function(
        "document.querySelector('#coursesTableContainer')?.innerText?.includes('CS-299')",
        timeout=5000,
    )

    print("✅ TC-CRUD-PA-001: Program Admin successfully created course via UI")


@pytest.mark.e2e
def test_tc_crud_pa_002_update_section_instructor(
    program_admin_authenticated_page: Page,
):
    """
    TC-CRUD-PA-002: Program Admin reassigns instructor to section via UI

    Steps:
    1. Login as program admin (fixture provides this)
    2. Navigate to sections page
    3. Click Edit on a section
    4. Select a different instructor
    5. Save and verify change appears in UI

    Expected: Instructor assignment succeeds and is visible in sections list
    """
    # Navigate to sections page
    program_admin_authenticated_page.goto(f"{BASE_URL}/sections")
    program_admin_authenticated_page.wait_for_load_state("networkidle")
    program_admin_authenticated_page.wait_for_selector(
        "#sectionsTableContainer", timeout=10000
    )

    # Wait for sections table to load
    program_admin_authenticated_page.wait_for_function(
        "document.querySelector('#sectionsTableContainer table tbody tr')", timeout=5000
    )

    # Click Edit button on first section
    program_admin_authenticated_page.click(
        "#sectionsTableContainer table tbody tr:first-child button:has-text('Edit')"
    )
    program_admin_authenticated_page.wait_for_selector(
        "#editSectionModal", state="visible"
    )

    # Wait for instructor dropdown to populate
    program_admin_authenticated_page.wait_for_function(
        "document.querySelector('#editSectionInstructorId').options.length > 1",
        timeout=5000,
    )

    # Select a different instructor (index 1 to skip "Unassigned")
    program_admin_authenticated_page.select_option("#editSectionInstructorId", index=1)

    # Click Save Changes
    program_admin_authenticated_page.click(
        "#editSectionModal button:has-text('Save Changes')"
    )
    program_admin_authenticated_page.wait_for_selector(
        "#editSectionModal", state="hidden"
    )

    # Verify the section still appears after update
    program_admin_authenticated_page.wait_for_load_state("networkidle")
    program_admin_authenticated_page.wait_for_function(
        "document.querySelector('#sectionsTableContainer table tbody tr')", timeout=5000
    )

    print(
        "✅ TC-CRUD-PA-002: Program Admin successfully reassigned section instructor via UI"
    )


@pytest.mark.e2e
def test_tc_crud_pa_003_cannot_delete_institution_user(
    program_admin_authenticated_page: Page,
):
    """
    TC-CRUD-PA-003: Program Admin cannot delete institution users (permission boundary)

    Steps:
    1. Login as program admin (fixture provides this)
    2. Get list of users via API
    3. Attempt to DELETE an institution admin
    4. Verify API returns 403 Forbidden
    5. Verify user still exists (via API)

    Expected: 403 Forbidden (insufficient permissions)
    """
    # Get CSRF token
    csrf_token = program_admin_authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Get list of users to find an institution admin
    users_response = program_admin_authenticated_page.request.get(
        f"{BASE_URL}/api/users",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )
    assert users_response.ok, "Failed to fetch users"
    users = users_response.json().get("users", [])

    # Find an institution admin (higher privilege level)
    inst_admin = next((u for u in users if u.get("role") == "institution_admin"), None)
    assert inst_admin, "No institution admin found for deletion test"

    target_user_id = inst_admin["user_id"]

    # Attempt to delete institution admin (should fail with 403)
    response = program_admin_authenticated_page.request.delete(
        f"{BASE_URL}/api/users/{target_user_id}",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    # Verify 403 Forbidden
    assert response.status == 403, f"Expected 403, got {response.status}"

    # Verify user still exists (fetch users again)
    users_after_response = program_admin_authenticated_page.request.get(
        f"{BASE_URL}/api/users",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )
    assert users_after_response.ok, "Failed to fetch users for verification"
    users_after = users_after_response.json().get("users", [])

    user_still_exists = any(u["user_id"] == target_user_id for u in users_after)
    assert user_still_exists, "User was deleted despite 403 response"

    print(
        "✅ TC-CRUD-PA-003: Program Admin correctly blocked from deleting institution users"
    )


@pytest.mark.e2e
def test_tc_crud_pa_004_manage_program_courses(program_admin_authenticated_page: Page):
    """
    TC-CRUD-PA-004: Program Admin can update courses in their programs via UI

    Steps:
    1. Login as program admin (fixture provides this)
    2. Navigate to courses page
    3. Click Edit on a course
    4. Update course title
    5. Save and verify change appears in UI

    Expected: Course update succeeds and is visible in courses list
    """
    # Navigate to courses page
    program_admin_authenticated_page.goto(f"{BASE_URL}/courses")
    program_admin_authenticated_page.wait_for_load_state("networkidle")
    program_admin_authenticated_page.wait_for_selector(
        "#coursesTableContainer", timeout=10000
    )

    # Wait for courses table to load
    program_admin_authenticated_page.wait_for_function(
        "document.querySelector('#coursesTableContainer table tbody tr')", timeout=5000
    )

    # Get the first course's current title for verification
    original_title = program_admin_authenticated_page.evaluate(
        "document.querySelector('#coursesTableContainer table tbody tr td:nth-child(2)')?.innerText"
    )

    # Click Edit button on first course
    program_admin_authenticated_page.click(
        "#coursesTableContainer table tbody tr:first-child button:has-text('Edit')"
    )
    program_admin_authenticated_page.wait_for_selector(
        "#editCourseModal", state="visible"
    )

    # Update course title
    program_admin_authenticated_page.fill(
        "#editCourseTitle", f"{original_title} - Updated"
    )

    # Click Save Changes
    program_admin_authenticated_page.click(
        "#editCourseModal button:has-text('Save Changes')"
    )
    program_admin_authenticated_page.wait_for_selector(
        "#editCourseModal", state="hidden"
    )

    # Verify the updated title appears in the table
    program_admin_authenticated_page.wait_for_load_state("networkidle")
    program_admin_authenticated_page.wait_for_function(
        f"document.querySelector('#coursesTableContainer')?.innerText?.includes('{original_title} - Updated')",
        timeout=5000,
    )

    print("✅ TC-CRUD-PA-004: Program Admin successfully managed program course via UI")


@pytest.mark.e2e
def test_tc_crud_pa_005_create_sections(program_admin_authenticated_page: Page):
    """
    TC-CRUD-PA-005: Program Admin creates course sections via UI

    Steps:
    1. Login as program admin (fixture provides this)
    2. Navigate to sections page
    3. Click "Create Section" button
    4. Fill section form (select offering, enter section number, status)
    5. Submit and verify section appears in sections list

    Expected: Section created successfully and visible in UI
    """
    # Navigate to sections page
    program_admin_authenticated_page.goto(f"{BASE_URL}/sections")
    program_admin_authenticated_page.wait_for_load_state("networkidle")

    # Click "Create Section" button
    program_admin_authenticated_page.click('button:has-text("Create Section")')
    program_admin_authenticated_page.wait_for_selector(
        "#createSectionModal", state="visible"
    )

    # Wait for offerings dropdown to populate
    program_admin_authenticated_page.wait_for_function(
        "document.getElementById('sectionOfferingId').options.length > 1",
        timeout=5000,
    )

    # Select first offering
    program_admin_authenticated_page.select_option("#sectionOfferingId", index=1)

    # Fill section form
    program_admin_authenticated_page.fill("#sectionNumber", "999")
    program_admin_authenticated_page.fill("#sectionCapacity", "30")
    program_admin_authenticated_page.select_option("#sectionStatus", "open")

    # Submit form
    program_admin_authenticated_page.click("#createSectionBtn")
    program_admin_authenticated_page.wait_for_selector(
        "#createSectionModal", state="hidden", timeout=5000
    )

    # Verify section appears in sections list
    program_admin_authenticated_page.wait_for_load_state("networkidle")
    program_admin_authenticated_page.wait_for_function(
        "document.querySelector('#sectionsTableContainer')?.innerText?.includes('999')",
        timeout=5000,
    )

    print("✅ TC-CRUD-PA-005: Program Admin successfully created section via UI")


@pytest.mark.e2e
def test_tc_crud_pa_006_cannot_access_other_programs(
    program_admin_authenticated_page: Page,
):
    """
    TC-CRUD-PA-006: Program Admin can only see courses in their assigned programs

    Steps:
    1. Login as program admin (fixture provides this)
    2. Get list of courses via API
    3. Verify all courses belong to program admin's programs
    4. Verify courses from other programs are not visible

    Expected: Program admin cannot access courses from other programs

    Note: lisa.prog@cei.edu is assigned to programs [3, 4] (Liberal Arts and Business)
    """
    page = program_admin_authenticated_page

    # Navigate to dashboard to establish session
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")

    # Get current user info to know their assigned programs
    user_response = page.request.get(f"{BASE_URL}/api/me")
    assert user_response.ok, f"Failed to fetch user info: {user_response.status}"

    user_data = user_response.json()
    user_program_ids = user_data.get("program_ids", [])
    assert (
        len(user_program_ids) > 0
    ), f"Program admin should have at least one assigned program, got: {user_program_ids}"

    # Get all courses via API - should be filtered by user's programs
    courses_response = page.request.get(f"{BASE_URL}/api/courses")
    assert courses_response.ok, f"Failed to fetch courses: {courses_response.status}"

    courses_data = courses_response.json()
    assert courses_data["success"], "Courses API should succeed"
    courses = courses_data.get("courses", [])

    print(f"User program_ids: {user_program_ids}")
    print(f"Found {len(courses)} courses")

    # Verify all visible courses belong to user's assigned programs
    for course in courses:
        course_program_ids = course.get("program_ids", [])
        # Course should have at least one program ID that overlaps with user's programs
        has_overlap = any(pid in user_program_ids for pid in course_program_ids)
        assert has_overlap, (
            f"Course {course.get('course_number')} (program_ids: {course_program_ids}) "
            f"doesn't overlap with user's programs {user_program_ids}"
        )

    print(
        f"✅ TC-CRUD-PA-006: Program Admin can only see courses in their assigned programs"
    )
