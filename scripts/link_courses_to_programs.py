#!/usr/bin/env python3
"""
Link Courses to Programs Script

Automatically links courses to programs based on course number prefixes.
Run this after importing course data to ensure Program Management panel populates correctly.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import src.database.database_service as database_service
import src.database.database_service as db


def link_courses_to_programs(institution_id):
    """Link courses to programs based on course prefixes"""
    print("🔗 Linking courses to programs...")

    # Get all courses and programs
    courses = db.get_all_courses(institution_id)
    programs = db.get_programs_by_institution(institution_id)

    if not courses or not programs:
        print("   ⚠️  No courses or programs found to link")
        return 0

    # Build program lookup by name
    program_lookup = {p["name"]: p["id"] for p in programs}

    # Course prefix to program mapping
    course_mappings = {
        "BIOL": "Biological Sciences",
        "BSN": "Biological Sciences",
        "ZOOL": "Zoology",
        "CEI": "CEI Default Program",
    }

    linked_count = 0
    for course in courses:
        # Extract prefix from course number (e.g., "BIOL-228" -> "BIOL")
        course_number = course["course_number"]
        prefix = course_number.split("-")[0] if "-" in course_number else None

        if prefix and prefix in course_mappings:
            program_name = course_mappings[prefix]
            program_id = program_lookup.get(program_name)

            if program_id:
                try:
                    db.link_course_to_program(course["id"], program_id)
                    linked_count += 1
                    print(f"   ✓ Linked {course_number} to {program_name}")
                except Exception:  # nosec B110 - might already be linked
                    pass

    if linked_count > 0:
        print(f"   ✅ Linked {linked_count} courses to programs")
    else:
        print("   ℹ️  No new course-program links created")

    return linked_count


def main():
    """Main entry point"""
    print("📚 Course-Program Linking Utility")
    print("=" * 50)

    # Get CEI institution
    institution = db.get_institution_by_short_name("CEI")
    if not institution:
        print("❌ CEI institution not found")
        return 1

    # Handle both dict and object formats
    institution_id = (
        institution.get("id") if isinstance(institution, dict) else institution.id
    )
    institution_name = (
        institution.get("name") if isinstance(institution, dict) else institution.name
    )
    print(f"Found institution: {institution_name} (ID: {institution_id})\n")

    # Link courses
    count = link_courses_to_programs(institution_id)

    print("\n" + "=" * 50)
    if count > 0:
        print("✅ Course linking completed successfully!")
    else:
        print("✅ All courses already linked or no courses to link")

    return 0


if __name__ == "__main__":
    sys.exit(main())
