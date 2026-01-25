"""Tests for user profile management API endpoints.

TDD tests for:
- Profile update (PATCH /api/auth/profile)
- Password change (POST /api/auth/change-password)
"""

import os
from unittest.mock import patch

from src.app import app
from tests.test_credentials import NEW_PASSWORD, SECURE_PASSWORD

TEST_PASSWORD = os.environ.get("TEST_PASSWORD", SECURE_PASSWORD)
NEW_TEST_PASSWORD = NEW_PASSWORD


class TestProfileUpdateAPI:
    """Test profile update API endpoint."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()
        self.test_user = {
            "user_id": "user-123",
            "email": "test@example.com",
            "role": "instructor",
            "first_name": "John",
            "last_name": "Doe",
            "institution_id": "inst-123",
        }

    def _login_user(self):
        """Create authenticated session."""
        from tests.test_utils import create_test_session

        create_test_session(self.client, self.test_user)

    def test_profile_update_requires_authentication(self):
        """Test that profile update requires login."""
        # No login - should return 401
        response = self.client.patch(
            "/api/auth/profile",
            json={"first_name": "Jane"},
        )
        assert response.status_code == 401

    def test_profile_update_success(self):
        """Test successful profile update."""
        self._login_user()

        with patch("src.api.routes.auth.update_user_profile") as mock_update:
            mock_update.return_value = True

            response = self.client.patch(
                "/api/auth/profile",
                json={"first_name": "Jane", "last_name": "Smith"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert "Profile updated" in data["message"]

            # Verify the update was called with correct data
            mock_update.assert_called_once()
            call_args = mock_update.call_args
            assert call_args[0][0] == "user-123"  # user_id
            assert call_args[0][1]["first_name"] == "Jane"
            assert call_args[0][1]["last_name"] == "Smith"

    def test_profile_update_no_json(self):
        """Test profile update with no JSON data."""
        self._login_user()

        response = self.client.patch("/api/auth/profile")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "No JSON data" in data["error"]

    def test_profile_update_cannot_change_email(self):
        """Test that email cannot be changed via profile update."""
        self._login_user()

        with patch("src.api.routes.auth.update_user_profile") as mock_update:
            mock_update.return_value = True

            response = self.client.patch(
                "/api/auth/profile",
                json={
                    "first_name": "Jane",
                    "email": "hacker@evil.com",  # Attempt to change email
                },
            )

            assert response.status_code == 200
            # Verify email was NOT included in the update call
            call_args = mock_update.call_args
            assert "email" not in call_args[0][1]

    def test_profile_update_cannot_change_role(self):
        """Test that role cannot be changed via profile update."""
        self._login_user()

        with patch("src.api.routes.auth.update_user_profile") as mock_update:
            mock_update.return_value = True

            response = self.client.patch(
                "/api/auth/profile",
                json={
                    "first_name": "Jane",
                    "role": "site_admin",  # Attempt to escalate privileges
                },
            )

            assert response.status_code == 200
            # Verify role was NOT included in the update call
            call_args = mock_update.call_args
            assert "role" not in call_args[0][1]

    def test_profile_update_database_error(self):
        """Test profile update handles database errors."""
        self._login_user()

        with patch("src.api.routes.auth.update_user_profile") as mock_update:
            mock_update.side_effect = Exception("Database error")

            response = self.client.patch(
                "/api/auth/profile",
                json={"first_name": "Jane"},
            )

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False


class TestChangePasswordAPI:
    """Test password change API endpoint."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()
        self.test_user = {
            "user_id": "user-123",
            "email": "test@example.com",
            "role": "instructor",
            "first_name": "John",
            "last_name": "Doe",
            "institution_id": "inst-123",
        }

    def _login_user(self):
        """Create authenticated session."""
        from tests.test_utils import create_test_session

        create_test_session(self.client, self.test_user)

    def test_change_password_requires_authentication(self):
        """Test that password change requires login."""
        # No login - should return 401
        response = self.client.post(
            "/api/auth/change-password",
            json={
                "current_password": TEST_PASSWORD,
                "new_password": NEW_TEST_PASSWORD,
            },
        )
        assert response.status_code == 401

    def test_change_password_success(self):
        """Test successful password change."""
        self._login_user()

        with (
            patch("src.api.routes.auth.get_user_by_id") as mock_get_user,
            patch("src.services.password_service.verify_password") as mock_verify,
            patch("src.services.password_service.hash_password") as mock_hash,
            patch("src.api.routes.auth.update_user") as mock_update,
        ):
            mock_get_user.return_value = {
                "user_id": "user-123",
                "password_hash": "old_hash",
            }
            mock_verify.return_value = True
            mock_hash.return_value = "new_hash"
            mock_update.return_value = True

            response = self.client.post(
                "/api/auth/change-password",
                json={
                    "current_password": TEST_PASSWORD,
                    "new_password": NEW_TEST_PASSWORD,
                },
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert "Password changed" in data["message"]

    def test_change_password_no_json(self):
        """Test password change with no JSON data."""
        self._login_user()

        response = self.client.post("/api/auth/change-password")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "No JSON data" in data["error"]

    def test_change_password_missing_current_password(self):
        """Test password change with missing current password."""
        self._login_user()

        response = self.client.post(
            "/api/auth/change-password",
            json={"new_password": NEW_TEST_PASSWORD},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "current_password" in data["error"]

    def test_change_password_missing_new_password(self):
        """Test password change with missing new password."""
        self._login_user()

        response = self.client.post(
            "/api/auth/change-password",
            json={"current_password": TEST_PASSWORD},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "new_password" in data["error"]

    def test_change_password_wrong_current_password(self):
        """Test password change with incorrect current password."""
        self._login_user()

        with (
            patch("src.api.routes.auth.get_user_by_id") as mock_get_user,
            patch("src.services.password_service.verify_password") as mock_verify,
        ):
            mock_get_user.return_value = {
                "user_id": "user-123",
                "password_hash": "old_hash",
            }
            mock_verify.return_value = False  # Wrong password

            response = self.client.post(
                "/api/auth/change-password",
                json={
                    "current_password": "wrong_password",
                    "new_password": NEW_TEST_PASSWORD,
                },
            )

            assert response.status_code == 401
            data = response.get_json()
            assert data["success"] is False
            assert "Current password is incorrect" in data["error"]

    def test_change_password_weak_new_password(self):
        """Test password change with weak new password."""
        self._login_user()

        with (
            patch("src.api.routes.auth.get_user_by_id") as mock_get_user,
            patch("src.services.password_service.verify_password") as mock_verify,
            patch("src.services.password_service.hash_password") as mock_hash,
        ):
            mock_get_user.return_value = {
                "user_id": "user-123",
                "password_hash": "old_hash",
            }
            mock_verify.return_value = True
            # Simulate password validation failure
            from src.services.password_service import PasswordValidationError

            mock_hash.side_effect = PasswordValidationError(
                "Password does not meet requirements"
            )

            response = self.client.post(
                "/api/auth/change-password",
                json={
                    "current_password": TEST_PASSWORD,
                    "new_password": "weak",  # Too short
                },
            )

            assert response.status_code == 400
            data = response.get_json()
            assert data["success"] is False

    def test_change_password_database_error(self):
        """Test password change handles database errors."""
        self._login_user()

        with (
            patch("src.api.routes.auth.get_user_by_id") as mock_get_user,
            patch("src.services.password_service.verify_password") as mock_verify,
            patch("src.services.password_service.hash_password") as mock_hash,
            patch("src.api.routes.auth.update_user") as mock_update,
        ):
            mock_get_user.return_value = {
                "user_id": "user-123",
                "password_hash": "old_hash",
            }
            mock_verify.return_value = True
            mock_hash.return_value = "new_hash"
            mock_update.side_effect = Exception("Database error")

            response = self.client.post(
                "/api/auth/change-password",
                json={
                    "current_password": TEST_PASSWORD,
                    "new_password": NEW_TEST_PASSWORD,
                },
            )

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False
