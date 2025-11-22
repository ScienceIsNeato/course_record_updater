"""Database service facade backed by SQLite implementation."""

from __future__ import annotations

import logging
from contextlib import nullcontext
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from constants import (
    COURSE_OFFERINGS_COLLECTION,
    COURSE_OUTCOMES_COLLECTION,
    COURSE_SECTIONS_COLLECTION,
    COURSES_COLLECTION,
    DB_CLIENT_NOT_AVAILABLE_MSG,
    DEFAULT_INSTITUTION_TIMEZONE,
    INSTITUTIONS_COLLECTION,
    TERMS_COLLECTION,
    USERS_COLLECTION,
)
from database_factory import get_database_service, refresh_database_service
from models_sql import Base

logger = logging.getLogger(__name__)

# Initialize database service singleton
_db_service = get_database_service()

# Database service alias for backwards compatibility
db = _db_service


def refresh_connection():
    """Reinitialize the database service (primarily for tests)."""
    global _db_service, db
    _db_service = refresh_database_service()
    db = _db_service
    return _db_service


def reset_database() -> bool:
    """Drop and recreate all tables for a clean database state (SQLite only)."""
    if hasattr(_db_service, "sqlite"):
        engine = _db_service.sqlite.engine
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        return True
    logger.error("[DB Service] reset_database unsupported for current backend")
    return False


def db_operation_timeout():
    """
    Legacy no-op helper retained for API compatibility.

    Returns a null context manager (does nothing).
    This exists to avoid breaking existing code that calls this function,
    but the timeout functionality is handled internally by database implementations.
    """
    return nullcontext()


def check_db_connection() -> bool:
    """Simple connectivity check for the active database service."""
    try:
        _db_service.get_all_institutions()
        return True
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("[DB Service] Database connection check failed: %s", exc)
        return False


def sanitize_for_logging(value: Any, max_length: int = 100) -> str:
    """Sanitize user input for safe logging to prevent log injection attacks."""
    if value is None:
        return "None"
    text = str(value)[:max_length]
    sanitized = (
        text.replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
        .replace("\x00", "\\x00")
        .replace("\x1b", "\\x1b")
    )
    return "".join(
        char if ord(char) >= 32 or char == "\t" else f"\\x{ord(char):02x}"
        for char in sanitized
    )


# ---------------------------------------------------------------------------
# Institution operations
# ---------------------------------------------------------------------------


def create_institution(institution_data: Dict[str, Any]) -> Optional[str]:
    return _db_service.create_institution(institution_data)


def get_institution_by_id(institution_id: str) -> Optional[Dict[str, Any]]:
    return _db_service.get_institution_by_id(institution_id)


def get_all_institutions() -> List[Dict[str, Any]]:
    return _db_service.get_all_institutions()


def create_default_mocku_institution() -> Optional[str]:
    return _db_service.create_default_mocku_institution()


def create_new_institution(
    institution_data: Dict[str, Any], admin_user_data: Dict[str, Any]
) -> Optional[Tuple[str, str]]:
    return _db_service.create_new_institution(institution_data, admin_user_data)


def create_new_institution_simple(
    name: str, short_name: str, active: bool = True
) -> Optional[str]:
    """Create a new institution without creating an admin user (site admin workflow)"""
    return _db_service.create_new_institution_simple(name, short_name, active)


def get_institution_instructor_count(institution_id: str) -> int:
    return _db_service.get_institution_instructor_count(institution_id)


def get_institution_by_short_name(short_name: str) -> Optional[Dict[str, Any]]:
    return _db_service.get_institution_by_short_name(short_name)


def update_institution(institution_id: str, institution_data: Dict[str, Any]) -> bool:
    return _db_service.update_institution(institution_id, institution_data)


def delete_institution(institution_id: str) -> bool:
    return _db_service.delete_institution(institution_id)


# ---------------------------------------------------------------------------
# User operations
# ---------------------------------------------------------------------------


def create_user(user_data: Dict[str, Any]) -> Optional[str]:
    return _db_service.create_user(user_data)


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    return _db_service.get_user_by_email(email)


def get_user_by_reset_token(reset_token: str) -> Optional[Dict[str, Any]]:
    return _db_service.get_user_by_reset_token(reset_token)


def get_all_users(institution_id: str) -> List[Dict[str, Any]]:
    return _db_service.get_all_users(institution_id)


def get_users_by_role(role: str) -> List[Dict[str, Any]]:
    return _db_service.get_users_by_role(role)


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    return _db_service.get_user_by_id(user_id)


def update_user(user_id: str, user_data: Dict[str, Any]) -> bool:
    return _db_service.update_user(user_id, user_data)


def update_user_active_status(user_id: str, active_user: bool) -> bool:
    return _db_service.update_user_active_status(user_id, active_user)


def calculate_and_update_active_users(institution_id: str) -> int:
    return _db_service.calculate_and_update_active_users(institution_id)


def update_user_extended(user_id: str, update_data: Dict[str, Any]) -> bool:
    return _db_service.update_user_extended(user_id, update_data)


def get_user_by_verification_token(token: str) -> Optional[Dict[str, Any]]:
    return _db_service.get_user_by_verification_token(token)


def update_user_profile(user_id: str, profile_data: Dict[str, Any]) -> bool:
    return _db_service.update_user_profile(user_id, profile_data)


def update_user_role(
    user_id: str, new_role: str, program_ids: List[str] = None
) -> bool:
    return _db_service.update_user_role(user_id, new_role, program_ids)


def deactivate_user(user_id: str) -> bool:
    return _db_service.deactivate_user(user_id)


def delete_user(user_id: str) -> bool:
    return _db_service.delete_user(user_id)


# ---------------------------------------------------------------------------
# Audit log operations
# ---------------------------------------------------------------------------


def create_audit_log(audit_data: Dict[str, Any]) -> bool:
    return _db_service.create_audit_log(audit_data)


def get_audit_logs_by_entity(
    entity_type: str, entity_id: str, limit: int = 50
) -> List[Dict[str, Any]]:
    return _db_service.get_audit_logs_by_entity(entity_type, entity_id, limit)


def get_audit_logs_by_user(
    user_id: str,
    start_date: Optional[Any] = None,
    end_date: Optional[Any] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    return _db_service.get_audit_logs_by_user(user_id, start_date, end_date, limit)


def get_recent_audit_logs(
    institution_id: Optional[str] = None, limit: int = 50
) -> List[Dict[str, Any]]:
    return _db_service.get_recent_audit_logs(institution_id, limit)


def get_audit_logs_filtered(
    start_date: Any,
    end_date: Any,
    entity_type: Optional[str] = None,
    user_id: Optional[str] = None,
    institution_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    return _db_service.get_audit_logs_filtered(
        start_date, end_date, entity_type, user_id, institution_id
    )


# ---------------------------------------------------------------------------
# Course operations
# ---------------------------------------------------------------------------


def create_course(course_data: Dict[str, Any]) -> Optional[str]:
    return _db_service.create_course(course_data)


def update_course(course_id: str, course_data: Dict[str, Any]) -> bool:
    return _db_service.update_course(course_id, course_data)


def update_course_programs(course_id: str, program_ids: List[str]) -> bool:
    return _db_service.update_course_programs(course_id, program_ids)


def delete_course(course_id: str) -> bool:
    return _db_service.delete_course(course_id)


def get_course_by_number(
    course_number: str, institution_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    return _db_service.get_course_by_number(course_number, institution_id)


def get_courses_by_department(
    institution_id: str, department: str
) -> List[Dict[str, Any]]:
    return _db_service.get_courses_by_department(institution_id, department)


def create_course_outcome(outcome_data: Dict[str, Any]) -> str:
    return _db_service.create_course_outcome(outcome_data)


def update_course_outcome(outcome_id: str, outcome_data: Dict[str, Any]) -> bool:
    return _db_service.update_course_outcome(outcome_id, outcome_data)


def update_outcome_assessment(
    outcome_id: str,
    students_took: Optional[int] = None,
    students_passed: Optional[int] = None,
    assessment_tool: Optional[str] = None,
) -> bool:
    """Update outcome assessment data (corrected field names from demo feedback)."""
    return _db_service.update_outcome_assessment(
        outcome_id, students_took, students_passed, assessment_tool
    )


def delete_course_outcome(outcome_id: str) -> bool:
    return _db_service.delete_course_outcome(outcome_id)


def get_course_outcomes(course_id: str) -> List[Dict[str, Any]]:
    return _db_service.get_course_outcomes(course_id)


def get_course_outcome(outcome_id: str) -> Optional[Dict[str, Any]]:
    return _db_service.get_course_outcome(outcome_id)


def get_course_by_id(course_id: str) -> Optional[Dict[str, Any]]:
    return _db_service.get_course_by_id(course_id)


def _generate_unique_course_number(base_number: str, institution_id: str) -> str:
    """
    Generate a duplicate-friendly course number (e.g., BIOL-201-V2, -V3, etc.)
    that does not collide with existing records for the institution.
    """
    normalized = (base_number or "COURSE").strip().upper()
    suffix_index = 2
    candidate = f"{normalized}-V{suffix_index}"

    while get_course_by_number(candidate, institution_id):
        suffix_index += 1
        candidate = f"{normalized}-V{suffix_index}"

    return candidate


def duplicate_course_record(
    source_course: Dict[str, Any],
    overrides: Optional[Dict[str, Any]] = None,
    duplicate_programs: bool = True,
) -> Optional[str]:
    """
    Clone an existing course (and optionally program assignments) for demo workflows.
    """
    if not source_course:
        return None

    institution_id = source_course.get("institution_id")
    if not institution_id:
        logger.error("[DB Service] Cannot duplicate course without institution context")
        return None

    overrides = overrides or {}
    allowed_override_fields = {
        "course_number",
        "course_title",
        "department",
        "credit_hours",
        "active",
    }
    sanitized_overrides = {
        key: value
        for key, value in overrides.items()
        if key in allowed_override_fields and value is not None
    }

    program_ids_override = (
        overrides.get("program_ids") if "program_ids" in overrides else None
    )

    base_number = sanitized_overrides.get("course_number") or source_course.get(
        "course_number"
    )
    if not base_number:
        logger.error(
            "[DB Service] Source course missing course_number; cannot duplicate"
        )
        return None

    if "course_number" not in sanitized_overrides:
        sanitized_overrides["course_number"] = _generate_unique_course_number(
            base_number, institution_id
        )

    new_course_data: Dict[str, Any] = {
        "course_number": source_course.get("course_number"),
        "course_title": source_course.get("course_title"),
        "department": source_course.get("department"),
        "credit_hours": source_course.get("credit_hours", 3),
        "institution_id": institution_id,
        "active": source_course.get("active", True),
        "extras": deepcopy(source_course.get("extras") or {}),
    }

    new_course_data.update(sanitized_overrides)

    extras = new_course_data.get("extras") or {}
    extras["duplicated_from_course_id"] = source_course.get(
        "course_id"
    ) or source_course.get("id")
    extras["duplicated_from_course_number"] = source_course.get("course_number")
    new_course_data["extras"] = extras

    if program_ids_override is not None:
        program_ids = program_ids_override
    elif duplicate_programs:
        program_ids = source_course.get("program_ids") or []
    else:
        program_ids = []

    if program_ids is not None:
        new_course_data["program_ids"] = program_ids

    return create_course(new_course_data)


def get_all_courses(institution_id: str) -> List[Dict[str, Any]]:
    return _db_service.get_all_courses(institution_id)


def get_all_instructors(institution_id: str) -> List[Dict[str, Any]]:
    return _db_service.get_all_instructors(institution_id)


def get_all_sections(institution_id: str) -> List[Dict[str, Any]]:
    return _db_service.get_all_sections(institution_id)


def get_section_by_id(section_id: str) -> Optional[Dict[str, Any]]:
    return _db_service.get_section_by_id(section_id)


def create_course_offering(offering_data: Dict[str, Any]) -> Optional[str]:
    return _db_service.create_course_offering(offering_data)


def update_course_offering(offering_id: str, offering_data: Dict[str, Any]) -> bool:
    return _db_service.update_course_offering(offering_id, offering_data)


def delete_course_offering(offering_id: str) -> bool:
    return _db_service.delete_course_offering(offering_id)


def get_course_offering(offering_id: str) -> Optional[Dict[str, Any]]:
    return _db_service.get_course_offering(offering_id)


def get_course_offering_by_course_and_term(
    course_id: str, term_id: str
) -> Optional[Dict[str, Any]]:
    return _db_service.get_course_offering_by_course_and_term(course_id, term_id)


def get_all_course_offerings(institution_id: str) -> List[Dict[str, Any]]:
    return _db_service.get_all_course_offerings(institution_id)


# ---------------------------------------------------------------------------
# Term operations
# ---------------------------------------------------------------------------


def create_term(term_data: Dict[str, Any]) -> Optional[str]:
    return _db_service.create_term(term_data)


def update_term(term_id: str, term_data: Dict[str, Any]) -> bool:
    return _db_service.update_term(term_id, term_data)


def archive_term(term_id: str) -> bool:
    return _db_service.archive_term(term_id)


def delete_term(term_id: str) -> bool:
    return _db_service.delete_term(term_id)


def get_term_by_name(
    name: str, institution_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    return _db_service.get_term_by_name(name, institution_id)


def get_active_terms(institution_id: str) -> List[Dict[str, Any]]:
    return _db_service.get_active_terms(institution_id)


def get_term_by_id(term_id: str) -> Optional[Dict[str, Any]]:
    return _db_service.get_term_by_id(term_id)


def get_sections_by_term(term_id: str) -> List[Dict[str, Any]]:
    return _db_service.get_sections_by_term(term_id)


# ---------------------------------------------------------------------------
# Section operations
# ---------------------------------------------------------------------------


def create_course_section(section_data: Dict[str, Any]) -> Optional[str]:
    return _db_service.create_course_section(section_data)


def update_course_section(section_id: str, section_data: Dict[str, Any]) -> bool:
    return _db_service.update_course_section(section_id, section_data)


def assign_instructor(section_id: str, instructor_id: str) -> bool:
    return _db_service.assign_instructor(section_id, instructor_id)


def delete_course_section(section_id: str) -> bool:
    return _db_service.delete_course_section(section_id)


def get_sections_by_instructor(instructor_id: str) -> List[Dict[str, Any]]:
    return _db_service.get_sections_by_instructor(instructor_id)


# ---------------------------------------------------------------------------
# Program operations
# ---------------------------------------------------------------------------


def create_program(program_data: Dict[str, Any]) -> Optional[str]:
    return _db_service.create_program(program_data)


def get_programs_by_institution(institution_id: str) -> List[Dict[str, Any]]:
    return _db_service.get_programs_by_institution(institution_id)


def get_program_by_id(program_id: str) -> Optional[Dict[str, Any]]:
    return _db_service.get_program_by_id(program_id)


def get_program_by_name_and_institution(
    program_name: str, institution_id: str
) -> Optional[Dict[str, Any]]:
    return _db_service.get_program_by_name_and_institution(program_name, institution_id)


def update_program(program_id: str, updates: Dict[str, Any]) -> bool:
    return _db_service.update_program(program_id, updates)


def delete_program(program_id: str, reassign_to_program_id: str) -> bool:
    return _db_service.delete_program(program_id, reassign_to_program_id)


def get_courses_by_program(program_id: str) -> List[Dict[str, Any]]:
    return _db_service.get_courses_by_program(program_id)


def get_unassigned_courses(institution_id: str) -> List[Dict[str, Any]]:
    return _db_service.get_unassigned_courses(institution_id)


def assign_course_to_default_program(course_id: str, institution_id: str) -> bool:
    return _db_service.assign_course_to_default_program(course_id, institution_id)


def add_course_to_program(course_id: str, program_id: str) -> bool:
    return _db_service.add_course_to_program(course_id, program_id)


def remove_course_from_program(course_id: str, program_id: str) -> bool:
    return _db_service.remove_course_from_program(course_id, program_id)


def bulk_add_courses_to_program(
    course_ids: List[str], program_id: str
) -> Dict[str, Any]:
    return _db_service.bulk_add_courses_to_program(course_ids, program_id)


def bulk_remove_courses_from_program(
    course_ids: List[str], program_id: str
) -> Dict[str, Any]:
    return _db_service.bulk_remove_courses_from_program(course_ids, program_id)


# ---------------------------------------------------------------------------
# Invitation operations
# ---------------------------------------------------------------------------


def create_invitation(invitation_data: Dict[str, Any]) -> Optional[str]:
    return _db_service.create_invitation(invitation_data)


def get_invitation_by_id(invitation_id: str) -> Optional[Dict[str, Any]]:
    return _db_service.get_invitation_by_id(invitation_id)


def get_invitation_by_token(invitation_token: str) -> Optional[Dict[str, Any]]:
    return _db_service.get_invitation_by_token(invitation_token)


def get_invitation_by_email(
    email: str, institution_id: str
) -> Optional[Dict[str, Any]]:
    return _db_service.get_invitation_by_email(email, institution_id)


def update_invitation(invitation_id: str, updates: Dict[str, Any]) -> bool:
    return _db_service.update_invitation(invitation_id, updates)


def list_invitations(
    institution_id: str, status: Optional[str] = None, limit: int = 50, offset: int = 0
) -> List[Dict[str, Any]]:
    return _db_service.list_invitations(institution_id, status, limit, offset)


def get_outcomes_by_status(
    institution_id: str,
    status: str,
    program_id: Optional[str] = None,
    term_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get course outcomes filtered by status.

    Args:
        institution_id: Institution ID to filter by
        status: CLO status to filter by
        program_id: Optional program ID to further filter results
        term_id: Optional term ID to further filter results

    Returns:
        List of course outcome dictionaries
    """
    return _db_service.get_outcomes_by_status(
        institution_id, status, program_id, term_id
    )


def get_sections_by_course(course_id: str) -> List[Dict[str, Any]]:
    """
    Get all course sections for a given course.

    Args:
        course_id: The course ID to get sections for

    Returns:
        List of course section dictionaries
    """
    return _db_service.get_sections_by_course(course_id)


__all__ = [
    "COURSE_OFFERINGS_COLLECTION",
    "COURSE_OUTCOMES_COLLECTION",
    "COURSE_SECTIONS_COLLECTION",
    "COURSES_COLLECTION",
    "DB_CLIENT_NOT_AVAILABLE_MSG",
    "DEFAULT_INSTITUTION_TIMEZONE",
    "INSTITUTIONS_COLLECTION",
    "TERMS_COLLECTION",
    "USERS_COLLECTION",
    "db",
    "reset_database",
    "refresh_connection",
    "db_operation_timeout",
    "check_db_connection",
    "sanitize_for_logging",
    "create_institution",
    "get_institution_by_id",
    "get_all_institutions",
    "create_default_mocku_institution",
    "create_new_institution",
    "get_institution_instructor_count",
    "get_institution_by_short_name",
    "create_user",
    "get_user_by_email",
    "get_user_by_reset_token",
    "get_all_users",
    "get_users_by_role",
    "get_user_by_id",
    "update_user",
    "update_user_active_status",
    "calculate_and_update_active_users",
    "update_user_extended",
    "get_user_by_verification_token",
    "create_course",
    "get_course_by_number",
    "get_courses_by_department",
    "create_course_outcome",
    "get_course_outcomes",
    "get_course_by_id",
    "get_all_courses",
    "get_all_instructors",
    "get_all_sections",
    "create_course_offering",
    "get_course_offering",
    "get_course_offering_by_course_and_term",
    "get_all_course_offerings",
    "create_term",
    "get_term_by_name",
    "get_active_terms",
    "get_sections_by_term",
    "create_course_section",
    "get_sections_by_instructor",
    "create_program",
    "get_programs_by_institution",
    "get_program_by_id",
    "get_program_by_name_and_institution",
    "update_program",
    "delete_program",
    "get_courses_by_program",
    "get_unassigned_courses",
    "assign_course_to_default_program",
    "add_course_to_program",
    "remove_course_from_program",
    "bulk_add_courses_to_program",
    "bulk_remove_courses_from_program",
    "create_invitation",
    "get_invitation_by_id",
    "get_invitation_by_token",
    "get_invitation_by_email",
    "update_invitation",
    "list_invitations",
    "get_outcomes_by_status",
    "get_sections_by_course",
]
