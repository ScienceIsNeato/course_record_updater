"""SQLAlchemy models for Course Record Updater SQLite backend."""

from __future__ import annotations

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

Base = declarative_base()  # type: ignore[valid-type,misc]

# Constants for foreign key references
COURSES_ID = "courses.id"
INSTITUTIONS_ID = "institutions.id"
CASCADE_OPTIONS = "all, delete-orphan"


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


class TimestampMixin:
    """Common timestamp columns."""

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


# Association table linking courses to programs
course_program_table = Table(
    "course_programs",
    Base.metadata,
    Column("course_id", String, ForeignKey(COURSES_ID), primary_key=True),
    Column("program_id", String, ForeignKey("programs.id"), primary_key=True),
)


class Institution(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """Institution model."""

    __tablename__ = "institutions"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    short_name = Column(String, nullable=False, unique=True)
    website_url = Column(String)
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
    password_reset_expires_at = Column(DateTime)
    extras = Column(PickleType, default=dict)

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
    Column("user_id", String, ForeignKey("users.id"), primary_key=True),
    Column("program_id", String, ForeignKey("programs.id"), primary_key=True),
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
    active = Column(Boolean, default=True)
    institution_id = Column(String, ForeignKey(INSTITUTIONS_ID))
    extras = Column(PickleType, default=dict)

    institution = relationship("Institution", back_populates="terms")
    offerings = relationship(
        "CourseOffering",
        back_populates="term",
        cascade=CASCADE_OPTIONS,
    )


class CourseOffering(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """Course offering model."""

    __tablename__ = "course_offerings"

    id = Column(String, primary_key=True, default=generate_uuid)
    course_id = Column(String, ForeignKey(COURSES_ID), nullable=False)
    term_id = Column(String, ForeignKey("terms.id"), nullable=False)
    institution_id = Column(String, ForeignKey(INSTITUTIONS_ID), nullable=False)
    status = Column(String, default="active")
    capacity = Column(Integer)
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
    instructor_id = Column(String, ForeignKey("users.id"))
    section_number = Column(String, default="001")
    enrollment = Column(Integer)
    status = Column(String, default="assigned")
    grade_distribution = Column(JSON, default=dict)
    assigned_date = Column(DateTime)
    completed_date = Column(DateTime)
    extras = Column(PickleType, default=dict)

    offering = relationship("CourseOffering", back_populates="sections")
    instructor = relationship("User", back_populates="sections")


class CourseOutcome(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """Course outcome model."""

    __tablename__ = "course_outcomes"

    id = Column(String, primary_key=True, default=generate_uuid)
    course_id = Column(String, ForeignKey(COURSES_ID), nullable=False)
    clo_number = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    assessment_method = Column(String)
    active = Column(Boolean, default=True)
    assessment_data = Column(JSON, default=dict)
    narrative = Column(Text)
    extras = Column(JSON, default=dict)

    course = relationship("Course", back_populates="outcomes")


class UserInvitation(Base, TimestampMixin):  # type: ignore[valid-type,misc]
    """User invitation model."""

    __tablename__ = "user_invitations"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, nullable=False)
    role = Column(String, nullable=False)
    institution_id = Column(String, ForeignKey(INSTITUTIONS_ID), nullable=False)
    token = Column(String, nullable=False, unique=True)
    invited_by = Column(String)
    invited_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    status = Column(String, default="pending")
    accepted_at = Column(DateTime)
    personal_message = Column(Text)
    extras = Column(JSON, default=dict)

    institution = relationship("Institution", back_populates="invitations")


def to_dict(model: Any, extra_fields: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Convert SQLAlchemy model to dictionary merging extras."""

    data: Dict[str, Any] = {}
    if hasattr(model, "extras") and model.extras:
        data.update(model.extras)

    if isinstance(model, Institution):
        data.update(
            {
                "institution_id": model.id,
                "name": model.name,
                "short_name": model.short_name,
                "website_url": model.website_url,
                "created_by": model.created_by,
                "admin_email": model.admin_email,
                "allow_self_registration": model.allow_self_registration,
                "require_email_verification": model.require_email_verification,
                "is_active": model.is_active,
                "created_at": model.created_at,
                "updated_at": model.updated_at,
            }
        )
    elif isinstance(model, User):
        data.update(
            {
                "user_id": model.id,
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
                "password_reset_expires_at": model.password_reset_expires_at,
                "created_at": model.created_at,
                "updated_at": model.updated_at,
            }
        )
        if "program_ids" not in data:
            data["program_ids"] = [program.id for program in model.programs]
    elif isinstance(model, Program):
        data.update(
            {
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
        )
        if "program_admins" not in data:
            data["program_admins"] = (
                model.extras.get("program_admins", []) if model.extras else []
            )
    elif isinstance(model, Course):
        data.update(
            {
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
        )
        if "program_ids" not in data:
            data["program_ids"] = [program.id for program in model.programs]
    elif isinstance(model, Term):
        data.update(
            {
                "term_id": model.id,
                "term_name": model.term_name,
                "name": model.name,
                "start_date": model.start_date,
                "end_date": model.end_date,
                "assessment_due_date": model.assessment_due_date,
                "active": model.active,
                "institution_id": model.institution_id,
                "created_at": model.created_at,
                "last_modified": model.updated_at,
            }
        )
    elif isinstance(model, CourseOffering):
        data.update(
            {
                "offering_id": model.id,
                "course_id": model.course_id,
                "term_id": model.term_id,
                "institution_id": model.institution_id,
                "status": model.status,
                "capacity": model.capacity,
                "total_enrollment": model.total_enrollment,
                "section_count": model.section_count,
                "created_at": model.created_at,
                "last_modified": model.updated_at,
            }
        )
    elif isinstance(model, CourseSection):
        data.update(
            {
                "section_id": model.id,
                "offering_id": model.offering_id,
                "instructor_id": model.instructor_id,
                "section_number": model.section_number,
                "enrollment": model.enrollment,
                "status": model.status,
                "grade_distribution": model.grade_distribution,
                "assigned_date": model.assigned_date,
                "completed_date": model.completed_date,
                "created_at": model.created_at,
                "last_modified": model.updated_at,
            }
        )
    elif isinstance(model, CourseOutcome):
        data.update(
            {
                "outcome_id": model.id,
                "course_id": model.course_id,
                "clo_number": model.clo_number,
                "description": model.description,
                "assessment_method": model.assessment_method,
                "assessment_data": model.assessment_data,
                "narrative": model.narrative,
                "active": model.active,
                "created_at": model.created_at,
                "last_modified": model.updated_at,
            }
        )
    elif isinstance(model, UserInvitation):
        data.update(
            {
                "invitation_id": model.id,
                "email": model.email,
                "role": model.role,
                "institution_id": model.institution_id,
                "token": model.token,
                "invited_by": model.invited_by,
                "invited_at": model.invited_at,
                "expires_at": model.expires_at,
                "status": model.status,
                "accepted_at": model.accepted_at,
                "personal_message": model.personal_message,
                "created_at": model.created_at,
                "updated_at": model.updated_at,
            }
        )

    if extra_fields:
        data.update(extra_fields)

    return data


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
    "course_program_table",
    "user_program_table",
    "to_dict",
]
