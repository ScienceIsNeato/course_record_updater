"""
Unit tests for clo_workflow_service.py

Tests the CLO submission and approval workflow service methods.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from clo_workflow_service import CLOWorkflowService
from constants import CLOApprovalStatus, CLOStatus


class TestSubmitCLOForApproval:
    """Test CLOWorkflowService.submit_clo_for_approval method"""

    @patch("clo_workflow_service.db")
    def test_submit_clo_success(self, mock_db):
        """Test successful CLO submission"""
        # Setup
        outcome_id = "outcome-123"
        user_id = "user-456"
        mock_db.get_course_outcome.return_value = {
            "id": outcome_id,
            "status": CLOStatus.IN_PROGRESS,
        }
        mock_db.update_course_outcome.return_value = True

        # Execute
        result = CLOWorkflowService.submit_clo_for_approval(outcome_id, user_id)

        # Verify
        assert result is True
        mock_db.get_course_outcome.assert_called_once_with(outcome_id)
        mock_db.update_course_outcome.assert_called_once()

        # Check update data
        update_call = mock_db.update_course_outcome.call_args[0]
        assert update_call[0] == outcome_id
        update_data = update_call[1]
        assert update_data["status"] == CLOStatus.AWAITING_APPROVAL
        assert update_data["submitted_by_user_id"] == user_id
        assert update_data["approval_status"] == CLOApprovalStatus.PENDING
        assert "submitted_at" in update_data

    @patch("clo_workflow_service.db")
    def test_submit_clo_not_found(self, mock_db):
        """Test submission when CLO doesn't exist"""
        mock_db.get_course_outcome.return_value = None

        result = CLOWorkflowService.submit_clo_for_approval("nonexistent", "user-123")

        assert result is False
        mock_db.update_course_outcome.assert_not_called()

    @patch("clo_workflow_service.db")
    def test_submit_clo_update_fails(self, mock_db):
        """Test submission when database update returns False"""
        mock_db.get_course_outcome.return_value = {
            "id": "outcome-123",
            "status": CLOStatus.IN_PROGRESS,
        }
        mock_db.update_course_outcome.return_value = False

        result = CLOWorkflowService.submit_clo_for_approval("outcome-123", "user-456")

        assert result is False

    @patch("clo_workflow_service.db")
    def test_submit_clo_database_error(self, mock_db):
        """Test submission with database error"""
        mock_db.get_course_outcome.return_value = {"id": "outcome-123"}
        mock_db.update_course_outcome.side_effect = Exception("Database error")

        result = CLOWorkflowService.submit_clo_for_approval("outcome-123", "user-456")

        assert result is False


class TestApproveCLO:
    """Test CLOWorkflowService.approve_clo method"""

    @patch("clo_workflow_service.db")
    def test_approve_clo_from_awaiting_approval(self, mock_db):
        """Test approving CLO from awaiting_approval status"""
        outcome_id = "outcome-123"
        reviewer_id = "admin-456"
        mock_db.get_course_outcome.return_value = {
            "id": outcome_id,
            "status": CLOStatus.AWAITING_APPROVAL,
        }
        mock_db.update_course_outcome.return_value = True

        result = CLOWorkflowService.approve_clo(outcome_id, reviewer_id)

        assert result is True
        update_call = mock_db.update_course_outcome.call_args[0]
        update_data = update_call[1]
        assert update_data["status"] == CLOStatus.APPROVED
        assert update_data["approval_status"] == CLOApprovalStatus.APPROVED
        assert update_data["reviewed_by_user_id"] == reviewer_id
        assert "reviewed_at" in update_data
        # Note: feedback_comments preserved for audit trail (not cleared)

    @patch("clo_workflow_service.db")
    def test_approve_clo_from_approval_pending(self, mock_db):
        """Test approving CLO from approval_pending status (after rework)"""
        outcome_id = "outcome-123"
        reviewer_id = "admin-456"
        mock_db.get_course_outcome.return_value = {
            "id": outcome_id,
            "status": CLOStatus.APPROVAL_PENDING,
            "feedback_comments": "Previous feedback",
        }
        mock_db.update_course_outcome.return_value = True

        result = CLOWorkflowService.approve_clo(outcome_id, reviewer_id)

        assert result is True
        update_call = mock_db.update_course_outcome.call_args[0]
        update_data = update_call[1]
        assert update_data["status"] == CLOStatus.APPROVED
        # Note: feedback_comments preserved for audit trail (not cleared)

    @patch("clo_workflow_service.db")
    def test_approve_clo_wrong_status(self, mock_db):
        """Test approval fails for CLO not ready for approval"""
        mock_db.get_course_outcome.return_value = {
            "id": "outcome-123",
            "status": CLOStatus.IN_PROGRESS,
        }

        result = CLOWorkflowService.approve_clo("outcome-123", "admin-456")

        assert result is False
        mock_db.update_course_outcome.assert_not_called()

    @patch("clo_workflow_service.db")
    def test_approve_clo_not_found(self, mock_db):
        """Test approval when CLO doesn't exist"""
        mock_db.get_course_outcome.return_value = None

        result = CLOWorkflowService.approve_clo("nonexistent", "admin-123")

        assert result is False

    @patch("clo_workflow_service.db")
    def test_approve_clo_update_fails(self, mock_db):
        """Test approval when database update returns False"""
        mock_db.get_course_outcome.return_value = {
            "id": "outcome-123",
            "status": CLOStatus.AWAITING_APPROVAL,
        }
        mock_db.update_course_outcome.return_value = False

        result = CLOWorkflowService.approve_clo("outcome-123", "admin-456")

        assert result is False

    @patch("clo_workflow_service.db")
    def test_approve_clo_database_error(self, mock_db):
        """Test approval with database exception"""
        mock_db.get_course_outcome.return_value = {
            "id": "outcome-123",
            "status": CLOStatus.AWAITING_APPROVAL,
        }
        mock_db.update_course_outcome.side_effect = Exception("Database error")

        result = CLOWorkflowService.approve_clo("outcome-123", "admin-456")

        assert result is False


class TestRequestRework:
    """Test CLOWorkflowService.request_rework method"""

    @patch("clo_workflow_service.CLOWorkflowService._send_rework_notification")
    @patch("clo_workflow_service.db")
    def test_request_rework_without_email(self, mock_db, mock_send_email):
        """Test requesting rework without sending email"""
        outcome_id = "outcome-123"
        reviewer_id = "admin-456"
        comments = "Please revise the assessment method"

        mock_db.get_course_outcome.return_value = {
            "id": outcome_id,
            "status": CLOStatus.AWAITING_APPROVAL,
        }
        mock_db.update_course_outcome.return_value = True

        result = CLOWorkflowService.request_rework(
            outcome_id, reviewer_id, comments, send_email=False
        )

        assert result is True
        update_call = mock_db.update_course_outcome.call_args[0]
        update_data = update_call[1]
        assert update_data["status"] == CLOStatus.APPROVAL_PENDING
        assert update_data["approval_status"] == CLOApprovalStatus.NEEDS_REWORK
        assert update_data["feedback_comments"] == comments
        assert update_data["reviewed_by_user_id"] == reviewer_id
        assert "reviewed_at" in update_data
        assert "feedback_provided_at" in update_data
        mock_send_email.assert_not_called()

    @patch("clo_workflow_service.CLOWorkflowService._send_rework_notification")
    @patch("clo_workflow_service.db")
    def test_request_rework_with_email(self, mock_db, mock_send_email):
        """Test requesting rework with email notification"""
        outcome_id = "outcome-123"
        reviewer_id = "admin-456"
        comments = "Please add more detail"

        mock_db.get_course_outcome.return_value = {
            "id": outcome_id,
            "status": CLOStatus.AWAITING_APPROVAL,
        }
        mock_db.update_course_outcome.return_value = True
        mock_send_email.return_value = True

        result = CLOWorkflowService.request_rework(
            outcome_id, reviewer_id, comments, send_email=True
        )

        assert result is True
        mock_send_email.assert_called_once_with(outcome_id, comments)

    @patch("clo_workflow_service.db")
    def test_request_rework_wrong_status(self, mock_db):
        """Test rework request fails for wrong status"""
        mock_db.get_course_outcome.return_value = {
            "id": "outcome-123",
            "status": CLOStatus.APPROVED,
        }

        result = CLOWorkflowService.request_rework(
            "outcome-123", "admin-456", "Comments"
        )

        assert result is False
        mock_db.update_course_outcome.assert_not_called()

    @patch("clo_workflow_service.db")
    def test_request_rework_not_found(self, mock_db):
        """Test rework request when CLO doesn't exist"""
        mock_db.get_course_outcome.return_value = None

        result = CLOWorkflowService.request_rework(
            "nonexistent", "admin-123", "Comments"
        )

        assert result is False

    @patch("clo_workflow_service.db")
    def test_request_rework_update_fails(self, mock_db):
        """Test rework request when database update returns False"""
        mock_db.get_course_outcome.return_value = {
            "id": "outcome-123",
            "status": CLOStatus.AWAITING_APPROVAL,
        }
        mock_db.update_course_outcome.return_value = False

        result = CLOWorkflowService.request_rework(
            "outcome-123", "admin-456", "Comments"
        )

        assert result is False

    @patch("clo_workflow_service.db")
    def test_request_rework_database_error(self, mock_db):
        """Test rework request with database exception"""
        mock_db.get_course_outcome.return_value = {
            "id": "outcome-123",
            "status": CLOStatus.AWAITING_APPROVAL,
        }
        mock_db.update_course_outcome.side_effect = Exception("Database error")

        result = CLOWorkflowService.request_rework(
            "outcome-123", "admin-456", "Comments"
        )

        assert result is False


class TestMarkAsNCI:
    """Test CLOWorkflowService.mark_as_nci method (CEI demo follow-up)"""

    @patch("clo_workflow_service.db")
    def test_mark_as_nci_success_with_reason(self, mock_db):
        """Test marking CLO as Never Coming In with reason"""
        outcome_id = "outcome-123"
        reviewer_id = "admin-456"
        reason = "Instructor left institution"

        mock_db.get_course_outcome.return_value = {
            "id": outcome_id,
            "status": CLOStatus.AWAITING_APPROVAL,
        }
        mock_db.update_course_outcome.return_value = True

        result = CLOWorkflowService.mark_as_nci(outcome_id, reviewer_id, reason)

        assert result is True
        update_call = mock_db.update_course_outcome.call_args[0]
        update_data = update_call[1]
        assert update_data["status"] == "never_coming_in"
        assert update_data["approval_status"] == "never_coming_in"
        assert update_data["feedback_comments"] == reason
        assert update_data["reviewed_by_user_id"] == reviewer_id

    @patch("clo_workflow_service.db")
    def test_mark_as_nci_success_without_reason(self, mock_db):
        """Test marking CLO as NCI without specific reason"""
        outcome_id = "outcome-123"
        reviewer_id = "admin-456"

        mock_db.get_course_outcome.return_value = {
            "id": outcome_id,
            "status": CLOStatus.IN_PROGRESS,
        }
        mock_db.update_course_outcome.return_value = True

        result = CLOWorkflowService.mark_as_nci(outcome_id, reviewer_id, None)

        assert result is True
        update_call = mock_db.update_course_outcome.call_args[0]
        update_data = update_call[1]
        assert update_data["feedback_comments"] == "Marked as Never Coming In (NCI)"

    @patch("clo_workflow_service.db")
    def test_mark_as_nci_not_found(self, mock_db):
        """Test NCI marking when CLO doesn't exist"""
        mock_db.get_course_outcome.return_value = None

        result = CLOWorkflowService.mark_as_nci("fake-id", "admin-456", "Reason")

        assert result is False

    @patch("clo_workflow_service.db")
    def test_mark_as_nci_update_fails(self, mock_db):
        """Test NCI marking when database update returns False"""
        mock_db.get_course_outcome.return_value = {
            "id": "outcome-123",
            "status": CLOStatus.ASSIGNED,
        }
        mock_db.update_course_outcome.return_value = False

        result = CLOWorkflowService.mark_as_nci("outcome-123", "admin-456", "Reason")

        assert result is False

    @patch("clo_workflow_service.db")
    def test_mark_as_nci_database_error(self, mock_db):
        """Test NCI marking with database exception"""
        mock_db.get_course_outcome.return_value = {
            "id": "outcome-123",
            "status": CLOStatus.AWAITING_APPROVAL,
        }
        mock_db.update_course_outcome.side_effect = Exception("Database error")

        result = CLOWorkflowService.mark_as_nci("outcome-123", "admin-456", "Reason")

        assert result is False


class TestAutoMarkInProgress:
    """Test CLOWorkflowService.auto_mark_in_progress method"""

    @patch("clo_workflow_service.db")
    def test_auto_mark_from_assigned(self, mock_db):
        """Test auto-marking from assigned status"""
        outcome_id = "outcome-123"
        user_id = "user-456"
        mock_db.get_course_outcome.return_value = {
            "id": outcome_id,
            "status": CLOStatus.ASSIGNED,
        }
        mock_db.update_course_outcome.return_value = True

        result = CLOWorkflowService.auto_mark_in_progress(outcome_id, user_id)

        assert result is True
        update_call = mock_db.update_course_outcome.call_args[0]
        update_data = update_call[1]
        assert update_data["status"] == CLOStatus.IN_PROGRESS

    @patch("clo_workflow_service.db")
    def test_auto_mark_from_approval_pending(self, mock_db):
        """Test auto-marking from approval_pending (after rework feedback)"""
        outcome_id = "outcome-123"
        user_id = "user-456"
        mock_db.get_course_outcome.return_value = {
            "id": outcome_id,
            "status": CLOStatus.APPROVAL_PENDING,
        }
        mock_db.update_course_outcome.return_value = True

        result = CLOWorkflowService.auto_mark_in_progress(outcome_id, user_id)

        assert result is True

    @patch("clo_workflow_service.db")
    def test_auto_mark_already_in_progress(self, mock_db):
        """Test auto-marking when already in progress (no-op)"""
        mock_db.get_course_outcome.return_value = {
            "id": "outcome-123",
            "status": CLOStatus.IN_PROGRESS,
        }

        result = CLOWorkflowService.auto_mark_in_progress("outcome-123", "user-456")

        assert result is True
        mock_db.update_course_outcome.assert_not_called()

    @patch("clo_workflow_service.db")
    def test_auto_mark_already_submitted(self, mock_db):
        """Test auto-marking when already submitted (no-op)"""
        mock_db.get_course_outcome.return_value = {
            "id": "outcome-123",
            "status": CLOStatus.AWAITING_APPROVAL,
        }

        result = CLOWorkflowService.auto_mark_in_progress("outcome-123", "user-456")

        assert result is True
        mock_db.update_course_outcome.assert_not_called()

    @patch("clo_workflow_service.db")
    def test_auto_mark_database_error(self, mock_db):
        """Test auto-marking with database exception"""
        mock_db.get_course_outcome.side_effect = Exception("Database error")

        result = CLOWorkflowService.auto_mark_in_progress("outcome-123", "user-456")

        assert result is False


class TestGetCLOsByStatus:
    """Test CLOWorkflowService.get_clos_by_status method"""

    @patch("clo_workflow_service.CLOWorkflowService.get_outcome_with_details")
    @patch("clo_workflow_service.db")
    def test_get_clos_by_status_success(self, mock_db, mock_get_details):
        """Test getting CLOs by status"""
        institution_id = "inst-123"
        status = CLOStatus.AWAITING_APPROVAL

        mock_db.get_outcomes_by_status.return_value = [
            {"outcome_id": "outcome-1"},
            {"outcome_id": "outcome-2"},
        ]
        mock_get_details.side_effect = [
            {"id": "outcome-1", "course_number": "CS-101"},
            {"id": "outcome-2", "course_number": "CS-102"},
        ]

        result = CLOWorkflowService.get_clos_by_status(
            status=status,
            institution_id=institution_id,
        )

        assert len(result) == 2
        assert result[0]["course_number"] == "CS-101"
        assert result[1]["course_number"] == "CS-102"
        mock_db.get_outcomes_by_status.assert_called_once_with(
            institution_id=institution_id,
            status=status,
            program_id=None,
        )

    @patch("clo_workflow_service.CLOWorkflowService.get_outcome_with_details")
    @patch("clo_workflow_service.db")
    def test_get_clos_by_status_with_program_filter(self, mock_db, mock_get_details):
        """Test getting CLOs by status with program filter"""
        institution_id = "inst-123"
        program_id = "prog-456"
        status = CLOStatus.AWAITING_APPROVAL

        mock_db.get_outcomes_by_status.return_value = [{"id": "outcome-1"}]
        mock_get_details.return_value = {"id": "outcome-1"}

        CLOWorkflowService.get_clos_by_status(
            status=status,
            institution_id=institution_id,
            program_id=program_id,
        )

        mock_db.get_outcomes_by_status.assert_called_once_with(
            institution_id=institution_id,
            status=status,
            program_id=program_id,
        )

    @patch("clo_workflow_service.db")
    def test_get_clos_by_status_empty_result(self, mock_db):
        """Test getting CLOs when none match"""
        mock_db.get_outcomes_by_status.return_value = []

        result = CLOWorkflowService.get_clos_by_status(
            status=CLOStatus.AWAITING_APPROVAL,
            institution_id="inst-123",
        )

        assert result == []

    @patch("clo_workflow_service.CLOWorkflowService.get_outcome_with_details")
    @patch("clo_workflow_service.db")
    def test_get_clos_by_status_filters_none_details(self, mock_db, mock_get_details):
        """Test that outcomes with None details are filtered out"""
        mock_db.get_outcomes_by_status.return_value = [
            {"outcome_id": "outcome-1"},
            {"outcome_id": "outcome-2"},
            {"outcome_id": "outcome-3"},
        ]
        # Second outcome returns None (missing data)
        mock_get_details.side_effect = [
            {"outcome_id": "outcome-1", "clo_number": "1"},
            None,
            {"outcome_id": "outcome-3", "clo_number": "3"},
        ]

        result = CLOWorkflowService.get_clos_by_status(
            status=CLOStatus.AWAITING_APPROVAL,
            institution_id="inst-123",
        )

        assert len(result) == 2
        assert result[0]["outcome_id"] == "outcome-1"
        assert result[1]["outcome_id"] == "outcome-3"

    @patch("clo_workflow_service.db")
    def test_get_clos_by_status_exception_handling(self, mock_db):
        """Test exception handling in get_clos_by_status"""
        mock_db.get_outcomes_by_status.side_effect = Exception("Database error")

        result = CLOWorkflowService.get_clos_by_status(
            status=CLOStatus.AWAITING_APPROVAL,
            institution_id="inst-123",
        )

        assert result == []


class TestGetOutcomeWithDetails:
    """Test CLOWorkflowService.get_outcome_with_details method"""

    @patch("clo_workflow_service.db")
    def test_get_outcome_with_details_success(self, mock_db):
        """Test getting outcome with enriched details"""
        outcome_id = "outcome-123"

        mock_db.get_course_outcome.return_value = {
            "id": outcome_id,
            "course_id": "course-456",
            "clo_number": "1",
            "description": "Test CLO",
        }

        mock_db.get_course.return_value = {
            "id": "course-456",
            "course_number": "CS-101",
            "course_title": "Intro to CS",
        }

        mock_db.get_sections_by_course.return_value = [
            {"id": "section-789", "instructor_id": "instructor-111"}
        ]

        mock_db.get_user.return_value = {
            "id": "instructor-111",
            "display_name": "Jane Doe",
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
        }

        result = CLOWorkflowService.get_outcome_with_details(outcome_id)

        assert result is not None
        assert result["id"] == outcome_id
        assert result["course_number"] == "CS-101"
        assert result["course_title"] == "Intro to CS"
        assert result["instructor_name"] == "Jane Doe"
        assert result["instructor_email"] == "jane@example.com"

    @patch("clo_workflow_service.db")
    def test_get_outcome_with_details_not_found(self, mock_db):
        """Test getting details when outcome doesn't exist"""
        mock_db.get_course_outcome.return_value = None

        result = CLOWorkflowService.get_outcome_with_details("nonexistent")

        assert result is None

    @patch("clo_workflow_service.db")
    def test_get_outcome_with_details_no_instructor(self, mock_db):
        """Test getting details when course has no instructor"""
        mock_db.get_course_outcome.return_value = {
            "id": "outcome-123",
            "course_id": "course-456",
        }
        mock_db.get_course.return_value = {
            "id": "course-456",
            "course_number": "CS-101",
        }
        mock_db.get_sections_by_course.return_value = []

        result = CLOWorkflowService.get_outcome_with_details("outcome-123")

        assert result is not None
        assert result["instructor_name"] is None
        assert result["instructor_email"] is None

    @patch("clo_workflow_service.db")
    def test_get_outcome_with_details_instructor_no_display_name(self, mock_db):
        """Test getting details when instructor has no display_name"""
        mock_db.get_course_outcome.return_value = {
            "id": "outcome-123",
            "course_id": "course-456",
        }
        mock_db.get_course.return_value = {
            "id": "course-456",
            "course_number": "CS-101",
        }
        mock_db.get_sections_by_course.return_value = [
            {"id": "section-789", "instructor_id": "instructor-111"}
        ]
        mock_db.get_user.return_value = {
            "id": "instructor-111",
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
        }

        result = CLOWorkflowService.get_outcome_with_details("outcome-123")

        assert result is not None
        assert result["instructor_name"] == "Jane Doe"
        assert result["instructor_email"] == "jane@example.com"

    @patch("clo_workflow_service.db")
    def test_get_outcome_with_details_exception(self, mock_db):
        """Test getting details with database exception"""
        mock_db.get_course_outcome.side_effect = Exception("Database error")

        result = CLOWorkflowService.get_outcome_with_details("outcome-123")

        assert result is None


class TestSendReworkNotification:
    """Test CLOWorkflowService._send_rework_notification method"""

    @patch("clo_workflow_service.EmailService")
    @patch("clo_workflow_service.CLOWorkflowService.get_outcome_with_details")
    def test_send_rework_notification_success(
        self, mock_get_details, mock_email_service
    ):
        """Test sending rework notification email"""
        from app import app  # Import Flask app for context

        outcome_id = "outcome-123"
        feedback = "Please improve the assessment description"

        mock_get_details.return_value = {
            "id": outcome_id,
            "course_number": "CS-101",
            "clo_number": "1",
            "instructor_email": "instructor@example.com",
        }
        mock_email_service._send_email.return_value = True

        # Need app context for render_template()
        with app.app_context():
            result = CLOWorkflowService._send_rework_notification(outcome_id, feedback)

        assert result is True
        mock_email_service._send_email.assert_called_once()
        call_args = mock_email_service._send_email.call_args
        assert call_args[1]["to_email"] == "instructor@example.com"
        assert "CS-101" in call_args[1]["subject"]
        assert feedback in call_args[1]["text_body"]

    @patch("clo_workflow_service.CLOWorkflowService.get_outcome_with_details")
    def test_send_rework_notification_no_outcome(self, mock_get_details):
        """Test notification fails when outcome not found"""
        mock_get_details.return_value = None

        result = CLOWorkflowService._send_rework_notification("nonexistent", "Feedback")

        assert result is False

    @patch("clo_workflow_service.CLOWorkflowService.get_outcome_with_details")
    def test_send_rework_notification_no_email(self, mock_get_details):
        """Test notification fails when no instructor email"""
        mock_get_details.return_value = {
            "id": "outcome-123",
            "instructor_email": None,
        }

        result = CLOWorkflowService._send_rework_notification("outcome-123", "Feedback")

        assert result is False

    @patch("clo_workflow_service.EmailService")
    @patch("clo_workflow_service.CLOWorkflowService.get_outcome_with_details")
    def test_send_rework_notification_email_fails(
        self, mock_get_details, mock_email_service
    ):
        """Test notification when email sending fails"""
        from app import app

        mock_get_details.return_value = {
            "id": "outcome-123",
            "course_number": "CS-101",
            "clo_number": "1",
            "instructor_email": "instructor@example.com",
        }
        mock_email_service._send_email.return_value = False

        with app.app_context():
            result = CLOWorkflowService._send_rework_notification(
                "outcome-123", "Feedback"
            )

        assert result is False

    @patch("clo_workflow_service.EmailService")
    @patch("clo_workflow_service.CLOWorkflowService.get_outcome_with_details")
    def test_send_rework_notification_exception(
        self, mock_get_details, mock_email_service
    ):
        """Test notification when exception occurs"""
        mock_get_details.return_value = {
            "id": "outcome-123",
            "course_number": "CS-101",
            "clo_number": "1",
            "instructor_email": "instructor@example.com",
        }
        mock_email_service._send_email.side_effect = Exception("SMTP error")

        result = CLOWorkflowService._send_rework_notification("outcome-123", "Feedback")

        assert result is False


class TestGetInstructorFromOutcome:
    """Test CLOWorkflowService._get_instructor_from_outcome method"""

    @patch("clo_workflow_service.db")
    def test_get_instructor_from_submitted_by_user_id(self, mock_db):
        """Test getting instructor from submitted_by_user_id"""
        outcome = {
            "outcome_id": "outcome-123",
            "course_id": "course-456",
            "submitted_by_user_id": "user-789",
        }
        mock_db.get_user.return_value = {
            "id": "user-789",
            "email": "instructor@example.com",
        }

        result = CLOWorkflowService._get_instructor_from_outcome(outcome)

        assert result["id"] == "user-789"
        mock_db.get_user.assert_called_once_with("user-789")

    @patch("clo_workflow_service.db")
    def test_get_instructor_no_course_id(self, mock_db):
        """Test returns None when outcome has no course_id"""
        outcome = {
            "outcome_id": "outcome-123",
            "submitted_by_user_id": None,
            "course_id": None,
        }

        result = CLOWorkflowService._get_instructor_from_outcome(outcome)

        assert result is None

    @patch("clo_workflow_service.db")
    def test_get_instructor_no_instructor_id_in_section(self, mock_db):
        """Test returns None when section has no instructor_id"""
        outcome = {
            "outcome_id": "outcome-123",
            "course_id": "course-456",
            "submitted_by_user_id": None,
        }
        mock_db.get_sections_by_course.return_value = [
            {"section_id": "section-1", "instructor_id": None}
        ]

        result = CLOWorkflowService._get_instructor_from_outcome(outcome)

        assert result is None
