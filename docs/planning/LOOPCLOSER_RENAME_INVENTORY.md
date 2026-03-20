# LoopCloser Rename Inventory

## Status Summary

The repository is already in mixed state.

- Public/product branding is mostly `LoopCloser`.
- The GitHub repo slug and many docs still use `course_record_updater`.
- Local and CI database defaults still use `course_records*` names.
- Deployment and hosted identity are already mostly `loopcloser`.

This means the rename must be treated as a staged migration, not a text-only cleanup.

## Canonical Targets

- Product name: `LoopCloser`
- Repo slug: `loopcloser`
- Primary domain: `loopcloser.io`

## Inventory By Area

### 1. Repo Slug And Tooling Identity

These still point at the old repository slug and will need to move when the repo is renamed.

- `README.md`
  - GitHub badge URLs still use `ScienceIsNeato/course_record_updater`
  - clone instructions still say `cd course_record_updater`
- `docs/setup/CI_SETUP_GUIDE.md`
- `docs/RUNBOOK.md`
- `config/.safety-project.ini`
- `.safety-project.ini`

### 2. Public Branding Already On LoopCloser

These are already aligned with the new product identity and should be preserved as the canonical naming.

- `README.md`
- `package.json`
- `templates/index.html`
- `templates/components/app_header.html`
- `src/services/email_service.py`
- `src/api/routes/health.py`
- LoopCloser static images and branding assets

### 3. Local And CI Database Naming Still Legacy

These are operational, not cosmetic, and need a controlled pass.

- `.envrc.template`
  - `sqlite:///course_records_dev.db`
  - `sqlite:///course_records_e2e.db`
  - `sqlite:///course_records_smoke.db`
  - production fallback `sqlite:///course_records.db`
- `.github/workflows/quality-gate.yml`
  - legacy database filenames in CI setup
- `src/database/database_sql.py`
- `scripts/seed_db.py`
- `scripts/restart_server.sh`
- `scripts/run_uat.sh`
- `scripts/run_smoke.sh`
- `tests/e2e/conftest.py`

### 4. Deployment And Hosted Identity Already LoopCloser

These are current operational identifiers and must be treated as the external source of truth during cutover planning.

- `.github/workflows/build.yml`
  - `PROJECT_ID=loopcloser`
  - `REGISTRY=us-central1-docker.pkg.dev/loopcloser/loopcloser-images`
  - `IMAGE_NAME=loopcloser-app`
- `.github/workflows/deploy.yml`
  - Cloud Run services: `loopcloser-dev`, `loopcloser-staging`, `loopcloser-prod`
  - domains: `dev.loopcloser.io`, `staging.loopcloser.io`, `loopcloser.io`
  - sender identity: `loopcloser_demo_admin@loopcloser.io`
- `.github/workflows/release.yml`
- `deploy/environments/dev.env`
- `deploy/environments/staging.env`
- `deploy/environments/prod.env`
- `scripts/deploy.sh`
- `scripts/seed_remote_db.sh`

### 5. Email And Absolute URL Identity

These produce user-facing links and should be cut over carefully.

- `src/services/email_service.py`
  - branding name already `LoopCloser`
  - default sender email still `noreply@courserecord.app`
- `src/api/routes/reminders.py`
- any `BASE_URL` usage in deploy/runtime config

### 6. External Systems Tied To The Rename

These must be tracked explicitly because they may not auto-redirect or may fail silently.

- GitHub repository slug and any slug-dependent integrations
- GitHub Actions cloud auth / OIDC trust conditions
- Google Cloud Run service names and service URLs
- Artifact Registry image paths
- GCS buckets
- Secret Manager secret names
- Brevo sender/domain configuration
- Neon connection-string consumers
- Codecov/project slug style tooling
- Ethereal/Mailtrap docs and auxiliary test setup

## Risk Notes

### High Risk

- Cloud auth tied to old repo slug via OIDC or policy conditions
- image paths and deploy scripts that do not redirect
- app-generated email links if `BASE_URL` changes before domain readiness
- secret names or secret consumers changing out of sync

### Medium Risk

- local/CI DB file renames breaking tests and scripts
- stale docs causing operator mistakes during cutover
- mixed sender/domain branding in email flows

### Low Risk

- README prose
- package metadata display strings
- historical archive cleanup

## Immediate Implementation Targets

These are the safest first implementation steps.

1. Keep this inventory updated as the cutover source of truth.
2. Create an external-system cutover matrix from the deployment and workflow files.
3. Start a repo-local normalization pass for legacy DB names and old repo slug references only after the matrix is complete.

## Deferred Until External Readiness Is Confirmed

1. GitHub repository rename
2. Any Cloud Run service-name replacement
3. Any bucket or secret-name migration
4. Any sender/domain cutover that affects live email links