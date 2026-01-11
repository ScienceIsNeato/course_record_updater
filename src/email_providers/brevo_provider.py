"""
Brevo (formerly Sendinblue) Email Provider

Production-ready transactional email provider using Brevo's API.
Provides reliable email delivery with good deliverability and free tier (300 emails/day).

See: https://www.brevo.com/
API Docs: https://developers.brevo.com/
"""

import os
from typing import Any, Dict, Optional

import requests

from src.email_providers.base_provider import EmailProvider
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BrevoProvider(EmailProvider):
    """
    Brevo email provider for production transactional emails

    Uses Brevo's REST API to send emails with excellent deliverability.
    Free tier: 300 emails/day, perfect for testing and small deployments.

    Configuration requires:
    - api_key: Brevo API key (from https://app.brevo.com/settings/keys/api)
    - sender_email: Verified sender email address
    - sender_name: Sender display name
    """

    def __init__(self) -> None:
        """Initialize Brevo provider"""
        self._configured = False
        self._api_key: Optional[str] = None
        self._sender_email: Optional[str] = None
        self._sender_name: Optional[str] = None
        self._api_url = "https://api.brevo.com/v3/smtp/email"

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure Brevo provider

        Args:
            config: Configuration dictionary. Required:
                - api_key: Brevo API key
                - sender_email: Verified sender email
                - sender_name: Sender display name (optional)
        """
        self._api_key = config.get("api_key") or os.getenv("BREVO_API_KEY")
        self._sender_email = config.get("sender_email") or config.get("default_sender")
        self._sender_name = config.get("sender_name") or config.get(
            "default_sender_name", "LoopCloser"
        )

        if not self._api_key:
            raise ValueError(
                "Brevo provider requires 'api_key' in config or BREVO_API_KEY env var"
            )

        if not self._sender_email:
            raise ValueError(
                "Brevo provider requires 'sender_email' or 'default_sender' in config"
            )

        self._configured = True
        logger.info(
            f"[Brevo Provider] Configured for {self._sender_email} "
            f"({self._sender_name})"
        )

    def validate_configuration(self) -> bool:
        """
        Validate configuration

        Returns:
            True if all required settings are present
        """
        return (
            self._configured
            and self._api_key is not None
            and self._sender_email is not None
        )

    def send_email(
        self, to_email: str, subject: str, html_body: str, text_body: str
    ) -> bool:
        """
        Send email via Brevo API

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body

        Returns:
            True if email sent successfully, False otherwise

        Raises:
            Exception: If API request fails
        """
        if not self.validate_configuration():
            logger.error("[Brevo Provider] Provider not properly configured")
            return False

        try:
            # Build request payload
            payload = {
                "sender": {
                    "name": self._sender_name,
                    "email": self._sender_email,
                },
                "to": [
                    {
                        "email": to_email,
                    }
                ],
                "subject": subject,
                "htmlContent": html_body,
                "textContent": text_body,
            }

            # Send via Brevo API
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": self._api_key,
            }

            response = requests.post(
                self._api_url,
                json=payload,
                headers=headers,
                timeout=10,
            )

            # Check response
            if response.status_code == 201:
                message_id = response.json().get("messageId")
                logger.info(
                    f"[Brevo Provider] Email sent successfully: {subject} -> {to_email} "
                    f"(Message ID: {message_id})"
                )
                return True
            raise RuntimeError(
                f"Brevo returned HTTP {response.status_code}: {response.text}"
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"[Brevo Provider] API request failed: {e}")
            return False

        except Exception as e:
            logger.error(f"[Brevo Provider] Failed to send email to {to_email}: {e}")
            return False

    def read_email(
        self,
        recipient_email: str,
        subject_substring: Optional[str] = None,
        unique_identifier: Optional[str] = None,
        timeout: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """
        Read emails from Brevo - NOT SUPPORTED

        Brevo is a sending service and does not provide inbox/IMAP access.
        Use Ethereal Email provider for E2E testing that requires email verification.

        Raises:
            NotImplementedError: Always - Brevo doesn't support reading emails
        """
        raise NotImplementedError(
            "Brevo is a sending service and does not support reading emails. "
            "Use Ethereal Email provider for E2E testing or Console provider for local testing."
        )
