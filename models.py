"""
Data Models for CEI Course Management System

This module defines the data structures for the expanded relational model
that supports CEI's enterprise requirements while maintaining backward
compatibility with the existing flat course model.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# User Roles and Permissions
ROLES = {
    "instructor": {
        "name": "Instructor",
        "permissions": [
            "view_own_sections",
            "edit_own_assessments",
            "submit_assessments",
            "view_own_courses",
            "export_own_data",
        ],
    },
    "program_admin": {
        "name": "Program Administrator",
        "permissions": [
            "view_all_sections",
            "assign_instructors",
            "manage_courses",
            "manage_terms",
            "send_notifications",
            "view_reports",
            "manage_outcomes",
            "export_program_data",
        ],
    },
    "site_admin": {
        "name": "Site Administrator",
        "permissions": [
            "manage_users",
            "manage_system_settings",
            "import_data",
            "full_access",
            "manage_environments",
            "view_audit_logs",
        ],
    },
}

# Status Enums
SECTION_STATUSES = [
    "assigned",  # Instructor assigned, not yet started
    "in_progress",  # Term active, assessments in progress
    "completed",  # All assessments submitted
    "overdue",  # Past due date, incomplete
    "archived",  # Term completed, data archived
]

ASSESSMENT_STATUSES = [
    "not_started",  # No assessment data entered
    "in_progress",  # Partial data entered
    "completed",  # All required fields completed
    "submitted",  # Submitted for review
    "approved",  # Approved by program admin
]


class DataModel:
    """Base class for all data models with common functionality"""

    @staticmethod
    def generate_id() -> str:
        """Generate a new UUID for entity IDs"""
        return str(uuid.uuid4())

    @staticmethod
    def current_timestamp():
        """Get current timestamp for Firestore"""
        # Will be replaced with firestore.SERVER_TIMESTAMP in actual usage
        return datetime.now(timezone.utc)


class User(DataModel):
    """User entity for authentication and role management"""

    @staticmethod
    def create_schema(
        email: str,
        first_name: str,
        last_name: str,
        role: str = "instructor",
        department: Optional[str] = None,
        active: bool = True,
        institution_id: Optional[str] = None,
        account_status: str = "imported",
    ) -> Dict[str, Any]:
        """Create a new user record schema"""

        if role not in ROLES:
            raise ValueError(
                f"Invalid role: {role}. Must be one of {list(ROLES.keys())}"
            )

        return {
            "user_id": User.generate_id(),
            "email": email.lower().strip(),
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "role": role,
            "department": department,
            "institution_id": institution_id,
            "active": active,
            "account_status": account_status,  # imported, invited, active
            "active_user": False,  # Derived field for billing (see calculate_active_status)
            "invite_sent_at": None,
            "invite_accepted_at": None,
            "created_at": User.current_timestamp(),
            "last_login": None,
            "last_modified": User.current_timestamp(),
        }

    @staticmethod
    def get_permissions(role: str) -> List[str]:
        """Get permissions for a given role"""
        return list(ROLES.get(role, {}).get("permissions", []))

    @staticmethod
    def calculate_active_status(account_status: str, has_active_courses: bool) -> bool:
        """
        Calculate if a user should be considered 'active' for billing purposes.

        Active user criteria:
        - A) Account status is 'active' (they've accepted invite and created account)
        - B) They are associated with active courses (current or upcoming terms)

        Args:
            account_status: User's account status (imported, invited, active)
            has_active_courses: Whether user has courses in current/upcoming terms

        Returns:
            True if user should count against billing headcount
        """
        return account_status == "active" and has_active_courses


class Course(DataModel):
    """Course entity - represents the platonic form of a course"""

    @staticmethod
    def create_schema(
        course_number: str,
        course_title: str,
        department: str,
        credit_hours: int = 3,
        active: bool = True,
    ) -> Dict[str, Any]:
        """Create a new course record schema"""

        return {
            "course_id": Course.generate_id(),
            "course_number": course_number.strip().upper(),
            "course_title": course_title.strip(),
            "department": department.strip(),
            "credit_hours": credit_hours,
            "active": active,
            "created_at": Course.current_timestamp(),
            "last_modified": Course.current_timestamp(),
        }


class Term(DataModel):
    """Term entity - represents academic terms/semesters"""

    @staticmethod
    def create_schema(
        name: str,
        start_date: str,  # YYYY-MM-DD format
        end_date: str,  # YYYY-MM-DD format
        assessment_due_date: str,  # YYYY-MM-DD format
        active: bool = True,
    ) -> Dict[str, Any]:
        """Create a new term record schema"""

        return {
            "term_id": Term.generate_id(),
            "name": name.strip(),
            "start_date": start_date,
            "end_date": end_date,
            "assessment_due_date": assessment_due_date,
            "active": active,
            "created_at": Term.current_timestamp(),
            "last_modified": Term.current_timestamp(),
        }


class CourseOffering(DataModel):
    """CourseOffering entity - represents a course offered in a specific term"""

    @staticmethod
    def create_schema(
        course_id: str,
        term_id: str,
        institution_id: str,
        status: str = "active",
        capacity: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a new course offering record schema"""

        return {
            "offering_id": CourseOffering.generate_id(),
            "course_id": course_id,
            "term_id": term_id,
            "institution_id": institution_id,
            "status": status,
            "capacity": capacity,
            "total_enrollment": 0,  # Will be calculated from sections
            "section_count": 0,  # Will be calculated from sections
            "created_at": CourseOffering.current_timestamp(),
            "last_modified": CourseOffering.current_timestamp(),
        }


class CourseSection(DataModel):
    """CourseSection entity - represents a specific section of a course offering"""

    @staticmethod
    def create_schema(
        offering_id: str,
        section_number: str = "001",
        instructor_id: Optional[str] = None,
        enrollment: Optional[int] = None,
        status: str = "assigned",
    ) -> Dict[str, Any]:
        """Create a new course section record schema"""

        if status not in SECTION_STATUSES:
            raise ValueError(
                f"Invalid status: {status}. Must be one of {SECTION_STATUSES}"
            )

        return {
            "section_id": CourseSection.generate_id(),
            "offering_id": offering_id,
            "instructor_id": instructor_id,
            "section_number": section_number.strip(),
            "enrollment": enrollment,
            "status": status,
            "grade_distribution": {},
            "assigned_date": (
                CourseSection.current_timestamp() if instructor_id else None
            ),
            "completed_date": None,
            "created_at": CourseSection.current_timestamp(),
            "last_modified": CourseSection.current_timestamp(),
        }

    # Grade distribution functionality removed per requirements


class CourseOutcome(DataModel):
    """CourseOutcome entity - represents CLOs and their assessments"""

    @staticmethod
    def create_schema(
        course_id: str,
        clo_number: str,
        description: str,
        assessment_method: Optional[str] = None,
        active: bool = True,
    ) -> Dict[str, Any]:
        """Create a new course outcome record schema"""

        return {
            "outcome_id": CourseOutcome.generate_id(),
            "course_id": course_id,
            "clo_number": clo_number.strip(),
            "description": description.strip(),
            "assessment_method": (
                assessment_method.strip() if assessment_method else None
            ),
            "assessment_data": {
                "students_assessed": None,
                "students_meeting": None,
                "percentage_meeting": None,
                "assessment_status": "not_started",
            },
            "narrative": None,
            "active": active,
            "created_at": CourseOutcome.current_timestamp(),
            "last_modified": CourseOutcome.current_timestamp(),
        }

    @staticmethod
    def update_assessment_data(
        students_assessed: Optional[int] = None,
        students_meeting: Optional[int] = None,
        percentage_meeting: Optional[float] = None,
        assessment_status: str = "in_progress",
        narrative: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create assessment data update"""

        if assessment_status not in ASSESSMENT_STATUSES:
            raise ValueError(
                f"Invalid assessment_status: {assessment_status}. Must be one of {ASSESSMENT_STATUSES}"
            )

        # Calculate percentage if both counts provided
        if students_assessed and students_meeting and not percentage_meeting:
            percentage_meeting = round((students_meeting / students_assessed) * 100, 2)

        return {
            "assessment_data": {
                "students_assessed": students_assessed,
                "students_meeting": students_meeting,
                "percentage_meeting": percentage_meeting,
                "assessment_status": assessment_status,
            },
            "narrative": narrative.strip() if narrative else None,
            "last_modified": CourseOutcome.current_timestamp(),
        }


class LegacyCourse(DataModel):
    """Legacy course model for backward compatibility"""

    @staticmethod
    def from_flat_record(course_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert current flat course record to legacy format"""
        return {
            "course_number": course_data.get("course_number"),
            "course_title": course_data.get("course_title"),
            "instructor_name": course_data.get("instructor_name"),
            "term": course_data.get("term"),
            "num_students": course_data.get("num_students"),
            "grade_a": course_data.get("grade_a"),
            "grade_b": course_data.get("grade_b"),
            "grade_c": course_data.get("grade_c"),
            "grade_d": course_data.get("grade_d"),
            "grade_f": course_data.get("grade_f"),
            "timestamp": course_data.get("timestamp"),
        }

    @staticmethod
    def to_relational_entities(
        course_data: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        """Convert legacy flat course to new relational entities"""

        # This would be used during migration
        # Returns dict with keys: 'course', 'term', 'section', 'user'

        course = Course.create_schema(
            course_number=course_data["course_number"],
            course_title=course_data["course_title"],
            department="Unknown",  # Would need to be determined during migration
        )

        term = Term.create_schema(
            name=course_data["term"],
            start_date="2024-01-01",  # Would need actual dates
            end_date="2024-05-01",
            assessment_due_date="2024-05-15",
        )

        user = User.create_schema(
            email=f"{course_data['instructor_name'].lower().replace(' ', '.')}@cei.edu",
            first_name=course_data["instructor_name"].split()[0],
            last_name=" ".join(course_data["instructor_name"].split()[1:]),
            role="instructor",
        )

        # Create a course offering (bridge between course and term)
        offering = CourseOffering.create_schema(
            course_id=course["course_id"],
            term_id=term["term_id"],
            institution_id="cei_default",  # Legacy migration assumes CEI
        )

        section = CourseSection.create_schema(
            offering_id=offering["offering_id"],
            instructor_id=user["user_id"],
            enrollment=course_data.get("num_students"),
        )

        # Grade distribution functionality removed per requirements
        section["grade_distribution"] = {}

        return {
            "course": course,
            "term": term,
            "offering": offering,
            "user": user,
            "section": section,
        }


# Validation functions
def validate_email(email: str) -> bool:
    """Basic email validation"""
    if not email or "@" not in email:
        return False

    parts = email.split("@")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return False

    # Check that domain part has at least one dot
    return "." in parts[1] and parts[1].count(".") >= 1


def validate_course_number(course_number: str) -> bool:
    """Validate course number format (e.g., ACC-201, NURS-150)"""
    parts = course_number.split("-")
    return len(parts) == 2 and parts[0].isalpha() and parts[1].isdigit()


def validate_term_name(term_name: str) -> bool:
    """Validate term name format (e.g., 2024 Fall, 2024 Spring, 2024FA, 2024SP)"""
    # Handle space-separated format: "2024 Fall"
    parts = term_name.split()
    if len(parts) == 2 and parts[0].isdigit() and len(parts[0]) == 4:
        return True

    # Handle CEI abbreviated format: "2024FA", "2024SP", "2024SU", "2024WI"
    if len(term_name) == 6 and term_name[:4].isdigit():
        season = term_name[4:].upper()
        return season in ["FA", "SP", "SU", "WI"]  # Fall, Spring, Summer, Winter

    return False


def parse_cei_term(effterm_c: str) -> Tuple[str, str]:
    """
    Parse CEI's effterm_c format into year and season.

    Args:
        effterm_c: Term code like '2024FA', '2024SP', etc.

    Returns:
        Tuple of (year, season) where season is the full name

    Example:
        parse_cei_term('2024FA') -> ('2024', 'Fall')
    """
    if not effterm_c or len(effterm_c) != 6:
        raise ValueError(f"Invalid effterm_c format: {effterm_c}")

    year = effterm_c[:4]
    season_code = effterm_c[4:].upper()

    season_map = {"FA": "Fall", "SP": "Spring", "SU": "Summer", "WI": "Winter"}

    if season_code not in season_map:
        raise ValueError(f"Invalid season code: {season_code}")

    return year, season_map[season_code]


def format_term_name(year: str, season: str) -> str:
    """
    Format year and season into standard term name.

    Args:
        year: 4-digit year string
        season: Full season name (Fall, Spring, Summer, Winter)

    Returns:
        Formatted term name like '2024 Fall'
    """
    return f"{year} {season}"


# Export all model classes and constants
__all__ = [
    "User",
    "Course",
    "Term",
    "CourseOffering",
    "CourseSection",
    "CourseOutcome",
    "LegacyCourse",
    "ROLES",
    "SECTION_STATUSES",
    "ASSESSMENT_STATUSES",
    "validate_email",
    "validate_course_number",
    "validate_term_name",
    "parse_cei_term",
    "format_term_name",
]
