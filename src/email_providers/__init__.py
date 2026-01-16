"""
Email Provider Package

Simplified email architecture with two providers:
- BrevoProvider: All real email sending (dev, staging, prod)
- EtherealProvider: Automated E2E testing with IMAP verification

"""

from src.email_providers.base_provider import EmailProvider
from src.email_providers.brevo_provider import BrevoProvider
from src.email_providers.ethereal_provider import EtherealProvider
from src.email_providers.factory import create_email_provider

__all__ = [
    "EmailProvider",
    "BrevoProvider",
    "EtherealProvider",
    "create_email_provider",
]
