# Email System V1 Implementation Guide

## Overview

Implementing swappable email infrastructure for CEI demo with Gmail SMTP integration and E2E testing capabilities.

## Phase 1: Email Service Interface ✅ COMPLETE

### What Was Built

**New Infrastructure (`email_providers/` package):**
- `base_provider.py`: Abstract EmailProvider interface
- `console_provider.py`: Development mode provider (logs to console/files)
- `gmail_provider.py`: Gmail SMTP provider for production  
- `factory.py`: Provider selection based on configuration

**Refactored:**
- `email_service.py`: Now uses provider pattern
- Maintains 100% backward compatibility
- All existing public methods unchanged

### Benefits
- Zero breaking changes
- Swappable email providers (Gmail → SendGrid/Mailgun later)
- Clean separation of concerns (templates vs. transport)
- Easier testing with ConsoleProvider

### Testing
- All 36 email service unit tests pass
- Global coverage maintained at 81.92%
- Type-safe with mypy strict mode

---

## Phase 2: Gmail Test Account Setup (NEXT)

### Test Email Strategy (Hybrid Approach)

**🎯 Best of Both Worlds:**
- **Bella Barkington** = Real Gmail (test actual delivery)
- **Everyone else** = Mailtrap (sandbox testing, no phone verification needed)

| # | Email Address | Display Name | Role | Provider | Status |
|---|--------------|--------------|------|----------|--------|
| 1 | lassie.tests.instructor1.test@gmail.com | Bella Barkington | Instructor | Gmail | ✅ Created |
| 2 | rufus@lassietests.mailtrap.io | Rufus McWoof | Instructor | Mailtrap | ⬜ Auto-configured |
| 3 | fido@lassietests.mailtrap.io | Fido Fetchsworth | Program Admin | Mailtrap | ⬜ Auto-configured |
| 4 | daisy@lassietests.mailtrap.io | Daisy Pawsalot | Institution Admin | Mailtrap | ⬜ Auto-configured |
| 5 | system@lassietests.mailtrap.io | Lassie Test System | System Sender | Mailtrap | ⬜ Auto-configured |

**Why This Works:**
- ✅ No more phone verification issues
- ✅ All emails caught in Mailtrap inbox (no spam risk)
- ✅ Can test real Gmail delivery with Bella
- ✅ Mailtrap has API for E2E test verification
- ✅ Free tier: 100 emails/month

---

## Setup Part 1: Mailtrap (No Phone Verification Needed!)

### Create Mailtrap Account (~5 minutes)

1. **Sign Up**
   - Go to https://mailtrap.io/
   - Click "Sign Up" (free tier is fine)
   - Use your personal email
   - Verify email

2. **Create Project**
   - Name: "Lassie Tests"
   - Click "Create Project"

3. **Get SMTP Credentials**
   - Click on "Email Testing" → "Inboxes"
   - Click on "My Inbox" (default inbox)
   - Click "Show Credentials"
   - You'll see:
     ```
     Host: sandbox.smtp.mailtrap.io
     Port: 2525 or 587
     Username: [copy this]
     Password: [copy this]
     ```

4. **Save Credentials** (you'll need these for `.env` file)

---

## Setup Part 2: Bella's Gmail Account (Already Done! ✅)

**Completed:**
- ✅ Account created: `lassie.tests.instructor1.test@gmail.com`
- ✅ Name: Bella Barkington
- ⏳ Still need: App Password for Gmail SMTP

### Generate App Password for Bella (~2 minutes)

1. **Enable 2FA** (if not done)
   - Go to https://myaccount.google.com/security
   - Enable "2-Step Verification"

2. **Generate App Password**
   - Go to https://myaccount.google.com/apppasswords
   - App: "Mail" | Device: "Other (Course Record)"
   - Copy the 16-character password
   - Save it securely

---

## Configuration

Add to your `.env` file:

```bash
# ===== PRIMARY SMTP (Mailtrap for testing) =====
MAIL_SERVER=sandbox.smtp.mailtrap.io
MAIL_PORT=2525
MAIL_USE_TLS=false
MAIL_USE_SSL=false
MAIL_USERNAME=<your-mailtrap-username>
MAIL_PASSWORD=<your-mailtrap-password>
MAIL_DEFAULT_SENDER=system@lassietests.mailtrap.io
MAIL_DEFAULT_SENDER_NAME=Course Record Updater (Test)
MAIL_SUPPRESS_SEND=false  # Enable real sending to Mailtrap

# ===== OPTIONAL: Bella's Gmail for live testing =====
# Uncomment these to test real Gmail delivery
# MAIL_SERVER=smtp.gmail.com
# MAIL_PORT=587
# MAIL_USE_TLS=true
# MAIL_USERNAME=lassie.tests.instructor1.test@gmail.com
# MAIL_PASSWORD=<bella-app-password>
# MAIL_DEFAULT_SENDER=lassie.tests.instructor1.test@gmail.com

# ===== Mailtrap API (for E2E test verification) =====
MAILTRAP_API_TOKEN=<get-from-mailtrap-settings>
```

**⏱️ Total Setup Time**: ~10 minutes (vs 30-45 for all Gmail accounts!)

---

## Testing Setup

Once you've set up your email provider (Mailtrap or Gmail), test it:

### Test Mailtrap SMTP

```bash
cd ${AGENT_HOME} && source venv/bin/activate && source .envrc
python scripts/test_mailtrap_smtp.py
```

**Expected Output:**
```
🔍 Testing Mailtrap SMTP Configuration...
============================================================

📧 Configuration:
   Server: sandbox.smtp.mailtrap.io:2525
   From: system@lassietests.mailtrap.io
   Username: <your-username>

📨 Sending 3 test emails...
   All emails will be caught in your Mailtrap inbox

   → Sending to Rufus McWoof (rufus@lassietests.mailtrap.io)...
      ✅ Sent successfully
   → Sending to Fido Fetchsworth (fido@lassietests.mailtrap.io)...
      ✅ Sent successfully
   → Sending to Daisy Pawsalot (daisy@lassietests.mailtrap.io)...
      ✅ Sent successfully

============================================================
📊 Results: 3/3 emails sent

✅ SUCCESS! All test emails sent to Mailtrap!

📬 Check your Mailtrap inbox:
   https://mailtrap.io/inboxes
   Look for 3 verification emails
```

### Test Gmail SMTP (optional - for Bella)

If you want to test real Gmail delivery with Bella:

1. Update `.env` to use Gmail:
```bash
# Comment out Mailtrap, uncomment Gmail
# MAIL_SERVER=sandbox.smtp.mailtrap.io
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=lassie.tests.instructor1.test@gmail.com
MAIL_PASSWORD=<bella-app-password>
```

2. Run test:
```bash
cd ${AGENT_HOME} && source venv/bin/activate && source .envrc
python scripts/test_gmail_smtp.py
```

3. Check Bella's inbox:
- Login to `lassie.tests.instructor1.test@gmail.com`
- Look for email from "Course Record Updater (Test)"
- Subject: "Verify your Course Record Updater account"

**Note:** For most testing, stick with Mailtrap. Only use Gmail when you need to verify actual delivery.

---

### Environment Configuration Matrix

| Environment | Provider | Email Sending | Recipient Filter |
|------------|----------|---------------|------------------|
| Local Dev | console | No (logs only) | N/A |
| CI/Testing | console | No (logs only) | N/A |
| Staging | gmail | Yes | Test accounts only |
| Production | gmail | Yes | Real users |

### Safety Measures

Enhance protected domain check in `email_service.py`:

```python
# In non-production: ONLY allow test accounts
if not is_production:
    if "@gmail.com" in to_email:
        # Only allow our test accounts
        if "lassie.tests" not in to_email or "test" not in to_email:
            raise EmailServiceError("Only lassie.tests accounts allowed in dev")
    # Existing protected domain check continues...
```

---

## Phase 3: E2E Email Verification Infrastructure

### Gmail API Setup

1. **Create Google Cloud Project**
   - Visit https://console.cloud.google.com
   - Create project: "Course Record Email Testing"

2. **Enable Gmail API**
   - Go to APIs & Services → Library
   - Search for "Gmail API"
   - Enable it

3. **Create OAuth2 Credentials**
   - Go to APIs & Services → Credentials
   - Create OAuth 2.0 Client ID
   - Application type: Desktop app
   - Name: "Email Testing Client"
   - Download credentials JSON

4. **Generate Refresh Tokens**
   - Use Google's OAuth2 playground or custom script
   - Scope: https://www.googleapis.com/auth/gmail.readonly
   - Generate refresh token for each test account
   - Store in `.env` (NOT committed)

### GmailVerifier Helper

Create `tests/e2e/email_helpers.py`:

```python
"""
Gmail API helper for E2E email verification
"""
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
import time
import re

class GmailVerifier:
    """Helper to verify emails sent during E2E tests"""
    
    def __init__(self, test_account_email: str, refresh_token: str):
        """Initialize with OAuth2 credentials"""
        self.email = test_account_email
        self.creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GMAIL_CLIENT_ID"),
            client_secret=os.getenv("GMAIL_CLIENT_SECRET")
        )
        self.service = build('gmail', 'v1', credentials=self.creds)
        
    def wait_for_email(self, subject_contains: str, timeout: int = 30):
        """Poll inbox for email matching criteria"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            messages = self.service.users().messages().list(
                userId='me',
                q=f'subject:{subject_contains} is:unread'
            ).execute()
            
            if messages.get('messages'):
                return self._get_message(messages['messages'][0]['id'])
                
            time.sleep(2)
            
        raise TimeoutError(f"Email with subject '{subject_contains}' not found within {timeout}s")
        
    def extract_verification_link(self, message):
        """Parse email body for verification/reset links"""
        # Extract link from email body
        body = self._get_email_body(message)
        match = re.search(r'(http[s]?://[^\s]+/verify-email/[^\s<]+)', body)
        if match:
            return match.group(1)
        raise ValueError("Verification link not found in email")
        
    def cleanup_inbox(self, older_than_hours: int = 24):
        """Delete old test emails"""
        # Implementation...
```

### E2E Test Example

Create `tests/e2e/test_email_flows.py`:

```python
def test_registration_email_flow():
    """Test complete registration → verification flow"""
    verifier = GmailVerifier(
        "lassie.tests.instructor1.test@gmail.com",
        os.getenv("INSTRUCTOR1_GMAIL_TOKEN")
    )
    
    # 1. Register user
    response = client.post('/api/register/institution-admin', json={
        'email': 'lassie.tests.instructor1.test@gmail.com',
        'password': 'TestPassword123!',
        # ... other fields
    })
    assert response.status_code == 201
    
    # 2. Wait for verification email
    email = verifier.wait_for_email('Verify your', timeout=30)
    assert email is not None
    
    # 3. Extract verification link
    verify_link = verifier.extract_verification_link(email)
    assert '/verify-email/' in verify_link
    
    # 4. Click verification link
    token = verify_link.split('/verify-email/')[1]
    response = client.get(f'/verify-email/{token}')
    assert response.status_code == 200
    
    # 5. Verify account activated
    # Check that user can now login...
```

---

## Phase 4: Admin Instructor Reminder Feature

### Data Model

Add to `models.py` or create new table:

```python
class InstructorReminder(db.Model):
    """Track instructor reminder emails"""
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    institution_id = db.Column(db.String(36), ForeignKey('institutions.id'))
    term_id = db.Column(db.String(36), ForeignKey('terms.id'))
    sent_by_user_id = db.Column(db.String(36), ForeignKey('users.id'))
    recipient_user_ids = db.Column(JSON)  # List of instructor IDs
    subject = db.Column(db.String(200))
    message = db.Column(db.Text)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    reminder_type = db.Column(db.String(50), default='course_submission_request')
```

### Email Template

Add to `email_service.py`:

```python
@staticmethod
def send_course_submission_reminder(
    email: str,
    instructor_name: str,
    admin_name: str,
    term_name: str,
    deadline: Optional[str] = None,
    personal_message: Optional[str] = None,
) -> bool:
    """
    Send course submission reminder to instructor
    
    Args:
        email: Instructor email
        instructor_name: Instructor's name
        admin_name: Admin sending reminder
        term_name: Academic term
        deadline: Optional submission deadline
        personal_message: Optional message from admin
    """
    subject = f"Course Data Submission Reminder - {term_name}"
    
    # Generate HTML and text templates
    # Include link to course management page
    # Include deadline if provided
    # Include personal message if provided
    
    return EmailService._send_email(...)
```

### API Endpoint

Add to `api_routes.py` or new file:

```python
@api.route("/admin/send-instructor-reminders", methods=["POST"])
@login_required
def send_instructor_reminders():
    """Send course submission reminders to instructors"""
    # Verify admin permissions
    # Validate request data
    # Send emails to each instructor
    # Track in database
    # Return summary
```

### UI Component

Add to `templates/dashboard/institution_admin.html`:

- "Send Reminders" button
- Modal with:
  - Term selector dropdown
  - Instructor multi-select checkboxes
  - Optional personal message textarea
  - Preview button
  - Send button with confirmation

JavaScript in `static/instructor_reminder.js`:
- Handle instructor selection
- Message preview
- Batch sending with progress
- Success/error feedback

---

## Timeline & Effort Estimates

- **Phase 1** (Email Interface): ✅ Complete (~2 hours actual)
- **Phase 2** (Gmail Accounts): ~1 hour (manual setup)
- **Phase 3** (E2E Infrastructure): ~3-4 hours
- **Phase 4** (Reminder Feature): ~4-5 hours
- **Phase 5** (Testing & QA): ~2-3 hours
- **Phase 6** (Documentation): ~1-2 hours

**Total**: 13-17 hours remaining

---

## Success Criteria

- [x] Phase 1: Provider pattern implemented
- [ ] Phase 2: Gmail SMTP sends real emails  
- [ ] Phase 3: E2E tests verify email delivery
- [ ] Phase 4: Admins can send course reminders
- [ ] All transactional emails work (verification, reset, invitation, welcome)
- [ ] Documentation complete
- [ ] System ready for CEI demo

---

## Security Considerations

1. **Never commit credentials** (app passwords, refresh tokens)
2. **Test accounts only** in non-production
3. **Rate limiting** on reminder sends (max 50/hour)
4. **Protected domain check** remains active
5. **Audit logging** for all reminder sends

---

## Future Enhancements (Post-V1)

- Email queuing with Celery/Redis
- Email analytics (open rates, click rates)
- Migration to SendGrid/Mailgun
- Email preference management
- Bounce/complaint handling
- Template versioning

