"""
Gmail SMTP Email Provider

Production provider that sends emails via Gmail SMTP.
Supports both SSL (port 465) and TLS (port 587) connections.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Union

from email_providers.base_provider import EmailProvider
from logging_config import get_logger

logger = get_logger(__name__)


class GmailProvider(EmailProvider):
    """
    Email provider for Gmail SMTP
    
    Sends emails via Gmail's SMTP servers using app passwords.
    Supports both SSL (port 465) and TLS (port 587) connections.
    
    Configuration requires:
    - server: SMTP server address (default: smtp.gmail.com)
    - port: SMTP port (587 for TLS, 465 for SSL)
    - use_tls: Whether to use STARTTLS (default: True for port 587)
    - use_ssl: Whether to use SSL (default: True for port 465)
    - username: Gmail email address
    - password: Gmail app password (not regular password)
    - default_sender: From email address
    - default_sender_name: From display name
    """
    
    def __init__(self):
        """Initialize Gmail provider"""
        self._configured = False
        self._server = None
        self._port = None
        self._use_tls = None
        self._use_ssl = None
        self._username = None
        self._password = None
        self._default_sender = None
        self._default_sender_name = None
        
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure Gmail SMTP provider
        
        Args:
            config: Configuration dictionary with SMTP settings
        """
        self._server = config.get("server", "smtp.gmail.com")
        self._port = config.get("port", 587)
        self._use_tls = config.get("use_tls", True)
        self._use_ssl = config.get("use_ssl", False)
        self._username = config.get("username")
        self._password = config.get("password")
        self._default_sender = config.get("default_sender", self._username)
        self._default_sender_name = config.get(
            "default_sender_name", "Course Record Updater"
        )
        
        self._configured = True
        logger.info(
            f"[Gmail Provider] Configured (server={self._server}, "
            f"port={self._port}, TLS={self._use_tls}, SSL={self._use_ssl})"
        )
        
    def validate_configuration(self) -> bool:
        """
        Validate Gmail configuration
        
        Returns:
            True if all required settings are present
        """
        if not self._configured:
            return False
            
        # Check required fields
        required = [self._server, self._port, self._username, self._password]
        if not all(required):
            logger.error("[Gmail Provider] Missing required configuration")
            return False
            
        # Validate port/TLS/SSL combination
        if self._use_ssl and self._port != 465:
            logger.warning(
                f"[Gmail Provider] SSL mode typically uses port 465, got {self._port}"
            )
            
        if self._use_tls and self._port != 587:
            logger.warning(
                f"[Gmail Provider] TLS mode typically uses port 587, got {self._port}"
            )
            
        return True
        
    def send_email(
        self, to_email: str, subject: str, html_body: str, text_body: str
    ) -> bool:
        """
        Send email via Gmail SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
            
        Returns:
            True if email sent successfully, False otherwise
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
            
            # Connect and send
            server: Union[smtplib.SMTP, smtplib.SMTP_SSL]
            
            if self._use_ssl:
                # SSL connection (port 465)
                server = smtplib.SMTP_SSL(self._server, self._port)
            else:
                # Plain or TLS connection (port 587)
                server = smtplib.SMTP(self._server, self._port)
                if self._use_tls:
                    server.starttls()
                    
            # Authenticate if credentials provided
            if self._username and self._password:
                server.login(self._username, self._password)
                
            # Send message
            server.send_message(msg)
            server.quit()
            
            logger.info(f"[Gmail Provider] Email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"[Gmail Provider] Authentication failed: {e}")
            return False
            
        except smtplib.SMTPException as e:
            logger.error(f"[Gmail Provider] SMTP error sending email: {e}")
            return False
            
        except Exception as e:
            logger.error(f"[Gmail Provider] Failed to send email to {to_email}: {e}")
            return False

