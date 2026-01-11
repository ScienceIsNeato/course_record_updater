"""SQLAlchemy models for LoopCloser SQLite backend."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    PickleType,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

from src.utils.term_utils import TERM_STATUS_ACTIVE, get_term_status
from src.utils.time_utils import get_current_time

Base = declarative_base()  # type: ignore[valid-type,misc]

# Module logger
logger = logging.getLogger(__name__)

# Constants for foreign key references
COURSES_ID = "courses.id"
PROGRAMS_ID = "programs.id"
INSTITUTIONS_ID = "institutions.id"
USERS_ID = "users.id"
CASCADE_OPTIONS = "all, delete-orphan"


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


class TimestampMixin:
    """Common timestamp columns."""

    created_at = Column(DateTime, nullable=False, default=get_current_time)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=get_current_time,
        onupdate=get_current_time,
    )


# Association table linking courses to programs
course_program_table = Table(
    "course_programs",
    Base.metadata,
    Column("course_id", String, ForeignKey(COURSES_ID), primary_key=True),
    Column("program_id", String, ForeignKey(PROGRAMS_ID), primary_key=True),
)


class Institution(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """Institution model."""

    __tablename__ = "institutions"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    short_name = Column(String, nullable=False, unique=True)
    website_url = Column(String)
    logo_path = Column(String)
    created_by = Column(String)
    admin_email = Column(String, nullable=False)
    allow_self_registration = Column(Boolean, default=False)
    require_email_verification = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    extras = Column(PickleType, default=dict)

    users = relationship(
        "User",
        back_populates="institution",
        cascade=CASCADE_OPTIONS,
    )
    programs = relationship(
        "Program",
        back_populates="institution",
        cascade=CASCADE_OPTIONS,
    )
    courses = relationship(
        "Course",
        back_populates="institution",
        cascade=CASCADE_OPTIONS,
    )
    terms = relationship(
        "Term",
        back_populates="institution",
        cascade=CASCADE_OPTIONS,
    )
    invitations = relationship(
        "UserInvitation",
        back_populates="institution",
        cascade=CASCADE_OPTIONS,
    )


class User(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """User model."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    display_name = Column(String)
    account_status = Column(String, default="pending")
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String)
    email_verification_sent_at = Column(DateTime)
    role = Column(String, nullable=False)
    institution_id = Column(String, ForeignKey(INSTITUTIONS_ID))
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    last_login_at = Column(DateTime)
    invited_by = Column(String)
    invited_at = Column(DateTime)
    registration_completed_at = Column(DateTime)
    oauth_provider = Column(String)
    oauth_id = Column(String)
    password_reset_token = Column(String)
    password_reset_token_data = Column(
        PickleType
    )  # Stores token metadata (expires_at, etc.)
    password_reset_requested_at = Column(DateTime)
    password_reset_completed_at = Column(DateTime)
    password_reset_expires_at = Column(DateTime)
    extras = Column(PickleType, default=dict)

    # Per-user date override for demos and testing (admin-only)
    system_date_override = Column(DateTime)
    institution = relationship("Institution", back_populates="users")
    programs = relationship(
        "Program",
        secondary="user_programs",
        back_populates="users",
    )
    sections = relationship("CourseSection", back_populates="instructor")


# Association table linking users to programs
user_program_table = Table(
    "user_programs",
    Base.metadata,
    Column("user_id", String, ForeignKey(USERS_ID), primary_key=True),
    Column("program_id", String, ForeignKey(PROGRAMS_ID), primary_key=True),
)


class Program(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """Academic program model."""

    __tablename__ = "programs"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    short_name = Column(String, nullable=False)
    description = Column(Text)
    institution_id = Column(String, ForeignKey(INSTITUTIONS_ID), nullable=False)
    created_by = Column(String)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    extras = Column(PickleType, default=dict)

    institution = relationship("Institution", back_populates="programs")
    courses = relationship(
        "Course",
        secondary=course_program_table,
        back_populates="programs",
    )
    users = relationship(
        "User",
        secondary=user_program_table,
        back_populates="programs",
    )


class Course(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """Course model."""

    __tablename__ = "courses"

    id = Column(String, primary_key=True, default=generate_uuid)
    course_number = Column(String, nullable=False)
    course_title = Column(String, nullable=False)
    department = Column(String)
    credit_hours = Column(Integer, default=3)
    institution_id = Column(String, ForeignKey(INSTITUTIONS_ID), nullable=False)
    active = Column(Boolean, default=True)
    extras = Column(PickleType, default=dict)

    institution = relationship("Institution", back_populates="courses")
    programs = relationship(
        "Program",
        secondary=course_program_table,
        back_populates="courses",
    )
    offerings = relationship(
        "CourseOffering",
        back_populates="course",
        cascade=CASCADE_OPTIONS,
    )
    outcomes = relationship(
        "CourseOutcome",
        back_populates="course",
        cascade=CASCADE_OPTIONS,
    )


class Term(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """Term model."""

    __tablename__ = "terms"

    id = Column(String, primary_key=True, default=generate_uuid)
    term_name = Column(String, nullable=False)
    name = Column(String, nullable=False)
    start_date = Column(String)
    end_date = Column(String)
    assessment_due_date = Column(String)
    institution_id = Column(String, ForeignKey(INSTITUTIONS_ID))
    extras = Column(PickleType, default=dict)

    institution = relationship("Institution", back_populates="terms")
    offerings = relationship(
        "CourseOffering",
        back_populates="term",
        cascade=CASCADE_OPTIONS,
    )

    def get_status(self, reference_date: datetime | None = None) -> str:
        """Return computed status for this term."""
        # Cast Column types to their runtime values for type checker
        start = str(self.start_date) if self.start_date else None
        end = str(self.end_date) if self.end_date else None
        return get_term_status(start, end, reference_date)


class CourseOffering(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """Course offering model."""

    __tablename__ = "course_offerings"

    id = Column(String, primary_key=True, default=generate_uuid)
    course_id = Column(String, ForeignKey(COURSES_ID), nullable=False)
    term_id = Column(String, ForeignKey("terms.id"), nullable=False)
    institution_id = Column(String, ForeignKey(INSTITUTIONS_ID), nullable=False)
    program_id = Column(
        String, ForeignKey(PROGRAMS_ID), nullable=True
    )  # Link to specific program context
    total_enrollment = Column(Integer, default=0)
    section_count = Column(Integer, default=0)
    extras = Column(PickleType, default=dict)

    course = relationship("Course", back_populates="offerings")
    term = relationship("Term", back_populates="offerings")
    sections = relationship(
        "CourseSection",
        back_populates="offering",
        cascade=CASCADE_OPTIONS,
    )
    institution = relationship("Institution")


class CourseSection(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """Course section model."""

    __tablename__ = "course_sections"

    id = Column(String, primary_key=True, default=generate_uuid)
    offering_id = Column(String, ForeignKey("course_offerings.id"), nullable=False)
    instructor_id = Column(String, ForeignKey(USERS_ID))
    section_number = Column(String, default="001")

    # Enrollment Data (pre-populated from feed or admin)
    enrollment = Column(Integer)
    withdrawals = Column(Integer, default=0)

    # Course-Level Assessment Data (instructor-entered)
    students_passed = Column(Integer, nullable=True)  # Students with A, B, C
    students_dfic = Column(Integer, nullable=True)  # Students with D, F, Incomplete
    cannot_reconcile = Column(Boolean, default=False)  # Enrollment math doesn't add up
    reconciliation_note = Column(
        Text, nullable=True
    )  # Explanation when cannot_reconcile=True

    # Course-Level Narratives (NOT at CLO level - corrected from demo feedback)
    narrative_celebrations = Column(Text, nullable=True)  # What went well
    narrative_challenges = Column(Text, nullable=True)  # What was difficult
    narrative_changes = Column(Text, nullable=True)  # What to do differently next time

    # Workflow fields
    status = Column(String, default="assigned")
    due_date = Column(DateTime, nullable=True)  # When assessment is due (Phase 3.2)
    assigned_date = Column(DateTime)
    completed_date = Column(DateTime)

    # Deprecated: grade_distribution JSON replaced with explicit fields above
    extras = Column(PickleType, default=dict)

    offering = relationship("CourseOffering", back_populates="sections")
    instructor = relationship("User", back_populates="sections")
    outcomes = relationship(
        "CourseSectionOutcome", back_populates="section", cascade=CASCADE_OPTIONS
    )


class CourseOutcome(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """Course outcome model."""

    __tablename__ = "course_outcomes"

    id = Column(String, primary_key=True, default=generate_uuid)
    course_id = Column(String, ForeignKey(COURSES_ID), nullable=False)
    program_id = Column(
        String, ForeignKey(PROGRAMS_ID), nullable=True
    )  # Filter for program-specific defaults
    clo_number = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    assessment_method = Column(String)
    active = Column(Boolean, default=True)

    # CLO Assessment Fields (corrected from demo feedback)
    students_took = Column(
        Integer, nullable=True
    )  # How many students took THIS CLO assessment
    students_passed = Column(
        Integer, nullable=True
    )  # How many students passed THIS CLO assessment
    assessment_tool = Column(
        String(50), nullable=True
    )  # Brief description: "Test #3", "Lab 2", etc.

    # Deprecated: assessment_data JSON removed in favor of explicit fields above
    # Deprecated: narrative removed - narratives belong at COURSE level, not CLO level
    extras = Column(JSON, default=dict)

    # Workflow status fields
    status = Column(String, default="unassigned")  # CLOStatus enum
    submitted_at = Column(DateTime, nullable=True)
    submitted_by_user_id = Column(String, ForeignKey(USERS_ID), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_user_id = Column(String, ForeignKey(USERS_ID), nullable=True)
    approval_status = Column(String, default="pending")  # CLOApprovalStatus enum
    feedback_comments = Column(Text, nullable=True)
    feedback_provided_at = Column(DateTime, nullable=True)

    course = relationship("Course", back_populates="outcomes")
    submitted_by = relationship(
        "User", foreign_keys=[submitted_by_user_id], backref="submitted_outcomes"
    )
    reviewed_by = relationship(
        "User", foreign_keys=[reviewed_by_user_id], backref="reviewed_outcomes"
    )


class CourseSectionOutcome(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """
    Course Section Outcome (Instance).

    Represents the instantiation of a CLO for a specific section, holding
    the actual assessment data (students_took, students_passed, etc.).
    """

    __tablename__ = "course_section_outcomes"

    id = Column(String, primary_key=True, default=generate_uuid)
    section_id = Column(String, ForeignKey("course_sections.id"), nullable=False)
    outcome_id = Column(
        String, ForeignKey("course_outcomes.id"), nullable=False
    )  # The template

    # Assessment Data (Instructor Input)
    students_took = Column(Integer, nullable=True)
    students_passed = Column(Integer, nullable=True)
    assessment_tool = Column(String(50), nullable=True)

    # Workflow Status
    status = Column(String, default="assigned")
    approval_status = Column(String, default="pending")

    # Audit Trail
    submitted_at = Column(DateTime(timezone=True))
    submitted_by = Column(String)  # User ID
    reviewed_at = Column(DateTime(timezone=True))
    reviewed_by = Column(String)  # User ID
    feedback_comments = Column(Text)

    extras = Column(PickleType, default=dict)

    section = relationship("CourseSection", back_populates="outcomes")
    outcome = relationship("CourseOutcome")


class UserInvitation(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """User invitation model."""

    __tablename__ = "user_invitations"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, nullable=False)
    role = Column(String, nullable=False)
    institution_id = Column(String, ForeignKey(INSTITUTIONS_ID), nullable=False)
    token = Column(String, nullable=False, unique=True)
    invited_by = Column(String)
    invited_at = Column(DateTime, default=get_current_time)
    expires_at = Column(DateTime)
    status = Column(String, default="pending")
    accepted_at = Column(DateTime)
    personal_message = Column(Text)
    extras = Column(JSON, default=dict)

    institution = relationship("Institution", back_populates="invitations")


def to_dict(model: Any, extra_fields: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Convert SQLAlchemy model to dictionary merging extras."""
    data: Dict[str, Any] = {}

    # Add extras if present
    if hasattr(model, "extras") and model.extras:
        data.update(model.extras)

    # Get model-specific data using dispatch pattern
    model_data = _get_model_data(model)
    data.update(model_data)

    # Add extra fields if provided
    if extra_fields:
        data.update(extra_fields)

    return data


def _get_model_data(model: Any) -> Dict[str, Any]:
    """Get model-specific data using dispatch pattern."""
    model_type = type(model)

    # Dispatch to appropriate handler
    if model_type == Institution:
        return _institution_to_dict(model)
    elif model_type == User:
        return _user_to_dict(model)
    elif model_type == Program:
        return _program_to_dict(model)
    elif model_type == Course:
        return _course_to_dict(model)
    elif model_type == Term:
        return _term_to_dict(model)
    elif model_type == CourseOffering:
        return _course_offering_to_dict(model)
    elif model_type == CourseSection:
        return _course_section_to_dict(model)
    elif model_type == CourseOutcome:
        return _course_outcome_to_dict(model)
    elif model_type == UserInvitation:
        return _user_invitation_to_dict(model)
    elif model_type == CourseSectionOutcome:
        return _course_section_outcome_to_dict(model)
    else:
        return {}


def _course_section_outcome_to_dict(model: CourseSectionOutcome) -> Dict[str, Any]:
    """Convert CourseSectionOutcome model to dictionary."""
    return {
        "id": model.id,
        "section_id": model.section_id,
        "outcome_id": model.outcome_id,
        "students_took": model.students_took,
        "students_passed": model.students_passed,
        "assessment_tool": model.assessment_tool,
        "created_at": model.created_at,
        "last_modified": model.updated_at,
    }


def _institution_to_dict(model: Institution) -> Dict[str, Any]:
    """Convert Institution model to dictionary."""
    return {
        "institution_id": model.id,
        "name": model.name,
        "short_name": model.short_name,
        "website_url": model.website_url,
        "logo_path": model.logo_path,
        "created_by": model.created_by,
        "admin_email": model.admin_email,
        "allow_self_registration": model.allow_self_registration,
        "require_email_verification": model.require_email_verification,
        "is_active": model.is_active,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _user_to_dict(model: User) -> Dict[str, Any]:
    """Convert User model to dictionary."""
    data = {
        "id": model.id,  # Primary key (conventional)
        "user_id": model.id,  # Legacy compatibility
        "email": model.email,
        "password_hash": model.password_hash,
        "first_name": model.first_name,
        "last_name": model.last_name,
        "display_name": model.display_name,
        "account_status": model.account_status,
        "email_verified": model.email_verified,
        "email_verification_token": model.email_verification_token,
        "email_verification_sent_at": model.email_verification_sent_at,
        "role": model.role,
        "institution_id": model.institution_id,
        "login_attempts": model.login_attempts,
        "locked_until": model.locked_until,
        "last_login_at": model.last_login_at,
        "invited_by": model.invited_by,
        "invited_at": model.invited_at,
        "registration_completed_at": model.registration_completed_at,
        "oauth_provider": model.oauth_provider,
        "oauth_id": model.oauth_id,
        "password_reset_token": model.password_reset_token,
        "password_reset_token_data": model.password_reset_token_data,
        "password_reset_requested_at": model.password_reset_requested_at,
        "password_reset_completed_at": model.password_reset_completed_at,
        "password_reset_expires_at": model.password_reset_expires_at,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
        "system_date_override": model.system_date_override,
    }
    # Add program_ids if not already present
    if "program_ids" not in data:
        data["program_ids"] = [program.id for program in model.programs]
    return data


def _program_to_dict(model: Program) -> Dict[str, Any]:
    """Convert Program model to dictionary."""
    data = {
        "program_id": model.id,
        "name": model.name,
        "short_name": model.short_name,
        "description": model.description,
        "institution_id": model.institution_id,
        "created_by": model.created_by,
        "is_default": model.is_default,
        "is_active": model.is_active,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }
    # Add program_admins if not already present
    if "program_admins" not in data:
        data["program_admins"] = (
            model.extras.get("program_admins", []) if model.extras else []
        )
    return data


def _course_to_dict(model: Course) -> Dict[str, Any]:
    """Convert Course model to dictionary."""
    data = {
        "course_id": model.id,
        "course_number": model.course_number,
        "course_title": model.course_title,
        "department": model.department,
        "credit_hours": model.credit_hours,
        "institution_id": model.institution_id,
        "active": model.active,
        "created_at": model.created_at,
        "last_modified": model.updated_at,
    }
    # Add program_ids if not already present
    if "program_ids" not in data:
        data["program_ids"] = [program.id for program in model.programs]
    return data


def _term_to_dict(model: Term) -> Dict[str, Any]:
    """Convert Term model to dictionary."""
    status = model.get_status()
    return {
        "term_id": model.id,
        "term_name": model.term_name,
        "name": model.name,
        "start_date": model.start_date,
        "end_date": model.end_date,
        "assessment_due_date": model.assessment_due_date,
        "status": status,
        "is_active": status == TERM_STATUS_ACTIVE,
        "institution_id": model.institution_id,
        "created_at": model.created_at,
        "last_modified": model.updated_at,
        "offerings_count": len(model.offerings) if model.offerings else 0,
    }


def _course_offering_to_dict(model: CourseOffering) -> Dict[str, Any]:
    """Convert CourseOffering model to dictionary."""
    term = getattr(model, "term", None)
    term_start = None
    term_end = None
    if term:
        term_start = term.start_date
        term_end = term.end_date
    elif hasattr(model, "extras") and model.extras:
        term_start = model.extras.get("term_start_date")
        term_end = model.extras.get("term_end_date")

    status = get_term_status(term_start, term_end)
    return {
        "offering_id": model.id,
        "course_id": model.course_id,
        "term_id": model.term_id,
        "institution_id": model.institution_id,
        "program_id": model.program_id,
        "status": status,
        "term_status": status,
        "timeline_status": status,
        "is_active": status == TERM_STATUS_ACTIVE,
        "term_start_date": term_start,
        "term_end_date": term_end,
        "total_enrollment": model.total_enrollment,
        "section_count": model.section_count,
        "created_at": model.created_at,
        "last_modified": model.updated_at,
    }


def _course_section_to_dict(model: CourseSection) -> Dict[str, Any]:
    """Convert CourseSection model to dictionary."""
    return {
        "section_id": model.id,
        "offering_id": model.offering_id,
        "instructor_id": model.instructor_id,
        "section_number": model.section_number,
        # Enrollment data (pre-populated from feed)
        "enrollment": model.enrollment,
        "withdrawals": model.withdrawals,
        # Course-level assessment data (instructor-entered)
        "students_passed": model.students_passed,
        "students_dfic": model.students_dfic,
        "cannot_reconcile": model.cannot_reconcile,
        "reconciliation_note": model.reconciliation_note,
        # Course-level narratives (NOT at CLO level)
        "narrative_celebrations": model.narrative_celebrations,
        "narrative_challenges": model.narrative_challenges,
        "narrative_changes": model.narrative_changes,
        # Workflow fields
        "status": model.status,
        "due_date": model.due_date,
        "assigned_date": model.assigned_date,
        "completed_date": model.completed_date,
        "created_at": model.created_at,
        "last_modified": model.updated_at,
    }


def _course_outcome_to_dict(model: CourseOutcome) -> Dict[str, Any]:
    """Convert CourseOutcome model to dictionary."""
    base_dict = {
        "outcome_id": model.id,
        "course_id": model.course_id,
        "clo_number": model.clo_number,
        "description": model.description,
        "assessment_method": model.assessment_method,
        # CLO assessment fields (corrected from demo feedback)
        "students_took": model.students_took,
        "students_passed": model.students_passed,
        "assessment_tool": model.assessment_tool,
        "active": model.active,
        "created_at": model.created_at,
        "last_modified": model.updated_at,
        # CLO workflow fields
        "status": model.status,
        "submitted_at": model.submitted_at,
        "submitted_by_user_id": model.submitted_by_user_id,
        "reviewed_at": model.reviewed_at,
        "reviewed_by_user_id": model.reviewed_by_user_id,
        "approval_status": model.approval_status,
        "feedback_comments": model.feedback_comments,
        "feedback_provided_at": model.feedback_provided_at,
    }

    # Add course info if relationship satisfies (is loaded)
    # Note: simple check 'if model.course' might trigger lazy load which fails if detached.
    # But since we use selectinload, it should be available.
    # Safe approach: check dict or inspect.
    # For now, we wrap in try/except or rely on explicit loading.
    try:
        if model.course:
            base_dict.update(
                {
                    "course_number": model.course.course_number,
                    "course_title": model.course.course_title,
                    "course": {
                        "course_number": model.course.course_number,
                        "course_title": model.course.course_title,
                    },
                }
            )
    except Exception as e:
        # Relationship not loaded or detached; log at debug level so it can be
        # investigated without failing normal operations.
        logger.debug("Course relationship not available for model: %s", e)

    return base_dict


def _user_invitation_to_dict(model: UserInvitation) -> Dict[str, Any]:
    """Convert UserInvitation model to dictionary."""
    return {
        "id": model.id,  # Primary key for update operations
        "invitation_id": model.id,  # Legacy compatibility
        "email": model.email,
        "role": model.role,
        "institution_id": model.institution_id,
        "token": model.token,
        "invited_by": model.invited_by,
        "invited_at": model.invited_at.isoformat() if model.invited_at else None,
        "expires_at": model.expires_at.isoformat() if model.expires_at else None,
        "status": model.status,
        "accepted_at": model.accepted_at.isoformat() if model.accepted_at else None,
        "personal_message": model.personal_message,
        "created_at": model.created_at.isoformat() if model.created_at else None,
        "updated_at": model.updated_at.isoformat() if model.updated_at else None,
    }


class AuditLog(Base):  # type: ignore[valid-type,misc]
    """Audit Log model for tracking all CRUD operations."""

    __tablename__ = "audit_log"

    audit_id = Column(String, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)

    # Who performed the action
    user_id = Column(String, index=True)
    user_email = Column(String)
    user_role = Column(String)

    # What was done
    operation_type = Column(
        String, nullable=False, index=True
    )  # CREATE, UPDATE, DELETE
    entity_type = Column(
        String, nullable=False, index=True
    )  # users, institutions, etc.
    entity_id = Column(String, nullable=False, index=True)

    # Change details
    old_values = Column(Text)  # JSON: Previous state (NULL for CREATE)
    new_values = Column(Text)  # JSON: New state (NULL for DELETE)
    changed_fields = Column(Text)  # JSON array: changed field names (UPDATE only)

    # Context
    source_type = Column(String, nullable=False)  # API, IMPORT, SYSTEM, SCRIPT
    source_details = Column(Text)
    ip_address = Column(String)
    user_agent = Column(Text)

    # Request tracking
    request_id = Column(String)
    session_id = Column(String)

    # Institution context (for multi-tenant filtering)
    institution_id = Column(String, index=True)


# Import BulkEmailJob to ensure it's registered with Base
from src.bulk_email_models.bulk_email_job import BulkEmailJob  # noqa: E402

__all__ = [
    "Base",
    "Institution",
    "User",
    "Program",
    "Course",
    "Term",
    "CourseOffering",
    "CourseSection",
    "CourseOutcome",
    "UserInvitation",
    "AuditLog",
    "BulkEmailJob",
    "course_program_table",
    "user_program_table",
    "to_dict",
]
