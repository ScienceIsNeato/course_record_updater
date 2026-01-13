"""
Unit tests for BulkEmailJob model
"""

from datetime import datetime, timezone
from unittest.mock import Mock

from src.bulk_email_models.bulk_email_job import BulkEmailJob


class TestBulkEmailJob:
    """Test BulkEmailJob model"""

    def test_to_dict(self):
        """Test converting job to dictionary"""
        job = BulkEmailJob(
            id="job-123",
            job_type="instructor_reminder",
            created_by_user_id="user-456",
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            started_at=datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 1, 12, 10, 0, tzinfo=timezone.utc),
            recipient_count=20,
            status="completed",
            emails_sent=18,
            emails_failed=2,
            emails_pending=0,
            personal_message="Test",
            failed_recipients=[{"email": "failed@example.com"}],
            error_message=None,
        )

        result = job.to_dict()

        assert result["id"] == "job-123"
        assert result["job_type"] == "instructor_reminder"
        assert result["created_by_user_id"] == "user-456"
        assert result["created_at"] == "2024-01-01T12:00:00+00:00"
        assert result["started_at"] == "2024-01-01T12:05:00+00:00"
        assert result["completed_at"] == "2024-01-01T12:10:00+00:00"
        assert result["recipient_count"] == 20
        assert result["status"] == "completed"
        assert result["emails_sent"] == 18
        assert result["emails_failed"] == 2
        assert result["emails_pending"] == 0
        assert result["personal_message"] == "Test"
        assert result["failed_recipients"] == [{"email": "failed@example.com"}]
        assert result["error_message"] is None
        assert result["progress_percentage"] == 100

    def test_to_dict_with_none_timestamps(self):
        """Test to_dict with None timestamps"""
        job = BulkEmailJob(
            id="job-123",
            job_type="test",
            created_by_user_id="user-456",
            created_at=None,
            started_at=None,
            completed_at=None,
            recipient_count=10,
            status="pending",
            emails_sent=0,
            emails_failed=0,
            emails_pending=10,
            personal_message=None,
            failed_recipients=None,
            error_message=None,
        )

        result = job.to_dict()

        assert result["created_at"] is None
        assert result["started_at"] is None
        assert result["completed_at"] is None
        assert result["failed_recipients"] == []

    def test_calculate_progress_percentage_zero_recipients(self):
        """Test progress calculation with zero recipients"""
        job = BulkEmailJob(
            id="job-123",
            job_type="test",
            created_by_user_id="user-456",
            created_at=datetime.now(timezone.utc),
            started_at=None,
            completed_at=None,
            recipient_count=0,
            status="pending",
            emails_sent=0,
            emails_failed=0,
            emails_pending=0,
            personal_message=None,
            failed_recipients=None,
            error_message=None,
        )

        progress = job._calculate_progress_percentage()
        assert progress == 0

    def test_calculate_progress_percentage_partial(self):
        """Test progress calculation with partial completion"""
        job = BulkEmailJob(
            id="job-123",
            job_type="test",
            created_by_user_id="user-456",
            created_at=datetime.now(timezone.utc),
            started_at=None,
            completed_at=None,
            recipient_count=100,
            status="running",
            emails_sent=45,
            emails_failed=5,
            emails_pending=50,
            personal_message=None,
            failed_recipients=None,
            error_message=None,
        )

        progress = job._calculate_progress_percentage()
        assert progress == 50

    def test_update_progress_first_time(self):
        """Test update_progress marks job as running"""
        job = BulkEmailJob(
            id="job-123",
            job_type="test",
            created_by_user_id="user-456",
            created_at=datetime.now(timezone.utc),
            started_at=None,
            completed_at=None,
            recipient_count=10,
            status="pending",
            emails_sent=0,
            emails_failed=0,
            emails_pending=10,
            personal_message=None,
            failed_recipients=None,
            error_message=None,
        )

        job.update_progress(
            emails_sent=3,
            emails_failed=1,
            emails_pending=6,
            failed_recipients=[{"email": "failed@example.com"}],
        )

        assert job.status == "running"
        assert job.started_at is not None
        assert job.emails_sent == 3
        assert job.emails_failed == 1
        assert job.emails_pending == 6
        assert job.failed_recipients == [{"email": "failed@example.com"}]

    def test_update_progress_completion(self):
        """Test update_progress marks job as completed"""
        job = BulkEmailJob(
            id="job-123",
            job_type="test",
            created_by_user_id="user-456",
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            recipient_count=10,
            status="running",
            emails_sent=5,
            emails_failed=2,
            emails_pending=3,
            personal_message=None,
            failed_recipients=None,
            error_message=None,
        )

        job.update_progress(emails_sent=8, emails_failed=2, emails_pending=0)

        assert job.status == "completed"
        assert job.completed_at is not None
        assert job.emails_sent == 8
        assert job.emails_failed == 2
        assert job.emails_pending == 0

    def test_mark_failed(self):
        """Test marking job as failed"""
        job = BulkEmailJob(
            id="job-123",
            job_type="test",
            created_by_user_id="user-456",
            created_at=datetime.now(timezone.utc),
            started_at=None,
            completed_at=None,
            recipient_count=10,
            status="pending",
            emails_sent=0,
            emails_failed=0,
            emails_pending=10,
            personal_message=None,
            failed_recipients=None,
            error_message=None,
        )

        job.mark_failed("SMTP connection timeout")

        assert job.status == "failed"
        assert job.error_message == "SMTP connection timeout"
        assert job.completed_at is not None

    def test_mark_cancelled(self):
        """Test marking job as cancelled"""
        job = BulkEmailJob(
            id="job-123",
            job_type="test",
            created_by_user_id="user-456",
            created_at=datetime.now(timezone.utc),
            started_at=None,
            completed_at=None,
            recipient_count=10,
            status="running",
            emails_sent=3,
            emails_failed=0,
            emails_pending=7,
            personal_message=None,
            failed_recipients=None,
            error_message=None,
        )

        job.mark_cancelled()

        assert job.status == "cancelled"
        assert job.completed_at is not None

    def test_create_job(self):
        """Test create_job static method"""
        mock_db = Mock()
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        recipients = [
            {"email": "user1@example.com", "name": "User 1"},
            {"email": "user2@example.com", "name": "User 2"},
        ]

        job = BulkEmailJob.create_job(
            db=mock_db,
            job_type="instructor_reminder",
            created_by_user_id="admin-123",
            recipients=recipients,
            template_data={"term": "Fall 2024"},
            personal_message="Please submit by Friday",
        )

        # Verify job was created correctly
        assert job.job_type == "instructor_reminder"
        assert job.created_by_user_id == "admin-123"
        assert job.recipient_count == 2
        assert job.recipients == recipients
        assert job.template_data == {"term": "Fall 2024"}
        assert job.personal_message == "Please submit by Friday"
        assert job.emails_pending == 2
        # Note: status/id defaults are set by SQLAlchemy at DB level, not in Python

        # Verify database operations
        mock_db.add.assert_called_once_with(job)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(job)

    def test_get_job(self):
        """Test get_job static method"""
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()

        expected_job = BulkEmailJob(
            id="job-123",
            job_type="test",
            created_by_user_id="user-456",
            recipient_count=10,
            status="completed",
        )

        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = expected_job

        result = BulkEmailJob.get_job(mock_db, "job-123")

        assert result == expected_job
        mock_db.query.assert_called_once_with(BulkEmailJob)

    def test_get_recent_jobs_with_user_filter(self):
        """Test get_recent_jobs with user_id filter"""
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_limit = Mock()

        expected_jobs = [
            BulkEmailJob(
                id="job-1",
                job_type="test",
                created_by_user_id="user-123",
                recipient_count=5,
            ),
            BulkEmailJob(
                id="job-2",
                job_type="test",
                created_by_user_id="user-123",
                recipient_count=3,
            ),
        ]

        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.limit.return_value = mock_limit
        mock_limit.all.return_value = expected_jobs

        result = BulkEmailJob.get_recent_jobs(mock_db, user_id="user-123", limit=10)

        assert result == expected_jobs
        mock_db.query.assert_called_once_with(BulkEmailJob)
        mock_query.filter.assert_called_once()

    def test_get_recent_jobs_without_user_filter(self):
        """Test get_recent_jobs without user_id filter"""
        mock_db = Mock()
        mock_query = Mock()
        mock_order = Mock()
        mock_limit = Mock()

        expected_jobs = [
            BulkEmailJob(
                id="job-1",
                job_type="test",
                created_by_user_id="user-123",
                recipient_count=5,
            ),
            BulkEmailJob(
                id="job-2",
                job_type="test",
                created_by_user_id="user-456",
                recipient_count=3,
            ),
        ]

        mock_db.query.return_value = mock_query
        mock_query.order_by.return_value = mock_order
        mock_order.limit.return_value = mock_limit
        mock_limit.all.return_value = expected_jobs

        result = BulkEmailJob.get_recent_jobs(mock_db, user_id=None, limit=50)

        assert result == expected_jobs
        mock_db.query.assert_called_once_with(BulkEmailJob)
        # Should NOT call filter when user_id is None
        mock_query.filter.assert_not_called()
