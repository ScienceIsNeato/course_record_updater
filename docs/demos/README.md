# Demo System

Deterministic, automated demo orchestration system for showcasing LoopCloser workflows.

## Quick Start

```bash
# Run demo from repository root (human-guided mode by default)
python demos/run_demo.py --demo full_semester_workflow.json

# Automated validation (no pauses, fail on first issue)
python demos/run_demo.py --demo full_semester_workflow.json --auto --fail-fast

# Iterate on specific step with fast feedback
python demos/run_demo.py --demo full_semester_workflow.json --auto --start-step 15 --fail-fast
```

## Available Demos

| Demo | Duration | Description |
|------|----------|-------------|
| `full_semester_workflow.json` | 20 min | Complete semester lifecycle from setup through audit |

## Execution Modes

### Human-Guided Mode (Default)

For live presentations. The script:
- Executes pre-commands automatically (setup, data verification)
- Shows clear instructions for UI interactions
- Provides clickable URLs for navigation
- Displays expected results to verify
- Waits for Enter key before proceeding
- Executes post-commands automatically (verification)

**Use Case**: You're presenting the demo to stakeholders

### Automated Mode (`--auto`)

For validation and iteration. The script:
- Executes all commands automatically
- Performs browser automation for UI steps
- Runs straight through without pauses
- Reports pass/fail for each step

**Use Case**: AI agent validates the demo works end-to-end

## CLI Reference

```bash
python demos/run_demo.py --demo <file> [OPTIONS]
```

### Required Arguments

- `--demo <file>`: Path to demo JSON file

### Optional Flags

- `--auto`: Run in automated mode (no pauses, browser automation)
- `--start-step <N>`: Resume from step N (skip steps 1 through N-1)
- `--fail-fast`: Exit immediately on first verification failure
- `--verify-only`: Dry-run mode (show steps, run verifications, don't execute actions)

### Common Workflows

**Full validation run:**
```bash
python demos/run_demo.py --demo full_semester_workflow.json --auto --fail-fast
```

**Iterate on failing step:**
```bash
# Step 37 is failing, iterate quickly
python demos/run_demo.py --demo full_semester_workflow.json --auto --start-step 37 --fail-fast
```

**Preview demo without executing:**
```bash
python demos/run_demo.py --demo full_semester_workflow.json --verify-only
```

**Human presentation:**
```bash
python demos/run_demo.py --demo full_semester_workflow.json
# Press Enter to advance through each step
```

## Creating New Demos

### 1. Create JSON File

Follow the naming convention: `{descriptive_name}.json`

Example: `single_term_audit.json`, `quick_feature_tour.json`

### 2. Define Demo Structure

```json
{
  "demo_name": "Your Demo Name",
  "demo_id": "your_demo_name",
  "version": "1.0",
  "description": "What this demo shows",
  "estimated_duration_minutes": 15,
  "environment": {
    "setup_commands": [
      "python scripts/seed_db.py --demo --clear --env dev",
      "./restart_server.sh dev"
    ],
    "base_url": "http://localhost:3001"
  },
  "steps": [...]
}
```

### 3. Define Steps

Each step should have:

```json
{
  "step_number": 1,
  "phase": "Setup",
  "name": "Short step name",
  "purpose": "Why we're doing this step",
  
  "pre_commands": [
    {
      "command": "sqlite3 db.db 'SELECT COUNT(*) FROM users'",
      "purpose": "Verify users exist",
      "expected_output": "5"
    }
  ],
  
  "instructions": {
    "human": "Click X, then Y, then Z",
    "automated": {
      "action": "browser_click",
      "element": "Login Button"
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
    "email": "user@example.com",
    "password": "pass123"
  },
  
  "expected_results": [
    "Dashboard loads",
    "User name appears in header"
  ],
  
  "post_commands": [
    {
      "command": "curl -s http://localhost:3001/api/me",
      "purpose": "Verify session established",
      "expected_output_contains": "user@example.com"
    }
  ],
  
  "artifacts": {
    "screenshots": ["01_dashboard.png"],
    "logs": []
  },
  
  "pause_for_human": true
}
```

### 4. Test Your Demo

```bash
# Validate structure
python run_demo.py --demo your_demo.json --verify-only

# Run automated validation
python run_demo.py --demo your_demo.json --auto --fail-fast

# Test human experience
python run_demo.py --demo your_demo.json
```

## Artifacts

During demo execution, artifacts are collected in:

```
demos/artifacts/{demo_id}_{timestamp}/
├── screenshots/
├── logs/
└── exports/
```

Screenshots are automatically captured at each step that specifies them.

## Troubleshooting

### Demo fails at step N

Use `--start-step` to resume from that step:
```bash
python run_demo.py --demo full_semester_workflow.json --auto --start-step N --fail-fast
```

### Need to see what's happening

Run without `--auto` to step through manually and observe each action.

### Verification commands failing

Check the expected outputs in the JSON. Use `--verify-only` to see what each verification expects.

### Browser automation not working

Ensure the browser tab integration is connected and the server is running.

## Best Practices

1. **Keep steps atomic**: Each step should do one logical thing
2. **Verify everything**: Add post_commands to verify the step worked
3. **Clear instructions**: Write human instructions as if for someone unfamiliar with the app
4. **Meaningful purposes**: Explain *why* each step matters
5. **Capture artifacts**: Screenshot key moments for documentation
6. **Test both modes**: Validate with `--auto`, present without it

## Demo Philosophy

- **Deterministic**: Same steps, same order, every time
- **Client-agnostic**: Demos show generic workflows, not customer-specific data
- **Dual-purpose**: Works for both automated validation and human presentation
- **Fast iteration**: `--start-step` + `--fail-fast` enable rapid development

## Contributing

When adding a new demo:
1. Create the JSON file in `demos/`
2. Test thoroughly with `--auto --fail-fast`
3. Run through manually to verify instructions are clear
4. Add entry to the "Available Demos" table above
5. Commit with message: `demo: add {demo_name}`

