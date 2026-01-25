"""
Reminder API routes.

Provides endpoints for sending course-specific assessment reminders to instructors.
"""

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

import src.database.database_service as database_service
from src.api.utils import get_current_user_safe
from src.services.auth_service import login_required, permission_required
from src.utils.logging_config import get_logger

# Create blueprint
reminders_bp = Blueprint("reminders", __name__, url_prefix="/api")

# Initialize logger
logger = get_logger(__name__)


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

        # Get request data
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        instructor_id = data.get("instructor_id")
        course_id = data.get("course_id")

        if not instructor_id or not course_id:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Missing required fields: instructor_id, course_id",
                    }
                ),
                400,
            )

        # Get instructor details
        instructor = database_service.get_user_by_id(instructor_id)
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

        # Get course details
        course = database_service.get_course_by_id(course_id)
        if not course:
            return (
                jsonify({"success": False, "error": f"Course not found: {course_id}"}),
                404,
            )

        # Get current user (admin sending the reminder)
        current_user = get_current_user_safe()
        admin_name = f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}".strip()
        if not admin_name:
            admin_name = current_user.get("email", "Your program administrator")

        # Get institution name
        institution_id = instructor.get("institution_id")
        institution = (
            database_service.get_institution_by_id(institution_id)
            if institution_id
            else None
        )
        institution_name = (
            institution.get("name", "Your institution")
            if institution
            else "Your institution"
        )

        # Build assessment URL with course parameter
        # Use configured BASE_URL (not request.url_root which may be wrong on Cloud Run)
        from flask import current_app

        from src.utils.constants import DEFAULT_BASE_URL

        base_url = current_app.config.get("BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        assessment_url = f"{base_url}/assessments?course={course_id}"

        # Send email
        instructor_name = f"{instructor.get('first_name', '')} {instructor.get('last_name', '')}".strip()
        if not instructor_name:
            instructor_name = instructor.get("email", "Instructor")

        course_number = course.get("course_number", "Course")
        course_title = course.get("course_title", "")
        course_display = (
            f"{course_number} - {course_title}" if course_title else course_number
        )

        email_sent = EmailService.send_course_assessment_reminder(
            to_email=instructor["email"],
            instructor_name=instructor_name,
            course_display=course_display,
            admin_name=admin_name,
            institution_name=institution_name,
            assessment_url=assessment_url,
        )

        # Record reminder for each section the instructor teaches for this course
        sections = database_service.get_sections_by_course(course_id)
        reminder_count = 0
        for section in sections:
            if str(section.get("instructor_id")) == str(instructor_id):
                section_id = section.get("section_id") or section.get("id")
                if section_id:
                    database_service.create_reminder(
                        section_id=section_id,
                        instructor_id=instructor_id,
                        sent_by=current_user.get("user_id"),
                        reminder_type="individual",
                    )
                    # Record history for each section outcome in this section
                    section_outcomes = database_service.get_section_outcomes_by_section(
                        section_id
                    )
                    for so in section_outcomes:
                        so_id = so.get("id")
                        if so_id:
                            database_service.add_outcome_history(so_id, "Reminder Sent")
                    reminder_count += 1

        # Check email result and return appropriate response
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
        else:
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

    except Exception as e:
        logger.error(f"[API] Error sending course reminder: {str(e)}", exc_info=True)
        return (
            jsonify({"success": False, "error": "Failed to send reminder email"}),
            500,
        )
