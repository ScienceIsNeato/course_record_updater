"""
Base Email Provider Abstract Class

Defines the interface that all email providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class EmailProvider(ABC):
    """
    Abstract base class for email service providers
    
    All email providers (Gmail, SendGrid, Mailgun, etc.) must implement this interface.
    This allows swapping providers without changing application code.
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
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the provider with settings
        
        Args:
            config: Dictionary of configuration values (e.g., SMTP credentials)
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

