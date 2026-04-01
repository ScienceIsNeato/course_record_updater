"""
Console Email Provider

A no-op email provider that logs emails to the application log and always
reports success. Used as a fallback in e2e/test environments when real email
infrastructure (Ethereal SMTP credentials) is not available — for example,
in CI where ETHEREAL_USER is not configured.

This lets e2e tests exercise the full bulk-email pipeline (job creation,
progress tracking, UI polling) without requiring network access to an
SMTP server.
"""

from typing import Any, Dict, Optional

from src.email_providers.base_provider import EmailProvider
from src.utils.logging_config import get_app_logger

logger = get_app_logger()


class ConsoleEmailProvider(EmailProvider):
    """
    Email provider that logs emails instead of sending them.

    Always returns True from send_email(), simulating successful delivery.
    Does not support read_email (raises NotImplementedError).
    """

    def __init__(self) -> None:
        self._configured = False
        self._from_email: Optional[str] = None

    def configure(self, config: Dict[str, Any]) -> None:
        """Accept any configuration without requiring credentials."""
        self._from_email = config.get(
            "default_sender", config.get("from_email", "console@localhost")
        )
        self._configured = True
        logger.info("[Console Provider] Configured — emails will be logged, not sent")

    def validate_configuration(self) -> bool:
        """Always valid once configured."""
        return self._configured

    def send_email(
        self, to_email: str, subject: str, html_body: str, text_body: str
    ) -> bool:
        """Log the email and return True (simulated success)."""
        logger.info(
            f"[Console Provider] SIMULATED SEND: "
            f"to={to_email}, subject={subject!r}, "
            f"text_length={len(text_body)}, html_length={len(html_body)}"
        )
        return True

    def read_email(
        self,
        recipient_email: str,
        subject_substring: Optional[str] = None,
        unique_identifier: Optional[str] = None,
        timeout: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """Console provider cannot read emails."""
        raise NotImplementedError(
            "ConsoleEmailProvider does not support reading emails"
        )
