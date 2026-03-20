---
applyTo: "**"
---

# PR Closing Protocol 🔄

## Purpose

This protocol provides a systematic loop for closing PRs by addressing all feedback, CI failures, and quality issues in a coordinated manner with real-time comment resolution.

## The PR Closing Loop

### Step 1: Gather All Issues
**Run your project's PR validation check to collect everything wrong.**

This should generate:
- Comprehensive checklist of all issues
- Individual error logs for each failing check
- List of unresolved PR comments
- CI status summary

**Use slop-mop (preferred — projects that have it):**
```bash
# Run the myopia:ignored-feedback gate to get categorized, actionable report
sm swab -g myopia:ignored-feedback

# Read the generated report (path shown in output)
cat /path/to/pr_XX_comments_report.md

# The report includes:
# - Comments grouped by category (Security > Logic > Testing > Style)
# - AI agent workflow instructions
# - Copy-paste resolution commands per thread
```

**Manual gathering (last resort only):**
- Fetch PR comments via `gh api graphql`
- Check CI status via `gh pr checks`
- Run local quality gates

### Step 2: Create Comprehensive Plan & Resolve Stale Comments
**Develop a planning document that maps code changes to comments:**

**🔑 CRITICAL: While reviewing comments, immediately resolve any that are already fixed/outdated**

```bash
# For each unresolved comment, check:
# - Is this already fixed in recent commits?
# - Is the file/code mentioned no longer relevant?
# - Has the issue been obviated by other changes?

# If YES → Resolve it RIGHT NOW using sm buff resolve:
sm buff resolve <PR> PRRT_xxx --scenario no_longer_applicable --message "Already resolved in commit <SHA>: [explanation]"

# If the comment is a false positive or doesn't apply:
sm buff resolve <PR> PRRT_xxx --scenario invalid_with_explanation --message "[Why this doesn't apply]"
```

Create `/tmp/PR_{PR}_RESOLUTION_PLAN.md` containing:

```markdown
# PR #{PR} Resolution Plan

## Already Resolved (marked during planning)
- [x] Comment PRRT_aaa: "Database URL mismatch" 
      → Already fixed in commit e925af5 - RESOLVED ✅

## Unresolved Comments (need fixes)
- [ ] Comment PRRT_xxx: "CI seeds data into wrong database"
      → Fix: Update .github/workflows/quality-gate.yml lines 147, 154, 164, 184
      → Files: .github/workflows/quality-gate.yml
      
- [ ] Comment PRRT_yyy: "Session stores date as string but API expects datetime"
      → Fix: Update data/session/manager.py to store as datetime
      → Files: data/session/manager.py, tests for verification

## Failing CI Checks
- [ ] complexity: Refactor _get_current_term_from_db (complexity 17→8)
      → Fix: Extract helper methods
      → Files: src/app.py

## Quality Issues
- [ ] E2E tests: Program admin login fails
      → Fix: Use absolute database paths
      → Files: tests/e2e/conftest.py

## Resolution Mapping
Comment PRRT_xxx will be resolved by commits:
      - fix: standardize CI database to loopcloser_ci.db
  
Comment PRRT_yyy will be resolved by commits:
  - fix: store session dates as datetime objects
```

**Grouping Strategy:**
- **First**: Resolve any already-fixed comments (don't wait!)
- Group remaining by underlying concept (not file location)
- Identify which commits will address which comments
- Plan comment resolution messages for each commit

### Step 3: Commit Progress As You Go
**Work incrementally with small, focused commits:**

```bash
# Fix one issue or theme
git add <files>
git commit -m "fix: descriptive message

- What was fixed
- How it addresses the issue
- Reference to related PR comments if applicable"
```

**Key Principle:** Each commit should be atomic and pass quality gates.

### Step 4: Resolve Comments Immediately After Each Commit
**🔑 CRITICAL STEP - This is where the loop closes:**

After EACH successful commit that addresses a PR comment:

```bash
# Resolve the thread with sm buff resolve:
sm buff resolve <PR> PRRT_xxxxxxxxxxxx \
  --scenario fixed_in_code \
  --message "Fixed in commit $(git rev-parse HEAD | cut -c1-7). [Brief explanation of what was changed and how it addresses the comment]"
```

**Example:**
```bash
sm buff resolve 92 PRRT_kwDORBxXu85z0rB- \
  --scenario fixed_in_code \
  --message "Fixed in commit d541c5a. Updated E2E test setup to use absolute database paths (os.path.abspath) instead of relative paths."
```

**🚨 NEVER resolve threads with raw GraphQL — use `sm buff resolve` exclusively.**
See `sm_buff.instructions.md` / `sm_buff.mdc` for the full resolve reference (scenarios, flags, examples).

**Why Resolve Before Push:**
- Comment is addressed in local history
- Reviewer can see progress even before CI runs
- No risk of forgetting to resolve later
- Creates tight feedback loop

### Step 5: Push All Committed Work
**🔑 CRITICAL: ONLY push when ALL comments resolved AND all local checks pass**

**Pre-Push Verification Checklist:**
```bash
# 1. Check ALL comments resolved
sm buff verify <PR>
# Must show: all threads resolved

# 2. Verify local quality gates ALL pass
sm scour
# Must show: All checks passed

# 3. Final sanity check
git status  # Should be clean or only PR_X_RESOLUTION_PLAN.md uncommitted

# Or use finalize which does all three:
sm buff finalize <PR>
```

**ONLY push if:**
- ✅ ALL PR comments resolved (`sm buff verify` clean)
- ✅ ALL local quality checks pass
- ✅ Plan shows all items completed

**Why This Matters:**
- Each push triggers expensive CI ($$$)
- Pushing with unresolved comments = wasted CI cycle
- Goal: One final push that makes PR green, not iterative push/fix/push
- Exception: If CI reveals NEW issues we couldn't detect locally, then iterate

**If verification fails:**
- Go back to Step 3 (fix remaining issues)
- Do NOT push yet
- Complete ALL work first

**After verification passes:**
```bash
git push origin <branch-name>
```

### Step 6: Monitor CI Until Complete (AUTOMATED)
**🔑 CRITICAL: Use watch mode - it runs unattended until CI finishes (even if it takes hours/days)**

```bash
cd ${AGENT_HOME} && python3 cursor-rules/scripts/pr_status.py --watch ${PR_NUMBER}
```

**What watch mode does:**
- Polls CI status every 30 seconds automatically
- Shows progress updates when status changes
- **Keeps running unattended until ALL checks complete**
- **Automatically reports final results** (pass/fail with links)
- Works for minutes, hours, or days - keeps polling until done
- Ctrl+C to cancel if needed

**Why This Matters:**
- No manual checking needed
- No breaking stride to check "is CI done yet?"
- Script handles the waiting, you handle the fixing
- Clear signal when ready for next iteration

**Alternative (if watch script not available):**
```bash
gh pr checks ${PR_NUMBER}  # Manual check
gh run watch              # Watch single run
```

**Do NOT:**
- Manually refresh GitHub page every 5 minutes
- Stop working while waiting for CI
- Start fixing new issues before CI completes (wait for results first)

### Step 7: Check Completion Criteria
**When CI completes, evaluate:**

```bash
# Check thread resolution and CI status:
sm buff inspect <PR>

# Or targeted checks:
sm buff verify <PR>     # Threads resolved?
sm buff status <PR>     # CI passing?
```

**Completion Criteria:**
- ✅ All PR comments resolved (`sm buff verify` clean)
- ✅ All CI checks passing (`sm buff status` shows SUCCESS)

**If NOT complete:**
- New comments appeared → Go to Step 1
- CI checks failing → Go to Step 1
- Otherwise → Protocol complete! 🎉

## Automation Helpers

### Thread Resolution

`sm buff resolve` handles comment posting and thread resolution in a single command.
No custom scripts needed — `sm buff inspect` generates a command pack with pre-built
resolve commands for every unresolved thread.

```bash
# Run inspect to get the command pack:
sm buff inspect <PR>

# Read the generated commands:
cat .slopmop/buff-persistent-memory/pr-<PR>/loop-NNN/commands.sh

# Each command is a ready-to-run sm buff resolve call:
sm buff resolve <PR> PRRT_xxxx --scenario fixed_in_code --message "Updated database paths to absolute"
```
