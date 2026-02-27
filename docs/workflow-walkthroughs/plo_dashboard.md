# PLO Dashboard Walkthrough

**Duration:** 15 minutes
**Year:** 2025
**Workflow:** Navigate → View programs → Filter → Drill down (Program → PLO → CLO → Section) → Change display mode

---

## Setup

```bash
# Seed demo database (clears existing data)
python scripts/seed_db.py --demo --clear --env dev

# Start server
bash scripts/restart_server.sh dev
```

**Demo Account:**
- URL: http://localhost:3001
- Email: demo2025.admin@example.com
- Password: Demo2024!

---

## Demo Flow

### Step 1: Login

Navigate to http://localhost:3001. Enter the credentials above and click "Sign In".

You should be redirected to the Institution Admin Dashboard showing Demo University.

**Press Enter to continue →**

---

### Step 2: Navigate to PLO Dashboard

In the top navigation bar, click "PLOs" (project-diagram icon).

The PLO Dashboard page loads with:
- **Summary cards** at the top showing program count, PLO count, mapped CLOs, and data coverage
- **Filter dropdowns** for Term and Program
- **Tree container** showing all programs with their PLO hierarchies

The current active term (Fall 2025) is auto-selected.

**Press Enter to continue →**

---

### Step 3: View Program Overview

You should see two program cards:
1. **Biological Sciences (BIOL)** — 3 PLOs, mapping v1 published
2. **Zoology (ZOOL)** — 2 PLOs, mapping v1 published

Each card shows the program name, PLO count, mapped CLO count, and mapping version.

**Press Enter to continue →**

---

### Step 4: Drill Down — Program → PLOs

Click on the **Biological Sciences** card to expand it.

Three PLOs appear:
- **PLO 1:** Apply scientific reasoning and the scientific method
- **PLO 2:** Demonstrate proficiency in laboratory techniques
- **PLO 3:** Communicate biological concepts effectively

Each PLO shows how many CLOs are mapped to it.

**Press Enter to continue →**

---

### Step 5: Drill Down — PLO → CLOs

Click on **PLO 1** to expand the CLO table.

A table appears with columns: CLO#, Course, Description, Assessment, Status.

CLOs from BIOL-101, BIOL-201, and BIOL-301 are listed, each showing their course-level assessment data (percentage by default for BIOL program).

CLOs with assessment data show a percentage (e.g., "83%"). CLOs without data show "N/A" in grey.

**Press Enter to continue →**

---

### Step 6: Drill Down — CLO → Sections

Click on a CLO row (e.g., BIOL-101 CLO 1) to expand the section sub-table.

Individual course sections appear with:
- Section number
- Instructor name
- Students who took / passed
- Assessment tool used
- Section status

**Press Enter to continue →**

---

### Step 7: Change Term Filter

Use the **Term** dropdown at the top to switch to "Spring 2025".

The tree reloads with Spring 2025 section-level data. Some CLOs may now show different assessment numbers or "N/A" if data wasn't entered for that term.

**Press Enter to continue →**

---

### Step 8: Filter by Program

Use the **Program** dropdown to select "Zoology (ZOOL)".

Only the Zoology program card appears. Note that ZOOL is configured with **"both"** display mode, so assessment values show as "S (78%)" or "U (54%)" — combining binary and percentage formats.

Click "All Programs" to restore the full view.

**Press Enter to continue →**

---

### Step 9: View from Program Admin Dashboard

Navigate back to the main Dashboard (click "Dashboard" in nav).

If viewing as a Program Admin, scroll down to the **Program Learning Outcomes** panel (panel 6).

This panel shows a mini summary table with PLO numbers, descriptions, and mapped CLO counts, with a link to the full PLO Dashboard.

**Press Enter to continue →**

---

## Summary

The PLO Dashboard provides:
- Cross-program visibility into PLO → CLO → Section assessment data
- Configurable display modes (percentage, binary, or both)
- Term and program filtering
- 4-level drill-down from program overview to individual section outcomes
- Empty state handling for programs without PLOs, mappings, or data
