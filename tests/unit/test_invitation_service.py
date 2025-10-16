"""
Unit tests for invitation_service.py

Tests the InvitationService class and its methods for user invitation functionality.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest

from invitation_service import InvitationError, InvitationService


class TestInvitationServiceCreation:
    """Test invitation creation functionality"""

    @patch("invitation_service.db")
    @patch("invitation_service.secrets.token_urlsafe")
    def test_create_invitation_success(self, mock_token, mock_db):
        """Test successful invitation creation"""
        # Setup
        mock_token.return_value = "secure-token-123"
        mock_db.get_user_by_email.return_value = None  # No existing user
        mock_db.get_invitation_by_email.return_value = None  # No existing invitation
        mock_db.create_invitation.return_value = "inv-123"

        # Execute
        result = InvitationService.create_invitation(
            inviter_user_id="user-123",
            inviter_email="admin@mocku.test",
            invitee_email="instructor@example.com",
            invitee_role="instructor",
            institution_id="inst-123",
        )

        # Verify
        assert result["id"] == "inv-123"
        assert result["email"] == "instructor@example.com"
        assert result["role"] == "instructor"
        assert result["token"] == "secure-token-123"
        assert result["institution_id"] == "inst-123"

        mock_db.create_invitation.assert_called_once()
        invitation_data = mock_db.create_invitation.call_args[0][0]
        assert invitation_data["invited_by"] == "user-123"
        assert invitation_data["email"] == "instructor@example.com"

    @patch("invitation_service.db")
    def test_create_invitation_invalid_role(self, mock_db):
        """Test invitation creation with invalid role"""
        # Execute & Verify
        with pytest.raises(InvitationError, match="Invalid role"):
            InvitationService.create_invitation(
                inviter_user_id="user-123",
                inviter_email="admin@mocku.test",
                invitee_email="instructor@example.com",
                invitee_role="invalid_role",
                institution_id="inst-123",
            )

    @patch("invitation_service.db")
    def test_create_invitation_user_exists(self, mock_db):
        """Test invitation creation when user already exists"""
        # Setup
        mock_db.get_user_by_email.return_value = {"id": "existing-user"}

        # Execute & Verify
        with pytest.raises(InvitationError, match="already exists"):
            InvitationService.create_invitation(
                inviter_user_id="user-123",
                inviter_email="admin@mocku.test",
                invitee_email="existing@example.com",
                invitee_role="instructor",
                institution_id="inst-123",
            )

    @patch("invitation_service.db")
    def test_create_invitation_pending_exists(self, mock_db):
        """Test invitation creation when pending invitation exists"""
        # Setup
        mock_db.get_user_by_email.return_value = None
        mock_db.get_invitation_by_email.return_value = {"status": "pending"}

        # Execute & Verify
        with pytest.raises(InvitationError, match="Pending invitation already exists"):
            InvitationService.create_invitation(
                inviter_user_id="user-123",
                inviter_email="admin@mocku.test",
                invitee_email="instructor@example.com",
                invitee_role="instructor",
                institution_id="inst-123",
            )

    @patch("invitation_service.db")
    def test_create_invitation_with_program_ids(self, mock_db):
        """Test invitation creation with program IDs"""
        # Setup
        mock_db.get_user_by_email.return_value = None
        mock_db.get_invitation_by_email.return_value = None
        mock_db.create_invitation.return_value = "inv-123"

        # Execute
        result = InvitationService.create_invitation(
            inviter_user_id="user-123",
            inviter_email="admin@mocku.test",
            invitee_email="instructor@example.com",
            invitee_role="program_admin",
            institution_id="inst-123",
            program_ids=["prog-1", "prog-2"],
            personal_message="Welcome to the team!",
        )

        # Verify
        invitation_data = mock_db.create_invitation.call_args[0][0]
        assert invitation_data["program_ids"] == ["prog-1", "prog-2"]
        assert invitation_data["personal_message"] == "Welcome to the team!"

    @patch("invitation_service.db")
    def test_create_invitation_database_failure(self, mock_db):
        """Test invitation creation with database failure"""
        # Setup
        mock_db.get_user_by_email.return_value = None
        mock_db.get_invitation_by_email.return_value = None
        mock_db.create_invitation.return_value = None  # Database failure

        # Execute & Verify
        with pytest.raises(InvitationError, match="Failed to save invitation"):
            InvitationService.create_invitation(
                inviter_user_id="user-123",
                inviter_email="admin@mocku.test",
                invitee_email="instructor@example.com",
                invitee_role="instructor",
                institution_id="inst-123",
            )


class TestInvitationServiceEmail:
    """Test invitation email functionality"""

    @patch("invitation_service.EmailService")
    @patch("invitation_service.db")
    def test_send_invitation_success(self, mock_db, mock_email_service):
        """Test successful invitation email sending"""
        # Setup
        mock_db.get_institution_by_id.return_value = {"name": "Test Institution"}
        mock_email_service.send_invitation_email.return_value = True
        mock_db.update_invitation.return_value = True

        invitation_data = {
            "id": "inv-123",
            "email": "instructor@example.com",
            "token": "secure-token-123",
            "inviter_email": "admin@mocku.test",
            "role": "instructor",
            "institution_id": "inst-123",
            "expires_at": "2024-01-01T00:00:00",
        }

        # Execute
        result = InvitationService.send_invitation(invitation_data)

        # Verify
        assert result is True
        mock_email_service.send_invitation_email.assert_called_once()
        mock_db.update_invitation.assert_called_once()

        # Check the update call arguments
        update_call = mock_db.update_invitation.call_args[0]
        assert update_call[0] == "inv-123"
        assert update_call[1]["status"] == "sent"
        assert "sent_at" in update_call[1]

    @patch("invitation_service.EmailService")
    @patch("invitation_service.db")
    def test_send_invitation_institution_not_found(self, mock_db, mock_email_service):
        """Test invitation email when institution not found"""
        # Setup
        mock_db.get_institution_by_id.return_value = None

        invitation_data = {"id": "inv-123", "institution_id": "inst-123"}

        # Execute & Verify
        with pytest.raises(InvitationError, match="Institution not found"):
            InvitationService.send_invitation(invitation_data)

    @patch("invitation_service.EmailService")
    @patch("invitation_service.db")
    def test_send_invitation_email_failure(self, mock_db, mock_email_service):
        """Test invitation email sending failure"""
        # Setup
        mock_db.get_institution_by_id.return_value = {"name": "Test Institution"}
        mock_email_service.send_invitation_email.return_value = False

        invitation_data = {
            "id": "inv-123",
            "email": "instructor@example.com",
            "token": "secure-token-123",
            "inviter_email": "admin@mocku.test",
            "role": "instructor",
            "institution_id": "inst-123",
            "expires_at": "2024-01-01T00:00:00",
        }

        # Execute
        result = InvitationService.send_invitation(invitation_data)

        # Verify
        assert result is False
        mock_email_service.send_invitation_email.assert_called_once()
        mock_db.update_invitation.assert_not_called()


class TestInvitationServiceAcceptance:
    """Test invitation acceptance functionality"""

    @patch("invitation_service.EmailService")
    @patch("invitation_service.PasswordService")
    @patch("invitation_service.db")
    def test_accept_invitation_success(
        self, mock_db, mock_password_service, mock_email_service
    ):
        """Test successful invitation acceptance"""
        # Setup
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        invitation = {
            "id": "inv-123",
            "status": "sent",
            "expires_at": future_date.isoformat(),
            "email": "instructor@example.com",
            "role": "instructor",
            "institution_id": "inst-123",
            "invited_by": "admin-123",
            "program_ids": [],
        }

        mock_db.get_invitation_by_token.return_value = invitation
        mock_password_service.validate_password_strength.return_value = None
        mock_password_service.hash_password.return_value = "hashed-password"
        mock_db.create_user.return_value = "user-123"
        mock_db.update_invitation.return_value = True
        mock_db.get_institution_by_id.return_value = {"name": "Test Institution"}
        mock_email_service.send_welcome_email.return_value = True

        # Execute
        result = InvitationService.accept_invitation(
            invitation_token="secure-token-123",
            password="ValidPassword123!",
            display_name="John Doe",
        )

        # Verify
        assert result["id"] == "user-123"
        assert result["email"] == "instructor@example.com"
        assert result["role"] == "instructor"
        assert result["display_name"] == "John Doe"
        assert result["account_status"] == "active"
        assert result["email_verified"] is True

        mock_password_service.validate_password_strength.assert_called_once_with(
            "ValidPassword123!"
        )
        mock_password_service.hash_password.assert_called_once_with("ValidPassword123!")
        mock_db.create_user.assert_called_once()
        mock_db.update_invitation.assert_called_once()
        mock_email_service.send_welcome_email.assert_called_once()

    @patch("invitation_service.db")
    def test_accept_invitation_invalid_token(self, mock_db):
        """Test invitation acceptance with invalid token"""
        # Setup
        mock_db.get_invitation_by_token.return_value = None

        # Execute & Verify
        with pytest.raises(InvitationError, match="Invalid invitation token"):
            InvitationService.accept_invitation("invalid-token", "password123")

    @patch("invitation_service.db")
    def test_accept_invitation_already_accepted(self, mock_db):
        """Test invitation acceptance when already accepted"""
        # Setup
        invitation = {"status": "accepted"}
        mock_db.get_invitation_by_token.return_value = invitation

        # Execute & Verify
        with pytest.raises(InvitationError, match="already been accepted"):
            InvitationService.accept_invitation("token", "password123")

    @patch("invitation_service.db")
    def test_accept_invitation_expired(self, mock_db):
        """Test invitation acceptance when expired"""
        # Setup
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        invitation = {
            "id": "inv-123",
            "status": "sent",
            "expires_at": past_date.isoformat(),
        }
        mock_db.get_invitation_by_token.return_value = invitation
        mock_db.update_invitation.return_value = True

        # Execute & Verify
        with pytest.raises(InvitationError, match="expired"):
            InvitationService.accept_invitation("token", "password123")

        # Verify invitation was marked as expired
        mock_db.update_invitation.assert_called_once()

    @patch("invitation_service.PasswordService")
    @patch("invitation_service.db")
    def test_accept_invitation_weak_password(self, mock_db, mock_password_service):
        """Test invitation acceptance with weak password"""
        # Setup
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        invitation = {"status": "sent", "expires_at": future_date.isoformat()}
        mock_db.get_invitation_by_token.return_value = invitation
        mock_password_service.validate_password_strength.side_effect = Exception(
            "Password too weak"
        )

        # Execute & Verify
        with pytest.raises(InvitationError, match="Password too weak"):
            InvitationService.accept_invitation("token", "weak")

    @patch("invitation_service.PasswordService")
    @patch("invitation_service.db")
    def test_accept_invitation_user_creation_failure(
        self, mock_db, mock_password_service
    ):
        """Test invitation acceptance with user creation failure"""
        # Setup
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        invitation = {
            "id": "inv-123",
            "status": "sent",
            "expires_at": future_date.isoformat(),
            "email": "instructor@example.com",
            "role": "instructor",
            "institution_id": "inst-123",
            "invited_by": "admin-123",
            "program_ids": [],
        }

        mock_db.get_invitation_by_token.return_value = invitation
        mock_password_service.validate_password_strength.return_value = None
        mock_password_service.hash_password.return_value = "hashed-password"
        mock_db.create_user.return_value = None  # User creation failure

        # Execute & Verify
        with pytest.raises(InvitationError, match="Failed to create user account"):
            InvitationService.accept_invitation("token", "ValidPassword123!")

    @patch("invitation_service.db")
    def test_accept_invitation_status_expired(self, mock_db):
        """Test invitation acceptance when status is already 'expired'"""
        # Setup
        invitation = {"status": "expired"}  # Invitation already marked as expired
        mock_db.get_invitation_by_token.return_value = invitation

        # Execute & Verify
        with pytest.raises(InvitationError, match="Invitation has expired"):
            InvitationService.accept_invitation("token", "ValidPassword123!")

    @patch("invitation_service.db")
    def test_accept_invitation_unknown_status(self, mock_db):
        """Test invitation acceptance with unknown/cancelled status"""
        # Setup
        invitation = {
            "status": "cancelled"
        }  # Unknown status other than sent/accepted/expired
        mock_db.get_invitation_by_token.return_value = invitation

        # Execute & Verify
        with pytest.raises(InvitationError, match="not available for acceptance"):
            InvitationService.accept_invitation("token", "ValidPassword123!")


class TestInvitationServiceManagement:
    """Test invitation management functionality"""

    @patch("invitation_service.db")
    def test_resend_invitation_success(self, mock_db):
        """Test successful invitation resending"""
        # Setup
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        invitation = {
            "id": "inv-123",
            "status": "sent",
            "expires_at": future_date.isoformat(),
            "email": "instructor@example.com",
            "token": "secure-token-123",
            "inviter_email": "admin@mocku.test",
            "role": "instructor",
            "institution_id": "inst-123",
        }

        mock_db.get_invitation_by_id.return_value = invitation

        with patch.object(
            InvitationService, "send_invitation", return_value=True
        ) as mock_send:
            # Execute
            result = InvitationService.resend_invitation("inv-123")

            # Verify
            assert result is True
            mock_send.assert_called_once_with(invitation)

    @patch("invitation_service.db")
    def test_resend_invitation_not_found(self, mock_db):
        """Test resending invitation that doesn't exist"""
        # Setup
        mock_db.get_invitation_by_id.return_value = None

        # Execute & Verify
        with pytest.raises(InvitationError, match="not found"):
            InvitationService.resend_invitation("inv-123")

    @patch("invitation_service.db")
    def test_resend_invitation_wrong_status(self, mock_db):
        """Test resending invitation with wrong status"""
        # Setup
        invitation = {"status": "accepted"}
        mock_db.get_invitation_by_id.return_value = invitation

        # Execute & Verify
        with pytest.raises(InvitationError, match="Cannot resend"):
            InvitationService.resend_invitation("inv-123")

    @patch("invitation_service.db")
    def test_resend_invitation_expired_extends_expiry(self, mock_db):
        """Test resending expired invitation extends expiry"""
        # Setup
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        invitation = {
            "id": "inv-123",
            "status": "sent",
            "expires_at": past_date.isoformat(),
            "email": "instructor@example.com",
            "token": "secure-token-123",
            "inviter_email": "admin@mocku.test",
            "role": "instructor",
            "institution_id": "inst-123",
        }

        mock_db.get_invitation_by_id.return_value = invitation
        mock_db.update_invitation.return_value = True

        with patch.object(InvitationService, "send_invitation", return_value=True):
            # Execute
            result = InvitationService.resend_invitation("inv-123")

            # Verify
            assert result is True
            mock_db.update_invitation.assert_called_once()
            update_call = mock_db.update_invitation.call_args[0][1]
            new_expires_at = datetime.fromisoformat(update_call["expires_at"])
            # Make timezone-aware if needed for comparison
            if new_expires_at.tzinfo is None:
                new_expires_at = new_expires_at.replace(tzinfo=timezone.utc)
            assert new_expires_at > datetime.now(timezone.utc)

    @patch("invitation_service.db")
    def test_get_invitation_status_success(self, mock_db):
        """Test getting invitation status"""
        # Setup
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        invitation = {
            "id": "inv-123",
            "status": "sent",
            "email": "instructor@example.com",
            "role": "instructor",
            "expires_at": future_date.isoformat(),
            "invited_at": "2024-01-01T00:00:00",
        }
        mock_db.get_invitation_by_token.return_value = invitation

        # Execute
        result = InvitationService.get_invitation_status("secure-token-123")

        # Verify
        assert result["status"] == "sent"
        assert result["invitee_email"] == "instructor@example.com"
        assert result["invitee_role"] == "instructor"
        assert result["is_expired"] is False

    @patch("invitation_service.db")
    def test_get_invitation_status_expired(self, mock_db):
        """Test getting status of expired invitation"""
        # Setup
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        invitation = {
            "id": "inv-123",
            "status": "sent",
            "email": "instructor@example.com",
            "role": "instructor",
            "expires_at": past_date.isoformat(),
            "invited_at": "2024-01-01T00:00:00",
        }
        mock_db.get_invitation_by_token.return_value = invitation
        mock_db.update_invitation.return_value = True

        # Execute
        result = InvitationService.get_invitation_status("secure-token-123")

        # Verify
        assert result["status"] == "expired"
        assert result["is_expired"] is True
        mock_db.update_invitation.assert_called_once()

    @patch("invitation_service.db")
    def test_list_invitations_success(self, mock_db):
        """Test listing invitations"""
        # Setup
        invitations = [
            {"id": "inv-1", "status": "sent"},
            {"id": "inv-2", "status": "pending"},
        ]
        mock_db.list_invitations.return_value = invitations

        # Execute
        result = InvitationService.list_invitations(
            institution_id="inst-123", status="sent", limit=10, offset=0
        )

        # Verify
        assert result == invitations
        mock_db.list_invitations.assert_called_once_with("inst-123", "sent", 10, 0)

    @patch("invitation_service.db")
    def test_cancel_invitation_success(self, mock_db):
        """Test successful invitation cancellation"""
        # Setup
        invitation = {"id": "inv-123", "status": "sent"}
        mock_db.get_invitation_by_id.return_value = invitation
        mock_db.update_invitation.return_value = True

        # Execute
        result = InvitationService.cancel_invitation("inv-123")

        # Verify
        assert result is True
        mock_db.update_invitation.assert_called_once()
        update_call = mock_db.update_invitation.call_args[0][1]
        assert update_call["status"] == "cancelled"

    @patch("invitation_service.db")
    def test_cancel_invitation_not_found(self, mock_db):
        """Test cancelling invitation that doesn't exist"""
        # Setup
        mock_db.get_invitation_by_id.return_value = None

        # Execute & Verify
        with pytest.raises(InvitationError, match="not found"):
            InvitationService.cancel_invitation("inv-123")

    @patch("invitation_service.db")
    def test_cancel_invitation_wrong_status(self, mock_db):
        """Test cancelling invitation with wrong status"""
        # Setup
        invitation = {"status": "accepted"}
        mock_db.get_invitation_by_id.return_value = invitation

        # Execute & Verify
        with pytest.raises(InvitationError, match="Cannot cancel"):
            InvitationService.cancel_invitation("inv-123")


class TestInvitationServiceIntegration:
    """Integration tests for invitation service"""

    @patch("invitation_service.EmailService")
    @patch("invitation_service.PasswordService")
    @patch("invitation_service.db")
    def test_complete_invitation_flow(
        self, mock_db, mock_password_service, mock_email_service
    ):
        """Test complete invitation flow from creation to acceptance"""
        # Setup mocks
        mock_db.get_user_by_email.return_value = None
        mock_db.get_invitation_by_email.return_value = None
        mock_db.create_invitation.return_value = "inv-123"
        mock_db.get_institution_by_id.return_value = {"name": "Test Institution"}
        mock_email_service.send_invitation_email.return_value = True
        mock_db.update_invitation.return_value = True

        # Step 1: Create invitation
        invitation = InvitationService.create_invitation(
            inviter_user_id="admin-123",
            inviter_email="admin@mocku.test",
            invitee_email="instructor@example.com",
            invitee_role="instructor",
            institution_id="inst-123",
        )

        assert invitation["id"] == "inv-123"

        # Step 2: Send invitation
        email_sent = InvitationService.send_invitation(invitation)
        assert email_sent is True

        # Step 3: Accept invitation
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        invitation_for_acceptance = {
            "id": "inv-123",
            "status": "sent",
            "expires_at": future_date.isoformat(),
            "email": "instructor@example.com",
            "role": "instructor",
            "institution_id": "inst-123",
            "invited_by": "admin-123",
            "program_ids": [],
        }

        mock_db.get_invitation_by_token.return_value = invitation_for_acceptance
        mock_password_service.validate_password_strength.return_value = None
        mock_password_service.hash_password.return_value = "hashed-password"
        mock_db.create_user.return_value = "user-123"
        mock_email_service.send_welcome_email.return_value = True

        user = InvitationService.accept_invitation(
            invitation_token=invitation["token"],
            password="ValidPassword123!",
            display_name="John Doe",
        )

        assert user["id"] == "user-123"
        assert user["email"] == "instructor@example.com"
        assert user["account_status"] == "active"

        # Verify all database operations occurred
        mock_db.create_invitation.assert_called_once()
        mock_db.create_user.assert_called_once()
        assert mock_db.update_invitation.call_count >= 2  # Status updates

    def test_check_and_handle_expiry_naive_datetime(self):
        """Test _check_and_handle_expiry handles naive datetime by adding timezone."""
        from datetime import datetime
        from unittest.mock import patch

        from invitation_service import InvitationService

        # Create invitation with naive datetime (no timezone)
        naive_datetime = datetime(2099, 1, 1, 0, 0, 0)  # Future date, naive
        invitation = {
            "id": "inv-123",
            "email": "test@example.com",
            "expires_at": naive_datetime.isoformat(),  # Naive ISO string
            "status": "sent",
        }

        with patch("invitation_service.db") as mock_db:
            # Should add timezone to naive datetime (line 271)
            # Won't raise error since future date
            InvitationService._check_and_handle_expiry(invitation)

            # Line 271 was executed to add timezone
            # No exception means success
