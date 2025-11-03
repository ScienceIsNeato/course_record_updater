"""
Data Models for Course Management System

This module defines the data structures for the expanded relational model
that supports multi-institutional enterprise requirements.
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# Import password service for secure password handling
from password_service import hash_password, validate_password_strength

# NOTE: User roles and permissions are now managed in auth_service.py
# This provides centralized role-based access control with the UserRole enum
# and ROLE_PERMISSIONS mapping.

# DEPRECATED: Old ROLES dictionary - kept for backward compatibility during transition
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
            "view_program_sections",
            "assign_instructors",
            "manage_program_courses",
            "manage_terms",
            "send_notifications",
            "view_program_reports",
            "manage_outcomes",
            "export_program_data",
            "invite_instructors",
            "manage_course_program_associations",
        ],
    },
    "institution_admin": {
        "name": "Institution Administrator",
        "permissions": [
            "view_all_sections",
            "assign_instructors",
            "manage_courses",
            "manage_programs",
            "create_programs",
            "manage_terms",
            "send_notifications",
            "view_reports",
            "manage_outcomes",
            "export_institution_data",
            "invite_users",
            "manage_program_admins",
            "manage_institution_settings",
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
            "manage_institutions",
            "impersonate_users",
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

# Authentication Status Enums
ACCOUNT_STATUSES = [
    "pending",  # User record created, awaiting email verification
    "active",  # User has verified email and can log in
    "suspended",  # Account temporarily disabled
    "locked",  # Account locked due to failed login attempts
]

INVITATION_STATUSES = [
    "pending",  # Invitation sent, not yet accepted
    "accepted",  # Invitation accepted, user registered
    "expired",  # Invitation expired without acceptance
    "cancelled",  # Invitation cancelled by inviter
]


class DataModel:
    """Base class for all data models with common functionality"""

    @staticmethod
    def generate_id() -> str:
        """Generate a new UUID for entity IDs"""
        return str(uuid.uuid4())

    @staticmethod
    def current_timestamp():
        """Get current timestamp for persistence operations"""
        return datetime.now(timezone.utc)

    @staticmethod
    def create_password_hash(password: str) -> str:
        """
        Create a secure password hash using bcrypt

        Args:
            password: Plain text password

        Returns:
            Hashed password string

        Raises:
            PasswordValidationError: If password doesn't meet requirements
        """
        return hash_password(password)

    @staticmethod
    def validate_password(password: str) -> None:
        """
        Validate password meets strength requirements

        Args:
            password: Password to validate

        Raises:
            PasswordValidationError: If password doesn't meet requirements
        """
        validate_password_strength(password)

    @staticmethod
    def generate_password_reset_token() -> str:
        """
        Generate a secure password reset token

        Returns:
            Cryptographically secure random token
        """
        from password_service import generate_reset_token

        return generate_reset_token()

    @staticmethod
    def create_password_reset_data(user_id: str, email: str) -> Dict:
        """
        Create password reset token data with expiry

        Args:
            user_id: User ID for the reset request
            email: User email for verification

        Returns:
            Dictionary with token data
        """
        from password_service import PasswordService

        return PasswordService.create_reset_token_data(user_id, email)


class User(DataModel):
    """Enhanced User model with full authentication support"""

    @staticmethod
    def create_schema(
        email: str,
        first_name: str,
        last_name: str,
        role: str = "instructor",
        institution_id: Optional[str] = None,
        password_hash: Optional[str] = None,
        account_status: str = "pending",
        program_ids: Optional[List[str]] = None,
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new user record schema with enhanced authentication fields"""

        # Import here to avoid circular imports
        from auth_service import UserRole

        valid_roles = [r.value for r in UserRole]
        if role not in valid_roles:
            raise ValueError(f"Invalid role: {role}. Must be one of {valid_roles}")

        if account_status not in ACCOUNT_STATUSES:
            raise ValueError(
                f"Invalid account_status: {account_status}. Must be one of {ACCOUNT_STATUSES}"
            )

        # Validate required fields based on role
        if role != "site_admin" and not institution_id:
            raise ValueError(
                "institution_id is required for all roles except site_admin"
            )

        return {
            # Identity
            "user_id": User.generate_id(),
            "email": email.lower().strip(),
            "password_hash": password_hash,
            # Profile
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "display_name": display_name.strip() if display_name else None,
            # Authentication State
            "account_status": account_status,
            "email_verified": False,
            "email_verification_token": None,
            "email_verification_sent_at": None,
            # Password Reset
            "password_reset_token": None,
            "password_reset_expires_at": None,
            # Role & Institution
            "role": role,
            "institution_id": institution_id,
            "program_ids": program_ids
            or [],  # Programs user has access to (for program_admin)
            # Activity Tracking
            "created_at": User.current_timestamp(),
            "updated_at": User.current_timestamp(),
            "last_login_at": None,
            "login_attempts": 0,
            "locked_until": None,
            # Invitation Tracking
            "invited_by": None,  # user_id of inviter
            "invited_at": None,
            "registration_completed_at": None,
            # Future OAuth Support
            "oauth_provider": None,
            "oauth_id": None,
        }

    @staticmethod
    def get_permissions(role: str) -> List[str]:
        """Get permissions for a given role using new authorization system"""
        # Import here to avoid circular imports
        from auth_service import ROLE_PERMISSIONS

        return ROLE_PERMISSIONS.get(role, [])

    @staticmethod
    def full_name(first_name: str, last_name: str) -> str:
        """Generate full name from first and last name"""
        return f"{first_name} {last_name}"

    @staticmethod
    def is_active(account_status: str, locked_until: Optional[datetime] = None) -> bool:
        """
        Check if user account is active and can log in

        Args:
            account_status: User's account status
            locked_until: Timestamp until which account is locked

        Returns:
            True if user can log in
        """
        if account_status != "active":
            return False

        if locked_until and locked_until > datetime.now(timezone.utc):
            return False

        return True

    @staticmethod
    def generate_verification_token() -> str:
        """Generate a secure email verification token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_reset_token() -> str:
        """Generate a secure password reset token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def calculate_active_status(account_status: str, has_active_courses: bool) -> bool:
        """
        Calculate if a user should be considered 'active' for billing purposes.

        Active user criteria:
        - A) Account status is 'active' (they've completed registration)
        - B) They are associated with active courses (current or upcoming terms)

        Args:
            account_status: User's account status
            has_active_courses: Whether user has courses in current/upcoming terms

        Returns:
            True if user should count against billing headcount
        """
        return account_status == "active" and has_active_courses


class UserInvitation(DataModel):
    """Track pending user invitations"""

    @staticmethod
    def create_schema(
        email: str,
        role: str,
        institution_id: str,
        invited_by: str,
        personal_message: Optional[str] = None,
        expires_days: int = 7,
    ) -> Dict[str, Any]:
        """Create a new user invitation record schema"""

        # Import here to avoid circular imports
        from auth_service import UserRole

        valid_roles = [r.value for r in UserRole]
        if role not in valid_roles:
            raise ValueError(f"Invalid role: {role}. Must be one of {valid_roles}")

        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)

        return {
            "invitation_id": UserInvitation.generate_id(),
            "email": email.lower().strip(),
            "role": role,
            "institution_id": institution_id,
            # Invitation Management
            "token": UserInvitation.generate_invitation_token(),
            "invited_by": invited_by,
            "invited_at": UserInvitation.current_timestamp(),
            "expires_at": expires_at,
            # Status Tracking
            "status": "pending",
            "accepted_at": None,
            # Personal Message
            "personal_message": personal_message.strip() if personal_message else None,
        }

    @staticmethod
    def generate_invitation_token() -> str:
        """Generate a secure invitation token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def is_expired(expires_at: datetime) -> bool:
        """Check if invitation has expired"""
        return datetime.now(timezone.utc) > expires_at

    @staticmethod
    def can_accept(status: str, expires_at: datetime) -> bool:
        """Check if invitation can still be accepted"""
        return status == "pending" and not UserInvitation.is_expired(expires_at)


class Institution(DataModel):
    """Enhanced Institution model with auth fields"""

    @staticmethod
    def create_schema(
        name: str,
        short_name: str,
        created_by: str,
        admin_email: str,
        website_url: Optional[str] = None,
        allow_self_registration: bool = False,
        require_email_verification: bool = True,
    ) -> Dict[str, Any]:
        """Create a new institution record schema"""

        return {
            "institution_id": Institution.generate_id(),
            "name": name.strip(),
            "short_name": short_name.strip().upper(),
            "website_url": website_url.strip() if website_url else None,
            # Auth fields
            "created_by": created_by,
            "admin_email": admin_email.lower().strip(),
            # Settings
            "allow_self_registration": allow_self_registration,
            "require_email_verification": require_email_verification,
            # Activity
            "created_at": Institution.current_timestamp(),
            "updated_at": Institution.current_timestamp(),
            "is_active": True,
        }


class Program(DataModel):
    """Academic Program/Department within an Institution"""

    @staticmethod
    def create_schema(
        name: str,
        short_name: str,
        institution_id: str,
        created_by: str,
        description: Optional[str] = None,
        is_default: bool = False,
        program_admins: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new program record schema"""

        return {
            # Identity
            "program_id": Program.generate_id(),
            "name": name.strip(),
            "short_name": short_name.strip().upper(),
            "description": description.strip() if description else None,
            # Hierarchy
            "institution_id": institution_id,
            # Management
            "created_by": created_by,
            "program_admins": program_admins or [],  # user_ids of program admins
            # Settings
            "is_default": is_default,  # True for "Unclassified" default program
            # Activity
            "created_at": Program.current_timestamp(),
            "updated_at": Program.current_timestamp(),
            "is_active": True,
        }

    @staticmethod
    def admin_count(program_admins: List[str]) -> int:
        """Get count of program administrators"""
        return len(program_admins)


class Course(DataModel):
    """Course entity - represents the platonic form of a course"""

    @staticmethod
    def create_schema(
        course_number: str,
        course_title: str,
        department: str,
        institution_id: str,
        credit_hours: int = 3,
        program_ids: Optional[List[str]] = None,
        active: bool = True,
    ) -> Dict[str, Any]:
        """Create a new course record schema with program associations"""

        return {
            "course_id": Course.generate_id(),
            "course_number": course_number.strip().upper(),
            "course_title": course_title.strip(),
            "department": department.strip(),
            "credit_hours": credit_hours,
            "institution_id": institution_id,
            "program_ids": program_ids or [],  # Courses can belong to multiple programs
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
        """
        Create a new course section record schema

        Args:
            offering_id: ID of the course offering this section belongs to
            section_number: Section identifier (default: "001")
            instructor_id: Optional ID of assigned instructor
            enrollment: Number of enrolled students (was previously 'num_students')
            status: Section status from SECTION_STATUSES

        Returns:
            Dictionary containing the course section schema

        Breaking Change Note:
            The 'num_students' parameter has been renamed to 'enrollment' for consistency
            with the CourseOffering model's total_enrollment field.
        """

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
            # CLO Assessment Fields (corrected from demo feedback)
            "students_took": None,  # How many students took THIS CLO assessment
            "students_passed": None,  # How many students passed THIS CLO assessment
            "assessment_tool": None,  # Brief description: "Test #3", "Lab 2", etc. (40-50 chars)
            # Deprecated: assessment_data JSON removed, narrative removed (belongs at course level)
            "active": active,
            "created_at": CourseOutcome.current_timestamp(),
            "last_modified": CourseOutcome.current_timestamp(),
        }

    @staticmethod
    def update_assessment_data(
        students_took: Optional[int] = None,
        students_passed: Optional[int] = None,
        assessment_tool: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create assessment data update (corrected field names from demo feedback)"""

        # Validate assessment_tool length if provided
        if assessment_tool and len(assessment_tool) > 50:
            raise ValueError(
                f"assessment_tool must be 50 characters or less (got {len(assessment_tool)})"
            )

        # Calculate percentage if both counts provided
        percentage_meeting = None
        if students_took and students_passed:
            percentage_meeting = round((students_passed / students_took) * 100, 2)

        return {
            "students_took": students_took,
            "students_passed": students_passed,
            "assessment_tool": assessment_tool.strip() if assessment_tool else None,
            "percentage_meeting": percentage_meeting,  # Calculated field for convenience
            "last_modified": CourseOutcome.current_timestamp(),
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
    """
    Validate term name format - supports standard space-separated format

    Standard format: "2024 Fall", "2024 Spring", "2024 Summer", "2024 Winter"
    For institution-specific formats, use adapter-specific validation.
    """
    # Handle space-separated format: "2024 Fall"
    parts = term_name.split()
    if len(parts) == 2 and parts[0].isdigit() and len(parts[0]) == 4:
        season = parts[1].lower()
        return season in ["fall", "spring", "summer", "winter"]

    return False


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
    # Core Models
    "User",
    "UserInvitation",
    "Institution",
    "Program",
    "Course",
    "Term",
    "CourseOffering",
    "CourseSection",
    "CourseOutcome",
    # Constants
    "ROLES",  # DEPRECATED: Use auth_service.UserRole instead
    "SECTION_STATUSES",
    "ASSESSMENT_STATUSES",
    "ACCOUNT_STATUSES",
    "INVITATION_STATUSES",
    # Validation Functions
    "validate_email",
    "validate_course_number",
    "validate_term_name",
    "format_term_name",
]
