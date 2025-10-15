"""
Ethereal Email Provider

Test email provider using Ethereal.email - a fake SMTP service for development/testing.
Unlike Console provider, this actually sends emails via SMTP that can be verified via IMAP.
Perfect for E2E testing where you need to verify email delivery and content.

See: https://ethereal.email/
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict

from email_providers.base_provider import EmailProvider
from logging_config import get_logger

logger = get_logger(__name__)


class EtherealProvider(EmailProvider):
    """
    Ethereal Email provider for E2E testing
    
    Sends real SMTP emails to Ethereal.email test accounts.
    Emails never reach actual recipients but can be verified programmatically via IMAP.
    Ideal for automated E2E testing where you need to:
    - Send actual emails via SMTP
    - Verify email delivery and content via IMAP/POP3
    - Avoid sending test emails to real users
    """

    def __init__(self):
        """Initialize Ethereal provider"""
        self._configured = False
        self._smtp_host = None
        self._smtp_port = None
        self._username = None
        self._password = None
        self._from_email = None

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure Ethereal provider

        Args:
            config: Configuration dictionary. Required:
                - smtp_host: Ethereal SMTP host (smtp.ethereal.email)
                - smtp_port: SMTP port (587 for STARTTLS)
                - username: Ethereal account email
                - password: Ethereal account password
                - from_email: From address (usually same as username)
        """
        self._smtp_host = config.get("smtp_host", "smtp.ethereal.email")
        self._smtp_port = int(config.get("smtp_port", 587))
        self._username = config.get("username")
        self._password = config.get("password")
        self._from_email = config.get("from_email", self._username)

        if not self._username or not self._password:
            raise ValueError(
                "Ethereal provider requires 'username' and 'password' in config"
            )

        self._configured = True
        logger.info(
            f"[Ethereal Provider] Configured for {self._username} "
            f"via {self._smtp_host}:{self._smtp_port}"
        )

    def validate_configuration(self) -> bool:
        """
        Validate configuration

        Returns:
            True if all required settings are present
        """
        return (
            self._configured
            and self._smtp_host is not None
            and self._smtp_port is not None
            and self._username is not None
            and self._password is not None
        )

    def send_email(
        self, to_email: str, subject: str, html_body: str, text_body: str
    ) -> bool:
        """
        Send email via Ethereal SMTP

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body

        Returns:
            True if email sent successfully, False otherwise

        Raises:
            Exception: If SMTP connection or sending fails
        """
        if not self.validate_configuration():
            logger.error("[Ethereal Provider] Provider not properly configured")
            return False

        try:
            # Create MIME multipart message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self._from_email
            msg["To"] = to_email

            # Attach both text and HTML versions
            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(html_body, "html")
            msg.attach(part1)
            msg.attach(part2)

            # Connect to SMTP server and send
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.starttls()  # Upgrade to TLS
                server.login(self._username, self._password)
                server.send_message(msg)

            logger.info(
                f"[Ethereal Provider] Email sent successfully: {subject} -> {to_email}"
            )
            logger.debug(
                f"[Ethereal Provider] View at: https://ethereal.email/messages "
                f"(login as {self._username})"
            )

            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"[Ethereal Provider] SMTP authentication failed: {e}")
            raise

        except smtplib.SMTPException as e:
            logger.error(f"[Ethereal Provider] SMTP error: {e}")
            raise

        except Exception as e:
            logger.error(f"[Ethereal Provider] Failed to send email: {e}")
            raise

