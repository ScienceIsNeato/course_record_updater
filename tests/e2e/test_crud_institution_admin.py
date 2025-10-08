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

# E2E tests should be purely UI-based - no direct database queries!
# If we need to verify something, we do it through the UI or API endpoints
#
# TODO: The remaining tests (002-010) still use direct DB queries and need conversion
# Keeping these imports temporarily until all tests are converted to UI-based approach
from database_service import (
    get_active_terms,
    get_all_course_offerings,
    get_all_courses,
    get_all_sections,
    get_all_users,
    get_programs_by_institution,
)
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
    # authenticated_page is already logged in as institution admin (sarah.admin@cei.edu)
    # Console error monitoring is automatic via the 'page' fixture

    # Navigate to institution admin dashboard
    authenticated_page.goto(f"{BASE_URL}/dashboard")
    authenticated_page.wait_for_load_state("networkidle")

    # Click "Add Program" button to open modal
    authenticated_page.click('button:has-text("Add Program")')
    authenticated_page.wait_for_selector("#createProgramModal", state="visible")

    # Wait for institution dropdown to be populated (happens on modal shown event)
    authenticated_page.wait_for_function(
        "document.getElementById('programInstitutionId').options.length > 1",
        timeout=3000,
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
    """TC-CRUD-IA-002: Institution Admin updates course details"""
    users = get_all_users()
    inst_admin = next((u for u in users if u["role"] == "institution_admin"), None)

    if not inst_admin:
        pytest.skip("No institution admin found")

    institution_id = inst_admin["institution_id"]
    courses = get_all_courses(institution_id)

    if not courses:
        pytest.skip("No courses found")

    course_id = courses[0]["course_id"]
    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    course_data = {"title": "Updated by Institution Admin", "credit_hours": 4}

    response = authenticated_page.request.put(
        f"{BASE_URL}/api/courses/{course_id}",
        data=course_data,
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    assert response.ok
    result = response.json()
    assert result["success"] is True

    print("✅ TC-CRUD-IA-002: Institution Admin successfully updated course")


@pytest.mark.e2e
def test_tc_crud_ia_003_delete_empty_program(authenticated_page: Page):
    """TC-CRUD-IA-003: Institution Admin deletes program with no courses"""
    users = get_all_users()
    inst_admin = next((u for u in users if u["role"] == "institution_admin"), None)

    if not inst_admin:
        pytest.skip("No institution admin found")

    institution_id = inst_admin["institution_id"]

    # First create an empty program to delete
    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
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
    users = get_all_users()
    inst_admin = next((u for u in users if u["role"] == "institution_admin"), None)

    if not inst_admin:
        pytest.skip("No institution admin found")

    institution_id = inst_admin["institution_id"]
    programs = get_programs_by_institution(institution_id)
    courses = get_all_courses(institution_id)

    # Find a program with courses
    program_with_courses = None
    for program in programs:
        if any(
            c.get("program_ids") and program["program_id"] in c.get("program_ids", [])
            for c in courses
        ):
            program_with_courses = program
            break

    if not program_with_courses:
        pytest.skip("No program with courses found")

    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Attempt to delete program with courses (should fail or require force)
    response = authenticated_page.request.delete(
        f"{BASE_URL}/api/programs/{program_with_courses['program_id']}",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    # Expecting 400 or 403 (referential integrity violation)
    assert response.status in [400, 403], f"Expected 400/403, got {response.status}"

    print(
        "✅ TC-CRUD-IA-004: Institution Admin correctly blocked from deleting program with courses"
    )


@pytest.mark.e2e
def test_tc_crud_ia_005_invite_instructor(authenticated_page: Page):
    """TC-CRUD-IA-005: Institution Admin invites new instructor"""
    users = get_all_users()
    inst_admin = next((u for u in users if u["role"] == "institution_admin"), None)

    if not inst_admin:
        pytest.skip("No institution admin found")

    institution_id = inst_admin["institution_id"]
    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Create invitation
    invitation_data = {
        "email": f"newinstructor_{pytest.__version__}@test.edu",
        "first_name": "New",
        "last_name": "Instructor",
        "role": "instructor",
        "institution_id": institution_id,
    }

    response = authenticated_page.request.post(
        f"{BASE_URL}/api/invitations",
        data=invitation_data,
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    assert response.ok, f"Invitation creation failed: {response.status}"
    result = response.json()
    assert result["success"] is True

    print("✅ TC-CRUD-IA-005: Institution Admin successfully invited instructor")


@pytest.mark.e2e
def test_tc_crud_ia_006_manage_institution_users(authenticated_page: Page):
    """TC-CRUD-IA-006: Institution Admin can manage users within institution"""
    users = get_all_users()
    inst_admin = next((u for u in users if u["role"] == "institution_admin"), None)

    if not inst_admin:
        pytest.skip("No institution admin found")

    # Find a user in the same institution
    institution_id = inst_admin["institution_id"]
    inst_users = [
        u
        for u in users
        if u.get("institution_id") == institution_id
        and u["user_id"] != inst_admin["user_id"]
    ]

    if not inst_users:
        pytest.skip("No other users in institution")

    target_user_id = inst_users[0]["user_id"]
    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
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
    assert result["success"] is True

    print("✅ TC-CRUD-IA-006: Institution Admin successfully managed institution user")


@pytest.mark.e2e
def test_tc_crud_ia_007_create_term(authenticated_page: Page):
    """TC-CRUD-IA-007: Institution Admin creates new term"""
    users = get_all_users()
    inst_admin = next((u for u in users if u["role"] == "institution_admin"), None)

    if not inst_admin:
        pytest.skip("No institution admin found")

    institution_id = inst_admin["institution_id"]
    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    term_data = {
        "term_name": "SP2099",
        "name": "Spring 2099",
        "start_date": "2099-01-15",
        "end_date": "2099-05-15",
        "is_active": True,
        "institution_id": institution_id,
    }

    response = authenticated_page.request.post(
        f"{BASE_URL}/api/terms",
        data=term_data,
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    assert response.ok
    result = response.json()
    assert result["success"] is True

    print("✅ TC-CRUD-IA-007: Institution Admin successfully created term")


@pytest.mark.e2e
def test_tc_crud_ia_008_create_course_offerings(authenticated_page: Page):
    """TC-CRUD-IA-008: Institution Admin creates course offerings"""
    users = get_all_users()
    inst_admin = next((u for u in users if u["role"] == "institution_admin"), None)

    if not inst_admin:
        pytest.skip("No institution admin found")

    institution_id = inst_admin["institution_id"]
    courses = get_all_courses(institution_id)
    terms = get_active_terms(institution_id)

    if not courses or not terms:
        pytest.skip("Need both courses and terms for offering creation")

    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    offering_data = {
        "course_id": courses[0]["course_id"],
        "term_id": terms[0]["term_id"],
        "faculty_assigned": "Test Faculty",
    }

    response = authenticated_page.request.post(
        f"{BASE_URL}/api/offerings",
        data=offering_data,
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    assert response.ok
    result = response.json()
    assert result["success"] is True

    print("✅ TC-CRUD-IA-008: Institution Admin successfully created course offering")


@pytest.mark.e2e
def test_tc_crud_ia_009_assign_instructors_to_sections(authenticated_page: Page):
    """TC-CRUD-IA-009: Institution Admin assigns instructors to sections"""
    users = get_all_users()
    inst_admin = next((u for u in users if u["role"] == "institution_admin"), None)
    instructors = [u for u in users if u["role"] == "instructor"]

    if not inst_admin or not instructors:
        pytest.skip("Need institution admin and instructors")

    institution_id = inst_admin["institution_id"]
    sections = get_all_sections(institution_id)

    if not sections:
        pytest.skip("No sections found")

    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    assignment_data = {"instructor_id": instructors[0]["user_id"]}

    response = authenticated_page.request.patch(
        f"{BASE_URL}/api/sections/{sections[0]['section_id']}/instructor",
        data=assignment_data,
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    assert response.ok
    result = response.json()
    assert result["success"] is True

    print(
        "✅ TC-CRUD-IA-009: Institution Admin successfully assigned instructor to section"
    )


@pytest.mark.e2e
def test_tc_crud_ia_010_cannot_access_other_institutions(
    authenticated_page: Page, ensure_multiple_institutions
):
    """TC-CRUD-IA-010: Institution Admin cannot access other institutions"""
    second_inst_id, cleanup = ensure_multiple_institutions

    if not second_inst_id:
        pytest.skip("Could not ensure multiple institutions")

    users = get_all_users()
    inst_admin = next((u for u in users if u["role"] == "institution_admin"), None)

    if not inst_admin:
        pytest.skip("No institution admin found")

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

    csrf_token = authenticated_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Attempt to access course from other institution
    response = authenticated_page.request.get(
        f"{BASE_URL}/api/courses/{other_courses[0]['course_id']}",
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )

    assert response.status in [403, 404]

    print(
        "✅ TC-CRUD-IA-010: Institution Admin correctly blocked from accessing other institutions"
    )
