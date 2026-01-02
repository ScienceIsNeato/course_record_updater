"""
Unit tests for Bulk Email API routes.

Tests the bulk email endpoints for sending reminders and tracking progress.

NOTE: bulk_email.py uses @lazy_permission_required decorator which resolves
permission checks at RUNTIME, not import time. This allows proper mocking
in tests without import pollution issues.
"""

import json
import unittest
from unittest.mock import Mock, patch

import pytest
from flask import Flask

from src.api.routes.bulk_email import bulk_email_bp


# Module-level fixture to bypass permission checks for ALL tests in this file
# This runs BEFORE test class instantiation, ensuring patches are active
# when decorators are evaluated (critical for pytest-xdist parallel execution)
@pytest.fixture(scope="module", autouse=True)
def bypass_permissions():
    """Bypass permission checks for all bulk_email route tests"""
    with patch(
        "auth_service.permission_required",
        lambda perm, context_keys=None: lambda f: f,
    ):
        yield


class TestBulkEmailAPI(unittest.TestCase):
    """Test bulk email API endpoints"""

    def setUp(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(bulk_email_bp)
        self.client = self.app.test_client()

        # Mock current user
        self.mock_user = {
            "id": "test-user-123",
            "user_id": "test-user-123",  # Required for logging
            "email": "admin@example.com",
            "role": "program_admin",
        }

    @patch("api.routes.bulk_email.get_current_user")
    @patch("api.routes.bulk_email.BulkEmailService")
    @patch("api.routes.bulk_email.get_db")
    def test_send_instructor_reminders_success(
        self, mock_get_db, mock_service, mock_get_user
    ):
        """Test sending instructor reminders successfully"""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_service.send_instructor_reminders.return_value = "job-123"
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        # Make request
        response = self.client.post(
            "/api/bulk-email/send-instructor-reminders",
            data=json.dumps(
                {
                    "instructor_ids": ["inst-1", "inst-2", "inst-3"],
                    "personal_message": "Please submit by Friday",
                    "term": "Fall 2024",
                    "deadline": "2024-12-31",
                }
            ),
            content_type="application/json",
        )

        # Assert
        assert response.status_code == 202
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["job_id"] == "job-123"
        assert data["recipient_count"] == 3

        # Verify service was called correctly
        mock_service.send_instructor_reminders.assert_called_once()
        call_kwargs = mock_service.send_instructor_reminders.call_args[1]
        assert call_kwargs["instructor_ids"] == ["inst-1", "inst-2", "inst-3"]
        assert call_kwargs["created_by_user_id"] == "test-user-123"
        assert call_kwargs["personal_message"] == "Please submit by Friday"
        assert call_kwargs["term"] == "Fall 2024"
        assert call_kwargs["deadline"] == "2024-12-31"

    @patch("api.routes.bulk_email.get_current_user")
    def test_send_instructor_reminders_missing_body(self, mock_get_user):
        """Test sending reminders with missing request body"""
        mock_get_user.return_value = self.mock_user

        response = self.client.post(
            "/api/bulk-email/send-instructor-reminders",
            data="",
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "required" in data["error"].lower()

    @patch("api.routes.bulk_email.get_current_user")
    def test_send_instructor_reminders_empty_list(self, mock_get_user):
        """Test sending reminders with empty instructor list"""
        mock_get_user.return_value = self.mock_user

        response = self.client.post(
            "/api/bulk-email/send-instructor-reminders",
            data=json.dumps({"instructor_ids": []}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "non-empty" in data["error"].lower()

    @patch("api.routes.bulk_email.get_current_user")
    def test_send_instructor_reminders_invalid_type(self, mock_get_user):
        """Test sending reminders with invalid instructor_ids type"""
        mock_get_user.return_value = self.mock_user

        response = self.client.post(
            "/api/bulk-email/send-instructor-reminders",
            data=json.dumps({"instructor_ids": "not-a-list"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False

    @patch("api.routes.bulk_email.get_current_user")
    def test_send_instructor_reminders_no_auth(self, mock_get_user):
        """Test sending reminders without authentication"""
        mock_get_user.return_value = None

        response = self.client.post(
            "/api/bulk-email/send-instructor-reminders",
            data=json.dumps({"instructor_ids": ["inst-1"]}),
            content_type="application/json",
        )

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["success"] is False
        assert "authentication" in data["error"].lower()

    @patch("api.routes.bulk_email.get_current_user")
    @patch("api.routes.bulk_email.BulkEmailService")
    @patch("api.routes.bulk_email.get_db")
    def test_get_job_status_success(self, mock_get_db, mock_service, mock_get_user):
        """Test getting job status successfully"""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        mock_job_status = {
            "id": "job-123",
            "job_type": "instructor_reminder",
            "status": "running",
            "created_by_user_id": "test-user-123",  # Match the mock user
            "recipient_count": 5,
            "emails_sent": 3,
            "emails_failed": 0,
            "emails_pending": 2,
            "progress_percentage": 60,
        }
        mock_service.get_job_status.return_value = mock_job_status

        # Make request
        response = self.client.get("/api/bulk-email/job-status/job-123")

        # Assert
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["job"]["id"] == "job-123"
        assert data["job"]["status"] == "running"
        assert data["job"]["progress_percentage"] == 60

    @patch("api.routes.bulk_email.get_current_user")
    @patch("api.routes.bulk_email.BulkEmailService")
    @patch("api.routes.bulk_email.get_db")
    def test_get_job_status_not_found(self, mock_get_db, mock_service, mock_get_user):
        """Test getting status for non-existent job"""
        mock_get_user.return_value = self.mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_service.get_job_status.return_value = None

        response = self.client.get("/api/bulk-email/job-status/nonexistent")

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["success"] is False
        assert "not found" in data["error"].lower()

    @patch("api.routes.bulk_email.get_current_user")
    def test_get_job_status_no_auth(self, mock_get_user):
        """Test getting job status without authentication"""
        mock_get_user.return_value = None

        response = self.client.get("/api/bulk-email/job-status/job-123")

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["success"] is False

    @patch("api.routes.bulk_email.get_current_user")
    @patch("api.routes.bulk_email.BulkEmailService")
    @patch("api.routes.bulk_email.get_db")
    def test_get_recent_jobs_success(self, mock_get_db, mock_service, mock_get_user):
        """Test getting recent jobs successfully"""
        mock_get_user.return_value = self.mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        mock_jobs = [
            {
                "id": "job-1",
                "job_type": "instructor_reminder",
                "status": "completed",
                "recipient_count": 5,
            },
            {
                "id": "job-2",
                "job_type": "instructor_reminder",
                "status": "running",
                "recipient_count": 3,
            },
        ]
        mock_service.get_recent_jobs.return_value = mock_jobs

        response = self.client.get("/api/bulk-email/recent-jobs")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["jobs"]) == 2
        assert data["total"] == 2

    @patch("api.routes.bulk_email.get_current_user")
    @patch("api.routes.bulk_email.BulkEmailService")
    @patch("api.routes.bulk_email.get_db")
    def test_get_recent_jobs_with_limit(self, mock_get_db, mock_service, mock_get_user):
        """Test getting recent jobs with custom limit"""
        mock_get_user.return_value = self.mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_service.get_recent_jobs.return_value = []

        response = self.client.get("/api/bulk-email/recent-jobs?limit=10")

        assert response.status_code == 200
        mock_service.get_recent_jobs.assert_called_once()
        call_kwargs = mock_service.get_recent_jobs.call_args[1]
        assert call_kwargs["limit"] == 10

    @patch("api.routes.bulk_email.get_current_user")
    @patch("api.routes.bulk_email.BulkEmailService")
    @patch("api.routes.bulk_email.get_db")
    def test_get_recent_jobs_limit_capped(
        self, mock_get_db, mock_service, mock_get_user
    ):
        """Test that limit is capped at maximum"""
        mock_get_user.return_value = self.mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        mock_service.get_recent_jobs.return_value = []

        response = self.client.get("/api/bulk-email/recent-jobs?limit=500")

        assert response.status_code == 200
        call_kwargs = mock_service.get_recent_jobs.call_args[1]
        assert call_kwargs["limit"] == 100  # Capped at max

    @patch("api.routes.bulk_email.get_current_user")
    @patch("api.routes.bulk_email.BulkEmailService")
    @patch("api.routes.bulk_email.get_db")
    def test_send_instructor_reminders_value_error(
        self, mock_get_db, mock_service, mock_get_user
    ):
        """Test send instructor reminders ValueError handling"""
        mock_get_user.return_value = self.mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        # Mock service to raise ValueError
        mock_service.send_instructor_reminders.side_effect = ValueError(
            "Invalid instructor ID format"
        )

        response = self.client.post(
            "/api/bulk-email/send-instructor-reminders",
            data=json.dumps({"instructor_ids": ["invalid-id"]}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Invalid instructor ID format" in data["error"]
        mock_db.close.assert_called_once()

    @patch("api.routes.bulk_email.get_current_user")
    @patch("api.routes.bulk_email.BulkEmailService")
    @patch("api.routes.bulk_email.get_db")
    def test_send_instructor_reminders_generic_exception(
        self, mock_get_db, mock_service, mock_get_user
    ):
        """Test send instructor reminders generic Exception handling"""
        mock_get_user.return_value = self.mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        # Mock service to raise generic exception
        mock_service.send_instructor_reminders.side_effect = RuntimeError(
            "Database connection lost"
        )

        response = self.client.post(
            "/api/bulk-email/send-instructor-reminders",
            data=json.dumps({"instructor_ids": ["test-123"]}),
            content_type="application/json",
        )

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["success"] is False
        mock_db.close.assert_called_once()

    @patch("api.routes.bulk_email.get_current_user")
    @patch("api.routes.bulk_email.BulkEmailService")
    @patch("api.routes.bulk_email.get_db")
    def test_get_job_status_generic_exception(
        self, mock_get_db, mock_service, mock_get_user
    ):
        """Test get job status generic Exception handling"""
        mock_get_user.return_value = self.mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        # Mock service to raise exception
        mock_service.get_job_status.side_effect = RuntimeError("Database error")

        response = self.client.get("/api/bulk-email/job-status/test-job-123")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["success"] is False
        mock_db.close.assert_called_once()

    @patch("api.routes.bulk_email.get_current_user")
    @patch("api.routes.bulk_email.BulkEmailService")
    @patch("api.routes.bulk_email.get_db")
    def test_get_recent_jobs_generic_exception(
        self, mock_get_db, mock_service, mock_get_user
    ):
        """Test get recent jobs generic Exception handling"""
        mock_get_user.return_value = self.mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        # Mock service to raise exception
        mock_service.get_recent_jobs.side_effect = RuntimeError("Database error")

        response = self.client.get("/api/bulk-email/recent-jobs")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["success"] is False
        mock_db.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
