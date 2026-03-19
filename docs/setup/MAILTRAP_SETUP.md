# Mailtrap Setup for E2E Email Testing

## Current Status

❌ **Mailtrap API is returning 404** - credentials or endpoint may need updating

## What Works

✅ **Sending emails via SMTP** - emails successfully delivered to Mailtrap inbox
✅ **Manual verification** - emails visible in Mailtrap UI at https://mailtrap.io

## What Doesn't Work

❌ **Fetching emails via API** - 404 error when trying to read inbox programmatically

## Current Configuration (`.envrc`)

```bash
export MAILTRAP_API_TOKEN="2d0c4c393d8240c54697b0ab4a7e894b"
export MAILTRAP_ACCOUNT_ID="335505888614cb"
export MAILTRAP_INBOX_ID="4102679"
```

## Troubleshooting Steps

### 1. Verify API Token

1. Log in to Mailtrap: https://mailtrap.io
2. Go to **Settings** → **API Tokens**
3. Check if token `2d0c4c393d8240c54697b0ab4a7e894b` is listed and active
4. If not, generate a new token and update `.envrc`

### 2. Find Correct Inbox ID

1. In Mailtrap, navigate to your inbox
2. URL format: `https://mailtrap.io/inboxes/{INBOX_ID}/messages`
3. The inbox ID in URL should match `MAILTRAP_INBOX_ID` in `.envrc`
4. Currently configured: `4102679`

### 3. Find Correct Account ID

1. In Mailtrap, go to **Settings** → **API**
2. Look for "Account ID" in the API documentation section
3. Update `MAILTRAP_ACCOUNT_ID` in `.envrc`

### 4. Test API Manually

```bash
# Source environment
source .envrc

# Test API access
curl -X GET \
  "https://sandbox.api.mailtrap.io/api/accounts/${MAILTRAP_ACCOUNT_ID}/inboxes/${MAILTRAP_INBOX_ID}/messages" \
  -H "Api-Token: ${MAILTRAP_API_TOKEN}"
```

**Expected**: JSON array of emails  
**Current**: `404 Not Found`

### 5. Alternative: Check for API v2

Mailtrap may have migrated to a new API version. Check their docs:

- https://api-docs.mailtrap.io/
- Look for the correct endpoint format for sandbox testing

## Temporary Workaround

For now, email **sending** works but **automated E2E verification** is blocked by the API 404.

Options:

1. **Fix Mailtrap API credentials** (recommended)
2. **Use manual verification** - check Mailtrap UI during test runs
3. **Switch to different email testing service** - Mailosaur, Gmail API, etc.

## Next Steps

**USER ACTION REQUIRED**: Please verify your Mailtrap credentials and update `.envrc` with correct values.

Once fixed, UAT-001 will test the complete flow including email verification!
