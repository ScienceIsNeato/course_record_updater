---
trigger: always_on
description: "Core configuration and module loading rules"
---

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
