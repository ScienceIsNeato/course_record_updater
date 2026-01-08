"""
Unit tests for BrevoProvider
"""

import os
from unittest.mock import Mock, patch

import pytest

from src.email_providers.brevo_provider import BrevoProvider


class TestBrevoProviderConfiguration:
    """Test BrevoProvider configuration and validation"""

    def test_initialization(self):
        """Test provider initialization"""
        provider = BrevoProvider()
        assert not provider.validate_configuration()

    def test_configuration(self):
        """Test provider configuration"""
        provider = BrevoProvider()
        config = {
            "api_key": "test-api-key",
            "sender_email": "test@example.com",
            "sender_name": "Test Sender",
        }
        provider.configure(config)
        assert provider.validate_configuration()

    @patch.dict("os.environ", {"BREVO_API_KEY": ""}, clear=False)
    def test_configuration_requires_api_key(self):
        """Test that configuration requires API key"""
        provider = BrevoProvider()
        config = {
            "sender_email": "test@example.com",
            "sender_name": "Test Sender",
        }
        with pytest.raises(ValueError, match="api_key"):
            provider.configure(config)

    def test_configuration_requires_sender_email(self):
        """Test that configuration requires sender email"""
        provider = BrevoProvider()
        config = {
            "api_key": "test-api-key",
            "sender_name": "Test Sender",
        }
        with pytest.raises(ValueError, match="sender_email"):
            provider.configure(config)


class TestBrevoProviderSending:
    """Test BrevoProvider email sending (with mocked API)"""

    @patch("src.email_providers.brevo_provider.requests.post")
    def test_send_email_success(self, mock_post):
        """Test successful email sending"""
        mock_post.return_value = Mock(
            status_code=201, json=lambda: {"messageId": "test-id"}
        )

        provider = BrevoProvider()
        provider.configure(
            {
                "api_key": "test-api-key",
                "sender_email": "sender@example.com",
                "sender_name": "Test Sender",
            }
        )

        result = provider.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            html_body="<p>Test HTML</p>",
            text_body="Test Text",
        )

        assert result is True
        mock_post.assert_called_once()

    @patch("src.email_providers.brevo_provider.requests.post")
    def test_send_email_api_error(self, mock_post):
        """Test email sending with API error"""
        mock_post.return_value = Mock(status_code=400, text="Bad Request")

        provider = BrevoProvider()
        provider.configure(
            {
                "api_key": "test-api-key",
                "sender_email": "sender@example.com",
                "sender_name": "Test Sender",
            }
        )

        result = provider.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            html_body="<p>Test HTML</p>",
            text_body="Test Text",
        )

        assert result is False

    def test_send_email_without_configuration(self):
        """Test that sending email without configuration fails"""
        provider = BrevoProvider()

        result = provider.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            html_body="<p>Test HTML</p>",
            text_body="Test Text",
        )

        assert result is False

    def test_read_email_not_implemented(self):
        """Test that read_email raises NotImplementedError"""
        provider = BrevoProvider()

        with pytest.raises(NotImplementedError):
            provider.read_email("test@example.com")
