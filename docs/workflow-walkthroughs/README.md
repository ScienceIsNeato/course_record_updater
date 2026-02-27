# Workflow Walkthroughs

Product demonstration materials for showcasing key workflows.

## Available Demos

### 1. Single Term Outcome Management (2025)

**File:** `single_term_outcome_management.md`  
**Duration:** 30 minutes  
**Workflow:** Import → Assign → Complete → Audit → Export

Complete end-to-end demonstration of collecting and managing learning outcomes for a single academic term.

---

## Quick Start

### Interactive Demo (Recommended)

```bash
# Run interactive demo with step-by-step guidance
python docs/workflow-walkthroughs/scripts/run_demo.py single_term_outcome_management.md
```

The interactive runner will:

- Parse the demo markdown
- Run setup commands (with your confirmation)
- Guide you through each step
- Pause for you to complete actions
- Track progress

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

   ````markdown
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
   ````

   **Demo Account:**
   - URL: http://localhost:3001
   - Email: demo2025.admin@example.com
   - Password: Demo2024!

   ***

   ## Demo Flow

   ### Step 1: Title

   Instructions for what to do and expect.

   **Press Enter to continue →**

   ***

   ### Step 2: Title

   More instructions...

   **Press Enter to continue →**

   ```

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
# Basic usage
python docs/workflow-walkthroughs/scripts/run_demo.py single_term_outcome_management.md

# Skip setup (if already done)
python docs/workflow-walkthroughs/scripts/run_demo.py --no-setup single_term_outcome_management.md
```

---

## Demo Data

All demos use the generic demo seeder:

```bash
python scripts/seed_db.py --demo --clear --env dev
```

This creates:

- Institution: Demo University (DEMO2025)
- Admin: demo2025.admin@example.com
- Instructors: demo2025.instructor1@example.com, demo2025.instructor2@example.com
- Programs: Computer Science, Business, General Education
- Sample courses and terms

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
