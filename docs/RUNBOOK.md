# Operations Runbook

> Operational procedures for Loopcloser (`loopcloser.io`)

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Daily Operations](#daily-operations)
3. [Database Operations](#database-operations)
4. [Deployment Operations](#deployment-operations)
5. [Incident Response](#incident-response)
6. [Monitoring & Alerts](#monitoring--alerts)

---

## Quick Reference

### Service URLs

| Environment | URL                           | GCP Console                                                                           |
| ----------- | ----------------------------- | ------------------------------------------------------------------------------------- |
| Production  | https://loopcloser.io         | [Console](https://console.cloud.google.com/run/detail/us-central1/loopcloser-prod)    |
| Staging     | https://staging.loopcloser.io | [Console](https://console.cloud.google.com/run/detail/us-central1/loopcloser-staging) |
| Dev         | https://dev.loopcloser.io     | [Console](https://console.cloud.google.com/run/detail/us-central1/loopcloser-dev)     |

### Key Contacts

| Role                  | Contact       |
| --------------------- | ------------- |
| Primary Developer     | (Add contact) |
| Pilot Partner Contact | (Add contact) |
| GCP Admin             | (Add contact) |

### Important Links

- [GitHub Repository](https://github.com/ScienceIsNeato/course_record_updater)
- [Cloud Run Console](https://console.cloud.google.com/run)
- [Cloud Monitoring](https://console.cloud.google.com/monitoring)
- [Error Reporting](https://console.cloud.google.com/errors)

---

## Daily Operations

### Health Check

```bash
# Quick health check for all environments
curl -s https://loopcloser.io/health | jq .
curl -s https://staging.loopcloser.io/health | jq .
curl -s https://dev.loopcloser.io/health | jq .
```

Expected response:

```json
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0"
}
```

### View Recent Logs

```bash
# Production logs (last 1 hour)
gcloud run logs read --service=loopcloser-prod --region=us-central1 --limit=100

# Filter for errors only
gcloud run logs read --service=loopcloser-prod --region=us-central1 \
  --log-filter="severity>=ERROR" --limit=50

# Stream logs in real-time
gcloud run logs tail --service=loopcloser-prod --region=us-central1
```

### Check Service Status

```bash
# Get service details
gcloud run services describe loopcloser-prod --region=us-central1

# List all revisions
gcloud run revisions list --service=loopcloser-prod --region=us-central1

# Check current traffic split
gcloud run services describe loopcloser-prod --region=us-central1 \
  --format="value(status.traffic)"
```

---

## Database Operations

### Backup Database

```bash
# Manual backup to GCS
BACKUP_NAME="loopcloser-$(date +%Y%m%d-%H%M%S).db"
gsutil cp gs://loopcloser-db-prod/loopcloser.db gs://loopcloser-db-prod/backup/$BACKUP_NAME
echo "Backup created: gs://loopcloser-db-prod/backup/$BACKUP_NAME"
```

### List Backups

```bash
gsutil ls -l gs://loopcloser-db-prod/backup/
```

### Restore Database

```bash
# 1. Stop accepting traffic (optional but recommended)
gcloud run services update-traffic loopcloser-prod \
  --region=us-central1 --to-revisions=loopcloser-prod-00001-abc=0

# 2. Backup current database
gsutil cp gs://loopcloser-db-prod/loopcloser.db \
  gs://loopcloser-db-prod/backup/pre-restore-$(date +%Y%m%d-%H%M%S).db

# 3. Restore from backup
gsutil cp gs://loopcloser-db-prod/backup/loopcloser-20250115-120000.db \
  gs://loopcloser-db-prod/loopcloser.db

# 4. Restart service to pick up restored database
gcloud run services update loopcloser-prod --region=us-central1 --no-traffic

# 5. Resume traffic
gcloud run services update-traffic loopcloser-prod \
  --region=us-central1 --to-latest
```

### Database Maintenance

```bash
# Check database size
gsutil du -s gs://loopcloser-db-prod/loopcloser.db

# Download database for local inspection
gsutil cp gs://loopcloser-db-prod/loopcloser.db /tmp/loopcloser-prod.db
sqlite3 /tmp/loopcloser-prod.db ".schema"
sqlite3 /tmp/loopcloser-prod.db "SELECT COUNT(*) FROM users;"
```

### Reset Demo/Test Data (Non-Production Only)

```bash
# For staging/dev environments only!
# This replaces the database with fresh seeded data

# 1. Build and push image with seed script
docker build -t loopcloser-seeder -f Dockerfile.seed .

# 2. Run seeder job
gcloud run jobs execute loopcloser-seed-staging --region=us-central1
```

---

## Deployment Operations

### Standard Deployment

1. Go to GitHub Actions
2. Select "Deploy to Cloud Run" workflow
3. Choose environment
4. Click "Run workflow"

### Emergency Deployment (CLI)

```bash
# Deploy specific commit
git checkout <commit-sha>

# Build and tag
docker build -t loopcloser-emergency .
docker tag loopcloser-emergency us-central1-docker.pkg.dev/loopcloser/loopcloser-images/loopcloser-app:emergency

# Push
docker push us-central1-docker.pkg.dev/loopcloser/loopcloser-images/loopcloser-app:emergency

# Deploy
gcloud run deploy loopcloser-prod \
  --image=us-central1-docker.pkg.dev/loopcloser/loopcloser-images/loopcloser-app:emergency \
  --region=us-central1
```

### Rollback

```bash
# List revisions
gcloud run revisions list --service=loopcloser-prod --region=us-central1

# Rollback to specific revision
gcloud run services update-traffic loopcloser-prod \
  --region=us-central1 \
  --to-revisions=loopcloser-prod-00005-xyz=100
```

### Blue-Green Deployment

```bash
# Deploy new revision without traffic
gcloud run deploy loopcloser-prod \
  --image=<new-image> \
  --region=us-central1 \
  --no-traffic

# Send 10% traffic to new revision
gcloud run services update-traffic loopcloser-prod \
  --region=us-central1 \
  --to-revisions=loopcloser-prod-00006-new=10,loopcloser-prod-00005-old=90

# Monitor for issues, then shift 100%
gcloud run services update-traffic loopcloser-prod \
  --region=us-central1 \
  --to-latest
```

---

## Incident Response

### Severity Levels

| Level | Description                      | Response Time     |
| ----- | -------------------------------- | ----------------- |
| SEV-1 | Service down, all users affected | Immediate         |
| SEV-2 | Major feature broken             | Within 1 hour     |
| SEV-3 | Minor issue, workaround exists   | Within 24 hours   |
| SEV-4 | Cosmetic/low impact              | Next business day |

### SEV-1: Service Down

```bash
# 1. Check service status
gcloud run services describe loopcloser-prod --region=us-central1

# 2. Check logs for errors
gcloud run logs read --service=loopcloser-prod --region=us-central1 \
  --log-filter="severity>=ERROR" --limit=50

# 3. Check if recent deployment caused issue
gcloud run revisions list --service=loopcloser-prod --region=us-central1

# 4. If recent deployment, rollback immediately
gcloud run services update-traffic loopcloser-prod \
  --region=us-central1 \
  --to-revisions=<previous-revision>=100

# 5. Notify stakeholders
# (Add notification procedure)

# 6. Create incident report after resolution
```

### SEV-2: Database Issues

```bash
# 1. Check GCS bucket accessibility
gsutil ls gs://loopcloser-db-prod/

# 2. Check database file exists and has content
gsutil stat gs://loopcloser-db-prod/loopcloser.db

# 3. Download and check database integrity
gsutil cp gs://loopcloser-db-prod/loopcloser.db /tmp/check.db
sqlite3 /tmp/check.db "PRAGMA integrity_check;"

# 4. If corrupted, restore from backup
gsutil cp gs://loopcloser-db-prod/backup/<latest-backup>.db \
  gs://loopcloser-db-prod/loopcloser.db
```

### SEV-2: Email Delivery Issues

```bash
# 1. Check Brevo API status
curl -s https://status.brevo.com/api/v2/summary.json | jq .

# 2. Check application logs for email errors
gcloud run logs read --service=loopcloser-prod --region=us-central1 \
  --log-filter="textPayload:email OR textPayload:Email" --limit=50

# 3. Verify Brevo credentials
# (Check Secret Manager values are correct)

# 4. Test email sending manually
# (Use admin interface or direct API test)
```

### Post-Incident

1. Create incident report in GitHub Issues
2. Identify root cause
3. Implement preventive measures
4. Update runbook if needed

---

## Monitoring & Alerts

### Cloud Monitoring Dashboard

Access: [Cloud Monitoring Console](https://console.cloud.google.com/monitoring)

Key metrics to watch:

- Request count
- Latency (p50, p95, p99)
- Error rate
- Instance count
- Memory utilization
- CPU utilization

### Setting Up Alerts

```bash
# Create alert for high error rate
gcloud alpha monitoring policies create \
  --display-name="Loopcloser High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-filter='resource.type="cloud_run_revision" AND resource.labels.service_name="loopcloser-prod" AND metric.type="run.googleapis.com/request_count" AND metric.labels.response_code_class="5xx"' \
  --condition-threshold-value=5 \
  --condition-threshold-comparison=COMPARISON_GT \
  --notification-channels=<channel-id>
```

### Uptime Monitoring

Set up uptime checks in Cloud Monitoring:

1. Go to Cloud Monitoring > Uptime Checks
2. Create check for `https://loopcloser.io/health`
3. Set check frequency: 1 minute
4. Configure alerting policy

### Log-Based Metrics

Create custom metrics for business events:

```bash
# Count of user logins
gcloud logging metrics create user_logins \
  --description="Count of user login events" \
  --log-filter='resource.type="cloud_run_revision" textPayload:"User logged in"'

# Count of assessment submissions
gcloud logging metrics create assessment_submissions \
  --description="Count of assessment submissions" \
  --log-filter='resource.type="cloud_run_revision" textPayload:"Assessment submitted"'
```

---

## Scheduled Tasks

### Daily

- [ ] Review error logs
- [ ] Check service health
- [ ] Verify backup completed

### Weekly

- [ ] Review metrics dashboard
- [ ] Check GCS storage usage
- [ ] Review security alerts

### Monthly

- [ ] Rotate service account keys
- [ ] Review and prune old revisions
- [ ] Update dependencies (security patches)
- [ ] Review costs

---

## Appendix: Useful Commands

### GCP Authentication

```bash
# Login to GCP
gcloud auth login

# Set project
gcloud config set project loopcloser

# View current config
gcloud config list
```

### Docker Commands

```bash
# Build image
docker build -t loopcloser-app .

# Run locally
docker run -p 8080:8080 -e ENV=development loopcloser-app

# Push to registry
docker push us-central1-docker.pkg.dev/loopcloser/loopcloser-images/loopcloser-app:latest
```

### SQLite Commands

```bash
# Connect to downloaded database
sqlite3 /tmp/loopcloser.db

# Common queries
.tables
.schema users
SELECT COUNT(*) FROM users;
SELECT * FROM users LIMIT 5;
```
