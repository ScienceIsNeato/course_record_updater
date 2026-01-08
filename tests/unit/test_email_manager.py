"""
Unit tests for EmailManager

Tests rate limiting, exponential backoff, retry logic, and queue management.
"""

import time
import unittest
from unittest.mock import Mock, patch

from src.email_providers.email_manager import EmailJob, EmailManager, EmailStatus


class TestEmailJob(unittest.TestCase):
    """Test EmailJob dataclass"""

    def test_email_job_creation(self):
        """Test creating an EmailJob"""
        job = EmailJob(
            to_email="test@example.com",
            subject="Test Subject",
            html_body="<p>Test</p>",
            text_body="Test",
        )

        assert job.to_email == "test@example.com"
        assert job.subject == "Test Subject"
        assert job.html_body == "<p>Test</p>"
        assert job.text_body == "Test"
        assert job.status == EmailStatus.PENDING
        assert job.attempts == 0
        assert job.last_error is None
        assert job.metadata is None

    def test_email_job_with_metadata(self):
        """Test EmailJob with metadata"""
        metadata = {"user_id": 123, "template": "verification"}
        job = EmailJob(
            to_email="test@example.com",
            subject="Test",
            html_body="<p>Test</p>",
            text_body="Test",
            metadata=metadata,
        )

        assert job.metadata == metadata


class TestEmailManagerInitialization(unittest.TestCase):
    """Test EmailManager initialization"""

    def test_default_initialization(self):
        """Test EmailManager with default settings"""
        manager = EmailManager()

        assert manager.rate == 0.1
        assert manager.max_retries == 3
        assert manager.base_delay == 5.0
        assert manager.max_delay == 60.0
        assert manager.tokens == 1.0
        assert len(manager.queue) == 0

    def test_custom_initialization(self):
        """Test EmailManager with custom settings"""
        manager = EmailManager(rate=0.5, max_retries=5, base_delay=2.0, max_delay=30.0)

        assert manager.rate == 0.5
        assert manager.max_retries == 5
        assert manager.base_delay == 2.0
        assert manager.max_delay == 30.0


class TestEmailManagerQueueManagement(unittest.TestCase):
    """Test queue management functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.manager = EmailManager(rate=1.0)  # Fast rate for testing

    def test_add_email(self):
        """Test adding an email to the queue"""
        job = self.manager.add_email(
            to_email="test@example.com",
            subject="Test Subject",
            html_body="<p>Test</p>",
            text_body="Test",
        )

        assert isinstance(job, EmailJob)
        assert job.to_email == "test@example.com"
        assert job.status == EmailStatus.PENDING
        assert len(self.manager.queue) == 1

    def test_add_multiple_emails(self):
        """Test adding multiple emails to the queue"""
        for i in range(3):
            self.manager.add_email(
                to_email=f"test{i}@example.com",
                subject=f"Test {i}",
                html_body=f"<p>Test {i}</p>",
                text_body=f"Test {i}",
            )

        assert len(self.manager.queue) == 3
        assert all(job.status == EmailStatus.PENDING for job in self.manager.queue)

    def test_get_status_empty_queue(self):
        """Test getting status of empty queue"""
        status = self.manager.get_status()

        assert status["pending"] == 0
        assert status["sending"] == 0
        assert status["sent"] == 0
        assert status["failed"] == 0
        assert status["total"] == 0

    def test_get_status_with_emails(self):
        """Test getting status with emails in queue"""
        # Add some emails
        self.manager.add_email("test1@example.com", "Test 1", "<p>Test</p>", "Test")
        self.manager.add_email("test2@example.com", "Test 2", "<p>Test</p>", "Test")

        status = self.manager.get_status()

        assert status["pending"] == 2
        assert status["total"] == 2

    def test_clear_queue(self):
        """Test clearing the queue"""
        # Add some emails
        self.manager.add_email("test1@example.com", "Test 1", "<p>Test</p>", "Test")
        self.manager.add_email("test2@example.com", "Test 2", "<p>Test</p>", "Test")

        assert len(self.manager.queue) == 2

        self.manager.clear_queue()

        assert len(self.manager.queue) == 0

    def test_get_failed_jobs(self):
        """Test getting failed jobs"""
        # Add and mark some jobs as failed
        job1 = self.manager.add_email(
            "test1@example.com", "Test 1", "<p>Test</p>", "Test"
        )
        job2 = self.manager.add_email(
            "test2@example.com", "Test 2", "<p>Test</p>", "Test"
        )
        job3 = self.manager.add_email(
            "test3@example.com", "Test 3", "<p>Test</p>", "Test"
        )

        job1.status = EmailStatus.FAILED
        job3.status = EmailStatus.FAILED

        failed_jobs = self.manager.get_failed_jobs()

        assert len(failed_jobs) == 2
        assert job1 in failed_jobs
        assert job3 in failed_jobs
        assert job2 not in failed_jobs


class TestEmailManagerRateLimiting(unittest.TestCase):
    """Test rate limiting functionality"""

    def test_acquire_token_immediate(self):
        """Test acquiring a token when one is available"""
        manager = EmailManager(rate=1.0)

        # First token should be immediate (starts with 1 token)
        start_time = time.time()
        success = manager._acquire_token(timeout=1.0)
        elapsed = time.time() - start_time

        assert success is True
        assert elapsed < 0.1  # Should be nearly instant

    def test_acquire_token_wait(self):
        """Test acquiring a token when none available (must wait)"""
        manager = EmailManager(rate=10.0)  # 10 tokens per second = 0.1s per token

        # Use up the initial token
        manager._acquire_token(timeout=1.0)

        # Next token should require waiting
        start_time = time.time()
        success = manager._acquire_token(timeout=1.0)
        elapsed = time.time() - start_time

        assert success is True
        assert elapsed >= 0.05  # Should wait at least 0.05s (conservative)

    def test_acquire_token_timeout(self):
        """Test token acquisition timeout"""
        manager = EmailManager(rate=0.1)  # Very slow rate

        # Use up the initial token
        manager._acquire_token(timeout=1.0)

        # Try to acquire another with short timeout (should fail)
        success = manager._acquire_token(timeout=0.1)

        assert success is False

    def test_calculate_backoff_delay(self):
        """Test exponential backoff calculation"""
        manager = EmailManager(base_delay=2.0, max_delay=20.0)

        # Test exponential growth
        assert manager._calculate_backoff_delay(0) == 2.0  # 2 * 2^0
        assert manager._calculate_backoff_delay(1) == 4.0  # 2 * 2^1
        assert manager._calculate_backoff_delay(2) == 8.0  # 2 * 2^2
        assert manager._calculate_backoff_delay(3) == 16.0  # 2 * 2^3

        # Test max delay cap
        assert manager._calculate_backoff_delay(4) == 20.0  # Capped at max_delay
        assert manager._calculate_backoff_delay(10) == 20.0  # Still capped


class TestEmailManagerSending(unittest.TestCase):
    """Test email sending functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.manager = EmailManager(rate=10.0, max_retries=3, base_delay=0.1)
        self.send_func = Mock()

    def test_send_all_success(self):
        """Test sending all emails successfully"""
        # Add emails
        self.manager.add_email("test1@example.com", "Test 1", "<p>Test</p>", "Test")
        self.manager.add_email("test2@example.com", "Test 2", "<p>Test</p>", "Test")

        # Mock successful sending
        self.send_func.return_value = True

        stats = self.manager.send_all(self.send_func, timeout=5.0)

        assert stats["sent"] == 2
        assert stats["failed"] == 0
        assert stats["pending"] == 0
        assert self.send_func.call_count == 2

    def test_send_all_failures(self):
        """Test sending with all failures"""
        # Add emails
        self.manager.add_email("test1@example.com", "Test 1", "<p>Test</p>", "Test")
        self.manager.add_email("test2@example.com", "Test 2", "<p>Test</p>", "Test")

        # Mock failed sending
        self.send_func.return_value = False

        stats = self.manager.send_all(self.send_func, timeout=5.0)

        assert stats["sent"] == 0
        assert stats["failed"] == 2
        assert stats["pending"] == 0
        # Should retry 3 times per email
        assert self.send_func.call_count == 6  # 2 emails * 3 retries

    def test_send_all_mixed_results(self):
        """Test sending with mixed success/failure"""
        # Add emails
        self.manager.add_email("test1@example.com", "Test 1", "<p>Test</p>", "Test")
        self.manager.add_email("test2@example.com", "Test 2", "<p>Test</p>", "Test")
        self.manager.add_email("test3@example.com", "Test 3", "<p>Test</p>", "Test")

        # Mock: first succeeds, second fails, third succeeds
        self.send_func.side_effect = [True, False, False, False, True]

        stats = self.manager.send_all(self.send_func, timeout=5.0)

        assert stats["sent"] == 2
        assert stats["failed"] == 1
        assert stats["pending"] == 0

    def test_send_with_retry_success_on_first_attempt(self):
        """Test sending succeeds on first attempt"""
        job = self.manager.add_email("test@example.com", "Test", "<p>Test</p>", "Test")
        self.send_func.return_value = True

        success = self.manager._send_with_retry(job, self.send_func, timeout=5.0)

        assert success is True
        assert job.attempts == 1
        assert self.send_func.call_count == 1

    def test_send_with_retry_success_on_second_attempt(self):
        """Test sending succeeds on second attempt"""
        job = self.manager.add_email("test@example.com", "Test", "<p>Test</p>", "Test")
        self.send_func.side_effect = [False, True]

        success = self.manager._send_with_retry(job, self.send_func, timeout=5.0)

        assert success is True
        assert job.attempts == 2
        assert self.send_func.call_count == 2

    def test_send_with_retry_all_attempts_fail(self):
        """Test sending fails after all retry attempts"""
        job = self.manager.add_email("test@example.com", "Test", "<p>Test</p>", "Test")
        self.send_func.return_value = False

        success = self.manager._send_with_retry(job, self.send_func, timeout=5.0)

        assert success is False
        assert job.attempts == 3  # max_retries
        assert self.send_func.call_count == 3

    def test_send_with_retry_exception_handling(self):
        """Test exception handling during send"""
        job = self.manager.add_email("test@example.com", "Test", "<p>Test</p>", "Test")
        self.send_func.side_effect = [
            Exception("Network error"),
            Exception("Timeout"),
            True,  # Succeeds on third attempt
        ]

        success = self.manager._send_with_retry(job, self.send_func, timeout=5.0)

        assert success is True
        assert job.attempts == 3
        assert self.send_func.call_count == 3

    def test_send_with_retry_records_last_error(self):
        """Test that last error is recorded"""
        job = self.manager.add_email("test@example.com", "Test", "<p>Test</p>", "Test")
        error_msg = "Connection refused"
        self.send_func.side_effect = Exception(error_msg)

        success = self.manager._send_with_retry(job, self.send_func, timeout=5.0)

        assert success is False
        assert job.last_error == error_msg

    def test_send_empty_queue(self):
        """Test sending with empty queue"""
        stats = self.manager.send_all(self.send_func, timeout=5.0)

        assert stats["sent"] == 0
        assert stats["failed"] == 0
        assert stats["pending"] == 0
        assert self.send_func.call_count == 0


class TestEmailManagerIntegration(unittest.TestCase):
    """Integration tests for EmailManager"""

    def test_full_workflow_all_success(self):
        """Test complete workflow with all emails succeeding"""
        manager = EmailManager(rate=10.0, max_retries=2, base_delay=0.1)

        # Add emails
        recipients = ["test1@example.com", "test2@example.com", "test3@example.com"]
        for email in recipients:
            manager.add_email(email, "Test", "<p>Test</p>", "Test")

        # Verify initial status
        status = manager.get_status()
        assert status["pending"] == 3
        assert status["total"] == 3

        # Send all emails
        send_func = Mock(return_value=True)
        stats = manager.send_all(send_func, timeout=5.0)

        # Verify results
        assert stats["sent"] == 3
        assert stats["failed"] == 0

        # Verify final status
        status = manager.get_status()
        assert status["sent"] == 3
        assert status["failed"] == 0
        assert status["pending"] == 0

    def test_full_workflow_with_retries(self):
        """Test complete workflow with retries"""
        manager = EmailManager(rate=10.0, max_retries=3, base_delay=0.1)

        # Add emails
        manager.add_email("test1@example.com", "Test 1", "<p>Test</p>", "Test")
        manager.add_email("test2@example.com", "Test 2", "<p>Test</p>", "Test")

        # Mock: first email fails twice then succeeds, second email succeeds immediately
        send_func = Mock(side_effect=[False, False, True, True])

        stats = manager.send_all(send_func, timeout=5.0)

        assert stats["sent"] == 2
        assert stats["failed"] == 0
        assert send_func.call_count == 4  # 3 attempts for first, 1 for second

    def test_full_workflow_with_failures(self):
        """Test complete workflow with permanent failures"""
        manager = EmailManager(rate=10.0, max_retries=2, base_delay=0.1)

        # Add emails
        manager.add_email("test1@example.com", "Test 1", "<p>Test</p>", "Test")
        manager.add_email("test2@example.com", "Test 2", "<p>Test</p>", "Test")
        manager.add_email("test3@example.com", "Test 3", "<p>Test</p>", "Test")

        # Mock: first succeeds, second always fails, third succeeds
        send_func = Mock(side_effect=[True, False, False, True])

        stats = manager.send_all(send_func, timeout=5.0)

        assert stats["sent"] == 2
        assert stats["failed"] == 1

        # Check failed jobs
        failed_jobs = manager.get_failed_jobs()
        assert len(failed_jobs) == 1
        assert failed_jobs[0].to_email == "test2@example.com"
        assert failed_jobs[0].attempts == 2


if __name__ == "__main__":
    unittest.main()
