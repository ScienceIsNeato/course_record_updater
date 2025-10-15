"""
Mailtrap UI Scraper for E2E Email Verification

Since Mailtrap Sandbox API v2 doesn't support reading messages programmatically,
this scraper uses Playwright to check the Mailtrap inbox UI directly.

This is a pragmatic workaround for automated E2E testing until we migrate to
a service with a proper read API (Mailosaur, Ethereal, etc.).
"""

import os
import time
from typing import Dict, List, Optional

from playwright.sync_api import Page, sync_playwright


class MailtrapScraperError(Exception):
    """Raised when Mailtrap scraping fails"""


class MailtrapScraper:
    """Scrapes Mailtrap inbox UI to fetch emails for E2E testing"""

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        inbox_id: Optional[str] = None,
    ):
        """
        Initialize Mailtrap scraper.

        Args:
            username: Mailtrap web login email (defaults to MAILTRAP_WEB_EMAIL env var)
            password: Mailtrap web login password (defaults to MAILTRAP_WEB_PASSWORD env var)
            inbox_id: Mailtrap inbox ID (defaults to MAILTRAP_INBOX_ID env var)
        """
        self.username = username or os.getenv("MAILTRAP_WEB_EMAIL")
        self.password = password or os.getenv("MAILTRAP_WEB_PASSWORD")
        self.inbox_id = inbox_id or os.getenv("MAILTRAP_INBOX_ID")

        if not all([self.username, self.password, self.inbox_id]):
            raise MailtrapScraperError(
                "MAILTRAP_WEB_EMAIL, MAILTRAP_WEB_PASSWORD, and MAILTRAP_INBOX_ID "
                "must be set in environment"
            )

        self.inbox_url = f"https://mailtrap.io/inboxes/{self.inbox_id}/messages"
        self.login_url = "https://mailtrap.io/signin"

    def wait_for_email(
        self,
        recipient_email: str,
        subject_substring: Optional[str] = None,
        unique_identifier: Optional[str] = None,
        timeout: int = 60,
        poll_interval: int = 3,
    ) -> Optional[Dict[str, str]]:
        """
        Wait for an email to appear in the Mailtrap inbox.

        Args:
            recipient_email: Email address to look for in the "To" field
            subject_substring: Optional substring to match in subject
            unique_identifier: Optional unique string that should appear in email
            timeout: Maximum seconds to wait (default 60)
            poll_interval: Seconds between checks (default 3)

        Returns:
            Dictionary with email details if found, None otherwise
            Keys: subject, to, from, body_preview
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                # Login to Mailtrap
                self._login(page)

                # Navigate to inbox
                page.goto(self.inbox_url)
                page.wait_for_load_state("networkidle")

                # Poll for email
                start_time = time.time()
                while time.time() - start_time < timeout:
                    # Look for email in the list
                    email = self._find_email_in_list(
                        page, recipient_email, subject_substring, unique_identifier
                    )

                    if email:
                        return email

                    # Wait before next poll
                    time.sleep(poll_interval)
                    page.reload()
                    page.wait_for_load_state("networkidle")

                # Timeout reached
                return None

            finally:
                browser.close()

    def get_latest_email(self) -> Optional[Dict[str, str]]:
        """
        Get the most recent email from the inbox.

        Returns:
            Dictionary with email details if found, None if inbox is empty
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                self._login(page)
                page.goto(self.inbox_url)
                page.wait_for_load_state("networkidle")

                return self._get_first_email(page)

            finally:
                browser.close()

    def _login(self, page: Page) -> None:
        """Login to Mailtrap"""
        print(f"🔐 Navigating to {self.login_url}")
        page.goto(self.login_url, wait_until="domcontentloaded")

        # Wait for login form to appear
        print("⏳ Waiting for login form...")
        page.wait_for_selector(
            'input[type="email"], input[name="email"]', timeout=10000
        )

        # Fill login form - Mailtrap has a two-step login
        print(f"📧 Step 1: Filling email: {self.username}")
        email_field = page.locator('input[type="email"], input[name="email"]').first
        email_field.fill(self.username)

        # Wait a moment for button to become active after filling email
        time.sleep(0.5)

        # Press Enter on the email field (simpler than finding button)
        print("🔘 Pressing Enter to continue...")
        email_field.press("Enter")

        # Wait for password field to appear
        print("⏳ Waiting for password field...")
        page.wait_for_selector('input[type="password"]', timeout=10000)

        print("🔑 Step 2: Filling password...")
        password_field = page.locator('input[type="password"]').first
        password_field.fill(self.password)

        # Submit - press Enter on password field
        print("🚀 Submitting login form (pressing Enter)...")
        password_field.press("Enter")

        # Wait a moment and check what happened
        time.sleep(2)
        page.screenshot(path="/tmp/mailtrap_after_submit.png")
        print(f"📸 After submit screenshot: /tmp/mailtrap_after_submit.png")
        print(f"📍 Current URL: {page.url}")

        # Wait for redirect to dashboard
        print("⏳ Waiting for redirect to inboxes...")
        page.wait_for_url("**/inboxes**", timeout=15000)
        print("✅ Login successful!")

    def _find_email_in_list(
        self,
        page: Page,
        recipient_email: str,
        subject_substring: Optional[str],
        unique_identifier: Optional[str],
    ) -> Optional[Dict[str, str]]:
        """
        Find email in the inbox list.

        Mailtrap shows emails in a list with subject and recipient visible.
        """
        # Get all email items in the list
        email_items = page.locator('[data-qa="email_item"]').all()

        if not email_items:
            return None

        for item in email_items:
            try:
                # Get text content to check
                text_content = item.text_content() or ""

                # Check if this email matches our criteria
                if recipient_email.lower() not in text_content.lower():
                    continue

                if (
                    subject_substring
                    and subject_substring.lower() not in text_content.lower()
                ):
                    continue

                if unique_identifier and unique_identifier not in text_content:
                    continue

                # Found a match! Click to open and extract details
                item.click()
                page.wait_for_load_state("networkidle")

                # Extract email details from the opened email view
                email_details = self._extract_email_details(page)

                # Verify the unique identifier is in the body if specified
                if unique_identifier:
                    body = email_details.get("body", "")
                    if unique_identifier not in body:
                        # False positive, keep looking
                        continue

                return email_details

            except Exception:  # pylint: disable=broad-except
                # Item might have disappeared or be stale, continue to next
                continue

        return None

    def _get_first_email(self, page: Page) -> Optional[Dict[str, str]]:
        """Get the first email in the inbox"""
        email_items = page.locator('[data-qa="email_item"]').all()

        if not email_items:
            return None

        # Click first email
        email_items[0].click()
        page.wait_for_load_state("networkidle")

        return self._extract_email_details(page)

    def _extract_email_details(self, page: Page) -> Dict[str, str]:
        """
        Extract email details from the opened email view.

        Returns dictionary with: subject, to, from, body
        """
        # Wait for email to load
        time.sleep(1)

        # Extract details from the email view
        subject = ""
        to = ""
        from_addr = ""
        body = ""

        try:
            # Subject is in the email header
            subject_elem = page.locator("h1, h2, [data-qa='email_subject']").first
            if subject_elem.count() > 0:
                subject = subject_elem.text_content() or ""

            # To/From in email metadata
            # Mailtrap shows these in the "Show Headers" section
            # For now, extract from visible text
            page_text = page.text_content("body") or ""

            # Simple extraction from visible text
            if "To:" in page_text:
                to_start = page_text.find("To:") + 3
                to_end = page_text.find("\n", to_start)
                to = page_text[to_start:to_end].strip() if to_end > to_start else ""

            if "From:" in page_text:
                from_start = page_text.find("From:") + 5
                from_end = page_text.find("\n", from_start)
                from_addr = (
                    page_text[from_start:from_end].strip()
                    if from_end > from_start
                    else ""
                )

            # Get email body content
            # Try to find the HTML or text tab content
            body_elem = page.locator(".email-body, .email-content, iframe").first
            if body_elem.count() > 0:
                # If it's an iframe, get its content
                if body_elem.evaluate("el => el.tagName") == "IFRAME":
                    frame = body_elem.content_frame()
                    if frame:
                        body = frame.text_content("body") or ""
                else:
                    body = body_elem.text_content() or ""

        except Exception as e:  # pylint: disable=broad-except
            print(f"Warning: Failed to extract some email details: {e}")

        return {
            "subject": subject,
            "to": to,
            "from": from_addr,
            "body": body,
        }


# Convenience functions for easy import
def wait_for_email(
    recipient_email: str,
    subject_substring: Optional[str] = None,
    unique_identifier: Optional[str] = None,
    timeout: int = 60,
) -> Optional[Dict[str, str]]:
    """
    Wait for an email to appear in Mailtrap inbox.

    Args:
        recipient_email: Email address to look for
        subject_substring: Optional substring to match in subject
        unique_identifier: Optional unique string in email (like timestamp)
        timeout: Maximum seconds to wait

    Returns:
        Email details if found, None otherwise
    """
    scraper = MailtrapScraper()
    return scraper.wait_for_email(
        recipient_email, subject_substring, unique_identifier, timeout
    )


def get_latest_email() -> Optional[Dict[str, str]]:
    """Get the most recent email from Mailtrap inbox"""
    scraper = MailtrapScraper()
    return scraper.get_latest_email()
