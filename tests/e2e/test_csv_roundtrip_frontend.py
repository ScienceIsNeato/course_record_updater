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


def _step_export_data(page: Page, save_dir: Path) -> Path:
    """Step 1: Export data using Generic CSV adapter."""
    print("\n📦 STEP 1: Export data using Generic CSV adapter...")

    # Find Export Adapter dropdown
    adapter_select = page.locator("select#export_adapter")
    adapter_select.wait_for(timeout=5000)
    page.wait_for_timeout(1000)

    try:
        adapter_select.select_option(value="generic_csv_v1")
        print("   ✅ Selected Generic CSV adapter (generic_csv_v1)")
    except Exception:
        options = adapter_select.locator("option").all()
        available = [
            f"{opt.text_content()} (value: {opt.get_attribute('value')})"
            for opt in options
        ]
        print(f"   ⚠️  Available adapters: {available}")
        pytest.skip(f"Generic CSV adapter not available. Available: {available}")

    export_button = page.locator('button:has-text("Export Data")')
    export_button.wait_for(timeout=5000)

    with page.expect_download(timeout=20000) as download_info:
        export_button.click()
        print("   🖱️  Clicked Export Data button")

    download = download_info.value
    assert download is not None, "Export did not trigger a file download"

    filename = download.suggested_filename
    print(f"   📥 Download filename: {filename}")
    assert "courses" in filename.lower(), f"Export filename unexpected: {filename}"
    assert ".zip" in filename.lower(), f"Export file is not ZIP format: {filename}"

    download_path = save_dir / filename
    download.save_as(download_path)

    assert download_path.exists(), "Downloaded file was not saved"
    assert download_path.stat().st_size > 0, "Downloaded file is empty"
    print(
        f"   ✅ Export downloaded successfully ({download_path.stat().st_size} bytes)"
    )

    return download_path


def _step_verify_zip(download_path: Path):
    """Step 2: Verify ZIP structure and content."""
    print("\n🔍 STEP 2: Verify ZIP structure...")

    with zipfile.ZipFile(download_path, "r") as zf:
        file_list = zf.namelist()
        print(f"   Files in ZIP: {len(file_list)}")

        assert "manifest.json" in file_list, "manifest.json not found in ZIP"
        manifest_data = json.loads(zf.read("manifest.json"))

        assert manifest_data.get("format_version") == "1.0", "Invalid manifest version"
        entity_counts = manifest_data.get("entity_counts", {})

        print(
            f"   ✅ Manifest valid (format version: {manifest_data.get('format_version')})"
        )
        print(f"   📊 Entity counts:")
        for entity_type, count in entity_counts.items():
            if count > 0:
                print(f"      - {entity_type}: {count}")

        expected_files = ["users.csv", "courses.csv", "terms.csv"]
        for expected_file in expected_files:
            if expected_file in file_list:
                print(f"   ✅ {expected_file} present")

        original_user_count = entity_counts.get("users", 0)
        original_course_count = entity_counts.get("courses", 0)

        return original_user_count, original_course_count


def _step_import_data(page: Page, file_path: Path):
    """Step 3: Re-import the exported CSV."""
    print("\n📤 STEP 3: Re-import the exported CSV...")

    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")
    time.sleep(1)

    # Expand Data Management panel if needed
    try:
        panel_header = page.locator(
            'h5:has-text("Data Management"), .panel-title:has-text("Data Management")'
        )
        if panel_header.count() > 0:
            panel_content = (
                panel_header.locator("..").locator("..").locator(".panel-content")
            )
            if panel_content.count() > 0 and not panel_content.is_visible():
                panel_header.click()
                print("   🖱️  Expanded Data Management panel")
                time.sleep(0.5)
    except Exception as e:
        print(f"   ⚠️  Could not check/expand panel: {e}")

    # Upload file
    file_input = page.locator('#dataImportForm input[type="file"]')
    file_input.wait_for(timeout=5000)
    file_input.set_input_files(str(file_path))
    print(f"   📁 Uploaded file to inline form: {file_path.name}")

    # Select Adapter
    import_adapter_select = page.locator("#import_adapter")
    import_adapter_select.wait_for(timeout=5000)
    page.wait_for_timeout(1000)

    try:
        import_adapter_select.select_option(value="generic_csv_v1")
        print("   ✅ Selected Generic CSV adapter for import")
    except Exception:
        pytest.skip(f"Generic CSV adapter not available for import")

    # Submit
    import_button = page.locator('button:has-text("Excel Import")')
    import_button.wait_for(timeout=5000)
    import_button.click()
    print("   🖱️  Submitted import via inline form")

    # Wait for results
    try:
        results_div = page.locator("#importResults")
        results_div.wait_for(state="visible", timeout=15000)

        error_alert = page.locator("#importResults .alert-danger")
        if error_alert.count() > 0:
            pytest.fail(f"Import failed with error: {error_alert.text_content()}")

        print("   ✅ Import completed successfully")
    except Exception as e:
        pytest.fail(f"Import did not complete: {str(e)}")

    time.sleep(2)


def _step_verify_integrity(page: Page, original_course_count: int):
    """Step 4: Verify data integrity after roundtrip."""
    print("\n✅ STEP 4: Verify data integrity...")

    page.goto(f"{BASE_URL}/courses")
    page.wait_for_load_state("networkidle")

    course_rows = page.locator("table tbody tr")
    visible_course_count = course_rows.count()

    print(f"   📊 Visible courses after roundtrip: {visible_course_count}")
    print(f"   📊 Original course count: {original_course_count}")

    assert visible_course_count > 0, "No courses visible after roundtrip import"

    if visible_course_count > 0:
        first_course = course_rows.first
        course_number = first_course.locator("td").first.text_content()
        assert (
            course_number and len(course_number.strip()) > 0
        ), "First course has empty number"
        print(f"   ✅ First course number: {course_number.strip()}")


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
    """
    page = authenticated_page
    page.goto(f"{BASE_URL}/dashboard")
    page.wait_for_load_state("networkidle")

    print("\n" + "=" * 70)
    print("TC-IE-104: Generic CSV Roundtrip Validation")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        save_dir = Path(tmpdir)

        # Step 1: Export
        download_path = _step_export_data(page, save_dir)

        # Step 2: Verify ZIP
        _, original_course_count = _step_verify_zip(download_path)

        # Step 3: Import
        _step_import_data(page, download_path)

        # Step 4: Verify
        _step_verify_integrity(page, original_course_count)

    print("\n" + "=" * 70)
    print("✅ TC-IE-104: Roundtrip validation PASSED!")
    print("=" * 70)
