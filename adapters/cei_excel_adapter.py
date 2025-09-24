"""
CEI Excel Import Adapter

This adapter handles the specific Excel format used by CEI (College of Education and Innovation).
It contains all CEI-specific parsing logic, column mappings, and data transformations.

This keeps CEI-specific logic separate from the generic import system.
"""

from typing import Any, Dict, Optional, Tuple

import pandas as pd

from models import validate_course_number

# Constants for repeated strings
FACULTY_NAME_COLUMN = "Faculty Name"


def validate_cei_term_name(term_name: str) -> bool:
    """
    Validate CEI-specific term name formats

    Supports:
    - Standard format: "2024 Fall", "2024 Spring", etc.
    - CEI abbreviated format: "2024FA", "2024SP", "2024SU", "2024WI"
    """
    # Handle space-separated format: "2024 Fall"
    parts = term_name.split()
    if len(parts) == 2 and parts[0].isdigit() and len(parts[0]) == 4:
        season = parts[1].lower()
        return season in ["fall", "spring", "summer", "winter"]

    # Handle CEI abbreviated format: "FA2024", "SP2025", "SU2023", "WI2026"
    if len(term_name) == 6 and term_name[2:].isdigit():
        season = term_name[:2].upper()
        return season in ["FA", "SP", "SU", "WI"]  # Fall, Spring, Summer, Winter

    return False


def parse_cei_term(effterm_c: str) -> Tuple[str, str]:
    """
    Parse CEI's effterm_c format into year and season.

    Args:
        effterm_c: Term code like 'FA2024', 'SP2025', etc.

    Returns:
        Tuple of (year, season) where season is the full name

    Example:
        parse_cei_term('FA2024') -> ('2024', 'Fall')
    """
    if not effterm_c or len(effterm_c) != 6:
        raise ValueError(f"Invalid effterm_c format: {effterm_c}")

    season_code = effterm_c[:2].upper()
    year = effterm_c[2:]

    season_map = {"FA": "Fall", "SP": "Spring", "SU": "Summer", "WI": "Winter"}

    if season_code not in season_map:
        raise ValueError(f"Invalid season code: {season_code}")

    return year, season_map[season_code]


def _extract_course_data(
    row: pd.Series, institution_id: str
) -> Optional[Dict[str, Any]]:
    """Extract course information from row."""
    if "course" not in row or pd.isna(row["course"]):
        return None

    course_number = str(row.get("course", ""))
    if not validate_course_number(course_number):
        return None

    return {
        "course_number": course_number,
        "course_title": f"Course {course_number}",  # CEI file doesn't have course titles
        "department": _extract_department_from_course(course_number),
        "credit_hours": 3,  # Default, CEI file doesn't have credit hours
        "institution_id": institution_id,
    }


def _extract_user_data(
    row: pd.Series, institution_id: str, course_data: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Extract instructor information from row."""

    # Handle two different input formats:
    # 1. Files with email column (test data format)
    # 2. Files with Faculty Name column (original format)

    if "email" in row and not pd.isna(row["email"]):
        # Format 1: Has email column - extract name from email if needed
        email = str(row["email"]).strip()
        if not email:
            return None

        # Try to extract name from email or use placeholder
        first_name, last_name = _extract_name_from_email(email)

        return {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "role": "instructor",
            "department": course_data.get("department") if course_data else None,
            "institution_id": institution_id,
            "account_status": "imported",
            "active_user": False,
        }

    elif FACULTY_NAME_COLUMN in row and not pd.isna(row[FACULTY_NAME_COLUMN]):
        # Format 2: Has Faculty Name but NO email - this is a problem!
        # We cannot and should not generate fake emails
        instructor_name = str(row[FACULTY_NAME_COLUMN])
        first_name, last_name = _parse_name(instructor_name)

        return {
            "email": None,  # No email available - must be added manually later
            "first_name": first_name,
            "last_name": last_name,
            "role": "instructor",
            "department": course_data.get("department") if course_data else None,
            "institution_id": institution_id,
            "account_status": "needs_email",  # Flag that email is required
            "active_user": False,
        }

    return None  # No instructor information available


def _extract_term_data(row: pd.Series, institution_id: str) -> Optional[Dict[str, Any]]:
    """Extract term information from row."""

    # Handle two different input formats:
    # 1. Files with effterm_c column (original format like "FA2024")
    # 2. Files with Term column (standard format like "2024 Fall")

    if "effterm_c" in row and not pd.isna(row["effterm_c"]):
        # Format 1: CEI abbreviated format
        effterm_c = str(row["effterm_c"]).strip()
        if not effterm_c:
            return None

        try:
            year, season = parse_cei_term(effterm_c)
            return {
                "name": f"{season} {year}",
                "year": int(year),
                "season": season,
                "institution_id": institution_id,
                "is_active": True,
            }
        except ValueError as e:
            print(f"Warning: Could not parse term '{effterm_c}': {e}")
            return None

    elif "Term" in row and not pd.isna(row["Term"]):
        # Format 2: Standard format like "2024 Fall"
        term_name = str(row["Term"]).strip()
        if not term_name:
            return None

        try:
            # Parse standard format "YYYY Season"
            parts = term_name.split()
            if len(parts) >= 2 and parts[0].isdigit():
                parsed_year = int(parts[0])
                parsed_season = parts[1].title()  # Fall, Spring, etc.

                return {
                    "name": term_name,
                    "year": parsed_year,
                    "season": parsed_season,
                    "institution_id": institution_id,
                    "is_active": True,
                }
        except (ValueError, IndexError) as e:
            print(f"Warning: Could not parse term '{term_name}': {e}")
            return None

    return None


def _extract_offering_data(
    course_data: Optional[Dict[str, Any]],
    term_data: Optional[Dict[str, Any]],
    user_data: Optional[Dict[str, Any]],
    institution_id: str,
) -> Optional[Dict[str, Any]]:
    """Extract offering information from course and term data."""
    if not course_data or not term_data:
        return None

    return {
        "course_number": course_data["course_number"],
        "term_name": term_data["name"],
        "institution_id": institution_id,
        "instructor_email": user_data.get("email") if user_data else None,
        "is_active": True,
    }


def _extract_section_data(
    row: pd.Series,
    course_data: Optional[Dict[str, Any]],
    term_data: Optional[Dict[str, Any]],
    user_data: Optional[Dict[str, Any]],
    institution_id: str,
) -> Optional[Dict[str, Any]]:
    """Extract section information from row and related data."""
    if (
        not course_data
        or not term_data
        or "students" not in row
        or pd.isna(row["students"])
    ):
        return None

    try:
        student_count = int(row["students"])
        return {
            "course_number": course_data["course_number"],
            "term_name": term_data["name"],
            "section_number": "001",  # CEI doesn't provide section numbers
            "instructor_email": user_data.get("email") if user_data else None,
            "student_count": student_count,
            "institution_id": institution_id,
            "status": "active",
        }
    except (ValueError, TypeError):
        # Invalid student count, skip section
        return None


def parse_cei_excel_row(
    row: pd.Series, institution_id: str
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Parse a single row from CEI's Excel format.

    Args:
        row: Pandas Series representing one row
        institution_id: The institution ID to assign to entities

    Returns:
        Dictionary with entity types and their data
    """
    try:
        # Extract all entity data using focused helper functions
        course_data = _extract_course_data(row, institution_id)
        user_data = _extract_user_data(row, institution_id, course_data)
        term_data = _extract_term_data(row, institution_id)
        offering_data = _extract_offering_data(
            course_data, term_data, user_data, institution_id
        )
        section_data = _extract_section_data(
            row, course_data, term_data, user_data, institution_id
        )

        return {
            "course": course_data,
            "user": user_data,
            "term": term_data,
            "offering": offering_data,
            "section": section_data,
        }

    except Exception as e:
        # Log error and return empty entities to continue processing
        print(f"Error parsing CEI Excel row: {str(e)}")
        return {
            "course": None,
            "user": None,
            "term": None,
            "offering": None,
            "section": None,
        }


def _extract_department_from_course(course_number: str) -> str:
    """Extract department from course number (e.g., 'MATH-101' -> 'Mathematics')."""
    # CEI-specific department mapping
    department_map = {
        "MATH": "Mathematics",
        "ENG": "English",
        "HIST": "History",
        "SCI": "Science",
        "BUS": "Business",
        "ART": "Art",
        "MUS": "Music",
        "PE": "Physical Education",
        "COMP": "Computer Science",
        "BIO": "Biology",
        "CHEM": "Chemistry",
        "PHYS": "Physics",
        "SOC": "Sociology",
        "PSYC": "Psychology",
        "ECON": "Economics",
        "POLS": "Political Science",
        "PHIL": "Philosophy",
        "REL": "Religious Studies",
        "FOR": "Foreign Language",
        "NURS": "Nursing",
        "EDU": "Education",
    }

    if "-" in course_number:
        prefix = course_number.split("-")[0].upper()
        return department_map.get(prefix, prefix)
    return "General Studies"


def _parse_name(full_name: str) -> Tuple[str, str]:
    """Parse full name into first and last name."""
    if not full_name or not full_name.strip():
        return "Unknown", "Instructor"

    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], "Name"
    elif len(parts) == 2:
        return parts[0], parts[1]
    else:
        # More than 2 parts, assume first is first name, rest is last name
        return parts[0], " ".join(parts[1:])


def _extract_name_from_email(email: str) -> Tuple[str, str]:
    """Extract first and last name from email address."""
    if not email or "@" not in email:
        return "Unknown", "Instructor"

    local_part = email.split("@")[0]

    # Handle common email formats
    if "." in local_part:
        # firstname.lastname format
        parts = local_part.split(".")
        first_name = parts[0].title()
        last_name = ".".join(parts[1:]).title()
    else:
        # Single name or other format - use as last name
        first_name = "Unknown"
        last_name = local_part.title()

    return first_name, last_name
