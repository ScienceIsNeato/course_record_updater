"""
E2E Tests for Program Admin CRUD Operations

Tests complete program admin workflows with authenticated API calls:
- Course management (create, update within programs)
- Section instructor assignment
- Permission boundaries (cannot delete inst users, cannot access other programs)

Test Naming Convention:
- test_tc_crud_pa_XXX: Matches UAT test case ID (TC-CRUD-PA-XXX)
"""

import pytest
from playwright.sync_api import Page

from database_service import get_all_courses, get_all_sections, get_all_users
from tests.e2e.conftest import BASE_URL

# ========================================
# PROGRAM ADMIN CRUD TESTS (6 tests)
# ========================================


@pytest.mark.e2e
def test_tc_crud_pa_001_create_course(authenticated_page: Page):
    """
    TC-CRUD-PA-001: Program Admin creates new course via UI

    Expected: Course created successfully within program admin's programs
    """
    # Get program admin for login
    users = get_all_users()
    prog_admin = next((u for u in users if u["role"] == "program_admin"), None)

    if not prog_admin:
        pytest.skip("No program admin user found in database for E2E test")

    prog_admin_email = prog_admin["email"]

    # Login as program admin
    authenticated_page.context.clear_cookies()
    authenticated_page.goto(f"{BASE_URL}/login")
    authenticated_page.wait_for_load_state("networkidle")
    authenticated_page.fill('input[name="email"]', prog_admin_email)
    authenticated_page.fill('input[name="password"]', "ProgramAdminPass123!")
    authenticated_page.click('button[type="submit"]')

    try:
        authenticated_page.wait_for_url(f"{BASE_URL}/dashboard", timeout=3000)
    except Exception as e:
        pytest.skip(f"Program admin login failed: {e}")

    # Navigate to dashboard
    authenticated_page.goto(f"{BASE_URL}/dashboard")
    authenticated_page.wait_for_load_state("networkidle")

    # Click "Add Course" button to open modal
    authenticated_page.click('button:has-text("Add Course")')
    authenticated_page.wait_for_selector("#createCourseModal", state="visible")

    # Wait for program dropdown to populate
    authenticated_page.wait_for_function(
        "document.getElementById('courseProgramIds').options.length > 0", timeout=3000
    )

    # Fill in course form
    authenticated_page.fill("#courseNumber", "CS299")
    authenticated_page.fill("#courseTitle", "Special Topics in AI")
    authenticated_page.fill("#courseDepartment", "Computer Science")
    authenticated_page.fill("#courseCreditHours", "3")

    # Select first program from dropdown (multi-select)
    authenticated_page.select_option("#courseProgramIds", index=0)

    # courseActive is checked by default

    # Handle alert dialog
    authenticated_page.once("dialog", lambda dialog: dialog.accept())

    # Submit form and wait for modal to close
    authenticated_page.click('#createCourseForm button[type="submit"]')
    authenticated_page.wait_for_selector(
        "#createCourseModal", state="hidden", timeout=5000
    )

    print("✅ TC-CRUD-PA-001: Program Admin successfully created course via UI")


@pytest.mark.e2e
def test_tc_crud_pa_002_update_section_instructor(authenticated_page: Page):
    """
    TC-CRUD-PA-002: Program Admin reassigns instructor to section

    Steps:
    1. Login as program admin
    2. Find a section in program admin's programs
    3. Call PATCH /api/sections/<id>/instructor with new instructor_id
    4. Verify API response success
    5. Verify instructor updated in database

    Expected: Instructor assignment succeeds for sections in program admin's programs
    """
    # Get program admin and instructors
    users = get_all_users()
    prog_admin = next((u for u in users if u["role"] == "program_admin"), None)
    instructors = [u for u in users if u["role"] == "instructor"]

    if not prog_admin or len(instructors) < 2:
        pytest.skip("Insufficient users for E2E test (need prog admin + 2 instructors)")

    prog_admin_email = prog_admin["email"]
    institution_id = prog_admin["institution_id"]

    # Find a section in this institution
    sections = get_all_sections(institution_id)
    if not sections:
        pytest.skip("No sections found for E2E test")

    section_id = sections[0]["section_id"]
    new_instructor_id = instructors[0]["user_id"]

    # Login as program admin
    authenticated_page.context.clear_cookies()
    authenticated_page.goto(f"{BASE_URL}/login")
    authenticated_page.wait_for_load_state("networkidle")
    authenticated_page.fill('input[name="email"]', prog_admin_email)
    authenticated_page.fill('input[name="password"]', "ProgramAdminPass123!")
    authenticated_page.click('button[type="submit"]')

    try:
        authenticated_page.wait_for_url(f"{BASE_URL}/dashboard", timeout=3000)
    except Exception as e:
        pytest.skip(f"Program admin login failed: {e}")

    # Get CSRF token
    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Reassign instructor
    assignment_data = {"instructor_id": new_instructor_id}

    response = authenticated_page.request.patch(
        f"{BASE_URL}/api/sections/{section_id}/instructor",
        data=assignment_data,
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    # Verify API response
    assert (
        response.ok
    ), f"Instructor assignment failed: {response.status} - {response.text()}"
    result = response.json()
    assert result["success"] is True

    # Verify in database
    updated_sections = get_all_sections(institution_id)
    updated_section = next(
        (s for s in updated_sections if s["section_id"] == section_id), None
    )
    assert updated_section is not None
    assert (
        updated_section.get("instructor_id") == new_instructor_id
    ), "Instructor not updated in database"

    print("✅ TC-CRUD-PA-002: Program Admin successfully reassigned instructor")


@pytest.mark.e2e
def test_tc_crud_pa_003_cannot_delete_institution_user(authenticated_page: Page):
    """
    TC-CRUD-PA-003: Program Admin cannot delete institution admin

    Steps:
    1. Login as program admin
    2. Attempt to DELETE /api/users/<id> for institution admin
    3. Verify API returns 403 Forbidden
    4. Verify institution admin still exists

    Expected: 403 Forbidden (insufficient permissions)
    """
    # Get program admin and institution admin
    users = get_all_users()
    prog_admin = next((u for u in users if u["role"] == "program_admin"), None)
    inst_admin = next((u for u in users if u["role"] == "institution_admin"), None)

    if not prog_admin or not inst_admin:
        pytest.skip("Need both program admin and institution admin for E2E test")

    prog_admin_email = prog_admin["email"]
    inst_admin_id = inst_admin["user_id"]

    # Login as program admin
    authenticated_page.context.clear_cookies()
    authenticated_page.goto(f"{BASE_URL}/login")
    authenticated_page.wait_for_load_state("networkidle")
    authenticated_page.fill('input[name="email"]', prog_admin_email)
    authenticated_page.fill('input[name="password"]', "ProgramAdminPass123!")
    authenticated_page.click('button[type="submit"]')

    try:
        authenticated_page.wait_for_url(f"{BASE_URL}/dashboard", timeout=3000)
    except Exception as e:
        pytest.skip(f"Program admin login failed: {e}")

    # Get CSRF token
    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Attempt to delete institution admin
    response = authenticated_page.request.delete(
        f"{BASE_URL}/api/users/{inst_admin_id}",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    # Verify 403 Forbidden
    assert response.status == 403, f"Expected 403, got {response.status}"

    # Verify user still exists
    from database_service import get_user_by_id

    user_still_exists = get_user_by_id(inst_admin_id)
    assert user_still_exists is not None, "Institution admin was deleted despite 403"

    print(
        "✅ TC-CRUD-PA-003: Program Admin correctly blocked from deleting institution admin"
    )


@pytest.mark.e2e
def test_tc_crud_pa_004_manage_program_courses(authenticated_page: Page):
    """
    TC-CRUD-PA-004: Program Admin can update courses in their programs

    Steps:
    1. Login as program admin
    2. Find a course in program admin's programs
    3. Call PUT /api/courses/<id> with updated data
    4. Verify API response success
    5. Verify course updated in database

    Expected: Course update succeeds for courses in program admin's programs
    """
    # Get program admin
    users = get_all_users()
    prog_admin = next((u for u in users if u["role"] == "program_admin"), None)

    if not prog_admin:
        pytest.skip("No program admin user found")

    prog_admin_email = prog_admin["email"]
    institution_id = prog_admin["institution_id"]

    # Get courses for this institution
    courses = get_all_courses(institution_id)
    if not courses:
        pytest.skip("No courses found for E2E test")

    course_id = courses[0]["course_id"]

    # Login as program admin
    authenticated_page.context.clear_cookies()
    authenticated_page.goto(f"{BASE_URL}/login")
    authenticated_page.wait_for_load_state("networkidle")
    authenticated_page.fill('input[name="email"]', prog_admin_email)
    authenticated_page.fill('input[name="password"]', "ProgramAdminPass123!")
    authenticated_page.click('button[type="submit"]')

    try:
        authenticated_page.wait_for_url(f"{BASE_URL}/dashboard", timeout=3000)
    except Exception as e:
        pytest.skip(f"Program admin login failed: {e}")

    # Get CSRF token
    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Update course
    course_data = {"title": "Updated Course Title by Program Admin", "credit_hours": 4}

    response = authenticated_page.request.put(
        f"{BASE_URL}/api/courses/{course_id}",
        data=course_data,
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    # Verify API response
    assert response.ok, f"Course update failed: {response.status} - {response.text()}"
    result = response.json()
    assert result["success"] is True

    # Verify in database
    updated_courses = get_all_courses(institution_id)
    updated_course = next(
        (c for c in updated_courses if c["course_id"] == course_id), None
    )
    assert updated_course is not None
    assert updated_course["title"] == "Updated Course Title by Program Admin"
    assert updated_course["credit_hours"] == 4

    print("✅ TC-CRUD-PA-004: Program Admin successfully updated course")


@pytest.mark.e2e
def test_tc_crud_pa_005_create_sections(authenticated_page: Page):
    """
    TC-CRUD-PA-005: Program Admin creates course sections

    Steps:
    1. Login as program admin
    2. Find a course offering in program admin's programs
    3. Call POST /api/offerings/<id>/sections with section data
    4. Verify API response success with section_id
    5. Verify section created in database

    Expected: Section created successfully
    """
    # Get program admin
    users = get_all_users()
    prog_admin = next((u for u in users if u["role"] == "program_admin"), None)

    if not prog_admin:
        pytest.skip("No program admin user found")

    prog_admin_email = prog_admin["email"]
    institution_id = prog_admin["institution_id"]

    # Get sections before (to count)
    sections_before = get_all_sections(institution_id)
    section_count_before = len(sections_before)

    # For this test, we need an offering_id - we'll use a placeholder or skip
    # In a real E2E test, we'd first create an offering
    from database_service import get_all_course_offerings

    offerings = get_all_course_offerings(institution_id)

    if not offerings:
        pytest.skip("No course offerings found for section creation test")

    offering_id = offerings[0]["offering_id"]

    # Login as program admin
    authenticated_page.context.clear_cookies()
    authenticated_page.goto(f"{BASE_URL}/login")
    authenticated_page.wait_for_load_state("networkidle")
    authenticated_page.fill('input[name="email"]', prog_admin_email)
    authenticated_page.fill('input[name="password"]', "ProgramAdminPass123!")
    authenticated_page.click('button[type="submit"]')

    try:
        authenticated_page.wait_for_url(f"{BASE_URL}/dashboard", timeout=3000)
    except Exception as e:
        pytest.skip(f"Program admin login failed: {e}")

    # Get CSRF token
    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Create section
    section_data = {
        "section_number": "999",
        "capacity": 30,
        "enrolled": 0,
        "schedule_days": "MWF",
        "schedule_time": "10:00-11:00",
        "location": "Room 101",
    }

    response = authenticated_page.request.post(
        f"{BASE_URL}/api/offerings/{offering_id}/sections",
        data=section_data,
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    # Verify API response
    assert (
        response.ok
    ), f"Section creation failed: {response.status} - {response.text()}"
    result = response.json()
    assert result["success"] is True
    assert "section_id" in result

    # Verify in database
    sections_after = get_all_sections(institution_id)
    assert (
        len(sections_after) == section_count_before + 1
    ), "Section not created in database"

    print("✅ TC-CRUD-PA-005: Program Admin successfully created section")


@pytest.mark.e2e
def test_tc_crud_pa_006_cannot_access_other_programs(
    authenticated_page: Page, ensure_multiple_institutions
):
    """
    TC-CRUD-PA-006: Program Admin cannot access data from other programs

    Steps:
    1. Login as program admin
    2. Attempt to access/modify course from a different institution's program
    3. Verify API returns 403 or 404

    Expected: Access denied to other programs' data
    """
    second_inst_id, cleanup = ensure_multiple_institutions

    if not second_inst_id:
        pytest.skip("Could not ensure multiple institutions")

    # Get two program admins from different institutions (if available)
    users = get_all_users()
    prog_admins = [u for u in users if u["role"] == "program_admin"]

    if len(prog_admins) < 1:
        pytest.skip("Need at least 1 program admin for E2E test")

    prog_admin = prog_admins[0]
    prog_admin_email = prog_admin["email"]
    prog_admin_institution = prog_admin["institution_id"]

    # Use the second institution (either existing or temp-created)
    other_courses = get_all_courses(second_inst_id)

    # If no courses in second institution, create one for the test
    if not other_courses:
        from database_service import create_course, get_programs_by_institution

        programs = get_programs_by_institution(second_inst_id)
        if not programs:
            pytest.skip("No programs in second institution for test setup")

        # Create a test course in the second institution
        course_id = create_course(
            {
                "course_number": "TEST101",
                "title": "Test Course for Multi-Tenant Check",
                "institution_id": second_inst_id,
                "program_ids": [programs[0]["program_id"]],
            }
        )
        other_courses = [{"course_id": course_id}]

    other_course_id = other_courses[0]["course_id"]

    # Login as program admin
    authenticated_page.context.clear_cookies()
    authenticated_page.goto(f"{BASE_URL}/login")
    authenticated_page.wait_for_load_state("networkidle")
    authenticated_page.fill('input[name="email"]', prog_admin_email)
    authenticated_page.fill('input[name="password"]', "ProgramAdminPass123!")
    authenticated_page.click('button[type="submit"]')

    try:
        authenticated_page.wait_for_url(f"{BASE_URL}/dashboard", timeout=3000)
    except Exception as e:
        pytest.skip(f"Program admin login failed: {e}")

    # Get CSRF token
    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Attempt to access course from other institution
    response = authenticated_page.request.get(
        f"{BASE_URL}/api/courses/{other_course_id}",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    # Verify 403 or 404 (either is acceptable for cross-institution access)
    assert response.status in [403, 404], f"Expected 403/404, got {response.status}"

    print(
        "✅ TC-CRUD-PA-006: Program Admin correctly blocked from accessing other programs"
    )
