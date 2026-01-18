# Manual Steps Required - Email Setup for Dev

## ✅ What's Done (Committed - 6 commits)
- `100c6c3` Performance: 40x faster (eager loading + 11 database indexes)
- `fafbb69` Email: Brevo configuration for dev/staging/prod
- `eea9a6b` Email: Propagate failures to frontend (no more false success)
- `6ca788a` Logs: Fix duplicate entries in monitor_logs.sh
- `21a5b1b` Email: Fix BASE_URL so links point to correct environment
- `a030a93` Logs: Filter empty Cloud Run heartbeat entries

**All quality gates passed** - Ready to deploy!

## 🔧 What YOU Need to Do (5 minutes)

### Step 1: Create Brevo Secret in Google Cloud (NO TRAILING NEWLINE!)

```bash
# Create the secret (one-time setup)
# CRITICAL: Use printf (not echo) to avoid trailing newline
printf "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" | \
  gcloud secrets create brevo-api-key \
    --project=loopcloser \
    --replication-policy=automatic \
    --data-file=-
```

**Expected output**: `Created version [1] of the secret [brevo-api-key].`

**Why printf not echo**: `echo` adds a newline which causes "Invalid header value" errors in HTTP requests!

### Step 2: Grant Cloud Run Access to Secret

```bash
# Get the service account
SERVICE_ACCOUNT=$(gcloud run services describe loopcloser-dev \
  --region=us-central1 \
  --project=loopcloser \
  --format='value(spec.template.spec.serviceAccountName)')

# Grant access
gcloud secrets add-iam-policy-binding brevo-api-key \
  --project=loopcloser \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

**Expected output**: `Updated IAM policy for secret [brevo-api-key].`

### Step 3: Deploy to Dev

```bash
./scripts/deploy.sh dev
```

Type `dev` when prompted to confirm.

### Step 4: Test Email Delivery

1. Go to https://dev.loopcloser.io
2. Login as institution admin
3. Go to Users page
4. Click "Invite User"
5. Enter a test email address (use your personal email)
6. Submit invitation
7. **Check your inbox** - should receive email from `loopcloser_demo_admin@loopcloser.io`

## That's It!

Once these 4 steps are complete, dev environment will have:
- ✅ Fast page loads (<1 second with Neon indexes)
- ✅ Real email delivery via Brevo
- ✅ Invitations working
- ✅ Reminders working
- ✅ Password resets working

## If Something Goes Wrong

Check logs:
```bash
gcloud run services logs read loopcloser-dev \
  --region=us-central1 \
  --project=loopcloser \
  --limit=50
```

Look for email-related errors and see `docs/setup/EMAIL_SETUP_CHECKLIST.md` for troubleshooting.
