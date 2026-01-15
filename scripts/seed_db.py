#!/usr/bin/env python3
"""
Baseline Database Seeding for E2E Tests

Creates minimal shared infrastructure needed across all E2E tests.
Tests create their own specific data (users, sections) via API calls.
"""

import argparse
import json
import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Typing imports for static analysis
from typing import Any, Dict, List, Optional, Tuple, Union, cast

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import database_service
from src.models.models import (
    Course,
    CourseOffering,
    CourseOutcome,
    CourseSection,
    Institution,
    Program,
    Term,
    User,
)
from src.services.password_service import hash_password
from src.utils.constants import PROGRAM_DEFAULT_DESCRIPTION, SITE_ADMIN_INSTITUTION_ID


class BaselineSeeder(ABC):
    """
    Abstract base class for database seeding operations.

    Provides shared utilities for manifest loading, logging, and database interaction.
    Subclasses implement specific seeding strategies (test vs demo vs production).

    TODO (Future - Phase 2): Move all hardcoded data from subclasses to JSON manifests.
    See SEED_DB_REFACTOR_PLAN.md for migration strategy.
    """

    def __init__(self, manifest_path: Optional[str] = None, env: str = "prod") -> None:
        self.manifest_path = manifest_path
        self.env = env
        self.created: Dict[str, List[Any]] = {
            "institutions": [],
            "users": [],
            "programs": [],
            "terms": [],
            "courses": [],
            "offerings": [],
            "sections": [],
        }

    @staticmethod
    def _coerce_to_str(value: Any) -> Optional[str]:
        """Return a string representation for IDs when possible."""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, int):
            return str(value)
        return None

    def log(self, message: str) -> None:
        """Log with [SEED] prefix"""
        print(f"[SEED] {message}")

    def load_manifest(self, manifest_path: Optional[str]) -> Dict[str, Any]:
        """Load and parse manifest JSON file (shared utility)"""
        if not manifest_path:
            return {}

        try:
            manifest_file = Path(manifest_path)
            if manifest_file.exists():
                self.log(f"📋 Loading manifest from {manifest_path}")
                with open(manifest_file, "r") as f:
                    return json.load(f)
            else:
                self.log(f"⚠️  Manifest not found at {manifest_path}, using defaults")
                return {}
        except Exception as e:
            self.log(f"⚠️  Failed to load manifest: {e}")
            return {}

    def create_institutions_from_manifest(
        self, institutions_data: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Create institutions from manifest data.

        Args:
            institutions_data: List of institution dictionaries

        Returns:
            List of created/existing institution IDs
        """
        institution_ids = []
        for inst_data in institutions_data:
            short_name = inst_data.get("short_name", "")

            # Check if already exists
            existing = database_service.db.get_institution_by_short_name(short_name)  # type: ignore[name-defined]
            if existing:
                institution_ids.append(existing["institution_id"])
                continue

            schema = Institution.create_schema(  # type: ignore[name-defined]
                name=inst_data.get("name", short_name),
                short_name=short_name,
                admin_email=inst_data.get(
                    "admin_email", f"admin@{short_name.lower()}.test"
                ),
                website_url=inst_data.get(
                    "website_url", f"https://{short_name.lower()}.test"
                ),
                created_by="system",
            )
            if inst_data.get("logo_path"):
                schema["logo_path"] = inst_data["logo_path"]

            inst_id = database_service.db.create_institution(schema)  # type: ignore[name-defined]
            if inst_id:
                institution_ids.append(inst_id)
                self.created["institutions"].append(inst_id)
                self.log(f"   ✓ Created institution: {inst_data.get('name')}")

        return institution_ids

    def create_terms_from_manifest(
        self, institution_ids: List[str], terms_data: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Create terms from manifest data.

        Args:
            institution_ids: List of institution IDs to create terms for
            terms_data: List of term dictionaries with name, code, and offset days

        Returns:
            List of created term IDs
        """
        term_ids = []
        base_date = datetime.now(timezone.utc)

        for term_data in terms_data:
            for inst_id in institution_ids:
                # Use explicit dates if provided, else calculate relative to now
                if term_data.get("start_date") and term_data.get("end_date"):
                    # Parse YYYY-MM-DD strings
                    try:
                        # Handle both date-only and full timestamps if necessary
                        sd_str = term_data["start_date"]
                        ed_str = term_data["end_date"]
                        # Create naive datetimes (or timezone aware if needed, standardizing on UTC is safest but inputs are likely naive dates)
                        # We use .fromisoformat which handles YYYY-MM-DD as midnight
                        start_date = datetime.fromisoformat(sd_str)
                        end_date = datetime.fromisoformat(ed_str)
                        # Ensure timezone awareness if base_date is aware (base_date is UTC)
                        if start_date.tzinfo is None:
                            start_date = start_date.replace(tzinfo=timezone.utc)
                        if end_date.tzinfo is None:
                            end_date = end_date.replace(tzinfo=timezone.utc)
                    except ValueError:
                        self.log(
                            f"   ⚠️ Invalid date format for term {term_data.get('name')}, falling back to defaults"
                        )
                        start_date = base_date
                        end_date = base_date + timedelta(days=120)
                else:
                    start_offset = term_data.get("start_offset_days", 0)
                    end_offset = term_data.get("end_offset_days", 120)
                    start_date = base_date + timedelta(days=start_offset)
                    end_date = base_date + timedelta(days=end_offset)

                schema = Term.create_schema(  # type: ignore[name-defined]
                    name=term_data.get("name", "Default Term"),
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    assessment_due_date=end_date.isoformat(),
                )
                schema["term_name"] = term_data.get("name")
                schema["term_code"] = term_data.get("term_code") or term_data.get(
                    "code", ""
                )
                schema["institution_id"] = inst_id

                term_id = database_service.db.create_term(schema)  # type: ignore[name-defined]
                if term_id:
                    term_ids.append(term_id)
                    self.created["terms"].append(term_id)

        self.log(
            f"   ✓ Created {len(term_ids)} terms across {len(institution_ids)} institutions"
        )
        return term_ids

    def create_programs_from_manifest(
        self,
        institution_id_or_ids: Union[str, List[str]],
        programs_data: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Create programs from manifest data.

        Args:
            institution_id_or_ids: Single institution ID or list of institution IDs
            programs_data: List of program dictionaries with 'name', optional 'code', 'description', 'institution_idx'

        Returns:
            List of created program IDs
        """
        # Normalize to list
        raw_institution_ids = (
            institution_id_or_ids
            if isinstance(institution_id_or_ids, list)
            else [institution_id_or_ids]
        )
        institution_ids: List[str] = []
        for inst_id in raw_institution_ids:
            normalized = self._coerce_to_str(inst_id)
            if normalized:
                institution_ids.append(normalized)
        if not institution_ids:
            return []

        program_ids = []
        for prog_data in programs_data:
            # Determine institution - use institution_idx if provided, else first institution
            inst_idx = prog_data.get("institution_idx", 0)
            if inst_idx < len(institution_ids):
                institution_id = institution_ids[inst_idx]
            else:
                institution_id = institution_ids[0]

            schema = Program.create_schema(  # type: ignore[name-defined]
                name=prog_data["name"],
                short_name=prog_data.get("code", prog_data["name"][:4].upper()),
                institution_id=institution_id,
                description=prog_data.get("description", PROGRAM_DEFAULT_DESCRIPTION),
                created_by="system",
            )

            prog_id = database_service.db.create_program(schema)  # type: ignore[name-defined]
            if prog_id:
                program_ids.append(prog_id)
                self.created["programs"].append(prog_id)
                self.log(f"   ✓ Created program: {prog_data['name']}")

        return program_ids

    def create_courses_from_manifest(
        self,
        institution_id_or_ids: Union[str, List[str]],
        courses_data: List[Dict[str, Any]],
        program_ids_or_map: Union[List[str], Dict[str, str]],
    ) -> List[str]:
        """
        Create courses from manifest data.

        Args:
            institution_id_or_ids: Single institution ID or list of institution IDs
            courses_data: List of course dictionaries with 'code', 'name', 'credits', 'program_code' or 'program_idx'
            program_ids_or_map: Either a Dict mapping program codes to IDs, or a List of program IDs

        Returns:
            List of created course IDs
        """
        # Normalize institutions
        raw_institution_ids = (
            institution_id_or_ids
            if isinstance(institution_id_or_ids, list)
            else [institution_id_or_ids]
        )
        institution_ids: List[str] = []
        for inst_id in raw_institution_ids:
            normalized = self._coerce_to_str(inst_id)
            if normalized:
                institution_ids.append(normalized)
        if not institution_ids:
            return []

        # Normalize program reference - can be dict (code->id) or list (by index)
        if isinstance(program_ids_or_map, dict):
            program_map: Optional[Dict[str, str]] = cast(
                Dict[str, str], program_ids_or_map
            )
            program_list: Optional[List[str]] = None
        else:
            program_map = None
            program_list = cast(List[str], program_ids_or_map)

        course_ids = []
        for course_data in courses_data:
            # Resolve program ID
            program_id = None
            if "program_code" in course_data and program_map:
                program_id = program_map.get(course_data["program_code"])
            elif "program_idx" in course_data and program_list:
                idx = course_data["program_idx"]
                if idx < len(program_list):
                    program_id = program_list[idx]

            if not program_id:
                self.log(
                    f"   ⚠️  No program found for course {course_data.get('code')}, skipping"
                )
                continue

            # Get institution from program if we have multiple
            program = database_service.db.get_program_by_id(program_id)
            institution_id = self._coerce_to_str(
                program.get("institution_id") if program else None
            )
            if institution_id is None:
                institution_id = institution_ids[0]

            schema = Course.create_schema(
                course_number=course_data["code"],
                course_title=course_data["name"],
                department=(
                    course_data["code"].split("-")[0]
                    if "-" in course_data["code"]
                    else course_data["code"][:4]
                ),
                institution_id=institution_id,
                credit_hours=course_data.get("credits", 3),
                program_ids=[program_id],
                active=True,
            )

            course_id = database_service.db.create_course(schema)
            if course_id:
                course_ids.append(course_id)
                self.created["courses"].append(course_id)
                self.log(
                    f"   ✓ Created course: {course_data['code']} - {course_data['name']}"
                )

        return course_ids

    def create_users_from_manifest(
        self,
        institution_id_or_ids: Union[str, List[str]],
        users_data: List[Dict[str, Any]],
        program_ids_or_map: Union[Dict[str, str], List[str]],
        default_password_hash: str,
    ) -> List[Optional[str]]:
        """
        Create users from manifest data.

        Args:
            institution_id_or_ids: Single institution ID or list of institution IDs
            users_data: List of user dictionaries with email, first_name, last_name, role
            program_ids_or_map: Dict mapping program codes to IDs, or list of program IDs
            default_password_hash: Hashed password to use for users without password_env_var

        Returns:
            List of created user IDs
        """
        # Normalize institutions
        institution_ids = (
            institution_id_or_ids
            if isinstance(institution_id_or_ids, list)
            else [institution_id_or_ids]
        )

        # Normalize program reference
        program_map = (
            program_ids_or_map if isinstance(program_ids_or_map, dict) else None
        )
        program_list = (
            program_ids_or_map if isinstance(program_ids_or_map, list) else None
        )

        user_ids: List[Optional[str]] = []
        for user_data in users_data:
            # Resolve email (may be from env var)
            email = self._resolve_user_email(user_data)
            if not email:
                user_ids.append(None)  # Maintain index alignment
                continue

            # Skip if user already exists
            existing = database_service.db.get_user_by_email(email)
            if existing:
                user_ids.append(existing["user_id"])
                continue

            # Resolve institution
            inst_idx = user_data.get("institution_idx", 0)
            role = user_data.get("role", "instructor")

            # Site admins use special institution ID
            if role == "site_admin":
                inst_id = str(SITE_ADMIN_INSTITUTION_ID)
            else:
                inst_id = (
                    institution_ids[inst_idx]
                    if inst_idx < len(institution_ids)
                    else institution_ids[0]
                )

            password_hash = self._resolve_user_password_hash(
                user_data, default_password_hash
            )
            program_ids = self._resolve_user_program_ids(
                user_data, program_map, program_list
            )

            schema = User.create_schema(
                email=email,
                first_name=user_data.get("first_name", ""),
                last_name=user_data.get("last_name", ""),
                role=role,
                institution_id=inst_id,
                password_hash=password_hash,
                account_status="active",
                program_ids=program_ids,
            )
            schema["email_verified"] = True
            if user_data.get("system_date_override"):
                try:
                    schema["system_date_override"] = datetime.fromisoformat(
                        user_data["system_date_override"]
                    )
                except ValueError:
                    self.log(
                        f"   ⚠️ Invalid date format for system_date_override: {user_data['system_date_override']}"
                    )

            user_id = database_service.db.create_user(schema)
            if user_id:
                user_ids.append(user_id)
                self.created["users"].append(user_id)
                self.log(
                    f"   ✓ Created user: {user_data.get('first_name')} {user_data.get('last_name')} ({role})"
                )
            else:
                user_ids.append(None)  # Maintain index alignment on creation failure

        return user_ids

    def _resolve_user_email(self, user_data: Dict[str, Any]) -> Optional[str]:
        """Return email from manifest or test credentials env."""
        email = user_data.get("email")
        if email:
            return email
        env_key = user_data.get("email_env_var")
        if not env_key:
            return None

        try:
            from tests import test_credentials  # Local import to avoid cycles

            return getattr(test_credentials, env_key, None)
        except ImportError:
            return None

    def _resolve_user_password_hash(
        self, user_data: Dict[str, Any], fallback: str
    ) -> str:
        """Hash password from manifest or fall back to default."""
        password_hash = fallback
        env_key = user_data.get("password_env_var")
        if not env_key:
            return password_hash

        try:
            from tests import test_credentials

            password_value = getattr(test_credentials, env_key, None)
            if password_value:
                password_hash = hash_password(password_value)
        except ImportError:
            # Gracefully handle missing test_credentials module - use default password hash
            pass

        return password_hash

    def _resolve_user_program_ids(
        self,
        user_data: Dict[str, Any],
        program_map: Optional[Dict[str, str]],
        program_list: Optional[List[str]],
    ) -> List[str]:
        """Return program IDs based on manifest references."""
        if "program_code" in user_data and program_map:
            code = user_data["program_code"]
            if code in program_map:
                return [program_map[code]]
        elif "program_idx" in user_data and program_list:
            idx = user_data["program_idx"]
            if 0 <= idx < len(program_list):
                return [program_list[idx]]
        return []

    def create_offerings_from_manifest(
        self,
        institution_id: str,
        term_id_or_map: Union[str, Dict[str, str]],
        offerings_data: List[Dict[str, Any]],
        course_map: Dict[str, str],
        instructor_ids: List[str],
        assessment_due_date: str = "2025-12-15T23:59:59",
    ) -> Dict[str, Any]:
        """
        Create offerings and sections from manifest data.

        Args:
            institution_id: The institution to create offerings for
            term_id_or_map: Default term ID, or Dict mapping term codes to term IDs
            offerings_data: List of offering dicts with 'course_code' and 'sections'
            course_map: Dict mapping course codes to course IDs
            instructor_ids: List of instructor IDs for assignment
            assessment_due_date: Default due date for sections

        Returns:
            Dict with 'offering_ids' and 'section_count'
        """
        offering_ids = []
        section_count = 0

        default_term_id = term_id_or_map if isinstance(term_id_or_map, str) else None
        term_map = term_id_or_map if isinstance(term_id_or_map, dict) else {}

        for offering_data in offerings_data:
            course_id = self._resolve_course_id_from_manifest(offering_data, course_map)
            if not course_id:
                continue

            term_id = self._resolve_term_id_from_manifest(
                offering_data, default_term_id, term_map
            )
            if not term_id:
                self.log(
                    f"   ⚠️  No term ID resolveable for offering {offering_data.get('course_code')}, skipping"
                )
                continue

            offering_id = self._create_offering_with_sections(
                institution_id,
                course_id,
                term_id,
                offering_data,
                instructor_ids,
            )
            if not offering_id:
                continue

            offering_ids.append(offering_id)
            section_count += self._create_sections_for_offering(
                offering_id, offering_data.get("sections", []), instructor_ids
            )

        return {"offering_ids": offering_ids, "section_count": section_count}

    def _resolve_course_id_from_manifest(
        self, offering_data: Dict[str, Any], course_map: Dict[str, str]
    ) -> Optional[str]:
        course_code = self._coerce_to_str(offering_data.get("course_code"))
        if course_code:
            course_id = course_map.get(course_code)
            if course_id:
                return course_id

        course_id_from_manifest = self._coerce_to_str(offering_data.get("course_id"))
        if course_id_from_manifest:
            return course_id_from_manifest

        if course_code is not None:
            for code, cid in course_map.items():
                if code == course_code:
                    return cid
        self.log(f"   ⚠️  Course code '{course_code}' not found, skipping offering")
        return None

    def _resolve_term_id_from_manifest(
        self,
        offering_data: Dict[str, Any],
        default_term_id: Optional[str],
        term_map: Dict[str, str],
    ) -> Optional[str]:
        if "_term_id" in offering_data:
            return offering_data["_term_id"]
        if "term_code" in offering_data and term_map:
            return term_map.get(offering_data["term_code"])
        if default_term_id:
            return default_term_id
        if term_map:
            return next(iter(term_map.values()), None)

        return None

    def _create_offering_with_sections(
        self,
        institution_id: str,
        course_id: str,
        term_id: str,
        offering_data: Dict[str, Any],
        instructor_ids: List[str],
    ) -> Optional[str]:
        schema = CourseOffering.create_schema(
            course_id=course_id,
            term_id=term_id,
            institution_id=institution_id,
        )

        offering_id = database_service.db.create_course_offering(schema)
        return offering_id

    def _create_sections_for_offering(
        self,
        offering_id: str,
        sections: List[Dict[str, Any]],
        instructor_ids: List[str],
    ) -> int:
        section_count = 0
        for section in sections:
            section_schema = self._build_section_schema(
                offering_id, section, instructor_ids
            )
            if database_service.db.create_course_section(section_schema):
                section_count += 1
        return section_count

    def _build_section_schema(
        self,
        offering_id: str,
        section_data: Dict[str, Any],
        instructor_ids: List[str],
    ) -> Dict[str, Any]:
        """Return CourseSection schema using manifest section definition."""
        instructor_id = self._resolve_section_instructor(section_data, instructor_ids)
        return CourseSection.create_schema(
            offering_id=offering_id,
            section_number=section_data.get("section_number", "001"),
            instructor_id=instructor_id,
            enrollment=section_data.get("enrollment", 0),
            status=section_data.get("status", "assigned"),
        )

    def _resolve_section_instructor(
        self, section_data: Dict[str, Any], instructor_ids: List[str]
    ) -> Optional[str]:
        """Map instructor index to ID if provided."""
        idx = section_data.get("instructor_idx")
        if isinstance(idx, int) and 0 <= idx < len(instructor_ids):
            return instructor_ids[idx]
        return None

    def create_clos_from_manifest(
        self, course_ids: List[str], manifest_data: Dict[str, Any]
    ) -> int:
        """
        Create CLOs from manifest templates and specific CLO definitions.

        Args:
            course_ids: List of course IDs to apply templates to
            manifest_data: Full manifest dict containing 'clo_templates' and 'clos'

        Returns:
            Number of CLOs created
        """
        course_map = self._build_course_lookup(course_ids)
        clo_count = self._create_clo_templates(
            course_map, manifest_data.get("clo_templates", {})
        )
        clo_count += self._create_specific_clos(
            course_ids, course_map, manifest_data.get("clos", [])
        )
        return clo_count

    def _build_course_lookup(self, course_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Build course lookup mapping by ID and course number."""
        course_map: Dict[str, Dict[str, Any]] = {}
        for cid in course_ids:
            course = database_service.db.get_course_by_id(cid)
            if not course:
                continue
            course_map[cid] = course
            course_number = self._coerce_to_str(course.get("course_number"))
            if course_number:
                course_map[course_number] = course
        return course_map

    def _create_clo_templates(
        self,
        course_map: Dict[str, Dict[str, Any]],
        clo_templates: Dict[str, List[Dict[str, Any]]],
    ) -> int:
        from src.models.models import CourseOutcome
        from src.utils.constants import CLOStatus

        clo_count = 0
        for course in course_map.values():
            course_num = self._coerce_to_str(course.get("course_number")) or ""
            prefix = course_num.split("-")[0] if "-" in course_num else ""
            templates = clo_templates.get(prefix, [])
            if not templates:
                continue
            course_id = self._coerce_to_str(course.get("id") or course.get("course_id"))
            if not course_id:
                continue
            existing = database_service.db.get_course_outcomes(course_id)
            existing_numbers = {str(c.get("clo_number")) for c in existing or []}
            for template in templates:
                template_num = str(template["num"])
                if template_num in existing_numbers:
                    continue
                schema = CourseOutcome.create_schema(
                    course_id=course_id,
                    clo_number=template_num,
                    description=template["desc"],
                    assessment_method=template["method"],
                )
                schema["status"] = CLOStatus.ASSIGNED
                schema["active"] = True
                if database_service.db.create_course_outcome(schema):
                    clo_count += 1
        return clo_count

    def _create_specific_clos(
        self,
        course_ids: List[str],
        course_map: Dict[str, Dict[str, Any]],
        specific_clos: List[Dict[str, Any]],
    ) -> int:
        from src.utils.constants import CLOApprovalStatus, CLOStatus

        clo_count = 0
        status_lookup = self._status_lookup()
        for clo_data in specific_clos:
            target_course = self._resolve_target_course(
                clo_data, course_ids, course_map
            )
            if not target_course:
                self.log(
                    f"   ⚠️  Target course not found for CLO #{clo_data.get('clo_number')}"
                )
                continue
            target_id = self._coerce_to_str(
                target_course.get("id") or target_course.get("course_id")
            )
            if not target_id:
                self.log(
                    f"   ⚠️  Missing course ID for CLO #{clo_data.get('clo_number')}, skipping"
                )
                continue
            status_str = clo_data.get("status", "assigned")
            status_enum, approval_status = status_lookup.get(
                status_str, (CLOStatus.ASSIGNED, None)
            )
            submitted_at = self._parse_submitted_at(
                status_str, clo_data.get("submitted_at")
            )
            students_took = clo_data.get("students_took")
            students_passed = clo_data.get("students_passed")
            assessment_tool = clo_data.get("assessment_tool")
            updates = self._build_clo_updates(
                status_enum,
                approval_status,
                submitted_at,
                students_took,
                students_passed,
                assessment_tool,
            )
            existing = database_service.db.get_course_outcomes(target_id)
            existing_clo = next(
                (
                    c
                    for c in existing or []
                    if str(c.get("clo_number")) == str(clo_data.get("clo_number"))
                ),
                None,
            )
            if existing_clo:
                if updates:
                    database_service.db.update_course_outcome(
                        existing_clo["outcome_id"], updates
                    )
                continue
            schema = self._build_clo_schema(
                target_id,
                clo_data,
                status_enum,
                approval_status,
                submitted_at,
                students_took,
                students_passed,
                assessment_tool,
            )
            if database_service.db.create_course_outcome(schema):
                clo_count += 1
                self.log(
                    f"   ✓ Created specific CLO #{clo_data.get('clo_number')} for {clo_data.get('course_code')}"
                )
        return clo_count

    @staticmethod
    def _parse_submitted_at(
        status_str: str, submitted_value: Optional[str]
    ) -> Optional[datetime]:
        """Parse submitted_at when applicable."""
        if status_str not in {"approved", "awaiting_approval"} or not submitted_value:
            return None
        try:
            return datetime.fromisoformat(submitted_value)
        except ValueError:
            return None

    @staticmethod
    def _status_lookup() -> Dict[str, Tuple[Any, Optional[str]]]:
        from src.utils.constants import CLOApprovalStatus, CLOStatus

        return {
            "unassigned": (CLOStatus.UNASSIGNED, None),
            "approved": (CLOStatus.APPROVED, CLOApprovalStatus.APPROVED),
            "completed": (CLOStatus.COMPLETED, None),
            "needs_rework": (
                "approval_pending",  # UI expects this for "Needs Rework" badge
                CLOApprovalStatus.NEEDS_REWORK,
            ),
            "never_coming_in": (
                CLOStatus.NEVER_COMING_IN,
                CLOApprovalStatus.NEVER_COMING_IN,
            ),
            "awaiting_approval": (
                CLOStatus.AWAITING_APPROVAL,
                CLOApprovalStatus.PENDING,
            ),
        }

    def _resolve_target_course(
        self,
        clo_data: Dict[str, Any],
        course_ids: List[str],
        course_map: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        course_code = self._coerce_to_str(clo_data.get("course_code"))
        target_course = course_map.get(course_code) if course_code else None
        if not target_course and "course_idx" in clo_data:
            idx = clo_data["course_idx"]
            if 0 <= idx < len(course_ids):
                target_course = course_map.get(course_ids[idx])
        return target_course

    def _build_clo_updates(
        self,
        status_enum: Any,
        approval_status: Optional[str],
        submitted_at: Optional[datetime],
        students_took: Optional[int],
        students_passed: Optional[int],
        assessment_tool: Optional[str],
    ) -> Dict[str, Any]:
        updates: Dict[str, Any] = {}
        status_name = status_enum.name if hasattr(status_enum, "name") else status_enum
        if status_enum and status_name != "ASSIGNED":
            updates["status"] = status_enum
        if approval_status:
            updates["approval_status"] = approval_status
        if submitted_at:
            updates["submitted_at"] = submitted_at
        if students_took is not None:
            updates["students_took"] = students_took
        if students_passed is not None:
            updates["students_passed"] = students_passed
        if assessment_tool:
            updates["assessment_tool"] = assessment_tool
        if students_took is not None and students_passed is not None:
            updates["percentage_meeting"] = (
                round((students_passed / students_took) * 100, 2)
                if students_took > 0
                else None
            )
        return updates

    def _build_clo_schema(
        self,
        course_id: str,
        clo_data: Dict[str, Any],
        status_enum: Any,
        approval_status: Optional[str],
        submitted_at: Optional[datetime],
        students_took: Optional[int],
        students_passed: Optional[int],
        assessment_tool: Optional[str],
    ) -> Dict[str, Any]:
        description = self._coerce_to_str(clo_data.get("description")) or ""
        assessment_method = self._coerce_to_str(clo_data.get("assessment_method")) or ""
        schema = CourseOutcome.create_schema(
            course_id=course_id,
            clo_number=str(clo_data.get("clo_number")),
            description=description,
            assessment_method=assessment_method,
        )
        schema["status"] = status_enum
        if approval_status:
            schema["approval_status"] = approval_status
        if submitted_at:
            schema["submitted_at"] = submitted_at
        if students_took is not None:
            schema["students_took"] = students_took
        if students_passed is not None:
            schema["students_passed"] = students_passed
        if assessment_tool:
            schema["assessment_tool"] = assessment_tool
        schema["percentage_meeting"] = (
            round((students_passed / students_took) * 100, 2)
            if students_took and students_passed is not None and students_took > 0
            else None
        )
        schema["active"] = True
        return schema

    @abstractmethod
    def seed(self) -> bool:
        """Implement seeding logic in subclasses"""
        pass


class BaselineTestSeeder(BaselineSeeder):
    """
    Seeds baseline test infrastructure for E2E/integration tests.

    Uses tests/fixtures/baseline_test_manifest.json for all data.
    All data must come from manifest - no hardcoded fallbacks.
    """

    DEFAULT_MANIFEST_PATH = "tests/fixtures/baseline_test_manifest.json"

    def __init__(self, manifest_path: Optional[str] = None) -> None:
        super().__init__()
        self.manifest_path = manifest_path

    def seed(self) -> bool:
        """Implementation of abstract seed method"""
        return self.seed_baseline()

    def _get_manifest_path(self) -> str:
        """Get the manifest path, relative to project root"""
        if self.manifest_path:
            return self.manifest_path

        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        return os.path.join(project_root, self.DEFAULT_MANIFEST_PATH)

    def seed_baseline(self, manifest_data: Optional[Dict[str, Any]] = None) -> bool:
        """Seed baseline data from manifest - REQUIRED"""
        self.log("🌱 Seeding baseline E2E infrastructure...")

        # Refresh database service to ensure it uses the correct database
        # NOTE: Must use database_service.refresh_connection() NOT database_factory.refresh_database_service()
        # because the latter only updates the factory cache, not the database_service.db alias
        from src.database import database_service

        database_service.refresh_connection()

        # Load manifest - REQUIRED
        if manifest_data is None:
            manifest_path = self._get_manifest_path()
            manifest_data = self.load_manifest(manifest_path)

        if not manifest_data:
            self.log("❌ Manifest is required for baseline seeding")
            return False

        # Validate required sections
        required_sections = [
            "institutions",
            "programs",
            "terms",
            "courses",
            "users",
            "offerings",
        ]
        for section in required_sections:
            if section not in manifest_data:
                self.log(f"❌ '{section}' required in manifest")
                return False

        # Create institutions
        self.log("🏢 Creating test institutions...")
        inst_ids = self.create_institutions_from_manifest(manifest_data["institutions"])

        # Create programs
        self.log("📚 Creating academic programs...")
        prog_ids = self.create_programs_from_manifest(
            inst_ids, manifest_data["programs"]
        )

        # Create terms
        self.log("📅 Creating academic terms...")
        term_ids = self.create_terms_from_manifest(inst_ids, manifest_data["terms"])

        # Create courses
        self.log("📖 Creating sample courses...")
        course_ids = self.create_courses_from_manifest(
            inst_ids, manifest_data["courses"], prog_ids
        )

        # Build course_map by index for offerings
        course_map = {str(i): cid for i, cid in enumerate(course_ids)}

        # Create users (site_admin, instructors, program admins, institution admins)
        self.log("👥 Creating users...")
        from tests.test_credentials import INSTITUTION_ADMIN_PASSWORD

        default_hash = hash_password(INSTITUTION_ADMIN_PASSWORD)
        user_ids = self.create_users_from_manifest(
            inst_ids, manifest_data["users"], prog_ids, default_hash
        )

        # Filter instructor IDs for section assignment
        instructor_ids: List[str] = []
        for i, user_data in enumerate(manifest_data["users"]):
            if (
                user_data.get("role") == "instructor"
                and i < len(user_ids)
                and user_ids[i] is not None
            ):
                user_id = user_ids[i]
                if user_id is not None:  # Type narrowing for mypy
                    instructor_ids.append(user_id)

        # Create offerings and sections
        self.log("📝 Creating course offerings and sections...")
        # Convert index-based offerings to code-based format for base class method
        offerings_data = manifest_data["offerings"]
        for offering in offerings_data:
            # Add course_code from course_idx
            course_idx = offering.get("course_idx", 0)
            offering["course_code"] = str(course_idx)
            # Add term handling
            term_idx = offering.get("term_idx", 0)
            if term_idx < len(term_ids):
                offering["_term_id"] = term_ids[term_idx]

        # Use first term as default
        default_term_id = term_ids[1] if len(term_ids) > 1 else term_ids[0]

        result = self.create_offerings_from_manifest(
            institution_id=inst_ids[0],
            term_id_or_map=default_term_id,
            offerings_data=offerings_data,
            course_map=course_map,
            instructor_ids=instructor_ids,
        )
        self.log(
            f"   ✓ Created {len(result['offering_ids'])} offerings and {result['section_count']} sections"
        )

        self.log("✅ Baseline seeding completed!")
        self.print_summary()
        return True

    def print_summary(self) -> None:
        """Print seeding summary"""
        self.log("")
        self.log("📊 Summary:")
        self.log(f"   Institutions: {len(self.created['institutions'])} created")
        self.log(f"   Users: {len(self.created['users'])} created")
        self.log(f"   Programs: {len(self.created['programs'])} created")
        self.log(f"   Terms: {len(self.created['terms'])} created")
        self.log(f"   Courses: {len(self.created['courses'])} created")
        self.log("")
        self.log("🔑 Test Accounts: (see manifest for credentials)")


class DatabaseSeeder:
    """
    Compatibility wrapper for integration tests.

    Integration tests expect DatabaseSeeder.seed_full_dataset() but we refactored
    to BaselineTestSeeder.seed_baseline() for E2E tests. This provides backward compatibility.
    """

    def __init__(self, verbose: bool = True) -> None:
        self.seeder = BaselineTestSeeder()
        self.verbose = verbose

    def seed_full_dataset(self) -> bool:
        """Seed the full baseline dataset (compatibility method)"""
        return self.seeder.seed_baseline()


class DemoSeeder(BaselineSeeder):
    """
    Complete seeding for product demonstrations (2025).

    Uses demos/full_semester_manifest.json for all data configuration.
    Extends BaselineSeeder and uses its generic manifest methods.
    """

    DEFAULT_MANIFEST_PATH = "demos/full_semester_manifest.json"

    def __init__(self, manifest_path: Optional[str] = None, env: str = "dev") -> None:
        super().__init__()
        self.manifest_path = manifest_path
        self.env = env
        self._manifest_cache: Optional[Dict[str, Any]] = None

    def seed(self) -> bool:
        """Implementation of abstract seed method - calls seed_demo()"""
        return self.seed_demo()

    def log(self, message: str) -> None:
        """Log with [SEED] prefix"""
        print(f"[SEED] {message}")

    def load_demo_manifest(self) -> Dict[str, Any]:
        """Load demo data from external JSON (cached)"""
        if self._manifest_cache is not None:
            return self._manifest_cache

        try:
            if self.manifest_path:
                manifest_path = os.path.abspath(self.manifest_path)
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                manifest_path = os.path.join(
                    script_dir, "..", self.DEFAULT_MANIFEST_PATH
                )

            if os.path.exists(manifest_path):
                self.log(f"📋 Loading demo data from {manifest_path}")
                with open(manifest_path, "r") as f:
                    self._manifest_cache = json.load(f)
                    return self._manifest_cache
            else:
                self.log(f"⚠️  Manifest not found at {manifest_path}, using defaults")
                self._manifest_cache = {}
                return {}
        except Exception as e:
            self.log(f"⚠️  Failed to load manifest: {e}")
            self._manifest_cache = {}
            return {}

    def seed_demo(self) -> bool:
        """Seed complete data for product demo - manifest required."""
        self.log("🎬 Seeding demo environment...")

        # Load manifest - REQUIRED
        manifest = self.load_demo_manifest()
        if not manifest:
            self.log("❌ Manifest is required for demo seeding")
            return False

        # Validate required sections
        required = [
            "institutions",
            "programs",
            "terms",
            "courses",
            "users",
            "offerings",
        ]
        for section in required:
            if not manifest.get(section):
                self.log(f"❌ '{section}' required in manifest")
                return False

        # 1. Create Institutions
        self.log("🏢 Creating demo institution(s)...")
        inst_ids = self.create_institutions_from_manifest(manifest["institutions"])
        if not inst_ids:
            return False

        # 2. Create Programs
        self.log("📚 Creating demo programs...")
        prog_ids = self.create_programs_from_manifest(inst_ids, manifest["programs"])

        # Build map
        program_map = {}
        for i, prog in enumerate(manifest["programs"]):
            if i < len(prog_ids):
                program_map[prog.get("code", "")] = prog_ids[i]

        # 3. Create Terms
        self.log("📅 Creating terms...")
        term_ids = self.create_terms_from_manifest(inst_ids, manifest["terms"])
        term_map = {}
        for i, term in enumerate(manifest["terms"]):
            if i < len(term_ids):
                term_map[term.get("term_code") or term.get("code")] = term_ids[i]

        # 4. Create Courses
        self.log("📖 Creating demo courses...")
        course_ids = self.create_courses_from_manifest(
            inst_ids, manifest["courses"], program_map
        )
        course_map = {}
        for i, course in enumerate(manifest["courses"]):
            target_code = course.get("code") or course.get("course_number")
            if i < len(course_ids):
                course_map[target_code] = course_ids[i]

        # 5. Create CLOs
        self.log("🎯 Creating Course Learning Outcomes...")
        clo_count = self.create_clos_from_manifest(course_ids, manifest)
        self.log(f"   ✅ Created {clo_count} CLOs across demo courses")

        # 6. Create Users
        self.log("👥 Creating demo faculty/staff...")
        from tests.test_credentials import DEMO_PASSWORD

        default_hash = hash_password(DEMO_PASSWORD)

        user_ids = self.create_users_from_manifest(
            inst_ids, manifest["users"], program_map, default_hash
        )

        # 7. Create Offerings
        self.log("📋 Creating demo offerings and sections...")

        # Use generic method which handles instructor verification
        # Filter out None values for instructor assignment
        valid_instructor_ids = [uid for uid in user_ids if uid is not None]
        result = self.create_offerings_from_manifest(
            institution_id=inst_ids[0],
            term_id_or_map=term_map,
            offerings_data=manifest["offerings"],
            course_map=course_map,
            instructor_ids=valid_instructor_ids,
        )
        self.log(
            f"   ✅ Created {len(result['offering_ids'])} offerings and {result['section_count']} sections"
        )

        # 8. Apply section-specific CLO overrides (post-seeding)
        if "section_outcome_overrides" in manifest:
            self.log("🔧 Applying section-specific CLO overrides...")
            override_count = self.apply_section_outcome_overrides(
                manifest["section_outcome_overrides"], inst_ids[0]
            )
            self.log(f"   ✅ Applied {override_count} section outcome overrides")

        self.log("✅ Demo seeding completed!")
        self.print_summary()
        return True

    def apply_section_outcome_overrides(
        self, overrides: List[Dict[str, Any]], institution_id: str
    ) -> int:
        """
        Apply section-specific CLO status overrides after seeding.

        This allows individual section outcomes to have different statuses
        than the course-level template (e.g., one section submitted, another forgot).

        Args:
            overrides: List of override dicts with course_code, section_number,
                      clo_number, and the updates to apply
            institution_id: Institution ID to look up course/section

        Returns:
            Number of overrides successfully applied
        """
        from src.utils.constants import CLOApprovalStatus, CLOStatus

        applied_count = 0
        status_lookup = self._status_lookup()

        for override in overrides:
            course_code = override.get("course_code")
            section_number = override.get("section_number")
            clo_number = str(override.get("clo_number"))
            new_status = override.get("status", "assigned")

            # Skip if required fields are missing
            if not course_code or not section_number:
                continue

            # Look up the section outcome to update
            section_outcome = self._find_section_outcome(
                course_code, section_number, clo_number, institution_id
            )
            if not section_outcome:
                self.log(
                    f"   ⚠️ Section outcome not found: {course_code} Sec {section_number} CLO {clo_number}"
                )
                continue

            # Build updates
            status_enum, approval_status = status_lookup.get(
                new_status, (CLOStatus.ASSIGNED, None)
            )
            updates: Dict[str, Any] = {
                "status": status_enum,
            }
            if approval_status:
                updates["approval_status"] = approval_status

            # Add optional fields
            if "feedback_comments" in override:
                updates["feedback_comments"] = override["feedback_comments"]
            if "students_took" in override:
                updates["students_took"] = override["students_took"]
            if "students_passed" in override:
                updates["students_passed"] = override["students_passed"]

            # Apply the update (this creates history for the current status too,
            # but we'll add explicit historical entries below)
            if database_service.db.update_section_outcome(
                section_outcome["id"], updates
            ):
                applied_count += 1
                self.log(
                    f"   ✓ Updated {course_code} Sec {section_number} CLO {clo_number} → {new_status}"
                )

                # Add explicit history entries from manifest
                if "history" in override:
                    self._create_history_entries(
                        section_outcome["id"], override["history"]
                    )

        return applied_count

    def _create_history_entries(
        self, section_outcome_id: str, history_data: List[Dict[str, Any]]
    ) -> None:
        """Create OutcomeHistory entries with relative dates from manifest."""
        from datetime import timedelta

        from src.database.database_sqlite import SQLiteDatabase
        from src.models.models_sql import OutcomeHistory

        now = datetime.now(timezone.utc)

        # Cast to access internal session_scope (demo seeder only)
        db: SQLiteDatabase = database_service.db  # type: ignore[assignment]
        with db.sqlite.session_scope() as session:
            for entry in history_data:
                event = entry.get("event")
                relative_days = entry.get("relative_days", 0)
                occurred_at = now + timedelta(days=relative_days)

                history_entry = OutcomeHistory(
                    section_outcome_id=section_outcome_id,
                    event=event,
                    occurred_at=occurred_at,
                )
                session.add(history_entry)

    def _find_section_outcome(
        self,
        course_code: str,
        section_number: str,
        clo_number: str,
        institution_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Find a specific section outcome by course/section/CLO number."""
        # Step 1: Find the course by course_code
        course = database_service.db.get_course_by_number(course_code, institution_id)
        if not course:
            return None
        course_id = course.get("id") or course.get("course_id")
        if not course_id:
            return None

        # Step 2: Find the course outcome (template) by clo_number
        course_outcomes = database_service.db.get_course_outcomes(course_id)
        outcome_template = None
        for co in course_outcomes or []:
            if str(co.get("clo_number")) == clo_number:
                outcome_template = co
                break
        if not outcome_template:
            return None
        outcome_id = outcome_template.get("id") or outcome_template.get("outcome_id")
        if not outcome_id:
            return None

        # Step 3: Find the section by section_number
        sections = database_service.db.get_sections_by_course(course_id)
        target_section = None
        for sec in sections or []:
            if sec.get("section_number") == section_number:
                target_section = sec
                break
        if not target_section:
            return None
        section_id = target_section.get("id") or target_section.get("section_id")
        if not section_id:
            return None

        # Step 4: Find the section outcome by section_id and outcome_id
        section_outcome = (
            database_service.db.get_section_outcome_by_course_outcome_and_section(
                outcome_id, section_id
            )
        )
        return section_outcome

    def print_summary(self) -> None:
        """Print demo seeding summary"""
        # Environment-aware configuration
        env_config = {
            "dev": {"port": 3001, "env_name": "dev"},
            "e2e": {"port": 3002, "env_name": "e2e"},
            "smoke": {"port": 3003, "env_name": "smoke"},
            "ci": {"port": 3001, "env_name": "ci"},
            "prod": {"port": 3001, "env_name": "prod"},
        }

        config = env_config.get(self.env, {"port": 3001, "env_name": "dev"})
        port = config["port"]
        env_name = config["env_name"]

        self.log("")
        self.log("📊 Demo Environment Ready:")
        self.log(f"   Institutions: {len(self.created['institutions'])} created")
        self.log(f"   Users: {len(self.created['users'])} created")
        self.log(f"   Terms: {len(self.created['terms'])} created")
        self.log(f"   Courses: {len(self.created['courses'])} created")
        self.log("🎬 Next Steps:")
        self.log(f"   1. Start server: ./restart_server.sh {env_name}")
        self.log(f"   2. Navigate to: http://localhost:{port}")
        self.log("   3. Login with the credentials above")


def main() -> None:
    """Main seeding entry point"""
    parser = argparse.ArgumentParser(
        description="Seed baseline E2E test data",
        epilog="Examples:\n"
        "  python scripts/seed_database_service.db.py --demo --clear --env dev\n"
        "  python scripts/seed_database_service.db.py --clear --env e2e\n"
        "  python scripts/seed_database_service.db.py --env prod\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--clear", action="store_true", help="Clear database first")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Seed generic demo environment for product demonstrations",
    )
    parser.add_argument(
        "--env",
        choices=["dev", "e2e", "smoke", "ci", "prod"],
        default="prod",
        help="Environment to seed (dev, e2e, smoke, ci, or prod). Determines which database file to use.",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        help="Path to JSON manifest file for custom seeding (overrides generic defaults)",
    )

    # Parse arguments and catch errors
    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code != 0:
            print("\n❌ ERROR: Invalid arguments provided")
            print("💡 TIP: Use --env dev (not just 'dev')")
            print("Run with -h or --help for usage information\n")
        raise

    # Map environment to database file
    db_mapping = {
        "dev": "sqlite:///course_records_dev.db",
        "e2e": "sqlite:///course_records_e2e.db",
        "smoke": "sqlite:///course_records_smoke.db",
        "ci": "sqlite:///course_records_ci.db",
        "prod": "sqlite:///course_records.db",
    }

    database_url = db_mapping[args.env]
    os.environ["DATABASE_URL"] = database_url

    # Refresh database service to ensure it uses the correct database
    # NOTE: Must use database_service.refresh_connection() NOT database_factory.refresh_database_service()
    # because the latter only updates the factory cache, not the database_service.db alias
    from src.database import database_service

    database_service.refresh_connection()

    # Log which database we're using
    db_file = database_url.replace("sqlite:///", "")
    print(f"[SEED] 🗄️  Using {args.env} database: {db_file}")

    if args.demo:
        demo_seeder = DemoSeeder(manifest_path=args.manifest, env=args.env)

        if args.clear:
            demo_seeder.log("🧹 Clearing database...")
            from src.database.database_service import reset_database

            reset_database()

        success = demo_seeder.seed_demo()
        sys.exit(0 if success else 1)
    else:
        baseline_seeder = BaselineTestSeeder()

        if args.clear:
            baseline_seeder.log("🧹 Clearing database...")
            from src.database.database_service import reset_database

            reset_database()

        # Load manifest if provided
        manifest_data = None
        if args.manifest:
            try:
                with open(args.manifest, "r") as f:
                    manifest_data = json.load(f)
                baseline_seeder.log(f"📄 Loaded custom manifest: {args.manifest}")
            except Exception as e:
                print(f"❌ Failed to load manifest: {e}")
                sys.exit(1)

        success = baseline_seeder.seed_baseline(manifest_data)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
