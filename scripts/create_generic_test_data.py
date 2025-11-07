#!/usr/bin/env python3
"""
create_generic_test_data.py - Create generic CSV adapter test data for E2E tests

Creates a ZIP file following the Generic CSV Adapter format with:
- ~6-10 representative course records
- Edge cases: conflicts, duplicates, various data types
- Institution-agnostic format (no CEI-specific data)
"""

import csv
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, cast

# Output directory
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "tests" / "e2e" / "fixtures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "generic_test_data.zip"

# Format version
FORMAT_VERSION = "1.0"
MANIFEST_FILENAME = "manifest.json"

# Test institution ID (generic, not CEI-specific)
TEST_INSTITUTION_ID = "test-institution-001"
TEST_INSTITUTION_NAME = "Test University"

# Timestamps
NOW = datetime.now(timezone.utc).isoformat()
CREATED_AT = "2024-01-01T00:00:00Z"
UPDATED_AT = NOW

# Create ZIP file
with zipfile.ZipFile(OUTPUT_FILE, "w", zipfile.ZIP_DEFLATED) as zf:
    # 1. institutions.csv
    institutions_csv = [
        [
            "id",
            "name",
            "short_name",
            "website_url",
            "created_by",
            "admin_email",
            "allow_self_registration",
            "require_email_verification",
            "is_active",
            "created_at",
            "updated_at",
        ],
        [
            TEST_INSTITUTION_ID,
            TEST_INSTITUTION_NAME,
            "TestU",
            "https://testu.edu",
            "admin-001",
            "admin@testu.edu",
            "true",
            "true",
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
    ]
    zf.writestr(
        "institutions.csv",
        "\n".join(",".join(row) for row in institutions_csv),
    )

    # 2. programs.csv
    programs_csv = [
        [
            "program_id",
            "name",
            "short_name",
            "description",
            "institution_id",
            "created_by",
            "is_default",
            "is_active",
            "created_at",
            "updated_at",
        ],
        [
            "prog-cs",
            "Computer Science",
            "CS",
            "Undergraduate Computer Science Program",
            TEST_INSTITUTION_ID,
            "admin-001",
            "true",
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            "prog-math",
            "Mathematics",
            "MATH",
            "Mathematics Program",
            TEST_INSTITUTION_ID,
            "admin-001",
            "false",
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            "prog-eng",
            "Engineering",
            "ENG",
            "Engineering Program",
            TEST_INSTITUTION_ID,
            "admin-001",
            "false",
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
    ]
    zf.writestr(
        "programs.csv",
        "\n".join(",".join(row) for row in programs_csv),
    )

    # 3. users.csv (instructors and admins)
    users_csv = [
        [
            "id",
            "email",
            "password_hash",
            "first_name",
            "last_name",
            "display_name",
            "role",
            "institution_id",
            "invited_by",
            "invited_at",
            "registration_completed_at",
            "account_status",
            "email_verified",
            "oauth_provider",
            "created_at",
            "updated_at",
        ],
        [
            "user-instructor-1",
            "instructor1@testu.edu",
            "",  # No password hash (security)
            "Alice",
            "Johnson",
            "",
            "instructor",
            TEST_INSTITUTION_ID,
            "",
            "",
            CREATED_AT,
            "pending",
            "false",
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            "user-instructor-2",
            "instructor2@testu.edu",
            "",
            "Bob",
            "Smith",
            "",
            "instructor",
            TEST_INSTITUTION_ID,
            "",
            "",
            CREATED_AT,
            "pending",
            "false",
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            "user-admin-1",
            "admin@testu.edu",
            "",
            "Admin",
            "User",
            "",
            "institution_admin",
            TEST_INSTITUTION_ID,
            "",
            "",
            CREATED_AT,
            "pending",
            "false",
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
    ]
    zf.writestr(
        "users.csv",
        "\n".join(",".join(row) for row in users_csv),
    )

    # 4. user_programs.csv
    user_programs_csv = [
        ["user_id", "program_id"],
        ["user-instructor-1", "prog-cs"],
        ["user-instructor-1", "prog-math"],
        ["user-instructor-2", "prog-eng"],
    ]
    zf.writestr(
        "user_programs.csv",
        "\n".join(",".join(row) for row in user_programs_csv),
    )

    # 5. courses.csv (6-10 courses with edge cases)
    courses_csv = [
        [
            "id",
            "course_number",
            "course_title",
            "department",
            "credit_hours",
            "institution_id",
            "active",
            "created_at",
            "updated_at",
        ],
        # Normal course
        [
            "course-cs101",
            "CS101",
            "Introduction to Computer Science",
            "Computer Science",
            "3",
            TEST_INSTITUTION_ID,
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Course with hyphen in number
        [
            "course-math201",
            "MATH-201",
            "Calculus I",
            "Mathematics",
            "4",
            TEST_INSTITUTION_ID,
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Course with different credit hours
        [
            "course-eng301",
            "ENG301",
            "Engineering Design",
            "Engineering",
            "2",
            TEST_INSTITUTION_ID,
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Inactive course (edge case)
        [
            "course-cs999",
            "CS999",
            "Deprecated Course",
            "Computer Science",
            "3",
            TEST_INSTITUTION_ID,
            "false",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Course with long title (edge case)
        [
            "course-math401",
            "MATH401",
            "Advanced Topics in Mathematical Analysis and Differential Equations",
            "Mathematics",
            "3",
            TEST_INSTITUTION_ID,
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Course with special characters
        [
            "course-cs202",
            "CS202",
            "Data Structures & Algorithms",
            "Computer Science",
            "3",
            TEST_INSTITUTION_ID,
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Duplicate course number (conflict case)
        [
            "course-cs101-dup",
            "CS101",
            "Introduction to Computer Science (Duplicate)",
            "Computer Science",
            "3",
            TEST_INSTITUTION_ID,
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
    ]
    zf.writestr(
        "courses.csv",
        "\n".join(",".join(row) for row in courses_csv),
    )

    # 6. course_programs.csv
    course_programs_csv = [
        ["course_id", "program_id"],
        ["course-cs101", "prog-cs"],
        ["course-math201", "prog-math"],
        ["course-eng301", "prog-eng"],
        ["course-cs202", "prog-cs"],
        ["course-math401", "prog-math"],
        # Duplicate association (edge case)
        ["course-cs101", "prog-math"],
    ]
    zf.writestr(
        "course_programs.csv",
        "\n".join(",".join(row) for row in course_programs_csv),
    )

    # 7. terms.csv
    terms_csv = [
        [
            "id",
            "term_name",
            "name",
            "start_date",
            "end_date",
            "assessment_due_date",
            "active",
            "institution_id",
            "created_at",
            "updated_at",
        ],
        [
            "term-fa2024",
            "FA2024",
            "Fall 2024",
            "2024-08-26",
            "2024-12-15",
            "2024-12-20",
            "true",
            TEST_INSTITUTION_ID,
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            "term-sp2025",
            "SP2025",
            "Spring 2025",
            "2025-01-13",
            "2025-05-10",
            "2025-05-15",
            "true",
            TEST_INSTITUTION_ID,
            CREATED_AT,
            UPDATED_AT,
        ],
        # Inactive term (edge case)
        [
            "term-su2023",
            "SU2023",
            "Summer 2023",
            "2023-06-01",
            "2023-08-15",
            "2023-08-20",
            "false",
            TEST_INSTITUTION_ID,
            CREATED_AT,
            UPDATED_AT,
        ],
    ]
    zf.writestr(
        "terms.csv",
        "\n".join(",".join(row) for row in terms_csv),
    )

    # 8. course_offerings.csv
    course_offerings_csv = [
        [
            "id",
            "course_id",
            "term_id",
            "institution_id",
            "status",
            "capacity",
            "total_enrollment",
            "section_count",
            "created_at",
            "updated_at",
        ],
        [
            "off-cs101-fa2024",
            "course-cs101",
            "term-fa2024",
            TEST_INSTITUTION_ID,
            "active",
            "75",
            "50",
            "2",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            "off-math201-fa2024",
            "course-math201",
            "term-fa2024",
            TEST_INSTITUTION_ID,
            "active",
            "60",
            "45",
            "1",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            "off-eng301-sp2025",
            "course-eng301",
            "term-sp2025",
            TEST_INSTITUTION_ID,
            "active",
            "40",
            "30",
            "1",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Full capacity (edge case)
        [
            "off-cs202-fa2024",
            "course-cs202",
            "term-fa2024",
            TEST_INSTITUTION_ID,
            "active",
            "50",
            "50",
            "1",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Zero enrollment (edge case)
        [
            "off-math401-sp2025",
            "course-math401",
            "term-sp2025",
            TEST_INSTITUTION_ID,
            "active",
            "30",
            "0",
            "0",
            CREATED_AT,
            UPDATED_AT,
        ],
    ]
    zf.writestr(
        "course_offerings.csv",
        "\n".join(",".join(row) for row in course_offerings_csv),
    )

    # 9. course_sections.csv
    course_sections_csv = [
        [
            "id",
            "offering_id",
            "instructor_id",
            "section_number",
            "enrollment",
            "status",
            "grade_distribution",
            "assigned_date",
            "completed_date",
            "created_at",
            "updated_at",
        ],
        [
            "section-1",
            "off-cs101-fa2024",
            "user-instructor-1",
            "001",
            "25",
            "in_progress",
            "{}",
            CREATED_AT,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            "section-2",
            "off-cs101-fa2024",
            "user-instructor-2",
            "002",
            "25",
            "in_progress",
            '{"A":5,"B":10,"C":8,"D":2}',
            CREATED_AT,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            "section-3",
            "off-math201-fa2024",
            "user-instructor-1",
            "001",
            "45",
            "in_progress",
            "{}",
            CREATED_AT,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Completed section (edge case)
        [
            "section-4",
            "off-eng301-sp2025",
            "user-instructor-2",
            "001",
            "30",
            "completed",
            '{"A":8,"B":12,"C":7,"D":3}',
            CREATED_AT,
            UPDATED_AT,
            CREATED_AT,
            UPDATED_AT,
        ],
        # Section with no instructor (edge case)
        [
            "section-5",
            "off-cs202-fa2024",
            "",
            "001",
            "50",
            "assigned",
            "{}",
            CREATED_AT,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
    ]
    zf.writestr(
        "course_sections.csv",
        "\n".join(",".join(row) for row in course_sections_csv),
    )

    # 10. course_outcomes.csv
    course_outcomes_csv = [
        [
            "id",
            "course_id",
            "clo_number",
            "description",
            "assessment_method",
            "active",
            "assessment_data",
            "narrative",
            "created_at",
            "updated_at",
        ],
        [
            "outcome-1",
            "course-cs101",
            "1",
            "Students will understand basic programming concepts",
            "Written Exam",
            "true",
            "{}",
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            "outcome-2",
            "course-cs101",
            "2",
            "Students will write simple programs",
            "Programming Assignment",
            "true",
            '{"students_took":25,"students_passed":20}',
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            "outcome-3",
            "course-math201",
            "1",
            "Students will solve differential equations",
            "Problem Set",
            "true",
            "{}",
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Inactive outcome (edge case)
        [
            "outcome-4",
            "course-cs101",
            "3",
            "Deprecated learning outcome",
            "Exam",
            "false",
            "{}",
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
    ]
    zf.writestr(
        "course_outcomes.csv",
        "\n".join(",".join(row) for row in course_outcomes_csv),
    )

    # 11. user_invitations.csv (empty for test data)
    user_invitations_csv = [
        [
            "id",
            "email",
            "role",
            "institution_id",
            "invited_by",
            "invited_at",
            "status",
            "accepted_at",
            "personal_message",
            "created_at",
            "updated_at",
        ],
    ]
    zf.writestr(
        "user_invitations.csv",
        "\n".join(",".join(row) for row in user_invitations_csv),
    )

    # 12. manifest.json
    manifest = {
        "format_version": FORMAT_VERSION,
        "export_timestamp": NOW,
        "institution_id": TEST_INSTITUTION_ID,
        "institution_name": TEST_INSTITUTION_NAME,
        "adapter_id": "generic_csv_v1",
        "entity_counts": {
            "institutions": 1,
            "programs": 3,
            "users": 3,
            "user_programs": 3,
            "courses": 7,
            "course_programs": 6,
            "terms": 3,
            "course_offerings": 5,
            "course_sections": 5,
            "course_outcomes": 4,
            "user_invitations": 0,
        },
        "import_order": [
            "institutions",
            "programs",
            "users",
            "user_programs",
            "courses",
            "course_programs",
            "terms",
            "course_offerings",
            "course_sections",
            "course_outcomes",
            "user_invitations",
        ],
    }
    zf.writestr(
        MANIFEST_FILENAME,
        json.dumps(manifest, indent=2),
    )

print(f"✅ Created generic test data: {OUTPUT_FILE}")
entity_counts = cast(Dict[str, int], manifest["entity_counts"])
print(f"   Contains: {sum(entity_counts.values())} total records")
print(f"   Entity types: {len([k for k, v in entity_counts.items() if v > 0])}")

