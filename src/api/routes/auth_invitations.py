"""
Auth Invitations API routes.

Provides endpoints for creating, accepting, listing, resending,
and cancelling user invitations.
"""

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

from src.api.utils import (
    get_current_institution_id_safe,
    get_current_user_safe,
    handle_api_error,
)
from src.services.auth_service import (
    login_required,
    permission_required,
)
from src.utils.constants import (
    INSTITUTION_CONTEXT_REQUIRED_MSG,
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
auth_invitations_bp = Blueprint("auth_invitations", __name__, url_prefix="/api")

# Initialize logger
logger = get_logger(__name__)


# ===== INVITATION API ENDPOINTS =====


@auth_invitations_bp.route("/auth/invite", methods=["POST"])
@permission_required("manage_institution_users")
def create_invitation_api() -> ResponseReturnValue:
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
        from src.services.invitation_service import InvitationError, InvitationService

        # Get request data (silent=True prevents 415 exception, returns None instead)
        data = request.get_json(silent=True) or {}
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
        current_user = get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": USER_NOT_AUTHENTICATED_MSG}), 401

        institution_id = get_current_institution_id_safe()
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
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            section_id=data.get("section_id"),
            replace_existing=data.get("replace_existing", False),
        )

        # Send invitation email
        email_sent, email_error = InvitationService.send_invitation(invitation)

        response_body = {
            "success": True,
            "invitation_id": invitation["id"],
            "message": (
                INVITATION_CREATED_AND_SENT_MSG
                if email_sent and not email_error
                else INVITATION_CREATED_EMAIL_FAILED_MSG
            ),
        }
        if email_error:
            response_body["email_error"] = email_error

        return jsonify(response_body), 201

    except InvitationError as e:
        logger.error(f"Invitation error: {e}")
        # Return 409 if conflict, else 400
        status_code = 409 if "already exists" in str(e) else 400
        return jsonify({"success": False, "error": str(e)}), status_code

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


@auth_invitations_bp.route("/auth/accept-invitation", methods=["POST"])
def accept_invitation_api() -> ResponseReturnValue:
    """
    Accept an invitation and create user account

    JSON Body:
    {
        "invitation_token": "secure-token-here",
        "password": "newpassword123",  # pragma: allowlist secret - API documentation example
        "display_name": "John Doe"  // Optional
    }

    Returns:
        200: Invitation accepted and account created
        400: Invalid request data or token
        410: Invitation expired or already accepted
        500: Server error
    """
    try:
        from src.services.invitation_service import InvitationService

        # Get request data
        data = request.get_json(silent=True) or {}
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


@auth_invitations_bp.route(
    "/auth/invitation-status/<invitation_token>", methods=["GET"]
)
def get_invitation_status_api(invitation_token: str) -> ResponseReturnValue:
    """
    Get invitation status by token

    URL: /api/auth/invitation-status/{invitation_token}

    Returns:
        200: Invitation status retrieved
        404: Invitation not found
        500: Server error
    """
    try:
        from src.services.invitation_service import InvitationService

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


@auth_invitations_bp.route("/auth/resend-invitation/<invitation_id>", methods=["POST"])
@permission_required("manage_institution_users")
def resend_invitation_api(invitation_id: str) -> ResponseReturnValue:
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
        from src.services.invitation_service import InvitationService

        # Resend invitation
        success, email_error = InvitationService.resend_invitation(invitation_id)

        response_body = {
            "success": True,
            "message": "Invitation resent successfully",
        }
        if email_error:
            response_body.update(
                {
                    "message": INVITATION_CREATED_EMAIL_FAILED_MSG,
                    "email_error": email_error,
                }
            )

        if success:
            return jsonify(response_body), 200
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Failed to resend invitation",
                    "email_error": email_error,
                }
            ),
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


@auth_invitations_bp.route("/auth/invitations", methods=["GET"])
@permission_required("manage_institution_users")
def list_invitations_api() -> ResponseReturnValue:
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
        from src.services.invitation_service import InvitationService

        # Get institution context
        institution_id = get_current_institution_id_safe()
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


@auth_invitations_bp.route(
    "/auth/cancel-invitation/<invitation_id>", methods=["DELETE"]
)
@permission_required("manage_institution_users")
def cancel_invitation_api(invitation_id: str) -> ResponseReturnValue:
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
        from src.services.invitation_service import InvitationService

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


@auth_invitations_bp.route("/invitations", methods=["POST"])
@permission_required("manage_institution_users")
def create_invitation_public_api() -> ResponseReturnValue:
    """
    Create and send a user invitation via /api/invitations.

    Accepts field names:
    - email (alias: invitee_email)
    - role (alias: invitee_role)
    - program_ids (optional)
    - personal_message (optional)

    Returns 201 with invitation_id on success.
    """
    try:
        from src.services.invitation_service import InvitationError, InvitationService

        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        # Normalize fields
        invitee_email = payload.get("invitee_email") or payload.get("email")
        invitee_role = payload.get("invitee_role") or payload.get("role")
        program_ids = payload.get("program_ids", [])
        personal_message = payload.get("personal_message")
        first_name = payload.get("first_name")
        last_name = payload.get("last_name")
        section_id = payload.get("section_id")
        replace_existing = payload.get("replace_existing", False)

        if not invitee_email:
            return (
                jsonify({"success": False, "error": MISSING_REQUIRED_FIELD_EMAIL_MSG}),
                400,
            )
        if not invitee_role:
            return (
                jsonify({"success": False, "error": "Missing required field: role"}),
                400,
            )

        current_user = get_current_user_safe()
        if not current_user:
            return jsonify({"success": False, "error": USER_NOT_AUTHENTICATED_MSG}), 401

        institution_id = get_current_institution_id_safe()
        if not institution_id:
            return (
                jsonify({"success": False, "error": INSTITUTION_CONTEXT_REQUIRED_MSG}),
                400,
            )

        # Create and send invitation
        invitation = InvitationService.create_invitation(
            inviter_user_id=current_user["user_id"],
            inviter_email=current_user["email"],
            invitee_email=invitee_email,
            invitee_role=invitee_role,
            institution_id=institution_id,
            program_ids=program_ids,
            personal_message=personal_message,
            first_name=first_name,
            last_name=last_name,
            section_id=section_id,
            replace_existing=replace_existing,
        )

        email_sent, email_error = InvitationService.send_invitation(invitation)

        return (
            jsonify(
                {
                    "success": True,
                    "invitation_id": invitation["id"],
                    "message": (
                        INVITATION_CREATED_AND_SENT_MSG
                        if email_sent and not email_error
                        else INVITATION_CREATED_EMAIL_FAILED_MSG
                    ),
                    **({"email_error": email_error} if email_error else {}),
                }
            ),
            201,
        )

    except InvitationError as exc:
        return handle_api_error(exc, "Create invitation", str(exc), 400)
    except Exception as exc:
        return handle_api_error(exc, "Create invitation", "Failed to create invitation")
