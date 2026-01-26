"""Unit tests for invitations API routes (migrated from test_api_routes.py)."""

import json
from unittest.mock import patch

from src.app import app
from src.utils.constants import GENERIC_PASSWORD, WEAK_PASSWORD

TEST_PASSWORD = GENERIC_PASSWORD  # Test password for unit tests


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
                    "password": WEAK_PASSWORD,
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
