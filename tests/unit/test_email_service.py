"""
Unit tests for Email Service

Tests email functionality including templates, SMTP integration, and
CRITICAL PROTECTION against sending emails to CEI/protected domains.
"""

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from email_service import (
    EmailService,
    EmailServiceError,
    send_invitation_email,
    send_password_reset_email,
    send_verification_email,
    send_welcome_email,
)


@pytest.fixture
def app():
    """Create Flask app for testing"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True
    app.config["MAIL_SUPPRESS_SEND"] = True  # Always suppress in tests
    app.config["BASE_URL"] = "http://localhost:5000"

    # Configure email service
    EmailService.configure_app(app)

    return app


@pytest.fixture
def app_context(app):
    """Create app context for testing"""
    with app.app_context():
        yield app


class TestEmailProtection:
    """Test critical protection against sending emails to CEI/protected domains"""

    def test_protected_domain_detection_cei_edu(self):
        """Test detection of cei.edu domain"""
        assert EmailService._is_protected_email("test@cei.edu") is True
        assert EmailService._is_protected_email("admin@cei.edu") is True
        assert EmailService._is_protected_email("student@cei.edu") is True

    def test_protected_domain_detection_coastal_domains(self):
        """Test detection of coastal education domains"""
        assert EmailService._is_protected_email("test@coastaledu.org") is True
        assert EmailService._is_protected_email("admin@coastal.edu") is True
        assert EmailService._is_protected_email("faculty@coastalcarolina.edu") is True

    def test_protected_domain_detection_subdomains(self):
        """Test detection of subdomains of protected domains"""
        assert EmailService._is_protected_email("test@mail.cei.edu") is True
        assert EmailService._is_protected_email("admin@student.coastal.edu") is True

    def test_safe_domain_detection(self):
        """Test that safe domains are not flagged as protected"""
        assert EmailService._is_protected_email("test@example.com") is False
        assert EmailService._is_protected_email("admin@gmail.com") is False
        assert EmailService._is_protected_email("user@testuniversity.edu") is False
        assert EmailService._is_protected_email("faculty@northernvalley.edu") is False

    def test_invalid_email_handling(self):
        """Test handling of invalid email formats"""
        assert EmailService._is_protected_email("") is False
        assert EmailService._is_protected_email("invalid-email") is False
        assert EmailService._is_protected_email("@cei.edu") is False
        assert EmailService._is_protected_email(None) is False

    def test_protected_email_blocking_verification(self, app_context):
        """Test that verification emails are blocked for protected domains in non-production"""
        with pytest.raises(
            EmailServiceError,
            match="Cannot send emails to protected domain.*in non-production environment",
        ):
            EmailService.send_verification_email(
                email="test@cei.edu",
                verification_token="test-token",
                user_name="Test User",
            )

    def test_protected_email_blocking_password_reset(self, app_context):
        """Test that password reset emails are blocked for protected domains in non-production"""
        with pytest.raises(
            EmailServiceError,
            match="Cannot send emails to protected domain.*in non-production environment",
        ):
            EmailService.send_password_reset_email(
                email="admin@coastal.edu",
                reset_token="reset-token",
                user_name="Admin User",
            )

    def test_protected_email_blocking_invitation(self, app_context):
        """Test that invitation emails are blocked for protected domains in non-production"""
        with pytest.raises(
            EmailServiceError,
            match="Cannot send emails to protected domain.*in non-production environment",
        ):
            EmailService.send_invitation_email(
                email="faculty@coastalcarolina.edu",
                invitation_token="invite-token",
                inviter_name="Test Inviter",
                institution_name="Test Institution",
                role="instructor",
            )

    def test_protected_email_blocking_welcome(self, app_context):
        """Test that welcome emails are blocked for protected domains in non-production"""
        with pytest.raises(
            EmailServiceError,
            match="Cannot send emails to protected domain.*in non-production environment",
        ):
            EmailService.send_welcome_email(
                email="student@cei.edu",
                user_name="Student User",
                institution_name="Test Institution",
            )

    def test_safe_email_sending_verification(self, app_context):
        """Test that verification emails work for safe domains"""
        result = EmailService.send_verification_email(
            email="test@example.com",
            verification_token="test-token",
            user_name="Test User",
        )
        assert result is True  # Should succeed (suppressed in test mode)

    def test_safe_email_sending_convenience_functions(self, app_context):
        """Test that convenience functions also respect protection"""
        # Should work for safe domains
        assert send_verification_email("test@example.com", "token", "User") is True
        assert send_password_reset_email("test@gmail.com", "token", "User") is True
        assert (
            send_invitation_email(
                "test@university.edu", "token", "Inviter", "Institution", "role"
            )
            is True
        )
        assert send_welcome_email("test@company.com", "User", "Institution") is True

        # Should fail for protected domains
        with pytest.raises(EmailServiceError):
            send_verification_email("test@cei.edu", "token", "User")

        with pytest.raises(EmailServiceError):
            send_password_reset_email("test@coastal.edu", "token", "User")

    def test_production_mode_allows_protected_emails(self):
        """Test that production mode allows emails to protected domains"""
        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret-key"
        app.config["TESTING"] = True
        app.config["MAIL_SUPPRESS_SEND"] = True
        app.config["BASE_URL"] = "http://localhost:5000"
        app.config["ENV"] = "production"  # Set production mode

        EmailService.configure_app(app)

        with app.app_context():
            # Should NOT raise exception in production mode
            result = EmailService.send_verification_email(
                email="test@cei.edu",
                verification_token="test-token",
                user_name="Test User",
            )
            assert result is True  # Should succeed (suppressed in test mode)


class TestEmailConfiguration:
    """Test email service configuration"""

    def test_configure_app_sets_defaults(self, app):
        """Test that app configuration sets correct defaults"""
        assert app.config["MAIL_SERVER"] == "localhost"
        assert app.config["MAIL_PORT"] == 587
        assert app.config["MAIL_USE_TLS"] is True
        assert app.config["MAIL_USE_SSL"] is False
        assert app.config["MAIL_DEFAULT_SENDER"] == "noreply@courserecord.app"
        assert app.config["BASE_URL"] == "http://localhost:5000"
        assert app.config["MAIL_SUPPRESS_SEND"] is True

    def test_configure_app_with_env_vars(self):
        """Test configuration with environment variables"""
        app = Flask(__name__)
        app.config["TESTING"] = True

        with patch.dict(
            "os.environ",
            {
                "MAIL_SERVER": "smtp.gmail.com",
                "MAIL_PORT": "465",
                "MAIL_USE_SSL": "true",
                "MAIL_USERNAME": "test@gmail.com",
                "BASE_URL": "https://production.com",
            },
        ):
            EmailService.configure_app(app)

            assert app.config["MAIL_SERVER"] == "smtp.gmail.com"
            assert app.config["MAIL_PORT"] == 465
            assert app.config["MAIL_USE_SSL"] is True
            assert app.config["MAIL_USERNAME"] == "test@gmail.com"
            assert app.config["BASE_URL"] == "https://production.com"


class TestEmailTemplates:
    """Test email template generation"""

    def test_verification_email_html_template(self, app_context):
        """Test HTML verification email template"""
        html = EmailService._render_verification_email_html(
            user_name="John Doe",
            verification_url="http://localhost:5000/verify/token123",
            email="john@example.com",
        )

        assert "John Doe" in html
        assert "http://localhost:5000/verify/token123" in html
        assert "john@example.com" in html
        assert "Verify Email Address" in html
        assert "<!DOCTYPE html>" in html

    def test_verification_email_text_template(self, app_context):
        """Test text verification email template"""
        text = EmailService._render_verification_email_text(
            user_name="Jane Smith",
            verification_url="http://localhost:5000/verify/token456",
            email="jane@example.com",
        )

        assert "Jane Smith" in text
        assert "http://localhost:5000/verify/token456" in text
        assert "jane@example.com" in text
        assert "Course Record Updater" in text

    def test_password_reset_email_templates(self, app_context):
        """Test password reset email templates"""
        html = EmailService._render_password_reset_email_html(
            user_name="Test User",
            reset_url="http://localhost:5000/reset/token789",
            email="test@example.com",
        )

        text = EmailService._render_password_reset_email_text(
            user_name="Test User",
            reset_url="http://localhost:5000/reset/token789",
            email="test@example.com",
        )

        assert "Test User" in html and "Test User" in text
        assert (
            "http://localhost:5000/reset/token789" in html
            and "http://localhost:5000/reset/token789" in text
        )
        assert "Reset Password" in html
        assert "Password Reset" in text

    def test_invitation_email_templates(self, app_context):
        """Test invitation email templates"""
        html = EmailService._render_invitation_email_html(
            email="invitee@example.com",
            invitation_url="http://localhost:5000/accept/token123",
            inviter_name="Admin User",
            institution_name="Test University",
            role="instructor",
            personal_message="Welcome to our team!",
        )

        text = EmailService._render_invitation_email_text(
            email="invitee@example.com",
            invitation_url="http://localhost:5000/accept/token123",
            inviter_name="Admin User",
            institution_name="Test University",
            role="instructor",
            personal_message="Welcome to our team!",
        )

        assert "Admin User" in html and "Admin User" in text
        assert "Test University" in html and "Test University" in text
        assert "Instructor" in html and "Instructor" in text
        assert "Welcome to our team!" in html and "Welcome to our team!" in text
        assert "Accept Invitation" in html

    def test_invitation_email_without_personal_message(self, app_context):
        """Test invitation email templates without personal message"""
        html = EmailService._render_invitation_email_html(
            email="invitee@example.com",
            invitation_url="http://localhost:5000/accept/token123",
            inviter_name="Admin User",
            institution_name="Test University",
            role="program_admin",
            personal_message=None,
        )

        assert "Admin User" in html
        assert "Test University" in html
        assert "Program Admin" in html
        assert "Personal message" not in html

    def test_welcome_email_templates(self, app_context):
        """Test welcome email templates"""
        html = EmailService._render_welcome_email_html(
            user_name="New User",
            institution_name="Welcome University",
            dashboard_url="http://localhost:5000/dashboard",
        )

        text = EmailService._render_welcome_email_text(
            user_name="New User",
            institution_name="Welcome University",
            dashboard_url="http://localhost:5000/dashboard",
        )

        assert "New User" in html and "New User" in text
        assert "Welcome University" in html and "Welcome University" in text
        assert (
            "http://localhost:5000/dashboard" in html
            and "http://localhost:5000/dashboard" in text
        )
        assert "Go to Dashboard" in html


class TestEmailURLBuilding:
    """Test URL building for email links"""

    def test_verification_url_building(self, app_context):
        """Test verification URL building"""
        url = EmailService._build_verification_url("test-token-123")
        assert url == "http://localhost:5000/verify-email/test-token-123"

    def test_password_reset_url_building(self, app_context):
        """Test password reset URL building"""
        url = EmailService._build_password_reset_url("reset-token-456")
        assert url == "http://localhost:5000/reset-password/reset-token-456"

    @patch("email_service.EmailService._send_email")
    def test_send_password_reset_confirmation_email(self, mock_send_email, app_context):
        """Test sending password reset confirmation email (covers lines 212-222)"""
        mock_send_email.return_value = True

        result = EmailService.send_password_reset_confirmation_email(
            user_name="John Doe", email="john@example.com"
        )

        # Should return True for successful send
        assert result is True

        # Verify _send_email was called with correct parameters
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args
        assert call_args[1]["to_email"] == "john@example.com"
        assert call_args[1]["subject"] == "Password Reset Successful"
        assert "html_body" in call_args[1]
        assert "text_body" in call_args[1]

    def test_invitation_url_building(self, app_context):
        """Test invitation URL building"""
        url = EmailService._build_invitation_url("invite-token-789")
        assert url == "http://localhost:5000/register/accept/invite-token-789"

    def test_dashboard_url_building(self, app_context):
        """Test dashboard URL building"""
        url = EmailService._build_dashboard_url()
        assert url == "http://localhost:5000/dashboard"

    def test_url_building_with_custom_base_url(self):
        """Test URL building with custom base URL"""
        app = Flask(__name__)
        app.config["BASE_URL"] = "https://production.courserecord.app"

        with app.app_context():
            verification_url = EmailService._build_verification_url("token")
            reset_url = EmailService._build_password_reset_url("token")
            invitation_url = EmailService._build_invitation_url("token")
            dashboard_url = EmailService._build_dashboard_url()

            assert verification_url.startswith("https://production.courserecord.app")
            assert reset_url.startswith("https://production.courserecord.app")
            assert invitation_url.startswith("https://production.courserecord.app")
            assert dashboard_url.startswith("https://production.courserecord.app")


class TestEmailSuppression:
    """Test email suppression in development mode"""

    def test_email_suppression_enabled(self, app_context):
        """Test that emails are suppressed when MAIL_SUPPRESS_SEND is True"""
        # This should succeed because suppression is enabled in test fixture
        result = EmailService._send_email(
            to_email="test@example.com",
            subject="Test Subject",
            html_body="<p>Test HTML</p>",
            text_body="Test Text",
        )

        assert result is True

    def test_email_suppression_logs_content(self, app_context):
        """Test that suppressed emails log their content"""
        with patch("email_service.logger") as mock_logger:
            EmailService._send_email(
                to_email="test@example.com",
                subject="Test Subject",
                html_body="<p>Test HTML</p>",
                text_body="Test Text Content",
            )

            # Check that info logs were called
            mock_logger.info.assert_called()

            # Verify log messages contain expected content (using parameterized logging)
            # Check all call arguments (both format string and parameters)
            all_log_args = [call.args for call in mock_logger.info.call_args_list]
            assert any(
                "Email suppressed (dev mode)" in args[0] for args in all_log_args
            )
            assert any(
                len(args) > 1 and "Test Text Content" in str(args)
                for args in all_log_args
            )


class TestSMTPSending:
    """Test actual SMTP sending logic (not suppressed)"""

    def test_smtp_ssl_connection(self):
        """Test SMTP SSL connection and sending"""
        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret-key"
        app.config["TESTING"] = True
        app.config["MAIL_SUPPRESS_SEND"] = False  # Enable actual sending
        app.config["BASE_URL"] = "http://localhost:5000"
        app.config["MAIL_SERVER"] = "smtp.gmail.com"
        app.config["MAIL_PORT"] = 465
        app.config["MAIL_USE_SSL"] = True
        app.config["MAIL_USE_TLS"] = False
        app.config["MAIL_USERNAME"] = "test@gmail.com"
        app.config["MAIL_PASSWORD"] = "test-password"
        app.config["MAIL_DEFAULT_SENDER"] = "noreply@test.com"
        app.config["MAIL_DEFAULT_SENDER_NAME"] = "Test Service"

        EmailService.configure_app(app)

        with app.app_context():
            with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
                mock_server = MagicMock()
                mock_smtp_ssl.return_value = mock_server

                result = EmailService._send_email(
                    to_email="recipient@example.com",
                    subject="Test Subject",
                    html_body="<p>Test HTML</p>",
                    text_body="Test Text",
                )

                assert result is True
                mock_smtp_ssl.assert_called_once_with("smtp.gmail.com", 465)
                mock_server.login.assert_called_once_with(
                    "test@gmail.com", "test-password"
                )
                mock_server.send_message.assert_called_once()
                mock_server.quit.assert_called_once()

    def test_smtp_tls_connection(self):
        """Test SMTP TLS connection and sending"""
        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret-key"
        app.config["TESTING"] = True
        app.config["MAIL_SUPPRESS_SEND"] = False  # Enable actual sending
        app.config["BASE_URL"] = "http://localhost:5000"
        app.config["MAIL_SERVER"] = "smtp.mailgun.org"
        app.config["MAIL_PORT"] = 587
        app.config["MAIL_USE_SSL"] = False
        app.config["MAIL_USE_TLS"] = True
        app.config["MAIL_USERNAME"] = "test@mailgun.org"
        app.config["MAIL_PASSWORD"] = "mailgun-password"

        EmailService.configure_app(app)

        with app.app_context():
            with patch("smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value = mock_server

                result = EmailService._send_email(
                    to_email="recipient@example.com",
                    subject="Test Subject",
                    html_body="<p>Test HTML</p>",
                    text_body="Test Text",
                )

                assert result is True
                mock_smtp.assert_called_once_with("smtp.mailgun.org", 587)
                mock_server.starttls.assert_called_once()
                mock_server.login.assert_called_once_with(
                    "test@mailgun.org", "mailgun-password"
                )
                mock_server.send_message.assert_called_once()
                mock_server.quit.assert_called_once()

    def test_smtp_no_auth_connection(self):
        """Test SMTP connection without authentication"""
        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret-key"
        app.config["TESTING"] = True
        app.config["MAIL_SUPPRESS_SEND"] = False  # Enable actual sending
        app.config["BASE_URL"] = "http://localhost:5000"
        app.config["MAIL_SERVER"] = "localhost"
        app.config["MAIL_PORT"] = 25
        app.config["MAIL_USE_SSL"] = False
        app.config["MAIL_USE_TLS"] = False
        # No username/password for local SMTP

        EmailService.configure_app(app)

        with app.app_context():
            with patch("smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value = mock_server

                result = EmailService._send_email(
                    to_email="recipient@example.com",
                    subject="Test Subject",
                    html_body="<p>Test HTML</p>",
                    text_body="Test Text",
                )

                assert result is True
                mock_smtp.assert_called_once_with("localhost", 25)
                mock_server.starttls.assert_not_called()  # TLS disabled
                mock_server.login.assert_not_called()  # No auth
                mock_server.send_message.assert_called_once()
                mock_server.quit.assert_called_once()

    def test_smtp_message_formatting(self):
        """Test SMTP message formatting with proper headers"""
        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret-key"
        app.config["TESTING"] = True
        app.config["MAIL_SUPPRESS_SEND"] = False  # Enable actual sending
        app.config["BASE_URL"] = "http://localhost:5000"
        app.config["MAIL_SERVER"] = "localhost"
        app.config["MAIL_PORT"] = 587
        app.config["MAIL_DEFAULT_SENDER"] = "noreply@courserecord.app"
        app.config["MAIL_DEFAULT_SENDER_NAME"] = "Course Record System"

        EmailService.configure_app(app)

        with app.app_context():
            with patch("smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value = mock_server

                EmailService._send_email(
                    to_email="recipient@example.com",
                    subject="Test Email Subject",
                    html_body="<h1>HTML Content</h1>",
                    text_body="Plain text content",
                )

                # Verify send_message was called with proper message
                mock_server.send_message.assert_called_once()
                sent_message = mock_server.send_message.call_args[0][0]

                assert sent_message["Subject"] == "Test Email Subject"
                assert (
                    sent_message["From"]
                    == "Course Record System <noreply@courserecord.app>"
                )
                assert sent_message["To"] == "recipient@example.com"

    def test_smtp_connection_error_handling(self):
        """Test SMTP connection error handling"""
        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret-key"
        app.config["TESTING"] = True
        app.config["MAIL_SUPPRESS_SEND"] = False  # Enable actual sending
        app.config["BASE_URL"] = "http://localhost:5000"
        app.config["MAIL_SERVER"] = "smtp.gmail.com"
        app.config["MAIL_PORT"] = 465
        app.config["MAIL_USE_SSL"] = True

        EmailService.configure_app(app)

        with app.app_context():
            with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
                mock_smtp_ssl.side_effect = Exception("Connection failed")

                with patch("email_service.logger") as mock_logger:
                    result = EmailService._send_email(
                        to_email="recipient@example.com",
                        subject="Test Subject",
                        html_body="<p>Test HTML</p>",
                        text_body="Test Text",
                    )

                    # Should return False on connection failure
                    assert result is False

                    # Should log the error
                    mock_logger.error.assert_called_once()
                    error_call = mock_logger.error.call_args[0][0]
                    assert "Failed to send email to" in error_call
                    assert "Connection failed" in error_call

    def test_smtp_authentication_error_handling(self):
        """Test SMTP authentication error handling"""
        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret-key"
        app.config["TESTING"] = True
        app.config["MAIL_SUPPRESS_SEND"] = False  # Enable actual sending
        app.config["BASE_URL"] = "http://localhost:5000"
        app.config["MAIL_SERVER"] = "smtp.gmail.com"
        app.config["MAIL_PORT"] = 587
        app.config["MAIL_USE_TLS"] = True
        app.config["MAIL_USERNAME"] = "test@gmail.com"
        app.config["MAIL_PASSWORD"] = "wrong-password"

        EmailService.configure_app(app)

        with app.app_context():
            with patch("smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_server.login.side_effect = Exception("Authentication failed")
                mock_smtp.return_value = mock_server

                with patch("email_service.logger") as mock_logger:
                    result = EmailService._send_email(
                        to_email="recipient@example.com",
                        subject="Test Subject",
                        html_body="<p>Test HTML</p>",
                        text_body="Test Text",
                    )

                    # Should return False on authentication failure
                    assert result is False

                    # Should log the error
                    mock_logger.error.assert_called_once()
                    error_call = mock_logger.error.call_args[0][0]
                    assert "Failed to send email to" in error_call
                    assert "Authentication failed" in error_call


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_convenience_functions_exist(self):
        """Test that all convenience functions are available"""
        assert callable(send_verification_email)
        assert callable(send_password_reset_email)
        assert callable(send_invitation_email)
        assert callable(send_welcome_email)

    def test_convenience_functions_work(self, app_context):
        """Test that convenience functions work correctly"""
        # These should all succeed with suppression enabled
        assert send_verification_email("test@example.com", "token", "User") is True
        assert send_password_reset_email("test@example.com", "token", "User") is True
        assert (
            send_invitation_email(
                "test@example.com", "token", "Inviter", "Institution", "role"
            )
            is True
        )
        assert send_welcome_email("test@example.com", "User", "Institution") is True
