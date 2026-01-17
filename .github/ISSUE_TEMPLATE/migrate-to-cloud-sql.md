---
title: "Migrate from ephemeral SQLite to Cloud SQL for deployed environments"
labels: ["enhancement", "infrastructure", "deployment"]
---

## Problem

Currently, deployed Cloud Run environments (dev, staging, prod) use **ephemeral SQLite databases** stored in `/tmp/`. This means:

❌ **Database is wiped on every deployment or container restart**  
❌ **All data is lost** (user accounts, courses, assessments, etc.)  
❌ **Requires manual re-seeding** after each deployment using `scripts/seed_remote_db.sh`

This is acceptable for `dev` (demo/testing environment) but **catastrophic for production**.

### What Happened

We initially attempted to use GCS FUSE-mounted SQLite (`/data/loopcloser.db` backed by GCS bucket) for persistence, but discovered it's **extremely slow**:
- Page loads: 20+ seconds
- Audit page: 20.61 seconds
- Root cause: SQLite's random I/O pattern + network latency to GCS

See: PR #[number] - "Fix: Remote database seeding for Cloud Run"

## Proposed Solution

Migrate to **Cloud SQL (PostgreSQL)** for staging and production environments.

### Benefits
✅ Fast performance (dedicated database server)  
✅ True persistence across deployments  
✅ Proper transactions and concurrent access  
✅ Industry standard for Cloud Run  
✅ Automated backups  
✅ Scalable for future growth

### Migration Checklist

**Phase 1: Infrastructure Setup**
- [ ] Create Cloud SQL instance (dev, staging, prod)
- [ ] Configure VPC connector for Cloud Run → Cloud SQL
- [ ] Set up automated backups
- [ ] Configure connection pooling

**Phase 2: Application Changes**
- [ ] Add PostgreSQL dependencies (`psycopg2-binary`)
- [ ] Update database models for PostgreSQL compatibility
  - [ ] Test UUID fields
  - [ ] Test JSON fields
  - [ ] Test date/time handling
- [ ] Create migration script (SQLite → PostgreSQL schema)
- [ ] Update `database_service.py` to support both backends

**Phase 3: Deployment**
- [ ] Keep SQLite for local development (fast, simple)
- [ ] Use PostgreSQL for deployed environments
- [ ] Update deployment scripts
- [ ] Document new setup process

**Phase 4: Data Migration**
- [ ] Create seeding script for PostgreSQL
- [ ] Migrate existing data (if any) from GCS snapshots

### Cost Estimate

| Environment | Instance | Monthly Cost |
|-------------|----------|--------------|
| Dev | db-f1-micro (0.6GB RAM) | ~$7 |
| Staging | db-g1-small (1.7GB RAM) | ~$25 |
| Prod | db-n1-standard-1 (3.75GB RAM) | ~$50 |

**Total**: ~$82/month for all environments

### Alternative Considered

**Firestore/Datastore**: NoSQL alternative, but would require significant application refactoring. Not recommended.

## Current Workaround

For `dev` environment only:
- Using ephemeral `/tmp/` SQLite (fast, but data lost on restart)
- Re-seed using: `./scripts/seed_remote_db.sh dev --demo --clear`
- Acceptable for demos/testing

**⚠️ DO NOT deploy staging/prod with ephemeral database!**

## References

- [Cloud Run + Cloud SQL guide](https://cloud.google.com/sql/docs/postgres/connect-run)
- [SQLite vs PostgreSQL compatibility](https://www.sqlite.org/pgcompat.html)
- GCS FUSE performance issues discussion: [link to PR]
