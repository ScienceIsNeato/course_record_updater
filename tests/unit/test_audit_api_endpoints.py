"""Unit tests for Audit Log API endpoints."""

from datetime import datetime, timedelta
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from app import app
from tests.test_utils import create_test_session


@pytest.fixture
def client():
    """Create test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def create_site_admin_session(client):
    """Create session for site admin user."""
    user_data = {
        "user_id": "site-admin-123",
        "role": "site_admin",
        "institution_id": "inst-1",
        "email": "siteadmin@example.com",
    }
    create_test_session(client, user_data)


def get_csrf_token(client):
    """Get CSRF token using Flask-WTF's generate_csrf."""
    from flask import session as flask_session
    from flask_wtf.csrf import generate_csrf

    # Get the raw token from the session (created by create_test_session)
    with client.session_transaction() as sess:
        raw_token = sess.get("csrf_token")

    # Generate the signed token from the raw token
    with client.application.test_request_context():
        if raw_token:
            flask_session["csrf_token"] = raw_token
        return generate_csrf()


# ============================================================================
# GET /api/audit/recent TESTS
# ============================================================================


class TestAuditRecentEndpoint:
    """Tests for GET /api/audit/recent endpoint"""

    @patch("audit_service.AuditService.get_recent_activity")
    def test_get_recent_logs_success(self, mock_get_recent, client):
        """Test GET /api/audit/recent - success"""
        create_site_admin_session(client)
        mock_get_recent.return_value = [
            {
                "audit_id": "audit-1",
                "timestamp": "2025-10-08T12:00:00Z",
                "user_email": "admin@example.com",
                "operation_type": "CREATE",
                "entity_type": "users",
                "entity_id": "user-123",
            },
            {
                "audit_id": "audit-2",
                "timestamp": "2025-10-08T11:00:00Z",
                "user_email": "admin@example.com",
                "operation_type": "UPDATE",
                "entity_type": "courses",
                "entity_id": "course-456",
            },
        ]

        response = client.get("/api/audit/recent")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["logs"]) == 2
        assert data["total"] == 2
        assert data["limit"] == 50  # default limit
        assert data["logs"][0]["entity_type"] == "users"

    @patch("audit_service.AuditService.get_recent_activity")
    def test_get_recent_logs_with_limit(self, mock_get_recent, client):
        """Test GET /api/audit/recent with custom limit"""
        create_site_admin_session(client)
        mock_get_recent.return_value = []

        response = client.get("/api/audit/recent?limit=100")

        assert response.status_code == 200
        mock_get_recent.assert_called_once_with(institution_id=None, limit=100)

    @patch("audit_service.AuditService.get_recent_activity")
    def test_get_recent_logs_with_institution_filter(self, mock_get_recent, client):
        """Test GET /api/audit/recent with institution_id filter"""
        create_site_admin_session(client)
        mock_get_recent.return_value = []

        response = client.get("/api/audit/recent?institution_id=inst-123")

        assert response.status_code == 200
        mock_get_recent.assert_called_once_with(institution_id="inst-123", limit=50)

    @patch("audit_service.AuditService.get_recent_activity")
    def test_get_recent_logs_limit_capped_at_500(self, mock_get_recent, client):
        """Test that limit is capped at 500"""
        create_site_admin_session(client)
        mock_get_recent.return_value = []

        response = client.get("/api/audit/recent?limit=9999")

        assert response.status_code == 200
        mock_get_recent.assert_called_once_with(institution_id=None, limit=500)

    def test_get_recent_logs_requires_admin(self, client):
        """Test that non-admin users cannot access audit logs"""
        # Create instructor session (not site admin)
        user_data = {
            "user_id": "instructor-123",
            "role": "instructor",
            "institution_id": "inst-1",
            "email": "instructor@example.com",
        }
        create_test_session(client, user_data)

        response = client.get("/api/audit/recent")

        assert response.status_code == 403


# ============================================================================
# GET /api/audit/entity/<type>/<id> TESTS
# ============================================================================


class TestAuditEntityHistoryEndpoint:
    """Tests for GET /api/audit/entity/<type>/<id> endpoint"""

    @patch("audit_service.AuditService.get_entity_history")
    def test_get_entity_history_success(self, mock_get_history, client):
        """Test GET /api/audit/entity/<type>/<id> - success"""
        create_site_admin_session(client)
        mock_get_history.return_value = [
            {
                "audit_id": "audit-1",
                "timestamp": "2025-10-08T12:00:00Z",
                "operation_type": "CREATE",
                "old_values": None,
                "new_values": '{"name": "Test User"}',
            },
            {
                "audit_id": "audit-2",
                "timestamp": "2025-10-08T13:00:00Z",
                "operation_type": "UPDATE",
                "old_values": '{"name": "Test User"}',
                "new_values": '{"name": "Updated User"}',
            },
        ]

        response = client.get("/api/audit/entity/user/user-123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["entity_type"] == "user"
        assert data["entity_id"] == "user-123"
        assert data["total_changes"] == 2
        assert len(data["history"]) == 2

    @patch("audit_service.AuditService.get_entity_history")
    def test_get_entity_history_with_limit(self, mock_get_history, client):
        """Test entity history with custom limit"""
        create_site_admin_session(client)
        mock_get_history.return_value = []

        response = client.get("/api/audit/entity/course/course-456?limit=200")

        assert response.status_code == 200
        # Verify the call was made with correct EntityType enum and limit
        assert mock_get_history.called
        call_args = mock_get_history.call_args
        assert call_args.kwargs["entity_id"] == "course-456"
        assert call_args.kwargs["limit"] == 200

    def test_get_entity_history_invalid_entity_type(self, client):
        """Test entity history with invalid entity type"""
        create_site_admin_session(client)

        response = client.get("/api/audit/entity/invalid_type/id-123")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid entity type" in data["error"]

    @patch("audit_service.AuditService.get_entity_history")
    def test_get_entity_history_limit_capped_at_1000(self, mock_get_history, client):
        """Test that limit is capped at 1000"""
        create_site_admin_session(client)
        mock_get_history.return_value = []

        response = client.get("/api/audit/entity/user/user-123?limit=9999")

        assert response.status_code == 200
        call_args = mock_get_history.call_args
        assert call_args.kwargs["limit"] == 1000


# ============================================================================
# GET /api/audit/user/<id> TESTS
# ============================================================================


class TestAuditUserActivityEndpoint:
    """Tests for GET /api/audit/user/<id> endpoint"""

    @patch("audit_service.AuditService.get_user_activity")
    def test_get_user_activity_success(self, mock_get_activity, client):
        """Test GET /api/audit/user/<id> - success"""
        create_site_admin_session(client)
        mock_get_activity.return_value = [
            {
                "audit_id": "audit-1",
                "timestamp": "2025-10-08T12:00:00Z",
                "operation_type": "CREATE",
                "entity_type": "users",
                "entity_id": "user-456",
            },
            {
                "audit_id": "audit-2",
                "timestamp": "2025-10-08T13:00:00Z",
                "operation_type": "UPDATE",
                "entity_type": "courses",
                "entity_id": "course-789",
            },
        ]

        response = client.get("/api/audit/user/user-123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["user_id"] == "user-123"
        assert data["total_actions"] == 2
        assert len(data["activity"]) == 2

    @patch("audit_service.AuditService.get_user_activity")
    def test_get_user_activity_with_date_range(self, mock_get_activity, client):
        """Test user activity with date range filtering"""
        create_site_admin_session(client)
        mock_get_activity.return_value = []

        response = client.get(
            "/api/audit/user/user-123"
            "?start_date=2025-10-01T00:00:00Z"
            "&end_date=2025-10-08T23:59:59Z"
        )

        assert response.status_code == 200
        # Verify dates were parsed and passed correctly
        assert mock_get_activity.called
        call_args = mock_get_activity.call_args
        assert call_args.kwargs["user_id"] == "user-123"
        assert call_args.kwargs["start_date"] is not None
        assert call_args.kwargs["end_date"] is not None
        assert isinstance(call_args.kwargs["start_date"], datetime)

    def test_get_user_activity_invalid_start_date(self, client):
        """Test user activity with invalid start_date format"""
        create_site_admin_session(client)

        response = client.get("/api/audit/user/user-123?start_date=invalid-date")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid start_date format" in data["error"]

    def test_get_user_activity_invalid_end_date(self, client):
        """Test user activity with invalid end_date format"""
        create_site_admin_session(client)

        response = client.get("/api/audit/user/user-123?end_date=not-a-date")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid end_date format" in data["error"]


# ============================================================================
# POST /api/audit/export TESTS
# ============================================================================


class TestAuditExportEndpoint:
    """Tests for POST /api/audit/export endpoint"""

    @patch("audit_service.AuditService.export_audit_log")
    def test_export_logs_csv_success(self, mock_export, client):
        """Test POST /api/audit/export - CSV format"""
        create_site_admin_session(client)
        mock_export.return_value = (
            b"timestamp,user_email,operation\n2025-10-08,admin@example.com,CREATE\n"
        )

        response = client.post(
            "/api/audit/export",
            json={
                "format": "csv",
                "start_date": "2025-10-01T00:00:00Z",
                "end_date": "2025-10-08T23:59:59Z",
            },
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 200
        assert response.mimetype == "text/csv"
        assert b"timestamp,user_email,operation" in response.data

    @patch("audit_service.AuditService.export_audit_log")
    def test_export_logs_json_success(self, mock_export, client):
        """Test POST /api/audit/export - JSON format"""
        create_site_admin_session(client)
        mock_export.return_value = (
            b'[{"timestamp": "2025-10-08", "operation": "CREATE"}]'
        )

        response = client.post(
            "/api/audit/export",
            json={
                "format": "json",
                "start_date": "2025-10-01T00:00:00Z",
                "end_date": "2025-10-08T23:59:59Z",
            },
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 200
        assert response.mimetype == "application/json"

    @patch("audit_service.AuditService.export_audit_log")
    def test_export_logs_with_filters(self, mock_export, client):
        """Test export with optional filters"""
        create_site_admin_session(client)
        mock_export.return_value = b"test"

        response = client.post(
            "/api/audit/export",
            json={
                "format": "csv",
                "start_date": "2025-10-01T00:00:00Z",
                "end_date": "2025-10-08T23:59:59Z",
                "entity_type": "user",
                "user_id": "user-123",
                "institution_id": "inst-456",
            },
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 200
        # Verify filters were passed
        assert mock_export.called
        call_args = mock_export.call_args
        assert call_args.kwargs["user_id"] == "user-123"
        assert call_args.kwargs["institution_id"] == "inst-456"

    def test_export_logs_missing_start_date(self, client):
        """Test export fails without start_date"""
        create_site_admin_session(client)

        response = client.post(
            "/api/audit/export",
            json={
                "format": "csv",
                "end_date": "2025-10-08T23:59:59Z",
            },
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "start_date and end_date are required" in data["error"]

    def test_export_logs_invalid_format(self, client):
        """Test export fails with invalid format"""
        create_site_admin_session(client)

        response = client.post(
            "/api/audit/export",
            json={
                "format": "xml",  # Invalid format
                "start_date": "2025-10-01T00:00:00Z",
                "end_date": "2025-10-08T23:59:59Z",
            },
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid format" in data["error"]

    def test_export_logs_invalid_entity_type(self, client):
        """Test export fails with invalid entity_type"""
        create_site_admin_session(client)

        response = client.post(
            "/api/audit/export",
            json={
                "format": "csv",
                "start_date": "2025-10-01T00:00:00Z",
                "end_date": "2025-10-08T23:59:59Z",
                "entity_type": "invalid_entity",
            },
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid entity type" in data["error"]
