"""Programs API routes for CRUD and course-program association management."""

from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

from src.api.utils import (
    InstitutionContextMissingError,
    get_current_institution_id_safe,
    get_current_user_id_safe,
    get_current_user_safe,
    handle_api_error,
    resolve_institution_scope,
)
from src.database.database_service import (
    add_course_to_program,
    assign_course_to_default_program,
    bulk_add_courses_to_program,
    bulk_remove_courses_from_program,
    create_program,
    delete_program,
    get_course_by_number,
    get_courses_by_program,
    get_program_by_id,
    get_programs_by_institution,
    remove_course_from_program,
    update_program,
)
from src.models.models import Program
from src.services.auth_service import UserRole, permission_required
from src.utils.constants import (
    COURSE_NOT_FOUND_MSG,
    NO_DATA_PROVIDED_MSG,
    PROGRAM_NOT_FOUND_MSG,
    USER_NOT_FOUND_MSG,
)
from src.utils.logging_config import get_logger

programs_bp = Blueprint("programs", __name__, url_prefix="/api")
logger = get_logger(__name__)


@programs_bp.route("/programs", methods=["GET"])
@permission_required("view_program_data")
def list_programs() -> ResponseReturnValue:
    """Get programs for the current institution (or all for site admins)."""
    try:
        try:
            _, institution_ids, is_global = resolve_institution_scope()
        except InstitutionContextMissingError:
            return (
                jsonify({"success": False, "error": "Institution context required"}),
                400,
            )

        if is_global:
            programs: List[Dict[str, Any]] = []
            for inst_id in institution_ids:
                programs.extend(get_programs_by_institution(inst_id))
        else:
            institution_id = institution_ids[0]
            programs = get_programs_by_institution(institution_id)

        return jsonify({"success": True, "programs": programs})

    except Exception as e:
        return handle_api_error(e, "List programs", "Failed to retrieve programs")


@programs_bp.route("/programs", methods=["POST"])
@permission_required("manage_programs")
def create_program_api() -> ResponseReturnValue:
    """Create a new program."""
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        required_fields = ["name", "short_name"]
        for field in required_fields:
            if field not in data:
                return (
                    jsonify(
                        {"success": False, "error": f"Missing required field: {field}"}
                    ),
                    400,
                )

        institution_id = get_current_institution_id_safe()
        current_user = get_current_user_safe()

        if not current_user:
            return jsonify({"success": False, "error": USER_NOT_FOUND_MSG}), 400

        if not institution_id:
            if current_user.get("role") == UserRole.SITE_ADMIN.value:
                institution_id = str(
                    data.get("institution_id")
                    or request.args.get("institution_id")
                    or ""
                )
            if not institution_id:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Institution context required to create program",
                        }
                    ),
                    400,
                )

        user_id = get_current_user_id_safe()
        if not user_id:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        program_data = Program.create_schema(
            name=data["name"],
            short_name=data["short_name"],
            institution_id=institution_id,
            created_by=user_id,
            description=data.get("description"),
            is_default=data.get("is_default", False),
            program_admins=data.get("program_admins", []),
        )

        program_id = create_program(program_data)

        if program_id:
            return (
                jsonify(
                    {
                        "success": True,
                        "program_id": program_id,
                        "message": "Program created successfully",
                    }
                ),
                201,
            )
        else:
            return jsonify({"success": False, "error": "Failed to create program"}), 500

    except Exception as e:
        return handle_api_error(e, "Create program", "Failed to create program")


@programs_bp.route("/programs/<program_id>", methods=["GET"])
@permission_required("view_program_data", context_keys=["program_id"])
def get_program(program_id: str) -> ResponseReturnValue:
    """Get program details by ID."""
    try:
        program = get_program_by_id(program_id)

        if program:
            return jsonify({"success": True, "program": program})
        else:
            return jsonify({"success": False, "error": PROGRAM_NOT_FOUND_MSG}), 404

    except Exception as e:
        return handle_api_error(e, "Get program", "Failed to retrieve program")


@programs_bp.route("/programs/<program_id>", methods=["PUT"])
@permission_required("manage_programs")
def update_program_api(program_id: str) -> ResponseReturnValue:
    """Update an existing program."""
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        program = get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": PROGRAM_NOT_FOUND_MSG}), 404

        success = update_program(program_id, data)

        if success:
            return jsonify({"success": True, "message": "Program updated successfully"})
        else:
            return jsonify({"success": False, "error": "Failed to update program"}), 500

    except Exception as e:
        return handle_api_error(e, "Update program", "Failed to update program")


@programs_bp.route("/programs/<program_id>", methods=["DELETE"])
@permission_required("manage_programs")
def delete_program_api(program_id: str) -> ResponseReturnValue:
    """Delete a program (with course reassignment to default)."""
    try:
        program = get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": PROGRAM_NOT_FOUND_MSG}), 404

        if program.get("is_default", False):
            return (
                jsonify({"success": False, "error": "Cannot delete default program"}),
                400,
            )

        try:
            courses_for_program = get_courses_by_program(program_id)  # type: ignore[name-defined]
        except Exception:
            courses_for_program = []

        force_flag = request.args.get("force", "false").lower() == "true"
        if courses_for_program and not force_flag:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Cannot delete program with assigned courses without force",
                        "code": "PROGRAM_HAS_COURSES",
                    }
                ),
                409,
            )

        institution_id = program.get("institution_id")
        programs = get_programs_by_institution(institution_id) if institution_id else []
        default_program = next(
            (p for p in programs if p.get("is_default", False)), None
        )

        if not default_program:
            logger.error(
                "[API] No default program found for institution %s - data integrity issue",
                institution_id,
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No default program found for course reassignment",
                    }
                ),
                500,
            )

        default_prog_id = default_program.get("program_id") or default_program.get("id")
        if not default_prog_id:
            logger.error(
                "[API] Default program %s has no program_id or id key: %s",
                default_program.get("name", "unknown"),
                list(default_program.keys()),
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Default program data integrity issue",
                    }
                ),
                500,
            )

        success = delete_program(program_id, default_prog_id)

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": "Program deleted successfully and courses reassigned",
                }
            )
        else:
            return jsonify({"success": False, "error": "Failed to delete program"}), 500

    except Exception as e:
        return handle_api_error(e, "Delete program", "Failed to delete program")


@programs_bp.route("/programs/<program_id>/courses", methods=["GET"])
@permission_required("view_program_data", context_keys=["program_id"])
def get_program_courses(program_id: str) -> ResponseReturnValue:
    """Get all courses associated with a program."""
    try:
        program = get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": PROGRAM_NOT_FOUND_MSG}), 404

        courses = get_courses_by_program(program_id)

        return jsonify(
            {
                "success": True,
                "program_id": program_id,
                "program_name": program.get("name"),
                "courses": courses,
                "count": len(courses),
            }
        )

    except Exception as e:
        return handle_api_error(
            e, "Get program courses", "Failed to retrieve program courses"
        )


@programs_bp.route("/programs/<program_id>/courses", methods=["POST"])
@permission_required("manage_programs")
def add_course_to_program_api(program_id: str) -> ResponseReturnValue:
    """Add a course to a program."""
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        course_id = data.get("course_id")
        if not course_id:
            return (
                jsonify(
                    {"success": False, "error": "Missing required field: course_id"}
                ),
                400,
            )

        program = get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": PROGRAM_NOT_FOUND_MSG}), 404

        course = get_course_by_number(course_id)
        if not course:
            return jsonify({"success": False, "error": COURSE_NOT_FOUND_MSG}), 404

        success = add_course_to_program(course["course_id"], program_id)

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": f"Course {course_id} added to program {program.get('name', program_id)}",
                }
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to add course to program"}),
                500,
            )

    except Exception as e:
        return handle_api_error(
            e, "Add course to program", "Failed to add course to program"
        )


@programs_bp.route("/programs/<program_id>/courses/<course_id>", methods=["DELETE"])
@permission_required("manage_programs")
def remove_course_from_program_api(
    program_id: str, course_id: str
) -> ResponseReturnValue:
    """Remove a course from a program."""
    try:
        program, institution_id = _validate_program_for_removal(program_id)
        default_program_id = _get_default_program_id(institution_id)
        success = _remove_course_with_orphan_handling(
            course_id, program_id, institution_id, default_program_id
        )
        return _build_removal_response(success, course_id, program)

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return handle_api_error(
            e, "Remove course from program", "Failed to remove course from program"
        )


def _validate_program_for_removal(program_id: str) -> Tuple[Dict[str, Any], str]:
    """Validate program exists and return program with institution ID."""
    program = get_program_by_id(program_id)
    if not program:
        raise ValueError(PROGRAM_NOT_FOUND_MSG)
    institution_id = str(program.get("institution_id") or "")
    return program, institution_id


def _get_default_program_id(institution_id: str) -> Optional[str]:
    """Get the default program ID for the institution."""
    if not institution_id:
        return None
    programs = get_programs_by_institution(institution_id)
    if not programs:
        return None
    default_program = next((p for p in programs if p.get("is_default", False)), None)
    if not default_program:
        return None
    return default_program.get("program_id") or default_program.get("id")


def _remove_course_with_orphan_handling(
    course_id: str,
    program_id: str,
    institution_id: str,
    default_program_id: Optional[str],
) -> bool:
    """Remove course from program and handle orphan prevention."""
    success = remove_course_from_program(course_id, program_id)
    if success and default_program_id:
        assign_course_to_default_program(course_id, institution_id)
    return success


def _build_removal_response(
    success: bool, course_id: str, program: Dict[str, Any]
) -> ResponseReturnValue:
    """Build response for course removal."""
    if success:
        prog_name = program.get("name", program.get("id"))
        return jsonify(
            {
                "success": True,
                "message": f"Course {course_id} removed from program {prog_name}",
            }
        )
    return (
        jsonify({"success": False, "error": "Failed to remove course from program"}),
        500,
    )


@programs_bp.route("/programs/<program_id>/courses/bulk", methods=["POST"])
@permission_required("manage_programs")
def bulk_manage_program_courses(program_id: str) -> ResponseReturnValue:
    """Bulk add or remove courses from a program."""
    try:
        validation_response = _validate_bulk_manage_request()
        if validation_response:
            return validation_response

        data = request.get_json(silent=True) or {}
        action = data.get("action")
        course_ids = data.get("course_ids", [])

        program = get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": PROGRAM_NOT_FOUND_MSG}), 404

        if action == "add":
            result, message = _execute_bulk_add(course_ids, program_id)
        else:  # remove
            result, message = _execute_bulk_remove(course_ids, program_id)

        return jsonify({"success": True, "message": message, "details": result})

    except Exception as e:
        return handle_api_error(
            e, "Bulk manage program courses", "Failed to bulk manage program courses"
        )


def _validate_bulk_manage_request() -> Optional[ResponseReturnValue]:
    """Validate bulk manage request data and return error response if invalid."""
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400
    action = data.get("action")
    course_ids = data.get("course_ids", [])
    if not action or action not in ["add", "remove"]:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid or missing action. Use 'add' or 'remove'",
                }
            ),
            400,
        )
    if not course_ids or not isinstance(course_ids, list):
        return (
            jsonify({"success": False, "error": "Missing or invalid course_ids array"}),
            400,
        )
    return None


def _execute_bulk_add(course_ids: list, program_id: str) -> Tuple[Dict[str, Any], str]:
    """Execute bulk add operation."""
    result = bulk_add_courses_to_program(course_ids, program_id)
    message = f"Bulk add operation completed: {result['success_count']} added"
    return result, message


def _execute_bulk_remove(
    course_ids: list, program_id: str
) -> Tuple[Dict[str, Any], str]:
    """Execute bulk remove operation with orphan handling."""
    institution_id = get_current_institution_id_safe()
    default_program_id = _get_default_program_id(institution_id)
    result = bulk_remove_courses_from_program(course_ids, program_id)
    if result.get("removed", 0) > 0 and default_program_id and institution_id:
        for course_id in course_ids:
            assign_course_to_default_program(course_id, institution_id)
    message = f"Bulk remove operation completed: {result.get('removed', 0)} removed"
    return result, message


@programs_bp.route("/courses/<course_id>/programs", methods=["GET"])
@permission_required("view_program_data")
def get_course_programs(course_id: str) -> ResponseReturnValue:
    """Get all programs associated with a course."""
    try:
        course = get_course_by_number(course_id)
        if not course:
            return jsonify({"success": False, "error": COURSE_NOT_FOUND_MSG}), 404

        program_ids = course.get("program_ids", [])
        programs = []
        for program_id in program_ids:
            program = get_program_by_id(program_id)
            if program:
                programs.append(program)

        return jsonify(
            {
                "success": True,
                "course_id": course_id,
                "course_title": course.get("course_title"),
                "programs": programs,
                "count": len(programs),
            }
        )

    except Exception as e:
        return handle_api_error(
            e, "Get course programs", "Failed to retrieve course programs"
        )
