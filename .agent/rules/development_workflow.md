---
trigger: always_on
description: "Antigravity rule"
---

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
# 1. Make change to ship_it.py
vim scripts/ship_it.py

# 2. Test the change locally
python scripts/ship_it.py --checks sonar

# 3. Verify output shows expected behavior
# (e.g., log header says "PR validation" instead of "COMMIT validation")

# 4. THEN commit
git add scripts/ship_it.py
git commit -m "fix: correct validation type"
```

❌ **WRONG Workflow (What NOT to do):**
```bash
# Make change
vim scripts/ship_it.py

# Immediately commit without testing
git add scripts/ship_it.py
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

## Push Discipline 💰

GitHub Actions cost money. NEVER push without explicit user request.

Only push in two scenarios:
1. Opening PR (local gates pass, commits complete, ready for CI validation)
2. Resolving ALL PR issues (all feedback addressed, local gates pass)

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
1. **ONLY use ship_it.py --checks coverage**: Never run direct pytest coverage commands
2. **Coverage failures are UNIQUE TO THIS COMMIT**: If coverage decreased, it's due to current changeset
3. **Focus on modified files**: Missing coverage MUST cover lines that are uncovered in the current changeset
4. **Never guess at coverage targets**: Don't randomly add tests to other areas
5. **Understand test failures**: When tests fail, push further to understand why - don't delete them
6. **Fix or explain**: If a test is impossible to run, surface to user with explanation
7. **Coverage results in scratch file**: The ship_it.py --coverage check writes full pycov results to logs/coverage_report.txt for analysis

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
python scripts/ship_it.py --validation-type PR  # Fails if unaddressed PR comments exist
```

### AI Implementation Protocol
When ship_it.py fails due to unaddressed PR comments:
1. **Fetch Comments**: Use GitHub MCP tools to get all unaddressed PR feedback
2. **Strategic Analysis**: Group comments by underlying concept (not file location)
3. **Risk-First Planning**: Prioritize by risk/surface area - lower-level changes obviate surface comments
4. **Batch Clarification**: Ask all unclear questions together, don't guess
5. **Thematic Implementation**: Address entire concepts with comprehensive commits
6. **Resolve Each Comment**: Reply directly to each comment thread explaining resolution and cross-referencing related fixes
7. **Iterate**: Re-run ship_it.py, repeat until no unaddressed comments remain

### Comment Resolution Strategy
- **Reply to Each Thread**: Address each comment in its own thread to mark as resolved
- **Cross-Reference**: Mention related comments addressed in the same thematic fix
- **Show Resolution**: Explain how the issue was fixed with code examples when helpful
- **Strategic Context**: Connect individual fixes to broader conceptual themes
