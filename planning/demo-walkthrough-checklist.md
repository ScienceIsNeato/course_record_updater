# Demo Build Checklist (Temporary)

> _Progress tracker for `feature/workflow-walkthroughs`. The actual narrative lives in `planning/demo_walkthrough.md`._

- ✅ = complete this sprint  
- 🔄 = in progress / partially addressed  
- ☐ = not started

## Phase 1 – Environment Setup
- ✅ Natural-key session model documented + `/logout` helper verified.
- ✅ Deterministic demo seed + restart flow documented (see walkthrough).

## Phase 2 – Institution & Program Configuration
- ✅ Program/course editing path verified (stats cards update, modal loads programs).
- 🔄 Program refresh copy tweaks + screenshot (`artifacts/program-refresh.png`).
- ✅ Course duplication storyline: logs verified in `demo_artifacts/phase2/course_duplication_logs.md`.
- 🔄 Cross-program attachment proof (API/table filter) once duplicate captured.
- ✅ Course import flow artifacts: logs verified in `demo_artifacts/phase2/import_logs.md`.

## Phase 3 – Faculty & Assessment Execution
- ✅ Instructor invitation artifacts: logs verified in `demo_artifacts/phase3/invitation_logs.md`.
- ✅ Reminder runbook: logs verified in `demo_artifacts/phase3/reminder_logs.md`.
- 🔄 Faculty submission proof: screenshot of completed form + success banner, log reference.

## Phase 4 – Audit & Dashboards
- ✅ Audit workflow filters, export, and NCI logic implemented + tested.
- ✅ Data prerequisites validated (Setup script `scripts/demo_fast_forward_to_semester_end.py` creates submitted/pending mix).
- 🔄 Audit workflow screenshots + exported CSV/PDF stored under `demo_artifacts/audit/`.
- 🔄 Dashboard evidence (Assessment Progress, CLO Audit widget, Data Management panel) before/after.

## Cross-Cutting
- ✅ STATUS.md updated alongside major milestones.
- 🔄 Track remaining blockers (login friction, seed data gaps) as checklist items.
- 🔄 Plan cleanup: remove checklist once branch merges or move final doc into `/documentation`.
