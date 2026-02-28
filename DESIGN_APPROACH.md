# PLO Dashboard — Design Approach

UX and architectural rationale for the Program Learning Outcomes
dashboard. Covers the decisions embodied in
`templates/plo_dashboard.html`, `static/plo_dashboard.js`,
`static/plo_dashboard.css`, and the program-admin mini-panel.

---

## 1. Tree drilldown over a flat table

**Decision:** Render PLOs as a **collapsible tree** (Program → PLO →
CLO → Section) rather than a flat grid or a matrix view.

**Why:**
- The *domain is inherently hierarchical.* A matrix view (PLOs × CLOs
  on two axes) scales badly — six PLOs × forty CLOs gives you a 240-
  cell sparse grid where most cells are empty. A tree only renders
  what exists.
- **Progressive disclosure.** An accreditor asking "how are we doing
  on PLO-3?" wants one number first (the pass-rate badge on the
  collapsed PLO-3 row), *then* the option to drill into which CLOs
  contribute and which sections delivered them. A table shows
  everything at once; a tree lets you stop where your question stops.
- **Cheap empty states.** A PLO with no mappings renders as a single
  row with a muted pill ("No CLOs mapped yet"). In a matrix that's a
  blank column.

**Trade-off:** Matrices are better for spotting gaps ("which CLOs are
orphaned?"). We mitigate that in the Map-CLO modal — its dropdown is
pre-filtered to *unmapped* CLOs so the gap list is always one click
away.

---

## 2. The three-badge assessment display mode

**Decision:** Every tree node carries a single **pass-rate badge**
whose format is controlled by a **per-program** setting
(`assessment_display_mode`): `"binary"` → `S`/`U`, `"percentage"` →
`78%`, `"both"` → `S (78%)`.

**Why per-program and not per-institution?**
- Different departments have genuinely different reporting cultures.
  Nursing programs often accredit on binary mastery (Satisfactory /
  Unsatisfactory); engineering programs prefer raw percentages. One
  institution-wide switch forces a compromise nobody wants.
- The setting lives in `programs.extras` (PickleType JSON blob) so it
  costs no schema migration and can be overridden cheaply via
  `PUT /api/programs/<id>`.

**Why three modes, not two?**
- `both` is the *explainer mode*. When you're walking a dean through
  the dashboard you want "we render S/U because XX% passed" visible at
  a glance. When they're doing self-service later they'll flip to
  whichever single mode their report template uses.

**Why one badge per node, not sparklines or mini-charts?**
- A tree with a sparkline at every row is visually noisy — your eye
  can't pick out the failing PLO. A single coloured token (green / amber)
  is a faster scan.

See `formatAssessment()` in `static/plo_dashboard.js:30` for the
render table and `DEFAULT_PASS_THRESHOLD = 70`.

---

## 3. Draft/publish mapping workflow stays visible

**Decision:** The tree header shows a **version badge**
(`v2 · published` or `draft`). The Map-CLO modal footer has an
explicit **Publish Draft** button — publishing isn't implied by
closing the modal.

**Why keep the workflow surface-level?**
- PLO↔CLO mappings are the *audit trail* for accreditation. A user
  should never accidentally publish because they clicked away. Making
  "Publish" an explicit button and showing the version badge at all
  times means you always know whether you're looking at the version of
  record or at work-in-progress.
- The backend `publish_plo_mapping()` snapshots the PLO description
  into each entry (`plo_description_snapshot`) — so even if you edit a
  PLO template later, historical mappings stay faithful. The UI
  surfaces this as "editing a PLO doesn't bump the mapping version."

---

## 4. Term filter defaults to active, not "all"

**Decision:** The Term filter (`pickDefaultTerm()` in
`plo_dashboard.js:52`) defaults to the **first active term**, falling
back to most-recent by `start_date`. "All Terms" is an explicit
option, not the default.

**Why:**
- The common question is "how are we doing *this semester*?" Not "how
  are we doing across all of history?" Defaulting to all-terms makes
  the first number you see the least actionable one.
- Respecting the existing term-status infrastructure
  (`term_status === "ACTIVE"`) means a department chair who has
  already curated which term is "current" sees their choice reflected
  everywhere.

---

## 5. Three distinct empty states, three distinct messages

| Level | Condition | Message | Call to action |
| ----- | --------- | ------- | -------------- |
| Tree  | `plos.length === 0` | "No Program Outcomes defined for this program yet." | Opens the **New PLO** modal |
| PLO   | `plo.clos.length === 0` | "No CLOs mapped to this PLO yet." | Points at **Map CLO to PLO** |
| CLO   | `clo.sections.length === 0` | "No section assessments in the selected term." | Hints at the **Term** filter |

**Why three and not one generic "nothing here"?**
- Each empty state has a *different resolution path.* A missing PLO is
  solved by creating one; a missing CLO mapping is solved by opening a
  draft and linking; an empty section list is solved by changing the
  term filter (or waiting for instructors to submit). One generic
  message would tell the user *that* something's missing but not
  *which tool fixes it*.

---

## 6. Mini-panel on the program-admin dashboard is fire-and-forget

**Decision:** The PLO summary on the main program-admin dashboard
(`loadPloSummary()` in `static/program_dashboard.js`) runs *after* the
core dashboard renders, tolerates per-program fetch failures, and
shows a compact table rather than a mini-tree.

**Why not inline the tree?**
- The `/api/programs/<id>/plo-dashboard` endpoint walks
  mappings + section outcomes and joins across five tables per
  program. Doing that for every program in the institution before the
  dashboard paints would block the whole page on PLO latency.
  Rendering everything else first, then populating the PLO panel when
  it lands, keeps the perceived load time equal to today's.
- A per-program fetch-failure yields a placeholder row
  (`plo_count: "—"`) rather than blanking the whole panel — one stale
  program shouldn't hide the other nine.
- The panel's job is *"should I go look at the PLO dashboard?"* — a
  five-column summary table (Program · PLOs · Mapped CLOs · Mapping
  Status · Pass Rate) answers that. Drilldown belongs on the
  dedicated page.

---

## 7. PLO numbers are integers, not labels

**Decision:** `program_outcomes.plo_number` is `INTEGER NOT NULL`; the
UI renders it as `PLO-<n>` and the New-PLO form takes
`<input type="number" min="1">`.

**Why an integer and not a free-text label like "PLO-1a"?**
- **Sorting.** `ORDER BY plo_number` gives you PLO-1 through PLO-12
  in the right order. String labels give you PLO-1, PLO-10, PLO-11,
  PLO-2.
- **Uniqueness is cheap.** `(program_id, plo_number)` is a natural
  unique constraint. With free-text labels you'd need case-folded
  comparison and users would wonder why "PLO 1" ≠ "PLO-1".
- **Room to grow.** If a program later *does* need sub-lettered
  outcomes (PLO-1a, PLO-1b) that's a `sub_letter` column away.
  Going the other direction — from strings back to integers — would
  be a destructive migration.

---

## 8. Automated demo verifies via direct sqlite, not API reads

**Decision:** `demos/plo_dashboard_workflow.json` drives mutations
through the real API (`api_post`/`api_put`) but verifies results with
`sqlite3` queries in `post_commands`.

**Why not verify via `api_get`?**
- The JSON runner's `api_get` action doesn't capture the response
  body — you get a status code, not data you can assert on. Direct
  sqlite queries can assert `COUNT(*) = 1`, `version = 2`,
  `description CONTAINS 'capstone'`.
- Sqlite verification is **tamper-evident**. If the API layer has a
  bug that says "success" but doesn't actually persist, the sqlite
  check catches it. An API-only verification loop is self-referential.
- This also keeps the demo **deterministic across runs**. Rows are
  identified by stable business keys (`short_name='BIOL'`,
  `plo_number=5`) rather than by capturing auto-generated IDs from
  JSON responses.

The wrapper script `docs/workflow-walkthroughs/scripts/run_demo.py`
defaults to this JSON demo and `--env local` so the single command
`python docs/workflow-walkthroughs/scripts/run_demo.py --auto` hits
all four beats (create / edit / map / drilldown) with verification.
