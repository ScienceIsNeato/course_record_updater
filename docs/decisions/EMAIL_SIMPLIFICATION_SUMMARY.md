# Email System Simplification - Summary

## What Changed

### Architecture Simplification
**Before:** 5 email providers (Console, Gmail, Mailtrap SMTP, Mailtrap API, Ethereal)
**After:** 2 email providers (Brevo, Ethereal)

### Provider Roles
- **Brevo**: ALL real email sending (local dev, staging, prod)
  - 300 emails/day free tier
  - Reliable transactional email service
  - API-based (no SMTP complexity)
  
- **Ethereal**: E2E testing ONLY
  - Fake SMTP with IMAP verification
  - Used in automated tests to verify email delivery
  - NOT for manual sending

### Files Deleted
- `email_providers/console_provider.py` - No longer needed
- `email_providers/gmail_provider.py` - Replaced by Brevo
- `email_providers/mailtrap_provider.py` - Replaced by Brevo
- `tests/unit/test_mailtrap_provider.py` - Obsolete tests

### Files Created
- `.envrc.template` - Environment configuration template for different deployments
- `EMAIL_SIMPLIFICATION_SUMMARY.md` - This file

### Files Modified
- `email_providers/factory.py` - Simplified to Brevo + Ethereal only
- `email_providers/__init__.py` - Updated exports
- `email_providers/base_provider.py` - Extended with `read_email()` method
- `email_providers/ethereal_provider.py` - Implemented `read_email()` via IMAP
- `email_providers/brevo_provider.py` - Created Brevo API integration
- `.envrc` - Simplified email configuration
- `tests/unit/test_email_factory.py` - Added Brevo tests

## Configuration

### Email Provider Selection
**New feature:** `EMAIL_PROVIDER` environment variable for explicit provider selection.

**Logic:**
1. If `EMAIL_PROVIDER` is set → use that provider (explicit override)
2. Otherwise, use environment-based mapping:
   - `ENV=test` or `TESTING=true` → `ethereal`
   - `ENV=development/staging/production` → `brevo`

**Recommendation:** Always set `EMAIL_PROVIDER` explicitly to avoid ambiguity.

### Local Development (.envrc)
```bash
# Explicit provider selection (recommended)
export EMAIL_PROVIDER="brevo"

# Brevo configuration (always configure both providers)
export BREVO_API_KEY="your-api-key"
export BREVO_SENDER_EMAIL="your-email@example.com"
export BREVO_SENDER_NAME="Your Name"

# Ethereal configuration (used in E2E tests)
export ETHEREAL_USER="your-user@ethereal.email"
export ETHEREAL_PASS="your-password"
export ETHEREAL_SMTP_HOST="smtp.ethereal.email"
export ETHEREAL_SMTP_PORT="587"
export ETHEREAL_IMAP_HOST="imap.ethereal.email"
export ETHEREAL_IMAP_PORT="993"
```

### Staging
Same as local, but with production Brevo API key

### Production
```bash
# Explicit provider selection
export EMAIL_PROVIDER="brevo"

# Brevo for real email sending
export BREVO_API_KEY="production-api-key"
export BREVO_SENDER_EMAIL="noreply@courserecord.app"
export BREVO_SENDER_NAME="LoopCloser"

# Set production flags
export ENV="production"
export PRODUCTION="true"
```

### E2E Testing
```bash
# Explicit provider selection for E2E tests
export EMAIL_PROVIDER="ethereal"

# Or rely on environment mapping
export ENV="test"  # Auto-selects ethereal

# Ethereal configuration
export ETHEREAL_USER="test@ethereal.email"
export ETHEREAL_PASS="password"
# ... (other Ethereal settings)
```

## Testing Status

### ✅ Passing
- Email factory tests (Brevo + Ethereal creation)
- Ethereal provider tests
- Email template tests
- URL building tests
- Protected domain detection tests

### ⚠️ Needs Fixing
- Tests mocking `gmail_provider` (no longer exists)
- SMTP configuration tests (no longer using SMTP config)

## Next Steps

1. **Fix failing tests** - Update to use whitelisted emails or mock whitelist
2. **Update test fixtures** - Remove Gmail/Mailtrap/Console provider references
3. **Run full test suite** - Ensure all tests pass
4. **Manual testing** - Send test email via Brevo to verify integration
5. **Update documentation** - README, setup guides, etc.

## Benefits

1. **Simpler**: 2 providers instead of 5
2. **Reliable**: Brevo is a production-grade service
4. **Cheaper**: 300 emails/day free tier (vs Gmail app password complexity)
5. **Testable**: Ethereal provides full IMAP verification for E2E tests
6. **Maintainable**: Less code, fewer dependencies, clearer architecture

## Brevo MCP Tools

The Brevo MCP server is installed and provides tools for:
- Contact management (`get_contacts`, `create_contact`, `update_contact`, `delete_contact`)
- Campaign management (`create_email_campaign`, `send_email_campaign`, etc.)
- Deal management

**Note:** Brevo MCP tools do NOT support reading email inboxes (send-only). Use Ethereal for E2E email verification.

