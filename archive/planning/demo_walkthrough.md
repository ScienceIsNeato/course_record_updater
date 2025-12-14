# Reusable Demo Walkthrough (Draft)

> Narrative script for giving the demo. Update in place as we refine the storyline.  
> Supporting work items live in `planning/demo-walkthrough-checklist.md`.

## Why This Demo
- Show how a multi-tenant institution can plan, execute, and audit a semester’s assessment cycle without bespoke scripting.
- Prove the hybrid natural-key architecture (sessions survive reseeds), streamlined course management, automated reminders, and audit close-out.

## Personas & Credentials
| Role | Login | Notes |
| --- | --- | --- |
| Institution Admin | `demo2025.admin@example.com` / `Admin123!` | Primary narrator; edits programs/courses, runs reminders & audits |
| Biology Faculty (Dr. Morgan) | `dr.morgan@demo.example.com` / `Instructor123!` | Receives invites/reminders, submits CLO data |
| Zoology Faculty (Dr. Patel) | `dr.patel@demo.example.com` / `Instructor123!` | Provides "pending/missing evidence" contrast |

## Environment Reset
```bash
activate
python scripts/seed_db.py --demo --clear --env dev
./restart_server.sh dev     # requires env arg (dev/e2e)
```
- Visit `/logout` before logging back in if cookies linger.
- Demo runs at `http://localhost:3001`.

## Storyboard Snapshot
1. **Programs & Courses** – update descriptions, duplicate `BIOL-201`, attach to multiple programs, re-import Excel to show idempotence.
2. **Faculty Access & Reminders** – invite biology instructor, prove reminder job + email preview logging.
3. **Assessment Submission** – faculty submits CLO data with evidence; admin reviews.
4. **Audit Closeout** – approve Biology submission, reject Nursing, export reports, highlight dashboard changes.

## Artifacts to Capture
- Screenshots → `artifacts/` (program edits, duplicate modal, reminder toast, faculty submission, dashboard panels).
- Logs → `logs/email.log`, `logs/server.log`, optional `logs/import_flow.log`.
- Exports → `demo_artifacts/audit/*.csv|pdf`.

## Talking Points
- Natural keys keep sessions stable across reseeds (`/logout` resets quickly).
- Duplicate button accelerates “version 2” courses and multi-program coverage.
- Email previews now land in `logs/email.log`, so demos don’t rely on external inboxes.
- Audit approvals instantly feed dashboard KPIs—closed loop.

---

## Phase 1 – Environment & Narrative Setup
1. Mention the hybrid session model (natural keys stored in Flask-Session). Show `/logout` for stale cookies.
2. Run reseed + restart commands; refresh dashboard to prove data loads immediately.
3. Call out new `/logout` GET endpoint for quick resets during walkthroughs.

## Phase 2 – Institution & Program Configuration
1. **Program refresh**  
   - Navigate to **Dashboard** → **Programs**.  
   - Click **Edit** on "Biological Sciences". Change description to: *"Primary focus for Fall 2024 Accreditation Cycle."*
   - Click **Save**. Show success toast.
   - Refresh page (or check "Assessment Progress" card) to show updates persist.
   - *Narrative*: "We can rapidly align program metadata with current accreditation goals."
2. **Course versioning + duplication**  
   - Navigate to **Courses**. Find `BIOL-201 Cellular Biology`.
   - Click **Duplicate** (copy icon).
   - **Modal Action**:
     - Change Course Number to `BIOL-201-V2`.
     - In **Programs**, select BOTH "Biological Sciences" and "Nursing" (cross-program attachment).
     - Click **Duplicate**.
   - Verify `BIOL-201-V2` appears in list.
   - *Log Check*: Show `demo_artifacts/phase2/course_duplication_logs.md` to prove backend idempotence.
3. **Course import flow**  
   - Click **Import Courses**.
   - Upload `demo_data/course_import_template.xlsx` (generated via `scripts/advance_demo.py generate_logs`).
   - Show success toast: "Imported 9 records".
   - **Idempotence Test**: Upload the *same file again*.
   - Show toast: "0 created, 9 updated/skipped".
   - *Artifact*: Reference `demo_artifacts/phase2/import_logs.md` which shows `Term already exists` and `Updated course` logic.

## Phase 3 – Faculty & Assessment Execution
1. **Instructor invitation**  
   - Navigate to **People** → **Instructors**.
   - Click **Invite Instructor**.
   - Email: `new.faculty@demo.example.com` (matches log artifact).
   - Program: "Biological Sciences".
   - Click **Send Invite**.
   - *Log Verification*: Open `logs/email.log` (or `demo_artifacts/phase3/invitation_logs.md`) to show the "BLOCKED (Allowlist)" message, proving the email system attempted delivery safely in dev.
2. **Reminders**  
   - Navigate to **Bulk Emails** → **Pending Assessments**.
   - Filter by Term: "Fall 2024".
   - Click **Send Reminders**.
   - Show success toast.
   - *Log Verification*: Reference `demo_artifacts/phase3/reminder_logs.md` to show the rendered email text ("Hello Alex Morgan...").
3. **Faculty submission**  
   - *Option A (Manual)*: Logout, login as `faculty.biology@example.com`. Submit `BIOL-201` with `demo_data/sample_evidence.pdf`.
   - *Option B (Fast Forward)*: Skip to Phase 4 setup script.

## Phase 4 – End-of-Semester Audit
> **Fast Forward**: If skipping manual execution of Phase 3, run:
> ```bash
> python scripts/advance_demo.py semester_end --env dev
> ```
> This script simulates faculty submissions, sends reminders, and duplicates courses to establish the "Day 90" state.

1. **Prereqs** – Ensure Biology has ≥1 submitted, ≥1 pending; Nursing missing evidence (seed already close).  
2. **Audit workflow**  
   - Navigate to **Audit Center**.
   - **Filter**: Set Program="Biological Sciences", Term="Fall 2024".
   - **Review**: Click `BIOL-201` (Status: Awaiting Approval).
     - Review CLO data. Click **Approve**. Status changes to "Approved".
   - **Request Rework**: Click `ZOOL-101` (Status: Awaiting Approval).
     - Click **Request Rework**. Comment: "Missing student samples for CLO 2."
     - Verify status changes to "Returned".
   - **NCI**: Find a dropped course/section. Click **Mark NCI** (Never Coming In).
3. **Export & Closure**
   - Click **Export Current View**.
   - Save CSV as `audit_report_FA24.csv`.
   - Open CSV to show columns: `Course`, `Instructor`, `Status`, `Action Date`.
4. **Dashboard proof**  
   - Navigate to **Dashboard**.
   - **Assessment Progress**: Show "Approved" count increased.
   - **CLO Audit**: Show NCI category in chart.

---

## Appendix – Reset Reminders
- Always reseed + restart before major walkthrough changes.
- Keep `logs/email.log` tailing to quote from during reminders/audits.
- Archive artifacts under `artifacts/` and `demo_artifacts/` as you iterate so the final demo deck has receipts.
