"""
Quick test to verify Mailtrap scraper works
"""

import os
from datetime import datetime

from tests.e2e.mailtrap_scraper import wait_for_email


def test_scraper_basic():
    """Test that scraper can fetch emails from Mailtrap UI"""
    print("\n" + "=" * 60)
    print("🔬 Testing Mailtrap UI Scraper")
    print("=" * 60)

    # Check environment
    username = os.getenv("MAILTRAP_API_USERNAME")
    password = os.getenv("MAILTRAP_API_PASSWORD")
    inbox_id = os.getenv("MAILTRAP_INBOX_ID")

    print(f"Username: {username}")
    print(f"Password: {'*' * len(password) if password else 'NOT SET'}")
    print(f"Inbox ID: {inbox_id}")

    if not all([username, password, inbox_id]):
        print("\n❌ Missing Mailtrap credentials in environment")
        return

    # Try to fetch the latest email (we know there are 10+ in the inbox)
    print("\n🔍 Attempting to fetch latest email...")

    email = wait_for_email(
        recipient_email="@loopclosertests.mailtrap.io",  # All test emails go here
        timeout=10,  # Should be instant since emails already exist
    )

    if email:
        print("\n✅ Successfully retrieved email!")
        print(f"   Subject: {email.get('subject', 'N/A')}")
        print(f"   To: {email.get('to', 'N/A')}")
        print(f"   From: {email.get('from', 'N/A')}")
        print(f"   Body preview: {email.get('body', '')[:100]}...")
    else:
        print("\n❌ Failed to retrieve email")


if __name__ == "__main__":
    test_scraper_basic()
