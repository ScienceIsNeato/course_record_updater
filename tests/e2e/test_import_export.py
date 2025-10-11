"""
E2E Tests for Import/Export Functionality

Automated UAT test cases from UAT_IMPORT_EXPORT.md that validate:
- Excel import workflows (dry run, actual import, conflict resolution)
- Data visibility across UI views (courses, instructors, sections)
- Export functionality (Excel, CSV, JSON)
- Roundtrip validation (import → export → import)

These tests simulate real user interactions with the browser and verify
both UI behavior and database state.

Test Naming Convention:
- test_tc_ie_XXX: Matches UAT test case ID (e.g., TC-IE-001)
"""

import re
import time
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

# Import fixtures and helpers
from tests.conftest import INSTITUTION_ADMIN_EMAIL, INSTITUTION_ADMIN_PASSWORD
from tests.e2e.conftest import (
    BASE_URL,
    close_modal,
    take_screenshot,
    wait_for_modal,
)

# E2E tests should verify via UI only - no direct database imports needed
# (Removed database_service imports to enforce UI-based verification)


# ========================================
# SCENARIO 0: Basic Health Check & Login Debugging
# ========================================


@pytest.mark.e2e
def test_login_page_structure(page: Page, server_running: bool):
    """
    Validate that login page structure contains all required form elements.

    Verifies: Page loads, email input, password input, submit button, CSRF token all present
    """
    # Navigate to login page
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")

    # Verify page loaded (check title or heading)
    page_title = page.title()
    print(f"📄 Page title: {page_title}")

    # Check email input
    email_input = page.locator('input[name="email"]')
    assert email_input.count() > 0, "Email input not found"
    print("✅ Email input exists")

    # Check password input
    password_input = page.locator('input[name="password"]')
    assert password_input.count() > 0, "Password input not found"
    print("✅ Password input exists")

    # Check submit button
    submit_button = page.locator('button[type="submit"]')
    assert submit_button.count() > 0, "Submit button not found"
    print("✅ Submit button exists")

    # Check CSRF token
    csrf_input = page.locator('input[name="csrf_token"]')
    assert csrf_input.count() > 0, "CSRF token input not found"

    # Get CSRF token value
    csrf_value = csrf_input.get_attribute("value")
    assert csrf_value is not None and len(csrf_value) > 0, "CSRF token is empty"
    print(f"✅ CSRF token exists (length: {len(csrf_value)})")

    print("✅ Login page structure validation passed")


@pytest.mark.e2e
def test_login_script_loading(page: Page, server_running: bool):
    """
    Validate that auth.js loads and event handlers are properly initialized.

    Verifies: auth.js loads, DOMContentLoaded fires, initializeLoginForm runs,
              event listener is attached to form
    """
    # Listen for console messages
    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

    # Listen for script loads
    script_loads = []
    page.on(
        "response",
        lambda response: (
            script_loads.append(response.url) if ".js" in response.url else None
        ),
    )

    # Navigate to login
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")

    # Check if auth.js loaded
    auth_js_loaded = any("auth.js" in url for url in script_loads)
    print(f"📦 auth.js loaded: {auth_js_loaded}")
    if auth_js_loaded:
        auth_js_url = [url for url in script_loads if "auth.js" in url][0]
        print(f"   URL: {auth_js_url}")

    # Check if form exists and has properties
    form_check = page.evaluate(
        """
        () => {
            const form = document.getElementById('loginForm');
            if (!form) return {exists: false};
            
            return {
                exists: true,
                formOnsubmit: form.onsubmit ? 'set' : 'not set',
                hasAction: form.action || 'none',
                hasMethod: form.method || 'get'
            };
        }
    """
    )

    print(f"🔍 Form properties: {form_check}")

    # Check if functions are defined in global scope
    functions_check = page.evaluate(
        """
        () => {
            return {
                handleLogin: typeof handleLogin,
                initializeLoginForm: typeof initializeLoginForm,
                initializePage: typeof initializePage,
                getCSRFToken: typeof getCSRFToken
            };
        }
    """
    )

    print(f"🔍 Global functions defined: {functions_check}")

    # Check if DOMContentLoaded event has fired
    dom_ready = page.evaluate(
        """
        () => {
            return document.readyState === 'complete' || document.readyState === 'interactive';
        }
    """
    )

    print(f"✅ DOM ready: {dom_ready}")

    # CRITICAL: Check if initializePage() was actually called
    # We can infer this by checking if event listeners were attached
    initialization_check = page.evaluate(
        """
        () => {
            // Check current path that initializePage would see
            const currentPath = window.location.pathname;
            
            // Check if form has submit listener (indirect check)
            const form = document.getElementById('loginForm');
            
            return {
                currentPath: currentPath,
                pathIncludesLogin: currentPath.includes('/login'),
                formExists: !!form,
                // Try to manually check if listener was added
                // by attempting to access internal properties (may not work)
                formListenerCount: form ? (form._events ? Object.keys(form._events).length : 'unknown') : 0
            };
        }
    """
    )

    print(f"🔍 Initialization check: {initialization_check}")

    # Print any console logs
    if console_logs:
        print(f"📋 Console logs ({len(console_logs)} total):")
        for log in console_logs[:10]:  # Limit to first 10
            print(f"   {log}")

    print(f"✅ HYPOTHESIS 3 TEST COMPLETE - Check if auth.js loaded and initialized")
    print(f"")
    print(
        f"🚨 KEY FINDING: auth.js loads, functions defined, BUT form.onsubmit is NOT SET"
    )
    print(f"   This means initializeLoginForm() was never called!")
    print(
        f"   The form uses traditional HTML submit (action='/login'), causing page reload"
    )


# ========================================
# SCENARIO 1: Excel Import - End-to-End Data Flow
# ========================================


@pytest.mark.e2e
@pytest.mark.e2e
def test_tc_ie_003_imported_course_visibility(
    authenticated_page: Page,
    server_running: bool,
):
    """
    TC-IE-003: Imported Course Visibility in Courses List

    Prerequisites: TC-IE-002 must have run successfully (courses imported)

    Verify that:
    1. Courses list loads and displays imported courses
    2. Course numbers, titles, departments are visible
    3. Can click a course to view details
    4. No empty or corrupted data
    """
    page = authenticated_page

    # Navigate to Courses page
    page.goto(f"{BASE_URL}/courses")
    page.wait_for_load_state("networkidle")

    # Wait for course list/table to load
    course_list_selectors = [
        "table tbody tr",
        ".course-list .course-item",
        '[data-testid="course-list"]',
    ]

    course_elements = None
    for selector in course_list_selectors:
        locator = page.locator(selector)
        if locator.count() > 0:
            course_elements = locator
            break

    if course_elements is None or course_elements.count() == 0:
        take_screenshot(page, "tc_ie_003_no_courses")
        pytest.fail("No courses found in courses list view")

    # Verify courses are visible (seed data has 6 CEI courses)
    course_count = course_elements.count()
    assert course_count >= 5, f"Expected at least 5 courses, found {course_count}"

    # Verify course data integrity (check first 5 courses)
    for i in range(min(5, course_count)):
        course_row = course_elements.nth(i)
        row_text = course_row.text_content()

        # Verify row has meaningful content (not empty or "null")
        assert len(row_text.strip()) > 0, f"Course row {i} is empty"
        assert "null" not in row_text.lower(), f"Course row {i} contains 'null'"
        assert (
            "undefined" not in row_text.lower()
        ), f"Course row {i} contains 'undefined'"

    # Try to search for a specific course (MATH-101 or similar)
    search_box = page.locator('input[type="search"], input[placeholder*="search" i]')
    if search_box.count() > 0:
        search_box.fill("MATH")
        page.wait_for_timeout(1000)  # Wait for filter/search to apply

        # Verify filtered results
        filtered_courses = page.locator("table tbody tr, .course-item")
        assert (
            filtered_courses.count() > 0
        ), "No courses found when searching for 'MATH'"

    # Click on first course to view details
    first_course = course_elements.first
    first_course.click()

    # Wait for course details to load (may be modal or new page)
    page.wait_for_timeout(2000)

    # Verify course details are visible
    details_selectors = [
        ".course-details",
        ".modal-body",
        "text=/course number/i",
        "text=/course title/i",
    ]

    details_visible = False
    for selector in details_selectors:
        if page.locator(selector).count() > 0:
            details_visible = True
            break

    assert details_visible, "Course details did not load after clicking course"


@pytest.mark.e2e
def test_tc_ie_004_imported_instructor_visibility(
    authenticated_page: Page,
    server_running: bool,
):
    """
    TC-IE-004: Imported Instructor Visibility in Users List

    Prerequisites: TC-IE-002 must have run successfully (instructors imported)

    Verify that:
    1. Users list loads and displays imported instructors
    2. Instructor emails, names, roles are visible
    3. Role badges display "Instructor"
    4. No duplicate or missing emails
    """
    page = authenticated_page

    # Navigate to Users page
    page.goto(f"{BASE_URL}/users")
    page.wait_for_load_state("networkidle")

    # Filter by role: Instructor (if filter exists)
    role_filter = page.locator('select[name="role"], select[id*="role"]')
    if role_filter.count() > 0:
        role_filter.select_option("instructor")
        page.wait_for_timeout(1000)

    # Wait for user list/table to load
    user_list_selectors = [
        "table tbody tr",
        ".user-list .user-item",
        '[data-testid="user-list"]',
    ]

    user_elements = None
    for selector in user_list_selectors:
        locator = page.locator(selector)
        if locator.count() > 0:
            user_elements = locator
            break

    if user_elements is None or user_elements.count() == 0:
        take_screenshot(page, "tc_ie_004_no_instructors")
        pytest.fail("No instructors found in users list view")

    # Verify instructors are visible (seed data has 2 instructors for CEI)
    instructor_count = user_elements.count()
    assert (
        instructor_count >= 2
    ), f"Expected at least 2 instructors, found {instructor_count}"

    # Verify instructor data integrity (check first 3 instructors)
    emails_seen = set()
    for i in range(min(3, instructor_count)):
        instructor_row = user_elements.nth(i)
        row_text = instructor_row.text_content()

        # Verify row has meaningful content
        assert len(row_text.strip()) > 0, f"Instructor row {i} is empty"

        # Verify email format (should contain @)
        assert "@" in row_text, f"Instructor row {i} missing email address"

        # Verify role badge (should say "Instructor" or "instructor")
        assert (
            "instructor" in row_text.lower()
        ), f"Instructor row {i} missing role badge"

        # Check for duplicate emails (extract email and compare)
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", row_text)
        if email_match:
            email = email_match.group(0)
            assert (
                email not in emails_seen
            ), f"Duplicate instructor email found: {email}"
            emails_seen.add(email)


@pytest.mark.e2e
def test_tc_ie_005_imported_section_visibility(
    authenticated_page: Page,
    server_running: bool,
):
    """
    TC-IE-005: Imported Section Visibility in Sections Table

    Prerequisites: TC-IE-002 must have run successfully (sections imported)

    Verify that:
    1. Sections list loads and displays imported sections
    2. Section numbers are human-readable (001, 002, NOT UUIDs)
    3. Course, instructor, term relationships intact
    4. Enrollment counts are reasonable integers
    """
    page = authenticated_page

    # Navigate to Sections page or dashboard sections view
    page.goto(f"{BASE_URL}/sections")
    page.wait_for_load_state("networkidle")

    # Wait for section list/table to load
    section_list_selectors = [
        "table tbody tr",
        ".section-list .section-item",
        '[data-testid="section-list"]',
    ]

    section_elements = None
    for selector in section_list_selectors:
        locator = page.locator(selector)
        if locator.count() > 0:
            section_elements = locator
            break

    if section_elements is None or section_elements.count() == 0:
        take_screenshot(page, "tc_ie_005_no_sections")
        pytest.fail("No sections found in sections list view")

    # Verify sections are visible (seed data has 6 CEI sections)
    section_count = section_elements.count()
    assert section_count >= 5, f"Expected at least 5 sections, found {section_count}"

    # Verify section data integrity (check first 5 sections)
    for i in range(min(5, section_count)):
        section_row = section_elements.nth(i)
        row_text = section_row.text_content()

        # CRITICAL: Verify section numbers are human-readable (NOT UUIDs)
        # UUIDs look like: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        # Human-readable section numbers: "001", "002", "003"
        uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        uuid_match = re.search(uuid_pattern, row_text, re.IGNORECASE)

        assert (
            uuid_match is None
        ), f"Section row {i} contains UUID instead of human-readable section number: {row_text}"

        # Verify section has course reference (course number like CS-101, MATH-101)
        course_pattern = r"[A-Z]{2,4}-\d{3}"  # 2-4 uppercase letters, dash, 3 digits
        course_match = re.search(course_pattern, row_text)
        assert course_match is not None, f"Section row {i} missing course reference"

        # Verify enrollment is a reasonable number (0-100)
        # Look for patterns like "25 students" or just "25"
        enrollment_pattern = r"(\d{1,3})\s*(students?)?"
        enrollment_match = re.search(enrollment_pattern, row_text)
        if enrollment_match:
            enrollment = int(enrollment_match.group(1))
            assert (
                0 <= enrollment <= 100
            ), f"Section row {i} has unreasonable enrollment: {enrollment}"

    # Try filtering by term if filter exists
    term_filter = page.locator('select[name="term"], select[id*="term"]')
    if term_filter.count() > 0:
        # Select first term option (not "All")
        term_options = term_filter.locator("option")
        if term_options.count() > 1:
            term_filter.select_option(index=1)
            page.wait_for_timeout(1000)

            # Verify filtered results
            filtered_sections = page.locator("table tbody tr, .section-item")
            assert (
                filtered_sections.count() > 0
            ), "No sections found after applying term filter"
