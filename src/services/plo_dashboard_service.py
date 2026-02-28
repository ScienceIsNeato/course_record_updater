"""PLO Dashboard service layer.

Aggregates hierarchical program-learning-outcome data for the dashboard:
Program → PLO → CLO → CourseSection, with assessment data at each level.
"""

from typing import Any, Dict, List, Optional, Tuple

from src.database import database_service
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Assessment display modes stored in program.extras["plo_assessment_display"]
DISPLAY_PERCENTAGE = "percentage"
DISPLAY_BINARY = "binary"
DISPLAY_BOTH = "both"
DEFAULT_DISPLAY_MODE = DISPLAY_PERCENTAGE
BINARY_PASS_THRESHOLD = 0.70  # 70% threshold for S/U determination


def get_assessment_display_mode(program: Dict[str, Any]) -> str:
    """Return the assessment display mode for a program.

    Reads from ``program.extras["plo_assessment_display"]``.
    Falls back to ``"percentage"`` when unset.
    """
    # to_dict() flattens extras into the top-level dict, so check both
    extras = program.get("extras") or {}
    mode = program.get("plo_assessment_display") or extras.get(
        "plo_assessment_display", DEFAULT_DISPLAY_MODE
    )
    if mode not in (DISPLAY_PERCENTAGE, DISPLAY_BINARY, DISPLAY_BOTH):
        return DEFAULT_DISPLAY_MODE
    return mode


def _build_section_node(so: Dict[str, Any]) -> Dict[str, Any]:
    """Build a section-level node from a section outcome record."""
    section = so.get("_section") or so.get("section") or {}
    instructor = so.get("_instructor") or section.get("instructor") or {}
    instructor_name = (
        " ".join(
            filter(
                None,
                [instructor.get("first_name"), instructor.get("last_name")],
            )
        )
        or "Unassigned"
    )
    return {
        "section_outcome_id": so.get("id"),
        "section_id": section.get("section_id") or section.get("id", ""),
        "section_number": section.get("section_number", ""),
        "instructor_name": instructor_name,
        "students_took": so.get("students_took"),
        "students_passed": so.get("students_passed"),
        "assessment_tool": so.get("assessment_tool"),
        "status": so.get("status", ""),
    }


def _aggregate_assessment_nodes(
    nodes: List[Dict[str, Any]],
) -> Tuple[Optional[int], Optional[int], bool]:
    """Aggregate took/passed counts from child nodes.

    Works for both section-level and CLO-level aggregation.

    Returns (agg_took, agg_passed, has_data).
    """
    agg_took = 0
    agg_passed = 0
    has_data = False
    for node in nodes:
        if node["students_took"] is not None:
            agg_took += node["students_took"]
            passed = node["students_passed"]
            agg_passed += passed if passed is not None else 0
            has_data = True
    if has_data:
        return agg_took, agg_passed, True
    return None, None, False


def _build_clo_node(
    entry: Dict[str, Any],
    clo_lookup: Dict[str, Dict[str, Any]],
    so_by_outcome: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Build a CLO-level node from a mapping entry."""
    clo_id = entry.get("course_outcome_id", "")
    clo_info = clo_lookup.get(clo_id, {})
    course_info = clo_info.get("course", {})

    section_nodes = [_build_section_node(so) for so in so_by_outcome.get(clo_id, [])]
    agg_took, agg_passed, has_data = _aggregate_assessment_nodes(section_nodes)

    return {
        "id": clo_id,
        "clo_number": clo_info.get("clo_number", ""),
        "description": clo_info.get("description", ""),
        "course_code": course_info.get("course_number", "")
        or course_info.get("course_code", ""),
        "course_name": course_info.get("name", "")
        or course_info.get("course_name", ""),
        "assessment_method": clo_info.get("assessment_method", ""),
        "students_took": agg_took,
        "students_passed": agg_passed,
        "status": clo_info.get("status", ""),
        "sections": section_nodes,
        "_has_data": has_data,
    }


def _build_course_and_clo_lookups(
    program_id: str,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Build course and CLO lookup dicts for a program."""
    courses_raw = database_service.get_courses_by_program(program_id)
    course_lookup: Dict[str, Dict[str, Any]] = {}
    clo_lookup: Dict[str, Dict[str, Any]] = {}
    for course in courses_raw:
        cid = course.get("course_id") or course.get("id", "")
        course_lookup[cid] = course
        clos = database_service.get_course_outcomes(cid)
        for clo in clos:
            clo_id = clo.get("outcome_id") or clo.get("id", "")
            clo_lookup[clo_id] = {**clo, "course": course}
    return course_lookup, clo_lookup


def _build_program_node(
    prog: Dict[str, Any],
    so_by_outcome: Dict[str, List[Dict[str, Any]]],
) -> Tuple[Dict[str, Any], int, int, int]:
    """Build a program-level node with nested PLO/CLO data.

    Returns (program_node, plo_count, clos_with_data, clos_missing_data).
    """
    pid = prog.get("id") or prog.get("program_id", "")
    display_mode = get_assessment_display_mode(prog)

    plos = database_service.get_program_outcomes(pid)
    mapping = database_service.get_latest_published_plo_mapping(pid)
    entries = mapping.get("entries", []) if mapping else []

    # Index entries by PLO id
    entries_by_plo: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries:
        plo_id = entry.get("program_outcome_id", "")
        entries_by_plo.setdefault(plo_id, []).append(entry)

    _, clo_lookup = _build_course_and_clo_lookups(pid)

    plo_nodes: List[Dict[str, Any]] = []
    mapped_clo_count = 0
    with_data = 0
    missing_data = 0

    for plo in plos:
        plo_entries = entries_by_plo.get(plo["id"], [])
        clo_nodes: List[Dict[str, Any]] = []

        for entry in plo_entries:
            node = _build_clo_node(entry, clo_lookup, so_by_outcome)
            has_data = node.pop("_has_data")
            clo_nodes.append(node)
            if has_data:
                with_data += 1
            else:
                missing_data += 1

        mapped_clo_count += len(clo_nodes)

        # Aggregate took/passed across all CLOs in this PLO
        plo_took, plo_passed, _ = _aggregate_assessment_nodes(clo_nodes)

        plo_nodes.append(
            {
                "id": plo["id"],
                "plo_number": plo.get("plo_number"),
                "description": plo.get("description", ""),
                "mapped_clo_count": len(clo_nodes),
                "students_took": plo_took,
                "students_passed": plo_passed,
                "mapped_clos": clo_nodes,
            }
        )

    # Aggregate took/passed across all PLOs in this program
    all_clo_nodes = [clo for plo in plo_nodes for clo in plo["mapped_clos"]]
    prog_took, prog_passed, _ = _aggregate_assessment_nodes(all_clo_nodes)

    program_node = {
        "id": pid,
        "name": prog.get("name", ""),
        "short_name": prog.get("short_name", ""),
        "plo_count": len(plos),
        "mapped_clo_count": mapped_clo_count,
        "students_took": prog_took,
        "students_passed": prog_passed,
        "mapping_version": mapping.get("version") if mapping else None,
        "mapping_status": mapping.get("status") if mapping else None,
        "assessment_display_mode": display_mode,
        "plos": plo_nodes,
    }
    return program_node, len(plos), with_data, missing_data


def get_plo_dashboard_tree(
    institution_id: str,
    term_id: Optional[str] = None,
    program_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the hierarchical tree for the PLO dashboard.

    Returns::

        {
            "programs": [ ... ],
            "term": {"id": ..., "name": ...} | None,
            "summary": { ... },
        }
    """
    # Resolve term
    term_info: Optional[Dict[str, Any]] = None
    if term_id:
        term = database_service.get_term_by_id(term_id)
        if term:
            tid = term.get("id") or term.get("term_id", "")
            term_info = {
                "id": tid,
                "name": term.get("name") or term.get("term_name", ""),
            }

    # Resolve programs
    all_programs = database_service.get_programs_by_institution(institution_id)
    if program_id:
        all_programs = [
            p
            for p in all_programs
            if (p.get("id") or p.get("program_id")) == program_id
        ]

    # Pre-fetch section outcomes for the term to avoid repeated queries
    all_section_outcomes: List[Dict[str, Any]] = []
    if term_id:
        all_section_outcomes = database_service.get_section_outcomes_by_criteria(
            institution_id=institution_id,
            term_id=term_id,
        )
    # Index by outcome_id for fast lookup
    so_by_outcome: Dict[str, List[Dict[str, Any]]] = {}
    for so in all_section_outcomes:
        oid = so.get("outcome_id", "")
        so_by_outcome.setdefault(oid, []).append(so)

    total_plos = 0
    total_mapped_clos = 0
    clos_with_data = 0
    clos_missing_data = 0

    program_nodes: List[Dict[str, Any]] = []

    for prog in all_programs:
        node, plo_count, with_data, missing_data = _build_program_node(
            prog, so_by_outcome
        )
        program_nodes.append(node)
        total_plos += plo_count
        total_mapped_clos += node["mapped_clo_count"]
        clos_with_data += with_data
        clos_missing_data += missing_data

    return {
        "programs": program_nodes,
        "term": term_info,
        "summary": {
            "total_programs": len(program_nodes),
            "total_plos": total_plos,
            "total_mapped_clos": total_mapped_clos,
            "clos_with_data": clos_with_data,
            "clos_missing_data": clos_missing_data,
        },
    }
