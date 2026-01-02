"""
Ethereal Email Provider

Test email provider using Ethereal.email - a fake SMTP service for development/testing.
Unlike Console provider, this actually sends emails via SMTP that can be verified via IMAP.
Perfect for E2E testing where you need to verify email delivery and content.

See: https://ethereal.email/
"""

import email
import imaplib
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from src.email_providers.base_provider import EmailProvider
from src.utils.logging_config import get_logger

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

    def __init__(self) -> None:
        """Initialize Ethereal provider"""
        self._configured = False
        self._smtp_host: Optional[str] = None
        self._smtp_port: Optional[int] = None
        self._imap_host: Optional[str] = None
        self._imap_port: Optional[int] = None
        self._username: Optional[str] = None
        self._password: Optional[str] = None
        self._from_email: Optional[str] = None

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure Ethereal provider

        Args:
            config: Configuration dictionary. Required:
                - smtp_host: Ethereal SMTP host (smtp.ethereal.email)
                - smtp_port: SMTP port (587 for STARTTLS)
                - imap_host: Ethereal IMAP host (imap.ethereal.email)
                - imap_port: IMAP port (993 for SSL)
                - username: Ethereal account email
                - password: Ethereal account password
                - from_email: From address (usually same as username)
        """
        self._smtp_host = config.get("smtp_host", "smtp.ethereal.email")
        self._smtp_port = int(config.get("smtp_port", 587))
        self._imap_host = config.get("imap_host", "imap.ethereal.email")
        self._imap_port = int(config.get("imap_port", 993))
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
            f"(SMTP: {self._smtp_host}:{self._smtp_port}, "
            f"IMAP: {self._imap_host}:{self._imap_port})"
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
            # Type guards for configuration
            if not (self._smtp_host and self._smtp_port and self._username and self._password and self._from_email):
                raise ValueError("Provider not properly configured")
            
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

            # Connect to SMTP server and send (with 10s timeout to prevent hanging)
            with smtplib.SMTP(self._smtp_host, self._smtp_port, timeout=10) as server:
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

    def _connect_to_imap(self) -> Optional[imaplib.IMAP4_SSL]:
        """Connect to IMAP server and select INBOX"""
        try:
            mail = imaplib.IMAP4_SSL(self._imap_host, self._imap_port)
            mail.login(self._username, self._password)
            mail.select("INBOX")
            return mail
        except Exception as e:
            logger.error(f"[Ethereal Provider] IMAP connection failed: {e}")
            return None
    
    def _extract_email_body(self, email_message: email.message.Message) -> tuple[str, str]:
        """Extract text and HTML body from email message"""
        body_text = ""
        body_html = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                payload = part.get_payload(decode=True)
                if content_type == "text/plain" and isinstance(payload, bytes):
                    body_text = payload.decode("utf-8", errors="ignore")
                elif content_type == "text/html" and isinstance(payload, bytes):
                    body_html = payload.decode("utf-8", errors="ignore")
        else:
            payload = email_message.get_payload(decode=True)
            if isinstance(payload, bytes):
                body_text = payload.decode("utf-8", errors="ignore")
        
        return body_text, body_html
    
    def _matches_search_criteria(
        self,
        subject: str,
        body_text: str,
        body_html: str,
        subject_substring: Optional[str],
        unique_identifier: Optional[str],
    ) -> bool:
        """Check if email matches search criteria"""
        if subject_substring and subject_substring.lower() not in subject.lower():
            return False
        
        if unique_identifier and (unique_identifier not in subject and 
                                   unique_identifier not in body_text and 
                                   unique_identifier not in body_html):
            return False
        
        return True
    
    def _try_parse_email(
        self,
        num: bytes,
        mail: imaplib.IMAP4_SSL,
        subject_substring: Optional[str],
        unique_identifier: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Try to parse and check a single email"""
        try:
            # Convert bytes to str for IMAP fetch
            num_str = num.decode('utf-8') if isinstance(num, bytes) else str(num)
            fetch_result = mail.fetch(num_str, "(RFC822)")
            # Type guard: ensure fetch_result is indexable tuple
            if not fetch_result or not isinstance(fetch_result, tuple) or len(fetch_result) < 2:
                return None
            _, msg_data = fetch_result
            # Type guard: ensure msg_data is indexable
            if not msg_data or not isinstance(msg_data, (list, tuple)) or len(msg_data) == 0:
                return None
            first_item = msg_data[0]
            # Type guard: ensure first_item is indexable tuple
            if not isinstance(first_item, tuple) or len(first_item) < 2:
                return None
            email_body = first_item[1]
            # Type guard: ensure we have bytes
            if not isinstance(email_body, bytes):
                return None
            email_message = email.message_from_bytes(email_body)
            
            # Extract email details
            subject = email_message.get("Subject", "")
            from_addr = email_message.get("From", "")
            to_addr = email_message.get("To", "")
            
            # Extract body content
            body_text, body_html = self._extract_email_body(email_message)
            
            # Check if this email matches criteria
            if not self._matches_search_criteria(subject, body_text, body_html, subject_substring, unique_identifier):
                return None
            
            # Found a match!
            logger.info(f"[Ethereal Provider] Found matching email: {subject}")
            return {
                "subject": subject,
                "from": from_addr,
                "to": to_addr,
                "body": body_text,
                "html_body": body_html,
            }
        except Exception as e:
            logger.debug(f"[Ethereal Provider] Error parsing email: {e}")
            return None
    
    def _validate_imap_read_request(self, recipient_email: str) -> bool:
        """Validate IMAP read request and log errors if invalid"""
        if not self.validate_configuration():
            logger.error("[Ethereal Provider] Provider not properly configured for IMAP")
            return False
        
        if not (self._imap_host and self._imap_port and self._username and self._password):
            logger.error("[Ethereal Provider] Missing IMAP configuration")
            return False
        
        if recipient_email.lower() != self._username.lower():
            logger.warning(
                f"[Ethereal Provider] Can only read emails for configured account "
                f"({self._username}), not {recipient_email}"
            )
            return False
        
        return True
    
    def _search_emails_once(
        self, 
        subject_substring: Optional[str], 
        unique_identifier: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Perform a single IMAP search iteration"""
        try:
            mail = self._connect_to_imap()
            if not mail:
                return None
            
            # Search for all emails
            _, message_numbers = mail.search(None, "ALL")
            
            # Process emails in reverse order (newest first)
            for num in reversed(message_numbers[0].split()):
                result = self._try_parse_email(num, mail, subject_substring, unique_identifier)
                if result:
                    mail.close()
                    mail.logout()
                    return result
            
            # No match found, close connection
            mail.close()
            mail.logout()
            
        except Exception as e:
            logger.debug(f"[Ethereal Provider] IMAP search iteration error: {e}")
        
        return None
    
    def read_email(
        self,
        recipient_email: str,
        subject_substring: Optional[str] = None,
        unique_identifier: Optional[str] = None,
        timeout: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """
        Read email from Ethereal IMAP inbox
        
        Connects to Ethereal's IMAP server and searches for matching emails.
        Polls for up to `timeout` seconds if email not immediately found.
        
        Args:
            recipient_email: Email address to check (must be configured account)
            subject_substring: Optional substring to match in subject
            unique_identifier: Optional unique string to find in email body/subject
            timeout: Maximum seconds to wait for email (polls every 2s)
            
        Returns:
            Email dictionary if found, None otherwise
            Keys: subject, from, to, body, html_body
        """
        if not self._validate_imap_read_request(recipient_email):
            return None
        
        logger.info(
            f"[Ethereal Provider] Searching IMAP for email "
            f"(subject={subject_substring}, identifier={unique_identifier})"
        )
        
        start_time = time.time()
        poll_interval = 2
        
        while time.time() - start_time < timeout:
            result = self._search_emails_once(subject_substring, unique_identifier)
            if result:
                return result
            
            # Wait before next poll
            elapsed = time.time() - start_time
            if elapsed < timeout:
                time.sleep(min(poll_interval, timeout - elapsed))
        
        logger.warning(
            f"[Ethereal Provider] Email not found after {timeout}s: "
            f"subject={subject_substring}, identifier={unique_identifier}"
        )
        return None

