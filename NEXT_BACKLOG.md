# Course Record Updater – Post-Adapter Implementation Backlog

## Priority 0 – Environment Separation (DEV/E2E/CI) **COMPLETED** ✅
**Status**: Completed  
**Docs**: `.envrc.template`, `run_uat.sh`, `restart_server.sh`  
**Goal**: Separate development, E2E testing, and CI environments to prevent conflicts and enable parallel work.
**Progress**: ✅ Complete three-environment model implemented.
**Completed Tasks**:
- [x] **Step 1**: Updated `.envrc` with `APP_ENV` variable and case statement for environment detection
- [x] **Step 2**: Updated `restart_server.sh` to support explicit environment argument
- [x] **Step 3**: Updated `run_uat.sh` to use `e2e` environment
- [x] **Step 4**: Tested local isolation (dev on 3001, E2E on 3002)
- [x] **Step 5**: CI pipeline uses `APP_ENV=e2e`
- [x] **Step 6**: Documentation updated
**Environment Configuration**:
- **DEV**: Port 3001, `course_records_dev.db`, manual control, persistent data
- **E2E**: Port 3002, `course_records_e2e.db`, auto-managed by run_uat.sh, fresh DB each run
- **CI**: Port 3003, `course_records_ci.db`, GitHub Actions managed, ephemeral
**Benefits Delivered**: E2E tests don't interrupt dev work, multiple agents can work simultaneously, clear environment separation.

## Priority 1 – Export System Enhancement (Epic) **UPDATED**
**Status**: Import system completed, export needs refinement  
**Docs**: `adapters/`, `import_service.py`, `export_service.py`, `scripts/ship_it.py`  
**Goal**: Complete the bidirectional adapter-based system with enhanced export capabilities and roundtrip validation.
**Progress**: ✅ Full adapter-based import system implemented with CEI Excel adapter, conflict resolution, dry-run mode, and comprehensive validation.
**Remaining Tasks**:
- [ ] **Enhanced Export Service**: Improve export service with better formatting and institution-specific adapters
- [ ] **Roundtrip Validation Framework**: Implement automated import→export→diff testing across all adapters
- [ ] **Default Adapter Export Views**: Create standard academic and administrative export formats
- [ ] **API Export Endpoints**: Add export endpoints with adapter selection and format options
- [ ] **CI Quality Gate**: Integrate roundtrip validation into CI pipeline
**Definition of Done**: Export system matches import capabilities, roundtrip validation passes, export API functional.  
**Hand-off**: Can be delegated once core architecture decisions are made.

## Priority 1 – Multi-Tenant Context Hardening (Story 5.6) **UPDATED**
**Status**: Partially completed - database migration done  
**Docs**: `database_service.py`, `database_sqlite.py`, `api_routes.py`, `auth_service.py`  
**Goal**: Complete transition from Firestore to SQLite and implement proper tenant scoping.
**Progress**: ✅ Full migration from Firestore to SQLite database, ✅ Institution-agnostic design implemented.
**Remaining Tasks**:
- [ ] Apply institution/program filters across all list endpoints to honor multi-tenant scoping
- [ ] Implement context middleware fallbacks and default program handling
- [ ] Expand unit/integration coverage for context switching and access control
- [ ] Remove any remaining Firestore references and complete SQLite transition
**Definition of Done**: Full SQLite integration, proper tenant scoping, comprehensive test coverage.  
**Hand-off**: Database coordination complete - can be delegated for remaining scoping work.

## Priority 2 – Email Communication System Launch (Epic)
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

## Priority 3 – Email Template Validation & Stakeholder Sign-off (Story) **Hand-off Candidate**
**Status**: Not started  
**Docs**: `planning/INSTRUCTOR_MANAGEMENT_TIMELINE.md:88`, `email_service.py`  
**Goal**: Verify copy, branding, and layout with CEI stakeholders before enabling live emails.
**Key Tasks**:
- [ ] Render HTML/text versions of each template and capture screenshots/PDF artifacts for review.
- [ ] Facilitate review with CEI stakeholders (Leslie, program admins) and iterate on copy/branding feedback.
- [ ] Archive approved templates and note sign-off in STATUS or planning docs.
**Definition of Done**: Stakeholder approval recorded; final templates (and visuals) attached to planning docs.  
**Hand-off**: Perfect for a background agent to coordinate and document.

## Priority 4 – Email UAT & Monitoring Readiness (Story) **Hand-off Candidate**
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

## Priority 5 – Excel Import System (Epic) **COMPLETED** ✅
**Status**: Completed  
**Docs**: `import_service.py`, `adapters/`, `templates/components/data_management_panel.html`, `api_routes.py`  
**Goal**: Implement comprehensive Excel import system with adapter architecture and validation.
**Progress**: ✅ Complete adapter-based import system with CEI Excel adapter, ✅ Dry-run mode implemented, ✅ Conflict resolution strategies, ✅ Comprehensive validation and error handling, ✅ UI integration with data management panel.
**Key Features Delivered**:
- ✅ Adapter registry system for extensible import formats
- ✅ CEI Excel format adapter with multiple format variants support
- ✅ Conflict resolution (USE_THEIRS, USE_MINE, MERGE, MANUAL_REVIEW)
- ✅ Dry-run mode for import validation without data persistence
- ✅ Comprehensive import statistics and error reporting
- ✅ UI integration with file upload and import options
- ✅ Institution-agnostic design supporting multi-tenant operations
**Definition of Done**: ✅ All features implemented and tested.  
**Hand-off**: System complete and operational.

## Priority 6 – Billing Foundations (Epic)
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

## Priority 7 – Account Settings Save & Password Change (Story) **Hand-off Candidate**
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

## Priority 8 – Production Deployment & Infrastructure (Epic) **UPDATED**
**Status**: Foundations in place, deployment pipeline needed  
**Docs**: `scripts/ship_it.py`, `QUALITY_GATE_SUMMARY.md`, `sonar-project.properties`, `.github/workflows/`  
**Goal**: Complete production deployment pipeline and hosting infrastructure.
**Progress**: ✅ Comprehensive quality gates with ship_it.py, ✅ SonarCloud integration, ✅ SQLite database ready for production, ✅ Security scanning and linting pipeline.
**Remaining Tasks**:
- [ ] **Hosting Platform**: Choose and configure hosting platform with auto-scaling and health checks
- [ ] **Environment Strategy**: Implement dev/staging/prod environment separation with proper configuration management
- [ ] **CI/CD Pipeline**: Extend quality gates to include automated deployment and rollback capabilities
- [ ] **Domain & SSL**: Set up custom domain, SSL certificates, and DNS configuration
- [ ] **Database Management**: Configure production SQLite backup strategy and migration procedures
- [ ] **Monitoring & Logging**: Implement application monitoring, error tracking, and centralized logging
- [ ] **Security Hardening**: Production security review, HTTPS enforcement, and rate limiting
**Definition of Done**: Application deployable to production with monitoring, domain configured, automated deployment pipeline.  
**Hand-off**: Infrastructure work - requires hosting platform decisions and production access.

## Priority 9 – Dashboard Pagination & Filtering (Story) **Hand-off Candidate**
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

## Priority 10 – Dashboard Quick Actions & Button Audit (Story) **Hand-off Candidate**
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

## Priority 11 – Monitoring & Alerting Foundations (Story)
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
