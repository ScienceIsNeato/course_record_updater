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


@pytest.mark.third_party
def test_ethereal_send_and_remockuve():
    """
    Test complete Ethereal Email send/remockuve cycle.

    This test:
    1. Generates a unique identifier
    2. Sends an email via SMTP to our Ethereal account
    3. Polls the IMAP inbox for the email
    4. Verifies the email content matches
    """
    # Get Ethereal credentials from environment
    ethereal_user = os.getenv("ETHEREAL_USER")
    ethereal_pass = os.getenv("ETHEREAL_PASS")
    smtp_host = os.getenv("ETHEREAL_SMTP_HOST", "smtp.ethereal.email")
    smtp_port = int(os.getenv("ETHEREAL_SMTP_PORT", "587"))
    imap_host = os.getenv("ETHEREAL_IMAP_HOST", "imap.ethereal.email")
    imap_port = int(os.getenv("ETHEREAL_IMAP_PORT", "993"))

    assert ethereal_user, "ETHEREAL_USER must be set in environment"
    assert ethereal_pass, "ETHEREAL_PASS must be set in environment"

    # Generate unique identifier for this test
    unique_id = f"test-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
    subject = f"Ethereal Integration Test {unique_id}"
    body_text = f"This is a test email with unique ID: {unique_id}"
    body_html = (
        f"<p>This is a test email with unique ID: <strong>{unique_id}</strong></p>"
    )

    print(f"\n🔬 Testing Ethereal Email Integration")
    print(f"📧 Unique ID: {unique_id}")
    print(f"📨 Sending to: {ethereal_user}")

    # Step 1: Send email via SMTP
    print("\n📤 Step 1: Sending email via SMTP...")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = ethereal_user
    msg["To"] = ethereal_user

    # Attach both text and HTML versions
    part1 = MIMEText(body_text, "plain")
    part2 = MIMEText(body_html, "html")
    msg.attach(part1)
    msg.attach(part2)

    # Send via SMTP with STARTTLS
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(ethereal_user, ethereal_pass)
            server.send_message(msg)
        print("✅ Email sent successfully!")
    except Exception as e:
        pytest.fail(f"Failed to send email via SMTP: {e}")

    # Step 2: Poll IMAP inbox for the email
    print("\n📥 Step 2: Polling IMAP inbox...")
    max_attempts = 15  # 30 seconds total (15 attempts * 2 seconds)
    email_found = False
    email_body = None

    for attempt in range(1, max_attempts + 1):
        print(f"   Attempt {attempt}/{max_attempts}...")

        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(imap_host, imap_port)
            mail.login(ethereal_user, ethereal_pass)
            mail.select("INBOX")

            # Search for emails with our unique ID in the subject
            # Use SUBJECT search criterion
            status, messages = mail.search(None, f'SUBJECT "{unique_id}"')

            if status == "OK" and messages[0]:
                email_ids = messages[0].split()
                if email_ids:
                    # Found it! Fetch the email
                    latest_email_id = email_ids[-1]
                    status, msg_data = mail.fetch(latest_email_id, "(RFC822)")

                    if status == "OK":
                        # Parse the email
                        email_message = email.message_from_bytes(msg_data[0][1])

                        # Extract body
                        if email_message.is_multipart():
                            for part in email_message.walk():
                                if part.get_content_type() == "text/plain":
                                    email_body = part.get_payload(decode=True).decode()
                                    break
                        else:
                            email_body = email_message.get_payload(decode=True).decode()

                        email_found = True
                        print(f"✅ Email found on attempt {attempt}!")
                        print(f"   Subject: {email_message['Subject']}")
                        print(f"   Body preview: {email_body[:100]}...")

            mail.close()
            mail.logout()

            if email_found:
                break

        except Exception as e:
            print(f"   ⚠️  IMAP error: {e}")

        # Wait before next attempt
        if not email_found and attempt < max_attempts:
            time.sleep(2)

    # Step 3: Verify email was found and content matches
    print("\n🔍 Step 3: Verifying email content...")
    assert (
        email_found
    ), f"Email with unique ID '{unique_id}' not found after {max_attempts} attempts"
    assert email_body is not None, "Email body was empty"
    assert unique_id in email_body, f"Unique ID '{unique_id}' not found in email body"

    print("✅ Email content verified successfully!")
    print(f"\n🎉 Ethereal Email integration test PASSED!")


if __name__ == "__main__":
    # Allow running directly for quick testing
    test_ethereal_send_and_remockuve()
