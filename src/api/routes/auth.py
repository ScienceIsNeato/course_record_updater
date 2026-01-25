"""
Authentication API routes.

Provides endpoints for login, logout, session management, profile updates,
and password management (change password, forgot password, reset password).
"""

from typing import Any, Dict

from flask import Blueprint, jsonify, request, session
from flask.typing import ResponseReturnValue

from src.api.utils import handle_api_error
from src.database.database_service import get_user_by_id, update_user, update_user_profile
from src.services.auth_service import get_current_user, login_required
from src.utils.constants import (
    MISSING_REQUIRED_FIELD_EMAIL_MSG,
    NO_JSON_DATA_PROVIDED_MSG,
    USER_NOT_FOUND_MSG,
)
from src.utils.logging_config import get_logger

# Create blueprint with /api prefix so routes are /api/auth/*
auth_bp = Blueprint("auth", __name__, url_prefix="/api")

logger = get_logger(__name__)


def _get_current_user_safe() -> Dict[str, Any]:
    """Get current user, return empty dict if None."""
    user = get_current_user()
    return user if user else {}


def _get_current_user_id_safe() -> str:
    """Get current user's ID, return 'unknown' if None."""
    user = _get_current_user_safe()
    user_id = user.get("user_id")
    return str(user_id) if user_id else "unknown"


# ===== LOGIN/LOGOUT ENDPOINTS =====


@auth_bp.route("/auth/login", methods=["POST"])
def login_api() -> ResponseReturnValue:
    """Authenticate user and create session."""
    from src.services.login_service import INVALID_CREDENTIALS_MSG, LoginError, LoginService
    from src.services.password_service import AccountLockedError

    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        for field in ["email", "password"]:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

        result = LoginService.authenticate_user(
            email=data["email"],
            password=data["password"],
            remember_me=data.get("remember_me", False),
        )

        next_url = session.pop("next_after_login", None)
        if next_url:
            result["next_url"] = next_url

        return jsonify({"success": True, **result}), 200

    except AccountLockedError:
        logger.warning(f"Account locked during login attempt: {data.get('email', 'unknown')}")
        return jsonify({"success": False, "error": "Account is locked"}), 423
    except LoginError as e:
        logger.error(f"User login failed: {e}")
        return jsonify({"success": False, "error": str(e) if str(e) != INVALID_CREDENTIALS_MSG else INVALID_CREDENTIALS_MSG}), 401
    except Exception as e:
        logger.error(f"Login error: {e}")
        return handle_api_error(e, "User login", "An unexpected error occurred")


@auth_bp.route("/auth/logout", methods=["POST"])
def logout_api() -> ResponseReturnValue:
    """Logout current user and destroy session."""
    try:
        from src.services.login_service import LoginService
        result = LoginService.logout_user()
        return jsonify({"success": True, **result}), 200
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"success": False, "error": "Logout failed"}), 500


@auth_bp.route("/auth/status", methods=["GET"])
def login_status_api() -> ResponseReturnValue:
    """Get current login status."""
    try:
        from src.services.login_service import LoginService
        status = LoginService.get_login_status()
        return jsonify({"success": True, **status}), 200
    except Exception as e:
        logger.error(f"Error getting login status: {e}")
        return jsonify({"success": False, "error": "Failed to get login status"}), 500


@auth_bp.route("/auth/refresh", methods=["POST"])
def refresh_session_api() -> ResponseReturnValue:
    """Refresh current user session."""
    try:
        from src.services.login_service import LoginService
        result = LoginService.refresh_session()
        return jsonify({"success": True, **result}), 200
    except Exception as e:
        logger.error(f"Session refresh error: {e}")
        if "No active session" in str(e):
            return jsonify({"success": False, "error": str(e)}), 401
        return jsonify({"success": False, "error": "Failed to refresh session"}), 500


@auth_bp.route("/auth/lockout-status/<email>", methods=["GET"])
def check_lockout_status_api(email: str) -> ResponseReturnValue:
    """Check account lockout status for an email."""
    try:
        from src.services.login_service import LoginService
        status = LoginService.check_account_lockout_status(email)
        return jsonify({"success": True, **status}), 200
    except Exception as e:
        logger.error(f"Error checking lockout status: {e}")
        return jsonify({"success": False, "error": "Failed to check lockout status"}), 500


@auth_bp.route("/auth/unlock-account", methods=["POST"])
@login_required
def unlock_account_api() -> ResponseReturnValue:
    """Manually unlock a locked account (admin function)."""
    try:
        from src.services.login_service import LoginService

        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400
        if "email" not in data:
            return jsonify({"success": False, "error": MISSING_REQUIRED_FIELD_EMAIL_MSG}), 400

        current_user = _get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        result = LoginService.unlock_account(data["email"], current_user["id"])
        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Account unlock error: {e}")
        return jsonify({"success": False, "error": "Failed to unlock account"}), 500


# ===== PROFILE MANAGEMENT ENDPOINTS =====


@auth_bp.route("/auth/profile", methods=["PATCH"])
@login_required
def update_profile_api() -> ResponseReturnValue:
    """Update current user's profile information."""
    try:
        current_user = _get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        # Filter allowed fields - SECURITY: prevent email/role/institution changes
        allowed_fields = {"first_name", "last_name"}
        profile_data = {k: v for k, v in data.items() if k in allowed_fields}
        if not profile_data:
            return jsonify({"success": False, "error": "No valid fields to update"}), 400

        user_id = _get_current_user_id_safe()
        success = update_user_profile(user_id, profile_data)

        if success:
            if "first_name" in profile_data:
                session["first_name"] = profile_data["first_name"]
            if "last_name" in profile_data:
                session["last_name"] = profile_data["last_name"]
            new_first = profile_data.get("first_name", session.get("first_name", ""))
            new_last = profile_data.get("last_name", session.get("last_name", ""))
            session["display_name"] = f"{new_first} {new_last}".strip()
            return jsonify({"success": True, "message": "Profile updated successfully"}), 200
        return jsonify({"success": False, "error": "Failed to update profile"}), 500

    except Exception as e:
        logger.error(f"Profile update error: {e}")
        return jsonify({"success": False, "error": "Failed to update profile"}), 500


@auth_bp.route("/auth/change-password", methods=["POST"])
@login_required
def change_password_api() -> ResponseReturnValue:
    """Change current user's password (requires current password verification)."""
    try:
        from src.services.password_service import PasswordValidationError, hash_password, verify_password

        current_user = _get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        if "current_password" not in data:
            return jsonify({"success": False, "error": "Missing required field: current_password"}), 400
        if "new_password" not in data:
            return jsonify({"success": False, "error": "Missing required field: new_password"}), 400

        user_id = _get_current_user_id_safe()
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"success": False, "error": USER_NOT_FOUND_MSG}), 404

        if not verify_password(data["current_password"], user.get("password_hash", "")):
            return jsonify({"success": False, "error": "Current password is incorrect"}), 401

        try:
            new_hash = hash_password(data["new_password"])
        except PasswordValidationError as e:
            return jsonify({"success": False, "error": str(e)}), 400

        success = update_user(user_id, {"password_hash": new_hash})
        if success:
            logger.info(f"Password changed for user {user_id}")
            return jsonify({"success": True, "message": "Password changed successfully"}), 200
        return jsonify({"success": False, "error": "Failed to change password"}), 500

    except Exception as e:
        logger.error(f"Password change error: {e}")
        return jsonify({"success": False, "error": "Failed to change password"}), 500


# ===== PASSWORD RESET ENDPOINTS =====


@auth_bp.route("/auth/forgot-password", methods=["POST"])
def forgot_password_api() -> ResponseReturnValue:
    """Request password reset email."""
    try:
        from src.services.password_reset_service import PasswordResetService

        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400
        if "email" not in data:
            return jsonify({"success": False, "error": MISSING_REQUIRED_FIELD_EMAIL_MSG}), 400

        result = PasswordResetService.request_password_reset(data["email"])
        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        if "Too many" in str(e):
            return jsonify({"success": False, "error": str(e)}), 429
        elif "restricted in development" in str(e):
            return jsonify({"success": False, "error": str(e)}), 400
        return jsonify({"success": False, "error": "Password reset request failed"}), 500


@auth_bp.route("/auth/reset-password", methods=["POST"])
def reset_password_api() -> ResponseReturnValue:
    """Complete password reset with new password."""
    try:
        from src.services.password_reset_service import PasswordResetService

        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        for field in ["reset_token", "new_password"]:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

        result = PasswordResetService.reset_password(
            reset_token=data["reset_token"], new_password=data["new_password"]
        )
        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Password reset error: {e}")
        if any(phrase in str(e) for phrase in ["Invalid", "expired", "validation failed"]):
            return jsonify({"success": False, "error": str(e)}), 400
        return jsonify({"success": False, "error": "Password reset failed"}), 500


@auth_bp.route("/auth/validate-reset-token/<reset_token>", methods=["GET"])
def validate_reset_token_api(reset_token: str) -> ResponseReturnValue:
    """Validate a password reset token."""
    try:
        from src.services.password_reset_service import PasswordResetService
        result = PasswordResetService.validate_reset_token(reset_token)
        return jsonify({"success": True, **result}), 200
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return jsonify({"success": False, "error": "Failed to validate reset token"}), 500


@auth_bp.route("/auth/reset-status/<email>", methods=["GET"])
def reset_status_api(email: str) -> ResponseReturnValue:
    """Get password reset status for an email."""
    try:
        from src.services.password_reset_service import PasswordResetService
        result = PasswordResetService.get_reset_status(email)
        return jsonify({"success": True, **result}), 200
    except Exception as e:
        logger.error(f"Reset status error: {e}")
        return jsonify({"success": False, "error": "Failed to get reset status"}), 500
