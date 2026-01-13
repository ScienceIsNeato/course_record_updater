"""
Third-party integration tests for Gmail email delivery

Sends test emails TO Bella's Gmail (lassie.tests.instructor1.test@gmail.com)
# TODO: Rename Gmail account to loopcloser.tests.instructor1.test@gmail.com if needed
using the configured SMTP provider. Manual inbox verification required.

To run:
1. Remove @pytest.mark.skip decorator
2. Run: pytest tests/integration/test_gmail_third_party.py -v -s
3. Manually check Bella's Gmail inbox for test emails
"""

import os
import time
from datetime import datetime

import pytest

from src.app import app as flask_app
from src.services.email_service import EmailService


@pytest.mark.third_party
@pytest.mark.skip(reason="Manual Gmail inbox verification required after running")
class TestGmailDeliveryVerification:
    """
    Gmail delivery verification tests

    Sends emails TO Bella's Gmail using configured SMTP (Ethereal/Mailtrap/etc.)
    Manual verification: Check Bella's inbox after running tests.
    """

    @pytest.fixture(autouse=True)
    def setup_test(self):
        """Configure test environment"""
        # Ensure email sending is enabled
        flask_app.config["MAIL_SUPPRESS_SEND"] = False

        # Get recipient email from environment
        self.recipient_email = os.getenv(
            "GMAIL_TEST_USERNAME", "lassie.tests.instructor1.test@gmail.com"
        )

        # Generate unique test identifier
        self.test_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.test_id = f"TEST-{int(time.time())}"

        # Track SMTP provider being used
        self.smtp_server = flask_app.config.get("MAIL_SERVER", "unknown")

        EmailService.configure_app(flask_app)

        yield

    def test_send_verification_email_to_gmail(self):
        """
        Send verification email TO Bella's Gmail inbox

        Uses configured SMTP provider to send email to Bella's Gmail.
        Manual verification: Check inbox after test completes.
        """
        with flask_app.app_context():
            # Send verification email
            success = EmailService.send_verification_email(
                email=self.recipient_email,
                verification_token=f"{self.test_id}-verification",
                user_name="Bella Barkington",
            )

            # Assert send succeeded
            assert success, f"Failed to send email to {self.recipient_email}"

            # Print verification instructions
            print("\n" + "=" * 80)
            print("✅ VERIFICATION EMAIL SENT")
            print("=" * 80)
            print(f"   Timestamp: {self.test_timestamp}")
            print(f"   Test ID: {self.test_id}")
            print(f"   Recipient: {self.recipient_email}")
            print(f"   SMTP Server: {self.smtp_server}")
            print("   Email Type: Verification")
            print("\n📬 MANUAL VERIFICATION REQUIRED:")
            print("   1. Open Gmail: https://mail.google.com")
            print(f"   2. Login as: {self.recipient_email}")
            print(f"   3. Look for email with Test ID in subject: {self.test_id}")
            print("   4. Verify email contains:")
            print("      ✓ Subject mentions 'Verify'")
            print("      ✓ Body addresses 'Bella Barkington'")
            print("      ✓ Verification link present")
            print(f"      ✓ Test ID: {self.test_id}")
            print("=" * 80 + "\n")

    def test_send_password_reset_email_to_gmail(self):
        """
        Send password reset email TO Bella's Gmail inbox

        Tests password reset email flow with manual verification.
        """
        with flask_app.app_context():
            # Send password reset email
            success = EmailService.send_password_reset_email(
                email=self.recipient_email,
                reset_token=f"{self.test_id}-reset",
                user_name="Bella Barkington",
            )

            # Assert send succeeded
            assert success, f"Failed to send password reset to {self.recipient_email}"

            # Print verification instructions
            print("\n" + "=" * 80)
            print("✅ PASSWORD RESET EMAIL SENT")
            print("=" * 80)
            print(f"   Timestamp: {self.test_timestamp}")
            print(f"   Test ID: {self.test_id}")
            print(f"   Recipient: {self.recipient_email}")
            print(f"   SMTP Server: {self.smtp_server}")
            print("   Email Type: Password Reset")
            print("\n📬 MANUAL VERIFICATION REQUIRED:")
            print("   1. Open Gmail: https://mail.google.com")
            print(f"   2. Login as: {self.recipient_email}")
            print("   3. Look for password reset email")
            print("   4. Verify email contains:")
            print("      ✓ Subject mentions 'Password Reset'")
            print("      ✓ Body addresses 'Bella Barkington'")
            print("      ✓ Reset link present")
            print(f"      ✓ Test ID in link: {self.test_id}")
            print("=" * 80 + "\n")
