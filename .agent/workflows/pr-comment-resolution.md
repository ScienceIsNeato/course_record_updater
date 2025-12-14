---
description: How to respond to PR review comments after making fixes
---

# PR Comment Resolution Workflow

## When to Resolve Comments

**Immediately after each successful commit that addresses PR comments**, reply to each resolved comment. Do NOT wait until all fixes are complete.

## Comment Resolution Process

### After Each Commit:

1. **Identify resolved comments**: For each fix in the commit, identify which PR comment(s) it addresses

2. **Reply to each comment individually** using:
   ```bash
   gh pr comment <PR_NUMBER> --body "Fixed in commit <SHA>. <Brief explanation of how it was fixed>"
   ```

3. **For line-specific comments**, reply directly to that thread (not a general PR comment)

4. **Cross-reference related fixes**:
   ```
   Fixed in commit abc1234.
   - Path traversal protection added with directory whitelisting
   - Also fixed related issue at line 95 (same commit)
   ```

### Reply Template:

```
✅ **Resolved in commit `<short-sha>`**

<Brief description of fix>

<Optional: code snippet showing the fix>
```

### Example Replies:

**For security issue:**
```
✅ **Resolved in commit `c4cbd23`**

Added path traversal protection:
- Normalize path and check for `..` sequences
- Whitelist allowed directories: `demos/`, `test_data/`, `tests/e2e/fixtures/`
- Verify file exists before processing
```

**For unused variable:**
```
✅ **Resolved in commit `e01d5a8`**

Prefixed with underscore to indicate intentionally unused: `_admin_email`
```

**For documentation issue:**
```
✅ **Resolved in commit `c4cbd23`**

Updated "Live system for CEI" to "Live production system" to keep documentation institution-agnostic.
```

## Key Principles

1. **Timely Resolution**: Reply immediately after commit, not after all fixes
2. **Specific References**: Always include commit SHA
3. **Clear Explanation**: Explain what was done, not just "fixed"
4. **Cross-Reference**: If one commit fixes multiple comments, mention all in each reply
5. **Mark as Resolved**: If you have permission, mark the thread as resolved in GitHub UI
