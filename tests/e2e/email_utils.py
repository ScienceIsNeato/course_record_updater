"""
Email verification utilities for E2E tests.

Provides functions to interact with Mailtrap API for email verification,
including fetching emails, extracting tokens, and waiting for email delivery.
"""

import os
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import requests

# Mailtrap API configuration
MAILTRAP_API_TOKEN = os.getenv("MAILTRAP_API_TOKEN")
MAILTRAP_ACCOUNT_ID = os.getenv("MAILTRAP_ACCOUNT_ID", "335505888614cb")
# Note: Set MAILTRAP_INBOX_ID in .envrc to your actual Mailtrap inbox ID
# You can find this in Mailtrap dashboard URL: https://mailtrap.io/inboxes/YOUR_INBOX_ID
MAILTRAP_INBOX_ID = os.getenv("MAILTRAP_INBOX_ID")
MAILTRAP_API_BASE = f"https://mailtrap.io/api/accounts/{MAILTRAP_ACCOUNT_ID}"

# Use Mailtrap UI scraper for email verification
# Mailtrap Sandbox API v2 doesn't support reading messages, so we scrape the UI
SKIP_EMAIL_VERIFICATION = MAILTRAP_INBOX_ID is None

# Check if scraping is available (requires Mailtrap web credentials)
USE_MAILTRAP_SCRAPER = bool(
    os.getenv("MAILTRAP_WEB_EMAIL")
    and os.getenv("MAILTRAP_WEB_PASSWORD")
    and MAILTRAP_INBOX_ID
)


class MailtrapError(Exception):
    """Base exception for Mailtrap API errors."""

    pass


def get_mailtrap_auth() -> tuple:
    """
    Get authentication credentials for Mailtrap API.

    Returns:
        Tuple of (username, password) for basic auth
    """
    # Use username/password for API (not API token)
    username = os.getenv("MAILTRAP_API_USERNAME", MAILTRAP_ACCOUNT_ID)
    password = os.getenv("MAILTRAP_API_PASSWORD")

    if not username or not password:
        raise MailtrapError(
            "MAILTRAP_API_USERNAME and MAILTRAP_API_PASSWORD must be set in .envrc"
        )

    return (username, password)


def get_inbox_emails(inbox_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch all emails from Mailtrap inbox.

    Args:
        inbox_id: Optional inbox ID (defaults to MAILTRAP_INBOX_ID env var)

    Returns:
        List of email dictionaries with keys: id, subject, from_email, to_email,
        html_body, text_body, created_at, etc.

    Raises:
        MailtrapError: If API request fails
    """
    inbox_id = inbox_id or MAILTRAP_INBOX_ID

    url = f"{MAILTRAP_API_BASE}/inboxes/{inbox_id}/messages"

    try:
        auth = get_mailtrap_auth()
        response = requests.get(url, auth=auth, timeout=10)
        response.raise_for_status()
        result: List[Dict[str, Any]] = response.json()
        return result
    except requests.exceptions.RequestException as e:
        raise MailtrapError(f"Failed to fetch inbox emails: {e}") from e


def get_email_by_recipient(
    recipient_email: str, inbox_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get the most recent email sent to a specific recipient.

    Args:
        recipient_email: Email address of recipient
        inbox_id: Optional inbox ID

    Returns:
        Email dictionary if found, None otherwise
    """
    emails = get_inbox_emails(inbox_id)

    # Filter by recipient (Mailtrap returns newest first)
    for email in emails:
        to_emails = email.get("to_email", "").split(",")
        to_emails = [e.strip() for e in to_emails]

        if recipient_email in to_emails:
            return email

    return None


def get_email_by_subject(
    subject_substring: str, inbox_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get the most recent email with subject containing substring.

    Args:
        subject_substring: Substring to search for in subject
        inbox_id: Optional inbox ID

    Returns:
        Email dictionary if found, None otherwise
    """
    emails = get_inbox_emails(inbox_id)

    for email in emails:
        if subject_substring.lower() in email.get("subject", "").lower():
            return email

    return None


def wait_for_email(
    recipient_email: str,
    subject_substring: Optional[str] = None,
    timeout: int = 30,
    poll_interval: float = 2.0,
    inbox_id: Optional[str] = None,
    unique_identifier: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Wait for an email to arrive in Mailtrap inbox.

    Uses UI scraping since Mailtrap API doesn't support reading messages.

    Args:
        recipient_email: Email address of recipient
        subject_substring: Optional subject filter
        timeout: Maximum seconds to wait
        poll_interval: Seconds between polling attempts (ignored if using scraper)
        inbox_id: Optional inbox ID
        unique_identifier: Optional unique string to find in email (e.g. timestamp)

    Returns:
        Email dictionary if found within timeout, None otherwise
    """
    if USE_MAILTRAP_SCRAPER:
        # Use UI scraper for reliable email fetching
        from tests.e2e.mailtrap_scraper import wait_for_email as scraper_wait

        return scraper_wait(
            recipient_email=recipient_email,
            subject_substring=subject_substring,
            unique_identifier=unique_identifier,
            timeout=timeout,
        )

    # Fallback to API method (won't work with current Mailtrap setup)
    start_time = time.time()

    while time.time() - start_time < timeout:
        email = get_email_by_recipient(recipient_email, inbox_id)

        if email:
            # If subject filter specified, check it matches
            if subject_substring:
                if subject_substring.lower() in email.get("subject", "").lower():
                    return email
            else:
                return email

        time.sleep(poll_interval)

    return None


def extract_verification_link(email: Dict[str, Any]) -> Optional[str]:
    """
    Extract verification link from email body.

    Looks for links containing '/verify' or 'token=' in the email HTML or text body.

    Args:
        email: Email dictionary from Mailtrap API

    Returns:
        Verification link URL if found, None otherwise
    """
    # Try HTML body first
    html_body = email.get("html_body", "")
    if html_body:
        # Look for links with /verify or token=
        link_pattern = r'href=["\'](https?://[^"\']*(?:/verify|token=)[^"\']*)["\']'
        match = re.search(link_pattern, html_body)
        if match:
            return match.group(1)

    # Try text body
    text_body = email.get("text_body", "")
    if text_body:
        # Look for URLs in text
        url_pattern = r"https?://[^\s]+(?:/verify|token=)[^\s]+"
        match = re.search(url_pattern, text_body)
        if match:
            return match.group(0)

    return None


def extract_reset_link(email: Dict[str, Any]) -> Optional[str]:
    """
    Extract password reset link from email body.

    Looks for links containing '/reset-password' or 'reset' in the email.

    Args:
        email: Email dictionary from Mailtrap API

    Returns:
        Reset link URL if found, None otherwise
    """
    # Try HTML body first
    html_body = email.get("html_body", "")
    if html_body:
        # Look for reset links
        link_pattern = r'href=["\'](https?://[^"\']*reset[^"\']*)["\']'
        match = re.search(link_pattern, html_body, re.IGNORECASE)
        if match:
            return match.group(1)

    # Try text body
    text_body = email.get("text_body", "")
    if text_body:
        url_pattern = r"https?://[^\s]+reset[^\s]+"
        match = re.search(url_pattern, text_body, re.IGNORECASE)
        if match:
            return match.group(0)

    return None


def extract_token_from_url(url: str, param_name: str = "token") -> Optional[str]:
    """
    Extract token parameter from URL query string.

    Args:
        url: URL containing token
        param_name: Query parameter name (default: 'token')

    Returns:
        Token value if found, None otherwise
    """
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    return query_params.get(param_name, [None])[0]


def delete_all_emails(inbox_id: Optional[str] = None) -> None:
    """
    Delete all emails from Mailtrap inbox.

    Useful for cleaning up before/after tests.

    Args:
        inbox_id: Optional inbox ID

    Raises:
        MailtrapError: If API request fails
    """
    inbox_id = inbox_id or MAILTRAP_INBOX_ID

    url = f"{MAILTRAP_API_BASE}/inboxes/{inbox_id}/clean"

    try:
        auth = get_mailtrap_auth()
        response = requests.patch(url, auth=auth, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise MailtrapError(f"Failed to delete emails: {e}") from e


def verify_email_content(
    email: Dict[str, Any],
    expected_subject: Optional[str] = None,
    expected_recipient: Optional[str] = None,
    expected_text_snippets: Optional[List[str]] = None,
) -> bool:
    """
    Verify email content matches expectations.

    Args:
        email: Email dictionary from Mailtrap API
        expected_subject: Expected subject (exact match)
        expected_recipient: Expected recipient email
        expected_text_snippets: List of text snippets that should appear in body

    Returns:
        True if all checks pass, False otherwise
    """
    # Check subject
    if expected_subject and email.get("subject") != expected_subject:
        print(
            f"Subject mismatch: expected '{expected_subject}', got '{email.get('subject')}'"
        )
        return False

    # Check recipient
    if expected_recipient:
        to_emails = email.get("to_email", "").split(",")
        to_emails = [e.strip() for e in to_emails]
        if expected_recipient not in to_emails:
            print(f"Recipient mismatch: expected '{expected_recipient}' in {to_emails}")
            return False

    # Check text snippets in body
    if expected_text_snippets:
        html_body = email.get("html_body", "")
        text_body = email.get("text_body", "")

        for snippet in expected_text_snippets:
            if snippet not in html_body and snippet not in text_body:
                print(f"Missing text snippet: '{snippet}'")
                return False

    return True
