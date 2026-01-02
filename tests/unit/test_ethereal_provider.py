"""
Unit tests for Ethereal Email provider
"""

import pytest

from src.email_providers.ethereal_provider import EtherealProvider


class TestEtherealProvider:
    """Test Ethereal Email provider"""

    def test_initialization(self):
        """Test provider initialization"""
        provider = EtherealProvider()
        assert provider is not None
        assert not provider.validate_configuration()

    def test_configuration(self):
        """Test provider configuration"""
        provider = EtherealProvider()

        config = {
            "username": "test@ethereal.email",
            "password": "testpass",
            "smtp_host": "smtp.ethereal.email",
            "smtp_port": 587,
        }

        provider.configure(config)
        assert provider.validate_configuration()

    def test_configuration_requires_credentials(self):
        """Test that configuration requires username and password"""
        provider = EtherealProvider()

        with pytest.raises(ValueError, match="username.*password"):
            provider.configure({})

    def test_send_email_without_configuration(self):
        """Test that send_email fails if not configured"""
        provider = EtherealProvider()

        result = provider.send_email(
            to_email="test@example.com",
            subject="Test",
            html_body="<p>Test</p>",
            text_body="Test",
        )

        assert result is False
