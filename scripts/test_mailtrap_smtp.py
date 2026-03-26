#!/usr/bin/env python3
"""
Test Mailtrap by sending verification emails via API

Uses EmailManager for intelligent rate limiting, exponential backoff, and retries.

Usage:
    cd ${AGENT_HOME} && source venv/bin/activate && source .envrc
    python scripts/test_mailtrap_smtp.py
"""

import os
import sys

import requests

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.email_providers.email_manager import EmailManager


def _get_mailtrap_api_token() -> str | None:
    """Return API token if configured, printing guidance when missing."""
    api_token = os.getenv("MAILTRAP_API_TOKEN")
    if api_token:
        return api_token
    print("\n❌ ERROR: Missing MAILTRAP_API_TOKEN")
    print("Add this to your .env file:")
    print("   MAILTRAP_API_TOKEN=<your-api-token>")
    return None


def _build_test_recipients() -> list[dict[str, str]]:
    return [
        {"email": "rufus@loopclosertests.mailtrap.io", "name": "Rufus McWoof"},
        {"email": "fido@loopclosertests.mailtrap.io", "name": "Fido Fetchsworth"},
        {"email": "daisy@loopclosertests.mailtrap.io", "name": "Daisy Pawsalot"},
    ]


def _send_via_mailtrap_api(
    api_token: str, to_email: str, subject: str, html_body: str, text_body: str
) -> bool:
    """Send one email through the Mailtrap API."""
    try:
        url = "https://sandbox.api.mailtrap.io/api/send/4102679"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "from": {"email": "system@demomailtrap.co", "name": "LoopCloser (Test)"},
            "to": [{"email": to_email}],
            "subject": subject,
            "text": text_body,
            "html": html_body,
            "category": "LoopCloser",
        }
        response = requests.post(url, headers=headers, json=payload, timeout=30)  # B113
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"   → ✅ Sent to {to_email}")
                return True
            print(f"   → ❌ API error for {to_email}: {result}")
            return False
        if response.status_code == 429:
            print(f"   → ⏳ Rate limited for {to_email} (will retry with backoff)")
            return False
        print(f"   → ❌ HTTP {response.status_code} for {to_email}")
        return False
    except Exception as e:
        print(f"   → ❌ Error sending to {to_email}: {e}")
        return False


def _report_mailtrap_results(
    stats: dict[str, int], email_manager: EmailManager
) -> bool:
    """Print final send statistics and return success."""
    print("\n" + "=" * 60)
    print("📊 Final Results:")
    print(f"   ✅ Sent: {stats['sent']}")
    print(f"   ❌ Failed: {stats['failed']}")
    print(f"   ⏳ Pending: {stats['pending']}")

    if stats["failed"] > 0:
        print("\n❌ Failed Jobs:")
        for job in email_manager.get_failed_jobs():
            print(f"   - {job.to_email}: {job.last_error} (attempts: {job.attempts})")

    if stats["sent"] == len(_build_test_recipients()):
        print("\n✅ SUCCESS! All test emails sent to Mailtrap!")
        print("\n📬 Check your Mailtrap inbox:")
        print("   https://mailtrap.io/inboxes")
        return True

    print(
        f"\n⚠️  PARTIAL SUCCESS: {stats['sent']}/{len(_build_test_recipients())} sent"
    )
    return False


def test_mailtrap_api() -> bool:
    """Test Mailtrap API by sending verification emails"""

    print("\n🔍 Testing Mailtrap API with EmailManager...")
    print("=" * 60)

    api_token = _get_mailtrap_api_token()
    if not api_token:
        return False

    print(f"\n📧 Configuration:")
    print(f"   API Token: {'*' * len(api_token)}")
    print(f"   From: system@demomailtrap.co")
    print(f"   Rate Limiting: 1 email every 10 seconds")
    print(f"   Retry Logic: 3 attempts with exponential backoff (5s, 10s, 20s)")

    test_recipients = _build_test_recipients()

    print(f"\n📨 Queueing {len(test_recipients)} test emails...")

    # Create email manager with conservative settings for Mailtrap free plan
    email_manager = EmailManager(
        rate=0.1,  # 1 email every 10 seconds
        max_retries=3,
        base_delay=5.0,  # Start with 5 second delay
        max_delay=60.0,  # Cap at 60 seconds
    )

    # Add all emails to the queue
    for recipient in test_recipients:
        email_manager.add_email(
            to_email=recipient["email"],
            subject="Verify your LoopCloser account",
            html_body=f"<h1>Hello {recipient['name']}!</h1><p>Please verify your account.</p>",
            text_body=f"Hello {recipient['name']}! Please verify your account.",
            metadata={"name": recipient["name"]},
        )
        print(f"   ✓ Queued: {recipient['name']} ({recipient['email']})")

    # Send all emails with intelligent rate limiting and retries
    print("\n🚀 Starting intelligent email sending...")
    print("   (Rate limiting + exponential backoff will manage timing)")
    print()

    stats = email_manager.send_all(
        lambda to_email, subject, html_body, text_body: _send_via_mailtrap_api(
            api_token, to_email, subject, html_body, text_body
        ),
        timeout=60,
    )
    return _report_mailtrap_results(stats, email_manager)


if __name__ == "__main__":
    success = test_mailtrap_api()
    sys.exit(0 if success else 1)
