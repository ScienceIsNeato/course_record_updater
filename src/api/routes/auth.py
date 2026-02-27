"""
Auth API routes.

Provides endpoints for user registration, email verification,
login/logout, session management, and account lockout handling.
"""

from typing import Any, Dict

from flask import Blueprint, flash, jsonify, redirect, request, url_for
from flask.typing import ResponseReturnValue

from src.api.utils import get_current_user_safe, handle_api_error
from src.services.auth_service import login_required
from src.services.registration_service import (
    RegistrationError,
    get_registration_status,
    register_institution_admin,
    resend_verification_email,
    verify_email,
)
from src.utils.constants import (
    INVALID_EMAIL_FORMAT_MSG,
    MISSING_REQUIRED_FIELD_EMAIL_MSG,
    NO_JSON_DATA_PROVIDED_MSG,
)
from src.utils.logging_config import get_logger

# Create blueprint
auth_bp = Blueprint("auth", __name__, url_prefix="/api")

# Initialize logger
logger = get_logger(__name__)


# ===== REGISTRATION API ENDPOINTS =====


@auth_bp.route("/auth/register", methods=["POST"])
def register_institution_admin_api() -> ResponseReturnValue:
    """Register a new institution administrator.

    Expects JSON with email, password, first_name, last_name,
    institution_name, and optional website_url.

    Returns 201 with success, message, user_id, institution_id, email_sent.
    """
    try:
        data = request.get_json(silent=True) or {}

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


@auth_bp.route("/auth/verify-email/<token>", methods=["GET"])
def verify_email_api(token: str) -> ResponseReturnValue:
    """
    Verify user's email address using verification token.
    Redirects to login page with success/error message.

    URL: /api/auth/verify-email/{verification_token}
    """
    from urllib.parse import urlencode

    try:
        # Validate token
        if not token or len(token) < 10:
            flash("Invalid verification token. Please request a new one.", "error")
            return redirect(url_for("login"))

        # Verify email
        result = verify_email(token)

        if result["success"]:
            # Build success message
            if result.get("already_verified"):
                message = "Your email was already verified. You can log in now."
            else:
                message = "Email verified successfully! Your account is now active."

            # Redirect to login with success message
            return redirect(f"/login?message={urlencode({'': message})[1:]}")
        else:
            flash(result.get("error", "Verification failed."), "error")
            return redirect(url_for("login"))

    except RegistrationError as e:
        logger.warning(f"Email verification failed: {e}")
        flash(str(e), "error")
        return redirect(url_for("login"))

    except Exception as e:
        logger.error(f"Unexpected error in email verification: {e}")
        flash("Email verification failed due to a server error.", "error")
        return redirect(url_for("login"))


@auth_bp.route("/auth/resend-verification", methods=["POST"])
def resend_verification_email_api() -> ResponseReturnValue:
    """Resend verification email for a pending user.

    Expects JSON with email. Returns 200 with success, message, email_sent.
    """
    try:
        data = request.get_json(silent=True) or {}

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


@auth_bp.route("/auth/registration-status/<email>", methods=["GET"])
def get_registration_status_api(email: str) -> ResponseReturnValue:
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


# ===== LOGIN/LOGOUT API ENDPOINTS =====


@auth_bp.route("/auth/login", methods=["POST"])
def login_api() -> ResponseReturnValue:
    """
    Authenticate user and create session.

    Request body:
    - email: User email
    - password: User password
    - remember_me: Boolean (optional) for extended session

    Returns:
    - success: Boolean indicating authentication result
    - user: User data if successful
    - error: Error message if failed
    """
    from src.services.login_service import (
        INVALID_CREDENTIALS_MSG,
        LoginError,
        LoginService,
    )
    from src.services.password_service import AccountLockedError

    data: Dict[str, Any] = {}
    try:

        # Get request data
        data = request.get_json(silent=True) or {}
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

        # Import session locally to avoid circular imports when this module is
        # loaded early in app initialization. This is necessary because session
        # depends on app context which may not be fully initialized during imports.
        # Check for 'next' URL in session (set by reminder-login route for
        # deep-linking after authentication)
        from flask import session

        next_url = session.pop("next_after_login", None)
        if next_url:
            result["next_url"] = next_url

        return (
            jsonify({"success": True, **result}),
            200,
        )

    except AccountLockedError:
        logger.warning(
            f"Account locked during login attempt: {data.get('email', 'unknown')}"
        )
        return jsonify({"success": False, "error": "Account is locked"}), 423
    except LoginError as e:
        logger.error(f"User login failed: {e}")
        error_msg = str(e)
        if error_msg == INVALID_CREDENTIALS_MSG:
            error_msg = INVALID_CREDENTIALS_MSG
        return jsonify({"success": False, "error": error_msg}), 401
    except Exception as e:
        logger.error(f"Login error: {e}")
        return handle_api_error(e, "User login", "An unexpected error occurred")


@auth_bp.route("/auth/logout", methods=["POST"])
def logout_api() -> ResponseReturnValue:
    """
    Logout current user and destroy session

    Returns:
        200: Logout successful
        500: Server error
    """
    try:
        from src.services.login_service import LoginService

        # Logout user
        result = LoginService.logout_user()

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"success": False, "error": "Logout failed"}), 500


@auth_bp.route("/auth/status", methods=["GET"])
def login_status_api() -> ResponseReturnValue:
    """
    Get current login status

    Returns:
        200: Status retrieved successfully
        500: Server error
    """
    try:
        from src.services.login_service import LoginService

        # Get login status
        status = LoginService.get_login_status()

        return jsonify({"success": True, **status}), 200

    except Exception as e:
        logger.error(f"Error getting login status: {e}")
        return jsonify({"success": False, "error": "Failed to get login status"}), 500


@auth_bp.route("/auth/refresh", methods=["POST"])
def refresh_session_api() -> ResponseReturnValue:
    """
    Refresh current user session

    Returns:
        200: Session refreshed successfully
        401: No active session
        500: Server error
    """
    try:
        from src.services.login_service import LoginService

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


@auth_bp.route("/auth/lockout-status/<email>", methods=["GET"])
def check_lockout_status_api(email: str) -> ResponseReturnValue:
    """
    Check account lockout status for an email

    URL: /api/auth/lockout-status/{email}

    Returns:
        200: Lockout status retrieved
        500: Server error
    """
    try:
        from src.services.login_service import LoginService

        # Check lockout status
        status = LoginService.check_account_lockout_status(email)

        return jsonify({"success": True, **status}), 200

    except Exception as e:
        logger.error(f"Error checking lockout status: {e}")
        return (
            jsonify({"success": False, "error": "Failed to check lockout status"}),
            500,
        )


@auth_bp.route("/auth/unlock-account", methods=["POST"])
@login_required
def unlock_account_api() -> ResponseReturnValue:
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
        from src.services.login_service import LoginService

        # Get request data
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        if "email" not in data:
            return (
                jsonify({"success": False, "error": MISSING_REQUIRED_FIELD_EMAIL_MSG}),
                400,
            )

        # Get current user and verify admin role
        current_user = get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": "Authentication required"}), 401

        # Only site_admin and institution_admin can unlock accounts
        user_role = current_user.get("role")
        if user_role not in ["site_admin", "institution_admin"]:
            return (
                jsonify(
                    {"success": False, "error": "Unauthorized: Admin role required"}
                ),
                403,
            )

        # Unlock account
        result = LoginService.unlock_account(data["email"], current_user["user_id"])

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"Account unlock error: {e}")
        return jsonify({"success": False, "error": "Failed to unlock account"}), 500
