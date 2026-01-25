"""
Outcomes API routes.

Provides endpoints for managing course learning outcomes (CLOs),
including CRUD operations, assessment data updates, and submission workflows.
"""

from typing import Any, Dict, Tuple

from flask import Blueprint, jsonify, request, session
from flask.typing import ResponseReturnValue

import src.database.database_service as database_service
from src.api.utils import (
    get_current_institution_id_safe,
    get_current_user_safe,
    handle_api_error,
    resolve_institution_scope,
)
from src.database.database_service import (
    delete_course_outcome,
    get_course_by_id,
    get_course_outcome,
    get_course_outcomes,
    get_section_outcome,
    update_course_outcome,
    update_section_outcome,
)
from src.services.auth_service import (
    get_current_user,
    login_required,
    permission_required,
)
from src.utils.constants import (
    COURSE_NOT_FOUND_MSG,
    NO_JSON_DATA_PROVIDED_MSG,
    OUTCOME_NOT_FOUND_MSG,
    CLOStatus,
)
from src.utils.logging_config import get_logger

outcomes_bp = Blueprint("outcomes", __name__, url_prefix="/api")
logger = get_logger(__name__)


@outcomes_bp.route("/outcomes", methods=["GET"])
@permission_required("view_program_data")
def list_all_outcomes_endpoint() -> ResponseReturnValue:
    """Get all outcomes for the institution, optionally filtered."""
    institution_id = get_current_institution_id_safe()
    program_id = request.args.get("program_id")
    course_id = request.args.get("course_id")
    status = request.args.get("status") or None  # Allow 'active', 'archived', etc.

    try:
        if course_id:
            outcomes = get_course_outcomes(course_id)
            if status:
                outcomes = [
                    o
                    for o in outcomes
                    if o.get("status") == status
                    or (status == "active" and o.get("active") == True)
                ]
        else:
            outcomes = database_service.get_outcomes_by_status(
                institution_id, status, program_id=program_id
            )

        return (
            jsonify({"success": True, "outcomes": outcomes, "count": len(outcomes)}),
            200,
        )

    except Exception as e:
        return handle_api_error(e, "List outcomes", "Failed to list outcomes")


@outcomes_bp.route("/outcomes", methods=["POST"])
@permission_required("manage_courses")
def create_outcome_endpoint() -> ResponseReturnValue:
    """Create a new course outcome. Requires course_id in body."""
    try:
        data = request.get_json(silent=True) or {}
        if not data or "course_id" not in data:
            return jsonify({"success": False, "error": "course_id is required"}), 400
        if "description" not in data:
            return jsonify({"success": False, "error": "description is required"}), 400

        course = get_course_by_id(data["course_id"])
        institution_id = get_current_institution_id_safe()
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": COURSE_NOT_FOUND_MSG}), 404

        outcome_id = database_service.create_course_outcome(data)

        if outcome_id:
            return (
                jsonify(
                    {
                        "success": True,
                        "outcome_id": outcome_id,
                        "message": "Course outcome created successfully",
                    }
                ),
                201,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to create course outcome"}),
                500,
            )

    except Exception as e:
        return handle_api_error(e, "Create outcome", "Failed to create outcome")


@outcomes_bp.route("/courses/<course_id>/outcomes", methods=["GET"])
@login_required
def get_course_outcomes_endpoint_get(course_id: str) -> ResponseReturnValue:
    """Get outcomes for a course, scoped by user role."""
    from src.database.database_service import (
        get_section_outcomes_by_criteria,
        get_sections_by_course,
    )

    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": "Unauthorized"}), 401

        # Get course details for the response
        course = get_course_by_id(course_id)
        if not course:
            return (
                jsonify({"success": False, "error": f"Course not found: {course_id}"}),
                404,
            )
        if not course.get("course_number"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Course {course_id} has no course_number",
                    }
                ),
                500,
            )
        if not course.get("course_title"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Course {course_id} has no course_title",
                    }
                ),
                500,
            )
        course_number = course["course_number"]
        course_title = course["course_title"]

        # 1. Get all sections for this course
        sections = get_sections_by_course(course_id)

        # 2. For admins, show all sections; for instructors, filter to their sections
        user_role = current_user.get("role", "")
        if user_role in ["institution_admin", "site_admin", "program_admin"]:
            user_section_ids = [s["section_id"] for s in sections]
        else:
            # Filter sections where the current user is the instructor
            user_section_ids = [
                s["section_id"]
                for s in sections
                if str(s.get("instructor_id")) == str(current_user["user_id"])
            ]

        # 3. Get ALL section outcomes for this course
        all_outcomes = get_section_outcomes_by_criteria(
            institution_id=current_user["institution_id"], course_id=course_id
        )

        # 4. Filter outcomes that belong to the user's sections
        outcomes = [o for o in all_outcomes if o.get("section_id") in user_section_ids]

        return (
            jsonify(
                {
                    "success": True,
                    "outcomes": outcomes,
                    "course_number": course_number,
                    "course_title": course_title,
                }
            ),
            200,
        )

    except Exception as e:
        return handle_api_error(
            e, "Get course outcomes", "Failed to get course outcomes"
        )


@outcomes_bp.route("/courses/<course_id>/outcomes", methods=["POST"])
@permission_required("manage_courses")
def create_course_outcome_endpoint(course_id: str) -> ResponseReturnValue:
    """Create a new course outcome for the given course."""
    try:
        data = request.get_json(silent=True) or {}
        if not data or "description" not in data:
            return jsonify({"success": False, "error": "description is required"}), 400

        # Check if course exists
        course = get_course_by_id(course_id)
        if not course:
            return jsonify({"success": False, "error": COURSE_NOT_FOUND_MSG}), 404

        data["course_id"] = course_id

        outcome_id = database_service.create_course_outcome(data)

        if outcome_id:
            # Get section outcomes that were auto-created for this course outcome
            from src.database.database_service import get_section_outcomes_by_outcome

            section_outcomes = get_section_outcomes_by_outcome(outcome_id)
            section_outcome_ids = [so.get("id") for so in section_outcomes]

            return (
                jsonify(
                    {
                        "success": True,
                        "outcome_id": outcome_id,
                        "section_outcome_ids": section_outcome_ids,
                        "message": "Course outcome created successfully",
                    }
                ),
                201,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to create course outcome"}),
                500,
            )

    except Exception as e:
        return handle_api_error(
            e, "Create course outcome", "Failed to create course outcome"
        )


@outcomes_bp.route("/courses/<course_id>/submit", methods=["POST"])
@login_required
def submit_course_for_approval_endpoint(course_id: str) -> ResponseReturnValue:
    """Submit all CLOs for a course for approval after validation."""
    from src.services.clo_workflow_service import CLOWorkflowService

    try:
        # Check if course exists
        course = get_course_by_id(course_id)
        if not course:
            return jsonify({"success": False, "error": COURSE_NOT_FOUND_MSG}), 404

        # Get current user
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "error": "User not authenticated"}), 401

        # Get optional section_id from request body
        data = request.get_json(silent=True) or {} or {}
        section_id = data.get("section_id")
        alert_program_admins = bool(data.get("alert_program_admins"))

        # Submit course (validates first)
        result = CLOWorkflowService.submit_course_for_approval(
            course_id, user_id, section_id, notify_admins=alert_program_admins
        )

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return handle_api_error(
            e, "Submit course for approval", "Failed to submit course"
        )


@outcomes_bp.route("/outcomes/<outcome_id>", methods=["GET"])
@permission_required("view_program_data")
def get_course_outcome_by_id_endpoint(outcome_id: str) -> ResponseReturnValue:
    """Get course outcome details by outcome ID"""
    try:
        outcome = get_course_outcome(outcome_id)

        if not outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Verify institution access
        institution_id = get_current_institution_id_safe()
        course_id = outcome.get("course_id")
        if not course_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404
        course = get_course_by_id(str(course_id))
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        return jsonify({"success": True, "outcome": outcome}), 200

    except Exception as e:
        return handle_api_error(
            e, "Get course outcome", "Failed to retrieve course outcome"
        )


@outcomes_bp.route("/outcomes/<outcome_id>/audit-details", methods=["GET"])
@permission_required("audit_clo")
def get_outcome_audit_details_endpoint(outcome_id: str) -> ResponseReturnValue:
    """Get detailed audit information for an outcome."""
    from src.services.clo_workflow_service import CLOWorkflowService

    try:
        outcome = CLOWorkflowService.get_outcome_with_details(outcome_id)
        if not outcome:
            return jsonify({"success": False, "error": "Outcome not found"}), 404

        return jsonify({"success": True, "outcome": outcome}), 200
    except Exception as e:
        return handle_api_error(
            e, "Get audit details", "Failed to retrieve outcome audit details"
        )


@outcomes_bp.route("/outcomes/<outcome_id>", methods=["PUT"])
@permission_required("manage_courses")
def update_course_outcome_endpoint(outcome_id: str) -> ResponseReturnValue:
    """Update course outcome details."""
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        # Verify outcome exists and institution access
        outcome = get_course_outcome(outcome_id)

        if not outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        institution_id = get_current_institution_id_safe()
        course_id = outcome.get("course_id")
        if not course_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404
        course = get_course_by_id(str(course_id))
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        success = update_course_outcome(outcome_id, data)

        if success:
            return (
                jsonify(
                    {"success": True, "message": "Course outcome updated successfully"}
                ),
                200,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to update course outcome"}),
                500,
            )

    except Exception as e:
        return handle_api_error(
            e, "Update course outcome", "Failed to update course outcome"
        )


@outcomes_bp.route("/outcomes/<outcome_id>/assessment", methods=["PUT"])
@permission_required("submit_assessments")  # Or login_required + manual check
def update_outcome_assessment_endpoint(outcome_id: str) -> ResponseReturnValue:
    """Update assessment data for a Section Outcome."""
    from src.database.database_service import get_section_by_id

    try:
        data = request.get_json(silent=True) or {}

        logger.info(f"update_outcome_assessment for ID: {outcome_id}")

        # Verify outcome exists (this is a Section Outcome ID from frontend)
        outcome = get_section_outcome(outcome_id)
        if not outcome:
            return jsonify({"success": False, "error": "Outcome not found"}), 404

        logger.info(f"Outcome found, section_id={outcome['section_id']}")

        # Verify user access (Instructor of record)
        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": "Unauthorized"}), 401

        section = get_section_by_id(outcome["section_id"])

        if not section:
            return jsonify({"success": False, "error": "Section not found"}), 404

        # Check if user is the instructor or an admin
        if str(section.get("instructor_id")) != str(
            current_user["user_id"]
        ) and current_user["role"] not in ["institution_admin", "system_admin"]:
            return jsonify({"success": False, "error": "Unauthorized"}), 403

        allowed_fields = [
            "students_took",
            "students_passed",
            "assessment_tool",
            "feedback_comments",
            "status",
        ]
        updates = {k: v for k, v in data.items() if k in allowed_fields}

        success = update_section_outcome(outcome_id, updates)
        if not success:
            logger.error(f"Failed to update section outcome for ID: {outcome_id}")
            return (
                jsonify(
                    {"success": False, "message": "Failed to save assessment data"}
                ),
                500,
            )

        return jsonify({"success": True, "message": "Assessment data saved"}), 200

    except Exception as e:
        return handle_api_error(
            e, "Update assessment", "Failed to update assessment data"
        )


@outcomes_bp.route("/outcomes/<outcome_id>", methods=["DELETE"])
@permission_required("manage_courses")
def delete_course_outcome_endpoint(outcome_id: str) -> ResponseReturnValue:
    """Delete a course outcome."""
    try:
        # Verify outcome exists and institution access
        outcome = get_course_outcome(outcome_id)

        if not outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        institution_id = get_current_institution_id_safe()
        course_id = outcome.get("course_id")
        if not course_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404
        course = get_course_by_id(str(course_id))
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        success = delete_course_outcome(outcome_id)

        if success:
            return (
                jsonify(
                    {"success": True, "message": "Course outcome deleted successfully"}
                ),
                200,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to delete course outcome"}),
                500,
            )

    except Exception as e:
        return handle_api_error(
            e, "Delete course outcome", "Failed to delete course outcome"
        )
