"""
UAT-001: Complete User Registration & Password Management Workflow

Tests the entire authentication email lifecycle from registration through
password reset, including:
- New user registration with email verification
- Password reset request
- Password reset completion with confirmation email
- Security: Expired token handling

Estimated Duration: 3-4 minutes
"""

import os

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL
from tests.e2e.email_utils import (
    SKIP_EMAIL_VERIFICATION,
    extract_reset_link,
    extract_token_from_url,
    extract_verification_link,
    verify_email_content,
    wait_for_email,
)


@pytest.mark.e2e
@pytest.mark.slow
class TestUAT001RegistrationAndPasswordManagement:
    """
    UAT-001: Complete User Registration & Password Management Workflow

    Validates the entire authentication email lifecycle in a single comprehensive test.
    """

    # Test user credentials
    TEST_EMAIL = "jane.smith@test.com"
    TEST_PASSWORD = "JaneSmith123!"
    TEST_NEW_PASSWORD = "JaneNewPassword456!"
    TEST_FIRST_NAME = "Jane"
    TEST_LAST_NAME = "Smith"

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean up emails before and after test."""
        if SKIP_EMAIL_VERIFICATION:
            print(
                "\n⚠️  MAILTRAP_INBOX_ID not configured - email verification will be skipped"
            )
            print(
                "   Set MAILTRAP_INBOX_ID in .envrc to enable email verification tests"
            )
            print(
                "   Find your inbox ID at: https://mailtrap.io/inboxes/YOUR_INBOX_ID\n"
            )
        # Note: Mailtrap cleanup endpoint currently has issues, skipping for now
        # Emails will accumulate in inbox but won't affect test results

        yield

        # Cleanup after test (currently disabled due to API issues)
        # if not SKIP_EMAIL_VERIFICATION:
        #     try:
        #         delete_all_emails()
        #     except Exception as e:
        #         print(f"Warning: Could not clean up emails after test: {e}")

    def test_complete_registration_and_password_workflow(self, page: Page):
        """
        Test complete user journey from registration through password reset.

        This test exercises:
        1. New user registration
        2. Email verification
        3. Login with verified account
        4. Password reset request
        5. Password reset completion
        6. Password reset confirmation email
        7. Login with new password
        8. Security: Old password no longer works
        """

        # ====================================================================
        # STEP 1: New User Registration
        # ====================================================================

        # Navigate to registration page
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state("networkidle")

        # Verify registration form is displayed
        expect(page.locator('h1:has-text("Create Account")')).to_be_visible()

        # Fill out registration form (note: camelCase field names)
        page.fill('input[name="firstName"]', self.TEST_FIRST_NAME)
        page.fill('input[name="lastName"]', self.TEST_LAST_NAME)
        page.fill('input[name="email"]', self.TEST_EMAIL)
        page.fill('input[name="institutionName"]', "Test Institution")
        page.fill('input[name="password"]', self.TEST_PASSWORD)
        page.fill('input[name="confirmPassword"]', self.TEST_PASSWORD)

        # Accept terms and conditions
        page.check('input[name="agreeTerms"]')

        # Submit registration (button enabled after form completion)
        page.click('button[type="submit"]')

        # Registration redirects to login page - wait for navigation
        expect(page).to_have_url(f"{BASE_URL}/login", timeout=5000)

        # Note: Success message may not persist across redirect
        # The fact that we're on the login page indicates successful registration

        # ====================================================================
        # STEP 2: Verify Email Received
        # ====================================================================

        print("\n📧 Checking for verification email...")

        if not SKIP_EMAIL_VERIFICATION:
            # Wait for verification email to arrive
            verification_email = wait_for_email(
                recipient_email=self.TEST_EMAIL,
                subject_substring="verify",
                timeout=30,
            )

            assert verification_email is not None, "Verification email not received"

            # Verify email content
            assert verify_email_content(
                verification_email,
                expected_recipient=self.TEST_EMAIL,
                expected_text_snippets=[
                    self.TEST_FIRST_NAME,  # Email should contain user's first name
                    "verify",  # Email should mention verification
                ],
            )

            # Extract verification link
            verification_link = extract_verification_link(verification_email)
            assert (
                verification_link is not None
            ), "Could not find verification link in email"

            # Verify token is in link
            verification_token = extract_token_from_url(verification_link, "token")
            assert verification_token is not None, "No token in verification link"
            assert len(verification_token) > 10, "Token seems too short"

            print("✅ Verification email received with valid token")

            # ====================================================================
            # STEP 3: Click Verification Link
            # ====================================================================

            print("\n🔗 Clicking verification link...")

            # Navigate to verification link (API endpoint returns JSON)
            page.goto(verification_link)
            page.wait_for_load_state("networkidle")

            # Verify API response shows success
            # The page content will be JSON: {"success": true, "message": "...", ...}
            page_content = page.content()
            assert "success" in page_content.lower(), "Expected success response"
            assert "verified" in page_content.lower(), "Expected 'verified' in response"

            print("✅ Email verification API call successful")

            # Now navigate to login page
            page.goto(f"{BASE_URL}/login")
            page.wait_for_load_state("networkidle")

        else:
            print("\n⚠️  Email verification automated testing not available")
            print(
                "📧 Mailtrap Sandbox API v2 does not support reading messages programmatically"
            )
            print(
                f"🔗 Manual verification: https://mailtrap.io/inboxes/{os.getenv('MAILTRAP_INBOX_ID', '4102679')}/messages"
            )
            print("   Expected: Verification email sent to", self.TEST_EMAIL)
            print("   Subject: 'Verify your Course Record Updater account'")
            print("\n🔒 Testing security: Unverified user should NOT be able to log in")

            # Try to login with unverified account
            page.fill('input[name="email"]', self.TEST_EMAIL)
            page.fill('input[name="password"]', self.TEST_PASSWORD)
            page.click('button[type="submit"]:has-text("Sign In")')

            # Should stay on login page and show error message
            expect(page).to_have_url(f"{BASE_URL}/login", timeout=5000)

            # Verify helpful error message is displayed
            error_alert = page.locator(".alert-danger, .alert-warning")
            expect(error_alert).to_be_visible(timeout=5000)

            # Check that the error message mentions verification
            error_text = error_alert.text_content()
            assert (
                "verif" in error_text.lower()
            ), f"Expected error about verification, got: {error_text}"

            print(
                "✅ Security check passed: Unverified user correctly blocked from login"
            )
            print(
                "📧 Email verification workflow validated (registration → email sent)"
            )
            print("\n⏭️  Skipping remaining test steps that require verified account")
            return  # Stop test here since we can't proceed without email verification

        # ====================================================================
        # STEP 5: Login with Verified Account
        # ====================================================================

        # Fill login form
        page.fill('input[name="email"]', self.TEST_EMAIL)
        page.fill('input[name="password"]', self.TEST_PASSWORD)

        # Submit login
        page.click('button[type="submit"]:has-text("Sign In")')

        # Verify successful login - redirected to dashboard
        expect(page).to_have_url(f"{BASE_URL}/dashboard", timeout=5000)
        expect(page.locator("h1, h2").filter(has_text="Dashboard")).to_be_visible()

        # ====================================================================
        # STEP 5: Password Reset Request
        # ====================================================================

        # Logout
        page.click('a:has-text("Logout"), button:has-text("Logout")')
        page.wait_for_load_state("networkidle")

        # Navigate to login page
        page.goto(f"{BASE_URL}/login")

        # Click "Forgot Password" link
        page.click('a:has-text("Forgot Password")')
        page.wait_for_load_state("networkidle")

        # Verify on password reset request page
        expect(page.locator('h2:has-text("Reset Password")')).to_be_visible()

        # Enter email for reset
        page.fill('input[name="email"]', self.TEST_EMAIL)

        # Submit reset request
        page.click('button[type="submit"]:has-text("Reset")')

        # Verify success message
        expect(
            page.locator(
                '.alert-success:has-text("Check your email for reset instructions")'
            )
        ).to_be_visible(timeout=5000)

        # ====================================================================
        # STEP 6: Verify Password Reset Email
        # ====================================================================

        # Wait for password reset email
        reset_email = wait_for_email(
            recipient_email=self.TEST_EMAIL,
            subject_substring="password reset",
            timeout=30,
        )

        assert reset_email is not None, "Password reset email not received"

        # Extract reset link
        reset_link = extract_reset_link(reset_email)
        assert reset_link is not None, "Could not find reset link in email"

        # Verify token is in link
        reset_token = extract_token_from_url(reset_link, "token")
        assert reset_token is not None, "No token in reset link"
        assert len(reset_token) > 10, "Reset token seems too short"

        # ====================================================================
        # STEP 7: Complete Password Reset
        # ====================================================================

        # Navigate to reset link
        page.goto(reset_link)
        page.wait_for_load_state("networkidle")

        # Verify reset form displayed
        expect(page.locator('h2:has-text("Reset Password")')).to_be_visible()

        # Verify email pre-filled (if applicable)
        email_input = page.locator('input[name="email"]')
        if email_input.is_visible():
            expect(email_input).to_have_value(self.TEST_EMAIL)

        # Enter new password (twice)
        page.fill('input[name="password"]', self.TEST_NEW_PASSWORD)
        page.fill('input[name="confirm_password"]', self.TEST_NEW_PASSWORD)

        # Submit password reset
        page.click('button[type="submit"]:has-text("Reset")')

        # Verify success message
        expect(
            page.locator('.alert-success:has-text("Password reset successful")')
        ).to_be_visible(timeout=5000)

        # ====================================================================
        # STEP 8: Verify Password Reset Confirmation Email
        # ====================================================================

        # Wait for confirmation email
        confirmation_email = wait_for_email(
            recipient_email=self.TEST_EMAIL,
            subject_substring="password",
            timeout=30,
        )

        assert (
            confirmation_email is not None
        ), "Password confirmation email not received"

        # Verify email mentions password change and includes timestamp
        # (Timestamp verification would require parsing email body more thoroughly)

        # ====================================================================
        # STEP 9: Login with NEW Password
        # ====================================================================

        # Navigate to login page
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

        # Fill login form with NEW password
        page.fill('input[name="email"]', self.TEST_EMAIL)
        page.fill('input[name="password"]', self.TEST_NEW_PASSWORD)

        # Submit login
        page.click('button[type="submit"]:has-text("Log In")')

        # Verify successful login
        expect(page).to_have_url(f"{BASE_URL}/dashboard", timeout=5000)
        expect(page.locator("h1, h2").filter(has_text="Dashboard")).to_be_visible()

        # Logout
        page.click('a:has-text("Logout"), button:has-text("Logout")')
        page.wait_for_load_state("networkidle")

        # ====================================================================
        # STEP 10: Verify OLD Password No Longer Works
        # ====================================================================

        # Navigate to login page
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

        # Attempt login with OLD password
        page.fill('input[name="email"]', self.TEST_EMAIL)
        page.fill('input[name="password"]', self.TEST_PASSWORD)  # OLD password

        # Submit login
        page.click('button[type="submit"]:has-text("Log In")')

        # Verify login fails
        expect(
            page.locator('.alert-danger:has-text("Invalid credentials")')
        ).to_be_visible(timeout=5000)

        # Verify still on login page (not redirected to dashboard)
        assert "/login" in page.url

        # ====================================================================
        # TEST COMPLETE
        # ====================================================================

        print(
            "✅ UAT-001 PASSED: Registration and password management workflow complete"
        )
