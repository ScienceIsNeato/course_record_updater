---
applyTo: "**"
---

# LoopCloser Project Rules 📚

## 🔄 PR Closing Protocol

**CRITICAL**: When working on PRs, follow the checked-in **PR Closing Protocol** in `.github/instructions/pr_closing_protocol.instructions.md`.

**Key principle**: Resolve PR comments IMMEDIATELY after each commit that addresses them (Step 4).

**Integration with slop-mop:**
```bash
# Step 1: Gather all issues
sm scour

# Step 6: Monitor CI
gh pr checks <PR_NUMBER> --watch
```

If you need to follow one specific run instead of the PR-level summary:
```bash
gh run list --branch <HEAD_BRANCH> --limit 5
gh run watch <RUN_ID>
```

See `.github/instructions/pr_closing_protocol.instructions.md` for the complete 7-step loop.

---

## 🚨 CRITICAL: Quality Gate Command Protocol 🚨

### Default Validation Command

**WHEN USER ASKS TO**: validate, commit, get tests passing, check quality, etc.

**ALWAYS RUN**: 
```bash
sm swab
```

**EXCEPTIONS** (user must explicitly request):
- `sm scour` - for PR-level validation
- `sm swab -g <gate>` - for individual check types
- `sm swab -g e2e` - for E2E tests

**RULE**: If user doesn't specify a particular check, default to `sm swab`.

**PURPOSE**: Encourages model to rapidly iterate via the fail-fast and intentional ordering of quality gates.
- Dany mode for execution and fixes
- Brief switch to Tyrion mode in only two spots

**PROTOCOL**:
- run quality gate command above
- analyze failure in tyrion mode and come up with a plan to address it
- have Dany execute the plan
- if all checks green, done. If not, back to top

### slop-mop Command Reference

**Verbs (preferred):**
```bash
sm swab                  # Fast commit validation ← DEFAULT
sm scour                 # Full PR validation
```

**Individual gates (when needed):**
```bash
sm swab -g python-lint-format
sm swab -g python-tests
sm swab -g python-coverage
sm swab -g python-security-local
sm swab -g js-tests
sm swab -g e2e
```

**Help:**
```bash
sm help                  # List all gates
sm help commit           # Show what's in a profile
sm help python-coverage  # Gate-specific help
```

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

### 🎯 slop-mop is the source of truth

All quality gate commands should use slop-mop (`sm swab` / `sm scour`). The wrapper script `scripts/quality_gate.py` exists for CI compatibility but local development should use `sm` directly.

**Where to Find Detailed Information**:
- Coverage analysis: `htmlcov/index.html`
- Test results: `test-results.xml`
- Security reports: `bandit-report.json`, `safety-report.txt`

**If You Need to Debug**:
- Run `sm help <gate>` for gate-specific guidance
- Check `logs/application.log` for detailed execution logs

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

## Coverage Workflow

### 🎯 CRITICAL: Pay Down Coverage Debt Directly

**Core Principle:** Treat coverage failures as real test debt. Fix the failing tests, align the runner with the repo's real config, and add meaningful coverage to the highest-yield modules first.

**✅ CORRECT WORKFLOW:**

1. Run the failing gate directly:
```bash
sm swab -g overconfidence:untested-code.js --verbose
sm swab -g overconfidence:untested-code.py --verbose
```

2. Read the failing files and uncovered blocks.
3. Fix broken tests or mismatched test environments first.
4. Add meaningful tests to the biggest uncovered modules.
5. Re-run the specific gate, then return to `sm swab`.

**Mindset:**

- Prefer high-yield coverage wins over scattered micro-tests.
- Keep test code to the same standard as production code.
- Do not rely on time-budget skips to make commit validation pass.

## PR Validation Checklist Workflow

### 🎯 CRITICAL: Iterative Checklist Protocol

**🔑 WORKFLOW PRINCIPLE**: The PR validation generates a checklist. You MUST iterate on this checklist, checking items off as you fix them. Do NOT push until ALL items are checked off.

**✅ CORRECT WORKFLOW:**

1. **Run PR validation ONCE**:
   ```bash
   sm scour
   ```

2. **Review the checklist** in `logs/pr_{PR}_issues_report_{commit}.md`

3. **Work through items systematically**:
   ```bash
   # Inspect the current PR state and generate the command pack
   sm buff inspect <PR_NUMBER>

   # Resolve threads as you complete each fix
   sm buff resolve <PR_NUMBER> PRRT_xxx --scenario fixed_in_code --message "Fixed in commit <sha>. [brief explanation]"

   # Verify no unresolved review threads remain
   sm buff verify <PR_NUMBER>
   ```

4. **Reply to PR comments immediately when committing fixes**:
   - Use `sm buff resolve` immediately after each commit that addresses a thread
   - Include the current commit SHA in the reply message
   - This eliminates the need to "reserve" comments until after push
   - Comments are resolved synchronously with local commits

5. **DO NOT re-run PR validation** until ALL items are completed and you're ready to push

6. **DO NOT push** until checklist shows all items completed

7. **After pushing**, re-run PR validation to generate new report for next iteration

**❌ FORBIDDEN WORKFLOW:**
- Re-running PR validation before addressing all items
- Pushing before all checklist items are completed
- Ignoring the checklist and working ad-hoc
- Not tracking progress through the `sm buff` report and command pack

**📋 Checklist Management:**
- Use the generated `sm buff inspect` report and command pack as the source of truth
- Resolve threads with `sm buff resolve` as you complete them
- Review unresolved-thread status regularly with `sm buff verify <PR_NUMBER>`
- Re-run `sm buff inspect <PR_NUMBER>` after pushes to refresh the report

**🚨 ENFORCEMENT**: Before pushing, verify checklist is complete:
```bash
sm buff verify <PR_NUMBER>
# Should show no unresolved review threads
```

**NO EXCEPTIONS**: The checklist exists to prevent the "20 rounds of back and forth and 100+ commits" problem. Use it.