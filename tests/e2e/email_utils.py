"""
Email verification utilities for E2E tests.

Provides functions to interact with email services for verification:
- Ethereal Email (IMAP for E2E testing)
- Mailtrap (API for legacy support)

Includes fetching emails, extracting tokens, and waiting for email delivery.
"""

import email
import imaplib
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

# Email verification strategy
# Use Ethereal IMAP if configured, otherwise skip verification
ETHEREAL_USER = os.getenv("ETHEREAL_USER")
ETHEREAL_PASS = os.getenv("ETHEREAL_PASS")
ETHEREAL_IMAP_HOST = os.getenv("ETHEREAL_IMAP_HOST", "imap.ethereal.email")
ETHEREAL_IMAP_PORT = int(os.getenv("ETHEREAL_IMAP_PORT", "993"))

# Skip email verification only if Ethereal is not configured
SKIP_EMAIL_VERIFICATION = not (ETHEREAL_USER and ETHEREAL_PASS)
USE_ETHEREAL_IMAP = bool(ETHEREAL_USER and ETHEREAL_PASS)


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
    Legacy function - delegates to Ethereal IMAP.

    DEPRECATED: Use wait_for_email_via_imap() directly for new code.

    Args:
        recipient_email: Email address of recipient
        subject_substring: Optional subject filter
        timeout: Maximum seconds to wait
        poll_interval: Seconds between polling attempts (ignored)
        inbox_id: Optional inbox ID (ignored)
        unique_identifier: Optional unique string to find in email

    Returns:
        Email dictionary if found within timeout, None otherwise
    """
    # Delegate to Ethereal IMAP implementation
    return wait_for_email_via_imap(
        recipient_email=recipient_email,
        subject_substring=subject_substring,
        unique_identifier=unique_identifier,
        timeout=timeout,
        poll_interval=int(poll_interval),
    )


# Legacy Mailtrap API implementation (no longer functional)
def _wait_for_email_mailtrap_legacy(
    recipient_email: str,
    subject_substring: Optional[str] = None,
    timeout: int = 30,
    poll_interval: float = 2.0,
    inbox_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Legacy Mailtrap API implementation - kept for reference only.

    NOTE: Mailtrap Sandbox API v2 doesn't support reading messages.
    This function is no longer functional.
    """
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


# ============================================================================
# Ethereal Email IMAP Functions
# ============================================================================


def wait_for_email_via_imap(
    recipient_email: str,
    subject_substring: Optional[str] = None,
    unique_identifier: Optional[str] = None,
    timeout: int = 30,
    poll_interval: int = 2,
) -> Optional[Dict[str, Any]]:
    """
    Wait for an email to appear in Ethereal inbox via IMAP.

    Args:
        recipient_email: Email address to look for (usually ETHEREAL_USER)
        subject_substring: Optional substring to match in subject
        unique_identifier: Optional unique string to find in email body/subject
        timeout: Maximum seconds to wait
        poll_interval: Seconds between polling attempts

    Returns:
        Email dictionary if found, None otherwise
        Keys: subject, from, to, body, html_body
    """
    if not USE_ETHEREAL_IMAP:
        print("⚠️  Ethereal IMAP not configured, skipping email verification")
        return None

    print(f"\n📥 Polling Ethereal IMAP inbox for email...")
    if subject_substring:
        print(f"   Subject contains: {subject_substring}")
    if unique_identifier:
        print(f"   Unique ID: {unique_identifier}")

    max_attempts = timeout // poll_interval

    for attempt in range(1, max_attempts + 1):
        print(f"   Attempt {attempt}/{max_attempts}...")

        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(ETHEREAL_IMAP_HOST, ETHEREAL_IMAP_PORT)
            mail.login(ETHEREAL_USER, ETHEREAL_PASS)
            mail.select("INBOX")

            # Search for all emails
            status, messages = mail.search(None, "ALL")

            if status == "OK" and messages[0]:
                email_ids = messages[0].split()

                # Check most recent emails first (reverse order)
                for email_id in reversed(email_ids):
                    status, msg_data = mail.fetch(email_id, "(RFC822)")

                    if status == "OK":
                        # Parse email
                        email_message = email.message_from_bytes(msg_data[0][1])

                        # Extract subject
                        subject = email_message.get("Subject", "")

                        # Check if this email matches our criteria
                        if subject_substring and subject_substring not in subject:
                            continue

                        # Extract body
                        body = ""
                        html_body = ""
                        if email_message.is_multipart():
                            for part in email_message.walk():
                                content_type = part.get_content_type()
                                if content_type == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                elif content_type == "text/html":
                                    html_body = part.get_payload(decode=True).decode()
                        else:
                            body = email_message.get_payload(decode=True).decode()

                        # Check unique identifier if specified
                        if unique_identifier:
                            if (
                                unique_identifier not in subject
                                and unique_identifier not in body
                            ):
                                continue

                        # Check recipient email if specified
                        if recipient_email:
                            to_field = email_message.get("To", "")
                            # Handle both single email and comma-separated list
                            to_emails = [e.strip() for e in to_field.split(",")]
                            if recipient_email not in to_emails:
                                continue

                        # Found a match!
                        mail.close()
                        mail.logout()

                        print(f"✅ Email found on attempt {attempt}!")
                        print(f"   Subject: {subject}")
                        print(f"   To: {email_message.get('To', '')}")

                        return {
                            "subject": subject,
                            "from": email_message.get("From", ""),
                            "to": email_message.get("To", ""),
                            "body": body,
                            "html_body": html_body,
                        }

            mail.close()
            mail.logout()

        except Exception as e:
            print(f"   ⚠️  IMAP error: {e}")

        # Wait before next attempt
        if attempt < max_attempts:
            time.sleep(poll_interval)

    print(f"❌ Email not found after {max_attempts} attempts ({timeout}s)")
    return None


def extract_verification_link_from_email(email_dict: Dict[str, Any]) -> Optional[str]:
    """
    Extract verification link from email body.

    Args:
        email_dict: Email dictionary with 'body' or 'html_body' key

    Returns:
        Verification URL if found, None otherwise
    """
    html_body = email_dict.get("html_body", "")
    text_body = email_dict.get("body", "")

    # Search for verification link patterns
    # Pattern 1: /api/auth/verify-email/{token}
    # Pattern 2: /verify-email?token={token}
    patterns = [
        r"(https?://[^\s]+/api/auth/verify-email/[a-zA-Z0-9._-]+)",
        r"(https?://[^\s]+/verify-email\?token=[a-zA-Z0-9._-]+)",
    ]

    for pattern in patterns:
        # Try HTML body first
        match = re.search(pattern, html_body)
        if match:
            return match.group(1)

        # Try text body
        match = re.search(pattern, text_body)
        if match:
            return match.group(1)

    return None


def extract_password_reset_link_from_email(email_dict: Dict[str, Any]) -> Optional[str]:
    """
    Extract password reset link from email body.

    Args:
        email_dict: Email dictionary with 'body' or 'html_body' key

    Returns:
        Reset URL if found, None otherwise
    """
    html_body = email_dict.get("html_body", "")
    text_body = email_dict.get("body", "")

    # Search for reset link patterns
    # Pattern: /reset-password/{token} or /reset-password?token={token}
    patterns = [
        r"(https?://[^\s]+/reset-password/[a-zA-Z0-9._-]+)",
        r"(https?://[^\s]+/reset-password\?token=[a-zA-Z0-9._-]+)",
    ]

    for pattern in patterns:
        # Try HTML body first
        match = re.search(pattern, html_body)
        if match:
            return match.group(1)

        # Try text body
        match = re.search(pattern, text_body)
        if match:
            return match.group(1)

    return None
