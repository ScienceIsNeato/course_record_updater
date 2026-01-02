"""Tests for audit log API endpoints.

TDD tests for:
- Recent audit logs (GET /api/audit/recent)
- Audit log search (GET /api/audit/search)
"""

import os
from unittest.mock import patch

import pytest

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

        with patch("src.api_routes.get_recent_audit_logs") as mock_get_logs:
            mock_get_logs.return_value = [
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

            # Verify call with correct institution_id (positional args)
            mock_get_logs.assert_called_once_with("inst-123", 50)

    def test_search_audit_logs_success(self):
        """Test successful search of audit logs."""
        self._login_institution_admin()

        with patch("src.api_routes.get_audit_logs_filtered") as mock_search:
            mock_search.return_value = [
                {
                    "id": "log-2",
                    "action": "update",
                    "entity_type": "course",
                    "timestamp": "2023-01-02T12:00:00Z",
                }
            ]

            response = self.client.get(
                "/api/audit/search?start_date=2023-01-01&end_date=2023-01-31&entity_type=course"
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert len(data["logs"]) == 1
            assert data["logs"][0]["id"] == "log-2"

            # Verify filtered search call
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert call_args[1]["institution_id"] == "inst-123"
            assert call_args[1]["entity_type"] == "course"
            assert call_args[1]["start_date"] == "2023-01-01"
            assert call_args[1]["end_date"] == "2023-01-31"

    def test_search_audit_logs_database_error(self):
        """Test audit log search handles database errors."""
        self._login_institution_admin()

        with patch("src.api_routes.get_audit_logs_filtered") as mock_search:
            mock_search.side_effect = Exception("Database error")

            response = self.client.get("/api/audit/search")

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False
