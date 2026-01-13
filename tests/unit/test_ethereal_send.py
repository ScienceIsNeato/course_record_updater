"""
Unit tests for Ethereal Provider send_email (mocked SMTP)
"""

from unittest.mock import MagicMock, patch

import pytest

from src.email_providers.ethereal_provider import EtherealProvider


class TestEtherealProviderSending:
    """Test Ethereal Provider email sending with mocked SMTP"""

    @patch("src.email_providers.ethereal_provider.smtplib.SMTP")
    def test_send_email_success(self, mock_smtp_class):
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

    def test_send_email_without_configuration(self):
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
    def test_send_email_smtp_error(self, mock_smtp_class):
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
