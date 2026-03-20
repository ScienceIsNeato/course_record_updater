# LoopCloser Rename Matrix

## Purpose

This matrix captures the concrete identifiers that matter during the rename from the legacy `course_record_updater` repo identity to the canonical `loopcloser` product/repo/domain identity.

Use this document as the cutover worksheet for external systems and repo-owned runtime identifiers.

## Canonical Target

- Product name: `LoopCloser`
- Repo slug: `loopcloser`
- Primary domain: `loopcloser.io`

## Matrix

| Area | Current Value | Target Value | Source Of Truth | Cutover Notes |
| --- | --- | --- | --- | --- |
| GitHub repo slug | `course_record_updater` | `loopcloser` | GitHub repo settings | Rename late, after runtime/deploy config is already updated. |
| GitHub badge URLs | `ScienceIsNeato/course_record_updater` | `ScienceIsNeato/loopcloser` | `README.md` | Low risk, but should be updated immediately after repo rename. |
| GitHub repository links in docs | `https://github.com/ScienceIsNeato/course_record_updater` | `https://github.com/ScienceIsNeato/loopcloser` | `docs/RUNBOOK.md` | Update at the same time as the repo rename so links stay valid. |
| Codecov slug | `codecov.io/gh/ScienceIsNeato/course_record_updater` | `codecov.io/gh/ScienceIsNeato/loopcloser` | `docs/setup/CI_SETUP_GUIDE.md` | Likely requires post-rename integration verification, not just doc edits. |
| Product display name | `LoopCloser` | `LoopCloser` | UI/docs/email | Already aligned. Preserve as canonical. |
| Production domain | `loopcloser.io` | `loopcloser.io` | deploy env + deploy workflow | Already aligned. Must remain source of truth for email links. |
| Dev domain | `dev.loopcloser.io` | `dev.loopcloser.io` | deploy env + deploy workflow | Already aligned. |
| Staging domain | `staging.loopcloser.io` | `staging.loopcloser.io` | deploy env + deploy workflow | Already aligned. |
| GCP project ID | `loopcloser` | `loopcloser` or replacement if required | workflow env + deploy script | Do not change casually. High-risk identifier. |
| Artifact Registry base | `us-central1-docker.pkg.dev/loopcloser/loopcloser-images` | keep or explicitly migrate | build/deploy/release workflows | Image paths do not auto-redirect. Treat as explicit migration if changed. |
| Image name | `loopcloser-app` | keep or explicitly migrate | build/deploy/release workflows | Keep unless there is a real branding reason. |
| Cloud Run dev service | `loopcloser-dev` | keep or replacement service | deploy workflow + env files | Cloud Run service names are not cheap renames. Replacement is safer than mutation. |
| Cloud Run staging service | `loopcloser-staging` | keep or replacement service | deploy workflow + env files | Same rule as above. |
| Cloud Run prod service | `loopcloser-prod` | keep or replacement service | deploy workflow + env files | Same rule as above. |
| GCS bucket dev | `loopcloser-db-dev` | keep or replacement bucket | deploy env docs | Bucket rename is not trivial. Replacement/cutover if changed. |
| GCS bucket staging | `loopcloser-db-staging` | keep or replacement bucket | deploy env docs | Same rule as above. |
| GCS bucket prod | `loopcloser-db-prod` | keep or replacement bucket | deploy env docs | Same rule as above. |
| Brevo sender email | `loopcloser_demo_admin@loopcloser.io` | likely `noreply@loopcloser.io` or another approved sender | deploy workflow + deploy script | Verify domain/sender readiness before changing app output. |
| Brevo sender name dev | `LoopCloser Dev` | `LoopCloser Dev` | deploy workflow + deploy script | Already aligned. |
| Brevo sender name staging | `LoopCloser Staging` | `LoopCloser Staging` | deploy workflow + deploy script | Already aligned. |
| Brevo sender name prod | `LoopCloser` | `LoopCloser` | deploy workflow + deploy script | Already aligned. |
| Email default sender in app | `noreply@loopcloser.io` | approved sender at `loopcloser.io` | `src/services/email_service.py` | Repo-local default already aligned; verify live Brevo sender choice before further changes. |
| Secret: Brevo API key | `brevo-api-key` | keep or versioned replacement | deploy workflow + secret manager | Safe to keep unless secret naming standard changes. |
| Secret: app secret key | `loopcloser-secret-key` | keep or versioned replacement | deploy/release workflow | Already aligned with product. |
| Secret: Neon dev DB | `neon-dev-database-url` | keep | deploy workflow + scripts | Recommendation: leave stable unless Neon change is required. |
| Secret: release deploy arg | `GCP_RUN_SECRETS_ARG` | keep or replace deliberately | release workflow | Operational secret; rename only with a coordinated workflow change. |
| Local dev DB filename | `course_records_dev.db` | `loopcloser_dev.db` | `.envrc.template` | Safe repo-local normalization task. |
| Local E2E DB filename | `course_records_e2e.db` | `loopcloser_e2e.db` | `.envrc.template` | Safe repo-local normalization task. |
| Local smoke DB filename | `course_records_smoke.db` | `loopcloser_smoke.db` | `.envrc.template` | Safe repo-local normalization task. |
| Local prod fallback DB filename | `course_records.db` | `loopcloser.db` | `.envrc.template` | Safe repo-local normalization task. |
| CI DB filenames | various `course_records*` values | `loopcloser*` equivalents | `quality-gate.yml` | Safe once test/script assumptions are updated in the same pass. |
| Local clone dir examples | repo-name-neutral wording | repo-name-neutral wording or `loopcloser` post-rename | README/docs | Already normalized to avoid assuming the old checkout name. |
| GitHub Actions cloud auth mode | static `GCP_SA_KEY` credential | static credential or deliberate OIDC migration | build/deploy/release workflows | Verified not repo-slug-sensitive in checked-in workflows; low rename risk unless auth architecture changes separately. |

## Sequencing Notes

### Change Early

- Planning docs and inventory
- repo-local DB filename defaults
- CI/test naming tied only to local files
- docs that explain the future canonical state

### Change Only After External Readiness

- app email sender address
- any `BASE_URL`-driven user-facing link identity
- anything that depends on Brevo sender/domain verification

### Change Late

- GitHub repo slug
- repo URL, badge, and Codecov slug updates that depend on the real rename
- badge URLs and clone examples that depend on the actual rename having happened

### Avoid Changing Without A Separate Decision

- GCP project ID
- Artifact Registry path
- Cloud Run service names
- GCS bucket names
- Neon internal database naming

## Immediate Tasks Derived From This Matrix

1. Prepare a post-repo-rename patch set for badge URLs, repository links, and Codecov slug references.
2. Verify external integrations outside the repo for any repo-slug assumptions that are not visible in checked-in workflows.
3. Keep GitHub cloud auth under observation only if the team later replaces static credentials with OIDC/workload identity.