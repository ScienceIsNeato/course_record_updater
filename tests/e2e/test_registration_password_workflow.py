"""
E2E: Complete User Registration & Password Management Workflow

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

import time
from collections.abc import Generator

import pytest
from playwright.sync_api import Page, expect

from src.utils.constants import INVALID_CREDENTIALS_MSG
from tests.e2e.conftest import BASE_URL
from tests.e2e.email_utils import (
    SKIP_EMAIL_VERIFICATION,
    clear_ethereal_inbox,
    extract_password_reset_link_from_email,
    extract_verification_link_from_email,
    wait_for_email_via_imap,
)

pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.xdist_group("email")]


class TestRegistrationAndPasswordManagement:
    """
    E2E: Complete User Registration & Password Management Workflow

    Validates the entire authentication email lifecycle in a single comprehensive test.
    """

    # Test user credentials
    # Using Ethereal domain for E2E email verification
    TEST_EMAIL = "jane.smith@ethereal.email"
    TEST_PASSWORD = "JaneSmith123!"
    TEST_NEW_PASSWORD = "JaneNewPassword456!"
    TEST_FIRST_NAME = "Jane"
    TEST_LAST_NAME = "Smith"

    def _register_new_user(self, page: Page) -> None:
        """Register the test user and land on the login page."""
        page.goto(f"{BASE_URL}/register")
        page.wait_for_load_state("networkidle")
        expect(page.locator('h1:has-text("Create Account")')).to_be_visible()

        page.fill('input[name="firstName"]', self.TEST_FIRST_NAME)
        page.fill('input[name="lastName"]', self.TEST_LAST_NAME)
        page.fill('input[name="email"]', self.TEST_EMAIL)
        page.fill('input[name="institutionName"]', "Test Institution")
        page.fill('input[name="password"]', self.TEST_PASSWORD)
        page.fill('input[name="confirmPassword"]', self.TEST_PASSWORD)

        terms_checkbox = page.locator('input[name="agreeTerms"]')
        expect(terms_checkbox).to_be_visible()
        terms_checkbox.check()
        expect(terms_checkbox).to_be_checked()

        page.click('button[type="submit"]')
        page.wait_for_url(f"{BASE_URL}/login*", timeout=5000)

    def _complete_email_verification_or_assert_blocked(self, page: Page) -> bool:
        """Verify account email or assert that unverified login is blocked."""
        print("\n📧 Checking for verification email...")
        if not SKIP_EMAIL_VERIFICATION:
            verification_email = wait_for_email_via_imap(
                recipient_email=self.TEST_EMAIL,
                subject_substring="Verify",
                timeout=90,
            )
            assert verification_email is not None, "Verification email not received"

            verification_link = extract_verification_link_from_email(verification_email)
            assert (
                verification_link is not None
            ), "Could not find verification link in email"
            assert self.TEST_FIRST_NAME in verification_email.get("body", "")
            assert "verify" in verification_email.get("subject", "").lower()

            print(f"✅ Verification email received with link: {verification_link}")
            print("\n🔗 Clicking verification link...")

            page.goto(verification_link)
            page.wait_for_load_state("networkidle")
            page_content = page.content()
            assert "success" in page_content.lower(), "Expected success response"
            assert "verified" in page_content.lower(), "Expected 'verified' in response"
            print("✅ Email verification API call successful")

            page.goto(f"{BASE_URL}/login")
            page.wait_for_load_state("networkidle")
            return True

        print("\n⚠️  Email verification automated testing not available")
        print(
            "📧 Ethereal Email credentials not configured (ETHEREAL_USER/ETHEREAL_PASS)"
        )
        print("🔗 Manual verification: Log into https://ethereal.email/ to check inbox")
        print("   Expected: Verification email sent to", self.TEST_EMAIL)
        print("   Subject: 'Verify your LoopCloser account'")
        print("\n🔒 Testing security: Unverified user should NOT be able to log in")

        page.fill('input[name="email"]', self.TEST_EMAIL)
        page.fill('input[name="password"]', self.TEST_PASSWORD)
        page.click('button[type="submit"]:has-text("Sign In")')
        expect(page).to_have_url(f"{BASE_URL}/login", timeout=5000)

        error_alert = page.locator(".alert-danger, .alert-warning")
        expect(error_alert).to_be_visible(timeout=5000)
        error_text = error_alert.text_content()
        assert (
            "verif" in error_text.lower()
        ), f"Expected error about verification, got: {error_text}"

        print("✅ Security check passed: Unverified user correctly blocked from login")
        print("📧 Email verification workflow validated (registration → email sent)")
        print("\n⏭️  Skipping remaining test steps that require verified account")
        return False

    def _login_and_assert_dashboard(self, page: Page, password: str) -> None:
        """Login and verify institution-admin dashboard context."""
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")
        page.fill('input[name="email"]', self.TEST_EMAIL)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]:has-text("Sign In")')
        expect(page).to_have_url(f"{BASE_URL}/dashboard", timeout=5000)
        expect(page.locator("h1, h2").filter(has_text="Institution")).to_be_visible()
        page.wait_for_function(
            "window.currentUser && window.currentUser.institutionId && window.currentUser.institutionId.length > 0",
            timeout=15000,
        )

    def _logout_to_login_page(self, page: Page) -> None:
        """Open the user menu, logout, and return to the login page."""
        page.click('button:has-text("Institution Admin")')
        with page.expect_navigation(timeout=10000):
            page.click('button:has-text("Logout")')
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

    def _request_password_reset(self, page: Page) -> str:
        """Request a reset email and return the reset link."""
        page.click('a:has-text("Forgot your password?")')
        page.wait_for_load_state("networkidle")
        expect(page.locator('h1:has-text("Reset Password")')).to_be_visible()
        page.fill('input[name="email"]', self.TEST_EMAIL)
        page.click('button[type="submit"]:has-text("Send Reset Instructions")')
        page.wait_for_load_state("networkidle")
        expect(page.locator('text="Check Your Email"')).to_be_visible(timeout=5000)

        reset_email = wait_for_email_via_imap(
            recipient_email=self.TEST_EMAIL,
            subject_substring="Reset",
            timeout=90,
        )
        assert reset_email is not None, "Password reset email not received"
        reset_link = extract_password_reset_link_from_email(reset_email)
        assert reset_link is not None, "Could not find reset link in email"
        print(f"✅ Password reset email received with link: {reset_link}")
        return reset_link

    def _complete_password_reset(self, page: Page, reset_link: str) -> None:
        """Open the reset link, submit a new password, and verify confirmation email."""
        page.goto(reset_link)
        page.wait_for_load_state("networkidle")
        expect(page.locator('h1:has-text("Reset Password")')).to_be_visible()

        email_input = page.locator('input[name="email"]')
        if email_input.count() > 0:
            try:
                expect(email_input).to_have_value(self.TEST_EMAIL, timeout=1000)
                print("✅ Email field pre-filled correctly")
            except Exception:
                print("ℹ️  Email field not pre-filled (optional feature)")

        page.fill('input[name="password"]', self.TEST_NEW_PASSWORD)
        page.fill('input[name="confirm_password"]', self.TEST_NEW_PASSWORD)
        page.click('button[type="submit"]:has-text("Reset Password")')
        page.wait_for_load_state("networkidle")

        success_heading = page.locator('h4:has-text("Password Reset Successful")')
        if success_heading.count() > 0:
            expect(success_heading).to_be_visible(timeout=5000)
            print("✅ Password reset successful message displayed")
        else:
            try:
                expect(page.locator(".alert-success")).to_be_visible(timeout=2000)
                print("✅ Success alert displayed")
            except Exception:
                page.wait_for_url("**/login", timeout=3000)
                print("✅ Redirected to login page")

        confirmation_email = wait_for_email_via_imap(
            recipient_email=self.TEST_EMAIL,
            subject_substring="password",
            timeout=90,
        )
        assert (
            confirmation_email is not None
        ), "Password confirmation email not received"
        assert "password" in confirmation_email.get("body", "").lower()
        print("✅ Password confirmation email received")

    def _assert_old_password_rejected(self, page: Page) -> None:
        """Verify the old password no longer authenticates."""
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")
        page.fill('input[name="email"]', self.TEST_EMAIL)
        page.fill('input[name="password"]', self.TEST_PASSWORD)
        page.click('button[type="submit"]:has-text("Sign In")')
        expect(
            page.locator(f'.alert-danger:has-text("{INVALID_CREDENTIALS_MSG}")')
        ).to_be_visible(timeout=5000)
        assert "/login" in page.url

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self) -> Generator[None, None, None]:
        """Setup and teardown for E2E test: test."""
        unique_suffix = int(time.time())
        self.TEST_EMAIL = f"jane.smith+{unique_suffix}@ethereal.email"

        # Clear any stale emails from previous test runs
        if not SKIP_EMAIL_VERIFICATION:
            clear_ethereal_inbox()
        else:
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

    def test_complete_registration_and_password_workflow(self, page: Page) -> None:
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

        self._register_new_user(page)
        if not self._complete_email_verification_or_assert_blocked(page):
            return
        self._login_and_assert_dashboard(page, self.TEST_PASSWORD)
        self._logout_to_login_page(page)
        reset_link = self._request_password_reset(page)
        self._complete_password_reset(page, reset_link)
        self._login_and_assert_dashboard(page, self.TEST_NEW_PASSWORD)
        self._logout_to_login_page(page)
        self._assert_old_password_rejected(page)

        # ====================================================================
        # TEST COMPLETE
        # ====================================================================

        print(
            "✅ E2E test: PASSED: Registration and password management workflow complete"
        )
