"""
Email Provider Package

Simplified email architecture with two providers:
- BrevoProvider: All real email sending (dev, staging, prod)
- EtherealProvider: Automated E2E testing with IMAP verification

Whitelist protection is handled at the EmailService layer, not provider layer.
"""

from email_providers.base_provider import EmailProvider
from email_providers.brevo_provider import BrevoProvider
from email_providers.ethereal_provider import EtherealProvider
from email_providers.factory import create_email_provider

__all__ = [
    "EmailProvider",
    "BrevoProvider",
    "EtherealProvider",
    "create_email_provider",
]
