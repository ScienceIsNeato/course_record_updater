"""
Unit tests for BulkEmailJob model
"""

from datetime import datetime, timezone

from bulk_email_models.bulk_email_job import BulkEmailJob


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
