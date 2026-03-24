#!/usr/bin/env python3
"""
Simple Export Test Script

Tests just the export functionality by creating some test data and exporting it.
This is a simpler test than the full roundtrip validation.
"""

import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database_service import (
    create_course,
    create_term,
    create_user,
)
from src.services.export_service import ExportConfig, ExportService


def ensure_mocku_institution() -> str:
    """Return an existing MockU institution ID or create it."""
    from src.database.database_service import (
        create_default_mocku_institution,
        get_institution_by_short_name,
    )

    mocku_institution = get_institution_by_short_name("MockU")
    if mocku_institution:
        institution_id = mocku_institution["institution_id"]
        print(f"✅ Using existing MockU institution: {institution_id}")
        return institution_id

    institution_id = create_default_mocku_institution()
    print(f"✅ Created MockU institution: {institution_id}")
    return institution_id


def create_export_test_data(institution_id: str) -> None:
    """Create minimal data needed to exercise export generation."""
    from datetime import date

    print("📝 Creating test data...")

    user1 = create_user(
        {
            "email": "test.instructor1@test.edu",
            "first_name": "Test",
            "last_name": "Instructor1",
            "role": "instructor",
            "department": "MATH",
            "institution_id": institution_id,
            "account_status": "active",
            "active_user": True,
        }
    )

    user2 = create_user(
        {
            "email": "test.instructor2@test.edu",
            "first_name": "Test",
            "last_name": "Instructor2",
            "role": "instructor",
            "department": "SCI",
            "institution_id": institution_id,
            "account_status": "active",
            "active_user": True,
        }
    )

    print(f"✅ Created users: {user1}, {user2}")

    course1 = create_course(
        {
            "course_number": "MATH-101",
            "course_name": "Basic Math",
            "department": "MATH",
            "institution_id": institution_id,
        }
    )

    course2 = create_course(
        {
            "course_number": "SCI-201",
            "course_name": "Basic Science",
            "department": "SCI",
            "institution_id": institution_id,
        }
    )

    print(f"✅ Created courses: {course1}, {course2}")

    term1 = create_term(
        {
            "term_name": "Fall 2024",
            "start_date": date(2024, 8, 15),
            "end_date": date(2024, 12, 15),
            "year": 2024,
            "season": "Fall",
            "institution_id": institution_id,
            "is_active": True,
        }
    )

    print(f"✅ Created term: {term1}")


def run_export(institution_id: str) -> bool:
    """Run the export and print a concise result summary."""
    print("\n📤 Testing export...")

    export_service = ExportService()
    config = ExportConfig(
        institution_id=institution_id,
        adapter_id="cei_excel_format_v1",
        export_view="standard",
    )

    output_path = Path("build-output/test_export.xlsx")
    result = export_service.export_data(config, output_path)

    if result.success:
        print("✅ Export successful!")
        print(f"📁 File: {result.file_path}")
        print(f"📊 Records: {result.records_exported}")

        if result.warnings:
            print(f"⚠️  Warnings: {result.warnings}")

        return True

    print("❌ Export failed!")
    print(f"🔍 Errors: {result.errors}")
    return False


def run_export_test() -> bool:
    """Test export functionality with simple test data."""

    print("🧪 Testing Export Service")
    print("=" * 50)

    try:
        institution_id = ensure_mocku_institution()
        create_export_test_data(institution_id)
        return run_export(institution_id)

    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        return False


if __name__ == "__main__":
    success = run_export_test()
    print("\n" + "=" * 50)
    print(f"🏁 Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
