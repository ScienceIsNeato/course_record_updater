"""Unit tests for Ethereal Provider send_email (mocked SMTP)."""

import smtplib
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.email_providers.ethereal_provider import EtherealProvider


class TestEtherealProviderSending:
    """Test Ethereal Provider email sending with mocked SMTP"""

    @patch("src.email_providers.ethereal_provider.smtplib.SMTP")
    def test_send_email_success(self, mock_smtp_class: Any) -> None:
        """Test successful email sending via Ethereal"""
        # Setup mock
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        provider = EtherealProvider()
        provider.configure(
            {
                "smtp_host": "smtp.ethereal.email",
                "smtp_port": 587,
                "username": "test@ethereal.email",
                "password": "testpass",
                "from_email": "test@ethereal.email",
            }
        )

        result = provider.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            html_body="<p>Test HTML</p>",
            text_body="Test Text",
        )

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@ethereal.email", "testpass")
        mock_server.send_message.assert_called_once()

    def test_send_email_without_configuration(self) -> None:
        """Test that sending without configuration fails"""
        provider = EtherealProvider()

        result = provider.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            html_body="<p>Test HTML</p>",
            text_body="Test Text",
        )

        assert result is False

    @patch("src.email_providers.ethereal_provider.smtplib.SMTP")
    def test_send_email_smtp_error(self, mock_smtp_class: Any) -> None:
        """Test email sending with SMTP error"""
        # Setup mock to raise exception
        mock_smtp_class.return_value.__enter__.side_effect = Exception("SMTP Error")

        provider = EtherealProvider()
        provider.configure(
            {
                "smtp_host": "smtp.ethereal.email",
                "smtp_port": 587,
                "username": "test@ethereal.email",
                "password": "testpass",
                "from_email": "test@ethereal.email",
            }
        )

        with pytest.raises(Exception, match="SMTP Error"):
            provider.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_body="<p>Test HTML</p>",
                text_body="Test Text",
            )

    @patch("src.email_providers.ethereal_provider.time.sleep")
    @patch("src.email_providers.ethereal_provider.smtplib.SMTP")
    def test_send_email_retries_rate_limited_recipient_error(
        self, mock_smtp_class: Any, mock_sleep: Any
    ) -> None:
        """Retry transient Ethereal rate limits instead of failing immediately."""
        mock_server = MagicMock()
        mock_server.send_message.side_effect = [
            smtplib.SMTPRecipientsRefused(
                {"recipient@example.com": (429, b"Rate limited")}
            ),
            None,
        ]
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        provider = EtherealProvider()
        provider.configure(
            {
                "smtp_host": "smtp.ethereal.email",
                "smtp_port": 587,
                "username": "test@ethereal.email",
                "password": "testpass",
                "from_email": "test@ethereal.email",
            }
        )

        result = provider.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            html_body="<p>Test HTML</p>",
            text_body="Test Text",
        )

        assert result is True
        assert mock_server.send_message.call_count == 2
        mock_sleep.assert_called_once_with(2)

    @patch("src.email_providers.ethereal_provider.time.sleep")
    @patch("src.email_providers.ethereal_provider.smtplib.SMTP")
    def test_send_email_does_not_retry_non_retryable_smtp_error(
        self, mock_smtp_class: Any, mock_sleep: Any
    ) -> None:
        """Do not hide terminal SMTP errors behind retries."""
        mock_server = MagicMock()
        mock_server.send_message.side_effect = smtplib.SMTPDataError(
            550, b"Mailbox unavailable"
        )
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        provider = EtherealProvider()
        provider.configure(
            {
                "smtp_host": "smtp.ethereal.email",
                "smtp_port": 587,
                "username": "test@ethereal.email",
                "password": "testpass",
                "from_email": "test@ethereal.email",
            }
        )

        with pytest.raises(smtplib.SMTPDataError):
            provider.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_body="<p>Test HTML</p>",
                text_body="Test Text",
            )

        mock_sleep.assert_not_called()
        assert mock_server.send_message.call_count == 1
