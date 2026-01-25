"""
Course Offering API routes.

Provides endpoints for managing course offerings (CRUD operations)
with program enrichment, term status annotation, and section statistics.
"""

from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

import src.database.database_service as database_service
from src.api.utils import (
    InstitutionContextMissingError,
    get_current_institution_id_safe,
    get_current_user_safe,
    handle_api_error,
    resolve_institution_scope,
)
from src.database.database_service import (
    delete_course_offering,
    get_all_course_offerings,
    get_all_courses,
    get_all_sections,
    get_all_terms,
    get_course_offering,
    get_programs_by_institution,
    update_course_offering,
)
from src.services.auth_service import (
    UserRole,
    get_current_institution_id,
    permission_required,
)
from src.utils.constants import (
    COURSE_OFFERING_NOT_FOUND_MSG,
    NO_JSON_DATA_PROVIDED_MSG,
)
from src.utils.logging_config import get_logger
from src.utils.term_utils import TERM_STATUS_ACTIVE, get_term_status

offerings_bp = Blueprint("offerings", __name__, url_prefix="/api")
logger = get_logger(__name__)


def _filter_sections_by_params(
    sections: List[Dict[str, Any]], term_id: Optional[str], course_id: Optional[str]
) -> List[Dict[str, Any]]:
    """Filter sections by term_id and course_id if specified"""
    if term_id:
        sections = [s for s in sections if s.get("term_id") == term_id]
    if course_id:
        sections = [s for s in sections if s.get("course_id") == course_id]
    return sections


def _aggregate_offerings_from_sections(
    sections: List[Dict[str, Any]],
) -> Dict[str, Dict[str, int]]:
    """Compute section/enrollment stats per offering."""
    stats: Dict[str, Dict[str, int]] = {}
    for section in sections:
        offering_id = section.get("offering_id")
        if not offering_id:
            continue

        entry = stats.setdefault(
            offering_id, {"section_count": 0, "total_enrollment": 0}
        )
        entry["section_count"] += 1
        entry["total_enrollment"] += section.get("enrollment") or 0

    return stats


def _build_course_program_map(
    courses: List[Dict[str, Any]], program_map: Dict[str, str]
) -> Dict[str, Dict[str, List[Any]]]:
    """Build mapping of course_id to list of program names and IDs"""
    course_program_map = {}
    for course in courses:
        p_ids = course.get("program_ids") or []
        p_names = [program_map[pid] for pid in p_ids if pid in program_map]
        course_id = course.get("course_id") or course.get("id")
        if course_id:
            course_program_map[str(course_id)] = {"names": p_names, "ids": p_ids}
    return course_program_map


def _enrich_offerings_with_programs(
    offerings: List[Dict[str, Any]],
    course_program_map: Dict[str, Dict[str, List[Any]]],
    program_map: Dict[str, str],
) -> None:
    """Add program_names and program_ids to each offering based on explicit selection or course defaults."""
    for offering in offerings:
        names: List[str] = []
        ids: List[str] = []
        program_id = offering.get("program_id")
        if program_id and program_id in program_map:
            names = [program_map[program_id]]
            ids = [program_id]
        elif offering.get("course_id"):
            course_data = course_program_map.get(
                offering["course_id"], {"names": [], "ids": []}
            )
            names = course_data.get("names", [])
            ids = course_data.get("ids", [])
        offering["program_names"] = names
        offering["program_ids"] = ids


def _strip_term_status_fields(payload: Dict[str, Any]) -> None:
    """Remove unsupported status toggles from term payloads."""
    for key in ("status", "active", "is_active"):
        payload.pop(key, None)


def _resolve_term_dates(
    term: Optional[Dict[str, Any]], fallback: Dict[str, Any]
) -> tuple[Optional[str], Optional[str]]:
    """Resolve term start/end dates from the term record or offering fallback."""
    if term:
        return term.get("start_date"), term.get("end_date")
    return fallback.get("term_start_date"), fallback.get("term_end_date")


def _annotate_offering_status(
    offering: Dict[str, Any], term: Optional[Dict[str, Any]]
) -> None:
    """Ensure offerings always expose a deterministic status."""
    start_date, end_date = _resolve_term_dates(term, offering)
    if start_date:
        offering["term_start_date"] = start_date
    if end_date:
        offering["term_end_date"] = end_date

    status = get_term_status(start_date, end_date)
    offering["status"] = status
    offering["term_status"] = status
    offering["timeline_status"] = status
    offering["is_active"] = status == TERM_STATUS_ACTIVE


def _build_term_lookup(terms: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    for term in terms:
        tid = term.get("term_id") or term.get("id")
        if tid:
            lookup[tid] = term
    return lookup


def _filter_offerings_by_term(
    offerings: List[Dict[str, Any]], term_id: Optional[str]
) -> List[Dict[str, Any]]:
    if not term_id:
        return offerings
    return [o for o in offerings if o.get("term_id") == term_id]


def _filter_offerings_by_course(
    offerings: List[Dict[str, Any]], course_id: Optional[str]
) -> List[Dict[str, Any]]:
    if not course_id:
        return offerings
    return [o for o in offerings if o.get("course_id") == course_id]


def _populate_offering_metadata(
    offering: Dict[str, Any],
    section_stats: Dict[str, Dict[str, int]],
    course_lookup: Dict[str, Dict[str, Any]],
    term_lookup: Dict[str, Dict[str, Any]],
) -> None:
    offering_id = str(offering.get("offering_id") or "")
    stats = section_stats.get(
        offering_id,
        {"section_count": 0, "total_enrollment": 0},
    )
    offering["section_count"] = stats["section_count"]
    offering["total_enrollment"] = stats["total_enrollment"]

    course_id = str(offering.get("course_id") or "")
    course = course_lookup.get(course_id)
    if course:
        offering["course_number"] = course.get("course_number")
        offering["course_title"] = course.get("course_title")
        offering["course_name"] = course.get("course_title") or course.get(
            "course_number"
        )
        offering["department"] = course.get("department")
    else:
        offering.setdefault("course_name", "Unknown Course")

    term_id = str(offering.get("term_id") or "")
    term = term_lookup.get(term_id)
    if term:
        offering["term_name"] = (
            term.get("name")
            or term.get("term_name")
            or offering.get("term_name")
            or "Unknown Term"
        )
    else:
        offering["term_name"] = offering.get("term_name") or "Unknown Term"

    _annotate_offering_status(offering, term)


def _build_offering_context(
    institution_id: str, term_id: Optional[str], course_id: Optional[str]
) -> Tuple[
    Dict[str, Dict[str, int]],
    Dict[str, Dict[str, Any]],
    Dict[str, Dict[str, Any]],
    Dict[str, Dict[str, List[Any]]],
    Dict[str, str],
]:
    sections = get_all_sections(institution_id) or []
    section_stats = _aggregate_offerings_from_sections(
        _filter_sections_by_params(sections, term_id, course_id)
    )
    courses = get_all_courses(institution_id) or []
    programs = get_programs_by_institution(institution_id) or []
    program_map: Dict[str, str] = {}
    for program in programs:
        program_key = program.get("program_id") or program.get("id")
        if not program_key:
            continue
        program_name = program.get("name") or program.get("program_name") or ""
        program_map[str(program_key)] = program_name
    course_program_map = _build_course_program_map(courses, program_map)
    course_lookup: Dict[str, Dict[str, Any]] = {}
    for course in courses:
        course_key = course.get("course_id") or course.get("id")
        if course_key:
            course_lookup[str(course_key)] = course
    term_lookup = _build_term_lookup(get_all_terms(institution_id) or [])
    return section_stats, course_lookup, term_lookup, course_program_map, program_map


def _get_filtered_offerings(
    institution_id: str, term_id: Optional[str], course_id: Optional[str]
) -> List[Dict[str, Any]]:
    offerings = get_all_course_offerings(institution_id) or []
    if term_id:
        offerings = _filter_offerings_by_term(offerings, term_id)
    if course_id:
        offerings = _filter_offerings_by_course(offerings, course_id)
    return offerings


def _log_offering_program_enrichment(offerings: List[Dict[str, Any]]) -> None:
    offerings_with_programs = [o for o in offerings if o.get("program_ids")]
    offerings_without_programs = [o for o in offerings if not o.get("program_ids")]
    logger.info(
        f"[/api/offerings] After enrichment: {len(offerings_with_programs)} with programs, {len(offerings_without_programs)} without programs"
    )
    if offerings_without_programs:
        logger.warning(
            f"[/api/offerings] Offerings without programs: {[o.get('course_name', 'Unknown') for o in offerings_without_programs]}"
        )


@offerings_bp.route("/offerings", methods=["POST"])
@permission_required("manage_courses")
def create_course_offering_endpoint() -> ResponseReturnValue:
    """Create a new course offering from JSON body (course_id, term_id required)."""
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        required_fields = ["course_id", "term_id"]
        missing_fields = [f for f in required_fields if not data.get(f)]

        if missing_fields:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f'Missing required fields: {", ".join(missing_fields)}',
                    }
                ),
                400,
            )

        offering_payload = {
            "course_id": data["course_id"],
            "term_id": data["term_id"],
            "program_id": data.get("program_id"),
            "institution_id": get_current_institution_id(),
        }

        sections_data = data.get("sections")
        if not sections_data:
            sections_data = [{"section_number": "001"}]

        offering_payload["section_count"] = len(sections_data)
        offering_id = database_service.create_course_offering(offering_payload)

        if offering_id:
            for sec in sections_data:
                section_payload = {
                    "offering_id": offering_id,
                    "section_number": sec.get("section_number", "001"),
                    "enrollment": 0,
                    "status": "assigned",
                }
                database_service.create_course_section(section_payload)

            return (
                jsonify(
                    {
                        "success": True,
                        "offering_id": offering_id,
                        "message": "Course offering created successfully",
                    }
                ),
                201,
            )
        else:
            return (
                jsonify(
                    {"success": False, "error": "Failed to create course offering"}
                ),
                500,
            )

    except Exception as e:
        return handle_api_error(
            e, "Create course offering", "Failed to create course offering"
        )


@offerings_bp.route("/offerings", methods=["GET"])
@permission_required("view_program_data")
def list_course_offerings() -> ResponseReturnValue:
    """Get list of course offerings, optionally filtered by term or course"""
    try:
        term_id = request.args.get("term_id")
        course_id = request.args.get("course_id")
        institution_id = get_current_institution_id_safe()

        (
            section_stats,
            course_lookup,
            term_lookup,
            course_program_map,
            program_map,
        ) = _build_offering_context(institution_id, term_id, course_id)

        offerings = _get_filtered_offerings(institution_id, term_id, course_id)
        logger.info(f"[/api/offerings] After filtering: {len(offerings)} offerings")

        for offering in offerings:
            _populate_offering_metadata(
                offering, section_stats, course_lookup, term_lookup
            )

        _enrich_offerings_with_programs(offerings, course_program_map, program_map)
        _log_offering_program_enrichment(offerings)

        return (
            jsonify({"success": True, "offerings": offerings, "count": len(offerings)}),
            200,
        )

    except Exception as e:
        return handle_api_error(
            e, "List course offerings", "Failed to retrieve course offerings"
        )


@offerings_bp.route("/offerings/<offering_id>", methods=["GET"])
@permission_required("view_program_data")
def get_course_offering_endpoint(offering_id: str) -> ResponseReturnValue:
    """Get course offering details by ID"""
    try:
        offering = get_course_offering(offering_id)

        if offering:
            return jsonify({"success": True, "offering": offering}), 200
        else:
            return (
                jsonify({"success": False, "error": COURSE_OFFERING_NOT_FOUND_MSG}),
                404,
            )

    except Exception as e:
        return handle_api_error(
            e, "Get course offering", "Failed to retrieve course offering"
        )


@offerings_bp.route("/offerings/<offering_id>", methods=["PUT"])
@permission_required("manage_courses")
def update_course_offering_endpoint(offering_id: str) -> ResponseReturnValue:
    """Update course offering details."""
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        offering = get_course_offering(offering_id)
        if not offering:
            return (
                jsonify({"success": False, "error": COURSE_OFFERING_NOT_FOUND_MSG}),
                404,
            )

        for field in (
            "status",
            "term_status",
            "timeline_status",
            "is_active",
            "active",
        ):
            data.pop(field, None)
        success = update_course_offering(offering_id, data)

        if success:
            updated_offering = get_course_offering(offering_id)
            return (
                jsonify(
                    {
                        "success": True,
                        "offering": updated_offering,
                        "message": "Course offering updated successfully",
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {"success": False, "error": "Failed to update course offering"}
                ),
                500,
            )

    except Exception as e:
        return handle_api_error(
            e, "Update course offering", "Failed to update course offering"
        )


@offerings_bp.route("/offerings/<offering_id>", methods=["DELETE"])
@permission_required("manage_courses")
def delete_course_offering_endpoint(offering_id: str) -> ResponseReturnValue:
    """Delete course offering and its associated sections."""
    try:
        offering = get_course_offering(offering_id)
        if not offering:
            return (
                jsonify({"success": False, "error": COURSE_OFFERING_NOT_FOUND_MSG}),
                404,
            )

        success = delete_course_offering(offering_id)

        if success:
            return (
                jsonify(
                    {"success": True, "message": "Course offering deleted successfully"}
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {"success": False, "error": "Failed to delete course offering"}
                ),
                500,
            )

    except Exception as e:
        return handle_api_error(
            e, "Delete course offering", "Failed to delete course offering"
        )
