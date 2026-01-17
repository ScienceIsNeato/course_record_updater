"""
Unit tests for CLO workflow admin notification fallback behavior.

Tests that when a program has no program_admins, the system falls back
to institution_admins for submission notifications.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.services.clo_workflow_service import CLOWorkflowService


class TestAdminNotificationFallback:
    """Test admin notification fallback to institution admins."""

    @patch("src.services.clo_workflow_service.db")
    @patch("src.services.clo_workflow_service.EmailService")
    def test_falls_back_to_institution_admin_when_no_program_admins(
        self, mock_email_service, mock_db
    ):
        """
        When a program has no program_admins, should fall back to institution_admins.
        """
        course_id = "test-course-123"
        user_id = "test-instructor-456"
        program_id = "test-program-789"
        institution_id = "test-institution-000"

        # Mock course with program
        mock_db.get_course_by_id.return_value = {
            "id": course_id,
            "course_number": "BIO-101",
            "program_ids": [program_id],
            "institution_id": institution_id,
        }

        # Mock instructor
        mock_db.get_user_by_id.return_value = {
            "user_id": user_id,
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@test.com",
        }

        # Mock: NO program admins
        mock_db.get_program_admins.return_value = []

        # Mock: Institution HAS institution admins
        mock_db.get_all_users.return_value = [
            {
                "user_id": "inst-admin-1",
                "role": "institution_admin",
                "email": "admin1@test.com",
                "first_name": "Admin",
                "last_name": "One",
            },
            {
                "user_id": "inst-admin-2",
                "role": "institution_admin",
                "email": "admin2@test.com",
                "first_name": "Admin",
                "last_name": "Two",
            },
            {
                "user_id": "some-instructor",
                "role": "instructor",
                "email": "instructor@test.com",
            },
        ]

        # Mock email service
        mock_email_service.send_admin_submission_alert.return_value = True

        # Call the method
        success, error = CLOWorkflowService._notify_program_admins_for_course(
            course_id, user_id, clo_count=3
        )

        # Should succeed (found institution admins)
        assert success is True, f"Expected success, got error: {error}"
        assert error is None

        # Should have called get_all_users to find institution admins
        mock_db.get_all_users.assert_called_once_with(institution_id)

        # Should have sent 2 emails (to 2 institution admins, not the instructor)
        assert mock_email_service.send_admin_submission_alert.call_count == 2

        # Verify emails sent to institution admins
        calls = mock_email_service.send_admin_submission_alert.call_args_list
        emails_sent_to = [call.kwargs["to_email"] for call in calls]
        assert "admin1@test.com" in emails_sent_to
        assert "admin2@test.com" in emails_sent_to
        assert "instructor@test.com" not in emails_sent_to

    @patch("src.services.clo_workflow_service.db")
    @patch("src.services.clo_workflow_service.EmailService")
    def test_fails_when_no_program_admins_and_no_institution_admins(
        self, mock_email_service, mock_db
    ):
        """
        When a program has no admins AND institution has no admins, should return False.
        """
        course_id = "test-course-123"
        user_id = "test-instructor-456"
        program_id = "test-program-789"
        institution_id = "test-institution-000"

        # Mock course
        mock_db.get_course_by_id.return_value = {
            "id": course_id,
            "course_number": "BIO-101",
            "program_ids": [program_id],
            "institution_id": institution_id,
        }

        # Mock instructor
        mock_db.get_user_by_id.return_value = {
            "user_id": user_id,
            "first_name": "Jane",
            "last_name": "Doe",
        }

        # NO program admins
        mock_db.get_program_admins.return_value = []

        # NO institution admins either
        mock_db.get_all_users.return_value = []

        # Call should fail
        success, error = CLOWorkflowService._notify_program_admins_for_course(
            course_id, user_id, clo_count=3
        )

        assert success is False
        assert "No program or institution admins" in error

        # Should NOT have sent any emails
        mock_email_service.send_admin_submission_alert.assert_not_called()
