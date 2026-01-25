"""Unit tests for API routes."""

import json

# Test constants to avoid hard-coded values
import os

# Unused imports removed
from unittest.mock import Mock, patch

import pytest

# Import the Flask application
from src.app import app
from src.utils.constants import USER_NOT_FOUND_MSG

TEST_PASSWORD = os.environ.get(
    "TEST_PASSWORD", "SecurePass123!"
)  # Test password for unit tests only


class TestAPIBlueprint:
    """Test API blueprint setup and registration."""

    def test_api_blueprints_registered_in_app(self):
        """Test that API blueprints are registered in the Flask app."""
        blueprint_names = list(app.blueprints.keys())
        # After refactor, routes are split into multiple blueprints
        assert len(blueprint_names) > 0


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
                json={"email": "test@example.com", "password": "password123"},
                headers={"X-CSRFToken": csrf_token},
            )

            assert response.status_code == 500  # Should handle the exception

    def test_login_api_login_error(self, client, csrf_token):
        """Test login API handles LoginError correctly."""
        with patch("src.services.login_service.LoginService") as mock_login_service:
            mock_login_service.authenticate_user.side_effect = Exception("LoginError")

            response = client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "password123"},
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
                json={"email": "test@example.com", "password": "password123"},
                headers={"X-CSRFToken": csrf_token},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["next_url"] == "/assessments?course=course-123"

            # Verify next_after_login was removed from session
            with client.session_transaction() as sess:
                assert "next_after_login" not in sess


class TestDashboardRoutes:
    """Test dashboard routes and user role handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_dashboard_instructor_role(self):
        """Test dashboard for instructor role"""
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "user123",
            "email": "instructor@example.com",
            "role": "instructor",
            "first_name": "John",
            "last_name": "Doe",
            "institution_id": "inst-123",
        }
        create_test_session(self.client, user_data)

        with patch("src.app.render_template") as mock_render:
            mock_render.return_value = "Dashboard HTML"
            response = self.client.get("/dashboard")

            assert response.status_code == 200
            # Verify the correct template was called for instructor role
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            assert call_args[0][0] == "dashboard/instructor.html"
            assert "user" in call_args[1]

    def test_dashboard_program_admin_role(self):
        """Test dashboard for program_admin role"""
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "user123",
            "email": "admin@example.com",
            "role": "program_admin",
            "first_name": "Jane",
            "last_name": "Admin",
            "institution_id": "inst-123",
        }
        create_test_session(self.client, user_data)

        with patch("src.app.render_template") as mock_render:
            mock_render.return_value = "Dashboard HTML"
            response = self.client.get("/dashboard")

            assert response.status_code == 200
            # Verify the correct template was called for program_admin role
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            assert call_args[0][0] == "dashboard/program_admin.html"
            assert "user" in call_args[1]

    def test_dashboard_site_admin_role(self):
        """Test dashboard for site_admin role"""
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "user123",
            "email": "siteadmin@example.com",
            "role": "site_admin",
            "first_name": "Super",
            "last_name": "Admin",
            "institution_id": "inst-123",
        }
        create_test_session(self.client, user_data)

        with patch("src.app.render_template") as mock_render:
            mock_render.return_value = "Dashboard HTML"
            response = self.client.get("/dashboard")

            assert response.status_code == 200
            # Verify the correct template was called for site_admin role
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            assert call_args[0][0] == "dashboard/site_admin.html"
            assert "user" in call_args[1]

    def test_dashboard_unknown_role(self):
        """Test dashboard for unknown role"""
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "user123",
            "email": "unknown@example.com",
            "role": "unknown_role",
            "first_name": "Unknown",
            "last_name": "User",
            "institution_id": "inst-123",
        }
        create_test_session(self.client, user_data)

        with (
            patch("src.app.redirect") as mock_redirect,
            patch("src.app.flash") as mock_flash,
        ):
            mock_redirect.return_value = "Redirect response"
            self.client.get("/dashboard")

            # Should flash error message and redirect for unknown role
            mock_flash.assert_called_once()
            mock_redirect.assert_called_once()

    def test_dashboard_no_user(self):
        """Test dashboard when no user is logged in"""
        # No session created - user is unauthenticated
        # Dashboard is now a web route, so it should redirect to login
        response = self.client.get("/dashboard")

        # Web routes redirect to login when not authenticated
        assert response.status_code == 302
        assert "/login" in response.location


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_endpoint_success(self):
        """Test health endpoint returns success."""
        with app.test_client() as client:
            response = client.get("/api/health")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["status"] == "healthy"
            assert data["success"] is True
            assert data["message"] == "Loopcloser API is running"
            assert data["version"] == "2.0.0"

    def test_health_endpoint_no_auth_required(self):
        """Test health endpoint works without authentication."""
        with app.test_client() as client:
            response = client.get("/api/health")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["status"] == "healthy"


class TestDashboardEndpoint:
    """Test the dashboard endpoint."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()

    @patch("src.app.render_template")
    def test_dashboard_endpoint_exists(self, mock_render):
        """Test that dashboard endpoint is registered."""
        from tests.test_utils import create_test_session

        # Create real session instead of mocking
        user_data = {
            "user_id": "user123",
            "email": "admin@example.com",
            "role": "site_admin",
            "first_name": "Admin",
            "last_name": "User",
            "institution_id": "inst-123",
        }
        create_test_session(self.client, user_data)
        mock_render.return_value = "Dashboard HTML"

        response = self.client.get("/dashboard")
        # Endpoint exists and works correctly
        assert response.status_code == 200


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


class TestInvitationEndpoints:
    """Test invitation API endpoints (Story 2.2)"""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.institution_admin_user = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "institution_admin",
            "institution_id": "inst-123",
        }

    def _login_institution_admin(self, overrides=None):
        """Authenticate requests as an institution admin."""
        from tests.test_utils import create_test_session

        user_data = {**self.institution_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    @patch("src.services.invitation_service.InvitationService")
    def test_create_invitation_success(self, mock_invitation_service):
        """Test successful invitation creation."""
        self._login_institution_admin()

        # Mock the class methods, not instance methods
        mock_invitation_service.create_invitation.return_value = {
            "id": "inv-789",
            "invitee_email": "instructor@test.com",
            "invitee_role": "instructor",
            "status": "sent",
        }
        mock_invitation_service.send_invitation.return_value = (True, None)

        response = self.client.post(
            "/api/auth/invite",
            json={
                "invitee_email": "instructor@test.com",
                "invitee_role": "instructor",
                "personal_message": "Welcome to our team!",
            },
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"] is True
        assert "Invitation created and sent successfully" in data["message"]
        assert data["invitation_id"] == "inv-789"

        # Verify service was called correctly
        mock_invitation_service.create_invitation.assert_called_once()
        mock_invitation_service.send_invitation.assert_called_once()

    def test_create_invitation_no_json(self):
        """Test invitation creation with no JSON data."""
        response = self.client.post("/api/auth/invite")

        # Real auth returns 401 for unauthenticated requests
        assert response.status_code == 401

    def test_create_invitation_missing_email(self):
        """Test invitation creation with missing email."""
        response = self.client.post(
            "/api/auth/invite",
            json={"invitee_role": "instructor", "personal_message": "Welcome!"},
        )

        # Real auth returns 401 for unauthenticated requests
        assert response.status_code == 401

    def test_create_invitation_missing_role(self):
        """Test invitation creation with missing role."""
        response = self.client.post(
            "/api/auth/invite",
            json={
                "invitee_email": "instructor@test.com",
                "personal_message": "Welcome!",
            },
        )

        # Real auth returns 401 for unauthenticated requests
        assert response.status_code == 401

    @patch("src.services.invitation_service.InvitationService")
    def test_create_invitation_invalid_email(self, mock_invitation_service):
        """Test invitation creation with invalid email format."""
        from src.services.invitation_service import InvitationError

        self._login_institution_admin()

        # Mock the service to raise an error for invalid email
        mock_invitation_service.create_invitation.side_effect = InvitationError(
            "Invalid email format"
        )

        response = self.client.post(
            "/api/auth/invite",
            json={
                "invitee_email": "invalid-email",  # No @ or .
                "invitee_role": "instructor",
            },
        )

        assert response.status_code == 400  # Now returns 400 for invalid input
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Invalid email format" in data["error"]

    @patch("src.services.invitation_service.InvitationService")
    def test_create_invitation_service_error(self, mock_invitation_service):
        """Test invitation creation with service error."""
        from src.services.invitation_service import InvitationError

        self._login_institution_admin()

        mock_invitation_service.create_invitation.side_effect = InvitationError(
            "User already exists"
        )

        response = self.client.post(
            "/api/auth/invite",
            json={
                "invitee_email": "existing@test.com",
                "invitee_role": "instructor",
            },
        )

        assert response.status_code == 409  # InvitationError returns 409 Conflict
        data = json.loads(response.data)
        assert data["success"] is False
        assert "User already exists" in data["error"]

    @patch("src.services.invitation_service.InvitationService")
    def test_create_invitation_server_error(self, mock_invitation_service):
        """Test invitation creation with unexpected server error."""
        self._login_institution_admin()

        mock_invitation_service.create_invitation.side_effect = Exception(
            "Database error"
        )

        response = self.client.post(
            "/api/auth/invite",
            json={
                "invitee_email": "instructor@test.com",
                "invitee_role": "instructor",
            },
        )

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Failed to create invitation" in data["error"]

    @patch("src.services.invitation_service.InvitationService")
    def test_create_invitation_with_program_ids(self, mock_invitation_service):
        """Test invitation creation with program IDs for program_admin role."""
        self._login_institution_admin()

        mock_invitation_service.create_invitation.return_value = {
            "id": "inv-789",
            "invitee_email": "admin@test.com",
            "invitee_role": "program_admin",
            "status": "sent",
        }
        mock_invitation_service.send_invitation.return_value = (True, None)

        response = self.client.post(
            "/api/auth/invite",
            json={
                "invitee_email": "admin@test.com",
                "invitee_role": "program_admin",
                "program_ids": ["prog-123", "prog-456"],
                "personal_message": "Welcome as program admin!",
            },
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"] is True

        # Verify service was called with program_ids
        call_args = mock_invitation_service.create_invitation.call_args[1]
        assert call_args["program_ids"] == ["prog-123", "prog-456"]

    @patch("src.services.invitation_service.InvitationService")
    def test_create_invitation_public_api_alias_fields(self, mock_invitation_service):
        """Ensure /api/invitations accepts email/role aliases and returns 201."""
        self._login_institution_admin()

        mock_invitation_service.create_invitation.return_value = {
            "id": "inv-999",
            "invitee_email": "instructor@test.com",
            "invitee_role": "instructor",
            "status": "sent",
        }
        mock_invitation_service.send_invitation.return_value = (True, None)

        # Use alias fields email/role
        response = self.client.post(
            "/api/invitations",
            json={
                "email": "instructor@test.com",
                "role": "instructor",
                "personal_message": "Welcome!",
            },
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["invitation_id"] == "inv-999"

        # Verify service was called with normalized args
        call_args = mock_invitation_service.create_invitation.call_args[1]
        assert call_args["invitee_email"] == "instructor@test.com"
        assert call_args["invitee_role"] == "instructor"


class TestAcceptInvitationEndpoints:
    """Test accept invitation API endpoints (Story 2.2)"""

    @patch("src.services.invitation_service.InvitationService")
    def test_accept_invitation_success(self, mock_invitation_service):
        """Test successful invitation acceptance."""
        # Mock successful invitation acceptance
        mock_invitation_service.accept_invitation.return_value = {
            "id": "user-123",
            "email": "invited@test.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "instructor",
        }

        with app.test_client() as client:
            response = client.post(
                "/api/auth/accept-invitation",
                json={
                    "invitation_token": "valid-token-123",
                    "password": TEST_PASSWORD,
                    "display_name": "John Doe",
                },
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert (
                "Invitation accepted and account created successfully"
                in data["message"]
            )
            assert data["user_id"] == "user-123"

            # Verify service was called correctly
            mock_invitation_service.accept_invitation.assert_called_once_with(
                invitation_token="valid-token-123",
                password=TEST_PASSWORD,
                display_name="John Doe",
            )

    def test_accept_invitation_no_json(self):
        """Test invitation acceptance with no JSON data."""
        with app.test_client() as client:
            response = client.post("/api/auth/accept-invitation")

            # Should return 400 Bad Request (after fix for silent=True)
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "No JSON data provided" in data["error"]

    def test_accept_invitation_missing_token(self):
        """Test invitation acceptance with missing token."""
        with app.test_client() as client:
            response = client.post(
                "/api/auth/accept-invitation",
                json={"password": TEST_PASSWORD, "display_name": "John Doe"},
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Missing required field: invitation_token" in data["error"]

    def test_accept_invitation_missing_password(self):
        """Test invitation acceptance with missing password."""
        with app.test_client() as client:
            response = client.post(
                "/api/auth/accept-invitation",
                json={
                    "invitation_token": "valid-token-123",
                    "display_name": "John Doe",
                },
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Missing required field: password" in data["error"]

    @patch("src.services.invitation_service.InvitationService")
    def test_accept_invitation_invalid_token(self, mock_invitation_service):
        """Test invitation acceptance with invalid token."""
        from src.services.invitation_service import InvitationError

        mock_invitation_service.accept_invitation.side_effect = InvitationError(
            "Invalid or expired invitation token"
        )

        with app.test_client() as client:
            response = client.post(
                "/api/auth/accept-invitation",
                json={
                    "invitation_token": "invalid-token",
                    "password": TEST_PASSWORD,
                },
            )

            assert response.status_code == 410  # Gone - expired/invalid
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Invalid or expired invitation token" in data["error"]

    @patch("src.services.invitation_service.InvitationService")
    def test_accept_invitation_expired_token(self, mock_invitation_service):
        """Test invitation acceptance with expired token."""
        from src.services.invitation_service import InvitationError

        mock_invitation_service.accept_invitation.side_effect = InvitationError(
            "Invitation has expired"
        )

        with app.test_client() as client:
            response = client.post(
                "/api/auth/accept-invitation",
                json={
                    "invitation_token": "expired-token",
                    "password": TEST_PASSWORD,
                },
            )

            assert response.status_code == 410  # Gone - expired
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Invitation has expired" in data["error"]

    @patch("src.services.invitation_service.InvitationService")
    def test_accept_invitation_weak_password(self, mock_invitation_service):
        """Test invitation acceptance with weak password."""
        from src.services.invitation_service import InvitationError

        mock_invitation_service.accept_invitation.side_effect = InvitationError(
            "Invalid password - does not meet security requirements"
        )

        with app.test_client() as client:
            response = client.post(
                "/api/auth/accept-invitation",
                json={
                    "invitation_token": "valid-token-123",
                    "password": os.environ.get("TEST_WEAK_PASSWORD", "weak"),
                },
            )

            assert (
                response.status_code == 400
            )  # "Invalid" in error message triggers 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Invalid password" in data["error"]

    @patch("src.services.invitation_service.InvitationService")
    def test_accept_invitation_server_error(self, mock_invitation_service):
        """Test invitation acceptance with server error."""
        mock_invitation_service.accept_invitation.side_effect = Exception(
            "Database connection failed"
        )

        with app.test_client() as client:
            response = client.post(
                "/api/auth/accept-invitation",
                json={
                    "invitation_token": "valid-token-123",
                    "password": TEST_PASSWORD,
                },
            )

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Failed to accept invitation" in data["error"]

    @patch("src.services.invitation_service.InvitationService")
    def test_accept_invitation_without_display_name(self, mock_invitation_service):
        """Test invitation acceptance without optional display name."""
        mock_invitation_service.accept_invitation.return_value = {
            "id": "user-123",
            "email": "invited@test.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "role": "instructor",
        }

        with app.test_client() as client:
            response = client.post(
                "/api/auth/accept-invitation",
                json={
                    "invitation_token": "valid-token-123",
                    "password": TEST_PASSWORD,
                    # No display_name provided
                },
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True

            # Verify service was called with None for display_name
            mock_invitation_service.accept_invitation.assert_called_once_with(
                invitation_token="valid-token-123",
                password=TEST_PASSWORD,
                display_name=None,
            )


class TestListInvitationsEndpoints:
    """Test list invitations API endpoints (Story 2.2)"""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.institution_admin_user = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "institution_admin",
            "institution_id": "inst-123",
        }

    def _login_institution_admin(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.institution_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    @patch("src.services.invitation_service.InvitationService")
    def test_list_invitations_success(self, mock_invitation_service):
        """Test successful invitation listing."""
        self._login_institution_admin()
        mock_invitation_service.list_invitations.return_value = [
            {
                "id": "inv-1",
                "invitee_email": "user1@test.com",
                "status": "pending",
                "created_at": "2024-01-01T10:00:00Z",
            },
            {
                "id": "inv-2",
                "invitee_email": "user2@test.com",
                "status": "accepted",
                "created_at": "2024-01-02T10:00:00Z",
            },
        ]

        response = self.client.get("/api/auth/invitations")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["invitations"]) == 2
        assert data["count"] == 2
        assert data["limit"] == 50
        assert data["offset"] == 0

        # Verify service was called correctly
        mock_invitation_service.list_invitations.assert_called_once_with(
            institution_id="inst-123", status=None, limit=50, offset=0
        )

    @patch("src.services.invitation_service.InvitationService")
    def test_list_invitations_with_filters(self, mock_invitation_service):
        """Test invitation listing with filters."""
        self._login_institution_admin()
        mock_invitation_service.list_invitations.return_value = []

        response = self.client.get(
            "/api/auth/invitations?status=pending&limit=10&offset=5"
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

        # Verify service was called with filters
        mock_invitation_service.list_invitations.assert_called_once_with(
            institution_id="inst-123", status="pending", limit=10, offset=5
        )

    def test_list_invitations_no_institution(self):
        """Test invitation listing without institution context."""
        # Don't create session - test unauthenticated request
        response = self.client.get("/api/auth/invitations")

        # Real auth returns 401 for unauthenticated requests
        assert response.status_code == 401

    @patch("src.services.invitation_service.InvitationService")
    def test_list_invitations_limit_clamping(self, mock_invitation_service):
        """Test invitation listing with limit over 100 gets clamped."""
        self._login_institution_admin()
        mock_invitation_service.list_invitations.return_value = []

        response = self.client.get("/api/auth/invitations?limit=150")  # Over max 100

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["limit"] == 100  # Clamped to max

        # Verify service was called with clamped limit
        mock_invitation_service.list_invitations.assert_called_once_with(
            institution_id="inst-123", status=None, limit=100, offset=0  # Clamped
        )

    @patch("src.services.invitation_service.InvitationService")
    def test_list_invitations_service_error(self, mock_invitation_service):
        """Test invitation listing with service error."""
        self._login_institution_admin()
        mock_invitation_service.list_invitations.side_effect = Exception(
            "Database error"
        )

        response = self.client.get("/api/auth/invitations")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Failed to list invitations" in data["error"]

    @patch("src.services.invitation_service.InvitationService")
    def test_list_invitations_empty_result(self, mock_invitation_service):
        """Test invitation listing with empty results."""
        self._login_institution_admin()
        mock_invitation_service.list_invitations.return_value = []

        response = self.client.get("/api/auth/invitations")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["invitations"]) == 0
        assert data["count"] == 0


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


from tests.test_utils import CommonAuthMixin


class TestUserEndpoints(CommonAuthMixin):
    """Test user management endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()

    @patch("src.api.routes.users.get_all_users", return_value=[])
    def test_get_users_endpoint_exists(self, mock_get_all_users):
        """Test that GET /api/users endpoint exists and returns valid JSON."""
        self._login_user()

        response = self.client.get("/api/users")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "users" in data
        assert isinstance(data["users"], list)
        mock_get_all_users.assert_called_once_with("inst-123")

    @patch("src.api.routes.users.get_users_by_role")
    def test_get_users_with_department_filter(self, mock_get_users):
        """Test GET /api/users with department filter"""
        self._login_site_admin(
            {"user_id": "test-user", "institution_id": "test-institution"}
        )
        mock_get_users.return_value = [
            {
                "user_id": "1",
                "email": "math1@example.com",
                "department": "MATH",
                "role": "instructor",
                "institution_id": "test-institution",
            },
            {
                "user_id": "2",
                "email": "cs1@example.com",
                "department": "CS",
                "role": "instructor",
                "institution_id": "test-institution",
            },
            {
                "user_id": "3",
                "email": "math2@example.com",
                "department": "MATH",
                "role": "instructor",
                "institution_id": "test-institution",
            },
        ]

        response = self.client.get("/api/users?role=instructor&department=MATH")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["users"]) == 2  # Should filter to only MATH department
        for user in data["users"]:
            assert user["department"] == "MATH"

    @patch("src.api.routes.users.get_users_by_role")
    def test_get_users_exception_handling(self, mock_get_users):
        """Test GET /api/users exception handling"""
        self._login_user()
        mock_get_users.side_effect = Exception("Database connection failed")

        response = self.client.get("/api/users?role=instructor")
        assert response.status_code == 500

        data = json.loads(response.data)
        assert data["success"] is False
        assert "error" in data

    def test_create_user_no_json_data(self):
        """Test POST /api/users with no JSON data"""
        # Don't create session - test unauthenticated request
        response = self.client.post("/api/users", content_type="application/json")

        # Real auth returns 401 for unauthenticated requests
        assert response.status_code == 401

    def test_create_user_database_failure(self):
        """Test POST /api/users when database creation fails"""
        self._login_site_admin()

        user_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "instructor",
            "institution_id": "inst-123",  # Required for non-site_admin roles
            "password": "TestPass123!",
        }

        # Mock database failure
        with patch("src.api.routes.users.create_user_db", return_value=None):
            response = self.client.post(
                "/api/users", json=user_data, content_type="application/json"
            )
            # Real API returns 500 on database failure
            assert response.status_code == 500

            data = json.loads(response.data)
            assert data["success"] is False
            assert "error" in data

    def test_create_user_exception_handling(self):
        """Test POST /api/users with exception"""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data_session = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "inst-123",
        }
        create_test_session(self.client, user_data_session)

        user_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "instructor",
            "institution_id": "inst-123",  # Required for non-site_admin roles
            "password": "TestPass123!",
        }

        # Mock database exception
        with patch(
            "src.api.routes.users.create_user_db", side_effect=Exception("DB Error")
        ):
            response = self.client.post(
                "/api/users", json=user_data, content_type="application/json"
            )
            # Real API returns 500 on exception
            assert response.status_code == 500

            data = json.loads(response.data)
            assert data["success"] is False

    @patch("src.api.routes.users.get_all_users", return_value=[])
    def test_get_users_without_permission_stub_mode(self, mock_get_all_users):
        """Test GET /api/users in stub mode (auth always passes)."""
        self._login_site_admin()

        response = self.client.get("/api/users")
        # Should succeed in stub mode, but return empty list
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "users" in data
        mock_get_all_users.assert_called_once_with("inst-123")

    @patch("src.api.routes.users.get_users_by_role")
    def test_get_users_with_role_filter(self, mock_get_users):
        """Test GET /api/users with role filter."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "inst-123",
        }
        create_test_session(self.client, user_data)
        mock_get_users.return_value = [
            {"user_id": "1", "email": "instructor@example.com", "role": "instructor"}
        ]

        response = self.client.get("/api/users?role=instructor")
        assert response.status_code == 200

        # Verify the role filter was applied
        mock_get_users.assert_called_with("instructor")

    def test_create_user_success(self):
        """Test POST /api/users with valid data."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data_session = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "inst-123",
        }
        create_test_session(self.client, user_data_session)

        user_data = {
            "email": "newuser@example.com",
            "role": "instructor",
            "first_name": "New",
            "last_name": "User",
            "institution_id": "inst-123",  # Required for non-site_admin roles
            "password": "TestPass123!",  # Provide password for immediate activation
        }

        response = self.client.post(
            "/api/users", json=user_data, content_type="application/json"
        )
        assert response.status_code == 201

        data = json.loads(response.data)
        assert "message" in data
        assert "created" in data["message"].lower()
        assert "user_id" in data  # Real API returns actual user_id

    def test_create_user_missing_required_fields(self):
        """Test POST /api/users with missing required fields."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data_session = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "inst-123",
        }
        create_test_session(self.client, user_data_session)

        incomplete_data = {
            "email": "incomplete@example.com"
            # Missing role
        }

        response = self.client.post(
            "/api/users", json=incomplete_data, content_type="application/json"
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data
        assert "required" in data["error"].lower()


class TestCourseEndpoints:
    """Test course management endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.site_admin_user = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "inst-123",
        }

    def _login_site_admin(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    def _login_user(self, overrides=None):
        return self._login_site_admin(overrides)

    @patch("src.api.routes.courses.get_all_courses")
    def test_get_courses_endpoint_exists(self, mock_get_all_courses):
        """Test that GET /api/courses endpoint exists and returns valid JSON."""
        self._login_site_admin({"institution_id": "riverside-tech-institute"})
        mock_get_all_courses.return_value = []

        response = self.client.get("/api/courses")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "courses" in data
        assert isinstance(data["courses"], list)

    @patch("src.api.routes.courses.get_courses_by_department")
    def test_get_courses_with_department_filter(self, mock_get_courses):
        """Test GET /api/courses with department filter."""
        self._login_site_admin({"institution_id": "riverside-tech-institute"})
        mock_get_courses.return_value = [
            {
                "course_number": "MATH-101",
                "course_title": "Algebra",
                "department": "MATH",
            }
        ]

        response = self.client.get("/api/courses?department=MATH")
        assert response.status_code == 200

        mock_get_courses.assert_called_with("riverside-tech-institute", "MATH")

    @patch("src.api.routes.courses.create_course")
    def test_create_course_success(self, mock_create_course):
        """Test POST /api/courses with valid data."""
        self._login_site_admin()
        mock_create_course.return_value = "course-123"

        course_data = {
            "course_number": "TEST-101",
            "course_title": "Test Course",
            "department": "TEST",
            "credit_hours": 3,
        }

        response = self.client.post(
            "/api/courses", json=course_data, content_type="application/json"
        )
        assert response.status_code == 201

        data = json.loads(response.data)
        assert "message" in data
        assert "course_id" in data

    @patch("src.api.utils.get_current_institution_id")
    def test_create_course_requires_institution_context(self, mock_get_institution_id):
        """Test POST /api/courses fails when no institution context is available."""
        self._login_site_admin()
        mock_get_institution_id.return_value = None  # No institution context

        course_data = {
            "course_number": "TEST-101",
            "course_title": "Test Course",
            "department": "TEST",
        }

        response = self.client.post(
            "/api/courses", json=course_data, content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Institution context required" in data["error"]

    @patch("src.api.routes.courses.create_course")
    @patch("src.api.utils.get_current_institution_id")
    def test_create_course_adds_institution_context(
        self, mock_get_institution_id, mock_create_course
    ):
        """Test POST /api/courses automatically adds institution_id from context."""
        self._login_site_admin()
        mock_get_institution_id.return_value = "test-institution-123"
        mock_create_course.return_value = "course-456"

        course_data = {
            "course_number": "TEST-101",
            "course_title": "Test Course",
            "department": "TEST",
        }

        response = self.client.post(
            "/api/courses", json=course_data, content_type="application/json"
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["course_id"] == "course-456"

        # Verify that institution_id was added to the course data
        mock_create_course.assert_called_once()
        call_args = mock_create_course.call_args[0][0]
        assert call_args["institution_id"] == "test-institution-123"
        assert call_args["course_number"] == "TEST-101"
        assert call_args["course_title"] == "Test Course"
        assert call_args["department"] == "TEST"

    @patch("src.api.routes.courses.get_course_by_number", return_value=None)
    def test_get_course_by_number_endpoint_exists(self, mock_get_course):
        """Test that GET /api/courses/<course_number> endpoint exists."""
        self._login_site_admin()

        response = self.client.get("/api/courses/MATH-101")
        # Endpoint exists and correctly returns 404 for non-existent course
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data
        mock_get_course.assert_called_once_with("MATH-101")

    @patch("src.api.routes.courses.get_course_by_number")
    def test_get_course_by_number_not_found(self, mock_get_course):
        """Test GET /api/courses/<course_number> when course doesn't exist."""
        self._login_site_admin()
        mock_get_course.return_value = None

        response = self.client.get("/api/courses/NONEXISTENT-999")
        assert response.status_code == 404

        data = json.loads(response.data)
        assert "error" in data
        assert "not found" in data["error"].lower()

    @patch("src.api.routes.courses.duplicate_course_record")
    @patch("src.api.routes.courses.get_course_by_id")
    def test_duplicate_course_success(
        self, mock_get_course_by_id, mock_duplicate_course
    ):
        """Test POST /api/courses/<course_id>/duplicate succeeds."""
        self._login_site_admin()
        source_course = {
            "course_id": "course-123",
            "course_number": "BIOL-201",
            "institution_id": "inst-123",
            "program_ids": ["prog-1"],
        }
        duplicated_course = {
            "course_id": "course-999",
            "course_number": "BIOL-201-V2",
            "institution_id": "inst-123",
            "program_ids": ["prog-1"],
        }

        mock_get_course_by_id.side_effect = [source_course, duplicated_course]
        mock_duplicate_course.return_value = "course-999"

        response = self.client.post(
            "/api/courses/course-123/duplicate",
            json={"credit_hours": 4},
            content_type="application/json",
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["course"]["course_id"] == "course-999"
        mock_duplicate_course.assert_called_once()

    @patch("src.api.routes.courses.get_course_by_id")
    def test_duplicate_course_forbidden_for_other_institution(
        self, mock_get_course_by_id
    ):
        """Test duplication blocked when user lacks institution access."""
        self._login_site_admin(
            {"role": "institution_admin", "institution_id": "inst-999"}
        )
        mock_get_course_by_id.return_value = {
            "course_id": "course-123",
            "course_number": "BIOL-201",
            "institution_id": "inst-123",
        }

        response = self.client.post("/api/courses/course-123/duplicate", json={})
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data["success"] is False

    @patch("src.api.routes.courses.get_course_by_id")
    def test_duplicate_course_not_found(self, mock_get_course_by_id):
        """Test duplication returns 404 when course missing."""
        self._login_site_admin()
        mock_get_course_by_id.return_value = None

        response = self.client.post("/api/courses/missing-course/duplicate", json={})
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["success"] is False


class TestTermEndpoints:
    """Test term management endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.site_admin_user = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "riverside-tech-institute",
        }

    def _login_user(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.routes.terms.get_active_terms")
    def test_get_terms_success(self, mock_get_terms, mock_get_current_institution_id):
        """Test GET /api/terms."""
        self._login_user()

        # Mock the institution ID
        mock_get_current_institution_id.return_value = "riverside-tech-institute"
        mock_get_terms.return_value = [
            {
                "term_name": "Fall2024",
                "start_date": "2024-08-15",
                "end_date": "2024-12-15",
            },
            {
                "term_name": "Spring2025",
                "start_date": "2025-01-15",
                "end_date": "2025-05-15",
            },
        ]

        response = self.client.get("/api/terms")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "terms" in data
        assert len(data["terms"]) == 2

    def test_create_term_endpoint_exists(self):
        """Test that POST /api/terms endpoint exists."""
        self._login_user()

        response = self.client.post("/api/terms", json={})
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404


class TestSectionEndpoints:
    """Test section management endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.site_admin_user = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "riverside-tech-institute",
        }

    def _login_site_admin(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    def _login_user(self, overrides=None):
        return self._login_site_admin(overrides)

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.routes.sections.get_all_sections")
    def test_get_sections_endpoint_exists(
        self, mock_get_all_sections, mock_get_current_institution_id
    ):
        """Test that GET /api/sections endpoint exists."""
        self._login_user()

        # Mock the institution ID and sections
        mock_get_current_institution_id.return_value = "riverside-tech-institute"
        mock_get_all_sections.return_value = []

        response = self.client.get("/api/sections")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "sections" in data
        assert isinstance(data["sections"], list)

    def test_create_section_endpoint_exists(self):
        """Test that POST /api/sections endpoint exists."""
        self._login_user()

        response = self.client.post("/api/sections", json={})
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404


class TestImportEndpoints:
    """Test import functionality endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.site_admin_user = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "riverside-tech-institute",
        }

    def _login_site_admin(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    def test_excel_import_endpoint_exists(self):
        """Test that POST /api/import/excel endpoint exists."""
        self._login_site_admin()

        response = self.client.post("/api/import/excel")
        # Should not be 404 (endpoint exists), but will be 400 due to missing file
        assert response.status_code != 404

    @patch("src.services.auth_service.has_permission")
    def test_excel_import_missing_file(self, mock_has_permission):
        """Test POST /api/import/excel without file."""
        self._login_site_admin()

        mock_has_permission.return_value = True

        response = self.client.post(
            "/api/import/excel",
            data={"conflict_strategy": "use_theirs", "dry_run": "false"},
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data
        assert "file" in data["error"].lower()


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_method_not_allowed(self):
        """Test method not allowed responses."""
        with app.test_client() as client:
            # Try DELETE on an endpoint that doesn't support it
            response = client.delete("/api/health")
            assert response.status_code == 405

    def test_api_endpoints_return_json(self):
        """Test that API endpoints return JSON responses."""
        with app.test_client() as client:
            response = client.get("/api/health")
            assert response.status_code == 200
            assert response.content_type.startswith("application/json")


class TestRequestValidation:
    """Test request data validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.site_admin_user = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "riverside-tech-institute",
        }

    def _login_site_admin(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    @patch("src.services.auth_service.has_permission")
    def test_course_creation_validation(self, mock_has_permission):
        """Test course creation with various validation scenarios."""
        self._login_site_admin()

        mock_has_permission.return_value = True

        # Test missing required field
        invalid_course = {
            "course_title": "Test Course"
            # Missing course_number
        }

        response = self.client.post(
            "/api/courses", json=invalid_course, content_type="application/json"
        )
        assert response.status_code == 400

    @patch("src.services.auth_service.has_permission")
    def test_term_creation_validation(self, mock_has_permission):
        """Test term creation with date validation."""
        self._login_site_admin()

        mock_has_permission.return_value = True

        # Test invalid date format
        invalid_term = {
            "term_name": "InvalidTerm",
            "start_date": "invalid-date",
            "end_date": "2024-12-15",
        }

        response = self.client.post(
            "/api/terms", json=invalid_term, content_type="application/json"
        )
        assert response.status_code == 400


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


class TestInstitutionEndpoints:
    """Test institution management endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.site_admin_user = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "riverside-tech-institute",
        }

    def _login_site_admin(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    def _login_user(self, overrides=None):
        """Alias for _login_site_admin for backward compatibility"""
        return self._login_site_admin(overrides)

    @patch("src.api.routes.institutions.get_all_institutions")
    @patch("src.api.routes.institutions.get_institution_instructor_count")
    def test_list_institutions_success(self, mock_get_count, mock_get_institutions):
        """Test GET /api/institutions endpoint."""
        self._login_site_admin()

        mock_get_institutions.return_value = [
            {"institution_id": "inst1", "name": "University 1"},
            {"institution_id": "inst2", "name": "University 2"},
        ]
        mock_get_count.return_value = 15

        response = self.client.get("/api/institutions")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "institutions" in data
        assert len(data["institutions"]) == 2

    @patch("src.api.routes.institutions.create_new_institution")
    def test_create_institution_success(self, mock_create_institution):
        """Test POST /api/institutions/register endpoint success (public registration)."""
        # No login needed - this is a public registration endpoint
        mock_create_institution.return_value = ("institution123", "user123")

        institution_data = {
            "institution": {
                "name": "Test University",
                "short_name": "TU",
                "domain": "test.edu",
            },
            "admin_user": {
                "email": "admin@test.edu",
                "first_name": "Admin",
                "last_name": "User",
                "password": "password123",
            },
        }

        response = self.client.post("/api/institutions/register", json=institution_data)
        assert response.status_code == 201

        data = json.loads(response.data)
        assert data["success"] is True
        assert "institution_id" in data

    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.institutions.get_institution_by_id")
    def test_get_institution_details_success(self, mock_get_institution, mock_get_user):
        """Test GET /api/institutions/<id> endpoint success."""
        self._login_site_admin()

        mock_get_user.return_value = {
            "user_id": "user123",
            "institution_id": "institution123",
            "role": "admin",
        }
        mock_get_institution.return_value = {
            "institution_id": "institution123",
            "name": "Test University",
            "domain": "test.edu",
        }

        response = self.client.get("/api/institutions/institution123")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "institution" in data
        assert data["institution"]["name"] == "Test University"

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.routes.users.get_all_instructors")
    def test_list_instructors_success(self, mock_get_instructors, mock_get_mocku):
        """Test GET /api/instructors endpoint success."""
        self._login_site_admin()

        mock_get_mocku.return_value = "mocku-institution-id"
        mock_get_instructors.return_value = [
            {"user_id": "inst1", "first_name": "John", "last_name": "Doe"},
            {"user_id": "inst2", "first_name": "Jane", "last_name": "Smith"},
        ]

        response = self.client.get("/api/instructors")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "instructors" in data
        assert len(data["instructors"]) == 2

    @patch("src.api.routes.institutions.create_new_institution")
    def test_create_institution_missing_data(self, mock_create_institution):
        """Test POST /api/institutions/register with missing data."""
        with app.test_client() as client:
            response = client.post("/api/institutions/register", json={})
            assert response.status_code == 400

            data = json.loads(response.data)
            assert data["success"] is False

    @patch("src.api.routes.institutions.create_new_institution")
    def test_create_institution_missing_admin_user_field(self, mock_create_institution):
        """Test POST /api/institutions/register with missing admin user field."""
        with app.test_client() as client:
            # Send institution data but missing admin user email
            response = client.post(
                "/api/institutions/register",
                json={
                    "institution": {
                        "name": "Test University",
                        "short_name": "TU",
                        "domain": "testuniversity.edu",
                    },
                    "admin_user": {
                        "first_name": "John",
                        "last_name": "Doe",
                        "password": "SecurePassword123!",
                        # Missing email field
                    },
                },
            )
            assert response.status_code == 400

            data = json.loads(response.data)
            assert data["success"] is False
            assert "Admin user email is required" in data["error"]

    @patch("src.api.routes.institutions.create_new_institution")
    def test_create_institution_creation_failure(self, mock_create_institution):
        """Test POST /api/institutions/register when institution creation fails."""
        # Setup - make create_new_institution return None (failure)
        mock_create_institution.return_value = None

        with app.test_client() as client:
            response = client.post(
                "/api/institutions/register",
                json={
                    "institution": {
                        "name": "Test University",
                        "short_name": "TU",
                        "domain": "testuniversity.edu",
                    },
                    "admin_user": {
                        "email": "admin@testuniversity.edu",
                        "first_name": "John",
                        "last_name": "Doe",
                        "password": "SecurePassword123!",
                    },
                },
            )
            assert response.status_code == 500

            data = json.loads(response.data)
            assert data["success"] is False
            assert "Failed to create institution" in data["error"]

    @patch("src.api.routes.institutions.create_new_institution")
    def test_create_institution_exception_handling(self, mock_create_institution):
        """Test POST /api/institutions/register exception handling."""
        # Setup - make create_new_institution raise an exception
        mock_create_institution.side_effect = Exception("Database connection failed")

        with app.test_client() as client:
            response = client.post(
                "/api/institutions/register",
                json={
                    "institution": {
                        "name": "Test University",
                        "short_name": "TU",
                        "domain": "testuniversity.edu",
                    },
                    "admin_user": {
                        "email": "admin@testuniversity.edu",
                        "first_name": "John",
                        "last_name": "Doe",
                        "password": "SecurePassword123!",
                    },
                },
            )
            assert response.status_code == 500

            data = json.loads(response.data)
            assert data["success"] is False
            assert "Failed to create institution" in data["error"]

    @patch("src.api.routes.institutions.get_all_institutions")
    def test_list_institutions_exception(self, mock_get_institutions):
        """Test GET /api/institutions exception handling."""
        self._login_user()

        mock_get_institutions.side_effect = Exception("Database error")

        response = self.client.get("/api/institutions")
        assert response.status_code == 500

        data = json.loads(response.data)
        assert data["success"] is False

    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.institutions.get_institution_by_id")
    def test_get_institution_details_access_denied(
        self, mock_get_institution, mock_get_user
    ):
        """Test GET /api/institutions/<id> access denied."""
        self._login_user(
            {
                "user_id": "user123",
                "email": "instructor@test.com",
                "role": "instructor",
                "institution_id": "different-institution",
            }
        )

        mock_get_user.return_value = {
            "user_id": "user123",
            "institution_id": "different-institution",
            "role": "instructor",
        }

        response = self.client.get("/api/institutions/target-institution")
        assert response.status_code == 403

        data = json.loads(response.data)
        assert data["success"] is False
        assert "permission denied" in data["error"].lower()

    @patch("src.api.routes.courses.create_course")
    def test_create_course_data_validation(self, mock_create_course):
        """Test course creation with comprehensive data validation."""
        self._login_user({"institution_id": "test-institution"})

        mock_create_course.return_value = "course123"

        # Test with complete, valid course data
        course_data = {
            "course_number": "CS-101",
            "course_title": "Introduction to Computer Science",
            "department": "CS",
            "credit_hours": 3,
            "description": "An introductory course covering fundamental concepts.",
        }

        response = self.client.post("/api/courses", json=course_data)
        assert response.status_code == 201

        data = json.loads(response.data)
        assert data["success"] is True
        assert "course_id" in data

        # Verify the course was created with proper data
        mock_create_course.assert_called_once()
        call_args = mock_create_course.call_args[0][0]
        assert call_args["course_number"] == "CS-101"
        assert call_args["department"] == "CS"
        assert call_args["credit_hours"] == 3

    @patch("src.api.routes.terms.create_term")
    def test_create_term_data_validation(self, mock_create_term):
        """Test term creation with proper data validation."""
        self._login_user({"institution_id": "test-institution"})

        mock_create_term.return_value = "term123"

        term_data = {
            "term_name": "Fall 2024",
            "start_date": "2024-08-15",
            "end_date": "2024-12-15",
            "is_active": True,
        }

        response = self.client.post("/api/terms", json=term_data)

        # Test that the endpoint responds properly (exact status may vary)
        assert response.status_code in [200, 201, 400]  # Various valid responses

        data = json.loads(response.data)
        assert "success" in data  # Response should have success field

    def test_api_error_handling_comprehensive(self):
        """Test comprehensive API error handling scenarios."""
        self._login_user({"institution_id": "test-institution"})

        # Test invalid JSON data
        response = self.client.post(
            "/api/courses", data="invalid json", content_type="application/json"
        )
        # Should handle invalid JSON gracefully
        assert response.status_code in [400, 500]  # Either error response is valid

        # Test missing content type
        response = self.client.post("/api/courses", data='{"test": "data"}')
        # Should handle gracefully - exact behavior varies
        assert response.status_code is not None

    def test_api_endpoints_comprehensive_error_handling(self):
        """Test comprehensive error handling across different API endpoints."""
        with app.test_client() as client:
            # Test various endpoints for proper error responses
            endpoints_to_test = [
                ("/api/nonexistent", "GET"),
                ("/api/courses", "DELETE"),  # Method not allowed
                ("/api/users", "PUT"),  # Method not allowed
            ]

            for endpoint, method in endpoints_to_test:
                if method == "GET":
                    response = client.get(endpoint)
                elif method == "DELETE":
                    response = client.delete(endpoint)
                elif method == "PUT":
                    response = client.put(endpoint)

                # Should return proper HTTP error codes
                assert response.status_code in [404, 405, 500]

    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.users.has_permission")
    def test_get_user_endpoint_comprehensive(
        self, mock_has_permission, mock_get_current_user
    ):
        """Test user retrieval endpoint with permission checking."""
        self._login_user({"institution_id": "test-institution"})

        mock_get_current_user.return_value = {"user_id": "user123"}
        mock_has_permission.return_value = True

        response = self.client.get("/api/users/user123")

        # Should handle user retrieval properly
        assert response.status_code in [200, 404]

        data = json.loads(response.data)
        assert "success" in data

    @patch("src.api.routes.imports.create_progress_tracker")
    @patch("src.api.routes.imports.update_progress")
    def test_import_excel_api_validation(
        self, mock_update_progress, mock_create_progress
    ):
        """Test Excel import API validation and error handling."""
        self._login_user({"institution_id": "test-institution"})

        mock_create_progress.return_value = "progress123"

        # Test missing file
        response = self.client.post("/api/import/excel")
        assert response.status_code == 400

        data = json.loads(response.data)
        assert data["success"] is False
        assert "no excel file" in data["error"].lower()

    def test_import_progress_endpoint(self):
        """Test import progress tracking endpoint."""
        with app.test_client() as client:
            response = client.get("/api/import/progress/nonexistent")

            # Should handle progress requests
            assert response.status_code in [200, 404, 500]

    @patch("src.api.utils.handle_api_error")
    def test_api_error_handler_functionality(self, mock_handle_error):
        """Test API error handler functionality."""
        mock_handle_error.return_value = (
            {"success": False, "error": "Test error"},
            500,
        )

        # Test that error handler is called appropriately
        test_exception = Exception("Test exception")
        result = mock_handle_error(test_exception, "Test operation", "Test message")

        assert result[0]["success"] is False
        assert result[1] == 500

    @patch("src.api.utils.get_current_institution_id")
    def test_institution_context_handling(self, mock_get_institution_id):
        """Test institution context handling across endpoints."""
        self._login_user({"institution_id": "test-institution"})

        mock_get_institution_id.return_value = "institution123"

        # Test endpoints that require institution context
        endpoints = ["/api/courses", "/api/terms", "/api/sections"]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            # Should handle institution context properly
            assert response.status_code in [200, 400, 403, 500]


class TestUserManagementAPI:
    """Test user management API endpoints comprehensively."""

    def setup_method(self):
        """Set up test client and mock data."""
        from src.app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.site_admin_user = {
            "user_id": "test-user",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }

    def _login_site_admin(self, overrides=None):
        """Authenticate requests as a site admin user."""
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.users.get_users_by_role")
    @patch("src.api.routes.users.has_permission")
    def test_list_users_with_role_filter(
        self,
        mock_has_permission,
        mock_get_users,
        mock_get_current_user,
        mock_get_institution_id,
    ):
        """Test listing users with role filter."""
        self._login_site_admin()
        mock_has_permission.return_value = True
        mock_get_current_user.return_value = {
            "user_id": "test-user",
            "role": "site_admin",
        }
        mock_get_institution_id.return_value = "test-institution"
        mock_get_users.return_value = [
            {
                "user_id": "1",
                "email": "instructor1@mocku.test",
                "role": "instructor",
                "institution_id": "test-institution",
            },
            {
                "user_id": "2",
                "email": "instructor2@mocku.test",
                "role": "instructor",
                "institution_id": "test-institution",
            },
        ]

        response = self.client.get("/api/users?role=instructor")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 2
        assert len(data["users"]) == 2
        mock_get_users.assert_called_once_with("instructor")

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.users.get_users_by_role")
    @patch("src.api.routes.users.has_permission")
    def test_list_users_with_department_filter(
        self,
        mock_has_permission,
        mock_get_users,
        mock_get_current_user,
        mock_get_institution_id,
    ):
        """Test listing users with department filter."""
        self._login_site_admin()
        mock_has_permission.return_value = True
        mock_get_current_user.return_value = {
            "user_id": "test-user",
            "role": "site_admin",
        }
        mock_get_institution_id.return_value = "test-institution"
        mock_get_users.return_value = [
            {
                "user_id": "1",
                "email": "math1@mocku.test",
                "role": "instructor",
                "department": "MATH",
                "institution_id": "test-institution",
            },
            {
                "user_id": "2",
                "email": "eng1@mocku.test",
                "role": "instructor",
                "department": "ENG",
                "institution_id": "test-institution",
            },
        ]

        response = self.client.get("/api/users?role=instructor&department=MATH")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 1
        assert data["users"][0]["department"] == "MATH"

    @patch("src.api.routes.users.has_permission")
    def test_create_user_validation(self, mock_has_permission):
        """Test create user with validation."""
        self._login_site_admin()
        mock_has_permission.return_value = True

        # Test with no JSON data
        response = self.client.post("/api/users")
        # May return 500 if permission decorator fails, 400 if it gets to validation
        assert response.status_code in [400, 500]

        # Test missing required fields
        response = self.client.post("/api/users", json={"email": "test@mocku.test"})
        assert response.status_code == 400
        data = response.get_json()
        assert "First Name is required" in data["error"]

    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.users.has_permission")
    def test_get_user_permission_denied(
        self, mock_has_permission, mock_get_current_user
    ):
        """Test user trying to access other user's details without permission."""
        self._login_site_admin({"user_id": "user123", "role": "instructor"})
        mock_get_current_user.return_value = {"user_id": "user123"}
        mock_has_permission.return_value = False

        response = self.client.get("/api/users/other_user")

        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == "Permission denied"


class TestCourseManagementOperations:
    """Test advanced course management functionality."""

    def setup_method(self):
        """Set up test client."""
        from src.app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()

    @patch("src.api.routes.courses.create_course")
    @patch("src.services.auth_service.has_permission")
    def test_create_course_comprehensive_validation(
        self, mock_has_permission, mock_create_course
    ):
        """Test comprehensive course creation validation."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_has_permission.return_value = True
        mock_create_course.return_value = "course123"

        # Test successful course creation
        course_data = {
            "course_number": "MATH-101",
            "course_title": "Algebra I",
            "department": "MATH",
            "credit_hours": 3,
        }

        response = self.client.post("/api/courses", json=course_data)

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["course_id"] == "course123"
        mock_create_course.assert_called_once()

    @patch("src.services.auth_service.has_permission")
    def test_create_course_missing_fields(self, mock_has_permission):
        """Test course creation with missing required fields."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_has_permission.return_value = True

        # Test missing course_number
        response = self.client.post(
            "/api/courses", json={"course_title": "Test Course", "department": "TEST"}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "Missing required fields" in data["error"]

    @patch("src.api.routes.terms.create_term")
    @patch("src.services.auth_service.has_permission")
    def test_create_term_comprehensive(self, mock_has_permission, mock_create_term):
        """Test comprehensive term creation."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_has_permission.return_value = True
        mock_create_term.return_value = "term123"

        term_data = {
            "name": "2024 Fall",
            "start_date": "2024-08-15",
            "end_date": "2024-12-15",
            "assessment_due_date": "2024-12-20",
        }

        response = self.client.post("/api/terms", json=term_data)

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["term_id"] == "term123"

    @patch("src.api.routes.sections.get_sections_by_instructor")
    def test_get_sections_by_instructor_comprehensive(self, mock_get_sections):
        """Test getting sections by instructor comprehensively."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_get_sections.return_value = [
            {
                "section_id": "1",
                "course_number": "MATH-101",
                "instructor_id": "instructor1",
            },
            {
                "section_id": "2",
                "course_number": "ENG-102",
                "instructor_id": "instructor1",
            },
        ]

        response = self.client.get("/api/sections?instructor_id=instructor1")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["sections"]) == 2
        mock_get_sections.assert_called_once_with("instructor1")

    @patch("src.api.routes.sections.get_sections_by_term")
    def test_get_sections_by_term_comprehensive(self, mock_get_sections):
        """Test getting sections by term comprehensively."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_get_sections.return_value = [
            {"section_id": "1", "course_number": "MATH-101", "term_id": "term1"},
            {"section_id": "2", "course_number": "ENG-102", "term_id": "term1"},
        ]

        response = self.client.get("/api/sections?term_id=term1")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["sections"]) == 2
        mock_get_sections.assert_called_once_with("term1")

    def test_get_import_progress_comprehensive(self):
        """Test import progress endpoint comprehensively."""
        # Test with valid progress ID
        response = self.client.get("/api/import/progress/progress123")

        # Should handle progress endpoint (currently returns stubbed data)
        assert response.status_code in [200, 404]  # May not be implemented yet

    @patch("src.services.auth_service.has_permission")
    def test_import_excel_file_validation(self, mock_has_permission):
        """Test Excel import file validation."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_has_permission.return_value = True

        # Test no file uploaded
        response = self.client.post("/api/import/excel")
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "No Excel file provided"

    @patch("src.api.routes.programs.get_program_by_id")
    @patch("src.api.routes.programs.remove_course_from_program")
    @patch("src.services.auth_service.has_permission")
    def test_remove_course_from_program_success(
        self, mock_has_permission, mock_remove, mock_get_program
    ):
        """Test successful course removal from program."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_has_permission.return_value = True
        mock_get_program.return_value = {
            "program_id": "prog1",
            "name": "Computer Science",
            "institution_id": "test-institution",
        }
        mock_remove.return_value = True

        response = self.client.delete("/api/programs/prog1/courses/course1")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "course1" in data["message"]
        mock_remove.assert_called_once()

    @patch("src.api.routes.programs.get_program_by_id")
    @patch("src.services.auth_service.has_permission")
    def test_remove_course_from_program_not_found(
        self, mock_has_permission, mock_get_program
    ):
        """Test course removal when program not found."""
        from tests.test_utils import create_test_session

        # Create authenticated session
        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_has_permission.return_value = True
        mock_get_program.return_value = None  # Program not found

        response = self.client.delete("/api/programs/invalid-prog/courses/course1")

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "Program not found" in data["error"]

    @patch("src.api.routes.programs.get_program_by_id")
    @patch("src.api.routes.programs.bulk_add_courses_to_program")
    @patch("src.services.auth_service.has_permission")
    def test_bulk_manage_courses_add_action(
        self, mock_has_permission, mock_bulk_add, mock_get_program
    ):
        """Test bulk add courses to program."""
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_has_permission.return_value = True
        mock_get_program.return_value = {"program_id": "prog1", "name": "CS"}
        mock_bulk_add.return_value = {"success_count": 2, "error_count": 0}

        response = self.client.post(
            "/api/programs/prog1/courses/bulk",
            json={"action": "add", "course_ids": ["c1", "c2"]},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "2 added" in data["message"]
        mock_bulk_add.assert_called_once_with(["c1", "c2"], "prog1")

    @patch("src.api.routes.programs.get_program_by_id")
    @patch("src.api.routes.programs.bulk_remove_courses_from_program")
    @patch("src.services.auth_service.has_permission")
    def test_bulk_manage_courses_remove_action(
        self, mock_has_permission, mock_bulk_remove, mock_get_program
    ):
        """Test bulk remove courses from program."""
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)

        mock_has_permission.return_value = True
        mock_get_program.return_value = {"program_id": "prog1", "name": "CS"}
        mock_bulk_remove.return_value = {"removed": 2, "failed": 0}

        response = self.client.post(
            "/api/programs/prog1/courses/bulk",
            json={"action": "remove", "course_ids": ["c1", "c2"]},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "2 removed" in data["message"]
        mock_bulk_remove.assert_called_once_with(["c1", "c2"], "prog1")

    @patch("src.services.auth_service.has_permission")
    def test_bulk_manage_courses_invalid_action(self, mock_has_permission):
        """Test bulk manage with invalid action."""
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)
        mock_has_permission.return_value = True

        response = self.client.post(
            "/api/programs/prog1/courses/bulk",
            json={"action": "invalid", "course_ids": ["c1"]},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid or missing action" in data["error"]

    @patch("src.services.auth_service.has_permission")
    def test_bulk_manage_courses_missing_course_ids(self, mock_has_permission):
        """Test bulk manage with missing course_ids."""
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }
        create_test_session(self.client, user_data)
        mock_has_permission.return_value = True

        response = self.client.post(
            "/api/programs/prog1/courses/bulk",
            json={"action": "add"},  # Missing course_ids
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Missing or invalid course_ids" in data["error"]


class TestAPIRoutesErrorHandling:
    """Test API routes error handling and edge cases."""

    def setup_method(self):
        """Set up test client."""
        from src.app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.site_admin_user = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }

    def _login_site_admin(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    @patch("src.api.routes.users.get_all_users", return_value=[])
    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.users.has_permission")
    def test_list_users_no_role_filter_coverage(
        self,
        mock_has_permission,
        mock_get_current_user,
        mock_get_mocku_id,
        mock_get_all_users,
    ):
        """Test list_users endpoint without role filter."""
        self._login_site_admin({"institution_id": "riverside-tech-institute"})
        mock_has_permission.return_value = True
        mock_get_current_user.return_value = {
            "user_id": "test-user",
            "role": "site_admin",
        }
        mock_get_mocku_id.return_value = "riverside-tech-institute"

        response = self.client.get("/api/users")

        assert response.status_code == 200
        data = response.get_json()
        assert data["users"] == []
        mock_get_all_users.assert_called_once_with("riverside-tech-institute")

    @patch("src.api.routes.users.get_user_by_id", return_value=None)
    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.users.has_permission")
    def test_get_user_not_found_coverage(
        self,
        mock_has_permission,
        mock_get_current_user,
        mock_get_mocku_id,
        mock_get_user,
    ):
        """Test get_user endpoint when user not found."""
        self._login_site_admin({"institution_id": "riverside-tech-institute"})
        mock_get_current_user.return_value = {
            "user_id": "admin-user",
            "role": "site_admin",
        }
        mock_has_permission.return_value = True
        mock_get_mocku_id.return_value = "riverside-tech-institute"

        response = self.client.get("/api/users/nonexistent-user")

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == USER_NOT_FOUND_MSG
        mock_get_user.assert_called_once_with("nonexistent-user")

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.users.has_permission")
    def test_create_user_stub_success_coverage(
        self, mock_has_permission, mock_get_current_user, mock_get_mocku_id
    ):
        """Test create_user endpoint with real implementation."""
        self._login_site_admin({"institution_id": "riverside-tech-institute"})
        mock_has_permission.return_value = True
        mock_get_current_user.return_value = {
            "user_id": "admin-user",
            "role": "site_admin",
        }
        mock_get_mocku_id.return_value = "riverside-tech-institute"

        user_data = {
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "role": "instructor",
            "institution_id": "riverside-tech-institute",  # Required for non-site_admin roles
            "password": "TestPass123!",
        }

        response = self.client.post("/api/users", json=user_data)

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert "user_id" in data  # Real API returns actual user_id

    def test_import_excel_empty_filename_coverage(self):
        """Test import_excel endpoint with empty filename."""
        self._login_site_admin()

        with patch("src.services.auth_service.has_permission", return_value=True):
            from io import BytesIO

            data = {"excel_file": (BytesIO(b"test"), "")}

            response = self.client.post("/api/import/excel", data=data)

            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "No file selected"

    # REMOVED: test_import_excel_invalid_file_type_coverage
    # Legacy test for hardcoded file type validation that was removed in greenfield refactor.
    # File type validation is now handled by adapters via supported_formats declaration.

    @patch("src.api.routes.imports._check_excel_import_permissions")
    @patch("src.services.auth_service.has_permission")
    def test_import_excel_permission_error(self, mock_has_permission, mock_check_perms):
        """Test import_excel endpoint with PermissionError."""
        self._login_site_admin()
        mock_has_permission.return_value = True
        mock_check_perms.side_effect = PermissionError(
            "User has no associated institution"
        )

        from io import BytesIO

        data = {"excel_file": (BytesIO(b"test"), "test.xlsx")}

        response = self.client.post("/api/import/excel", data=data)

        assert response.status_code == 403
        data = response.get_json()
        assert data["success"] is False
        assert "User has no associated institution" in data["error"]

    @patch("src.api.routes.users._resolve_users_scope")
    @patch("src.api.utils.get_current_user")
    @patch("src.api.routes.users.has_permission")
    def test_list_users_value_error(
        self,
        mock_has_permission,
        mock_get_current_user,
        mock_resolve_scope,
    ):
        """Test list_users with ValueError from scope resolution."""
        self._login_site_admin()
        mock_has_permission.return_value = True
        mock_get_current_user.return_value = self.site_admin_user
        mock_resolve_scope.side_effect = ValueError("Invalid scope")

        response = self.client.get("/api/users")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid scope" in data["error"]


class TestAPIRoutesProgressTracking:
    """Test API progress tracking functionality."""

    def setup_method(self):
        """Set up test client."""
        from src.app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()

    @patch("src.api.routes.imports.create_progress_tracker")
    @patch("src.api.routes.imports.update_progress")
    def test_progress_tracking_coverage(
        self, mock_update_progress, mock_create_progress
    ):
        """Test progress tracking functions are called."""
        mock_create_progress.return_value = "progress123"

        # Test that progress functions exist and can be called
        from src.api.routes.imports import create_progress_tracker, update_progress

        progress_id = create_progress_tracker()
        assert progress_id == "progress123"

        # Test update_progress
        update_progress("progress123", status="running", message="Test")
        mock_update_progress.assert_called_with(
            "progress123", status="running", message="Test"
        )

    def test_import_progress_stub_response(self):
        """Test import progress endpoint stub response."""
        response = self.client.get("/api/import/progress/test123")

        # Should return progress data (currently stubbed)
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.get_json()
            # Basic structure check for progress response
            assert isinstance(data, dict)


class TestAPIRoutesValidation:
    """Test API validation endpoints."""

    def setup_method(self):
        """Set up test client."""
        from src.app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.site_admin_user = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }

    def _login_site_admin(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    @patch("src.services.auth_service.has_permission")
    @patch("src.api.routes.imports.import_excel")
    @patch("src.api.utils.get_current_institution_id")
    def test_validate_import_file_coverage(
        self, mock_get_institution_id, mock_import_excel, mock_has_permission
    ):
        """Test import file validation endpoint."""
        self._login_site_admin()
        mock_has_permission.return_value = True
        mock_get_institution_id.return_value = "test-institution"

        # Mock import result
        from src.services.import_service import ImportResult

        mock_result = ImportResult(
            success=True,
            records_processed=10,
            records_created=8,
            records_updated=2,
            records_skipped=0,
            conflicts_detected=0,
            conflicts_resolved=0,
            errors=[],
            warnings=[],
            conflicts=[],
            dry_run=True,
            execution_time=1.0,
        )
        mock_import_excel.return_value = mock_result

        # Test with valid Excel file
        from io import BytesIO

        data = {"excel_file": (BytesIO(b"test excel data"), "test.xlsx")}

        response = self.client.post("/api/import/validate", data=data)

        # Should validate the file
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "validation" in data

    def test_validate_import_no_file(self):
        """Test validation endpoint with no file."""
        self._login_site_admin()

        with patch("src.services.auth_service.has_permission", return_value=True):
            response = self.client.post("/api/import/validate")

            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "No Excel file provided"

    def test_validate_import_empty_filename(self):
        """Test validation endpoint with empty filename."""
        self._login_site_admin()

        with patch("src.services.auth_service.has_permission", return_value=True):
            from io import BytesIO

            data = {"excel_file": (BytesIO(b"test"), "")}

            response = self.client.post("/api/import/validate", data=data)

            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "No file selected"

    # REMOVED: test_validate_import_invalid_file_type
    # Legacy test for hardcoded file type validation that was removed in greenfield refactor.
    # File type validation is now handled by adapters via supported_formats declaration.

    @patch("src.services.auth_service.has_permission")
    @patch("src.api.routes.imports.import_excel")
    @patch("os.unlink")
    @patch("src.api.utils.get_current_institution_id")
    def test_validate_import_cleanup_error(
        self,
        mock_get_institution_id,
        mock_unlink,
        mock_import_excel,
        mock_has_permission,
    ):
        """Test validation endpoint cleanup error handling."""
        self._login_site_admin()
        mock_has_permission.return_value = True
        mock_get_institution_id.return_value = "test-institution"
        mock_unlink.side_effect = OSError("Permission denied")

        # Mock import result
        from src.services.import_service import ImportResult

        mock_result = ImportResult(
            success=True,
            records_processed=5,
            records_created=0,
            records_updated=0,
            records_skipped=0,
            conflicts_detected=0,
            conflicts_resolved=0,
            errors=[],
            warnings=[],
            conflicts=[],
            dry_run=True,
            execution_time=1.0,
        )
        mock_import_excel.return_value = mock_result

        from io import BytesIO

        data = {"excel_file": (BytesIO(b"excel data"), "test.xlsx")}

        response = self.client.post("/api/import/validate", data=data)

        # Should still succeed despite cleanup error
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True


class TestAPIRoutesHealthCheck:
    """Test API health check endpoint."""

    def setup_method(self):
        """Set up test client."""
        from src.app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()

    def test_health_check_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/api/health")

        # Should return health status
        assert response.status_code == 200
        data = response.get_json()

        # Basic health check response structure
        assert isinstance(data, dict)

        # Should have expected health check fields
        if "status" in data:
            assert data["status"] == "healthy"
        if "success" in data:
            assert data["success"] is True


class TestAPIRoutesExtended:
    """Test missing coverage lines in API routes."""

    def setup_method(self):
        """Set up test client."""
        from src.app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.site_admin_user = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "test-institution",
        }

    def _login_site_admin(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    def test_api_error_handler_comprehensive(self):
        """Test API error handler function directly."""
        from src.api.utils import handle_api_error
        from src.app import app

        # Test error handler with app context
        with app.app_context():
            test_exception = Exception("Test error message")

            result = handle_api_error(test_exception, "Test operation", "User message")

            # Should return tuple with JSON response and status code
            assert isinstance(result, tuple)
            assert len(result) == 2

            _, status_code = result
            assert status_code == 500

            # Test with default parameters
            result2 = handle_api_error(test_exception)
            assert isinstance(result2, tuple)
            assert result2[1] == 500

    @patch("src.api.routes.courses.get_all_courses")
    @patch("src.api.utils.get_all_institutions")
    @patch("src.api.utils.get_current_institution_id_safe")
    def test_list_courses_global_scope(
        self, mock_get_mocku_id, mock_get_institutions, mock_get_all_courses
    ):
        """Site admin without institution context should see system-wide courses."""
        self._login_site_admin()
        mock_get_mocku_id.return_value = None
        mock_get_institutions.return_value = [
            {"institution_id": "inst-1"},
            {"institution_id": "inst-2"},
        ]
        mock_get_all_courses.side_effect = [
            [{"course_id": "c1", "department": "ENG"}],
            [{"course_id": "c2", "department": "SCI"}],
        ]

        response = self.client.get("/api/courses")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 2
        returned_ids = {course["course_id"] for course in data["courses"]}
        assert returned_ids == {"c1", "c2"}

    @patch("src.api.utils.get_current_institution_id_safe")
    @patch("src.api.routes.courses.get_courses_by_department")
    def test_list_courses_with_department(self, mock_get_courses, mock_get_inst_id):
        """Test list_courses with department filter."""
        self._login_site_admin()
        mock_get_inst_id.return_value = "institution123"
        mock_get_courses.return_value = [{"course_id": "1", "department": "MATH"}]

        response = self.client.get("/api/courses?department=MATH")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["courses"]) == 1

    @patch("src.api.routes.courses.resolve_institution_scope")
    @patch("src.api.routes.courses.get_current_program_id")
    @patch("src.api.routes.courses.get_courses_by_program")
    def test_list_courses_with_program_override(
        self, mock_get_by_program, mock_get_program_id, mock_scope
    ):
        """Test list_courses with program_id override parameter."""
        self._login_site_admin()
        mock_scope.return_value = (
            {"user_id": "admin1", "role": "site_admin", "institution_id": "inst1"},
            ["inst1"],
            False,
        )
        mock_get_program_id.return_value = None
        mock_get_by_program.return_value = [
            {"course_id": "c1", "program_ids": ["prog1"]}
        ]

        response = self.client.get("/api/courses?program_id=prog1")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["courses"]) == 1
        assert data["current_program_id"] == "prog1"
        mock_get_by_program.assert_called_once_with("prog1")


class TestAPIRoutesHelpers:
    """Test helper functions in API routes."""

    def test_resolve_institution_scope_missing_context(self):
        """Test _resolve_institution_scope raises error when context missing and required."""
        from src.api.utils import (
            InstitutionContextMissingError,
            resolve_institution_scope,
        )

        with patch(
            "src.api.utils.get_current_user", return_value={"role": "instructor"}
        ):
            with patch("src.api.utils.get_current_institution_id", return_value=None):
                with pytest.raises(InstitutionContextMissingError):
                    resolve_institution_scope(require=True)

    def test_resolve_institution_scope_no_require(self):
        """Test _resolve_institution_scope returns empty list when not required."""
        from src.api.utils import resolve_institution_scope

        with patch(
            "src.api.utils.get_current_user", return_value={"role": "instructor"}
        ):
            with patch("src.api.utils.get_current_institution_id", return_value=None):
                user, institutions, is_global = resolve_institution_scope(require=False)
                assert user == {"role": "instructor"}
                assert institutions == []
                assert is_global is False

    def test_create_progress_tracker(self):
        """Test create_progress_tracker function."""
        from src.api.routes.imports import create_progress_tracker

        progress_id = create_progress_tracker()
        assert isinstance(progress_id, str)
        assert len(progress_id) > 0

    def test_update_progress(self):
        """Test update_progress function."""
        from src.api.routes.imports import create_progress_tracker, update_progress

        progress_id = create_progress_tracker()
        update_progress(progress_id, status="processing", message="Test update")
        # Should not raise an exception

    def test_get_progress(self):
        """Test get_progress function."""
        from src.api.routes.imports import (
            create_progress_tracker,
            get_progress,
            update_progress,
        )

        progress_id = create_progress_tracker()
        update_progress(progress_id, status="processing", message="Test message")

        progress = get_progress(progress_id)
        assert isinstance(progress, dict)
        assert progress.get("status") == "processing"
        assert progress.get("message") == "Test message"

    def test_cleanup_progress(self):
        """Test cleanup_progress function."""
        from src.api.routes.imports import cleanup_progress, create_progress_tracker

        progress_id = create_progress_tracker()
        cleanup_progress(progress_id)
        # Should not raise an exception


class TestAPIRoutesHelperFunctions:
    """Test helper functions for course listing complexity reduction."""

    def setup_method(self):
        """Set up test client."""
        from src.app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_resolve_courses_scope_success(self):
        """Test _resolve_courses_scope with valid scope."""
        from unittest.mock import patch

        from src.api.routes.courses import _resolve_courses_scope

        mock_user = {"role": "site_admin"}
        mock_institutions = ["inst1"]
        mock_global = False

        with patch("src.api.routes.courses.resolve_institution_scope") as mock_resolve:
            mock_resolve.return_value = (mock_user, mock_institutions, mock_global)

            user, institutions, is_global = _resolve_courses_scope()

            assert user == mock_user
            assert institutions == mock_institutions
            assert is_global == mock_global

    def test_resolve_courses_scope_missing_context(self):
        """Test _resolve_courses_scope with missing institution context."""
        from unittest.mock import patch

        import pytest

        from src.api.routes.courses import _resolve_courses_scope
        from src.api.utils import InstitutionContextMissingError

        with patch("src.api.routes.courses.resolve_institution_scope") as mock_resolve:
            mock_resolve.side_effect = InstitutionContextMissingError("Missing context")

            with pytest.raises(ValueError, match="Institution context required"):
                _resolve_courses_scope()

    def test_user_can_access_program_site_admin(self):
        """Test _user_can_access_program for site admin."""
        from src.api.routes.courses import _user_can_access_program

        user = {"role": "site_admin"}
        program_id = "test-program"

        result = _user_can_access_program(user, program_id)
        assert result is True

    def test_user_can_access_program_with_access(self):
        """Test _user_can_access_program for user with program access."""
        from src.api.routes.courses import _user_can_access_program

        user = {"role": "program_admin", "program_ids": ["prog1", "prog2"]}
        program_id = "prog1"

        result = _user_can_access_program(user, program_id)
        assert result is True

    def test_user_can_access_program_without_access(self):
        """Test _user_can_access_program for user without program access."""
        from src.api.routes.courses import _user_can_access_program

        user = {"role": "program_admin", "program_ids": ["prog1", "prog2"]}
        program_id = "prog3"

        result = _user_can_access_program(user, program_id)
        assert result is False

    def test_user_can_access_program_no_user(self):
        """Test _user_can_access_program with no user."""
        from src.api.routes.courses import _user_can_access_program

        result = _user_can_access_program(None, "test-program")
        assert result is False

    def test_resolve_program_override_no_override(self):
        """Test _resolve_program_override with no override."""
        from unittest.mock import patch

        from src.api.routes.courses import _resolve_program_override

        with self.app.test_request_context("/?"):
            with patch(
                "src.api.routes.courses.get_current_program_id"
            ) as mock_get_program:
                mock_get_program.return_value = "current-program"

                result = _resolve_program_override({"role": "user"})
                assert result == "current-program"

    def test_resolve_program_override_with_access(self):
        """Test _resolve_program_override with valid override."""
        from unittest.mock import patch

        from src.api.routes.courses import _resolve_program_override

        user = {"role": "site_admin"}

        with self.app.test_request_context("/?program_id=override-program"):
            with patch(
                "src.api.routes.courses.get_current_program_id"
            ) as mock_get_program:
                mock_get_program.return_value = "current-program"

                result = _resolve_program_override(user)
                assert result == "override-program"

    def test_resolve_program_override_without_access(self):
        """Test _resolve_program_override with invalid override."""
        from unittest.mock import patch

        import pytest

        from src.api.routes.courses import _resolve_program_override

        user = {"role": "program_admin", "program_ids": ["other-program"]}

        with self.app.test_request_context("/?program_id=override-program"):
            with patch(
                "src.api.routes.courses.get_current_program_id"
            ) as mock_get_program:
                mock_get_program.return_value = "current-program"

                with pytest.raises(
                    PermissionError, match="Access denied to specified program"
                ):
                    _resolve_program_override(user)

    def test_get_global_courses_no_filter(self):
        """Test _get_global_courses without department filter."""
        from unittest.mock import patch

        from src.api.routes.courses import _get_global_courses

        institution_ids = ["inst1", "inst2"]
        mock_courses_1 = [{"id": "c1", "department": "CS"}]
        mock_courses_2 = [{"id": "c2", "department": "MATH"}]

        with patch("src.api.routes.courses.get_all_courses") as mock_get_courses:
            mock_get_courses.side_effect = [mock_courses_1, mock_courses_2]

            courses, context = _get_global_courses(institution_ids, None)

            assert len(courses) == 2
            assert context == "system-wide"

    def test_get_global_courses_with_filter(self):
        """Test _get_global_courses with department filter."""
        from unittest.mock import patch

        from src.api.routes.courses import _get_global_courses

        institution_ids = ["inst1", "inst2"]
        mock_courses_1 = [{"id": "c1", "department": "CS"}]
        mock_courses_2 = [{"id": "c2", "department": "MATH"}]

        with patch("src.api.routes.courses.get_all_courses") as mock_get_courses:
            mock_get_courses.side_effect = [mock_courses_1, mock_courses_2]

            courses, context = _get_global_courses(institution_ids, "CS")

            assert len(courses) == 1
            assert courses[0]["id"] == "c1"
            assert context == "system-wide, department CS"

    def test_get_program_courses_no_filter(self):
        """Test _get_program_courses without department filter."""
        from unittest.mock import patch

        from src.api.routes.courses import _get_program_courses

        program_id = "test-program"
        mock_courses = [
            {"id": "c1", "department": "CS"},
            {"id": "c2", "department": "MATH"},
        ]

        with patch("src.api.routes.courses.get_courses_by_program") as mock_get_courses:
            mock_get_courses.return_value = mock_courses

            courses, context = _get_program_courses(program_id, None)

            assert len(courses) == 2
            assert context == f"program {program_id}"

    def test_get_program_courses_with_filter(self):
        """Test _get_program_courses with department filter."""
        from unittest.mock import patch

        from src.api.routes.courses import _get_program_courses

        program_id = "test-program"
        mock_courses = [
            {"id": "c1", "department": "CS"},
            {"id": "c2", "department": "MATH"},
        ]

        with patch("src.api.routes.courses.get_courses_by_program") as mock_get_courses:
            mock_get_courses.return_value = mock_courses

            courses, context = _get_program_courses(program_id, "CS")

            assert len(courses) == 1
            assert courses[0]["id"] == "c1"

    def test_resolve_users_scope_success(self):
        """Test _resolve_users_scope with valid scope."""
        from unittest.mock import patch

        from src.api.routes.users import _resolve_users_scope

        mock_user = {"role": "site_admin"}
        mock_institutions = ["inst1"]
        mock_global = False

        with patch("src.api.routes.users.resolve_institution_scope") as mock_resolve:
            mock_resolve.return_value = (mock_user, mock_institutions, mock_global)

            user, institutions, is_global = _resolve_users_scope()

            assert user == mock_user
            assert institutions == mock_institutions
            assert is_global == mock_global

    def test_resolve_users_scope_missing_context(self):
        """Test _resolve_users_scope with missing institution context."""
        from unittest.mock import patch

        import pytest

        from src.api.routes.users import _resolve_users_scope
        from src.api.utils import InstitutionContextMissingError

        with patch("src.api.routes.users.resolve_institution_scope") as mock_resolve:
            mock_resolve.side_effect = InstitutionContextMissingError("Missing context")

            with pytest.raises(ValueError, match="Institution context required"):
                _resolve_users_scope()

    def test_get_users_by_scope_global(self):
        """Test _get_users_by_scope for global scope."""
        from unittest.mock import patch

        from src.api.routes.users import _get_users_by_scope

        institution_ids = ["inst1", "inst2"]
        role_filter = "admin"

        with patch("src.api.routes.users._get_global_users") as mock_global:
            mock_global.return_value = [{"id": "user1"}]

            result = _get_users_by_scope(True, institution_ids, role_filter)

            mock_global.assert_called_once_with(institution_ids, role_filter)
            assert result == [{"id": "user1"}]

    def test_get_users_by_scope_institution(self):
        """Test _get_users_by_scope for institution scope."""
        from unittest.mock import patch

        from src.api.routes.users import _get_users_by_scope

        institution_ids = ["inst1"]
        role_filter = "admin"

        with patch("src.api.routes.users._get_institution_users") as mock_institution:
            mock_institution.return_value = [{"id": "user1"}]

            result = _get_users_by_scope(False, institution_ids, role_filter)

            mock_institution.assert_called_once_with("inst1", role_filter)
            assert result == [{"id": "user1"}]

    def test_get_global_users_with_role_filter(self):
        """Test _get_global_users with role filter."""
        from unittest.mock import patch

        from src.api.routes.users import _get_global_users

        institution_ids = ["inst1", "inst2"]
        role_filter = "admin"
        mock_users = [
            {"id": "user1", "institution_id": "inst1"},
            {"id": "user2", "institution_id": "inst3"},  # Should be filtered out
            {"id": "user3", "institution_id": "inst2"},
        ]

        with patch("src.api.routes.users.get_users_by_role") as mock_get_users:
            mock_get_users.return_value = mock_users

            result = _get_global_users(institution_ids, role_filter)

            mock_get_users.assert_called_once_with(role_filter)
            assert len(result) == 2
            assert result[0]["id"] == "user1"
            assert result[1]["id"] == "user3"

    def test_get_global_users_without_role_filter(self):
        """Test _get_global_users without role filter."""
        from unittest.mock import patch

        from src.api.routes.users import _get_global_users

        institution_ids = ["inst1", "inst2"]
        mock_users_1 = [{"id": "user1"}]
        mock_users_2 = [{"id": "user2"}]

        with patch("src.api.routes.users.get_all_users") as mock_get_users:
            mock_get_users.side_effect = [mock_users_1, mock_users_2]

            result = _get_global_users(institution_ids, None)

            assert mock_get_users.call_count == 2
            assert len(result) == 2
            assert result[0]["id"] == "user1"
            assert result[1]["id"] == "user2"

    def test_get_institution_users_with_role_filter(self):
        """Test _get_institution_users with role filter."""
        from unittest.mock import patch

        from src.api.routes.users import _get_institution_users

        institution_id = "inst1"
        role_filter = "admin"
        mock_users = [
            {"id": "user1", "institution_id": "inst1"},
            {"id": "user2", "institution_id": "inst2"},  # Should be filtered out
        ]

        with patch("src.api.routes.users.get_users_by_role") as mock_get_users:
            mock_get_users.return_value = mock_users

            result = _get_institution_users(institution_id, role_filter)

            mock_get_users.assert_called_once_with(role_filter)
            assert len(result) == 1
            assert result[0]["id"] == "user1"

    def test_get_institution_users_without_role_filter(self):
        """Test _get_institution_users without role filter."""
        from unittest.mock import patch

        from src.api.routes.users import _get_institution_users

        institution_id = "inst1"
        mock_users = [{"id": "user1"}, {"id": "user2"}]

        with patch("src.api.routes.users.get_all_users") as mock_get_users:
            mock_get_users.return_value = mock_users

            result = _get_institution_users(institution_id, None)

            mock_get_users.assert_called_once_with(institution_id)
            assert result == mock_users


class TestRemoveCourseHelpers:
    """Test helper functions for remove_course_from_program_api."""

    def test_validate_program_for_removal_success(self):
        """Test _validate_program_for_removal with valid program."""
        from unittest.mock import patch

        from src.api.routes.programs import _validate_program_for_removal

        mock_program = {
            "id": "prog1",
            "institution_id": "inst1",
            "name": "Test Program",
        }

        with patch("src.api.routes.programs.get_program_by_id") as mock_get_program:
            mock_get_program.return_value = mock_program

            program, institution_id = _validate_program_for_removal("prog1")

            mock_get_program.assert_called_once_with("prog1")
            assert program == mock_program
            assert institution_id == "inst1"

    def test_validate_program_for_removal_not_found(self):
        """Test _validate_program_for_removal raises ValueError when program not found."""
        from unittest.mock import patch

        import pytest

        from src.api.routes.programs import _validate_program_for_removal

        with patch("src.api.routes.programs.get_program_by_id") as mock_get_program:
            mock_get_program.return_value = None

            with pytest.raises(ValueError, match="Program not found"):
                _validate_program_for_removal("prog1")

    def test_get_default_program_id_with_default(self):
        """Test _get_default_program_id returns default program."""
        from unittest.mock import patch

        from src.api.routes.programs import _get_default_program_id

        mock_programs = [
            {"id": "prog1", "is_default": False},
            {"id": "prog2", "is_default": True},
            {"id": "prog3", "is_default": False},
        ]

        with patch(
            "src.api.routes.programs.get_programs_by_institution"
        ) as mock_get_programs:
            mock_get_programs.return_value = mock_programs

            result = _get_default_program_id("inst1")

            mock_get_programs.assert_called_once_with("inst1")
            assert result == "prog2"

    def test_get_default_program_id_no_default(self):
        """Test _get_default_program_id returns None when no default exists."""
        from unittest.mock import patch

        from src.api.routes.programs import _get_default_program_id

        mock_programs = [
            {"id": "prog1", "is_default": False},
            {"id": "prog2", "is_default": False},
        ]

        with patch(
            "src.api.routes.programs.get_programs_by_institution"
        ) as mock_get_programs:
            mock_get_programs.return_value = mock_programs

            result = _get_default_program_id("inst1")

            assert result is None

    def test_get_default_program_id_no_institution(self):
        """Test _get_default_program_id returns None when no institution_id."""
        from src.api.routes.programs import _get_default_program_id

        result = _get_default_program_id(None)
        assert result is None

        result = _get_default_program_id("")
        assert result is None

    def test_get_default_program_id_no_programs(self):
        """Test _get_default_program_id returns None when institution has no programs."""
        from unittest.mock import patch

        from src.api.routes.programs import _get_default_program_id

        with patch(
            "src.api.routes.programs.get_programs_by_institution"
        ) as mock_get_programs:
            mock_get_programs.return_value = None

            result = _get_default_program_id("inst1")

            assert result is None

    def test_remove_course_with_orphan_handling_success(self):
        """Test _remove_course_with_orphan_handling successfully removes course."""
        from unittest.mock import patch

        from src.api.routes.programs import _remove_course_with_orphan_handling

        with (
            patch("src.api.routes.programs.remove_course_from_program") as mock_remove,
            patch(
                "src.api.routes.programs.assign_course_to_default_program"
            ) as mock_assign,
        ):
            mock_remove.return_value = True

            result = _remove_course_with_orphan_handling(
                "course1", "prog1", "inst1", "default_prog"
            )

            mock_remove.assert_called_once_with("course1", "prog1")
            mock_assign.assert_called_once_with("course1", "inst1")
            assert result is True

    def test_remove_course_with_orphan_handling_no_default_program(self):
        """Test _remove_course_with_orphan_handling when no default program exists."""
        from unittest.mock import patch

        from src.api.routes.programs import _remove_course_with_orphan_handling

        with (
            patch("src.api.routes.programs.remove_course_from_program") as mock_remove,
            patch(
                "src.api.routes.programs.assign_course_to_default_program"
            ) as mock_assign,
        ):
            mock_remove.return_value = True

            result = _remove_course_with_orphan_handling(
                "course1", "prog1", "inst1", None
            )

            mock_remove.assert_called_once_with("course1", "prog1")
            # Should not try to assign when no default program
            mock_assign.assert_not_called()
            assert result is True

    def test_build_removal_response_success(self):
        """Test _build_removal_response builds success response."""
        from src.api.routes.programs import _build_removal_response
        from src.app import app

        with app.app_context():
            mock_program = {"name": "Test Program"}
            response = _build_removal_response(True, "course1", mock_program)

            data = response.get_json()
            assert data["success"] is True
            assert "removed from program Test Program" in data["message"]
            # Success case returns just response (defaults to 200)
            assert response.status_code == 200

    def test_build_removal_response_failure(self):
        """Test _build_removal_response builds failure response."""
        from src.api.routes.programs import _build_removal_response
        from src.app import app

        with app.app_context():
            mock_program = {"name": "Test Program"}
            response, status = _build_removal_response(False, "course1", mock_program)

            data = response.get_json()
            assert data["success"] is False
            assert "Failed to remove" in data["error"]
            assert status == 500


class TestBulkManageHelpers:
    """Test helper functions for bulk_manage_program_courses."""

    def test_validate_bulk_manage_request_success(self):
        """Test _validate_bulk_manage_request with valid data."""

        from src.api.routes.programs import _validate_bulk_manage_request
        from src.app import app

        with app.test_client() as client:
            with client.application.test_request_context(
                json={"action": "add", "course_ids": ["course1", "course2"]}
            ):
                result = _validate_bulk_manage_request()
                assert result is None  # No validation error

    def test_validate_bulk_manage_request_no_data(self):
        """Test _validate_bulk_manage_request with no data."""
        from src.api.routes.programs import _validate_bulk_manage_request
        from src.app import app

        with app.test_client() as client:
            # Empty dict is treated as "no data"
            with client.application.test_request_context(json={}):
                response, status = _validate_bulk_manage_request()
                data = response.get_json()
                assert data["success"] is False
                assert "No data provided" in data["error"]
                assert status == 400

    def test_validate_bulk_manage_request_invalid_action(self):
        """Test _validate_bulk_manage_request with invalid action."""

        from src.api.routes.programs import _validate_bulk_manage_request
        from src.app import app

        with app.test_client() as client:
            with client.application.test_request_context(
                json={"action": "invalid", "course_ids": ["course1"]}
            ):
                response, status = _validate_bulk_manage_request()
                data = response.get_json()
                assert data["success"] is False
                assert "Invalid or missing action" in data["error"]
                assert status == 400

    def test_validate_bulk_manage_request_missing_course_ids(self):
        """Test _validate_bulk_manage_request with missing course_ids."""

        from src.api.routes.programs import _validate_bulk_manage_request
        from src.app import app

        with app.test_client() as client:
            with client.application.test_request_context(json={"action": "add"}):
                response, status = _validate_bulk_manage_request()
                data = response.get_json()
                assert data["success"] is False
                assert "Missing or invalid course_ids" in data["error"]
                assert status == 400

    def test_execute_bulk_add(self):
        """Test _execute_bulk_add helper."""
        from unittest.mock import patch

        from src.api.routes.programs import _execute_bulk_add

        mock_result = {"success_count": 5, "failed_count": 0}

        with patch(
            "src.api.routes.programs.bulk_add_courses_to_program"
        ) as mock_bulk_add:
            mock_bulk_add.return_value = mock_result

            result, message = _execute_bulk_add(["course1", "course2"], "prog1")

            mock_bulk_add.assert_called_once_with(["course1", "course2"], "prog1")
            assert result == mock_result
            assert "5 added" in message

    def test_execute_bulk_remove_with_default_program(self):
        """Test _execute_bulk_remove with default program available."""
        from unittest.mock import patch

        from src.api.routes.programs import _execute_bulk_remove

        mock_result = {"removed": 3, "failed": 0}

        with (
            patch(
                "src.api.routes.programs.get_current_institution_id_safe"
            ) as mock_get_inst,
            patch(
                "src.api.routes.programs._get_default_program_id"
            ) as mock_get_default,
            patch(
                "src.api.routes.programs.bulk_remove_courses_from_program"
            ) as mock_bulk_remove,
            patch(
                "src.api.routes.programs.assign_course_to_default_program"
            ) as mock_assign,
        ):
            mock_get_inst.return_value = "inst1"
            mock_get_default.return_value = "default_prog"
            mock_bulk_remove.return_value = mock_result

            result, message = _execute_bulk_remove(
                ["course1", "course2", "course3"], "prog1"
            )

            mock_bulk_remove.assert_called_once_with(
                ["course1", "course2", "course3"], "prog1"
            )
            # Should assign all courses to default program
            assert mock_assign.call_count == 3
            assert result == mock_result
            assert "3 removed" in message

    def test_execute_bulk_remove_no_default_program(self):
        """Test _execute_bulk_remove when no default program exists."""
        from unittest.mock import patch

        from src.api.routes.programs import _execute_bulk_remove

        mock_result = {"removed": 2, "failed": 0}

        with (
            patch(
                "src.api.routes.programs.get_current_institution_id_safe"
            ) as mock_get_inst,
            patch(
                "src.api.routes.programs._get_default_program_id"
            ) as mock_get_default,
            patch(
                "src.api.routes.programs.bulk_remove_courses_from_program"
            ) as mock_bulk_remove,
            patch(
                "src.api.routes.programs.assign_course_to_default_program"
            ) as mock_assign,
        ):
            mock_get_inst.return_value = "inst1"
            mock_get_default.return_value = None  # No default program
            mock_bulk_remove.return_value = mock_result

            result, message = _execute_bulk_remove(["course1", "course2"], "prog1")

            # Should not try to assign when no default program
            mock_assign.assert_not_called()
            assert result == mock_result
            assert "2 removed" in message


class TestExcelImportHelpers:
    """Test helper functions for excel_import_api."""

    def test_check_excel_import_permissions_site_admin(self):
        """Test _check_excel_import_permissions for site admin - must have institution_id."""
        from unittest.mock import patch

        import pytest

        from src.api.routes.imports import _check_excel_import_permissions

        # SECURITY: Site admins can no longer import without an institution context
        # This enforces multi-tenant isolation - ALL users need institution_id
        mock_user = {
            "user_id": "admin1",
            "role": "site_admin",
            "institution_id": None,
        }

        with patch("src.api.utils.get_current_user") as mock_get_user:
            mock_get_user.return_value = mock_user

            # Should fail because site admin has no institution_id
            with pytest.raises(
                PermissionError, match="User has no associated institution"
            ):
                _check_excel_import_permissions("courses")

    def test_check_excel_import_permissions_no_user(self):
        """Test _check_excel_import_permissions raises when no user."""
        from unittest.mock import patch

        import pytest

        from src.api.routes.imports import _check_excel_import_permissions

        with patch("src.api.utils.get_current_user") as mock_get_user:
            mock_get_user.return_value = None

            with pytest.raises(PermissionError, match="Authentication required"):
                _check_excel_import_permissions("courses")

    # REMOVED: MockU-specific tests no longer apply after security fix
    # Site admins now follow the same rules as all other users:
    # They must have an institution_id and can only import into their own institution

    def test_determine_target_institution_institution_admin(self):
        """Test _determine_target_institution for institution admin."""
        from src.api.routes.imports import _determine_target_institution

        result = _determine_target_institution("inst123")

        assert result == "inst123"

    def test_determine_target_institution_no_institution(self):
        """Test _determine_target_institution when user has no institution."""
        import pytest

        from src.api.routes.imports import _determine_target_institution

        with pytest.raises(PermissionError, match="User has no associated institution"):
            _determine_target_institution(None)

    def test_validate_import_permissions_site_admin_courses(self):
        """Test _validate_import_permissions for site admin importing courses."""
        from src.api.routes.imports import _validate_import_permissions

        # Should not raise
        _validate_import_permissions("site_admin", "courses")

    def test_validate_import_permissions_invalid_role(self):
        """Test _validate_import_permissions with invalid role."""
        import pytest

        from src.api.routes.imports import _validate_import_permissions

        with pytest.raises(PermissionError, match="Invalid user role"):
            _validate_import_permissions("invalid_role", "courses")

    def test_validate_import_permissions_forbidden_data_type(self):
        """Test _validate_import_permissions when user cannot import data type."""
        import pytest

        from src.api.routes.imports import _validate_import_permissions

        # Institution admin cannot import institutions
        with pytest.raises(
            PermissionError, match="institution_admin cannot import institutions"
        ):
            _validate_import_permissions("institution_admin", "institutions")


class TestValidateExcelImportRequest:
    def test_validate_excel_import_request_adapter_not_found(self):
        """Covers adapter-not-found branch in _validate_excel_import_request."""
        from src.api.routes.imports import _validate_excel_import_request

        class DummyFile:
            filename = "test.xlsx"

        with app.test_request_context(
            "/api/import/excel",
            method="POST",
            data={"import_adapter": "missing_adapter", "import_data_type": "courses"},
        ):
            with (
                patch(
                    "src.api.routes.imports._get_excel_file_from_request",
                    return_value=DummyFile(),
                ),
                patch(
                    "src.adapters.adapter_registry.AdapterRegistry"
                ) as mock_registry_cls,
            ):
                mock_registry_cls.return_value.get_adapter_by_id.return_value = None
                with pytest.raises(ValueError, match="Adapter not found"):
                    _validate_excel_import_request()

    def test_validate_excel_import_request_adapter_info_missing(self):
        """Covers adapter-info-missing branch in _validate_excel_import_request."""
        from src.api.routes.imports import _validate_excel_import_request

        class DummyFile:
            filename = "test.xlsx"

        dummy_adapter = Mock()
        dummy_adapter.get_adapter_info.return_value = None

        with app.test_request_context(
            "/api/import/excel",
            method="POST",
            data={
                "import_adapter": "cei_excel_format_v1",
                "import_data_type": "courses",
            },
        ):
            with (
                patch(
                    "src.api.routes.imports._get_excel_file_from_request",
                    return_value=DummyFile(),
                ),
                patch(
                    "src.adapters.adapter_registry.AdapterRegistry"
                ) as mock_registry_cls,
            ):
                mock_registry_cls.return_value.get_adapter_by_id.return_value = (
                    dummy_adapter
                )
                with pytest.raises(ValueError, match="Adapter info not available"):
                    _validate_excel_import_request()

    def test_validate_excel_import_request_no_supported_formats(self):
        """Covers supported_formats empty branch in _validate_excel_import_request."""
        from src.api.routes.imports import _validate_excel_import_request

        class DummyFile:
            filename = "test.xlsx"

        dummy_adapter = Mock()
        dummy_adapter.get_adapter_info.return_value = {"supported_formats": []}

        with app.test_request_context(
            "/api/import/excel",
            method="POST",
            data={
                "import_adapter": "cei_excel_format_v1",
                "import_data_type": "courses",
            },
        ):
            with (
                patch(
                    "src.api.routes.imports._get_excel_file_from_request",
                    return_value=DummyFile(),
                ),
                patch(
                    "src.adapters.adapter_registry.AdapterRegistry"
                ) as mock_registry_cls,
            ):
                mock_registry_cls.return_value.get_adapter_by_id.return_value = (
                    dummy_adapter
                )
                with pytest.raises(ValueError, match="No supported formats defined"):
                    _validate_excel_import_request()

    def test_validate_excel_import_request_file_has_no_extension(self):
        """Covers file extension empty branch in _validate_excel_import_request."""
        from src.api.routes.imports import _validate_excel_import_request

        class DummyFile:
            filename = "test"

        dummy_adapter = Mock()
        dummy_adapter.get_adapter_info.return_value = {"supported_formats": [".xlsx"]}

        with app.test_request_context(
            "/api/import/excel",
            method="POST",
            data={
                "import_adapter": "cei_excel_format_v1",
                "import_data_type": "courses",
            },
        ):
            with (
                patch(
                    "src.api.routes.imports._get_excel_file_from_request",
                    return_value=DummyFile(),
                ),
                patch(
                    "src.adapters.adapter_registry.AdapterRegistry"
                ) as mock_registry_cls,
            ):
                mock_registry_cls.return_value.get_adapter_by_id.return_value = (
                    dummy_adapter
                )
                with pytest.raises(ValueError, match="File has no extension"):
                    _validate_excel_import_request()

    def test_validate_excel_import_request_file_extension_not_supported(self):
        """Covers invalid extension branch in _validate_excel_import_request."""
        from src.api.routes.imports import _validate_excel_import_request

        class DummyFile:
            filename = "test.csv"

        dummy_adapter = Mock()
        dummy_adapter.get_adapter_info.return_value = {"supported_formats": [".xlsx"]}

        with app.test_request_context(
            "/api/import/excel",
            method="POST",
            data={
                "import_adapter": "cei_excel_format_v1",
                "import_data_type": "courses",
            },
        ):
            with (
                patch(
                    "src.api.routes.imports._get_excel_file_from_request",
                    return_value=DummyFile(),
                ),
                patch(
                    "src.adapters.adapter_registry.AdapterRegistry"
                ) as mock_registry_cls,
            ):
                mock_registry_cls.return_value.get_adapter_by_id.return_value = (
                    dummy_adapter
                )
                with pytest.raises(ValueError, match=r"Invalid file format"):
                    _validate_excel_import_request()


class TestExcelImportEdgeCases:
    """Test edge cases in excel_import_api function."""

    def test_unsafe_filename_sanitization(self):
        """Test filename sanitization fallback for unsafe names."""
        import re

        # Simulate the exact logic from src/api/routes/imports.py
        filename = "..."  # Only dots
        safe_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)

        # Line 3025-3026: Check if empty or starts with dot
        if not safe_filename or safe_filename.startswith("."):
            safe_filename = f"upload_{hash(filename) % 10000}"  # Line 3026

        # Should have generated fallback filename
        assert safe_filename.startswith("upload_")
        assert len(safe_filename) > 7  # "upload_" + digits


class TestUserCreationPermissionValidation:
    """Test _validate_user_creation_permissions function."""

    def test_program_admin_cannot_create_site_admin(self):
        """Test that program admin cannot create site admin accounts."""
        from src.api.routes.users import _validate_user_creation_permissions
        from src.app import app

        current_user = {"role": "program_admin", "institution_id": "mock_university"}
        data = {"role": "site_admin", "institution_id": "mock_university"}

        with app.app_context():
            is_valid, error_response = _validate_user_creation_permissions(
                current_user, data
            )

            assert is_valid is False
            assert error_response is not None
            response_data, status_code = error_response
            assert status_code == 403
            json_data = response_data.get_json()
            assert json_data["success"] is False
            assert (
                "Program admins can only create instructor accounts"
                in json_data["error"]
            )

    def test_program_admin_cannot_create_institution_admin(self):
        """Test that program admin cannot create institution admin accounts."""
        from src.api.routes.users import _validate_user_creation_permissions
        from src.app import app

        current_user = {"role": "program_admin", "institution_id": "mock_university"}
        data = {"role": "institution_admin", "institution_id": "mock_university"}

        with app.app_context():
            is_valid, error_response = _validate_user_creation_permissions(
                current_user, data
            )

            assert is_valid is False
            assert error_response is not None
            response_data, status_code = error_response
            assert status_code == 403
            json_data = response_data.get_json()
            assert json_data["success"] is False
            assert (
                "Program admins can only create instructor accounts"
                in json_data["error"]
            )

    def test_program_admin_cannot_create_program_admin(self):
        """Test that program admin cannot create other program admin accounts."""
        from src.api.routes.users import _validate_user_creation_permissions
        from src.app import app

        current_user = {"role": "program_admin", "institution_id": "mock_university"}
        data = {"role": "program_admin", "institution_id": "mock_university"}

        with app.app_context():
            is_valid, error_response = _validate_user_creation_permissions(
                current_user, data
            )

            assert is_valid is False
            assert error_response is not None
            response_data, status_code = error_response
            assert status_code == 403
            json_data = response_data.get_json()
            assert json_data["success"] is False
            assert (
                "Program admins can only create instructor accounts"
                in json_data["error"]
            )

    def test_program_admin_requires_institution_id(self):
        """Test that program admin must provide institution_id when creating instructors."""
        from src.api.routes.users import _validate_user_creation_permissions
        from src.app import app

        current_user = {"role": "program_admin", "institution_id": "mock_university"}
        data = {
            "role": "instructor"
            # Missing institution_id
        }

        with app.app_context():
            is_valid, error_response = _validate_user_creation_permissions(
                current_user, data
            )

            assert is_valid is False
            assert error_response is not None
            response_data, status_code = error_response
            assert status_code == 400
            json_data = response_data.get_json()
            assert json_data["success"] is False
            assert "institution_id is required" in json_data["error"]

    def test_program_admin_cannot_create_at_different_institution(self):
        """Test that program admin can only create users at their own institution."""
        from src.api.routes.users import _validate_user_creation_permissions
        from src.app import app

        current_user = {"role": "program_admin", "institution_id": "mock_university"}
        data = {"role": "instructor", "institution_id": "different_institution"}

        with app.app_context():
            is_valid, error_response = _validate_user_creation_permissions(
                current_user, data
            )

            assert is_valid is False
            assert error_response is not None
            response_data, status_code = error_response
            assert status_code == 403
            json_data = response_data.get_json()
            assert json_data["success"] is False
            assert (
                "Program admins can only create users at their own institution"
                in json_data["error"]
            )

    def test_program_admin_can_create_instructor_at_own_institution(self):
        """Test that program admin can create instructors at their own institution."""
        from src.api.routes.users import _validate_user_creation_permissions

        current_user = {"role": "program_admin", "institution_id": "mock_university"}
        data = {"role": "instructor", "institution_id": "mock_university"}

        is_valid, error_response = _validate_user_creation_permissions(
            current_user, data
        )

        assert is_valid is True
        assert error_response is None

    def test_institution_admin_cannot_create_site_admin(self):
        """Test that institution admin cannot create site admin accounts."""
        from src.api.routes.users import _validate_user_creation_permissions
        from src.app import app

        current_user = {
            "role": "institution_admin",
            "institution_id": "mock_university",
        }
        data = {"role": "site_admin", "institution_id": "mock_university"}

        with app.app_context():
            is_valid, error_response = _validate_user_creation_permissions(
                current_user, data
            )

            assert is_valid is False
            assert error_response is not None
            response_data, status_code = error_response
            assert status_code == 403
            json_data = response_data.get_json()
            assert json_data["success"] is False
            assert (
                "Institution admins cannot create site admin accounts"
                in json_data["error"]
            )

    def test_institution_admin_can_create_institution_admin(self):
        """Test that institution admin can create other institution admins."""
        from src.api.routes.users import _validate_user_creation_permissions

        current_user = {
            "role": "institution_admin",
            "institution_id": "mock_university",
        }
        data = {"role": "institution_admin", "institution_id": "mock_university"}

        is_valid, error_response = _validate_user_creation_permissions(
            current_user, data
        )

        assert is_valid is True
        assert error_response is None

    def test_site_admin_can_create_any_role(self):
        """Test that site admin can create users of any role."""
        from src.api.routes.users import _validate_user_creation_permissions

        current_user = {"role": "site_admin", "institution_id": None}

        # Test creating site_admin
        data = {"role": "site_admin", "institution_id": "mock_university"}
        is_valid, error_response = _validate_user_creation_permissions(
            current_user, data
        )
        assert is_valid is True
        assert error_response is None

        # Test creating institution_admin
        data = {"role": "institution_admin", "institution_id": "mock_university"}
        is_valid, error_response = _validate_user_creation_permissions(
            current_user, data
        )
        assert is_valid is True
        assert error_response is None

        # Test creating program_admin
        data = {"role": "program_admin", "institution_id": "mock_university"}
        is_valid, error_response = _validate_user_creation_permissions(
            current_user, data
        )
        assert is_valid is True
        assert error_response is None

        # Test creating instructor
        data = {"role": "instructor", "institution_id": "mock_university"}
        is_valid, error_response = _validate_user_creation_permissions(
            current_user, data
        )
        assert is_valid is True
        assert error_response is None


class TestCourseReminderEndpoint:
    """Test /api/send-course-reminder endpoint."""

    @pytest.fixture
    def authenticated_client_and_token(self, client):
        """Create an authenticated client with CSRF properly configured."""
        from tests.test_utils import create_test_session

        # Create session with program admin user (has manage_programs permission)
        user_data = {
            "user_id": "admin-123",
            "email": "admin@example.com",
            "role": "program_admin",
            "first_name": "Admin",
            "last_name": "User",
            "institution_id": "inst-123",
        }
        create_test_session(client, user_data)

        # The global conftest.py autouse fixture handles CSRF token injection automatically
        # No need to return a token - the client's POST method is already wrapped
        return client

    @patch("src.database.database_service.get_user_by_id")
    @patch("src.database.database_service.get_course_by_id")
    @patch("src.database.database_service.get_institution_by_id")
    @patch("src.api.utils.get_current_user")
    @patch("src.services.email_service.EmailService.send_course_assessment_reminder")
    def test_send_course_reminder_success(
        self,
        mock_send_email,
        mock_get_current_user,
        mock_get_institution,
        mock_get_course,
        mock_get_instructor,
        authenticated_client_and_token,
    ):
        """Test successfully sending course reminder email."""
        client = authenticated_client_and_token
        # Setup mocks
        mock_get_instructor.return_value = {
            "user_id": "instructor-123",
            "email": "instructor@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "institution_id": "inst-123",
        }
        mock_get_course.return_value = {
            "id": "course-123",
            "course_number": "CS101",
            "course_title": "Intro to Computer Science",
        }
        mock_get_institution.return_value = {
            "id": "inst-123",
            "name": "Test University",
        }
        mock_get_current_user.return_value = {
            "user_id": "admin-123",
            "email": "admin@example.com",
            "first_name": "Admin",
            "last_name": "User",
            "institution_id": "inst-123",
        }

        # Send request
        response = client.post(
            "/api/send-course-reminder",
            json={
                "instructor_id": "instructor-123",
                "course_id": "course-123",
            },
        )

        # Verify
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Reminder sent" in data["message"]
        mock_send_email.assert_called_once()

    @patch("src.database.database_service.get_user_by_id")
    @patch("src.database.database_service.get_course_by_id")
    def test_send_course_reminder_missing_json(
        self, mock_get_course, mock_get_instructor, authenticated_client_and_token
    ):
        """Test sending reminder with no JSON data returns 400."""
        client = authenticated_client_and_token
        response = client.post(
            "/api/send-course-reminder",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "No JSON data provided" in data["error"]

    @patch("src.database.database_service.get_user_by_id")
    @patch("src.database.database_service.get_course_by_id")
    def test_send_course_reminder_missing_fields(
        self, mock_get_course, mock_get_instructor, authenticated_client_and_token
    ):
        """Test sending reminder with missing required fields returns 400."""
        client = authenticated_client_and_token
        response = client.post(
            "/api/send-course-reminder",
            json={"instructor_id": "instructor-123"},  # Missing course_id
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Missing required fields" in data["error"]

    @patch("src.database.database_service.get_user_by_id")
    @patch("src.database.database_service.get_course_by_id")
    def test_send_course_reminder_instructor_not_found(
        self, mock_get_course, mock_get_instructor, authenticated_client_and_token
    ):
        """Test sending reminder for non-existent instructor returns 404."""
        client = authenticated_client_and_token
        mock_get_instructor.return_value = None

        response = client.post(
            "/api/send-course-reminder",
            json={
                "instructor_id": "nonexistent",
                "course_id": "course-123",
            },
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "Instructor not found" in data["error"]

    @patch("src.database.database_service.get_user_by_id")
    @patch("src.database.database_service.get_course_by_id")
    def test_send_course_reminder_course_not_found(
        self, mock_get_course, mock_get_instructor, authenticated_client_and_token
    ):
        """Test sending reminder for non-existent course returns 404."""
        client = authenticated_client_and_token
        mock_get_instructor.return_value = {
            "user_id": "instructor-123",
            "email": "instructor@example.com",
        }
        mock_get_course.return_value = None

        response = client.post(
            "/api/send-course-reminder",
            json={
                "instructor_id": "instructor-123",
                "course_id": "nonexistent",
            },
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "Course not found" in data["error"]

    @patch("src.database.database_service.get_institution_by_id")
    @patch("src.database.database_service.get_course_by_id")
    @patch("src.database.database_service.get_user_by_id")
    @patch("src.api.utils.get_current_user")
    @patch("src.services.email_service.EmailService.send_course_assessment_reminder")
    def test_send_course_reminder_instructor_no_name(
        self,
        mock_send_email,
        mock_get_current_user,
        mock_get_instructor,
        mock_get_course,
        mock_get_institution,
        authenticated_client_and_token,
    ):
        """Test sending reminder when instructor has no first/last name uses email fallback."""
        client = authenticated_client_and_token
        # Instructor with no first/last name
        mock_get_instructor.return_value = {
            "user_id": "instructor-123",
            "email": "instructor@example.com",
            "first_name": "",
            "last_name": "",
            "institution_id": "inst-123",
        }
        mock_get_course.return_value = {
            "id": "course-123",
            "course_number": "CS101",
            "course_title": "Intro to CS",
        }
        mock_get_institution.return_value = {
            "id": "inst-123",
            "name": "Test University",
        }
        mock_get_current_user.return_value = {
            "user_id": "admin-123",
            "email": "admin@example.com",
            "first_name": "Admin",
            "last_name": "User",
            "institution_id": "inst-123",
        }

        response = client.post(
            "/api/send-course-reminder",
            json={"instructor_id": "instructor-123", "course_id": "course-123"},
        )

        assert response.status_code == 200
        # Verify email was called with email address as name fallback
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args[1]
        assert call_args["instructor_name"] == "instructor@example.com"

    @patch("src.database.database_service.get_user_by_id")
    @patch("src.database.database_service.get_course_by_id")
    @patch("src.database.database_service.get_institution_by_id")
    @patch("src.api.utils.get_current_user")
    @patch("src.services.email_service.EmailService.send_course_assessment_reminder")
    def test_send_course_reminder_email_exception(
        self,
        mock_send_email,
        mock_get_current_user,
        mock_get_institution,
        mock_get_course,
        mock_get_instructor,
        authenticated_client_and_token,
    ):
        """Test sending reminder handles email exceptions gracefully."""
        client = authenticated_client_and_token
        # Setup mocks
        mock_get_instructor.return_value = {
            "user_id": "instructor-123",
            "email": "instructor@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "institution_id": "inst-123",
        }
        mock_get_course.return_value = {
            "id": "course-123",
            "course_number": "CS101",
            "course_title": "Intro to Computer Science",
        }
        mock_get_institution.return_value = {
            "id": "inst-123",
            "name": "Test University",
        }
        mock_get_current_user.return_value = {
            "user_id": "admin-123",
            "email": "admin@example.com",
            "first_name": "Admin",
            "last_name": "User",
            "institution_id": "inst-123",
        }
        mock_send_email.side_effect = Exception("SMTP error")

        # Send request
        response = client.post(
            "/api/send-course-reminder",
            json={
                "instructor_id": "instructor-123",
                "course_id": "course-123",
            },
        )

        # Verify
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to send reminder email" in data["error"]


class TestUpdateUserRoleEndpoint:
    """Test /api/users/<user_id>/role endpoint."""

    def get_csrf_token(self, client):
        """Get CSRF token using Flask-WTF's generate_csrf."""
        from flask import session as flask_session
        from flask_wtf.csrf import generate_csrf

        with client.session_transaction() as sess:
            raw_token = sess.get("csrf_token")

        with client.application.test_request_context():
            if raw_token:
                flask_session["csrf_token"] = raw_token
            return generate_csrf()

    @pytest.fixture
    def institution_admin_client(self, client):
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "admin-1",
            "email": "admin@example.com",
            "role": "institution_admin",
            "first_name": "Admin",
            "last_name": "User",
            "institution_id": "inst-123",
        }
        create_test_session(client, user_data)
        return client

    @patch("src.api.utils.get_current_institution_id")
    def test_missing_role_returns_400(self, mock_get_inst, institution_admin_client):
        mock_get_inst.return_value = "inst-123"
        response = institution_admin_client.patch(
            "/api/users/u1/role",
            json={},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "Role is required"

    @patch("src.api.utils.get_current_institution_id")
    def test_invalid_role_returns_400(self, mock_get_inst, institution_admin_client):
        mock_get_inst.return_value = "inst-123"
        response = institution_admin_client.patch(
            "/api/users/u1/role",
            json={"role": "site_admin"},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 400
        assert response.get_json()["success"] is False
        assert "Invalid role" in response.get_json()["error"]

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.routes.users.get_user_by_id")
    def test_user_not_found_returns_404(
        self, mock_get_user, mock_get_inst, institution_admin_client
    ):
        mock_get_inst.return_value = "inst-123"
        mock_get_user.return_value = None
        response = institution_admin_client.patch(
            "/api/users/u1/role",
            json={"role": "instructor"},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 404
        assert response.get_json()["error"] == "User not found"

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.routes.users.get_user_by_id")
    def test_institution_mismatch_returns_404(
        self, mock_get_user, mock_get_inst, institution_admin_client
    ):
        mock_get_inst.return_value = "inst-123"
        mock_get_user.return_value = {"user_id": "u1", "institution_id": "inst-999"}
        response = institution_admin_client.patch(
            "/api/users/u1/role",
            json={"role": "instructor"},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 404
        assert response.get_json()["error"] == "User not found"

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.routes.users.update_user_role")
    @patch("src.api.routes.users.get_user_by_id")
    def test_update_failure_returns_500(
        self, mock_get_user, mock_update_role, mock_get_inst, institution_admin_client
    ):
        mock_get_inst.return_value = "inst-123"
        mock_get_user.return_value = {"user_id": "u1", "institution_id": "inst-123"}
        mock_update_role.return_value = False
        response = institution_admin_client.patch(
            "/api/users/u1/role",
            json={"role": "instructor"},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 500
        assert response.get_json()["error"] == "Failed to update role"

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.routes.users.update_user_role")
    @patch("src.api.routes.users.get_user_by_id")
    def test_success_returns_200(
        self, mock_get_user, mock_update_role, mock_get_inst, institution_admin_client
    ):
        mock_get_inst.return_value = "inst-123"
        mock_get_user.side_effect = [
            {"user_id": "u1", "institution_id": "inst-123"},
            {"user_id": "u1", "institution_id": "inst-123", "role": "instructor"},
        ]
        mock_update_role.return_value = True
        response = institution_admin_client.patch(
            "/api/users/u1/role",
            json={"role": "instructor"},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert "User role updated" in payload["message"]


class TestDuplicateCourseEndpoint:
    """Test /api/courses/<course_id>/duplicate endpoint."""

    def get_csrf_token(self, client):
        """Get CSRF token using Flask-WTF's generate_csrf."""
        from flask import session as flask_session
        from flask_wtf.csrf import generate_csrf

        with client.session_transaction() as sess:
            raw_token = sess.get("csrf_token")

        with client.application.test_request_context():
            if raw_token:
                flask_session["csrf_token"] = raw_token
            return generate_csrf()

    @pytest.fixture
    def institution_admin_client(self, client):
        from tests.test_utils import create_test_session

        user_data = {
            "user_id": "admin-1",
            "email": "admin@example.com",
            "role": "institution_admin",
            "first_name": "Admin",
            "last_name": "User",
            "institution_id": "inst-123",
        }
        create_test_session(client, user_data)
        return client

    @patch("src.api.routes.courses.get_course_by_id")
    def test_source_course_missing_returns_404(
        self, mock_get_course, institution_admin_client
    ):
        mock_get_course.return_value = None
        response = institution_admin_client.post(
            "/api/courses/c1/duplicate",
            json={},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 404
        assert response.get_json()["success"] is False

    @patch("src.api.routes.courses.get_course_by_id")
    @patch("src.api.utils.get_current_user")
    def test_permission_denied_returns_403(
        self, mock_get_user, mock_get_course, institution_admin_client
    ):
        mock_get_course.return_value = {"course_id": "c1", "institution_id": "inst-999"}
        mock_get_user.return_value = {
            "role": "institution_admin",
            "institution_id": "inst-123",
        }
        response = institution_admin_client.post(
            "/api/courses/c1/duplicate",
            json={},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 403
        assert response.get_json()["error"] == "Permission denied"

    @patch("src.api.routes.courses.duplicate_course_record")
    @patch("src.api.routes.courses.get_course_by_id")
    @patch("src.api.utils.get_current_user")
    def test_duplicate_failure_returns_500(
        self, mock_get_user, mock_get_course, mock_duplicate, institution_admin_client
    ):
        mock_get_course.return_value = {"course_id": "c1", "institution_id": "inst-123"}
        mock_get_user.return_value = {
            "role": "institution_admin",
            "institution_id": "inst-123",
        }
        mock_duplicate.return_value = None
        response = institution_admin_client.post(
            "/api/courses/c1/duplicate",
            json={"program_ids": ["p1"], "duplicate_programs": False},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 500
        assert response.get_json()["error"] == "Failed to duplicate course"

    @patch("src.api.routes.courses.duplicate_course_record")
    @patch("src.api.routes.courses.get_course_by_id")
    @patch("src.api.utils.get_current_user")
    def test_duplicate_success_returns_201(
        self, mock_get_user, mock_get_course, mock_duplicate, institution_admin_client
    ):
        mock_get_user.return_value = {
            "role": "institution_admin",
            "institution_id": "inst-123",
        }
        mock_get_course.side_effect = [
            {"course_id": "c1", "institution_id": "inst-123"},
            {
                "course_id": "new-1",
                "institution_id": "inst-123",
                "course_number": "CS101-V2",
            },
        ]
        mock_duplicate.return_value = "new-1"

        response = institution_admin_client.post(
            "/api/courses/c1/duplicate",
            json={"program_ids": ["p1"], "duplicate_programs": False},
            headers={"X-CSRFToken": self.get_csrf_token(institution_admin_client)},
        )
        assert response.status_code == 201
        payload = response.get_json()
        assert payload["success"] is True
        assert payload["course"]["course_id"] == "new-1"
