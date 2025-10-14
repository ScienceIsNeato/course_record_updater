"""
Third-party integration tests for Gmail email delivery

Tests actual Gmail SMTP delivery using Bella Barkington's test account.
Requires manual setup of Gmail account with app password.

To run these tests:
1. Create Bella's Gmail account: lassie.tests.instructor1.test@gmail.com
2. Enable 2FA and generate app password
3. Set environment variables:
   - GMAIL_TEST_USERNAME=lassie.tests.instructor1.test@gmail.com
   - GMAIL_TEST_PASSWORD=<app-password>
4. Remove @pytest.mark.skip decorator
5. Run: pytest tests/integration/test_gmail_third_party.py -v
"""

import os
import time

import pytest

from email_service import EmailService


@pytest.mark.skip(
    reason="Requires manual Gmail account setup with app password. "
    "See docstring for setup instructions."
)
class TestGmailThirdPartyIntegration:
    """
    Real Gmail integration tests using Bella Barkington's test account

    These tests actually send emails via Gmail SMTP and verify delivery.
    Marked as skip until Gmail account is properly configured.
    """

    @pytest.fixture(autouse=True)
    def setup_gmail_config(self, app):
        """Configure app to use Gmail SMTP for Bella's account"""
        # Check for required environment variables
        gmail_username = os.getenv("GMAIL_TEST_USERNAME")
        gmail_password = os.getenv("GMAIL_TEST_PASSWORD")

        if not gmail_username or not gmail_password:
            pytest.fail(
                "Missing required environment variables:\n"
                "  GMAIL_TEST_USERNAME=lassie.tests.instructor1.test@gmail.com\n"
                "  GMAIL_TEST_PASSWORD=<app-password>"
            )

        # Configure Flask app for Gmail
        app.config["MAIL_SERVER"] = "smtp.gmail.com"
        app.config["MAIL_PORT"] = 587
        app.config["MAIL_USE_TLS"] = True
        app.config["MAIL_USE_SSL"] = False
        app.config["MAIL_USERNAME"] = gmail_username
        app.config["MAIL_PASSWORD"] = gmail_password
        app.config["MAIL_DEFAULT_SENDER"] = gmail_username
        app.config["MAIL_DEFAULT_SENDER_NAME"] = "Course Record Test System"
        app.config["MAIL_SUPPRESS_SEND"] = False  # Enable real sending

        EmailService.configure_app(app)

        yield

    def test_send_verification_email_via_gmail(self, app):
        """
        Test sending verification email through Gmail SMTP

        TDD: This test is expected to FAIL until Gmail account is set up.
        """
        with app.app_context():
            # Attempt to send verification email to Bella's account
            success = EmailService.send_verification_email(
                email="lassie.tests.instructor1.test@gmail.com",
                verification_token="test-token-bella-123",
                user_name="Bella Barkington",
            )

            # Assert email was sent successfully
            assert success is True, "Failed to send verification email via Gmail SMTP"

    def test_gmail_smtp_authentication(self, app):
        """
        Test that Gmail SMTP authentication works

        TDD: This test is expected to FAIL until credentials are configured.
        """
        with app.app_context():
            # Try to send a simple test email
            success = EmailService.send_verification_email(
                email="lassie.tests.instructor1.test@gmail.com",
                verification_token="auth-test-token",
                user_name="Bella Barkington",
            )

            assert success is True, "Gmail SMTP authentication failed"

    def test_gmail_email_formatting(self, app):
        """
        Test that emails sent via Gmail are properly formatted

        Manual verification required:
        1. Run this test with skip removed
        2. Check Bella's inbox
        3. Verify email has:
           - Proper from address
           - Subject line
           - HTML formatting
           - Verification link
        """
        with app.app_context():
            success = EmailService.send_verification_email(
                email="lassie.tests.instructor1.test@gmail.com",
                verification_token="format-test-token",
                user_name="Bella Barkington",
            )

            assert success is True

            # Give Gmail a moment to process
            time.sleep(2)

            # Manual verification step - check inbox
            print("\n" + "=" * 60)
            print("📧 MANUAL VERIFICATION REQUIRED:")
            print("   1. Log into: lassie.tests.instructor1.test@gmail.com")
            print("   2. Check inbox for verification email")
            print("   3. Verify:")
            print("      - From: Course Record Test System")
            print("      - Subject: Verify your Course Record Updater account")
            print("      - Body: Contains 'Hello Bella Barkington'")
            print("      - Link: Contains 'format-test-token'")
            print("=" * 60)


@pytest.mark.skip(
    reason="Requires manual Gmail account setup and inbox access. "
    "See docstring for setup instructions."
)
class TestGmailDeliveryVerification:
    """
    Email delivery verification tests

    These tests would use Gmail API or IMAP to programmatically verify
    email delivery. Requires additional setup (OAuth2 or app password + IMAP).

    Phase 3 feature - not implemented yet.
    """

    def test_verify_email_delivered_to_inbox(self):
        """
        TDD placeholder: Verify email actually arrives in Bella's inbox

        Would use Gmail API to:
        1. Send verification email
        2. Wait for delivery
        3. Check inbox for email
        4. Verify content

        Not implemented - requires Gmail API setup.
        """
        pytest.fail("Not implemented - requires Gmail API setup")

    def test_verify_email_content_matches(self):
        """
        TDD placeholder: Verify delivered email content matches template

        Would use Gmail API to:
        1. Send email
        2. Fetch from inbox
        3. Parse HTML/text
        4. Assert content matches expected values

        Not implemented - requires Gmail API setup.
        """
        pytest.fail("Not implemented - requires Gmail API setup")
