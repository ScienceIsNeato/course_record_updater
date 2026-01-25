"""
Registration API routes.

Provides endpoints for user registration, email verification, and invitation management.
"""

from typing import Any, Dict

from flask import Blueprint, flash, jsonify, redirect, request, url_for
from flask.typing import ResponseReturnValue

from src.api.utils import handle_api_error
from src.services.auth_service import (
    get_current_institution_id,
    get_current_user,
    permission_required,
)
from src.services.registration_service import (
    RegistrationError,
    get_registration_status,
    register_institution_admin,
    resend_verification_email,
    verify_email,
)
from src.utils.constants import (
    INSTITUTION_CONTEXT_REQUIRED_MSG,
    INVALID_EMAIL_FORMAT_MSG,
    INVITATION_CREATED_AND_SENT_MSG,
    INVITATION_CREATED_EMAIL_FAILED_MSG,
    INVITATION_NOT_FOUND_MSG,
    MISSING_REQUIRED_FIELD_EMAIL_MSG,
    NO_JSON_DATA_PROVIDED_MSG,
    NOT_FOUND_MSG,
    USER_NOT_AUTHENTICATED_MSG,
)
from src.utils.logging_config import get_logger

# Create blueprint
registration_bp = Blueprint("registration", __name__, url_prefix="/api")

logger = get_logger(__name__)


def _get_current_user_safe() -> Dict[str, Any]:
    """Get current user, return empty dict if None."""
    user = get_current_user()
    return user if user else {}


def _get_current_institution_id_safe() -> str:
    """Get current institution ID, return empty string if None."""
    inst_id = get_current_institution_id()
    return inst_id if inst_id else ""


@registration_bp.route("/auth/register", methods=["POST"])
def register_institution_admin_api() -> ResponseReturnValue:
    """Register a new institution administrator."""
    try:
        data = request.get_json(silent=True) or {}
        required = ["email", "password", "first_name", "last_name", "institution_name"]
        missing = [f for f in required if not data.get(f)]

        if missing:
            return jsonify({"success": False, "error": f"Missing required fields: {', '.join(missing)}"}), 400

        email = data["email"].strip().lower()
        if "@" not in email or "." not in email:
            return jsonify({"success": False, "error": INVALID_EMAIL_FORMAT_MSG}), 400

        result = register_institution_admin(
            email=email,
            password=data["password"],
            first_name=data["first_name"].strip(),
            last_name=data["last_name"].strip(),
            institution_name=data["institution_name"].strip(),
            website_url=data.get("website_url", "").strip() or None,
        )

        return jsonify({
            "success": result["success"],
            "message": result["message"],
            "user_id": result["user_id"],
            "institution_id": result["institution_id"],
            "email_sent": result["email_sent"],
        }), 201

    except RegistrationError as e:
        logger.warning(f"Registration failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in registration: {e}")
        return jsonify({"success": False, "error": "Registration failed due to server error"}), 500


@registration_bp.route("/auth/verify-email/<token>", methods=["GET"])
def verify_email_api(token: str) -> ResponseReturnValue:
    """Verify user's email address using verification token."""
    from urllib.parse import urlencode

    try:
        if not token or len(token) < 10:
            flash("Invalid verification token. Please request a new one.", "error")
            return redirect(url_for("login"))

        result = verify_email(token)

        if result["success"]:
            msg = "Your email was already verified. You can log in now." if result.get("already_verified") else "Email verified successfully! Your account is now active."
            return redirect(f"/login?message={urlencode({'': msg})[1:]}")
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


@registration_bp.route("/auth/resend-verification", methods=["POST"])
def resend_verification_email_api() -> ResponseReturnValue:
    """Resend verification email for pending user."""
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email", "").strip().lower()
        if not email:
            return jsonify({"success": False, "error": "Email address is required"}), 400
        if "@" not in email or "." not in email:
            return jsonify({"success": False, "error": INVALID_EMAIL_FORMAT_MSG}), 400

        result = resend_verification_email(email)
        return jsonify({"success": result["success"], "message": result["message"], "email_sent": result["email_sent"]}), 200

    except RegistrationError as e:
        logger.warning(f"Resend verification failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in resend verification: {e}")
        return jsonify({"success": False, "error": "Failed to resend verification email"}), 500


@registration_bp.route("/auth/registration-status/<email>", methods=["GET"])
def get_registration_status_api(email: str) -> ResponseReturnValue:
    """Get registration status for an email address."""
    try:
        email = email.strip().lower()
        if not email or "@" not in email or "." not in email:
            return jsonify({"exists": False, "status": "invalid_email", "message": INVALID_EMAIL_FORMAT_MSG}), 400
        return jsonify(get_registration_status(email)), 200
    except Exception as e:
        logger.error(f"Unexpected error in registration status check: {e}")
        return jsonify({"exists": False, "status": "error", "message": "Failed to check registration status"}), 500


# ===== INVITATION API ENDPOINTS =====


@registration_bp.route("/auth/invite", methods=["POST"])
@permission_required("manage_institution_users")
def create_invitation_api() -> ResponseReturnValue:
    """Create and send a user invitation."""
    try:
        from src.services.invitation_service import InvitationError, InvitationService

        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        for field in ["invitee_email", "invitee_role"]:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

        current_user = _get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": USER_NOT_AUTHENTICATED_MSG}), 401

        institution_id = _get_current_institution_id_safe()
        if not institution_id:
            return jsonify({"success": False, "error": INSTITUTION_CONTEXT_REQUIRED_MSG}), 400

        invitation = InvitationService.create_invitation(
            inviter_user_id=current_user["user_id"],
            inviter_email=current_user["email"],
            invitee_email=data["invitee_email"],
            invitee_role=data["invitee_role"],
            institution_id=institution_id,
            program_ids=data.get("program_ids", []),
            personal_message=data.get("personal_message"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            section_id=data.get("section_id"),
            replace_existing=data.get("replace_existing", False),
        )

        email_sent, email_error = InvitationService.send_invitation(invitation)
        response = {
            "success": True,
            "invitation_id": invitation["id"],
            "message": INVITATION_CREATED_AND_SENT_MSG if email_sent and not email_error else INVITATION_CREATED_EMAIL_FAILED_MSG,
        }
        if email_error:
            response["email_error"] = email_error
        return jsonify(response), 201

    except InvitationError as e:
        logger.error(f"Invitation error: {e}")
        return jsonify({"success": False, "error": str(e)}), 409 if "already exists" in str(e) else 400
    except Exception as e:
        logger.error(f"Error creating invitation: {e}")
        if "already exists" in str(e):
            return jsonify({"success": False, "error": str(e)}), 409
        elif "Invalid role" in str(e):
            return jsonify({"success": False, "error": str(e)}), 400
        return jsonify({"success": False, "error": "Failed to create invitation"}), 500


@registration_bp.route("/auth/accept-invitation", methods=["POST"])
def accept_invitation_api() -> ResponseReturnValue:
    """Accept an invitation and create user account."""
    try:
        from src.services.invitation_service import InvitationService

        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        for field in ["invitation_token", "password"]:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

        user = InvitationService.accept_invitation(
            invitation_token=data["invitation_token"],
            password=data["password"],
            display_name=data.get("display_name"),
        )

        return jsonify({
            "success": True,
            "user_id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "message": "Invitation accepted and account created successfully",
        }), 200

    except Exception as e:
        logger.error(f"Error accepting invitation: {e}")
        if "expired" in str(e).lower() or "already been accepted" in str(e):
            return jsonify({"success": False, "error": str(e)}), 410
        elif "Invalid" in str(e) or "not available" in str(e):
            return jsonify({"success": False, "error": str(e)}), 400
        return jsonify({"success": False, "error": "Failed to accept invitation"}), 500


@registration_bp.route("/auth/invitation-status/<invitation_token>", methods=["GET"])
def get_invitation_status_api(invitation_token: str) -> ResponseReturnValue:
    """Get invitation status by token."""
    try:
        from src.services.invitation_service import InvitationService
        status = InvitationService.get_invitation_status(invitation_token)
        return jsonify({"success": True, **status}), 200
    except Exception as e:
        logger.error(f"Error getting invitation status: {e}")
        if NOT_FOUND_MSG in str(e).lower():
            return jsonify({"success": False, "error": INVITATION_NOT_FOUND_MSG}), 404
        return jsonify({"success": False, "error": "Failed to get invitation status"}), 500


@registration_bp.route("/auth/resend-invitation/<invitation_id>", methods=["POST"])
@permission_required("manage_institution_users")
def resend_invitation_api(invitation_id: str) -> ResponseReturnValue:
    """Resend an existing invitation."""
    try:
        from src.services.invitation_service import InvitationService
        success, email_error = InvitationService.resend_invitation(invitation_id)

        response = {"success": True, "message": "Invitation resent successfully"}
        if email_error:
            response.update({"message": INVITATION_CREATED_EMAIL_FAILED_MSG, "email_error": email_error})

        if success:
            return jsonify(response), 200
        return jsonify({"success": False, "error": "Failed to resend invitation", "email_error": email_error}), 500

    except Exception as e:
        logger.error(f"Error resending invitation: {e}")
        if NOT_FOUND_MSG in str(e).lower():
            return jsonify({"success": False, "error": INVITATION_NOT_FOUND_MSG}), 404
        elif "Cannot resend" in str(e):
            return jsonify({"success": False, "error": str(e)}), 400
        return jsonify({"success": False, "error": "Failed to resend invitation"}), 500


@registration_bp.route("/auth/invitations", methods=["GET"])
@permission_required("manage_institution_users")
def list_invitations_api() -> ResponseReturnValue:
    """List invitations for current user's institution."""
    try:
        from src.services.invitation_service import InvitationService

        institution_id = _get_current_institution_id_safe()
        if not institution_id:
            return jsonify({"success": False, "error": INSTITUTION_CONTEXT_REQUIRED_MSG}), 400

        status = request.args.get("status")
        limit = min(int(request.args.get("limit", 50)), 100)
        offset = int(request.args.get("offset", 0))

        invitations = InvitationService.list_invitations(
            institution_id=institution_id, status=status, limit=limit, offset=offset
        )

        return jsonify({
            "success": True,
            "invitations": invitations,
            "count": len(invitations),
            "limit": limit,
            "offset": offset,
        }), 200

    except Exception as e:
        logger.error(f"Error listing invitations: {e}")
        return jsonify({"success": False, "error": "Failed to list invitations"}), 500


@registration_bp.route("/auth/cancel-invitation/<invitation_id>", methods=["DELETE"])
@permission_required("manage_institution_users")
def cancel_invitation_api(invitation_id: str) -> ResponseReturnValue:
    """Cancel a pending invitation."""
    try:
        from src.services.invitation_service import InvitationService
        success = InvitationService.cancel_invitation(invitation_id)

        if success:
            return jsonify({"success": True, "message": "Invitation cancelled successfully"}), 200
        return jsonify({"success": False, "error": "Failed to cancel invitation"}), 500

    except Exception as e:
        logger.error(f"Error cancelling invitation: {e}")
        if NOT_FOUND_MSG in str(e).lower():
            return jsonify({"success": False, "error": INVITATION_NOT_FOUND_MSG}), 404
        elif "Cannot cancel" in str(e):
            return jsonify({"success": False, "error": str(e)}), 400
        return jsonify({"success": False, "error": "Failed to cancel invitation"}), 500


@registration_bp.route("/invitations", methods=["POST"])
@permission_required("manage_institution_users")
def create_invitation_public_api() -> ResponseReturnValue:
    """Create and send a user invitation via /api/invitations (alternate endpoint)."""
    try:
        from src.services.invitation_service import InvitationError, InvitationService

        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        invitee_email = payload.get("invitee_email") or payload.get("email")
        invitee_role = payload.get("invitee_role") or payload.get("role")

        if not invitee_email:
            return jsonify({"success": False, "error": MISSING_REQUIRED_FIELD_EMAIL_MSG}), 400
        if not invitee_role:
            return jsonify({"success": False, "error": "Missing required field: role"}), 400

        current_user = _get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": USER_NOT_AUTHENTICATED_MSG}), 401

        institution_id = _get_current_institution_id_safe()
        if not institution_id:
            return jsonify({"success": False, "error": INSTITUTION_CONTEXT_REQUIRED_MSG}), 400

        invitation = InvitationService.create_invitation(
            inviter_user_id=current_user["user_id"],
            inviter_email=current_user["email"],
            invitee_email=invitee_email,
            invitee_role=invitee_role,
            institution_id=institution_id,
            program_ids=payload.get("program_ids", []),
            personal_message=payload.get("personal_message"),
            first_name=payload.get("first_name"),
            last_name=payload.get("last_name"),
            section_id=payload.get("section_id"),
            replace_existing=payload.get("replace_existing", False),
        )

        email_sent, email_error = InvitationService.send_invitation(invitation)

        return jsonify({
            "success": True,
            "invitation_id": invitation["id"],
            "message": INVITATION_CREATED_AND_SENT_MSG if email_sent and not email_error else INVITATION_CREATED_EMAIL_FAILED_MSG,
            **({"email_error": email_error} if email_error else {}),
        }), 201

    except InvitationError as exc:
        return handle_api_error(exc, "Create invitation", str(exc), 400)
    except Exception as exc:
        return handle_api_error(exc, "Create invitation", "Failed to create invitation")
