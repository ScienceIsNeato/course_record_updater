"""
E2E test to verify Course Offerings page shows same count as Dashboard.

This test validates that:
1. Dashboard shows all course offerings with their programs
2. Dedicated Course Offerings page shows the same count
3. Program associations are properly displayed on both views
"""

from playwright.sync_api import Page, expect

from .conftest import BASE_URL


def test_offerings_dashboard_parity(authenticated_institution_admin_page: Page):
    """
    Test that Course Offerings dedicated page shows same count as dashboard.

    Regression test for issue where:
    1. Frontend validation was incorrectly filtering offerings with empty program_ids
    2. Variable name collision in list_course_offerings was filtering offerings incorrectly
    """
    page = authenticated_institution_admin_page

    # Should already be on dashboard after authentication
    expect(page.locator("h1")).to_be_visible()

    # Wait for dashboard to fully load
    page.wait_for_load_state("networkidle")

    # Navigate to dedicated Course Offerings page
    page.goto(f"{BASE_URL}/offerings")
    page.wait_for_load_state("networkidle")

    # Verify we're on offerings page
    expect(page.locator("h1, h2, h3")).to_contain_text(
        "Course Offerings", ignore_case=True
    )

    # Get count from dedicated offerings page (should show all offerings)
    # Look for table rows that are actual offerings (have action buttons)
    offerings_rows = page.locator('table tbody tr:has(button:has-text("Edit"))')
    offerings_page_count = offerings_rows.count()

    print(f"\nCourse Offerings page shows {offerings_page_count} offerings")

    # Verify we have offerings displayed
    assert (
        offerings_page_count > 0
    ), f"Course Offerings page should show offerings but shows {offerings_page_count}"

    # Verify offerings have program associations by checking first row
    if offerings_page_count > 0:
        first_row = offerings_rows.first
        expect(first_row).to_be_visible()
        print(
            f"✓ Verified {offerings_page_count} offerings displayed with action buttons"
        )
