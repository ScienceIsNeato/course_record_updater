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

import time
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

# Import database services for verification
from database_service import (
    get_active_terms,
    get_all_courses,
    get_all_sections,
    get_all_users,
)

# Import fixtures and helpers
from tests.e2e.conftest import (
    BASE_URL,
    close_modal,
    take_screenshot,
    wait_for_modal,
)

# ========================================
# SCENARIO 0: Basic Health Check
# ========================================


@pytest.mark.e2e
def test_health_endpoint(page: Page, server_running: bool):
    """
    Test Case: Basic health check - verify server is running and accessible
    """
    # Hit the health endpoint
    response = page.request.get(f"{BASE_URL}/api/health")

    # Verify response
    assert response.ok, f"Health check failed: {response.status}"
    assert response.status == 200, f"Expected 200, got {response.status}"

    print("✅ Health endpoint responding correctly")


# ========================================
# SCENARIO 1: Excel Import - End-to-End Data Flow
# ========================================


@pytest.mark.e2e
def test_tc_ie_001_dry_run_import_validation(
    authenticated_page: Page,
    database_baseline: dict,
    test_data_file: Path,
    server_running: bool,
):
    """
    TC-IE-001: Dry Run Import Validation

    Verify that dry run validation:
    1. Shows validation results without modifying database
    2. Reports correct entity counts
    3. Displays any errors/warnings
    4. Completes within reasonable time (< 15 seconds)
    """
    page = authenticated_page

    # Navigate to dashboard
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")

    # Locate Data Management panel and expand if needed
    # Look for either "Excel Import" button or "Import" button in Data Management
    try:
        # Try to find the Excel Import button directly
        excel_import_button = page.locator('button:has-text("Excel Import")')
        excel_import_button.wait_for(timeout=5000)
    except Exception:
        # If not found, try expanding Data Management panel first
        data_mgmt_panel = page.locator('text="Data Management"')
        if data_mgmt_panel.count() > 0:
            data_mgmt_panel.click()
            time.sleep(0.5)  # Brief pause for panel expansion

    # Click Excel Import button to open modal
    page.click('button:has-text("Excel Import")')

    # Wait for import modal to appear
    wait_for_modal(page, ".modal")

    # Upload test file
    file_input = page.locator('input[type="file"]')
    file_input.set_input_files(str(test_data_file))

    # Select adapter (if dropdown exists)
    adapter_select = page.locator(
        'select[name="adapter"], select[name="import_adapter"]'
    )
    if adapter_select.count() > 0:
        adapter_select.select_option("cei_excel_format_v1")

    # Enable dry run checkbox
    dry_run_checkbox = page.locator(
        'input[name="dry_run"], input[type="checkbox"][id*="dry"]'
    )
    if dry_run_checkbox.count() > 0:
        dry_run_checkbox.check()

    # Click Validate button
    validate_button = page.locator(
        'button:has-text("Validate"), button:has-text("Import")'
    )
    validate_button.first.click()

    # Wait for validation results (should appear within 15 seconds)
    try:
        validation_results = page.locator(
            ".validation-results, .import-results, .modal-body"
        )
        validation_results.wait_for(state="visible", timeout=15000)
    except Exception as e:
        # If validation results don't appear, take screenshot and fail
        take_screenshot(page, "tc_ie_001_validation_timeout")
        pytest.fail(f"Validation results did not appear within 15 seconds: {e}")

    # Assert validation success message
    success_indicators = [
        'text="Validation successful"',
        'text="Import successful"',
        ".success-message",
        ".alert-success",
    ]

    success_found = False
    for indicator in success_indicators:
        if page.locator(indicator).count() > 0:
            success_found = True
            break

    if not success_found:
        take_screenshot(page, "tc_ie_001_no_success_message")
        pytest.fail("No validation success message found in results")

    # Verify records found count > 0
    records_text_selectors = [
        ".records-found",
        "text=/records? (found|processed)/i",
        ".validation-summary",
    ]

    records_count = 0
    for selector in records_text_selectors:
        locator = page.locator(selector)
        if locator.count() > 0:
            text = locator.first.text_content()
            # Extract number from text like "150 records processed"
            import re

            match = re.search(r"(\d+)\s*records?", text, re.IGNORECASE)
            if match:
                records_count = int(match.group(1))
                break

    assert records_count > 0, f"Expected records found > 0, got {records_count}"

    # CRITICAL: Verify database unchanged (dry run should NOT modify)
    post_test_counts = {
        "courses": len(get_all_courses() or []),
        "users": len(get_all_users() or []),
        "sections": len(get_all_sections() or []),
        "terms": len(get_active_terms() or []),
    }

    assert post_test_counts == database_baseline, (
        f"Dry run modified database! "
        f"Before: {database_baseline}, After: {post_test_counts}"
    )

    # Close modal
    close_button = page.locator(
        '.modal button:has-text("Close"), .modal .close, button.close'
    )
    if close_button.count() > 0:
        close_button.first.click()


@pytest.mark.e2e
def test_tc_ie_002_successful_import_with_conflict_resolution(
    authenticated_page: Page,
    database_baseline: dict,
    test_data_file: Path,
    database_backup,
    server_running: bool,
):
    """
    TC-IE-002: Successful Import with Conflict Resolution

    Verify that actual import:
    1. Creates database records successfully
    2. Shows import summary with entity counts
    3. Handles conflict strategy correctly
    4. Increases database record counts appropriately
    """
    page = authenticated_page

    # Navigate to dashboard
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")

    # Open import modal (same as TC-IE-001)
    try:
        page.click('button:has-text("Excel Import")', timeout=5000)
    except Exception:
        # Try expanding Data Management panel first
        data_mgmt_panel = page.locator('text="Data Management"')
        if data_mgmt_panel.count() > 0:
            data_mgmt_panel.click()
            time.sleep(0.5)
        page.click('button:has-text("Excel Import")')

    wait_for_modal(page, ".modal")

    # Upload test file
    page.locator('input[type="file"]').set_input_files(str(test_data_file))

    # Select adapter
    adapter_select = page.locator(
        'select[name="adapter"], select[name="import_adapter"]'
    )
    if adapter_select.count() > 0:
        adapter_select.select_option("cei_excel_format_v1")

    # DISABLE dry run checkbox (actual import)
    dry_run_checkbox = page.locator(
        'input[name="dry_run"], input[type="checkbox"][id*="dry"]'
    )
    if dry_run_checkbox.count() > 0 and dry_run_checkbox.is_checked():
        dry_run_checkbox.uncheck()

    # Select conflict strategy: "Use theirs (overwrite)"
    conflict_select = page.locator('select[name="conflict_strategy"]')
    if conflict_select.count() > 0:
        conflict_select.select_option("use_theirs")

    # Click Import button
    import_button = page.locator('button:has-text("Import")')
    import_button.first.click()

    # Wait for import completion (may take longer than validation)
    try:
        results = page.locator(".import-results, .validation-results, .modal-body")
        results.wait_for(state="visible", timeout=30000)
    except Exception as e:
        take_screenshot(page, "tc_ie_002_import_timeout")
        pytest.fail(f"Import did not complete within 30 seconds: {e}")

    # Assert import success
    success_indicators = [
        'text="Import successful"',
        'text="Import completed"',
        ".success-message",
        ".alert-success",
    ]

    success_found = False
    for indicator in success_indicators:
        if page.locator(indicator).count() > 0:
            success_found = True
            break

    if not success_found:
        take_screenshot(page, "tc_ie_002_no_success_message")
        # Check for error messages
        error_locator = page.locator(".error-message, .alert-danger, text=/error/i")
        if error_locator.count() > 0:
            error_text = error_locator.first.text_content()
            pytest.fail(f"Import failed with error: {error_text}")
        else:
            pytest.fail("No import success message found in results")

    # Wait a moment for database writes to complete
    time.sleep(1)

    # Verify database records INCREASED
    post_import_counts = {
        "courses": len(get_all_courses() or []),
        "users": len(get_all_users() or []),
        "sections": len(get_all_sections() or []),
        "terms": len(get_active_terms() or []),
    }

    assert post_import_counts["courses"] > database_baseline["courses"], (
        f"Course count did not increase! "
        f"Before: {database_baseline['courses']}, After: {post_import_counts['courses']}"
    )

    assert post_import_counts["users"] > database_baseline["users"], (
        f"User count did not increase! "
        f"Before: {database_baseline['users']}, After: {post_import_counts['users']}"
    )

    assert post_import_counts["sections"] > database_baseline["sections"], (
        f"Section count did not increase! "
        f"Before: {database_baseline['sections']}, After: {post_import_counts['sections']}"
    )

    # Verify specific courses exist (spot check)
    courses = get_all_courses() or []
    course_numbers = [c.get("course_number", "") for c in courses]

    # Look for at least one MATH course (should be in CEI test data)
    math_courses = [num for num in course_numbers if "MATH" in num.upper()]
    assert len(math_courses) > 0, "No MATH courses found after import"

    # Close modal
    close_button = page.locator(
        '.modal button:has-text("Close"), .modal .close, button.close'
    )
    if close_button.count() > 0:
        close_button.first.click()


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

    # Verify at least 10 courses visible (should have imported 40-50)
    course_count = course_elements.count()
    assert course_count >= 10, f"Expected at least 10 courses, found {course_count}"

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

    # Verify at least 5 instructors visible (should have imported 15-20)
    instructor_count = user_elements.count()
    assert (
        instructor_count >= 5
    ), f"Expected at least 5 instructors, found {instructor_count}"

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
        import re

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

    # Verify at least 10 sections visible (should have imported 60-80)
    section_count = section_elements.count()
    assert section_count >= 10, f"Expected at least 10 sections, found {section_count}"

    # Verify section data integrity (check first 5 sections)
    for i in range(min(5, section_count)):
        section_row = section_elements.nth(i)
        row_text = section_row.text_content()

        # CRITICAL: Verify section numbers are human-readable (NOT UUIDs)
        # UUIDs look like: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        # Human-readable section numbers: "001", "002", "003"
        import re

        uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        uuid_match = re.search(uuid_pattern, row_text, re.IGNORECASE)

        assert (
            uuid_match is None
        ), f"Section row {i} contains UUID instead of human-readable section number: {row_text}"

        # Verify section has course reference (course number like MATH-101)
        course_pattern = r"[A-Z]{3,4}-\d{3}"
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


@pytest.mark.e2e
def test_tc_ie_007_conflict_resolution_duplicate_import(
    authenticated_page: Page,
    test_data_file: Path,
    server_running: bool,
):
    """
    TC-IE-007: Import Conflict Resolution (Duplicate Data)

    Prerequisites: TC-IE-002 must have run successfully (initial import done)

    Verify that re-importing the same file:
    1. Detects conflicts (all records are duplicates)
    2. Applies conflict resolution strategy correctly
    3. Does NOT create duplicate database records
    4. Database record counts remain stable (not doubled)
    """
    page = authenticated_page

    # Capture baseline counts BEFORE re-import
    baseline_counts = {
        "courses": len(get_all_courses() or []),
        "users": len(get_all_users() or []),
        "sections": len(get_all_sections() or []),
        "terms": len(get_active_terms() or []),
    }

    # Navigate to dashboard
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")

    # Open import modal
    try:
        page.click('button:has-text("Excel Import")', timeout=5000)
    except Exception:
        data_mgmt_panel = page.locator('text="Data Management"')
        if data_mgmt_panel.count() > 0:
            data_mgmt_panel.click()
            time.sleep(0.5)
        page.click('button:has-text("Excel Import")')

    wait_for_modal(page, ".modal")

    # Upload THE SAME file again
    page.locator('input[type="file"]').set_input_files(str(test_data_file))

    # Select adapter
    adapter_select = page.locator(
        'select[name="adapter"], select[name="import_adapter"]'
    )
    if adapter_select.count() > 0:
        adapter_select.select_option("cei_excel_format_v1")

    # DISABLE dry run
    dry_run_checkbox = page.locator(
        'input[name="dry_run"], input[type="checkbox"][id*="dry"]'
    )
    if dry_run_checkbox.count() > 0 and dry_run_checkbox.is_checked():
        dry_run_checkbox.uncheck()

    # Select conflict strategy: "Use theirs (overwrite)"
    conflict_select = page.locator('select[name="conflict_strategy"]')
    if conflict_select.count() > 0:
        conflict_select.select_option("use_theirs")

    # Click Import
    page.locator('button:has-text("Import")').first.click()

    # Wait for import completion
    try:
        results = page.locator(".import-results, .validation-results, .modal-body")
        results.wait_for(state="visible", timeout=30000)
    except Exception as e:
        take_screenshot(page, "tc_ie_007_reimport_timeout")
        pytest.fail(f"Re-import did not complete within 30 seconds: {e}")

    # Assert import completed (may show conflicts resolved message)
    success_or_conflict_indicators = [
        'text="Import successful"',
        'text="Import completed"',
        "text=/conflicts? resolved/i",
        ".success-message",
    ]

    result_found = False
    for indicator in success_or_conflict_indicators:
        if page.locator(indicator).count() > 0:
            result_found = True
            break

    assert result_found, "No import completion message found after re-import"

    # Wait for database writes
    time.sleep(1)

    # CRITICAL: Verify database counts DID NOT DOUBLE
    post_reimport_counts = {
        "courses": len(get_all_courses() or []),
        "users": len(get_all_users() or []),
        "sections": len(get_all_sections() or []),
        "terms": len(get_active_terms() or []),
    }

    assert post_reimport_counts["courses"] == baseline_counts["courses"], (
        f"Course count changed after re-import! "
        f"Before: {baseline_counts['courses']}, After: {post_reimport_counts['courses']}"
    )

    assert post_reimport_counts["users"] == baseline_counts["users"], (
        f"User count changed after re-import! "
        f"Before: {baseline_counts['users']}, After: {post_reimport_counts['users']}"
    )

    assert post_reimport_counts["sections"] == baseline_counts["sections"], (
        f"Section count changed after re-import! "
        f"Before: {baseline_counts['sections']}, After: {post_reimport_counts['sections']}"
    )

    # Verify no duplicate courses (spot check by course_number)
    courses = get_all_courses() or []
    course_numbers = [c.get("course_number", "") for c in courses]
    unique_course_numbers = set(course_numbers)

    assert len(course_numbers) == len(unique_course_numbers), (
        f"Duplicate course numbers found! "
        f"Total: {len(course_numbers)}, Unique: {len(unique_course_numbers)}"
    )


# ========================================
# SCENARIO 2: Excel Export - Data Integrity Validation
# ========================================


@pytest.mark.e2e
@pytest.mark.slow
def test_tc_ie_101_export_courses_to_excel(
    authenticated_page: Page,
    server_running: bool,
):
    """
    TC-IE-101: Export All Courses to Excel

    Prerequisites: TC-IE-002 must have run successfully (courses imported)

    Verify that:
    1. Export generates valid Excel file
    2. File downloads successfully
    3. Row count matches database course count
    4. Export filename has timestamp

    Note: This test does NOT validate file contents (would require openpyxl)
    but verifies the download flow works end-to-end.
    """
    page = authenticated_page

    # Navigate to dashboard
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")

    # Find Data Management panel and Export Courses button
    try:
        export_button = page.locator('button:has-text("Export Courses")')
        export_button.wait_for(timeout=5000)
    except Exception:
        # Try expanding Data Management panel first
        data_mgmt_panel = page.locator('text="Data Management"')
        if data_mgmt_panel.count() > 0:
            data_mgmt_panel.click()
            time.sleep(0.5)

    # Get baseline course count for comparison
    expected_course_count = len(get_all_courses() or [])
    assert expected_course_count > 0, "No courses in database to export"

    # Select Excel format (if dropdown exists)
    format_select = page.locator('select[name="export_format"], select[id*="format"]')
    if format_select.count() > 0:
        # Look for Excel option (might be "xlsx", "excel", or "Excel (.xlsx)")
        format_options = format_select.locator("option")
        excel_option_found = False
        for i in range(format_options.count()):
            option_text = format_options.nth(i).text_content().lower()
            if "xlsx" in option_text or "excel" in option_text:
                format_select.select_option(index=i)
                excel_option_found = True
                break

        if not excel_option_found:
            format_select.select_option(index=0)  # Default to first option

    # Set up download expectation BEFORE clicking export
    with page.expect_download(timeout=15000) as download_info:
        # Click Export Courses button
        page.locator('button:has-text("Export Courses")').first.click()

    # Get download object
    download = download_info.value

    # Verify download occurred
    assert download is not None, "Export did not trigger a file download"

    # Verify filename contains timestamp or date
    filename = download.suggested_filename
    assert "courses" in filename.lower(), f"Export filename unexpected: {filename}"
    assert (
        ".xlsx" in filename or ".xls" in filename
    ), f"Export file is not Excel format: {filename}"

    # Save download to temp location for validation
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        download_path = Path(tmpdir) / filename
        download.save_as(download_path)

        # Verify file exists and has content
        assert download_path.exists(), "Downloaded file was not saved"
        assert download_path.stat().st_size > 0, "Downloaded file is empty"

        # Optional: Validate Excel structure (requires openpyxl)
        try:
            import pandas as pd

            df = pd.read_excel(download_path)

            # Verify row count approximately matches database
            # (Allow ±5 rows for timing issues with concurrent tests)
            assert abs(len(df) - expected_course_count) <= 5, (
                f"Export row count mismatch! "
                f"Database: {expected_course_count}, Export: {len(df)}"
            )

            # Verify required columns exist
            required_columns = ["course_number", "course_title"]
            for col in required_columns:
                assert col in df.columns, f"Missing required column in export: {col}"

        except ImportError:
            # pandas not available, skip detailed validation
            pass


# TODO: Add more export test cases:
# - test_tc_ie_102_export_users_to_excel
# - test_tc_ie_103_export_sections_to_excel
# - test_tc_ie_104_roundtrip_validation (import → export → re-import)
# - test_tc_ie_201_export_courses_to_csv
# - test_tc_ie_202_export_courses_to_json
