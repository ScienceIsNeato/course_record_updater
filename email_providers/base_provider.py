"""
Base Email Provider Abstract Class

Defines the interface that all email providers must implement.
Supports both sending emails (SMTP) and reading emails (IMAP/API).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class EmailProvider(ABC):
    """
    Abstract base class for email service providers
    
    All email providers (Gmail, Ethereal, Mailgun, etc.) must implement this interface.
    This allows swapping providers without changing application code.
    
    Providers should implement:
    - send_email(): Required for all providers
    - read_email(): Optional, can raise NotImplementedError if not supported
    """
    
    @abstractmethod
    def send_email(
        self, to_email: str, subject: str, html_body: str, text_body: str
    ) -> bool:
        """
        Send an email
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_body: HTML version of email body
            text_body: Plain text version of email body
            
        Returns:
            True if email sent successfully, False otherwise
            
        Raises:
            Exception: If sending fails with unrecoverable error
        """
        ...
    
    @abstractmethod
    def read_email(
        self,
        recipient_email: str,
        subject_substring: Optional[str] = None,
        unique_identifier: Optional[str] = None,
        timeout: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """
        Read an email from the provider's inbox
        
        Args:
            recipient_email: Email address to check (usually the configured account)
            subject_substring: Optional substring to match in subject
            unique_identifier: Optional unique string to find in email
            timeout: Maximum seconds to wait for email
            
        Returns:
            Dictionary with email details if found, None otherwise
            Keys: subject, from, to, body, html_body
            
        Raises:
            NotImplementedError: If provider doesn't support reading emails
        """
        ...
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the provider with settings
        
        Args:
            config: Dictionary of configuration values (e.g., SMTP credentials, whitelist)
        """
        ...
    
    @abstractmethod
    def validate_configuration(self) -> bool:
        """
        Validate that the provider is properly configured
        
        Returns:
            True if configuration is valid, False otherwise
        """
        ...

