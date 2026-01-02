---
trigger: always_on
description: "Antigravity rule"
---
# Course Record Updater Project Rules 📚

## 🚨 CRITICAL: Quality Gate Command Protocol 🚨

### ABSOLUTE PROHIBITION: NEVER PIPE OR MODIFY ship_it.py COMMANDS

**BEFORE running ANY ship_it.py command, STOP and verify:**

✅ **ALLOWED**:
```bash
python scripts/ship_it.py --checks sonar
python scripts/ship_it.py --checks coverage
```

❌ **ABSOLUTELY FORBIDDEN** (causes immediate rule violation):
```bash
# NO piping
python scripts/ship_it.py --checks sonar | grep "Coverage"
python scripts/ship_it.py --checks sonar 2>&1 | tail -100

# NO redirection  
python scripts/ship_it.py --checks sonar > output.txt

# NO environment manipulation before command
rm -rf .scannerwork && python scripts/ship_it.py --checks sonar

# NO combining with other commands
cd /tmp && python scripts/ship_it.py --checks sonar
```

**WHY THIS RULE EXISTS**:
1. Script outputs are carefully designed and complete
2. Results are auto-saved to files (logs/sonarcloud_issues.txt, etc.)
3. Piping breaks user experience and hides context
4. If cleanup is needed, add it to the script itself

**ENFORCEMENT**: If you catch yourself typing `|`, `>`, `&&`, or `rm -rf` before ship_it.py - STOP IMMEDIATELY and reconsider.

**NO EXCEPTIONS, NO EXCUSES, NO "BUT IT WOULD BE BETTER IF..."**

---

## Greenfield Project Philosophy

### 🚀 NO BACKWARD COMPATIBILITY REQUIRED

**🔑 CRITICAL PROJECT PRINCIPLE**: This is a greenfield, unreleased project. There is NEVER a reason to maintain backward compatibility until we officially onboard CEI in a few months.

**✅ CORRECT APPROACH**: Always choose clean refactoring over compatibility layers:
- **Wholesale replacement** of old approaches with new ones
- **Complete removal** of deprecated patterns
- **Clean slate** implementations without legacy baggage

**❌ AVOID COMPATIBILITY MINDSET**:
- "For backward compatibility..." comments
- Deprecated method maintenance
- Legacy parameter support
- Migration scripts for unreleased features

**🎯 REAL-WORLD EXAMPLES FROM OUR JOURNEY**:

1. **ImportService Institution Refactor**:
   - ❌ Wrong: Keep `cei_institution_id` property + add `institution_id` for "compatibility"
   - ✅ Right: Replace `cei_institution_id` entirely with `institution_id`

2. **Test Class Renaming**:
   - ❌ Wrong: Keep `TestFinalCoverage` classes and add new logical names
   - ✅ Right: Delete coverage-chasing classes, merge tests into logical groups

3. **Database Schema Changes**:
   - ❌ Wrong: Add migration scripts and maintain old column names
   - ✅ Right: Nuke the database, implement clean schema

4. **API Endpoint Updates**:
   - ❌ Wrong: Version endpoints (`/api/v1/old`, `/api/v2/new`)
   - ✅ Right: Update endpoints in place, no versioning needed

**🔥 NUCLEAR OPTION AVAILABLE**: We can nuke the database at will. Use this freedom to implement clean solutions.

## Quality Gate Command Protocol

### 🚨 NEVER MODIFY ship_it.py COMMANDS 🚨

**🔑 CRITICAL RULE**: ALWAYS run `python scripts/ship_it.py --checks <check_name>` commands WITHOUT any piping, redirection, grep, tail, or other modifications.

**✅ CORRECT**:
```bash
python scripts/ship_it.py --checks sonar
python scripts/ship_it.py --checks coverage
python scripts/ship_it.py --checks tests
```

**❌ FORBIDDEN**:
```bash
python scripts/ship_it.py --checks sonar 2>&1 | tail -50
python scripts/ship_it.py --checks sonar | grep "Coverage"
python scripts/ship_it.py --checks sonar 2>&1 | tee /tmp/output.txt
```

**Why This Rule Exists**:
1. The script is designed to provide ALL necessary information in its output
2. Results are automatically written to local files (see logs/ directory)
3. The script's exit code indicates success/failure
4. Piping/filtering output breaks the user experience and hides important context
5. File paths to detailed reports are printed at the end

**Where to Find Detailed Information**:
- SonarCloud issues: `logs/sonarcloud_issues.txt`
- Coverage analysis: `logs/coverage_report.txt`
- PR coverage gaps: `logs/pr_coverage_gaps.txt`
- JavaScript coverage: `coverage/lcov-report/index.html`

**If You Need to Debug**:
- Read the log files mentioned in the script output
- Check `logs/application.log` for detailed execution logs
- Run the underlying command directly (e.g., `sonar-scanner`)

**NO EXCEPTIONS**: Do not argue about why piping/filtering "would be better". The rule exists for good reasons.

## Institution-Agnostic Design

### 🏢 CEI IS JUST ANOTHER CUSTOMER

**🔑 DESIGN PRINCIPLE**: Treat CEI as "just another customer" - the only special aspect is that it's the first to get a custom data import adapter.

**✅ CORRECT APPROACH**:
- Generic service classes that accept `institution_id` parameters
- Institution-specific logic in dedicated adapters
- No hardcoded references to "CEI" in generic code
- Conventional data formats (not CEI-specific formats)

**❌ AVOID CEI-CENTRIC THINKING**:
- Hardcoded CEI institution IDs in service classes
- CEI-specific methods in generic models (`get_cei_institution_id()`)
- CEI-specific data formats in shared code (`parse_cei_term()`)
- Comments assuming CEI is the only customer

**🎯 IMPLEMENTATION GUIDELINES**:
- Move CEI-specific parsing to CEI adapter
- Use conventional term formats (FA2024, not 2024FA)
- Generic institution management in database services
- Realistic test data (not "test-institution-id")

## SonarCloud Quality & Coverage Workflow

### 🎯 CRITICAL: The "Complete Grocery List" Protocol

**Core Principle:** Work from the COMPLETE list of Sonar issues, not incrementally. Line numbers will shift as you work, refactors will obviate some issues, 100% completion may not be achievable—this is all expected and acceptable.

**✅ CORRECT WORKFLOW:**

**Step 1: Generate the Complete Grocery List** (once per iteration):
```bash
python scripts/ship_it.py --checks sonar-analyze  # Upload analysis (~90s)
python scripts/ship_it.py --checks sonar-status   # Fetch results (~5s)
```

This automatically writes THREE complete lists to disk:
- `logs/sonarcloud_issues.txt` - Code smells, security hotspots, bugs
- `logs/pr_coverage_gaps.txt` - Uncovered NEW lines (ranked by file)
- `logs/sonarcloud_duplications.txt` - Duplication blocks

**Step 2: Read ALL Three Lists**:
```bash
cat logs/sonarcloud_issues.txt
cat logs/pr_coverage_gaps.txt
cat logs/sonarcloud_duplications.txt
```

**Step 3: Create Internal TODO List** (concept-based, NOT line-based):

Group issues by CONCEPT/IMPACT, not by file or line number. Examples:
- "Code smells: Cognitive complexity" (even if across 5 files)
- "Code smells: Unused parameters/return values"
- "Security: Pin GitHub Actions to commit SHAs"
- "Coverage: Top 5 uncovered files (audit_clo.js, offeringManagement.js, app.py, ...)"
- "Duplication: Extract shared dropdown/button helpers from JS management files"

**Why concept-based?**
- Line numbers shift as you make changes
- Refactoring one area often fixes related issues elsewhere
- Easier to maintain mental model while working
- More resilient to the "building the car while driving it" problem

**Step 4: Work Through TODO List Sequentially**:
- Put on blinders and fix items one concept at a time
- Accept that line numbers will shift
- Accept that some fixes will obviate others (e.g., refactoring a function removes 3 code smell issues)
- **DO NOT re-run Sonar** until you've completed your entire TODO list (or hit a natural stopping point)

**Step 5: Commit Everything at Once**:
```bash
git add -A
git commit -m "fix: address Sonar issues batch

- [list conceptual fixes, not line numbers]
- Cognitive complexity: refactored X, Y, Z
- Unused params: removed from A, B, C  
- Coverage: added tests for top 5 files
- Duplication: extracted shared helpers
"
```

**Step 6: Validate** (ONLY after commit):
```bash
python scripts/ship_it.py --checks sonar-analyze
python scripts/ship_it.py --checks sonar-status
```

**Step 7: Iterate** (only if significant issues remain):
- Read the UPDATED reports (they're regenerated automatically)
- Create new TODO list from the new reports
- Repeat steps 3-6

### Key Mindset Shifts

**❌ OLD (incremental, causes churn)**:
- Fix issue on line 478
- Re-run Sonar to see if it worked
- Fix issue on line 482  
- Re-run Sonar again
- Fix issue on line 490
- Re-run Sonar again
- (Wasted API calls, line number churn, mental overhead)

**✅ NEW (batch/concept-based)**:
- Read complete lists from disk
- Fix ALL cognitive complexity issues (5 files)
- Fix ALL unused parameters (3 files)
- Add tests for top 5 uncovered files (100+ lines of coverage)
- Extract ALL duplicate helpers (3 JS files)
- THEN commit and validate once
- (Efficient, resilient to line number changes, clear progress)

### Acceptance Criteria

**Success looks like:**
- Quality gate passes OR
- All actionable issues addressed (remaining issues documented with rationale in commit message)

**Progress tracking:**
- Use internal TODO list (concept-based)
- Cross off concepts as completed, not individual line numbers
- Work systematically through the list without checking interim Sonar results

### Common Pitfalls to Avoid

**❌ WRONG:**
- "Let me re-run Sonar to see if my fix worked" (trust the fix, validate at the end)
- "I'll just fix these 2 issues and commit" (work through the complete list)
- "Line 478 is still uncovered" (line numbers shift; focus on concepts)
- Grepping live Sonar output instead of reading saved reports

**✅ RIGHT:**
- Read all three reports from disk at the start
- Build concept-based TODO list
- Work through entire list
- Commit once at the end
- Validate to get UPDATED reports
- Iterate if needed

## PR Validation Checklist Workflow

### 🎯 CRITICAL: Iterative Checklist Protocol

**🔑 WORKFLOW PRINCIPLE**: The PR validation report generates a checklist. You MUST iterate on this checklist, checking items off as you fix them. Do NOT push until ALL items are checked off.

**✅ CORRECT WORKFLOW:**

1. **Run PR validation ONCE** (generates report):
   ```bash
   python scripts/ship_it.py --validation-type PR
   ```

2. **Review the checklist** in `logs/pr_{PR}_issues_report_{commit}.md`

3. **Work through items systematically**:
   ```bash
   # Mark item as in-progress when you start working on it
   python scripts/update_pr_checklist.py --in-progress "Fix failing CI job: e2e-tests"
   
   # Mark item as completed when done
   python scripts/update_pr_checklist.py --complete "Fix failing CI job: e2e-tests"
   
   # For PR comments, reply and resolve as you commit:
   python scripts/update_pr_checklist.py --complete "Address comment from ScienceIsNeato" --reply-to-comment --thread-id PRRT_xxx
   # This will reply with "Fixed in commit <sha>" and auto-resolve the thread
   
   # Check status anytime
   python scripts/update_pr_checklist.py --status
   ```

4. **Reply to PR comments immediately when committing fixes**:
   - Use `--reply-to-comment` flag with `--complete` to reply and resolve threads
   - The reply will reference the current commit SHA automatically
   - This eliminates the need to "reserve" comments until after push
   - Comments are resolved synchronously with local commits

5. **DO NOT re-run PR validation** until ALL items are completed and you're ready to push

6. **DO NOT push** until checklist shows all items completed

7. **After pushing**, re-run PR validation to generate new report for next iteration

**❌ FORBIDDEN WORKFLOW:**
- Re-running PR validation before addressing all items
- Pushing before all checklist items are completed
- Ignoring the checklist and working ad-hoc
- Not tracking progress through the checklist

**📋 Checklist Management:**
- Use `scripts/update_pr_checklist.py` to track progress
- Check items off as you complete them
- Review checklist status regularly: `python scripts/update_pr_checklist.py --status`
- The checklist state persists across sessions (stored in `logs/pr_{PR}_checklist_state_{commit}.json`)

**🚨 ENFORCEMENT**: Before pushing, verify checklist is complete:
```bash
python scripts/update_pr_checklist.py --status
# Should show: ✅ Completed: X, ⏳ Pending: 0
```

**NO EXCEPTIONS**: The checklist exists to prevent the "20 rounds of back and forth and 100+ commits" problem. Use it.