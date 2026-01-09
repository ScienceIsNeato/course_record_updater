"""
Email Provider Factory

Creates appropriate email provider based on configuration or environment.

Simplified architecture:
- Brevo: All real email sending (dev, staging, prod with whitelist protection)
- Ethereal: Automated E2E testing only (with IMAP verification)
"""

import os
from typing import Any, Dict, Optional

from src.email_providers.base_provider import EmailProvider
from src.email_providers.brevo_provider import BrevoProvider
from src.email_providers.ethereal_provider import EtherealProvider
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def create_email_provider(
    provider_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None
) -> EmailProvider:
    """
    Create and configure an email provider

    Args:
        provider_name: Provider to create ("brevo" or "ethereal").
                      If None, determined from environment.
        config: Configuration dictionary for the provider.
               If None, loaded from environment variables.

    Returns:
        Configured EmailProvider instance

    Raises:
        ValueError: If provider_name is invalid or required config missing
    """
    logger.info(
        f"[Email Factory] create_email_provider called: provider_name={provider_name}, config={'provided' if config else 'None'}"
    )

    # Determine provider if not specified
    if provider_name is None:
        provider_name = _determine_provider_from_environment()

    provider_name = provider_name.lower()

    # Create provider instance
    provider: EmailProvider
    if provider_name == "brevo":
        provider = BrevoProvider()
    elif provider_name == "ethereal":
        provider = EtherealProvider()
    else:
        raise ValueError(
            f"Unknown email provider: {provider_name}. "
            f"Valid options: brevo, ethereal"
        )

    # Configure provider
    if config is None:
        config = _load_config_from_environment()

    provider.configure(config)

    logger.info(f"[Email Factory] Created provider: {provider_name}")
    return provider


def _determine_provider_from_environment() -> str:
    """
    Determine which provider to use based on environment

    Logic:
    1. If EMAIL_PROVIDER is explicitly set, use that (override)
    2. Otherwise, use environment-based mapping:
       - test/testing -> ethereal (E2E tests with IMAP verification)
       - development/staging/production -> brevo (real email sending)

    Returns:
        Provider name ("brevo" or "ethereal")
    """
    # Check for explicit override
    explicit_provider = os.getenv("EMAIL_PROVIDER")
    if explicit_provider:
        logger.info(
            f"[Email Factory] Using explicit EMAIL_PROVIDER: {explicit_provider}"
        )
        return explicit_provider.lower()

    # Environment-based mapping
    env = os.getenv("ENV", "development").lower()
    is_testing = os.getenv("TESTING", "").lower() in ("true", "1", "yes")

    # Map environment to provider
    if env in ("test", "e2e") or is_testing:
        return "ethereal"
    else:
        # development, staging, production all use Brevo
        return "brevo"


def _load_config_from_environment() -> Dict[str, Any]:
    """
    Load provider configuration from environment variables

    Returns:
        Configuration dictionary with settings from environment
    """
    # Build base config with explicit Any type
    config: Dict[str, Any] = {
        "default_sender": os.getenv("MAIL_DEFAULT_SENDER", "noreply@courserecord.app"),
        "default_sender_name": os.getenv("MAIL_DEFAULT_SENDER_NAME", "LoopCloser"),
    }

    # Add Brevo-specific settings if Brevo is configured
    if os.getenv("BREVO_API_KEY"):
        config.update(
            {
                "api_key": os.getenv("BREVO_API_KEY"),
                "sender_email": os.getenv("BREVO_SENDER_EMAIL")
                or config.get("default_sender"),
                "sender_name": os.getenv("BREVO_SENDER_NAME")
                or config.get("default_sender_name"),
            }
        )

    # Add Ethereal-specific settings if Ethereal is configured
    ethereal_user = os.getenv("ETHEREAL_USER")
    logger.info(f"[Email Factory] ETHEREAL_USER from environment: {ethereal_user}")
    logger.info(f"[Email Factory] ENV from environment: {os.getenv('ENV')}")

    if ethereal_user:
        config.update(
            {
                "smtp_host": os.getenv("ETHEREAL_SMTP_HOST", "smtp.ethereal.email"),
                "smtp_port": int(os.getenv("ETHEREAL_SMTP_PORT", "587")),
                "imap_host": os.getenv("ETHEREAL_IMAP_HOST", "imap.ethereal.email"),
                "imap_port": int(os.getenv("ETHEREAL_IMAP_PORT", "993")),
                "username": ethereal_user,
                "password": os.getenv("ETHEREAL_PASS"),
                "from_email": ethereal_user,
            }
        )
        logger.info(
            f"[Email Factory] Ethereal configuration loaded for {ethereal_user}"
        )

    return config
