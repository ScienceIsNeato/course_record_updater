# Course Record Updater - Current Status

## Last Updated
2025-11-16 11:05 PST

## Current Task
🔄 **IN PROGRESS**: CEI demo workflow hardening (feature/workflow-walkthroughs)

## Branch Snapshot
- Branch: `feature/workflow-walkthroughs`
- Latest commit: `fix: stabilize session context and adapter loading` (passes `python scripts/ship_it.py --checks tests`)
- Goal: Convert the CEI-specific walkthrough into a reusable, end-to-end demo that ends with the audit sign-off.

## Recent Progress
- ✅ Session/natural-key work merged into this branch with docs (`ARCHITECTURE.md`).
- ✅ Course edit modal now loads/retains program selections; frontend + Jest tests updated.
- ✅ `/logout` GET route + test landed to reset stale sessions quickly.
- ✅ Adapter registry warning resolved and covered with tests.
- ✅ Temporary checklist created at `planning/demo-walkthrough-checklist.md` (contains storyline beats, personas, and remaining tasks).
- ✅ Email reminders now append previews to `logs/email.log` for demo storytelling (see `EmailService` + new unit tests).
- ✅ Course duplication endpoint/UI added (`POST /api/courses/<id>/duplicate` + button in course list) with Jest + API/Python coverage; program selects now support multi-select inline with roadmap narrative.
- ✅ Demo walkthrough narrative lives in `planning/demo_walkthrough.md`; build checklist/remaining tasks tracked separately in `planning/demo-walkthrough-checklist.md`.

## Open Work (see checklist for detail)
- 🔄 Phase 2: flesh out narrative for program refresh, course versioning, cross-program attachments, and Excel imports.
- 🔄 Phase 3: document instructor invitation/reset flow, bulk reminder runbook, and instructor submission walkthrough.
- 🔄 Phase 4: script end-of-term audit (data prerequisites, approve/reject flow, dashboard evidence).
- ☐ Capture screenshots/log excerpts for each phase once flows are validated.
- ☐ Decide final home for checklist (will delete or move once branch wraps).

## Environment Status (Dev)
- Database: `course_records_dev.db` reseeded via `python scripts/seed_db.py --demo --clear --env dev` before latest validation.
- Server: `./restart_server.sh dev` (port 3001) with adapter/session fixes loaded.
- Browser: Demo login with `demo2025.admin@example.com / Demo2024!` verified; dashboard panels populate.
- Logs: `logs/server.log` clean—no adapter warnings after latest changes.

## Validation
- Last run: `python scripts/ship_it.py --checks tests` (passes; includes pytest + JS unit tests).
- Outstanding checks: rerun ship_it once new demo steps alter backend/frontend logic; add targeted tests for new flows as they appear.

## Next Actions
1. Continue working through `planning/demo-walkthrough-checklist.md` (Phase 3+4 items) and capture required screenshots/logs.
2. Leverage new email preview log when running bulk reminder flow; stash snippets with other demo artifacts.
3. Once demo narrative is complete, prep summary + push branch (user will give push instructions).

## Notes
- Session persistence across reseeds is acceptable if we force re-login; no further work required there.
- Treat CEI as “first customer,” but keep the demo script institution-agnostic for future reuse.
- Checklist is temporary—cleanup before merge.
