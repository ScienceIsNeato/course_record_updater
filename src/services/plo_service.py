"""Program Learning Outcome (PLO) service layer.

Provides business-logic operations for PLO template management and
the versioned PLO↔CLO mapping draft/publish workflow.  Thin wrapper
around database_service that adds permission context, validation,
and audit logging.
"""

from typing import Any, Dict, List, Optional

from src.database import database_service
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


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


def get_program_outcome(plo_id: str) -> Optional[Dict[str, Any]]:
    """Return a single PLO by ID, or None."""
    return database_service.get_program_outcome(plo_id)


def create_program_outcome(data: Dict[str, Any]) -> str:
    """Create a new PLO template.

    Required keys: program_id, institution_id, plo_number, description.
    Returns the new PLO ID.

    Raises:
        ValueError: if required fields are missing.
    """
    required = ("program_id", "institution_id", "plo_number", "description")
    missing = [f for f in required if f not in data or data[f] is None]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    plo_id = database_service.create_program_outcome(data)
    logger.info("Created PLO %s for program %s", plo_id, data["program_id"])
    return plo_id


def update_program_outcome(plo_id: str, updates: Dict[str, Any]) -> bool:
    """Update a PLO template.  Returns True on success."""
    if not updates:
        raise ValueError("No update data provided")
    result = database_service.update_program_outcome(plo_id, updates)
    if result:
        logger.info("Updated PLO %s", plo_id)
    return result


def delete_program_outcome(plo_id: str) -> bool:
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
            raise ValueError(f"Mapping {mapping_id} not found")
        if str(mapping.get("program_id")) != str(program_id):
            raise ValueError(f"Mapping {mapping_id} not found")
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
    courses = []
    for course in courses_raw:
        clos = database_service.get_course_outcomes(course["course_id"])
        active_clos = [c for c in clos if c.get("active", True)]
        courses.append({**course, "clos": active_clos})

    # Build the matrix grid  (plo_id → {clo_outcome_id → entry_id})
    entries = mapping.get("entries", []) if mapping else []
    entry_lookup: Dict[str, Dict[str, Optional[str]]] = {}
    for plo in plos:
        entry_lookup[plo["id"]] = {}
    for entry in entries:
        plo_id = entry.get("program_outcome_id")
        clo_id = entry.get("course_outcome_id")
        if plo_id in entry_lookup:
            entry_lookup[plo_id][clo_id] = entry.get("id")

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
) -> Dict[str, Any]:
    """Build the hierarchical PLO → CLO → section-outcome tree for the dashboard.

    For each active PLO in the program, gathers the CLO templates mapped to it
    (using the latest published mapping, falling back to the draft) and then
    attaches the section-level assessment records for those CLOs, scoped to
    *term_id* when given.

    Assessment data is aggregated per-PLO (students_took / students_passed
    summed across all contributing section outcomes) so the UI can show a
    single pass-rate badge at each tree level before the user drills in.

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
    entries = mapping.get("entries", []) if mapping else []

    # Build plo_id → [clo_id, ...] and collect the universe of mapped CLOs
    plo_to_clos: Dict[str, List[str]] = {p["id"]: [] for p in plos}
    all_clo_ids: set[str] = set()
    for entry in entries:
        plo_id = entry.get("program_outcome_id")
        clo_id = entry.get("course_outcome_id")
        if plo_id in plo_to_clos and clo_id:
            plo_to_clos[plo_id].append(clo_id)
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

    def _aggregate(records: List[Dict[str, Any]]) -> Dict[str, Any]:
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

    tree: List[Dict[str, Any]] = []
    for plo in plos:
        clo_nodes: List[Dict[str, Any]] = []
        for clo_id in plo_to_clos.get(plo["id"], []):
            secs = sections_by_clo.get(clo_id, [])
            meta = clo_meta.get(clo_id, {"outcome_id": clo_id})
            clo_nodes.append(
                {
                    **meta,
                    "aggregate": _aggregate(secs),
                    "sections": secs,
                }
            )
        # Aggregate across all sections of all CLOs under this PLO
        all_plo_sections = [s for clo in clo_nodes for s in clo["sections"]]
        tree.append(
            {
                **plo,
                "aggregate": _aggregate(all_plo_sections),
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
