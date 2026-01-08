#!/usr/bin/env python3
"""
create_generic_test_data.py - Create generic CSV adapter test data for E2E tests

Creates a ZIP file following the Generic CSV Adapter format with:
- ~6-10 representative course records
- Edge cases: conflicts, duplicates, various data types
- Institution-agnostic format (no CEI-specific data)
"""

import csv
import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, cast

# Import test constants
sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.test_constants import (
    CREATED_AT,
    TEST_ADMIN_ID,
    TEST_ADMIN_USER,
    TEST_ASSESSMENT_DATA_EMPTY,
    TEST_ASSESSMENT_DATA_SAMPLE,
    TEST_ASSESSMENT_METHOD_ASSIGNMENT,
    TEST_ASSESSMENT_METHOD_EXAM,
    TEST_ASSESSMENT_METHOD_PROBLEM_SET,
    TEST_COURSE_CS101,
    TEST_COURSE_CS101_DUP,
    TEST_COURSE_CS202,
    TEST_COURSE_CS999,
    TEST_COURSE_ENG301,
    TEST_COURSE_MATH201,
    TEST_COURSE_MATH401,
    TEST_GRADE_DIST_COMPLETED,
    TEST_GRADE_DIST_EMPTY,
    TEST_GRADE_DIST_SAMPLE,
    TEST_INSTITUTION,
    TEST_INSTRUCTOR_1,
    TEST_INSTRUCTOR_2,
    TEST_OFFERING_CS101_FA2025,
    TEST_OFFERING_CS202_FA2025,
    TEST_OFFERING_ENG301_SP2026,
    TEST_OFFERING_MATH201_FA2025,
    TEST_OFFERING_MATH401_SP2026,
    TEST_OUTCOME_1,
    TEST_OUTCOME_2,
    TEST_OUTCOME_3,
    TEST_OUTCOME_4,
    TEST_PROGRAM_CS,
    TEST_PROGRAM_ENG,
    TEST_PROGRAM_MATH,
    TEST_SECTION_1,
    TEST_SECTION_2,
    TEST_SECTION_3,
    TEST_SECTION_4,
    TEST_SECTION_5,
    TEST_TERM_FA2025,
    TEST_TERM_SP2026,
    TEST_TERM_SU2024,
)

# Output directory
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "tests" / "e2e" / "fixtures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "generic_test_data.zip"

# Format version
FORMAT_VERSION = "1.0"
MANIFEST_FILENAME = "manifest.json"

# Timestamps
NOW = datetime.now(timezone.utc).isoformat()
UPDATED_AT = NOW


def _write_csv_to_zip(
    zf: zipfile.ZipFile, filename: str, rows: List[List[str]]
) -> None:
    """
    Write CSV rows to ZIP file using csv.writer for proper escaping.

    Args:
        zf: ZipFile object
        filename: Name of CSV file in ZIP
        rows: List of rows, each row is a list of strings
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    zf.writestr(filename, output.getvalue())


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
            TEST_INSTITUTION.id,
            TEST_INSTITUTION.name,
            TEST_INSTITUTION.short_name,
            TEST_INSTITUTION.website,
            TEST_ADMIN_ID,
            TEST_INSTITUTION.admin_email,
            "true",
            "true",
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
    ]
    _write_csv_to_zip(zf, "institutions.csv", institutions_csv)

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
            TEST_PROGRAM_CS.id,
            TEST_PROGRAM_CS.name,
            TEST_PROGRAM_CS.short_name,
            TEST_PROGRAM_CS.description,
            TEST_INSTITUTION.id,
            TEST_ADMIN_ID,
            "true",
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_PROGRAM_MATH.id,
            TEST_PROGRAM_MATH.name,
            TEST_PROGRAM_MATH.short_name,
            TEST_PROGRAM_MATH.description,
            TEST_INSTITUTION.id,
            TEST_ADMIN_ID,
            "false",
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_PROGRAM_ENG.id,
            TEST_PROGRAM_ENG.name,
            TEST_PROGRAM_ENG.short_name,
            TEST_PROGRAM_ENG.description,
            TEST_INSTITUTION.id,
            TEST_ADMIN_ID,
            "false",
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
    ]
    _write_csv_to_zip(zf, "programs.csv", programs_csv)

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
            TEST_INSTRUCTOR_1.id,
            TEST_INSTRUCTOR_1.email,
            "",  # No password hash (security)
            TEST_INSTRUCTOR_1.first_name,
            TEST_INSTRUCTOR_1.last_name,
            TEST_INSTRUCTOR_1.display_name,
            TEST_INSTRUCTOR_1.role,
            TEST_INSTITUTION.id,
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
            TEST_INSTRUCTOR_2.id,
            TEST_INSTRUCTOR_2.email,
            "",
            TEST_INSTRUCTOR_2.first_name,
            TEST_INSTRUCTOR_2.last_name,
            TEST_INSTRUCTOR_2.display_name,
            TEST_INSTRUCTOR_2.role,
            TEST_INSTITUTION.id,
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
            TEST_ADMIN_USER.id,
            TEST_ADMIN_USER.email,
            "",
            TEST_ADMIN_USER.first_name,
            TEST_ADMIN_USER.last_name,
            TEST_ADMIN_USER.display_name,
            TEST_ADMIN_USER.role,
            TEST_INSTITUTION.id,
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
    _write_csv_to_zip(zf, "users.csv", users_csv)

    # 4. user_programs.csv
    user_programs_csv = [
        ["user_id", "program_id"],
        [TEST_INSTRUCTOR_1.id, TEST_PROGRAM_CS.id],
        [TEST_INSTRUCTOR_1.id, TEST_PROGRAM_MATH.id],
        [TEST_INSTRUCTOR_2.id, TEST_PROGRAM_ENG.id],
    ]
    _write_csv_to_zip(zf, "user_programs.csv", user_programs_csv)

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
            TEST_COURSE_CS101.id,
            TEST_COURSE_CS101.number,
            TEST_COURSE_CS101.title,
            TEST_COURSE_CS101.department,
            TEST_COURSE_CS101.credits,
            TEST_INSTITUTION.id,
            str(TEST_COURSE_CS101.active).lower(),
            CREATED_AT,
            UPDATED_AT,
        ],
        # Course with hyphen in number
        [
            TEST_COURSE_MATH201.id,
            TEST_COURSE_MATH201.number,
            TEST_COURSE_MATH201.title,
            TEST_COURSE_MATH201.department,
            TEST_COURSE_MATH201.credits,
            TEST_INSTITUTION.id,
            str(TEST_COURSE_MATH201.active).lower(),
            CREATED_AT,
            UPDATED_AT,
        ],
        # Course with different credit hours
        [
            TEST_COURSE_ENG301.id,
            TEST_COURSE_ENG301.number,
            TEST_COURSE_ENG301.title,
            TEST_COURSE_ENG301.department,
            TEST_COURSE_ENG301.credits,
            TEST_INSTITUTION.id,
            str(TEST_COURSE_ENG301.active).lower(),
            CREATED_AT,
            UPDATED_AT,
        ],
        # Inactive course (edge case)
        [
            TEST_COURSE_CS999.id,
            TEST_COURSE_CS999.number,
            TEST_COURSE_CS999.title,
            TEST_COURSE_CS999.department,
            TEST_COURSE_CS999.credits,
            TEST_INSTITUTION.id,
            str(TEST_COURSE_CS999.active).lower(),
            CREATED_AT,
            UPDATED_AT,
        ],
        # Course with long title (edge case)
        [
            TEST_COURSE_MATH401.id,
            TEST_COURSE_MATH401.number,
            TEST_COURSE_MATH401.title,
            TEST_COURSE_MATH401.department,
            TEST_COURSE_MATH401.credits,
            TEST_INSTITUTION.id,
            str(TEST_COURSE_MATH401.active).lower(),
            CREATED_AT,
            UPDATED_AT,
        ],
        # Course with special characters
        [
            TEST_COURSE_CS202.id,
            TEST_COURSE_CS202.number,
            TEST_COURSE_CS202.title,
            TEST_COURSE_CS202.department,
            TEST_COURSE_CS202.credits,
            TEST_INSTITUTION.id,
            str(TEST_COURSE_CS202.active).lower(),
            CREATED_AT,
            UPDATED_AT,
        ],
        # Duplicate course number (conflict case)
        [
            TEST_COURSE_CS101_DUP.id,
            TEST_COURSE_CS101_DUP.number,
            TEST_COURSE_CS101_DUP.title,
            TEST_COURSE_CS101_DUP.department,
            TEST_COURSE_CS101_DUP.credits,
            TEST_INSTITUTION.id,
            str(TEST_COURSE_CS101_DUP.active).lower(),
            CREATED_AT,
            UPDATED_AT,
        ],
    ]
    _write_csv_to_zip(zf, "courses.csv", courses_csv)

    # 6. course_programs.csv
    course_programs_csv = [
        ["course_id", "program_id"],
        [TEST_COURSE_CS101.id, TEST_PROGRAM_CS.id],
        [TEST_COURSE_MATH201.id, TEST_PROGRAM_MATH.id],
        [TEST_COURSE_ENG301.id, TEST_PROGRAM_ENG.id],
        [TEST_COURSE_CS202.id, TEST_PROGRAM_CS.id],
        [TEST_COURSE_MATH401.id, TEST_PROGRAM_MATH.id],
        # Duplicate association (edge case)
        [TEST_COURSE_CS101.id, TEST_PROGRAM_MATH.id],
    ]
    _write_csv_to_zip(zf, "course_programs.csv", course_programs_csv)

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
            TEST_TERM_FA2025.id,
            TEST_TERM_FA2025.name,
            TEST_TERM_FA2025.display_name,
            TEST_TERM_FA2025.start_date,
            TEST_TERM_FA2025.end_date,
            TEST_TERM_FA2025.due_date,
            str(TEST_TERM_FA2025.active).lower(),
            TEST_INSTITUTION.id,
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_TERM_SP2026.id,
            TEST_TERM_SP2026.name,
            TEST_TERM_SP2026.display_name,
            TEST_TERM_SP2026.start_date,
            TEST_TERM_SP2026.end_date,
            TEST_TERM_SP2026.due_date,
            str(TEST_TERM_SP2026.active).lower(),
            TEST_INSTITUTION.id,
            CREATED_AT,
            UPDATED_AT,
        ],
        # Inactive term (edge case)
        [
            TEST_TERM_SU2024.id,
            TEST_TERM_SU2024.name,
            TEST_TERM_SU2024.display_name,
            TEST_TERM_SU2024.start_date,
            TEST_TERM_SU2024.end_date,
            TEST_TERM_SU2024.due_date,
            str(TEST_TERM_SU2024.active).lower(),
            TEST_INSTITUTION.id,
            CREATED_AT,
            UPDATED_AT,
        ],
    ]
    _write_csv_to_zip(zf, "terms.csv", terms_csv)

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
            TEST_OFFERING_CS101_FA2025.id,
            TEST_OFFERING_CS101_FA2025.course_id,
            TEST_OFFERING_CS101_FA2025.term_id,
            TEST_INSTITUTION.id,
            TEST_OFFERING_CS101_FA2025.status,
            TEST_OFFERING_CS101_FA2025.capacity,
            TEST_OFFERING_CS101_FA2025.enrollment,
            TEST_OFFERING_CS101_FA2025.section_count,
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_OFFERING_MATH201_FA2025.id,
            TEST_OFFERING_MATH201_FA2025.course_id,
            TEST_OFFERING_MATH201_FA2025.term_id,
            TEST_INSTITUTION.id,
            TEST_OFFERING_MATH201_FA2025.status,
            TEST_OFFERING_MATH201_FA2025.capacity,
            TEST_OFFERING_MATH201_FA2025.enrollment,
            TEST_OFFERING_MATH201_FA2025.section_count,
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_OFFERING_ENG301_SP2026.id,
            TEST_OFFERING_ENG301_SP2026.course_id,
            TEST_OFFERING_ENG301_SP2026.term_id,
            TEST_INSTITUTION.id,
            TEST_OFFERING_ENG301_SP2026.status,
            TEST_OFFERING_ENG301_SP2026.capacity,
            TEST_OFFERING_ENG301_SP2026.enrollment,
            TEST_OFFERING_ENG301_SP2026.section_count,
            CREATED_AT,
            UPDATED_AT,
        ],
        # Full capacity (edge case)
        [
            TEST_OFFERING_CS202_FA2025.id,
            TEST_OFFERING_CS202_FA2025.course_id,
            TEST_OFFERING_CS202_FA2025.term_id,
            TEST_INSTITUTION.id,
            TEST_OFFERING_CS202_FA2025.status,
            TEST_OFFERING_CS202_FA2025.capacity,
            TEST_OFFERING_CS202_FA2025.enrollment,
            TEST_OFFERING_CS202_FA2025.section_count,
            CREATED_AT,
            UPDATED_AT,
        ],
        # Zero enrollment (edge case)
        [
            TEST_OFFERING_MATH401_SP2026.id,
            TEST_OFFERING_MATH401_SP2026.course_id,
            TEST_OFFERING_MATH401_SP2026.term_id,
            TEST_INSTITUTION.id,
            TEST_OFFERING_MATH401_SP2026.status,
            TEST_OFFERING_MATH401_SP2026.capacity,
            TEST_OFFERING_MATH401_SP2026.enrollment,
            TEST_OFFERING_MATH401_SP2026.section_count,
            CREATED_AT,
            UPDATED_AT,
        ],
    ]
    _write_csv_to_zip(zf, "course_offerings.csv", course_offerings_csv)

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
            TEST_SECTION_1.id,
            TEST_SECTION_1.offering_id,
            TEST_SECTION_1.instructor_id or "",
            TEST_SECTION_1.section_number,
            TEST_SECTION_1.enrollment,
            TEST_SECTION_1.status,
            TEST_SECTION_1.grade_distribution,
            CREATED_AT,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_SECTION_2.id,
            TEST_SECTION_2.offering_id,
            TEST_SECTION_2.instructor_id or "",
            TEST_SECTION_2.section_number,
            TEST_SECTION_2.enrollment,
            TEST_SECTION_2.status,
            TEST_SECTION_2.grade_distribution,
            CREATED_AT,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_SECTION_3.id,
            TEST_SECTION_3.offering_id,
            TEST_SECTION_3.instructor_id or "",
            TEST_SECTION_3.section_number,
            TEST_SECTION_3.enrollment,
            TEST_SECTION_3.status,
            TEST_SECTION_3.grade_distribution,
            CREATED_AT,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Completed section (edge case)
        [
            TEST_SECTION_4.id,
            TEST_SECTION_4.offering_id,
            TEST_SECTION_4.instructor_id or "",
            TEST_SECTION_4.section_number,
            TEST_SECTION_4.enrollment,
            TEST_SECTION_4.status,
            TEST_SECTION_4.grade_distribution,
            CREATED_AT,
            UPDATED_AT,
            CREATED_AT,
            UPDATED_AT,
        ],
        # Section with no instructor (edge case)
        [
            TEST_SECTION_5.id,
            TEST_SECTION_5.offering_id,
            TEST_SECTION_5.instructor_id or "",
            TEST_SECTION_5.section_number,
            TEST_SECTION_5.enrollment,
            TEST_SECTION_5.status,
            TEST_SECTION_5.grade_distribution,
            CREATED_AT,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
    ]
    _write_csv_to_zip(zf, "course_sections.csv", course_sections_csv)

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
            TEST_OUTCOME_1.id,
            TEST_OUTCOME_1.course_id,
            TEST_OUTCOME_1.clo_number,
            TEST_OUTCOME_1.description,
            TEST_OUTCOME_1.assessment_method,
            str(TEST_OUTCOME_1.active).lower(),
            TEST_OUTCOME_1.assessment_data,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_OUTCOME_2.id,
            TEST_OUTCOME_2.course_id,
            TEST_OUTCOME_2.clo_number,
            TEST_OUTCOME_2.description,
            TEST_OUTCOME_2.assessment_method,
            str(TEST_OUTCOME_2.active).lower(),
            TEST_OUTCOME_2.assessment_data,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_OUTCOME_3.id,
            TEST_OUTCOME_3.course_id,
            TEST_OUTCOME_3.clo_number,
            TEST_OUTCOME_3.description,
            TEST_OUTCOME_3.assessment_method,
            str(TEST_OUTCOME_3.active).lower(),
            TEST_OUTCOME_3.assessment_data,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Inactive outcome (edge case)
        [
            TEST_OUTCOME_4.id,
            TEST_OUTCOME_4.course_id,
            TEST_OUTCOME_4.clo_number,
            TEST_OUTCOME_4.description,
            TEST_OUTCOME_4.assessment_method,
            str(TEST_OUTCOME_4.active).lower(),
            TEST_OUTCOME_4.assessment_data,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
    ]
    _write_csv_to_zip(zf, "course_outcomes.csv", course_outcomes_csv)

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
    _write_csv_to_zip(zf, "user_invitations.csv", user_invitations_csv)

    # 12. manifest.json
    manifest = {
        "format_version": FORMAT_VERSION,
        "export_timestamp": NOW,
        "institution_id": TEST_INSTITUTION.id,
        "institution_name": TEST_INSTITUTION.name,
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
