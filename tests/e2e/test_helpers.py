"""
E2E Test Helper Functions

Utilities for creating test data programmatically via API calls.
Tests use these helpers to create exactly the data they need.
"""

import json

from playwright.sync_api import Page


def create_test_user_via_api(
    admin_page: Page,
    base_url: str,
    email: str,
    first_name: str,
    last_name: str,
    role: str,
    institution_id: str,
    password: str = "TestUser123!",
    program_ids: list = None,
) -> dict:
    """
    Create a test user via admin API.

    Requires authenticated admin page with manage_users permission.

    Args:
        admin_page: Authenticated page (institution or site admin)
        base_url: Base URL (e.g., http://localhost:3002)
        email: User email
        first_name: First name
        last_name: Last name
        role: User role (instructor, program_admin, institution_admin)
        institution_id: Institution ID
        password: User password (default: TestUser123!)
        program_ids: List of program IDs to associate with user (optional)

    Returns:
        dict: Created user data including user_id

    Example:
        instructor = create_test_user_via_api(
            admin_page=authenticated_institution_admin_page,
            base_url=BASE_URL,
            email="john.smith@test.com",
            first_name="John",
            last_name="Smith",
            role="instructor",
            institution_id="mock-inst-id",
            program_ids=["cs-program-id"]
        )
    """
    # Get CSRF token
    csrf_token = admin_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    # Build user data
    user_data = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "role": role,
        "institution_id": institution_id,
        "password": password,
        "account_status": "active",
        "email_verified": True,  # Skip email verification for tests
    }

    # Add program_ids if provided
    if program_ids:
        user_data["program_ids"] = program_ids

    # Create user via API
    response = admin_page.request.post(
        f"{base_url}/api/users",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data=json.dumps(user_data),
    )

    assert response.ok, f"Failed to create user: {response.status} {response.text()}"
    user_data = response.json()

    assert user_data.get("success"), f"API returned error: {user_data.get('error')}"

    return {"user_id": user_data["user_id"], "email": email}


def login_as_user(page: Page, base_url: str, email: str, password: str) -> Page:
    """
    Log in as a specific user.

    Args:
        page: Playwright page
        base_url: Base URL
        email: User email
        password: User password

    Returns:
        Page: Authenticated page

    Example:
        page = login_as_user(page, BASE_URL, "john.smith@test.com", "TestUser123!")
    """
    page.context.clear_cookies()
    page.goto(f"{base_url}/login")
    page.wait_for_load_state("networkidle")

    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')

    # Wait for redirect to dashboard
    try:
        page.wait_for_url(f"{base_url}/dashboard", timeout=5000)
    except Exception:
        # Login might have failed - let test handle the error
        pass

    return page


def get_institution_id_from_user(user_page: Page) -> str:
    """
    Get institution ID from logged-in user's session.

    Args:
        user_page: Authenticated user page (any role)

    Returns:
        str: User's institution ID

    Example:
        inst_id = get_institution_id_from_user(authenticated_institution_admin_page)
    """
    # Get user's institution ID from session/profile
    base_url = (
        user_page.url.split("/dashboard")[0]
        if "/dashboard" in user_page.url
        else user_page.url.split("?")[0].rstrip("/")
    )
    response = user_page.request.get(f"{base_url}/api/me")
    if response.ok:
        user_data = response.json()
        return user_data.get("institution_id")

    # Fallback: MockU for tests (most tests use MockU)
    # This is safe since we control the test data
    return "mockuniversity"  # Standard institution ID for MockU


def get_program_id(
    admin_page: Page, base_url: str, program_code: str, institution_id: str
) -> str:
    """
    Get program ID by code and institution.

    Args:
        admin_page: Authenticated admin page
        base_url: Base URL
        program_code: Program code (e.g., "CS", "EE", "ME")
        institution_id: Institution ID

    Returns:
        str: Program ID

    Example:
        cs_program_id = get_program_id(admin_page, BASE_URL, "CS", mocku_id)
    """
    response = admin_page.request.get(
        f"{base_url}/api/programs?institution_id={institution_id}"
    )
    assert response.ok, f"Failed to fetch programs: {response.status}"

    data = response.json()
    programs = data.get("programs", [])

    program = next((p for p in programs if p.get("program_code") == program_code), None)
    assert program, f"Program '{program_code}' not found in institution"

    return program["program_id"]


def assign_user_to_program(
    admin_page: Page,
    base_url: str,
    user_id: str,
    program_id: str,
    role: str = "program_admin",
) -> None:
    """
    Assign user to a program (for program admins).

    Args:
        admin_page: Authenticated admin page
        base_url: Base URL
        user_id: User ID
        program_id: Program ID
        role: User's role in the program

    Example:
        assign_user_to_program(admin_page, BASE_URL, user_id, program_id, "program_admin")
    """
    csrf_token = admin_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    response = admin_page.request.post(
        f"{base_url}/api/users/{user_id}/programs",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data=json.dumps(
            {
                "program_id": program_id,
                "role": role,
            }
        ),
    )

    assert (
        response.ok
    ), f"Failed to assign user to program: {response.status} {response.text()}"


def create_test_section_via_api(
    admin_page: Page,
    base_url: str,
    course_id: str,
    term_id: str,
    section_code: str,
    instructor_id: str = None,
) -> dict:
    """
    Create a test section via API.

    Args:
        admin_page: Authenticated admin page
        base_url: Base URL
        course_id: Course ID
        term_id: Term ID
        section_code: Section code (e.g., "001", "002")
        instructor_id: Optional instructor ID to assign

    Returns:
        dict: Created section data including section_id

    Example:
        section = create_test_section_via_api(
            admin_page, BASE_URL, course_id, term_id, "001", instructor_id
        )
    """
    csrf_token = admin_page.evaluate(
        "document.querySelector('meta[name=\"csrf-token\"]')?.content"
    )

    section_data = {
        "course_id": course_id,
        "term_id": term_id,
        "section_code": section_code,
        "max_enrollment": 30,
    }

    if instructor_id:
        section_data["instructor_id"] = instructor_id

    response = admin_page.request.post(
        f"{base_url}/api/sections",
        headers={
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token if csrf_token else "",
        },
        data=json.dumps(section_data),
    )

    assert response.ok, f"Failed to create section: {response.status} {response.text()}"
    data = response.json()
    assert data.get("success"), f"API returned error: {data.get('error')}"

    return data.get("section", {})


def get_term_id(
    admin_page: Page, base_url: str, term_code: str, institution_id: str
) -> str:
    """
    Get term ID by code and institution.

    Args:
        admin_page: Authenticated admin page
        base_url: Base URL
        term_code: Term code (e.g., "FA2024", "SP2025")
        institution_id: Institution ID

    Returns:
        str: Term ID

    Example:
        term_id = get_term_id(admin_page, BASE_URL, "SP2025", mocku_id)
    """
    response = admin_page.request.get(
        f"{base_url}/api/terms?institution_id={institution_id}"
    )
    assert response.ok, f"Failed to fetch terms: {response.status}"

    data = response.json()
    terms = data.get("terms", [])

    term = next((t for t in terms if t.get("term_code") == term_code), None)
    assert term, f"Term '{term_code}' not found in institution"

    return term["term_id"]


def get_course_id(
    admin_page: Page, base_url: str, course_code: str, program_id: str
) -> str:
    """
    Get course ID by code and program.

    Args:
        admin_page: Authenticated admin page
        base_url: Base URL
        course_code: Course code (e.g., "CS101", "EE101")
        program_id: Program ID

    Returns:
        str: Course ID

    Example:
        course_id = get_course_id(admin_page, BASE_URL, "CS101", program_id)
    """
    response = admin_page.request.get(f"{base_url}/api/courses?program_id={program_id}")
    assert response.ok, f"Failed to fetch courses: {response.status}"

    data = response.json()
    courses = data.get("courses", [])

    course = next((c for c in courses if c.get("course_code") == course_code), None)
    assert course, f"Course '{course_code}' not found in program"

    return course["course_id"]
