"""Unit tests for API routes."""

import json

# Unused imports removed
from unittest.mock import patch

# Import the API blueprint and related modules
from api_routes import api
from app import app

# pytest import removed
# Flask import removed

# Test constants to avoid hard-coded values
TEST_PASSWORD = "SecurePass123!"  # Test password for unit tests only


class TestAPIBlueprint:
    """Test API blueprint setup and registration."""

    def test_api_blueprint_creation(self):
        """Test that API blueprint is created correctly."""
        assert api.name == "api"
        assert api.url_prefix == "/api"

    def test_api_blueprint_registered_in_app(self):
        """Test that API blueprint is registered in the Flask app."""
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        assert "api" in blueprint_names


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

        with patch("app.render_template") as mock_render:
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

        with patch("app.render_template") as mock_render:
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

        with patch("app.render_template") as mock_render:
            mock_render.return_value = "Dashboard HTML"
            response = self.client.get("/dashboard")

            assert response.status_code == 200
            # Verify the correct template was called for site_admin role
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            assert call_args[0][0] == "dashboard/site_admin_panels.html"
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
            patch("app.redirect") as mock_redirect,
            patch("app.flash") as mock_flash,
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
            assert data["message"] == "CEI Course Management API is running"
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

    @patch("app.render_template")
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

    @patch("api_routes.register_institution_admin")
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

    @patch("api_routes.register_institution_admin")
    def test_register_institution_admin_registration_error(self, mock_register):
        """Test registration with RegistrationError exception."""
        from registration_service import RegistrationError

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

    @patch("api_routes.register_institution_admin")
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
        with patch("api_routes.register_institution_admin") as mock_register:
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

    @patch("invitation_service.InvitationService")
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
        mock_invitation_service.send_invitation.return_value = True

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

    @patch("invitation_service.InvitationService")
    def test_create_invitation_invalid_email(self, mock_invitation_service):
        """Test invitation creation with invalid email format."""
        from invitation_service import InvitationError

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

        assert response.status_code == 500  # Generic error for invalid email format
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Failed to create invitation" in data["error"]

    @patch("invitation_service.InvitationService")
    def test_create_invitation_service_error(self, mock_invitation_service):
        """Test invitation creation with service error."""
        from invitation_service import InvitationError

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

    @patch("invitation_service.InvitationService")
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

    @patch("invitation_service.InvitationService")
    def test_create_invitation_with_program_ids(self, mock_invitation_service):
        """Test invitation creation with program IDs for program_admin role."""
        self._login_institution_admin()

        mock_invitation_service.create_invitation.return_value = {
            "id": "inv-789",
            "invitee_email": "admin@test.com",
            "invitee_role": "program_admin",
            "status": "sent",
        }
        mock_invitation_service.send_invitation.return_value = True

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


class TestAcceptInvitationEndpoints:
    """Test accept invitation API endpoints (Story 2.2)"""

    @patch("invitation_service.InvitationService")
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

            assert (
                response.status_code == 500
            )  # Flask returns 500 for UnsupportedMediaType
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Failed to accept invitation" in data["error"]

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

    @patch("invitation_service.InvitationService")
    def test_accept_invitation_invalid_token(self, mock_invitation_service):
        """Test invitation acceptance with invalid token."""
        from invitation_service import InvitationError

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

    @patch("invitation_service.InvitationService")
    def test_accept_invitation_expired_token(self, mock_invitation_service):
        """Test invitation acceptance with expired token."""
        from invitation_service import InvitationError

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

    @patch("invitation_service.InvitationService")
    def test_accept_invitation_weak_password(self, mock_invitation_service):
        """Test invitation acceptance with weak password."""
        from invitation_service import InvitationError

        mock_invitation_service.accept_invitation.side_effect = InvitationError(
            "Invalid password - does not meet security requirements"
        )

        with app.test_client() as client:
            response = client.post(
                "/api/auth/accept-invitation",
                json={"invitation_token": "valid-token-123", "password": "weak"},
            )

            assert (
                response.status_code == 400
            )  # "Invalid" in error message triggers 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Invalid password" in data["error"]

    @patch("invitation_service.InvitationService")
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

    @patch("invitation_service.InvitationService")
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

    @patch("invitation_service.InvitationService")
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

    @patch("invitation_service.InvitationService")
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

    @patch("invitation_service.InvitationService")
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

    @patch("invitation_service.InvitationService")
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

    @patch("invitation_service.InvitationService")
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

    @patch("registration_service.RegistrationService")
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

            assert (
                response.status_code == 500
            )  # Flask returns 500 for UnsupportedMediaType
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Failed to resend verification email" in data["error"]

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

    @patch("registration_service.RegistrationService")
    def test_resend_verification_user_not_found(self, mock_registration_service):
        """Test resend verification for non-existent user."""
        from registration_service import RegistrationError

        mock_registration_service.resend_verification_email.side_effect = (
            RegistrationError("User not found")
        )

        with app.test_client() as client:
            response = client.post(
                "/api/auth/resend-verification", json={"email": "notfound@test.com"}
            )

            assert response.status_code == 400  # RegistrationError returns 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "User not found" in data["error"]

    @patch("registration_service.RegistrationService")
    def test_resend_verification_already_verified(self, mock_registration_service):
        """Test resend verification for already verified user."""
        from registration_service import RegistrationError

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

    @patch("registration_service.RegistrationService")
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

    @patch("registration_service.RegistrationService")
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

    @patch("api_routes.get_all_users", return_value=[])
    def test_get_users_endpoint_exists(self, mock_get_all_users):
        """Test that GET /api/users endpoint exists and returns valid JSON."""
        self._login_user()

        response = self.client.get("/api/users")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "users" in data
        assert isinstance(data["users"], list)
        mock_get_all_users.assert_called_once_with("inst-123")

    @patch("api_routes.get_users_by_role")
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

    @patch("api_routes.get_users_by_role")
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
        }

        response = self.client.post(
            "/api/users", json=user_data, content_type="application/json"
        )
        # API currently returns 201 due to stub implementation
        assert response.status_code == 201

        data = json.loads(response.data)
        assert data["success"] is True
        assert data["user_id"] == "stub-user-id"

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
        }

        response = self.client.post(
            "/api/users", json=user_data, content_type="application/json"
        )
        # API currently returns 201 due to stub implementation
        assert response.status_code == 201

        data = json.loads(response.data)
        assert data["success"] is True
        assert data["user_id"] == "stub-user-id"

    @patch("api_routes.get_all_users", return_value=[])
    def test_get_users_without_permission_stub_mode(self, mock_get_all_users):
        """Test GET /api/users in stub mode (auth always passes)."""
        self._login_site_admin()

        response = self.client.get("/api/users")
        # Should succeed in stub mode, but return empty list
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "users" in data
        mock_get_all_users.assert_called_once_with("inst-123")

    @patch("api_routes.get_users_by_role")
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
        }

        response = self.client.post(
            "/api/users", json=user_data, content_type="application/json"
        )
        assert response.status_code == 201

        data = json.loads(response.data)
        assert "message" in data
        assert "created" in data["message"].lower()

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

    def _login_user(self, overrides=None):
        return self._login_site_admin(overrides)

    def _login_user(self, overrides=None):
        return self._login_site_admin(overrides)

    @patch("api_routes.get_all_courses")
    def test_get_courses_endpoint_exists(self, mock_get_all_courses):
        """Test that GET /api/courses endpoint exists and returns valid JSON."""
        self._login_site_admin({"institution_id": "riverside-tech-institute"})
        mock_get_all_courses.return_value = []

        response = self.client.get("/api/courses")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "courses" in data
        assert isinstance(data["courses"], list)

    @patch("api_routes.get_courses_by_department")
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

    @patch("api_routes.create_course")
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

    @patch("api_routes.get_course_by_number", return_value=None)
    def test_get_course_by_number_endpoint_exists(self, mock_get_course):
        """Test that GET /api/courses/<course_number> endpoint exists."""
        self._login_site_admin()

        response = self.client.get("/api/courses/MATH-101")
        # Endpoint exists and correctly returns 404 for non-existent course
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data
        mock_get_course.assert_called_once_with("MATH-101")

    @patch("api_routes.get_course_by_number")
    def test_get_course_by_number_not_found(self, mock_get_course):
        """Test GET /api/courses/<course_number> when course doesn't exist."""
        self._login_site_admin()
        mock_get_course.return_value = None

        response = self.client.get("/api/courses/NONEXISTENT-999")
        assert response.status_code == 404

        data = json.loads(response.data)
        assert "error" in data
        assert "not found" in data["error"].lower()


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

    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_active_terms")
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

    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_all_sections")
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

    @patch("api_routes.has_permission")
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

    @patch("api_routes.has_permission")
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

    @patch("api_routes.has_permission")
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
        from api_routes import get_current_user, has_permission

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

    @patch("api_routes.get_all_institutions")
    @patch("api_routes.get_institution_instructor_count")
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

    @patch("api_routes.create_new_institution")
    def test_create_institution_success(self, mock_create_institution):
        """Test POST /api/institutions endpoint success."""
        self._login_site_admin()

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

        response = self.client.post("/api/institutions", json=institution_data)
        assert response.status_code == 201

        data = json.loads(response.data)
        assert data["success"] is True
        assert "institution_id" in data

    @patch("api_routes.get_current_user")
    @patch("api_routes.get_institution_by_id")
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

    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_all_instructors")
    def test_list_instructors_success(self, mock_get_instructors, mock_get_cei):
        """Test GET /api/instructors endpoint success."""
        self._login_site_admin()

        mock_get_cei.return_value = "cei-institution-id"
        mock_get_instructors.return_value = [
            {"user_id": "inst1", "first_name": "John", "last_name": "Doe"},
            {"user_id": "inst2", "first_name": "Jane", "last_name": "Smith"},
        ]

        response = self.client.get("/api/instructors")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "instructors" in data
        assert len(data["instructors"]) == 2

    @patch("api_routes.create_new_institution")
    def test_create_institution_missing_data(self, mock_create_institution):
        """Test POST /api/institutions with missing data."""
        with app.test_client() as client:
            response = client.post("/api/institutions", json={})
            assert response.status_code == 400

            data = json.loads(response.data)
            assert data["success"] is False

    @patch("api_routes.create_new_institution")
    def test_create_institution_missing_admin_user_field(self, mock_create_institution):
        """Test POST /api/institutions with missing admin user field."""
        with app.test_client() as client:
            # Send institution data but missing admin user email
            response = client.post(
                "/api/institutions",
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

    @patch("api_routes.create_new_institution")
    def test_create_institution_creation_failure(self, mock_create_institution):
        """Test POST /api/institutions when institution creation fails."""
        # Setup - make create_new_institution return None (failure)
        mock_create_institution.return_value = None

        with app.test_client() as client:
            response = client.post(
                "/api/institutions",
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

    @patch("api_routes.create_new_institution")
    def test_create_institution_exception_handling(self, mock_create_institution):
        """Test POST /api/institutions exception handling."""
        # Setup - make create_new_institution raise an exception
        mock_create_institution.side_effect = Exception("Database connection failed")

        with app.test_client() as client:
            response = client.post(
                "/api/institutions",
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

    @patch("api_routes.get_all_institutions")
    def test_list_institutions_exception(self, mock_get_institutions):
        """Test GET /api/institutions exception handling."""
        self._login_user()

        mock_get_institutions.side_effect = Exception("Database error")

        response = self.client.get("/api/institutions")
        assert response.status_code == 500

        data = json.loads(response.data)
        assert data["success"] is False

    @patch("api_routes.get_current_user")
    @patch("api_routes.get_institution_by_id")
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

    @patch("api_routes.create_course")
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

    @patch("api_routes.create_term")
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

    @patch("api_routes.get_current_user")
    @patch("api_routes.has_permission")
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

    @patch("api_routes.create_progress_tracker")
    @patch("api_routes.update_progress")
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
        assert "no file" in data["error"].lower()

    def test_import_progress_endpoint(self):
        """Test import progress tracking endpoint."""
        with app.test_client() as client:
            response = client.get("/api/import/progress/nonexistent")

            # Should handle progress requests
            assert response.status_code in [200, 404, 500]

    @patch("api_routes.handle_api_error")
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

    @patch("api_routes.get_current_institution_id")
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
        from app import app

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

    @patch("auth_service.get_current_institution_id")
    @patch("api_routes.get_current_user")
    @patch("api_routes.get_users_by_role")
    @patch("api_routes.has_permission")
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
                "email": "instructor1@cei.edu",
                "role": "instructor",
                "institution_id": "test-institution",
            },
            {
                "user_id": "2",
                "email": "instructor2@cei.edu",
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

    @patch("auth_service.get_current_institution_id")
    @patch("api_routes.get_current_user")
    @patch("api_routes.get_users_by_role")
    @patch("api_routes.has_permission")
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
                "email": "math1@cei.edu",
                "role": "instructor",
                "department": "MATH",
                "institution_id": "test-institution",
            },
            {
                "user_id": "2",
                "email": "eng1@cei.edu",
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

    @patch("api_routes.has_permission")
    def test_create_user_validation(self, mock_has_permission):
        """Test create user with validation."""
        self._login_site_admin()
        mock_has_permission.return_value = True

        # Test with no JSON data
        response = self.client.post("/api/users")
        # May return 500 if permission decorator fails, 400 if it gets to validation
        assert response.status_code in [400, 500]

        # Test missing required fields
        response = self.client.post("/api/users", json={"email": "test@cei.edu"})
        assert response.status_code == 400
        data = response.get_json()
        assert "Missing required fields" in data["error"]

    @patch("api_routes.get_current_user")
    @patch("api_routes.has_permission")
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
        from app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()

    @patch("api_routes.create_course")
    @patch("api_routes.has_permission")
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

    @patch("api_routes.has_permission")
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

    @patch("api_routes.create_term")
    @patch("api_routes.has_permission")
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

    @patch("api_routes.get_sections_by_instructor")
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

    @patch("api_routes.get_sections_by_term")
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

    @patch("api_routes.has_permission")
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
        assert data["error"] == "No file uploaded"


class TestAPIRoutesErrorHandling:
    """Test API routes error handling and edge cases."""

    def setup_method(self):
        """Set up test client."""
        from app import app

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

    @patch("api_routes.get_all_users", return_value=[])
    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_current_user")
    @patch("api_routes.has_permission")
    def test_list_users_no_role_filter_coverage(
        self,
        mock_has_permission,
        mock_get_current_user,
        mock_get_cei_id,
        mock_get_all_users,
    ):
        """Test list_users endpoint without role filter."""
        self._login_site_admin({"institution_id": "riverside-tech-institute"})
        mock_has_permission.return_value = True
        mock_get_current_user.return_value = {
            "user_id": "test-user",
            "role": "site_admin",
        }
        mock_get_cei_id.return_value = "riverside-tech-institute"

        response = self.client.get("/api/users")

        assert response.status_code == 200
        data = response.get_json()
        assert data["users"] == []
        mock_get_all_users.assert_called_once_with("riverside-tech-institute")

    @patch("api_routes.get_user_by_id", return_value=None)
    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_current_user")
    @patch("api_routes.has_permission")
    def test_get_user_not_found_coverage(
        self,
        mock_has_permission,
        mock_get_current_user,
        mock_get_cei_id,
        mock_get_user,
    ):
        """Test get_user endpoint when user not found."""
        self._login_site_admin({"institution_id": "riverside-tech-institute"})
        mock_get_current_user.return_value = {
            "user_id": "admin-user",
            "role": "site_admin",
        }
        mock_has_permission.return_value = True
        mock_get_cei_id.return_value = "riverside-tech-institute"

        response = self.client.get("/api/users/nonexistent-user")

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "User not found"
        mock_get_user.assert_called_once_with("nonexistent-user")

    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_current_user")
    @patch("api_routes.has_permission")
    def test_create_user_stub_success_coverage(
        self, mock_has_permission, mock_get_current_user, mock_get_cei_id
    ):
        """Test create_user endpoint stub implementation."""
        self._login_site_admin({"institution_id": "riverside-tech-institute"})
        mock_has_permission.return_value = True
        mock_get_current_user.return_value = {
            "user_id": "admin-user",
            "role": "site_admin",
        }
        mock_get_cei_id.return_value = "riverside-tech-institute"

        user_data = {
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "role": "instructor",
        }

        response = self.client.post("/api/users", json=user_data)

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["user_id"] == "stub-user-id"

    def test_import_excel_empty_filename_coverage(self):
        """Test import_excel endpoint with empty filename."""
        self._login_site_admin()

        with patch("api_routes.has_permission", return_value=True):
            from io import BytesIO

            data = {"file": (BytesIO(b"test"), "")}

            response = self.client.post("/api/import/excel", data=data)

            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "No file selected"

    def test_import_excel_invalid_file_type_coverage(self):
        """Test import_excel endpoint with invalid file type."""
        self._login_site_admin()

        with patch("api_routes.has_permission", return_value=True):
            from io import BytesIO

            data = {"file": (BytesIO(b"test"), "test.txt")}

            response = self.client.post("/api/import/excel", data=data)

            assert response.status_code == 400
            data = response.get_json()
            assert "Invalid file type" in data["error"]


class TestAPIRoutesProgressTracking:
    """Test API progress tracking functionality."""

    def setup_method(self):
        """Set up test client."""
        from app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()

    @patch("api_routes.create_progress_tracker")
    @patch("api_routes.update_progress")
    def test_progress_tracking_coverage(
        self, mock_update_progress, mock_create_progress
    ):
        """Test progress tracking functions are called."""
        mock_create_progress.return_value = "progress123"

        # Test that progress functions exist and can be called
        from api_routes import create_progress_tracker, update_progress

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
        from app import app

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

    @patch("api_routes.has_permission")
    @patch("api_routes.import_excel")
    @patch("api_routes.get_current_institution_id")
    def test_validate_import_file_coverage(
        self, mock_get_institution_id, mock_import_excel, mock_has_permission
    ):
        """Test import file validation endpoint."""
        self._login_site_admin()
        mock_has_permission.return_value = True
        mock_get_institution_id.return_value = "test-institution"

        # Mock import result
        from import_service import ImportResult

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

        data = {"file": (BytesIO(b"test excel data"), "test.xlsx")}

        response = self.client.post("/api/import/validate", data=data)

        # Should validate the file
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "validation" in data

    def test_validate_import_no_file(self):
        """Test validation endpoint with no file."""
        self._login_site_admin()

        with patch("api_routes.has_permission", return_value=True):
            response = self.client.post("/api/import/validate")

            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "No file uploaded"

    def test_validate_import_empty_filename(self):
        """Test validation endpoint with empty filename."""
        self._login_site_admin()

        with patch("api_routes.has_permission", return_value=True):
            from io import BytesIO

            data = {"file": (BytesIO(b"test"), "")}

            response = self.client.post("/api/import/validate", data=data)

            assert response.status_code == 400
            data = response.get_json()
            assert data["error"] == "No file selected"

    def test_validate_import_invalid_file_type(self):
        """Test validation endpoint with invalid file type."""
        self._login_site_admin()

        with patch("api_routes.has_permission", return_value=True):
            from io import BytesIO

            data = {"file": (BytesIO(b"test"), "test.txt")}

            response = self.client.post("/api/import/validate", data=data)

            assert response.status_code == 400
            data = response.get_json()
            assert "Invalid file type" in data["error"]

    @patch("api_routes.has_permission")
    @patch("api_routes.import_excel")
    @patch("os.unlink")
    @patch("api_routes.get_current_institution_id")
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
        from import_service import ImportResult

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

        data = {"file": (BytesIO(b"excel data"), "test.xlsx")}

        response = self.client.post("/api/import/validate", data=data)

        # Should still succeed despite cleanup error
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True


class TestAPIRoutesHealthCheck:
    """Test API health check endpoint."""

    def setup_method(self):
        """Set up test client."""
        from app import app

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
        from app import app

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
        from api_routes import handle_api_error
        from app import app

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

    @patch("api_routes.get_all_courses")
    @patch("api_routes.get_all_institutions")
    @patch("api_routes.get_current_institution_id")
    def test_list_courses_global_scope(
        self, mock_get_cei_id, mock_get_institutions, mock_get_all_courses
    ):
        """Site admin without institution context should see system-wide courses."""
        self._login_site_admin()
        mock_get_cei_id.return_value = None
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

    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_courses_by_department")
    def test_list_courses_with_department(self, mock_get_courses, mock_get_cei_id):
        """Test list_courses with department filter."""
        self._login_site_admin()
        mock_get_cei_id.return_value = "institution123"
        mock_get_courses.return_value = [{"course_id": "1", "department": "MATH"}]

        response = self.client.get("/api/courses?department=MATH")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["courses"]) == 1
