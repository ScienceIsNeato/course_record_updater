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

    Required keys: program_id, institution_id, description.
    Optional keys: plo_number (auto-incremented if omitted).
    Returns the new PLO ID.

    Raises:
        ValueError: if required fields are missing.
    """
    # Auto-increment plo_number if not provided
    if "plo_number" not in data or data["plo_number"] is None:
        existing = database_service.get_program_outcomes(data.get("program_id", ""))
        max_num = max((p.get("plo_number", 0) for p in existing), default=0)
        data["plo_number"] = max_num + 1

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


def get_unmapped_clos(
    program_id: str, mapping_id: Optional[str] = None
) -> Dict[str, Any]:
    """Return CLOs in the program's courses that are NOT in the given mapping.

    If *mapping_id* is omitted, uses the current draft or latest published.

    Returns a dict with keys:
      - unmapped: List of unmapped CLO dicts
      - course_count: Number of courses linked to the program
      - total_clo_count: Total active CLOs found across all program courses
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
    total_clo_count = 0
    for course in courses:
        clos = database_service.get_course_outcomes(course["course_id"])
        for clo in clos:
            if clo.get("active", True):
                total_clo_count += 1
                if clo["outcome_id"] not in mapped_clo_ids:
                    unmapped.append({**clo, "course": course})

    return {
        "unmapped": unmapped,
        "course_count": len(courses),
        "total_clo_count": total_clo_count,
    }


# ---------------------------------------------------------------------------
# Cherry-picker helpers (Map CLO to PLO modal)
# ---------------------------------------------------------------------------


def _resolve_mapping(program_id: str) -> Optional[Dict[str, Any]]:
    """Resolve the current mapping (draft first, then latest published)."""
    mapping = database_service.get_plo_mapping_draft(program_id)
    if not mapping:
        mapping = database_service.get_latest_published_plo_mapping(program_id)
    return mapping


def get_plo_clo_picker(
    program_id: str, plo_id: str, term_id: Optional[str] = None
) -> Dict[str, Any]:
    """Return all program CLOs split by mapping status for a specific PLO.

    Used by the cherry-picker UI to show two panels:
      - mapped: CLOs currently linked to *this* PLO
      - available: CLOs not linked to this PLO (may be linked elsewhere)

    Each item in *available* includes ``mapped_to_plo_id`` when the CLO
    is already assigned to a different PLO in the same mapping.

    When *term_id* is provided the term-specific mapping is used first,
    falling back to the global (non-term) mapping.
    """
    mapping: Optional[Dict[str, Any]] = None

    # Prefer term-specific mapping when a term is selected
    if term_id:
        mapping = database_service.get_term_plo_mapping(program_id, term_id)

    # Fall back to draft → latest published (non-term)
    if not mapping:
        mapping = _resolve_mapping(program_id)

    mapped_to_this: set[str] = set()
    mapped_to_other: Dict[str, str] = {}  # clo_id → plo_id

    if mapping:
        for entry in mapping.get("entries", []):
            clo_id = entry.get("course_outcome_id")
            plo_oid = entry.get("program_outcome_id")
            if not clo_id:
                continue
            if str(plo_oid) == str(plo_id):
                mapped_to_this.add(clo_id)
            else:
                mapped_to_other[clo_id] = plo_oid

    courses = database_service.get_courses_by_program(program_id)
    mapped: List[Dict[str, Any]] = []
    available: List[Dict[str, Any]] = []
    total_clo_count = 0

    for course in courses:
        clos = database_service.get_course_outcomes(course["course_id"])
        for clo in clos:
            if not clo.get("active", True):
                continue
            total_clo_count += 1
            clo_data: Dict[str, Any] = {**clo, "course": course}

            if clo["outcome_id"] in mapped_to_this:
                mapped.append(clo_data)
            else:
                if clo["outcome_id"] in mapped_to_other:
                    clo_data["mapped_to_plo_id"] = mapped_to_other[clo["outcome_id"]]
                available.append(clo_data)

    return {
        "mapped": mapped,
        "available": available,
        "course_count": len(courses),
        "total_clo_count": total_clo_count,
    }


def sync_plo_clo_mappings(
    program_id: str,
    plo_id: str,
    clo_ids: List[str],
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Bulk-sync CLO mappings for a specific PLO in the current draft.

    Creates a draft if none exists, removes all existing entries for
    *plo_id*, then adds an entry for each CLO in *clo_ids*.  If any
    of the requested CLOs were previously mapped to a *different* PLO
    in this draft they are reassigned automatically.

    Returns the refreshed mapping dict.
    """
    draft = get_or_create_draft(program_id, user_id)
    mapping_id = draft["id"]

    # Re-fetch to guarantee fresh entry list after draft creation
    fresh = database_service.get_plo_mapping(mapping_id)
    entries = fresh.get("entries", []) if fresh else []

    clo_ids_set = {str(cid) for cid in clo_ids}

    # Remove entries that conflict:
    #   1. Current entries for this PLO (will be re-created)
    #   2. Entries mapping any of the requested CLOs to other PLOs
    for entry in entries:
        eid = entry.get("id")
        poid = str(entry.get("program_outcome_id", ""))
        coid = str(entry.get("course_outcome_id", ""))
        if poid == str(plo_id) or coid in clo_ids_set:
            database_service.remove_plo_mapping_entry(eid)

    # Add fresh entries
    for clo_id in clo_ids:
        database_service.add_plo_mapping_entry(mapping_id, plo_id, clo_id)

    updated = database_service.get_plo_mapping(mapping_id)
    logger.info(
        "Synced %d CLOs to PLO %s in mapping %s",
        len(clo_ids),
        plo_id,
        mapping_id,
    )
    return updated or {}


def save_term_plo_clo_mappings(
    program_id: str,
    term_id: str,
    plo_id: str,
    clo_ids: List[str],
    user_id: str,
) -> Dict[str, Any]:
    """Save PLO-CLO mappings for a specific term (auto-published).

    Unlike :func:`sync_plo_clo_mappings` this bypasses the draft workflow.
    The mapping is stored as published so the dashboard tree reflects
    changes immediately.

    Returns the refreshed term-specific mapping dict.
    """
    result = database_service.save_term_plo_mapping(
        program_id, term_id, plo_id, clo_ids, user_id
    )
    logger.info(
        "Saved term-specific mapping for PLO %s, term %s, program %s (%d CLOs)",
        plo_id,
        term_id,
        program_id,
        len(clo_ids),
    )
    return result
