"""
Dashboard API routes.

Provides endpoints for retrieving aggregated dashboard data based on user role and context.
"""

from flask import Blueprint, jsonify

from src.api.utils import handle_api_error
from src.services.auth_service import get_current_user, login_required
from src.services.dashboard_service import DashboardService, DashboardServiceError

# Create blueprint
dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/data", methods=["GET"])
@login_required
def get_dashboard_data():
    """
    Get aggregated dashboard data for the current user.

    Returns role-specific dashboard data including:
    - Summary statistics (courses, users, programs, etc.)
    - Recent activity
    - Relevant entities based on user's role and permissions

    Returns:
        200: Dashboard data successfully retrieved
        500: Server error
    """
    try:
        service = DashboardService()
        payload = service.get_dashboard_data(get_current_user())
        return jsonify({"success": True, "data": payload})
    except DashboardServiceError as exc:
        return handle_api_error(exc, "Dashboard data", "Failed to load dashboard data")
    except Exception as exc:
        return handle_api_error(exc, "Dashboard data", "Failed to load dashboard data")
