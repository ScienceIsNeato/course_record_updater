"""
Invitation Service Module

Handles user invitation functionality including:
- Creating and sending invitations
- Managing invitation tokens and expiry
- Processing invitation acceptance
- Tracking invitation status
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# Constants for datetime formatting
UTC_OFFSET = "+00:00"

import database_service as db
from auth_service import UserRole
from email_service import EmailService
from models import INVITATION_STATUSES, User, UserInvitation
from password_service import PasswordService

logger = logging.getLogger(__name__)

# Constants to avoid duplicate literals
INVITATION_NOT_FOUND_MSG = "Invitation not found"


class InvitationError(Exception):
    """Raised when invitation operations fail"""

    pass


class InvitationService:
    """Service for managing user invitations"""

    INVITATION_EXPIRY_DAYS = 7

    @staticmethod
    def create_invitation(
        inviter_user_id: str,
        inviter_email: str,
        invitee_email: str,
        invitee_role: str,
        institution_id: str,
        program_ids: Optional[List[str]] = None,
        personal_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new user invitation

        Args:
            inviter_user_id: ID of user sending the invitation
            inviter_email: Email of user sending the invitation
            invitee_email: Email address to invite
            invitee_role: Role to assign (instructor, program_admin, institution_admin)
            institution_id: Institution the invitee will belong to
            program_ids: Optional list of program IDs for program_admin role
            personal_message: Optional personal message from inviter

        Returns:
            Dictionary containing invitation details

        Raises:
            InvitationError: If invitation creation fails
        """
        try:
            # Validate role using new UserRole enum
            valid_roles = [role.value for role in UserRole]
            if invitee_role not in valid_roles:
                raise InvitationError(
                    f"Invalid role: {invitee_role}. Valid roles: {valid_roles}"
                )

            # Check if user already exists
            existing_user = db.get_user_by_email(invitee_email)
            if existing_user:
                raise InvitationError(f"User with email {invitee_email} already exists")

            # Check for existing pending invitation
            existing_invitation = db.get_invitation_by_email(
                invitee_email, institution_id
            )
            if existing_invitation and existing_invitation.get("status") == "pending":
                raise InvitationError(
                    f"Pending invitation already exists for {invitee_email}"
                )

            # Get inviter's full name for display
            inviter = db.get_user_by_id(inviter_user_id)
            inviter_name = (
                f"{inviter['first_name']} {inviter['last_name']}"
                if inviter and inviter.get("first_name")
                else inviter_email
            )

            # Get institution name for display
            institution = db.get_institution_by_id(institution_id)
            institution_name = (
                institution["name"] if institution else "Unknown Institution"
            )

            # Generate secure invitation token
            invitation_token = secrets.token_urlsafe(32)

            # Create invitation data using the correct UserInvitation schema
            # Note: expiry is handled internally by UserInvitation.create_schema via expires_days
            invitation_data = UserInvitation.create_schema(
                email=invitee_email,
                role=invitee_role,
                institution_id=institution_id,
                invited_by=inviter_user_id,
                personal_message=personal_message,
                expires_days=InvitationService.INVITATION_EXPIRY_DAYS,
            )

            # Add additional fields needed by invitation service
            # These are stored in the 'extras' JSON field for easy access
            invitation_data.update(
                {
                    "inviter_email": inviter_email,
                    "inviter_name": inviter_name,
                    "institution_name": institution_name,
                    "program_ids": program_ids or [],
                    "token": invitation_token,  # Override the auto-generated token
                }
            )

            # Save invitation to database
            invitation_id = db.create_invitation(invitation_data)
            if not invitation_id:
                raise InvitationError("Failed to save invitation to database")

            invitation_data["id"] = invitation_id

            logger.info(
                f"[Invitation Service] Created invitation {invitation_id} for {invitee_email}"
            )
            return invitation_data

        except Exception as e:
            logger.error(
                f"[Invitation Service] Failed to create invitation for {invitee_email}: {str(e)}"
            )
            raise InvitationError(f"Failed to create invitation: {str(e)}")

    @staticmethod
    def send_invitation(invitation_data: Dict[str, Any]) -> bool:
        """
        Send invitation email to invitee

        Args:
            invitation_data: Invitation details from create_invitation

        Returns:
            True if email sent successfully, False otherwise

        Raises:
            InvitationError: If email sending fails
        """
        try:
            # Send invitation email with inviter and institution information
            success = EmailService.send_invitation_email(
                email=invitation_data["email"],
                invitation_token=invitation_data["token"],
                inviter_name=invitation_data.get(
                    "inviter_name", invitation_data.get("inviter_email", "A colleague")
                ),
                institution_name=invitation_data.get(
                    "institution_name", "your institution"
                ),
                role=invitation_data["role"],
                personal_message=invitation_data.get("personal_message"),
            )

            if success:
                # Update invitation status to sent
                db.update_invitation(
                    invitation_data["id"],
                    {
                        "status": "sent",
                        "sent_at": datetime.now(timezone.utc).isoformat(),
                    },
                )

                logger.info(
                    f"[Invitation Service] Sent invitation email to {invitation_data['email']}"
                )
                return True
            else:
                logger.error(
                    f"[Invitation Service] Failed to send invitation email to {invitation_data['email']}"
                )
                return False

        except Exception as e:
            logger.error(
                f"[Invitation Service] Error sending invitation email: {str(e)}"
            )
            raise InvitationError(f"Failed to send invitation email: {str(e)}")

    @staticmethod
    def accept_invitation(
        invitation_token: str, password: str, display_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Accept an invitation and create user account

        Args:
            invitation_token: Secure invitation token
            password: Password for new user account
            display_name: Optional display name for user

        Returns:
            Dictionary containing new user details

        Raises:
            InvitationError: If invitation acceptance fails
        """
        try:
            # Validate invitation and check expiry
            invitation = InvitationService._validate_invitation_for_acceptance(
                invitation_token
            )

            # Prepare password
            password_hash = InvitationService._prepare_password(password)

            # Create user account
            user_data = InvitationService._create_user_from_invitation(
                invitation, password_hash, display_name
            )

            # Save user and update invitation
            user_id = InvitationService._finalize_invitation_acceptance(
                invitation, user_data
            )
            user_data["id"] = user_id

            # Send welcome email
            InvitationService._send_welcome_email(invitation, display_name)

            logger.info(
                f"[Invitation Service] Accepted invitation for {invitation['email']}, created user {user_id}"
            )
            return user_data

        except Exception as e:
            logger.error("[Invitation Service] Failed to accept invitation: %s", str(e))
            raise InvitationError(f"Failed to accept invitation: {str(e)}")

    @staticmethod
    def _validate_invitation_for_acceptance(invitation_token: str) -> Dict[str, Any]:
        """Validate invitation token and check status and expiry."""
        # Get invitation by token
        invitation = db.get_invitation_by_token(invitation_token)
        if not invitation:
            raise InvitationError("Invalid invitation token")

        # Check invitation status
        if invitation["status"] != "sent":
            if invitation["status"] == "accepted":
                raise InvitationError("Invitation has already been accepted")
            elif invitation["status"] == "expired":
                raise InvitationError("Invitation has expired")
            else:
                raise InvitationError("Invitation is not available for acceptance")

        # Check expiry
        InvitationService._check_and_handle_expiry(invitation)

        return invitation

    @staticmethod
    def _check_and_handle_expiry(invitation: Dict[str, Any]) -> None:
        """Check if invitation has expired and mark it if so."""
        expires_at = datetime.fromisoformat(
            invitation["expires_at"].replace("Z", UTC_OFFSET)
        )
        # Ensure both datetimes are timezone-aware for comparison
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expires_at:
            # Mark as expired
            db.update_invitation(
                invitation["id"],
                {
                    "status": "expired",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            raise InvitationError("Invitation has expired")

    @staticmethod
    def _prepare_password(password: str) -> str:
        """Validate and hash the password."""
        # Validate password strength
        PasswordService.validate_password_strength(password)

        # Hash password
        return PasswordService.hash_password(password)

    @staticmethod
    def _create_user_from_invitation(
        invitation: Dict[str, Any], password_hash: str, display_name: Optional[str]
    ) -> Dict[str, Any]:
        """Create user data from invitation details."""
        first_name, last_name = InvitationService._parse_display_name(
            display_name, invitation["email"]
        )

        user_data = User.create_schema(
            email=invitation["email"],
            first_name=first_name,
            last_name=last_name,
            password_hash=password_hash,
            role=invitation["role"],
            institution_id=invitation["institution_id"],
            program_ids=invitation.get("program_ids", []),
            display_name=display_name or invitation["email"].split("@")[0],
            account_status="active",  # Immediately active since invited
        )

        # Add additional fields not handled by create_schema
        user_data.update(
            {
                "email_verified": True,  # Email verified through invitation process
                "invited_by": invitation["invited_by"],
            }
        )

        return user_data

    @staticmethod
    def _parse_display_name(display_name: Optional[str], email: str) -> tuple:
        """Parse display name into first and last name components."""
        if display_name and " " in display_name:
            parts = display_name.split(" ")
            return parts[0], parts[-1]
        else:
            return display_name or email.split("@")[0], ""

    @staticmethod
    def _finalize_invitation_acceptance(
        invitation: Dict[str, Any], user_data: Dict[str, Any]
    ) -> str:
        """Save user to database and update invitation status."""
        # Save user to database
        user_id = db.create_user(user_data)
        if not user_id:
            raise InvitationError("Failed to create user account")

        # Update invitation status
        db.update_invitation(
            invitation["id"],
            {
                "status": "accepted",
                "accepted_at": datetime.now(timezone.utc),
                "accepted_by_user_id": user_id,
                "updated_at": datetime.now(timezone.utc),
            },
        )

        return user_id

    @staticmethod
    def _send_welcome_email(
        invitation: Dict[str, Any], display_name: Optional[str]
    ) -> None:
        """Send welcome email to newly created user."""
        institution = db.get_institution_by_id(invitation["institution_id"])
        if institution:
            EmailService.send_welcome_email(
                email=invitation["email"],
                user_name=display_name or invitation["email"].split("@")[0],
                institution_name=institution["name"],
            )

    @staticmethod
    def resend_invitation(invitation_id: str) -> bool:
        """
        Resend an existing invitation

        Args:
            invitation_id: ID of invitation to resend

        Returns:
            True if resent successfully, False otherwise

        Raises:
            InvitationError: If resending fails
        """
        try:
            # Get invitation
            invitation = db.get_invitation_by_id(invitation_id)
            if not invitation:
                raise InvitationError(INVITATION_NOT_FOUND_MSG)

            # Check if invitation can be resent
            if invitation["status"] not in ["pending", "sent"]:
                raise InvitationError(
                    f"Cannot resend invitation with status: {invitation['status']}"
                )

            # Check if expired and extend if needed
            expires_at = datetime.fromisoformat(
                invitation["expires_at"].replace("Z", UTC_OFFSET)
            )
            # Ensure both datetimes are timezone-aware for comparison
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                # Extend expiry
                new_expires_at = datetime.now(timezone.utc) + timedelta(
                    days=InvitationService.INVITATION_EXPIRY_DAYS
                )
                db.update_invitation(
                    invitation_id,
                    {
                        "expires_at": new_expires_at.isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                invitation["expires_at"] = new_expires_at.isoformat()

            # Resend email
            return InvitationService.send_invitation(invitation)

        except Exception as e:
            logger.error(
                f"[Invitation Service] Failed to resend invitation {invitation_id}: {str(e)}"
            )
            raise InvitationError(f"Failed to resend invitation: {str(e)}")

    @staticmethod
    def get_invitation_status(invitation_token: str) -> Dict[str, Any]:
        """
        Get invitation status by token

        Args:
            invitation_token: Invitation token

        Returns:
            Dictionary containing invitation status info

        Raises:
            InvitationError: If invitation not found
        """
        try:
            invitation = db.get_invitation_by_token(invitation_token)
            if not invitation:
                raise InvitationError(INVITATION_NOT_FOUND_MSG)

            # Check if expired
            expires_at = datetime.fromisoformat(
                invitation["expires_at"].replace("Z", UTC_OFFSET)
            )
            # Ensure both datetimes are timezone-aware for comparison
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            is_expired = datetime.now(timezone.utc) > expires_at

            if is_expired and invitation["status"] not in ["accepted", "expired"]:
                # Mark as expired
                db.update_invitation(
                    invitation["id"],
                    {
                        "status": "expired",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                invitation["status"] = "expired"

            return {
                "status": invitation["status"],
                "invitee_email": invitation["email"],
                "invitee_role": invitation["role"],
                "expires_at": invitation["expires_at"],
                "is_expired": is_expired,
                "created_at": invitation.get(
                    "invited_at", invitation.get("created_at")
                ),
                # Include invitation metadata for display
                "inviter_name": invitation.get("inviter_name"),
                "inviter_email": invitation.get("inviter_email"),
                "institution_name": invitation.get("institution_name"),
                "personal_message": invitation.get("personal_message"),
                "program_ids": invitation.get("program_ids", []),
            }

        except Exception as e:
            logger.error(
                f"[Invitation Service] Failed to get invitation status: {str(e)}"
            )
            raise InvitationError(f"Failed to get invitation status: {str(e)}")

    @staticmethod
    def list_invitations(
        institution_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List invitations for an institution

        Args:
            institution_id: Institution ID to list invitations for
            status: Optional status filter
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of invitation dictionaries
        """
        try:
            return db.list_invitations(institution_id, status, limit, offset)

        except Exception as e:
            logger.error(f"[Invitation Service] Failed to list invitations: {str(e)}")
            raise InvitationError(f"Failed to list invitations: {str(e)}")

    @staticmethod
    def cancel_invitation(invitation_id: str) -> bool:
        """
        Cancel a pending invitation

        Args:
            invitation_id: ID of invitation to cancel

        Returns:
            True if cancelled successfully

        Raises:
            InvitationError: If cancellation fails
        """
        try:
            invitation = db.get_invitation_by_id(invitation_id)
            if not invitation:
                raise InvitationError(INVITATION_NOT_FOUND_MSG)

            if invitation["status"] not in ["pending", "sent"]:
                raise InvitationError(
                    f"Cannot cancel invitation with status: {invitation['status']}"
                )

            # Update status to cancelled
            success = db.update_invitation(
                invitation_id,
                {
                    "status": "cancelled",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            if success:
                logger.info(
                    f"[Invitation Service] Cancelled invitation {invitation_id}"
                )
                return True
            else:
                raise InvitationError("Failed to update invitation status")

        except Exception as e:
            logger.error(
                f"[Invitation Service] Failed to cancel invitation {invitation_id}: {str(e)}"
            )
            raise InvitationError(f"Failed to cancel invitation: {str(e)}")
