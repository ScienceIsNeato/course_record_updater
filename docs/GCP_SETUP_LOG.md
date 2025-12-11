# GCP Setup Log - Loopcloser

> **Date:** 2025-12-11  
> **Domain:** loopcloser.io (Cloudflare)  
> **GCP Project:** loopcloser

---

## 1. Prerequisites Completed

- [x] Domain registered: `loopcloser.io` on Cloudflare (2025-12-09)
- [x] gcloud CLI installed and authenticated as `quarkswithforks@gmail.com`
- [x] Docker Desktop installed

---

## 2. GCP Project Setup (Completed)

### Create Project
```bash
gcloud projects create loopcloser --name="Loopcloser"
gcloud config set project loopcloser
```

### Enable Billing
- Linked billing account via: https://console.cloud.google.com/billing/linkedaccount?project=loopcloser

### Enable Required APIs
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  --project=loopcloser
```

### Create Artifact Registry
```bash
gcloud artifacts repositories create loopcloser-images \
  --repository-format=docker \
  --location=us-central1 \
  --description="Docker images for Loopcloser" \
  --project=loopcloser
```

### Create GCS Buckets (for SQLite persistence)
```bash
gsutil mb -l us-central1 -p loopcloser gs://loopcloser-db-dev
gsutil mb -l us-central1 -p loopcloser gs://loopcloser-db-staging
gsutil mb -l us-central1 -p loopcloser gs://loopcloser-db-prod
```

### Configure Docker Authentication
```bash
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
```

---

## 3. Docker Image Build (Completed)

### Build and Tag
```bash
docker build -t loopcloser-app .
docker tag loopcloser-app us-central1-docker.pkg.dev/loopcloser/loopcloser-images/loopcloser-app:latest
```

### Push to Registry
```bash
docker push us-central1-docker.pkg.dev/loopcloser/loopcloser-images/loopcloser-app:latest
```

---

## 4. Cloud Run Deployment (COMPLETED)

### Issues Resolved
1. Missing Python packages in Dockerfile (`api/`, `session/`, `bulk_email_models/`, `email_providers/`)
2. Missing `openpyxl` in requirements.txt
3. Architecture mismatch - needed `--platform linux/amd64` for Cloud Run

### Build Command (for Mac M-series)
```bash
gcloud run deploy loopcloser-dev \
  --image=us-central1-docker.pkg.dev/loopcloser/loopcloser-images/loopcloser-app:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="APP_ENV=development,DATABASE_URL=sqlite:////tmp/loopcloser.db" \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=2 \
  --project=loopcloser
```

---

## 5. DNS Configuration (TODO)

Once Cloud Run is deployed, configure Cloudflare DNS:

| Type | Name | Value | Proxy |
|------|------|-------|-------|
| CNAME | dev | `loopcloser-dev-HASH.run.app` | DNS only |
| CNAME | staging | `loopcloser-staging-HASH.run.app` | DNS only |
| CNAME | @ | `loopcloser-prod-HASH.run.app` | DNS only |

Then create Cloud Run domain mappings:
```bash
gcloud run domain-mappings create --service=loopcloser-dev --domain=dev.loopcloser.io --region=us-central1
```

---

## 6. Resources Created

| Resource | Name/ID | Status |
|----------|---------|--------|
| GCP Project | `loopcloser` (952626409962) | ✅ Active |
| Artifact Registry | `us-central1-docker.pkg.dev/loopcloser/loopcloser-images` | ✅ Created |
| GCS Bucket (Dev) | `gs://loopcloser-db-dev` | ✅ Created |
| GCS Bucket (Staging) | `gs://loopcloser-db-staging` | ✅ Created |
| GCS Bucket (Prod) | `gs://loopcloser-db-prod` | ✅ Created |
| Cloud Run (Dev) | `loopcloser-dev` | ✅ Live |

### Dev Environment URL
**https://loopcloser-dev-952626409962.us-central1.run.app**

---

## 7. Cloudflare Configuration (TODO)

Recommended security settings:
- SSL/TLS: Full (strict)
- Always Use HTTPS: ON
- Bot Fight Mode: ON
- Browser Integrity Check: ON

---

## Cost Estimates

Cloud Run free tier (monthly):
- 2 million requests
- 360,000 vCPU-seconds
- 180,000 GiB-seconds

For a dev environment, likely $0/month.

