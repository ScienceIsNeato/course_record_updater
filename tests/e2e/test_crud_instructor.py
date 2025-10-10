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
# Temporarily un-skipped to debug 500 error
def test_tc_crud_inst_002_update_section_assessment(
    instructor_authenticated_page: Page,
):
    """
    TC-CRUD-INST-002: Instructor updates CLO assessment data via UI

    Steps:
    1. Login as instructor (fixture provides this)
    2. Navigate to assessments page
    3. Select a course with outcomes
    4. Click "Update Assessment" for a CLO
    5. Fill assessment form and submit
    6. Verify assessment data appears in UI

    Expected: Assessment updates succeed for instructor's own sections

    Note: Complete assessment UI is implemented and functional in dev.
    E2E test encounters 500 error when loading /assessments page.
    Likely caused by /api/sections or /api/courses endpoint issue in E2E environment.
    The UI, endpoints, and seed data all work correctly - just needs E2E debugging.
    """
    page = instructor_authenticated_page

    # Add console listener to capture ALL console messages (not just errors)
    console_messages = []

    def log_console(msg):
        console_messages.append(f"[{msg.type}] {msg.text}")
        print(f"📢 CONSOLE [{msg.type}]: {msg.text}")

    page.on("console", log_console)

    # Add dialog listener to see if alerts fire
    def log_dialog(dialog):
        print(f"🚨 DIALOG DETECTED: {dialog.type} - {dialog.message}")
        dialog.accept()  # Auto-accept to continue

    page.on("dialog", log_dialog)

    # Add response listener to capture 500 errors
    failed_requests = []

    def log_response(response):
        if response.status == 500:
            failed_requests.append(
                {
                    "url": response.url,
                    "status": response.status,
                    "method": response.request.method,
                }
            )
            print(f"🔴 500 ERROR: {response.request.method} {response.url}")

    page.on("response", log_response)

    # Navigate to assessments page
    page.goto(f"{BASE_URL}/assessments")
    page.wait_for_load_state("networkidle")

    # DEBUG: Check if extra_js block is rendered
    page_html = page.content()
    if "🚨 ASSESSMENT JS LOADED!" in page_html:
        print("✅ extra_js block IS rendered in HTML")
    else:
        print("❌ extra_js block NOT rendered in HTML!")
        # Check what scripts ARE there
        print(f"\nScripts in page: {page_html.count('<script')}")
        if "extra_js" in page_html.lower():
            print("'extra_js' text found in HTML (likely comment)")
        if "formatTimestamp" in page_html:
            print("✅ base_dashboard.html scripts present")

    # If we got 500 errors, print details before failing
    if failed_requests:
        print("\n🔴 Failed requests:")
        for req in failed_requests:
            print(f"  {req['method']} {req['url']} → {req['status']}")
        # Try to get response body
        import time

        time.sleep(1)  # Give time for all requests to complete

    # Debug: Check what's in the course selector
    import time

    time.sleep(2)  # Give JavaScript time to run

    options_html = page.locator("#courseSelect").inner_html()
    print(f"\n📋 Course selector HTML:\n{options_html}\n")

    # Check if JavaScript loaded and ran
    js_debug = page.evaluate(
        """() => {
        return {
            courseSelectExists: !!document.getElementById('courseSelect'),
            loadCoursesExists: typeof loadCourses !== 'undefined',
            windowLoaded: document.readyState
        };
    }"""
    )
    print(f"JS Debug: {js_debug}")

    # Try to get the actual options
    options = page.locator("#courseSelect option").all()
    print(f"Found {len(options)} options in dropdown")
    for i, opt in enumerate(options):
        value = opt.get_attribute("value")
        text = opt.inner_text()
        print(f"  Option {i}: value='{value}', text='{text}'")

    # Wait for course selector to load
    page.wait_for_selector("#courseSelect option:not([value=''])", timeout=10000)

    # Select first available course
    page.select_option("#courseSelect", index=1)

    # Wait for outcomes to load
    page.wait_for_selector(".update-assessment-btn", timeout=10000)

    # Click first "Update Assessment" button
    page.click(".update-assessment-btn")

    # Wait for modal to appear
    page.wait_for_selector("#updateAssessmentModal", state="visible", timeout=5000)

    # Fill assessment data
    page.fill("#studentsAssessed", "25")
    page.fill("#studentsMeetingTarget", "20")
    page.fill("#assessmentNarrative", "Students performed well overall")

    # Submit form
    page.click("#updateAssessmentForm button[type='submit']")

    # Wait for modal to close
    page.wait_for_selector("#updateAssessmentModal", state="hidden", timeout=5000)

    # Wait for alert and dismiss it
    page.once("dialog", lambda dialog: dialog.accept())

    # Verify assessment data appears (wait for reload)
    page.wait_for_function(
        "() => document.querySelector('.list-group-item .text-success')?.textContent?.includes('20/25')",
        timeout=5000,
    )

    print("✅ TC-CRUD-INST-002: Instructor successfully updated assessment via UI")


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
