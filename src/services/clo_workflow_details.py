"""Detail enrichment and notification helpers for CLO workflow service."""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Mapping, Optional, cast

from src.database.database_service import db
from src.utils.logging_config import get_logger

from .email_service import EmailService

logger = get_logger(__name__)

ADMIN_NOTIFICATION_FAILURE_MSG = "Failed to notify admins: {error}"
ADMIN_EMAIL_SEND_FAILURE_MSG = "Failed to send email to {email}: {error}"
COURSE_NOT_FOUND_MSG = "Course not found: {course_id}"


class CLOWorkflowDetailsMixin:
    @staticmethod
    def _service_class() -> type["CLOWorkflowDetailsMixin"]:
        service_module = sys.modules.get("src.services.clo_workflow_service")
        service_class = getattr(service_module, "CLOWorkflowService", None)
        if service_class is None:
            return CLOWorkflowDetailsMixin
        return cast(type["CLOWorkflowDetailsMixin"], service_class)

    @staticmethod
    def _service_db() -> Any:
        service_module = sys.modules.get("src.services.clo_workflow_service")
        return getattr(service_module, "db", db)

    @staticmethod
    def _service_email_service() -> Any:
        service_module = sys.modules.get("src.services.clo_workflow_service")
        return getattr(service_module, "EmailService", EmailService)

    @staticmethod
    def _format_person_name(person: Dict[str, Any], fallback: str = "") -> str:
        full_name = (
            f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
        )
        return full_name or person.get("email", fallback)

    @staticmethod
    def _course_program_ids(course: Optional[Dict[str, Any]]) -> List[str]:
        if not course:
            return []

        raw_program_ids = course.get("program_ids")
        if isinstance(raw_program_ids, list):
            program_ids = [
                str(program_id_value)
                for program_id_value in cast(List[Any], raw_program_ids)
                if program_id_value
            ]
            if program_ids:
                return program_ids
        elif isinstance(raw_program_ids, str):
            return [raw_program_ids]

        program_id = course.get("program_id")
        return [str(program_id)] if program_id else []

    @staticmethod
    def _expand_outcome_for_sections(outcome: Dict[str, Any]) -> List[Dict[str, Any]]:
        service = CLOWorkflowDetailsMixin._service_class()
        service_db = CLOWorkflowDetailsMixin._service_db()
        course_outcome_id = service._resolve_outcome_id(outcome)
        if not course_outcome_id:
            return []

        course_id = outcome.get("course_id")
        raw_sections: Any = (
            service_db.get_sections_by_course(course_id) if course_id else []
        )
        sections: List[Mapping[str, Any]] = cast(
            List[Mapping[str, Any]],
            raw_sections,
        )
        results: List[Dict[str, Any]] = []

        if sections:
            for section in sections:
                section_id_value = section.get("section_id") or section.get("id")
                section_id = str(section_id_value) if section_id_value else None
                if not section_id:
                    continue

                section_outcome = (
                    service_db.get_section_outcome_by_course_outcome_and_section(
                        course_outcome_id, section_id
                    )
                )
                if not section_outcome:
                    continue

                section_outcome_id = section_outcome.get("id")
                if not section_outcome_id:
                    continue

                enriched_section_outcome: Dict[str, Any] = {
                    **section_outcome,
                    "course_id": course_id,
                    "clo_number": outcome.get("clo_number"),
                    "description": outcome.get("description"),
                    "assessment_method": outcome.get("assessment_method"),
                }
                details = service.get_outcome_with_details(
                    str(section_outcome_id),
                    section_data=dict(section),
                    outcome_data=enriched_section_outcome,
                )
                if details:
                    results.append(details)
            return results

        details = service.get_outcome_with_details(
            course_outcome_id, outcome_data=outcome
        )
        return [details] if details else []

    @staticmethod
    def _resolve_outcome_id(outcome: Dict[str, Any]) -> Optional[str]:
        raw_id = outcome.get("outcome_id") or outcome.get("id")
        return str(raw_id) if raw_id else None

    @staticmethod
    def _get_instructor_from_outcome(
        outcome: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if outcome.get("status") == "unassigned":
            return None

        instructor_id = outcome.get("submitted_by_user_id")
        if instructor_id:
            return CLOWorkflowDetailsMixin._service_db().get_user(instructor_id)

        course_id = outcome.get("course_id")
        if not course_id:
            return None

        sections = CLOWorkflowDetailsMixin._service_db().get_sections_by_course(
            course_id
        )
        if not sections:
            return None

        section = sections[0]
        instructor_id = section.get("instructor_id")
        if not instructor_id:
            return None

        return CLOWorkflowDetailsMixin._service_db().get_user(instructor_id)

    @staticmethod
    def _build_instructor_name(instructor: Dict[str, Any]) -> Optional[str]:
        instructor_name = instructor.get("display_name")
        if instructor_name:
            return instructor_name

        first = instructor.get("first_name", "")
        last = instructor.get("last_name", "")
        return f"{first} {last}".strip() or None

    @staticmethod
    def _get_term_name_for_instructor(
        instructor_id: str, course_id: str, outcome_id: str
    ) -> Optional[str]:
        try:
            service_db = CLOWorkflowDetailsMixin._service_db()
            sections = service_db.get_sections_by_instructor(instructor_id)
            relevant_sections = [s for s in sections if s.get("course_id") == course_id]
            if relevant_sections:
                term_id = relevant_sections[0].get("term_id")
                if term_id:
                    term = service_db.get_term_by_id(term_id)
                    if term:
                        return term.get("name")
        except Exception as e:
            logger.warning(f"Failed to resolve term for outcome {outcome_id}: {e}")
        return None

    @staticmethod
    def _get_program_name_for_course(course_id: str) -> Optional[str]:
        programs = CLOWorkflowDetailsMixin._service_db().get_programs_for_course(
            course_id
        )
        if programs:
            return programs[0].get("name") or programs[0].get("program_name")
        return None

    @staticmethod
    def _enrich_outcome_with_instructor_details(
        outcome: Dict[str, Any],
        course_id: str,
        outcome_id: str,
        section_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[
        Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]
    ]:
        if section_data:
            return CLOWorkflowDetailsMixin._service_class()._resolve_section_context(
                section_data
            )

        outcome_section_id = outcome.get("section_id")
        if outcome_section_id:
            resolved = (
                CLOWorkflowDetailsMixin._service_class()._resolve_from_section_id(
                    outcome, outcome_section_id
                )
            )
            if resolved:
                return resolved

        return CLOWorkflowDetailsMixin._service_class()._resolve_from_course_fallback(
            outcome, course_id, outcome_id
        )

    @staticmethod
    def _resolve_from_section_id(
        outcome: Dict[str, Any], outcome_section_id: str
    ) -> Optional[
        tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]
    ]:
        section = outcome.get(
            "_section"
        ) or CLOWorkflowDetailsMixin._service_db().get_section_by_id(outcome_section_id)
        if not section:
            return None

        (
            instructor_name,
            instructor_email,
            term_name,
            instructor_id,
            section_id,
        ) = CLOWorkflowDetailsMixin._service_class()._resolve_section_context(section)

        if not instructor_name:
            instructor = (
                CLOWorkflowDetailsMixin._service_class()._get_instructor_from_outcome(
                    outcome
                )
            )
            if instructor:
                instructor_name = (
                    CLOWorkflowDetailsMixin._service_class()._build_instructor_name(
                        instructor
                    )
                )
                instructor_email = instructor.get("email")
                instructor_id = instructor.get("user_id") or instructor.get("id")

        return (
            instructor_name,
            instructor_email,
            term_name,
            instructor_id,
            section_id or str(outcome_section_id),
        )

    @staticmethod
    def _resolve_from_course_fallback(
        outcome: Dict[str, Any], course_id: str, outcome_id: str
    ) -> tuple[
        Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]
    ]:
        service = CLOWorkflowDetailsMixin._service_class()
        service_db = CLOWorkflowDetailsMixin._service_db()
        instructor = service._get_instructor_from_outcome(outcome)
        section_id = None

        try:
            sections = service_db.get_sections_by_course(course_id)
            if sections:
                if instructor:
                    instructor_identifier = instructor.get("user_id") or instructor.get(
                        "id"
                    )
                    relevant = [
                        section
                        for section in sections
                        if section.get("instructor_id") == instructor_identifier
                    ]
                    if relevant:
                        section_id = relevant[0].get("section_id") or relevant[0].get(
                            "id"
                        )

                if not section_id:
                    section_id = sections[0].get("section_id") or sections[0].get("id")
        except Exception:
            pass

        if not instructor:
            return None, None, None, None, section_id

        instructor_name = service._build_instructor_name(instructor)
        instructor_email = instructor.get("email")
        instructor_id = instructor.get("user_id") or instructor.get("id")
        term_name = (
            service._get_term_name_for_instructor(instructor_id, course_id, outcome_id)
            if instructor_id
            else None
        )

        return instructor_name, instructor_email, term_name, instructor_id, section_id

    @staticmethod
    def _resolve_section_context(
        section_data: Dict[str, Any],
    ) -> tuple[
        Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]
    ]:
        instructor = section_data.get("_instructor")
        instructor_id = section_data.get("instructor_id")

        if not instructor and instructor_id:
            instructor = CLOWorkflowDetailsMixin._service_db().get_user(instructor_id)

        instructor_name = (
            CLOWorkflowDetailsMixin._service_class()._build_instructor_name(instructor)
            if instructor
            else None
        )
        instructor_email = instructor.get("email") if instructor else None

        term_name = None
        offering = section_data.get("_offering")
        if not offering:
            offering_id = section_data.get("offering_id")
            if offering_id:
                offering = CLOWorkflowDetailsMixin._service_db().get_course_offering(
                    offering_id
                )

        if offering:
            term = offering.get("_term")
            if not term:
                term_id = offering.get("term_id")
                if term_id:
                    term = CLOWorkflowDetailsMixin._service_db().get_term_by_id(term_id)
            if term:
                term_name = term.get("term_name") or term.get("name")

        section_id = section_data.get("section_id") or section_data.get("id")
        return instructor_name, instructor_email, term_name, instructor_id, section_id

    @staticmethod
    def get_outcome_with_details(
        outcome_id: str,
        section_data: Optional[Dict[str, Any]] = None,
        outcome_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            service = CLOWorkflowDetailsMixin._service_class()
            outcome = (
                outcome_data
                or CLOWorkflowDetailsMixin._service_db().get_section_outcome(outcome_id)
            )
            if not outcome:
                return None

            enriched_outcome = service._enrich_outcome_with_template(outcome)
            course = service._get_course_for_outcome(enriched_outcome)
            instructor_details = service._get_instructor_details_for_outcome(
                enriched_outcome, course, outcome_id, section_data
            )
            program_name = service._get_program_name_for_outcome(course)
            final_details = service._build_final_outcome_details(
                enriched_outcome,
                course,
                instructor_details,
                program_name,
                section_data,
            )
            service._add_outcome_history(final_details)
            return final_details
        except Exception as e:
            logger.error(f"Error getting outcome with details: {e}")
            return None

    @staticmethod
    def _enrich_outcome_with_template(outcome: Dict[str, Any]) -> Dict[str, Any]:
        if "_template" in outcome:
            return {
                **outcome["_template"],
                **outcome,
                "id": outcome["id"],
            }

        raw_course_id = outcome.get("course_id")
        if not raw_course_id and outcome.get("outcome_id"):
            template = CLOWorkflowDetailsMixin._service_db().get_course_outcome(
                outcome["outcome_id"]
            )
            if template:
                return {
                    **template,
                    **outcome,
                    "id": outcome["id"],
                }
        return outcome

    @staticmethod
    def _get_course_for_outcome(outcome: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if "_template" in outcome and outcome["_template"].get("_course"):
            return outcome["_template"]["_course"]

        raw_course_id = outcome.get("course_id")
        course_id = raw_course_id if isinstance(raw_course_id, str) else None
        return (
            CLOWorkflowDetailsMixin._service_db().get_course_by_id(course_id)
            if course_id
            else None
        )

    @staticmethod
    def _get_instructor_details_for_outcome(
        outcome: Dict[str, Any],
        course: Optional[Dict[str, Any]],
        outcome_id: str,
        section_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not course:
            return {
                "instructor_name": None,
                "instructor_email": None,
                "instructor_id": None,
                "term_name": None,
                "section_id": outcome.get("section_id"),
            }

        course_id = (
            course.get("id")
            if isinstance(course, dict) and course.get("id")
            else course
        )
        (
            instructor_name,
            instructor_email,
            term_name,
            instructor_id,
            resolved_section_id,
        ) = CLOWorkflowDetailsMixin._service_class()._enrich_outcome_with_instructor_details(
            outcome,
            course_id if isinstance(course_id, str) else "",
            outcome_id,
            section_data=section_data,
        )

        return {
            "instructor_name": instructor_name,
            "instructor_email": instructor_email,
            "instructor_id": instructor_id,
            "term_name": term_name,
            "section_id": resolved_section_id or outcome.get("section_id"),
        }

    @staticmethod
    def _get_program_name_for_outcome(
        course: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        if not course:
            return None

        service = CLOWorkflowDetailsMixin._service_class()
        program_ids = service._course_program_ids(course)
        if program_ids and "_programs" in course:
            programs = course["_programs"]
            if programs:
                return programs[0].get("name") or programs[0].get("program_name")

        course_id = (
            course.get("id")
            if isinstance(course, dict) and course.get("id")
            else course
        )
        if not course_id or not isinstance(course_id, str):
            return None
        return service._get_program_name_for_course(course_id)

    @staticmethod
    def _build_final_outcome_details(
        enriched_outcome: Dict[str, Any],
        course: Optional[Dict[str, Any]],
        instructor_details: Dict[str, Any],
        program_name: Optional[str],
        section_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        final_details = enriched_outcome.copy()

        section_id = instructor_details.get("section_id")
        section_number = section_data.get("section_number") if section_data else None
        section_status = section_data.get("status") if section_data else None

        if not section_number and section_id:
            section = enriched_outcome.get("_section")
            if not section:
                section = CLOWorkflowDetailsMixin._service_db().get_section_by_id(
                    section_id
                )
            if section:
                section_number = section_number or section.get("section_number")

        final_details.update(
            {
                "course_number": course.get("course_number") if course else None,
                "course_title": course.get("course_title") if course else None,
                "instructor_name": instructor_details.get("instructor_name"),
                "instructor_email": instructor_details.get("instructor_email"),
                "instructor_id": instructor_details.get("instructor_id"),
                "section_id": section_id,
                "section_number": section_number,
                "section_status": section_status,
                "program_name": program_name,
                "term_name": instructor_details.get("term_name"),
            }
        )
        return final_details

    @staticmethod
    def _add_outcome_history(final_details: Dict[str, Any]) -> None:
        if "_history" in final_details:
            final_details["history"] = final_details["_history"]
            return

        outcome_id_for_history = final_details.get("id")
        if outcome_id_for_history:
            final_details[
                "history"
            ] = CLOWorkflowDetailsMixin._service_db().get_outcome_history(
                outcome_id_for_history
            )
        else:
            final_details["history"] = []

    @staticmethod
    def _notify_program_admins(section_outcome_id: str, user_id: str) -> None:
        try:
            service_db = CLOWorkflowDetailsMixin._service_db()
            email_service = CLOWorkflowDetailsMixin._service_email_service()
            service = CLOWorkflowDetailsMixin._service_class()
            outcome = service_db.get_section_outcome(section_outcome_id)
            if not outcome:
                logger.warning(
                    f"Outcome not found for notification: {section_outcome_id}"
                )
                return

            course = service_db.get_course_by_id(outcome["course_id"])
            if not course:
                logger.warning(
                    f"Course not found for notification: {outcome['course_id']}"
                )
                return

            instructor = service_db.get_user_by_id(user_id)
            if not instructor:
                logger.warning(f"Instructor not found for notification: {user_id}")
                return

            program_ids = service._course_program_ids(course)
            program_id = program_ids[0] if program_ids else None
            if not program_id:
                logger.warning(f"No program ID for course {course['id']}")
                return

            admins = service_db.get_program_admins(program_id)
            if not admins:
                logger.info(f"No program admins found for program {program_id}")
                return

            instructor_name = CLOWorkflowDetailsMixin._format_person_name(instructor)

            section_id = outcome.get("section_id")
            section_number = "Unknown"
            if section_id:
                section_data = service_db.get_section_by_id(section_id)
                if section_data:
                    section_number = section_data.get("section_number", "Unknown")

            course_code = f"{course['course_number']}-{section_number}"

            for admin in admins:
                try:
                    email_service.send_admin_submission_alert(
                        to_email=admin["email"],
                        admin_name=admin.get("first_name", "Admin"),
                        instructor_name=instructor_name,
                        course_code=course_code,
                        clo_count=1,
                    )
                except Exception as e:
                    logger.error(
                        ADMIN_EMAIL_SEND_FAILURE_MSG.format(
                            email=admin["email"], error=e
                        )
                    )

            logger.info(f"Sent admin alerts to {len(admins)} program admins")
        except Exception as e:
            logger.error(ADMIN_NOTIFICATION_FAILURE_MSG.format(error=e))

    @staticmethod
    def _notify_program_admins_for_course(
        course_id: str, user_id: str, clo_count: int
    ) -> tuple[bool, Optional[str]]:
        try:
            service_db = CLOWorkflowDetailsMixin._service_db()
            email_service = CLOWorkflowDetailsMixin._service_email_service()
            service = CLOWorkflowDetailsMixin._service_class()
            course = service_db.get_course_by_id(course_id)
            if not course:
                error_msg = COURSE_NOT_FOUND_MSG.format(course_id=course_id)
                logger.warning(error_msg)
                return False, error_msg

            instructor = service_db.get_user_by_id(user_id)
            if not instructor:
                error_msg = f"Instructor not found: {user_id}"
                logger.warning(error_msg)
                return False, error_msg

            program_ids = service._course_program_ids(course)
            program_id = program_ids[0] if program_ids else None

            admins: List[Dict[str, Any]] = []
            if program_id:
                admins = service_db.get_program_admins(program_id)
                if not admins:
                    logger.info(
                        f"No program admins for program {program_id}, falling back to institution admins"
                    )
            else:
                logger.info(
                    f"No program ID for course {course_id}, using institution admins for notifications"
                )

            if not admins:
                institution_id = course.get("institution_id")
                if institution_id:
                    admins = [
                        user
                        for user in service_db.get_all_users(institution_id)
                        if user.get("role") == "institution_admin"
                    ]

            if not admins:
                error_msg = (
                    f"No program or institution admins found for course {course_id}"
                )
                logger.warning(error_msg)
                return False, error_msg

            instructor_name = CLOWorkflowDetailsMixin._format_person_name(
                instructor, "Instructor"
            )

            course_code = course.get("course_number") or course_id

            for admin in admins:
                try:
                    email_service.send_admin_submission_alert(
                        to_email=admin["email"],
                        admin_name=admin.get("first_name", "Admin"),
                        instructor_name=instructor_name,
                        course_code=course_code,
                        clo_count=clo_count,
                    )
                except Exception as e:
                    logger.error(
                        ADMIN_EMAIL_SEND_FAILURE_MSG.format(
                            email=admin["email"], error=e
                        )
                    )

            logger.info(f"Sent admin submission alerts to {len(admins)} program admins")
            return True, None
        except Exception as e:
            error_msg = ADMIN_NOTIFICATION_FAILURE_MSG.format(error=e)
            logger.error(error_msg)
            return False, str(e)
