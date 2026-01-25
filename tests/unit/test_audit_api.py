"""Tests for audit log API endpoints.

TDD tests for:
- Recent audit logs (GET /api/audit/recent)
"""

from unittest.mock import patch

from src.app import app


class TestAuditAPI:
    """Test audit log API endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.institution_admin_user = {
            "user_id": "inst-admin-123",
            "email": "admin@examples.com",
            "role": "institution_admin",
            "institution_id": "inst-123",
        }
        self.instructor_user = {
            "user_id": "instructor-456",
            "email": "instructor@example.com",
            "role": "instructor",
            "institution_id": "inst-123",
        }

    def _login_institution_admin(self):
        """Create authenticated session for institution admin."""
        from tests.test_utils import create_test_session

        create_test_session(self.client, self.institution_admin_user)

    def _login_instructor(self):
        """Create authenticated session for instructor."""
        from tests.test_utils import create_test_session

        create_test_session(self.client, self.instructor_user)

    def test_get_recent_audit_logs_requires_admin(self):
        """Test that non-admins cannot access audit logs."""
        self._login_instructor()

        response = self.client.get("/api/audit/recent")
        assert response.status_code == 403

    def test_get_recent_audit_logs_success(self):
        """Test successful retrieval of recent audit logs."""
        self._login_institution_admin()

        with patch(
            "src.api.routes.audit.AuditService.get_recent_activity"
        ) as mock_get_recent:
            mock_get_recent.return_value = [
                {
                    "id": "log-1",
                    "action": "create",
                    "entity_type": "user",
                    "user_id": "user-1",
                    "timestamp": "2023-01-01T12:00:00Z",
                }
            ]

            response = self.client.get("/api/audit/recent")

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert len(data["logs"]) == 1
            assert data["logs"][0]["id"] == "log-1"

            # Verify call with keyword args
            mock_get_recent.assert_called_once()

    def test_get_recent_audit_logs_database_error(self):
        """Test audit log retrieval handles database errors."""
        self._login_institution_admin()

        with patch(
            "src.api.routes.audit.AuditService.get_recent_activity"
        ) as mock_get_recent:
            mock_get_recent.side_effect = Exception("Database error")

            response = self.client.get("/api/audit/recent")

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False
