#!/usr/bin/env python3
"""
Quick test script for Mailtrap SMTP configuration

Tests that Mailtrap SMTP is working by sending test emails.
Run after setting up Mailtrap account and configuring .env file.

Usage:
    cd ${AGENT_HOME} && source venv/bin/activate && source .envrc
    python scripts/test_mailtrap_smtp.py
"""

import os
import sys

from flask import Flask

from email_service import EmailService


def test_mailtrap_smtp():
    """Test Mailtrap SMTP by sending verification email"""
    
    print("\n🔍 Testing Mailtrap SMTP Configuration...")
    print("=" * 60)
    
    # Check required env vars
    required_vars = ["MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_SERVER"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print("\n❌ ERROR: Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\nAdd these to your .env file:")
        print("   MAIL_SERVER=sandbox.smtp.mailtrap.io")
        print("   MAIL_PORT=2525")
        print("   MAIL_USERNAME=<your-mailtrap-username>")
        print("   MAIL_PASSWORD=<your-mailtrap-password>")
        return False
    
    # Check if Mailtrap is configured
    mail_server = os.getenv("MAIL_SERVER", "")
    if "mailtrap" not in mail_server.lower():
        print(f"\n⚠️  WARNING: MAIL_SERVER is set to '{mail_server}'")
        print("   This doesn't look like Mailtrap. Expected: sandbox.smtp.mailtrap.io")
        print("   Continuing anyway...")
    
    # Create Flask app context
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-key"
    app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "sandbox.smtp.mailtrap.io")
    app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", "2525"))
    app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "false").lower() == "true"
    app.config["MAIL_USE_SSL"] = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
    app.config["MAIL_DEFAULT_SENDER"] = os.getenv(
        "MAIL_DEFAULT_SENDER", "system@lassietests.mailtrap.io"
    )
    app.config["MAIL_SUPPRESS_SEND"] = False  # Enable real sending
    app.config["BASE_URL"] = os.getenv("BASE_URL", "http://localhost:3001")
    
    # Print config (hide password)
    print(f"\n📧 Configuration:")
    print(f"   Server: {app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']}")
    print(f"   TLS: {app.config['MAIL_USE_TLS']}")
    print(f"   SSL: {app.config['MAIL_USE_SSL']}")
    print(f"   From: {app.config['MAIL_DEFAULT_SENDER']}")
    print(f"   Username: {app.config['MAIL_USERNAME']}")
    print(f"   Password: {'*' * 16} (hidden)")
    
    EmailService.configure_app(app)
    
    # Test recipients (all caught by Mailtrap)
    test_recipients = [
        ("rufus@lassietests.mailtrap.io", "Rufus McWoof"),
        ("fido@lassietests.mailtrap.io", "Fido Fetchsworth"),
        ("daisy@lassietests.mailtrap.io", "Daisy Pawsalot"),
    ]
    
    print(f"\n📨 Sending {len(test_recipients)} test emails...")
    print("   All emails will be caught in your Mailtrap inbox")
    
    success_count = 0
    
    try:
        with app.app_context():
            for email, name in test_recipients:
                print(f"\n   → Sending to {name} ({email})...")
                
                success = EmailService.send_verification_email(
                    email=email,
                    verification_token=f"test-token-{name.replace(' ', '-').lower()}",
                    user_name=name
                )
                
                if success:
                    print(f"      ✅ Sent successfully")
                    success_count += 1
                else:
                    print(f"      ❌ Failed")
        
        print(f"\n{'=' * 60}")
        print(f"📊 Results: {success_count}/{len(test_recipients)} emails sent")
        
        if success_count == len(test_recipients):
            print("\n✅ SUCCESS! All test emails sent to Mailtrap!")
            print(f"\n📬 Check your Mailtrap inbox:")
            print(f"   https://mailtrap.io/inboxes")
            print(f"   Look for {len(test_recipients)} verification emails")
            print(f"   Subjects: 'Verify your Course Record Updater account'")
            return True
        else:
            print(f"\n⚠️  PARTIAL SUCCESS: {success_count} sent, {len(test_recipients) - success_count} failed")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\n💡 Common issues:")
        print("   - Wrong Mailtrap credentials")
        print("   - Incorrect server/port (should be sandbox.smtp.mailtrap.io:2525)")
        print("   - Network/firewall issues")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Mailtrap SMTP Test Script")
    print("=" * 60)
    
    success = test_mailtrap_smtp()
    
    print("\n" + "=" * 60)
    
    sys.exit(0 if success else 1)

