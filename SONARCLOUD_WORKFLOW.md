# SonarCloud Workflow

## Quick Reference

### Running SonarCloud Analysis

```bash
# Run full SonarCloud analysis
python scripts/ship_it.py --checks sonar

# Issues are automatically written to: logs/sonarcloud_issues.txt
```

### Reviewing Issues

```bash
# Simply read the issues file
cat logs/sonarcloud_issues.txt

# Or open in your editor
code logs/sonarcloud_issues.txt
```

## Workflow for Fixing Issues

### 1. Run Analysis

```bash
python scripts/ship_it.py --checks sonar
```

This will:
- Generate fresh coverage data
- Run SonarCloud scanner
- Fetch quality gate status
- Write ALL issues to `logs/sonarcloud_issues.txt`
- Display summary in terminal

### 2. Review Issues

Simply read the issues file:

```bash
cat logs/sonarcloud_issues.txt
```

The file contains:
- **🔴 Critical Issues**: Blockers and critical severity
- **🟡 Major Issues**: Important code smells and bugs
- **🔥 Security Hotspots**: Security-related code that needs review

Each issue shows:
- File path and line number
- Issue description
- Rule ID (for reference)
- Severity level

### 3. Fix Issues

Work through issues systematically:
1. Start with critical/blocker issues
2. Address security hotspots
3. Fix major code smells

### 4. Re-run Analysis

After making fixes:

```bash
python scripts/ship_it.py --checks sonar
```

The `logs/sonarcloud_issues.txt` file will be **automatically updated** with the current state.

### 5. Track Progress

Compare before/after by:
- Reading the updated file
- Checking issue counts in terminal output
- Reviewing SonarCloud UI for visual diff

## Benefits of This Approach

✅ **No Repeated Grep Commands**: Issues file automatically updates each run

✅ **Easy Reference**: Just open `logs/sonarcloud_issues.txt` anytime

✅ **Progress Tracking**: File content changes as you fix issues

✅ **Shareable**: Send the file to teammates or attach to PRs

✅ **Persistent**: File survives terminal sessions

## Advanced Usage

### See More Issues

By default, the script shows 50 issues per category. To see all:

```bash
# Show all issues (modify maintainability-gate.sh to pass --max-display)
python scripts/sonar_issues_scraper.py --project-key ScienceIsNeato_course_record_updater --max-display 200
```

### Custom Output Location

```bash
python scripts/sonar_issues_scraper.py --output-file custom_path.txt
```

### Filter by Severity

```bash
python scripts/sonar_issues_scraper.py --severity BLOCKER,CRITICAL
```

## File Location

**Default**: `logs/sonarcloud_issues.txt`

This file is:
- ✅ In `.gitignore` (not committed)
- ✅ Auto-created if missing
- ✅ Overwritten each run (always current)
- ✅ UTF-8 encoded (supports emojis and special chars)

## Integration with Development Workflow

### When to Run

- **Before committing**: Catch issues early
- **After refactoring**: Verify improvements
- **During PR review**: Share issues with team
- **Weekly**: Track technical debt reduction

### Quality Gate Integration

The analysis is part of `ship_it.py --checks sonar`, which:
- ✅ Enforces quality gate pass/fail
- ✅ Blocks commits if critical issues exist
- ✅ Provides actionable feedback
- ✅ Integrates with CI/CD pipeline

## Troubleshooting

### Issues File Not Created

Check that:
1. `logs/` directory exists
2. You have write permissions
3. Script completed successfully (no early exit)

### Stale Issues Shown

The file is overwritten each run, so:
- Re-run analysis to refresh
- Check you're reading the right file
- Verify SonarCloud has analyzed latest code

### Missing Issues

Default shows 50 per category. Use `--max-display` to see more.

## Related Documentation

- `SONARCLOUD_SETUP_GUIDE.md` - Initial setup and configuration
- `SONARCLOUD_TROUBLESHOOTING.md` - Common issues and fixes
- `scripts/sonar_issues_scraper.py` - Source code for scraper

