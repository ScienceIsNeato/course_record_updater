# Workflow Walkthroughs

Product demonstration materials for showcasing key workflows.

## Available Demos

### 1. Single Term Outcome Management (2025)
**File:** `single_term_outcome_management.md`
**Duration:** 30 minutes
**Workflow:** Import → Assign → Complete → Audit → Export

Complete end-to-end demonstration of collecting and managing learning outcomes for a single academic term.

### 2. Program Learning Outcomes Dashboard (2026)
**File:** `plo_dashboard.md` · Automated: `demos/plo_dashboard_workflow.json`
**Duration:** 10 minutes
**Workflow:** Create PLO → Edit → Map CLO → Publish → Drill to Section

Full PLO lifecycle on the new dashboard. Seed data ships with two
programs (BIOL + ZOOL) across two terms with published mappings, so
the drilldown tree has real section-assessment leaves out of the box.
BIOL's PLO-4 is intentionally unmapped to demonstrate empty states.

**Automated run (all four beats via real API + sqlite verification):**
```bash
python docs/workflow-walkthroughs/scripts/run_demo.py --auto
```

---

## Quick Start

### Interactive Demo (Recommended)

```bash
# Default: PLO dashboard demo (JSON-backed, fully automated)
python docs/workflow-walkthroughs/scripts/run_demo.py --auto

# Run a specific markdown demo interactively
python docs/workflow-walkthroughs/scripts/run_demo.py single_term_outcome_management.md
```

The runner dispatches based on file extension:
- **`.json`** → delegates to `demos/run_demo.py` (API calls, CSRF
  handling, sqlite3 verification, `--fail-fast`, `--verify-only`)
- **`.md`** → parses the walkthrough contract below, runs the setup
  block, then steps through each section pausing on
  `**Press Enter to continue →**`

### Manual Demo

```bash
# 1. Seed demo database
python scripts/seed_db.py --demo --clear --env dev

# 2. Start server
./restart_server.sh dev

# 3. Follow demo script
open docs/workflow-walkthroughs/single_term_outcome_management.md
```

**Demo Account:**
- URL: http://localhost:3001
- Email: demo2025.admin@example.com
- Password: Demo2024!

---

## Creating New Demos

To add a new workflow demonstration:

1. **Create markdown file** named after the workflow (e.g., `multi_year_assessment_tracking.md`)

2. **Follow the standard structure:**
   ```markdown
   # Workflow Name
   
   **Duration:** X minutes
   **Year:** 2025
   **Workflow:** Brief description
   
   ## Setup
   
   ```bash
   # Setup commands
   python scripts/seed_db.py --demo --clear --env dev
   ./restart_server.sh dev
   ```
   
   **Demo Account:**
   - URL: http://localhost:3001
   - Email: demo2025.admin@example.com
   - Password: Demo2024!
   
   ---
   
   ## Demo Flow
   
   ### Step 1: Title
   
   Instructions for what to do and expect.
   
   **Press Enter to continue →**
   
   ---
   
   ### Step 2: Title
   
   More instructions...
   
   **Press Enter to continue →**
   ```

3. **Test with run_demo.py:**
   ```bash
   python docs/workflow-walkthroughs/scripts/run_demo.py your_new_demo.md
   ```

### Demo Markdown Contract

For compatibility with `run_demo.py`, demos should follow these conventions:

- **`## Setup` section** with bash code block containing setup commands
- **`### Step N: Title`** for each demo step  
- **`**Press Enter to continue →**`** markers where demo should pause
- Clear instructions for actions and expected results
- **Demo Account** section with credentials

---

## Tools

### run_demo.py - Interactive Demo Runner

Parses markdown demo files and provides step-by-step interactive guidance.

**Features:**
- Runs setup commands automatically (with confirmation)
- Displays steps one at a time
- Waits for Enter key to continue
- Tracks progress through demo
- Color-coded output for readability

**Usage:**
```bash
# Default to PLO JSON demo, run automated
python docs/workflow-walkthroughs/scripts/run_demo.py --auto

# Automated with fast iteration
python docs/workflow-walkthroughs/scripts/run_demo.py --auto --start-step 4 --fail-fast

# Markdown demo, interactive
python docs/workflow-walkthroughs/scripts/run_demo.py single_term_outcome_management.md

# Markdown demo, skip setup block
python docs/workflow-walkthroughs/scripts/run_demo.py --no-setup plo_dashboard.md
```

---

## Demo Data

All demos use the manifest-driven demo seeder:

```bash
# Generic demo data
python scripts/seed_db.py --demo --clear --env dev

# Full semester manifest (includes PLOs + published PLO↔CLO mappings)
python scripts/seed_db.py --demo --manifest demos/full_semester_manifest.json --clear --env local
```

The full-semester manifest creates:
- Institution: Fictional University (demo accounts)
- **BIOL** and **ZOOL** programs, each with multi-term courses
- **Program Outcomes** (4 in BIOL, 2 in ZOOL) with a **v1 published
  PLO↔CLO mapping** so the PLO dashboard tree is populated on first
  load
- Per-program `assessment_display_mode` preference (BIOL=both,
  ZOOL=percentage)
- Section-level assessment overrides to give the drilldown real
  leaf data

**Why 2025 prefix?**  
Unique prefixes prevent conflicts with E2E test users when running in parallel.

---

## Use Cases

**Sales & Pitching:** Use single_term_outcome_management.md for complete workflow demo

**User Training:** Follow demo step-by-step for onboarding new users

**QA Testing:** Use demo as smoke test for critical paths

**Development:** Reference for expected user journeys

---

## Maintenance

- Keep demos up-to-date with product features
- Test demos before important presentations
- Add new workflow demos as product expands
- Archive outdated demos (don't delete - move to archived/)

---

**Last Updated:** November 11, 2025  
**Contact:** Product Team
