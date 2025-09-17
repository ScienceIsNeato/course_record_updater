# Agent Lessons Learned

## Quality Gate Execution Best Practices

### ✅ CORRECT: Use Appropriate Validation Type
```bash
# Fast commit validation (default - excludes slow security & sonar)
python scripts/ship_it.py

# Full PR validation (comprehensive - includes all checks)
python scripts/ship_it.py --validation-type PR
```

### ❌ INCORRECT: Unnecessarily Enumerate Individual Checks
```bash
# DON'T do this unless you specifically need only certain checks
python scripts/ship_it.py --checks black isort lint tests coverage security types
```

### When to Use Specific Checks
Only specify `--checks` when you need targeted validation:
- `--checks tests` - Quick test-only run during development
- `--checks black isort` - Format-only fixes
- `--checks tests coverage` - Test validation cycle

### Updated Default Behavior (2025)
- **No flags** = Fast commit validation (excludes security & sonar for speed)
- **`--validation-type PR`** = Comprehensive validation with all checks
- **Fail-fast always enabled** = Immediate feedback on first failure
- **78s time savings** with commit validation vs PR validation

### Validation Type Selection
- **Commit validation**: Use during development for rapid feedback cycles
- **PR validation**: Use before creating pull requests for comprehensive quality assurance
- **Specific checks**: Use for targeted fixes or debugging specific issues

## Key Insight
The script now optimizes for development speed by default while maintaining comprehensive validation options. The fail-fast behavior is always enabled, and validation types allow developers to choose the appropriate level of checking based on context.
