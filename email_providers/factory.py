"""
Email Provider Factory

Creates appropriate email provider based on configuration or environment.
"""

import os
from typing import Any, Dict, Optional

from email_providers.base_provider import EmailProvider
from email_providers.console_provider import ConsoleProvider
from email_providers.gmail_provider import GmailProvider
from email_providers.mailtrap_provider import MailtrapProvider
from logging_config import get_logger

logger = get_logger(__name__)


def create_email_provider(
    provider_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None
) -> EmailProvider:
    """
    Create and configure an email provider
    
    Args:
        provider_name: Provider to create ("console", "gmail").
                      If None, determined from environment/config.
        config: Configuration dictionary for the provider.
               If None, loaded from environment variables.
               
    Returns:
        Configured EmailProvider instance
        
    Raises:
        ValueError: If provider_name is invalid
    """
    # Determine provider if not specified
    if provider_name is None:
        provider_name = _determine_provider_from_environment()
        
    provider_name = provider_name.lower()
    
    # Create provider instance
    provider: EmailProvider
    if provider_name == "console":
        provider = ConsoleProvider()
    elif provider_name == "gmail":
        provider = GmailProvider()
    elif provider_name == "mailtrap":
        provider = MailtrapProvider()
    else:
        raise ValueError(
            f"Unknown email provider: {provider_name}. "
            f"Valid options: console, gmail, mailtrap"
        )
        
    # Configure provider
    if config is None:
        config = _load_config_from_environment()
        
    provider.configure(config)
    
    # Validate configuration
    if not provider.validate_configuration():
        logger.warning(
            f"[Email Factory] Provider {provider_name} configuration may be incomplete"
        )
        
    logger.info(f"[Email Factory] Created provider: {provider_name}")
    return provider


def _determine_provider_from_environment() -> str:
    """
    Determine which provider to use based on environment
    
    Logic:
    - If MAIL_SUPPRESS_SEND=true -> console
    - If MAIL_SERVER contains "mailtrap" -> mailtrap
    - If ENV=production or PRODUCTION=true -> gmail
    - If MAIL_USERNAME is set -> gmail
    - Default -> console (safe for development)
    
    Returns:
        Provider name ("console", "gmail", or "mailtrap")
    """
    # Check explicit suppress flag
    if os.getenv("MAIL_SUPPRESS_SEND", "false").lower() == "true":
        return "console"
    
    # Check if Mailtrap is configured
    mail_server = os.getenv("MAIL_SERVER", "").lower()
    if "mailtrap" in mail_server or "sandbox.smtp" in mail_server:
        return "mailtrap"
        
    # Check environment type
    env = os.getenv("ENV", "development").lower()
    is_production = os.getenv("PRODUCTION", "false").lower() == "true"
    
    if env == "production" or is_production:
        return "gmail"
        
    # Check if SMTP credentials are configured
    if os.getenv("MAIL_USERNAME"):
        return "gmail"
        
    # Default to console for safety
    return "console"


def _load_config_from_environment() -> Dict[str, Any]:
    """
    Load provider configuration from environment variables
    
    Returns:
        Configuration dictionary with settings from environment
    """
    return {
        # SMTP settings
        "server": os.getenv("MAIL_SERVER", "smtp.gmail.com"),
        "port": int(os.getenv("MAIL_PORT", "587")),
        "use_tls": os.getenv("MAIL_USE_TLS", "true").lower() == "true",
        "use_ssl": os.getenv("MAIL_USE_SSL", "false").lower() == "true",
        "username": os.getenv("MAIL_USERNAME"),
        "password": os.getenv("MAIL_PASSWORD"),
        "default_sender": os.getenv(
            "MAIL_DEFAULT_SENDER", os.getenv("MAIL_USERNAME", "noreply@courserecord.app")
        ),
        "default_sender_name": os.getenv(
            "MAIL_DEFAULT_SENDER_NAME", "Course Record Updater"
        ),
        # Console provider settings
        "write_to_files": True,
        "log_dir": "logs/emails",
    }

