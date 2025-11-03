"""SQLite-backed database implementation."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from constants import DEFAULT_INSTITUTION_TIMEZONE
from database_interface import DatabaseInterface
from database_sql import SQLiteService
from models_sql import (
    Course,
    CourseOffering,
    CourseOutcome,
    CourseSection,
    Institution,
    Program,
    Term,
    User,
    UserInvitation,
    course_program_table,
    to_dict,
)

logger = logging.getLogger(__name__)


def _ensure_uuid(value: Optional[str]) -> str:
    return value or str(uuid.uuid4())


class SQLiteDatabase(DatabaseInterface):
    """Concrete database implementation using SQLite and SQLAlchemy."""

    def __init__(self, db_url: Optional[str] = None) -> None:
        self.sqlite = SQLiteService(db_url)

    # ------------------------------------------------------------------
    # Institution operations
    # ------------------------------------------------------------------
    def create_institution(self, institution_data: Dict[str, Any]) -> Optional[str]:
        payload = dict(institution_data)
        institution_id = _ensure_uuid(payload.pop("institution_id", None))
        name = payload.get("name") or payload.get("institution_name")
        short_name = payload.get("short_name")
        if not name or not short_name:
            logger.error("[SQLiteDatabase] Institution requires name and short_name")
            return None

        institution = Institution(
            id=institution_id,
            name=name,
            short_name=short_name.upper(),
            website_url=payload.get("website_url"),
            created_by=payload.get("created_by"),
            admin_email=(payload.get("admin_email") or "").lower(),
            allow_self_registration=payload.get("allow_self_registration", False),
            require_email_verification=payload.get("require_email_verification", True),
            is_active=payload.get("is_active", True),
            extras={**payload, "institution_id": institution_id},
        )

        with self.sqlite.session_scope() as session:
            session.add(institution)
            logger.info("[SQLiteDatabase] Created institution %s", institution_id)

        # Automatically create default program for the institution
        default_program_data = {
            "name": f"{short_name} Default Program",
            "institution_id": institution_id,
            "is_default": True,
        }
        default_program_id = self.create_program(default_program_data)
        if default_program_id:
            logger.info(
                "[SQLiteDatabase] Created default program %s for institution %s",
                default_program_id,
                institution_id,
            )
        else:
            logger.warning(
                "[SQLiteDatabase] Failed to create default program for institution %s",
                institution_id,
            )

        return institution_id

    def get_institution_by_id(self, institution_id: str) -> Optional[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            inst = session.get(Institution, institution_id)
            return to_dict(inst) if inst else None

    def get_all_institutions(self) -> List[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            records = (
                session.execute(
                    select(Institution).where(Institution.is_active.is_(True))
                )
                .scalars()
                .all()
            )
            return [to_dict(record) for record in records]

    def create_default_mocku_institution(self) -> Optional[str]:
        existing = self.get_institution_by_short_name("MockU")
        if existing:
            return existing["institution_id"]

        mocku_payload = {
            "name": "Mock University",
            "short_name": "MockU",
            "domain": "mocku.test",
            "timezone": DEFAULT_INSTITUTION_TIMEZONE,
            "is_active": True,
            "billing_settings": {
                "instructor_seat_limit": 100,
                "current_instructor_count": 0,
                "subscription_status": "active",
            },
            "settings": {
                "default_credit_hours": 3,
                "academic_year_start_month": 8,
                "grading_scale": "traditional",
            },
            "created_at": datetime.now(timezone.utc),
        }
        return self.create_institution(mocku_payload)

    def create_new_institution(
        self, institution_data: Dict[str, Any], admin_user_data: Dict[str, Any]
    ) -> Optional[Tuple[str, str]]:
        institution_id = self.create_institution(institution_data)
        if not institution_id:
            return None

        user_payload = dict(admin_user_data)
        user_payload.setdefault("institution_id", institution_id)
        user_id = self.create_user(user_payload)
        if not user_id:
            return None
        return institution_id, user_id

    def create_new_institution_simple(
        self, name: str, short_name: str, active: bool = True
    ) -> Optional[str]:
        """Create a new institution without creating an admin user (site admin workflow)"""
        institution_data = {
            "name": name,
            "short_name": short_name,
            "active": active,
        }
        return self.create_institution(institution_data)

    def get_institution_instructor_count(self, institution_id: str) -> int:
        with self.sqlite.session_scope() as session:
            return (
                session.execute(
                    select(func.count(User.id)).where(
                        and_(
                            User.institution_id == institution_id,
                            User.role == "instructor",
                        )
                    )
                ).scalar()
                or 0
            )

    def get_institution_by_short_name(
        self, short_name: str
    ) -> Optional[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            record = (
                session.execute(
                    select(Institution).where(
                        func.lower(Institution.short_name) == short_name.lower()
                    )
                )
                .scalars()
                .first()
            )
            return to_dict(record) if record else None

    def update_institution(
        self, institution_id: str, institution_data: Dict[str, Any]
    ) -> bool:
        """Update institution details."""
        try:
            with self.sqlite.session_scope() as session:
                inst = session.get(Institution, institution_id)
                if not inst:
                    return False

                for key, value in institution_data.items():
                    if hasattr(inst, key) and key != "id":
                        setattr(inst, key, value)

                inst.updated_at = datetime.now(timezone.utc)
                return True
        except Exception as e:
            logger.error(f"Failed to update institution: {e}")
            return False

    def delete_institution(self, institution_id: str) -> bool:
        """
        Delete institution (CASCADE deletes all related data).
        WARNING: This is DESTRUCTIVE and IRREVERSIBLE.
        """
        try:
            with self.sqlite.session_scope() as session:
                inst = session.get(Institution, institution_id)
                if not inst:
                    return False
                # SQLAlchemy cascade will handle deletion of related entities
                session.delete(inst)
                return True
        except Exception as e:
            logger.error(f"Failed to delete institution: {e}")
            return False

    # ------------------------------------------------------------------
    # User operations
    # ------------------------------------------------------------------
    def create_user(self, user_data: Dict[str, Any]) -> Optional[str]:
        payload = dict(user_data)
        # Accept both "id" and "user_id" for backward compatibility
        user_id = _ensure_uuid(payload.pop("id", None) or payload.pop("user_id", None))
        email = payload.get("email")
        if not email:
            logger.error("[SQLiteDatabase] User requires email")
            return None

        user = User(
            id=user_id,
            email=email.lower(),
            password_hash=payload.get("password_hash"),
            first_name=payload.get("first_name", ""),
            last_name=payload.get("last_name", ""),
            display_name=payload.get("display_name"),
            account_status=payload.get("account_status", "pending"),
            email_verified=payload.get("email_verified", False),
            email_verification_token=payload.get("email_verification_token"),
            email_verification_sent_at=payload.get("email_verification_sent_at"),
            role=payload.get("role", "instructor"),
            institution_id=payload.get("institution_id"),
            login_attempts=payload.get("login_attempts", 0),
            locked_until=payload.get("locked_until"),
            last_login_at=payload.get("last_login_at"),
            invited_by=payload.get("invited_by"),
            invited_at=payload.get("invited_at"),
            registration_completed_at=payload.get("registration_completed_at"),
            oauth_provider=payload.get("oauth_provider"),
            oauth_id=payload.get("oauth_id"),
            password_reset_token=payload.get("password_reset_token"),
            password_reset_expires_at=payload.get("password_reset_expires_at"),
            extras={**payload, "user_id": user_id},
        )

        with self.sqlite.session_scope() as session:
            existing = (
                session.execute(select(User).where(User.email == user.email))
                .scalars()
                .first()
            )
            if existing:
                logger.error("[SQLiteDatabase] Duplicate email %s", user.email)
                return None
            session.add(user)
            program_ids = payload.get("program_ids") or []
            if program_ids:
                programs = (
                    session.execute(select(Program).where(Program.id.in_(program_ids)))
                    .scalars()
                    .all()
                )
                user.programs = programs
            logger.info("[SQLiteDatabase] Created user %s", user_id)
            return user_id

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            record = (
                session.execute(select(User).where(User.email == email.lower()))
                .scalars()
                .first()
            )
            return to_dict(record) if record else None

    def get_user_by_reset_token(self, reset_token: str) -> Optional[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            record = (
                session.execute(
                    select(User).where(User.password_reset_token == reset_token)
                )
                .scalars()
                .first()
            )
            return to_dict(record) if record else None

    def get_all_users(self, institution_id: str) -> List[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            records = (
                session.execute(
                    select(User).where(User.institution_id == institution_id)
                )
                .scalars()
                .all()
            )
            return [to_dict(user) for user in records]

    def get_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            records = (
                session.execute(select(User).where(User.role == role)).scalars().all()
            )
            return [to_dict(user) for user in records]

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            user = session.get(User, user_id)
            return to_dict(user) if user else None

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Alias for get_user_by_id"""
        return self.get_user_by_id(user_id)

    def update_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        with self.sqlite.session_scope() as session:
            user = session.get(User, user_id)
            if not user:
                logger.warning(f"[UPDATE_USER] User {user_id} not found in database")
                return False
            logger.info(
                f"[UPDATE_USER] Updating user {user_id}: {list(user_data.keys())}"
            )
            for key, value in user_data.items():
                if key == "program_ids":
                    programs = (
                        session.execute(
                            select(Program).where(Program.id.in_(value or []))
                        )
                        .scalars()
                        .all()
                    )
                    user.programs = programs
                elif hasattr(User, key):
                    setattr(user, key, value)
                user.extras[key] = value
            user.updated_at = datetime.now(timezone.utc)
            return True

    def update_user_active_status(self, user_id: str, active_user: bool) -> bool:
        status = "active" if active_user else "inactive"
        return self.update_user(user_id, {"account_status": status})

    def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """
        Update user profile fields only (first_name, last_name, display_name).
        Used for self-service profile updates by users.
        """
        allowed_fields = ["first_name", "last_name", "display_name"]
        filtered_data = {k: v for k, v in profile_data.items() if k in allowed_fields}
        if not filtered_data:
            return False
        return self.update_user(user_id, filtered_data)

    def update_user_role(
        self, user_id: str, new_role: str, program_ids: Optional[List[str]] = None
    ) -> bool:
        """
        Update user's role and program associations.
        Used by admins to change user roles and assignments.
        """
        update_data: Dict[str, Any] = {"role": new_role}
        if program_ids is not None:
            update_data["program_ids"] = program_ids
        return self.update_user(user_id, update_data)

    def deactivate_user(self, user_id: str) -> bool:
        """
        Soft delete: Mark user account as suspended.
        Preserves user data for audit trail while preventing login.
        """
        return self.update_user(user_id, {"account_status": "suspended"})

    def calculate_and_update_active_users(self, institution_id: str) -> int:
        with self.sqlite.session_scope() as session:
            count = (
                session.execute(
                    select(func.count(User.id)).where(
                        and_(
                            User.institution_id == institution_id,
                            User.account_status == "active",
                        )
                    )
                ).scalar()
                or 0
            )
            institution = session.get(Institution, institution_id)
            if institution:
                extras = institution.extras or {}
                billing = extras.get("billing_settings", {})
                billing["current_instructor_count"] = count
                extras["billing_settings"] = billing
                institution.extras = extras
            return count

    def update_user_extended(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        return self.update_user(user_id, update_data)

    def get_user_by_verification_token(self, token: str) -> Optional[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            user = (
                session.execute(
                    select(User).where(User.email_verification_token == token)
                )
                .scalars()
                .first()
            )
            return to_dict(user) if user else None

    # ------------------------------------------------------------------
    # Course operations
    # ------------------------------------------------------------------
    def create_course(self, course_data: Dict[str, Any]) -> Optional[str]:
        payload = dict(course_data)
        course_id = _ensure_uuid(payload.pop("course_id", None))
        course = Course(
            id=course_id,
            course_number=payload.get("course_number", "").upper(),
            course_title=payload.get("course_title", ""),
            department=payload.get("department"),
            credit_hours=payload.get("credit_hours", 3),
            institution_id=payload.get("institution_id"),
            active=payload.get("active", True),
            extras={**payload, "course_id": course_id},
        )

        with self.sqlite.session_scope() as session:
            session.add(course)
            program_ids = payload.get("program_ids") or []
            if program_ids:
                programs = (
                    session.execute(select(Program).where(Program.id.in_(program_ids)))
                    .scalars()
                    .all()
                )
                course.programs = programs
            logger.info("[SQLiteDatabase] Created course %s", course_id)
            return course_id

    def update_course(self, course_id: str, course_data: Dict[str, Any]) -> bool:
        """Update course details."""
        try:
            with self.sqlite.session_scope() as session:
                course = session.get(Course, course_id)
                if not course:
                    return False

                # Handle program associations separately
                if "program_ids" in course_data:
                    program_ids = course_data.pop("program_ids")
                    if program_ids is not None:
                        programs = (
                            session.execute(
                                select(Program).where(Program.id.in_(program_ids))
                            )
                            .scalars()
                            .all()
                        )
                        course.programs = list(programs)

                # Update regular fields
                for key, value in course_data.items():
                    if hasattr(course, key) and key != "id":
                        setattr(course, key, value)

                course.updated_at = datetime.now(timezone.utc)
                return True
        except Exception as e:
            logger.error(f"Failed to update course: {e}")
            return False

    def update_course_programs(self, course_id: str, program_ids: List[str]) -> bool:
        """Update course-program associations."""
        return self.update_course(course_id, {"program_ids": program_ids})

    def delete_course(self, course_id: str) -> bool:
        """Delete course (CASCADE deletes offerings, sections)."""
        try:
            with self.sqlite.session_scope() as session:
                course = session.get(Course, course_id)
                if not course:
                    return False
                session.delete(course)
                return True
        except Exception as e:
            logger.error(f"Failed to delete course: {e}")
            return False

    def get_course_by_number(
        self, course_number: str, institution_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            query = select(Course).where(
                func.upper(Course.course_number) == course_number.upper()
            )
            if institution_id:
                query = query.where(Course.institution_id == institution_id)

            record = session.execute(query).scalars().first()
            return to_dict(record) if record else None

    def get_courses_by_department(
        self, institution_id: str, department: str
    ) -> List[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            records = (
                session.execute(
                    select(Course).where(
                        and_(
                            Course.institution_id == institution_id,
                            Course.department == department,
                        )
                    )
                )
                .scalars()
                .all()
            )
            return [to_dict(course) for course in records]

    def create_course_outcome(self, outcome_data: Dict[str, Any]) -> str:
        payload = dict(outcome_data)
        outcome_id = _ensure_uuid(payload.pop("outcome_id", None))

        # Build extras dict, excluding non-JSON-serializable fields (datetime, etc.)
        # and fields already stored in dedicated columns
        exclude_fields = {
            "outcome_id",
            "course_id",
            "clo_number",
            "description",
            "assessment_method",
            "active",
            "status",
            "students_took",
            "students_passed",
            "assessment_tool",
            "created_at",
            "last_modified",
            "updated_at",
        }
        extras_dict = {k: v for k, v in payload.items() if k not in exclude_fields}
        extras_dict["outcome_id"] = outcome_id

        outcome = CourseOutcome(
            id=outcome_id,
            course_id=payload.get("course_id"),
            clo_number=payload.get("clo_number"),
            description=payload.get("description", ""),
            assessment_method=payload.get("assessment_method"),
            active=payload.get("active", True),
            status=payload.get("status", "unassigned"),
            # New CLO assessment fields (corrected from demo feedback)
            students_took=payload.get("students_took"),
            students_passed=payload.get("students_passed"),
            assessment_tool=payload.get("assessment_tool"),
            extras=extras_dict,
        )

        with self.sqlite.session_scope() as session:
            session.add(outcome)
            return outcome_id

    def update_course_outcome(
        self, outcome_id: str, outcome_data: Dict[str, Any]
    ) -> bool:
        """Update course outcome details."""
        try:
            with self.sqlite.session_scope() as session:
                outcome = session.get(CourseOutcome, outcome_id)
                if not outcome:
                    return False

                for key, value in outcome_data.items():
                    if hasattr(outcome, key) and key != "id":
                        setattr(outcome, key, value)

                outcome.last_modified = datetime.now(timezone.utc)
                return True
        except Exception as e:
            logger.error(f"Failed to update outcome: {e}")
            return False

    def update_outcome_assessment(
        self,
        outcome_id: str,
        students_took: Optional[int] = None,
        students_passed: Optional[int] = None,
        assessment_tool: Optional[str] = None,
    ) -> bool:
        """Update outcome assessment data (corrected field names from demo feedback)."""
        update_data: Dict[str, Any] = {}
        if students_took is not None:
            update_data["students_took"] = students_took
        if students_passed is not None:
            update_data["students_passed"] = students_passed
        if assessment_tool is not None:
            update_data["assessment_tool"] = assessment_tool
        return self.update_course_outcome(outcome_id, update_data)

    def delete_course_outcome(self, outcome_id: str) -> bool:
        """Delete course outcome."""
        try:
            with self.sqlite.session_scope() as session:
                outcome = session.get(CourseOutcome, outcome_id)
                if not outcome:
                    return False
                session.delete(outcome)
                return True
        except Exception as e:
            logger.error(f"Failed to delete outcome: {e}")
            return False

    def get_course_outcomes(self, course_id: str) -> List[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            outcomes = (
                session.execute(
                    select(CourseOutcome).where(CourseOutcome.course_id == course_id)
                )
                .scalars()
                .all()
            )
            return [to_dict(outcome) for outcome in outcomes]

    def get_course_outcome(self, outcome_id: str) -> Optional[Dict[str, Any]]:
        """Get single course outcome by ID (includes students_took, students_passed, assessment_tool)"""
        with self.sqlite.session_scope() as session:
            outcome = session.get(CourseOutcome, outcome_id)
            return to_dict(outcome) if outcome else None

    def get_outcomes_by_status(
        self,
        institution_id: str,
        status: str,
        program_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get course outcomes filtered by status."""
        with self.sqlite.session_scope() as session:
            # Build query with joins to get institution filtering
            query = (
                select(CourseOutcome)
                .join(Course, CourseOutcome.course_id == Course.id)
                .where(
                    and_(
                        Course.institution_id == institution_id,
                        CourseOutcome.status == status,
                    )
                )
            )

            # Add program filter if specified (Course has many-to-many relationship with Program)
            if program_id:
                from models_sql import course_program_table

                query = query.join(
                    course_program_table, Course.id == course_program_table.c.course_id
                ).where(course_program_table.c.program_id == program_id)

            outcomes = session.execute(query).scalars().all()
            return [to_dict(outcome) for outcome in outcomes]

    def get_sections_by_course(self, course_id: str) -> List[Dict[str, Any]]:
        """Get all course sections for a given course."""
        with self.sqlite.session_scope() as session:
            # Get sections through course offering
            sections = (
                session.execute(
                    select(CourseSection)
                    .join(
                        CourseOffering, CourseSection.offering_id == CourseOffering.id
                    )
                    .where(CourseOffering.course_id == course_id)
                )
                .scalars()
                .all()
            )
            return [to_dict(section) for section in sections]

    def get_course_by_id(self, course_id: str) -> Optional[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            course = session.get(Course, course_id)
            return to_dict(course) if course else None

    def get_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Alias for get_course_by_id"""
        return self.get_course_by_id(course_id)

    def get_all_courses(self, institution_id: str) -> List[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            courses = (
                session.execute(
                    select(Course)
                    .where(Course.institution_id == institution_id)
                    .options(selectinload(Course.programs))
                )
                .scalars()
                .all()
            )
            return [to_dict(course) for course in courses]

    def get_all_instructors(self, institution_id: str) -> List[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            instructors = (
                session.execute(
                    select(User).where(
                        and_(
                            User.institution_id == institution_id,
                            User.role == "instructor",
                        )
                    )
                )
                .scalars()
                .all()
            )
            return [to_dict(user) for user in instructors]

    def get_all_sections(self, institution_id: str) -> List[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            sections = (
                session.execute(
                    select(CourseSection)
                    .join(CourseOffering)
                    .where(CourseOffering.institution_id == institution_id)
                )
                .scalars()
                .all()
            )

            # Enrich sections with related data using separate queries
            enriched_sections = []

            for i, section in enumerate(sections):
                section_dict = to_dict(section)

                # Get offering details to find course and term
                offering = session.get(CourseOffering, section.offering_id)

                if offering:
                    # Add course_id for easy filtering (e.g., in assessment UI)
                    section_dict["course_id"] = offering.course_id
                    section_dict["term_id"] = offering.term_id

                    # Get course details
                    course = session.get(Course, offering.course_id)
                    if course:
                        section_dict["course_number"] = course.course_number
                        section_dict["course_title"] = course.course_title

                    # Get term details
                    term = session.get(Term, offering.term_id)
                    if term:
                        section_dict["term_name"] = term.term_name

                # Get instructor details if assigned
                if section.instructor_id:
                    instructor = session.get(User, section.instructor_id)
                    if instructor:
                        section_dict["instructor_name"] = (
                            f"{instructor.first_name} {instructor.last_name}"
                        )

                enriched_sections.append(section_dict)

            return enriched_sections

    def get_section_by_id(self, section_id: str) -> Optional[Dict[str, Any]]:
        """Get single section by ID"""
        with self.sqlite.session_scope() as session:
            section = session.get(CourseSection, section_id)
            return to_dict(section) if section else None

    def create_course_offering(self, offering_data: Dict[str, Any]) -> Optional[str]:
        payload = dict(offering_data)
        offering_id = _ensure_uuid(payload.pop("offering_id", None))
        offering = CourseOffering(
            id=offering_id,
            course_id=payload.get("course_id"),
            term_id=payload.get("term_id"),
            institution_id=payload.get("institution_id"),
            status=payload.get("status", "active"),
            capacity=payload.get("capacity"),
            total_enrollment=payload.get("total_enrollment", 0),
            section_count=payload.get("section_count", 0),
            extras={**payload, "offering_id": offering_id},
        )
        with self.sqlite.session_scope() as session:
            session.add(offering)
            return offering_id

    def update_course_offering(
        self, offering_id: str, offering_data: Dict[str, Any]
    ) -> bool:
        """Update course offering details."""
        try:
            with self.sqlite.session_scope() as session:
                offering = session.get(CourseOffering, offering_id)
                if not offering:
                    return False

                for key, value in offering_data.items():
                    if hasattr(offering, key) and key != "id":
                        setattr(offering, key, value)

                offering.updated_at = datetime.now(timezone.utc)
                return True
        except Exception as e:
            logger.error(f"Failed to update offering: {e}")
            return False

    def delete_course_offering(self, offering_id: str) -> bool:
        """Delete course offering (CASCADE deletes sections)."""
        try:
            with self.sqlite.session_scope() as session:
                offering = session.get(CourseOffering, offering_id)
                if not offering:
                    return False
                session.delete(offering)
                return True
        except Exception as e:
            logger.error(f"Failed to delete offering: {e}")
            return False

    def get_course_offering(self, offering_id: str) -> Optional[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            offering = session.get(CourseOffering, offering_id)
            return to_dict(offering) if offering else None

    def get_course_offering_by_course_and_term(
        self, course_id: str, term_id: str
    ) -> Optional[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            offering = (
                session.execute(
                    select(CourseOffering).where(
                        and_(
                            CourseOffering.course_id == course_id,
                            CourseOffering.term_id == term_id,
                        )
                    )
                )
                .scalars()
                .first()
            )
            return to_dict(offering) if offering else None

    def get_all_course_offerings(self, institution_id: str) -> List[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            offerings = (
                session.execute(
                    select(CourseOffering).where(
                        CourseOffering.institution_id == institution_id
                    )
                )
                .scalars()
                .all()
            )
            return [to_dict(offering) for offering in offerings]

    # ------------------------------------------------------------------
    # Term operations
    # ------------------------------------------------------------------
    def create_term(self, term_data: Dict[str, Any]) -> Optional[str]:
        payload = dict(term_data)
        term_id = _ensure_uuid(payload.pop("term_id", None))
        term_name = payload.get("term_name")
        if not term_name:
            logger.error("[SQLiteDatabase] term_name is required")
            return None
        term = Term(
            id=term_id,
            term_name=term_name,
            name=payload.get("name", term_name),
            start_date=payload.get("start_date"),
            end_date=payload.get("end_date"),
            assessment_due_date=payload.get("assessment_due_date"),
            active=payload.get("active", True),
            institution_id=payload.get("institution_id"),
            extras={**payload, "term_id": term_id},
        )
        with self.sqlite.session_scope() as session:
            session.add(term)
            return term_id

    def update_term(self, term_id: str, term_data: Dict[str, Any]) -> bool:
        """Update term details."""
        try:
            with self.sqlite.session_scope() as session:
                term = session.get(Term, term_id)
                if not term:
                    return False

                for key, value in term_data.items():
                    if hasattr(term, key) and key != "id":
                        setattr(term, key, value)

                term.updated_at = datetime.now(timezone.utc)
                return True
        except Exception as e:
            logger.error(f"Failed to update term: {e}")
            return False

    def archive_term(self, term_id: str) -> bool:
        """Archive term (soft delete - set active=False)."""
        return self.update_term(term_id, {"active": False})

    def delete_term(self, term_id: str) -> bool:
        """Delete term (CASCADE deletes offerings and sections)."""
        try:
            with self.sqlite.session_scope() as session:
                term = session.get(Term, term_id)
                if not term:
                    return False
                session.delete(term)
                return True
        except Exception as e:
            logger.error(f"Failed to delete term: {e}")
            return False

    def get_term_by_name(
        self, name: str, institution_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            filters = [Term.term_name == name]
            if institution_id is not None:
                filters.append(Term.institution_id == institution_id)

            term = session.execute(select(Term).where(and_(*filters))).scalars().first()
            return to_dict(term) if term else None

    def get_active_terms(self, institution_id: str) -> List[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            terms = (
                session.execute(
                    select(Term).where(
                        and_(
                            Term.institution_id == institution_id,
                            Term.active.is_(True),
                        )
                    )
                )
                .scalars()
                .all()
            )
            return [to_dict(term) for term in terms]

    def get_term_by_id(self, term_id: str) -> Optional[Dict[str, Any]]:
        """Get single term by ID"""
        with self.sqlite.session_scope() as session:
            term = session.get(Term, term_id)
            return to_dict(term) if term else None

    def get_sections_by_term(self, term_id: str) -> List[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            sections = (
                session.execute(
                    select(CourseSection)
                    .join(CourseOffering)
                    .where(CourseOffering.term_id == term_id)
                )
                .scalars()
                .all()
            )
            return [to_dict(section) for section in sections]

    # ------------------------------------------------------------------
    # Section operations
    # ------------------------------------------------------------------
    def create_course_section(self, section_data: Dict[str, Any]) -> Optional[str]:
        payload = dict(section_data)
        section_id = _ensure_uuid(payload.pop("section_id", None))
        section = CourseSection(
            id=section_id,
            offering_id=payload.get("offering_id"),
            instructor_id=payload.get("instructor_id"),
            section_number=payload.get("section_number", "001"),
            # Enrollment data (pre-populated from feed)
            enrollment=payload.get("enrollment"),
            withdrawals=payload.get("withdrawals", 0),
            # Course-level assessment data (instructor-entered)
            students_passed=payload.get("students_passed"),
            students_dfic=payload.get("students_dfic"),
            cannot_reconcile=payload.get("cannot_reconcile", False),
            reconciliation_note=payload.get("reconciliation_note"),
            # Course-level narratives
            narrative_celebrations=payload.get("narrative_celebrations"),
            narrative_challenges=payload.get("narrative_challenges"),
            narrative_changes=payload.get("narrative_changes"),
            # Workflow fields
            status=payload.get("status", "assigned"),
            due_date=payload.get("due_date"),
            assigned_date=payload.get("assigned_date"),
            completed_date=payload.get("completed_date"),
            extras={**payload, "section_id": section_id},
        )
        with self.sqlite.session_scope() as session:
            session.add(section)
            return section_id

    def update_course_section(
        self, section_id: str, section_data: Dict[str, Any]
    ) -> bool:
        """Update course section details."""
        try:
            with self.sqlite.session_scope() as session:
                section = session.get(CourseSection, section_id)
                if not section:
                    return False

                for key, value in section_data.items():
                    if hasattr(section, key) and key != "id":
                        setattr(section, key, value)

                section.updated_at = datetime.now(timezone.utc)
                return True
        except Exception as e:
            logger.error(f"Failed to update section: {e}")
            return False

    def assign_instructor(self, section_id: str, instructor_id: str) -> bool:
        """Assign instructor to a section."""
        return self.update_course_section(
            section_id,
            {
                "instructor_id": instructor_id,
                "status": "assigned",
                "assigned_date": datetime.now(timezone.utc),
            },
        )

    def delete_course_section(self, section_id: str) -> bool:
        """Delete course section."""
        try:
            with self.sqlite.session_scope() as session:
                section = session.get(CourseSection, section_id)
                if not section:
                    return False
                session.delete(section)
                return True
        except Exception as e:
            logger.error(f"Failed to delete section: {e}")
            return False

    def get_sections_by_instructor(self, instructor_id: str) -> List[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            sections = (
                session.execute(
                    select(CourseSection).where(
                        CourseSection.instructor_id == instructor_id
                    )
                )
                .scalars()
                .all()
            )

            # Enrich sections with related data (same as get_all_sections)
            enriched_sections = []

            for section in sections:
                section_dict = to_dict(section)

                # Get offering details to find course and term
                offering = session.get(CourseOffering, section.offering_id)

                if offering:
                    # Add course_id for easy filtering (e.g., in assessment UI)
                    section_dict["course_id"] = offering.course_id
                    section_dict["term_id"] = offering.term_id

                    # Get course details
                    course = session.get(Course, offering.course_id)
                    if course:
                        section_dict["course_number"] = course.course_number
                        section_dict["course_title"] = course.course_title

                    # Get term details
                    term = session.get(Term, offering.term_id)
                    if term:
                        section_dict["term_name"] = term.term_name

                # Get instructor details if assigned (though we know it's this instructor)
                if section.instructor_id:
                    instructor = session.get(User, section.instructor_id)
                    if instructor:
                        section_dict["instructor_name"] = (
                            f"{instructor.first_name} {instructor.last_name}"
                        )

                enriched_sections.append(section_dict)

            return enriched_sections

    # ------------------------------------------------------------------
    # Program operations
    # ------------------------------------------------------------------
    def create_program(self, program_data: Dict[str, Any]) -> Optional[str]:
        payload = dict(program_data)
        program_id = _ensure_uuid(payload.pop("program_id", None))
        program = Program(
            id=program_id,
            name=payload.get("name", ""),
            short_name=payload.get("short_name", "").upper(),
            description=payload.get("description"),
            institution_id=payload.get("institution_id"),
            created_by=payload.get("created_by"),
            is_default=payload.get("is_default", False),
            is_active=payload.get("is_active", True),
            extras={**payload, "program_id": program_id},
        )
        with self.sqlite.session_scope() as session:
            session.add(program)
            return program_id

    def get_programs_by_institution(self, institution_id: str) -> List[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            programs = (
                session.execute(
                    select(Program).where(Program.institution_id == institution_id)
                )
                .scalars()
                .all()
            )
            return [to_dict(program) for program in programs]

    def get_program_by_id(self, program_id: str) -> Optional[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            program = session.get(Program, program_id)
            return to_dict(program) if program else None

    def link_course_to_program(self, course_id: str, program_id: str) -> bool:
        """
        Link a course to a program.

        Args:
            course_id: Course ID
            program_id: Program ID

        Returns:
            True if linked successfully (or already linked), False on database error
        """
        from models_sql import course_program_table

        try:
            with self.sqlite.session_scope() as session:
                # Check if link already exists
                existing = session.execute(
                    select(course_program_table).where(
                        course_program_table.c.course_id == course_id,
                        course_program_table.c.program_id == program_id,
                    )
                ).first()

                if existing:
                    return True  # Already linked

                # Create link
                session.execute(
                    course_program_table.insert().values(
                        course_id=course_id, program_id=program_id
                    )
                )
                return True
        except Exception as e:
            logger.error(
                f"[LINK_COURSE_PROGRAM] Failed to link course {course_id} to program {program_id}: {e}"
            )
            return False

    def get_program_by_name_and_institution(
        self, program_name: str, institution_id: str
    ) -> Optional[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            program = (
                session.execute(
                    select(Program).where(
                        and_(
                            Program.institution_id == institution_id,
                            func.lower(Program.name) == program_name.lower(),
                        )
                    )
                )
                .scalars()
                .first()
            )
            return to_dict(program) if program else None

    def update_program(self, program_id: str, updates: Dict[str, Any]) -> bool:
        with self.sqlite.session_scope() as session:
            program = session.get(Program, program_id)
            if not program:
                return False
            for key, value in updates.items():
                if hasattr(Program, key):
                    setattr(program, key, value)
                program.extras[key] = value
            program.updated_at = datetime.now(timezone.utc)
            return True

    def delete_program(self, program_id: str, reassign_to_program_id: str) -> bool:
        with self.sqlite.session_scope() as session:
            program = session.get(Program, program_id)
            if not program:
                return False
            reassignment = session.get(Program, reassign_to_program_id)
            if not reassignment:
                return False
            for course in list(program.courses):
                if course not in reassignment.courses:
                    reassignment.courses.append(course)
            session.delete(program)
            return True

    def get_courses_by_program(self, program_id: str) -> List[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            program = session.get(Program, program_id)
            if not program:
                return []
            return [to_dict(course) for course in program.courses]

    def get_unassigned_courses(self, institution_id: str) -> List[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            courses = (
                session.execute(
                    select(Course)
                    .outerjoin(
                        course_program_table,
                        Course.id == course_program_table.c.course_id,
                    )
                    .where(
                        and_(
                            Course.institution_id == institution_id,
                            course_program_table.c.program_id.is_(None),
                        )
                    )
                )
                .scalars()
                .all()
            )
            return [to_dict(course) for course in courses]

    def assign_course_to_default_program(
        self, course_id: str, institution_id: str
    ) -> bool:
        with self.sqlite.session_scope() as session:
            default_program = (
                session.execute(
                    select(Program).where(
                        and_(
                            Program.institution_id == institution_id,
                            Program.is_default.is_(True),
                        )
                    )
                )
                .scalars()
                .first()
            )
            if not default_program:
                return False
            course = session.get(Course, course_id)
            if not course:
                return False
            if course not in default_program.courses:
                default_program.courses.append(course)
            return True

    def add_course_to_program(self, course_id: str, program_id: str) -> bool:
        with self.sqlite.session_scope() as session:
            course = session.get(Course, course_id)
            program = session.get(Program, program_id)
            if not course or not program:
                return False
            if course not in program.courses:
                program.courses.append(course)
            return True

    def remove_course_from_program(self, course_id: str, program_id: str) -> bool:
        with self.sqlite.session_scope() as session:
            course = session.get(Course, course_id)
            program = session.get(Program, program_id)
            if not course or not program:
                return False
            if course in program.courses:
                program.courses.remove(course)
            return True

    def bulk_add_courses_to_program(
        self, course_ids: List[str], program_id: str
    ) -> Dict[str, Any]:
        success_count = 0
        failures: List[str] = []
        for course_id in course_ids:
            if self.add_course_to_program(course_id, program_id):
                success_count += 1
            else:
                failures.append(course_id)
        return {"added": success_count, "failed": failures}

    def bulk_remove_courses_from_program(
        self, course_ids: List[str], program_id: str
    ) -> Dict[str, Any]:
        success_count = 0
        failures: List[str] = []
        for course_id in course_ids:
            if self.remove_course_from_program(course_id, program_id):
                success_count += 1
            else:
                failures.append(course_id)
        return {"removed": success_count, "failed": failures}

    # ------------------------------------------------------------------
    # Invitation operations
    # ------------------------------------------------------------------
    def create_invitation(self, invitation_data: Dict[str, Any]) -> Optional[str]:
        payload = dict(invitation_data)
        invitation_id = _ensure_uuid(payload.pop("invitation_id", None))

        # Build extras dict, excluding non-JSON-serializable fields (datetime, etc.)
        # and fields already stored in dedicated columns
        exclude_fields = {
            "invitation_id",
            "email",
            "role",
            "institution_id",
            "token",
            "invited_by",
            "invited_at",
            "expires_at",
            "status",
            "accepted_at",
            "personal_message",
            "created_at",
            "updated_at",
        }
        extras_dict = {k: v for k, v in payload.items() if k not in exclude_fields}
        extras_dict["invitation_id"] = invitation_id

        invitation = UserInvitation(
            id=invitation_id,
            email=payload.get("email", "").lower(),
            role=payload.get("role", "instructor"),
            institution_id=payload.get("institution_id"),
            token=payload.get("token", str(uuid.uuid4())),
            invited_by=payload.get("invited_by"),
            invited_at=payload.get("invited_at", datetime.now(timezone.utc)),
            expires_at=payload.get("expires_at"),
            status=payload.get("status", "pending"),
            accepted_at=payload.get("accepted_at"),
            personal_message=payload.get("personal_message"),
            extras=extras_dict,
        )
        with self.sqlite.session_scope() as session:
            session.add(invitation)
            session.flush()  # Ensure invitation is immediately visible to subsequent queries
            return invitation_id

    def get_invitation_by_id(self, invitation_id: str) -> Optional[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            invitation = session.get(UserInvitation, invitation_id)
            return to_dict(invitation) if invitation else None

    def get_invitation_by_token(
        self, invitation_token: str
    ) -> Optional[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            invitation = (
                session.execute(
                    select(UserInvitation).where(
                        UserInvitation.token == invitation_token
                    )
                )
                .scalars()
                .first()
            )
            return to_dict(invitation) if invitation else None

    def get_invitation_by_email(
        self, email: str, institution_id: str
    ) -> Optional[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            invitation = (
                session.execute(
                    select(UserInvitation)
                    .where(
                        and_(
                            UserInvitation.email == email.lower(),
                            UserInvitation.institution_id == institution_id,
                        )
                    )
                    .order_by(UserInvitation.created_at.desc())
                )
                .scalars()
                .first()
            )
            return to_dict(invitation) if invitation else None

    def update_invitation(self, invitation_id: str, updates: Dict[str, Any]) -> bool:
        with self.sqlite.session_scope() as session:
            # Use query for string UUID primary key instead of session.get()
            invitation = session.execute(
                select(UserInvitation).where(UserInvitation.id == invitation_id)
            ).scalar_one_or_none()
            if not invitation:
                return False
            for key, value in updates.items():
                if hasattr(UserInvitation, key):
                    setattr(invitation, key, value)
                else:
                    logger.warning(
                        "[SQLiteDatabase] Unknown attribute '%s' for UserInvitation; storing in extras.",
                        key,
                    )
                    invitation.extras[key] = value
            invitation.updated_at = datetime.now(timezone.utc)
            return True

    def list_invitations(
        self, institution_id: str, status: Optional[str], limit: int, offset: int
    ) -> List[Dict[str, Any]]:
        with self.sqlite.session_scope() as session:
            query = select(UserInvitation).where(
                UserInvitation.institution_id == institution_id
            )
            if status:
                query = query.where(UserInvitation.status == status)
            query = query.order_by(UserInvitation.invited_at.desc())
            invitations = (
                session.execute(query.offset(offset).limit(limit)).scalars().all()
            )
            return [to_dict(invitation) for invitation in invitations]

    # ------------------------------------------------------------------
    # Audit log operations
    # ------------------------------------------------------------------
    def create_audit_log(self, audit_data: Dict[str, Any]) -> bool:
        """Create audit log entry."""
        from models_sql import AuditLog

        try:
            with self.sqlite.session_scope() as session:
                audit_log = AuditLog(**audit_data)
                session.add(audit_log)
                return True
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            return False

    def get_audit_logs_by_entity(
        self, entity_type: str, entity_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get audit history for specific entity."""
        from models_sql import AuditLog

        try:
            with self.sqlite.session_scope() as session:
                query = select(AuditLog).where(
                    AuditLog.entity_type == entity_type,
                    AuditLog.entity_id == entity_id,
                )
                query = query.order_by(AuditLog.timestamp.desc()).limit(limit)
                logs = session.execute(query).scalars().all()
                return [self._audit_log_to_dict(log) for log in logs]
        except Exception as e:
            logger.error(f"Failed to get entity audit logs: {e}")
            return []

    def get_audit_logs_by_user(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get all activity by specific user."""
        from models_sql import AuditLog

        try:
            with self.sqlite.session_scope() as session:
                query = select(AuditLog).where(AuditLog.user_id == user_id)

                if start_date:
                    query = query.where(AuditLog.timestamp >= start_date)
                if end_date:
                    query = query.where(AuditLog.timestamp <= end_date)

                query = query.order_by(AuditLog.timestamp.desc()).limit(limit)
                logs = session.execute(query).scalars().all()
                return [self._audit_log_to_dict(log) for log in logs]
        except Exception as e:
            logger.error(f"Failed to get user audit logs: {e}")
            return []

    def get_recent_audit_logs(
        self, institution_id: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent system activity."""
        from models_sql import AuditLog

        try:
            with self.sqlite.session_scope() as session:
                query = select(AuditLog)

                if institution_id:
                    query = query.where(AuditLog.institution_id == institution_id)

                query = query.order_by(AuditLog.timestamp.desc()).limit(limit)
                logs = session.execute(query).scalars().all()
                return [self._audit_log_to_dict(log) for log in logs]
        except Exception as e:
            logger.error(f"Failed to get recent audit logs: {e}")
            return []

    def get_audit_logs_filtered(
        self,
        start_date: datetime,
        end_date: datetime,
        entity_type: Optional[str] = None,
        user_id: Optional[str] = None,
        institution_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get filtered audit logs for export."""
        from models_sql import AuditLog

        try:
            with self.sqlite.session_scope() as session:
                query = select(AuditLog).where(
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date,
                )

                if entity_type:
                    query = query.where(AuditLog.entity_type == entity_type)
                if user_id:
                    query = query.where(AuditLog.user_id == user_id)
                if institution_id:
                    query = query.where(AuditLog.institution_id == institution_id)

                query = query.order_by(AuditLog.timestamp.desc())
                logs = session.execute(query).scalars().all()
                return [self._audit_log_to_dict(log) for log in logs]
        except Exception as e:
            logger.error(f"Failed to get filtered audit logs: {e}")
            return []

    def _audit_log_to_dict(self, log: Any) -> Dict[str, Any]:
        """Convert AuditLog model to dictionary."""
        return {
            "audit_id": log.audit_id,
            "timestamp": log.timestamp,
            "user_id": log.user_id,
            "user_email": log.user_email,
            "user_role": log.user_role,
            "operation_type": log.operation_type,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "old_values": log.old_values,
            "new_values": log.new_values,
            "changed_fields": log.changed_fields,
            "source_type": log.source_type,
            "source_details": log.source_details,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "request_id": log.request_id,
            "session_id": log.session_id,
            "institution_id": log.institution_id,
        }

    # ------------------------------------------------------------------
    # Delete operations (for testing/cleanup)
    # ------------------------------------------------------------------
    def delete_user(self, user_id: str) -> bool:
        """Delete a user (for testing purposes)."""
        with self.sqlite.session_scope() as session:
            user = session.get(User, user_id)
            if not user:
                return False
            session.delete(user)
            return True

    def delete_program_simple(self, program_id: str) -> bool:
        """Delete a program without reassignment (for testing purposes)."""
        with self.sqlite.session_scope() as session:
            program = session.get(Program, program_id)
            if not program:
                return False
            session.delete(program)
            return True
