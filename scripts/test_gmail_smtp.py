#!/usr/bin/env python3
"""
Quick test script for Gmail SMTP configuration

Tests that Gmail SMTP is working by sending a test email.
Run after creating Gmail test accounts and setting up .env file.

Usage:
    cd ${AGENT_HOME} && source venv/bin/activate && source .envrc
    python scripts/test_gmail_smtp.py
"""

import os
import sys

from flask import Flask

from email_service import EmailService


def test_gmail_smtp():
    """Test Gmail SMTP by sending verification email"""
    
    print("\n🔍 Testing Gmail SMTP Configuration...")
    print("=" * 60)
    
    # Check required env vars
    required_vars = ["MAIL_USERNAME", "MAIL_PASSWORD"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print("\n❌ ERROR: Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\nAdd these to your .env file:")
        print("   MAIL_USERNAME=lassie.tests.system.test@gmail.com")
        print("   MAIL_PASSWORD=xxxx-xxxx-xxxx-xxxx  # App password from Gmail")
        return False
    
    # Create Flask app context
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-key"  # nosec B105  # nosemgrep
    app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", "587"))
    app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
    app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", os.getenv("MAIL_USERNAME"))
    app.config["MAIL_SUPPRESS_SEND"] = False  # Enable real sending
    app.config["BASE_URL"] = os.getenv("BASE_URL", "http://localhost:3001")
    
    # Print config (hide password)
    print(f"\n📧 Configuration:")
    print(f"   Server: {app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']}")
    print(f"   TLS: {app.config['MAIL_USE_TLS']}")
    print(f"   From: {app.config['MAIL_DEFAULT_SENDER']}")
    print(f"   Username: {app.config['MAIL_USERNAME']}")
    print(f"   Password: {'*' * 16} (hidden)")
    
    EmailService.configure_app(app)
    
    # Test recipient (send to first instructor account)
    test_recipient = "lassie.tests.instructor1.test@gmail.com"
    
    print(f"\n📨 Sending test email to: {test_recipient}")
    print("   Subject: Verify your Course Record Updater account")
    print("   Type: Email verification")
    
    try:
        with app.app_context():
            success = EmailService.send_verification_email(
                email=test_recipient,
                verification_token="test-token-12345",  # nosec B106
                user_name="Bella Barkington"
            )
        
        if success:
            print("\n✅ SUCCESS! Test email sent successfully!")
            print(f"\n📬 Check the inbox: {test_recipient}")
            print("   Look for: 'Verify your Course Record Updater account'")
            print("   From: Course Record Updater (Test)")
            return True
        else:
            print("\n❌ FAILED: Email provider reported failure")
            print("   Check logs above for error details")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\n💡 Common issues:")
        print("   - Wrong app password (should be 16 chars from Gmail)")
        print("   - 2FA not enabled (required for app passwords)")
        print("   - Account locked (too many failed attempts)")
        print("   - Username should be full email address")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Gmail SMTP Test Script")
    print("=" * 60)
    
    success = test_gmail_smtp()
    
    print("\n" + "=" * 60)
    
    sys.exit(0 if success else 1)

