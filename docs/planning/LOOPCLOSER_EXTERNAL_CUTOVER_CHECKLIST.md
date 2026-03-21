# LoopCloser External Cutover Checklist

## Purpose

This checklist covers the systems outside normal source edits that matter for the rename to `loopcloser` and `loopcloser.io`.

Use this on rename day and during preflight. It is intentionally operational, not aspirational.

## Critical Reality Check

Current deployment documentation and current automation do not describe the same runtime model.

- `docs/setup/DEPLOYMENT.md` and `docs/GCP_SETUP_LOG.md` describe GCS-backed SQLite persistence.
- `.github/workflows/deploy.yml` and `scripts/deploy.sh` currently deploy:
  - dev: Neon database via secret
  - staging: ephemeral `/tmp/loopcloser.db`
  - prod: ephemeral `/tmp/loopcloser.db`

Do not execute rename-day infrastructure changes until the desired runtime model is explicitly chosen.

## External Systems

### 1. GitHub Repository

Current:
- repo slug: `course_record_updater`

Target:
- repo slug: `loopcloser`

Preflight:
- confirm no active PRs or branch-protection assumptions depend on the old slug
- confirm cloud auth is not pinned to old repo-slug OIDC conditions
- confirm any repo-linked package publishing or badges can be updated immediately after rename

Verified from checked-in repo state:
- remaining checked-in repo-slug references are concentrated in `README.md`, `docs/RUNBOOK.md`, and `docs/setup/CI_SETUP_GUIDE.md`
- these references are links/badges, not runtime config

Rename-day actions:
- rename repository in GitHub settings
- update local git remotes
- verify Actions still run
- verify branch protections and required checks still reference the right workflows

Post-cutover verification:
- `git remote -v`
- `gh repo view`
- run one no-op or doc-only CI validation if needed

### 2. GitHub Actions Secrets And Cloud Auth

Current identifiers in use:
- `GCP_SA_KEY`
- `SAFETY_API_KEY`
- `ETHEREAL_USER`
- `ETHEREAL_PASS`
- `GCP_RUN_SECRETS_ARG`

Current externally referenced secret names in GCP/workflows:
- `brevo-api-key`
- `loopcloser-secret-key`
- `neon-dev-database-url`

Preflight:
- inspect any OIDC or policy conditions that include `ScienceIsNeato/course_record_updater`
- confirm whether auth is static key only or partially repo-slug-sensitive
- verify `GCP_RUN_SECRETS_ARG` contents match the intended production secret mapping

Verified from checked-in workflows:
- `.github/workflows/build.yml`, `.github/workflows/deploy.yml`, and `.github/workflows/release.yml` authenticate with static `GCP_SA_KEY` credentials
- no checked-in workflow currently uses repo-slug-bound OIDC/workload-identity claims for GCP auth

Rename-day actions:
- update any repo-slug-based auth policies if they exist
- keep secret values stable unless there is an explicit secret migration

Post-cutover verification:
- build workflow auth succeeds
- deploy workflow auth succeeds
- release workflow auth succeeds

### 3. Google Cloud Run

Current services:
- `loopcloser-dev`
- `loopcloser-staging`
- `loopcloser-prod`

Current domains:
- `dev.loopcloser.io`
- `staging.loopcloser.io`
- `loopcloser.io`

Preflight:
- decide whether service names remain as-is or whether new replacement services will be created
- confirm which runtime model is canonical
- confirm current domain mappings and certificates are healthy

Rename-day actions:
- none required if service names remain unchanged
- if renaming services, create new services and cut traffic deliberately rather than attempting in-place mutation

Post-cutover verification:
- `gcloud run services list --region=us-central1 --project=loopcloser`
- verify HTTP 200 on dev, staging, and prod URLs

### 4. Artifact Registry

Current:
- project: `loopcloser`
- registry: `us-central1-docker.pkg.dev/loopcloser/loopcloser-images`
- image: `loopcloser-app`

Preflight:
- decide whether image path stays stable
- confirm workflows and scripts all point to the same image path

Recommendation:
- keep the registry path stable for this rename unless there is a compelling reason to move it

Post-cutover verification:
- build workflow pushes successfully
- deploy and release workflows can still pull expected tags

### 5. Storage Buckets

Current buckets:
- `loopcloser-db-dev`
- `loopcloser-db-staging`
- `loopcloser-db-prod`

Preflight:
- decide whether these stay stable
- if runtime model is no longer GCS-backed SQLite, document that clearly and avoid misleading operators

Recommendation:
- do not rename buckets as part of the repo/domain rename unless the storage model actually depends on them

### 6. Neon

Current external identifier in workflows/scripts:
- `neon-dev-database-url`

Preflight:
- inventory every place `DATABASE_URL` is sourced from Neon
- confirm whether staging/prod should stay ephemeral SQLite or move to Neon/persistent storage

Recommendation:
- leave Neon internal naming stable during this rename
- only change connection-string consumers if the runtime architecture is changing for a separate reason

### 7. Brevo

Current sender configuration in deploy automation:
- sender email: `loopcloser_demo_admin@loopcloser.io`
- sender names: `LoopCloser Dev`, `LoopCloser Staging`, `LoopCloser`

Current app default sender:
- `noreply@loopcloser.io`

Preflight:
- verify `loopcloser.io` is authenticated in Brevo
- verify the exact production sender address to use
- verify templates and automation are not still using old sender/domain values

Rename-day actions:
- none if Brevo is already aligned and verified
- if changing sender identity further, do it only after domain verification is green

Post-cutover verification:
- send a real test email from dev/staging path
- confirm From and links are correct

### 8. Codecov / Repo-Slug Integrations

Current docs still reference the old repo slug in badges and links.

Known checked-in references:
- `docs/setup/CI_SETUP_GUIDE.md`
- badge section examples that mirror `README.md`

Preflight:
- verify whether Codecov project slug must be manually updated after repo rename

Rename-day actions:
- update links and any repo-slug-specific integration settings

### 9. Ethereal / Mailtrap / Manual Email Tooling

Current role:
- Ethereal is active for automated email verification paths
- Mailtrap and Gmail tooling appear secondary/manual

Recommendation:
- treat these as follow-up cleanup items unless a concrete rename dependency appears

## Rename-Day Sequence

1. Confirm canonical runtime model.
2. Confirm `loopcloser.io` domain readiness and sender readiness.
3. Confirm GitHub cloud auth assumptions are repo-rename safe.
4. Land repo-local rename changes first.
5. Rename the GitHub repository.
6. Update repo-slug-linked docs, badges, remotes, and integrations:
  - `README.md`
  - `docs/RUNBOOK.md`
  - `docs/setup/CI_SETUP_GUIDE.md`
7. Run CI.
8. Verify deploy workflows and email flows.

## Hard Stop Conditions

Stop the rename if any of the following are unresolved:

- runtime architecture is still ambiguous between GCS-backed SQLite and Neon/ephemeral SQLite
- cloud auth is repo-slug sensitive and has not been updated
- Brevo sender/domain verification is not confirmed
- release/deploy secret mapping is not understood and verified

## Post-Cutover Checks

- GitHub repo reachable at new slug
- CI green on renamed repo
- build, deploy, and release workflows authenticate successfully
- dev, staging, and prod URLs return healthy responses
- email invite/reset/reminder links point to `loopcloser.io`
- operator docs no longer send people to the old repo slug