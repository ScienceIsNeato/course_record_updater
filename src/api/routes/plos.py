"""Program Learning Outcomes (PLO) API routes.

Provides endpoints for:
- PLO template CRUD (create, read, update, soft-delete)
- Versioned PLO↔CLO mapping draft/publish workflow
- Mapping version retrieval and history
"""

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

from src.api.utils import (
    get_current_institution_id_safe,
    get_current_user_id_safe,
    handle_api_error,
)
from src.database.database_service import get_program_by_id
from src.services.auth_service import permission_required
from src.services.plo_service import (
    add_mapping_entry,
    create_program_outcome,
    delete_program_outcome,
    discard_draft,
    get_draft,
    get_latest_published_mapping,
    get_mapping,
    get_mapping_by_version,
    get_or_create_draft,
    get_program_outcome,
    get_published_mappings,
    list_program_outcomes,
    publish_mapping,
    remove_mapping_entry,
    update_program_outcome,
)
from src.utils.constants import (
    NO_DATA_PROVIDED_MSG,
    PROGRAM_NOT_FOUND_MSG,
)
from src.utils.logging_config import get_logger

plo_bp = Blueprint("plos", __name__, url_prefix="/api/programs")
logger = get_logger(__name__)

PLO_NOT_FOUND_MSG = "Program outcome not found"
MAPPING_NOT_FOUND_MSG = "PLO mapping not found"


# ---------------------------------------------------------------------------
# PLO template CRUD
# ---------------------------------------------------------------------------


@plo_bp.route("/<program_id>/plos", methods=["GET"])
@permission_required("view_program_data")
def list_plos(program_id: str) -> ResponseReturnValue:
    """List all PLOs for a program."""
    include_inactive = request.args.get("include_inactive", "false").lower() == "true"

    program = get_program_by_id(program_id)
    if not program:
        return jsonify({"success": False, "error": PROGRAM_NOT_FOUND_MSG}), 404

    plos = list_program_outcomes(program_id, include_inactive=include_inactive)
    return jsonify({"success": True, "plos": plos, "total": len(plos)}), 200


@plo_bp.route("/<program_id>/plos", methods=["POST"])
@permission_required("manage_programs")
def create_plo(program_id: str) -> ResponseReturnValue:
    """Create a new PLO for a program."""
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

    institution_id = get_current_institution_id_safe()
    data["program_id"] = program_id
    data["institution_id"] = institution_id

    try:
        plo_id = create_program_outcome(data)
        plo = get_program_outcome(plo_id)
        return jsonify({"success": True, "plo": plo}), 201
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return handle_api_error(e, "create_plo", "Failed to create program outcome")


@plo_bp.route("/<program_id>/plos/<plo_id>", methods=["GET"])
@permission_required("view_program_data")
def get_plo(program_id: str, plo_id: str) -> ResponseReturnValue:
    """Get a single PLO by ID."""
    plo = get_program_outcome(plo_id)
    if not plo:
        return jsonify({"success": False, "error": PLO_NOT_FOUND_MSG}), 404
    return jsonify({"success": True, "plo": plo}), 200


@plo_bp.route("/<program_id>/plos/<plo_id>", methods=["PUT"])
@permission_required("manage_programs")
def update_plo(program_id: str, plo_id: str) -> ResponseReturnValue:
    """Update a PLO's description or plo_number."""
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

    try:
        success = update_program_outcome(plo_id, data)
        if not success:
            return jsonify({"success": False, "error": PLO_NOT_FOUND_MSG}), 404
        plo = get_program_outcome(plo_id)
        return jsonify({"success": True, "plo": plo}), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return handle_api_error(e, "update_plo", "Failed to update program outcome")


@plo_bp.route("/<program_id>/plos/<plo_id>", methods=["DELETE"])
@permission_required("manage_programs")
def delete_plo(program_id: str, plo_id: str) -> ResponseReturnValue:
    """Soft-delete a PLO."""
    success = delete_program_outcome(plo_id)
    if not success:
        return jsonify({"success": False, "error": PLO_NOT_FOUND_MSG}), 404
    return jsonify({"success": True, "message": "Program outcome deactivated"}), 200


# ---------------------------------------------------------------------------
# PLO Mapping — draft lifecycle
# ---------------------------------------------------------------------------


@plo_bp.route("/<program_id>/plo-mappings/draft", methods=["POST"])
@permission_required("manage_programs")
def create_or_get_draft_mapping(program_id: str) -> ResponseReturnValue:
    """Get or create a draft mapping for the program.

    If a published version exists the draft will be pre-populated with
    its entries.  Idempotent — calling twice returns the same draft.
    """
    program = get_program_by_id(program_id)
    if not program:
        return jsonify({"success": False, "error": PROGRAM_NOT_FOUND_MSG}), 404

    user_id = get_current_user_id_safe()

    try:
        draft = get_or_create_draft(program_id, user_id)
        return jsonify({"success": True, "mapping": draft}), 200
    except Exception as e:
        return handle_api_error(e, "create_draft_mapping", "Failed to create draft")


@plo_bp.route("/<program_id>/plo-mappings/draft", methods=["GET"])
@permission_required("view_program_data")
def get_draft_mapping(program_id: str) -> ResponseReturnValue:
    """Get the current draft mapping for the program, if any."""
    draft = get_draft(program_id)
    if not draft:
        return jsonify({"success": False, "error": "No draft mapping exists"}), 404
    return jsonify({"success": True, "mapping": draft}), 200


@plo_bp.route("/<program_id>/plo-mappings/draft", methods=["DELETE"])
@permission_required("manage_programs")
def discard_draft_mapping(program_id: str) -> ResponseReturnValue:
    """Discard the current draft mapping and all its entries."""
    draft = get_draft(program_id)
    if not draft:
        return jsonify({"success": False, "error": "No draft mapping exists"}), 404

    success = discard_draft(draft["id"])
    if not success:
        return jsonify({"success": False, "error": "Failed to discard draft"}), 500
    return jsonify({"success": True, "message": "Draft mapping discarded"}), 200


# ---------------------------------------------------------------------------
# PLO Mapping — entries (add / remove CLO links)
# ---------------------------------------------------------------------------


@plo_bp.route("/<program_id>/plo-mappings/<mapping_id>/entries", methods=["POST"])
@permission_required("manage_programs")
def add_entry(program_id: str, mapping_id: str) -> ResponseReturnValue:
    """Add a PLO↔CLO link to a mapping."""
    data = request.get_json(silent=True) or {}
    plo_id = data.get("program_outcome_id")
    clo_id = data.get("course_outcome_id")

    if not plo_id or not clo_id:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "program_outcome_id and course_outcome_id are required",
                }
            ),
            400,
        )

    try:
        entry_id = add_mapping_entry(mapping_id, plo_id, clo_id)
        return jsonify({"success": True, "entry_id": entry_id}), 201
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return handle_api_error(e, "add_mapping_entry", "Failed to add mapping entry")


@plo_bp.route(
    "/<program_id>/plo-mappings/<mapping_id>/entries/<entry_id>",
    methods=["DELETE"],
)
@permission_required("manage_programs")
def remove_entry(
    program_id: str, mapping_id: str, entry_id: str
) -> ResponseReturnValue:
    """Remove a PLO↔CLO link from a mapping."""
    success = remove_mapping_entry(entry_id)
    if not success:
        return jsonify({"success": False, "error": "Entry not found"}), 404
    return jsonify({"success": True, "message": "Entry removed"}), 200


# ---------------------------------------------------------------------------
# PLO Mapping — publish
# ---------------------------------------------------------------------------


@plo_bp.route("/<program_id>/plo-mappings/<mapping_id>/publish", methods=["POST"])
@permission_required("manage_programs")
def publish_draft(program_id: str, mapping_id: str) -> ResponseReturnValue:
    """Publish a draft mapping, assigning the next version number.

    Freezes PLO description snapshots into each entry for historical
    preservation.
    """
    data = request.get_json(silent=True) or {}
    description = data.get("description")

    try:
        published = publish_mapping(mapping_id, description)
        return jsonify({"success": True, "mapping": published}), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return handle_api_error(e, "publish_mapping", "Failed to publish mapping")


# ---------------------------------------------------------------------------
# PLO Mapping — retrieval (published versions)
# ---------------------------------------------------------------------------


@plo_bp.route("/<program_id>/plo-mappings", methods=["GET"])
@permission_required("view_program_data")
def list_published_mappings(program_id: str) -> ResponseReturnValue:
    """List all published mapping versions for a program."""
    mappings = get_published_mappings(program_id)
    return (
        jsonify({"success": True, "mappings": mappings, "total": len(mappings)}),
        200,
    )


@plo_bp.route("/<program_id>/plo-mappings/latest", methods=["GET"])
@permission_required("view_program_data")
def latest_published_mapping(program_id: str) -> ResponseReturnValue:
    """Return the most-recently published mapping version."""
    mapping = get_latest_published_mapping(program_id)
    if not mapping:
        return (
            jsonify({"success": False, "error": "No published mappings found"}),
            404,
        )
    return jsonify({"success": True, "mapping": mapping}), 200


@plo_bp.route("/<program_id>/plo-mappings/version/<int:version>", methods=["GET"])
@permission_required("view_program_data")
def get_mapping_version(program_id: str, version: int) -> ResponseReturnValue:
    """Retrieve a specific published mapping version."""
    mapping = get_mapping_by_version(program_id, version)
    if not mapping:
        return jsonify({"success": False, "error": MAPPING_NOT_FOUND_MSG}), 404
    return jsonify({"success": True, "mapping": mapping}), 200


@plo_bp.route("/<program_id>/plo-mappings/<mapping_id>", methods=["GET"])
@permission_required("view_program_data")
def get_mapping_by_id(program_id: str, mapping_id: str) -> ResponseReturnValue:
    """Retrieve a mapping (draft or published) by ID."""
    mapping = get_mapping(mapping_id)
    if not mapping:
        return jsonify({"success": False, "error": MAPPING_NOT_FOUND_MSG}), 404
    return jsonify({"success": True, "mapping": mapping}), 200
