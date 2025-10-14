"""
Unit tests for MailtrapProvider

Tests the Mailtrap email provider without actually sending emails.
All SMTP calls are mocked.
"""

from unittest.mock import MagicMock, patch

import pytest

from email_providers.mailtrap_provider import MailtrapProvider


class TestMailtrapProviderConfiguration:
    """Test MailtrapProvider configuration and validation"""

    def test_default_initialization(self):
        """Test provider initializes with default state"""
        provider = MailtrapProvider()

        assert provider._configured is False
        assert provider._server is None
        assert provider._username is None
        assert provider._password is None

    def test_configure_with_defaults(self):
        """Test configuration with default Mailtrap settings"""
        provider = MailtrapProvider()

        config = {"username": "test-user", "password": "test-pass"}

        provider.configure(config)

        assert provider._configured is True
        assert provider._server == "sandbox.smtp.mailtrap.io"
        assert provider._port == 2525
        assert provider._username == "test-user"
        assert provider._password == "test-pass"

    def test_configure_with_custom_settings(self):
        """Test configuration with custom Mailtrap settings"""
        provider = MailtrapProvider()

        config = {
            "server": "custom.mailtrap.io",
            "port": 587,
            "username": "custom-user",
            "password": "custom-pass",
            "default_sender": "test@example.com",
            "default_sender_name": "Test Sender",
        }

        provider.configure(config)

        assert provider._server == "custom.mailtrap.io"
        assert provider._port == 587
        assert provider._username == "custom-user"
        assert provider._password == "custom-pass"
        assert provider._default_sender == "test@example.com"
        assert provider._default_sender_name == "Test Sender"

    def test_validate_configuration_success(self):
        """Test validation succeeds with complete config"""
        provider = MailtrapProvider()

        config = {"username": "test-user", "password": "test-pass"}

        provider.configure(config)

        assert provider.validate_configuration() is True

    def test_validate_configuration_not_configured(self):
        """Test validation fails if not configured"""
        provider = MailtrapProvider()

        assert provider.validate_configuration() is False

    def test_validate_configuration_missing_username(self):
        """Test validation fails if username missing"""
        provider = MailtrapProvider()

        config = {"password": "test-pass"}

        provider.configure(config)

        assert provider.validate_configuration() is False

    def test_validate_configuration_missing_password(self):
        """Test validation fails if password missing"""
        provider = MailtrapProvider()

        config = {"username": "test-user"}

        provider.configure(config)

        assert provider.validate_configuration() is False


class TestMailtrapProviderSending:
    """Test MailtrapProvider email sending (with mocked SMTP)"""

    @pytest.fixture
    def configured_provider(self):
        """Fixture for configured Mailtrap provider"""
        provider = MailtrapProvider()
        config = {
            "server": "sandbox.smtp.mailtrap.io",
            "port": 2525,
            "username": "test-user",
            "password": "test-pass",
            "default_sender": "test@lassietests.mailtrap.io",
            "default_sender_name": "Test System",
        }
        provider.configure(config)
        return provider

    @patch("email_providers.mailtrap_provider.smtplib.SMTP")
    def test_send_email_success(self, mock_smtp_class, configured_provider):
        """Test successful email sending via Mailtrap"""
        # Mock SMTP connection
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        # Send email
        success = configured_provider.send_email(
            to_email="recipient@lassietests.mailtrap.io",
            subject="Test Subject",
            html_body="<p>HTML Body</p>",
            text_body="Text Body",
        )

        # Verify success
        assert success is True

        # Verify SMTP connection
        mock_smtp_class.assert_called_once_with("sandbox.smtp.mailtrap.io", 2525)

        # Verify authentication
        mock_server.login.assert_called_once_with("test-user", "test-pass")

        # Verify message sent
        mock_server.send_message.assert_called_once()

        # Verify connection closed
        mock_server.quit.assert_called_once()

    @patch("email_providers.mailtrap_provider.smtplib.SMTP")
    def test_send_email_with_correct_headers(
        self, mock_smtp_class, configured_provider
    ):
        """Test email has correct headers"""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        configured_provider.send_email(
            to_email="recipient@lassietests.mailtrap.io",
            subject="Test Subject",
            html_body="<p>HTML</p>",
            text_body="Text",
        )

        # Get the message that was sent
        call_args = mock_server.send_message.call_args
        msg = call_args[0][0]

        # Verify headers
        assert msg["Subject"] == "Test Subject"
        assert msg["To"] == "recipient@lassietests.mailtrap.io"
        assert "Test System <test@lassietests.mailtrap.io>" in msg["From"]

    @patch("email_providers.mailtrap_provider.smtplib.SMTP")
    def test_send_email_authentication_error(
        self, mock_smtp_class, configured_provider
    ):
        """Test handling of authentication errors"""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        # Simulate authentication failure
        import smtplib

        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(
            535, b"Authentication failed"
        )

        success = configured_provider.send_email(
            to_email="recipient@lassietests.mailtrap.io",
            subject="Test",
            html_body="<p>HTML</p>",
            text_body="Text",
        )

        assert success is False

    @patch("email_providers.mailtrap_provider.smtplib.SMTP")
    def test_send_email_smtp_exception(self, mock_smtp_class, configured_provider):
        """Test handling of generic SMTP errors"""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        # Simulate SMTP exception
        import smtplib

        mock_server.send_message.side_effect = smtplib.SMTPException("SMTP error")

        success = configured_provider.send_email(
            to_email="recipient@lassietests.mailtrap.io",
            subject="Test",
            html_body="<p>HTML</p>",
            text_body="Text",
        )

        assert success is False

    @patch("email_providers.mailtrap_provider.smtplib.SMTP")
    def test_send_email_generic_exception(self, mock_smtp_class, configured_provider):
        """Test handling of unexpected exceptions"""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        # Simulate unexpected exception
        mock_server.send_message.side_effect = Exception("Unexpected error")

        success = configured_provider.send_email(
            to_email="recipient@lassietests.mailtrap.io",
            subject="Test",
            html_body="<p>HTML</p>",
            text_body="Text",
        )

        assert success is False

    @patch("email_providers.mailtrap_provider.smtplib.SMTP")
    def test_send_email_no_authentication(self, mock_smtp_class, configured_provider):
        """Test sending without authentication (if credentials not set)"""
        # Configure provider without credentials
        provider = MailtrapProvider()
        config = {
            "server": "sandbox.smtp.mailtrap.io",
            "port": 2525,
            "default_sender": "test@lassietests.mailtrap.io",
        }
        provider.configure(config)

        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        provider.send_email(
            to_email="recipient@lassietests.mailtrap.io",
            subject="Test",
            html_body="<p>HTML</p>",
            text_body="Text",
        )

        # Login should not be called if no credentials
        mock_server.login.assert_not_called()

        # But message should still be sent
        mock_server.send_message.assert_called_once()
