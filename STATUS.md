# 🚧 Current Work Status

**Last Updated**: 2025-12-15

---

## Current Task: UI/UX Demo Refinement & Critical Fixes ✅

### ✅ Fix Sections and Enrollment in Offerings Panel
- **Issue**: Sections and Enrollment counts were zero.
- **Fix**: Updated `dashboard_service.py` to robustly handle parsing.

### ✅ Enhance Demo Data
- **Issue**: Demo data had zero enrollment.
- **Fix**: Updated `seed_db.py` to randomise enrollment.

### ✅ Fix 'Manage' Button in Program Management
- **Issue**: Button did nothing.
- **Fix**: Wired it to 'Edit Program' modal via `data-action`.

### ✅ Improve Dashboard Navigation
- **Issue**: Confusing flow and lack of feedback.
- **Fix**: Renamed nav items to specific workflow names (e.g., "Program Management"), added page title updates, and scroll-to-top behavior.

### ✅ Fix /courses Page Error
- **Issue**: `Unexpected token '<'` (HTML 404) when loading courses.
- **Fix**: Updated `courses_list.html` to use valid `/api/programs` endpoint.

### ✅ Fix Assessment Save Error
- **Issue**: `reloadSections is not defined` when saving assessment.
- **Fix**: Corrected function scope in `assessments.html`.

---

## Next Steps

1. **Verify Cloud Run Deployment** relative to `dev` environment.
2. **Configure Cloudflare DNS** (External).
3. **Deploy Staging Environment**.

---

## PR Validation Work (In Progress) 🧪

### ✅ E2E stability fixes
- **Offerings modal**: Treat empty `program_id` as `null` and use `bootstrap.Modal.getOrCreateInstance(...).hide()` so the modal reliably closes after successful create.
- **Users edit modal**: Avoid attempting role updates unless current user is `institution_admin` or `site_admin` (prevents 403s for instructors editing their profile) and close modal reliably.
- **E2E regression fix**: Updated `tests/e2e/test_crud_institution_admin.py` to select the required `#offeringProgramId` field when creating an offering (form `required` prevented submit, so `/api/offerings` was never called).

### ✅ Sonar protocol noise reduction
- Updated `scripts/analyze_pr_coverage.py` to exclude `demos/` and `docs/workflow-walkthroughs/scripts/` from "new code coverage" targets, aligning with `.coveragerc`/Sonar exclusions.

### ⏳ Sonar quality gate (currently failing)
- **Quality gate metrics**: `Coverage on New Code` below threshold and `new_duplicated_lines_density` slightly above threshold.
- **Fixes in progress**: Addressing Sonar-reported code smells (`import_service.py` return-value refactor, `models_sql.py` FK constants), workflow security hotspots (`npm ci --ignore-scripts`, restricted `wget` redirects), and remaining coverage/duplication targets per `logs/pr_coverage_gaps.txt` and `logs/sonarcloud_duplications.txt`.

### ✅ Sonar + E2E hardening work (local)
- **Bootstrap modal stability**: Improved modal close behavior and prevented 403 role update attempts for instructors.
- **JS test reliability**: Added jsdom polyfills in `tests/javascript/setupTests.js` (e.g., `scrollTo`, `alert`) to make `npm run test:coverage` reliable locally.
- **Surgical new-code coverage**: Added/expanded Jest tests for `static/termManagement.js`, `static/offeringManagement.js`, `static/audit_clo.js`, and course/dashboard helpers; added Python unit tests for `/api/users/<id>/role` and `/api/courses/<id>/duplicate` endpoints with CSRF handling.
- **Duplication reduction**: Refactored `static/offeringManagement.js` to share select-option population + button loading helpers (reduces duplicated blocks while preserving behavior).
- **Workflow security hotspots**: Pinned GitHub Action `uses:` references to full commit SHAs in `.github/workflows/*.yml`.
