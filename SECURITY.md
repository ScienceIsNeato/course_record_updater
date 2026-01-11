Security & Static Scan Policy

This repository runs automated security checks as part of the quality gate (bandit, semgrep, detect-secrets, safety).

Goals
- Surface real security problems (HIGH and MEDIUM severity) and fail CI on those.
- Avoid noisy failures on developer helper scripts and false positives (LOW severity) so maintainers can iterate quickly.

Policy
1. Bandit (Python) - configuration and evaluation:
   - We exclude developer-only scripts from strict blocking scans (the `scripts/` directory is excluded in bandit runs by default).
   - CI will fail if Bandit reports any HIGH or MEDIUM severity issues.
   - LOW severity issues will be reported as WARN (not failing the CI) and listed in the build output for review.

2. Handling flagged issues:
   - If a HIGH or MEDIUM issue is reported, it must be fixed before merging.
   - If a LOW issue is reported and it's a true positive, prefer fixing it.
   - If a LOW issue is a false positive (e.g., dev helper script intentionally uses subprocess with controlled input), add an in-line justification comment and optionally add a short entry to SECURITY.md explaining why it's safe.
   - Use `# nosec <B######>` inline comments sparingly and only with an explanation.

3. Auditing & Remediation:
   - Maintainers should periodically review LOW severity findings and either fix or document/justify them.
   - For genuine security-sensitive code, ensure tests and additional validation are in place.

Why exclude `scripts/`?
- Scripts often perform repository maintenance tasks, demos, or local development automation. They may use patterns that trigger static scanners (e.g., subprocess calls, assert statements) but do not run in production or process untrusted input.
- Excluding the folder from strict CI failure reduces noise while still surfacing findings for review.

If you are unsure about a security finding, open an issue and tag @security-team (or the repository owner) for review.
