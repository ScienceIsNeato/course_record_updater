"""
Email Whitelist for Environment-Based Protection

Prevents accidental email sending to real users in local/test environments.
Configurable via EMAIL_WHITELIST environment variable.

Environment behavior:
- local, test: Whitelist enforced (blocks non-whitelisted emails)
- dev, staging, production: Whitelist disabled (all emails allowed)
"""

import os
from typing import List, Optional, Set

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Environments where whitelist is enforced
WHITELIST_ENFORCED_ENVS = {"local", "test", "e2e"}


class EmailWhitelist:
    """
    Manages email address whitelist for local/test environments.
    
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
            env: Environment name (local, test, dev, staging, production)
                 Defaults to ENV environment variable
            whitelist_emails: List of allowed email addresses/patterns
                             Defaults to EMAIL_WHITELIST environment variable
        """
        self.env = (env or os.getenv("ENV", "local")).lower()
        
        # Load whitelist from environment or use provided list
        if whitelist_emails is None:
            whitelist_str = os.getenv("EMAIL_WHITELIST", "")
            whitelist_emails = [
                email.strip().lower()
                for email in whitelist_str.split(",")
                if email.strip()
            ]
        else:
            # Normalize provided patterns
            whitelist_emails = [e.strip().lower() for e in whitelist_emails if e.strip()]
        
        self.whitelist: Set[str] = set(whitelist_emails)
        
        # Whitelist only enforced in local/test environments
        self.whitelist_enforced = self.env in WHITELIST_ENFORCED_ENVS
        
        logger.info(
            f"[EmailWhitelist] Initialized for '{self.env}' environment "
            f"(whitelist {'ENFORCED' if self.whitelist_enforced else 'DISABLED'}, "
            f"{len(self.whitelist)} patterns configured)"
        )
        
        if self.whitelist_enforced and not self.whitelist:
            logger.warning(
                "[EmailWhitelist] No whitelist configured for local/test environment! "
                "Set EMAIL_WHITELIST environment variable to allow email sending. "
                "Example: EMAIL_WHITELIST=*@ethereal.email,*@test.local"
            )

    def is_allowed(self, email: str) -> bool:
        """
        Check if an email address is allowed to receive emails.
        
        Args:
            email: Email address to check
            
        Returns:
            True if email is allowed, False otherwise
        """
        # Whitelist not enforced in dev/staging/production - allow all emails
        if not self.whitelist_enforced:
            return True
        
        # Local/test environments: check whitelist
        email_lower = email.lower().strip()
        
        # Exact match
        if email_lower in self.whitelist:
            return True
        
        # Domain wildcard match (e.g., "*@ethereal.email", "*@test.local")
        for pattern in self.whitelist:
            if pattern.startswith("*@"):
                domain = pattern[2:].lower()
                if email_lower.endswith(f"@{domain}"):
                    return True
        
        logger.debug(
            f"[EmailWhitelist] Email '{email}' not in whitelist for {self.env} environment"
        )
        return False

    def get_blocked_reason(self, email: str) -> Optional[str]:
        """
        Get reason why an email is blocked, or None if allowed.
        
        Args:
            email: Email address to check
            
        Returns:
            Reason string if blocked, None if allowed
        """
        if self.is_allowed(email):
            return None
        
        return (
            f"Email address '{email}' is not on the whitelist for the '{self.env}' environment. "
            f"Add it to EMAIL_WHITELIST or use a whitelisted domain "
            f"(configured: {sorted(self.whitelist)})"
        )


# Singleton instance
_whitelist_instance: Optional[EmailWhitelist] = None


def get_email_whitelist() -> EmailWhitelist:
    """
    Get the singleton email whitelist instance.
    
    Returns:
        EmailWhitelist: Singleton whitelist instance
    """
    global _whitelist_instance
    if _whitelist_instance is None:
        _whitelist_instance = EmailWhitelist()
    return _whitelist_instance


def reset_whitelist() -> None:
    """Reset the singleton instance (for testing)."""
    global _whitelist_instance
    _whitelist_instance = None
