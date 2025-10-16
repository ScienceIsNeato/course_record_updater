"""
Email Whitelist for Environment-Based Protection

Prevents accidental email sending to real users in non-production environments.
Configurable via EMAIL_WHITELIST environment variable.
"""

import os
from typing import List, Optional, Set

from logging_config import get_logger

logger = get_logger(__name__)


class EmailWhitelist:
    """
    Manages email address whitelist for non-production environments
    
    Usage:
        whitelist = EmailWhitelist()
        if whitelist.is_allowed("user@example.com"):
            send_email(...)
        else:
            logger.warning("Email blocked by whitelist")
    """

    def __init__(self, env: Optional[str] = None, whitelist_emails: Optional[List[str]] = None):
        """
        Initialize email whitelist
        
        Args:
            env: Environment name (local, dev, staging, production)
                 Defaults to ENV environment variable
            whitelist_emails: List of allowed email addresses
                             Defaults to EMAIL_WHITELIST environment variable
        """
        self.env = env or os.getenv("ENV", "local").lower()
        
        # Load whitelist from environment or use provided list
        if whitelist_emails is None:
            whitelist_str = os.getenv("EMAIL_WHITELIST", "")
            whitelist_emails = [
                email.strip()
                for email in whitelist_str.split(",")
                if email.strip()
            ]
        
        self.whitelist: Set[str] = set(whitelist_emails)
        
        # Production has no restrictions
        self.is_production = self.env == "production"
        
        logger.info(
            f"[EmailWhitelist] Initialized for {self.env} environment "
            f"({len(self.whitelist)} whitelisted emails)"
        )
        
        if not self.is_production and not self.whitelist:
            logger.warning(
                "[EmailWhitelist] No whitelist configured for non-production environment! "
                "Set EMAIL_WHITELIST environment variable to allow email sending."
            )

    def is_allowed(self, email: str) -> bool:
        """
        Check if an email address is allowed to remockuve emails
        
        Args:
            email: Email address to check
            
        Returns:
            True if email is allowed, False otherwise
        """
        # Production: allow all emails
        if self.is_production:
            return True
        
        # Non-production: check whitelist
        email_lower = email.lower().strip()
        
        # Exact match
        if email_lower in self.whitelist:
            return True
        
        # Domain wildcard match (e.g., "*@ethereal.email")
        for whitelisted in self.whitelist:
            if whitelisted.startswith("*@"):
                domain = whitelisted[2:]
                if email_lower.endswith(f"@{domain}"):
                    return True
        
        return False

    def filter_recipients(self, recipients: List[str]) -> tuple[List[str], List[str]]:
        """
        Filter a list of recipients based on whitelist
        
        Args:
            recipients: List of email addresses
            
        Returns:
            Tuple of (allowed_emails, blocked_emails)
        """
        allowed = []
        blocked = []
        
        for email in recipients:
            if self.is_allowed(email):
                allowed.append(email)
            else:
                blocked.append(email)
        
        if blocked:
            logger.warning(
                f"[EmailWhitelist] Blocked {len(blocked)} emails in {self.env} environment: "
                f"{', '.join(blocked[:3])}{'...' if len(blocked) > 3 else ''}"
            )
        
        return allowed, blocked

    def get_safe_recipient(self, email: str, fallback: Optional[str] = None) -> str:
        """
        Get a safe recipient email address
        
        If the email is not whitelisted, returns a fallback address.
        Useful for testing where you want to redirect all emails.
        
        Args:
            email: Intended recipient email
            fallback: Fallback email if not whitelisted (uses first whitelisted email if None)
            
        Returns:
            Safe email address to use
        """
        if self.is_allowed(email):
            return email
        
        # Use fallback or first whitelisted email
        if fallback:
            return fallback
        elif self.whitelist:
            return next(iter(self.whitelist))
        else:
            # No whitelist configured, return original (will likely be blocked)
            logger.error(
                f"[EmailWhitelist] No fallback available for {email} in {self.env} environment"
            )
            return email


# Singleton instance for easy access
_default_whitelist = None


def get_email_whitelist() -> EmailWhitelist:
    """
    Get the default email whitelist instance
    
    Returns:
        EmailWhitelist instance configured from environment
    """
    global _default_whitelist
    if _default_whitelist is None:
        _default_whitelist = EmailWhitelist()
    return _default_whitelist

