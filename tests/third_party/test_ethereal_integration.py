"""
Third-party integration test for Ethereal Email

Validates that we can:
1. Send emails via Ethereal SMTP
2. Retrieve emails via Ethereal IMAP
3. Verify email content matches what was sent

This test proves the Ethereal Email service works before integrating it into the main application.
"""

import email
import imaplib
import os
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pytest


def _ethereal_config() -> tuple[str, str, str, int, str, int]:
    """Load Ethereal credentials and connection settings from the environment."""
    ethereal_user = os.getenv("ETHEREAL_USER")
    ethereal_pass = os.getenv("ETHEREAL_PASS")
    smtp_host = os.getenv("ETHEREAL_SMTP_HOST", "smtp.ethereal.email")
    smtp_port = int(os.getenv("ETHEREAL_SMTP_PORT", "587"))
    imap_host = os.getenv("ETHEREAL_IMAP_HOST", "imap.ethereal.email")
    imap_port = int(os.getenv("ETHEREAL_IMAP_PORT", "993"))
    assert ethereal_user, "ETHEREAL_USER must be set in environment"
    assert ethereal_pass, "ETHEREAL_PASS must be set in environment"
    return ethereal_user, ethereal_pass, smtp_host, smtp_port, imap_host, imap_port


def _send_ethereal_message(
    ethereal_user: str,
    ethereal_pass: str,
    smtp_host: str,
    smtp_port: int,
    subject: str,
    body_text: str,
    body_html: str,
) -> None:
    """Send one message to the Ethereal mailbox via SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = ethereal_user
    msg["To"] = ethereal_user
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))
    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
        server.starttls()
        server.login(ethereal_user, ethereal_pass)
        server.send_message(msg)


def _poll_ethereal_inbox(
    ethereal_user: str,
    ethereal_pass: str,
    imap_host: str,
    imap_port: int,
    unique_id: str,
    max_attempts: int,
) -> tuple[bool, str | None]:
    """Poll the inbox for a matching message and return its text body."""
    email_found = False
    email_body = None
    for attempt in range(1, max_attempts + 1):
        print(f"   Attempt {attempt}/{max_attempts}...")
        try:
            mail = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=10)
            mail.login(ethereal_user, ethereal_pass)
            mail.select("INBOX")
            status, messages = mail.search(None, f'SUBJECT "{unique_id}"')
            if status == "OK" and messages[0]:
                email_ids = messages[0].split()
                if email_ids:
                    status, msg_data = mail.fetch(email_ids[-1], "(RFC822)")
                    if status == "OK":
                        raw_message = msg_data[0][1]
                        if isinstance(raw_message, (bytes, bytearray)):
                            email_message = email.message_from_bytes(raw_message)
                            email_body = _extract_email_body(email_message)
                            email_found = email_body is not None
                            if email_found:
                                print(f"✅ Email found on attempt {attempt}!")
                                print(f"   Subject: {email_message['Subject']}")
                                print(f"   Body preview: {email_body[:100]}...")
            mail.close()
            mail.logout()
            if email_found:
                break
        except Exception as e:
            print(f"   ⚠️  IMAP error: {e}")
        if not email_found and attempt < max_attempts:
            time.sleep(2)
    return email_found, email_body


def _extract_email_body(email_message: email.message.Message) -> str | None:
    """Extract the plain text payload from an email message."""
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if isinstance(payload, (bytes, bytearray)):
                    return payload.decode()
        return None
    payload = email_message.get_payload(decode=True)
    if isinstance(payload, (bytes, bytearray)):
        return payload.decode()
    return None


@pytest.mark.third_party
def test_ethereal_send_and_receive() -> None:
    """
    Test complete Ethereal Email send/receive cycle.

    This test:
    1. Generates a unique identifier
    2. Sends an email via SMTP to our Ethereal account
    3. Polls the IMAP inbox for the email
    4. Verifies the email content matches
    """
    ethereal_user, ethereal_pass, smtp_host, smtp_port, imap_host, imap_port = (
        _ethereal_config()
    )

    # Generate unique identifier for this test
    unique_id = f"test-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
    subject = f"Ethereal Integration Test {unique_id}"
    body_text = f"This is a test email with unique ID: {unique_id}"
    body_html = (
        f"<p>This is a test email with unique ID: <strong>{unique_id}</strong></p>"
    )

    print("\n🔬 Testing Ethereal Email Integration")
    print(f"📧 Unique ID: {unique_id}")
    print(f"📨 Sending to: {ethereal_user}")

    # Step 1: Send email via SMTP
    print("\n📤 Step 1: Sending email via SMTP...")
    try:
        _send_ethereal_message(
            ethereal_user,
            ethereal_pass,
            smtp_host,
            smtp_port,
            subject,
            body_text,
            body_html,
        )
        print("✅ Email sent successfully!")
    except Exception as e:
        pytest.fail(f"Failed to send email via SMTP: {e}")

    # Step 2: Poll IMAP inbox for the email
    print("\n📥 Step 2: Polling IMAP inbox...")
    max_attempts = 15  # 30 seconds total (15 attempts * 2 seconds)
    email_found, email_body = _poll_ethereal_inbox(
        ethereal_user,
        ethereal_pass,
        imap_host,
        imap_port,
        unique_id,
        max_attempts,
    )

    # Step 3: Verify email was found and content matches
    print("\n🔍 Step 3: Verifying email content...")
    assert (
        email_found
    ), f"Email with unique ID '{unique_id}' not found after {max_attempts} attempts"
    assert email_body is not None, "Email body was empty"
    assert unique_id in email_body, f"Unique ID '{unique_id}' not found in email body"

    print("✅ Email content verified successfully!")
    print("\n🎉 Ethereal Email integration test PASSED!")


if __name__ == "__main__":
    # Allow running directly for quick testing
    test_ethereal_send_and_receive()
