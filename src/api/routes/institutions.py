"""
Institutions API routes.

Provides endpoints for managing institutions and user program context.
Includes institution CRUD operations and context management.
"""

from typing import Any, Dict

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

from src.api.utils import handle_api_error
from src.database.database_service import (
    create_new_institution,
    delete_institution,
    get_all_institutions,
    get_institution_by_id,
    get_institution_instructor_count,
    get_program_by_id,
    update_institution,
)
from src.services.auth_service import (
    UserRole,
    clear_current_program_id,
    get_current_program_id,
    get_current_user,
    login_required,
    permission_required,
    set_current_program_id,
)
from src.utils.constants import (
    FAILED_TO_CREATE_INSTITUTION_MSG,
    INSTITUTION_NOT_FOUND_MSG,
    NO_DATA_PROVIDED_MSG,
    NO_JSON_DATA_PROVIDED_MSG,
    PERMISSION_DENIED_MSG,
)
from src.utils.logging_config import get_logger

# Create blueprint
institutions_bp = Blueprint("institutions", __name__, url_prefix="/api")

# Initialize logger
logger = get_logger(__name__)


# ========================================
# HELPER FUNCTIONS
# ========================================


def _get_current_user_safe() -> Dict[str, Any]:
    """Get current user and ensure it is not None (for type safety in protected routes)."""
    user = get_current_user()
    if user is None:
        # In a real request this should have been caught by @login_required
        # but for type safety we must handle the None case.
        return {}
    return user


# ========================================
# INSTITUTION MANAGEMENT API
# ========================================


@institutions_bp.route("/institutions", methods=["GET"])
@permission_required("manage_institutions")
def list_institutions() -> ResponseReturnValue:
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


@institutions_bp.route("/institutions", methods=["POST"])
@permission_required("manage_institutions")
def create_institution_admin() -> ResponseReturnValue:
    """Site admin creates a new institution (without initial user)"""
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        # Simple institution creation for site admins
        required_fields = ["name", "short_name"]
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

        # Create institution (without admin user - site admin can add users separately)
        from src.database.database_service import create_new_institution_simple

        institution_id = create_new_institution_simple(
            name=data["name"],
            short_name=data["short_name"],
            active=data.get("active", True),
        )

        if institution_id:
            return (
                jsonify(
                    {
                        "success": True,
                        "institution_id": institution_id,
                        "message": "Institution created successfully",
                    }
                ),
                201,
            )
        else:
            return (
                jsonify({"success": False, "error": FAILED_TO_CREATE_INSTITUTION_MSG}),
                500,
            )

    except Exception as e:
        return handle_api_error(
            e, "Create institution", FAILED_TO_CREATE_INSTITUTION_MSG
        )


@institutions_bp.route("/institutions/register", methods=["POST"])
def create_institution_public() -> ResponseReturnValue:
    """Create a new institution with its first admin user (public endpoint for registration)"""
    try:
        data = request.get_json(silent=True) or {}

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
                jsonify({"success": False, "error": FAILED_TO_CREATE_INSTITUTION_MSG}),
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
        return handle_api_error(
            e, "Create institution", FAILED_TO_CREATE_INSTITUTION_MSG
        )


@institutions_bp.route("/institutions/<institution_id>", methods=["GET"])
@permission_required("view_institution_data", context_keys=["institution_id"])
def get_institution_details(institution_id: str) -> ResponseReturnValue:
    """Get institution details (users can only view their own institution)"""
    try:
        current_user = _get_current_user_safe()

        # Users can only view their own institution unless they're site admin
        if (
            current_user.get("institution_id") != institution_id
            and current_user.get("role") != UserRole.SITE_ADMIN.value
        ):
            return jsonify({"success": False, "error": PERMISSION_DENIED_MSG}), 403

        institution = get_institution_by_id(institution_id)
        if not institution:
            return jsonify({"success": False, "error": INSTITUTION_NOT_FOUND_MSG}), 404

        # Add current instructor count
        institution["current_instructor_count"] = get_institution_instructor_count(
            institution_id
        )

        return jsonify({"success": True, "institution": institution})

    except Exception as e:
        return handle_api_error(e, "Get institution", "Failed to retrieve institution")


@institutions_bp.route("/institutions/<institution_id>", methods=["PUT"])
@permission_required("manage_institutions")
def update_institution_endpoint(institution_id: str) -> ResponseReturnValue:
    """
    Update institution details (site admin or institution admin only)

    Allows updating name, short_name, settings, contact information, etc.
    """
    try:
        current_user = _get_current_user_safe()

        # Only site admin or own institution admin can update
        if (
            current_user.get("role") != UserRole.SITE_ADMIN.value
            and current_user.get("institution_id") != institution_id
        ):
            return jsonify({"success": False, "error": PERMISSION_DENIED_MSG}), 403

        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        # Check if institution exists
        institution = get_institution_by_id(institution_id)
        if not institution:
            return jsonify({"success": False, "error": INSTITUTION_NOT_FOUND_MSG}), 404

        success = update_institution(institution_id, data)

        if success:
            updated_institution = get_institution_by_id(institution_id)
            return (
                jsonify(
                    {
                        "success": True,
                        "institution": updated_institution,
                        "message": "Institution updated successfully",
                    }
                ),
                200,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to update institution"}),
                500,
            )

    except Exception as e:
        return handle_api_error(e, "Update institution", "Failed to update institution")


@institutions_bp.route("/institutions/<institution_id>", methods=["DELETE"])
@permission_required("manage_institutions")
def delete_institution_endpoint(institution_id: str) -> ResponseReturnValue:
    """
    Delete institution (site admin only - CASCADE deletes ALL related data)

    WARNING: This is DESTRUCTIVE and IRREVERSIBLE. It will delete:
    - All programs
    - All courses
    - All terms
    - All offerings
    - All sections
    - All users
    - All related data

    Requires confirmation query parameter: ?confirm=i know what I'm doing
    """
    try:
        current_user = _get_current_user_safe()

        # Only site admin can delete institutions
        if current_user.get("role") != UserRole.SITE_ADMIN.value:
            return jsonify({"success": False, "error": PERMISSION_DENIED_MSG}), 403

        # Check for confirmation
        confirmation = request.args.get("confirm", "")
        if confirmation != "i know what I'm doing":
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Confirmation required. Add query parameter: ?confirm=i know what I'm doing",
                    }
                ),
                400,
            )

        # Check if institution exists
        institution = get_institution_by_id(institution_id)
        if not institution:
            return jsonify({"success": False, "error": INSTITUTION_NOT_FOUND_MSG}), 404

        success = delete_institution(institution_id)

        if success:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Institution '{institution['name']}' and all related data deleted successfully",
                    }
                ),
                200,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to delete institution"}),
                500,
            )

    except Exception as e:
        return handle_api_error(e, "Delete institution", "Failed to delete institution")


# ========================================
# CONTEXT MANAGEMENT API
# ========================================


@institutions_bp.route("/context/program", methods=["GET"])
@login_required
def get_program_context() -> ResponseReturnValue:
    """Get current user's program context and accessible programs"""
    try:
        current_user = _get_current_user_safe()
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


@institutions_bp.route("/context/program/<program_id>", methods=["POST"])
@login_required
def switch_program_context(program_id: str) -> ResponseReturnValue:
    """Switch user's active program context"""
    try:
        current_user = _get_current_user_safe()

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


@institutions_bp.route("/context/program", methods=["DELETE"])
@login_required
def clear_program_context() -> ResponseReturnValue:
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
