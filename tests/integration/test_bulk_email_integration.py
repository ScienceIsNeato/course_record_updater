"""
Integration tests for bulk email system.

Tests the complete flow from API request through job creation,
email sending, and status tracking.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.app import app
from tests.test_utils import CommonAuthMixin


@pytest.mark.integration
class TestBulkEmailIntegration(CommonAuthMixin):
    """Integration tests for bulk email system with real database"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self._login_site_admin()

    @patch("src.database.database_service.get_all_instructors")
    def test_api_endpoint_creates_job(self, mock_get_instructors):
        """Test that POST /api/bulk-email/send-instructor-reminders creates job"""
        # Mock instructors
        mock_get_instructors.return_value = [
            {
                "user_id": "inst-1",
                "email": "inst1@test.com",
                "first_name": "John",
                "last_name": "Doe",
            },
            {
                "user_id": "inst-2",
                "email": "inst2@test.com",
                "first_name": "Jane",
                "last_name": "Smith",
            },
        ]

        instructor_ids = ["inst-1", "inst-2"]

        # Mock email sending
        with patch(
            "src.services.bulk_email_service.EmailService"
        ) as mock_email_service:
            mock_instance = MagicMock()
            mock_email_service.return_value = mock_instance
            mock_instance._send_email.return_value = True

            response = self.client.post(
                "/api/bulk-email/send-instructor-reminders",
                data=json.dumps(
                    {
                        "instructor_ids": instructor_ids,
                        "personal_message": "Test",
                    }
                ),
                content_type="application/json",
            )

            assert response.status_code == 202  # Async job returns 202 Accepted
            data = response.get_json()
            assert data["success"] is True
            assert "job_id" in data

    def test_empty_recipient_list(self):
        """Test that empty instructor list returns error"""
        response = self.client.post(
            "/api/bulk-email/send-instructor-reminders",
            data=json.dumps({"instructor_ids": []}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "instructor_ids" in data["error"]

    def test_missing_body(self):
        """Test that missing request body returns error"""
        response = self.client.post(
            "/api/bulk-email/send-instructor-reminders",
            data="",
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    @patch("src.database.database_service.get_all_instructors")
    def test_job_status_endpoint(self, mock_get_instructors):
        """Test GET /api/bulk-email/job-status/{job_id}"""
        mock_get_instructors.return_value = [
            {
                "user_id": "inst-1",
                "email": "inst1@test.com",
                "first_name": "John",
                "last_name": "Doe",
            },
        ]

        with patch(
            "src.services.bulk_email_service.EmailService"
        ) as mock_email_service:
            mock_instance = MagicMock()
            mock_email_service.return_value = mock_instance
            mock_instance._send_email.return_value = True

            # Create job
            response = self.client.post(
                "/api/bulk-email/send-instructor-reminders",
                data=json.dumps({"instructor_ids": ["inst-1"]}),
                content_type="application/json",
            )

            assert response.status_code == 202  # Async job returns 202 Accepted
            job_id = response.get_json()["job_id"]

            # Get job status
            response = self.client.get(f"/api/bulk-email/job-status/{job_id}")

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert "job" in data

    def test_job_status_not_found(self):
        """Test GET /api/bulk-email/job-status with invalid ID"""
        response = self.client.get("/api/bulk-email/job-status/invalid-job-id")

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "not found" in data["error"].lower()

    @patch("src.database.database_service.get_all_instructors")
    def test_recent_jobs_endpoint(self, mock_get_instructors):
        """Test GET /api/bulk-email/recent-jobs"""
        mock_get_instructors.return_value = [
            {
                "user_id": "inst-1",
                "email": "inst1@test.com",
                "first_name": "John",
                "last_name": "Doe",
            },
        ]

        with patch(
            "src.services.bulk_email_service.EmailService"
        ) as mock_email_service:
            mock_instance = MagicMock()
            mock_email_service.return_value = mock_instance
            mock_instance._send_email.return_value = True

            # Create a job
            self.client.post(
                "/api/bulk-email/send-instructor-reminders",
                data=json.dumps({"instructor_ids": ["inst-1"]}),
                content_type="application/json",
            )

            # Get recent jobs
            response = self.client.get("/api/bulk-email/recent-jobs?limit=5")

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert "jobs" in data
