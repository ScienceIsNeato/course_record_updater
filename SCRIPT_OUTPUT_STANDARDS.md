# Script Output Standards 📋

**Rule:** Scripts output ≤50 lines to stdout + write full logs to `logs/[name].txt`

**Why:** User needs visibility (red-flag detection), AI needs details (analysis), no piping (reliability).

## Format

**Stdout (≤50 lines):**
- Progress indicators  
- Status (✅/❌) + key metrics
- **Log file path**

**Logfile (`logs/[name].txt`):**
- Complete output
- Warnings/errors with context
- Debug info + timestamps

**Exit codes:** 0=success, 1=validation failed, 2=runtime error

## Agent Protocol

**DO:** Run scripts unmodified, show user full stdout, read logs for analysis  
**DON'T:** Pipe, filter, suppress, or redirect script output  

**If script outputs >100 lines:** Note violation, fix opportunistically (add summary mode), commit with current work

## Log Locations

`logs/sonarcloud_issues.txt`, `logs/coverage_report.txt`, `logs/seed_output.txt`, etc.

## Compliance

**Current:** `ship_it.py` ✅, `run_uat.sh` ✅  
**Needs update:** `seed_db.py` (too verbose)

