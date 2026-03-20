# LoopCloser Rename Cutover Plan

## Goal

Complete the migration from legacy `course_record_updater` / `course-record-updater` naming to the `LoopCloser` product, `loopcloser` repository slug, and `loopcloser.io` primary domain without breaking deployment, CI/CD, email delivery, or local development workflows.

## Fixed Targets

- Product name: `LoopCloser`
- GitHub repository slug: `loopcloser`
- Primary production domain: `loopcloser.io`

## Working Rules

- Treat display-name changes as cheap and identifier/path changes as migrations.
- Do not do a blanket search-and-replace.
- Rename public identity, runtime/deploy identity, and repo/tooling identity in separate passes.
- Prefer cutover with validation over in-place mutation when external systems are involved.
- Keep low-value internal identifiers stable if renaming them adds risk without product benefit.

## Phase 1: Inventory And Freeze Scope

1. Build and maintain a rename inventory of all old and mixed-state identifiers.
2. Record the exact current values for:
   - GitHub repo slug
   - Artifact Registry image path
   - Cloud Run service names
   - GCP project IDs
   - GCS bucket names
   - Secret Manager secret names
   - Brevo sender/domain identities
   - Neon connection-string consumers
3. Decide which internals stay stable for this cutover.
   - Recommendation: leave Neon database/role names unchanged unless a real operational reason appears.

## Phase 2: External Readiness

1. Verify `loopcloser.io` is the canonical public domain.
2. Verify Brevo sender/domain readiness for `loopcloser.io`.
3. Verify Cloud Run domain mapping or front-door routing plan.
4. Audit GitHub Actions cloud authentication for repo-slug-sensitive OIDC trust.
5. Identify every external resource that will not auto-redirect:
   - image paths
   - Cloud Run service URLs
   - GCS bucket names
   - Secret Manager secret names
   - Codecov/project slug references
   - email sender/domain configuration

Verified current-state finding:

- Checked-in GitHub workflows currently authenticate to GCP with static `GCP_SA_KEY` credentials, not repo-slug-bound OIDC/workload identity.
- Repo rename still requires integration verification, but checked-in deploy auth is not currently blocked on GitHub slug claims.

## Phase 3: Runtime And Deploy Config

1. Update deployment workflows, runtime env templates, and deploy scripts to the canonical LoopCloser identifiers.
2. Cut over app-generated absolute URLs and email sender identity.
3. Normalize local and CI database/env naming where the old name is still operational.
4. Keep changes grouped so CI and deploy validation can happen before the repo rename.

## Phase 4: Repo And Tooling Identity

1. Update repo-local references:
   - badges
   - repository links
   - Codecov slug references
   - package metadata
   - safety/project config
   - docs and runbooks
2. Rename the GitHub repository from `course_record_updater` to `loopcloser` only after runtime/deploy assumptions are already updated.
3. Immediately validate post-rename integrations:
   - Git remotes
   - Actions execution
   - package/image publishing
   - OIDC/cloud auth if the auth architecture changes later
   - branch protections
   - repo-slug-based integrations

## Phase 5: Verification And Cleanup

1. Validate CI on the renamed repo.
2. Validate deploy workflows and service reachability on `loopcloser.io`.
3. Validate invites, password resets, reminders, and other email-generated links.
4. Validate smoke and E2E URL assumptions.
5. Sweep for residual legacy names and classify each as intentional leftover or missed migration.
6. Remove old compatibility references or obsolete infrastructure only after the above passes.

## Order Of Operations

1. Maintain inventory and cutover matrix.
2. Prepare external systems and domain/sender readiness.
3. Update runtime/deploy configuration in the repo.
4. Prepare the post-rename repo-link patch set while leaving current GitHub URLs valid.
5. Rename the GitHub repository.
6. Run post-rename verification.
7. Remove leftovers only after confidence is high.

## High-Risk Areas

- `.github/workflows/build.yml`
- `.github/workflows/deploy.yml`
- `.github/workflows/release.yml`
- `.github/workflows/quality-gate.yml`
- `.envrc.template`
- `scripts/deploy.sh`
- `scripts/seed_remote_db.sh`
- `src/services/email_service.py`
- `src/api/routes/reminders.py`
- `docs/setup/DEPLOYMENT.md`
- `docs/RUNBOOK.md`

## Explicit Non-Goals For The First Pass

- Renaming Neon database internals just for branding.
- Rewriting historical archive material unless it still drives active operations.
- Removing old compatibility references before post-cutover validation.