"""
Mailtrap SMTP Email Provider

Testing provider that sends emails via Mailtrap's sandbox SMTP.
All emails are caught in Mailtrap inbox - perfect for development/testing.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict

from email_providers.base_provider import EmailProvider
from logging_config import get_logger

logger = get_logger(__name__)


class MailtrapProvider(EmailProvider):
    """
    Email provider for Mailtrap sandbox testing
    
    Sends emails via Mailtrap SMTP - all emails are caught in inbox.
    Perfect for testing email flows without sending to real recipients.
    
    Configuration requires:
    - server: Mailtrap SMTP server (default: sandbox.smtp.mailtrap.io)
    - port: SMTP port (typically 2525 or 587)
    - username: Mailtrap inbox username
    - password: Mailtrap inbox password
    - default_sender: From email address (can be anything)
    - default_sender_name: From display name
    """
    
    def __init__(self):
        """Initialize Mailtrap provider"""
        self._configured = False
        self._server = None
        self._port = None
        self._username = None
        self._password = None
        self._default_sender = None
        self._default_sender_name = None
        
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure Mailtrap SMTP provider
        
        Args:
            config: Configuration dictionary with SMTP settings
        """
        self._server = config.get("server", "sandbox.smtp.mailtrap.io")
        self._port = config.get("port", 2525)
        self._username = config.get("username")
        self._password = config.get("password")
        self._default_sender = config.get(
            "default_sender", "test@lassietests.mailtrap.io"
        )
        self._default_sender_name = config.get(
            "default_sender_name", "Course Record Updater (Test)"
        )
        
        self._configured = True
        logger.info(
            f"[Mailtrap Provider] Configured (server={self._server}, port={self._port})"
        )
        
    def validate_configuration(self) -> bool:
        """
        Validate Mailtrap configuration
        
        Returns:
            True if all required settings are present
        """
        if not self._configured:
            return False
            
        # Check required fields
        required = [self._server, self._port, self._username, self._password]
        if not all(required):
            logger.error("[Mailtrap Provider] Missing required configuration")
            return False
            
        return True
        
    def send_email(
        self, to_email: str, subject: str, html_body: str, text_body: str
    ) -> bool:
        """
        Send email via Mailtrap SMTP
        
        All emails are caught in Mailtrap inbox - nothing actually delivers.
        
        Args:
            to_email: Recipient email address (caught by Mailtrap)
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
            
        Returns:
            True if email sent to Mailtrap successfully, False otherwise
        """
        try:
            # Create MIME message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self._default_sender_name} <{self._default_sender}>"
            msg["To"] = to_email
            
            # Attach text and HTML parts
            text_part = MIMEText(text_body, "plain")
            html_part = MIMEText(html_body, "html")
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Connect and send (Mailtrap typically doesn't use TLS/SSL on 2525)
            server = smtplib.SMTP(self._server, self._port)
            
            # Authenticate
            if self._username and self._password:
                server.login(self._username, self._password)
                
            # Send message
            server.send_message(msg)
            server.quit()
            
            logger.info(
                f"[Mailtrap Provider] Email sent successfully to {to_email} "
                f"(caught in Mailtrap inbox)"
            )
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"[Mailtrap Provider] Authentication failed: {e}")
            return False
            
        except smtplib.SMTPException as e:
            logger.error(f"[Mailtrap Provider] SMTP error sending email: {e}")
            return False
            
        except Exception as e:
            logger.error(
                f"[Mailtrap Provider] Failed to send email to {to_email}: {e}"
            )
            return False

