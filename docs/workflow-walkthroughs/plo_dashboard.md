# Program Learning Outcomes Dashboard

**Duration:** 10 minutes
**Year:** 2026
**Workflow:** Create PLO → Edit PLO → Map CLO → Publish → Drill Program → PLO → CLO → Section

Walk the full PLO lifecycle on the new dashboard: create and edit a
Program Outcome, map a Course Outcome into it, publish the mapping,
then drill from program down to a specific section assessment. Seed
data ships with two programs (Biology and Zoology) spanning two terms
with mixed assessment coverage, so the tree has real leaves to land on.

> **Automated run:** the same demo is scripted end-to-end at
> `demos/plo_dashboard_workflow.json`. Run it with
> `python docs/workflow-walkthroughs/scripts/run_demo.py --auto`
> — it hits all four beats (create / edit / map / drilldown) via
> the real API and verifies each mutation with direct sqlite checks.

---

## Setup

```bash
source venv/bin/activate
source .envrc
python scripts/seed_db.py --demo --manifest demos/full_semester_manifest.json --clear --env local
./scripts/restart_server.sh local
```

**Demo Account:**
- URL: http://localhost:3001/plo-dashboard
- Email: `loopcloser_demo_admin@proton.me`
- Password: `TestPass123!`

**Seeded state:**
- **BIOL** — display mode `both` · 4 PLOs · v1 mapping published
  - PLO-4 is intentionally unmapped (demonstrates empty state)
- **ZOOL** — display mode `percentage` · 2 PLOs · v1 mapping published
- Two terms of section assessment data feeding the tree leaves

---

## Demo Flow

### Step 1: Login and open the PLO dashboard

Navigate to http://localhost:3001 and log in with the credentials above.

In the left nav, click **Program Outcomes** (sitemap icon). You land on
`/plo-dashboard` with the **Biology** program pre-selected.

The tree shows **PLO-1** through **PLO-4**. Each PLO header has a
pass-rate badge — BIOL uses the "both" display mode so badges read
something like `S (78%)`. PLO-4 has no badge and shows a muted
*"No CLOs mapped yet"* pill instead.

The summary strip across the top reads: **4 Program Outcomes · 8 Mapped
CLOs · ~XX% Overall Pass Rate · v1 published**.

**Press Enter to continue →**

---

### Step 2: Create PLO-5

Click **New PLO** (top right).

In the modal:
- **PLO Number:** `5`
- **Description:** `Students will integrate biological knowledge across
  scales from molecules to ecosystems.`

Click **Save**. The modal closes and the tree reloads in place.

**PLO-5** appears at the bottom with the same *"No CLOs mapped yet"*
pill that PLO-4 has. The summary strip ticks up to **5 Program Outcomes**.

*Why no version bump?* PLO templates live on `program_outcomes`, not
`plo_mappings`. Only mapping entries are versioned.

**Press Enter to continue →**

---

### Step 3: Edit PLO-5

Hover over **PLO-5** and click the small **✎** pencil button on the
right of its header.

Update the description to:
`Students will integrate biological knowledge across scales from
molecules to ecosystems, demonstrating synthesis through a capstone
project.`

Click **Save**. The tree updates in place — still no new mapping
version (again, this is a template edit).

**Press Enter to continue →**

---

### Step 4: Map a CLO into PLO-5

Click **Map CLO to PLO** in the tree card header.

Because the seeder already published mapping **v1**, opening this modal
auto-creates a new **draft** (v2-to-be) copied from v1. The tree header
badge changes from **v1 · published** to **draft**.

In the modal:
- **Program Outcome:** select **PLO-5**
- **Course Outcome:** select **BIOL-301 CLO-3** (it appears in the
  dropdown because no PLO currently owns it in the draft)

Click **Add Mapping**. Toast confirms. The dropdown re-populates with
remaining unmapped CLOs.

**Press Enter to continue →**

---

### Step 5: Publish the draft as v2

Still in the Map CLO modal, click **Publish Draft** in the footer.

Confirm. The draft is published as **version 2**. Close the modal.

The tree header badge reads **v2 · published**. Expand **PLO-5** —
**BIOL-301 CLO-3** is now nested under it, and any Fall-2025
section-assessment rows for that CLO flow into the PLO-5 pass-rate
badge.

Publishing also snapshots the PLO description into each mapping
entry (`plo_description_snapshot`) — historical mappings stay intact
even if you edit the template later.

**Press Enter to continue →**

---

### Step 6: Drill down to a specific section

Click **PLO-1** to expand. Three CLOs appear (BIOL-101/201/301 CLO-1),
each with its own aggregated pass rate.

Click **BIOL-101 CLO-1** to expand. You land on **section-level
leaves**: each row shows section number, instructor, term,
`students_took`, `students_passed`, and an S/U badge coloured green
(≥70%) or amber.

This is the full drilldown path: **Program → PLO → CLO → Section**.

**Press Enter to continue →**

---

### Step 7: Filter by term and flip display mode

With a CLO node still expanded, change the **Term** filter to
**Spring 2025**. The section leaves re-filter to just Spring rows —
the PLO and CLO pass-rate badges update to reflect only that term's
contribution.

Now change **Assessment Display** to **Percentage**. Every badge in
the tree instantly re-renders as a bare percentage (e.g. `78%`). This
preference is **saved per-program** (lands in `programs.extras`) so it
survives page reloads.

**Press Enter to continue →**

---

### Step 8: Switch to the Zoology program

Change the **Program** filter to **Zoology**.

The tree reloads. ZOOL has **2 PLOs** (seeded at v1). The
**Assessment Display** dropdown auto-switches to **Percentage** —
that's ZOOL's saved preference — so every badge already shows bare
percentages.

Expand **PLO-2 → ZOOL-101 CLO-2** to land on a section with real
numbers.

Done! You've covered all four beats:

| Beat       | What you did                                            |
| ---------- | ------------------------------------------------------- |
| Create PLO | PLO-5 via **New PLO** modal                             |
| Edit PLO   | Updated PLO-5 description inline                        |
| Map CLO    | Draft → BIOL-301 CLO-3 into PLO-5 → Publish v2          |
| Drilldown  | Program → PLO-1 → BIOL-101 CLO-1 → section rows         |

**Press Enter to continue →**

---
