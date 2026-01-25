"""Courses API routes."""

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
    assign_course_to_default_program,
    create_course,
    delete_course,
    duplicate_course_record,
    get_all_courses,
    get_course_by_id,
    get_course_by_number,
    get_courses_by_department,
    get_courses_by_program,
    get_unassigned_courses,
    update_course,
    update_course_programs,
)
from src.services.auth_service import (
    UserRole,
    get_current_program_id,
    permission_required,
)
from src.utils.constants import (
    COURSE_NOT_FOUND_MSG,
    INSTITUTION_CONTEXT_REQUIRED_MSG,
    NO_DATA_PROVIDED_MSG,
    NO_JSON_DATA_PROVIDED_MSG,
    PERMISSION_DENIED_MSG,
)
from src.utils.logging_config import get_logger

courses_bp = Blueprint("courses", __name__, url_prefix="/api")
logger = get_logger(__name__)


@courses_bp.route("/courses", methods=["GET"])
@permission_required("view_program_data")
def list_courses() -> ResponseReturnValue:
    """Get courses, optionally filtered by department and program context."""
    try:
        current_user, institution_ids, is_global = _resolve_courses_scope()
        current_program_id = _resolve_program_override(current_user)
        department_filter = request.args.get("department")

        courses, context_info = _get_courses_by_scope(
            is_global, institution_ids, current_program_id, department_filter
        )

        return jsonify(
            {
                "success": True,
                "courses": courses,
                "count": len(courses),
                "context": context_info,
                "current_program_id": current_program_id,
            }
        )

    except Exception as e:
        return handle_api_error(e, "Get courses", "Failed to retrieve courses")


def _resolve_courses_scope() -> Tuple[Dict[str, Any], List[str], bool]:
    """Resolve institution scope for courses listing."""
    try:
        return resolve_institution_scope()
    except InstitutionContextMissingError:
        raise ValueError(INSTITUTION_CONTEXT_REQUIRED_MSG)


def _resolve_program_override(current_user: Dict[str, Any]) -> Optional[str]:
    """Resolve program ID override with permission validation."""
    program_id_override = request.args.get("program_id")
    current_program_id = get_current_program_id()

    if not program_id_override:
        return current_program_id

    if _user_can_access_program(current_user, program_id_override):
        return program_id_override
    else:
        raise PermissionError("Access denied to specified program")


def _user_can_access_program(current_user: Dict[str, Any], program_id: str) -> bool:
    """Check if user can access the specified program."""
    if not current_user:
        return False
    if current_user.get("role") == UserRole.SITE_ADMIN.value:
        return True
    return program_id in current_user.get("program_ids", [])


def _get_courses_by_scope(
    is_global: bool,
    institution_ids: List[str],
    current_program_id: Optional[str],
    department_filter: Optional[str],
) -> Tuple[List[Dict[str, Any]], str]:
    """Get courses and context info based on scope and filters."""
    if is_global:
        return _get_global_courses(institution_ids, department_filter)
    else:
        return _get_institution_courses(
            institution_ids[0], current_program_id, department_filter
        )


def _get_global_courses(
    institution_ids: List[str], department_filter: Optional[str]
) -> Tuple[List[Dict[str, Any]], str]:
    """Get courses across all institutions with optional department filter."""
    courses: List[Dict[str, Any]] = []
    for inst_id in institution_ids:
        courses.extend(get_all_courses(inst_id))

    context_info = "system-wide"

    if department_filter:
        courses = [c for c in courses if c.get("department") == department_filter]
        context_info = f"system-wide, department {department_filter}"

    return courses, context_info


def _get_institution_courses(
    institution_id: str,
    current_program_id: Optional[str],
    department_filter: Optional[str],
) -> Tuple[List[Dict[str, Any]], str]:
    """Get courses for a specific institution with optional program/department filters."""
    if current_program_id:
        return _get_program_courses(current_program_id, department_filter)
    elif department_filter:
        courses = get_courses_by_department(institution_id, department_filter)
        context_info = f"department {department_filter}"
        return courses, context_info
    else:
        courses = get_all_courses(institution_id)
        context_info = f"institution {institution_id}"

        current_user = get_current_user_safe()
        if current_user and current_user.get("role") == UserRole.PROGRAM_ADMIN.value:
            user_program_ids = current_user.get("program_ids", [])
            if user_program_ids:
                courses = [
                    c
                    for c in courses
                    if any(pid in user_program_ids for pid in c.get("program_ids", []))
                ]
                context_info = f"programs {user_program_ids}"

        return courses, context_info


def _get_program_courses(
    program_id: str, department_filter: Optional[str]
) -> Tuple[List[Dict[str, Any]], str]:
    """Get courses for a specific program with optional department filter."""
    courses = get_courses_by_program(program_id)
    context_info = f"program {program_id}"

    if department_filter:
        courses = [c for c in courses if c.get("department") == department_filter]

    return courses, context_info


@courses_bp.route("/courses", methods=["POST"])
@permission_required("manage_courses")
def create_course_api() -> ResponseReturnValue:
    """Create a new course."""
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        required_fields = ["course_number", "course_title", "department"]
        missing_fields = [f for f in required_fields if not data.get(f)]
        if missing_fields:
            msg = f'Missing required fields: {", ".join(missing_fields)}'
            return jsonify({"success": False, "error": msg}), 400

        institution_id = get_current_institution_id_safe()
        if not institution_id:
            return (
                jsonify({"success": False, "error": INSTITUTION_CONTEXT_REQUIRED_MSG}),
                400,
            )

        data["institution_id"] = institution_id
        course_id = create_course(data)

        if course_id:
            return (
                jsonify(
                    {
                        "success": True,
                        "course_id": course_id,
                        "message": "Course created successfully",
                    }
                ),
                201,
            )
        else:
            return jsonify({"success": False, "error": "Failed to create course"}), 500

    except Exception as e:
        return handle_api_error(e, "Create course", "Failed to create course")


@courses_bp.route("/courses/<course_number>", methods=["GET"])
@permission_required("view_program_data")
def get_course(course_number: str) -> ResponseReturnValue:
    """Get course details by course number"""
    try:
        course = get_course_by_number(course_number)

        if course:
            return jsonify({"success": True, "course": course})
        else:
            return jsonify({"success": False, "error": COURSE_NOT_FOUND_MSG}), 404

    except Exception as e:
        return handle_api_error(e, "Get course by number", "Failed to retrieve course")


@courses_bp.route("/courses/unassigned", methods=["GET"])
@permission_required("manage_courses")
def list_unassigned_courses() -> ResponseReturnValue:
    """Get list of courses not assigned to any program"""
    try:
        try:
            _, institution_ids, is_global = resolve_institution_scope()
        except InstitutionContextMissingError:
            return (
                jsonify({"success": False, "error": INSTITUTION_CONTEXT_REQUIRED_MSG}),
                400,
            )

        if is_global:
            courses: List[Dict[str, Any]] = []
            for inst_id in institution_ids:
                courses.extend(get_unassigned_courses(inst_id))
            context_message = "system-wide"
        else:
            institution_id = institution_ids[0]
            courses = get_unassigned_courses(institution_id)
            context_message = f"institution {institution_id}"

        return jsonify(
            {
                "success": True,
                "courses": courses,
                "count": len(courses),
                "message": f"Found {len(courses)} unassigned courses ({context_message})",
            }
        )

    except Exception as e:
        return handle_api_error(
            e, "Get unassigned courses", "Failed to retrieve unassigned courses"
        )


@courses_bp.route("/courses/<course_id>/assign-default", methods=["POST"])
@permission_required("manage_courses")
def assign_course_to_default(course_id: str) -> ResponseReturnValue:
    """Assign a course to the default 'General' program"""
    try:
        institution_id = get_current_institution_id_safe()
        if not institution_id:
            current_user = get_current_user_safe()
            if current_user and current_user.get("role") == UserRole.SITE_ADMIN.value:
                payload = request.get_json(silent=True) or {}
                institution_id = str(
                    payload.get("institution_id")
                    or request.args.get("institution_id")
                    or ""
                )
            if not institution_id:
                return (
                    jsonify(
                        {"success": False, "error": INSTITUTION_CONTEXT_REQUIRED_MSG}
                    ),
                    400,
                )

        success = assign_course_to_default_program(course_id, institution_id)
        if success:
            return jsonify(
                {
                    "success": True,
                    "message": "Course assigned to default program successfully",
                }
            )
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Failed to assign course to default program",
                }
            ),
            500,
        )

    except Exception as e:
        return handle_api_error(
            e, "Assign course to default", "Failed to assign course to default program"
        )


@courses_bp.route("/courses/by-id/<course_id>", methods=["GET"])
@permission_required("view_program_data")
def get_course_by_id_endpoint(course_id: str) -> ResponseReturnValue:
    """Get course details by course ID"""
    try:
        course = get_course_by_id(course_id)

        if course:
            return jsonify({"success": True, "course": course}), 200
        else:
            return jsonify({"success": False, "error": COURSE_NOT_FOUND_MSG}), 404

    except Exception as e:
        return handle_api_error(e, "Get course by ID", "Failed to retrieve course")


@courses_bp.route("/courses/<course_id>", methods=["PUT"])
@permission_required("manage_courses")
def update_course_endpoint(course_id: str) -> ResponseReturnValue:
    """Update course details."""
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        course = get_course_by_id(course_id)
        if not course:
            return jsonify({"success": False, "error": COURSE_NOT_FOUND_MSG}), 404

        current_user = get_current_user_safe()
        if current_user.get("role") != UserRole.SITE_ADMIN.value and current_user.get(
            "institution_id"
        ) != course.get("institution_id"):
            return jsonify({"success": False, "error": PERMISSION_DENIED_MSG}), 403

        if "program_ids" in data:
            program_ids = data.pop("program_ids")
            update_course_programs(course_id, program_ids)

        success = update_course(course_id, data)

        if success:
            updated_course = get_course_by_id(course_id)
            return (
                jsonify(
                    {
                        "success": True,
                        "course": updated_course,
                        "message": "Course updated successfully",
                    }
                ),
                200,
            )
        return (
            jsonify({"success": False, "error": "Failed to update course"}),
            500,
        )

    except Exception as e:
        return handle_api_error(e, "Update course", "Failed to update course")


@courses_bp.route("/courses/<course_id>/duplicate", methods=["POST"])
@permission_required("manage_courses")
def duplicate_course_endpoint(course_id: str) -> ResponseReturnValue:
    """Duplicate an existing course for the current institution."""
    try:
        source_course = get_course_by_id(course_id)
        if not source_course:
            return jsonify({"success": False, "error": COURSE_NOT_FOUND_MSG}), 404

        current_user = get_current_user_safe()
        if current_user.get("role") != UserRole.SITE_ADMIN.value and current_user.get(
            "institution_id"
        ) != source_course.get("institution_id"):
            return jsonify({"success": False, "error": PERMISSION_DENIED_MSG}), 403

        payload = request.get_json(silent=True) or {}
        override_fields = {
            key: payload.get(key)
            for key in [
                "course_number",
                "course_title",
                "department",
                "credit_hours",
                "active",
            ]
            if payload.get(key) is not None
        }

        if "program_ids" in payload:
            override_fields["program_ids"] = payload.get("program_ids")

        duplicate_programs = payload.get("duplicate_programs", True)

        new_course_id = duplicate_course_record(
            source_course,
            overrides=override_fields,
            duplicate_programs=duplicate_programs,
        )

        if not new_course_id:
            return (
                jsonify({"success": False, "error": "Failed to duplicate course"}),
                500,
            )

        new_course = get_course_by_id(new_course_id)
        if not new_course:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Failed to retrieve duplicated course",
                    }
                ),
                500,
            )

        return (
            jsonify(
                {
                    "success": True,
                    "course": new_course,
                    "message": f"Course duplicated as {new_course.get('course_number')}",
                }
            ),
            201,
        )

    except Exception as e:
        return handle_api_error(e, "Duplicate course", "Failed to duplicate course")


@courses_bp.route("/courses/<course_id>", methods=["DELETE"])
@permission_required("manage_courses")
def delete_course_endpoint(course_id: str) -> ResponseReturnValue:
    """Delete course and all associated offerings, sections, and outcomes."""
    try:
        course = get_course_by_id(course_id)
        if not course:
            return jsonify({"success": False, "error": COURSE_NOT_FOUND_MSG}), 404

        current_user = get_current_user_safe()
        if current_user.get("role") != UserRole.SITE_ADMIN.value and current_user.get(
            "institution_id"
        ) != course.get("institution_id"):
            return jsonify({"success": False, "error": PERMISSION_DENIED_MSG}), 403

        success = delete_course(course_id)

        if success:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Course '{course['course_number']}' deleted successfully",
                    }
                ),
                200,
            )
        return (
            jsonify({"success": False, "error": "Failed to delete course"}),
            500,
        )

    except Exception as e:
        return handle_api_error(e, "Delete course", "Failed to delete course")
