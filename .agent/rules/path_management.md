---
trigger: always_on
description: "Rules for path and file operations"
---

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
python scripts/ship_it.py

# ✅ CORRECT - use activate alias
activate && python scripts/ship_it.py

# ✅ ALSO CORRECT - full manual setup
cd ${AGENT_HOME} && source venv/bin/activate && source .envrc && python scripts/ship_it.py
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

