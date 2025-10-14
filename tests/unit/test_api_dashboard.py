"""
Unit tests for Dashboard API routes.
"""

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

# Patch login_required BEFORE importing dashboard routes
with patch("auth_service.login_required", lambda f: f):
    from api.routes.dashboard import dashboard_bp

from dashboard_service import DashboardServiceError


@pytest.fixture
def app():
    """Create test Flask app with dashboard blueprint."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(dashboard_bp)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "user_id": "user-123",
        "email": "user@test.com",
        "role": "program_admin",
        "institution_id": "inst-123",
    }


class TestGetDashboardData:
    """Tests for GET /api/dashboard/data endpoint."""

    @patch("api.routes.dashboard.DashboardService")
    @patch("api.routes.dashboard.get_current_user")
    def test_get_dashboard_data_success(
        self, mock_get_user, mock_service_class, client, mock_user
    ):
        """Test successful dashboard data retrieval."""
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        mock_dashboard_data = {
            "summary": {"courses": 10, "students": 50},
            "recent_activity": [],
            "program_overview": [],
        }
        mock_service.get_dashboard_data.return_value = mock_dashboard_data

        response = client.get("/api/dashboard/data")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"] == mock_dashboard_data
        mock_service.get_dashboard_data.assert_called_once_with(mock_user)

    @patch("api.routes.dashboard.DashboardService")
    @patch("api.routes.dashboard.get_current_user")
    def test_get_dashboard_data_service_error(
        self, mock_get_user, mock_service_class, client, mock_user
    ):
        """Test error handling when DashboardService raises DashboardServiceError."""
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_dashboard_data.side_effect = DashboardServiceError(
            "Service error"
        )

        response = client.get("/api/dashboard/data")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to load dashboard data" in data["error"]

    @patch("api.routes.dashboard.DashboardService")
    @patch("api.routes.dashboard.get_current_user")
    def test_get_dashboard_data_generic_exception(
        self, mock_get_user, mock_service_class, client, mock_user
    ):
        """Test error handling when service raises generic exception."""
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_dashboard_data.side_effect = Exception("Unexpected error")

        response = client.get("/api/dashboard/data")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to load dashboard data" in data["error"]
