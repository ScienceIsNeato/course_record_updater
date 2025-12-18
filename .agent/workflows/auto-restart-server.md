---
description: Automatically restart server after template/static file changes
---

# Auto-Restart Server After Changes

When making changes to the following file types, **automatically restart the development server** before reporting completion to the user:

## Files That Require Server Restart

- **Templates** (`.html` files in `templates/`)
- **Static files** (`.js`, `.css` files in `static/`)
- **Python code** (`.py` files)
- **Configuration files** (`.envrc`, config files)

## Restart Command

// turbo
```bash
./restart_server.sh dev
```

## Workflow

1. Make code changes
2. Run any relevant tests
3. **Restart the server** (use the command above)
4. Report completion to user

## Why This Matters

Flask's development server needs to be restarted to pick up changes to:
- Jinja2 templates (even with auto-reload, some changes need restart)
- JavaScript/CSS files (browser caching)
- Python route handlers and business logic

By restarting automatically, the user can immediately test changes without manual intervention.
