# Demo System Implementation Plan

## Overview

Convert the scattered demo materials (markdown files, standalone scripts, multiple protocols) into a unified, deterministic demo system with automated and human-guided execution modes.

## Goals

1. **Single Source of Truth**: One JSON file per demo containing all steps, commands, and instructions
2. **Dual Execution Modes**:
   - `--auto`: Automated agent mode for validation/iteration
   - Default: Human-guided presenter mode with explicit instructions
3. **Deterministic**: Same steps, same order, every time
4. **Developer-Friendly**: Fast iteration with `--start-step` and `--fail-fast` flags

## Current State Problems

- Multiple demo protocols in use simultaneously
- `run_demo.py` exists but not integrated with main walkthrough
- `planning/demo_walkthrough.md` is manual narrative (not parsed)
- `scripts/advance_demo.py` is separate state setup tool
- Confusion about "how to run the demo"

## Target Architecture

```
demos/
├── README.md                          # How to create and run demos
├── run_demo.py                        # Orchestrator script
├── full_semester_workflow.json       # Main demo (client-agnostic)
├── quick_feature_tour.json           # Future: 5-min demo
└── artifacts/                         # Auto-generated during runs
    └── {demo_name}_{timestamp}/
        ├── screenshots/
        ├── logs/
        └── exports/
```

**Naming Convention**: `{descriptive_name}.json` (e.g., `full_semester_workflow.json`, `quick_feature_tour.json`)

- Keep demos client-agnostic
- Specific clients watch generic demos

## JSON Schema

```json
{
  "demo_name": "Full Semester Workflow",
  "demo_id": "full_semester_workflow",
  "version": "1.0",
  "description": "Complete semester lifecycle from setup through audit",
  "estimated_duration_minutes": 20,
  "environment": {
    "setup_commands": [
      "python scripts/seed_db.py --demo --clear --env dev",
      "./restart_server.sh dev"
    ],
    "base_url": "http://localhost:3001"
  },
  "steps": [
    {
      "step_number": 1,
      "phase": "Setup",
      "name": "Admin Login",
      "purpose": "Establish admin session for program configuration",

      "pre_commands": [
        {
          "command": "curl -s http://localhost:3001/api/health",
          "purpose": "Verify server is running",
          "expected_output_contains": "ok"
        }
      ],

      "instructions": {
        "human": "Click the link below to navigate to the login page, then sign in with the provided credentials.",
        "automated": {
          "action": "browser_login",
          "credentials": {
            "email": "demo2025.admin@example.com",
            "password": "Admin123!"
          }
        }
      },

      "urls": [
        {
          "label": "Login Page",
          "url": "http://localhost:3001/login",
          "clickable": true
        }
      ],

      "inputs": {
        "email": "demo2025.admin@example.com",
        "password": "Admin123!"
      },

      "expected_results": [
        "Dashboard loads with welcome message",
        "URL changes to /dashboard",
        "Admin name visible in header"
      ],

      "post_commands": [
        {
          "command": "sqlite3 course_records_dev.db \"SELECT COUNT(*) FROM users WHERE email='demo2025.admin@example.com'\"",
          "purpose": "Confirm admin user exists",
          "expected_output": "1"
        }
      ],

      "verification": {
        "type": "ui_check",
        "expected_url": "/dashboard",
        "expected_text": "Dashboard"
      },

      "artifacts": {
        "screenshots": ["01_admin_dashboard.png"],
        "logs": []
      },

      "pause_for_human": true
    }
  ]
}
```

### Key Schema Features

- **pre_commands**: CLI commands run before step (with purpose/verification)
- **instructions**: Dual format for human (text) and automated (action)
- **urls**: Clickable links for human navigation
- **inputs**: Standardized inputs displayed to human
- **expected_results**: What human should see after action
- **post_commands**: CLI verification after step
- **artifacts**: Screenshots/logs to capture
- **pause_for_human**: Whether to wait for Enter (ignored in --auto mode)

## CLI Interface

```bash
# Human presenter mode (default)
python demos/run_demo.py --demo full_semester_workflow.json

# Automated validation mode
python demos/run_demo.py --demo full_semester_workflow.json --auto

# Start from specific step (for iteration)
python demos/run_demo.py --demo full_semester_workflow.json --start-step 37

# Exit on first verification failure (for development)
python demos/run_demo.py --demo full_semester_workflow.json --auto --fail-fast

# Combined: iterate on step 37 with fast feedback
python demos/run_demo.py --demo full_semester_workflow.json \
  --auto \
  --start-step 37 \
  --fail-fast

# Verify-only mode (dry-run, no actions)
python demos/run_demo.py --demo full_semester_workflow.json --verify-only
```

### Flag Behavior

| Flag               | Purpose               | Behavior                                                 |
| ------------------ | --------------------- | -------------------------------------------------------- |
| `--demo <file>`    | Specify demo JSON     | Required                                                 |
| `--auto`           | Automated mode        | No pauses, executes automated actions, no human required |
| `--start-step <N>` | Resume from step N    | Skip steps 1 through N-1                                 |
| `--fail-fast`      | Exit on first failure | Stop immediately when any verification fails             |
| `--verify-only`    | Dry-run mode          | Show steps, run verifications, don't execute actions     |

## Execution Modes

### Automated Mode (`--auto`)

**Purpose**: Agent iterates on demo until it works flawlessly end-to-end

**Behavior**:

- Execute `pre_commands` automatically
- Perform automated UI actions (browser automation via existing browser tools)
- Execute `post_commands` automatically
- Show step info + results
- **No pauses** - runs straight through
- If verification fails: stop and report error (especially with `--fail-fast`)

**Use Case**: Development/validation by AI agent

### Human-Guided Mode (Default)

**Purpose**: Human presenter gives the demo

**Behavior**:

- Execute `pre_commands` automatically (with output explaining what/why)
- Show **explicit UI instructions** for human to follow
- Show **clickable URLs** to navigate
- Show **inputs/values** to enter
- Show **expected results** to look for
- **Wait for Enter** before proceeding to next step
- Execute `post_commands` automatically (with verification output)
- Pressing Enter repeatedly = same effect as `--auto` (if human already did UI actions)

**Use Case**: Live demo presentation

### Example Output (Human Mode)

```
================================================================================
[Step 2] Edit Biology Program
================================================================================

📋 Purpose: Update program description for accreditation cycle

🔧 Pre-Step Commands:
  ✓ Getting Biology program ID...
    $ sqlite3 course_records_dev.db "SELECT program_id FROM programs..."
    Result: abc-123-def
    (Captured as {{biology_program_id}})

📖 Instructions:
  1. Click 'Programs' link below
  2. Find 'Biological Sciences' in the table
  3. Click the Edit button (pencil icon)
  4. Change description to: "Primary focus for Fall 2024 Accreditation Cycle"
  5. Click Save

🔗 Quick Links:
  → Programs Page: http://localhost:3001/programs [Click to open]

📝 Inputs for this step:
  • Program Name: Biological Sciences
  • New Description: Primary focus for Fall 2024 Accreditation Cycle

✅ Expected Results:
  • Success toast appears
  • Program description updated in table
  • Modal closes automatically

🔍 Post-Step Verification:
  ✓ Verifying description was updated...
    $ sqlite3 course_records_dev.db "SELECT description FROM programs..."
    Expected: Contains "Fall 2024 Accreditation"
    Actual: "Primary focus for Fall 2024 Accreditation Cycle"
    ✅ PASS

📸 Artifacts captured: 02_program_edit_modal.png, 02_program_updated.png

Press Enter to continue to next step...
```

## Implementation Tasks

### Phase 1: Setup & Structure ✅

- [x] Create `demos/` directory
- [x] Write `demos/IMPLEMENTATION_PLAN.md` (this file)
- [ ] Write `demos/README.md` (how to create and run demos)
- [ ] Move `docs/workflow-walkthroughs/scripts/run_demo.py` → `demos/run_demo.py`
- [ ] Create `demos/artifacts/` directory structure

### Phase 2: JSON Conversion

- [ ] Convert `planning/demo_walkthrough.md` → `demos/full_semester_workflow.json`
  - [ ] Phase 1 - Environment Setup (steps 1-3)
  - [ ] Phase 2 - Institution & Program Config (steps 4-10)
  - [ ] Phase 3 - Faculty & Assessment (steps 11-15)
  - [ ] Phase 4 - Audit & Dashboards (steps 16-20)
- [ ] Integrate `scripts/advance_demo.py` commands as pre_commands where appropriate
- [ ] Add verification commands (database checks, API checks) as post_commands

### Phase 3: Enhance run_demo.py

- [ ] Add JSON parsing (replace markdown parsing)
- [ ] Implement `--auto` flag (automated execution)
- [ ] Implement `--start-step` flag
- [ ] Implement `--fail-fast` flag
- [ ] Implement `--verify-only` flag
- [ ] Add clickable URL rendering
- [ ] Add pre_command execution with output
- [ ] Add post_command verification
- [ ] Add variable capture/substitution (e.g., `{{biology_program_id}}`)
- [ ] Add artifact collection (screenshots, logs)
- [ ] Integrate with browser tools for automated actions

### Phase 4: Validation

- [ ] Run `--verify-only` to test JSON structure
- [ ] Run `--auto --fail-fast` to validate automated flow
- [ ] Iterate on failing steps using `--start-step` + `--fail-fast`
- [ ] Get full demo working end-to-end in automated mode
- [ ] Run in human mode (without --auto) to verify instructions are clear

### Phase 5: Cleanup & Documentation

- [ ] Archive old files:
  - [ ] `planning/demo_walkthrough.md` → archived or deleted
  - [ ] `planning/demo-walkthrough-checklist.md` → archived or deleted
  - [ ] `docs/workflow-walkthroughs/scripts/validate_demo.py` → review/archive
- [ ] Update `STATUS.md` to reflect new demo system
- [ ] Update root `README.md` to mention demo system
- [ ] Write `demos/README.md` with instructions for creating new demos

## Success Criteria

✅ **Single JSON file** defines entire demo  
✅ **Automated mode** runs flawlessly start-to-finish without human intervention  
✅ **Human mode** provides clear, actionable instructions at each step  
✅ **Fast iteration** via `--start-step` and `--fail-fast` for development  
✅ **Deterministic** - same steps, same order, every time  
✅ **Maintainable** - easy to add new steps or modify existing ones

## Timeline

- **Phase 1-2**: 1-2 hours (structure + JSON conversion)
- **Phase 3**: 2-3 hours (enhance run_demo.py)
- **Phase 4**: 2-4 hours (validation + iteration)
- **Phase 5**: 1 hour (cleanup + docs)

**Total Estimate**: 6-10 hours of focused work

## Future Enhancements (Post-MVP)

- [ ] Multiple demo files (`quick_feature_tour.json`, `single_term_audit.json`)
- [ ] Demo library/catalog in `demos/README.md`
- [ ] Record mode (capture a manual demo run into JSON)
- [ ] Diff mode (compare two demo runs)
- [ ] HTML report generation
- [ ] Video recording integration

## Notes

- Reuse existing work: walkthrough.md has all the steps, run_demo.py has orchestration logic
- Browser automation via existing `mcp_cursor-ide-browser_*` tools
- Keep demos client-agnostic (not "CEI demo", just "demo")
- Variable substitution enables dynamic IDs (e.g., course_id from previous step)
