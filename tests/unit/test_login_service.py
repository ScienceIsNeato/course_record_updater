"""
Unit tests for login_service.py

Tests the LoginService class and its methods for user authentication functionality.
"""

from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest

from login_service import LoginError, LoginService
from password_service import AccountLockedError


class TestLoginServiceAuthentication:
    """Test user authentication functionality"""

    @patch("login_service.SessionService")
    @patch("login_service.PasswordService")
    @patch("login_service.db")
    def test_authenticate_user_success(
        self, mock_db, mock_password_service, mock_session
    ):
        """Test successful user authentication"""
        # Setup
        mock_password_service.check_account_lockout.return_value = None
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "password_hash": "hashed-password",
            "role": "instructor",
            "account_status": "active",
            "email_verified": True,  # Required for login
            "institution_id": "inst-123",
            "display_name": "Test User",
            "login_count": 5,
        }
        mock_password_service.verify_password.return_value = True
        mock_password_service.clear_failed_attempts.return_value = None
        mock_db.update_user.return_value = True
        mock_session.create_user_session.return_value = None

        # Execute
        result = LoginService.authenticate_user(
            "test@example.com", "password123", False
        )

        # Verify
        assert result["login_success"] is True
        assert result["user_id"] == "user-123"
        assert result["email"] == "test@example.com"
        assert result["role"] == "instructor"
        assert result["message"] == "Login successful"

        mock_password_service.check_account_lockout.assert_called_once_with(
            "test@example.com"
        )
        mock_db.get_user_by_email.assert_called_once_with("test@example.com")
        mock_password_service.verify_password.assert_called_once_with(
            "password123", "hashed-password"
        )
        mock_password_service.clear_failed_attempts.assert_called_once_with(
            "test@example.com"
        )
        mock_db.update_user.assert_called_once()
        mock_session.create_user_session.assert_called_once()

    @patch("login_service.PasswordService")
    @patch("login_service.db")
    def test_authenticate_user_invalid_email(self, mock_db, mock_password_service):
        """Test authentication with invalid email"""
        # Setup
        mock_password_service.check_account_lockout.return_value = None
        mock_db.get_user_by_email.return_value = None
        mock_password_service.track_failed_login.return_value = None

        # Execute & Verify
        with pytest.raises(LoginError, match="Invalid email or password"):
            LoginService.authenticate_user("invalid@example.com", "password123")

        mock_password_service.track_failed_login.assert_called_once_with(
            "invalid@example.com"
        )

    @patch("login_service.PasswordService")
    @patch("login_service.db")
    def test_authenticate_user_invalid_password(self, mock_db, mock_password_service):
        """Test authentication with invalid password"""
        # Setup
        mock_password_service.check_account_lockout.return_value = None
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "password_hash": "hashed-password",
            "account_status": "active",
            "email_verified": True,  # Required for login
        }
        mock_password_service.verify_password.return_value = False
        mock_password_service.track_failed_login.return_value = None

        # Execute & Verify
        with pytest.raises(LoginError, match="Invalid email or password"):
            LoginService.authenticate_user("test@example.com", "wrongpassword")

        mock_password_service.track_failed_login.assert_called_once_with(
            "test@example.com"
        )

    @patch("login_service.PasswordService")
    @patch("login_service.db")
    def test_authenticate_user_pending_account(self, mock_db, mock_password_service):
        """Test authentication with pending account"""
        # Setup
        mock_password_service.check_account_lockout.return_value = None
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "password_hash": "hashed-password",
            "account_status": "pending",
        }

        # Execute & Verify
        with pytest.raises(LoginError, match="Account is pending activation"):
            LoginService.authenticate_user("test@example.com", "password123")

    @patch("login_service.PasswordService")
    @patch("login_service.db")
    def test_authenticate_user_suspended_account(self, mock_db, mock_password_service):
        """Test authentication with suspended account"""
        # Setup
        mock_password_service.check_account_lockout.return_value = None
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "password_hash": "hashed-password",
            "account_status": "suspended",
        }

        # Execute & Verify
        with pytest.raises(LoginError, match="Account has been suspended"):
            LoginService.authenticate_user("test@example.com", "password123")

    @patch("login_service.PasswordService")
    def test_authenticate_user_account_locked(self, mock_password_service):
        """Test authentication with locked account"""
        # Setup
        mock_password_service.check_account_lockout.side_effect = AccountLockedError(
            "Account is locked"
        )

        # Execute & Verify
        with pytest.raises(AccountLockedError, match="Account is locked"):
            LoginService.authenticate_user("test@example.com", "password123")

    @patch("login_service.PasswordService")
    @patch("login_service.db")
    def test_authenticate_user_no_password_hash(self, mock_db, mock_password_service):
        """Test authentication when user has no password hash"""
        # Setup
        mock_password_service.check_account_lockout.return_value = None
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "account_status": "active",
            "email_verified": True,  # Required for login
            # No password_hash field
        }

        # Execute & Verify
        with pytest.raises(
            LoginError, match="Account is not configured for password login"
        ):
            LoginService.authenticate_user("test@example.com", "password123")

    @patch("login_service.SessionService")
    @patch("login_service.PasswordService")
    @patch("login_service.db")
    def test_authenticate_user_remember_me(
        self, mock_db, mock_password_service, mock_session
    ):
        """Test authentication with remember me option"""
        # Setup
        mock_password_service.check_account_lockout.return_value = None
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "password_hash": "hashed-password",
            "role": "instructor",
            "account_status": "active",
            "email_verified": True,  # Required for login
            "login_count": 0,
        }
        mock_password_service.verify_password.return_value = True
        mock_password_service.clear_failed_attempts.return_value = None
        mock_db.update_user.return_value = True
        mock_session.create_user_session.return_value = None

        # Execute
        result = LoginService.authenticate_user(
            "test@example.com", "password123", remember_me=True
        )

        # Verify
        assert result["login_success"] is True
        mock_session.create_user_session.assert_called_once()
        session_call = mock_session.create_user_session.call_args
        assert (
            session_call[0][1] is True
        )  # remember_me is the second positional argument

    @patch("login_service.SessionService")
    @patch("login_service.db")
    @patch("login_service.PasswordService")
    def test_login_user_generic_exception(
        self, mock_password_service, mock_db, mock_session
    ):
        """Test authentication with generic exception (not credentials/account related)"""
        # Setup
        mock_password_service.check_account_lockout.return_value = None
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "password_hash": "hashed-password",
            "role": "instructor",
            "account_status": "active",
        }
        mock_password_service.verify_password.return_value = True

        # Make session creation raise a generic exception (not credentials/account related)
        mock_session.create_user_session.side_effect = Exception(
            "Database connection error"
        )

        # Execute & Verify
        with pytest.raises(LoginError, match="Login failed. Please try again."):
            LoginService.authenticate_user(
                "test@example.com", "password123", remember_me=False
            )


class TestLoginServiceLogout:
    """Test logout functionality"""

    @patch("login_service.SessionService")
    def test_logout_user_success(self, mock_session):
        """Test successful user logout"""
        # Setup
        mock_session.get_session_info.return_value = {"email": "test@example.com"}
        mock_session.destroy_session.return_value = None

        # Execute
        result = LoginService.logout_user()

        # Verify
        assert result["logout_success"] is True
        assert result["message"] == "Logout successful"
        mock_session.destroy_session.assert_called_once()

    @patch("login_service.SessionService")
    def test_logout_user_with_error(self, mock_session):
        """Test logout when error occurs"""
        # Setup
        mock_session.get_session_info.side_effect = Exception("Session error")
        mock_session.destroy_session.return_value = None

        # Execute
        result = LoginService.logout_user()

        # Verify - should still succeed and clean up session
        assert result["logout_success"] is True
        assert result["message"] == "Logout completed"
        mock_session.destroy_session.assert_called()


class TestLoginServiceStatus:
    """Test login status functionality"""

    @patch("login_service.SessionService")
    def test_get_login_status_logged_in(self, mock_session):
        """Test getting login status when user is logged in"""
        # Setup
        mock_session.is_user_logged_in.return_value = True
        mock_session.validate_session.return_value = True
        mock_session.get_session_info.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "role": "instructor",
            "institution_id": "inst-123",
            "display_name": "Test User",
            "last_activity": "2024-01-01T12:00:00",
        }

        # Execute
        result = LoginService.get_login_status()

        # Verify
        assert result["logged_in"] is True
        assert result["user_id"] == "user-123"
        assert result["email"] == "test@example.com"
        assert result["role"] == "instructor"
        assert result["message"] == "User is logged in"

    @patch("login_service.SessionService")
    def test_get_login_status_not_logged_in(self, mock_session):
        """Test getting login status when user is not logged in"""
        # Setup
        mock_session.is_user_logged_in.return_value = False

        # Execute
        result = LoginService.get_login_status()

        # Verify
        assert result["logged_in"] is False
        assert result["message"] == "Not logged in"

    @patch("login_service.SessionService")
    def test_get_login_status_invalid_session(self, mock_session):
        """Test getting login status when session is invalid"""
        # Setup
        mock_session.is_user_logged_in.return_value = True
        mock_session.validate_session.return_value = False

        # Execute
        result = LoginService.get_login_status()

        # Verify
        assert result["logged_in"] is False
        assert result["message"] == "Session expired or invalid"


class TestLoginServiceSessionManagement:
    """Test session management functionality"""

    @patch("login_service.SessionService")
    def test_refresh_session_success(self, mock_session):
        """Test successful session refresh"""
        # Setup
        mock_session.is_user_logged_in.return_value = True
        mock_session.refresh_session.return_value = None

        # Execute
        result = LoginService.refresh_session()

        # Verify
        assert result["refresh_success"] is True
        assert result["message"] == "Session refreshed successfully"
        mock_session.refresh_session.assert_called_once()

    @patch("login_service.SessionService")
    def test_refresh_session_no_active_session(self, mock_session):
        """Test session refresh when no active session"""
        # Setup
        mock_session.is_user_logged_in.return_value = False

        # Execute & Verify
        with pytest.raises(LoginError, match="No active session to refresh"):
            LoginService.refresh_session()

    @patch("login_service.SessionService")
    def test_refresh_session_error(self, mock_session):
        """Test session refresh with error"""
        # Setup
        mock_session.is_user_logged_in.return_value = True
        mock_session.refresh_session.side_effect = Exception("Refresh error")

        # Execute & Verify
        with pytest.raises(LoginError, match="Failed to refresh session"):
            LoginService.refresh_session()


class TestLoginServiceAccountLockout:
    """Test account lockout functionality"""

    @patch("login_service.PasswordService")
    def test_check_account_lockout_status_not_locked(self, mock_password_service):
        """Test checking lockout status when account is not locked"""
        # Setup
        mock_password_service.is_account_locked.return_value = (False, None)

        # Execute
        result = LoginService.check_account_lockout_status("test@example.com")

        # Verify
        assert result["is_locked"] is False
        assert result["message"] == "Account is not locked"

    @patch("login_service.PasswordService")
    def test_check_account_lockout_status_locked(self, mock_password_service):
        """Test checking lockout status when account is locked"""
        # Setup
        unlock_time = datetime.now() + timedelta(minutes=30)
        mock_password_service.is_account_locked.return_value = (True, unlock_time)

        # Execute
        result = LoginService.check_account_lockout_status("test@example.com")

        # Verify
        assert result["is_locked"] is True
        assert result["unlock_time"] == unlock_time.isoformat()
        assert "Account is locked until" in result["message"]

    @patch("login_service.PasswordService")
    def test_unlock_account_success(self, mock_password_service):
        """Test successful account unlock"""
        # Setup
        mock_password_service.clear_failed_attempts.return_value = None

        # Execute
        result = LoginService.unlock_account("test@example.com", "admin-123")

        # Verify
        assert result["unlock_success"] is True
        assert "has been unlocked" in result["message"]
        mock_password_service.clear_failed_attempts.assert_called_once_with(
            "test@example.com"
        )

    @patch("login_service.PasswordService")
    def test_unlock_account_error(self, mock_password_service):
        """Test account unlock with error"""
        # Setup
        mock_password_service.clear_failed_attempts.side_effect = Exception(
            "Unlock error"
        )

        # Execute & Verify
        with pytest.raises(LoginError, match="Failed to unlock account"):
            LoginService.unlock_account("test@example.com", "admin-123")


class TestLoginServiceNotifications:
    """Test notification functionality"""

    @patch("login_service.db")
    def test_send_account_locked_notification_success(self, mock_db):
        """Test sending account locked notification"""
        # Setup
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "institution_id": "inst-123",
        }
        mock_db.get_institution_by_id.return_value = {"name": "Test Institution"}

        # Execute
        result = LoginService.send_account_locked_notification("test@example.com")

        # Verify
        assert result is True

    @patch("login_service.db")
    def test_send_account_locked_notification_user_not_found(self, mock_db):
        """Test sending notification when user not found"""
        # Setup
        mock_db.get_user_by_email.return_value = None

        # Execute
        result = LoginService.send_account_locked_notification("test@example.com")

        # Verify
        assert result is False


class TestLoginServiceConvenienceFunctions:
    """Test convenience functions"""

    @patch("login_service.LoginService.authenticate_user")
    def test_login_user_convenience(self, mock_authenticate):
        """Test login_user convenience function"""
        # Setup
        expected_result = {"login_success": True}
        mock_authenticate.return_value = expected_result

        # Execute
        from login_service import login_user

        result = login_user("test@example.com", "password123", True)

        # Verify
        assert result == expected_result
        mock_authenticate.assert_called_once_with(
            "test@example.com", "password123", True
        )

    @patch("login_service.LoginService.logout_user")
    def test_logout_user_convenience(self, mock_logout):
        """Test logout_user convenience function"""
        # Setup
        expected_result = {"logout_success": True}
        mock_logout.return_value = expected_result

        # Execute
        from login_service import logout_user

        result = logout_user()

        # Verify
        assert result == expected_result
        mock_logout.assert_called_once()

    @patch("login_service.LoginService.get_login_status")
    def test_is_user_logged_in_convenience(self, mock_get_status):
        """Test is_user_logged_in convenience function"""
        # Setup
        mock_get_status.return_value = {"logged_in": True}

        # Execute
        from login_service import is_user_logged_in

        result = is_user_logged_in()

        # Verify
        assert result is True

    @patch("login_service.LoginService.get_login_status")
    def test_get_current_user_info_convenience_logged_in(self, mock_get_status):
        """Test get_current_user_info when logged in"""
        # Setup
        mock_get_status.return_value = {
            "logged_in": True,
            "user_id": "user-123",
            "email": "test@example.com",
            "role": "instructor",
        }

        # Execute
        from login_service import get_current_user_info

        result = get_current_user_info()

        # Verify
        assert result is not None
        assert result["user_id"] == "user-123"
        assert result["email"] == "test@example.com"

    @patch("login_service.LoginService.get_login_status")
    def test_get_current_user_info_convenience_not_logged_in(self, mock_get_status):
        """Test get_current_user_info when not logged in"""
        # Setup
        mock_get_status.return_value = {"logged_in": False}

        # Execute
        from login_service import get_current_user_info

        result = get_current_user_info()

        # Verify
        assert result is None


class TestLoginServiceIntegration:
    """Integration tests for login service"""

    @patch("login_service.SessionService")
    @patch("login_service.PasswordService")
    @patch("login_service.db")
    def test_complete_login_logout_flow(
        self, mock_db, mock_password_service, mock_session
    ):
        """Test complete login and logout flow"""
        # Setup for login
        mock_password_service.check_account_lockout.return_value = None
        mock_db.get_user_by_email.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "password_hash": "hashed-password",
            "role": "instructor",
            "account_status": "active",
            "email_verified": True,  # Required for login
            "login_count": 0,
        }
        mock_password_service.verify_password.return_value = True
        mock_password_service.clear_failed_attempts.return_value = None
        mock_db.update_user.return_value = True
        mock_session.create_user_session.return_value = None

        # Step 1: Login
        login_result = LoginService.authenticate_user("test@example.com", "password123")
        assert login_result["login_success"] is True

        # Setup for status check
        mock_session.is_user_logged_in.return_value = True
        mock_session.validate_session.return_value = True
        mock_session.get_session_info.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "role": "instructor",
        }

        # Step 2: Check status
        status_result = LoginService.get_login_status()
        assert status_result["logged_in"] is True

        # Setup for logout
        mock_session.get_session_info.return_value = {"email": "test@example.com"}
        mock_session.destroy_session.return_value = None

        # Step 3: Logout
        logout_result = LoginService.logout_user()
        assert logout_result["logout_success"] is True

        # Verify all services were called
        mock_password_service.check_account_lockout.assert_called()
        mock_db.get_user_by_email.assert_called()
        mock_session.create_user_session.assert_called()
        mock_session.destroy_session.assert_called()
