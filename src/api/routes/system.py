"""
System API routes.

Provides endpoints for system health checks and date override management.
"""

from typing import Any, Dict

from flask import Blueprint, jsonify, request, session
from flask.typing import ResponseReturnValue

from src.api.utils import handle_api_error
from src.database.database_service import update_user
from src.services.auth_service import get_current_user
from src.utils.logging_config import get_logger

# Create blueprint
system_bp = Blueprint("system", __name__, url_prefix="/api")

# Initialize logger
logger = get_logger(__name__)


def _get_current_user_safe() -> Dict[str, Any]:
    """Get current user and ensure it is not None (for type safety in protected routes)."""
    user = get_current_user()
    if user is None:
        return {}
    return user


def _get_current_user_id_safe() -> str:
    """Get current user's ID and ensure it is not None."""
    user = _get_current_user_safe()
    user_id = user.get("user_id")
    if not user_id:
        return "unknown"
    return str(user_id)


# ========================================
# HEALTH CHECK API
# ========================================


@system_bp.route("/health", methods=["GET"])
def health_check() -> ResponseReturnValue:
    """API health check endpoint"""
    return jsonify(
        {
            "success": True,
            "status": "healthy",
            "message": "Loopcloser API is running",
            "version": "2.0.0",
        }
    )


# ========================================
# SYSTEM DATE OVERRIDE API
# ========================================


@system_bp.route("/profile/system-date", methods=["GET"])
def get_system_date() -> ResponseReturnValue:
    """
    Get current system date override status.

    Only available to institution_admin and site_admin roles.
    """
    try:
        current_user = _get_current_user_safe()
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


@system_bp.route("/profile/system-date", methods=["POST"])
def set_system_date() -> ResponseReturnValue:
    """
    Set system date override.

    Only available to institution_admin and site_admin roles.
    Requires JSON body: {"date": "2024-01-15T12:00:00Z"}
    """
    from dateutil import parser as date_parser

    try:
        current_user = _get_current_user_safe()
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
        user_id = _get_current_user_id_safe()
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


@system_bp.route("/profile/system-date", methods=["DELETE"])
def clear_system_date() -> ResponseReturnValue:
    """
    Clear system date override (return to real time).

    Only available to institution_admin and site_admin roles.
    """
    try:
        current_user = _get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": "Not authenticated"}), 401

        # Check role - only admins can access
        role = current_user.get("role", "")
        if role not in ["institution_admin", "site_admin"]:
            return jsonify({"success": False, "error": "Admin access required"}), 403

        # Clear override
        user_id = _get_current_user_id_safe()
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
