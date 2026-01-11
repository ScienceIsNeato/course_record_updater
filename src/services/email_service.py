"""
Email Service

Provides email functionality for authentication system including:
- Email verification for registration
- Password reset emails
- User invitation emails
- Welcome emails

Features:
- Template-based emails with HTML and text versions
- Secure token embedding
- Development mode with console output
- Production-ready SMTP configuration
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional
from urllib.parse import urljoin

from flask import Flask, current_app

# Import email provider infrastructure
from src.email_providers import create_email_provider
from src.email_providers.base_provider import EmailProvider
from src.email_providers.brevo_provider import BrevoProvider

# Import constants to avoid duplication
from src.utils.constants import DEFAULT_BASE_URL

# Import centralized logging
from src.utils.logging_config import get_logger
from src.utils.time_utils import get_current_time

# Get standardized logger
logger = get_logger(__name__)

# Email configuration
DEFAULT_FROM_EMAIL = "noreply@courserecord.app"
DEFAULT_FROM_NAME = "LoopCloser"


class EmailServiceError(Exception):
    """Raised when email service encounters an error"""


class EmailService:
    """
    Comprehensive email service for authentication flows

    Handles template-based emails with secure token embedding

    CRITICAL SECURITY: Protects real institution email domains from being used in testing
    """

    # Protected email domains - NEVER send emails to these in testing/development
    PROTECTED_DOMAINS = [
        "cei.test",
        "coastaledu.org",
        "coastal.edu",
        "coastalcarolina.edu",
        # Add other protected domains as needed
    ]

    _last_error_message: Optional[str] = None

    @staticmethod
    def _is_protected_email(email: Optional[str]) -> bool:
        """
        Check if email address is from a protected domain (e.g., production institutions)

        Args:
            email: Email address to check (can be None)

        Returns:
            True if email is from protected domain, False otherwise
        """
        if not email or "@" not in email:
            return False

        # Handle malformed emails like "@mocku.test"
        email_parts = email.split("@")
        if len(email_parts) != 2 or not email_parts[0]:
            return False

        domain = email.split("@")[1].lower()

        # Check against protected domains
        for protected_domain in EmailService.PROTECTED_DOMAINS:
            if domain == protected_domain.lower() or domain.endswith(
                "." + protected_domain.lower()
            ):
                return True

        return False

    @staticmethod
    def configure_app(app: Flask) -> None:
        """
        Configure Flask app with email settings

        Args:
            app: Flask application instance
        """
        logger.info("[Email Service] Configuring email settings")

        # Email server configuration
        app.config.setdefault("MAIL_SERVER", os.getenv("MAIL_SERVER", "localhost"))
        app.config.setdefault("MAIL_PORT", int(os.getenv("MAIL_PORT", "587")))
        app.config.setdefault(
            "MAIL_USE_TLS", os.getenv("MAIL_USE_TLS", "true").lower() == "true"
        )
        app.config.setdefault(
            "MAIL_USE_SSL", os.getenv("MAIL_USE_SSL", "false").lower() == "true"
        )
        app.config.setdefault("MAIL_USERNAME", os.getenv("MAIL_USERNAME"))
        app.config.setdefault("MAIL_PASSWORD", os.getenv("MAIL_PASSWORD"))

        # Email content configuration
        app.config.setdefault(
            "MAIL_DEFAULT_SENDER", os.getenv("MAIL_DEFAULT_SENDER", DEFAULT_FROM_EMAIL)
        )
        app.config.setdefault(
            "MAIL_DEFAULT_SENDER_NAME",
            os.getenv("MAIL_DEFAULT_SENDER_NAME", DEFAULT_FROM_NAME),
        )

        # Base URL for email links
        app.config.setdefault("BASE_URL", os.getenv("BASE_URL", DEFAULT_BASE_URL))

        # Development mode
        app.config.setdefault(
            "MAIL_SUPPRESS_SEND",
            os.getenv("MAIL_SUPPRESS_SEND", "false").lower() == "true",
        )

        logger.info("[Email Service] Email configuration complete")

    @staticmethod
    def send_verification_email(
        email: str, verification_token: str, user_name: str
    ) -> bool:
        """
        Send email verification email to new user

        Args:
            email: User's email address
            verification_token: Secure verification token
            user_name: User's display name

        Returns:
            True if email sent successfully, False otherwise
        """
        logger.info(
            f"[Email Service] Sending verification email to {logger.sanitize(email)}"
        )

        verification_url = EmailService._build_verification_url(verification_token)

        subject = "Verify your LoopCloser account"

        html_body = EmailService._render_verification_email_html(
            user_name=user_name, verification_url=verification_url, email=email
        )

        text_body = EmailService._render_verification_email_text(
            user_name=user_name, verification_url=verification_url, email=email
        )

        return EmailService._send_email(
            to_email=email, subject=subject, html_body=html_body, text_body=text_body
        )

    @staticmethod
    def send_password_reset_email(email: str, reset_token: str, user_name: str) -> bool:
        """
        Send password reset email to user

        Args:
            email: User's email address
            reset_token: Secure reset token
            user_name: User's display name

        Returns:
            True if email sent successfully, False otherwise
        """
        logger.info(
            f"[Email Service] Sending password reset email to {logger.sanitize(email)}"
        )

        reset_url = EmailService._build_password_reset_url(reset_token)

        subject = "Reset your LoopCloser password"

        html_body = EmailService._render_password_reset_email_html(
            user_name=user_name, reset_url=reset_url, email=email
        )

        text_body = EmailService._render_password_reset_email_text(
            user_name=user_name, reset_url=reset_url, email=email
        )

        return EmailService._send_email(
            to_email=email, subject=subject, html_body=html_body, text_body=text_body
        )

    @staticmethod
    def send_password_reset_confirmation_email(email: str, user_name: str) -> bool:
        """
        Send password reset confirmation email

        Args:
            email: User's email address
            user_name: User's display name

        Returns:
            True if email sent successfully
        """
        subject = "Password Reset Successful"

        html_body = EmailService._render_password_reset_confirmation_email_html(
            user_name=user_name, email=email
        )

        text_body = EmailService._render_password_reset_confirmation_email_text(
            user_name=user_name, email=email
        )

        return EmailService._send_email(
            to_email=email, subject=subject, html_body=html_body, text_body=text_body
        )

    @staticmethod
    def send_invitation_email(
        email: str,
        invitation_token: str,
        inviter_name: str,
        institution_name: str,
        role: str,
        personal_message: Optional[str] = None,
    ) -> bool:
        """
        Send user invitation email

        Args:
            email: Invited user's email address
            invitation_token: Secure invitation token
            inviter_name: Name of person sending invitation
            institution_name: Name of institution
            role: Role being invited to
            personal_message: Optional personal message from inviter

        Returns:
            True if email sent successfully, False otherwise
        """
        logger.info(
            f"[Email Service] Sending invitation email to {logger.sanitize(email)}"
        )

        invitation_url = EmailService._build_invitation_url(invitation_token)

        subject = f"You're invited to join {institution_name} on LoopCloser"

        html_body = EmailService._render_invitation_email_html(
            email=email,
            invitation_url=invitation_url,
            inviter_name=inviter_name,
            institution_name=institution_name,
            role=role,
            personal_message=personal_message,
        )

        text_body = EmailService._render_invitation_email_text(
            email=email,
            invitation_url=invitation_url,
            inviter_name=inviter_name,
            institution_name=institution_name,
            role=role,
            personal_message=personal_message,
        )

        return EmailService._send_email(
            to_email=email, subject=subject, html_body=html_body, text_body=text_body
        )

    @staticmethod
    def send_welcome_email(email: str, user_name: str, institution_name: str) -> bool:
        """
        Send welcome email to newly verified user

        Args:
            email: User's email address
            user_name: User's display name
            institution_name: Name of institution

        Returns:
            True if email sent successfully, False otherwise
        """
        logger.info(
            f"[Email Service] Sending welcome email to {logger.sanitize(email)}"
        )

        dashboard_url = EmailService._build_dashboard_url()

        subject = f"Welcome to LoopCloser, {user_name}!"

        html_body = EmailService._render_welcome_email_html(
            user_name=user_name,
            institution_name=institution_name,
            dashboard_url=dashboard_url,
        )

        text_body = EmailService._render_welcome_email_text(
            user_name=user_name,
            institution_name=institution_name,
            dashboard_url=dashboard_url,
        )

        return EmailService._send_email(
            to_email=email, subject=subject, html_body=html_body, text_body=text_body
        )

    @staticmethod
    def send_course_assessment_reminder(
        to_email: str,
        instructor_name: str,
        course_display: str,
        admin_name: str,
        institution_name: str,
        assessment_url: str,
    ) -> bool:
        """
        Send course-specific assessment reminder to instructor

        Args:
            to_email: Instructor's email address
            instructor_name: Instructor's display name
            course_display: Course number and title (e.g., "BIOL-228 - Course BIOL-228")
            admin_name: Name of admin sending reminder
            institution_name: Name of institution
            assessment_url: Direct URL to assessment page for this course

        Returns:
            True if email sent successfully, False otherwise
        """
        logger.info(
            f"[Email Service] Sending course assessment reminder to {logger.sanitize(to_email)} for {course_display}"
        )

        subject = f"Reminder: Complete Assessment for {course_display}"

        html_body = EmailService._render_course_reminder_html(
            instructor_name=instructor_name,
            course_display=course_display,
            admin_name=admin_name,
            institution_name=institution_name,
            assessment_url=assessment_url,
        )

        text_body = EmailService._render_course_reminder_text(
            instructor_name=instructor_name,
            course_display=course_display,
            admin_name=admin_name,
            institution_name=institution_name,
            assessment_url=assessment_url,
        )

        return EmailService._send_email(
            to_email=to_email, subject=subject, html_body=html_body, text_body=text_body
        )

    # Private helper methods

    @staticmethod
    def _get_email_provider() -> EmailProvider:
        """
        Get configured email provider instance

        Returns:
            Configured EmailProvider (determined by environment)
        """
        # Let factory auto-detect provider and load config from environment
        # Provider selection based on ENV variable:
        #   - test/e2e -> ethereal (IMAP verification)
        #   - development/production -> brevo (real email)
        return create_email_provider()

    @staticmethod
    def _send_email(
        to_email: str, subject: str, html_body: str, text_body: str
    ) -> bool:
        """Send email using configured email provider"""
        provider = None
        try:
            EmailService._last_error_message = None
            # CRITICAL PROTECTION: Block protected domains in non-production environments
            is_production = current_app.config.get(
                "ENV"
            ) == "production" or current_app.config.get("PRODUCTION", False)

            if not is_production and EmailService._is_protected_email(to_email):
                error_message = (
                    f"Cannot send emails to protected domain ({to_email.split('@')[1] if '@' in to_email else to_email}) "
                    f"in non-production environment"
                )
                logger.error(
                    f"[Email Service] BLOCKED: Attempted to send email to protected domain in "
                    f"{current_app.config.get('ENV', 'development')} environment: {to_email}"
                )
                raise EmailServiceError(error_message)

            # WHITELIST PROTECTION: In local/test environments, only allow whitelisted emails
            from src.email_providers import get_email_whitelist

            whitelist = get_email_whitelist()
            if not whitelist.is_allowed(to_email):
                blocked_reason = whitelist.get_blocked_reason(to_email)
                logger.error(
                    f"[Email Service] BLOCKED by whitelist: {to_email} in "
                    f"{current_app.config.get('ENV', 'local')} environment"
                )
                raise EmailServiceError(blocked_reason)

            # Get email provider (console or gmail based on config)
            provider = EmailService._get_email_provider()

            # Send email via provider
            success = provider.send_email(to_email, subject, html_body, text_body)

            EmailService._log_email_preview(
                to_email=to_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                status="SENT" if success else "FAILED",
            )

            if success:
                logger.info(
                    f"[Email Service] Email sent successfully to {logger.sanitize(to_email)}"
                )
                EmailService._last_error_message = None
            else:
                logger.error(
                    f"[Email Service] Provider reported failure sending to {logger.sanitize(to_email)}"
                )
                EmailService._last_error_message = (
                    f"Provider reported failure sending to {to_email}"
                )
                EmailService._maybe_send_via_ethereal_fallback(
                    provider, to_email, subject, html_body, text_body
                )

            return success

        except EmailServiceError as exc:
            EmailService._log_email_preview(
                to_email=to_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                status="BLOCKED",
                error_message=str(exc),
            )
            # Re-raise EmailServiceError (protection errors) to caller
            raise
        except Exception as e:
            logger.error(
                f"[Email Service] Failed to send email to {logger.sanitize(to_email)}: {e}"
            )
            EmailService._log_email_preview(
                to_email=to_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                status="FAILED",
                error_message=str(e),
            )
            EmailService._last_error_message = str(e)
            EmailService._maybe_send_via_ethereal_fallback(
                provider, to_email, subject, html_body, text_body
            )
            return False

    @staticmethod
    def _get_email_log_path() -> Path:
        """
        Determine the log file destination for email previews.
        """
        try:
            cfg: "Mapping[str, Any]" = current_app.config
        except RuntimeError:
            cfg = {}

        log_override = cfg.get("EMAIL_LOG_PATH")
        if log_override:
            return Path(log_override)

        log_dir = cfg.get("LOG_DIR")
        if log_dir:
            return Path(log_dir) / "email.log"

        return Path("logs") / "email.log"

    @staticmethod
    def _truncate_preview(content: Optional[str], limit: int = 400) -> str:
        """
        Trim preview text so log entries stay compact.
        """
        if not content:
            return ""

        normalized = content.replace("\r", "").strip()
        if len(normalized) <= limit:
            return normalized

        return normalized[: limit - 3] + "..."

    @staticmethod
    def _log_email_preview(
        *,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Append a human-readable preview of the email to logs/email.log (or configured path).
        """
        try:
            log_path = EmailService._get_email_log_path()
            log_path.parent.mkdir(parents=True, exist_ok=True)

            timestamp = get_current_time().isoformat()
            sanitized_to = logger.sanitize(to_email, 120)
            sanitized_subject = logger.sanitize(subject, 200)
            error_text = logger.sanitize(error_message, 200) if error_message else None
            text_preview = EmailService._truncate_preview(text_body)
            html_preview = EmailService._truncate_preview(html_body)

            lines = [
                "",
                f"=== Email {status} @ {timestamp} ===",
                f"To: {sanitized_to}",
                f"Subject: {sanitized_subject}",
            ]

            if error_text:
                lines.append(f"Error: {error_text}")

            if text_preview:
                lines.append("Text Preview:")
                lines.append(text_preview)

            if html_preview:
                lines.append("HTML Preview:")
                lines.append(html_preview)

            lines.append("---")

            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write("\n".join(lines) + "\n")
        except Exception as log_error:  # noqa: BLE001
            logger.debug(
                "[Email Service] Unable to write email preview log: %s", log_error
            )

    @staticmethod
    def _maybe_send_via_ethereal_fallback(
        provider: Optional[EmailProvider],
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> None:
        """
        When Brevo fails in non-production environments, retry via Ethereal
        so local/E2E runs still have an inspectable copy of the email.
        """
        try:
            env = current_app.config.get("ENV", "development")
            is_production = env == "production"
        except RuntimeError:
            env = "development"
            is_production = False

        if is_production or not isinstance(provider, BrevoProvider):
            return

        ethereal_user = os.getenv("ETHEREAL_USER")
        if not ethereal_user:
            logger.warning(
                "[Email Service] Ethereal fallback requested but ETHEREAL_USER is not configured"
            )
            return

        try:
            logger.warning(
                "[Email Service] Brevo delivery failed in %s, retrying via Ethereal",
                env,
            )
            fallback_provider = create_email_provider("ethereal")
            fallback_success = fallback_provider.send_email(
                to_email, subject, html_body, text_body
            )
            EmailService._log_email_preview(
                to_email=to_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                status="FALLBACK",
                error_message=(
                    "Delivered to Ethereal after Brevo failure"
                    if fallback_success
                    else "Ethereal fallback also failed"
                ),
            )
            if fallback_success:
                logger.warning(
                    "[Email Service] Ethereal fallback delivered the message"
                )
            else:
                logger.error("[Email Service] Ethereal fallback failed as well")
        except Exception as fallback_error:
            logger.error(
                "[Email Service] Ethereal fallback threw an exception: %s",
                fallback_error,
            )

    @staticmethod
    def pop_last_error_message() -> Optional[str]:
        """
        Return the last captured error message (if any) and clear it.
        """
        message = EmailService._last_error_message
        EmailService._last_error_message = None
        return message

    @staticmethod
    def _build_verification_url(token: str) -> str:
        """
        Build email verification URL

        Returns API endpoint that frontend JavaScript will handle
        """
        base_url = current_app.config.get("BASE_URL", DEFAULT_BASE_URL)
        return urljoin(base_url, f"/api/auth/verify-email/{token}")

    @staticmethod
    def _build_password_reset_url(token: str) -> str:
        """
        Build password reset URL

        Returns web route that displays password reset form
        """
        base_url = current_app.config.get("BASE_URL", DEFAULT_BASE_URL)
        return urljoin(base_url, f"/reset-password/{token}")

    @staticmethod
    def _build_invitation_url(token: str) -> str:
        """Build invitation acceptance URL"""
        base_url = current_app.config.get("BASE_URL", DEFAULT_BASE_URL)
        return urljoin(base_url, f"/register/accept/{token}")

    @staticmethod
    def _build_dashboard_url() -> str:
        """Build dashboard URL"""
        base_url = current_app.config.get("BASE_URL", DEFAULT_BASE_URL)
        return urljoin(base_url, "/dashboard")

    # Email template methods

    @staticmethod
    def _render_verification_email_html(
        user_name: str, verification_url: str, email: str
    ) -> str:
        """Render HTML verification email template"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Verify your email</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background: #f9f9f9; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #3498db; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>LoopCloser</h1>
        </div>
        <div class="content">
            <h2>Welcome, {user_name}!</h2>
            <p>Thank you for registering with LoopCloser. To complete your registration, please verify your email address by clicking the button below:</p>
            
            <p style="text-align: center;">
                <a href="{verification_url}" class="button">Verify Email Address</a>
            </p>
            
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p><a href="{verification_url}">{verification_url}</a></p>
            
            <p><strong>Important:</strong> This verification link will expire in 24 hours for security reasons.</p>
            
            <p>If you didn't create this account, you can safely ignore this email.</p>
        </div>
        <div class="footer">
            <p>This email was sent to {email}</p>
            <p>&copy; {get_current_time().year} LoopCloser. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """

    @staticmethod
    def _render_verification_email_text(
        user_name: str, verification_url: str, email: str
    ) -> str:
        """Render text verification email template"""
        return f"""
LoopCloser - Email Verification

Welcome, {user_name}!

Thank you for registering with LoopCloser. To complete your registration, please verify your email address by visiting this link:

{verification_url}

Important: This verification link will expire in 24 hours for security reasons.

If you didn't create this account, you can safely ignore this email.

This email was sent to {email}

© {get_current_time().year} LoopCloser. All rights reserved.
        """

    @staticmethod
    def _render_password_reset_email_html(
        user_name: str, reset_url: str, email: str
    ) -> str:
        """Render HTML password reset email template"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reset your password</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #e74c3c; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background: #f9f9f9; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #e74c3c; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset</h1>
        </div>
        <div class="content">
            <h2>Hello, {user_name}</h2>
            <p>We received a request to reset your password for your LoopCloser account.</p>
            
            <p style="text-align: center;">
                <a href="{reset_url}" class="button">Reset Password</a>
            </p>
            
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p><a href="{reset_url}">{reset_url}</a></p>
            
            <p><strong>Important:</strong> This reset link will expire in 1 hour for security reasons.</p>
            
            <p>If you didn't request this password reset, you can safely ignore this email. Your password will not be changed.</p>
        </div>
        <div class="footer">
            <p>This email was sent to {email}</p>
            <p>&copy; {get_current_time().year} LoopCloser. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """

    @staticmethod
    def _render_password_reset_email_text(
        user_name: str, reset_url: str, email: str
    ) -> str:
        """Render text password reset email template"""
        return f"""
LoopCloser - Password Reset

Hello, {user_name}

We received a request to reset your password for your LoopCloser account.

To reset your password, visit this link:

{reset_url}

Important: This reset link will expire in 1 hour for security reasons.

If you didn't request this password reset, you can safely ignore this email. Your password will not be changed.

This email was sent to {email}

© {get_current_time().year} LoopCloser. All rights reserved.
        """

    @staticmethod
    def _render_password_reset_confirmation_email_html(
        user_name: str, email: str
    ) -> str:
        """Render HTML password reset confirmation email template"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Password Reset Successful</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #27ae60; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background: #f9f9f9; }}
        .success-icon {{ font-size: 48px; color: #27ae60; text-align: center; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset Successful</h1>
        </div>
        <div class="content">
            <div class="success-icon">✅</div>
            <p>Hello, {user_name}</p>
            <p>Your password has been successfully reset for your LoopCloser account.</p>
            <p><strong>Account:</strong> {email}</p>
            <p><strong>Reset completed:</strong> {get_current_time().strftime('%Y-%m-%d at %H:%M UTC')}</p>
            
            <h3>Security Information:</h3>
            <ul>
                <li>Your password has been securely updated</li>
                <li>All failed login attempts have been cleared</li>
                <li>You can now log in with your new password</li>
            </ul>
            
            <p><strong>If you did not perform this password reset:</strong></p>
            <p>Please contact support immediately as your account may have been compromised.</p>
            
            <p>For security reasons, we recommend:</p>
            <ul>
                <li>Using a strong, unique password</li>
                <li>Not sharing your login credentials</li>
                <li>Logging out when finished using the system</li>
            </ul>
        </div>
        <div class="footer">
            <p>This email was sent to {email}</p>
            <p>© {get_current_time().year} LoopCloser. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """

    @staticmethod
    def _render_password_reset_confirmation_email_text(
        user_name: str, email: str
    ) -> str:
        """Render text password reset confirmation email template"""
        return f"""
LoopCloser - Password Reset Successful

Hello, {user_name}

Your password has been successfully reset for your LoopCloser account.

Account: {email}
Reset completed: {get_current_time().strftime('%Y-%m-%d at %H:%M UTC')}

Security Information:
- Your password has been securely updated
- All failed login attempts have been cleared  
- You can now log in with your new password

IF YOU DID NOT PERFORM THIS PASSWORD RESET:
Please contact support immediately as your account may have been compromised.

For security reasons, we recommend:
- Using a strong, unique password
- Not sharing your login credentials
- Logging out when finished using the system

This email was sent to {email}

© {get_current_time().year} LoopCloser. All rights reserved.
        """

    @staticmethod
    def _render_invitation_email_html(
        email: str,
        invitation_url: str,
        inviter_name: str,
        institution_name: str,
        role: str,
        personal_message: Optional[str] = None,
    ) -> str:
        """Render HTML invitation email template"""
        personal_message_html = ""
        if personal_message:
            personal_message_html = f"""
            <div style="background: #ecf0f1; padding: 15px; border-left: 4px solid #3498db; margin: 20px 0;">
                <p><strong>Personal message from {inviter_name}:</strong></p>
                <p style="font-style: italic;">"{personal_message}"</p>
            </div>
            """

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>You're invited!</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #27ae60; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background: #f9f9f9; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #27ae60; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>You're Invited!</h1>
        </div>
        <div class="content">
            <h2>Join {institution_name}</h2>
            <p>{inviter_name} has invited you to join <strong>{institution_name}</strong> as a <strong>{role.replace('_', ' ').title()}</strong> on LoopCloser.</p>
            
            {personal_message_html}
            
            <p style="text-align: center;">
                <a href="{invitation_url}" class="button">Accept Invitation</a>
            </p>
            
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p><a href="{invitation_url}">{invitation_url}</a></p>
            
            <p><strong>Important:</strong> This invitation will expire in 7 days.</p>
            
            <p>If you're not sure why you received this invitation, please contact {inviter_name} directly.</p>
        </div>
        <div class="footer">
            <p>This email was sent to {email}</p>
            <p>&copy; {get_current_time().year} LoopCloser. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """

    @staticmethod
    def _render_invitation_email_text(
        email: str,
        invitation_url: str,
        inviter_name: str,
        institution_name: str,
        role: str,
        personal_message: Optional[str] = None,
    ) -> str:
        """Render text invitation email template"""
        personal_message_text = ""
        if personal_message:
            personal_message_text = f"""
Personal message from {inviter_name}:
"{personal_message}"

"""

        return f"""
LoopCloser - You're Invited!

Join {institution_name}

{inviter_name} has invited you to join {institution_name} as a {role.replace('_', ' ').title()} on LoopCloser.

{personal_message_text}To accept this invitation, visit:

{invitation_url}

Important: This invitation will expire in 7 days.

If you're not sure why you received this invitation, please contact {inviter_name} directly.

This email was sent to {email}

© {get_current_time().year} LoopCloser. All rights reserved.
        """

    @staticmethod
    def _render_welcome_email_html(
        user_name: str, institution_name: str, dashboard_url: str
    ) -> str:
        """Render HTML welcome email template"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Welcome!</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #9b59b6; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background: #f9f9f9; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #9b59b6; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to LoopCloser!</h1>
        </div>
        <div class="content">
            <h2>Hello, {user_name}!</h2>
            <p>Your email has been verified and your account is now active. Welcome to <strong>{institution_name}</strong> on LoopCloser!</p>
            
            <p>You can now access your dashboard to:</p>
            <ul>
                <li>Manage your courses and sections</li>
                <li>Track student outcomes and assessments</li>
                <li>Generate reports and analytics</li>
            </ul>
            
            <p style="text-align: center;">
                <a href="{dashboard_url}" class="button">Go to Dashboard</a>
            </p>
            
            <p>If you have any questions or need help getting started, don't hesitate to reach out to your institution administrator.</p>
            
            <p>We're excited to have you on board!</p>
        </div>
        <div class="footer">
            <p>&copy; {get_current_time().year} LoopCloser. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """

    @staticmethod
    def _render_welcome_email_text(
        user_name: str, institution_name: str, dashboard_url: str
    ) -> str:
        """Render text welcome email template"""
        return f"""
LoopCloser - Welcome!

Hello, {user_name}!

Your email has been verified and your account is now active. Welcome to {institution_name} on LoopCloser!

You can now access your dashboard to:
- Manage your courses and sections
- Track student outcomes and assessments
- Generate reports and analytics

Visit your dashboard: {dashboard_url}

If you have any questions or need help getting started, don't hesitate to reach out to your institution administrator.

We're excited to have you on board!

© {get_current_time().year} LoopCloser. All rights reserved.
        """

    @staticmethod
    def _render_course_reminder_html(
        instructor_name: str,
        course_display: str,
        admin_name: str,
        institution_name: str,
        assessment_url: str,
    ) -> str:
        """Render HTML course assessment reminder email template"""
        from html import escape

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Course Assessment Reminder</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }}
        .content {{
            padding: 30px;
        }}
        .course-badge {{
            display: inline-block;
            background-color: #f0f4ff;
            color: #4c63d2;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 14px;
            margin: 10px 0;
        }}
        .button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            padding: 14px 32px;
            text-decoration: none;
            border-radius: 6px;
            margin: 20px 0;
            font-weight: 600;
            text-align: center;
        }}
        .button:hover {{
            opacity: 0.9;
        }}
        .message-box {{
            background-color: #fff9e6;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #e0e0e0;
        }}
        .highlight {{
            color: #667eea;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 Assessment Reminder</h1>
        </div>
        <div class="content">
            <p>Hello {escape(instructor_name)},</p>
            
            <p>This is a friendly reminder from <strong>{escape(admin_name)}</strong> to complete your learning outcome assessments for:</p>
            
            <div style="text-align: center;">
                <div class="course-badge">{escape(course_display)}</div>
            </div>
            
            <div class="message-box">
                <p style="margin: 0;"><strong>📌 Action Required:</strong> Please submit your course learning outcome (CLO) assessment data at your earliest convenience.</p>
            </div>
            
            <p>Your assessment data helps {escape(institution_name)} track student success and continuously improve our programs. The process only takes a few minutes:</p>
            
            <ul>
                <li>Review course learning outcomes (CLOs)</li>
                <li>Enter student assessment numbers</li>
                <li>Add optional narrative comments</li>
                <li>Submit for approval</li>
            </ul>
            
            <div style="text-align: center;">
                <a href="{assessment_url}" class="button">Complete Assessment →</a>
            </div>
            
            <p style="font-size: 14px; color: #666; margin-top: 30px;">The link above will take you directly to the assessment page for this course. If you have any questions or need assistance, please don't hesitate to reach out to {escape(admin_name)}.</p>
            
            <p>Thank you for your continued dedication to student success!</p>
        </div>
        <div class="footer">
            <p>This is an automated reminder from the LoopCloser system.</p>
            <p>© {get_current_time().year} {escape(institution_name)}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """

    @staticmethod
    def _render_course_reminder_text(
        instructor_name: str,
        course_display: str,
        admin_name: str,
        institution_name: str,
        assessment_url: str,
    ) -> str:
        """Render text course assessment reminder email template"""
        return f"""
Course Assessment Reminder

Hello {instructor_name},

This is a friendly reminder from {admin_name} to complete your learning outcome assessments for:

📋 {course_display}

ACTION REQUIRED: Please submit your course learning outcome (CLO) assessment data at your earliest convenience.

Your assessment data helps {institution_name} track student success and continuously improve our programs. The process only takes a few minutes:

• Review course learning outcomes (CLOs)
• Enter student assessment numbers
• Add optional narrative comments
• Submit for approval

Complete your assessment here:
{assessment_url}

The link above will take you directly to the assessment page for this course. If you have any questions or need assistance, please don't hesitate to reach out to {admin_name}.

Thank you for your continued dedication to student success!

---
This is an automated reminder from the LoopCloser system.
© {get_current_time().year} {institution_name}. All rights reserved.
        """


# Convenience functions for easy import
def send_verification_email(
    email: str, verification_token: str, user_name: str
) -> bool:
    """Convenience function for sending verification emails"""
    return EmailService.send_verification_email(email, verification_token, user_name)


def send_password_reset_email(email: str, reset_token: str, user_name: str) -> bool:
    """Convenience function for sending password reset emails"""
    return EmailService.send_password_reset_email(email, reset_token, user_name)


def send_invitation_email(
    email: str,
    invitation_token: str,
    inviter_name: str,
    institution_name: str,
    role: str,
    personal_message: Optional[str] = None,
) -> bool:
    """Convenience function for sending invitation emails"""
    return EmailService.send_invitation_email(
        email, invitation_token, inviter_name, institution_name, role, personal_message
    )


def send_welcome_email(email: str, user_name: str, institution_name: str) -> bool:
    """Convenience function for sending welcome emails"""
    return EmailService.send_welcome_email(email, user_name, institution_name)
