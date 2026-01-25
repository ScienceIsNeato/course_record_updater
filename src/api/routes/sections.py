"""
Course Section API routes.

Provides endpoints for managing course sections (CRUD operations)
with role-based filtering, instructor assignment, and institution access verification.
"""

from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

from src.api.utils import (
    InstitutionContextMissingError,
    get_current_institution_id_safe,
    get_current_user_safe,
    handle_api_error,
    resolve_institution_scope,
)
from src.database.database_service import (
    assign_instructor,
    create_course_section,
    delete_course_section,
    get_all_sections,
    get_course_offering,
    get_section_by_id,
    get_sections_by_instructor,
    get_sections_by_term,
    get_user_by_id,
    update_course_section,
)
from src.services.auth_service import (
    UserRole,
    has_permission,
    permission_required,
)
from src.services.clo_workflow_service import CLOWorkflowService
from src.utils.constants import (
    INSTITUTION_CONTEXT_REQUIRED_MSG,
    NO_DATA_PROVIDED_MSG,
    NO_JSON_DATA_PROVIDED_MSG,
    SECTION_NOT_FOUND_MSG,
)
from src.utils.logging_config import get_logger

# Create blueprint
sections_bp = Blueprint("sections", __name__, url_prefix="/api")

# Initialize logger
logger = get_logger(__name__)


# ========================================
# HELPER FUNCTIONS
# ========================================


def _determine_section_filters(
    current_user: Dict[str, Any], instructor_id: Optional[str], term_id: Optional[str]
) -> Tuple[Optional[str], Optional[str]]:
    """Determine section filters based on user role and query parameters."""
    if not instructor_id and not term_id:
        if current_user["role"] == UserRole.INSTRUCTOR.value:
            # Instructors see only their own sections
            return current_user["user_id"], None
    return instructor_id, term_id


def _fetch_sections_by_filter(
    instructor_id: Optional[str], term_id: Optional[str]
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Tuple[Any, int]]]:
    """Fetch sections based on provided filters."""
    if instructor_id:
        return get_sections_by_instructor(instructor_id), None
    if term_id:
        return get_sections_by_term(term_id), None

    # No filters - get all sections for institution
    institution_id = get_current_institution_id_safe()
    if not institution_id:
        return None, (
            jsonify({"success": False, "error": INSTITUTION_CONTEXT_REQUIRED_MSG}),
            400,
        )
    return get_all_sections(institution_id), None


def _filter_sections_by_permission(
    sections: List[Dict[str, Any]], current_user: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Filter sections based on user permissions."""
    if current_user["role"] == UserRole.INSTRUCTOR.value and not has_permission(
        "view_all_sections"
    ):
        # Ensure instructors only see their own sections
        return [
            s for s in sections if s.get("instructor_id") == current_user["user_id"]
        ]
    return sections


# ========================================
# COURSE SECTION MANAGEMENT API
# ========================================


@sections_bp.route("/sections", methods=["GET"])
@permission_required("view_section_data")
def list_sections() -> ResponseReturnValue:
    """
    Get list of course sections

    Query parameters:
    - instructor_id: Filter by instructor (optional)
    - term_id: Filter by term (optional)
    """
    try:
        instructor_id = request.args.get("instructor_id")
        term_id = request.args.get("term_id")
        current_user = get_current_user_safe()

        # Determine filters based on role
        instructor_id, term_id = _determine_section_filters(
            current_user, instructor_id, term_id
        )

        # Fetch sections
        sections, error_response = _fetch_sections_by_filter(instructor_id, term_id)
        if error_response:
            return error_response

        if sections is None:
            sections = []

        # Apply permission-based filtering
        sections = _filter_sections_by_permission(sections, current_user)

        return jsonify({"success": True, "sections": sections, "count": len(sections)})

    except Exception as e:
        return handle_api_error(e, "Get sections", "Failed to retrieve sections")


@sections_bp.route("/sections", methods=["POST"])
@permission_required("manage_sections")
def create_section() -> ResponseReturnValue:
    """
    Create a new course section

    Request body should contain:
    - offering_id: Course offering ID (OR course_id + term_id)
    - section_number: Section number (required)
    - instructor_id: Instructor ID (optional)
    - enrollment: Number of enrolled students (optional)
    - capacity: Maximum enrollment (optional)
    - status: Section status (optional, default "open")
    """
    try:
        data = request.get_json(silent=True) or {}

        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        # If offering_id is provided, look up course_id and term_id
        if data.get("offering_id"):
            offering = get_course_offering(data["offering_id"])
            if not offering:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Invalid offering_id",
                        }
                    ),
                    400,
                )
            data["course_id"] = offering.get("course_id")
            data["term_id"] = offering.get("term_id")

        # Validate required fields
        required_fields = ["course_id", "term_id", "section_number"]
        missing_fields = [f for f in required_fields if not data.get(f)]

        if missing_fields:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f'Missing required fields: {", ".join(missing_fields)}',
                    }
                ),
                400,
            )

        section_id = create_course_section(data)

        if section_id:
            return (
                jsonify(
                    {
                        "success": True,
                        "section_id": section_id,
                        "message": "Course section created successfully",
                    }
                ),
                201,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to create course section"}),
                500,
            )

    except Exception as e:
        return handle_api_error(e, "Create section", "Failed to create section")


@sections_bp.route("/sections/<section_id>", methods=["GET"])
@permission_required("view_section_data")
def get_section_by_id_endpoint(section_id: str) -> ResponseReturnValue:
    """Get section details by section ID"""
    try:
        section = get_section_by_id(section_id)

        if not section:
            return jsonify({"success": False, "error": SECTION_NOT_FOUND_MSG}), 404

        # Verify institution access
        institution_id = get_current_institution_id_safe()
        offering_id = section.get("offering_id")
        if not offering_id:
            return jsonify({"success": False, "error": SECTION_NOT_FOUND_MSG}), 404
        offering = get_course_offering(str(offering_id))
        if not offering or offering.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": SECTION_NOT_FOUND_MSG}), 404

        return jsonify({"success": True, "section": section}), 200

    except Exception as e:
        return handle_api_error(e, "Get section by ID", "Failed to retrieve section")


@sections_bp.route("/sections/<section_id>", methods=["PUT"])
@permission_required("manage_sections")
def update_section_endpoint(section_id: str) -> ResponseReturnValue:
    """
    Update section details (supports new course-level assessment fields from CEI demo feedback)

    Allows updating:
    - section_number, enrollment, instructor_id (basic section data)
    - withdrawals, students_passed, students_dfic (course-level assessment data)
    - cannot_reconcile, reconciliation_note (enrollment reconciliation)
    - narrative_celebrations, narrative_challenges, narrative_changes (course reflections)
    """
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        # Check if section exists
        section = get_section_by_id(section_id)

        if not section:
            return jsonify({"success": False, "error": SECTION_NOT_FOUND_MSG}), 404

        # Verify institution access
        institution_id = get_current_institution_id_safe()
        offering_id = section.get("offering_id")
        if not offering_id:
            return jsonify({"success": False, "error": SECTION_NOT_FOUND_MSG}), 404
        offering = get_course_offering(str(offering_id))
        if not offering or offering.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": SECTION_NOT_FOUND_MSG}), 404

        # Validate enrollment if present
        if "enrollment" in data:
            try:
                enrollment = int(data["enrollment"])
                if enrollment < 0:
                    raise ValueError("Negative enrollment")
            except (ValueError, TypeError):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Enrollment must be a non-negative integer",
                        }
                    ),
                    400,
                )

        success = update_course_section(section_id, data)

        if success:
            # Fetch updated section
            updated_section = get_section_by_id(section_id)
            return (
                jsonify(
                    {
                        "success": True,
                        "section": updated_section,
                        "message": "Section updated successfully",
                    }
                ),
                200,
            )
        else:
            return jsonify({"success": False, "error": "Failed to update section"}), 500

    except Exception as e:
        return handle_api_error(e, "Update section", "Failed to update section")


@sections_bp.route("/sections/<section_id>/instructor", methods=["PATCH"])
@permission_required("manage_courses")
def assign_instructor_to_section_endpoint(section_id: str) -> ResponseReturnValue:
    """
    Assign an instructor to a section

    Request body should contain:
    - instructor_id: Instructor user ID
    """
    try:
        data = request.get_json(silent=True) or {}
        if not data or "instructor_id" not in data:
            return (
                jsonify({"success": False, "error": "instructor_id is required"}),
                400,
            )

        instructor_id = data["instructor_id"]

        # Verify section exists
        section = get_section_by_id(section_id)

        if not section:
            return jsonify({"success": False, "error": SECTION_NOT_FOUND_MSG}), 404

        # Verify institution access
        institution_id = get_current_institution_id_safe()
        offering_id = section.get("offering_id")
        if not offering_id:
            return jsonify({"success": False, "error": SECTION_NOT_FOUND_MSG}), 404
        offering = get_course_offering(str(offering_id))
        if not offering or offering.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": SECTION_NOT_FOUND_MSG}), 404

        # Verify instructor exists
        instructor = get_user_by_id(instructor_id)
        if not instructor:
            return jsonify({"success": False, "error": "Instructor not found"}), 404

        success = assign_instructor(section_id, instructor_id)

        if success:
            assigned_ok = CLOWorkflowService.mark_section_outcomes_assigned(section_id)
            if not assigned_ok:
                logger.warning(
                    "Instructor assigned to section %s but CLO statuses failed to update",
                    section_id,
                )
            return (
                jsonify(
                    {"success": True, "message": "Instructor assigned successfully"}
                ),
                200,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to assign instructor"}),
                500,
            )

    except Exception as e:
        return handle_api_error(e, "Assign instructor", "Failed to assign instructor")


@sections_bp.route("/sections/<section_id>", methods=["DELETE"])
@permission_required("manage_sections")
def delete_section_endpoint(section_id: str) -> ResponseReturnValue:
    """
    Delete section

    Removes the section from the database.
    """
    try:
        # Check if section exists
        section = get_section_by_id(section_id)

        if not section:
            return jsonify({"success": False, "error": SECTION_NOT_FOUND_MSG}), 404

        # Verify institution access
        institution_id = get_current_institution_id_safe()
        offering_id = section.get("offering_id")
        if not offering_id:
            return jsonify({"success": False, "error": SECTION_NOT_FOUND_MSG}), 404
        offering = get_course_offering(str(offering_id))
        if not offering or offering.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": SECTION_NOT_FOUND_MSG}), 404

        success = delete_course_section(section_id)

        if success:
            return (
                jsonify({"success": True, "message": "Section deleted successfully"}),
                200,
            )
        else:
            return jsonify({"success": False, "error": "Failed to delete section"}), 500

    except Exception as e:
        return handle_api_error(e, "Delete section", "Failed to delete section")
