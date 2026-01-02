---
trigger: always_on
description: "Core rules for AI response formatting"
---

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
- Update active modules based on context changes