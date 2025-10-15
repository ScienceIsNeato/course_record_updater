"""
Email Provider Package

Provides abstraction layer for email sending to support multiple backends.
Currently supports:
- ConsoleProvider: Development mode, logs emails to console/files
- GmailProvider: Gmail SMTP for production/staging
- EtherealProvider: Ethereal.email for E2E testing with IMAP verification
- MailtrapProvider: Mailtrap SMTP for testing

Future providers can be added (SendGrid, Mailgun, etc.) without changing application code.
"""

from email_providers.base_provider import EmailProvider
from email_providers.console_provider import ConsoleProvider
from email_providers.ethereal_provider import EtherealProvider
from email_providers.factory import create_email_provider
from email_providers.gmail_provider import GmailProvider
from email_providers.mailtrap_provider import MailtrapProvider

__all__ = [
    "EmailProvider",
    "ConsoleProvider",
    "EtherealProvider",
    "GmailProvider",
    "MailtrapProvider",
    "create_email_provider",
]

