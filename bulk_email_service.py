"""
Bulk Email Service

Handles sending emails to multiple recipients with progress tracking.
"""

import threading
from typing import Dict, List, Optional

from flask import current_app
from sqlalchemy.orm import Session

from bulk_email_models.bulk_email_job import BulkEmailJob
from email_providers.email_manager import EmailManager
from email_service import EmailService
from logging_config import get_logger

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

        from models_sql import User

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
            template_data={"term": term, "deadline": deadline},
            personal_message=personal_message,
        )

        # Start background thread to send emails
        thread = threading.Thread(
            target=BulkEmailService._send_emails_background,
            args=(job.id, recipients, personal_message, term, deadline),
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
        job_id: str,
        recipients: List[Dict],
        personal_message: Optional[str],
        term: Optional[str],
        deadline: Optional[str],
    ) -> None:
        """
        Background worker to send emails.

        Runs in separate thread to avoid blocking API requests.
        """
        # Import here to avoid circular dependencies
        from database_factory import get_database_service

        db_service = get_database_service()
        db = db_service.sqlite.get_session()  # type: ignore[attr-defined]

        try:
            # Get job
            job = BulkEmailJob.get_job(db, job_id)
            if not job:
                logger.error(f"[BulkEmailService] Job {job_id} not found")
                return

            # Create email manager with conservative rate limiting
            email_manager = EmailManager(
                rate=0.1,  # 1 email every 10 seconds
                max_retries=3,
                base_delay=5.0,
                max_delay=60.0,
            )

            # Queue all emails
            for recipient in recipients:
                email_manager.add_email(
                    to_email=recipient["email"],
                    subject=f"Reminder: Please submit your course data{f' for {term}' if term else ''}",
                    html_body=BulkEmailService._render_reminder_html(
                        recipient["name"], personal_message, term, deadline
                    ),
                    text_body=BulkEmailService._render_reminder_text(
                        recipient["name"], personal_message, term, deadline
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
            logger.error(f"[BulkEmailService] Job {job_id} failed: {e}", exc_info=True)

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
    ) -> str:
        """Render HTML email template for instructor reminder"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Course Data Reminder</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #0066cc;
            color: white;
            padding: 20px;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            background-color: #f9f9f9;
            padding: 30px;
            border-radius: 0 0 5px 5px;
        }}
        .personal-message {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
        }}
        .button {{
            display: inline-block;
            background-color: #0066cc;
            color: white;
            padding: 12px 30px;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Course Data Reminder</h1>
    </div>
    <div class="content">
        <p>Hello {instructor_name},</p>
        
        <p>This is a friendly reminder to submit your course data{f' for <strong>{term}</strong>' if term else ''}.</p>
        """

        if personal_message:
            html += f"""
        <div class="personal-message">
            <strong>Message from your program administrator:</strong>
            <p>{personal_message}</p>
        </div>
        """

        if deadline:
            html += f"""
        <p><strong>Deadline:</strong> {deadline}</p>
        """

        html += """
        <p>Please click the button below to submit your course information:</p>
        
        <a href="{{BASE_URL}}/courses/submit" class="button">Submit Course Data</a>
        
        <p>If you have any questions or need assistance, please don't hesitate to reach out to your program administrator.</p>
        
        <p>Thank you for your cooperation!</p>
    </div>
    <div class="footer">
        <p>This is an automated reminder from the Course Record Updater system.</p>
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

        text += "Please visit the following link to submit your course information:\n"
        text += "{{BASE_URL}}/courses/submit\n\n"
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
