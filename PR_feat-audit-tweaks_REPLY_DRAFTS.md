# PR feat/audit-tweaks — Reply Drafts

These are ready-to-post reply templates for common PR review thread types. Replace `{COMMIT_SHA}`, `{file_path}`, and `{brief_summary_of_change}` before posting.

- **Fixed in commit:**

  Fixed in commit `{COMMIT_SHA}`. Updated `{file_path}` to address the issue by `{brief_summary_of_change}` (for example: centralized test passwords, removed unsafe innerHTML, added SRI, or replaced CDN initialization). Please re-run checks or let me know if you'd like a different approach.

- **Explained rationale + non-blocking:**

  Thanks for raising this. This finding is low-severity/informational and was considered; we made a minimal, low-risk change to address it while avoiding broader API changes in this PR. If you'd prefer a larger refactor, I can follow up in a separate PR.

- **Request more info / repro:**

  Thanks — could you paste the failing output or a short repro case? I ran the relevant checks locally and made fix `{brief_summary_of_change}`; if your local failure differs I'll reproduce and adjust accordingly.

- **Resolved but left as FYI:**

  This was addressed in commit `{COMMIT_SHA}`; the change is non-functional (refactor/cleanup) and kept small to avoid widening the PR surface. Marking as resolved, but happy to expand if reviewer requests.

---

How to use:
1. Replace placeholders and run `gh pr comment <PR_NUMBER> --body-file /tmp/reply.md` to post.
2. To resolve threads programmatically, use the GraphQL mutation `resolveReviewThread` with the thread id.

If you want, I can attempt to post these replies and resolve threads automatically — confirm and provide `gh` credentials or run locally and I'll provide the exact commands to paste.
