# Script Output Standards 📋

## Core Principle

**All automation scripts MUST provide concise stdout summaries and write detailed output to log files.**

This enables:
- Human oversight via readable summaries
- AI analysis via structured log files  
- No output suppression (piping/filtering)
- Audit trails for debugging

---

## Standard Format

### Required Behavior

1. **Summary to stdout** (≤50 lines)
   - Progress indicators
   - Final status (✅/❌)
   - Key metrics (counts, duration, failures)
   - **Path to full log file**

2. **Details to file** (`logs/[script_name].log` or `logs/[script_name].txt`)
   - Complete execution log
   - All warnings/errors with context
   - Debug information
   - Timestamps for performance analysis

3. **Exit codes**
   - `0`: Success (all checks passed)
   - `1`: Validation failed (expected failure state)
   - `2`: Runtime error (unexpected failure)

---

## Example Output

```bash
🚀 Running SonarCloud Analysis...

✅ Configuration validated (0.2s)
✅ Source code scanned (12.3s)
⚠️  Coverage analysis (3 warnings)
❌ Quality gate failed (2.1s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Analysis Summary:
  Issues Found: 12 total
    • Critical: 2 ❌
    • Major: 5 ⚠️
    • Minor: 5 ℹ️
  
  Coverage: 78.5% (target: 80%)
  Duration: 17.6s

📁 Full report: logs/sonarcloud_issues.txt
💡 Quick check: grep "Critical" logs/sonarcloud_issues.txt
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Exit code: 1
```

---

## Agent Behavior Protocol

### When Running Scripts

✅ **DO:**
- Run scripts without modification (no piping, filtering, or redirection)
- Show the user the complete stdout summary
- Read log files for detailed analysis when needed
- Report: "See logs/[file].txt for details" if investigating

❌ **DON'T:**
- Pipe script output (`script.py | grep`, `script.py 2>&1 | tail`)
- Filter or suppress output
- Assume user doesn't need to see results
- Redirect to /dev/null or hide errors

### When Scripts Violate Standards

**If a script outputs >100 lines to stdout:**

1. **Note the violation** (briefly, 1 line)
2. **Quick fix** (5-10 minutes):
   - Add `--quiet` or `--summary` flag if missing
   - Redirect verbose output to log file
   - Print concise summary with log path
3. **Commit as part of current work**
4. **Move on** - don't block main task

**Example commit:**
```
fix(scripts): add summary mode to seed_db.py

- Redirect verbose logging to logs/seed_output.txt  
- Print concise summary (<30 lines) with log path
- Follows script output standards
```

---

## Standard Log Locations

**Convention:** `logs/[script_purpose].txt` or `logs/[script_purpose].log`

**Examples:**
- `ship_it.py --checks sonar` → `logs/sonarcloud_issues.txt`
- `ship_it.py --checks coverage` → `logs/coverage_report.txt`
- `scripts/seed_db.py` → `logs/seed_output.txt`
- `run_uat.sh` → `logs/test_server.log`

**Why this structure:**
- Predictable locations for debugging
- Separate logs per concern (not one mega-file)
- Easy to grep/analyze specific subsystems
- .gitignore already excludes logs/

---

## Rationale: Human-AI Collaboration

### The Problem This Solves

**Without this standard:**
- AI suppresses output to "save tokens" → User loses visibility
- Scripts become black boxes → Hard to debug failures  
- Output piping causes hangs → Wastes time
- No audit trail → Can't investigate later

**With this standard:**
- User sees summaries → Maintains oversight
- AI reads log files → Gets detailed analysis
- No output manipulation → Scripts run reliably
- Structured logs → Easy post-mortem debugging

### The Compromise

**User needs:** Visibility into what's happening (red-flag detection)  
**AI needs:** Detailed output for analysis (pattern matching)  
**Solution:** Summary for humans, logs for machines

---

## Migration Path

**Existing scripts that need updates:**
- `scripts/seed_db.py` - Currently too verbose (30+ lines of CREATE statements)
- Future validation scripts should follow this from the start

**Scripts that already comply:**
- `ship_it.py` - Good summary + writes to logs/
- `run_uat.sh` - Concise output + logs to logs/test_server.log

---

## Review Checklist

**Before committing a new script, verify:**
- [ ] Stdout output ≤50 lines for typical runs
- [ ] Detailed logs written to `logs/[name].txt`
- [ ] Summary includes log file path
- [ ] Exit codes meaningful (0/1/2)
- [ ] Progress indicators for long operations
- [ ] Error messages actionable

---

**Last Updated:** 2025-10-04  
**Status:** Active - enforce for all new scripts, fix existing opportunistically

