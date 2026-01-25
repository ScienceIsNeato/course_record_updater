"""
Terms API routes.

Provides CRUD endpoints for academic term management including
listing, creating, updating, and deleting terms.
"""

from datetime import datetime
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

from src.api.utils import (
    InstitutionContextMissingError,
    get_current_institution_id_safe,
    get_current_user_safe,
    handle_api_error,
    resolve_institution_scope,
)
from src.database.database_service import (
    create_term,
    delete_term,
    get_active_terms,
    get_all_terms,
    get_term_by_id,
    update_term,
)
from src.services.auth_service import permission_required
from src.utils.constants import (
    INSTITUTION_CONTEXT_REQUIRED_MSG,
    NO_DATA_PROVIDED_MSG,
    NO_JSON_DATA_PROVIDED_MSG,
    TERM_NOT_FOUND_MSG,
)
from src.utils.logging_config import get_logger

# Create blueprint
terms_bp = Blueprint("terms", __name__, url_prefix="/api")

# Initialize logger
logger = get_logger(__name__)


def _strip_term_status_fields(payload: Dict[str, Any]) -> None:
    """Remove unsupported status toggles from term payloads."""
    for key in ("status", "active", "is_active"):
        payload.pop(key, None)


@terms_bp.route("/terms", methods=["GET"])
@permission_required("view_program_data")
def list_terms() -> ResponseReturnValue:
    """Get list of terms. Use ?all=true to get all terms, otherwise returns only active terms."""
    try:
        try:
            _, institution_ids, is_global = resolve_institution_scope()
        except InstitutionContextMissingError:
            return (
                jsonify({"success": False, "error": INSTITUTION_CONTEXT_REQUIRED_MSG}),
                400,
            )

        # Check if caller wants all terms or just active ones
        include_all = request.args.get("all", "").lower() in ("true", "1", "yes")

        if is_global:
            terms: List[Dict[str, Any]] = []
            for inst_id in institution_ids:
                if include_all:
                    terms.extend(get_all_terms(inst_id))
                else:
                    terms.extend(get_active_terms(inst_id))
        else:
            if include_all:
                terms = get_all_terms(institution_ids[0])
            else:
                terms = get_active_terms(institution_ids[0])

        return jsonify({"success": True, "terms": terms, "count": len(terms)})

    except Exception as e:
        return handle_api_error(e, "Get terms", "Failed to retrieve terms")


@terms_bp.route("/terms", methods=["POST"])
@permission_required("manage_terms")
def create_term_api() -> ResponseReturnValue:
    """
    Create a new academic term

    Request body should contain:
    - name: Term name (e.g., "2024 Fall")
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    - assessment_due_date: Assessment due date (YYYY-MM-DD)
    """
    try:
        data = request.get_json(silent=True) or {}

        if not data:
            return jsonify({"success": False, "error": NO_DATA_PROVIDED_MSG}), 400

        # Validate required fields
        required_fields = ["name", "start_date", "end_date"]
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

        # Ensure institution context is included
        institution_id = get_current_institution_id_safe()
        if not institution_id:
            return (
                jsonify({"success": False, "error": INSTITUTION_CONTEXT_REQUIRED_MSG}),
                400,
            )

        # Map conventional 'name' to legacy 'term_name' for storage compatibility
        if data.get("name") and not data.get("term_name"):
            data["term_name"] = data["name"]

        # Attach institution_id to payload
        data["institution_id"] = institution_id
        _strip_term_status_fields(data)

        term_id = create_term(data)

        if term_id:
            return (
                jsonify(
                    {
                        "success": True,
                        "term_id": term_id,
                        "message": "Term created successfully",
                    }
                ),
                201,
            )
        else:
            return jsonify({"success": False, "error": "Failed to create term"}), 500

    except Exception as e:
        return handle_api_error(e, "Create term", "Failed to create term")


@terms_bp.route("/terms/<term_id>", methods=["GET"])
@permission_required("view_program_data")
def get_term_by_id_endpoint(term_id: str) -> ResponseReturnValue:
    """Get term details by term ID"""
    try:
        term = get_term_by_id(term_id)

        if not term:
            return jsonify({"success": False, "error": TERM_NOT_FOUND_MSG}), 404

        # Verify institution access
        institution_id = get_current_institution_id_safe()
        if term.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": TERM_NOT_FOUND_MSG}), 404

        return jsonify({"success": True, "term": term}), 200

    except Exception as e:
        return handle_api_error(e, "Get term by ID", "Failed to retrieve term")


@terms_bp.route("/terms/<term_id>", methods=["PUT"])
@permission_required("manage_terms")
def update_term_endpoint(term_id: str) -> ResponseReturnValue:
    """
    Update term details

    Allows updating name, dates, active status, etc.
    """
    try:
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": NO_JSON_DATA_PROVIDED_MSG}), 400

        # Verify term exists and institution access
        term = get_term_by_id(term_id)

        if not term:
            return jsonify({"success": False, "error": TERM_NOT_FOUND_MSG}), 404

        institution_id = get_current_institution_id_safe()
        if term.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": TERM_NOT_FOUND_MSG}), 404

        # Validate assessment_due_date format if present
        if data.get("assessment_due_date"):
            try:
                # Simple format check YYYY-MM-DD
                datetime.strptime(data["assessment_due_date"], "%Y-%m-%d")
            except ValueError:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Invalid assessment date format (YYYY-MM-DD required)",
                        }
                    ),
                    400,
                )

        _strip_term_status_fields(data)
        success = update_term(term_id, data)

        if success:
            # Fetch updated term
            updated_term = get_term_by_id(term_id)
            return (
                jsonify(
                    {
                        "success": True,
                        "term": updated_term,
                        "message": "Term updated successfully",
                    }
                ),
                200,
            )
        else:
            return jsonify({"success": False, "error": "Failed to update term"}), 500

    except Exception as e:
        return handle_api_error(e, "Update term", "Failed to update term")


@terms_bp.route("/terms/<term_id>", methods=["DELETE"])
@permission_required("manage_terms")
def delete_term_endpoint(term_id: str) -> ResponseReturnValue:
    """
    Delete term (hard delete - CASCADE deletes offerings and sections)

    WARNING: This will also delete all associated:
    - Course offerings
    - Course sections
    """
    try:
        # Verify term exists and institution access
        term = get_term_by_id(term_id)

        if not term:
            return jsonify({"success": False, "error": TERM_NOT_FOUND_MSG}), 404

        institution_id = get_current_institution_id_safe()
        if term.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": TERM_NOT_FOUND_MSG}), 404

        success = delete_term(term_id)

        if success:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Term '{term['name']}' deleted successfully",
                    }
                ),
                200,
            )
        else:
            return jsonify({"success": False, "error": "Failed to delete term"}), 500

    except Exception as e:
        return handle_api_error(e, "Delete term", "Failed to delete term")
