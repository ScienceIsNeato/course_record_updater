"""
Shared utilities for API routes.

This module contains common helper functions, error handlers, and utilities
used across multiple API route modules.
"""

from typing import Any, Dict, List, Tuple

from flask import jsonify, request

from src.database.database_service import get_all_institutions
from src.services.auth_service import (
    UserRole,
    get_current_institution_id,
    get_current_user,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Constants for export file types
DEFAULT_EXPORT_EXTENSION = ".xlsx"

# Mimetype mapping for common export formats
EXPORT_MIMETYPES = {
    DEFAULT_EXPORT_EXTENSION: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv",
    ".json": "application/json",
}


class InstitutionContextMissingError(Exception):
    """Raised when a request requires institution scope but none is set."""


def get_mimetype_for_extension(file_extension: str) -> str:
    """
    Get appropriate mimetype for a file extension.

    Args:
        file_extension: File extension (e.g., '.xlsx', '.csv')

    Returns:
        str: Appropriate mimetype, defaults to 'application/octet-stream' if unknown
    """
    return EXPORT_MIMETYPES.get(file_extension.lower(), "application/octet-stream")


def resolve_institution_scope(
    require: bool = True,
) -> Tuple[Dict[str, Any], List[str], bool]:
    """
    Return the current user, accessible institution ids, and whether scope is global.

    Args:
        require: If True, raises InstitutionContextMissingError when no scope is available

    Returns:
        Tuple of (current_user, institution_ids, is_global)

    Raises:
        InstitutionContextMissingError: If require=True and no institution scope is available
    """
    current_user = get_current_user()
    institution_id = get_current_institution_id()

    if institution_id:
        return current_user, [institution_id], False

    if current_user and current_user.get("role") == UserRole.SITE_ADMIN.value:
        institutions = get_all_institutions()
        institution_ids = [
            inst["institution_id"]
            for inst in institutions
            if inst.get("institution_id")
        ]
        return current_user, institution_ids, True

    if require:
        raise InstitutionContextMissingError()

    return current_user, [], False


def handle_api_error(
    e: Exception,
    operation_name: str = "API operation",
    user_message: str = "An error occurred",
    status_code: int = 500,
) -> Tuple[Any, int]:
    """
    Securely handle API errors by logging full details while returning sanitized responses.

    Args:
        e: The exception that occurred
        operation_name: Description of what operation failed (for logging)
        user_message: Safe message to return to the user
        status_code: HTTP status code to return

    Returns:
        tuple: (JSON response, HTTP status code)
    """
    # Log error with sanitized details (avoid logging user-controlled data)
    # Only log the operation name and exception type, not the message
    logger.error(
        f"{operation_name} failed with {type(e).__name__}",
        exc_info=True,  # This logs the traceback without the raw exception message
    )

    # Return sanitized response to user
    return jsonify({"success": False, "error": user_message}), status_code


def validate_request_json(required_fields: List[str] = None) -> Dict[str, Any]:
    """
    Validate that request contains JSON data and optionally check for required fields.

    Args:
        required_fields: List of field names that must be present in the JSON

    Returns:
        Dict containing the JSON data

    Raises:
        ValueError: If JSON is missing or required fields are not present
    """
    data = request.get_json()
    if not data:
        raise ValueError("No JSON data provided")

    if required_fields:
        missing_fields = [f for f in required_fields if not data.get(f)]
        if missing_fields:
            raise ValueError(f'Missing required fields: {", ".join(missing_fields)}')

    return data
