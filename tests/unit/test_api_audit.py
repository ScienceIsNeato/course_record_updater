"""
Unit tests for Audit API routes.
"""

# Patch permission_required BEFORE importing audit routes
import sys
from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

with patch("src.services.auth_service.permission_required", lambda perm: lambda f: f):
    if "src.api.routes.audit" in sys.modules:
        del sys.modules["src.api.routes.audit"]
    from src.api.routes.audit import audit_bp

from src.services.audit_service import EntityType


@pytest.fixture
def app():
    """Create test Flask app with audit blueprint."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(audit_bp)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_site_admin():
    """Mock site admin user."""
    return {
        "user_id": "admin-123",
        "email": "admin@test.com",
        "role": "site_admin",
        "institution_id": "inst-123",
    }


class TestGetRecentLogs:
    """Tests for GET /api/audit/recent endpoint."""

    @patch("src.api.routes.audit.AuditService.get_recent_activity")
    def test_get_recent_logs_success(self, mock_get_activity, client):
        """Test successful retrieval of recent logs."""
        mock_logs = [
            {"log_id": "1", "operation": "CREATE", "entity_type": "user"},
            {"log_id": "2", "operation": "UPDATE", "entity_type": "courses"},
        ]
        mock_get_activity.return_value = mock_logs

        response = client.get("/api/audit/recent")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["logs"] == mock_logs
        assert data["total"] == 2
        assert data["limit"] == 50
        assert data["offset"] == 0

    @patch("src.api.routes.audit.AuditService.get_recent_activity")
    def test_get_recent_logs_with_limit_and_offset(self, mock_get_activity, client):
        """Test recent logs with custom limit and offset."""
        mock_get_activity.return_value = []

        response = client.get("/api/audit/recent?limit=100&offset=50")

        assert response.status_code == 200
        data = response.get_json()
        assert data["limit"] == 100
        assert data["offset"] == 50
        mock_get_activity.assert_called_once_with(institution_id=None, limit=100)

    @patch("src.api.routes.audit.AuditService.get_recent_activity")
    def test_get_recent_logs_with_institution_filter(self, mock_get_activity, client):
        """Test recent logs filtered by institution."""
        mock_get_activity.return_value = []

        response = client.get("/api/audit/recent?institution_id=inst-123")

        assert response.status_code == 200
        mock_get_activity.assert_called_once_with(institution_id="inst-123", limit=50)

    @patch("src.api.routes.audit.AuditService.get_recent_activity")
    def test_get_recent_logs_limit_capped_at_500(self, mock_get_activity, client):
        """Test that limit is capped at 500."""
        mock_get_activity.return_value = []

        response = client.get("/api/audit/recent?limit=1000")

        assert response.status_code == 200
        data = response.get_json()
        assert data["limit"] == 500
        mock_get_activity.assert_called_once_with(institution_id=None, limit=500)

    @patch("src.api.routes.audit.AuditService.get_recent_activity")
    def test_get_recent_logs_invalid_limit(self, mock_get_activity, client):
        """Test error handling for invalid limit parameter."""
        response = client.get("/api/audit/recent?limit=invalid")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid parameter" in data["error"]

    @patch("src.api.routes.audit.AuditService.get_recent_activity")
    def test_get_recent_logs_service_error(self, mock_get_activity, client):
        """Test error handling when service raises exception."""
        mock_get_activity.side_effect = Exception("Database error")

        response = client.get("/api/audit/recent")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to fetch audit logs" in data["error"]


class TestGetEntityHistory:
    """Tests for GET /api/audit/entity/<entity_type>/<entity_id> endpoint."""

    @patch("src.api.routes.audit.AuditService.get_entity_history")
    def test_get_entity_history_success(self, mock_get_history, client):
        """Test successful retrieval of entity history."""
        mock_history = [
            {"log_id": "1", "operation": "CREATE", "timestamp": "2025-01-01T00:00:00Z"},
            {"log_id": "2", "operation": "UPDATE", "timestamp": "2025-01-02T00:00:00Z"},
        ]
        mock_get_history.return_value = mock_history

        response = client.get("/api/audit/entity/user/user-123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["entity_type"] == "user"
        assert data["entity_id"] == "user-123"
        assert data["history"] == mock_history
        assert data["total_changes"] == 2
        mock_get_history.assert_called_once_with(
            entity_type=EntityType.USER, entity_id="user-123", limit=100
        )

    @patch("src.api.routes.audit.AuditService.get_entity_history")
    def test_get_entity_history_with_limit(self, mock_get_history, client):
        """Test entity history with custom limit."""
        mock_get_history.return_value = []

        response = client.get("/api/audit/entity/course/course-456?limit=50")

        assert response.status_code == 200
        mock_get_history.assert_called_once_with(
            entity_type=EntityType.COURSE, entity_id="course-456", limit=50
        )

    @patch("src.api.routes.audit.AuditService.get_entity_history")
    def test_get_entity_history_limit_capped_at_1000(self, mock_get_history, client):
        """Test that limit is capped at 1000."""
        mock_get_history.return_value = []

        response = client.get("/api/audit/entity/user/user-123?limit=5000")

        assert response.status_code == 200
        mock_get_history.assert_called_once_with(
            entity_type=EntityType.USER, entity_id="user-123", limit=1000
        )

    def test_get_entity_history_invalid_entity_type(self, client):
        """Test error handling for invalid entity type."""
        response = client.get("/api/audit/entity/invalid_type/entity-123")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid entity type" in data["error"]

    @patch("src.api.routes.audit.AuditService.get_entity_history")
    def test_get_entity_history_service_error(self, mock_get_history, client):
        """Test error handling when service raises exception."""
        mock_get_history.side_effect = Exception("Database error")

        response = client.get("/api/audit/entity/user/user-123")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to fetch entity history" in data["error"]


class TestGetUserActivity:
    """Tests for GET /api/audit/user/<user_id> endpoint."""

    @patch("src.api.routes.audit.AuditService.get_user_activity")
    def test_get_user_activity_success(self, mock_get_activity, client):
        """Test successful retrieval of user activity."""
        mock_activity = [
            {"log_id": "1", "operation": "CREATE", "entity_type": "user"},
            {"log_id": "2", "operation": "UPDATE", "entity_type": "courses"},
        ]
        mock_get_activity.return_value = mock_activity

        response = client.get("/api/audit/user/user-123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["user_id"] == "user-123"
        assert data["activity"] == mock_activity
        assert data["total_actions"] == 2
        mock_get_activity.assert_called_once_with(
            user_id="user-123", limit=100, start_date=None, end_date=None
        )

    @patch("src.api.routes.audit.AuditService.get_user_activity")
    def test_get_user_activity_with_date_range(self, mock_get_activity, client):
        """Test user activity with date range filter."""
        mock_get_activity.return_value = []

        response = client.get(
            "/api/audit/user/user-123?start_date=2025-01-01T00:00:00Z&end_date=2025-01-31T23:59:59Z"
        )

        assert response.status_code == 200
        call_args = mock_get_activity.call_args
        assert call_args.kwargs["user_id"] == "user-123"
        assert call_args.kwargs["limit"] == 100
        assert isinstance(call_args.kwargs["start_date"], datetime)
        assert isinstance(call_args.kwargs["end_date"], datetime)

    @patch("src.api.routes.audit.AuditService.get_user_activity")
    def test_get_user_activity_with_limit(self, mock_get_activity, client):
        """Test user activity with custom limit."""
        mock_get_activity.return_value = []

        response = client.get("/api/audit/user/user-123?limit=50")

        assert response.status_code == 200
        mock_get_activity.assert_called_once_with(
            user_id="user-123", limit=50, start_date=None, end_date=None
        )

    def test_get_user_activity_invalid_start_date(self, client):
        """Test error handling for invalid start_date format."""
        response = client.get("/api/audit/user/user-123?start_date=invalid-date")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid start_date format" in data["error"]

    def test_get_user_activity_invalid_end_date(self, client):
        """Test error handling for invalid end_date format."""
        response = client.get("/api/audit/user/user-123?end_date=invalid-date")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid end_date format" in data["error"]

    @patch("src.api.routes.audit.AuditService.get_user_activity")
    def test_get_user_activity_service_error(self, mock_get_activity, client):
        """Test error handling when service raises exception."""
        mock_get_activity.side_effect = Exception("Database error")

        response = client.get("/api/audit/user/user-123")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to fetch user activity" in data["error"]


class TestExportLogs:
    """Tests for POST /api/audit/export endpoint."""

    @patch("src.api.routes.audit.AuditService.export_audit_log")
    def test_export_logs_csv_success(self, mock_export, client):
        """Test successful CSV export."""
        mock_export.return_value = b"log_id,operation,entity_type\n1,CREATE,users\n"

        response = client.post(
            "/api/audit/export",
            json={
                "format": "csv",
                "start_date": "2025-01-01T00:00:00Z",
                "end_date": "2025-01-31T23:59:59Z",
            },
        )

        assert response.status_code == 200
        assert response.mimetype == "text/csv"
        assert "audit_logs_" in response.headers["Content-Disposition"]
        assert ".csv" in response.headers["Content-Disposition"]

    @patch("src.api.routes.audit.AuditService.export_audit_log")
    def test_export_logs_json_success(self, mock_export, client):
        """Test successful JSON export."""
        mock_export.return_value = b'[{"log_id": "1", "operation": "CREATE"}]'

        response = client.post(
            "/api/audit/export",
            json={
                "format": "json",
                "start_date": "2025-01-01T00:00:00Z",
                "end_date": "2025-01-31T23:59:59Z",
            },
        )

        assert response.status_code == 200
        assert response.mimetype == "application/json"
        assert "audit_logs_" in response.headers["Content-Disposition"]
        assert ".json" in response.headers["Content-Disposition"]

    @patch("src.api.routes.audit.AuditService.export_audit_log")
    def test_export_logs_with_filters(self, mock_export, client):
        """Test export with optional filters."""
        mock_export.return_value = b"csv_data"

        response = client.post(
            "/api/audit/export",
            json={
                "format": "csv",
                "start_date": "2025-01-01T00:00:00Z",
                "end_date": "2025-01-31T23:59:59Z",
                "entity_type": "user",
                "user_id": "user-123",
                "institution_id": "inst-456",
            },
        )

        assert response.status_code == 200
        call_args = mock_export.call_args
        assert call_args.kwargs["entity_type"] == EntityType.USER
        assert call_args.kwargs["user_id"] == "user-123"
        assert call_args.kwargs["institution_id"] == "inst-456"

    def test_export_logs_invalid_format(self, client):
        """Test error handling for invalid export format."""
        response = client.post(
            "/api/audit/export",
            json={
                "format": "xml",
                "start_date": "2025-01-01T00:00:00Z",
                "end_date": "2025-01-31T23:59:59Z",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid format" in data["error"]

    def test_export_logs_missing_start_date(self, client):
        """Test error handling for missing start_date."""
        response = client.post(
            "/api/audit/export",
            json={"format": "csv", "end_date": "2025-01-31T23:59:59Z"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "start_date and end_date are required" in data["error"]

    def test_export_logs_missing_end_date(self, client):
        """Test error handling for missing end_date."""
        response = client.post(
            "/api/audit/export",
            json={"format": "csv", "start_date": "2025-01-01T00:00:00Z"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "start_date and end_date are required" in data["error"]

    def test_export_logs_invalid_date_format(self, client):
        """Test error handling for invalid date format."""
        response = client.post(
            "/api/audit/export",
            json={
                "format": "csv",
                "start_date": "invalid-date",
                "end_date": "2025-01-31T23:59:59Z",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid date format" in data["error"]

    def test_export_logs_invalid_entity_type(self, client):
        """Test error handling for invalid entity type."""
        response = client.post(
            "/api/audit/export",
            json={
                "format": "csv",
                "start_date": "2025-01-01T00:00:00Z",
                "end_date": "2025-01-31T23:59:59Z",
                "entity_type": "invalid_type",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid entity type" in data["error"]

    @patch("src.api.routes.audit.AuditService.export_audit_log")
    def test_export_logs_service_error(self, mock_export, client):
        """Test error handling when service raises exception."""
        mock_export.side_effect = Exception("Export failed")

        response = client.post(
            "/api/audit/export",
            json={
                "format": "csv",
                "start_date": "2025-01-01T00:00:00Z",
                "end_date": "2025-01-31T23:59:59Z",
            },
        )

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to export audit logs" in data["error"]
