# Remaining SonarCloud Fixes

## Status
✅ Test coverage improvements committed  
⏳ 31 code smell issues remaining

## Issues to Fix

### 1. JavaScript - templates/assessments.html (10 issues)
**Move functions to outer scope (javascript:S7721):**
- Line 626: `getStatusIndicatorHtml` 
- Line 643: `getBorderColorClass`
- Line 651: `getSuccessRateColorClass`
- Line 438: `getStatusBadge`
- Line 451: `canSubmitForApproval`

**Remove useless assignments (javascript:S1854):**
- Line 334: `successRateColorClass`
- Line 514: `hasEdited`
- Line 595: `hasEdited`

**Form labels (Web:S6853):**
- Line 60, 64, 68: Form labels not associated with controls

### 2. JavaScript - static/panels.js (8 issues)
**Prefer optional chain (javascript:S6582):**
- Lines: 309, 475, 486, 497, 508, 521, 534, 668, 710
- Change `x && x.y` to `x?.y`

### 3. JavaScript - static/script.js (1 issue)
**Prefer optional chain (javascript:S6582):**
- Line 488: Change `x && x.y` to `x?.y`

### 4. CSS - static/admin.css (8 issues)
**Text contrast (css:S7924):**
- Lines: 6, 50, 110, 198, 208, 321, 364, 371
- Increase contrast ratios to meet WCAG AA standards

### 5. CSS - static/auth.css (2 issues)
**Text contrast (css:S7924):**
- Lines: 347, 352
- Increase contrast ratios to meet WCAG AA standards

## Fix Strategy

1. **Quick wins**: Optional chain expressions (automated)
2. **Medium effort**: Move functions to outer scope
3. **Design review**: CSS contrast (may need color adjustments)
4. **HTML**: Fix form label associations

## Commands

```bash
# Run sonar check
python scripts/ship_it.py --checks sonar-status

# Test locally
npm test
pytest

# Push when done
git push origin feature/website-review
```

## Notes
- Test coverage is now good (new files covered)
- These are all code quality improvements, not bugs
- Can be addressed incrementally if time-limited

