# PLO Dashboard — Design Approach

This document captures the key design decisions behind the PLO (Program Learning Outcomes) Dashboard feature.

## Architecture: Single Tree API

**Decision:** A single `/api/plo-dashboard/tree` endpoint returns the entire 4-level hierarchy in one call.

**Rationale:** The dashboard needs Program → PLO → CLO → Section data displayed at once. Fetching each level with separate API calls would cause N+1 network round-trips and require complex client-side data stitching. The aggregation service pre-fetches all section outcomes for the term and indexes them by `outcome_id`, yielding O(1) lookups per CLO. This matches the existing `DashboardService` pattern used by other dashboard views.

## UI: Expandable Rows in Cards

**Decision:** The drill-down tree uses Bootstrap 5 `collapse` components inside cards, similar to the existing `audit_clo.html` page.

**Rationale:** Considered a sidebar tree navigation but rejected it because (a) it requires a different layout from every other dashboard page, (b) Bootstrap collapse is already used extensively in the codebase, and (c) the 4-level hierarchy maps naturally to nested expandable rows. No new front-end dependencies are needed.

## Assessment Display Configuration

**Decision:** Per-program assessment display mode (`percentage`, `binary`, or `both`) is stored in `Program.extras["plo_assessment_display"]`.

**Rationale:** The `Program.extras` JSON/PickleType column already exists for arbitrary per-program metadata. Using it avoids a schema migration. The display mode is read by the dashboard service and propagated to each program node so the frontend can format numbers accordingly. Default is `"percentage"` when unset.

### Display Rules

| Mode | Output | Example |
|------|--------|---------|
| `percentage` | `"{pct}%"` | `"78%"` |
| `binary` | `"S"` or `"U"` (70% threshold) | `"S"` |
| `both` | `"{S|U} ({pct}%)"` | `"S (78%)"` / `"U (54%)"` |

- Missing data: `"N/A"` with grey styling
- Threshold: 70% pass rate for Satisfactory/Unsatisfactory determination

## Default Scope

**Decision:** The dashboard defaults to showing all programs for the current (active) term, with optional filters.

**Rationale:** Institution admins need a cross-program overview. Program admins are auto-scoped to their program by the session context. Showing all programs by default is the most useful starting state; narrowing to a single program or changing the term is one click away.

## CLO-to-PLO Mapping UX

**Decision:** Leverage the existing draft/publish mapping API. The dashboard is read-only — it displays only the latest published mapping.

**Rationale:** PR #64 already built the complete mapping CRUD API with versioned draft → publish workflow and matrix builder. The dashboard does not need to duplicate this. It reads the latest published mapping and displays the CLO links.

## Instructor Access

**Decision:** Instructors do not see the PLO Dashboard in navigation.

**Rationale:** The PLO Dashboard is for program and institution admins who need cross-course visibility. Instructors interact with their own CLOs through the existing outcomes and assessment pages. A future enhancement may surface PLO context on the instructor's assessment page.

## Missing Assessment Data

**Decision:** Show `"N/A"` with a distinct grey style (`.rate-na`) for CLOs with no section-level assessment data.

**Rationale:** A blank cell is ambiguous — it could mean "not loaded yet" or "zero students." An explicit `"N/A"` clearly signals that assessment data has not been entered for that CLO/section combination.

## Demo Data Design

The demo manifest includes:
- **2 programs** (BIOL with 3 PLOs, ZOOL with 2 PLOs) with published v1 mappings
- **Mixed assessment coverage** across both terms for realistic drill-down
- **Program settings:** ZOOL configured with `"both"` display mode to showcase dual-format
- CLO entries spanning courses in both programs to demonstrate cross-course mapping
