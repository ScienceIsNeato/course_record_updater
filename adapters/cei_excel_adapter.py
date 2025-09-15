"""
CEI Excel Import Adapter

This adapter handles the specific Excel format used by CEI (College of Education and Innovation).
It contains all CEI-specific parsing logic, column mappings, and data transformations.

This keeps CEI-specific logic separate from the generic import system.
"""

from typing import Any, Dict, Optional, Tuple

import pandas as pd

from models import validate_course_number


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
        # Extract course information
        course_data = None
        if "course" in row and pd.notna(row["course"]):
            # Parse course number (e.g., "ACC-201")
            course_number = str(row.get("course", ""))
            if validate_course_number(course_number):
                course_data = {
                    "course_number": course_number,
                    "course_title": f"Course {course_number}",  # CEI file doesn't have course titles
                    "department": _extract_department_from_course(course_number),
                    "credit_hours": 3,  # Default, CEI file doesn't have credit hours
                    "institution_id": institution_id,
                }

        # Extract instructor information
        user_data = None
        if "Faculty Name" in row and pd.notna(row["Faculty Name"]):
            instructor_name = str(row["Faculty Name"])
            first_name, last_name = _parse_name(instructor_name)
            email = _generate_email(first_name, last_name)

            user_data = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "role": "instructor",
                "department": course_data.get("department") if course_data else None,
                "institution_id": institution_id,
                "account_status": "imported",  # User created from import, not yet invited
                "active_user": False,  # Will be calculated later based on active courses
            }

        # Extract term information
        term_data = None
        if "effterm_c" in row and pd.notna(row["effterm_c"]):
            effterm_c = str(row["effterm_c"]).strip()
            if effterm_c:
                try:
                    year, season = parse_cei_term(effterm_c)
                    term_data = {
                        "name": f"{season} {year}",
                        "year": int(year),
                        "season": season,
                        "institution_id": institution_id,
                        "is_active": True,
                    }
                except ValueError as e:
                    # Log the error but continue processing
                    print(f"Warning: Could not parse term '{effterm_c}': {e}")

        # Extract offering information (course offering in a specific term)
        offering_data = None
        if course_data and term_data:
            offering_data = {
                "course_number": course_data["course_number"],
                "term_name": term_data["name"],
                "institution_id": institution_id,
                "instructor_email": user_data.get("email") if user_data else None,
                "is_active": True,
            }

        # Extract section information
        section_data = None
        if offering_data and "students" in row and pd.notna(row["students"]):
            try:
                student_count = int(row["students"])
                section_data = {
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
                pass

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


def _generate_email(first_name: str, last_name: str) -> str:
    """Generate email address for instructor (CEI-specific format)."""
    # CEI uses firstname.lastname@cei.edu format
    clean_first = first_name.lower().replace(" ", "").replace(".", "")
    clean_last = last_name.lower().replace(" ", "").replace(".", "")
    return f"{clean_first}.{clean_last}@cei.edu"
