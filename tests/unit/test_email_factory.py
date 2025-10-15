"""
Unit tests for email provider factory
"""

import os
from unittest.mock import patch

import pytest

from email_providers.ethereal_provider import EtherealProvider
from email_providers.factory import create_email_provider


class TestEmailProviderFactory:
    """Test email provider factory"""

    @patch.dict(
        os.environ,
        {"ETHEREAL_USER": "test@ethereal.email", "ETHEREAL_PASS": "testpass"},
    )
    def test_create_ethereal_provider_from_environment(self):
        """Test creating Ethereal provider from environment variables"""
        provider = create_email_provider()
        assert isinstance(provider, EtherealProvider)
        assert provider.validate_configuration()

    def test_create_ethereal_provider_explicitly(self):
        """Test creating Ethereal provider explicitly"""
        config = {
            "username": "test@ethereal.email",
            "password": "testpass",
            "smtp_host": "smtp.ethereal.email",
            "smtp_port": 587,
        }

        provider = create_email_provider("ethereal", config)
        assert isinstance(provider, EtherealProvider)
        assert provider.validate_configuration()

    def test_invalid_provider_name(self):
        """Test that invalid provider name raises error"""
        with pytest.raises(ValueError, match="Unknown email provider"):
            create_email_provider("nonexistent")
