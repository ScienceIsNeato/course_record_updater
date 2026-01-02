"""
Bulk Email Job Model

Tracks bulk email operations for progress monitoring and history.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Session

from src.utils.logging_config import get_logger
from src.models.models_sql import Base  # type: ignore[attr-defined]

logger = get_logger(__name__)


class BulkEmailJob(Base):  # type: ignore[misc,valid-type]
    """
    Represents a bulk email sending job.
    
    Tracks progress, status, and results of sending emails to multiple recipients.
    Used for instructor reminders, bulk invitations, etc.
    """
    
    __tablename__ = "bulk_email_jobs"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Job metadata
    job_type = Column(String(50), nullable=False)  # 'instructor_reminder', 'bulk_invitation', etc.
    created_by_user_id = Column(String(36), nullable=False)  # Admin who initiated
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Job configuration
    recipient_count = Column(Integer, nullable=False, default=0)
    recipients = Column(JSON, nullable=False)  # List of {email, name, metadata}
    template_data = Column(JSON, nullable=True)  # Template variables
    personal_message = Column(Text, nullable=True)  # Optional custom message
    
    # Progress tracking
    status = Column(
        String(20),
        nullable=False,
        default="pending"
    )  # pending, running, completed, failed, cancelled
    emails_sent = Column(Integer, nullable=False, default=0)
    emails_failed = Column(Integer, nullable=False, default=0)
    emails_pending = Column(Integer, nullable=False, default=0)
    
    # Results
    failed_recipients = Column(JSON, nullable=True)  # List of {email, error}
    error_message = Column(Text, nullable=True)  # Overall error if job failed
    
    def __repr__(self):
        return (
            f"<BulkEmailJob(id={self.id}, type={self.job_type}, "
            f"status={self.status}, sent={self.emails_sent}/{self.recipient_count})>"
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "job_type": self.job_type,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "recipient_count": self.recipient_count,
            "status": self.status,
            "emails_sent": self.emails_sent,
            "emails_failed": self.emails_failed,
            "emails_pending": self.emails_pending,
            "personal_message": self.personal_message,
            "failed_recipients": self.failed_recipients or [],
            "error_message": self.error_message,
            "progress_percentage": self._calculate_progress_percentage(),
        }
    
    def _calculate_progress_percentage(self) -> int:
        """Calculate progress as percentage"""
        if self.recipient_count == 0:
            return 0
        completed = self.emails_sent + self.emails_failed
        return int((completed / self.recipient_count) * 100)
    
    def update_progress(
        self,
        emails_sent: int,
        emails_failed: int,
        emails_pending: int,
        failed_recipients: Optional[List[Dict]] = None
    ) -> None:
        """Update job progress"""
        self.emails_sent = emails_sent  # type: ignore[assignment]
        self.emails_failed = emails_failed  # type: ignore[assignment]
        self.emails_pending = emails_pending  # type: ignore[assignment]
        
        if failed_recipients:
            self.failed_recipients = failed_recipients  # type: ignore[assignment]
        
        # Update status based on progress
        if self.status == "pending":
            self.status = "running"  # type: ignore[assignment]
            self.started_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        
        # Check if completed
        if emails_pending == 0 and self.status == "running":
            self.status = "completed"  # type: ignore[assignment]
            self.completed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
            logger.info(
                f"[BulkEmailJob] Job {self.id} completed: "
                f"{emails_sent} sent, {emails_failed} failed"
            )
    
    def mark_failed(self, error_message: str) -> None:
        """Mark job as failed"""
        self.status = "failed"  # type: ignore[assignment]
        self.error_message = error_message  # type: ignore[assignment]
        self.completed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        logger.error(f"[BulkEmailJob] Job {self.id} failed: {error_message}")
    
    def mark_cancelled(self) -> None:
        """Mark job as cancelled"""
        self.status = "cancelled"  # type: ignore[assignment]
        self.completed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        logger.info(f"[BulkEmailJob] Job {self.id} cancelled")
    
    @staticmethod
    def create_job(
        db: Session,
        job_type: str,
        created_by_user_id: str,
        recipients: List[Dict],
        template_data: Optional[Dict] = None,
        personal_message: Optional[str] = None
    ) -> "BulkEmailJob":
        """
        Create a new bulk email job.
        
        Args:
            db: Database session
            job_type: Type of job (e.g., 'instructor_reminder')
            created_by_user_id: ID of user who created the job
            recipients: List of recipient dictionaries
            template_data: Optional template data
            personal_message: Optional personal message
            
        Returns:
            Created BulkEmailJob instance
        """
        job = BulkEmailJob(
            job_type=job_type,
            created_by_user_id=created_by_user_id,
            recipient_count=len(recipients),
            recipients=recipients,
            template_data=template_data or {},
            personal_message=personal_message,
            emails_pending=len(recipients),
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        logger.info(
            f"[BulkEmailJob] Created job {job.id}: {job_type} "
            f"for {len(recipients)} recipients"
        )
        
        return job
    
    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional["BulkEmailJob"]:
        """Get a bulk email job by ID"""
        return db.query(BulkEmailJob).filter(BulkEmailJob.id == job_id).first()
    
    @staticmethod
    def get_recent_jobs(
        db: Session,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List["BulkEmailJob"]:
        """
        Get recent bulk email jobs.
        
        Args:
            db: Database session
            user_id: Optional filter by user ID
            limit: Maximum number of jobs to return
            
        Returns:
            List of BulkEmailJob instances
        """
        query = db.query(BulkEmailJob)
        
        if user_id:
            query = query.filter(BulkEmailJob.created_by_user_id == user_id)
        
        return (
            query.order_by(BulkEmailJob.created_at.desc())
            .limit(limit)
            .all()
        )
