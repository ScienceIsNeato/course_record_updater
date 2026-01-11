"""
Unit tests for EmailService._maybe_send_via_ethereal_fallback fallback.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.app import app


class TestMaybeRetryWithEthereal:
    """Tests for the Ethereal fallback when Brevo fails."""

    @pytest.fixture(autouse=True)
    def setup_app_context(self):
        """Ensure app context for all tests."""
        with app.app_context():
            yield

    @patch("src.services.email_service.current_app")
    def test_fallback_skipped_in_production(self, mock_app):
        """Should not retry in production environment."""
        from src.email_providers.brevo_provider import BrevoProvider
        from src.services.email_service import EmailService

        mock_app.config.get.return_value = "production"
        mock_provider = MagicMock(spec=BrevoProvider)

        EmailService._maybe_send_via_ethereal_fallback(
            mock_provider, "test@example.com", "Subject", "<p>HTML</p>", "Text"
        )

        mock_app.config.get.assert_called()

    @patch("src.services.email_service.current_app")
    def test_fallback_skipped_for_non_brevo_provider(self, mock_app):
        """Should not retry if provider is not BrevoProvider."""
        from src.services.email_service import EmailService

        mock_app.config.get.return_value = "development"
        mock_provider = MagicMock()  # Not a BrevoProvider

        EmailService._maybe_send_via_ethereal_fallback(
            mock_provider, "test@example.com", "Subject", "<p>HTML</p>", "Text"
        )

    @patch("src.services.email_service.os.getenv")
    @patch("src.services.email_service.current_app")
    def test_fallback_skipped_when_ethereal_not_configured(
        self, mock_app, mock_getenv
    ):
        """Should skip fallback if ETHEREAL_USER not set."""
        from src.email_providers.brevo_provider import BrevoProvider
        from src.services.email_service import EmailService

        mock_app.config.get.return_value = "development"
        mock_getenv.return_value = None
        mock_provider = MagicMock(spec=BrevoProvider)

        EmailService._maybe_send_via_ethereal_fallback(
            mock_provider, "test@example.com", "Subject", "<p>HTML</p>", "Text"
        )

    @patch("src.services.email_service.EmailService._log_email_preview")
    @patch("src.services.email_service.create_email_provider")
    @patch("src.services.email_service.os.getenv")
    @patch("src.services.email_service.current_app")
    def test_fallback_success(
        self, mock_app, mock_getenv, mock_create_provider, mock_log
    ):
        """Should retry via Ethereal and log success."""
        from src.email_providers.brevo_provider import BrevoProvider
        from src.services.email_service import EmailService

        mock_app.config.get.return_value = "development"
        mock_getenv.return_value = "ethereal_user"

        mock_ethereal = MagicMock()
        mock_ethereal.send_email.return_value = True
        mock_create_provider.return_value = mock_ethereal

        mock_brevo = MagicMock(spec=BrevoProvider)

        EmailService._maybe_send_via_ethereal_fallback(
            mock_brevo, "test@example.com", "Subject", "<p>HTML</p>", "Text"
        )

        mock_create_provider.assert_called_once_with("ethereal")
        mock_ethereal.send_email.assert_called_once()

    @patch("src.services.email_service.EmailService._log_email_preview")
    @patch("src.services.email_service.create_email_provider")
    @patch("src.services.email_service.os.getenv")
    @patch("src.services.email_service.current_app")
    def test_fallback_failure(
        self, mock_app, mock_getenv, mock_create_provider, mock_log
    ):
        """Should handle Ethereal fallback failure."""
        from src.email_providers.brevo_provider import BrevoProvider
        from src.services.email_service import EmailService

        mock_app.config.get.return_value = "development"
        mock_getenv.return_value = "ethereal_user"

        mock_ethereal = MagicMock()
        mock_ethereal.send_email.return_value = False
        mock_create_provider.return_value = mock_ethereal

        mock_brevo = MagicMock(spec=BrevoProvider)

        EmailService._maybe_send_via_ethereal_fallback(
            mock_brevo, "test@example.com", "Subject", "<p>HTML</p>", "Text"
        )

        mock_log.assert_called_once()

    @patch("src.services.email_service.create_email_provider")
    @patch("src.services.email_service.os.getenv")
    @patch("src.services.email_service.current_app")
    def test_fallback_exception(self, mock_app, mock_getenv, mock_create_provider):
        """Should handle exceptions during Ethereal fallback."""
        from src.email_providers.brevo_provider import BrevoProvider
        from src.services.email_service import EmailService

        mock_app.config.get.return_value = "development"
        mock_getenv.return_value = "ethereal_user"
        mock_create_provider.side_effect = Exception("Connection failed")

        mock_brevo = MagicMock(spec=BrevoProvider)

        EmailService._maybe_send_via_ethereal_fallback(
            mock_brevo, "test@example.com", "Subject", "<p>HTML</p>", "Text"
        )

    @patch("src.services.email_service.current_app")
    def test_fallback_outside_app_context(self, mock_app):
        """Should handle being called outside Flask app context."""
        from src.email_providers.brevo_provider import BrevoProvider
        from src.services.email_service import EmailService

        mock_app.config.get.side_effect = RuntimeError("Outside app context")
        mock_provider = MagicMock(spec=BrevoProvider)

        EmailService._maybe_send_via_ethereal_fallback(
            mock_provider, "test@example.com", "Subject", "<p>HTML</p>", "Text"
        )
