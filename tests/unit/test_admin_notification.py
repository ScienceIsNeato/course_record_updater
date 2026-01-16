"""
Unit tests for admin notification feature.

Tests the email alert when instructors submit assessments.
"""

from unittest.mock import MagicMock, patch

from src.services.clo_workflow_service import CLOWorkflowService
from src.utils.constants import CLOStatus


class TestAdminNotificationOnSubmission:
    """Test admin email notifications when submitting CLOs"""

    @patch("src.services.clo_workflow_service.EmailService.send_admin_submission_alert")
    @patch("src.services.clo_workflow_service.db")
    def test_submit_with_admin_notification_sends_emails(
        self, mock_db, mock_send_alert
    ):
        """Test submission with notify_admins=True sends emails to program admins."""
        # Setup
        section_outcome_id = "outcome-123"
        user_id = "instructor-456"

        mock_db.get_section_outcome.return_value = {
            "id": section_outcome_id,
            "status": CLOStatus.IN_PROGRESS,
            "course_id": "course-789",
            "section_number": "001",
            "outcome_number": 1,
        }
        mock_db.update_section_outcome.return_value = True
        mock_db.get_course_by_id.return_value = {
            "id": "course-789",
            "course_number": "CS101",
            "program_id": "program-111",
        }
        mock_db.get_user_by_id.return_value = {
            "first_name": "John",
            "last_name": "Doe",
        }
        mock_db.get_program_admins.return_value = [
            {"email": "admin1@test.edu", "first_name": "Admin"}
        ]
        mock_send_alert.return_value = True

        # Execute
        result = CLOWorkflowService.submit_clo_for_approval(
            section_outcome_id, user_id, notify_admins=True
        )

        # Verify
        assert result is True
        mock_send_alert.assert_called_once()
        call_kwargs = mock_send_alert.call_args.kwargs
        assert call_kwargs["to_email"] == "admin1@test.edu"
        assert "John Doe" in call_kwargs["instructor_name"]
        assert call_kwargs["course_code"] == "CS101-001"

    @patch("src.services.clo_workflow_service.EmailService.send_admin_submission_alert")
    @patch("src.services.clo_workflow_service.db")
    def test_submit_without_notification_skips_emails(self, mock_db, mock_send_alert):
        """Test submission with notify_admins=False doesn't send emails."""
        # Setup
        mock_db.get_section_outcome.return_value = {
            "id": "outcome-123",
            "status": CLOStatus.IN_PROGRESS,
        }
        mock_db.update_section_outcome.return_value = True

        # Execute
        result = CLOWorkflowService.submit_clo_for_approval(
            "outcome-123", "user-456", notify_admins=False
        )

        # Verify
        assert result is True
        mock_send_alert.assert_not_called()

    @patch("src.services.clo_workflow_service.EmailService.send_admin_submission_alert")
    @patch("src.services.clo_workflow_service.db")
    def test_submit_default_notification_skips_emails(self, mock_db, mock_send_alert):
        """Test submission with default (no parameter) doesn't send emails."""
        # Setup
        mock_db.get_section_outcome.return_value = {
            "id": "outcome-123",
            "status": CLOStatus.IN_PROGRESS,
        }
        mock_db.update_section_outcome.return_value = True

        # Execute (no notify_admins parameter - default behavior)
        result = CLOWorkflowService.submit_clo_for_approval("outcome-123", "user-456")

        # Verify
        assert result is True
        mock_send_alert.assert_not_called()
