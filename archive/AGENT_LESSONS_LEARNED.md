# Agent Lessons Learned (Regenerated – September 2025)

This log captures practical guidance for automation agents working inside the LoopCloser codebase. Lessons below synthesize the latest architecture decisions, planning artifacts, and implementation gaps surfaced during the post-auth planning pass.

## 1. Quality Gates & Validation Workflow

- **Default mindset**: treat `python scripts/ship_it.py` without flags as the fast commit path (security & sonar skipped) and reserve `--validation-type PR` for full coverage before merges.
- **Targeted checks**: only pass `--checks …` when chasing a narrow failure; otherwise rely on the curated validation types to keep CI-time predictable.
- **Fail-fast awareness**: the script aborts on first failure, so reruns should begin with the earliest failing stage.
- **Documentation sync**: any future changes to validation behavior must be echoed in `README.md`, `QUALITY_GATE_SUMMARY.md`, and `CI_SETUP_GUIDE.md` to preserve onboarding clarity.

## 2. Tenant Context Integrity Comes First

- **Story 5.6 blockers**: `auth_service.py:334` and `auth_service.py:352` still return mock institution/program scopes. Treat these as critical debt before enabling customer-facing invites or billing logic.
- **API exposure**: endpoints like `/api/users` and `/api/auth/invite` assume correct `institution_id` context; running them with stubs risks cross-tenant leakage.
- **Execution pattern**: always pair data-fetching work with scoped Firestore queries plus regression tests that verify isolation (see incomplete checklist in `planning/AUTH_SYSTEM_DESIGN.md:744`).
- **Doc alignment**: when closing the Story 5.6 checklist, update both the design doc and `STATUS.md` so stakeholders know context enforcement is real.

## 3. Email System Launch Checklist

- **Stakeholder onboarding first**: schedule the 60-minute Email Systems Q&A before coding (cost model, deliverability risks, KISS paths). Capture notes alongside the epic in `NEXT_BACKLOG.md`.
- **Template hygiene**: centralize HTML/text templates (preferably Jinja) to keep branding tweaks cheap; log approvals per `planning/INSTRUCTOR_MANAGEMENT_TIMELINE.md` expectations.
- **Protected domains**: respect `EmailService.PROTECTED_DOMAINS` in non-prod and document safe testing channels (MailHog, console output) for UAT.
- **Admin affordances**: UI work in `templates/admin/user_management.html` should expose resend/preview states so operators can trace sends without diving into logs.
- **Telemetry**: add structured logging / metrics around each send path (invite, verification, reset, welcome) so failures surface in monitoring.

## 4. Building Backlog & Hand-off Artifacts

- **Source everything**: when creating planning docs (e.g., `NEXT_BACKLOG.md`), cite line-level references to `planning/`, `STATUS.md`, and service modules so future agents know where assumptions came from.
- **Highlight hand-offs**: label work that suits autonomous agents versus core dev ownership; it speeds parallelization and clarifies escalation paths.
- **Order by dependency**: sequence backlog items so tenant-safety work (Priority 0) precedes features (email, billing) that rely on it.
- **Documentation trail**: after generating plans, prompt humans to confirm priorities or request deeper breakdowns; backlog artifacts are living documents.

## 5. Tackling TODOs & Dead Buttons

- **Catalog quickly**: use repo-wide scans (`python` walk or `rg`) to locate `TODO` markers; many map directly to open stories (profile save, import validate-only, dashboard buttons).
- **Verify UI hooks**: buttons like `showInstitutions()` or “Coming soon!” alerts in dashboard templates should either be wired up or hidden—note the state in `UAT_GUIDE.md` so manual testers aren’t surprised.
- **Track resolution**: once TODOs are cleared, remove them and update associated docs/tests to prevent regressions.

## 6. Excel Import Refresh Guidance

- **Validate-only mode**: implement the TODO at `import_cli.py:269` so admins can preflight files without touching Firestore; expose it via the API for UI reuse.
- **Section ingestion bug**: investigate the “0 sections created” warning in `STATUS.md`—likely tied to program context; ensure fixes include regression tests.
- **Tenant safety**: import routines must respect the same institution/program filters as the auth layer; do not create users/courses outside scoped IDs.
- **Guide updates**: sync changes with `IMPORT_SYSTEM_GUIDE.md` and note new flags or behaviors in CLI help text.

## 7. Billing Foundations Cautions

- **Model alignment**: reuse `User.calculate_active_status` and Firestore billing scaffolding in `database_service.py:260` when designing the billing service.
- **Permission matrix**: cross-check new billing routes with `planning/documentation/PERMISSION_MATRIX.md` so roles have the expected capabilities.
- **UI expectations**: institution admins need visibility into usage, invoices, and plan management; plan for exports (CSV/JSON) to support finance workflows.
- **Staged rollout**: document integration touchpoints (e.g., future Stripe hooks) early to avoid surprises during implementation.

---

These lessons should be revisited whenever major architectural changes land, new stakeholder requirements surface, or significant TODO clusters are resolved. Agents should append or revise sections as they learn more rather than duplicating entire documents.
