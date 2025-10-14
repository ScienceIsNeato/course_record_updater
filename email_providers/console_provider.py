"""
Console Email Provider

Development/testing provider that logs emails instead of sending them.
Writes email content to console and optionally to files for inspection.
"""

import os
from datetime import datetime
from typing import Any, Dict

from email_providers.base_provider import EmailProvider
from logging_config import get_logger

logger = get_logger(__name__)


class ConsoleProvider(EmailProvider):
    """
    Email provider for development/testing
    
    Logs email content to console and writes to files instead of actually sending.
    Safe for development - no risk of accidentally sending test emails to real users.
    """
    
    def __init__(self):
        """Initialize console provider"""
        self._configured = False
        self._write_to_files = True
        self._log_dir = "logs/emails"
        
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure console provider
        
        Args:
            config: Configuration dictionary. Supports:
                - write_to_files: Whether to write emails to file (default: True)
                - log_dir: Directory for email files (default: logs/emails)
        """
        self._write_to_files = config.get("write_to_files", True)
        self._log_dir = config.get("log_dir", "logs/emails")
        
        # Create log directory if writing to files
        if self._write_to_files:
            os.makedirs(self._log_dir, exist_ok=True)
            
        self._configured = True
        logger.info(
            f"[Console Provider] Configured (write_to_files={self._write_to_files})"
        )
        
    def validate_configuration(self) -> bool:
        """
        Validate configuration
        
        Returns:
            True if configured (console provider has minimal requirements)
        """
        return self._configured
        
    def send_email(
        self, to_email: str, subject: str, html_body: str, text_body: str
    ) -> bool:
        """
        "Send" email by logging to console and optionally writing to file
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
            
        Returns:
            Always returns True (simulates successful send)
        """
        # Log to console
        logger.info(
            f"[Console Provider] Email suppressed (dev mode): {subject} -> {to_email}"
        )
        logger.info(f"[Console Provider] Email content:\n{text_body}")
        
        # Write to file if enabled
        if self._write_to_files:
            self._write_email_to_file(to_email, subject, html_body, text_body)
            
        return True
        
    def _write_email_to_file(
        self, to_email: str, subject: str, html_body: str, text_body: str
    ) -> None:
        """
        Write email to file for inspection
        
        Args:
            to_email: Recipient email
            subject: Email subject
            html_body: HTML body
            text_body: Text body
        """
        try:
            # Create safe filename from timestamp and recipient
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_email = to_email.replace("@", "_at_").replace(".", "_")
            filename = f"{timestamp}_{safe_email}.txt"
            filepath = os.path.join(self._log_dir, filename)
            
            # Write email metadata and content
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"To: {to_email}\n")
                f.write(f"Subject: {subject}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write("\n" + "=" * 80 + "\n")
                f.write("TEXT BODY:\n")
                f.write("=" * 80 + "\n\n")
                f.write(text_body)
                f.write("\n\n" + "=" * 80 + "\n")
                f.write("HTML BODY:\n")
                f.write("=" * 80 + "\n\n")
                f.write(html_body)
                
            logger.debug(f"[Console Provider] Email written to {filepath}")
            
        except Exception as e:
            # Don't fail email send if file write fails
            logger.warning(
                f"[Console Provider] Failed to write email to file: {e}"
            )

