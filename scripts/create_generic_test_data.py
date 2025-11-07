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
    TEST_ADMIN_ID,
    TEST_ADMIN_USER_EMAIL,
    TEST_ADMIN_USER_FIRST_NAME,
    TEST_ADMIN_USER_ID,
    TEST_ADMIN_USER_LAST_NAME,
    TEST_ASSESSMENT_DATA_EMPTY,
    TEST_ASSESSMENT_DATA_SAMPLE,
    TEST_ASSESSMENT_METHOD_ASSIGNMENT,
    TEST_ASSESSMENT_METHOD_EXAM,
    TEST_ASSESSMENT_METHOD_PROBLEM_SET,
    TEST_COURSE_CS101_CREDITS,
    TEST_COURSE_CS101_DEPARTMENT,
    TEST_COURSE_CS101_DUP_ID,
    TEST_COURSE_CS101_DUP_TITLE,
    TEST_COURSE_CS101_ID,
    TEST_COURSE_CS101_NUMBER,
    TEST_COURSE_CS101_TITLE,
    TEST_COURSE_CS202_CREDITS,
    TEST_COURSE_CS202_DEPARTMENT,
    TEST_COURSE_CS202_ID,
    TEST_COURSE_CS202_NUMBER,
    TEST_COURSE_CS202_TITLE,
    TEST_COURSE_CS999_ID,
    TEST_COURSE_CS999_NUMBER,
    TEST_COURSE_CS999_TITLE,
    TEST_COURSE_ENG301_CREDITS,
    TEST_COURSE_ENG301_DEPARTMENT,
    TEST_COURSE_ENG301_ID,
    TEST_COURSE_ENG301_NUMBER,
    TEST_COURSE_ENG301_TITLE,
    TEST_COURSE_MATH201_CREDITS,
    TEST_COURSE_MATH201_DEPARTMENT,
    TEST_COURSE_MATH201_ID,
    TEST_COURSE_MATH201_NUMBER,
    TEST_COURSE_MATH201_TITLE,
    TEST_COURSE_MATH401_CREDITS,
    TEST_COURSE_MATH401_DEPARTMENT,
    TEST_COURSE_MATH401_ID,
    TEST_COURSE_MATH401_NUMBER,
    TEST_COURSE_MATH401_TITLE,
    TEST_GRADE_DIST_COMPLETED,
    TEST_GRADE_DIST_EMPTY,
    TEST_GRADE_DIST_SAMPLE,
    TEST_INSTITUTION_ADMIN_EMAIL,
    TEST_INSTITUTION_ID,
    TEST_INSTITUTION_NAME,
    TEST_INSTITUTION_SHORT_NAME,
    TEST_INSTITUTION_WEBSITE,
    TEST_INSTRUCTOR_1_EMAIL,
    TEST_INSTRUCTOR_1_FIRST_NAME,
    TEST_INSTRUCTOR_1_ID,
    TEST_INSTRUCTOR_1_LAST_NAME,
    TEST_INSTRUCTOR_2_EMAIL,
    TEST_INSTRUCTOR_2_FIRST_NAME,
    TEST_INSTRUCTOR_2_ID,
    TEST_INSTRUCTOR_2_LAST_NAME,
    TEST_OFFERING_CS101_FA2024_ID,
    TEST_OFFERING_CS202_FA2024_ID,
    TEST_OFFERING_ENG301_SP2025_ID,
    TEST_OFFERING_MATH201_FA2024_ID,
    TEST_OFFERING_MATH401_SP2025_ID,
    TEST_OUTCOME_1_ID,
    TEST_OUTCOME_2_ID,
    TEST_OUTCOME_3_ID,
    TEST_OUTCOME_4_ID,
    TEST_PROGRAM_CS_DESCRIPTION,
    TEST_PROGRAM_CS_ID,
    TEST_PROGRAM_CS_NAME,
    TEST_PROGRAM_CS_SHORT_NAME,
    TEST_PROGRAM_ENG_DESCRIPTION,
    TEST_PROGRAM_ENG_ID,
    TEST_PROGRAM_ENG_NAME,
    TEST_PROGRAM_ENG_SHORT_NAME,
    TEST_PROGRAM_MATH_DESCRIPTION,
    TEST_PROGRAM_MATH_ID,
    TEST_PROGRAM_MATH_NAME,
    TEST_PROGRAM_MATH_SHORT_NAME,
    TEST_SECTION_1_ID,
    TEST_SECTION_2_ID,
    TEST_SECTION_3_ID,
    TEST_SECTION_4_ID,
    TEST_SECTION_5_ID,
    TEST_TERM_FA2024_DISPLAY_NAME,
    TEST_TERM_FA2024_DUE,
    TEST_TERM_FA2024_END,
    TEST_TERM_FA2024_ID,
    TEST_TERM_FA2024_NAME,
    TEST_TERM_FA2024_START,
    TEST_TERM_SP2025_DISPLAY_NAME,
    TEST_TERM_SP2025_DUE,
    TEST_TERM_SP2025_END,
    TEST_TERM_SP2025_ID,
    TEST_TERM_SP2025_NAME,
    TEST_TERM_SP2025_START,
    TEST_TERM_SU2023_DISPLAY_NAME,
    TEST_TERM_SU2023_DUE,
    TEST_TERM_SU2023_END,
    TEST_TERM_SU2023_ID,
    TEST_TERM_SU2023_NAME,
    TEST_TERM_SU2023_START,
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
CREATED_AT = "2024-01-01T00:00:00Z"
UPDATED_AT = NOW


def _write_csv_to_zip(zf: zipfile.ZipFile, filename: str, rows: List[List[str]]) -> None:
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
            TEST_INSTITUTION_ID,
            TEST_INSTITUTION_NAME,
            TEST_INSTITUTION_SHORT_NAME,
            TEST_INSTITUTION_WEBSITE,
            TEST_ADMIN_ID,
            TEST_INSTITUTION_ADMIN_EMAIL,
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
            TEST_PROGRAM_CS_ID,
            TEST_PROGRAM_CS_NAME,
            TEST_PROGRAM_CS_SHORT_NAME,
            TEST_PROGRAM_CS_DESCRIPTION,
            TEST_INSTITUTION_ID,
            TEST_ADMIN_ID,
            "true",
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_PROGRAM_MATH_ID,
            TEST_PROGRAM_MATH_NAME,
            TEST_PROGRAM_MATH_SHORT_NAME,
            TEST_PROGRAM_MATH_DESCRIPTION,
            TEST_INSTITUTION_ID,
            TEST_ADMIN_ID,
            "false",
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_PROGRAM_ENG_ID,
            TEST_PROGRAM_ENG_NAME,
            TEST_PROGRAM_ENG_SHORT_NAME,
            TEST_PROGRAM_ENG_DESCRIPTION,
            TEST_INSTITUTION_ID,
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
            TEST_INSTRUCTOR_1_ID,
            TEST_INSTRUCTOR_1_EMAIL,
            "",  # No password hash (security)
            TEST_INSTRUCTOR_1_FIRST_NAME,
            TEST_INSTRUCTOR_1_LAST_NAME,
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
            TEST_INSTRUCTOR_2_ID,
            TEST_INSTRUCTOR_2_EMAIL,
            "",
            TEST_INSTRUCTOR_2_FIRST_NAME,
            TEST_INSTRUCTOR_2_LAST_NAME,
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
            TEST_ADMIN_USER_ID,
            TEST_ADMIN_USER_EMAIL,
            "",
            TEST_ADMIN_USER_FIRST_NAME,
            TEST_ADMIN_USER_LAST_NAME,
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
    _write_csv_to_zip(zf, "users.csv", users_csv)

    # 4. user_programs.csv
    user_programs_csv = [
        ["user_id", "program_id"],
        [TEST_INSTRUCTOR_1_ID, TEST_PROGRAM_CS_ID],
        [TEST_INSTRUCTOR_1_ID, TEST_PROGRAM_MATH_ID],
        [TEST_INSTRUCTOR_2_ID, TEST_PROGRAM_ENG_ID],
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
            TEST_COURSE_CS101_ID,
            TEST_COURSE_CS101_NUMBER,
            TEST_COURSE_CS101_TITLE,
            TEST_COURSE_CS101_DEPARTMENT,
            TEST_COURSE_CS101_CREDITS,
            TEST_INSTITUTION_ID,
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Course with hyphen in number
        [
            TEST_COURSE_MATH201_ID,
            TEST_COURSE_MATH201_NUMBER,
            TEST_COURSE_MATH201_TITLE,
            TEST_COURSE_MATH201_DEPARTMENT,
            TEST_COURSE_MATH201_CREDITS,
            TEST_INSTITUTION_ID,
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Course with different credit hours
        [
            TEST_COURSE_ENG301_ID,
            TEST_COURSE_ENG301_NUMBER,
            TEST_COURSE_ENG301_TITLE,
            TEST_COURSE_ENG301_DEPARTMENT,
            TEST_COURSE_ENG301_CREDITS,
            TEST_INSTITUTION_ID,
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Inactive course (edge case)
        [
            TEST_COURSE_CS999_ID,
            TEST_COURSE_CS999_NUMBER,
            TEST_COURSE_CS999_TITLE,
            TEST_COURSE_CS101_DEPARTMENT,
            TEST_COURSE_CS101_CREDITS,
            TEST_INSTITUTION_ID,
            "false",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Course with long title (edge case)
        [
            TEST_COURSE_MATH401_ID,
            TEST_COURSE_MATH401_NUMBER,
            TEST_COURSE_MATH401_TITLE,
            TEST_COURSE_MATH201_DEPARTMENT,
            TEST_COURSE_MATH401_CREDITS,
            TEST_INSTITUTION_ID,
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Course with special characters
        [
            TEST_COURSE_CS202_ID,
            TEST_COURSE_CS202_NUMBER,
            TEST_COURSE_CS202_TITLE,
            TEST_COURSE_CS202_DEPARTMENT,
            TEST_COURSE_CS202_CREDITS,
            TEST_INSTITUTION_ID,
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Duplicate course number (conflict case)
        [
            TEST_COURSE_CS101_DUP_ID,
            TEST_COURSE_CS101_NUMBER,
            TEST_COURSE_CS101_DUP_TITLE,
            TEST_COURSE_CS101_DEPARTMENT,
            TEST_COURSE_CS101_CREDITS,
            TEST_INSTITUTION_ID,
            "true",
            CREATED_AT,
            UPDATED_AT,
        ],
    ]
    _write_csv_to_zip(zf, "courses.csv", courses_csv)

    # 6. course_programs.csv
    course_programs_csv = [
        ["course_id", "program_id"],
        [TEST_COURSE_CS101_ID, TEST_PROGRAM_CS_ID],
        [TEST_COURSE_MATH201_ID, TEST_PROGRAM_MATH_ID],
        [TEST_COURSE_ENG301_ID, TEST_PROGRAM_ENG_ID],
        [TEST_COURSE_CS202_ID, TEST_PROGRAM_CS_ID],
        [TEST_COURSE_MATH401_ID, TEST_PROGRAM_MATH_ID],
        # Duplicate association (edge case)
        [TEST_COURSE_CS101_ID, TEST_PROGRAM_MATH_ID],
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
            TEST_TERM_FA2024_ID,
            TEST_TERM_FA2024_NAME,
            TEST_TERM_FA2024_DISPLAY_NAME,
            TEST_TERM_FA2024_START,
            TEST_TERM_FA2024_END,
            TEST_TERM_FA2024_DUE,
            "true",
            TEST_INSTITUTION_ID,
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_TERM_SP2025_ID,
            TEST_TERM_SP2025_NAME,
            TEST_TERM_SP2025_DISPLAY_NAME,
            TEST_TERM_SP2025_START,
            TEST_TERM_SP2025_END,
            TEST_TERM_SP2025_DUE,
            "true",
            TEST_INSTITUTION_ID,
            CREATED_AT,
            UPDATED_AT,
        ],
        # Inactive term (edge case)
        [
            TEST_TERM_SU2023_ID,
            TEST_TERM_SU2023_NAME,
            TEST_TERM_SU2023_DISPLAY_NAME,
            TEST_TERM_SU2023_START,
            TEST_TERM_SU2023_END,
            TEST_TERM_SU2023_DUE,
            "false",
            TEST_INSTITUTION_ID,
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
            TEST_OFFERING_CS101_FA2024_ID,
            TEST_COURSE_CS101_ID,
            TEST_TERM_FA2024_ID,
            TEST_INSTITUTION_ID,
            "active",
            "75",
            "50",
            "2",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_OFFERING_MATH201_FA2024_ID,
            TEST_COURSE_MATH201_ID,
            TEST_TERM_FA2024_ID,
            TEST_INSTITUTION_ID,
            "active",
            "60",
            "45",
            "1",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_OFFERING_ENG301_SP2025_ID,
            TEST_COURSE_ENG301_ID,
            TEST_TERM_SP2025_ID,
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
            TEST_OFFERING_CS202_FA2024_ID,
            TEST_COURSE_CS202_ID,
            TEST_TERM_FA2024_ID,
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
            TEST_OFFERING_MATH401_SP2025_ID,
            TEST_COURSE_MATH401_ID,
            TEST_TERM_SP2025_ID,
            TEST_INSTITUTION_ID,
            "active",
            "30",
            "0",
            "0",
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
            TEST_SECTION_1_ID,
            TEST_OFFERING_CS101_FA2024_ID,
            TEST_INSTRUCTOR_1_ID,
            "001",
            "25",
            "in_progress",
            TEST_GRADE_DIST_EMPTY,
            CREATED_AT,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_SECTION_2_ID,
            TEST_OFFERING_CS101_FA2024_ID,
            TEST_INSTRUCTOR_2_ID,
            "002",
            "25",
            "in_progress",
            TEST_GRADE_DIST_SAMPLE,
            CREATED_AT,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_SECTION_3_ID,
            TEST_OFFERING_MATH201_FA2024_ID,
            TEST_INSTRUCTOR_1_ID,
            "001",
            "45",
            "in_progress",
            TEST_GRADE_DIST_EMPTY,
            CREATED_AT,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Completed section (edge case)
        [
            TEST_SECTION_4_ID,
            TEST_OFFERING_ENG301_SP2025_ID,
            TEST_INSTRUCTOR_2_ID,
            "001",
            "30",
            "completed",
            TEST_GRADE_DIST_COMPLETED,
            CREATED_AT,
            UPDATED_AT,
            CREATED_AT,
            UPDATED_AT,
        ],
        # Section with no instructor (edge case)
        [
            TEST_SECTION_5_ID,
            TEST_OFFERING_CS202_FA2024_ID,
            "",
            "001",
            "50",
            "assigned",
            TEST_GRADE_DIST_EMPTY,
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
            TEST_OUTCOME_1_ID,
            TEST_COURSE_CS101_ID,
            "1",
            "Students will understand basic programming concepts",
            TEST_ASSESSMENT_METHOD_EXAM,
            "true",
            TEST_ASSESSMENT_DATA_EMPTY,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_OUTCOME_2_ID,
            TEST_COURSE_CS101_ID,
            "2",
            "Students will write simple programs",
            TEST_ASSESSMENT_METHOD_ASSIGNMENT,
            "true",
            TEST_ASSESSMENT_DATA_SAMPLE,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        [
            TEST_OUTCOME_3_ID,
            TEST_COURSE_MATH201_ID,
            "1",
            "Students will solve differential equations",
            TEST_ASSESSMENT_METHOD_PROBLEM_SET,
            "true",
            TEST_ASSESSMENT_DATA_EMPTY,
            "",
            CREATED_AT,
            UPDATED_AT,
        ],
        # Inactive outcome (edge case)
        [
            TEST_OUTCOME_4_ID,
            TEST_COURSE_CS101_ID,
            "3",
            "Deprecated learning outcome",
            TEST_ASSESSMENT_METHOD_EXAM,
            "false",
            TEST_ASSESSMENT_DATA_EMPTY,
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
