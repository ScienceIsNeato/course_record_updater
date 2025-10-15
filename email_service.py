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
from typing import Optional
from urllib.parse import urljoin

from flask import current_app

# Import constants to avoid duplication
from constants import DEFAULT_BASE_URL

# Import email provider infrastructure
from email_providers import create_email_provider
from email_providers.base_provider import EmailProvider

# Import centralized logging
from logging_config import get_logger

# Get standardized logger
logger = get_logger(__name__)

# Email configuration
DEFAULT_FROM_EMAIL = "noreply@courserecord.app"
DEFAULT_FROM_NAME = "Course Record Updater"


class EmailServiceError(Exception):
    """Raised when email service encounters an error"""


class EmailService:
    """
    Comprehensive email service for authentication flows

    Handles template-based emails with secure token embedding

    CRITICAL SECURITY: Protects CEI email addresses from being used in testing
    """

    # Protected email domains - NEVER send emails to these in testing/development
    PROTECTED_DOMAINS = [
        "cei.edu",
        "coastaledu.org",
        "coastal.edu",
        "coastalcarolina.edu",
        # Add other protected domains as needed
    ]

    @staticmethod
    def _is_protected_email(email: Optional[str]) -> bool:
        """
        Check if email address is from a protected domain (e.g., CEI)

        Args:
            email: Email address to check (can be None)

        Returns:
            True if email is from protected domain, False otherwise
        """
        if not email or "@" not in email:
            return False

        # Handle malformed emails like "@cei.edu"
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
    def configure_app(app) -> None:
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

        subject = "Verify your Course Record Updater account"

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

        subject = "Reset your Course Record Updater password"

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

        subject = f"You're invited to join {institution_name} on Course Record Updater"

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

        subject = f"Welcome to Course Record Updater, {user_name}!"

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

    # Private helper methods

    @staticmethod
    def _get_email_provider() -> EmailProvider:
        """
        Get configured email provider instance

        Returns:
            Configured EmailProvider (console or gmail based on config)
        """
        # Build config from Flask app config
        config = {
            "server": current_app.config.get("MAIL_SERVER", "smtp.gmail.com"),
            "port": current_app.config.get("MAIL_PORT", 587),
            "use_tls": current_app.config.get("MAIL_USE_TLS", True),
            "use_ssl": current_app.config.get("MAIL_USE_SSL", False),
            "username": current_app.config.get("MAIL_USERNAME"),
            "password": current_app.config.get("MAIL_PASSWORD"),
            "default_sender": current_app.config.get(
                "MAIL_DEFAULT_SENDER", DEFAULT_FROM_EMAIL
            ),
            "default_sender_name": current_app.config.get(
                "MAIL_DEFAULT_SENDER_NAME", DEFAULT_FROM_NAME
            ),
        }

        # Determine provider type based on MAIL_SUPPRESS_SEND flag and server config
        # If True -> console provider (dev mode)
        # If False -> auto-detect based on MAIL_SERVER
        if current_app.config.get("MAIL_SUPPRESS_SEND", False):
            provider_name = "console"
        else:
            # Let factory auto-detect based on MAIL_SERVER
            provider_name = None

        return create_email_provider(provider_name=provider_name, config=config)

    @staticmethod
    def _send_email(
        to_email: str, subject: str, html_body: str, text_body: str
    ) -> bool:
        """Send email using configured email provider"""
        try:
            # CRITICAL PROTECTION: Block protected domains (e.g., CEI) in non-production environments
            is_production = current_app.config.get(
                "ENV"
            ) == "production" or current_app.config.get("PRODUCTION", False)

            if not is_production and EmailService._is_protected_email(to_email):
                logger.error(
                    f"[Email Service] BLOCKED: Attempted to send email to protected domain in {current_app.config.get('ENV', 'development')} environment: {to_email}"
                )
                raise EmailServiceError(
                    f"Cannot send emails to protected domain ({to_email.split('@')[1] if '@' in to_email else to_email}) in non-production environment"
                )

            # ADDITIONAL PROTECTION: In non-production, only allow lassie test accounts or mailtrap
            if not is_production:
                email_domain = to_email.split("@")[1] if "@" in to_email else ""

                # Allow Mailtrap sandbox addresses
                if "mailtrap.io" in email_domain:
                    pass  # Mailtrap is safe
                # Only allow our specific test Gmail accounts
                elif "gmail.com" in email_domain:
                    if "lassie.tests" not in to_email:
                        logger.error(
                            f"[Email Service] BLOCKED: Attempted to send to non-test Gmail account in {current_app.config.get('ENV', 'development')} environment: {to_email}"
                        )
                        raise EmailServiceError(
                            f"Only lassie.tests Gmail accounts allowed in non-production (attempted: {to_email})"
                        )
                # Block all other real domains in non-production
                elif email_domain and not any(
                    test_marker in email_domain.lower()
                    for test_marker in ["test", "example", "localhost"]
                ):
                    logger.error(
                        f"[Email Service] BLOCKED: Attempted to send to real domain in {current_app.config.get('ENV', 'development')} environment: {to_email}"
                    )
                    raise EmailServiceError(
                        f"Only test accounts (lassie.tests@gmail.com or @mailtrap.io) allowed in non-production (attempted: {to_email})"
                    )

            # Get email provider (console or gmail based on config)
            provider = EmailService._get_email_provider()

            # Send email via provider
            success = provider.send_email(to_email, subject, html_body, text_body)

            if success:
                logger.info(
                    f"[Email Service] Email sent successfully to {logger.sanitize(to_email)}"
                )
            else:
                logger.error(
                    f"[Email Service] Provider reported failure sending to {logger.sanitize(to_email)}"
                )

            return success

        except EmailServiceError:
            # Re-raise EmailServiceError (protection errors) to caller
            raise
        except Exception as e:
            logger.error(
                f"[Email Service] Failed to send email to {logger.sanitize(to_email)}: {e}"
            )
            return False

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
            <h1>Course Record Updater</h1>
        </div>
        <div class="content">
            <h2>Welcome, {user_name}!</h2>
            <p>Thank you for registering with Course Record Updater. To complete your registration, please verify your email address by clicking the button below:</p>
            
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
            <p>&copy; {datetime.now(timezone.utc).year} Course Record Updater. All rights reserved.</p>
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
Course Record Updater - Email Verification

Welcome, {user_name}!

Thank you for registering with Course Record Updater. To complete your registration, please verify your email address by visiting this link:

{verification_url}

Important: This verification link will expire in 24 hours for security reasons.

If you didn't create this account, you can safely ignore this email.

This email was sent to {email}

© {datetime.now(timezone.utc).year} Course Record Updater. All rights reserved.
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
            <p>We received a request to reset your password for your Course Record Updater account.</p>
            
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
            <p>&copy; {datetime.now(timezone.utc).year} Course Record Updater. All rights reserved.</p>
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
Course Record Updater - Password Reset

Hello, {user_name}

We received a request to reset your password for your Course Record Updater account.

To reset your password, visit this link:

{reset_url}

Important: This reset link will expire in 1 hour for security reasons.

If you didn't request this password reset, you can safely ignore this email. Your password will not be changed.

This email was sent to {email}

© {datetime.now(timezone.utc).year} Course Record Updater. All rights reserved.
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
            <p>Your password has been successfully reset for your Course Record Updater account.</p>
            <p><strong>Account:</strong> {email}</p>
            <p><strong>Reset completed:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d at %H:%M UTC')}</p>
            
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
            <p>© {datetime.now(timezone.utc).year} Course Record Updater. All rights reserved.</p>
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
Course Record Updater - Password Reset Successful

Hello, {user_name}

Your password has been successfully reset for your Course Record Updater account.

Account: {email}
Reset completed: {datetime.now(timezone.utc).strftime('%Y-%m-%d at %H:%M UTC')}

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

© {datetime.now(timezone.utc).year} Course Record Updater. All rights reserved.
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
            <p>{inviter_name} has invited you to join <strong>{institution_name}</strong> as a <strong>{role.replace('_', ' ').title()}</strong> on Course Record Updater.</p>
            
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
            <p>&copy; {datetime.now(timezone.utc).year} Course Record Updater. All rights reserved.</p>
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
Course Record Updater - You're Invited!

Join {institution_name}

{inviter_name} has invited you to join {institution_name} as a {role.replace('_', ' ').title()} on Course Record Updater.

{personal_message_text}To accept this invitation, visit:

{invitation_url}

Important: This invitation will expire in 7 days.

If you're not sure why you received this invitation, please contact {inviter_name} directly.

This email was sent to {email}

© {datetime.now(timezone.utc).year} Course Record Updater. All rights reserved.
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
            <h1>Welcome to Course Record Updater!</h1>
        </div>
        <div class="content">
            <h2>Hello, {user_name}!</h2>
            <p>Your email has been verified and your account is now active. Welcome to <strong>{institution_name}</strong> on Course Record Updater!</p>
            
            <p>You can now access your dashboard to:</p>
            <ul>
                <li>Manage your courses and sections</li>
                <li>Track student outcomes and assessments</li>
                <li>Import course data from Excel files</li>
                <li>Generate reports and analytics</li>
            </ul>
            
            <p style="text-align: center;">
                <a href="{dashboard_url}" class="button">Go to Dashboard</a>
            </p>
            
            <p>If you have any questions or need help getting started, don't hesitate to reach out to your institution administrator.</p>
            
            <p>We're excited to have you on board!</p>
        </div>
        <div class="footer">
            <p>&copy; {datetime.now(timezone.utc).year} Course Record Updater. All rights reserved.</p>
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
Course Record Updater - Welcome!

Hello, {user_name}!

Your email has been verified and your account is now active. Welcome to {institution_name} on Course Record Updater!

You can now access your dashboard to:
- Manage your courses and sections
- Track student outcomes and assessments
- Import course data from Excel files
- Generate reports and analytics

Visit your dashboard: {dashboard_url}

If you have any questions or need help getting started, don't hesitate to reach out to your institution administrator.

We're excited to have you on board!

© {datetime.now(timezone.utc).year} Course Record Updater. All rights reserved.
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
