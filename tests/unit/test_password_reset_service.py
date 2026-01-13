"""
Unit tests for password_reset_service.py

Tests the PasswordResetService class and its methods for password reset functionality.
"""

from unittest.mock import patch

import pytest

from src.services.email_service import EmailServiceError
from src.services.password_reset_service import PasswordResetError, PasswordResetService
from src.services.password_service import PasswordValidationError


class TestPasswordResetServiceRequest:
    """Test password reset request functionality"""

    @patch("src.services.password_reset_service.EmailService")
    @patch("src.services.password_reset_service.PasswordService")
    @patch("src.services.password_reset_service.db")
    def test_request_password_reset_success(
        self, mock_db, mock_password_service, mock_email_service
    ):
        """Test successful password reset request"""
        # Setup
        mock_password_service.check_rate_limit.return_value = None
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "account_status": "active",
            "display_name": "Test User",
        }
        mock_password_service.generate_reset_token.return_value = "secure-token"
        mock_password_service.create_reset_token_data.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "expires_at": "2024-01-01T14:00:00",
        }
        mock_db.update_user.return_value = True
        mock_email_service.send_password_reset_email.return_value = True

        # Execute
        result = PasswordResetService.request_password_reset("test@example.com")

        # Verify
        assert result["request_success"] is True
        assert "If an account with this email exists" in result["message"]
        mock_password_service.check_rate_limit.assert_called_once_with(
            "test@example.com"
        )
        mock_db.get_user_by_email.assert_called_once_with("test@example.com")
        mock_db.update_user.assert_called_once()
        mock_email_service.send_password_reset_email.assert_called_once()

    @patch("src.services.password_reset_service.PasswordService")
    @patch("src.services.password_reset_service.db")
    def test_request_password_reset_nonexistent_user(
        self, mock_db, mock_password_service
    ):
        """Test password reset request for non-existent user"""
        # Setup
        mock_password_service.check_rate_limit.return_value = None
        mock_db.get_user_by_email.return_value = None

        # Execute
        result = PasswordResetService.request_password_reset("nonexistent@example.com")

        # Verify - should still return success for security
        assert result["request_success"] is True
        assert "If an account with this email exists" in result["message"]

    @patch("src.services.password_reset_service.PasswordService")
    @patch("src.services.password_reset_service.db")
    def test_request_password_reset_pending_account(
        self, mock_db, mock_password_service
    ):
        """Test password reset request for pending account"""
        # Setup
        mock_password_service.check_rate_limit.return_value = None
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "account_status": "pending",
        }

        # Execute & Verify
        with pytest.raises(PasswordResetError, match="Account is pending activation"):
            PasswordResetService.request_password_reset("test@example.com")

    @patch("src.services.password_reset_service.PasswordService")
    def test_request_password_reset_rate_limit_exceeded(self, mock_password_service):
        """Test password reset request when rate limit exceeded"""
        # Setup
        mock_password_service.check_rate_limit.side_effect = Exception(
            "Rate limit exceeded"
        )

        # Execute & Verify
        with pytest.raises(
            PasswordResetError, match="Too many password reset requests"
        ):
            PasswordResetService.request_password_reset("test@example.com")

    @patch("src.services.password_reset_service.EmailService")
    @patch("src.services.password_reset_service.PasswordService")
    @patch("src.services.password_reset_service.db")
    def test_request_password_reset_email_service_error(
        self, mock_db, mock_password_service, mock_email_service
    ):
        """Test password reset request with email service error"""
        # Setup
        mock_password_service.check_rate_limit.return_value = None
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@mocku.test",
            "account_status": "active",
        }
        mock_password_service.generate_reset_token.return_value = "secure-token"
        mock_password_service.create_reset_token_data.return_value = {
            "expires_at": "2024-01-01T14:00:00"
        }
        mock_db.update_user.return_value = True
        mock_email_service.send_password_reset_email.side_effect = EmailServiceError(
            "Cannot send emails to protected domain"
        )

        # Execute & Verify
        with pytest.raises(PasswordResetError, match="Email sending is restricted"):
            PasswordResetService.request_password_reset("test@mocku.test")

    @patch("src.services.password_reset_service.EmailService")
    @patch("src.services.password_reset_service.PasswordService")
    @patch("src.services.password_reset_service.db")
    @patch(
        "src.services.password_reset_service.PasswordResetService._check_reset_rate_limit"
    )
    def test_request_password_reset_suspended_account(
        self, mock_rate_limit, mock_db, mock_password_service, mock_email_service
    ):
        """Test password reset request for suspended account"""
        # Setup
        mock_rate_limit.return_value = None
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "account_status": "suspended",
        }

        # Execute & Verify
        with pytest.raises(PasswordResetError) as exc_info:
            PasswordResetService.request_password_reset("test@example.com")

        assert "Account is suspended" in str(exc_info.value)
        mock_rate_limit.assert_called_once_with("test@example.com")
        mock_db.get_user_by_email.assert_called_once_with("test@example.com")
        mock_password_service.generate_password_reset_token.assert_not_called()
        mock_email_service.send_password_reset_email.assert_not_called()

    @patch("src.services.password_reset_service.EmailService")
    @patch("src.services.password_reset_service.PasswordService")
    @patch("src.services.password_reset_service.db")
    @patch(
        "src.services.password_reset_service.PasswordResetService._check_reset_rate_limit"
    )
    def test_request_password_reset_deactivated_account(
        self, mock_rate_limit, mock_db, mock_password_service, mock_email_service
    ):
        """Test password reset request for deactivated account"""
        # Setup
        mock_rate_limit.return_value = None
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "account_status": "deactivated",
        }

        # Execute & Verify
        with pytest.raises(PasswordResetError) as exc_info:
            PasswordResetService.request_password_reset("test@example.com")

        assert "Account is deactivated" in str(exc_info.value)
        mock_rate_limit.assert_called_once_with("test@example.com")
        mock_db.get_user_by_email.assert_called_once_with("test@example.com")
        mock_password_service.generate_password_reset_token.assert_not_called()
        mock_email_service.send_password_reset_email.assert_not_called()

    @patch("src.services.password_reset_service.EmailService")
    @patch("src.services.password_reset_service.PasswordService")
    @patch("src.services.password_reset_service.db")
    @patch(
        "src.services.password_reset_service.PasswordResetService._check_reset_rate_limit"
    )
    def test_request_password_reset_unknown_account_status(
        self, mock_rate_limit, mock_db, mock_password_service, mock_email_service
    ):
        """Test password reset request for unknown account status"""
        # Setup
        mock_rate_limit.return_value = None
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "account_status": "unknown_status",
        }

        # Execute & Verify
        with pytest.raises(PasswordResetError) as exc_info:
            PasswordResetService.request_password_reset("test@example.com")

        assert "Account is not available for password reset" in str(exc_info.value)
        mock_rate_limit.assert_called_once_with("test@example.com")
        mock_db.get_user_by_email.assert_called_once_with("test@example.com")
        mock_password_service.generate_password_reset_token.assert_not_called()
        mock_email_service.send_password_reset_email.assert_not_called()


class TestPasswordResetServiceReset:
    """Test password reset completion functionality"""

    @patch("src.services.password_reset_service.EmailService")
    @patch("src.services.password_reset_service.PasswordService")
    @patch("src.services.password_reset_service.db")
    def test_reset_password_success(
        self, mock_db, mock_password_service, mock_email_service
    ):
        """Test successful password reset"""
        # Setup
        mock_password_service.validate_password_strength.return_value = None
        mock_db.get_user_by_reset_token.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "display_name": "Test User",
            "password_reset_token_data": {
                "user_id": "user-123",
                "expires_at": "2024-12-31T23:59:59",
                "used": False,
            },
        }
        mock_password_service.is_reset_token_valid.return_value = True
        mock_password_service.hash_password.return_value = "hashed-new-password"
        mock_db.update_user.return_value = True
        mock_password_service.clear_failed_attempts.return_value = None
        mock_email_service.send_password_reset_confirmation_email.return_value = True

        # Execute
        result = PasswordResetService.reset_password(
            "valid-token", "NewSecurePassword123!"
        )

        # Verify
        assert result["reset_success"] is True
        assert result["email"] == "test@example.com"
        assert "Password has been reset successfully" in result["message"]
        mock_password_service.validate_password_strength.assert_called_once_with(
            "NewSecurePassword123!"
        )
        mock_password_service.hash_password.assert_called_once_with(
            "NewSecurePassword123!"
        )
        mock_db.update_user.assert_called_once()
        mock_password_service.clear_failed_attempts.assert_called_once_with(
            "test@example.com"
        )

    @patch("src.services.password_reset_service.PasswordService")
    def test_reset_password_invalid_token(self, mock_password_service):
        """Test password reset with invalid token"""
        # Setup
        mock_password_service.validate_password_strength.return_value = None

        # Execute & Verify
        with patch(
            "src.services.password_reset_service.PasswordResetService._get_user_by_reset_token"
        ) as mock_get_user:
            mock_get_user.return_value = None

            with pytest.raises(
                PasswordResetError, match="Invalid or expired reset token"
            ):
                PasswordResetService.reset_password("invalid-token", "NewPassword123!")

    @patch("src.services.password_reset_service.PasswordService")
    @patch("src.services.password_reset_service.db")
    def test_reset_password_expired_token(self, mock_db, mock_password_service):
        """Test password reset with expired token"""
        # Setup
        mock_password_service.validate_password_strength.return_value = None
        mock_db.get_user_by_reset_token.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "password_reset_token_data": {
                "user_id": "user-123",
                "expires_at": "2024-01-01T00:00:00",  # Expired
                "used": False,
            },
        }
        mock_password_service.is_reset_token_valid.return_value = False

        # Execute & Verify
        with pytest.raises(PasswordResetError, match="Reset token has expired"):
            PasswordResetService.reset_password("expired-token", "NewPassword123!")

    @patch("src.services.password_reset_service.PasswordService")
    def test_reset_password_weak_password(self, mock_password_service):
        """Test password reset with weak password"""
        # Setup
        mock_password_service.validate_password_strength.side_effect = (
            PasswordValidationError("Password too weak")
        )

        # Execute & Verify
        with pytest.raises(PasswordResetError, match="Password validation failed"):
            PasswordResetService.reset_password("valid-token", "weak")


class TestPasswordResetServiceValidation:
    """Test token validation functionality"""

    @patch("src.services.password_reset_service.PasswordService")
    @patch("src.services.password_reset_service.db")
    def test_validate_reset_token_valid(self, mock_db, mock_password_service):
        """Test validation of valid reset token"""
        # Setup
        mock_db.get_user_by_reset_token.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "display_name": "Test User",
            "password_reset_token_data": {
                "expires_at": "2024-12-31T23:59:59",
                "used": False,
            },
        }
        mock_password_service.is_reset_token_valid.return_value = True

        # Execute
        result = PasswordResetService.validate_reset_token("valid-token")

        # Verify
        assert result["valid"] is True
        assert result["email"] == "test@example.com"
        assert result["message"] == "Reset token is valid."

    @patch("src.services.password_reset_service.db")
    def test_validate_reset_token_invalid(self, mock_db):
        """Test validation of invalid reset token"""
        # Setup
        mock_db.get_user_by_reset_token.return_value = None

        # Execute
        result = PasswordResetService.validate_reset_token("invalid-token")

        # Verify
        assert result["valid"] is False
        assert "Invalid or expired" in result["message"]


class TestPasswordResetServiceStatus:
    """Test reset status functionality"""

    @patch("src.services.password_reset_service.PasswordService")
    @patch("src.services.password_reset_service.db")
    def test_get_reset_status_pending(self, mock_db, mock_password_service):
        """Test getting reset status when reset is pending"""
        # Setup
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "password_reset_token": "active-token",
            "password_reset_token_data": {
                "expires_at": "2024-12-31T23:59:59",
                "used": False,
            },
        }
        mock_password_service.is_reset_token_valid.return_value = True

        # Execute
        result = PasswordResetService.get_reset_status("test@example.com")

        # Verify
        assert result["has_pending_reset"] is True
        assert result["expires_at"] == "2024-12-31T23:59:59"

    @patch("src.services.password_reset_service.db")
    def test_get_reset_status_no_user(self, mock_db):
        """Test getting reset status when user doesn't exist"""
        # Setup
        mock_db.get_user_by_email.return_value = None

        # Execute
        result = PasswordResetService.get_reset_status("nonexistent@example.com")

        # Verify
        assert result["has_pending_reset"] is False
        assert "No user found" in result["message"]

    @patch("src.services.password_reset_service.db")
    def test_get_reset_status_no_pending_reset(self, mock_db):
        """Test getting reset status when no reset is pending"""
        # Setup
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            # No password_reset_token field
        }

        # Execute
        result = PasswordResetService.get_reset_status("test@example.com")

        # Verify
        assert result["has_pending_reset"] is False
        assert "No pending password reset" in result["message"]


class TestPasswordResetServiceHelpers:
    """Test helper methods"""

    @patch("src.services.password_reset_service.db")
    def test_get_user_by_reset_token_found(self, mock_db):
        """Test finding user by reset token"""
        # Setup
        expected_user = {"user_id": "user-123", "email": "test@example.com"}
        mock_db.get_user_by_reset_token.return_value = expected_user

        # Execute
        result = PasswordResetService._get_user_by_reset_token("valid-token")

        # Verify
        assert result == expected_user
        mock_db.get_user_by_reset_token.assert_called_once_with("valid-token")

    @patch("src.services.password_reset_service.db")
    def test_get_user_by_reset_token_not_found(self, mock_db):
        """Test finding user by reset token when not found"""
        # Setup
        mock_db.get_user_by_reset_token.return_value = None

        # Execute
        result = PasswordResetService._get_user_by_reset_token("invalid-token")

        # Verify
        assert result is None

    @patch("src.services.password_reset_service.PasswordService")
    def test_check_reset_rate_limit_ok(self, mock_password_service):
        """Test rate limit check when under limit"""
        # Setup
        mock_password_service.check_rate_limit.return_value = None

        # Execute - should not raise exception
        PasswordResetService._check_reset_rate_limit("test@example.com")

        # Verify
        mock_password_service.check_rate_limit.assert_called_once_with(
            "test@example.com"
        )

    @patch("src.services.password_reset_service.PasswordService")
    def test_check_reset_rate_limit_exceeded(self, mock_password_service):
        """Test rate limit check when limit exceeded"""
        # Setup
        mock_password_service.check_rate_limit.side_effect = Exception(
            "Rate limit exceeded"
        )

        # Execute & Verify
        with pytest.raises(
            PasswordResetError, match="Too many password reset requests"
        ):
            PasswordResetService._check_reset_rate_limit("test@example.com")


class TestPasswordResetServiceConvenienceFunctions:
    """Test convenience functions"""

    @patch(
        "src.services.password_reset_service.PasswordResetService.request_password_reset"
    )
    def test_request_password_reset_convenience(self, mock_request):
        """Test request_password_reset convenience function"""
        # Setup
        expected_result = {"request_success": True}
        mock_request.return_value = expected_result

        # Execute
        from src.services.password_reset_service import request_password_reset

        result = request_password_reset("test@example.com")

        # Verify
        assert result == expected_result
        mock_request.assert_called_once_with("test@example.com")

    @patch("src.services.password_reset_service.PasswordResetService.reset_password")
    def test_reset_password_convenience(self, mock_reset):
        """Test reset_password convenience function"""
        # Setup
        expected_result = {"reset_success": True}
        mock_reset.return_value = expected_result

        # Execute
        from src.services.password_reset_service import reset_password

        result = reset_password("token", "password")

        # Verify
        assert result == expected_result
        mock_reset.assert_called_once_with("token", "password")

    @patch(
        "src.services.password_reset_service.PasswordResetService.validate_reset_token"
    )
    def test_validate_reset_token_convenience(self, mock_validate):
        """Test validate_reset_token convenience function"""
        # Setup
        expected_result = {"valid": True}
        mock_validate.return_value = expected_result

        # Execute
        from src.services.password_reset_service import validate_reset_token

        result = validate_reset_token("token")

        # Verify
        assert result == expected_result
        mock_validate.assert_called_once_with("token")

    @patch("src.services.password_reset_service.PasswordResetService.get_reset_status")
    def test_get_reset_status_convenience(self, mock_get_status):
        """Test get_reset_status convenience function"""
        # Setup
        expected_result = {"has_pending_reset": False}
        mock_get_status.return_value = expected_result

        # Execute
        from src.services.password_reset_service import get_reset_status

        result = get_reset_status("test@example.com")

        # Verify
        assert result == expected_result
        mock_get_status.assert_called_once_with("test@example.com")
