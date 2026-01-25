"""Unit tests for dashboard and health API routes (migrated from test_api_routes.py)."""

import json
from unittest.mock import patch

from src.app import app


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
