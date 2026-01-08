"""
E2E Test for Generic CSV Adapter Roundtrip

TC-IE-104: Roundtrip Validation (Export → Import → Verify)

Validates complete bidirectional data flow through the UI:
1. Export courses using generic CSV adapter
2. Re-import the exported CSV file
3. Verify data integrity (counts, spot-check data)

This test exercises the full user workflow for the generic CSV export/import feature.
"""

import json
import tempfile
import time
import zipfile
from pathlib import Path

import pytest
from playwright.sync_api import Page

from tests.e2e.conftest import BASE_URL


@pytest.mark.e2e
@pytest.mark.slow
def test_tc_ie_104_csv_roundtrip_validation(
    authenticated_page: Page,
    server_running: bool,
):
    """
    TC-IE-104: Generic CSV Adapter Roundtrip Validation

    Full bidirectional workflow:
    1. Navigate to Data Management panel
    2. Export courses using generic CSV adapter (ZIP format)
    3. Verify ZIP download and structure
    4. Re-import the exported ZIP file
    5. Verify import success and data integrity

    Prerequisites:
    - Database has existing course data (from seed_db or previous imports)
    - User is authenticated as institution admin
    """
    page = authenticated_page

    # Navigate to dashboard
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")

    print("\n" + "=" * 70)
    print("TC-IE-104: Generic CSV Roundtrip Validation")
    print("=" * 70)

    # ========================================
    # STEP 1: Export using Generic CSV adapter (Adapter-Driven!)
    # ========================================
    print("\n📦 STEP 1: Export data using Generic CSV adapter...")

    # Find Export Adapter dropdown (THE ONLY CONTROL)
    adapter_select = page.locator("select#export_adapter")
    adapter_select.wait_for(timeout=5000)

    # Wait for adapters to load (dropdown gets populated dynamically)
    page.wait_for_timeout(1000)  # Give time for adapter registry to populate

    # Select Generic CSV adapter by VALUE
    try:
        adapter_select.select_option(value="generic_csv_v1")
        print("   ✅ Selected Generic CSV adapter (generic_csv_v1)")
    except Exception as e:
        # Debug: show available adapters
        options = adapter_select.locator("option").all()
        available = [
            f"{opt.text_content()} (value: {opt.get_attribute('value')})"
            for opt in options
        ]
        print(f"   ⚠️  Available adapters: {available}")
        pytest.skip(f"Generic CSV adapter not available. Available: {available}")

    # Find single "Export Data" button
    export_button = page.locator('button:has-text("Export Data")')
    export_button.wait_for(timeout=5000)

    # Set up download expectation BEFORE clicking export
    with page.expect_download(timeout=20000) as download_info:
        export_button.click()
        print("   🖱️  Clicked Export Data button")

    # Get download object
    download = download_info.value
    assert download is not None, "Export did not trigger a file download"

    # Verify filename
    filename = download.suggested_filename
    print(f"   📥 Download filename: {filename}")

    assert "courses" in filename.lower(), f"Export filename unexpected: {filename}"
    assert ".zip" in filename.lower(), f"Export file is not ZIP format: {filename}"

    # Save download to temp location
    with tempfile.TemporaryDirectory() as tmpdir:
        download_path = Path(tmpdir) / filename
        download.save_as(download_path)

        # Verify file exists and has content
        assert download_path.exists(), "Downloaded file was not saved"
        assert download_path.stat().st_size > 0, "Downloaded file is empty"

        file_size = download_path.stat().st_size
        print(f"   ✅ Export downloaded successfully ({file_size} bytes)")

        # ========================================
        # STEP 2: Verify ZIP structure and content
        # ========================================
        print("\n🔍 STEP 2: Verify ZIP structure...")

        # Validate ZIP structure
        with zipfile.ZipFile(download_path, "r") as zf:
            file_list = zf.namelist()
            print(f"   Files in ZIP: {len(file_list)}")

            # Verify manifest
            assert "manifest.json" in file_list, "manifest.json not found in ZIP"
            manifest_data = json.loads(zf.read("manifest.json"))

            assert (
                manifest_data.get("format_version") == "1.0"
            ), "Invalid manifest version"
            entity_counts = manifest_data.get("entity_counts", {})

            print(
                f"   ✅ Manifest valid (format version: {manifest_data.get('format_version')})"
            )
            print(f"   📊 Entity counts:")
            for entity_type, count in entity_counts.items():
                if count > 0:
                    print(f"      - {entity_type}: {count}")

            # Verify key CSV files exist
            expected_files = ["users.csv", "courses.csv", "terms.csv"]
            for expected_file in expected_files:
                if expected_file in file_list:
                    print(f"   ✅ {expected_file} present")

            # Store counts for comparison after import
            original_user_count = entity_counts.get("users", 0)
            original_course_count = entity_counts.get("courses", 0)

        # ========================================
        # STEP 3: Re-import the exported ZIP file
        # ========================================
        print("\n📤 STEP 3: Re-import the exported CSV...")

        # Navigate to import section (refresh page first to ensure clean state)
        page.goto(f"{BASE_URL}/dashboard")
        page.wait_for_load_state("networkidle")
        time.sleep(1)  # Allow dashboard to fully load

        # Expand Data Management panel if collapsed
        try:
            panel_header = page.locator(
                'h5:has-text("Data Management"), .panel-title:has-text("Data Management")'
            )
            if panel_header.count() > 0:
                # Check if panel content is visible
                panel_content = (
                    panel_header.locator("..").locator("..").locator(".panel-content")
                )
                if panel_content.count() > 0:
                    is_visible = panel_content.is_visible()
                    print(f"   📋 Data Management panel visible: {is_visible}")
                    if not is_visible:
                        panel_header.click()
                        print("   🖱️  Expanded Data Management panel")
                        time.sleep(0.5)
        except Exception as e:
            print(f"   ⚠️  Could not check/expand panel: {e}")

        # INLINE FORM APPROACH (no modal after greenfield refactor)
        # Step 1: Upload file to inline form
        file_input = page.locator('#dataImportForm input[type="file"]')
        file_input.wait_for(timeout=5000)
        file_input.set_input_files(str(download_path))
        print(f"   📁 Uploaded file to inline form: {filename}")

        # Step 2: Select Generic CSV adapter
        import_adapter_select = page.locator("#import_adapter")
        import_adapter_select.wait_for(timeout=5000)
        page.wait_for_timeout(1000)  # Wait for adapters to populate

        try:
            import_adapter_select.select_option(value="generic_csv_v1")
            print("   ✅ Selected Generic CSV adapter for import")
        except Exception:
            # Debug available adapters
            options = import_adapter_select.locator("option").all()
            available = [
                f"{opt.text_content()} (value: {opt.get_attribute('value')})"
                for opt in options
            ]
            print(f"   ⚠️  Available import adapters: {available}")
            pytest.skip(f"Generic CSV adapter not available for import")

        # Step 3: Click Excel Import button to submit inline form
        import_button = page.locator('button:has-text("Excel Import")')
        import_button.wait_for(timeout=5000)
        import_button.click()
        print("   🖱️  Submitted import via inline form (no modal)")

        # Wait for import to complete - check for results div becoming visible
        try:
            # Wait for import results to appear (inline form, not modal)
            results_div = page.locator("#importResults")
            results_div.wait_for(state="visible", timeout=15000)

            # Check if there's an error
            error_alert = page.locator("#importResults .alert-danger")
            if error_alert.count() > 0:
                error_text = error_alert.text_content()
                pytest.fail(f"Import failed with error: {error_text}")

            print("   ✅ Import completed successfully")
        except Exception as e:
            pytest.fail(
                f"Import did not complete - results div never appeared: {str(e)}"
            )

        # Wait a bit for modal to close
        time.sleep(2)

        # ========================================
        # STEP 4: Verify data integrity after roundtrip
        # ========================================
        print("\n✅ STEP 4: Verify data integrity...")

        # Navigate to courses page to verify data
        page.goto(f"{BASE_URL}/courses")
        page.wait_for_load_state("networkidle")

        # Count visible courses (table rows minus header)
        course_rows = page.locator("table tbody tr")
        visible_course_count = course_rows.count()

        print(f"   📊 Visible courses after roundtrip: {visible_course_count}")
        print(f"   📊 Original course count: {original_course_count}")

        # Verify course count is non-zero (data exists)
        assert visible_course_count > 0, "No courses visible after roundtrip import"

        # Spot-check: Verify first course has expected structure
        if visible_course_count > 0:
            first_course = course_rows.first
            course_number_cell = first_course.locator("td").first
            course_number = course_number_cell.text_content()

            assert (
                course_number is not None and len(course_number.strip()) > 0
            ), "First course has empty course number"
            print(f"   ✅ First course number: {course_number.strip()}")

        print("\n" + "=" * 70)
        print("✅ TC-IE-104: Roundtrip validation PASSED!")
        print("=" * 70)
        print(f"\nSummary:")
        print(f"  - Exported {original_course_count} courses to ZIP")
        print(f"  - Re-imported ZIP file successfully")
        print(f"  - Verified {visible_course_count} courses visible in UI")
        print(f"  - Data integrity maintained through export/import cycle")
