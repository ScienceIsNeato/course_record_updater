"""
Audit API routes.

Provides endpoints for viewing and exporting audit logs for system activity tracking.
Site admin only.
"""

from datetime import datetime
from io import BytesIO
from typing import Any, Union

from flask import Blueprint, jsonify, request, send_file
from werkzeug.wrappers import Response

from src.api.utils import handle_api_error, resolve_institution_scope
from src.database.database_service import get_audit_logs_filtered
from src.services.audit_service import AuditService, EntityType
from src.services.auth_service import permission_required
from src.utils.constants import TIMEZONE_UTC_SUFFIX
from src.utils.logging_config import get_logger
from src.utils.time_utils import get_current_time

# Create blueprint
audit_bp = Blueprint("audit", __name__, url_prefix="/api/audit")

# Initialize logger
logger = get_logger(__name__)


@audit_bp.route("/recent", methods=["GET"])
@permission_required("manage_users")  # Site admin only
def get_recent_logs() -> tuple[Any, int]:
    """
    Get recent audit logs with basic filtering.

    Query Parameters:
        - limit: Number of logs to return (default: 50, max: 500)
        - offset: Number of logs to skip (default: 0)
        - institution_id: Filter by institution (optional)

    Note: For advanced filtering (operation_type, entity_type, date ranges),
    use the POST /api/audit/export endpoint instead.

    Returns:
        200: Recent audit logs
        400: Invalid parameters
        500: Server error
    """
    try:
        # Get pagination parameters
        limit = min(int(request.args.get("limit", 50)), 500)
        offset = int(request.args.get("offset", 0))

        # Get institution filter (only filter currently supported for recent logs)
        institution_id = request.args.get("institution_id")

        # Get logs using AuditService
        logs = AuditService.get_recent_activity(
            institution_id=institution_id, limit=limit
        )

        return (
            jsonify(
                {
                    "success": True,
                    "logs": logs,
                    "total": len(logs),
                    "limit": limit,
                    "offset": offset,
                }
            ),
            200,
        )

    except ValueError as e:
        # Don't log user-controlled exception message
        logger.error(
            f"Fetch recent audit logs failed with {type(e).__name__}", exc_info=True
        )
        return jsonify({"success": False, "error": "Invalid parameter"}), 400
    except Exception as e:
        return handle_api_error(
            e, "Fetch recent audit logs", "Failed to fetch audit logs"
        )


@audit_bp.route("/entity/<entity_type>/<entity_id>", methods=["GET"])
@permission_required("manage_users")  # Site admin only
def get_entity_history(entity_type: str, entity_id: str) -> tuple[Any, int]:
    """
    Get complete audit history for a specific entity.

    Path Parameters:
        - entity_type: Type of entity (users, courses, institutions, etc.)
        - entity_id: ID of the entity

    Query Parameters:
        - limit: Number of logs to return (default: 100, max: 1000)

    Returns:
        200: Entity audit history
        400: Invalid entity type
        500: Server error
    """
    try:
        limit = min(int(request.args.get("limit", 100)), 1000)

        # Convert string to EntityType enum
        try:
            entity_type_enum = EntityType[entity_type.upper()]
        except KeyError:
            return (
                jsonify(
                    {"success": False, "error": f"Invalid entity type: {entity_type}"}
                ),
                400,
            )

        # Get entity history
        history = AuditService.get_entity_history(
            entity_type=entity_type_enum, entity_id=entity_id, limit=limit
        )

        return (
            jsonify(
                {
                    "success": True,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "history": history,
                    "total_changes": len(history),
                }
            ),
            200,
        )

    except Exception as e:
        return handle_api_error(
            e,
            f"Fetch entity history for {entity_type}/{entity_id}",
            "Failed to fetch entity history",
        )


@audit_bp.route("/user/<user_id>", methods=["GET"])
@permission_required("manage_users")  # Site admin only
def get_user_activity(user_id: str) -> tuple[Any, int]:
    """
    Get all audit logs for actions performed by a specific user.

    Path Parameters:
        - user_id: ID of the user

    Query Parameters:
        - limit: Number of logs to return (default: 100, max: 1000)
        - start_date: Filter by start date (ISO 8601 format)
        - end_date: Filter by end date (ISO 8601 format)

    Returns:
        200: User audit activity
        400: Invalid date format
        500: Server error
    """
    try:
        limit = min(int(request.args.get("limit", 100)), 1000)

        # Parse date strings to datetime objects
        start_date = None
        end_date = None
        if start_date_str := request.args.get("start_date"):
            try:
                start_date = datetime.fromisoformat(
                    start_date_str.replace("Z", TIMEZONE_UTC_SUFFIX)
                )
            except ValueError:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Invalid start_date format. Use ISO 8601.",
                        }
                    ),
                    400,
                )

        if end_date_str := request.args.get("end_date"):
            try:
                end_date = datetime.fromisoformat(
                    end_date_str.replace("Z", TIMEZONE_UTC_SUFFIX)
                )
            except ValueError:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Invalid end_date format. Use ISO 8601.",
                        }
                    ),
                    400,
                )

        # Get user activity
        activity = AuditService.get_user_activity(
            user_id=user_id, limit=limit, start_date=start_date, end_date=end_date
        )

        return (
            jsonify(
                {
                    "success": True,
                    "user_id": user_id,
                    "activity": activity,
                    "total_actions": len(activity),
                }
            ),
            200,
        )

    except Exception as e:
        return handle_api_error(
            e, f"Fetch user activity for {user_id}", "Failed to fetch user activity"
        )


@audit_bp.route("/export", methods=["POST"])
@permission_required("manage_users")  # Site admin only
def export_logs() -> Union[Response, tuple[Any, int]]:
    """
    Export audit logs in CSV or JSON format.

    Request Body:
        {
            "format": "csv" | "json",
            "start_date": str (required, ISO 8601),
            "end_date": str (required, ISO 8601),
            "entity_type": str (optional),
            "user_id": str (optional),
            "institution_id": str (optional)
        }

    Returns:
        200: File download (CSV or JSON)
        400: Invalid parameters or format
        500: Server error
    """
    try:
        data = request.get_json() or {}
        export_format = data.get("format", "csv").lower()

        if export_format not in ["csv", "json"]:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid format. Must be 'csv' or 'json'",
                    }
                ),
                400,
            )

        # Parse required date parameters
        start_date_str = data.get("start_date")
        end_date_str = data.get("end_date")

        if not start_date_str or not end_date_str:
            return (
                jsonify(
                    {"success": False, "error": "start_date and end_date are required"}
                ),
                400,
            )

        try:
            start_date = datetime.fromisoformat(
                start_date_str.replace("Z", TIMEZONE_UTC_SUFFIX)
            )
            end_date = datetime.fromisoformat(
                end_date_str.replace("Z", TIMEZONE_UTC_SUFFIX)
            )
        except ValueError as e:
            # Don't log user-controlled exception message
            logger.error(f"Audit export failed with {type(e).__name__}", exc_info=True)
            return (
                jsonify({"success": False, "error": "Invalid date format"}),
                400,
            )

        # Parse optional filters
        entity_type = None
        if entity_type_str := data.get("entity_type"):
            try:
                entity_type = EntityType[entity_type_str.upper()]
            except KeyError:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Invalid entity type: {entity_type_str}",
                        }
                    ),
                    400,
                )

        user_id = data.get("user_id")
        institution_id = data.get("institution_id")

        # Export logs using AuditService (returns bytes)
        export_bytes = AuditService.export_audit_log(
            start_date=start_date,
            end_date=end_date,
            entity_type=entity_type,
            user_id=user_id,
            institution_id=institution_id,
            format_type=export_format,
        )

        # Create BytesIO object for send_file
        export_io = BytesIO(export_bytes)
        export_io.seek(0)

        # Generate filename with timestamp
        timestamp = get_current_time().strftime("%Y%m%d_%H%M%S")
        filename = f"audit_logs_{timestamp}.{export_format}"

        # Determine mime type
        mime_type = "text/csv" if export_format == "csv" else "application/json"

        return send_file(
            export_io, as_attachment=True, download_name=filename, mimetype=mime_type
        )

    except Exception as e:
        return handle_api_error(e, "Export audit logs", "Failed to export audit logs")


@audit_bp.route("/search", methods=["GET"])
@permission_required("manage_institution_users")
def search_audit_logs_endpoint() -> tuple[Any, int]:
    """
    Search and filter audit logs (institution-scoped).

    Query Params:
        start_date (str): Start date (YYYY-MM-DD)
        end_date (str): End date (YYYY-MM-DD)
        entity_type (str): Filter by entity type (optional)
        limit (int): Number of logs to return (default: 100)

    Returns:
        200: { success: true, logs: [...] }
        403: Permission denied
    """
    try:
        _user, institution_ids, is_global = resolve_institution_scope()
        institution_id = institution_ids[0] if institution_ids else None

        if not institution_id and not is_global:
            return (
                jsonify({"success": False, "error": "Institution context required"}),
                400,
            )

        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        entity_type = request.args.get("entity_type")

        logs = get_audit_logs_filtered(
            start_date=start_date,
            end_date=end_date,
            entity_type=entity_type,
            institution_id=institution_id,
        )

        return jsonify({"success": True, "logs": logs}), 200

    except Exception as e:
        return handle_api_error(e, "Search audit logs", "Failed to search audit logs")
