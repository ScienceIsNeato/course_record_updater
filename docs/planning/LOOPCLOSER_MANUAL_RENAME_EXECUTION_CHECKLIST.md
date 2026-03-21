# LoopCloser Manual Rename Execution Checklist

## Purpose

This is the manual procedure to rename the GitHub repository from `course_record_updater` to `loopcloser` and finish the remaining repo-slug-linked cleanup.

This checklist assumes the repo-local rename work is already done and committed.

Do not treat this as a speculative plan. Execute it in order and stop on the listed hard-stop conditions.

## Current Verified State

- Current GitHub repo slug: `course_record_updater`
- Target GitHub repo slug: `loopcloser`
- Current local remote URL:
  - `https://github.com/ScienceIsNeato/loopcloser.git`
- Checked-in GCP workflow auth is static-key based via `GCP_SA_KEY`
- Remaining checked-in old-slug references are limited to:
  - `README.md`
  - `docs/RUNBOOK.md`
  - `docs/setup/CI_SETUP_GUIDE.md`

## Hard Stop Conditions

Stop and do not continue if any of the following are true:

1. GitHub repo rename is blocked by permissions, branch protection, or org policy.
2. GitHub Actions or other integrations show repo-slug-based failures immediately after rename.
3. Codecov or another required integration becomes disconnected and blocks required checks.
4. You discover cloud auth outside the repo that is pinned to `ScienceIsNeato/course_record_updater`.
5. The repo rename does not create the expected redirect from the old GitHub URL.

## Before You Start

1. Confirm no one else is actively pushing rename-related changes.
2. Confirm all local work is committed.
3. Keep this repository open locally at the current `main` branch.
4. Keep GitHub repo settings, Actions, and branch protection pages available in your browser.
5. If you use GitHub CLI, ensure you are authenticated with `gh auth status`.

## Step 1: Record Baseline

Run these commands locally and save the output so you can compare after the rename:

```bash
git remote -v
gh repo view ScienceIsNeato/course_record_updater
gh run list --limit 5
```

Expected result:

- `origin` points to `https://github.com/ScienceIsNeato/loopcloser.git`
- `gh repo view` succeeds for the old slug before rename
- recent workflow runs are visible

## Step 2: Rename The Repository In GitHub

In GitHub UI:

1. Open the repository settings page for `ScienceIsNeato/course_record_updater`.
2. Change the repository name to `loopcloser`.
3. Save the change.

Expected result:

- the repo is now reachable at `https://github.com/ScienceIsNeato/loopcloser`
- GitHub shows redirect behavior from the old slug

## Step 3: Update Your Local Remote

Because your current remote uses HTTPS, run:

```bash
git remote set-url origin https://github.com/ScienceIsNeato/loopcloser.git
git remote -v
git fetch origin
```

If you prefer SSH instead, use this instead of the first command:

```bash
git remote set-url origin git@github.com:ScienceIsNeato/loopcloser.git
```

Expected result:

- `origin` now points at `loopcloser.git`
- `git fetch origin` succeeds without redirect warnings or auth failures

## Step 4: Verify The Renamed Repo Exists

Run:

```bash
gh repo view ScienceIsNeato/loopcloser
gh repo view ScienceIsNeato/course_record_updater
```

Expected result:

- the new slug resolves cleanly
- the old slug either redirects or is no longer the primary repo location

If `gh repo view ScienceIsNeato/loopcloser` fails, stop here.

## Step 5: Check GitHub Settings And Protections

In GitHub UI, inspect these manually:

1. Branch protection rules still apply to `main`.
2. Required status checks still reference the expected workflows.
3. Actions are enabled and not paused by the rename.
4. Repository secrets and variables are still present.
5. Any repo-linked integrations still show the renamed repository.

Record any failures before proceeding.

## Step 6: Update The Remaining Checked-In Old-Slug References

Edit these exact locations:

1. `README.md`
2. `docs/RUNBOOK.md`
3. `docs/setup/CI_SETUP_GUIDE.md`

Make these replacements:

```text
https://github.com/ScienceIsNeato/course_record_updater
->
https://github.com/ScienceIsNeato/loopcloser
```

```text
https://codecov.io/gh/ScienceIsNeato/course_record_updater
->
https://codecov.io/gh/ScienceIsNeato/loopcloser
```

```text
https://github.com/ScienceIsNeato/course_record_updater/workflows/...
->
https://github.com/ScienceIsNeato/loopcloser/workflows/...
```

After editing, run this verification sweep for references that must be gone:

```bash
rg -n "ScienceIsNeato/course_record_updater|codecov\.io/gh/ScienceIsNeato/course_record_updater|https://github.com/ScienceIsNeato/course_record_updater/workflows/" README.md docs .github --glob '!docs/planning/**'
```

Expected result:

- no matches in active docs or repo guidance for the old GitHub slug, old Codecov path, or old workflow URL

## Step 7: Commit The Post-Rename Link Patch

Run:

```bash
git status --short
git add README.md docs/RUNBOOK.md docs/setup/CI_SETUP_GUIDE.md
git commit -m "docs: update links after LoopCloser repo rename"
```

Expected result:

- only the intended post-rename doc files are committed

## Step 8: Push And Verify CI

Run:

```bash
git push origin main
gh run list --limit 10
```

Then watch the key workflows in GitHub Actions UI:

1. Quality Gate
2. Build
3. Any release or security workflows that auto-trigger from `main`

Expected result:

- Actions run under the renamed repo
- no auth regressions from the rename
- required checks remain attached to the repo

## Step 9: Verify Deployed And Hosted Surfaces

Run these checks manually after CI is healthy:

```bash
curl -I https://loopcloser.io
curl -I https://staging.loopcloser.io
curl -I https://dev.loopcloser.io
```

Then validate manually:

1. GitHub repo page loads at the new slug.
2. README badges render.
3. Codecov link resolves to the expected project page.
4. `loopcloser.io` still serves correctly.
5. Recent invite/reset/reminder emails still point to `loopcloser.io`.

## Step 10: Share Results Back

When you are done, send back:

1. Output of `git remote -v` after the rename.
2. Output of `gh repo view ScienceIsNeato/loopcloser`.
3. Output of the `rg` verification sweep from Step 6.
4. Result summary for the relevant GitHub Actions runs.
5. Any failure or warning from branch protection, Codecov, or auth.

## Optional Follow-Up Checks

Run these only if something looks wrong:

```bash
gh secret list
gh variable list
gh api repos/ScienceIsNeato/loopcloser/branches/main/protection
```

Use these to inspect repository configuration drift after the rename.