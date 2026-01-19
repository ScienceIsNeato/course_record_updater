"""Unit tests for BulkEmailService."""

from unittest.mock import Mock, patch

import pytest

from src.services.bulk_email_service import BulkEmailService


@pytest.mark.unit
class TestBulkEmailService:
    """Test suite for BulkEmailService."""

    @patch("src.services.bulk_email_service.threading.Thread")
    @patch("src.services.bulk_email_service.BulkEmailJob")
    def test_send_instructor_reminders_success(self, mock_bulk_email_job, mock_thread):
        """Test sending reminders to instructors successfully."""
        # Setup mock database session
        mock_db = Mock()

        # Setup mock users
        mock_user1 = Mock()
        mock_user1.id = "user-1"
        mock_user1.email = "instructor1@test.edu"
        mock_user1.first_name = "John"
        mock_user1.last_name = "Doe"

        mock_user2 = Mock()
        mock_user2.id = "user-2"
        mock_user2.email = "instructor2@test.edu"
        mock_user2.first_name = "Jane"
        mock_user2.last_name = "Smith"

        # Mock database queries
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            mock_user1,
            mock_user2,
        ]

        # Mock job creation
        mock_job = Mock()
        mock_job.id = "job-123"
        mock_bulk_email_job.create_job.return_value = mock_job

        # Create Flask app and run within app context
        from flask import Flask

        app = Flask(__name__)

        with app.app_context():
            job_id = BulkEmailService.send_instructor_reminders(
                db=mock_db,
                instructor_ids=["user-1", "user-2"],
                created_by_user_id="admin-1",
                personal_message="Please submit your data",
                term="FA2024",
                deadline="2024-12-31",
            )

        # Verify
        assert job_id == "job-123"
        mock_bulk_email_job.create_job.assert_called_once()
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

    @patch("src.services.bulk_email_service.BulkEmailJob")
    def test_send_instructor_reminders_instructor_not_found(self, mock_bulk_email_job):
        """Test sending reminders when instructor not found."""
        mock_db = Mock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        mock_job = Mock()
        mock_job.id = "job-123"
        mock_bulk_email_job.create_job.return_value = mock_job

        # Create Flask app and run within app context
        from flask import Flask

        app = Flask(__name__)

        with app.app_context():
            # Should still create job even with no valid recipients
            job_id = BulkEmailService.send_instructor_reminders(
                db=mock_db,
                instructor_ids=["invalid-id"],
                created_by_user_id="admin-1",
            )

        assert job_id == "job-123"
        # Job should be created with empty recipients list
        call_args = mock_bulk_email_job.create_job.call_args
        assert call_args[1]["recipients"] == []

    @patch("src.services.bulk_email_service.BulkEmailJob")
    def test_send_instructor_reminders_no_email(self, mock_bulk_email_job):
        """Test sending reminders when instructor has no email."""
        mock_db = Mock()

        mock_user = Mock()
        mock_user.id = "user-1"
        mock_user.email = None  # No email
        mock_user.first_name = "John"
        mock_user.last_name = "Doe"

        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user

        mock_job = Mock()
        mock_job.id = "job-123"
        mock_bulk_email_job.create_job.return_value = mock_job

        # Create Flask app and run within app context
        from flask import Flask

        app = Flask(__name__)

        with app.app_context():
            job_id = BulkEmailService.send_instructor_reminders(
                db=mock_db,
                instructor_ids=["user-1"],
                created_by_user_id="admin-1",
            )

        assert job_id == "job-123"
        # Should skip user with no email
        call_args = mock_bulk_email_job.create_job.call_args
        assert call_args[1]["recipients"] == []

    @patch("src.services.bulk_email_service.BulkEmailJob")
    def test_send_instructor_reminders_no_name_fallback(self, mock_bulk_email_job):
        """Test sending reminders when instructor has no name (fallback to email)."""
        mock_db = Mock()

        mock_user = Mock()
        mock_user.id = "user-1"
        mock_user.email = "instructor@test.edu"
        mock_user.first_name = None
        mock_user.last_name = None

        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user

        mock_job = Mock()
        mock_job.id = "job-123"
        mock_bulk_email_job.create_job.return_value = mock_job

        # Create Flask app and run within app context
        from flask import Flask

        app = Flask(__name__)

        with app.app_context():
            job_id = BulkEmailService.send_instructor_reminders(
                db=mock_db,
                instructor_ids=["user-1"],
                created_by_user_id="admin-1",
            )

        assert job_id == "job-123"
        # Should use email as name
        call_args = mock_bulk_email_job.create_job.call_args
        recipients = call_args[1]["recipients"]
        assert len(recipients) == 1
        assert recipients[0]["name"] == "instructor@test.edu"

    def test_render_reminder_html_with_all_fields(self):
        """Test HTML rendering with all optional fields."""
        html = BulkEmailService._render_reminder_html(
            instructor_name="Dr. Smith",
            personal_message="Please review the new guidelines.",
            term="Spring 2024",
            deadline="March 15, 2024",
            base_url="http://localhost:5000",
        )

        assert "Dr. Smith" in html
        assert "Please review the new guidelines." in html
        assert "Spring 2024" in html
        assert "March 15, 2024" in html
        assert "<!DOCTYPE html>" in html

    def test_render_reminder_html_minimal(self):
        """Test HTML rendering with minimal fields."""
        html = BulkEmailService._render_reminder_html(
            instructor_name="Dr. Smith",
            personal_message=None,
            term=None,
            deadline=None,
            base_url="http://localhost:5000",
        )

        assert "Dr. Smith" in html
        assert "<!DOCTYPE html>" in html

    def test_render_reminder_html_with_course_id(self):
        """Test HTML rendering with course_id for course-specific link."""
        html = BulkEmailService._render_reminder_html(
            instructor_name="Dr. Smith",
            personal_message="Please review",
            term="Spring 2024",
            deadline="March 15",
            base_url="http://localhost:5000",
            course_id="course-123",
        )

        assert "Dr. Smith" in html
        assert "course-123" in html
        # URL should be properly encoded (old bug had double ?)
        assert "/reminder-login?next=/assessments%3Fcourse%3Dcourse-123" in html
        assert "Enter Course Assessments" in html

    def test_render_reminder_text_with_all_fields(self):
        """Test text rendering with all optional fields."""
        text = BulkEmailService._render_reminder_text(
            instructor_name="Dr. Smith",
            personal_message="Please review the new guidelines.",
            term="Spring 2024",
            deadline="March 15, 2024",
            base_url="http://localhost:5000",
        )

        assert "Dr. Smith" in text
        assert "Please review the new guidelines." in text
        assert "Spring 2024" in text
        assert "March 15, 2024" in text

    def test_render_reminder_text_minimal(self):
        """Test text rendering with minimal fields."""
        text = BulkEmailService._render_reminder_text(
            instructor_name="Dr. Smith",
            personal_message=None,
            term=None,
            deadline=None,
            base_url="http://localhost:5000",
        )

        assert "Dr. Smith" in text

    def test_render_reminder_text_with_course_id(self):
        """Test text rendering with course_id for course-specific link."""
        text = BulkEmailService._render_reminder_text(
            instructor_name="Dr. Smith",
            personal_message="Please review",
            term="Spring 2024",
            deadline="March 15",
            base_url="http://localhost:5000",
            course_id="course-123",
        )

        assert "Dr. Smith" in text
        assert "/reminder-login?next=/assessments?course=course-123" in text
        assert "enter your course assessments" in text

    @patch("src.services.bulk_email_service.BulkEmailJob")
    def test_get_job_status_success(self, mock_bulk_email_job):
        """Test getting job status successfully."""
        mock_db = Mock()

        mock_job = Mock()
        mock_job.to_dict.return_value = {
            "job_id": "job-123",
            "status": "in_progress",
            "total_recipients": 10,
            "emails_sent": 5,
            "emails_failed": 1,
            "emails_pending": 4,
            "error_message": None,
            "created_at": "2024-01-01",
            "completed_at": None,
        }

        mock_bulk_email_job.get_job.return_value = mock_job

        result = BulkEmailService.get_job_status(mock_db, "job-123")

        assert result["job_id"] == "job-123"
        assert result["status"] == "in_progress"
        assert result["total_recipients"] == 10
        assert result["emails_sent"] == 5

    @patch("src.services.bulk_email_service.BulkEmailJob")
    def test_get_job_status_not_found(self, mock_bulk_email_job):
        """Test getting status for non-existent job."""
        mock_db = Mock()
        mock_bulk_email_job.get_job.return_value = None

        result = BulkEmailService.get_job_status(mock_db, "invalid-job-id")

        assert result is None

    @patch("src.services.bulk_email_service.BulkEmailJob")
    def test_get_recent_jobs_success(self, mock_bulk_email_job):
        """Test getting recent jobs."""
        mock_db = Mock()

        mock_job1 = Mock()
        mock_job1.to_dict.return_value = {
            "job_id": "job-1",
            "status": "completed",
            "job_type": "instructor_reminder",
            "created_by_user_id": "admin-1",
            "total_recipients": 5,
            "created_at": "2024-01-01",
        }

        mock_job2 = Mock()
        mock_job2.to_dict.return_value = {
            "job_id": "job-2",
            "status": "in_progress",
            "job_type": "instructor_reminder",
            "created_by_user_id": "admin-1",
            "total_recipients": 3,
            "created_at": "2024-01-02",
        }

        mock_bulk_email_job.get_recent_jobs.return_value = [mock_job1, mock_job2]

        results = BulkEmailService.get_recent_jobs(mock_db, "admin-1", limit=10)

        assert len(results) == 2
        assert results[0]["job_id"] == "job-1"
        assert results[1]["job_id"] == "job-2"

    @patch("src.services.bulk_email_service.BulkEmailJob")
    def test_get_recent_jobs_empty(self, mock_bulk_email_job):
        """Test getting recent jobs when none exist."""
        mock_db = Mock()
        mock_bulk_email_job.get_recent_jobs.return_value = []

        results = BulkEmailService.get_recent_jobs(mock_db, "admin-1", limit=10)

        assert results == []

    @patch("src.database.database_factory.get_database_service")
    @patch("src.services.bulk_email_service.EmailManager")
    @patch("src.services.bulk_email_service.EmailService")
    @patch("src.services.bulk_email_service.BulkEmailJob")
    def test_send_emails_background_success(
        self,
        mock_bulk_email_job,
        mock_email_service,
        mock_email_manager,
        mock_get_db,
    ):
        """Test background email sending."""
        # Setup mocks
        mock_db = Mock()
        mock_db_service = Mock()
        mock_db_service.sql.get_session.return_value = mock_db
        mock_get_db.return_value = mock_db_service

        # Create Flask app context for current_app access
        from flask import Flask

        app = Flask(__name__)
        app.config["BASE_URL"] = "http://localhost:5000"

        mock_job = Mock()
        mock_job.id = "job-123"
        mock_bulk_email_job.get_job.return_value = mock_job

        mock_manager_instance = Mock()
        mock_manager_instance.get_status.return_value = {
            "sent": 2,
            "failed": 0,
            "pending": 0,
        }
        mock_manager_instance.get_failed_jobs.return_value = []
        mock_manager_instance.send_all.return_value = {"sent": 2, "failed": 0}
        mock_email_manager.return_value = mock_manager_instance

        mock_service_instance = Mock()
        mock_service_instance._send_email.return_value = True
        mock_email_service.return_value = mock_service_instance

        recipients = [
            {"user_id": "user-1", "email": "user1@test.edu", "name": "User 1"},
            {"user_id": "user-2", "email": "user2@test.edu", "name": "User 2"},
        ]

        # Execute within Flask app context
        with app.app_context():
            BulkEmailService._send_emails_background(
                app=app,
                job_id="job-123",
                recipients=recipients,
                personal_message="Test message",
                term="FA2024",
                deadline="2024-12-31",
            )

        # Verify
        mock_manager_instance.add_email.assert_called()
        mock_manager_instance.send_all.assert_called_once()
        mock_job.update_progress.assert_called()
        mock_db.commit.assert_called()
        mock_db.close.assert_called_once()

    @patch("src.database.database_factory.get_database_service")
    @patch("src.services.bulk_email_service.BulkEmailJob")
    def test_send_emails_background_job_not_found(
        self, mock_bulk_email_job, mock_get_db
    ):
        """Test background sending when job not found."""
        mock_db = Mock()
        mock_db_service = Mock()
        mock_db_service.sql.get_session.return_value = mock_db
        mock_get_db.return_value = mock_db_service

        mock_bulk_email_job.get_job.return_value = None

        # Should handle gracefully
        from flask import Flask

        app = Flask(__name__)

        BulkEmailService._send_emails_background(
            app=app,
            job_id="invalid-job",
            recipients=[],
            personal_message=None,
            term=None,
            deadline=None,
        )

        mock_db.close.assert_called_once()

    @patch("src.database.database_factory.get_database_service")
    @patch("src.services.bulk_email_service.BulkEmailJob")
    def test_send_emails_background_exception_handling(
        self, mock_bulk_email_job, mock_get_db
    ):
        """Test background sending exception handling."""
        mock_db = Mock()
        mock_db_service = Mock()
        mock_db_service.sql.get_session.return_value = mock_db
        mock_get_db.return_value = mock_db_service

        # First call returns job, second call (in except block) returns job
        mock_job = Mock()
        mock_job.id = "job-123"
        mock_bulk_email_job.get_job.side_effect = [
            Exception("Test error"),  # First call raises
            mock_job,  # Second call in except block returns job
        ]

        # Should handle exception and mark job as failed
        from flask import Flask

        app = Flask(__name__)

        BulkEmailService._send_emails_background(
            app=app,
            job_id="job-123",
            recipients=[],
            personal_message=None,
            term=None,
            deadline=None,
        )

        # Verify job marked as failed
        assert mock_bulk_email_job.get_job.call_count == 2
        mock_db.close.assert_called_once()
