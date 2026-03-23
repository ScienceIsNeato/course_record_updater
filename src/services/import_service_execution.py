"""Execution mixin for ImportService record-type processing helpers."""

from __future__ import annotations

import sys
from typing import Any, Callable, Dict, Optional


class ImportServiceExecutionMixin:
    @staticmethod
    def _service_fn(name: str) -> Any:
        service_module = sys.modules.get("src.services.import_service")
        if service_module is None:
            raise RuntimeError("src.services.import_service is not loaded")
        return getattr(service_module, name)

    @staticmethod
    def _strategy_value(strategy: Any) -> str:
        return str(getattr(strategy, "value", strategy))

    def _process_term_import(
        self, term_data: Dict[str, Any], dry_run: bool = False
    ) -> None:
        try:
            term_name = term_data.get("term_name")
            if not term_name:
                self.stats["errors"].append("Term missing term_name")
                return

            existing_term = self._service_fn("get_term_by_name")(
                term_name, self.institution_id
            )
            if existing_term:
                self.stats["records_skipped"] += 1
                self._log(f"Term already exists: {term_name}")
                return

            term_data["institution_id"] = self.institution_id
            term_data.pop("id", None)

            if not dry_run:
                self._service_fn("create_term")(term_data)
                self.stats["records_created"] += 1
                self._log(f"Created term: {term_name}")
            else:
                self._log(f"DRY RUN: Would create term: {term_name}")
        except Exception as e:
            self.stats["errors"].append(
                f"Error processing term {term_data.get('term_name')}: {str(e)}"
            )

    def _validate_and_lookup_course_term(
        self, course_number: str, term_name: str, institution_id: str, context: str
    ) -> tuple[Optional[str], Optional[str]]:
        course = self._service_fn("get_course_by_number")(course_number, institution_id)
        term = self._service_fn("get_term_by_name")(term_name, institution_id)

        if not course:
            self.stats["errors"].append(
                f"Course {course_number} not found for {context}"
            )
            return None, None

        if not term:
            self.stats["errors"].append(f"Term {term_name} not found for {context}")
            return None, None

        return course["course_id"], term["term_id"]

    def _handle_offering_conflict(
        self,
        strategy: Any,
        course_number: str,
        term_name: str,
    ) -> bool:
        strategy_value = self._strategy_value(strategy)
        if strategy_value == "use_mine":
            self.stats["records_skipped"] += 1
            self._log(f"Skipped existing offering: {course_number} - {term_name}")
            return True
        if strategy_value == "use_theirs":
            self.stats["records_updated"] += 1
            self._log(f"Updated offering: {course_number} - {term_name}")
            return True
        return False

    def _process_offering_import(
        self,
        offering_data: Dict[str, Any],
        strategy: Any,
        dry_run: bool = False,
    ) -> None:
        try:
            course_number = offering_data.get("course_number")
            term_name = offering_data.get("term_name")
            institution_id = self.institution_id

            if not course_number or not term_name:
                self.stats["errors"].append(
                    f"Missing course_number or term_name in offering data: {offering_data}"
                )
                return

            course_id, term_id = self._validate_and_lookup_course_term(
                course_number, term_name, institution_id, "offering"
            )
            if not course_id or not term_id:
                return

            if dry_run:
                self._log(
                    f"DRY RUN: Would create offering for {course_number} in {term_name}"
                )
                return

            existing_offering = self._service_fn(
                "get_course_offering_by_course_and_term"
            )(course_id, term_id)
            if existing_offering and self._handle_offering_conflict(
                strategy, course_number, term_name
            ):
                return

            from src.models.models import CourseOffering

            offering_schema = CourseOffering.create_schema(
                course_id=course_id,
                term_id=term_id,
                institution_id=institution_id,
            )
            offering_id = self._service_fn("create_course_offering")(offering_schema)

            if offering_id:
                self.stats["records_created"] += 1
                self._log(f"Created offering: {course_number} - {term_name}")
            else:
                self.stats["errors"].append(
                    f"Failed to create offering for {course_number} - {term_name}"
                )
        except Exception as e:
            error_msg = f"Error processing offering: {str(e)}"
            self.stats["errors"].append(error_msg)
            self._log(error_msg, "error")
            import traceback

            self._log(f"Traceback: {traceback.format_exc()}", "error")

    def _get_or_create_offering(
        self,
        course_id: str,
        term_id: str,
        institution_id: str,
        course_number: str,
        section_number: str,
    ) -> Optional[str]:
        existing_offering = self._service_fn("get_course_offering_by_course_and_term")(
            course_id, term_id
        )
        if existing_offering:
            return existing_offering["offering_id"]

        from src.models.models import CourseOffering

        offering_schema = CourseOffering.create_schema(
            course_id=course_id,
            term_id=term_id,
            institution_id=institution_id,
        )
        offering_id = self._service_fn("create_course_offering")(offering_schema)

        if not offering_id:
            self.stats["errors"].append(
                f"Failed to create offering for section {course_number}-{section_number}"
            )
            return None
        return offering_id

    def _update_offering_counts(
        self, offering_id: str, course_id: str, term_id: str, student_count: int
    ) -> None:
        offering = self._service_fn("get_course_offering_by_course_and_term")(
            course_id, term_id
        )
        if offering:
            self._service_fn("update_course_offering")(
                offering_id,
                {
                    "section_count": offering.get("section_count", 0) + 1,
                    "total_enrollment": offering.get("total_enrollment", 0)
                    + student_count,
                },
            )

    def _process_section_import(
        self,
        section_data: Dict[str, Any],
        dry_run: bool = False,
    ) -> None:
        try:
            course_number = section_data.get("course_number")
            term_name = section_data.get("term_name")
            section_number = section_data.get("section_number", "001")
            institution_id = self.institution_id
            student_count = section_data.get("student_count", 0)
            instructor_email = section_data.get("instructor_email")

            if not course_number or not term_name:
                self.stats["errors"].append(
                    f"Missing course_number or term_name in section data: {section_data}"
                )
                return

            course_id, term_id = self._validate_and_lookup_course_term(
                course_number, term_name, institution_id, "section"
            )
            if not course_id or not term_id:
                return

            offering_id = self._get_or_create_offering(
                course_id, term_id, institution_id, course_number, section_number
            )
            if not offering_id:
                return

            if dry_run:
                self._log(
                    f"DRY RUN: Would create section {section_number} for {course_number} in {term_name}"
                )
                return

            instructor_id = None
            if instructor_email:
                instructor = self._service_fn("get_user_by_email")(instructor_email)
                if instructor:
                    instructor_id = instructor["user_id"]

            from src.models.models import CourseSection

            section_schema = CourseSection.create_schema(
                offering_id=offering_id,
                section_number=section_number,
                instructor_id=instructor_id,
                enrollment=student_count,
                status="assigned",
            )
            section_id = self._service_fn("create_course_section")(section_schema)

            if section_id:
                self.stats["records_created"] += 1
                self._log(
                    f"Created section {section_number} for {course_number} in {term_name}"
                )
                self._update_offering_counts(
                    offering_id, course_id, term_id, student_count
                )
            else:
                self.stats["errors"].append(
                    f"Failed to create section {section_number} for {course_number}"
                )
        except Exception as e:
            error_msg = f"Error processing section: {str(e)}"
            self.stats["errors"].append(error_msg)
            self._log(error_msg, "error")
            import traceback

            self._log(f"Traceback: {traceback.format_exc()}", "error")

    def _process_clo_import(
        self,
        clo_data: Dict[str, Any],
        strategy: Any,
        dry_run: bool = False,
    ) -> None:
        try:
            course_number = clo_data.get("course_number")
            clo_number = clo_data.get("clo_number")
            description = clo_data.get("description")
            assessment_method = clo_data.get("assessment_method")

            if not course_number or not clo_number or not description:
                self.stats["errors"].append(
                    f"Missing required fields in CLO data: {clo_data}"
                )
                return

            course = self._service_fn("get_course_by_number")(
                course_number, self.institution_id
            )
            if not course:
                self.stats["errors"].append(
                    f"Course {course_number} not found for CLO {clo_number}"
                )
                return

            course_id = course["course_id"]
            if dry_run:
                self._log(f"DRY RUN: Would create CLO {clo_number} for {course_number}")
                return

            existing_clo = next(
                (
                    existing
                    for existing in self._service_fn("get_course_outcomes")(course_id)
                    if existing.get("clo_number") == clo_number
                ),
                None,
            )
            if existing_clo:
                strategy_value = self._strategy_value(strategy)
                if strategy_value == "use_mine":
                    self.stats["records_skipped"] += 1
                    self._log(f"Skipped existing CLO: {course_number}.{clo_number}")
                    return
                if strategy_value == "use_theirs":
                    self.stats["records_updated"] += 1
                    self._log(f"Updated CLO: {course_number}.{clo_number}")
                    return

            from src.models.models import CourseOutcome

            clo_schema = CourseOutcome.create_schema(
                course_id=course_id,
                clo_number=clo_number,
                description=description,
                assessment_method=assessment_method,
                active=True,
            )
            outcome_id = self._service_fn("create_course_outcome")(clo_schema)

            if outcome_id:
                self.stats["records_created"] += 1
                self._log(f"Created CLO {clo_number} for {course_number}")
            else:
                self.stats["errors"].append(
                    f"Failed to create CLO {clo_number} for {course_number}"
                )
        except Exception as e:
            error_msg = f"Error processing CLO: {str(e)}"
            self.stats["errors"].append(error_msg)
            self._log(error_msg, "error")
            import traceback

            self._log(f"Traceback: {traceback.format_exc()}", "error")

    def _try_link_single_course(
        self,
        course: Dict[str, Any],
        program_lookup: Dict[str, str],
        course_mappings: Dict[str, str],
        add_course_to_program_func: Callable[[str, str], bool],
    ) -> bool:
        course_number = course["course_number"]
        prefix = course_number.split("-")[0] if "-" in course_number else None
        if not (prefix and prefix in course_mappings):
            return False

        program_id = program_lookup.get(course_mappings[prefix])
        if not program_id:
            return False

        try:
            course_id = course.get("course_id") or course.get("id")
            if not course_id:
                self.logger.warning(
                    f"Course {course_number} missing course_id, cannot link"
                )
                return False
            add_course_to_program_func(course_id, program_id)
            return True
        except Exception:
            return False

    def _link_courses_to_programs(self) -> None:
        try:
            from src.database.database_service import (
                add_course_to_program,
                get_all_courses,
                get_programs_by_institution,
            )

            self.logger.info("[Import] Linking courses to programs...")
            courses = get_all_courses(self.institution_id)
            programs = get_programs_by_institution(self.institution_id)
            if not courses or not programs:
                self.logger.info("[Import] No courses or programs to link")
                return

            program_lookup = {
                program["name"]: program["program_id"] for program in programs
            }
            default_program = next(
                (name for name in program_lookup.keys() if "Default Program" in name),
                None,
            )
            course_mappings: Dict[str, Optional[str]] = {
                "BIOL": "Biological Sciences",
                "BSN": "Biological Sciences",
                "ZOOL": "Zoology",
                "CS": default_program,
                "EE": default_program,
                "GEN": default_program,
                "CEI": default_program,
            }
            course_mappings_typed = {
                key: value
                for key, value in course_mappings.items()
                if isinstance(value, str)
            }

            linked_count = len(
                [
                    course
                    for course in courses
                    if self._try_link_single_course(
                        course,
                        program_lookup,
                        course_mappings_typed,
                        add_course_to_program,
                    )
                ]
            )

            if linked_count > 0:
                self.logger.info(f"[Import] Linked {linked_count} courses to programs")
            else:
                self.logger.info("[Import] All courses already linked to programs")
        except Exception as e:
            self.logger.warning(f"[Import] Failed to link courses to programs: {e}")
