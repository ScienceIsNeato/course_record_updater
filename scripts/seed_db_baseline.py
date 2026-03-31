"""Shared baseline seeding helpers for seed_db."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

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

    def _validate_required_manifest_sections(
        self,
        manifest_data: Dict[str, Any],
        required_sections: List[str],
        require_non_empty: bool = False,
    ) -> bool:
        """Validate that all required manifest sections are present."""
        for section in required_sections:
            if section not in manifest_data:
                self.log(f"❌ '{section}' required in manifest")
                return False
            if require_non_empty and not manifest_data.get(section):
                self.log(f"❌ '{section}' required in manifest")
                return False
        return True

    def _build_program_map(
        self, programs_data: List[Dict[str, Any]], prog_ids: List[str]
    ) -> Dict[str, str]:
        """Build program code -> ID map for code-based lookups."""
        program_map: Dict[str, str] = {}
        for index, program_data in enumerate(programs_data):
            if index >= len(prog_ids):
                continue
            code = program_data.get("code", "")
            if code:
                program_map[code] = prog_ids[index]
        return program_map

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

            existing = database_service.db.get_institution_by_short_name(short_name)
            if existing:
                institution_ids.append(existing["institution_id"])
                continue

            schema = Institution.create_schema(
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

            inst_id = database_service.db.create_institution(schema)
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
                if term_data.get("start_date") and term_data.get("end_date"):
                    try:
                        sd_str = term_data["start_date"]
                        ed_str = term_data["end_date"]
                        start_date = datetime.fromisoformat(sd_str)
                        end_date = datetime.fromisoformat(ed_str)
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

                schema = Term.create_schema(
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

                term_id = database_service.db.create_term(schema)
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
            inst_idx = prog_data.get("institution_idx", 0)
            if inst_idx < len(institution_ids):
                institution_id = institution_ids[inst_idx]
            else:
                institution_id = institution_ids[0]

            schema = Program.create_schema(
                name=prog_data["name"],
                short_name=prog_data.get("code", prog_data["name"][:4].upper()),
                institution_id=institution_id,
                description=prog_data.get("description", PROGRAM_DEFAULT_DESCRIPTION),
                created_by="system",
            )

            prog_id = database_service.db.create_program(schema)
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
        institution_ids = (
            institution_id_or_ids
            if isinstance(institution_id_or_ids, list)
            else [institution_id_or_ids]
        )

        program_map = (
            program_ids_or_map if isinstance(program_ids_or_map, dict) else None
        )
        program_list = (
            program_ids_or_map if isinstance(program_ids_or_map, list) else None
        )

        user_ids: List[Optional[str]] = []
        for user_data in users_data:
            email = self._resolve_user_email(user_data)
            if not email:
                user_ids.append(None)
                continue

            existing = database_service.db.get_user_by_email(email)
            if existing:
                user_ids.append(existing["user_id"])
                continue

            inst_idx = user_data.get("institution_idx", 0)
            role = user_data.get("role", "instructor")

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
                user_ids.append(None)

        return user_ids

    def _resolve_user_email(self, user_data: Dict[str, Any]) -> Optional[str]:
        email = user_data.get("email")
        if email:
            return email
        env_key = user_data.get("email_env_var")
        if not env_key:
            return None

        try:
            from src.utils import constants

            return getattr(constants, env_key, None)
        except ImportError:
            return None

    def _resolve_user_password_hash(
        self, user_data: Dict[str, Any], fallback: str
    ) -> str:
        password_hash = fallback
        env_key = user_data.get("password_env_var")
        if not env_key:
            return password_hash

        try:
            from src.utils import constants

            password_value = getattr(constants, env_key, None)
            if password_value:
                password_hash = hash_password(password_value)
        except ImportError:
            pass

        return password_hash

    def _resolve_user_program_ids(
        self,
        user_data: Dict[str, Any],
        program_map: Optional[Dict[str, str]],
        program_list: Optional[List[str]],
    ) -> List[str]:
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
        offering_ids = []
        section_count = 0

        default_term_id = term_id_or_map if isinstance(term_id_or_map, str) else None
        term_map = term_id_or_map if isinstance(term_id_or_map, dict) else {}

        for offering_data in offerings_data:
            if "_comment" in offering_data and len(offering_data) == 1:
                continue
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
        idx = section_data.get("instructor_idx")
        if isinstance(idx, int) and 0 <= idx < len(instructor_ids):
            return instructor_ids[idx]
        return None

    def create_clos_from_manifest(
        self, course_ids: List[str], manifest_data: Dict[str, Any]
    ) -> int:
        course_map = self._build_course_lookup(course_ids)
        clo_count = self._create_clo_templates(
            course_map, manifest_data.get("clo_templates", {})
        )
        clo_count += self._create_specific_clos(
            course_ids, course_map, manifest_data.get("clos", [])
        )
        return clo_count

    def _build_course_lookup(self, course_ids: List[str]) -> Dict[str, Dict[str, Any]]:
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
        from src.utils.constants import CLOStatus

        clo_count = 0
        status_lookup = self._status_lookup()
        for clo_data in specific_clos:
            if "_comment" in clo_data and len(clo_data) == 1:
                continue
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
                "approval_pending",
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
