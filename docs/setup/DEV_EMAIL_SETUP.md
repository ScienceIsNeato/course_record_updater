# Email Setup for Dev Environment

## Solution Implemented ✅

Dev environment now uses **Brevo** for real email delivery (same as production).

**Configuration**:
- Email provider: Brevo (real SMTP)
- Credentials: Google Cloud Secret Manager (`brevo-api-key`)
- Sender: loopcloser_demo_admin@loopcloser.io
- Works for: Invitations, reminders, password resets

## Why It Doesn't Work

Looking at `deploy.sh` line 104, the only env vars set for dev are:
```bash
ENV_VARS="APP_ENV=dev,SESSION_COOKIE_SECURE=true,SESSION_COOKIE_HTTPONLY=true,SESSION_COOKIE_SAMESITE=Lax"
```

**Missing**:
- `EMAIL_PROVIDER` (not set)
- `BREVO_API_KEY` (not set)
- `ETHEREAL_*` credentials (not set)

**Email Provider Selection Logic** (from `email_providers/factory.py`):
1. If `EMAIL_PROVIDER` set → use that
2. If `ENV=test` or `TESTING=true` → use Ethereal
3. Otherwise → use Brevo (default for development/staging/production)

**Result**: Dev tries to use Brevo but has no `BREVO_API_KEY` → emails fail silently

## Solution Options

### Option 1: Use Ethereal (Recommended for Testing)
Ethereal is a fake SMTP service perfect for dev - you can view emails in browser without sending real emails.

**Steps**:
```bash
# Add EMAIL_PROVIDER and Ethereal creds to deploy.sh for dev
# Edit scripts/deploy.sh around line 104:

if [ "${ENVIRONMENT}" = "dev" ]; then
    ENV_VARS="${ENV_VARS},EMAIL_PROVIDER=ethereal,ETHEREAL_USER=your_ethereal_email@ethereal.email,ETHEREAL_PASS=your_ethereal_password"
fi
```

**Pros**:
- No real emails sent
- View emails at https://ethereal.email (login with credentials)
- Free, no rate limits
- Perfect for testing

**Cons**:
- Not real email delivery
- Can't test actual inbox delivery

### Option 2: Use Brevo (For Real Email)
Brevo sends real emails and is what production uses.

**Steps**:
```bash
# 1. Create secret in Google Secret Manager
gcloud secrets create brevo-api-key \
    --project=loopcloser \
    --replication-policy=automatic \
    --data-file=- <<< "your-brevo-api-key-here"

# 2. Update deploy.sh to use the secret (line 119):
    --update-secrets=DATABASE_URL=neon-dev-database-url:latest,BREVO_API_KEY=brevo-api-key:latest \
```

**Pros**:
- Real email delivery
- Same as production
- Tests actual email flow

**Cons**:
- Uses API quota
- Subject to Brevo rate limits
- Emails go to real inboxes (be careful!)

### Option 3: Quick Test with ENV=test
Force Ethereal by setting `ENV=test` (emails won't send but app won't crash):

```bash
# Edit deploy.sh line 104:
ENV_VARS="APP_ENV=${ENVIRONMENT},ENV=test,SESSION_COOKIE_SECURE=true..."
```

## Current State

**Dev environment has NO email configuration**, so:
- ✅ App works fine (doesn't crash)
- ❌ Emails silently fail  
- ❌ Invitations won't send
- ❌ Reminders won't send
- ❌ Password resets won't work

## Recommendation

For dev environment, I recommend **Option 1 (Ethereal)** because:
- Safe (no real emails)
- You can verify email content/delivery
- No quotas or rate limits
- Perfect for development testing

You already have Ethereal credentials in `.envrc`:
```bash
export ETHEREAL_USER="ta465kzuccljkwar@ethereal.email"
export ETHEREAL_PASS="b9JBrgBtAWkZ7FPZmy"
```

Just need to add these to Cloud Run via deploy.sh!
