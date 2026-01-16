# Deployment Guide

> **Target Domain:** `loopcloser.io`  
> **Platform:** Google Cloud Run  
> **Database:** SQLite with GCS persistence

---

## Table of Contents

1. [Environment Overview](#environment-overview)
2. [Prerequisites](#prerequisites)
3. [Domain Setup](#domain-setup)
4. [GCP Project Setup](#gcp-project-setup)
5. [Deployment Commands](#deployment-commands)
6. [Environment Variables](#environment-variables)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)

---

## Environment Overview

| Environment | URL | Purpose | Deploy Trigger |
|-------------|-----|---------|----------------|
| **Production** | `loopcloser.io` | Live production system | Manual (workflow_dispatch) |
| **Staging** | `staging.loopcloser.io` | Pre-production validation | Manual (workflow_dispatch) |
| **Dev** | `dev.loopcloser.io` | Development testing | Auto on merge to `develop` |

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          loopcloser.io                           │
│                    (Cloudflare DNS / Registrar)                  │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Google Cloud Run                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    Dev      │  │   Staging   │  │ Production  │             │
│  │  Service    │  │   Service   │  │   Service   │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                      │
│         ▼                ▼                ▼                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  GCS Bucket │  │  GCS Bucket │  │  GCS Bucket │             │
│  │  (Dev DB)   │  │ (Staging DB)│  │  (Prod DB)  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Local Development Tools

```bash
# Install Google Cloud CLI
brew install google-cloud-sdk  # macOS
# Or: https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud auth application-default login

# Install Docker (for local builds)
brew install docker  # macOS
```

### Required Access

- [ ] Google Cloud Platform account with billing enabled
- [x] Domain registered: `loopcloser.io` (Cloudflare)
- [ ] GitHub repository admin access (for secrets)

---

## Domain Setup

### 1. Domain Registration (Completed)

**Registrar:** Cloudflare  
**Domain:** `loopcloser.io`  
**Registered:** 2025-12-09

### 2. Configure DNS Records in Cloudflare

After Cloud Run services are deployed, add these DNS records in Cloudflare dashboard:

| Type | Name | Value | Proxy |
|------|------|-------|-------|
| CNAME | @ | `ghs.googlehosted.com.` | DNS only |
| CNAME | www | `ghs.googlehosted.com.` | DNS only |
| CNAME | staging | `ghs.googlehosted.com.` | DNS only |
| CNAME | dev | `ghs.googlehosted.com.` | DNS only |

> **Note:** Use "DNS only" (gray cloud) initially for Cloud Run domain verification. Can enable proxy later for DDoS protection.

### 3. Verify Domain in GCP

```bash
# Add domain mapping in Cloud Run
gcloud run domain-mappings create \
  --service=loopcloser-prod \
  --domain=loopcloser.io \
  --region=us-central1

gcloud run domain-mappings create \
  --service=loopcloser-staging \
  --domain=staging.loopcloser.io \
  --region=us-central1

gcloud run domain-mappings create \
  --service=loopcloser-dev \
  --domain=dev.loopcloser.io \
  --region=us-central1
```

---

## GCP Project Setup

### 1. Create Project

```bash
# Set project name
export PROJECT_ID="loopcloser"
export REGION="us-central1"

# Create project
gcloud projects create $PROJECT_ID --name="Loopcloser"

# Set as active project
gcloud config set project $PROJECT_ID

# Enable billing (required for Cloud Run)
# Do this in GCP Console: https://console.cloud.google.com/billing
```

### 2. Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  cloudresourcemanager.googleapis.com
```

### 3. Create Artifact Registry Repository

```bash
gcloud artifacts repositories create loopcloser-images \
  --repository-format=docker \
  --location=$REGION \
  --description="Docker images for Loopcloser"
```

### 4. Create GCS Buckets for Database Persistence

```bash
# Create buckets for each environment
gsutil mb -l $REGION gs://loopcloser-db-dev
gsutil mb -l $REGION gs://loopcloser-db-staging
gsutil mb -l $REGION gs://loopcloser-db-prod

# Set lifecycle rules (optional - for backup retention)
cat > lifecycle.json << 'EOF'
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {"age": 90, "matchesPrefix": ["backup/"]}
    }
  ]
}
EOF

gsutil lifecycle set lifecycle.json gs://loopcloser-db-prod
rm lifecycle.json
```

### 5. Create Service Account for GitHub Actions

```bash
# Create service account
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Deployer"

# Get service account email
export SA_EMAIL="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant required roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/iam.serviceAccountUser"

# Create and download key (store securely!)
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=$SA_EMAIL

echo "⚠️  IMPORTANT: Add contents of github-actions-key.json to GitHub Secrets as GCP_SA_KEY"
echo "⚠️  Then delete the local key file: rm github-actions-key.json"
```

### 6. Set Up Secret Manager

```bash
# Create secrets for each environment
echo -n "$(openssl rand -base64 32)" | \
  gcloud secrets create flask-secret-key-prod --data-file=-

echo -n "$(openssl rand -base64 32)" | \
  gcloud secrets create flask-secret-key-staging --data-file=-

echo -n "$(openssl rand -base64 32)" | \
  gcloud secrets create flask-secret-key-dev --data-file=-

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding flask-secret-key-prod \
  --member="serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Deployment Commands

### Manual Deployment (via GitHub Actions)

1. Go to **Actions** tab in GitHub
2. Select **Deploy to Cloud Run** workflow
3. Click **Run workflow**
4. Select environment (dev/staging/production)
5. Confirm deployment

### Local Build & Deploy (Emergency)

```bash
# Build image locally
docker build -t loopcloser-app .

# Tag for Artifact Registry
docker tag loopcloser-app \
  ${REGION}-docker.pkg.dev/${PROJECT_ID}/loopcloser-images/loopcloser-app:latest

# Push to registry
docker push \
  ${REGION}-docker.pkg.dev/${PROJECT_ID}/loopcloser-images/loopcloser-app:latest

# Deploy to Cloud Run
gcloud run deploy loopcloser-prod \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/loopcloser-images/loopcloser-app:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="ENV=production,DATABASE_URL=sqlite:////data/loopcloser.db" \
  --add-volume=name=sqlite-data,type=cloud-storage,bucket=loopcloser-db-prod \
  --add-volume-mount=volume=sqlite-data,mount-path=/data
```

---

## Environment Variables

### Required for All Environments

| Variable | Description | Example |
|----------|-------------|---------|
| `ENV` | Environment name | `production`, `staging`, `dev` |
| `DATABASE_URL` | SQLite connection string | `sqlite:////data/loopcloser.db` |
| `SECRET_KEY` | Flask session secret | (from Secret Manager) |
| `BASE_URL` | Application base URL | `https://loopcloser.io` |

### Email Configuration (Production)

| Variable | Description |
|----------|-------------|
| `BREVO_API_KEY` | Brevo API key for transactional emails |
| `BREVO_SENDER_EMAIL` | Verified sender email |
| `BREVO_SENDER_NAME` | Sender display name |

### Email Configuration (Dev/Staging)

| Variable | Description |
|----------|-------------|
| `ETHEREAL_USER` | Ethereal test email user |
| `ETHEREAL_PASS` | Ethereal test email password |

---

## Rollback Procedures

### Quick Rollback (Previous Revision)

```bash
# List revisions
gcloud run revisions list --service=loopcloser-prod --region=$REGION

# Route 100% traffic to previous revision
gcloud run services update-traffic loopcloser-prod \
  --region=$REGION \
  --to-revisions=loopcloser-prod-00002-abc=100
```

### Database Rollback

```bash
# List backups in GCS
gsutil ls gs://loopcloser-db-prod/backup/

# Copy backup to restore location
gsutil cp gs://loopcloser-db-prod/backup/loopcloser-2025-01-15.db \
  gs://loopcloser-db-prod/loopcloser.db
```

### Full Rollback (GitHub Actions)

1. Go to **Actions** > **Deploy to Cloud Run**
2. Find the successful deployment you want to restore
3. Click **Re-run all jobs**

---

## Troubleshooting

### Common Issues

#### 1. "Permission Denied" on GCS Bucket

```bash
# Verify Cloud Run service account has storage access
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.role:roles/storage"
```

#### 2. Database File Not Persisting

- Ensure GCS bucket is mounted correctly
- Check volume mount path matches `DATABASE_URL`
- Verify bucket exists and is accessible

```bash
# Test bucket access
gsutil ls gs://loopcloser-db-prod/
```

#### 3. SSL Certificate Not Provisioning

- DNS records may take up to 24 hours to propagate
- Verify domain ownership in GCP Console
- Check Cloud Run domain mapping status:

```bash
gcloud run domain-mappings describe \
  --domain=loopcloser.io \
  --region=$REGION
```

#### 4. Cold Start Latency

Cloud Run instances scale to zero. For better cold start performance:

```bash
# Set minimum instances (costs money!)
gcloud run services update loopcloser-prod \
  --region=$REGION \
  --min-instances=1
```

### Viewing Logs

```bash
# Stream logs
gcloud run logs read --service=loopcloser-prod --region=$REGION

# View in Cloud Console
# https://console.cloud.google.com/run/detail/$REGION/loopcloser-prod/logs
```

### Health Check

```bash
# Test health endpoint
curl https://loopcloser.io/health
```

---

## Security Checklist

- [ ] GCP project has billing alerts configured
- [ ] Service account keys rotated every 90 days
- [ ] Secret Manager used for all sensitive values
- [ ] Cloud Run services require HTTPS (automatic)
- [ ] Database buckets have versioning enabled
- [ ] IAM roles follow principle of least privilege
- [ ] GitHub repository secrets are configured

---

## Cost Estimation

| Resource | Dev | Staging | Production |
|----------|-----|---------|------------|
| Cloud Run | ~$5/mo | ~$5/mo | ~$20/mo |
| GCS Storage | ~$1/mo | ~$1/mo | ~$5/mo |
| Domain | - | - | ~$12/yr |
| **Total** | ~$6/mo | ~$6/mo | ~$27/mo |

> Costs assume low-to-moderate traffic. Cloud Run bills per request and CPU time.

---

## Related Documentation

- [CI_SETUP_GUIDE.md](CI_SETUP_GUIDE.md) - CI pipeline documentation
- [ENV_SETUP.md](ENV_SETUP.md) - Local environment setup
- [docs/RUNBOOK.md](docs/RUNBOOK.md) - Operations runbook


