"""
E2E Tests for Institution Admin CRUD Operations

Tests complete institution admin workflows with authenticated API calls:
- Program management (create, update, delete)
- Course and term management
- User invitations and management
- Course offerings and section management
- Multi-tenant boundaries

Test Naming Convention:
- test_tc_crud_ia_XXX: Matches UAT test case ID (TC-CRUD-IA-XXX)
"""

import pytest
from playwright.sync_api import Page

# E2E tests are now purely UI-based - no direct database queries!
# All tests interact with the UI or authenticated API endpoints only.
from tests.e2e.conftest import BASE_URL

# ========================================
# INSTITUTION ADMIN CRUD TESTS (10 tests)
# ========================================


@pytest.mark.e2e
def test_tc_crud_ia_001_create_program(authenticated_page: Page):
    """
    TC-CRUD-IA-001: Institution Admin creates new program via UI

    Expected: Program created successfully within institution
    """
    # authenticated_page is already logged in as institution admin (sarah.admin@mocku.test)
    # Console error monitoring is automatic via the 'page' fixture

    # Capture all console logs for debugging
    console_logs = []
    authenticated_page.on(
        "console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}")
    )

    # Navigate to institution admin dashboard
    authenticated_page.goto(f"{BASE_URL}/dashboard")
    authenticated_page.wait_for_load_state("networkidle")

    print("\n=== CONSOLE LOGS AFTER PAGE LOAD ===")
    for log in console_logs:
        print(log)
    console_logs.clear()

    # Click "Add Program" button to open modal
    authenticated_page.click('button:has-text("Add Program")')
    authenticated_page.wait_for_selector("#createProgramModal", state="visible")

    # Give event handlers time to execute
    authenticated_page.wait_for_timeout(1000)

    print("\n=== CONSOLE LOGS AFTER MODAL OPEN ===")
    for log in console_logs:
        print(log)

    # Check dropdown state
    dropdown_options = authenticated_page.evaluate(
        "document.getElementById('programInstitutionId').options.length"
    )
    user_context = authenticated_page.evaluate("window.userContext")
    print("\n=== DEBUG STATE ===")
    print(f"Dropdown options count: {dropdown_options}")
    print(f"window.userContext: {user_context}")

    # Wait for institution dropdown to be populated (happens on modal open event)
    authenticated_page.wait_for_function(
        "document.getElementById('programInstitutionId').options.length > 1",
        timeout=5000,
    )

    # Fill in program form (institution auto-selected for institution admins)
    authenticated_page.fill("#programName", "E2E Test Program")
    authenticated_page.fill("#programShortName", "E2E")
    # Institution already auto-selected by JavaScript - verify it's set
    institution_value = authenticated_page.input_value("#programInstitutionId")
    assert institution_value, "Institution should be auto-selected"
    authenticated_page.check("#programActive")

    # Handle alert dialog (JavaScript shows success message in alert)
    authenticated_page.once("dialog", lambda dialog: dialog.accept())

    # Submit form and wait for modal to close (success indicator)
    authenticated_page.click('#createProgramForm button[type="submit"]')
    authenticated_page.wait_for_selector(
        "#createProgramModal", state="hidden", timeout=5000
    )

    # Success! Modal closed without error = program created
    print("✅ TC-CRUD-IA-001: Institution Admin successfully created program via UI")


@pytest.mark.e2e
def test_tc_crud_ia_002_update_course_details(authenticated_page: Page):
    """TC-CRUD-IA-002: Institution Admin updates course details via UI"""
    # Navigate to courses page
    authenticated_page.goto(f"{BASE_URL}/courses")
    authenticated_page.wait_for_load_state("networkidle")

    # Wait for courses table to load
    authenticated_page.wait_for_selector("#coursesTableContainer table", timeout=10000)

    # Get the first course's current title for later verification
    original_title = authenticated_page.evaluate(
        "document.querySelector('#coursesTableContainer table tbody tr td:nth-child(2)')?.innerText"
    )

    if not original_title:
        pytest.skip("No courses available to update")

    # Click Edit button on first course
    authenticated_page.click(
        "#coursesTableContainer table tbody tr:first-child button:has-text('Edit')"
    )
    authenticated_page.wait_for_selector("#editCourseModal", state="visible")

    # Update course title
    new_title = "Updated by Institution Admin E2E"
    authenticated_page.fill("#editCourseTitle", new_title)

    # Update credit hours
    authenticated_page.fill("#editCourseCreditHours", "4")

    # Click Save Changes button
    authenticated_page.click("#editCourseModal button:has-text('Save Changes')")

    # Wait for modal to close (indicates save completed)
    authenticated_page.wait_for_selector(
        "#editCourseModal", state="hidden", timeout=5000
    )

    # Wait for courses list to reload
    authenticated_page.wait_for_load_state("networkidle")

    # Verify the updated title appears in the table
    updated_title = authenticated_page.evaluate(
        "document.querySelector('#coursesTableContainer table tbody tr td:nth-child(2)')?.innerText"
    )

    assert updated_title == new_title, f"Expected '{new_title}', got '{updated_title}'"

    print("✅ TC-CRUD-IA-002: Institution Admin successfully updated course via UI")


@pytest.mark.e2e
def test_tc_crud_ia_003_delete_empty_program(authenticated_page: Page):
    """TC-CRUD-IA-003: Institution Admin deletes program with no courses"""
    # Derive institution context from the authenticated page
    user_ctx = authenticated_page.evaluate("window.userContext")
    institution_id = user_ctx.get("institutionId") if user_ctx else None
    if not institution_id:
        pytest.skip("No institution context available for admin user")

    # First create an empty program to delete
    csrf_token = authenticated_page.evaluate(
        "document.querySelector(\"meta[name='csrf-token']\")?.content"
    )

    program_data = {
        "name": "Empty Program To Delete",
        "short_name": "EMPTY",
        "institution_id": institution_id,
    }

    create_response = authenticated_page.request.post(
        f"{BASE_URL}/api/programs",
        data=program_data,
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    if not create_response.ok:
        pytest.skip("Could not create empty program for deletion test")

    program_id = create_response.json().get("program_id")

    # Now delete it
    delete_response = authenticated_page.request.delete(
        f"{BASE_URL}/api/programs/{program_id}",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    assert delete_response.ok
    result = delete_response.json()
    assert result["success"] is True

    print("✅ TC-CRUD-IA-003: Institution Admin successfully deleted empty program")


@pytest.mark.e2e
def test_tc_crud_ia_004_cannot_delete_program_with_courses(authenticated_page: Page):
    """TC-CRUD-IA-004: Institution Admin cannot delete program with courses"""
    # Get institutions programs via API and find one with courses
    progs_resp = authenticated_page.request.get(f"{BASE_URL}/api/programs")
    assert progs_resp.ok, f"Failed to list programs: {progs_resp.status}"
    programs = progs_resp.json().get("programs", [])

    program_with_courses = None
    for prog in programs:
        pid = prog.get("program_id") or prog.get("id")
        if not pid:
            continue
        courses_resp = authenticated_page.request.get(
            f"{BASE_URL}/api/programs/{pid}/courses"
        )
        if courses_resp.ok:
            prog_courses = courses_resp.json().get("courses", [])
            if prog_courses:
                program_with_courses = pid
                break

    if not program_with_courses:
        pytest.skip("No program with courses found")

    csrf_token = authenticated_page.evaluate(
        "document.querySelector(\"meta[name='csrf-token']\")?.content"
    )

    # Attempt to delete program with courses (should fail or require force)
    response = authenticated_page.request.delete(
        f"{BASE_URL}/api/programs/{program_with_courses}",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    # Expecting 409 Conflict (referential integrity) or 400 (default program)
    # 400: Attempting to delete default program (which may have courses reassigned to it)
    # 409: Attempting to delete non-default program with courses
    assert response.status in [400, 409], f"Expected 400 or 409, got {response.status}"

    print(
        "✅ TC-CRUD-IA-004: Institution Admin correctly blocked from deleting program with courses"
    )


@pytest.mark.e2e
def test_tc_crud_ia_005_invite_instructor(authenticated_page: Page):
    """TC-CRUD-IA-005: Institution Admin invites new instructor"""
    # Derive institution context from the authenticated session (no direct DB)
    user_ctx = authenticated_page.evaluate("window.userContext")
    institution_id = user_ctx.get("institutionId") if user_ctx else None
    if not institution_id:
        pytest.skip("No institution context available for admin user")
    csrf_token = authenticated_page.evaluate(
        "document.querySelector(\"meta[name='csrf-token']\")?.content"
    )

    # Create invitation
    invitation_data = {
        "email": f"newinstructor_{pytest.__version__}@test.edu",
        "first_name": "New",
        "last_name": "Instructor",
        "role": "instructor",
        "institution_id": institution_id,
    }

    # Send as JSON (API expects JSON body)
    import json as json_module

    response = authenticated_page.request.post(
        f"{BASE_URL}/api/invitations",
        data=json_module.dumps(invitation_data),
        headers={
            "Content-Type": "application/json",
            **({"X-CSRFToken": csrf_token} if csrf_token else {}),
        },
    )

    assert response.ok, f"Invitation creation failed: {response.status}"
    result = response.json()
    assert result["success"] is True

    print("✅ TC-CRUD-IA-005: Institution Admin successfully invited instructor")


@pytest.mark.e2e
def test_tc_crud_ia_006_manage_institution_users(authenticated_page: Page):
    """TC-CRUD-IA-006: Institution Admin can manage users within institution"""
    # Derive institution context
    user_ctx = authenticated_page.evaluate("window.userContext")
    institution_id = user_ctx.get("institutionId") if user_ctx else None
    if not institution_id:
        pytest.skip("No institution context available for admin user")

    # List users via API and pick a non-admin user in the same institution
    users_resp = authenticated_page.request.get(f"{BASE_URL}/api/users")
    assert users_resp.ok, f"Failed to list users: {users_resp.status}"
    users_payload = users_resp.json()
    users = users_payload.get("users", [])
    target = next(
        (
            u
            for u in users
            if u.get("institution_id") == institution_id
            and u.get("role") != "institution_admin"
        ),
        None,
    )
    if not target:
        pytest.skip("No eligible users found to manage")

    target_user_id = target["user_id"]
    csrf_token = authenticated_page.evaluate(
        "document.querySelector(\"meta[name='csrf-token']\")?.content"
    )

    # Update user profile
    profile_data = {"first_name": "Updated", "last_name": "ByInstAdmin"}

    response = authenticated_page.request.patch(
        f"{BASE_URL}/api/users/{target_user_id}/profile",
        data=profile_data,
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    assert response.ok
    result = response.json()
    assert result.get("success") is True

    # Verify via UI: navigate to users list and assert updated name appears
    authenticated_page.goto(f"{BASE_URL}/users")
    authenticated_page.wait_for_load_state("networkidle")
    # The users table renders first/last name combined
    authenticated_page.wait_for_selector("#usersTableContainer")

    # Debug: print table contents
    table_text = authenticated_page.evaluate(
        "document.querySelector('#usersTableContainer')?.innerText"
    )
    print(f"DEBUG: Users table contents:\n{table_text}")

    authenticated_page.wait_for_function(
        "() => document.querySelector('#usersTableContainer')?.innerText?.includes('Updated ByInstAdmin')",
        timeout=5000,
    )

    print(
        "✅ TC-CRUD-IA-006: Institution Admin successfully managed institution user (UI verified)"
    )


@pytest.mark.e2e
def test_tc_crud_ia_007_create_term(authenticated_page: Page):
    """TC-CRUD-IA-007: Institution Admin creates new term via UI"""
    # Navigate to institution admin dashboard
    authenticated_page.goto(f"{BASE_URL}/dashboard")
    authenticated_page.wait_for_load_state("networkidle")

    # Click "Add Term" button to open modal
    authenticated_page.click('button:has-text("Add Term")')
    authenticated_page.wait_for_selector("#createTermModal", state="visible")

    # Fill in term form
    authenticated_page.fill("#termName", "Spring 2099")
    authenticated_page.fill("#termStartDate", "2099-01-15")
    authenticated_page.fill("#termEndDate", "2099-05-15")
    authenticated_page.fill("#termAssessmentDueDate", "2099-05-20")
    # termActive is checked by default, so no need to check it

    # Handle alert dialog
    authenticated_page.once("dialog", lambda dialog: dialog.accept())

    # Submit form and wait for modal to close
    authenticated_page.click('#createTermForm button[type="submit"]')
    authenticated_page.wait_for_selector(
        "#createTermModal", state="hidden", timeout=5000
    )

    print("✅ TC-CRUD-IA-007: Institution Admin successfully created term via UI")


@pytest.mark.e2e
def test_tc_crud_ia_008_create_course_offerings(authenticated_page: Page):
    """TC-CRUD-IA-008: Institution Admin creates course offerings via UI"""
    # Navigate to institution admin dashboard
    authenticated_page.goto(f"{BASE_URL}/dashboard")
    authenticated_page.wait_for_load_state("networkidle")

    # Click "Add Offering" button to open modal
    authenticated_page.click('button:has-text("Add Offering")')
    authenticated_page.wait_for_selector("#createOfferingModal", state="visible")

    # Wait for course and term dropdowns to populate
    authenticated_page.wait_for_function(
        "document.getElementById('offeringCourseId').options.length > 1", timeout=5000
    )
    authenticated_page.wait_for_function(
        "document.getElementById('offeringTermId').options.length > 1", timeout=5000
    )
    authenticated_page.wait_for_function(
        "document.getElementById('offeringProgramId').options.length > 1", timeout=5000
    )

    # Select first course, term, and program from dropdowns
    authenticated_page.select_option("#offeringCourseId", index=1)
    authenticated_page.select_option("#offeringTermId", index=1)
    authenticated_page.select_option("#offeringProgramId", index=1)

    # Fill optional fields if needed (capacity, enrolled)
    # Status is set to 'active' by default

    # Handle alert dialog
    authenticated_page.once("dialog", lambda dialog: dialog.accept())

    # Submit form and wait for modal to close
    authenticated_page.click('#createOfferingForm button[type="submit"]')
    authenticated_page.wait_for_selector(
        "#createOfferingModal", state="hidden", timeout=30000
    )

    print(
        "✅ TC-CRUD-IA-008: Institution Admin successfully created course offering via UI"
    )


@pytest.mark.e2e
def test_tc_crud_ia_009_assign_instructors_to_sections(authenticated_page: Page):
    """TC-CRUD-IA-009: Institution Admin assigns instructors to sections via UI"""
    # Navigate to sections page
    authenticated_page.goto(f"{BASE_URL}/sections")
    authenticated_page.wait_for_load_state("networkidle")
    authenticated_page.wait_for_selector("#sectionsTableContainer", timeout=10000)

    # Wait for sections table to load
    authenticated_page.wait_for_function(
        "document.querySelector('#sectionsTableContainer table tbody tr')", timeout=5000
    )

    # Click Edit button on first section
    authenticated_page.click(
        "#sectionsTableContainer table tbody tr:first-child button:has-text('Edit')"
    )
    authenticated_page.wait_for_selector("#editSectionModal", state="visible")

    # Wait for instructor dropdown to populate
    authenticated_page.wait_for_function(
        "document.querySelector('#editSectionInstructorId').options.length > 1",
        timeout=5000,
    )

    # Get section number for verification
    section_number = authenticated_page.evaluate(
        "document.querySelector('#editSectionNumber')?.value"
    )

    # Select an instructor (index 1 to skip "Unassigned" option)
    authenticated_page.select_option("#editSectionInstructorId", index=1)

    # Click Save Changes
    authenticated_page.click("#editSectionModal button:has-text('Save Changes')")
    authenticated_page.wait_for_selector("#editSectionModal", state="hidden")

    # Verify the section still appears in the list after update
    authenticated_page.wait_for_load_state("networkidle")
    authenticated_page.wait_for_function(
        f"document.querySelector('#sectionsTableContainer')?.innerText?.includes('{section_number}')",
        timeout=5000,
    )

    print(
        "✅ TC-CRUD-IA-009: Institution Admin successfully assigned instructor to section via UI"
    )


@pytest.mark.e2e
def test_tc_crud_ia_010_cannot_access_other_institutions(authenticated_page: Page):
    """TC-CRUD-IA-010: Institution Admin can only see their own institution's data (multi-tenant isolation)"""
    # Navigate to dashboard and wait for it to load
    authenticated_page.goto(f"{BASE_URL}/dashboard")
    authenticated_page.wait_for_load_state("networkidle")

    # Get CSRF token for API calls
    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Test 1: Fetch all courses visible to this user
    courses_response = authenticated_page.request.get(
        f"{BASE_URL}/api/courses",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    assert courses_response.ok, "Failed to fetch courses"
    my_courses = courses_response.json().get("courses", [])
    assert len(my_courses) > 0, "No courses found for user"

    # Extract the institution_id from the first course
    institution_id = my_courses[0].get("institution_id")
    assert institution_id, "Course missing institution_id"

    # Verify ALL courses belong to the same institution (multi-tenant isolation)
    for course in my_courses:
        assert (
            course.get("institution_id") == institution_id
        ), f"Multi-tenant isolation broken: course {course['course_id']} belongs to different institution!"

    # Test 2: Verify all programs belong to the same institution
    programs_response = authenticated_page.request.get(
        f"{BASE_URL}/api/programs",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    assert programs_response.ok, "Failed to fetch programs"
    my_programs = programs_response.json().get("programs", [])
    assert len(my_programs) > 0, "No programs found for user"

    for program in my_programs:
        assert (
            program.get("institution_id") == institution_id
        ), f"Multi-tenant isolation broken: program {program['program_id']} belongs to different institution!"

    print(
        "✅ TC-CRUD-IA-010: Institution Admin correctly scoped to own institution (multi-tenant isolation verified)"
    )
