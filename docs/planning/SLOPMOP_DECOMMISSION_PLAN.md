# Slop-Mop Decommission Plan For ship_it And maintAInability-gate

## Goal

Remove `scripts/ship_it.py` and `scripts/maintAInability-gate.sh` from the LoopCloser codebase once all required quality checks are either:

1. covered by built-in slop-mop gates,
2. covered by repo-local slop-mop custom gates, or
3. intentionally dropped with explicit rationale.

## Current State

Completed migration work:

- Python lint and formatting parity is present in slop-mop.
- JavaScript lint and formatting parity is present in slop-mop.
- Python tests, coverage, and diff coverage parity are present in slop-mop.
- JavaScript tests and coverage parity are present in slop-mop.
- Complexity, duplication, dead code, bogus tests, hand-wavy tests, debugger artifacts, gate dodging, and related hardening are present in slop-mop.
- `smoke` is now available as a custom slop-mop scour gate via `scripts/run_smoke.sh` and remains under the 30-second runtime budget, but the current smoke workflow still has a seeded-login mismatch that must be fixed before this gate is considered green.
- `e2e` is now available as a custom slop-mop scour gate, but is currently disabled because its measured runtime is about 68 seconds, above the 30-second enablement threshold.
- Upstream hardening follow-up has been filed in slop-mop issue `#102` for import validation parity and frontend runtime sanity parity.

## Remaining Work Before Deletion

### 1. Resolve Remaining Parity Gaps

These are the only substantial legacy checks still not fully replaced:

- Python import validation
  - Target state: built-in slop-mop support or an accepted repo-local custom gate.
  - Tracking: upstream slop-mop issue #102.

- Frontend runtime sanity validation
  - Current legacy behavior: `scripts/check_frontend.sh` validates HTML structure, required assets, API health, and JS syntax.
  - Target state: built-in slop-mop support or a repo-local custom gate with equivalent coverage.
  - Tracking: upstream slop-mop issue #102.

- E2E runtime budget
  - Target state: reduce the activated `./scripts/run_uat.sh` path to under 30 seconds if it is meant to stay enabled in routine scour runs.
  - If that is not realistic, keep it as a documented disabled-by-default custom scour gate and only enable it in contexts where the runtime is acceptable.

- Smoke seeded-login mismatch
  - Target state: make `scripts/run_smoke.sh` pass end to end with the seeded smoke account and manifest data.
  - This is now a localized smoke-runner/data issue, not a broad slop-mop migration gap.

### 2. Replace Legacy Entrypoints In Human And Automation Paths

Update all references so the repo no longer depends on the legacy wrappers:

- README and developer docs
- any local runbooks that still point to `ship_it.py`
- CI workflows or local tasks still invoking `ship_it.py` or `maintAInability-gate.sh`
- contributor guidance that still treats those scripts as the primary interface

Target replacement model:

- `sm swab` for fast day-to-day validation
- `sm scour` for deeper validation
- targeted `sm swab -g ...` or `sm scour -g ...` for focused remediation

### 3. Remove Embedded Smoke Logic From Legacy Gate Script

Once the custom slop-mop smoke gate is accepted as the canonical path:

- keep `scripts/run_smoke.sh` as the standalone smoke runner,
- stop referencing the smoke section inside `maintAInability-gate.sh`,
- treat the legacy embedded implementation as deprecated.

### 4. Confirm No Unique Legacy Behavior Remains

Before deleting the wrappers, verify there is no remaining behavior that exists only in the legacy scripts:

- environment bootstrap assumptions that need to move into standalone scripts,
- CI-specific orchestration still buried in `ship_it.py`,
- PR comment enforcement if the repo wants to enable `ignored-feedback` in slop-mop instead.

## Deletion Sequence

### Phase 1: Finish Parity

- Close or otherwise resolve the import-validation gap.
- Close or otherwise resolve the frontend runtime validation gap.
- Decide final policy for `e2e`: optimize under 30 seconds, or keep disabled by default.

### Phase 2: Cut Over Usage

- Replace repo docs and local workflow instructions to use slop-mop commands.
- Replace CI or task invocations that still call `ship_it.py` or `maintAInability-gate.sh`.
- Validate that `sm swab` and `sm scour` cover the intended commit and PR workflows.

### Phase 3: Deprecate Legacy Scripts

- Mark `scripts/ship_it.py` as deprecated.
- Mark `scripts/maintAInability-gate.sh` as deprecated.
- Keep them temporarily as thin wrappers only if needed for transition.

### Phase 4: Delete

- Remove `scripts/ship_it.py`.
- Remove `scripts/maintAInability-gate.sh`.
- Remove stale docs and references.
- Re-run slop-mop and repo smoke checks after deletion.

## Practical Recommendation

The codebase is already close to removal-ready. The remaining blocking work is not broad migration anymore; it is a short tail:

- import validation parity,
- frontend runtime sanity parity,
- e2e runtime policy,
- documentation and workflow cutover.

Once those are settled, deleting the legacy wrappers should be a small cleanup change rather than another large migration.