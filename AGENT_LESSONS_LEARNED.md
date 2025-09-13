# Agent Lessons Learned

## Quality Gate Execution Best Practices

### ✅ CORRECT: Run Full Suite by Default
```bash
# Run ALL quality checks (recommended default)
python scripts/ship_it.py --fail-fast

# This automatically runs: black, isort, lint, tests, coverage, security, types, imports, duplication, sonar
```

### ❌ INCORRECT: Unnecessarily Enumerate Individual Checks
```bash
# DON'T do this unless you specifically need only certain checks
python scripts/ship_it.py --checks black isort lint tests coverage security types --fail-fast
```

### When to Use Specific Checks
Only specify `--checks` when you need targeted validation:
- `--checks tests` - Quick test-only run during development
- `--checks black isort` - Format-only fixes
- `--checks tests coverage` - Test validation cycle

### Default Behavior
- **No `--checks` flag** = Run ALL available checks
- This is the comprehensive quality gate validation
- Use this for final validation before commits

## Key Insight
The agent was repeatedly enumerating individual checks instead of leveraging the default "run everything" behavior. The script is designed to run the full suite by default, which is the intended workflow for comprehensive quality validation.
