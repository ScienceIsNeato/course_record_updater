# Security & Static Scan Policy

This repository runs automated security checks as part of the quality gate (bandit, semgrep, detect-secrets, safety).

## Goals
- Surface real security problems (HIGH and MEDIUM severity) and fail CI on those.
- Avoid noisy failures on developer helper scripts and false positives (LOW severity) so maintainers can iterate quickly.

## Password Handling Policy

**Hardcoded passwords are ONLY allowed in these files:**

| File | Purpose |
|------|---------|
| `.envrc` | Environment variables (git-ignored, local only) |
| `src/utils/constants.py` | Centralized test/demo password constants |

All other code **MUST** import passwords from `constants.py`. This ensures:
1. **detect-secrets baseline stability**: Line numbers only change when you intentionally add new secrets
2. **Single source of truth**: All test passwords defined once with proper `# nosec` annotations
3. **Easy auditing**: Security review only needs to check two files

### Password Constants

The codebase uses exactly THREE password constants:

| Constant | Value | Purpose |
|----------|-------|---------|
| `GENERIC_PASSWORD` | `TestPass123!` | **Use everywhere** - all test accounts, seeds, E2E |
| `WEAK_PASSWORD` | `weak` | Testing rejection of weak passwords |
| `INVALID_PASSWORD` | `password123` | Testing password complexity requirements |

**DO NOT** create role-specific passwords (e.g., `SITE_ADMIN_PASSWORD`, `INSTRUCTOR_PASSWORD`). Use `GENERIC_PASSWORD` for all test accounts.

### Using Passwords in Code

```python
from src.utils.constants import GENERIC_PASSWORD

# Create test user with standard password
user = create_user(email="test@example.com", password=GENERIC_PASSWORD)

# For password validation tests only:
from src.utils.constants import WEAK_PASSWORD, INVALID_PASSWORD
with pytest.raises(PasswordValidationError):
    hash_password(WEAK_PASSWORD)
```

### When detect-secrets Fails

The failure message will guide you:

- **"Secrets found in constants.py"**: You added a new password. Run `detect-secrets scan > .secrets.baseline` to update the baseline.
- **"Secrets found in other files"**: You hardcoded a password. Move it to `constants.py` and import from there.

## Bandit (Python)

1. **Configuration and evaluation:**
   - We exclude developer-only scripts from strict blocking scans (the `scripts/` directory is excluded in bandit runs by default).
   - CI will fail if Bandit reports any HIGH or MEDIUM severity issues.
   - LOW severity issues will be reported as WARN (not failing the CI) and listed in the build output for review.

2. **Handling flagged issues:**
   - If a HIGH or MEDIUM issue is reported, it must be fixed before merging.
   - If a LOW issue is reported and it's a true positive, prefer fixing it.
   - If a LOW issue is a false positive (e.g., dev helper script intentionally uses subprocess with controlled input), add an in-line justification comment and optionally add a short entry to SECURITY.md explaining why it's safe.
   - Use `# nosec <B######>` inline comments sparingly and only with an explanation.

3. **Auditing & Remediation:**
   - Maintainers should periodically review LOW severity findings and either fix or document/justify them.
   - For genuine security-sensitive code, ensure tests and additional validation are in place.

## Why exclude `scripts/`?

Scripts often perform repository maintenance tasks, demos, or local development automation. They may use patterns that trigger static scanners (e.g., subprocess calls, assert statements) but do not run in production or process untrusted input.

Excluding the folder from strict CI failure reduces noise while still surfacing findings for review.

---

If you are unsure about a security finding, open an issue and tag @security-team (or the repository owner) for review.
