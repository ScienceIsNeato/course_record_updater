"""Unit tests for authentication API routes (migrated from test_api_routes.py)."""

import json
from unittest.mock import patch

from src.app import app
from src.utils.constants import GENERIC_PASSWORD, INVALID_PASSWORD, USER_NOT_FOUND_MSG

TEST_PASSWORD = GENERIC_PASSWORD  # Test password for unit tests


class TestLoginAPI:
    """Test login API error handling."""

    def test_login_api_account_locked_error(self, client, csrf_token):
        """Test login API handles AccountLockedError correctly."""
        with patch("src.services.login_service.LoginService") as mock_login_service:
            mock_login_service.authenticate_user.side_effect = Exception(
                "AccountLockedError"
            )

            response = client.post(
                "/api/auth/login",
                json={
                    "email": "test@example.com",
                    "password": INVALID_PASSWORD,
                },
                headers={"X-CSRFToken": csrf_token},
            )

            assert response.status_code == 500  # Should handle the exception

    def test_login_api_login_error(self, client, csrf_token):
        """Test login API handles LoginError correctly."""
        with patch("src.services.login_service.LoginService") as mock_login_service:
            mock_login_service.authenticate_user.side_effect = Exception("LoginError")

            response = client.post(
                "/api/auth/login",
                json={
                    "email": "test@example.com",
                    "password": INVALID_PASSWORD,
                },
                headers={"X-CSRFToken": csrf_token},
            )

            assert response.status_code == 500  # Should handle the exception

    def test_login_api_with_next_url_in_session(self, client, csrf_token):
        """Test login API includes next_url from session in response."""
        with patch("src.services.login_service.LoginService") as mock_login_service:
            mock_login_service.authenticate_user.return_value = {
                "user_id": "user-123",
                "role": "instructor",
                "token": "test-token",
            }

            # Set next_after_login in session
            with client.session_transaction() as sess:
                sess["next_after_login"] = "/assessments?course=course-123"

            response = client.post(
                "/api/auth/login",
                json={
                    "email": "test@example.com",
                    "password": INVALID_PASSWORD,
                },
                headers={"X-CSRFToken": csrf_token},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["next_url"] == "/assessments?course=course-123"

            # Verify next_after_login was removed from session
            with client.session_transaction() as sess:
                assert "next_after_login" not in sess


class TestRegistrationEndpoints:
    """Test registration API endpoints (Story 2.1)"""

    @patch("src.api.routes.auth.register_institution_admin")
    def test_register_institution_admin_success(self, mock_register):
        """Test successful registration of institution admin."""
        # Setup successful registration response
        mock_register.return_value = {
            "success": True,
            "message": "Registration successful! Please check your email to verify your account.",
            "user_id": "user-123",
            "institution_id": "inst-456",
            "email_sent": True,
        }

        with app.test_client() as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "admin@testuniv.edu",
                    "password": TEST_PASSWORD,
                    "first_name": "John",
                    "last_name": "Doe",
                    "institution_name": "Test University",
                    "website_url": "https://testuniv.edu",
                },
            )

            assert response.status_code == 201
            data = json.loads(response.data)
            assert data["success"] is True
            assert "Registration successful" in data["message"]
            assert data["user_id"] == "user-123"
            assert data["institution_id"] == "inst-456"
            assert data["email_sent"] is True

            # Verify the service was called with correct parameters
            mock_register.assert_called_once_with(
                email="admin@testuniv.edu",
                password=TEST_PASSWORD,
                first_name="John",
                last_name="Doe",
                institution_name="Test University",
                website_url="https://testuniv.edu",
            )

    def test_register_institution_admin_missing_fields(self):
        """Test registration with missing required fields."""
        with app.test_client() as client:
            # Missing email and password
            response = client.post(
                "/api/auth/register",
                json={
                    "first_name": "John",
                    "last_name": "Doe",
                    "institution_name": "Test University",
                },
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Missing required fields" in data["error"]
            assert "email" in data["error"]
            assert "password" in data["error"]

    def test_register_institution_admin_invalid_email(self):
        """Test registration with invalid email format."""
        with app.test_client() as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "invalid-email",  # No @ or .
                    "password": TEST_PASSWORD,
                    "first_name": "John",
                    "last_name": "Doe",
                    "institution_name": "Test University",
                },
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Invalid email format" in data["error"]

    @patch("src.api.routes.auth.register_institution_admin")
    def test_register_institution_admin_registration_error(self, mock_register):
        """Test registration with RegistrationError exception."""
        from src.services.registration_service import RegistrationError

        mock_register.side_effect = RegistrationError("Email already exists")

        with app.test_client() as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "admin@testuniv.edu",
                    "password": TEST_PASSWORD,
                    "first_name": "John",
                    "last_name": "Doe",
                    "institution_name": "Test University",
                },
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Email already exists" in data["error"]

    @patch("src.api.routes.auth.register_institution_admin")
    def test_register_institution_admin_server_error(self, mock_register):
        """Test registration with unexpected server error."""
        mock_register.side_effect = Exception("Database connection failed")

        with app.test_client() as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "admin@testuniv.edu",
                    "password": TEST_PASSWORD,
                    "first_name": "John",
                    "last_name": "Doe",
                    "institution_name": "Test University",
                },
            )

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Registration failed due to server error" in data["error"]

    def test_register_institution_admin_optional_website(self):
        """Test registration without optional website_url field."""
        with patch("src.api.routes.auth.register_institution_admin") as mock_register:
            mock_register.return_value = {
                "success": True,
                "message": "Registration successful!",
                "user_id": "user-123",
                "institution_id": "inst-456",
                "email_sent": True,
            }

            with app.test_client() as client:
                response = client.post(
                    "/api/auth/register",
                    json={
                        "email": "admin@testuniv.edu",
                        "password": TEST_PASSWORD,
                        "first_name": "John",
                        "last_name": "Doe",
                        "institution_name": "Test University",
                        # No website_url provided
                    },
                )

                assert response.status_code == 201

                # Verify website_url was passed as None
                mock_register.assert_called_once_with(
                    email="admin@testuniv.edu",
                    password=TEST_PASSWORD,
                    first_name="John",
                    last_name="Doe",
                    institution_name="Test University",
                    website_url=None,
                )


class TestResendVerificationEndpoints:
    """Test resend verification email API endpoints (Story 2.1)"""

    @patch("src.services.registration_service.RegistrationService")
    def test_resend_verification_success(self, mock_registration_service):
        """Test successful verification email resend."""
        # Mock successful resend
        mock_registration_service.resend_verification_email.return_value = {
            "success": True,
            "message": "Verification email sent! Please check your email.",
            "email_sent": True,
        }

        with app.test_client() as client:
            response = client.post(
                "/api/auth/resend-verification", json={"email": "admin@testuniv.edu"}
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "Verification email sent" in data["message"]
            assert data["email_sent"] is True

            # Verify service was called correctly
            mock_registration_service.resend_verification_email.assert_called_once_with(
                "admin@testuniv.edu"
            )

    def test_resend_verification_no_json(self):
        """Test resend verification with no JSON data."""
        with app.test_client() as client:
            response = client.post("/api/auth/resend-verification")

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Email address is required" in data["error"]

    def test_resend_verification_missing_email(self):
        """Test resend verification with missing email."""
        with app.test_client() as client:
            response = client.post("/api/auth/resend-verification", json={})

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Email address is required" in data["error"]

    def test_resend_verification_empty_email(self):
        """Test resend verification with empty email."""
        with app.test_client() as client:
            response = client.post(
                "/api/auth/resend-verification",
                json={"email": "   "},  # Whitespace only
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Email address is required" in data["error"]

    def test_resend_verification_invalid_email(self):
        """Test resend verification with invalid email format."""
        with app.test_client() as client:
            response = client.post(
                "/api/auth/resend-verification",
                json={"email": "invalid-email"},  # No @ or .
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Invalid email format" in data["error"]

    @patch("src.services.registration_service.RegistrationService")
    def test_resend_verification_user_not_found(self, mock_registration_service):
        """Test resend verification for non-existent user."""
        from src.services.registration_service import RegistrationError

        mock_registration_service.resend_verification_email.side_effect = (
            RegistrationError(USER_NOT_FOUND_MSG)
        )

        with app.test_client() as client:
            response = client.post(
                "/api/auth/resend-verification", json={"email": "notfound@test.com"}
            )

            assert response.status_code == 400  # RegistrationError returns 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert USER_NOT_FOUND_MSG in data["error"]

    @patch("src.services.registration_service.RegistrationService")
    def test_resend_verification_already_verified(self, mock_registration_service):
        """Test resend verification for already verified user."""
        from src.services.registration_service import RegistrationError

        mock_registration_service.resend_verification_email.side_effect = (
            RegistrationError("User is already verified")
        )

        with app.test_client() as client:
            response = client.post(
                "/api/auth/resend-verification", json={"email": "verified@test.com"}
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "User is already verified" in data["error"]

    @patch("src.services.registration_service.RegistrationService")
    def test_resend_verification_server_error(self, mock_registration_service):
        """Test resend verification with server error."""
        mock_registration_service.resend_verification_email.side_effect = Exception(
            "Email service unavailable"
        )

        with app.test_client() as client:
            response = client.post(
                "/api/auth/resend-verification", json={"email": "admin@test.com"}
            )

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Failed to resend verification email" in data["error"]

    @patch("src.services.registration_service.RegistrationService")
    def test_resend_verification_email_case_normalization(
        self, mock_registration_service
    ):
        """Test resend verification normalizes email to lowercase."""
        mock_registration_service.resend_verification_email.return_value = {
            "success": True,
            "message": "Verification email sent! Please check your email.",
            "email_sent": True,
        }

        with app.test_client() as client:
            response = client.post(
                "/api/auth/resend-verification",
                json={"email": "ADMIN@TESTUNIV.EDU"},  # Uppercase email
            )

            assert response.status_code == 200

            # Verify service was called with normalized email
            mock_registration_service.resend_verification_email.assert_called_once_with(
                "admin@testuniv.edu"  # Normalized to lowercase
            )


class TestAuthenticationIntegration:
    """Test authentication integration across endpoints."""

    def test_auth_service_integration(self):
        """Test that auth service is integrated with API routes."""
        # Test that auth functions are imported and available
        from src.services.auth_service import get_current_user, has_permission

        # Test that auth functions work correctly
        user = get_current_user()
        assert user is not None
        assert user["role"] == "site_admin"

        # Test valid permission
        assert has_permission("manage_users") is True

        # Test invalid permission
        assert has_permission("nonexistent_permission") is False
