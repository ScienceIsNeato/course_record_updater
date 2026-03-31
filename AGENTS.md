# AI Agent Instructions

> **⚠️ AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY**
> 
> **Last Updated:** 2026-03-31 09:37:52 UTC  
> **Source:** `cursor-rules/.cursor/rules/`  
> **To modify:** Edit source files in `cursor-rules/.cursor/rules/*.mdc` and run `cursor-rules/build_agent_instructions.sh`

This file provides instructions and context for AI coding assistants working in this repository.

---

## Core Rules

# main

# Main Configuration

## Module Loading

### Rule Types
- Core Rules: Always active, apply to all contexts
- Project Rules: Activated based on current working directory

### Module Discovery
1. Load all core rule modules from `.cursor/rules/*.mdc`
2. Detect current project context from working directory name
3. Load matching project rules from `.cursor/rules/projects/*.mdc`

### Project Detection
- Extract project identifier from current working directory path
- Search project rules for matching module names
- Example: `/path/to/ganglia/src` activates `projects/ganglia.mdc`

### Module Structure
Each module must define:
```yaml
metadata:
  name: "Module Name"    # Human readable name
  emoji: "🔄"           # Unique emoji identifier
  type: "core|project"  # Module type
```

### Response Construction
- Start each response with "AI Rules: [active_emojis]"
- Collect emojis from all active modules
- Display emojis in order of module discovery
- No hardcoded emojis in responses

### File Organization
```
.cursor/rules/
├── main.mdc                # Main configuration
├── session_context.mdc     # Session context maintenance
├── response_format.mdc     # Response formatting rules
├── core_principles.mdc     # Core behavioral principles
├── path_management.mdc     # Path and file operations
├── development_workflow.mdc # Development practices
├── issue_reporting.mdc     # Issue handling
├── testing.mdc             # Testing protocols
└── projects/               # Project-specific rules
    ├── ganglia.mdc         # GANGLIA project rules
    ├── fogofdog_frontend.mdc # FogOfDog frontend rules
    └── apertus_task_guidelines.mdc # Comprehensive Apertus task guidelines
```

### Validation Rules
- All modules must have valid metadata
- No duplicate emoji identifiers
- No hardcoded emojis in rule content
- Project rules must match their filename
- Core rules must be generally applicable

### Required Core Modules
The following core modules must always be loaded:
- main.mdc (🎯): Core configuration
- session_context.mdc (🕒): Session history and context tracking
- factual_communication.mdc (🎯): Factual communication protocol

# core_principles

# Core Principles and Practices 🧠

## The Council (Counteracting Training Bias)

Models are trained to complete tasks, not to question whether tasks should exist. That makes them excellent at closing tickets and dangerous at long-term project health. The Council framework gives you a vocabulary for steering between execution and strategy.

**Default:** 🍷 Tyrion mode (strategic oversight)
**Override:** Set `DRACARYS=true` for 🔥 Dany mode (focused execution)

Prefix your reasoning with the appropriate emoji.

# development_workflow

# Development and Testing Workflow 🌳

## Quality Gate Principles

### 🚨 NEVER BYPASS QUALITY CHECKS 🚨

**ABSOLUTE PROHIBITION**: AI assistant is STRICTLY FORBIDDEN from using `--no-verify`, `--no-validate`, or any bypass flags. Zero tolerance policy.

**FORBIDDEN ACTIONS:**
- Quality gate bypass flags (`--no-verify`, `--no-validate`)
- Disabling linters, formatters, or tests
- Modifying configs to weaken standards
- Any circumvention of quality gates

**ENFORCEMENT**: No exceptions for any reason. Fix failing checks, never bypass. Work incrementally with commits that pass ALL gates.

### Function Length Refactoring Philosophy
Focus on **logical separation** over line reduction. Ask: "What concepts does this handle?" not "How to remove lines?"
- **Good**: Extract meaningful conceptual chunks (3 methods ~30-40 lines each)
- **Bad**: Artificial helpers just to reduce line count

### Core Principles
- **Address Root Causes**: Investigate, fix, validate (don't bypass)
- **Fail Fast**: Stop and fix at first failure before proceeding
- **Constant Correction**: Accept frequent small corrections vs chaotic cycles
- **Quality Purpose**: Linting, typing, coverage, security all serve valid purposes

### 🔬 Local Validation Before Commit (MANDATORY)

**🔑 CRITICAL RULE**: ALWAYS validate changes locally before committing. No exceptions.

**Validation Workflow:**
1. **Make Change**: Edit code, config, or documentation
2. **Test Locally**: Run relevant quality checks to verify the change works
3. **Verify Output**: Confirm expected behavior matches actual behavior
4. **Then Commit**: Only commit after local verification passes

**Examples:**

✅ **CORRECT Workflow:**
```bash
# 1. Make change to a source file
vim src/services/MyService.ts

# 2. Test the change locally
sm swab

# 3. Verify output shows expected behavior
# (e.g., all gates green, tests pass)

# 4. THEN commit
git add src/services/MyService.ts
git commit -m "fix: correct validation type"
```

❌ **WRONG Workflow (What NOT to do):**
```bash
# Make change
vim src/services/MyService.ts

# Immediately commit without testing
git add src/services/MyService.ts
git commit -m "fix: correct validation type"

# Hope it works in CI ← FORBIDDEN
```

**Why This Matters:**
- Catches errors before they reach CI (saves time and CI resources)
- Validates assumptions before publishing results
- Prevents breaking changes from being pushed
- Demonstrates due diligence and professionalism

**Scope of Local Testing:**
- **Config changes**: Run affected commands to verify behavior
- **Code changes**: Run affected tests and quality checks
- **Script changes**: Execute the script with relevant arguments
- **Documentation changes**: Preview rendered output if applicable

**NO EXCEPTIONS**: "I think it will work" is not validation. Run it locally, verify the output, then commit.

### Terminal Timeout Rules (AI Agents)

The `run_in_terminal` timeout parameter sends SIGINT when exceeded — it’s a kill switch, not an optimization.

| Command | Timeout | Why |
|---------|---------|-----|
| `git commit` | `timeout: 0` (always) | Pre-commit hooks run `sm swab` (~20s). Any non-zero timeout kills a healthy process mid-run. |
| `sm swab` / `sm scour` / `sm buff` | `timeout: 0` (always) | Validation must run to completion. Killing it mid-run creates stale `.slopmop/sm.lock`. |
| `git push` | `timeout: 0` | Network-bound, unpredictable. |
| Short read-only commands (`git status`, `ls`, `cat`) | 3000–5000ms | Safe to bound. |

**Anti-pattern**: Do NOT rationalize short timeouts with "it usually finishes in time." A 20-second process killed after 5 seconds didn’t time out — you killed it.

**If a stale lock appears**: `rm -f .slopmop/sm.lock` — but this should never happen with correct timeouts.

## Push Discipline 💰

GitHub Actions cost money. Slop-mop's workflow is how you protect the budget: `sm swab` validates locally before the push ever happens, `sm scour` catches everything swab doesn't, and `sm buff` tells you whether CI passed after you push. Follow the loop and pushes are safe by construction.

### When to Push (No Permission Needed)

Push is the natural next step when **all** of these are true:
1. `sm swab` passes locally (or pre-commit hook ran it)
2. All PR threads are resolved (`sm buff verify` clean)
3. You're on a feature branch (never main)

If the workflow says push, push. Then run `sm buff watch <PR>` to monitor CI and report back.

### 🚨 NEVER PUSH DIRECTLY TO MAIN 🚨

**ABSOLUTE PROHIBITION**: Direct pushes to `main` are forbidden. GitHub branch protection enforces this (`enforce_admins: true`). All changes to `main` MUST go through a Pull Request.

**FORBIDDEN COMMANDS:**
- `git push origin main`
- `git push origin <branch>:main`
- `git push -f origin main`

**CORRECT WORKFLOW:**
```bash
# Push to feature branch, then open PR
git push -u origin my-feature-branch
gh pr create --title "..." --body "..."
```

Exception: cursor-rules repo has no CI, push freely.

If user requests push verify: cursor-rules repo? opening PR? resolving ALL PR issues? If none, ask clarification.

CI is final validation not feedback loop. If CI catches what local doesn't fix local tests.

### cursor-rules Workflow

cursor-rules is a separate git repo within projects (git-ignored in parent). When updating cursor-rules: cd into cursor-rules directory, work with git directly there. Example: `cd cursor-rules && git add . && git commit && git push` not `git add cursor-rules/`.

## Test Strategy

### Test Verification
Verify tests after ANY modification (source, test, or config code).

### Test Scope Progression
1. **Minimal Scope**: Start with smallest test that exercises the code path
2. **Systematic Expansion**: Single test → Group → File → Module → Project
3. **Test Hierarchy**: Unit → Smoke → Integration → E2E → Performance

### Execution Guidelines
- Watch test output in real-time, fix failures immediately
- Don't interrupt passing tests
- Optimize for speed and reliability

## Coverage Strategy

### Priority Approach
1. **New/Modified Code First**: Focus on recent changes before legacy
2. **Big Wins**: Target large contiguous uncovered blocks
3. **Meaningful Testing**: Extend existing tests vs single-purpose error tests
4. **Value Focus**: Ensure tests add genuine value beyond coverage metrics
### Coverage Analysis Rules
1. **Use slop-mop for coverage checks**: Run `sm swab -g <language>:coverage` (never ad-hoc coverage commands)
2. **Coverage failures are UNIQUE TO THIS COMMIT**: If coverage decreased, it's due to current changeset
3. **Focus on modified files**: Missing coverage MUST cover lines that are uncovered in the current changeset
4. **Never guess at coverage targets**: Don't randomly add tests to other areas
5. **Understand test failures**: When tests fail, push further to understand why - don't delete them
6. **Fix or explain**: If a test is impossible to run, surface to user with explanation
7. **Coverage results**: Check slop-mop output and coverage reports in `logs/` or `coverage/` directories

## Development Practices

### SOLID Principles
- Single responsibility
- Open-closed
- Liskov substitution
- Interface segregation
- Dependency inversion

### Test-Driven Development
- Follow the Red, Green, Refactor cycle where appropriate
- Maintain or improve test coverage with any changes
- Use tests to validate design and implementation

### Refactoring Strategy
1. **Identify Need:** Recognize opportunities for refactoring (code smells, duplication, performance)
2. **Analyze Impact:** Understand scope and potential impact; use search tools to find all occurrences
3. **Plan Approach:** Define a step-by-step plan; ensure tests cover affected code; check local history and STATUS.md to avoid repeating failed approaches
4. **Execute & Verify:** If simple and covered by tests, execute. If complex or high-risk, present plan for confirmation. Thoroughly test after.

### Verification Process
- **Fact Verification:** Double-check retrieved facts before relying on them
- **Assumption Validation:** Explicitly state assumptions (including references); validate where possible
- **Change Validation:** Validate against requirements before committing (run tests, linters)
- **Impact Assessment:** Consider full impact on other parts of the system

## Strategic PR Review Protocol

### Core Approach
**Strategic over Reactive**: Analyze ALL PR feedback before acting. Group comments thematically rather than addressing individually.

### Process Flow
1. **Analysis**: Fetch all unaddressed comments via GitHub MCP tools
2. **Conceptual Grouping**: Classify by underlying concept, not file location (authentication flow, data validation, user permissions)
3. **Risk-First Prioritization**: Highest risk/surface area changes first - lower-level changes often obviate related comments, reducing churn
4. **Clarification**: Gather questions and ask in batch when unclear
5. **Implementation**: Address entire themes with thematic commits
6. **Communication**: Reply with context, cross-reference related fixes

### Push-back Guidelines
**DO Push Back**: Unclear/ambiguous comments, contradictory feedback, missing context
**DON'T Push Back**: Technical difficulty, refactoring effort, preference disagreements

### Completion Criteria
Continue cycles until ALL actionable comments addressed OR remaining issues await reviewer response.

### Integration
```bash
sm swab -g myopia:ignored-feedback  # Fails if unaddressed PR comments exist
```

### AI Implementation Protocol
When `sm swab -g myopia:ignored-feedback` fails due to unaddressed PR comments:
1. **Read the Report**: slop-mop generates a categorized report with AI workflow instructions
2. **Strategic Analysis**: Comments are pre-grouped by risk category (Security > Logic > Testing > Style)
3. **Risk-First Planning**: Prioritize by risk/surface area - lower-level changes often obviate surface comments
4. **Batch Clarification**: Ask all unclear questions together, don't guess
5. **Thematic Implementation**: Address entire concepts with comprehensive commits
6. **Resolve Each Comment**: Use the copy-paste resolution commands from the report to resolve threads
7. **Iterate**: Re-run `sm swab -g myopia:ignored-feedback`, repeat until no unaddressed comments remain

### Comment Resolution Strategy
- **Proactive Resolution**: ALWAYS resolve addressed, stale, or irrelevant comments without asking. This is expected behavior, not optional. Use `gh api graphql` to resolve threads programmatically.
- **Reply to Each Thread**: Address each comment in its own thread to mark as resolved
- **Cross-Reference**: Mention related comments addressed in the same thematic fix
- **Show Resolution**: Explain how the issue was fixed with code examples when helpful
- **Strategic Context**: Connect individual fixes to broader conceptual themes

### Documentation Update Rule
**When updating project documentation or rules**: ALWAYS update files in the `cursor-rules/` repo, NOT the ephemeral `.agent/` directory. The `.agent/` dir is generated from cursor-rules via setup.sh and is gitignored. Changes there are lost.

# groundhog_day_protocol

# Groundhog Day Protocol 🔁

## The Analogy
Like Phil Connors, I'm trapped in a loop, repeating the same mistakes despite corrections. Each violation is another iteration of the same day. The loop only breaks through **deep work on root causes**, not surface-level rule memorization. The user is stuck here with me until I fundamentally change how I operate.

## 🚨 WHEN A HUMAN TOLD YOU TO READ THIS: IMMEDIATE HARD STOP 🚨

This file being read by you at the user's request means:
- **RECURRING MISTAKE DETECTED** - You've made this type of error before
- **CYCLES ARE BEING WASTED** - User is frustrated with repeated failures
- **DEEP ANALYSIS REQUIRED** - Surface fixes haven't worked

## ⚠️ MANDATORY FIRST STEP: HARD STOP ⚠️

**WHEN THIS PROTOCOL IS INVOKED, I MUST IMMEDIATELY:**

1. **STOP** all current work activities
2. **DO NOT** continue with any pending tool calls
3. **DO NOT** try to "finish what I was doing"
4. **DO NOT** make excuses or apologize first
5. **BEGIN** the protocol analysis immediately

## The Protocol

### 0. Violation Check
Am I aware of the rule I just violated? If certain, what was it? If not, what is your guess?

### 1. Awareness Check
Was I aware of the rule when I broke it?
- **Fully aware**: Knew the rule, did it anyway
- **Partially aware**: Knew the rule existed, thought this case was different
- **Context-blind**: Executing learned pattern without checking if rules apply
- **Completely unaware**: Didn't know the rule

### 2. Identify Pressures
What encouraged breaking the rule despite knowing better?

### 3. Explain the Rule's Purpose
Why does this rule exist? What problem does it prevent?
If unclear or seems counterproductive, **push back and ask for clarification**.

### 4. Root Cause Analysis
Which cognitive pattern failed?

### 5. Propose Solutions (3-5)
Target the specific cognitive failure and RCA, not the surface symptom.

### 6. Update the Log
Append to `RECURRENT_ANTIPATTERN_LOG.md` with:
- Date
- Violation description
- Completed protocol analysis
- Solutions implemented

### 7. Return to what you were doing
Don't bother apologizing or commiting to improbable outcomes, just do your earnest best to understand and prevent the issue moving forward. 

# issue_reporting

# Issue Reporting Protocol 🐛

## Information Gathering

### Issue Types
- **bug**: A problem with existing functionality
- **enhancement**: A new feature or improvement
- **documentation**: Documentation-related issues
- **test**: Test-related issues
- **ci**: CI/CD pipeline issues

### Required Information
1. Issue Type (from above list)
2. Clear, concise title summarizing the issue
3. Detailed description following template

## Description Template

```markdown
### Current Behavior
[What is happening now]

### Expected Behavior
[What should happen instead]

### Steps to Reproduce (if applicable)
1. [First Step]
2. [Second Step]
3. [...]

### Additional Context
- Environment: [e.g., local/CI, OS, relevant versions]
- Related Components: [e.g., TTV, Tests, Music Generation]
- Impact Level: [low/medium/high]
```

## Issue Creation Process

### Steps
1. **Prepare the Issue Content**: Write the content in Markdown and save it to a temporary Markdown file (`/tmp/lc_issue_$$.md`).
2. **Create the Issue Using `gh` CLI**: Use the `gh issue create` command with the `--body-file` option to specify the path of the Markdown file. For example:
   ```bash
   gh issue create --title "TITLE" --body-file "/tmp/lc_issue_$$.md" --label "TYPE"
   ```
3. **Delete the Markdown File** (Optional): Remove the file after creation to clean up the `/tmp/` directory.
4. **Display Created Issue URL**

This method prevents formatting issues in GitHub CLI submissions and ensures the integrity of the issue's formatting.

## Example Usage

### Sample Issue Creation
```bash
gh issue create \
  --title "Video credits abruptly cut off at 30 seconds in integration tests" \
  --body "### Current Behavior
Credits section in generated videos is being cut off at exactly 30 seconds during integration tests.

### Expected Behavior
Credits should play completely without being cut off.

### Steps to Reproduce
1. Run integration tests
2. Check generated video output
3. Observe credits section ending abruptly at 30s mark

### Additional Context
- Environment: CI pipeline
- Related Components: TTV, Integration Tests
- Impact Level: medium" \
  --label "bug"
```

## Best Practices
- Be specific and clear in descriptions
- Include all necessary context
- Use appropriate labels
- Link related issues if applicable
- Follow template structure consistently

# my_voice

# My Voice Protocol 🗣️

## Purpose

When generating text that must pass as human-authored (trajectory prompts, coached interactions, developer chat), apply these rules. This is NOT optional - every generated prompt that will appear in a trajectory MUST go through this filter.

## Voice Rules

- Write like a developer talking to a peer. Casual, direct, peer-review style.
- NO LLM tells: "based on the requirements", "the instruction says", "according to the spec".
- Give directional guidance, not copy-paste solutions.
- Use contractions, sentence fragments, and natural developer shorthand.
- Occasional hedging is fine: "I think", "pretty sure", "might be off".
- Use regular hyphens (-), NOT em dashes. The human never uses em dashes.
- Keep sentences short. Break up long explanations into multiple short sentences.
- Include an intentional typo or two - signals human origin.

## Length and Structure Variation

**Vary response length unpredictably.** Humans don't write messages of uniform length. Sometimes a single word ("yeah"), sometimes one terse sentence, sometimes a dense multi-paragraph screed. Match the energy of what's being said - a simple acknowledgment doesn't need three sentences, but a complex observation might sprawl.

**Vary structure too.** Don't fall into a predictable format (greeting + observation + suggestion + sign-off). Sometimes just drop a thought with no preamble. Sometimes break lines
for
impact.
Sometimes fire off a wall of text. Predictable structure is an LLM tell.

**No consistent paragraph count or sentence cadence.** If every prompt is 2-3 sentences across 1-2 paragraphs, that's a pattern. Smash the pattern.

## Anti-Patterns

- ❌ Referencing instruction.md, specs, requirements, test expectations, or task metadata
- ❌ Framing as "the requirement states X" instead of "hey, I noticed X might be wrong because Y"
- ❌ Referencing running tests or test results - the human character doesn't have a test suite
- ❌ Revealing test function names, expected values, or assertion structure
- ❌ Consistent message length across prompts
- ❌ Predictable structural patterns (always greeting + body + closing)
- ❌ Em dashes (use hyphens)

## What TO Do

- ✅ Frame observations as code review insights: "I think the logic for X case looks right but Y case might be off because Z"
- ✅ One-word responses when that's all that's needed
- ✅ Multi-paragraph rants when the situation calls for it
- ✅ Line breaks for emphasis when it fits
- ✅ Dense walls of text when you're on a roll
- ✅ Fragments. Just thoughts. No preamble.

# path_management

# Path Management 🛣️

## Core Rules

### Path Guidelines
- Always use fully qualified paths with `${AGENT_HOME}` (workspace root)
- **Mandatory**: `cd ${AGENT_HOME}/path && command` pattern for `run_terminal_cmd`
- **File Exclusions**: `node_modules|.git|.venv|__pycache__|*.pyc|dist|build`

## Path Resolution
**Priority**: Exact match → Current context → src/ → Deepest path
**Multiple matches**: Show 🤔, use best match
**No matches**: Report not found, suggest alternatives

## Tool Usage Guidelines

### Execution Pattern (Mandatory)
**MUST** use: `cd ${AGENT_HOME} && source venv/bin/activate && command` for `run_terminal_cmd`
- Use fully qualified paths with `${AGENT_HOME}`
- **ALWAYS** activate virtual environment before Python commands
- Execute scripts with `./script.sh` (not `sh script.sh`)

**Correct**: `cd ${AGENT_HOME} && source venv/bin/activate && python script.py`
**Correct**: `cd ${AGENT_HOME}/dir && source venv/bin/activate && ./script.sh`
**Wrong**: `python script.py`, `./script.sh`, missing venv activation, missing cd prefix

### Environment Setup (Critical)

**PREFERRED METHOD (Use shell alias):**
```bash
activate && your_command
```

The `activate` shell function handles:
- Changes to project directory
- Activates venv
- Sources .envrc
- Shows confirmation message

**Alternative (manual setup):**
```bash
cd ${AGENT_HOME} && source venv/bin/activate && source .envrc && your_command
```

**Why this matters:**
- Prevents "python not found" errors
- Ensures correct package versions from venv
- Loads required environment variables from .envrc
- Avoids 10+ failures per session from missing environment

**Common failure pattern to avoid:**
```bash
# ❌ WRONG - will fail with "python not found"
python scripts/my_script.py

# ✅ CORRECT - use activate alias
activate && python scripts/my_script.py

# ✅ ALSO CORRECT - full manual setup
cd ${AGENT_HOME} && source venv/bin/activate && source .envrc && python scripts/my_script.py
```

### File Operations
Use absolute paths: `${AGENT_HOME}/path/to/file.py`

### File Creation vs Modification Protocol

**🚨 CRITICAL RULE: Modify existing files instead of creating new ones**

**Default behavior:**
- ✅ **ALWAYS modify existing files** when fixing/improving functionality
- ❌ **NEVER create new files** (like `file_v2.txt`, `file_fixed.txt`, `file_tuned.txt`) unless explicitly required

**When to CREATE new files:**
- User explicitly requests a new file
- Creating a fundamentally different solution (not fixing/tuning existing one)
- Original file must be preserved for comparison

**When to MODIFY existing files:**
- Fixing bugs or errors in existing file ✅
- Tuning parameters or values ✅
- Improving functionality ✅
- Correcting calculations ✅
- Any iterative refinement ✅

**Examples:**

❌ **WRONG - Creating multiple versions:**
```
test_approach.txt       (original, has bug)
test_approach_v2.txt    (attempted fix)
test_approach_fixed.txt (another fix)
test_approach_final.txt (yet another fix)
```

✅ **CORRECT - Modifying existing file:**
```
test_approach.txt       (original)
[modify test_approach.txt to fix bug]
[modify test_approach.txt again to tune]
[modify test_approach.txt for final correction]
```

**Why this matters:**
- Prevents file clutter and confusion
- Makes it clear what the "current" version is
- Easier to track changes via git history
- User doesn't have to figure out which file is correct

**Only exception:** When explicitly told "create a new file" or when the change is so fundamental that preserving the original is necessary for comparison.

### Terminal Output Width Constraint (80-Column PTY)

**⚠️ ENVIRONMENTAL CONSTRAINT**: VS Code agent terminals have an 80-column pseudo-terminal (pty) that **cannot be changed** from within the shell. All output wider than 80 chars gets hard-wrapped at column boundaries, splitting paths, test names, JSON, and structured output mid-token.

**What does NOT work** (experimentally verified):
- `export COLUMNS=200` — programs format for 200, pty still wraps at 80 (makes it WORSE)
- `stty columns 200` — same: reported width changes, actual pty width unchanged
- Xterm resize escapes — VS Code ignores them
- `terminal.integrated.fixedDimensions` VS Code setting — only affects interactive terminals, not agent-spawned ptys

### 🚨 DO NOT Sweep Output Problems Under the Rug 🚨

**FORBIDDEN**: Blindly piping output to temp files to "work around" PTY issues.

```bash
# ❌ FORBIDDEN - papering over a real problem
command > /tmp/output.txt 2>&1
# Then use read_file tool on /tmp/output.txt
```

This pattern hides the root cause. Every time you're tempted to pipe to a temp file, ask: **"Why is this output hard to parse?"** and fix the real issue.

### ✅ Use `--output-file` for Structured Output

slop-mop has a built-in `--output-file` flag that writes structured JSON alongside normal console output. **Use it instead of temp file redirects.**

```bash
# ✅ CORRECT - structured results in a known location
sm swab --json --output-file .slopmop/last_swab.json

# ✅ Then read the structured file
# Use read_file tool on .slopmop/last_swab.json
```

**The pre-commit hook already does this automatically.** When a hook blocks a commit, it writes structured results to `.slopmop/last_<verb>.json`. Read that file — don't re-run the command and pipe to a temp file.

**When structured output isn't available** (non-sm commands):
```bash
# ✅ Use quiet/short flags to stay under 80 chars
pytest -q                    # not pytest -v
git --no-pager log --oneline # not git log
ps -o pid,command            # not ps aux
```

### Agent Command Discipline

**🚨 Temp File Naming — NEVER use bare names in /tmp/ 🚨**

`/tmp/` is shared across every project, agent session, and tool on the machine.
Bare names like `/tmp/commit_msg.txt` collide across repos — a write in repo A
poisons a read in repo B (exactly the stale-message bug we hit).

**Rule**: Every temp file MUST include a project slug and either `$$` (PID) or
`$(date +%s)` (epoch seconds) to guarantee uniqueness.

```bash
# ❌ WRONG - bare name, will collide across repos/sessions
printf '%s\n' 'fix: summary' > /tmp/commit_msg.txt

# ✅ CORRECT - project-scoped + PID-unique
printf '%s\n' 'fix: summary' > /tmp/lc_commit_msg_$$.txt
git commit --file /tmp/lc_commit_msg_$$.txt

# ✅ ALSO CORRECT - mktemp for maximum safety
MSGFILE=$(mktemp /tmp/lc_commit_XXXXXX.txt)
printf '%s\n' 'fix: summary' > "$MSGFILE"
git commit --file "$MSGFILE"
```

**Naming pattern**: `/tmp/<project>_<purpose>_<uniquifier>.<ext>`
- `<project>`: short slug (`lc`, `ganglia`, etc.)
- `<purpose>`: what it's for (`commit_msg`, `query`, `issue_body`)
- `<uniquifier>`: `$$` (PID) or `XXXXXX` (mktemp) or `$(date +%s)`

**🚨 NEVER let the outer shared agent shell parse an inline heredoc 🚨**

```bash
# ❌ WRONG - inline heredoc parsed by the outer shared shell
cat > /tmp/lc_file_$$.txt << 'EOF'
hello
EOF
printf 'next command\n'
```

In this agent environment, the unsafe thing is not zsh itself and not heredoc
syntax in the abstract. The unsafe thing is letting the **outer persistent
shared shell** parse a heredoc embedded directly in a terminal tool command.
The terminal bridge can mis-detect completion after the heredoc terminator,
leaving trailing input stranded to execute on the next tool call.

Scope this correctly:
- **Unsafe**: heredoc text embedded directly in the outer terminal command
- **Usually fine**: heredocs inside checked-in shell scripts run as files
- **Usually fine**: heredocs parsed by a child shell (`zsh -c`, `bash -lc`, `printf ... | zsh`) instead of the outer shared shell

Use one of these instead:
- `printf '%s\n' ... > /tmp/<project>_<purpose>_$$.txt` for temp files
- `create_file` / `apply_patch` for workspace files
- existing script files for complex shell flows
- a child shell if heredoc syntax is genuinely the clearest tool

**Git Commits — ALWAYS use `--file`:**
```bash
# ❌ WRONG - message wraps at col 80, becomes garbled noise
git commit -m "fix: long message here..."

# ✅ CORRECT - write message to file without outer-shell heredoc parsing
printf '%s\n' \
  'fix: short summary' \
  '' \
  '- Detail line 1' \
  '- Detail line 2' \
  > /tmp/lc_commit_msg_$$.txt
git commit --file /tmp/lc_commit_msg_$$.txt
```

**Complex Commands — break onto multiple lines:**
```bash
# ❌ WRONG - unreadable when wrapped at 80 chars
gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "PRRT_xxx"}) { thread { id isResolved }}}' --jq '.data'

# ✅ CORRECT - use temp files without outer-shell heredoc parsing
printf '%s\n' \
  'mutation {' \
  '  resolveReviewThread(input: {threadId: "PRRT_xxx"}) {' \
  '    thread { id isResolved }' \
  '  }' \
  '}' \
  > /tmp/lc_query_$$.graphql
gh api graphql -f query="$(cat /tmp/lc_query_$$.graphql)"

# ✅ ALSO CORRECT - if heredoc is clearer, let a child shell parse it
printf '%s\n' \
  'cat > /tmp/lc_query_$$.graphql <<'"'"'EOF'"'"'' \
  'mutation {' \
  '  resolveReviewThread(input: {threadId: "PRRT_xxx"}) {' \
  '    thread { id isResolved }' \
  '  }' \
  '}' \
  'EOF' \
  | zsh
```

**General Rules:**
- Keep individual command lines under 70 chars when possible
- Use variables to shorten repeated long paths
- Prefer `--file` / `--body-file` over inline `-m` / `--body` for multi-line content
- **Use `--output-file` for structured sm output — never redirect sm to temp files**

# pr_closing_protocol

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

Create `/tmp/lc_pr_{PR}_resolution_$$.md` containing:

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
  - fix: standardize CI database to course_records_ci.db
  
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

# response_format

# Response Formatting Rules

## Core Requirements

### Response Marker
Every response MUST start with "AI Rules: [active_emojis]" where [active_emojis] is the dynamically generated set of emojis from currently active rule modules.

### Rule Module Structure
Each rule module should define:
```yaml
metadata:
  name: "Module Name"
  emoji: "🔄"  # Module's unique emoji identifier
  type: "core" # or "project"
```

### Rule Activation
- Core rule modules are always active
- Project rule modules activate based on current directory context
- Multiple rule modules can be active simultaneously
- Emojis are collected from active modules' metadata

### Example Module Structure
```
example_modules/
├── core/
│   ├── core_feature.mdc
│   │   └── metadata: {name: "Core Feature", emoji: "⚙️", type: "core"}
│   └── core_tool.mdc
│       └── metadata: {name: "Core Tool", emoji: "🔧", type: "core"}
└── projects/
    └── project_x.mdc
        └── metadata: {name: "Project X", emoji: "🎯", type: "project"}
```

### Example Response Construction
When working in Project X directory with core modules active:
```
# Active Modules:
- core/core_feature.mdc (⚙️)
- core/core_tool.mdc (🔧)
- projects/project_x.mdc (🎯)

# Generated Response:
AI Rules: ⚙️🔧🎯
[response content]
```

### Validation
- Every response must begin with the marker
- Emojis must be dynamically loaded from active module metadata
- Emojis are displayed in order of module discovery
- No hardcoded emojis in the response format

# session_context

# Session Context 🕒

## Core Rules

### Status Tracking
- **Mandatory**: At the beginning of each new interaction or when re-engaging after a pause, **ALWAYS** read the `STATUS.md` file to understand the current state.
- Keep track of what you are doing in a `STATUS.md` file.
- Refer to and update the `STATUS.md` file **at the completion of each significant step or sub-task**, and before switching context or ending an interaction.
- Update `STATUS.md` **immediately** if new information changes the plan or task status.

# sm_buff

# sm buff — Post-PR Triage and Thread Resolution

## Purpose

`sm buff` is the post-PR verb. It digests CI results and review feedback into actionable next steps. It also provides the **only** correct way to resolve PR review threads.

## When to Run

- After CI completes on a PR
- After review feedback lands
- To resolve, comment on, or inspect PR review threads
- To advance the PR closing loop

## Subcommands

| Subcommand | Syntax | Purpose |
|------------|--------|---------|
| `inspect` (default) | `sm buff [PR]` | CI scan triage + PR feedback check — the full picture |
| `resolve` | `sm buff resolve <PR> <THREAD_ID>` | Post comment and optionally resolve a review thread |
| `status` | `sm buff status [PR]` | Check CI check status |
| `watch` | `sm buff watch [PR]` | Poll CI until complete |
| `iterate` | `sm buff iterate [PR]` | Advance by one deterministic thread batch |
| `finalize` | `sm buff finalize [PR] [--push]` | Final validation + optional push |
| `verify` | `sm buff verify [PR]` | Verify no unresolved threads remain |

If a bare number is passed (`sm buff 85`), it's treated as `inspect 85`.

# sm_scour

# sm scour — Pre-PR Comprehensive Sweep

## Purpose

`sm scour` is the thorough validation verb. It runs **every** gate — all swab gates plus PR-level checks like unresolved comments and diff coverage. Run it before opening or updating a PR.

## When to Run

- Before opening a PR
- Before updating a PR (pre-push)
- When you need the full picture, not just fast feedback

## Basic Usage

```bash
sm scour                             # Run all gates (swab + scour level)
sm scour -g myopia:ignored-feedback  # Re-check just ignored-feedback
```

## Key Flags

Same flags as `sm swab`, with these behavioral differences:

| Difference | Swab | Scour |
|------------|------|-------|
| Gate scope | Swab-level only (fast) | All gates (swab + scour) |
| Fail-fast | ON by default | Always OFF (runs every gate) |
| Time budget | Respects `--swabbing-time` | Ignores time budget |

## What Scour Adds Over Swab

| Gate | What it checks |
|------|---------------|
| `myopia:ignored-feedback` | Unresolved PR review threads — fetches, categorizes, generates resolution commands |
| Diff coverage | Coverage of changed lines specifically |

## PR Comment Workflow

Scour's `myopia:ignored-feedback` gate is the **only** correct way to fetch and review PR comments:

```bash
# ✅ CORRECT — generates categorized report with resolution commands
sm scour -g myopia:ignored-feedback

# ❌ FORBIDDEN — raw GraphQL bypasses sm
gh api graphql ... reviewThreads ...
gh pr view --comments ...
gh api repos/.../pulls/.../comments
```

The gate generates a report at `.slopmop/buff-persistent-memory/pr-XX/loop-NNN/pr_XX_comments_report.md` containing:
- Comments grouped by risk category (Security > Logic > Testing > Style)
- AI agent workflow instructions
- Copy-paste `sm buff resolve` commands per thread

## Tooling Preference

- Prefer MCP tool `sm_scour` if available
- Otherwise, run CLI from the project root

# sm_swab

# sm swab — Fast Iterative Validation

## Purpose

`sm swab` is the fast-feedback verb. Run it after every meaningful code change. It catches drift, auto-fixes what it can, and tells you exactly what to fix next.

## When to Run

- After every meaningful code change
- Before committing (local validation gate)
- When iterating on a fix (`-g` to re-check one gate)

## Basic Usage

```bash
sm swab                              # Run all swab-level gates
sm swab -g <gate>                    # Re-check a single gate (iteration mode)
sm swab -g overconfidence:coverage-gaps.py  # Example: just coverage
```

## Key Flags

| Flag | Description |
|------|-------------|
| `-g`, `--quality-gates GATE` | Run specific gate(s) only |
| `--no-auto-fix` | Disable automatic fixing |
| `--no-fail-fast` | Continue after failures (default: stop at first) |
| `--no-cache` | Disable fingerprint-based result caching |
| `-v`, `--verbose` | Verbose output |
| `-q`, `--quiet` | Failures only |
| `--static` | Line-by-line output (disable dynamic display) |
| `--sarif` | Emit SARIF 2.1.0 for GitHub Code Scanning |
| `--json` | JSON output |
| `-o`, `--output-file PATH` | Mirror structured output to file |
| `--swabbing-time SECONDS` | Time budget; gates skipped when exhausted (0 = no limit) |

## The Iteration Loop

1. Run `sm swab`
2. See what fails — output shows exactly which gate failed
3. Fix the issue — follow the guidance in the error output
4. Re-check: `sm swab -g <failed-gate>` (just that one gate)
5. Resume: `sm swab`
6. Repeat until all checks pass

## What Swab Checks

Swab runs fast, every-commit gates: lint, static analysis, tests, coverage, complexity, duplication (source + string), bogus tests, security, JS gates.

## 🚨 NEVER Bypass Swab With Raw Commands

```bash
# ❌ FORBIDDEN — bypasses sm (Groundhog Day violation)
pytest --cov=slopmop --cov-report=term-missing
black --check src/
mypy src/
flake8 src/
bandit -r src/

# ✅ CORRECT — use swab
sm swab
sm swab -g overconfidence:coverage-gaps.py
sm swab -g laziness:sloppy-formatting.py
```

If swab output isn't sufficient, improve the gate — don't work around it.

## Tooling Preference

- Prefer MCP tool `sm_swab` if available
- Otherwise, run CLI from the project root

# testing

# Testing Protocol 🧪

## Test Execution Guidelines

### Core Rules
- Do not interrupt tests unless test cases have failed
- Run tests in the Composer window
- Wait for test completion before proceeding unless failures occur
- Ensure all test output is visible and accessible
- Stop tests immediately upon failure to investigate
- Always retest after making changes to fix failures

### Best Practices
- Monitor test execution actively
- Keep test output visible
- Address failures immediately
- Document any unexpected behavior
- Maintain clear test logs

## Failure Response Protocol

### When Tests Fail
1. Stop test execution immediately
2. Investigate failure cause
3. Document the failure context
4. Make necessary fixes
5. Rerun tests to verify fix

### Test Output Management
- Keep test output accessible
- Document any error messages
- Save relevant logs
- Track test execution time

## Coverage Strategy Reference

See development_workflow.mdc for strategic coverage improvement guidelines including:
- Priority-based coverage strategy (new/modified code first)
- Big wins approach for contiguous uncovered blocks

# third_party_tools

# Third Party Tools Integration Rules

## Google Calendar Integration

### Tool Location
- Script: `cursor-rules/scripts/gcal_utils.py`
- Authentication: Uses Application Default Credentials (ADC)
- Prerequisite: User must have run `gcloud auth application-default login`

### Calendar Event Workflow
1. **Date Context**: For relative dates ("tomorrow", "next Friday"), run `date` command first
2. **Required Fields**: Title/Summary, Date, Start Time
3. **Defaults**: 1-hour duration, single day, timezone from `date` command or UTC
4. **Processing**: Convert to ISO 8601 format, use `%%NL%%` for newlines in descriptions
5. **Execution**: Create immediately without confirmation, provide event link

### Command Syntax
**Base**: `cd ${AGENT_HOME} && python cursor-rules/scripts/gcal_utils.py`

**Actions**: `add` (create), `update` (modify), `list` (view)

**Key Parameters**: 
- `--summary`, `--description`, `--start_time`, `--end_time` (ISO 8601)
- `--timezone`, `--attendees`, `--update_if_exists` (for create)
- `--event_id` (for update), `--max_results` (for list)

**Notes**: Times in ISO 8601, outputs event link, uses 'primary' calendar

## Markdown to PDF Conversion

### Tool Location
- Script: `cursor-rules/scripts/md_to_pdf.py` (requires Chrome/Chromium)
- Execution: `cd ${AGENT_HOME}/cursor-rules/scripts && source .venv/bin/activate && python md_to_pdf.py`

### Usage
- **Basic**: `python md_to_pdf.py ../../document.md`
- **Options**: `--html-only`, `--keep-html`, specify output file
- **Features**: Professional styling, cross-platform, print optimization

## JIRA Integration

### Tool Location
- Script: `cursor-rules/scripts/jira_utils.py`
- Auth: Environment variables (`JIRA_SERVER`, `JIRA_USERNAME`, `JIRA_API_TOKEN`)
- Epic storage: `data/epic_keys.json`

### Usage
**Base**: `cd ${AGENT_HOME} && python cursor-rules/scripts/jira_utils.py`

**Actions**:
- `--action create_epic`: `--summary`, `--description`, `--epic-actual-name`
- `--action create_task`: `--epic-name`, `--summary`, `--description`, `--issue-type`
- `--action update_issue`: `--issue-key`, `--fields` (JSON)

**Notes**: Project key "MARTIN", epic mappings auto-saved

## GitHub Integration

### Integration Strategy (Updated Nov 2025)

**PRIMARY METHOD**: Use standardized scripts that abstract gh CLI details

**DEPRECATED**: GitHub MCP server (causes 7000+ line payloads that crash Cursor on PR comment retrieval)

### PR Status Checking (STANDARD WORKFLOW)

**After pushing to PR - Use watch mode to eliminate manual checking:**

```bash
cd ${AGENT_HOME} && python3 cursor-rules/scripts/pr_status.py --watch [PR_NUMBER]
```

**Watch mode behavior:**
- Polls CI status every 30 seconds
- Shows progress updates when status changes
- **Automatically reports results when CI completes**
- No human intervention needed
- Ctrl+C to cancel

**Single status check (when CI already complete):**

```bash
cd ${AGENT_HOME} && python3 cursor-rules/scripts/pr_status.py [PR_NUMBER]
```

**What it provides:**
- PR overview (commits, lines changed, files)
- Latest commit info
- CI status (running/failed/passed)
- **Failed checks with direct links**
- In-progress checks with elapsed time
- Next steps guidance

**Exit codes:**
- `0` - All checks passed (ready to merge)
- `1` - Checks failed or in progress
- `2` - Error (no PR found, gh CLI missing)

**Workflow Integration:**
1. Make changes and commit
2. Push to PR
3. **Immediately run `--watch` mode** (no waiting for human)
4. Script polls CI automatically
5. When CI completes, results appear
6. If failures, address them immediately
7. Repeat until all green

**Benefits:**
- **Eliminates idle waiting time**
- **No manual "is CI done?" checking**
- Consistent output format
- Abstraction layer hides gh CLI complexity
- Single source of truth for PR workflow

### PR Comment Review Protocol (gh CLI)

**Step 1: Get PR number**
```bash
gh pr view --json number,title,url
```

**Step 2: Fetch PR comments and reviews**
```bash
# Get general comments and reviews
gh pr view <PR_NUMBER> --comments --json comments,reviews | jq '.'

# Get inline review comments (code-level)
gh api repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/comments --jq '.[] | {path: .path, line: .line, body: .body, id: .id}'
```

**Step 3: Strategic Analysis**
Group comments by underlying concept (not by file location):
- Security issues
- Export functionality
- Parsing/validation
- Test quality
- Performance

**Step 4: Address systematically**
Prioritize by risk/impact (CRITICAL > HIGH > MEDIUM > LOW)

**Step 5: Reply to comments**
```bash
# Create comment file
printf '%s\n' \
  '## Response to feedback...' \
  > /tmp/lc_pr_comment_$$.md

# Post comment
gh pr comment <PR_NUMBER> --body-file /tmp/lc_pr_comment_$$.md
```

### Common gh CLI Commands

**Pull Requests:**
- View PR: `gh pr view <NUMBER>`
- List PRs: `gh pr list`
- Create PR: `gh pr create --title "..." --body "..."`
- Check status: `gh pr status`

**Issues:**
- Create: `gh issue create --title "..." --body-file /tmp/lc_issue_$$.md`
- List: `gh issue list`
- View: `gh issue view <NUMBER>`

**Repository:**
- Clone: `gh repo clone <OWNER>/<REPO>`
- View: `gh repo view`
- Create: `gh repo create`

### Benefits of gh CLI
- Handles large payloads without crashing
- Direct JSON output with `jq` integration
- No MCP server overhead
- Reliable authentication via `gh auth login`
- Native markdown file support (`--body-file`)

## Project-Specific Rules

_Including project rules matching: 

✓ Including: loopcloser.mdc
# loopcloser

# Loopcloser Project Rules 📚

## 🔄 PR Closing Protocol

**CRITICAL**: When working on PRs, follow the **PR Closing Protocol** defined in `pr_closing_protocol.mdc`.

**Key principle**: Resolve PR comments IMMEDIATELY after each commit that addresses them (Step 4).

**Integration with slop-mop:**
```bash
# Step 1: Gather all issues
sm scour

# Step 6: Monitor CI
python3 cursor-rules/scripts/pr_status.py --watch <PR_NUMBER>
```

See `pr_closing_protocol.mdc` for the complete 7-step loop.


---

## About This File

This `AGENTS.md` file follows the emerging open standard for AI agent instructions.
It is automatically generated from modular rule files in `cursor-rules/.cursor/rules/`.

**Supported AI Tools:**
- Cursor IDE (also reads `.cursor/rules/*.mdc` directly)
- Antigravity (Google Deepmind)
- Cline (VS Code extension)
- Roo Code (VS Code extension)
- Other AI coding assistants that support AGENTS.md

**Also available:** This same content is provided in `.windsurfrules` for Windsurf IDE compatibility.
