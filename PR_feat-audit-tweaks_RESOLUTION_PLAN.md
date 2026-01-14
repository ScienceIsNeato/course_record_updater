# PR # (branch: feat/audit-tweaks) Resolution Plan

## Summary
Branch: feat/audit-tweaks
Created: PR resolution plan generated locally.

This document captures the results of the local PR validation run and maps the required fixes to concrete actions and files. It also lists reviewer threads that need resolving (fetch via `gh api` if required) and the commands to run locally to validate fixes.

---

## Validation Summary (local)
- Command run: `venv/bin/python scripts/ship_it.py --checks commit --no-fail-fast`
- Result: All local checks passed.
  - Python unit tests: passed
  - JavaScript tests (Jest): passed
  - Lint/format: auto-fixed where applicable
  - Security audit: previously addressed; baseline updated and committed

---

## Already Resolved (auto-detected locally)
- `tests` updated to use centralized test password constants (`src/utils/constants.py`), `.secrets.baseline` updated and committed.
  - Commits: recent local commits on branch `feat/audit-tweaks` include baseline and test credential centralization.

---

## Unresolved PR Review Threads (requires GH API)
- Action: Fetch PR threads and unresolved review comments for this PR number using the GitHub CLI or API and map each thread to the commit fixing it.
- Suggested commands:
  - `gh pr view --json number,headRefName,url`
  - `gh api graphql -f query='query { repository(owner: "<OWNER>", name: "<REPO>") { pullRequest(number: <PR>) { reviewThreads(first: 100) { nodes { id isResolved path line body } } } } }'`

---

## Proposed Local Fixes (if any remain)
- If new CI failures appear after pushing, follow this flow:
  1. Run failing check locally (e.g., `venv/bin/python -m pytest tests/...` or `venv/bin/python scripts/ship_it.py --checks js-tests-and-coverage`).
  2. Implement minimal fix and unit test to validate.
  3. Commit with message referencing PR thread ID and details.
  4. Resolve the PR thread via GraphQL and post an explanatory reply.

---

## Commit & Push Checklist
- [ ] Ensure unresolved review threads count is 0 via GraphQL
- [ ] Run `venv/bin/python scripts/ship_it.py --checks commit --no-fail-fast` locally and confirm all checks pass
- [ ] Commit changes and push branch
- [ ] Run `python3 cursor-rules/scripts/pr_status.py --watch <PR_NUMBER>` to monitor CI

---

## Contact / Notes
If you want, I can also:
- Fetch PR review threads and create a mapping of thread -> commit.
- Post resolution comments via `gh` for threads already fixed locally.


