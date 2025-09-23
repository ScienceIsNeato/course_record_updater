# Course Record Updater – Post-Auth Backlog

## JavaScript Testing Implementation (Epic) **PLANNED**
**Status**: Planning complete, awaiting SonarCloud resolution  
**Docs**: `planning/JAVASCRIPT_TESTING_PLAN.md`  
**Goal**: Establish enterprise-grade JavaScript testing coverage to match backend standards (80% coverage target).
**Why Important**: Currently 0% JS test coverage across 1,553 lines of frontend code. Users interact with untested JavaScript as much as tested backend code.
**Key Tasks**:
- [ ] **Phase 1**: Set up Jest + jsdom testing infrastructure with CI integration
- [ ] **Phase 2**: Test critical authentication and validation logic (auth.js - 287 lines)
- [ ] **Phase 3**: Test admin interface and dashboard components (admin.js - 414 lines)  
- [ ] **Phase 4**: Complete coverage of remaining UI components and utilities
- [ ] **Integration**: Update SonarCloud to track JavaScript coverage alongside Python metrics
**Definition of Done**: 80% JavaScript line coverage achieved, all critical user paths tested, CI pipeline includes JS testing, sustainable testing patterns established.  
**Timeline**: 4-week implementation once SonarCloud security issues are resolved.
**Hand-off**: Well-documented plan ready for systematic implementation.

## Priority 0 – Multi-Tenant Context Hardening (Story 5.6)
**Status**: Not started  
**Docs**: `planning/AUTH_SYSTEM_DESIGN.md:744`, `auth_service.py:334`, `auth_service.py:352`, `api_routes.py:443`  
**Goal**: Eliminate mock institution/program context so role-based auth uses actual tenant scopes before we expose invites and emails to customers.
**Why Now**: Email flows, dashboard filtering, and billing accuracy rely on correct context; current TODO stubs create cross-tenant data risks.
**Key Tasks**:
- [ ] Replace stubbed data in `auth_service.py:334` and `auth_service.py:352` with Firestore-backed queries that honor each user's scoped institutions/programs.
- [ ] Apply institution/program filters across list endpoints (e.g., `api_routes.py:443`, `api_routes.py:499`, `api_routes.py:555`) to satisfy Story 5.6 acceptance criteria.
- [ ] Implement context middleware fallbacks and default program handling per the design plan, ensuring consistent behavior for program switching.
- [ ] Expand unit/integration coverage for context switching and access control, closing unchecked boxes in Story 5.6.
**Definition of Done**: DB-backed context retrieval, scoped queries everywhere, regression tests in place, Story 5.6 checklist fully checked off.  
**Hand-off**: Requires DB coordination—best handled by primary dev for now.

## Priority 1 – Email Communication System Launch (Epic)
**Status**: In progress  
**Docs**: `planning/INSTRUCTOR_MANAGEMENT_TIMELINE.md:88`, `planning/AUTH_SYSTEM_DESIGN.md:215`, `email_service.py`, `invitation_service.py`, `templates/admin/user_management.html`  
**Goal**: Deliver production-ready outbound email workflows (invites, verification, reset, welcome) aligned with CEI roadmap.
**Key Tasks**:
- [ ] Schedule and document a 60-minute Email Systems Q&A with the product owner to cover architecture, delivery mechanics, cost model, deliverability pitfalls, security considerations, and low-complexity/KISS options before implementation begins.
- [ ] Audit existing templates in `email_service.py` against design expectations; migrate to reusable Jinja templates if that improves maintainability.
- [ ] Add configurable sender profiles and domain safeguards via `EmailService.configure_app`, documenting deployment steps in `README.md` and `QUALITY_GATE_SUMMARY.md`.
- [ ] Pull inviter display names/program context into emails (currently defaulting to raw email in `invitation_service.py`).
- [ ] Provide admin tooling for previewing recent emails or integrate previews into `templates/admin/user_management.html` alongside resend controls.
- [ ] Document SMTP credential management, protected domain handling, and rollout checklist.
**Definition of Done**: All outbound flows send approved templates through a configurable channel, admin UX surfaces resend/preview, deployment runbook updated.  
**Hand-off**: Implementation work is well-scoped once template strategy is confirmed—background agent ready.

## Priority 2 – Email Template Validation & Stakeholder Sign-off (Story) **Hand-off Candidate**
**Status**: Not started  
**Docs**: `planning/INSTRUCTOR_MANAGEMENT_TIMELINE.md:88`, `email_service.py`  
**Goal**: Verify copy, branding, and layout with CEI stakeholders before enabling live emails.
**Key Tasks**:
- [ ] Render HTML/text versions of each template and capture screenshots/PDF artifacts for review.
- [ ] Facilitate review with CEI stakeholders (Leslie, program admins) and iterate on copy/branding feedback.
- [ ] Archive approved templates and note sign-off in STATUS or planning docs.
**Definition of Done**: Stakeholder approval recorded; final templates (and visuals) attached to planning docs.  
**Hand-off**: Perfect for a background agent to coordinate and document.

## Priority 3 – Email UAT & Monitoring Readiness (Story) **Hand-off Candidate**
**Status**: Not started  
**Docs**: `TESTING_STRATEGY.md`, `UAT_GUIDE.md`, `email_service.py`, `invitation_service.py`  
**Goal**: Extend manual test coverage to include email workflows with observable send outcomes.
**Key Tasks**:
- [ ] Add invite, verification, password reset, and welcome email scenarios to `UAT_GUIDE.md` with expected console/log output.
- [ ] Configure a dev/test email sink (file transport/MailHog) and document verification steps.
- [ ] Add structured logging or metrics around email send success/failure for monitoring.
- [ ] Execute UAT pass and summarize results in `STATUS.md`.
**Definition of Done**: Updated UAT guide, observable email send telemetry, documented UAT execution.  
**Hand-off**: Great background agent effort.

## Priority 4 – Excel Import Validation Refresh (Epic)
**Status**: Needs scoping  
**Docs**: `planning/INSTRUCTOR_MANAGEMENT_TIMELINE.md:16`, `IMPORT_SYSTEM_GUIDE.md`, `import_service.py`, `import_cli.py:269`, `STATUS.md`  
**Goal**: Align import tooling with the new auth/multi-tenant model and close outstanding validation TODOs.
**Key Tasks**:
- [ ] Implement the `--validate-only` pathway in `import_cli.py:269` and expose it via API for UI preflight checks.
- [ ] Ensure imports honor institution/program context (tie-in with Priority 0) and restrict user/course creation appropriately.
- [ ] Resolve the "0 sections created" defect noted in `STATUS.md` and expand validation rules/tests accordingly.
- [ ] Update `IMPORT_SYSTEM_GUIDE.md` and related docs to reflect the refreshed flow.
**Definition of Done**: Validation-only mode works, imports are tenant-safe, section creation bug fixed, documentation/tests updated.  
**Hand-off**: Substantial systems work; viable for background agent with clear acceptance tests.

## Priority 5 – Billing Foundations (Epic)
**Status**: Not started  
**Docs**: `planning/documentation/PRICING_STRATEGY.md:23`, `planning/documentation/PERMISSION_MATRIX.md:25`, `models.py:303`, `database_service.py:260`  
**Goal**: Implement billing data model, reporting, and admin controls to prepare for monetization.
**Key Tasks**:
- [ ] Design Firestore collections/services for subscriptions, invoices, and usage aligned with Pricing Strategy.
- [ ] Implement a `billing_service` that leverages `User.calculate_active_status` for seat counts and tracks subscription lifecycle.
- [ ] Build institution admin UI to view usage, invoices, and manage payment details.
- [ ] Add reporting/exports for finance (CSV/JSON) and integrate with future payment providers.
- [ ] Update permission matrix and docs to show implemented billing capabilities.
**Definition of Done**: Billing data persisted, admin UI exposes usage/invoices, exports ready, documentation refreshed.  
**Hand-off**: Cross-cutting initiative—keep with core team.

## Priority 6 – Account Settings Save & Password Change (Story) **Hand-off Candidate**
**Status**: Not started  
**Docs**: `static/auth.js:623`, `templates/auth/profile.html`, `AUTH_SYSTEM_DESIGN.md:783`  
**Goal**: Make the profile page functional for updating user info and passwords.
**Key Tasks**:
- [ ] Implement `/api/account/profile` and wire `handleUpdateProfile` in `static/auth.js` to persist profile edits via `database_service.update_user`.
- [ ] Implement password change endpoint using `PasswordService` and hook `handleChangePassword` UI (with confirmations and strength meter updates).
- [ ] Add backend/unit tests plus UAT steps to verify both workflows.
- [ ] Log/audit password changes per security requirements and send confirmation emails if applicable.
**Definition of Done**: Profile edits and password changes persist securely, TODOs removed, Story 6.1 checklist completed.  
**Hand-off**: Focused development—ideal for background agent.

## Priority 7 – Production Deployment & Infrastructure (Epic) **CRITICAL GAP**
**Status**: Not started  
**Docs**: None (needs creation)  
**Goal**: Design and implement production deployment pipeline, environment separation, and hosting infrastructure to actually run the application for customers.
**Key Tasks**:
- [ ] **Environment Strategy**: Design dev/staging/prod environment separation with proper configuration management, secrets handling, and database isolation.
- [ ] **Hosting Platform**: Choose and configure hosting platform (Cloud Run, App Engine, traditional VPS, etc.) with auto-scaling, health checks, and monitoring.
- [ ] **CI/CD Pipeline**: Extend current quality gates to include deployment automation, environment promotion, and rollback capabilities.
- [ ] **Domain & SSL**: Set up custom domain, SSL certificates, and DNS configuration for customer-facing URLs.
- [ ] **Database Management**: Configure production Firestore instance, backup strategy, and migration procedures.
- [ ] **Monitoring & Logging**: Implement application monitoring, error tracking, performance metrics, and centralized logging.
- [ ] **Security Hardening**: Production security review, HTTPS enforcement, security headers, rate limiting, and vulnerability scanning.
- [ ] **Documentation**: Create deployment runbook, incident response procedures, and operational documentation.
**Definition of Done**: Application runs in production with proper monitoring, customers can access via custom domain, deployment is automated and repeatable.  
**Hand-off**: Core infrastructure work—requires architectural decisions and production access.

## Priority 8 – Dashboard Pagination & Filtering (Story) **Hand-off Candidate**
**Status**: Not started  
**Docs**: `templates/dashboard/program_admin.html`, `templates/dashboard/site_admin.html`, `static/admin.js`, `static/script.js`, `UAT_GUIDE.md`  
**Goal**: Add client-side pagination, consistent filtering, and "show X per page" controls so dashboards stay usable as data volume grows, while keeping the underlying API responses unpaginated for now.
**Key Tasks**:
- [ ] Introduce reusable pagination widgets (next/previous, page counts) for dashboard tables and admin user lists, slicing the existing API payloads in the browser with default page sizes (25/50/100).
- [ ] Ensure search and filter inputs reset pagination to page 1 and keep their state visible so users understand what subset is shown.
- [ ] Add a "Show X per page" selector and persist the choice per table (local storage/session storage is acceptable) to support power users.
- [ ] Update UAT steps and smoke checks to exercise pagination paths and attach reference screenshots for stakeholder review.
- [ ] Document in STATUS/backlog that API pagination remains a future optimization so the team is aware of the trade-off.
**Definition of Done**: Major dashboard tables expose pagination plus configurable page size without regressing filters/search, documentation/tests refreshed, API untouched for now.  
**Hand-off**: Well-scoped front-end effort that a background agent can own once UX wording is approved.

## Priority 9 – Dashboard Quick Actions & Button Audit (Story) **Hand-off Candidate**
**Status**: Partial  
**Docs**: `templates/dashboard/site_admin.html:7`, `templates/dashboard/program_admin.html`, `UAT_GUIDE.md`  
**Goal**: Replace "coming soon" actions with real workflows or hide them until implemented to avoid UAT friction.
**Key Tasks**:
- [ ] Inventory dashboard buttons that still raise placeholder alerts and map desired destinations (e.g., link Site Admin quick actions to `admin/user_management.html`).
- [ ] Either wire the buttons to real flows or hide them behind a feature flag until ready.
- [ ] Update UAT documentation to reflect the new behavior and add smoke tests ensuring no dead actions remain.
- [ ] Refresh `STATUS.md` to record the cleanup.
**Definition of Done**: All exposed actions function or are intentionally hidden, documentation/tests updated.  
**Hand-off**: UI polish that a background agent can execute once decisions are set.

## Priority 10 – Monitoring & Alerting Foundations (Story)
**Status**: Not started  
**Docs**: `logging_config.py`, `STATUS.md` (needs update), vendor docs for Slack webhooks & Sentry  
**Goal**: Establish lightweight observability (Slack alerts + Sentry capture) soon after the CEI POC demo so we can monitor live health without incurring costs.
**Key Tasks**:
- [ ] Draft a post-POC rollout plan confirming this work begins after the demo and record the sequencing in `STATUS.md`.
- [ ] Configure a Slack incoming webhook (free workspace) and add notification hooks in `logging_config.py` for critical events (import failures, auth exceptions).
- [ ] Integrate Sentry (free tier) with Flask to capture unhandled exceptions and key breadcrumbs while stripping sensitive data.
- [ ] Document required environment variables and secrets management, including how to disable alerting in non-prod environments.
- [ ] Add smoke/UAT steps to trigger a synthetic error and confirm Slack + Sentry both capture the event.
**Definition of Done**: Slack channel receives critical alerts, Sentry records application errors, rollout order documented, and toggles/secrets clearly defined.  
**Hand-off**: Requires coordination with product owner and workspace access—keep with core team.
