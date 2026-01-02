"""
Unit tests for email provider factory
"""

import os
from unittest.mock import patch

import pytest

from src.email_providers.brevo_provider import BrevoProvider
from src.email_providers.ethereal_provider import EtherealProvider
from src.email_providers.factory import create_email_provider


class TestEmailProviderFactory:
    """Test email provider factory"""

    @patch.dict(
        os.environ,
        {
            "EMAIL_PROVIDER": "ethereal",  # Explicit selection
            "ETHEREAL_USER": "test@ethereal.email",
            "ETHEREAL_PASS": "testpass",
        },
        clear=False,
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

    @patch.dict(
        os.environ,
        {
            "EMAIL_PROVIDER": "brevo",  # Explicit provider selection
            "BREVO_API_KEY": "test-api-key",
        },
        clear=False,
    )
    def test_create_brevo_provider_from_environment(self):
        """Test creating Brevo provider from environment variables"""
        provider = create_email_provider()
        assert isinstance(provider, BrevoProvider)
        assert provider.validate_configuration()

    def test_create_brevo_provider_explicitly(self):
        """Test creating Brevo provider explicitly"""
        config = {
            "api_key": "test-api-key",
            "sender_email": "test@example.com",
            "sender_name": "Test Sender",
        }

        provider = create_email_provider("brevo", config)
        assert isinstance(provider, BrevoProvider)
        assert provider.validate_configuration()

    @patch.dict(
        os.environ,
        {
            "EMAIL_PROVIDER": "",  # Clear explicit override to test env mapping
            "ENV": "test",
            "ETHEREAL_USER": "test@ethereal.email",
            "ETHEREAL_PASS": "testpass",
        },
        clear=False,
    )
    def test_environment_based_mapping_test_env(self):
        """Test that ENV=test automatically selects Ethereal"""
        provider = create_email_provider()
        assert isinstance(provider, EtherealProvider)

    @patch.dict(
        os.environ,
        {
            "EMAIL_PROVIDER": "",  # Clear explicit override to test env mapping
            "ENV": "development",
            "BREVO_API_KEY": "test-api-key",
        },
        clear=False,
    )
    def test_environment_based_mapping_development_env(self):
        """Test that ENV=development automatically selects Brevo"""
        provider = create_email_provider()
        assert isinstance(provider, BrevoProvider)

    @patch.dict(
        os.environ,
        {
            "EMAIL_PROVIDER": "ethereal",  # Explicit override
            "ENV": "production",  # Would normally select Brevo
            "ETHEREAL_USER": "test@ethereal.email",
            "ETHEREAL_PASS": "testpass",
        },
        clear=False,
    )
    def test_explicit_provider_overrides_environment_mapping(self):
        """Test that EMAIL_PROVIDER overrides environment-based mapping"""
        provider = create_email_provider()
        assert isinstance(provider, EtherealProvider)

    def test_invalid_provider_name(self):
        """Test that invalid provider name raises error"""
        with pytest.raises(ValueError, match="Unknown email provider"):
            create_email_provider("nonexistent")
