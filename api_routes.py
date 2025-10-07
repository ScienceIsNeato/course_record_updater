"""
API Routes Module

This module defines the new REST API endpoints for the CEI Course Management System.
These routes provide a proper REST API structure while maintaining backward compatibility
with the existing single-page application.
"""

import re
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

# Constants for error messages
PERMISSION_DENIED_MSG = "Permission denied"
USER_NOT_FOUND_MSG = "User not found"

# Import our services
from auth_service import (
    UserRole,
    clear_current_program_id,
    get_current_institution_id,
    get_current_program_id,
    get_current_user,
    has_permission,
    login_required,
    permission_required,
    set_current_program_id,
)
from constants import (
    COURSE_NOT_FOUND_MSG,
    INSTITUTION_CONTEXT_REQUIRED_MSG,
    INVALID_EMAIL_FORMAT_MSG,
    INVITATION_NOT_FOUND_MSG,
    NO_DATA_PROVIDED_MSG,
    NO_JSON_DATA_PROVIDED_MSG,
    NOT_FOUND_MSG,
    PROGRAM_NOT_FOUND_MSG,
)
from dashboard_service import DashboardService, DashboardServiceError
from database_service import (
    add_course_to_program,
    assign_course_to_default_program,
    bulk_add_courses_to_program,
    bulk_remove_courses_from_program,
    create_course,
    create_course_section,
    create_new_institution,
    create_program,
    create_term,
    delete_program,
    get_active_terms,
    get_all_courses,
    get_all_institutions,
    get_all_instructors,
    get_all_sections,
    get_all_users,
    get_course_by_number,
    get_courses_by_department,
    get_courses_by_program,
    get_institution_by_id,
    get_institution_instructor_count,
    get_program_by_id,
    get_programs_by_institution,
    get_sections_by_instructor,
    get_sections_by_term,
    get_unassigned_courses,
    get_user_by_id,
    get_users_by_role,
    remove_course_from_program,
    update_program,
    update_user,
)
from export_service import ExportConfig, create_export_service
from import_service import import_excel
from logging_config import get_logger
from models import Program
from registration_service import (
    RegistrationError,
    get_registration_status,
    register_institution_admin,
    resend_verification_email,
    verify_email,
)

# Create API blueprint
api = Blueprint("api", __name__, url_prefix="/api")

# Get logger for this module
logger = get_logger(__name__)

# Constants for export file types
_DEFAULT_EXPORT_EXTENSION = ".xlsx"

# Mimetype mapping for common export formats
_EXPORT_MIMETYPES = {
    _DEFAULT_EXPORT_EXTENSION: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv",
    ".json": "application/json",
}


def _get_mimetype_for_extension(file_extension: str) -> str:
    """
    Get appropriate mimetype for a file extension.

    Args:
        file_extension: File extension (e.g., '.xlsx', '.csv')

    Returns:
        str: Appropriate mimetype, defaults to 'application/octet-stream' if unknown
    """
    return _EXPORT_MIMETYPES.get(file_extension.lower(), "application/octet-stream")


class InstitutionContextMissingError(Exception):
    """Raised when a request requires institution scope but none is set."""


def _resolve_institution_scope(require: bool = True):
    """Return the current user, accessible institution ids, and whether scope is global."""

    current_user = get_current_user()
    institution_id = get_current_institution_id()

    if institution_id:
        return current_user, [institution_id], False

    if current_user and current_user.get("role") == UserRole.SITE_ADMIN.value:
        institutions = get_all_institutions()
        institution_ids = [
            inst["institution_id"]
            for inst in institutions
            if inst.get("institution_id")
        ]
        return current_user, institution_ids, True

    if require:
        raise InstitutionContextMissingError()

    return current_user, [], False


@api.before_request
def validate_context():
    """Validate institution and program context for API requests"""
    # Skip validation for context management endpoints
    if request.endpoint and (
        request.endpoint.startswith("api.get_program_context")
        or request.endpoint.startswith("api.switch_program_context")
        or request.endpoint.startswith("api.clear_program_context")
        or request.endpoint.startswith("api.create_institution")
        or request.endpoint.startswith("api.list_institutions")
        or "auth" in request.endpoint  # Skip for auth endpoints
    ):
        return

    # Skip validation for non-API endpoints
    if not request.endpoint or not request.endpoint.startswith("api."):
        return

    # Skip validation for OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        return

    try:
        current_user = get_current_user()
        if not current_user:
            return  # Let the auth decorators handle authentication

        # Site admins don't need context validation
        if current_user.get("role") == UserRole.SITE_ADMIN.value:
            return

        # Validate institution context for non-site-admin users
        institution_id = get_current_institution_id()
        if not institution_id:
            logger.warning(
                f"Missing institution context for user {current_user.get('user_id')} on endpoint {request.endpoint}"
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Institution context required",
                        "code": "MISSING_INSTITUTION_CONTEXT",
                    }
                ),
                400,
            )

        # Log context for debugging
        current_program_id = get_current_program_id()
        logger.debug(
            f"Request context - User: {current_user.get('user_id')}, Institution: {institution_id}, Program: {current_program_id}"
        )

    except Exception as e:
        logger.error(f"Context validation error: {e}")
        # Don't block requests on validation errors, let them proceed
        return


@api.route("/dashboard/data", methods=["GET"])
@login_required
def get_dashboard_data_route():
    """Return aggregated dashboard data for the current user."""
    try:
        service = DashboardService()
        payload = service.get_dashboard_data(get_current_user())
        return jsonify({"success": True, "data": payload})
    except DashboardServiceError as exc:
        return handle_api_error(exc, "Dashboard data", "Failed to load dashboard data")
    except Exception as exc:
        return handle_api_error(exc, "Dashboard data", "Failed to load dashboard data")


# Constants are now imported from constants.py


def handle_api_error(
    e, operation_name="API operation", user_message="An error occurred", status_code=500
):
    """
    Securely handle API errors by logging full details while returning sanitized responses.

    Args:
        e: The exception that occurred
        operation_name: Description of what operation failed (for logging)
        user_message: Safe message to return to the user

    Returns:
        tuple: (JSON response, HTTP status code)
    """
    # Log full error details for debugging (includes stack trace)
    logger.error(
        f"{operation_name} failed: {str(e)}\n"
        f"Full traceback:\n{traceback.format_exc()}"
    )

    # Return sanitized response to user
    return jsonify({"success": False, "error": user_message}), status_code


# ========================================
# DASHBOARD ROUTES (Role-based views)
# ========================================


# ========================================
# INSTITUTION MANAGEMENT API
# ========================================


@api.route("/institutions", methods=["GET"])
@permission_required("manage_institutions")
def list_institutions():
    """Get list of all institutions (site admin only)"""
    try:
        institutions = get_all_institutions()

        # Add current instructor counts
        for institution in institutions:
            institution["current_instructor_count"] = get_institution_instructor_count(
                institution["institution_id"]
            )

        return jsonify(
            {"success": True, "institutions": institutions, "count": len(institutions)}
        )

    except Exception as e:
        return handle_api_error(
            e, "Get institutions", "Failed to retrieve institutions"
        )


@api.route("/institutions", methods=["POST"])
def create_institution():
    """Create a new institution with its first admin user (public endpoint for registration)"""
    try:
        data = request.get_json()

        # Validate required fields
        required_institution_fields = ["name", "short_name", "domain"]
        required_user_fields = ["email", "first_name", "last_name", "password"]

        institution_data = data.get("institution", {})
        user_data = data.get("admin_user", {})

        # Validate institution data
        for field in required_institution_fields:
            if not institution_data.get(field):
                return (
                    jsonify(
                        {"success": False, "error": f"Institution {field} is required"}
                    ),
                    400,
                )

        # Validate user data
        for field in required_user_fields:
            if not user_data.get(field):
                return (
                    jsonify(
                        {"success": False, "error": f"Admin user {field} is required"}
                    ),
                    400,
                )

        # Create institution and admin user
        result = create_new_institution(institution_data, user_data)
        if not result:
            return (
                jsonify({"success": False, "error": "Failed to create institution"}),
                500,
            )

        institution_id, user_id = result

        return (
            jsonify(
                {
                    "success": True,
                    "institution_id": institution_id,
                    "admin_user_id": user_id,
                    "message": "Institution and admin user created successfully",
                }
            ),
            201,
        )

    except Exception as e:
        return handle_api_error(e, "Create institution", "Failed to create institution")


@api.route("/institutions/<institution_id>", methods=["GET"])
@permission_required("view_institution_data", context_keys=["institution_id"])
def get_institution_details(institution_id: str):
    """Get institution details (users can only view their own institution)"""
    try:
        current_user = get_current_user()

        # Users can only view their own institution unless they're site admin
        if (
            current_user.get("institution_id") != institution_id
            and current_user.get("role") != UserRole.SITE_ADMIN.value
        ):
            return jsonify({"success": False, "error": "Access denied"}), 403

        institution = get_institution_by_id(institution_id)
        if not institution:
            return jsonify({"success": False, "error": "Institution not found"}), 404

        # Add current instructor count
        institution["current_instructor_count"] = get_institution_instructor_count(
            institution_id
        )

        return jsonify({"success": True, "institution": institution})

    except Exception as e:
        return handle_api_error(e, "Get institution", "Failed to retrieve institution")


# ========================================
# CONTEXT MANAGEMENT API
# ========================================


@api.route("/context/program", methods=["GET"])
@login_required
def get_program_context():
    """Get current user's program context and accessible programs"""
    try:
        current_user = get_current_user()
        current_program_id = get_current_program_id()
        accessible_programs = current_user.get("program_ids", [])

        # Get program details for accessible programs
        program_details = []
        for program_id in accessible_programs:
            program = get_program_by_id(program_id)
            if program:
                program_details.append(program)

        return jsonify(
            {
                "success": True,
                "current_program_id": current_program_id,
                "program_ids": program_details,
                "has_multiple_programs": len(accessible_programs) > 1,
            }
        )

    except Exception as e:
        return handle_api_error(
            e, "Get program context", "Failed to retrieve program context"
        )


@api.route("/context/program/<program_id>", methods=["POST"])
@login_required
def switch_program_context(program_id: str):
    """Switch user's active program context"""
    try:
        current_user = get_current_user()

        # Verify user has access to this program
        accessible_programs = current_user.get("program_ids", [])
        if program_id not in accessible_programs:
            return jsonify({"success": False, "error": "Access denied to program"}), 403

        # Verify program exists
        program = get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": "Program not found"}), 404

        # Switch context
        if set_current_program_id(program_id):
            return jsonify(
                {
                    "success": True,
                    "message": f"Switched to program: {program.get('name', program_id)}",
                    "current_program_id": program_id,
                    "program": program,
                }
            )
        else:
            return (
                jsonify(
                    {"success": False, "error": "Failed to switch program context"}
                ),
                500,
            )

    except Exception as e:
        return handle_api_error(
            e, "Switch program context", "Failed to switch program context"
        )


@api.route("/context/program", methods=["DELETE"])
@login_required
def clear_program_context():
    """Clear user's active program context (return to institution-wide view)"""
    try:
        if clear_current_program_id():
            return jsonify(
                {
                    "success": True,
                    "message": "Cleared program context - now viewing institution-wide data",
                    "current_program_id": None,
                }
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to clear program context"}),
                500,
            )

    except Exception as e:
        return handle_api_error(
            e, "Clear program context", "Failed to clear program context"
        )


# ========================================
# USER MANAGEMENT API
# ========================================


@api.route("/users", methods=["GET"])
@permission_required("manage_users")
def list_users():
    """
    Get list of users, optionally filtered by role

    Query parameters:
    - role: Filter by user role (optional)
    - department: Filter by department (optional)
    """
    try:
        # Resolve institution scope and validate access
        _, institution_ids, is_global = _resolve_users_scope()

        # Get filter parameters
        role_filter = request.args.get("role")
        department_filter = request.args.get("department")

        # Get users based on scope and filters
        users = _get_users_by_scope(is_global, institution_ids, role_filter)

        # Apply department filter if specified
        if department_filter and users:
            users = [u for u in users if u.get("department") == department_filter]

        return jsonify({"success": True, "users": users, "count": len(users)})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return handle_api_error(e, "Get users", "Failed to retrieve users")


def _resolve_users_scope():
    """Resolve institution scope for user listing."""
    try:
        return _resolve_institution_scope()
    except InstitutionContextMissingError:
        raise ValueError(INSTITUTION_CONTEXT_REQUIRED_MSG)


def _get_users_by_scope(is_global: bool, institution_ids: list, role_filter: str):
    """Get users based on scope (global vs institution) and role filter."""
    if is_global:
        return _get_global_users(institution_ids, role_filter)
    else:
        return _get_institution_users(institution_ids[0], role_filter)


def _get_global_users(institution_ids: list, role_filter: str):
    """Get users for global scope with optional role filtering."""
    if role_filter:
        users = get_users_by_role(role_filter)
        if institution_ids:
            # Filter to users in accessible institutions
            users = [
                u
                for u in users
                if not u.get("institution_id")
                or u.get("institution_id") in institution_ids
            ]
        return users
    else:
        # Get all users from all accessible institutions
        users = []
        for inst_id in institution_ids:
            users.extend(get_all_users(inst_id))
        return users


def _get_institution_users(institution_id: str, role_filter: str):
    """Get users for single institution scope with optional role filtering."""
    if role_filter:
        # Filter users by role and institution
        return [
            u
            for u in get_users_by_role(role_filter)
            if u.get("institution_id") == institution_id
        ]
    else:
        # Get all users for the institution
        return get_all_users(institution_id)


@api.route("/users", methods=["POST"])
@permission_required("manage_users")
def create_user():
    """
    Create a new user

    Request body should contain:
    - email: User's email address
    - first_name: User's first name
    - last_name: User's last name
    - role: User's role (instructor, program_admin, site_admin)
    - department: User's department (optional)
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        # Validate required fields
        required_fields = ["email", "first_name", "last_name", "role"]
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

        # NOTE: create_user implementation will be added when user management API is implemented
        # user_id = create_user(data)
        user_id = "stub-user-id"  # Stub for now

        if user_id:
            return (
                jsonify(
                    {
                        "success": True,
                        "user_id": user_id,
                        "message": "User created successfully",
                    }
                ),
                201,
            )
        else:
            return jsonify({"success": False, "error": "Failed to create user"}), 500

    except Exception as e:
        return handle_api_error(e, "Create user", "Failed to create user")


@api.route("/users/<user_id>", methods=["GET"])
@login_required
def get_user_api(user_id: str):
    """
    Get user details by ID

    Users can only view their own details unless they have manage_users permission
    """
    try:
        current_user = get_current_user()

        # Check permissions - users can view their own info, admins can view any
        if user_id != current_user["user_id"] and not has_permission("manage_users"):
            return jsonify({"success": False, "error": PERMISSION_DENIED_MSG}), 403

        user = get_user_by_id(user_id)

        if user:
            return jsonify({"success": True, "user": user})
        else:
            return jsonify({"success": False, "error": USER_NOT_FOUND_MSG}), 404

    except Exception as e:
        return handle_api_error(e, "Get user by ID", "Failed to retrieve user")


@api.route("/users/<user_id>", methods=["PUT"])
@permission_required("manage_users")
def update_user_api(user_id: str):
    """
    Update user details

    Request body should contain fields to update:
    - first_name: User's first name
    - last_name: User's last name
    - role: User's role
    - account_status: User's account status
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        # Check if user exists
        existing_user = get_user_by_id(user_id)
        if not existing_user:
            return jsonify({"success": False, "error": USER_NOT_FOUND_MSG}), 404

        # Update user
        success = update_user(user_id, data)

        if success:
            # Return updated user data
            updated_user = get_user_by_id(user_id)
            return jsonify(
                {
                    "success": True,
                    "user": updated_user,
                    "message": "User updated successfully",
                }
            )
        else:
            return jsonify({"success": False, "error": "Failed to update user"}), 500

    except Exception as e:
        return handle_api_error(e, "Update user", "Failed to update user")


# ========================================
# COURSE MANAGEMENT API
# ========================================


@api.route("/courses", methods=["GET"])
@permission_required("view_program_data")
def list_courses():
    """
    Get list of courses, optionally filtered by department and program context

    Query parameters:
    - department: Filter by department (optional)
    - program_id: Override program context (optional, requires appropriate permissions)
    """
    try:
        # Resolve institution scope and validate access
        current_user, institution_ids, is_global = _resolve_courses_scope()

        # Handle program ID override with permission check
        current_program_id = _resolve_program_override(current_user)

        # Get department filter
        department_filter = request.args.get("department")

        # Get courses and context based on scope
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


def _resolve_courses_scope():
    """Resolve institution scope for courses listing."""
    try:
        return _resolve_institution_scope()
    except InstitutionContextMissingError:
        raise ValueError(INSTITUTION_CONTEXT_REQUIRED_MSG)


def _resolve_program_override(current_user):
    """Resolve program ID override with permission validation."""
    program_id_override = request.args.get("program_id")
    current_program_id = get_current_program_id()

    if not program_id_override:
        return current_program_id

    # Check if user has access to the specified program
    if _user_can_access_program(current_user, program_id_override):
        return program_id_override
    else:
        raise PermissionError("Access denied to specified program")


def _user_can_access_program(current_user, program_id):
    """Check if user can access the specified program."""
    if not current_user:
        return False

    # Site admins can access any program
    if current_user.get("role") == UserRole.SITE_ADMIN.value:
        return True

    # Check if program is in user's accessible programs
    accessible_programs = current_user.get("program_ids", [])
    return program_id in accessible_programs


def _get_courses_by_scope(
    is_global, institution_ids, current_program_id, department_filter
):
    """Get courses and context info based on scope and filters."""
    if is_global:
        return _get_global_courses(institution_ids, department_filter)
    else:
        return _get_institution_courses(
            institution_ids[0], current_program_id, department_filter
        )


def _get_global_courses(institution_ids, department_filter):
    """Get courses across all institutions with optional department filter."""
    courses: List[Dict[str, Any]] = []
    for inst_id in institution_ids:
        courses.extend(get_all_courses(inst_id))

    context_info = "system-wide"

    if department_filter:
        courses = [c for c in courses if c.get("department") == department_filter]
        context_info = f"system-wide, department {department_filter}"

    return courses, context_info


def _get_institution_courses(institution_id, current_program_id, department_filter):
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
        return courses, context_info


def _get_program_courses(program_id, department_filter):
    """Get courses for a specific program with optional department filter."""
    courses = get_courses_by_program(program_id)
    context_info = f"program {program_id}"

    if department_filter:
        courses = [c for c in courses if c.get("department") == department_filter]

    return courses, context_info


@api.route("/courses", methods=["POST"])
@permission_required("manage_courses")
def create_course_api():
    """
    Create a new course

    Request body should contain:
    - course_number: Course number (e.g., "ACC-201")
    - course_title: Course title
    - department: Department name
    - credit_hours: Number of credit hours (optional, default 3)
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        # Validate required fields
        required_fields = ["course_number", "course_title", "department"]
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

        # Add institutional context - all courses must be associated with an institution
        institution_id = get_current_institution_id()
        if not institution_id:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Institution context required to create courses",
                    }
                ),
                400,
            )

        # Ensure institution_id is set in the course data
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


@api.route("/courses/<course_number>", methods=["GET"])
@permission_required("view_program_data")
def get_course(course_number: str):
    """Get course details by course number"""
    try:
        course = get_course_by_number(course_number)

        if course:
            return jsonify({"success": True, "course": course})
        else:
            return jsonify({"success": False, "error": COURSE_NOT_FOUND_MSG}), 404

    except Exception as e:
        return handle_api_error(e, "Get course by number", "Failed to retrieve course")


@api.route("/courses/unassigned", methods=["GET"])
@permission_required("manage_courses")
def list_unassigned_courses():
    """Get list of courses not assigned to any program"""
    try:
        try:
            _, institution_ids, is_global = _resolve_institution_scope()
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


@api.route("/courses/<course_id>/assign-default", methods=["POST"])
@permission_required("manage_courses")
def assign_course_to_default(course_id: str):
    """Assign a course to the default 'General' program"""
    try:
        institution_id = get_current_institution_id()
        if not institution_id:
            current_user = get_current_user()
            if current_user and current_user.get("role") == UserRole.SITE_ADMIN.value:
                payload = request.get_json(silent=True) or {}
                institution_id = payload.get("institution_id") or request.args.get(
                    "institution_id"
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
        else:
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


# ========================================
# INSTRUCTOR MANAGEMENT API
# ========================================


@api.route("/instructors", methods=["GET"])
@permission_required("view_program_data")
def list_instructors():
    """Get list of all instructors"""
    try:
        try:
            _, institution_ids, is_global = _resolve_institution_scope()
        except InstitutionContextMissingError:
            return (
                jsonify({"success": False, "error": INSTITUTION_CONTEXT_REQUIRED_MSG}),
                400,
            )

        if is_global:
            instructors: List[Dict[str, Any]] = []
            for inst_id in institution_ids:
                instructors.extend(get_all_instructors(inst_id))
        else:
            instructors = get_all_instructors(institution_ids[0])

        return jsonify(
            {"success": True, "instructors": instructors, "count": len(instructors)}
        )

    except Exception as e:
        return handle_api_error(e, "Get instructors", "Failed to retrieve instructors")


# ========================================
# TERM MANAGEMENT API
# ========================================


@api.route("/terms", methods=["GET"])
@permission_required("view_program_data")
def list_terms():
    """Get list of active terms"""
    try:
        try:
            _, institution_ids, is_global = _resolve_institution_scope()
        except InstitutionContextMissingError:
            return (
                jsonify({"success": False, "error": INSTITUTION_CONTEXT_REQUIRED_MSG}),
                400,
            )

        if is_global:
            terms: List[Dict[str, Any]] = []
            for inst_id in institution_ids:
                terms.extend(get_active_terms(inst_id))
        else:
            terms = get_active_terms(institution_ids[0])

        return jsonify({"success": True, "terms": terms, "count": len(terms)})

    except Exception as e:
        return handle_api_error(e, "Get terms", "Failed to retrieve terms")


@api.route("/terms", methods=["POST"])
@permission_required("manage_terms")
def create_term_api():
    """
    Create a new academic term

    Request body should contain:
    - name: Term name (e.g., "2024 Fall")
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    - assessment_due_date: Assessment due date (YYYY-MM-DD)
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        # Validate required fields
        required_fields = ["name", "start_date", "end_date", "assessment_due_date"]
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

        term_id = create_term(data)

        if term_id:
            return (
                jsonify(
                    {
                        "success": True,
                        "term_id": term_id,
                        "message": "Term created successfully",
                    }
                ),
                201,
            )
        else:
            return jsonify({"success": False, "error": "Failed to create term"}), 500

    except Exception as e:
        return handle_api_error(e, "Create term", "Failed to create term")


# ========================================
# PROGRAM MANAGEMENT API
# ========================================


@api.route("/programs", methods=["GET"])
@permission_required("view_program_data")
def list_programs():
    """Get programs for the current institution (or all programs for site admins)."""
    try:
        try:
            _, institution_ids, is_global = _resolve_institution_scope()
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


@api.route("/programs", methods=["POST"])
@permission_required("manage_programs")
def create_program_api():
    """Create a new program"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        # Validate required fields
        required_fields = ["name", "short_name"]
        for field in required_fields:
            if field not in data:
                return (
                    jsonify(
                        {"success": False, "error": f"Missing required field: {field}"}
                    ),
                    400,
                )

        institution_id = get_current_institution_id()
        current_user = get_current_user()

        if not current_user:
            return jsonify({"success": False, "error": USER_NOT_FOUND_MSG}), 400

        if not institution_id:
            if current_user.get("role") == UserRole.SITE_ADMIN.value:
                institution_id = data.get("institution_id") or request.args.get(
                    "institution_id"
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

        # Create program schema
        program_data = Program.create_schema(
            name=data["name"],
            short_name=data["short_name"],
            institution_id=institution_id,
            created_by=current_user.get("user_id", "unknown"),
            description=data.get("description"),
            is_default=data.get("is_default", False),
            program_admins=data.get("program_admins", []),
        )

        # Create program in database
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


@api.route("/programs/<program_id>", methods=["GET"])
@permission_required("view_program_data", context_keys=["program_id"])
def get_program(program_id: str):
    """Get program details by ID"""
    try:
        program = get_program_by_id(program_id)

        if program:
            return jsonify({"success": True, "program": program})
        else:
            return jsonify({"success": False, "error": PROGRAM_NOT_FOUND_MSG}), 404

    except Exception as e:
        return handle_api_error(e, "Get program", "Failed to retrieve program")


@api.route("/programs/<program_id>", methods=["PUT"])
@permission_required("manage_programs")
def update_program_api(program_id: str):
    """Update an existing program"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        # Validate program exists and user has permission
        program = get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": PROGRAM_NOT_FOUND_MSG}), 404

        # Update program
        success = update_program(program_id, data)

        if success:
            return jsonify({"success": True, "message": "Program updated successfully"})
        else:
            return jsonify({"success": False, "error": "Failed to update program"}), 500

    except Exception as e:
        return handle_api_error(e, "Update program", "Failed to update program")


@api.route("/programs/<program_id>", methods=["DELETE"])
@permission_required("manage_programs")
def delete_program_api(program_id: str):
    """Delete a program (with course reassignment to default)"""
    try:
        # Validate program exists and user has permission
        program = get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": PROGRAM_NOT_FOUND_MSG}), 404

        # Prevent deletion of default program
        if program.get("is_default", False):
            return (
                jsonify({"success": False, "error": "Cannot delete default program"}),
                400,
            )

        # Get the default program for reassignment
        institution_id = program.get("institution_id")
        programs = get_programs_by_institution(institution_id) if institution_id else []
        default_program = next(
            (p for p in programs if p.get("is_default", False)), None
        )

        if not default_program:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No default program found for course reassignment",
                    }
                ),
                500,
            )

        # Delete program and reassign courses
        success = delete_program(program_id, default_program["id"])

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


# ========================================
# COURSE-PROGRAM ASSOCIATION API
# ========================================


@api.route("/programs/<program_id>/courses", methods=["GET"])
@permission_required("view_program_data", context_keys=["program_id"])
def get_program_courses(program_id: str):
    """Get all courses associated with a program"""
    try:
        # Validate program exists and user has access
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


@api.route("/programs/<program_id>/courses", methods=["POST"])
@permission_required("manage_programs")
def add_course_to_program_api(program_id: str):
    """Add a course to a program"""
    try:
        data = request.get_json()
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

        # Validate program exists
        program = get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": PROGRAM_NOT_FOUND_MSG}), 404

        # Validate course exists
        course = get_course_by_number(
            course_id
        )  # Assuming course_id is course_number for now
        if not course:
            return jsonify({"success": False, "error": COURSE_NOT_FOUND_MSG}), 404

        # Add course to program
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


@api.route("/programs/<program_id>/courses/<course_id>", methods=["DELETE"])
@permission_required("manage_programs")
def remove_course_from_program_api(program_id: str, course_id: str):
    """Remove a course from a program"""
    try:
        # Validate program exists and get institution context
        program, institution_id = _validate_program_for_removal(program_id)

        # Get default program for orphan prevention
        default_program_id = _get_default_program_id(institution_id)

        # Perform course removal with orphan handling
        success = _remove_course_with_orphan_handling(
            course_id, program_id, institution_id, default_program_id
        )

        # Return appropriate response
        return _build_removal_response(success, course_id, program)

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return handle_api_error(
            e, "Remove course from program", "Failed to remove course from program"
        )


def _validate_program_for_removal(program_id: str):
    """Validate program exists and return program with institution ID."""
    program = get_program_by_id(program_id)
    if not program:
        raise ValueError(PROGRAM_NOT_FOUND_MSG)

    institution_id = program.get("institution_id")
    return program, institution_id


def _get_default_program_id(institution_id: str):
    """Get the default program ID for the institution."""
    if not institution_id:
        return None

    programs = get_programs_by_institution(institution_id)
    if not programs:
        return None

    default_program = next((p for p in programs if p.get("is_default", False)), None)

    return default_program["id"] if default_program else None


def _remove_course_with_orphan_handling(
    course_id: str, program_id: str, institution_id: str, default_program_id: str
) -> bool:
    """Remove course from program and handle orphan prevention."""
    # Remove course from program
    success = remove_course_from_program(course_id, program_id)

    # If removal successful and default program exists, assign to default to prevent orphaning
    if success and default_program_id:
        assign_course_to_default_program(course_id, institution_id)

    return success


def _build_removal_response(success: bool, course_id: str, program: dict):
    """Build the appropriate response for course removal."""
    if success:
        return jsonify(
            {
                "success": True,
                "message": f"Course {course_id} removed from program {program.get('name', program.get('id'))}",
            }
        )
    else:
        return (
            jsonify(
                {"success": False, "error": "Failed to remove course from program"}
            ),
            500,
        )


@api.route("/programs/<program_id>/courses/bulk", methods=["POST"])
@permission_required("manage_programs")
def bulk_manage_program_courses(program_id: str):
    """Bulk add or remove courses from a program"""
    try:
        # Validate request data
        validation_response = _validate_bulk_manage_request()
        if validation_response:
            return validation_response

        data = request.get_json()
        action = data.get("action")
        course_ids = data.get("course_ids", [])

        # Validate program exists
        program = get_program_by_id(program_id)
        if not program:
            return jsonify({"success": False, "error": PROGRAM_NOT_FOUND_MSG}), 404

        # Execute bulk operation based on action
        if action == "add":
            result, message = _execute_bulk_add(course_ids, program_id)
        else:  # remove
            result, message = _execute_bulk_remove(course_ids, program_id)

        return jsonify({"success": True, "message": message, "details": result})

    except Exception as e:
        return handle_api_error(
            e, "Bulk manage program courses", "Failed to bulk manage program courses"
        )


def _validate_bulk_manage_request():
    """Validate bulk manage request data."""
    data = request.get_json()
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


def _execute_bulk_add(course_ids: list, program_id: str):
    """Execute bulk add operation."""
    result = bulk_add_courses_to_program(course_ids, program_id)
    message = f"Bulk add operation completed: {result['success_count']} added"
    return result, message


def _execute_bulk_remove(course_ids: list, program_id: str):
    """Execute bulk remove operation with orphan handling."""
    # Get default program for orphan handling
    institution_id = get_current_institution_id()
    default_program_id = _get_default_program_id(institution_id)

    result = bulk_remove_courses_from_program(course_ids, program_id)

    # Assign successfully removed courses to default program to prevent orphaning
    if result.get("removed", 0) > 0 and default_program_id:
        for course_id in course_ids:
            assign_course_to_default_program(course_id, institution_id)

    message = f"Bulk remove operation completed: {result.get('removed', 0)} removed"
    return result, message


@api.route("/courses/<course_id>/programs", methods=["GET"])
@permission_required("view_program_data")
def get_course_programs(course_id: str):
    """Get all programs associated with a course"""
    try:
        # Get course to validate it exists
        course = get_course_by_number(
            course_id
        )  # Assuming course_id is course_number for now
        if not course:
            return jsonify({"success": False, "error": COURSE_NOT_FOUND_MSG}), 404

        program_ids = course.get("program_ids", [])
        programs = []

        # Get program details for each program ID
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


# ========================================
# COURSE SECTION MANAGEMENT API
# ========================================


@api.route("/sections", methods=["GET"])
@permission_required("view_section_data")
def list_sections():
    """
    Get list of course sections

    Query parameters:
    - instructor_id: Filter by instructor (optional)
    - term_id: Filter by term (optional)
    """
    try:
        instructor_id = request.args.get("instructor_id")
        term_id = request.args.get("term_id")

        current_user = get_current_user()

        # If no filters specified, determine default based on role
        if not instructor_id and not term_id:
            if current_user["role"] == UserRole.INSTRUCTOR.value:
                # Instructors see only their own sections
                instructor_id = current_user["user_id"]
            # Program admins and site admins see all sections (no filter)

        # Apply filters
        if instructor_id:
            sections = get_sections_by_instructor(instructor_id)
        elif term_id:
            sections = get_sections_by_term(term_id)
        else:
            # Get institution context - for development, use CEI
            institution_id = get_current_institution_id()
            if not institution_id:
                return (
                    jsonify(
                        {"success": False, "error": INSTITUTION_CONTEXT_REQUIRED_MSG}
                    ),
                    400,
                )
            sections = get_all_sections(institution_id)

        # Filter based on permissions
        if current_user["role"] == UserRole.INSTRUCTOR.value and not has_permission(
            "view_all_sections"
        ):
            # Ensure instructors only see their own sections
            sections = [
                s for s in sections if s.get("instructor_id") == current_user["user_id"]
            ]

        return jsonify({"success": True, "sections": sections, "count": len(sections)})

    except Exception as e:
        return handle_api_error(e, "Get sections", "Failed to retrieve sections")


@api.route("/sections", methods=["POST"])
@permission_required("manage_courses")
def create_section():
    """
    Create a new course section

    Request body should contain:
    - course_id: Course ID
    - term_id: Term ID
    - section_number: Section number (optional, default "001")
    - instructor_id: Instructor ID (optional)
    - enrollment: Number of enrolled students (optional)
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        # Validate required fields
        required_fields = ["course_id", "term_id"]
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


# ========================================
# IMPORT API (New Excel Import System)
# ========================================

# Simple in-memory progress tracking for imports
import threading
import time
import uuid
from typing import Any, Dict

_progress_store: Dict[str, Dict[str, Any]] = {}
_progress_lock = threading.Lock()


def create_progress_tracker() -> str:
    """Create a new progress tracker and return its ID"""
    progress_id = str(uuid.uuid4())
    with _progress_lock:
        _progress_store[progress_id] = {
            "status": "starting",
            "percentage": 0,
            "message": "Initializing import...",
            "records_processed": 0,
            "total_records": 0,
            "created_at": time.time(),
        }
    return progress_id


def update_progress(progress_id: str, **kwargs):
    """Update progress information"""
    with _progress_lock:
        if progress_id in _progress_store:
            _progress_store[progress_id].update(kwargs)


def get_progress(progress_id: str) -> Dict[str, Any]:
    """Get current progress information"""
    with _progress_lock:
        return _progress_store.get(progress_id, {})


def cleanup_progress(progress_id: str):
    """Remove progress tracker after completion"""
    with _progress_lock:
        _progress_store.pop(progress_id, None)


@api.route("/import/progress/<progress_id>", methods=["GET"])
def get_import_progress(progress_id: str):
    """Get the current progress of an import operation"""
    progress = get_progress(progress_id)
    if not progress:
        return jsonify({"error": "Progress ID not found"}), 404

    return jsonify(progress)


@api.route("/import/validate", methods=["POST"])
@permission_required("import_data")
def validate_import_file():
    """
    Validate Excel file format without importing

    Form data:
    - file: Excel file upload
    - adapter_name: Import adapter to use (optional, default "cei_excel_adapter")
    """
    try:
        # Check if file was uploaded
        if "excel_file" not in request.files:
            return jsonify({"success": False, "error": "No Excel file provided"}), 400

        file = request.files["excel_file"]
        if file.filename == "":
            return jsonify({"success": False, "error": "No file selected"}), 400

        # Get parameters
        adapter_name = request.form.get("adapter_name", "cei_excel_adapter")

        # File type validation is handled by the adapter (adapter-driven architecture)
        # Adapters declare their supported formats via get_adapter_info()["supported_formats"]

        # Save uploaded file temporarily
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=_DEFAULT_EXPORT_EXTENSION
        ) as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name

        try:
            # Perform dry run validation
            institution_id = get_current_institution_id()
            if not institution_id:
                raise ValueError("Unable to determine current institution ID")

            result = import_excel(
                file_path=temp_file_path,
                institution_id=institution_id,
                conflict_strategy="use_theirs",
                dry_run=True,  # Always dry run for validation
                adapter_id=adapter_name,
            )

            # Create validation response
            validation_result = {
                "valid": result.success and len(result.errors) == 0,
                "records_found": result.records_processed,
                "potential_conflicts": result.conflicts_detected,
                "errors": result.errors,
                "warnings": result.warnings,
                "file_info": {"filename": file.filename, "adapter": adapter_name},
            }

            return jsonify({"success": True, "validation": validation_result})

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass

    except Exception as e:
        return handle_api_error(e, "Import validation", "Failed to validate file")


# ========================================
# HEALTH CHECK API
# ========================================


@api.route("/health", methods=["GET"])
def health_check():
    """API health check endpoint"""
    return jsonify(
        {
            "success": True,
            "status": "healthy",
            "message": "CEI Course Management API is running",
            "version": "2.0.0",
        }
    )


# ========================================
# ========================================
# ERROR HANDLERS
# ========================================


@api.errorhandler(404)
def api_not_found(error):
    """Handle 404 errors for API routes"""
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@api.errorhandler(500)
def api_internal_error(error):
    """Handle 500 errors for API routes"""
    return jsonify({"success": False, "error": "Internal server error"}), 500


# =============================================================================
# REGISTRATION API ENDPOINTS (Story 2.1)
# =============================================================================


@api.route("/auth/register", methods=["POST"])
def register_institution_admin_api():
    """
    Register a new institution administrator

    Expected JSON payload:
    {
        "email": "admin@example.com",
        "password": "SecurePass123!",
        "first_name": "John",
        "last_name": "Doe",
        "institution_name": "Example University",
        "website_url": "https://example.edu"  // optional
    }

    Returns:
    {
        "success": true,
        "message": "Registration successful! Please check your email to verify your account.",
        "user_id": "user-123",
        "institution_id": "inst-123"
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = [
            "email",
            "password",
            "first_name",
            "last_name",
            "institution_name",
        ]
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Missing required fields: {', '.join(missing_fields)}",
                    }
                ),
                400,
            )

        # Extract data
        email = data["email"].strip().lower()
        password = data["password"]
        first_name = data["first_name"].strip()
        last_name = data["last_name"].strip()
        institution_name = data["institution_name"].strip()
        website_url = data.get("website_url", "").strip() or None

        # Validate email format
        if "@" not in email or "." not in email:
            return jsonify({"success": False, "error": INVALID_EMAIL_FORMAT_MSG}), 400

        # Register the admin
        result = register_institution_admin(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            institution_name=institution_name,
            website_url=website_url,
        )

        # Return success response (exclude sensitive data)
        return (
            jsonify(
                {
                    "success": result["success"],
                    "message": result["message"],
                    "user_id": result["user_id"],
                    "institution_id": result["institution_id"],
                    "email_sent": result["email_sent"],
                }
            ),
            201,
        )

    except RegistrationError as e:
        logger.warning(f"Registration failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        logger.error(f"Unexpected error in registration: {e}")
        return (
            jsonify(
                {"success": False, "error": "Registration failed due to server error"}
            ),
            500,
        )


@api.route("/auth/verify-email/<token>", methods=["GET"])
def verify_email_api(token):
    """
    Verify user's email address using verification token

    URL: /api/auth/verify-email/{verification_token}

    Returns:
    {
        "success": true,
        "message": "Email verified successfully! Your account is now active.",
        "user_id": "user-123",
        "already_verified": false
    }
    """
    try:
        # Validate token
        if not token or len(token) < 10:
            return (
                jsonify({"success": False, "error": "Invalid verification token"}),
                400,
            )

        # Verify email
        result = verify_email(token)

        # Return success response
        return (
            jsonify(
                {
                    "success": result["success"],
                    "message": result["message"],
                    "user_id": result["user_id"],
                    "already_verified": result.get("already_verified", False),
                    "email": result.get("email"),
                    "display_name": result.get("display_name"),
                    "institution_name": result.get("institution_name"),
                }
            ),
            200,
        )

    except RegistrationError as e:
        logger.warning(f"Email verification failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        logger.error(f"Unexpected error in email verification: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Email verification failed due to server error",
                }
            ),
            500,
        )


@api.route("/auth/resend-verification", methods=["POST"])
def resend_verification_email_api():
    """
    Resend verification email for pending user

    Expected JSON payload:
    {
        "email": "admin@example.com"
    }

    Returns:
    {
        "success": true,
        "message": "Verification email sent! Please check your email.",
        "email_sent": true
    }
    """
    try:
        data = request.get_json()

        # Validate email
        email = data.get("email", "").strip().lower()
        if not email:
            return (
                jsonify({"success": False, "error": "Email address is required"}),
                400,
            )

        if "@" not in email or "." not in email:
            return jsonify({"success": False, "error": INVALID_EMAIL_FORMAT_MSG}), 400

        # Resend verification email
        result = resend_verification_email(email)

        # Return success response
        return (
            jsonify(
                {
                    "success": result["success"],
                    "message": result["message"],
                    "email_sent": result["email_sent"],
                }
            ),
            200,
        )

    except RegistrationError as e:
        logger.warning(f"Resend verification failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        logger.error(f"Unexpected error in resend verification: {e}")
        return (
            jsonify({"success": False, "error": "Failed to resend verification email"}),
            500,
        )


@api.route("/auth/registration-status/<email>", methods=["GET"])
def get_registration_status_api(email):
    """
    Get registration status for an email address

    URL: /api/auth/registration-status/{email}

    Returns:
    {
        "exists": true,
        "status": "active",  // or "pending_verification", "not_registered"
        "user_id": "user-123",
        "message": "Account is active and verified"
    }
    """
    try:
        # Validate email
        email = email.strip().lower()
        if not email or "@" not in email or "." not in email:
            return (
                jsonify(
                    {
                        "exists": False,
                        "status": "invalid_email",
                        "message": INVALID_EMAIL_FORMAT_MSG,
                    }
                ),
                400,
            )

        # Get registration status
        result = get_registration_status(email)

        # Return status
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Unexpected error in registration status check: {e}")
        return (
            jsonify(
                {
                    "exists": False,
                    "status": "error",
                    "message": "Failed to check registration status",
                }
            ),
            500,
        )


# ===== INVITATION API ENDPOINTS =====


@api.route("/auth/invite", methods=["POST"])
@permission_required("manage_institution_users")
def create_invitation_api():
    """
    Create and send a user invitation

    JSON Body:
    {
        "invitee_email": "instructor@example.com",
        "invitee_role": UserRole.INSTRUCTOR.value,
        "program_ids": ["prog-123"],  // Optional, for program_admin role
        "personal_message": "Welcome to our team!"  // Optional
    }

    Returns:
        201: Invitation created and sent successfully
        400: Invalid request data
        403: Insufficient permissions
        409: User already exists or invitation pending
        500: Server error
    """
    try:
        from auth_service import get_current_institution_id, get_current_user
        from invitation_service import InvitationService

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        # Validate required fields
        required_fields = ["invitee_email", "invitee_role"]
        for field in required_fields:
            if field not in data:
                return (
                    jsonify(
                        {"success": False, "error": f"Missing required field: {field}"}
                    ),
                    400,
                )

        # Get current user and institution
        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": "User not authenticated"}), 401

        institution_id = get_current_institution_id()
        if not institution_id:
            return (
                jsonify({"success": False, "error": INSTITUTION_CONTEXT_REQUIRED_MSG}),
                400,
            )

        # Create invitation
        invitation = InvitationService.create_invitation(
            inviter_user_id=current_user["user_id"],
            inviter_email=current_user["email"],
            invitee_email=data["invitee_email"],
            invitee_role=data["invitee_role"],
            institution_id=institution_id,
            program_ids=data.get("program_ids", []),
            personal_message=data.get("personal_message"),
        )

        # Send invitation email
        email_sent = InvitationService.send_invitation(invitation)

        return (
            jsonify(
                {
                    "success": True,
                    "invitation_id": invitation["id"],
                    "message": (
                        "Invitation created and sent successfully"
                        if email_sent
                        else "Invitation created but email failed to send"
                    ),
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error creating invitation: {e}")
        if "already exists" in str(e) or "already exists" in str(e):
            return jsonify({"success": False, "error": str(e)}), 409
        elif "Invalid role" in str(e):
            return jsonify({"success": False, "error": str(e)}), 400
        else:
            return (
                jsonify({"success": False, "error": "Failed to create invitation"}),
                500,
            )


@api.route("/auth/accept-invitation", methods=["POST"])
def accept_invitation_api():
    """
    Accept an invitation and create user account

    JSON Body:
    {
        "invitation_token": "secure-token-here",
        "password": "newpassword123",
        "display_name": "John Doe"  // Optional
    }

    Returns:
        200: Invitation accepted and account created
        400: Invalid request data or token
        410: Invitation expired or already accepted
        500: Server error
    """
    try:
        from invitation_service import InvitationService

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        # Validate required fields
        required_fields = ["invitation_token", "password"]
        for field in required_fields:
            if field not in data:
                return (
                    jsonify(
                        {"success": False, "error": f"Missing required field: {field}"}
                    ),
                    400,
                )

        # Accept invitation
        user = InvitationService.accept_invitation(
            invitation_token=data["invitation_token"],
            password=data["password"],
            display_name=data.get("display_name"),
        )

        return (
            jsonify(
                {
                    "success": True,
                    "user_id": user["id"],
                    "email": user["email"],
                    "role": user["role"],
                    "message": "Invitation accepted and account created successfully",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error accepting invitation: {e}")
        if "expired" in str(e).lower() or "already been accepted" in str(e):
            return jsonify({"success": False, "error": str(e)}), 410
        elif "Invalid" in str(e) or "not available" in str(e):
            return jsonify({"success": False, "error": str(e)}), 400
        else:
            return (
                jsonify({"success": False, "error": "Failed to accept invitation"}),
                500,
            )


@api.route("/auth/invitation-status/<invitation_token>", methods=["GET"])
def get_invitation_status_api(invitation_token):
    """
    Get invitation status by token

    URL: /api/auth/invitation-status/{invitation_token}

    Returns:
        200: Invitation status retrieved
        404: Invitation not found
        500: Server error
    """
    try:
        from invitation_service import InvitationService

        # Get invitation status
        status = InvitationService.get_invitation_status(invitation_token)

        return jsonify({"success": True, **status}), 200

    except Exception as e:
        logger.error(f"Error getting invitation status: {e}")
        if NOT_FOUND_MSG in str(e).lower():
            return jsonify({"success": False, "error": INVITATION_NOT_FOUND_MSG}), 404
        else:
            return (
                jsonify({"success": False, "error": "Failed to get invitation status"}),
                500,
            )


@api.route("/auth/resend-invitation/<invitation_id>", methods=["POST"])
@permission_required("manage_institution_users")
def resend_invitation_api(invitation_id):
    """
    Resend an existing invitation

    URL: /api/auth/resend-invitation/{invitation_id}

    Returns:
        200: Invitation resent successfully
        400: Cannot resend invitation (wrong status)
        404: Invitation not found
        500: Server error
    """
    try:
        from invitation_service import InvitationService

        # Resend invitation
        success = InvitationService.resend_invitation(invitation_id)

        if success:
            return (
                jsonify({"success": True, "message": "Invitation resent successfully"}),
                200,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to resend invitation"}),
                500,
            )

    except Exception as e:
        logger.error(f"Error resending invitation: {e}")
        if NOT_FOUND_MSG in str(e).lower():
            return jsonify({"success": False, "error": INVITATION_NOT_FOUND_MSG}), 404
        elif "Cannot resend" in str(e):
            return jsonify({"success": False, "error": str(e)}), 400
        else:
            return (
                jsonify({"success": False, "error": "Failed to resend invitation"}),
                500,
            )


@api.route("/auth/invitations", methods=["GET"])
@permission_required("manage_institution_users")
def list_invitations_api():
    """
    List invitations for current user's institution

    Query Parameters:
    - status: Filter by status (pending, sent, accepted, expired, cancelled)
    - limit: Number of results (default 50, max 100)
    - offset: Offset for pagination (default 0)

    Returns:
        200: List of invitations
        400: Invalid parameters
        500: Server error
    """
    try:
        from auth_service import get_current_institution_id
        from invitation_service import InvitationService

        # Get institution context
        institution_id = get_current_institution_id()
        if not institution_id:
            return (
                jsonify({"success": False, "error": INSTITUTION_CONTEXT_REQUIRED_MSG}),
                400,
            )

        # Get query parameters
        status = request.args.get("status")
        limit = min(int(request.args.get("limit", 50)), 100)
        offset = int(request.args.get("offset", 0))

        # List invitations
        invitations = InvitationService.list_invitations(
            institution_id=institution_id, status=status, limit=limit, offset=offset
        )

        return (
            jsonify(
                {
                    "success": True,
                    "invitations": invitations,
                    "count": len(invitations),
                    "limit": limit,
                    "offset": offset,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error listing invitations: {e}")
        return jsonify({"success": False, "error": "Failed to list invitations"}), 500


@api.route("/auth/cancel-invitation/<invitation_id>", methods=["DELETE"])
@permission_required("manage_institution_users")
def cancel_invitation_api(invitation_id):
    """
    Cancel a pending invitation

    URL: /api/auth/cancel-invitation/{invitation_id}

    Returns:
        200: Invitation cancelled successfully
        400: Cannot cancel invitation (wrong status)
        404: Invitation not found
        500: Server error
    """
    try:
        from invitation_service import InvitationService

        # Cancel invitation
        success = InvitationService.cancel_invitation(invitation_id)

        if success:
            return (
                jsonify(
                    {"success": True, "message": "Invitation cancelled successfully"}
                ),
                200,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to cancel invitation"}),
                500,
            )

    except Exception as e:
        logger.error(f"Error cancelling invitation: {e}")
        if NOT_FOUND_MSG in str(e).lower():
            return jsonify({"success": False, "error": INVITATION_NOT_FOUND_MSG}), 404
        elif "Cannot cancel" in str(e):
            return jsonify({"success": False, "error": str(e)}), 400
        else:
            return (
                jsonify({"success": False, "error": "Failed to cancel invitation"}),
                500,
            )


# ===== LOGIN/LOGOUT API ENDPOINTS =====


@api.route("/auth/login", methods=["POST"])
def login_api():
    """
    Authenticate user and create session

    JSON Body:
    {
        "email": "user@example.com",
        "password": "password123",
        "remember_me": false  // Optional, default false
    }

    Returns:
        200: Login successful
        400: Invalid request data
        401: Invalid credentials
        423: Account locked
        500: Server error
    """
    try:
        from login_service import LoginError, LoginService
        from password_service import AccountLockedError

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        # Validate required fields
        required_fields = ["email", "password"]
        for field in required_fields:
            if field not in data:
                return (
                    jsonify(
                        {"success": False, "error": f"Missing required field: {field}"}
                    ),
                    400,
                )

        # Authenticate user
        result = LoginService.authenticate_user(
            email=data["email"],
            password=data["password"],
            remember_me=data.get("remember_me", False),
        )

        return (
            jsonify({"success": True, **result}),
            200,
        )

    except AccountLockedError as e:
        logger.warning(
            f"Account locked during login attempt: {data.get('email', 'unknown')}"
        )
        return jsonify({"success": False, "error": "Account is locked"}), 423
    except LoginError as e:
        logger.error(f"User login failed: {e}")
        return jsonify({"success": False, "error": "Invalid email or password"}), 401
    except Exception as e:
        logger.error(f"Login error: {e}")
        return handle_api_error(e, "User login", "An unexpected error occurred")


@api.route("/auth/logout", methods=["POST"])
def logout_api():
    """
    Logout current user and destroy session

    Returns:
        200: Logout successful
        500: Server error
    """
    try:
        from login_service import LoginService

        # Logout user
        result = LoginService.logout_user()

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"success": False, "error": "Logout failed"}), 500


@api.route("/auth/status", methods=["GET"])
def login_status_api():
    """
    Get current login status

    Returns:
        200: Status retrieved successfully
        500: Server error
    """
    try:
        from login_service import LoginService

        # Get login status
        status = LoginService.get_login_status()

        return jsonify({"success": True, **status}), 200

    except Exception as e:
        logger.error(f"Error getting login status: {e}")
        return jsonify({"success": False, "error": "Failed to get login status"}), 500


@api.route("/auth/refresh", methods=["POST"])
def refresh_session_api():
    """
    Refresh current user session

    Returns:
        200: Session refreshed successfully
        401: No active session
        500: Server error
    """
    try:
        from login_service import LoginService

        # Refresh session
        result = LoginService.refresh_session()

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Session refresh error: {e}")
        if "No active session" in str(e):
            return jsonify({"success": False, "error": str(e)}), 401
        else:
            return (
                jsonify({"success": False, "error": "Failed to refresh session"}),
                500,
            )


@api.route("/auth/lockout-status/<email>", methods=["GET"])
def check_lockout_status_api(email):
    """
    Check account lockout status for an email

    URL: /api/auth/lockout-status/{email}

    Returns:
        200: Lockout status retrieved
        500: Server error
    """
    try:
        from login_service import LoginService

        # Check lockout status
        status = LoginService.check_account_lockout_status(email)

        return jsonify({"success": True, **status}), 200

    except Exception as e:
        logger.error(f"Error checking lockout status: {e}")
        return (
            jsonify({"success": False, "error": "Failed to check lockout status"}),
            500,
        )


@api.route("/auth/unlock-account", methods=["POST"])
@login_required
def unlock_account_api():
    """
    Manually unlock a locked account (admin function)

    JSON Body:
    {
        "email": "user@example.com"
    }

    Returns:
        200: Account unlocked successfully
        400: Invalid request data
        403: Insufficient permissions
        500: Server error
    """
    try:
        from auth_service import get_current_user
        from login_service import LoginService

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        if "email" not in data:
            return (
                jsonify({"success": False, "error": "Missing required field: email"}),
                400,
            )

        # Get current user (admin check would go here)
        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        # For now, allow any logged-in user to unlock accounts
        # In production, this should check for admin role

        # Unlock account
        result = LoginService.unlock_account(data["email"], current_user["id"])

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Account unlock error: {e}")
        return jsonify({"success": False, "error": "Failed to unlock account"}), 500


# ===== PASSWORD RESET API ENDPOINTS =====


@api.route("/auth/forgot-password", methods=["POST"])
def forgot_password_api():
    """
    Request password reset email

    JSON Body:
    {
        "email": "user@example.com"
    }

    Returns:
        200: Reset email sent (or would be sent)
        400: Invalid request data
        429: Too many requests
        500: Server error
    """
    try:
        from password_reset_service import PasswordResetService

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        if "email" not in data:
            return (
                jsonify({"success": False, "error": "Missing required field: email"}),
                400,
            )

        # Request password reset
        result = PasswordResetService.request_password_reset(data["email"])

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        if "Too many" in str(e):
            return jsonify({"success": False, "error": str(e)}), 429
        elif "restricted in development" in str(e):
            return jsonify({"success": False, "error": str(e)}), 400
        else:
            return (
                jsonify({"success": False, "error": "Password reset request failed"}),
                500,
            )


@api.route("/auth/reset-password", methods=["POST"])
def reset_password_api():
    """
    Complete password reset with new password

    JSON Body:
    {
        "reset_token": "secure-reset-token",
        "new_password": "newSecurePassword123!"
    }

    Returns:
        200: Password reset successful
        400: Invalid request data or token
        500: Server error
    """
    try:
        from password_reset_service import PasswordResetService

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        # Validate required fields
        required_fields = ["reset_token", "new_password"]
        for field in required_fields:
            if field not in data:
                return (
                    jsonify(
                        {"success": False, "error": f"Missing required field: {field}"}
                    ),
                    400,
                )

        # Reset password
        result = PasswordResetService.reset_password(
            reset_token=data["reset_token"], new_password=data["new_password"]
        )

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Password reset error: {e}")
        if any(
            phrase in str(e) for phrase in ["Invalid", "expired", "validation failed"]
        ):
            return jsonify({"success": False, "error": str(e)}), 400
        else:
            return jsonify({"success": False, "error": "Password reset failed"}), 500


@api.route("/auth/validate-reset-token/<reset_token>", methods=["GET"])
def validate_reset_token_api(reset_token):
    """
    Validate a password reset token

    URL: /api/auth/validate-reset-token/{token}

    Returns:
        200: Token validation result
        500: Server error
    """
    try:
        from password_reset_service import PasswordResetService

        # Validate reset token
        result = PasswordResetService.validate_reset_token(reset_token)

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return (
            jsonify({"success": False, "error": "Failed to validate reset token"}),
            500,
        )


@api.route("/auth/reset-status/<email>", methods=["GET"])
def reset_status_api(email):
    """
    Get password reset status for an email

    URL: /api/auth/reset-status/{email}

    Returns:
        200: Reset status retrieved
        500: Server error
    """
    try:
        from password_reset_service import PasswordResetService

        # Get reset status
        result = PasswordResetService.get_reset_status(email)

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Reset status error: {e}")
        return jsonify({"success": False, "error": "Failed to get reset status"}), 500


# ========================================
# DATA IMPORT/EXPORT API
# ========================================


@api.route("/import/excel", methods=["POST"])
@login_required
def excel_import_api():
    """
    Import data from Excel file

    Supports role-based data import with conflict resolution strategies.

    Form Data:
        excel_file: Excel file (.xlsx, .xls)
        import_adapter: Adapter ID (e.g., cei_excel_format_v1)
        conflict_strategy: How to handle conflicts (use_theirs, use_mine, merge, manual_review)
        dry_run: Test mode without saving (true/false)
        verbose_output: Detailed output (true/false)
        delete_existing_db: Clear database before import (true/false)
        import_data_type: Type of data being imported

    Returns:
        200: Import successful
        400: Invalid request or file
        403: Permission denied
        500: Server error
    """
    try:
        # Validate request and extract parameters
        file, import_params = _validate_excel_import_request()

        # Check user permissions
        current_user, institution_id = _check_excel_import_permissions(
            import_params["adapter_id"], import_params["import_data_type"]
        )

        # Process the import
        return _process_excel_import(file, current_user, institution_id, import_params)

    except ValueError as e:
        logger.warning(f"Invalid request for import: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

    except PermissionError as e:
        logger.warning(f"Permission denied for import: {e}")
        return jsonify({"success": False, "error": str(e)}), 403

    except Exception as e:
        logger.error(f"Excel import error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Import failed",
                }
            ),
            500,
        )


def _validate_excel_import_request():
    """Validate the Excel import request and extract parameters."""
    # Debug: Log request information
    logger.info("Excel import request received")
    logger.info("Request files: %s", list(request.files.keys()))
    logger.info("Request form: %s", dict(request.form))

    # Check if file was uploaded
    if "excel_file" not in request.files:
        logger.warning("No excel_file in request.files")
        raise ValueError("No Excel file provided")

    file = request.files["excel_file"]
    if not file.filename or file.filename == "":
        logger.warning("Empty filename in uploaded file")
        raise ValueError("No file selected")

    logger.info(
        f"File received: {file.filename}, size: {file.content_length if hasattr(file, 'content_length') else 'unknown'}"
    )

    # Get form parameters (need adapter_id for validation)
    import_params = {
        "adapter_id": request.form.get("import_adapter", "cei_excel_format_v1"),
        "conflict_strategy": request.form.get("conflict_strategy", "use_theirs"),
        "dry_run": request.form.get("dry_run", "false").lower() == "true",
        "verbose_output": request.form.get("verbose_output", "false").lower() == "true",
        "import_data_type": request.form.get("import_data_type", "courses"),
    }

    # Validate file extension against adapter's supported formats
    from adapters.adapter_registry import AdapterRegistry

    registry = AdapterRegistry()
    adapter = registry.get_adapter_by_id(import_params["adapter_id"])

    if not adapter:
        raise ValueError(f"Adapter not found: {import_params['adapter_id']}")

    # Get supported extensions
    adapter_info = adapter.get_adapter_info()
    if not adapter_info:
        raise ValueError(
            f"Adapter info not available for: {import_params['adapter_id']}"
        )

    supported_formats = adapter_info.get("supported_formats", [])
    if not supported_formats:
        raise ValueError(
            f"No supported formats defined for adapter: {import_params['adapter_id']}"
        )

    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if not file_ext:
        raise ValueError("File has no extension")

    if file_ext not in supported_formats:
        raise ValueError(
            f"Invalid file format {file_ext} for adapter {import_params['adapter_id']}. "
            f"Supported formats: {', '.join(supported_formats)}"
        )

    logger.info(
        f"File extension {file_ext} validated for adapter {import_params['adapter_id']}"
    )

    return file, import_params


def _check_excel_import_permissions(adapter_id, import_data_type):
    """Check user permissions for Excel import."""
    # Get current user and check authentication
    current_user = get_current_user()
    if not current_user:
        raise PermissionError("Authentication required")

    user_role = current_user.get("role")
    user_institution_id = current_user.get("institution_id")

    # Determine institution_id based on user role and adapter
    institution_id = _determine_target_institution(
        user_role, user_institution_id, adapter_id
    )

    # Check role-based permissions
    _validate_import_permissions(user_role, import_data_type)

    return current_user, institution_id


def _determine_target_institution(user_role, user_institution_id, adapter_id):
    """Determine the target institution for the import."""
    if user_role == UserRole.SITE_ADMIN.value:
        # Site admins can import for any institution - let adapter determine it
        if adapter_id == "cei_excel_format_v1":
            # CEI adapter always imports for CEI institution
            from database_service import create_default_cei_institution

            institution_id = create_default_cei_institution()
            if not institution_id:
                raise ValueError("Failed to create/find CEI institution")
            return institution_id
        else:
            # For other adapters, site admin needs to specify institution
            # TODO: Add institution selection UI for site admins
            raise ValueError(
                "Site admin must specify target institution for non-CEI adapters"
            )
    else:
        # Institution/program admins use their own institution
        if not user_institution_id:
            raise PermissionError("User has no associated institution")
        return user_institution_id


def _validate_import_permissions(user_role, import_data_type):
    """Validate that the user role can import the specified data type."""
    allowed_data_types = {
        UserRole.SITE_ADMIN.value: ["institutions", "programs", "courses", "users"],
        UserRole.INSTITUTION_ADMIN.value: [
            "programs",
            "courses",
            "faculty",
            "students",
        ],
        UserRole.PROGRAM_ADMIN.value: [],  # Program admins cannot import per requirements
        UserRole.INSTRUCTOR.value: [],  # Instructors cannot import
    }

    if user_role not in allowed_data_types:
        raise PermissionError("Invalid user role")

    if import_data_type not in allowed_data_types[user_role]:
        raise PermissionError(
            f"Permission denied: {user_role} cannot import {import_data_type}"
        )


def _process_excel_import(file, current_user, institution_id, import_params):
    """Process the Excel import with the validated parameters."""
    import os
    import re
    import tempfile

    # Sanitize filename for logging/display purposes only
    safe_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", file.filename)
    if not safe_filename or safe_filename.startswith("."):
        safe_filename = f"upload_{hash(file.filename) % 10000}"

    # Use secure temporary file creation
    temp_file_prefix = (
        f"import_{current_user.get('user_id')}_{import_params['import_data_type']}_"
    )

    try:
        # Create secure temporary file
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=temp_file_prefix,
            suffix=f"_{safe_filename}",
            delete=False,
        ) as temp_file:
            file.save(temp_file)
            temp_filepath = temp_file.name

        # Import the Excel processing function
        from import_service import import_excel

        # Execute the import
        result = import_excel(
            file_path=temp_filepath,
            institution_id=institution_id,
            conflict_strategy=import_params["conflict_strategy"],
            dry_run=import_params["dry_run"],
            adapter_id=import_params["adapter_id"],
            verbose=import_params["verbose_output"],
        )

        return (
            jsonify(
                {
                    "success": True,
                    "message": (
                        "Import completed successfully"
                        if not import_params["dry_run"]
                        else "Validation completed successfully"
                    ),
                    "records_processed": result.records_processed,
                    "records_created": result.records_created,
                    "records_updated": result.records_updated,
                    "records_skipped": result.records_skipped,
                    "conflicts_detected": result.conflicts_detected,
                    "execution_time": result.execution_time,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "dry_run": import_params["dry_run"],
                }
            ),
            200,
        )

    finally:
        # Clean up temporary file
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)


# ============================================================================
# ADAPTER MANAGEMENT ENDPOINTS
# ============================================================================


@api.route("/adapters", methods=["GET"])
@login_required
def get_available_adapters():
    """
    Get available adapters for the current user based on their role and institution scope.

    Returns:
        JSON response with list of available adapters
    """
    try:
        from adapters.adapter_registry import get_adapter_registry

        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": "User not authenticated"}), 401

        registry = get_adapter_registry()
        user_role = current_user.get("role")
        user_institution_id = current_user.get("institution_id")
        adapters = registry.get_adapters_for_user(user_role, user_institution_id)

        # Format adapters for frontend consumption
        adapter_list = []
        for adapter_info in adapters:
            adapter_list.append(
                {
                    "id": adapter_info["id"],
                    "name": adapter_info["name"],
                    "description": adapter_info["description"],
                    "institution_id": adapter_info.get(
                        "institution_id"
                    ),  # Use .get() for safety
                    "supported_formats": adapter_info["supported_formats"],
                    "data_types": adapter_info["data_types"],
                }
            )

        return jsonify({"success": True, "adapters": adapter_list})

    except Exception as e:
        logger.error(f"Error getting available adapters: {str(e)}")
        return (
            jsonify(
                {"success": False, "error": "Failed to retrieve available adapters"}
            ),
            500,
        )


# ==============================================
# Export Endpoints
# ==============================================


@api.route("/export/data", methods=["GET"])
@login_required
def export_data():
    """
    Export data using institution-specific adapter.

    Query parameters:
        - export_data_type: Type of data to export (courses, users, sections, etc.)
        - export_adapter: Adapter to use - adapter determines file format
        - include_metadata: Include metadata (true/false) - defaults to true
        - anonymize_data: Anonymize personal info (true/false) - defaults to false

    Site Admin Behavior:
        - Exports ALL institutions as a zip containing subdirectories per institution
        - Structure: system_export_TIMESTAMP.zip
                       ├── system_manifest.json
                       ├── cei/
                       │   └── [institution export files]
                       ├── rcc/
                       │   └── [institution export files]
                       └── ptu/
                           └── [institution export files]
    """
    try:
        current_user = get_current_user()
        if not current_user:
            logger.error("[EXPORT] User not authenticated")
            return jsonify({"success": False, "error": "Not authenticated"}), 401

        user_role = current_user.get("role")
        institution_id = current_user.get("institution_id")

        # Site Admin: Export all institutions
        if user_role == UserRole.SITE_ADMIN.value:
            logger.info("[EXPORT] Site Admin export - exporting all institutions")
            return _export_all_institutions(current_user)

        # Other roles: Export single institution
        if not institution_id:
            logger.error(
                f"[EXPORT] No institution_id for user: {current_user.get('email')}"
            )
            return jsonify({"success": False, "error": "No institution context"}), 400

        # Get parameters
        data_type_raw = request.args.get("export_data_type", "courses")
        adapter_id_raw = request.args.get("export_adapter", "cei_excel_format_v1")

        # Sanitize data_type to prevent path traversal (security fix for S2083)
        # Only allow alphanumeric characters and underscores
        data_type = re.sub(r"\W", "", data_type_raw)
        if not data_type:
            data_type = "courses"  # Fallback to safe default

        # Sanitize adapter_id to prevent log injection (security fix for S5145)
        # Only allow alphanumeric characters, underscores, and hyphens
        adapter_id = re.sub(r"[^a-zA-Z0-9_-]", "", adapter_id_raw)
        if not adapter_id:
            adapter_id = "cei_excel_format_v1"  # Fallback to safe default

        logger.info(
            f"[EXPORT] Request: institution_id={institution_id}, data_type={data_type}, adapter={adapter_id}"
        )
        include_metadata = (
            request.args.get("include_metadata", "true").lower() == "true"
        )

        # Create export service and get adapter info
        export_service = create_export_service()

        # Query adapter for its supported format
        try:
            adapter = export_service.registry.get_adapter_by_id(adapter_id)
            if not adapter:
                logger.error(f"[EXPORT] Adapter not found: {adapter_id}")
                return (
                    jsonify(
                        {"success": False, "error": f"Adapter not found: {adapter_id}"}
                    ),
                    400,
                )

            adapter_info = adapter.get_adapter_info()
            supported_formats = adapter_info.get(
                "supported_formats", [_DEFAULT_EXPORT_EXTENSION]
            )
            # Use first supported format from adapter
            file_extension = (
                supported_formats[0] if supported_formats else _DEFAULT_EXPORT_EXTENSION
            )
        except Exception as adapter_error:
            logger.error(f"[EXPORT] Error getting adapter info: {str(adapter_error)}")
            # Fallback to xlsx if adapter query fails
            file_extension = _DEFAULT_EXPORT_EXTENSION

        # Determine output format from file extension (remove leading dot)
        output_format = (
            file_extension.lstrip(".")
            if file_extension.startswith(".")
            else file_extension
        )

        # Create export config
        config = ExportConfig(
            institution_id=institution_id,
            adapter_id=adapter_id,
            export_view="standard",
            include_metadata=include_metadata,
            output_format=output_format,
        )

        # Create temp file for export in secure temp directory
        temp_dir = Path(tempfile.gettempdir())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # filename now uses sanitized data_type and adapter-determined extension
        filename = f"{data_type}_export_{timestamp}{file_extension}"
        output_path = temp_dir / filename

        # Verify output path is within temp directory (defense in depth)
        # Resolve parent directory first since output file doesn't exist yet
        resolved_output_parent = output_path.parent.resolve()
        resolved_temp_dir = temp_dir.resolve()
        if not str(resolved_output_parent).startswith(str(resolved_temp_dir)):
            logger.error(f"[EXPORT] Path traversal attempt detected: {output_path}")
            return jsonify({"success": False, "error": "Invalid export path"}), 400

        # Perform export
        result = export_service.export_data(config, str(output_path))

        if not result.success:
            logger.error(f"[EXPORT] Export failed: {result.errors}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Export failed",
                        "details": result.errors,
                    }
                ),
                500,
            )

        logger.info(
            f"[EXPORT] Export successful: {result.records_exported} records, file: {result.file_path}"
        )

        # Get appropriate mimetype from adapter's file extension
        mimetype = _get_mimetype_for_extension(file_extension)

        # Send file as download
        return send_file(
            str(output_path),
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype,
        )

    except Exception as e:
        logger.error(f"Error during export: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": f"Export failed: {str(e)}"}), 500


def _export_all_institutions(current_user: Dict[str, Any]):
    """
    Export all institutions for Site Admin as a zip of folders.

    Creates structure:
        system_export_TIMESTAMP.zip
          ├── system_manifest.json
          ├── <institution_short_name>/
          │     └── [export files per adapter]
          └── ...

    Args:
        current_user: Site Admin user dict

    Returns:
        Flask send_file response with system-wide export ZIP
    """
    import json
    import shutil
    import zipfile

    # Initialize temp directory variable for cleanup in except block
    system_export_dir = None

    try:
        # Get parameters
        data_type_raw = request.args.get("export_data_type", "courses")
        adapter_id_raw = request.args.get("export_adapter", "generic_csv_v1")

        # Sanitize parameters (allow alphanumeric, underscore, hyphen, and dot)
        data_type = re.sub(r"[^\w.-]", "", data_type_raw)
        if not data_type:
            data_type = "courses"

        # Keep underscores and hyphens for valid adapter IDs like "generic_csv_v1"
        adapter_id = re.sub(r"[^\w.-]", "", adapter_id_raw)
        if not adapter_id:
            adapter_id = "generic_csv_v1"

        include_metadata = (
            request.args.get("include_metadata", "true").lower() == "true"
        )

        logger.info(
            f"[EXPORT] Site Admin system-wide export: adapter={adapter_id}, data_type={data_type}"
        )

        # Get all institutions
        institutions = get_all_institutions()
        if not institutions:
            return jsonify({"success": False, "error": "No institutions found"}), 404

        # Create temp directory for building system export (remove if exists to avoid stale files)
        temp_base = Path(tempfile.gettempdir())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        system_export_dir = temp_base / f"system_export_{timestamp}"

        if system_export_dir.exists():
            shutil.rmtree(system_export_dir)
        system_export_dir.mkdir(parents=True)

        export_service = create_export_service()

        # Get adapter info for file extension
        try:
            adapter = export_service.registry.get_adapter_by_id(adapter_id)
            if not adapter:
                return (
                    jsonify(
                        {"success": False, "error": f"Adapter not found: {adapter_id}"}
                    ),
                    400,
                )

            adapter_info = adapter.get_adapter_info()
            supported_formats = adapter_info.get(
                "supported_formats", [_DEFAULT_EXPORT_EXTENSION]
            )
            file_extension = (
                supported_formats[0] if supported_formats else _DEFAULT_EXPORT_EXTENSION
            )
        except Exception as adapter_error:
            logger.error(f"[EXPORT] Error getting adapter info: {str(adapter_error)}")
            file_extension = _DEFAULT_EXPORT_EXTENSION

        output_format = (
            file_extension.lstrip(".")
            if file_extension.startswith(".")
            else file_extension
        )

        # Export each institution to its own subdirectory
        institution_results = []

        for inst in institutions:
            inst_id = inst.get("institution_id")
            inst_short_name = inst.get("short_name", inst_id)

            # Create subdirectory for this institution
            inst_dir = system_export_dir / inst_short_name
            inst_dir.mkdir(exist_ok=True)

            logger.info(
                f"[EXPORT] Exporting institution: {inst_short_name} ({inst_id})"
            )

            # Create export config for this institution
            config = ExportConfig(
                institution_id=inst_id,
                adapter_id=adapter_id,
                export_view="standard",
                include_metadata=include_metadata,
                output_format=output_format,
            )

            # Export to institution directory
            inst_filename = f"{data_type}_export_{timestamp}{file_extension}"
            inst_output_path = inst_dir / inst_filename

            result = export_service.export_data(config, str(inst_output_path))

            institution_results.append(
                {
                    "institution_id": inst_id,
                    "institution_name": inst.get("name"),
                    "short_name": inst_short_name,
                    "success": result.success,
                    "records_exported": result.records_exported,
                    "file": inst_filename,
                    "errors": result.errors if not result.success else [],
                }
            )

            if not result.success:
                logger.warning(
                    f"[EXPORT] Failed to export {inst_short_name}: {result.errors}"
                )

        # Create system-level manifest
        system_manifest = {
            "format_version": "1.0",
            "export_type": "system_wide",
            "export_timestamp": timestamp,
            "exported_by": current_user.get("email"),
            "adapter_id": adapter_id,
            "data_type": data_type,
            "total_institutions": len(institutions),
            "successful_exports": sum(1 for r in institution_results if r["success"]),
            "failed_exports": sum(1 for r in institution_results if not r["success"]),
            "institutions": institution_results,
        }

        manifest_path = system_export_dir / "system_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(system_manifest, f, indent=2)

        # Create final ZIP file
        system_zip_path = temp_base / f"system_export_{timestamp}.zip"

        # Exclude system files and directories
        excluded_patterns = {".DS_Store", "__MACOSX", ".git", "Thumbs.db"}

        with zipfile.ZipFile(system_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in system_export_dir.rglob("*"):
                # Skip excluded files and directories
                if any(pattern in file_path.parts for pattern in excluded_patterns):
                    continue
                if file_path.is_file():
                    arcname = file_path.relative_to(system_export_dir)
                    zipf.write(file_path, arcname)

        # Clean up temp directory
        shutil.rmtree(system_export_dir)

        logger.info(
            f"[EXPORT] System export complete: {system_manifest['successful_exports']}/{system_manifest['total_institutions']} institutions"
        )

        # Send file
        return send_file(
            str(system_zip_path),
            as_attachment=True,
            download_name=f"system_export_{timestamp}.zip",
            mimetype="application/zip",
        )

    except Exception as e:
        logger.error(f"[EXPORT] System export failed: {str(e)}", exc_info=True)
        # Clean up temp directory on error (system_export_dir initialized to None above)
        if system_export_dir is not None and system_export_dir.exists():
            try:
                shutil.rmtree(system_export_dir)
            except Exception as cleanup_error:
                logger.error(
                    f"[EXPORT] Failed to cleanup temp directory: {str(cleanup_error)}"
                )
        return (
            jsonify({"success": False, "error": f"System export failed: {str(e)}"}),
            500,
        )
