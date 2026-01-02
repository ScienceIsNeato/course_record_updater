"""
Email Manager

Centralized email sending with rate limiting, exponential backoff, and retry logic.
Handles the complexities of working with rate-limited email APIs like Mailtrap.
"""

import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class EmailStatus(Enum):
    """Status of an email in the queue"""
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


@dataclass
class EmailJob:
    """Represents a single email to be sent"""
    to_email: str
    subject: str
    html_body: str
    text_body: str
    status: EmailStatus = EmailStatus.PENDING
    attempts: int = 0
    last_error: Optional[str] = None
    metadata: Optional[Dict] = None


class EmailManager:
    """
    Manages email sending with rate limiting, exponential backoff, and retries.
    
    Features:
    - Token bucket rate limiting
    - Exponential backoff for rate limit errors
    - Automatic retry with configurable max attempts
    - Thread-safe queue management
    - Detailed status tracking
    """
    
    def __init__(
        self,
        rate: float = 0.1,  # Emails per second (0.1 = 1 every 10 seconds)
        max_retries: int = 3,
        base_delay: float = 5.0,  # Base delay for exponential backoff
        max_delay: float = 60.0,  # Maximum delay between retries
    ):
        """
        Initialize the email manager.
        
        Args:
            rate: Maximum emails per second
            max_retries: Maximum retry attempts per email
            base_delay: Base delay in seconds for exponential backoff
            max_delay: Maximum delay in seconds between retries
        """
        self.rate = rate
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        
        # Token bucket for rate limiting
        self.tokens = 1.0
        self.last_update = time.time()
        
        # Queue management
        self.queue: List[EmailJob] = []
        self.lock = threading.Lock()
        
        logger.info(
            f"[EmailManager] Initialized (rate={rate}/s, max_retries={max_retries}, "
            f"base_delay={base_delay}s, max_delay={max_delay}s)"
        )
    
    def add_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
        metadata: Optional[Dict] = None
    ) -> EmailJob:
        """
        Add an email to the queue.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML body content
            text_body: Plain text body content
            metadata: Optional metadata for tracking
            
        Returns:
            The created EmailJob
        """
        job = EmailJob(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            metadata=metadata or {}
        )
        
        with self.lock:
            self.queue.append(job)
        
        logger.debug(f"[EmailManager] Added email to queue: {to_email}")
        return job
    
    def _acquire_token(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire a token from the rate limiter.
        
        Args:
            timeout: Maximum time to wait for a token
            
        Returns:
            True if token acquired, False if timeout
        """
        start_time = time.time()
        
        while True:
            with self.lock:
                current_time = time.time()
                elapsed = current_time - self.last_update
                self.last_update = current_time
                
                # Add tokens based on elapsed time
                self.tokens = min(1.0, self.tokens + elapsed * self.rate)
                
                # Check if we can acquire a token
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return True
                
                # Check timeout
                if timeout is not None and (current_time - start_time) >= timeout:
                    return False
                
                # Calculate wait time for next token
                wait_time = (1.0 - self.tokens) / self.rate
            
            # Sleep outside the lock
            time.sleep(min(wait_time, 0.1))
    
    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)
    
    def send_all(
        self,
        send_func: Callable[[str, str, str, str], bool],
        timeout: Optional[float] = None
    ) -> Dict[str, int]:
        """
        Send all emails in the queue.
        
        Args:
            send_func: Function to send email (to, subject, html, text) -> bool
            timeout: Maximum time to wait for rate limiting per email
            
        Returns:
            Dictionary with counts: {sent, failed, pending}
        """
        stats = {"sent": 0, "failed": 0, "pending": 0}
        
        while True:
            # Get next pending email
            job = None
            with self.lock:
                for j in self.queue:
                    if j.status == EmailStatus.PENDING:
                        job = j
                        job.status = EmailStatus.SENDING
                        break
                
                if job is None:
                    # No more pending emails
                    break
            
            # Try to send the email with retries
            success = self._send_with_retry(job, send_func, timeout)
            
            with self.lock:
                if success:
                    job.status = EmailStatus.SENT
                    stats["sent"] += 1
                    logger.info(f"[EmailManager] Successfully sent email to {job.to_email}")
                else:
                    job.status = EmailStatus.FAILED
                    stats["failed"] += 1
                    logger.error(
                        f"[EmailManager] Failed to send email to {job.to_email} "
                        f"after {job.attempts} attempts: {job.last_error}"
                    )
        
        # Count remaining pending
        with self.lock:
            stats["pending"] = sum(1 for j in self.queue if j.status == EmailStatus.PENDING)
        
        logger.info(
            f"[EmailManager] Batch complete: {stats['sent']} sent, "
            f"{stats['failed']} failed, {stats['pending']} pending"
        )
        
        return stats
    
    def _send_with_retry(
        self,
        job: EmailJob,
        send_func: Callable[[str, str, str, str], bool],
        timeout: Optional[float]
    ) -> bool:
        """
        Send an email with retry logic.
        
        Args:
            job: Email job to send
            send_func: Function to send email
            timeout: Timeout for rate limiting
            
        Returns:
            True if sent successfully, False otherwise
        """
        for attempt in range(self.max_retries):
            job.attempts = attempt + 1
            
            # Wait for rate limiter
            if not self._acquire_token(timeout=timeout):
                job.last_error = "Rate limiter timeout"
                logger.warning(
                    f"[EmailManager] Rate limiter timeout for {job.to_email} "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                continue
            
            # Try to send
            try:
                logger.debug(
                    f"[EmailManager] Sending to {job.to_email} "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                
                success = send_func(
                    job.to_email,
                    job.subject,
                    job.html_body,
                    job.text_body
                )
                
                if success:
                    return True
                
                # Failed but no exception - might be rate limited
                job.last_error = "Send function returned False"
                
            except Exception as e:
                job.last_error = str(e)
                logger.warning(
                    f"[EmailManager] Error sending to {job.to_email}: {e} "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
            
            # If not last attempt, wait with exponential backoff
            if attempt < self.max_retries - 1:
                delay = self._calculate_backoff_delay(attempt)
                logger.debug(
                    f"[EmailManager] Waiting {delay}s before retry "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                time.sleep(delay)
        
        return False
    
    def get_status(self) -> Dict[str, int]:
        """
        Get current queue status.
        
        Returns:
            Dictionary with counts by status
        """
        with self.lock:
            return {
                "pending": sum(1 for j in self.queue if j.status == EmailStatus.PENDING),
                "sending": sum(1 for j in self.queue if j.status == EmailStatus.SENDING),
                "sent": sum(1 for j in self.queue if j.status == EmailStatus.SENT),
                "failed": sum(1 for j in self.queue if j.status == EmailStatus.FAILED),
                "total": len(self.queue)
            }
    
    def get_failed_jobs(self) -> List[EmailJob]:
        """Get all failed email jobs."""
        with self.lock:
            return [j for j in self.queue if j.status == EmailStatus.FAILED]
    
    def clear_queue(self) -> None:
        """Clear all emails from the queue."""
        with self.lock:
            self.queue.clear()
        logger.info("[EmailManager] Queue cleared")
