# Demo System Quick Start

## Prerequisites

1. **Run from project root** - The demo expects to be executed from `/path/to/course_record_updater`
2. **Virtual environment activated** - Source `venv/bin/activate` before running
3. **Environment variables loaded** - Source `.envrc` for required config
4. **Server running** - Flask app should be running on port 3001 (setup commands handle this)

## Running the Demo

### Automated Mode (Full Automation)

```bash
cd /path/to/course_record_updater
source venv/bin/activate
cd demos
python run_demo.py --demo full_semester_workflow.json --auto
```

This runs the entire demo automatically without any human interaction. Perfect for validation and testing.

### Human-Guided Mode (Presenter Mode)

```bash
cd /path/to/course_record_updater
source venv/bin/activate
cd demos
python run_demo.py --demo full_semester_workflow.json
```

This shows step-by-step instructions for a human presenter. Press Enter to advance to the next step.

### Development Mode (Fast Iteration)

```bash
# Start from a specific step and exit on first failure
cd demos
python run_demo.py --demo full_semester_workflow.json --auto --start-step 11 --fail-fast
```

Perfect for debugging a specific step without running the entire demo.

## What Gets Automated

The demo automates **8 API-actionable steps**:

- Step 1: Health check (api_check)
- Step 2, 7, 12: Login (api_post)
- Step 3: Edit program (api_put)
- Step 5: Duplicate course (api_post)
- Step 6, 10: Logout (api_post)
- Step 9: Assessment form (api_put)
- Step 11: Advance demo state (run_command)

The remaining **11 steps** are UI navigation for human presenters.

## Common Issues

### Issue: "No such file or directory: venv/bin/activate"

**Solution**: Run from the project root, not from `demos/` directory.

### Issue: "Connection refused" on API calls

**Solution**: Server isn't running. The setup commands should start it, but you can manually run `./restart_server.sh dev`.

### Issue: "Database locked" or "No such table"

**Solution**: Database needs to be seeded. Run `python scripts/seed_db.py --demo --clear --env dev`.

### Issue: UUIDs don't match in verification commands

**Solution**: This is expected! UUIDs are generated dynamically. The demo captures them via `capture_output_as` and substitutes them with `{{variable_name}}` syntax.

## Success Indicators

When the demo completes successfully, you'll see:

```
================================================================================
Demo Complete!
================================================================================

You've successfully completed the demo.

Key Takeaways:
  • Natural keys keep sessions stable across reseeds
  • Duplicate button accelerates version 2 courses
  • Email previews land in logs/email.log
  • Audit approvals instantly feed dashboard KPIs

Artifacts saved to: demos/artifacts/full_semester_workflow_TIMESTAMP
```

All API actions should show `✓ Success: 200` (or 201 for creation).

## Architecture Notes

### API-First Design

The demo follows the principle: **"Everything the UI can do, the API can do."**

This means:

- UI navigation steps (4, 8, 13-19) are for human context only
- All actual work happens via API calls (steps 2, 3, 5, 6, 7, 9, 10, 12)
- You can run the demo with `--auto` and get the same data state as a human would

### Variable Capture & Substitution

Dynamic IDs are captured from database queries:

```json
{
  "command": "sqlite3 ... WHERE course_number='BIOL-101'",
  "capture_output_as": "course_id"
}
```

Then substituted in API calls:

```json
{
  "endpoint": "/api/management/courses/{{course_id}}/duplicate"
}
```

This allows the demo to work even when UUIDs change between database reseeds.

### Session Management

The demo uses `requests.Session()` to maintain cookies across API calls:

- Login at step 2 → session persists
- All subsequent API calls use the same session
- Logout at step 6 → session cleared
- New login at step 7 → new session

### CSRF Protection

All API calls include CSRF tokens:

1. Token fetched from `/login` page
2. Included in `X-CSRFToken` header
3. Follows the same pattern as integration tests

## Next Steps

For more details on the demo system architecture, see `IMPLEMENTATION_PLAN.md`.

To create a new demo, copy `full_semester_workflow.json` and modify the steps.
