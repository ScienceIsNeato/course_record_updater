"""PLO Dashboard API routes.

Provides the aggregated tree endpoint consumed by the PLO Dashboard UI.
"""

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue

from src.api.utils import get_current_institution_id_safe, handle_api_error
from src.services.auth_service import login_required, permission_required
from src.services.plo_dashboard_service import get_plo_dashboard_tree
from src.utils.logging_config import get_logger

plo_dashboard_bp = Blueprint("plo_dashboard", __name__, url_prefix="/api/plo-dashboard")
logger = get_logger(__name__)


@plo_dashboard_bp.route("/tree", methods=["GET"])
@login_required
@permission_required("view_program_data")
def get_tree() -> ResponseReturnValue:
    """Return the PLO dashboard tree data.

    Query parameters (all optional):
      - term_id: filter section-level data by academic term
      - program_id: scope to a single program
    """
    institution_id = get_current_institution_id_safe()
    if not institution_id:
        return jsonify({"success": False, "error": "No institution context"}), 403

    term_id = request.args.get("term_id")
    program_id = request.args.get("program_id")

    try:
        tree = get_plo_dashboard_tree(
            institution_id=institution_id,
            term_id=term_id,
            program_id=program_id,
        )
        return jsonify({"success": True, "data": tree}), 200
    except Exception as exc:
        return handle_api_error(
            exc, "PLO dashboard tree", "Failed to load PLO dashboard data"
        )
