"""
Bulk Email Service

Handles sending emails to multiple recipients with progress tracking.
"""

import threading
from typing import Dict, List, Optional

from flask import current_app
from sqlalchemy.orm import Session

from src.bulk_email_models.bulk_email_job import BulkEmailJob
from src.email_providers.email_manager import EmailManager
from .email_service import EmailService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BulkEmailService:
    """
    Service for sending bulk emails with progress tracking.

    Uses EmailManager for rate limiting and retry logic.
    Updates BulkEmailJob for progress monitoring.
    """

    @staticmethod
    def send_instructor_reminders(
        db: Session,
        instructor_ids: List[str],
        created_by_user_id: str,
        personal_message: Optional[str] = None,
        term: Optional[str] = None,
        deadline: Optional[str] = None,
        course_id: Optional[str] = None,
    ) -> str:
        """
        Send reminder emails to multiple instructors.

        Args:
            db: Database session
            instructor_ids: List of instructor user IDs
            created_by_user_id: ID of admin sending reminders
            personal_message: Optional personal message to include
            term: Optional term/semester context
            deadline: Optional deadline date

        Returns:
            Job ID for tracking progress
        """
        # Fetch instructor details from database
        from sqlalchemy import select

        from src.models.models_sql import User

        recipients = []
        for instructor_id in instructor_ids:
            # Query user by ID
            user = db.execute(
                select(User).where(User.id == instructor_id)
            ).scalar_one_or_none()

            if not user:
                logger.warning(
                    f"[BulkEmailService] Instructor {instructor_id} not found, skipping"
                )
                continue

            if not user.email:
                logger.warning(
                    f"[BulkEmailService] Instructor {instructor_id} has no email, skipping"
                )
                continue

            # Build full name from first_name and last_name
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            if not full_name:
                full_name = str(user.email)  # Fallback to email if no name

            recipients.append(
                {
                    "user_id": user.id,
                    "email": user.email,
                    "name": full_name,
                }
            )

        # Create job record
        job = BulkEmailJob.create_job(
            db=db,
            job_type="instructor_reminder",
            created_by_user_id=created_by_user_id,
            recipients=recipients,
            template_data={"term": term, "deadline": deadline, "course_id": course_id},
            personal_message=personal_message,
        )

        # Start background thread to send emails
        # Pass Flask app for application context in background thread
        # pylint: disable=protected-access
        thread = threading.Thread(
            target=BulkEmailService._send_emails_background,
            args=(
                current_app._get_current_object(),  # type: ignore[attr-defined]
                job.id,
                recipients,
                personal_message,
                term,
                deadline,
                course_id,
            ),
            daemon=True,
        )
        thread.start()

        logger.info(
            f"[BulkEmailService] Started background job {job.id} "
            f"for {len(recipients)} instructors"
        )

        return str(job.id)

    @staticmethod
    def _send_emails_background(
        app,
        job_id: str,
        recipients: List[Dict],
        personal_message: Optional[str],
        term: Optional[str],
        deadline: Optional[str],
        course_id: Optional[str] = None,
    ) -> None:
        """
        Background worker to send emails.

        Runs in separate thread to avoid blocking API requests.
        Requires Flask app for application context.
        """
        # Wrap entire execution in Flask application context
        with app.app_context():
            # Import here to avoid circular dependencies
            from src.database.database_factory import get_database_service

            db_service = get_database_service()
            db = db_service.sqlite.get_session()  # type: ignore[attr-defined]

            try:
                # Get job
                job = BulkEmailJob.get_job(db, job_id)
                if not job:
                    logger.error(f"[BulkEmailService] Job {job_id} not found")
                    return

                # Get BASE_URL from config
                from src.utils.constants import DEFAULT_BASE_URL

                base_url = current_app.config.get("BASE_URL", DEFAULT_BASE_URL)

                # Create email manager with reasonable rate limit
                # EmailManager has exponential backoff to handle provider-specific rate limit errors
                # Rate is in emails/second (2.0 = 2 emails per second)
                # Conservative rate to avoid overwhelming providers while maintaining reasonable speed
                email_manager = EmailManager(
                    rate=2.0,  # 2 emails/sec (0.5s between emails); conservative limit
                    max_retries=3,
                    base_delay=1.0,  # Start with 1s backoff on errors
                    max_delay=30.0,  # Cap backoff at 30s
                )

                # Queue all emails
                from src.utils.constants import EMAIL_SUBJECT_REMINDER_PREFIX

                for recipient in recipients:
                    subject_suffix = f" for {term}" if term else ""
                    email_manager.add_email(
                        to_email=recipient["email"],
                        subject=f"{EMAIL_SUBJECT_REMINDER_PREFIX}{subject_suffix}",
                        html_body=BulkEmailService._render_reminder_html(
                            recipient["name"],
                            personal_message,
                            term,
                            deadline,
                            base_url,
                            course_id,
                        ),
                        text_body=BulkEmailService._render_reminder_text(
                            recipient["name"],
                            personal_message,
                            term,
                            deadline,
                            base_url,
                            course_id,
                        ),
                        metadata={"user_id": recipient.get("user_id")},
                    )

                # Get email service instance
                email_service = EmailService()

                # Define send function that uses EmailService
                def send_email(
                    to_email: str, subject: str, html_body: str, text_body: str
                ) -> bool:
                    """Send email via EmailService"""
                    # pylint: disable=protected-access
                    return email_service._send_email(
                        to_email, subject, html_body, text_body
                    )

                # Send all emails with progress updates
                def update_progress():
                    """Update job progress in database"""
                    status = email_manager.get_status()

                    failed_jobs = email_manager.get_failed_jobs()
                    failed_recipients = [
                        {
                            "email": job.to_email,
                            "error": job.last_error,
                            "attempts": job.attempts,
                        }
                        for job in failed_jobs
                    ]

                    job.update_progress(
                        emails_sent=status["sent"],
                        emails_failed=status["failed"],
                        emails_pending=status["pending"],
                        failed_recipients=failed_recipients,
                    )
                    db.commit()

                # Send emails and update progress periodically
                stats = email_manager.send_all(send_email, timeout=60)

                # Final progress update
                update_progress()

                logger.info(
                    f"[BulkEmailService] Job {job_id} completed: "
                    f"{stats['sent']} sent, {stats['failed']} failed"
                )

            except Exception as e:  # pylint: disable=broad-except
                logger.error(
                    f"[BulkEmailService] Job {job_id} failed: {e}", exc_info=True
                )

                # Mark job as failed
                job = BulkEmailJob.get_job(db, job_id)
                if job:
                    job.mark_failed(str(e))
                    db.commit()

            finally:
                db.close()

    @staticmethod
    def _render_reminder_html(
        instructor_name: str,
        personal_message: Optional[str],
        term: Optional[str],
        deadline: Optional[str],
        base_url: str,
        course_id: Optional[str] = None,
    ) -> str:
        """Render HTML email template for instructor reminder"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Course Data Reminder</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #27ae60; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background: #f9f9f9; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #27ae60; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
        .personal-message {{
            background: #ecf0f1;
            padding: 15px;
            border-left: 4px solid #3498db;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">Course Data Reminder</h1>
        </div>
        <div class="content">
            <p>Hello {instructor_name},</p>
            
            <p>This is a friendly reminder to submit your course data{f' for <strong>{term}</strong>' if term else ''}.</p>
        """

        if personal_message:
            # Escape HTML to prevent XSS attacks
            from html import escape

            escaped_message = escape(personal_message)
            html += f"""
            <div class="personal-message">
                <p><strong>Message from your program administrator:</strong></p>
                <p style="font-style: italic;">"{escaped_message}"</p>
            </div>
        """

        if deadline:
            html += f"""
            <p><strong>Deadline:</strong> {deadline}</p>
        """

        html += """
            <p>Please click the button below to submit your course information:</p>
            """

        # Build the link with course-specific redirect if available
        if course_id:
            # URL encode the next parameter to avoid double ? in URL
            from urllib.parse import quote

            next_url = quote(f"/assessments?course={course_id}")
            link = f"{base_url}/reminder-login?next={next_url}"
            button_text = "Enter Course Assessments"
        else:
            link = f"{base_url}/reminder-login"
            button_text = "Go to Dashboard"

        html += f"""
            <a href="{link}" class="button">{button_text}</a>
            
            <p>If you have any questions or need assistance, please don't hesitate to reach out to your program administrator.</p>
            
            <p>Thank you for your cooperation!</p>
        </div>
        <div class="footer">
            <p>This is an automated reminder from the Course Record Updater system.</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    @staticmethod
    def _render_reminder_text(
        instructor_name: str,
        personal_message: Optional[str],
        term: Optional[str],
        deadline: Optional[str],
        base_url: str,
        course_id: Optional[str] = None,
    ) -> str:
        """Render plain text email template for instructor reminder"""
        text = f"Hello {instructor_name},\n\n"
        text += "This is a friendly reminder to submit your course data"

        if term:
            text += f" for {term}"

        text += ".\n\n"

        if personal_message:
            text += f"Message from your program administrator:\n{personal_message}\n\n"

        if deadline:
            text += f"Deadline: {deadline}\n\n"

        # Build the link with course-specific redirect if available
        if course_id:
            link = f"{base_url}/reminder-login?next=/assessments?course={course_id}"
            text += (
                "Please visit the following link to enter your course assessments:\n"
            )
        else:
            link = f"{base_url}/reminder-login"
            text += "Please visit the following link to access your dashboard:\n"

        text += f"{link}\n\n"
        text += "If you have any questions or need assistance, please don't hesitate to reach out to your program administrator.\n\n"
        text += "Thank you for your cooperation!\n\n"
        text += "---\n"
        text += "This is an automated reminder from the Course Record Updater system."

        return text

    @staticmethod
    def get_job_status(db: Session, job_id: str) -> Optional[Dict]:
        """
        Get status of a bulk email job.

        Args:
            db: Database session
            job_id: Job ID

        Returns:
            Job status dictionary or None if not found
        """
        job = BulkEmailJob.get_job(db, job_id)
        if not job:
            return None

        return job.to_dict()

    @staticmethod
    def get_recent_jobs(
        db: Session, user_id: Optional[str] = None, limit: int = 50
    ) -> List[Dict]:
        """
        Get recent bulk email jobs.

        Args:
            db: Database session
            user_id: Optional filter by user ID
            limit: Maximum number of jobs to return

        Returns:
            List of job status dictionaries
        """
        jobs = BulkEmailJob.get_recent_jobs(db, user_id, limit)
        return [job.to_dict() for job in jobs]  # pylint: disable=unnecessary-lambda
