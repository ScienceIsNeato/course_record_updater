"""Program Learning Outcome (PLO) service layer.

Provides business-logic operations for PLO template management and
the versioned PLO↔CLO mapping draft/publish workflow.  Thin wrapper
around database_service that adds permission context, validation,
and audit logging.
"""

from typing import Any, Dict, List, Optional, Tuple, cast

from src.database import database_service
from src.utils.logging_config import get_logger
from src.utils.term_utils import get_term_status

logger = get_logger(__name__)
MAPPING_NOT_FOUND_MSG = "Mapping {mapping_id} not found"


def _mapping_entries(mapping: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return mapping entries as a typed list of dicts."""
    if not mapping:
        return []
    raw_entries = mapping.get("entries")
    if not isinstance(raw_entries, list):
        return []
    entry_values: List[Any] = cast(List[Any], raw_entries)
    return [
        cast(Dict[str, Any], entry) for entry in entry_values if isinstance(entry, dict)
    ]


# ---------------------------------------------------------------------------
# PLO template operations
# ---------------------------------------------------------------------------


def list_program_outcomes(
    program_id: str, *, include_inactive: bool = False
) -> List[Dict[str, Any]]:
    """Return PLOs for a program, ordered by plo_number."""
    return database_service.get_program_outcomes(
        program_id, include_inactive=include_inactive
    )


def get_program_outcome(  # noqa: ambiguity-mine - service API intentionally mirrors storage verb
    plo_id: str,
) -> Optional[Dict[str, Any]]:
    """Return a single PLO by ID, or None."""
    return database_service.get_program_outcome(plo_id)


def create_program_outcome(  # noqa: ambiguity-mine - service API intentionally mirrors storage verb
    data: Dict[str, Any],
) -> str:
    """Create a new PLO template.

    Required keys: program_id, institution_id, description.
    ``plo_number`` is optional – when omitted (or ``None``) the next
    available number for the program is assigned automatically.
    Returns the new PLO ID.

    Raises:
        ValueError: if required fields are missing.
    """
    required = ("program_id", "institution_id", "description")
    missing = [f for f in required if f not in data or data[f] is None]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    # Auto-assign next PLO number when not provided
    if data.get("plo_number") is None:
        existing = database_service.get_program_outcomes(
            data["program_id"], include_inactive=True
        )
        max_num = max((p.get("plo_number", 0) or 0 for p in existing), default=0)
        data["plo_number"] = max_num + 1

    plo_id = database_service.create_program_outcome(data)
    logger.info("Created PLO %s for program %s", plo_id, data["program_id"])
    return plo_id


def update_program_outcome(  # noqa: ambiguity-mine - service API intentionally mirrors storage verb
    plo_id: str, updates: Dict[str, Any]
) -> bool:
    """Update a PLO template.  Returns True on success."""
    if not updates:
        raise ValueError("No update data provided")
    result = database_service.update_program_outcome(plo_id, updates)
    if result:
        logger.info("Updated PLO %s", plo_id)
    return result


def delete_program_outcome(  # noqa: ambiguity-mine - service API intentionally mirrors storage verb
    plo_id: str,
) -> bool:
    """Soft-delete a PLO template.  Returns True on success."""
    result = database_service.delete_program_outcome(plo_id)
    if result:
        logger.info("Soft-deleted PLO %s", plo_id)
    return result


# ---------------------------------------------------------------------------
# PLO Mapping (draft / publish) operations
# ---------------------------------------------------------------------------


def get_or_create_draft(
    program_id: str, user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Return the current draft mapping for a program, creating one if needed.

    When a published version exists the new draft is pre-populated with its
    entries so the user starts from the last-published state.
    """
    draft = database_service.get_or_create_plo_mapping_draft(program_id, user_id)
    logger.info("Draft mapping %s for program %s", draft["id"], program_id)
    return draft


def get_draft(program_id: str) -> Optional[Dict[str, Any]]:
    """Return the draft mapping for a program, or None."""
    return database_service.get_plo_mapping_draft(program_id)


def add_mapping_entry(
    mapping_id: str,
    program_outcome_id: str,
    course_outcome_id: str,
) -> str:
    """Add a PLO↔CLO link to a draft mapping.  Returns the entry ID.

    Raises:
        ValueError: if any ID is empty.
    """
    if not all([mapping_id, program_outcome_id, course_outcome_id]):
        raise ValueError(
            "mapping_id, program_outcome_id, and course_outcome_id are required"
        )
    entry_id = database_service.add_plo_mapping_entry(
        mapping_id, program_outcome_id, course_outcome_id
    )
    logger.info(
        "Added mapping entry %s (PLO %s → CLO %s) in mapping %s",
        entry_id,
        program_outcome_id,
        course_outcome_id,
        mapping_id,
    )
    return entry_id


def remove_mapping_entry(entry_id: str) -> bool:
    """Remove a PLO↔CLO link from a draft mapping."""
    result = database_service.remove_plo_mapping_entry(entry_id)
    if result:
        logger.info("Removed mapping entry %s", entry_id)
    return result


def publish_mapping(
    mapping_id: str, description: Optional[str] = None
) -> Dict[str, Any]:
    """Publish a draft mapping, assigning the next version number.

    PLO description snapshots are frozen at publish time so historical
    versions preserve the text that was current when the map was published.

    Raises:
        ValueError: if the mapping is not in draft status.
    """
    published = database_service.publish_plo_mapping(mapping_id, description)
    logger.info(
        "Published mapping %s as version %s",
        published["id"],
        published["version"],
    )
    return published


def discard_draft(mapping_id: str) -> bool:
    """Delete a draft mapping and all its entries."""
    result = database_service.discard_plo_mapping_draft(mapping_id)
    if result:
        logger.info("Discarded draft mapping %s", mapping_id)
    return result


def get_mapping(mapping_id: str) -> Optional[Dict[str, Any]]:
    """Return a mapping (draft or published) by ID."""
    return database_service.get_plo_mapping(mapping_id)


def get_mapping_by_version(program_id: str, version: int) -> Optional[Dict[str, Any]]:
    """Return a specific published version for a program."""
    return database_service.get_plo_mapping_by_version(program_id, version)


def get_published_mappings(program_id: str) -> List[Dict[str, Any]]:
    """Return all published mapping versions for a program."""
    return database_service.get_published_plo_mappings(program_id)


def get_latest_published_mapping(
    program_id: str,
) -> Optional[Dict[str, Any]]:
    """Return the highest-versioned published mapping, or None."""
    return database_service.get_latest_published_plo_mapping(program_id)


# ---------------------------------------------------------------------------
# Matrix / cross-cutting queries
# ---------------------------------------------------------------------------


def get_mapping_matrix(
    program_id: str,
    mapping_id: Optional[str] = None,
    version: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a PLO × CLO matrix for the mapping UI.

    Resolution order for which mapping to use:
    1. Explicit *mapping_id* (draft or published)
    2. Explicit *version* number
    3. Current draft (if one exists)
    4. Latest published version

    Returns a dict with:
    - mapping: the resolved mapping dict (or None)
    - plos: list of active PLOs for the program
    - courses: list of courses with their CLOs
    - matrix: dict  ``{plo_id: {clo_id: entry_id | None}}``

    Raises:
        ValueError: when an explicit mapping_id or version is given
            but does not resolve to an existing mapping.
    """
    # Resolve the target mapping
    mapping: Optional[Dict[str, Any]] = None
    if mapping_id:
        mapping = database_service.get_plo_mapping(mapping_id)
        if not mapping:
            raise ValueError(MAPPING_NOT_FOUND_MSG.format(mapping_id=mapping_id))
        if str(mapping.get("program_id")) != str(program_id):
            raise ValueError(MAPPING_NOT_FOUND_MSG.format(mapping_id=mapping_id))
    elif version is not None:
        mapping = database_service.get_plo_mapping_by_version(program_id, version)
        if not mapping:
            raise ValueError(f"Mapping version {version} not found")
    else:
        mapping = database_service.get_plo_mapping_draft(program_id)
        if not mapping:
            mapping = database_service.get_latest_published_plo_mapping(program_id)

    # PLOs
    plos = database_service.get_program_outcomes(program_id)

    # Courses in the program, each with their CLOs
    courses_raw = database_service.get_courses_by_program(program_id)
    courses: List[Dict[str, Any]] = []
    for course in courses_raw:
        clos = database_service.get_course_outcomes(course["course_id"])
        active_clos = [c for c in clos if c.get("active", True)]
        courses.append({**course, "clos": active_clos})

    # Build the matrix grid  (plo_id → {clo_outcome_id → entry_id})
    entries = _mapping_entries(mapping)
    entry_lookup: Dict[str, Dict[str, Optional[str]]] = {}
    for plo in plos:
        entry_lookup[plo["id"]] = {}
    for entry in entries:
        plo_id = entry.get("program_outcome_id")
        clo_id = entry.get("course_outcome_id")
        if (
            isinstance(plo_id, str)
            and isinstance(clo_id, str)
            and plo_id in entry_lookup
        ):
            entry_id = entry.get("id")
            entry_lookup[plo_id][clo_id] = str(entry_id) if entry_id else None

    return {
        "mapping": mapping,
        "plos": plos,
        "courses": courses,
        "matrix": entry_lookup,
    }


def get_plo_dashboard_tree(
    program_id: str,
    institution_id: str,
    term_id: Optional[str] = None,
    plo_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the hierarchical PLO → CLO → section-outcome tree for the dashboard.

    For each active PLO in the program, or just the requested ``plo_id`` when
    provided, gathers the CLO templates mapped to it (using the latest
    published mapping, falling back to the draft) and then attaches the
    section-level assessment records for those CLOs, scoped to ``term_id``
    when given.

    Assessment data is aggregated per-PLO (students_took / students_passed
    summed across all contributing section outcomes) so the UI can show a
    single pass-rate badge at each tree level before the user drills in.

    Unknown ``plo_id`` values are not treated as errors; the mapping metadata
    is still returned, but the ``plos`` list is empty.

    Returns::

        {
            "mapping": <mapping dict | None>,
            "mapping_status": "published" | "draft" | "none",
            "assessment_display_mode": "binary" | "percentage" | "both",
            "term_id": <echo>,
            "plos": [
                {
                    "id": ..., "plo_number": ..., "description": ...,
                    "aggregate": {"students_took": int, "students_passed": int,
                                  "pass_rate": float | None,
                                  "section_count": int},
                    "clos": [
                        {
                            "outcome_id": ..., "clo_number": ...,
                            "description": ..., "course_number": ...,
                            "aggregate": {...},
                            "sections": [<section-outcome dict>, ...]
                        }
                    ]
                }
            ]
        }
    """
    program = database_service.get_program_by_id(program_id)
    display_mode = program.get("assessment_display_mode", "both") if program else "both"

    # Resolve mapping: prefer latest published (it is the version of record
    # for assessment rollups); fall back to current draft so admins see
    # work-in-progress before their first publish.
    mapping = database_service.get_latest_published_plo_mapping(program_id)
    mapping_status = "published"
    if not mapping:
        mapping = database_service.get_plo_mapping_draft(program_id)
        mapping_status = "draft" if mapping else "none"

    plos = database_service.get_program_outcomes(program_id)
    if plo_id:
        plos = [p for p in plos if p["id"] == plo_id]
    entries = _mapping_entries(mapping)

    # Build plo_id → [clo_id, ...] and collect the universe of mapped CLOs
    plo_to_clos: Dict[str, List[str]] = {p["id"]: [] for p in plos}
    all_clo_ids: set[str] = set()
    for entry in entries:
        entry_plo_id = entry.get("program_outcome_id")
        clo_id = entry.get("course_outcome_id")
        if (
            isinstance(entry_plo_id, str)
            and isinstance(clo_id, str)
            and entry_plo_id in plo_to_clos
        ):
            plo_to_clos[entry_plo_id].append(clo_id)
            all_clo_ids.add(clo_id)

    # Fetch all section outcomes for the mapped CLOs in one batched query.
    section_outcomes: List[Dict[str, Any]] = []
    if all_clo_ids:
        section_outcomes = database_service.get_section_outcomes_by_criteria(
            institution_id=institution_id,
            program_id=program_id,
            term_id=term_id,
            outcome_ids=list(all_clo_ids),
        )

    # Index section outcomes by CLO template id → list of section records
    sections_by_clo: Dict[str, List[Dict[str, Any]]] = {}
    for so in section_outcomes:
        clo_id = so.get("outcome_id")
        if clo_id:
            sections_by_clo.setdefault(clo_id, []).append(so)

    # Gather CLO template metadata (clo_number, description, course) so the
    # tree shows labels even when no section outcome exists yet.
    clo_meta: Dict[str, Dict[str, Any]] = {}
    courses = database_service.get_courses_by_program(program_id)
    for course in courses:
        for clo in database_service.get_course_outcomes(course["course_id"]):
            clo_meta[clo["outcome_id"]] = {
                "outcome_id": clo["outcome_id"],
                "clo_number": clo.get("clo_number"),
                "description": clo.get("description"),
                "course_id": course.get("course_id"),
                "course_number": course.get("course_number"),
                "course_title": course.get("course_title"),
            }

    tree: List[Dict[str, Any]] = []
    for plo in plos:
        clo_nodes: List[Dict[str, Any]] = []
        for clo_id in plo_to_clos.get(plo["id"], []):
            secs = sections_by_clo.get(clo_id, [])
            meta = clo_meta.get(clo_id, {"outcome_id": clo_id})
            clo_nodes.append(
                {
                    **meta,
                    "aggregate": _aggregate_section_outcomes(secs),
                    "sections": secs,
                }
            )
        # Aggregate across all sections of all CLOs under this PLO
        all_plo_sections = [s for clo in clo_nodes for s in clo["sections"]]
        tree.append(
            {
                **plo,
                "aggregate": _aggregate_section_outcomes(all_plo_sections),
                "clo_count": len(clo_nodes),
                "clos": clo_nodes,
            }
        )

    return {
        "mapping": mapping,
        "mapping_status": mapping_status,
        "assessment_display_mode": display_mode,
        "term_id": term_id,
        "program_id": program_id,
        "plos": tree,
    }


def get_unmapped_clos(
    program_id: str, mapping_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Return CLOs in the program's courses that are NOT in the given mapping.

    If *mapping_id* is omitted, uses the current draft or latest published.
    """
    # Resolve mapping
    mapping: Optional[Dict[str, Any]] = None
    if mapping_id:
        mapping = database_service.get_plo_mapping(mapping_id)
        if mapping and str(mapping.get("program_id")) != str(program_id):
            mapping = None  # Mapping doesn't belong to this program
    else:
        mapping = database_service.get_plo_mapping_draft(program_id)
        if not mapping:
            mapping = database_service.get_latest_published_plo_mapping(program_id)

    mapped_clo_ids: set[str] = set()
    if mapping:
        for entry in mapping.get("entries", []):
            cid = entry.get("course_outcome_id")
            if cid:
                mapped_clo_ids.add(cid)

    # Gather all active CLOs across the program's courses
    courses = database_service.get_courses_by_program(program_id)
    unmapped: List[Dict[str, Any]] = []
    for course in courses:
        clos = database_service.get_course_outcomes(course["course_id"])
        for clo in clos:
            if clo.get("active", True) and clo["outcome_id"] not in mapped_clo_ids:
                unmapped.append({**clo, "course": course})

    return unmapped


# ---------------------------------------------------------------------------
# Trend data (multi-term time series)
# ---------------------------------------------------------------------------


def _build_term_metadata(
    all_terms: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convert raw term rows into metadata dicts with ``is_current`` flag."""
    meta: List[Dict[str, Any]] = []
    for t in all_terms:
        status = get_term_status(
            str(t.get("start_date", "")),
            str(t.get("end_date", "")),
        )
        meta.append(
            {
                "term_id": t.get("id") or t.get("term_id"),
                "term_name": t.get("name") or t.get("term_name", ""),
                "start_date": t.get("start_date", ""),
                "is_current": status == "ACTIVE",
            }
        )
    return meta


def _resolve_plo_clo_mapping(
    program_id: str,
    plos: List[Dict[str, Any]],
) -> Tuple[Optional[int], Dict[str, List[str]], set[str], Dict[str, str]]:
    """Resolve latest published mapping and build PLO → CLO index.

    Returns:
        (mapping_version, plo_to_clos, all_clo_ids, plo_snapshots)
    """
    mapping = database_service.get_latest_published_plo_mapping(program_id)
    mapping_version = mapping.get("version") if mapping else None
    entries = _mapping_entries(mapping)

    plo_to_clos: Dict[str, List[str]] = {p["id"]: [] for p in plos}
    all_clo_ids: set[str] = set()
    plo_snapshots: Dict[str, str] = {}

    for entry in entries:
        plo_id = entry.get("program_outcome_id")
        clo_id = entry.get("course_outcome_id")
        if (
            isinstance(plo_id, str)
            and isinstance(clo_id, str)
            and plo_id in plo_to_clos
        ):
            plo_to_clos[plo_id].append(clo_id)
            all_clo_ids.add(clo_id)
            snap = entry.get("plo_description_snapshot")
            if isinstance(snap, str) and plo_id not in plo_snapshots:
                plo_snapshots[plo_id] = snap

    return mapping_version, plo_to_clos, all_clo_ids, plo_snapshots


def _index_outcomes_by_clo_term(
    section_outcomes: List[Dict[str, Any]],
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Index section outcomes into ``{clo_id: {term_id: [records]}}``."""
    by_clo_term: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for so in section_outcomes:
        clo_id = so.get("outcome_id")
        so_term_id = _extract_term_id(so)
        if clo_id and so_term_id:
            by_clo_term.setdefault(clo_id, {}).setdefault(so_term_id, []).append(so)
    return by_clo_term


def _build_clo_metadata(
    program_id: str,
) -> Dict[str, Dict[str, Any]]:
    """Build ``{clo_id: {outcome_id, clo_number, description, course_number}}``."""
    clo_meta: Dict[str, Dict[str, Any]] = {}
    courses = database_service.get_courses_by_program(program_id)
    for course in courses:
        for clo in database_service.get_course_outcomes(course["course_id"]):
            clo_meta[clo["outcome_id"]] = {
                "outcome_id": clo["outcome_id"],
                "clo_number": clo.get("clo_number"),
                "description": clo.get("description"),
                "course_number": course.get("course_number"),
            }
    return clo_meta


def _aggregate_section_outcomes(
    records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Aggregate section outcomes into a single trend data point."""
    took = 0
    passed = 0
    counted = 0
    for r in records:
        t = r.get("students_took")
        p = r.get("students_passed")
        if isinstance(t, int) and t > 0 and isinstance(p, int):
            took += t
            passed += p
            counted += 1
    rate = round(passed / took * 100, 1) if took > 0 else None
    return {
        "students_took": took,
        "students_passed": passed,
        "pass_rate": rate,
        "section_count": len(records),
        "sections_with_data": counted,
    }


def _build_trend_point(
    records: List[Dict[str, Any]],
    term_id: str,
) -> Optional[Dict[str, Any]]:
    """Return an aggregated trend point for *records*, or ``None`` if empty."""
    if not records:
        return None
    point = _aggregate_section_outcomes(records)
    point["term_id"] = term_id
    return point


def _detect_discontinuities(
    clo_ids: List[str],
    clo_meta: Dict[str, Dict[str, Any]],
    by_clo_term: Dict[str, Dict[str, List[Dict[str, Any]]]],
    term_meta: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Detect CLO composition changes between consecutive terms.

    Compares the set of CLOs that have assessment data in each term.
    When the set changes between term N and N+1, emits a discontinuity
    marker recording which CLOs were added/removed.

    Returns a list of discontinuity dicts, each with::

        {
            "term_index": int,       # index of the LATER term
            "term_id": str,
            "type": "clo_change",
            "added": [{"clo_id", "label"}],  # CLOs new in this term
            "removed": [{"clo_id", "label"}] # CLOs gone from prev term
        }
    """
    discontinuities: List[Dict[str, Any]] = []

    def _clo_label(clo_id: str) -> str:
        meta = clo_meta.get(clo_id, {})
        course = meta.get("course_number", "?")
        num = meta.get("clo_number", "?")
        return f"{course}/{num}"

    prev_active: Optional[set[str]] = None
    for idx, tm in enumerate(term_meta):
        tid = tm["term_id"]
        active = {cid for cid in clo_ids if by_clo_term.get(cid, {}).get(tid)}

        if prev_active is not None and active != prev_active:
            added = active - prev_active
            removed = prev_active - active
            if added or removed:
                discontinuities.append(
                    {
                        "term_index": idx,
                        "term_id": tid,
                        "type": "clo_change",
                        "added": [
                            {"clo_id": c, "label": _clo_label(c)} for c in sorted(added)
                        ],
                        "removed": [
                            {"clo_id": c, "label": _clo_label(c)}
                            for c in sorted(removed)
                        ],
                    }
                )

        # Only start tracking after the first term with any data
        if active or prev_active is not None:
            prev_active = active

    return discontinuities


def _assemble_plo_trends(
    plos: List[Dict[str, Any]],
    plo_to_clos: Dict[str, List[str]],
    clo_meta: Dict[str, Dict[str, Any]],
    by_clo_term: Dict[str, Dict[str, List[Dict[str, Any]]]],
    term_meta: List[Dict[str, Any]],
    plo_snapshots: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Assemble per-PLO and per-CLO trend arrays."""
    plo_results: List[Dict[str, Any]] = []
    for plo in plos:
        clo_ids = plo_to_clos.get(plo["id"], [])

        # CLO-level trends
        clo_trends = _build_clo_trends(clo_ids, clo_meta, by_clo_term, term_meta)

        # PLO-level trend (aggregate across all CLOs per term)
        plo_trend_points: List[Optional[Dict[str, Any]]] = []
        for tm in term_meta:
            tid = tm["term_id"]
            all_records: List[Dict[str, Any]] = []
            for clo_id in clo_ids:
                all_records.extend(by_clo_term.get(clo_id, {}).get(tid, []))
            plo_trend_points.append(_build_trend_point(all_records, tid))

        # Detect curriculum changes (CLO composition shifts between terms)
        discontinuities = _detect_discontinuities(
            clo_ids, clo_meta, by_clo_term, term_meta
        )

        plo_results.append(
            {
                "id": plo["id"],
                "plo_number": plo.get("plo_number"),
                "description": plo_snapshots.get(plo["id"], plo.get("description")),
                "trend": plo_trend_points,
                "clos": clo_trends,
                "discontinuities": discontinuities,
            }
        )
    return plo_results


def _build_clo_trends(
    clo_ids: List[str],
    clo_meta: Dict[str, Dict[str, Any]],
    by_clo_term: Dict[str, Dict[str, List[Dict[str, Any]]]],
    term_meta: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build per-CLO trend arrays across all terms."""
    clo_trends: List[Dict[str, Any]] = []
    for clo_id in clo_ids:
        meta = clo_meta.get(clo_id, {"outcome_id": clo_id})
        clo_trend_points: List[Optional[Dict[str, Any]]] = []
        for tm in term_meta:
            tid = tm["term_id"]
            records = by_clo_term.get(clo_id, {}).get(tid, [])
            clo_trend_points.append(_build_trend_point(records, tid))
        clo_trends.append({**meta, "trend": clo_trend_points})
    return clo_trends


def get_plo_trend_data(
    program_id: str,
    institution_id: str,
) -> Dict[str, Any]:
    """Build multi-term trend data for a program's PLO dashboard.

    Uses the **current** published mapping as a "lens" to look back through
    all historical terms.  This means the mapping is fixed (today's PLO↔CLO
    links), but assessment data comes from each term independently.

    Defensive design against data volatility:
    - Queries by CLO IDs directly (skips ``course_programs`` join issues).
    - Uses ``null`` for terms where a CLO had no data (not ``0``).
    - Includes ``is_current`` flag for in-progress terms.
    - Carries ``plo_description_snapshot`` from mapping entries when available.

    Returns::

        {
            "program_id": str,
            "mapping_version": int | None,
            "terms": [
                {"term_id": str, "term_name": str, "is_current": bool}, ...
            ],
            "plos": [
                {
                    "id": str, "plo_number": int, "description": str,
                    "trend": [
                        {"term_id": str, "pass_rate": float | None,
                         "students_took": int, "students_passed": int,
                         "section_count": int} | None, ...
                    ],
                    "clos": [
                        {
                            "outcome_id": str, "clo_number": str,
                            "description": str, "course_number": str,
                            "trend": [ ... ]   # same shape per term
                        }, ...
                    ]
                }, ...
            ]
        }
    """
    # 1. Get all terms, sorted chronologically (oldest first for charting)
    all_terms = database_service.get_all_terms(institution_id)
    all_terms.sort(key=lambda t: t.get("start_date", ""))

    if not all_terms:
        return {
            "program_id": program_id,
            "mapping_version": None,
            "terms": [],
            "plos": [],
        }

    term_meta = _build_term_metadata(all_terms)
    term_ids = [tm["term_id"] for tm in term_meta]

    # 2. Resolve mapping → PLO↔CLO associations
    plos = database_service.get_program_outcomes(program_id)
    mapping_version, plo_to_clos, all_clo_ids, plo_snapshots = _resolve_plo_clo_mapping(
        program_id, plos
    )

    # 3. Fetch ALL section outcomes across ALL terms in one query
    all_section_outcomes: List[Dict[str, Any]] = []
    if all_clo_ids and term_ids:
        all_section_outcomes = database_service.get_section_outcomes_by_criteria(
            institution_id=institution_id,
            outcome_ids=list(all_clo_ids),
            term_ids=term_ids,
        )

    # 4. Index by (clo_id, term_id) and build CLO metadata
    by_clo_term = _index_outcomes_by_clo_term(all_section_outcomes)
    clo_meta = _build_clo_metadata(program_id)

    # 5. Assemble trend results
    plo_results = _assemble_plo_trends(
        plos, plo_to_clos, clo_meta, by_clo_term, term_meta, plo_snapshots
    )

    return {
        "program_id": program_id,
        "mapping_version": mapping_version,
        "terms": term_meta,
        "plos": plo_results,
    }


def _extract_term_id(section_outcome: Dict[str, Any]) -> Optional[str]:
    """Extract term_id from a section outcome's nested relationships.

    The ``to_dict`` serialisation nests the offering's term under
    ``_section._offering.term_id`` (or similar paths).  We walk the
    common shapes to find the term identifier.
    """
    # Direct term_id on the section outcome (simplest)
    tid = section_outcome.get("term_id")
    if tid:
        return str(tid)

    # Nested: _section → _offering → term_id
    sec: Dict[str, Any] = (
        section_outcome.get("_section") or section_outcome.get("section") or {}
    )
    off: Dict[str, Any] = sec.get("_offering") or sec.get("offering") or {}
    tid = off.get("term_id")
    if tid:
        return str(tid)

    # Nested: _offering → term_id (flatter serialisation)
    off2: Dict[str, Any] = (
        section_outcome.get("_offering") or section_outcome.get("offering") or {}
    )
    tid = off2.get("term_id")
    if tid:
        return str(tid)

    # Nested term object
    term: Dict[str, Any] = (
        off.get("_term")
        or off.get("term")
        or off2.get("_term")
        or off2.get("term")
        or {}
    )
    tid = term.get("id") or term.get("term_id")
    if tid:
        return str(tid)

    return None
