# Email Setup Checklist for Dev Environment

## ✅ Code Changes (COMPLETE)

- [x] Updated `scripts/deploy.sh` to include `EMAIL_PROVIDER=brevo` for dev
- [x] Updated `scripts/deploy.sh` to mount `BREVO_API_KEY` secret for dev
- [x] Updated `.github/workflows/deploy.yml` for CI deploy parity
- [x] Updated `docs/email_delivery.md` with dev environment details

## 🔧 Manual Steps Required (USER ACTION NEEDED)

### Step 1: Create/Verify Brevo Secret in Google Cloud

Run this command to create the secret (if it doesn't exist):

```bash
# Check if secret exists
gcloud secrets describe brevo-api-key --project=loopcloser 2>/dev/null

# If not found, create it:
echo "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" | \
  gcloud secrets create brevo-api-key \
    --project=loopcloser \
    --replication-policy=automatic \
    --data-file=-
```

**Verify**:
```bash
gcloud secrets versions access latest --secret=brevo-api-key --project=loopcloser
# Should output: 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
```

### Step 2: Grant Cloud Run Access to Secret

```bash
# Get the Cloud Run service account
SERVICE_ACCOUNT=$(gcloud run services describe loopcloser-dev \
  --region=us-central1 \
  --project=loopcloser \
  --format='value(spec.template.spec.serviceAccountName)')

echo "Service account: ${SERVICE_ACCOUNT}"

# Grant access to brevo-api-key secret
gcloud secrets add-iam-policy-binding brevo-api-key \
  --project=loopcloser \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 3: Add GitHub Secret for CI Deploys (Optional - if using GitHub Actions)

1. Go to: https://github.com/ScienceIsNeato/course_record_updater/settings/secrets/actions
2. Click "New repository secret"
3. Name: `BREVO_API_KEY`
4. Value: `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`
5. Click "Add secret"

**Note**: GitHub secret is only needed if you deploy via GitHub Actions. Local deploys via `./scripts/deploy.sh` use Google Cloud secrets directly.

### Step 4: Deploy to Dev

```bash
# Deploy with new email configuration
./scripts/deploy.sh dev
```

### Step 5: Test Email Delivery

1. Go to https://dev.loopcloser.io
2. Login as institution admin
3. Send an invitation to a test email address
4. Check the recipient's inbox - should receive real email from loopcloser_demo_admin@loopcloser.io

## Verification Checklist

- [ ] Google Cloud secret `brevo-api-key` exists
- [ ] Cloud Run service account has `secretAccessor` role on secret
- [ ] GitHub secret `BREVO_API_KEY` added (if using CI deploys)
- [ ] Deployed to dev with `./scripts/deploy.sh dev`
- [ ] Tested invitation email delivery
- [ ] Tested reminder email delivery
- [ ] Verified emails arrive in recipient inbox

## Troubleshooting

### Emails Still Not Sending

Check Cloud Run logs:
```bash
gcloud run services logs read loopcloser-dev \
  --region=us-central1 \
  --project=loopcloser \
  --limit=50 | grep -i "email\|brevo"
```

Look for:
- `[Email Factory] Created provider: brevo` ✅ Good
- `BREVO_API_KEY not found` ❌ Secret not mounted
- `401 Unauthorized` ❌ Invalid API key
- `403 Forbidden` ❌ IP restrictions (Brevo might block Cloud Run IPs)

### Brevo IP Restrictions

If Brevo blocks Cloud Run IPs, you have two options:
1. Whitelist Cloud Run IP ranges in Brevo dashboard
2. Use SendGrid or another provider without IP restrictions
