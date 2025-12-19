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

from email_providers.email_manager import EmailManager


def test_mailtrap_api():
    """Test Mailtrap API by sending verification emails"""
    
    print("\n🔍 Testing Mailtrap API with EmailManager...")
    print("=" * 60)
    
    # Check required env vars
    api_token = os.getenv("MAILTRAP_API_TOKEN")
    
    if not api_token:
        print("\n❌ ERROR: Missing MAILTRAP_API_TOKEN")
        print("Add this to your .env file:")
        print("   MAILTRAP_API_TOKEN=<your-api-token>")
        return False
    
    print(f"\n📧 Configuration:")
    print(f"   API Token: {'*' * len(api_token)}")
    print(f"   From: system@demomailtrap.co")
    print(f"   Rate Limiting: 1 email every 10 seconds")
    print(f"   Retry Logic: 3 attempts with exponential backoff (5s, 10s, 20s)")
    
    # Test recipients
    test_recipients = [
        {
            "email": "rufus@loopclosertests.mailtrap.io",
            "name": "Rufus McWoof"
        },
        {
            "email": "fido@loopclosertests.mailtrap.io", 
            "name": "Fido Fetchsworth"
        },
        {
            "email": "daisy@loopclosertests.mailtrap.io",
            "name": "Daisy Pawsalot"
        }
    ]
    
    print(f"\n📨 Queueing {len(test_recipients)} test emails...")
    
    # Create email manager with conservative settings for Mailtrap free plan
    email_manager = EmailManager(
        rate=0.1,  # 1 email every 10 seconds
        max_retries=3,
        base_delay=5.0,  # Start with 5 second delay
        max_delay=60.0  # Cap at 60 seconds
    )
    
    # Add all emails to the queue
    for recipient in test_recipients:
        email_manager.add_email(
            to_email=recipient["email"],
            subject="Verify your Course Record Updater account",
            html_body=f"<h1>Hello {recipient['name']}!</h1><p>Please verify your account.</p>",
            text_body=f"Hello {recipient['name']}! Please verify your account.",
            metadata={"name": recipient["name"]}
        )
        print(f"   ✓ Queued: {recipient['name']} ({recipient['email']})")
    
    # Define the send function that EmailManager will call
    def send_via_mailtrap_api(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
        """Send email via Mailtrap API"""
        try:
            url = "https://sandbox.api.mailtrap.io/api/send/4102679"
            headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "from": {
                    "email": "system@demomailtrap.co",
                    "name": "Course Record Updater (Test)"
                },
                "to": [{"email": to_email}],
                "subject": subject,
                "text": text_body,
                "html": html_body,
                "category": "Course Record Updater"
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)  # B113
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print(f"   → ✅ Sent to {to_email}")
                    return True
                else:
                    print(f"   → ❌ API error for {to_email}: {result}")
                    return False
            elif response.status_code == 429:
                # Rate limited - let EmailManager handle retry
                print(f"   → ⏳ Rate limited for {to_email} (will retry with backoff)")
                return False
            else:
                print(f"   → ❌ HTTP {response.status_code} for {to_email}")
                return False
                
        except Exception as e:
            print(f"   → ❌ Error sending to {to_email}: {e}")
            return False
    
    # Send all emails with intelligent rate limiting and retries
    print("\n🚀 Starting intelligent email sending...")
    print("   (Rate limiting + exponential backoff will manage timing)")
    print()
    
    stats = email_manager.send_all(send_via_mailtrap_api, timeout=60)
    
    print("\n" + "=" * 60)
    print(f"📊 Final Results:")
    print(f"   ✅ Sent: {stats['sent']}")
    print(f"   ❌ Failed: {stats['failed']}")
    print(f"   ⏳ Pending: {stats['pending']}")
    
    # Show failed jobs if any
    if stats['failed'] > 0:
        print("\n❌ Failed Jobs:")
        for job in email_manager.get_failed_jobs():
            print(f"   - {job.to_email}: {job.last_error} (attempts: {job.attempts})")
    
    if stats['sent'] == len(test_recipients):
        print("\n✅ SUCCESS! All test emails sent to Mailtrap!")
        print("\n📬 Check your Mailtrap inbox:")
        print("   https://mailtrap.io/inboxes")
        return True
    else:
        print(f"\n⚠️  PARTIAL SUCCESS: {stats['sent']}/{len(test_recipients)} sent")
        return False


if __name__ == "__main__":
    success = test_mailtrap_api()
    sys.exit(0 if success else 1)