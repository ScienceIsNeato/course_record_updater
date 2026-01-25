"""
Auth Profile API routes.

Provides endpoints for user profile management, password changes, and
password reset workflows.
"""

from typing import Any, Dict

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

from src.database.database_service import (
    get_user_by_id,
    update_user,
    update_user_profile,
)
from src.services.auth_service import get_current_user, login_required
from src.utils.constants import (
    MISSING_REQUIRED_FIELD_EMAIL_MSG,
    NO_JSON_DATA_PROVIDED_MSG,
    USER_NOT_FOUND_MSG,
)
from src.utils.logging_config import get_logger

# Create blueprint
auth_profile_bp = Blueprint("auth_profile", __name__, url_prefix="/api")

# Initialize logger
logger = get_logger(__name__)


# HELPER: Safe access to current user for type checking
def _get_current_user_safe() -> Dict[str, Any]:
    """Get current user and ensure it is not None (for type safety in protected routes)."""
    user = get_current_user()
    if user is None:
        # In a real request this should have been caught by @login_required
        # but for type safety we must handle the None case.
        return {}
    return user


def _get_current_user_id_safe() -> str:
    """Get current user's ID and ensure it is not None."""
    user = _get_current_user_safe()
    user_id = user.get("user_id")
    if not user_id:
        return "unknown"
    return str(user_id)


# ===== PROFILE MANAGEMENT API ENDPOINTS =====


@auth_profile_bp.route("/auth/profile", methods=["PATCH"])
@login_required
def update_profile_api() -> ResponseReturnValue:
    """
    Update current user's profile information

    JSON Body (all fields optional):
    {
        "first_name": "Jane",
        "last_name": "Smith"
    }

    Note: email and role cannot be changed via this endpoint

    Returns:
        200: Profile updated successfully
        400: Invalid request data
        401: Not authenticated
        500: Server error
    """
    try:

        # Get current user
        current_user = _get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        # Get request data
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        # Filter allowed fields - SECURITY: prevent email/role/institution changes
        allowed_fields = {"first_name", "last_name"}
        profile_data = {k: v for k, v in data.items() if k in allowed_fields}

        if not profile_data:
            return (
                jsonify({"success": False, "error": "No valid fields to update"}),
                400,
            )

        # Update profile
        user_id = _get_current_user_id_safe()
        success = update_user_profile(user_id, profile_data)

        if success:
            # Update session with new values so page refresh shows updated data
            from flask import session

            if "first_name" in profile_data:
                session["first_name"] = profile_data["first_name"]
            if "last_name" in profile_data:
                session["last_name"] = profile_data["last_name"]
            # Update display_name in session as well
            new_first = profile_data.get("first_name", session.get("first_name", ""))
            new_last = profile_data.get("last_name", session.get("last_name", ""))
            session["display_name"] = f"{new_first} {new_last}".strip()

            return (
                jsonify({"success": True, "message": "Profile updated successfully"}),
                200,
            )
        else:
            return jsonify({"success": False, "error": "Failed to update profile"}), 500

    except Exception as e:
        logger.error(f"Profile update error: {e}")
        return jsonify({"success": False, "error": "Failed to update profile"}), 500


@auth_profile_bp.route("/auth/change-password", methods=["POST"])
@login_required
def change_password_api() -> ResponseReturnValue:
    """
    Change current user's password (requires current password verification)

    JSON Body:
    {
        "current_password": "oldPassword123!",  # pragma: allowlist secret - API documentation example
        "new_password": "newPassword456!"  # pragma: allowlist secret - API documentation example
    }

    Returns:
        200: Password changed successfully
        400: Invalid request data or weak password
        401: Current password incorrect or not authenticated
        500: Server error
    """
    try:
        from src.services.password_service import (
            PasswordValidationError,
            hash_password,
            verify_password,
        )

        # Get current user
        current_user = _get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        # Get request data
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        # Validate required fields
        if "current_password" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Missing required field: current_password",
                    }
                ),
                400,
            )
        if "new_password" not in data:
            return (
                jsonify(
                    {"success": False, "error": "Missing required field: new_password"}
                ),
                400,
            )

        # Get user with password hash
        user_id = _get_current_user_id_safe()
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"success": False, "error": USER_NOT_FOUND_MSG}), 404

        # Verify current password
        if not verify_password(data["current_password"], user.get("password_hash", "")):
            return (
                jsonify({"success": False, "error": "Current password is incorrect"}),
                401,
            )

        # Hash new password (validates strength requirements)
        try:
            new_hash = hash_password(data["new_password"])
        except PasswordValidationError as e:
            return jsonify({"success": False, "error": str(e)}), 400

        # Update password in database
        success = update_user(user_id, {"password_hash": new_hash})

        if success:
            logger.info(f"Password changed for user {user_id}")
            return (
                jsonify({"success": True, "message": "Password changed successfully"}),
                200,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to change password"}),
                500,
            )

    except Exception as e:
        logger.error(f"Password change error: {e}")
        return jsonify({"success": False, "error": "Failed to change password"}), 500


# ===== PASSWORD RESET API ENDPOINTS =====


@auth_profile_bp.route("/auth/forgot-password", methods=["POST"])
def forgot_password_api() -> ResponseReturnValue:
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
        from src.services.password_reset_service import PasswordResetService

        # Get request data
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        if "email" not in data:
            return (
                jsonify({"success": False, "error": MISSING_REQUIRED_FIELD_EMAIL_MSG}),
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


@auth_profile_bp.route("/auth/reset-password", methods=["POST"])
def reset_password_api() -> ResponseReturnValue:
    """
    Complete password reset with new password

    JSON Body:
    {
        "reset_token": "secure-reset-token",
        "new_password": "newSecurePassword123!"  # pragma: allowlist secret - API documentation example
    }

    Returns:
        200: Password reset successful
        400: Invalid request data or token
        500: Server error
    """
    try:
        from src.services.password_reset_service import PasswordResetService

        # Get request data
        data = request.get_json(silent=True) or {}
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


@auth_profile_bp.route("/auth/validate-reset-token/<reset_token>", methods=["GET"])
def validate_reset_token_api(reset_token: str) -> ResponseReturnValue:
    """
    Validate a password reset token

    URL: /api/auth/validate-reset-token/{token}

    Returns:
        200: Token validation result
        500: Server error
    """
    try:
        from src.services.password_reset_service import PasswordResetService

        # Validate reset token
        result = PasswordResetService.validate_reset_token(reset_token)

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return (
            jsonify({"success": False, "error": "Failed to validate reset token"}),
            500,
        )


@auth_profile_bp.route("/auth/reset-status/<email>", methods=["GET"])
def reset_status_api(email: str) -> ResponseReturnValue:
    """
    Get password reset status for an email

    URL: /api/auth/reset-status/{email}

    Returns:
        200: Reset status retrieved
        500: Server error
    """
    try:
        from src.services.password_reset_service import PasswordResetService

        # Get reset status
        result = PasswordResetService.get_reset_status(email)

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Reset status error: {e}")
        return jsonify({"success": False, "error": "Failed to get reset status"}), 500
