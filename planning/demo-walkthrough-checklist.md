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
- 🔄 Course duplication storyline: capture before/after table + API log snippet.
- 🔄 Cross-program attachment proof (API/table filter) once duplicate captured.
- 🔄 Course import flow artifacts: toast screenshot + `logs/import_flow.log`.

## Phase 3 – Faculty & Assessment Execution
- 🔄 Instructor invitation artifacts: toast + `logs/email.log` entry.
- 🔄 Reminder runbook: toast screenshot, email preview snippet, optional CSV export.
- 🔄 Faculty submission proof: screenshot of completed form + success banner, log reference.

## Phase 4 – Audit & Dashboards
- 🔄 Data prerequisites validated (submitted/pending/missing evidence mix).
- 🔄 Audit workflow screenshots + exported CSV/PDF stored under `demo_artifacts/audit/`.
- 🔄 Dashboard evidence (Assessment Progress, CLO Audit widget, Data Management panel) before/after.

## Cross-Cutting
- ✅ STATUS.md updated alongside major milestones.
- 🔄 Track remaining blockers (login friction, seed data gaps) as checklist items.
- 🔄 Plan cleanup: remove checklist once branch merges or move final doc into `/documentation`.

