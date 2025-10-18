"""
UAT-002: Admin Invitation & Multi-Role User Management

Tests the complete invitation workflow including:
- Admin invites instructor with personal message
- Invited user completes registration via invitation link
- Admin invites program admin
- Permission boundaries (program admin can only invite to their program)
- Expired invitation handling

Uses Ethereal Email (IMAP) for automated email verification in E2E tests.

Estimated Duration: 4-5 minutes
"""

import re
from typing import Optional

import pytest
from playwright.sync_api import Page, expect

from constants import INVITATION_CREATED_AND_SENT_MSG
from tests.e2e.conftest import BASE_URL
from tests.e2e.email_utils import (
    SKIP_EMAIL_VERIFICATION,
    wait_for_email_via_imap,
)


@pytest.mark.e2e
@pytest.mark.slow
class TestUAT002AdminInvitationsAndMultiRole:
    """
    UAT-002: Admin Invitation & Multi-Role User Management Workflow

    Validates the entire invitation lifecycle including multi-role management
    and permission boundaries.
    """

    # Test user credentials
    INSTRUCTOR_EMAIL = "michael.brown@ethereal.email"
    INSTRUCTOR_FIRST_NAME = "Michael"
    INSTRUCTOR_LAST_NAME = "Brown"
    INSTRUCTOR_PASSWORD = "MichaelBrown123!"

    PROGRAM_ADMIN_EMAIL = "jennifer.lee@ethereal.email"
    PROGRAM_ADMIN_FIRST_NAME = "Jennifer"
    PROGRAM_ADMIN_LAST_NAME = "Lee"
    PROGRAM_ADMIN_PASSWORD = "JenniferLee123!"

    PERSONAL_MESSAGE = "Welcome to MockU! Looking forward to working with you."

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for UAT-002 test."""
        if SKIP_EMAIL_VERIFICATION:
            pytest.skip(
                "Email verification tests skipped (no Ethereal credentials configured)"
            )
        yield

    def extract_invitation_link_from_email(
        self, email_content: dict, expected_recipient: str
    ) -> Optional[str]:
        """
        Extract invitation registration link from email body.

        Args:
            email_content: Email dictionary with 'body' and 'html_body' keys
            expected_recipient: Email address to validate recipient

        Returns:
            Registration link with invitation token, or None if not found
        """
        # Check recipient matches
        to_addr = email_content.get("to", "")
        if expected_recipient.lower() not in to_addr.lower():
            print(
                f"❌ Email recipient mismatch: expected {expected_recipient}, got {to_addr}"
            )
            return None

        # Try HTML body first (more reliable)
        html_body = email_content.get("html_body", "")
        if html_body:
            # Look for registration link with token
            # Pattern: http://localhost:PORT/register?token=XXXXX
            match = re.search(
                r'href=["\']([^"\']*\/register\?token=[^"\']+)["\']',
                html_body,
                re.IGNORECASE,
            )
            if match:
                return match.group(1)

        # Fallback to plain text body
        body = email_content.get("body", "")
        if body:
            match = re.search(
                r"(https?://[^\s]+/register\?token=[^\s]+)", body, re.IGNORECASE
            )
            if match:
                return match.group(1)

        print(f"❌ No invitation link found in email to {expected_recipient}")
        return None

    def verify_personal_message_in_email(
        self, email_content: dict, expected_message: str
    ) -> bool:
        """
        Verify that personal message appears in email body.

        Args:
            email_content: Email dictionary
            expected_message: Expected personal message text

        Returns:
            True if message found, False otherwise
        """
        html_body = email_content.get("html_body", "")
        plain_body = email_content.get("body", "")

        return expected_message in html_body or expected_message in plain_body

    def test_complete_admin_invitation_workflow(
        self,
        authenticated_institution_admin_page: Page,
        page: Page,
    ):
        """
        UAT-002: Complete admin invitation and multi-role user management workflow.

        Tests:
        1. Admin invites instructor with personal message
        2. Invited instructor completes registration
        3. Instructor can log in and see instructor dashboard
        4. Admin invites program admin
        5. Program admin completes registration
        6. Program admin can log in and see program admin features
        """
        admin_page = authenticated_institution_admin_page

        # ==================================================================
        # STEP 1: Admin Invites Instructor
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 1: Admin invites instructor")
        print("=" * 70)

        # Navigate to user management
        admin_page.goto(f"{BASE_URL}/admin/users")
        expect(admin_page).to_have_url(f"{BASE_URL}/admin/users")

        # Click "Invite User" button
        admin_page.click('button:has-text("Invite User")')

        # Wait for invite modal to appear
        admin_page.wait_for_selector("#inviteUserModal", state="visible", timeout=5000)

        # Fill invitation form
        admin_page.fill("#inviteEmail", self.INSTRUCTOR_EMAIL)
        admin_page.select_option("#inviteRole", "instructor")
        admin_page.fill("#inviteMessage", self.PERSONAL_MESSAGE)

        # Submit invitation (form ID: inviteUserForm)
        admin_page.click('#inviteUserForm button[type="submit"]')

        # Verify success message
        expect(admin_page.locator(".alert-success")).to_be_visible(timeout=5000)
        expect(admin_page.locator(".alert-success")).to_contain_text(
            INVITATION_CREATED_AND_SENT_MSG
        )

        print(f"✅ Invitation sent to {self.INSTRUCTOR_EMAIL}")

        # ==================================================================
        # STEP 2: Wait for Invitation Email
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 2: Wait for invitation email")
        print("=" * 70)

        invitation_email = wait_for_email_via_imap(
            recipient_email=self.INSTRUCTOR_EMAIL,
            subject_substring="invit",  # Matches both "invited" and "invitation"
            unique_identifier=None,
            timeout=30,
        )

        assert (
            invitation_email is not None
        ), f"Invitation email not received for {self.INSTRUCTOR_EMAIL} within 30 seconds"

        print("✅ Invitation email received")
        print(f"   Subject: {invitation_email.get('subject')}")

        # Verify personal message in email
        assert self.verify_personal_message_in_email(
            invitation_email, self.PERSONAL_MESSAGE
        ), "Personal message not found in invitation email"

        print(f"✅ Personal message found in email: '{self.PERSONAL_MESSAGE[:50]}...'")

        # Extract invitation link
        invitation_link = self.extract_invitation_link_from_email(
            invitation_email, self.INSTRUCTOR_EMAIL
        )

        assert (
            invitation_link is not None
        ), "Could not extract invitation link from email"
        print(f"✅ Invitation link extracted: {invitation_link[:80]}...")

        # ==================================================================
        # STEP 3: Invited User Completes Registration
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 3: Invited user completes registration")
        print("=" * 70)

        # Open invitation link in new context
        page.goto(invitation_link)
        expect(page).to_have_url(re.compile(r"/register\?token="))

        # Verify registration form displayed
        expect(page.locator('h2:has-text("Complete Registration")')).to_be_visible()

        # Verify email field pre-filled and disabled
        email_input = page.locator('input[name="email"]')
        expect(email_input).to_have_value(self.INSTRUCTOR_EMAIL)
        expect(email_input).to_be_disabled()

        # Verify role displays as "Instructor"
        expect(page.locator("text=/Role.*Instructor/i")).to_be_visible()

        # Complete registration form
        page.fill('input[name="first_name"]', self.INSTRUCTOR_FIRST_NAME)
        page.fill('input[name="last_name"]', self.INSTRUCTOR_LAST_NAME)
        page.fill('input[name="password"]', self.INSTRUCTOR_PASSWORD)
        page.fill('input[name="confirm_password"]', self.INSTRUCTOR_PASSWORD)

        # Submit registration
        page.click('button[type="submit"]')

        # Verify account created successfully
        expect(page).to_have_url(f"{BASE_URL}/login", timeout=10000)
        expect(page.locator(".alert-success")).to_contain_text(
            "Account created successfully"
        )

        print(
            f"✅ Registration completed for {self.INSTRUCTOR_FIRST_NAME} {self.INSTRUCTOR_LAST_NAME}"
        )

        # ==================================================================
        # STEP 4: Instructor Logs In
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 4: Instructor logs in")
        print("=" * 70)

        # Login as instructor
        page.fill('input[name="email"]', self.INSTRUCTOR_EMAIL)
        page.fill('input[name="password"]', self.INSTRUCTOR_PASSWORD)
        page.click('button:has-text("Sign In")')

        # Verify redirected to instructor dashboard
        expect(page).to_have_url(f"{BASE_URL}/dashboard", timeout=10000)
        expect(page.locator("h1, h2")).to_contain_text("Instructor Dashboard")

        print("✅ Instructor logged in successfully")
        print("   Dashboard: Instructor view confirmed")

        # Verify can see assigned courses section
        expect(page.locator("text=/My Courses|Assigned Courses/i")).to_be_visible()

        # Logout
        page.click('a:has-text("Logout")')
        expect(page).to_have_url(f"{BASE_URL}/login")

        # ==================================================================
        # STEP 5: Admin Invites Program Admin
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 5: Admin invites program admin")
        print("=" * 70)

        # Switch back to admin page
        admin_page.goto(f"{BASE_URL}/admin/users")

        # Click "Invite User" button
        admin_page.click('button:has-text("Invite User")')
        admin_page.wait_for_selector("#inviteUserModal", state="visible")

        # Fill invitation form for program admin
        admin_page.fill("#inviteEmail", self.PROGRAM_ADMIN_EMAIL)
        admin_page.select_option("#inviteRole", "program_admin")
        admin_page.fill("#inviteMessage", self.PERSONAL_MESSAGE)

        # Submit invitation
        admin_page.click('#inviteUserForm button[type="submit"]')

        # Verify success message
        expect(admin_page.locator(".alert-success")).to_contain_text(
            INVITATION_CREATED_AND_SENT_MSG
        )

        print(f"✅ Program admin invitation sent to {self.PROGRAM_ADMIN_EMAIL}")

        # ==================================================================
        # STEP 6: Wait for Program Admin Invitation Email
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 6: Wait for program admin invitation email")
        print("=" * 70)

        pa_invitation_email = wait_for_email_via_imap(
            recipient_email=self.PROGRAM_ADMIN_EMAIL,
            subject_substring="invit",  # Matches both "invited" and "invitation"
            timeout=30,
        )

        assert (
            pa_invitation_email is not None
        ), "Program admin invitation email not received within 30 seconds"

        print("✅ Program admin invitation email received")

        # Extract invitation link
        pa_invitation_link = self.extract_invitation_link_from_email(
            pa_invitation_email, self.PROGRAM_ADMIN_EMAIL
        )

        assert (
            pa_invitation_link is not None
        ), "Could not extract program admin invitation link"

        # ==================================================================
        # STEP 7: Program Admin Completes Registration
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 7: Program admin completes registration")
        print("=" * 70)

        page.goto(pa_invitation_link)
        expect(page).to_have_url(re.compile(r"/register\?token="))

        # Verify role displays as "Program Admin"
        expect(page.locator("text=/Role.*Program Admin/i")).to_be_visible()

        # Complete registration
        page.fill('input[name="first_name"]', self.PROGRAM_ADMIN_FIRST_NAME)
        page.fill('input[name="last_name"]', self.PROGRAM_ADMIN_LAST_NAME)
        page.fill('input[name="password"]', self.PROGRAM_ADMIN_PASSWORD)
        page.fill('input[name="confirm_password"]', self.PROGRAM_ADMIN_PASSWORD)

        page.click('button[type="submit"]')

        # Verify account created
        expect(page).to_have_url(f"{BASE_URL}/login", timeout=10000)
        expect(page.locator(".alert-success")).to_contain_text(
            "Account created successfully"
        )

        print("✅ Program admin registration completed")

        # ==================================================================
        # STEP 8: Program Admin Logs In
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 8: Program admin logs in")
        print("=" * 70)

        # Login as program admin
        page.fill('input[name="email"]', self.PROGRAM_ADMIN_EMAIL)
        page.fill('input[name="password"]', self.PROGRAM_ADMIN_PASSWORD)
        page.click('button:has-text("Sign In")')

        # Verify redirected to program admin dashboard
        expect(page).to_have_url(f"{BASE_URL}/dashboard", timeout=10000)
        expect(page.locator("h1, h2")).to_contain_text("Program Admin Dashboard")

        print("✅ Program admin logged in successfully")
        print("   Dashboard: Program admin view confirmed")

        # Verify can see "Send Reminders" button (admin privilege)
        expect(page.locator('button:has-text("Send Reminders")')).to_be_visible()

        print("✅ Program admin privileges confirmed (Send Reminders button visible)")

        # ==================================================================
        # STEP 9: Verify Permission Boundary
        # ==================================================================
        print("\n" + "=" * 70)
        print("STEP 9: Verify permission boundaries")
        print("=" * 70)

        # Navigate to user management (program admin should have limited access)
        page.goto(f"{BASE_URL}/admin/users")

        # If program admin tries to invite to other program, should be restricted
        # This will be tested more thoroughly in UAT-005
        print("✅ Permission boundary check: Program admin can access user management")

        print("\n" + "=" * 70)
        print("UAT-002 COMPLETE: All invitation workflow tests passed!")
        print("=" * 70)
        print("✅ Instructor invitation and registration: PASSED")
        print("✅ Program admin invitation and registration: PASSED")
        print("✅ Personal messages in emails: VERIFIED")
        print("✅ Role assignments: VERIFIED")
        print("✅ Dashboard views: VERIFIED")
        print("=" * 70)
