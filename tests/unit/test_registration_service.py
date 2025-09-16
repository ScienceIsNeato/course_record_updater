"""
Unit tests for Registration Service

Tests institution admin self-registration, email verification,
and account activation functionality.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from password_service import PasswordValidationError
from registration_service import (
    RegistrationError,
    RegistrationService,
    get_registration_status,
    register_institution_admin,
    resend_verification_email,
    verify_email,
)


class TestInstitutionAdminRegistration:
    """Test institution admin self-registration functionality"""

    @patch("registration_service.db")
    @patch("registration_service.send_verification_email")
    def test_register_institution_admin_success(self, mock_send_email, mock_db):
        """Test successful institution admin registration"""
        # Setup mocks
        mock_db.get_user_by_email.return_value = None  # User doesn't exist
        mock_db.create_institution.return_value = "inst-123"
        mock_db.create_program.return_value = "prog-123"
        mock_db.create_user.return_value = "user-123"
        mock_send_email.return_value = True

        # Test registration
        result = register_institution_admin(
            email="admin@example.com",
            password="SecurePass123!",
            first_name="John",
            last_name="Doe",
            institution_name="Example University",
            website_url="https://example.edu",
        )

        # Verify result
        assert result["success"] is True
        assert "user_id" in result
        assert "institution_id" in result
        assert "program_id" in result
        assert "verification_token" in result
        assert result["email_sent"] is True
        assert "Please check your email" in result["message"]

        # Verify database calls
        mock_db.get_user_by_email.assert_called_once_with("admin@example.com")
        mock_db.create_institution.assert_called_once()
        mock_db.create_program.assert_called_once()
        mock_db.create_user.assert_called_once()

        # Verify email sent
        mock_send_email.assert_called_once()
        args = mock_send_email.call_args[1]
        assert args["email"] == "admin@example.com"
        assert args["user_name"] == "John Doe"

    @patch("registration_service.db")
    def test_register_institution_admin_existing_user(self, mock_db):
        """Test registration fails when user already exists"""
        # Setup mock - user exists
        mock_db.get_user_by_email.return_value = {
            "id": "existing-user",
            "email": "admin@example.com",
        }

        # Test registration
        with pytest.raises(RegistrationError, match="already exists"):
            register_institution_admin(
                email="admin@example.com",
                password="SecurePass123!",
                first_name="John",
                last_name="Doe",
                institution_name="Example University",
            )

    def test_register_institution_admin_weak_password(self):
        """Test registration fails with weak password"""
        with pytest.raises(PasswordValidationError):
            register_institution_admin(
                email="admin@example.com",
                password="weak",
                first_name="John",
                last_name="Doe",
                institution_name="Example University",
            )

    @patch("registration_service.db")
    @patch("registration_service.send_verification_email")
    def test_register_institution_admin_email_failure(self, mock_send_email, mock_db):
        """Test registration succeeds even if email fails"""
        # Setup mocks
        mock_db.get_user_by_email.return_value = None
        mock_db.create_institution.return_value = "inst-123"
        mock_db.create_program.return_value = "prog-123"
        mock_db.create_user.return_value = "user-123"
        mock_send_email.return_value = False  # Email fails

        # Test registration
        result = register_institution_admin(
            email="admin@example.com",
            password="SecurePass123!",
            first_name="John",
            last_name="Doe",
            institution_name="Example University",
        )

        # Should still succeed but indicate email failure
        assert result["success"] is True
        assert result["email_sent"] is False

    @patch("registration_service.db")
    def test_register_institution_admin_database_error(self, mock_db):
        """Test registration fails on database error"""
        # Setup mock - database error
        mock_db.get_user_by_email.return_value = None
        mock_db.create_institution.side_effect = Exception("Database error")

        # Test registration
        with pytest.raises(RegistrationError, match="Registration failed"):
            register_institution_admin(
                email="admin@example.com",
                password="SecurePass123!",
                first_name="John",
                last_name="Doe",
                institution_name="Example University",
            )


class TestEmailVerification:
    """Test email verification functionality"""

    @patch("registration_service.db")
    @patch("registration_service.send_welcome_email")
    def test_verify_email_success(self, mock_send_welcome, mock_db):
        """Test successful email verification"""
        # Setup mocks
        future_time = datetime.now(timezone.utc) + timedelta(hours=12)
        mock_user = {
            "id": "user-123",
            "email": "admin@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "institution_id": "inst-123",
            "account_status": "pending",
            "email_verification_expires_at": future_time,
        }
        mock_institution = {"name": "Example University"}

        mock_db.get_user_by_verification_token.return_value = mock_user
        mock_db.get_institution_by_id.return_value = mock_institution
        mock_db.update_user.return_value = True
        mock_send_welcome.return_value = True

        # Test verification
        result = verify_email("valid-token")

        # Verify result
        assert result["success"] is True
        assert result["already_verified"] is False
        assert result["user_id"] == "user-123"
        assert result["email"] == "admin@example.com"
        assert result["display_name"] == "John Doe"
        assert result["institution_name"] == "Example University"
        assert result["welcome_email_sent"] is True
        assert "verified successfully" in result["message"]

        # Verify database calls
        mock_db.get_user_by_verification_token.assert_called_once_with("valid-token")
        mock_db.update_user.assert_called_once()

        # Verify user update
        update_call = mock_db.update_user.call_args
        assert update_call[0][0] == "user-123"  # user_id
        updates = update_call[0][1]  # updates dict
        assert updates["account_status"] == "active"
        assert updates["email_verified"] is True
        assert updates["email_verification_token"] is None

    @patch("registration_service.db")
    def test_verify_email_invalid_token(self, mock_db):
        """Test verification with invalid token"""
        mock_db.get_user_by_verification_token.return_value = None

        with pytest.raises(RegistrationError, match="Invalid verification token"):
            verify_email("invalid-token")

    @patch("registration_service.db")
    def test_verify_email_expired_token(self, mock_db):
        """Test verification with expired token"""
        # Setup mock with expired token
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_user = {
            "id": "user-123",
            "email": "admin@example.com",
            "account_status": "pending",
            "email_verification_expires_at": past_time,
        }

        mock_db.get_user_by_verification_token.return_value = mock_user

        with pytest.raises(RegistrationError, match="expired"):
            verify_email("expired-token")

    @patch("registration_service.db")
    def test_verify_email_already_verified(self, mock_db):
        """Test verification when already verified"""
        # Setup mock with active user
        future_time = datetime.now(timezone.utc) + timedelta(hours=12)
        mock_user = {
            "id": "user-123",
            "email": "admin@example.com",
            "account_status": "active",
            "email_verification_expires_at": future_time,
        }

        mock_db.get_user_by_verification_token.return_value = mock_user

        result = verify_email("already-verified-token")

        assert result["success"] is True
        assert result["already_verified"] is True
        assert "already verified" in result["message"]

    @patch("registration_service.db")
    def test_verify_email_iso_string_expiry(self, mock_db):
        """Test verification with ISO string expiry date"""
        # Setup mock with ISO string expiry
        future_time = datetime.now(timezone.utc) + timedelta(hours=12)
        mock_user = {
            "id": "user-123",
            "email": "admin@example.com",
            "institution_id": "inst-123",
            "account_status": "pending",
            "email_verification_expires_at": future_time.isoformat(),
        }
        mock_institution = {"name": "Example University"}

        mock_db.get_user_by_verification_token.return_value = mock_user
        mock_db.get_institution_by_id.return_value = mock_institution
        mock_db.update_user.return_value = True

        with patch("registration_service.send_welcome_email") as mock_welcome:
            mock_welcome.return_value = True

            result = verify_email("iso-token")

            assert result["success"] is True
            assert result["already_verified"] is False


class TestResendVerificationEmail:
    """Test resending verification email functionality"""

    @patch("registration_service.db")
    @patch("registration_service.send_verification_email")
    def test_resend_verification_email_success(self, mock_send_email, mock_db):
        """Test successful resend of verification email"""
        # Setup mocks
        mock_user = {
            "id": "user-123",
            "email": "admin@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "account_status": "pending",
        }

        mock_db.get_user_by_email.return_value = mock_user
        mock_db.update_user.return_value = True
        mock_send_email.return_value = True

        # Test resend
        result = resend_verification_email("admin@example.com")

        # Verify result
        assert result["success"] is True
        assert result["email_sent"] is True
        assert "verification_expires_at" in result
        assert "Verification email sent" in result["message"]

        # Verify database calls
        mock_db.get_user_by_email.assert_called_once_with("admin@example.com")
        mock_db.update_user.assert_called_once()

        # Verify email sent
        mock_send_email.assert_called_once()

    @patch("registration_service.db")
    def test_resend_verification_email_user_not_found(self, mock_db):
        """Test resend when user doesn't exist"""
        mock_db.get_user_by_email.return_value = None

        with pytest.raises(RegistrationError, match="No account found"):
            resend_verification_email("nonexistent@example.com")

    @patch("registration_service.db")
    def test_resend_verification_email_already_active(self, mock_db):
        """Test resend when account is already active"""
        mock_user = {
            "id": "user-123",
            "email": "admin@example.com",
            "account_status": "active",
        }

        mock_db.get_user_by_email.return_value = mock_user

        with pytest.raises(RegistrationError, match="already verified"):
            resend_verification_email("admin@example.com")


class TestRegistrationStatus:
    """Test registration status checking functionality"""

    @patch("registration_service.db")
    def test_get_registration_status_not_registered(self, mock_db):
        """Test status check for non-existent user"""
        mock_db.get_user_by_email.return_value = None

        result = get_registration_status("nonexistent@example.com")

        assert result["exists"] is False
        assert result["status"] == "not_registered"
        assert "No account found" in result["message"]

    @patch("registration_service.db")
    def test_get_registration_status_active(self, mock_db):
        """Test status check for active user"""
        mock_user = {
            "id": "user-123",
            "email": "admin@example.com",
            "account_status": "active",
            "email_verified": True,
            "role": "institution_admin",
            "institution_id": "inst-123",
        }

        mock_db.get_user_by_email.return_value = mock_user

        result = get_registration_status("admin@example.com")

        assert result["exists"] is True
        assert result["status"] == "active"
        assert result["user_id"] == "user-123"
        assert result["role"] == "institution_admin"
        assert result["institution_id"] == "inst-123"
        assert "active and verified" in result["message"]

    @patch("registration_service.db")
    def test_get_registration_status_pending_not_expired(self, mock_db):
        """Test status check for pending user with valid token"""
        future_time = datetime.now(timezone.utc) + timedelta(hours=12)
        mock_user = {
            "id": "user-123",
            "email": "admin@example.com",
            "account_status": "pending",
            "email_verified": False,
            "email_verification_expires_at": future_time,
        }

        mock_db.get_user_by_email.return_value = mock_user

        result = get_registration_status("admin@example.com")

        assert result["exists"] is True
        assert result["status"] == "pending_verification"
        assert result["user_id"] == "user-123"
        assert result["email_verified"] is False
        assert result["verification_expired"] is False
        assert "verification is pending" in result["message"]

    @patch("registration_service.db")
    def test_get_registration_status_pending_expired(self, mock_db):
        """Test status check for pending user with expired token"""
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_user = {
            "id": "user-123",
            "email": "admin@example.com",
            "account_status": "pending",
            "email_verified": False,
            "email_verification_expires_at": past_time,
        }

        mock_db.get_user_by_email.return_value = mock_user

        result = get_registration_status("admin@example.com")

        assert result["exists"] is True
        assert result["status"] == "pending_verification"
        assert result["verification_expired"] is True

    @patch("registration_service.db")
    def test_get_registration_status_database_error(self, mock_db):
        """Test status check with database error"""
        mock_db.get_user_by_email.side_effect = Exception("Database error")

        result = get_registration_status("admin@example.com")

        assert result["exists"] is False
        assert result["status"] == "error"
        assert "Failed to check" in result["message"]


class TestRegistrationServiceIntegration:
    """Integration tests for registration service"""

    @patch("registration_service.db")
    @patch("registration_service.send_verification_email")
    @patch("registration_service.send_welcome_email")
    def test_complete_registration_flow(self, mock_welcome, mock_verify_email, mock_db):
        """Test complete registration and verification flow"""
        # Setup mocks for registration
        mock_db.get_user_by_email.return_value = None
        mock_db.create_institution.return_value = "inst-123"
        mock_db.create_program.return_value = "prog-123"
        mock_db.create_user.return_value = "user-123"
        mock_verify_email.return_value = True

        # Test registration
        reg_result = register_institution_admin(
            email="admin@example.com",
            password="SecurePass123!",
            first_name="John",
            last_name="Doe",
            institution_name="Example University",
        )

        assert reg_result["success"] is True
        verification_token = reg_result["verification_token"]

        # Setup mocks for verification
        future_time = datetime.now(timezone.utc) + timedelta(hours=12)
        mock_user = {
            "id": "user-123",
            "email": "admin@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "institution_id": "inst-123",
            "account_status": "pending",
            "email_verification_expires_at": future_time,
        }
        mock_institution = {"name": "Example University"}

        mock_db.get_user_by_verification_token.return_value = mock_user
        mock_db.get_institution_by_id.return_value = mock_institution
        mock_db.update_user.return_value = True
        mock_welcome.return_value = True

        # Test verification
        verify_result = verify_email(verification_token)

        assert verify_result["success"] is True
        assert verify_result["user_id"] == "user-123"
        assert verify_result["welcome_email_sent"] is True


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_convenience_functions_exist(self):
        """Test that all convenience functions are available"""
        assert callable(register_institution_admin)
        assert callable(verify_email)
        assert callable(resend_verification_email)
        assert callable(get_registration_status)

    @patch("registration_service.RegistrationService.register_institution_admin")
    def test_convenience_function_register_institution_admin(self, mock_method):
        """Test convenience function delegates correctly"""
        mock_method.return_value = {"success": True}

        result = register_institution_admin(
            "admin@example.com", "pass", "John", "Doe", "University"
        )

        assert result["success"] is True
        mock_method.assert_called_once_with(
            "admin@example.com", "pass", "John", "Doe", "University", None
        )
