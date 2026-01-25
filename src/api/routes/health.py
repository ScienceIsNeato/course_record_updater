"""
Health and error handler API routes.

Provides the health check endpoint and global API error handlers (404, 500).
"""

from typing import Any, Tuple

from flask import Blueprint, jsonify

# Create blueprint
health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.route("/health", methods=["GET"])
def health_check() -> tuple[Any, int]:
    """API health check endpoint"""
    return (
        jsonify(
            {
                "success": True,
                "status": "healthy",
                "message": "Loopcloser API is running",
                "version": "2.0.0",
            }
        ),
        200,
    )


# ========================================
# ERROR HANDLERS
# ========================================


@health_bp.app_errorhandler(404)
def api_not_found(error: Any) -> Tuple[Any, int]:
    """Handle 404 errors for API routes"""
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@health_bp.app_errorhandler(500)
def api_internal_error(error: Any) -> Tuple[Any, int]:
    """Handle 500 errors for API routes"""
    return jsonify({"success": False, "error": "Internal server error"}), 500
