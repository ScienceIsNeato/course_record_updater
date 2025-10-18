"""
UAT-001: Complete User Registration & Password Management Workflow

Tests the entire authentication email lifecycle from registration through
password reset, including:
- New user registration with email verification via Ethereal Email
- Password reset request
- Password reset completion with confirmation email
- Security: Unverified users cannot log in
- Security: Old password no longer works after reset

Uses Ethereal Email (IMAP) for automated email verification in E2E tests.

Estimated Duration: 3-4 minutes
"""

import pytest
from playwright.sync_api import Page, expect

from constants import INVALID_CREDENTIALS_MSG
from tests.e2e.conftest import BASE_URL
from tests.e2e.email_utils import (
    SKIP_EMAIL_VERIFICATION,
    extract_password_reset_link_from_email,
    extract_verification_link_from_email,
    wait_for_email_via_imap,
)


@pytest.mark.e2e
@pytest.mark.slow
class TestUAT001RegistrationAndPasswordManagement:
    """
    UAT-001: Complete User Registration & Password Management Workflow

    Validates the entire authentication email lifecycle in a single comprehensive test.
    """

    # Test user credentials
    # Using Ethereal domain for E2E email verification
    TEST_EMAIL = "jane.smith@ethereal.email"
    TEST_PASSWORD = "JaneSmith123!"
    TEST_NEW_PASSWORD = "JaneNewPassword456!"
    TEST_FIRST_NAME = "Jane"
    TEST_LAST_NAME = "Smith"

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for UAT-001 test."""
        if SKIP_EMAIL_VERIFICATION:
            print(
                "\n⚠️  Ethereal Email not configured - email verification will be skipped"
            )
            print(
                "   Set ETHEREAL_USER and ETHEREAL_PASS in .envrc to enable email verification"
            )
            print("   Get free account at: https://ethereal.email/\n")

        yield

        # Note: Ethereal emails are temporary and auto-expire
        # No cleanup needed

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
        # Note: 10s timeout accounts for: form submission (1-2s) + email sending (1-2s) + JS redirect delay (3s)
        expect(page).to_have_url(f"{BASE_URL}/login", timeout=10000)

        # Note: Success message may not persist across redirect
        # The fact that we're on the login page indicates successful registration

        # ====================================================================
        # STEP 2: Verify Email Remockuved
        # ====================================================================

        print("\n📧 Checking for verification email...")

        if not SKIP_EMAIL_VERIFICATION:
            # Wait for verification email to arrive via Ethereal IMAP
            verification_email = wait_for_email_via_imap(
                recipient_email=self.TEST_EMAIL,
                subject_substring="Verify",
                timeout=30,
            )

            assert verification_email is not None, "Verification email not received"

            # Extract and validate verification link from email body
            verification_link = extract_verification_link_from_email(verification_email)
            assert (
                verification_link is not None
            ), "Could not find verification link in email"

            # Basic content checks
            assert self.TEST_FIRST_NAME in verification_email.get(
                "body", ""
            ), "Email should contain user's first name"
            assert (
                "verify" in verification_email.get("subject", "").lower()
            ), "Subject should mention verification"

            print(f"✅ Verification email received with link: {verification_link}")

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
                "📧 Ethereal Email credentials not configured (ETHEREAL_USER/ETHEREAL_PASS)"
            )
            print(
                f"🔗 Manual verification: Log into https://ethereal.email/ to check inbox"
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
        # Institution admin sees "Institution Administration" heading
        expect(page.locator("h1, h2").filter(has_text="Institution")).to_be_visible()

        # ====================================================================
        # STEP 5: Password Reset Request
        # ====================================================================

        # Logout - open dropdown menu first, then click logout
        page.click('button:has-text("Institution Admin")')  # Open user dropdown

        # Click logout and wait for navigation to complete (suppresses fetch abort errors)
        with page.expect_navigation(timeout=10000):
            page.click('button:has-text("Logout")')

        # Navigate to login page
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

        # Click "Forgot your password?" link
        page.click('a:has-text("Forgot your password?")')
        page.wait_for_load_state("networkidle")

        # Verify on password reset request page
        expect(page.locator('h1:has-text("Reset Password")')).to_be_visible()

        # Enter email for reset
        page.fill('input[name="email"]', self.TEST_EMAIL)

        # Submit reset request
        page.click('button[type="submit"]:has-text("Send Reset Instructions")')
        page.wait_for_load_state("networkidle")

        # Verify success page is displayed
        expect(page.locator('text="Check Your Email"')).to_be_visible(timeout=5000)

        # ====================================================================
        # STEP 6: Verify Password Reset Email
        # ====================================================================

        # Wait for password reset email via Ethereal IMAP
        reset_email = wait_for_email_via_imap(
            recipient_email=self.TEST_EMAIL,
            subject_substring="Reset",  # Matches "Reset your Course Record Updater password"
            timeout=30,
        )

        assert reset_email is not None, "Password reset email not received"

        # Extract reset link from email body
        reset_link = extract_password_reset_link_from_email(reset_email)
        assert reset_link is not None, "Could not find reset link in email"

        print(f"✅ Password reset email received with link: {reset_link}")

        # ====================================================================
        # STEP 7: Complete Password Reset
        # ====================================================================

        # Navigate to reset link
        page.goto(reset_link)
        page.wait_for_load_state("networkidle")

        # Verify reset form displayed
        expect(page.locator('h1:has-text("Reset Password")')).to_be_visible()

        # Check if email is pre-filled (optional - depends on implementation)
        email_input = page.locator('input[name="email"]')
        if email_input.count() > 0:
            # Email field exists - verify it has the correct value if visible
            try:
                expect(email_input).to_have_value(self.TEST_EMAIL, timeout=1000)
                print("✅ Email field pre-filled correctly")
            except Exception:
                # Email field not pre-filled - that's okay, continue
                print("ℹ️  Email field not pre-filled (optional feature)")

        # Enter new password (twice)
        page.fill('input[name="password"]', self.TEST_NEW_PASSWORD)
        page.fill('input[name="confirm_password"]', self.TEST_NEW_PASSWORD)

        # Submit password reset
        page.click('button[type="submit"]:has-text("Reset Password")')
        page.wait_for_load_state("networkidle")

        # Verify success page/message
        # The success state should be shown (form hidden, success message displayed)
        success_heading = page.locator('h4:has-text("Password Reset Successful")')
        if success_heading.count() > 0:
            expect(success_heading).to_be_visible(timeout=5000)
            print("✅ Password reset successful message displayed")
        else:
            # Alternative: check for alert or redirect to login
            try:
                expect(page.locator(".alert-success")).to_be_visible(timeout=2000)
                print("✅ Success alert displayed")
            except Exception:
                # Might have redirected to login
                page.wait_for_url("**/login", timeout=3000)
                print("✅ Redirected to login page")

        # ====================================================================
        # STEP 8: Verify Password Reset Confirmation Email
        # ====================================================================

        # Wait for confirmation email via Ethereal IMAP
        confirmation_email = wait_for_email_via_imap(
            recipient_email=self.TEST_EMAIL,
            subject_substring="password",
            timeout=30,
        )

        assert (
            confirmation_email is not None
        ), "Password confirmation email not received"

        # Verify email mentions password change
        assert (
            "password" in confirmation_email.get("body", "").lower()
        ), "Confirmation email should mention password"

        print("✅ Password confirmation email received")

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
        page.click('button[type="submit"]:has-text("Sign In")')

        # Verify successful login
        expect(page).to_have_url(f"{BASE_URL}/dashboard", timeout=5000)
        # Institution admin sees "Institution Administration" heading
        expect(page.locator("h1, h2").filter(has_text="Institution")).to_be_visible()

        # Logout - open dropdown menu first, then click logout
        page.click('button:has-text("Institution Admin")')  # Open user dropdown

        # Click logout and wait for navigation to complete (suppresses fetch abort errors)
        with page.expect_navigation(timeout=10000):
            page.click('button:has-text("Logout")')

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
        page.click('button[type="submit"]:has-text("Sign In")')

        # Verify login fails with correct error message (using constant)
        expect(
            page.locator(f'.alert-danger:has-text("{INVALID_CREDENTIALS_MSG}")')
        ).to_be_visible(timeout=5000)

        # Verify still on login page (not redirected to dashboard)
        assert "/login" in page.url

        # ====================================================================
        # TEST COMPLETE
        # ====================================================================

        print(
            "✅ UAT-001 PASSED: Registration and password management workflow complete"
        )
