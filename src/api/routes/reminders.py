"""
Reminder API routes.

Provides endpoints for sending course-specific assessment reminders to instructors.
"""

from collections.abc import Mapping
from typing import Any, Dict, cast

from flask import Blueprint, jsonify
from flask.typing import ResponseReturnValue

import src.database.database_service as database_service
from src.api.utils import (
    get_current_user_safe,
)
from src.api.utils import get_request_json_object as _get_request_json
from src.services.auth_service import login_required, permission_required
from src.utils.constants import (
    COURSE_NOT_FOUND_MSG,
    DEFAULT_BASE_URL,
    NO_JSON_DATA_PROVIDED_MSG,
)
from src.utils.logging_config import get_logger

# Create blueprint
reminders_bp = Blueprint("reminders", __name__, url_prefix="/api")

# Initialize logger
logger = get_logger(__name__)


def _display_name(person: Dict[str, Any], fallback: str) -> str:
    """Return first/last name when present, otherwise a fallback."""
    full_name = f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
    if full_name:
        return full_name
    return str(person.get("email", fallback))


def _parse_reminder_request() -> tuple[str, str] | None:
    """Return validated instructor and course ids from the request body."""
    data = _get_request_json()
    if not data:
        return None
    instructor_id = str(data.get("instructor_id", "")).strip()
    course_id = str(data.get("course_id", "")).strip()
    return instructor_id, course_id


def _get_reminder_entities(
    instructor_id: str, course_id: str
) -> tuple[Dict[str, Any] | None, Dict[str, Any] | None]:
    """Fetch the instructor and course for a reminder request."""
    return (
        database_service.get_user_by_id(instructor_id),
        database_service.get_course_by_id(course_id),
    )


def _build_reminder_email_context(
    instructor: Dict[str, Any], course: Dict[str, Any], course_id: str
) -> tuple[str, str, str]:
    """Build institution, assessment URL, and course display values for reminder email."""
    institution_id = instructor.get("institution_id")
    institution = (
        database_service.get_institution_by_id(institution_id)
        if institution_id
        else None
    )
    institution_data = cast(Dict[str, Any], institution) if institution else {}
    institution_name = str(institution_data.get("name", "Your institution"))

    from flask import current_app

    app_config = cast(Mapping[str, Any], current_app.config)
    base_url = str(app_config.get("BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
    assessment_url = f"{base_url}/assessments?course={course_id}"

    course_number = course.get("course_number", "Course")
    course_title = course.get("course_title", "")
    course_display = (
        f"{course_number} - {course_title}" if course_title else course_number
    )
    return institution_name, assessment_url, course_display


def _record_course_reminders(
    current_user: Dict[str, Any], instructor_id: str, course_id: str
) -> int:
    """Persist reminder and history entries for all matching sections."""
    reminder_count = 0
    for section in database_service.get_sections_by_course(course_id):
        if str(section.get("instructor_id")) != str(instructor_id):
            continue
        section_id = section.get("section_id") or section.get("id")
        if not section_id:
            continue
        database_service.create_reminder(
            section_id=section_id,
            instructor_id=instructor_id,
            sent_by=current_user.get("user_id"),
            reminder_type="individual",
        )
        for so in database_service.get_section_outcomes_by_section(section_id):
            so_id = so.get("id")
            if so_id:
                database_service.add_outcome_history(so_id, "Reminder Sent")
        reminder_count += 1
    return reminder_count


def _validate_reminder_request(
    instructor_id: str, course_id: str
) -> ResponseReturnValue | None:
    """Return an error response when the reminder payload is incomplete."""
    if instructor_id and course_id:
        return None
    return (
        jsonify(
            {
                "success": False,
                "error": "Missing required fields: instructor_id, course_id",
            }
        ),
        400,
    )


def _build_reminder_response(
    email_sent: bool,
    instructor: Dict[str, Any],
    instructor_name: str,
    course_display: str,
    course_number: str,
    current_user: Dict[str, Any],
    reminder_count: int,
) -> ResponseReturnValue:
    """Return the API response for a completed reminder attempt."""
    if email_sent:
        logger.info(
            f"[API] Course reminder sent to {instructor['email']} for {course_number} by {current_user.get('email')} "
            f"(recorded {reminder_count} section reminders)"
        )
        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Reminder sent to {instructor_name} for {course_display}",
                }
            ),
            200,
        )

    logger.warning(
        f"[API] Course reminder FAILED to {instructor['email']} for {course_number} "
        f"(but recorded {reminder_count} section reminders for tracking)"
    )
    return (
        jsonify(
            {
                "success": False,
                "error": f"Failed to send email to {instructor_name}. Email provider may be unavailable.",
                "reminders_recorded": reminder_count,
            }
        ),
        500,
    )


@reminders_bp.route("/send-course-reminder", methods=["POST"])
@login_required
@permission_required("manage_programs")
def send_course_reminder_api() -> ResponseReturnValue:
    """
    Send a course-specific assessment reminder to an instructor.

    Request Body:
        {
            "instructor_id": "user-uuid",
            "course_id": "course-uuid"
        }

    Returns:
        200: Reminder sent successfully
        400: Invalid request data
        404: Instructor or course not found
        500: Server error
    """
    try:
        from src.services.email_service import EmailService

        request_ids = _parse_reminder_request()
        if request_ids is None:
            return (
                jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}),
                400,
            )
        instructor_id, course_id = request_ids

        validation_error = _validate_reminder_request(instructor_id, course_id)
        if validation_error is not None:
            return validation_error

        instructor, course = _get_reminder_entities(instructor_id, course_id)
        if not instructor:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Instructor not found: {instructor_id}",
                    }
                ),
                404,
            )

        if not course:
            return jsonify({"success": False, "error": COURSE_NOT_FOUND_MSG}), 404

        # Get current user (admin sending the reminder)
        current_user = get_current_user_safe()
        assert current_user is not None
        admin_name = _display_name(current_user, "Your program administrator")

        instructor_name = _display_name(instructor, "Instructor")
        institution_name, assessment_url, course_display = (
            _build_reminder_email_context(instructor, course, course_id)
        )
        course_number = course.get("course_number", "Course")

        email_sent = EmailService.send_course_assessment_reminder(
            to_email=instructor["email"],
            instructor_name=instructor_name,
            course_display=course_display,
            admin_name=admin_name,
            institution_name=institution_name,
            assessment_url=assessment_url,
        )

        reminder_count = _record_course_reminders(
            current_user, instructor_id, course_id
        )

        return _build_reminder_response(
            email_sent=email_sent,
            instructor=instructor,
            instructor_name=instructor_name,
            course_display=course_display,
            course_number=course_number,
            current_user=current_user,
            reminder_count=reminder_count,
        )

    except Exception as e:
        logger.error(f"[API] Error sending course reminder: {str(e)}", exc_info=True)
        return (
            jsonify({"success": False, "error": "Failed to send reminder email"}),
            500,
        )
