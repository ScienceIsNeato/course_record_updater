"""
CEI Excel Import Adapter

This adapter handles the specific Excel format used by CEI (College of Education and Innovation).
It contains all CEI-specific parsing logic, column mappings, and data transformations.

This keeps CEI-specific logic separate from the generic import system.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from models import validate_course_number

from .file_base_adapter import FileBaseAdapter, FileCompatibilityError

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


class CEIExcelAdapter(FileBaseAdapter):
    """
    Adapter for CEI's Excel format with automatic compatibility detection.

    Handles CEI's specific Excel format with dual format support:
    1. Original format with Faculty Name and effterm_c columns
    2. Test format with email and Term columns

    Automatically detects data types and validates file compatibility.
    """

    SUPPORTED_EXTENSIONS = [".xlsx", ".xls"]
    MAX_FILE_SIZE_MB = 10
    MAX_RECORDS_TO_PROCESS = 5000

    def __init__(self):
        """Initialize CEI Excel adapter with format specifications."""
        super().__init__()

        # Adapter identification
        self.adapter_id = "cei_excel_format_v1"
        self.institution_id = "cei_institution_id"

        # Required columns for original format
        self.original_format_columns = [
            "course",
            "Faculty Name",
            "effterm_c",
            "students",
        ]

        # Required columns for test format
        self.test_format_columns = ["course", "email", "Term", "students"]

        # Optional columns that may be present
        self.optional_columns = ["Course Title", "Department", "Credits"]

    def validate_file_compatibility(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate that the file is compatible with CEI Excel format.

        Checks for:
        1. Excel file format (.xlsx or .xls)
        2. Required column structure (either original or test format)
        3. Valid data patterns in key columns

        Returns:
            Tuple[bool, str]: (is_compatible, message)
        """
        try:
            # Check file extension first
            if not file_path.lower().endswith((".xlsx", ".xls")):
                return False, "Unsupported file extension. Expected .xlsx or .xls"

            # Check if file exists
            import os

            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"

            # Check file size (basic check)
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > self.MAX_FILE_SIZE_MB:
                return (
                    False,
                    f"File too large ({file_size_mb:.1f}MB). Maximum allowed: {self.MAX_FILE_SIZE_MB}MB",
                )

            # Read Excel file to check structure
            try:
                df = pd.read_excel(file_path, nrows=10)  # Sample first 10 rows
            except Exception as e:
                return False, f"Cannot read Excel file: {str(e)}"

            if df.empty:
                return False, "Excel file is empty"

            # Check for either format structure
            has_original_format = all(
                col in df.columns for col in self.original_format_columns
            )
            has_test_format = all(col in df.columns for col in self.test_format_columns)

            if not (has_original_format or has_test_format):
                missing_original = [
                    col for col in self.original_format_columns if col not in df.columns
                ]
                missing_test = [
                    col for col in self.test_format_columns if col not in df.columns
                ]

                return False, (
                    f"File doesn't match CEI format. "
                    f"Missing for original format: {missing_original}. "
                    f"Missing for test format: {missing_test}."
                )

            # Validate data patterns in key columns
            validation_errors = []

            # Check course column
            if "course" in df.columns:
                sample_courses = df["course"].dropna().head(3)
                invalid_courses = [
                    course
                    for course in sample_courses
                    if not validate_course_number(str(course))
                ]
                if (
                    len(invalid_courses) == len(sample_courses)
                    and len(sample_courses) > 0
                ):
                    validation_errors.append("No valid course numbers found")

            # Check term format if using original format
            if has_original_format and "effterm_c" in df.columns:
                sample_terms = df["effterm_c"].dropna().head(3)
                invalid_terms = [
                    term
                    for term in sample_terms
                    if not validate_cei_term_name(str(term))
                ]
                if len(invalid_terms) == len(sample_terms) and len(sample_terms) > 0:
                    validation_errors.append(
                        "No valid term codes found (expected format: FA2024, SP2025)"
                    )

            # Check student count column
            if "students" in df.columns:
                sample_students = df["students"].dropna().head(3)
                try:
                    numeric_counts = [int(x) for x in sample_students if pd.notna(x)]
                    if not numeric_counts and len(sample_students) > 0:
                        validation_errors.append(
                            "Student count column contains no valid numbers"
                        )
                except (ValueError, TypeError):
                    validation_errors.append(
                        "Student count column contains invalid data"
                    )

            if validation_errors:
                return False, f"Data validation failed: {'; '.join(validation_errors)}"

            # Determine format and provide success message
            format_type = "original" if has_original_format else "test"
            record_count = len(df)

            return True, (
                f"File compatible with CEI Excel format ({format_type}). "
                f"Found {record_count} sample records."
            )

        except Exception as e:
            return False, f"Error validating file: {str(e)}"

    def detect_data_types(self, file_path: str) -> List[str]:
        """
        Automatically detect what types of data are present in the file.

        CEI Excel files typically contain:
        - courses: Course information
        - faculty: Instructor information
        - terms: Academic term data
        - sections: Course section details
        """
        try:
            df = pd.read_excel(file_path, nrows=50)  # Sample for analysis
            detected_types = []

            # Check for course data
            if "course" in df.columns and not df["course"].isna().all():
                detected_types.append("courses")

            # Check for faculty data
            if (
                FACULTY_NAME_COLUMN in df.columns
                and not df[FACULTY_NAME_COLUMN].isna().all()
            ) or ("email" in df.columns and not df["email"].isna().all()):
                detected_types.append("faculty")

            # Check for term data
            if ("effterm_c" in df.columns and not df["effterm_c"].isna().all()) or (
                "Term" in df.columns and not df["Term"].isna().all()
            ):
                detected_types.append("terms")

            # Check for section data (student counts indicate sections)
            if "students" in df.columns and not df["students"].isna().all():
                detected_types.append("sections")

            return detected_types

        except Exception:
            # If we can't read the file, return empty list
            return []

    def get_adapter_info(self) -> Dict[str, Any]:
        """
        Return metadata about this adapter for UI display and filtering.
        """
        return {
            "id": "cei_excel_format_v1",
            "name": "CEI Excel Format v1.2",
            "description": "Imports course, faculty, and section data from CEI's Excel exports. Supports both original format (Faculty Name, effterm_c) and test format (email, Term).",
            "supported_formats": [".xlsx", ".xls"],
            "institution_id": "cei_institution_id",
            "data_types": ["courses", "faculty", "terms", "sections"],
            "version": "1.2.0",
            "created_by": "System Developer",
            "last_updated": "2024-09-25",
            "file_size_limit": "10MB",
            "max_records": 5000,
            "format_variants": [
                "Original: course, Faculty Name, effterm_c, students",
                "Test: course, email, Term, students",
            ],
        }

    def get_file_size_limit(self) -> int:
        """Get the file size limit in bytes for CEI files."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    def get_max_records(self) -> int:
        """Get the maximum number of records this adapter can process."""
        return self.MAX_RECORDS_TO_PROCESS

    def parse_file(
        self, file_path: str, options: Dict[str, Any]
    ) -> Dict[str, List[Dict]]:
        """
        Parse CEI Excel file into structured data ready for database import.

        Args:
            file_path: Path to the Excel file
            options: Import options including institution_id

        Returns:
            Dict mapping data types to lists of records
        """
        try:
            # Validate file first
            is_compatible, compatibility_message = self.validate_file_compatibility(
                file_path
            )
            if not is_compatible:
                raise FileCompatibilityError(
                    f"File incompatible: {compatibility_message}"
                )

            # Get institution ID from options
            institution_id = options.get("institution_id")
            if not institution_id:
                raise ValueError("institution_id is required in options")

            # Read the Excel file
            try:
                df = pd.read_excel(file_path)
            except Exception as e:
                raise FileCompatibilityError(f"Cannot read Excel file: {str(e)}") from e

            if df.empty:
                raise FileCompatibilityError("Excel file is empty")

            # Initialize result structure
            result: Dict[str, List[Dict]] = {
                "courses": [],
                "users": [],  # Note: using 'users' not 'faculty' to match database service
                "terms": [],
                "offerings": [],
                "sections": [],
            }

            # Process each row using existing parsing logic
            for _, row in df.iterrows():
                try:
                    # Use existing parse_cei_excel_row function
                    entities = parse_cei_excel_row(row, institution_id)

                    # Add timestamp to all entities
                    timestamp = datetime.now().isoformat()

                    # Collect entities by type
                    if entities.get("course"):
                        course = entities["course"].copy()
                        course["created_at"] = timestamp
                        result["courses"].append(course)

                    if entities.get("user"):
                        user = entities["user"].copy()
                        user["created_at"] = timestamp
                        result["users"].append(user)

                    if entities.get("term"):
                        term = entities["term"].copy()
                        term["created_at"] = timestamp
                        result["terms"].append(term)

                    if entities.get("offering"):
                        offering = entities["offering"].copy()
                        offering["created_at"] = timestamp
                        result["offerings"].append(offering)

                    if entities.get("section"):
                        section = entities["section"].copy()
                        section["created_at"] = timestamp
                        result["sections"].append(section)

                except Exception as e:
                    # Log error but continue processing other rows
                    print(f"Warning: Error processing row {_}: {str(e)}")
                    continue

            # Remove duplicates from each data type
            result = self._deduplicate_results(result)

            # Validate we have some data
            total_records = sum(len(records) for records in result.values())
            if total_records == 0:
                raise FileCompatibilityError("No valid records found in file")

            return result

        except FileCompatibilityError:
            raise
        except ValueError as e:
            # Re-raise ValueError as-is (for missing institution_id, etc.)
            raise
        except Exception as e:
            raise FileCompatibilityError(f"Error parsing file: {str(e)}") from e

    def _deduplicate_results(
        self, result: Dict[str, List[Dict]]
    ) -> Dict[str, List[Dict]]:
        """Remove duplicate records from parsed results."""

        # Define key fields for each data type to identify duplicates
        key_fields = {
            "courses": ["course_number", "institution_id"],
            "users": ["email", "first_name", "last_name", "institution_id"],
            "terms": ["name", "year", "institution_id"],
            "offerings": ["course_number", "term_name", "institution_id"],
            "sections": [
                "course_number",
                "term_name",
                "section_number",
                "institution_id",
            ],
        }

        for data_type, records in result.items():
            if not records:
                continue

            keys = key_fields.get(data_type, ["id"])
            seen = set()
            unique_records = []

            for record in records:
                # Create key tuple from specified fields
                key_values = []
                for field in keys:
                    value = record.get(field)
                    # Handle None values and convert to string for hashing
                    key_values.append(str(value) if value is not None else "")

                key = tuple(key_values)

                if key not in seen:
                    seen.add(key)
                    unique_records.append(record)

            result[data_type] = unique_records

        return result
