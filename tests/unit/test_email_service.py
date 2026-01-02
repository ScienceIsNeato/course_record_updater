"""
Unit tests for Email Service

Tests email functionality including templates, SMTP integration, and
CRITICAL PROTECTION against sending emails to real institution/protected domains.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from flask import Flask

from src.services.email_service import (
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


@pytest.fixture(autouse=True)
def mock_whitelist():
    """Mock whitelist to allow all emails by default in tests."""
    with patch("email_providers.get_email_whitelist") as mock_get_wl:
        whitelist = Mock()
        whitelist.is_allowed.return_value = True
        mock_get_wl.return_value = whitelist
        yield mock_get_wl


class TestEmailProtection:
    """Test critical protection against sending emails to real institution/protected domains"""

    def test_protected_domain_detection_cei_test(self):
        """Test detection of cei.test domain"""
        assert EmailService._is_protected_email("test@cei.test") is True
        assert EmailService._is_protected_email("admin@cei.test") is True
        assert EmailService._is_protected_email("student@cei.test") is True

    def test_protected_domain_detection_coastal_domains(self):
        """Test detection of coastal education domains"""
        assert EmailService._is_protected_email("test@coastaledu.org") is True
        assert EmailService._is_protected_email("admin@coastal.edu") is True
        assert EmailService._is_protected_email("faculty@coastalcarolina.edu") is True

    def test_protected_domain_detection_subdomains(self):
        """Test detection of subdomains of protected domains"""
        assert EmailService._is_protected_email("test@mail.cei.test") is True
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
        assert EmailService._is_protected_email("@cei.test") is False
        assert EmailService._is_protected_email(None) is False

    def test_protected_email_blocking_verification(self, app_context):
        """Test that verification emails are blocked for protected domains in non-production"""
        with pytest.raises(
            EmailServiceError,
            match="Cannot send emails to protected domain.*in non-production environment",
        ):
            EmailService.send_verification_email(
                email="test@cei.test",
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
                email="student@cei.test",
                user_name="Student User",
                institution_name="Test Institution",
            )

    def test_whitelist_blocking(self, app_context):
        """Test blocking by whitelist integration."""
        with patch("email_providers.get_email_whitelist") as mock_get_wl:
            whitelist = Mock()
            whitelist.is_allowed.return_value = False
            whitelist.get_blocked_reason.return_value = "Blocked by whitelist logic"
            mock_get_wl.return_value = whitelist

            with pytest.raises(EmailServiceError, match="Blocked by whitelist logic"):
                EmailService._send_email(
                    to_email="test@blocked.com",
                    subject="Test",
                    html_body="Body",
                    text_body="Text",
                )

    @patch("email_service.create_email_provider")
    def test_safe_email_sending_verification(self, mock_create_provider, app_context):
        """Test that verification emails work for safe domains"""
        # Mock provider
        mock_provider = Mock()
        mock_provider.send_email.return_value = True
        mock_create_provider.return_value = mock_provider

        result = EmailService.send_verification_email(
            email="test@example.com",
            verification_token="test-token",
            user_name="Test User",
        )
        assert result is True  # Should succeed (suppressed in test mode)

    @patch("email_service.create_email_provider")
    def test_safe_email_sending_convenience_functions(
        self, mock_create_provider, app_context
    ):
        """Test that convenience functions also respect protection"""
        # Mock provider
        mock_provider = Mock()
        mock_provider.send_email.return_value = True
        mock_create_provider.return_value = mock_provider

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
            send_verification_email("test@cei.test", "token", "User")

        with pytest.raises(EmailServiceError):
            send_password_reset_email("test@coastal.edu", "token", "User")

    @patch("email_service.create_email_provider")
    def test_production_mode_allows_protected_emails(self, mock_create_provider):
        """Test that production mode allows emails to protected domains"""
        # Mock the email provider
        mock_provider = Mock()
        mock_provider.send_email.return_value = True
        mock_create_provider.return_value = mock_provider

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret-key"
        app.config["TESTING"] = True
        app.config["MAIL_SUPPRESS_SEND"] = True
        app.config["BASE_URL"] = "http://localhost:5000"
        app.config["ENV"] = "production"  # Set production mode
        app.config["PRODUCTION"] = True

        EmailService.configure_app(app)

        with app.app_context():
            # Should NOT raise exception in production mode
            result = EmailService.send_verification_email(
                email="test@mocku.test",
                verification_token="test-token",
                user_name="Test User",
            )
            assert result is True  # Should succeed


class TestEmailConfiguration:
    """Test email service configuration"""

    def test_configure_app_sets_defaults(self, app):
        """Test that app configuration sets correct defaults"""
        # Email system now uses provider-based architecture
        # Check that basic config is set
        assert "MAIL_DEFAULT_SENDER" in app.config
        assert app.config["BASE_URL"] == "http://localhost:5000"
        assert app.config["MAIL_SUPPRESS_SEND"] is True
        # MAIL_SERVER, MAIL_PORT, etc. are legacy SMTP configs no longer used
        # MAIL_DEFAULT_SENDER can come from env vars, so don't test exact value

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
        assert url == "http://localhost:5000/api/auth/verify-email/test-token-123"

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


class TestEmailLogging:
    """Tests for email preview logging to disk."""

    @patch("email_service.create_email_provider")
    def test_logs_successful_email_preview(
        self,
        mock_create_provider,
        app_context,
        tmp_path,
    ):
        """Ensure successful sends append preview entries."""

        mock_provider = Mock()
        mock_provider.send_email.return_value = True
        mock_create_provider.return_value = mock_provider

        log_path = tmp_path / "emails.log"
        app_context.config["EMAIL_LOG_PATH"] = str(log_path)

        result = EmailService.send_verification_email(
            email="test@example.com",
            verification_token="token-123",
            user_name="Demo User",
        )

        assert result is True
        assert log_path.exists()
        contents = log_path.read_text(encoding="utf-8")
        assert "Email SENT" in contents
        assert "test@example.com" in contents
        assert "Verify your Course Record Updater account" in contents

    def test_logs_blocked_email_preview(self, tmp_path, app_context):
        """Ensure blocked emails are still recorded for storytelling/demo purposes."""
        log_path = tmp_path / "blocked-emails.log"
        app_context.config["EMAIL_LOG_PATH"] = str(log_path)

        with pytest.raises(
            EmailServiceError,
            match="Cannot send emails to protected domain",
        ):
            EmailService.send_verification_email(
                email="test@cei.test",
                verification_token="token-456",
                user_name="Blocked User",
            )

        assert log_path.exists()
        contents = log_path.read_text(encoding="utf-8")
        assert "Email BLOCKED" in contents
        assert "test@cei.test" in contents
        assert "Cannot send emails to protected domain" in contents

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

    @patch("email_service.create_email_provider")
    def test_email_suppression_enabled(self, mock_create_provider, app_context):
        """Test that emails are suppressed when MAIL_SUPPRESS_SEND is True"""

        # Mock provider
        mock_provider = Mock()
        mock_provider.send_email.return_value = True
        mock_create_provider.return_value = mock_provider

        # This should succeed because suppression is enabled in test fixture
        result = EmailService._send_email(
            to_email="test@example.com",
            subject="Test Subject",
            html_body="<p>Test HTML</p>",
            text_body="Test Text",
        )

        assert result is True

    @patch("email_service.create_email_provider")
    def test_email_suppression_logs_content(self, mock_create_provider, app_context):
        """Test that suppressed emails log their content"""

        # Mock provider
        mock_provider = Mock()
        mock_provider.send_email.return_value = True
        mock_create_provider.return_value = mock_provider

        # Provider-based system handles logging
        result = EmailService._send_email(
            to_email="test@example.com",
            subject="Test Subject",
            html_body="<p>Test HTML</p>",
            text_body="Test Text Content",
        )

        # Email should succeed
        assert result is True
        # Actual logging happens in email providers, tested separately


class TestProviderSending:
    """Test provider-based email sending"""

    @patch("email_service.create_email_provider")
    def test_provider_sending_success(self, mock_create_provider):
        """Test email sending via provider"""

        # Mock provider
        mock_provider = Mock()
        mock_provider.send_email.return_value = True
        mock_create_provider.return_value = mock_provider

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret-key"
        app.config["TESTING"] = True
        app.config["MAIL_SUPPRESS_SEND"] = False
        app.config["BASE_URL"] = "http://localhost:5000"
        EmailService.configure_app(app)

        with app.app_context():
            result = EmailService._send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_body="<p>Test HTML</p>",
                text_body="Test Text",
            )

            assert result is True
            mock_provider.send_email.assert_called_once()

    @patch("email_service.create_email_provider")
    def test_provider_sending_failure(self, mock_create_provider):
        """Test email sending failure via provider"""

        # Mock provider to fail
        mock_provider = Mock()
        mock_provider.send_email.side_effect = Exception("Provider error")
        mock_create_provider.return_value = mock_provider

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret-key"
        app.config["TESTING"] = True
        app.config["MAIL_SUPPRESS_SEND"] = False
        app.config["BASE_URL"] = "http://localhost:5000"
        EmailService.configure_app(app)

        with app.app_context():
            result = EmailService._send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_body="<p>Test HTML</p>",
                text_body="Test Text",
            )

            # Should return False on provider failure
            assert result is False


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_convenience_functions_exist(self):
        """Test that all convenience functions are available"""
        assert callable(send_verification_email)
        assert callable(send_password_reset_email)
        assert callable(send_invitation_email)
        assert callable(send_welcome_email)

    @patch("email_service.create_email_provider")
    def test_convenience_functions_work(self, mock_create_provider, app_context):
        """Test that convenience functions work correctly"""

        # Mock provider
        mock_provider = Mock()
        mock_provider.send_email.return_value = True
        mock_create_provider.return_value = mock_provider

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


class TestCourseReminderEmail:
    """Test course assessment reminder email functionality."""

    @patch("email_service.create_email_provider")
    def test_send_course_assessment_reminder(self, mock_create_provider, app_context):
        """Test sending course assessment reminder email."""

        # Mock provider
        mock_provider = Mock()
        mock_provider.send_email.return_value = True
        mock_create_provider.return_value = mock_provider

        # Send reminder
        result = EmailService.send_course_assessment_reminder(
            to_email="instructor@example.com",
            instructor_name="Dr. Smith",
            course_display="CS101 - Intro to Programming",
            admin_name="Dr. Admin",
            institution_name="Example University",
            assessment_url="http://localhost:3001/assessments?course=123",
        )

        assert result is True
        mock_provider.send_email.assert_called_once()

    @patch("email_service.create_email_provider")
    def test_send_course_assessment_reminder_failure(
        self, mock_create_provider, app_context
    ):
        """Test course reminder handles send failure."""

        mock_provider = Mock()
        mock_provider.send_email.return_value = False
        mock_create_provider.return_value = mock_provider

        result = EmailService.send_course_assessment_reminder(
            to_email="fail@example.com",
            instructor_name="Dr. Test",
            course_display="TEST101",
            admin_name="Admin",
            institution_name="Test U",
            assessment_url="http://localhost:3001/test",
        )

        assert result is False

    @patch("email_service.create_email_provider")
    def test_send_course_assessment_reminder_with_empty_names(
        self, mock_create_provider, app_context
    ):
        """Test course reminder with minimal data."""

        mock_provider = Mock()
        mock_provider.send_email.return_value = True
        mock_create_provider.return_value = mock_provider

        result = EmailService.send_course_assessment_reminder(
            to_email="test@example.com",
            instructor_name="",
            course_display="",
            admin_name="",
            institution_name="",
            assessment_url="http://localhost:3001/test",
        )

        assert result is True

    @patch("email_service.create_email_provider")
    def test_send_course_assessment_reminder_exception(
        self, mock_create_provider, app_context
    ):
        """Test course reminder handles exceptions."""

        mock_provider = Mock()
        mock_provider.send_email.side_effect = Exception("Test error")
        mock_create_provider.return_value = mock_provider

        result = EmailService.send_course_assessment_reminder(
            to_email="test@example.com",
            instructor_name="Test",
            course_display="TEST",
            admin_name="Admin",
            institution_name="Univ",
            assessment_url="http://localhost:3001/test",
        )

        assert result is False
