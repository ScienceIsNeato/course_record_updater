"""
Context and user profile API routes.

Provides endpoints for managing program context switching, retrieving
current user information, and system date override functionality.
Also includes the global context validation before_app_request handler.
"""

from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request, session
from flask.typing import ResponseReturnValue

from src.api.utils import (
    get_current_institution_id_safe,
    get_current_user_id_safe,
    get_current_user_safe,
    handle_api_error,
)
from src.database.database_service import (
    get_program_by_id,
    update_user,
)
from src.services.auth_service import (
    UserRole,
    clear_current_program_id,
    get_current_program_id,
    login_required,
    set_current_program_id,
)
from src.utils.logging_config import get_logger

# Create blueprint
context_bp = Blueprint("context", __name__, url_prefix="/api")

# Initialize logger
logger = get_logger(__name__)


# ========================================
# CONTEXT VALIDATION (before_app_request)
# ========================================

# Endpoints that skip context validation (checked before requiring institution context)
_CONTEXT_SKIP_ENDPOINTS = frozenset(
    [
        "get_program_context",
        "switch_program_context",
        "clear_program_context",
        "create_institution",
        "list_institutions",
        "get_current_user_info",
        "get_system_date",
        "set_system_date",
        "clear_system_date",
    ]
)


def _should_skip_context_validation(endpoint: str) -> bool:
    """Check if the endpoint should skip context validation."""
    if not endpoint:
        return True
    # Skip non-API endpoints (static files, HTML pages)
    if "." not in endpoint:
        return True
    # Skip auth endpoints
    if "auth" in endpoint:
        return True
    # Get the function name (after the dot)
    func_name = endpoint.rsplit(".", 1)[-1]
    return func_name in _CONTEXT_SKIP_ENDPOINTS


@context_bp.before_app_request
def validate_context() -> Optional[ResponseReturnValue]:
    """Validate institution and program context for API requests"""
    # Skip validation for certain endpoints and methods
    endpoint = request.endpoint
    if not endpoint or _should_skip_context_validation(endpoint):
        return None

    # Skip validation for OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        return None

    try:
        current_user = get_current_user_safe()
        if not current_user:
            return None  # Let the auth decorators handle authentication

        # Site admins don't need context validation
        if current_user.get("role") == UserRole.SITE_ADMIN.value:
            return None

        # Validate institution context for non-site-admin users
        institution_id = get_current_institution_id_safe()
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
        return None

    return None


# ========================================
# PROGRAM CONTEXT API
# ========================================


@context_bp.route("/context/program", methods=["GET"])
@login_required
def get_program_context() -> ResponseReturnValue:
    """Get current user's program context and accessible programs"""
    try:
        current_user = get_current_user_safe()
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


@context_bp.route("/context/program/<program_id>", methods=["POST"])
@login_required
def switch_program_context(program_id: str) -> ResponseReturnValue:
    """Switch user's active program context"""
    try:
        current_user = get_current_user_safe()

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


@context_bp.route("/context/program", methods=["DELETE"])
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


# ========================================
# USER MANAGEMENT API
# ========================================


@context_bp.route("/me", methods=["GET"])
def get_current_user_info() -> ResponseReturnValue:
    """
    Get current authenticated user's information

    Returns full user object including program_ids for RBAC validation
    """
    try:
        current_user = get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": "Not authenticated"}), 401

        # Return user data with program_ids for program admin RBAC
        return jsonify(
            {
                "success": True,
                "user_id": current_user["user_id"],
                "email": current_user["email"],
                "first_name": current_user.get("first_name"),
                "last_name": current_user.get("last_name"),
                "role": current_user["role"],
                "institution_id": current_user.get("institution_id"),
                "program_ids": current_user.get("program_ids", []),
            }
        )
    except Exception as e:
        return handle_api_error(e, "Get current user", "Failed to get user information")


# ========================================
# SYSTEM DATE OVERRIDE API
# ========================================


@context_bp.route("/profile/system-date", methods=["GET"])
def get_system_date() -> ResponseReturnValue:
    """
    Get current system date override status.

    Only available to institution_admin and site_admin roles.
    """
    try:
        current_user = get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": "Not authenticated"}), 401

        # Check role - only admins can access
        role = current_user.get("role", "")
        if role not in ["institution_admin", "site_admin"]:
            return jsonify({"success": False, "error": "Admin access required"}), 403

        override = current_user.get("system_date_override")
        return jsonify(
            {
                "success": True,
                "is_overridden": override is not None,
                "override_date": override.isoformat() if override else None,
            }
        )
    except Exception as e:
        return handle_api_error(e, "Get system date", "Failed to get system date")


@context_bp.route("/profile/system-date", methods=["POST"])
def set_system_date() -> ResponseReturnValue:
    """
    Set system date override.

    Only available to institution_admin and site_admin roles.
    Requires JSON body: {"date": "2024-01-15T12:00:00Z"}
    """
    from dateutil import parser as date_parser

    try:
        current_user = get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": "Not authenticated"}), 401

        # Check role - only admins can access
        role = current_user.get("role", "")
        if role not in ["institution_admin", "site_admin"]:
            return jsonify({"success": False, "error": "Admin access required"}), 403

        data = request.get_json()
        if not data or "date" not in data:
            return jsonify({"success": False, "error": "date field required"}), 400

        try:
            override_date = date_parser.parse(data["date"])
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Invalid date format"}), 400

        # Update user record with override
        user_id = get_current_user_id_safe()
        if user_id:
            update_user(user_id, {"system_date_override": override_date})

        # Update session immediately so validation middleware picks it up
        session["system_date_override"] = override_date.isoformat()

        return jsonify(
            {
                "success": True,
                "force_refresh": True,
                "message": f"System date set to {override_date.isoformat()}",
            }
        )
    except Exception as e:
        return handle_api_error(e, "Set system date", "Failed to set system date")


@context_bp.route("/profile/system-date", methods=["DELETE"])
def clear_system_date() -> ResponseReturnValue:
    """
    Clear system date override (return to real time).

    Only available to institution_admin and site_admin roles.
    """
    try:
        current_user = get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": "Not authenticated"}), 401

        # Check role - only admins can access
        role = current_user.get("role", "")
        if role not in ["institution_admin", "site_admin"]:
            return jsonify({"success": False, "error": "Admin access required"}), 403

        # Clear override
        user_id = get_current_user_id_safe()
        update_user(user_id, {"system_date_override": None})

        # Update session immediately
        session.pop("system_date_override", None)

        return jsonify(
            {
                "success": True,
                "force_refresh": True,
                "message": "System date reset to live",
            }
        )
    except Exception as e:
        return handle_api_error(e, "Clear system date", "Failed to clear system date")
