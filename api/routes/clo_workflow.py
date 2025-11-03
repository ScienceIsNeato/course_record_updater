"""
CLO Workflow API routes.

Provides endpoints for the CLO submission and approval workflow:
- Instructors submit CLOs for approval
- Admins review, approve, or request rework on CLOs
"""

from functools import wraps

from flask import Blueprint, jsonify, request, session

from api.utils import get_current_user, handle_api_error
from auth_service import get_current_institution_id
from clo_workflow_service import CLOWorkflowService
from constants import OUTCOME_NOT_FOUND_MSG, PERMISSION_DENIED_MSG
from database_service import get_course_by_id, get_course_outcome
from logging_config import get_logger


def lazy_permission_required(permission_name: str):
    """
    Lazy permission decorator that resolves auth_service at RUNTIME, not import time.

    This allows tests to mock permission_required before the decorator is evaluated.
    The standard @permission_required decorator captures the function at import time,
    making it impossible to mock in tests.

    Args:
        permission_name: The permission required (e.g., "update_clo", "audit_clo")

    Returns:
        Decorator function
    """
    def decorator(f):
        # Cache the wrapped function to avoid re-wrapping on every request
        _wrapped_function = None

        @wraps(f)
        def decorated_function(*args, **kwargs):
            nonlocal _wrapped_function

            # Only wrap once (on first request)
            if _wrapped_function is None:
                # Import auth_service at RUNTIME, not import time
                from auth_service import (
                    permission_required as runtime_permission_required,
                )

                # Get the actual permission_required decorator
                actual_decorator = runtime_permission_required(permission_name)

                # Apply it ONCE and cache the result
                _wrapped_function = actual_decorator(f)

            # Call the cached wrapped function
            return _wrapped_function(*args, **kwargs)

        return decorated_function
    return decorator


# Create blueprint
clo_workflow_bp = Blueprint("clo_workflow", __name__, url_prefix="/api/outcomes")

# Initialize logger
logger = get_logger(__name__)


@clo_workflow_bp.route("/<outcome_id>/submit", methods=["POST"])
@lazy_permission_required("submit_clo")
def submit_clo_for_approval(outcome_id: str):
    """
    Instructor submits their completed CLO for admin review.
    Changes status from IN_PROGRESS to AWAITING_APPROVAL.
    """
    try:
        # Verify outcome exists
        outcome = get_course_outcome(outcome_id)
        if not outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Verify user has access (owns the course section)
        user_id = session.get("user_id")
        institution_id = get_current_institution_id()

        # Verify institution access through course
        course = get_course_by_id(outcome.get("course_id"))
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Submit for approval
        success = CLOWorkflowService.submit_clo_for_approval(outcome_id, user_id)

        if success:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "CLO submitted for approval successfully",
                        "outcome_id": outcome_id,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {"success": False, "error": "Failed to submit CLO for approval"}
                ),
                500,
            )

    except Exception as e:
        return handle_api_error(
            e, "Submit CLO for approval", "Failed to submit CLO for approval"
        )


@clo_workflow_bp.route("/audit", methods=["GET"])
@lazy_permission_required("audit_clo")
def get_clos_for_audit():
    """
    Get CLOs awaiting approval for audit review.

    Program admins see CLOs in their programs.
    Institution admins see all CLOs at their institution.

    Query parameters:
    - status: Filter by specific status (default: awaiting_approval)
    - program_id: Filter by specific program (program admins only see their programs)
    """
    try:
        institution_id = get_current_institution_id()
        user = get_current_user()

        # Get query parameters
        status = request.args.get("status", "awaiting_approval")
        program_id = request.args.get("program_id")

        # Program admins can only see their programs
        if user.get("role") == "program_admin":
            # Get program IDs from user
            user_program_ids = user.get("program_ids", [])
            if not user_program_ids:
                # No programs assigned, return empty list
                return jsonify({"success": True, "outcomes": [], "count": 0}), 200

            if program_id and program_id not in user_program_ids:
                # Requested program not in user's scope
                return jsonify({"success": False, "error": PERMISSION_DENIED_MSG}), 403

            # Use first program if not specified
            if not program_id:
                program_id = user_program_ids[0]

        # Get CLOs by status
        outcomes = CLOWorkflowService.get_clos_by_status(
            status=status,
            institution_id=institution_id,
            program_id=program_id,
        )

        return (
            jsonify({"success": True, "outcomes": outcomes, "count": len(outcomes)}),
            200,
        )

    except Exception as e:
        return handle_api_error(
            e, "Get CLOs for audit", "Failed to retrieve CLOs for audit"
        )


@clo_workflow_bp.route("/<outcome_id>/approve", methods=["POST"])
@lazy_permission_required("audit_clo")
def approve_clo(outcome_id: str):
    """
    Approve a CLO that has been submitted for review.

    Changes status from AWAITING_APPROVAL (or APPROVAL_PENDING) to APPROVED.
    """
    try:
        # Verify outcome exists
        outcome = get_course_outcome(outcome_id)
        if not outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Verify institution access
        institution_id = get_current_institution_id()
        course = get_course_by_id(outcome.get("course_id"))
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Get reviewer ID
        user_id = session.get("user_id")

        # Approve the CLO
        success = CLOWorkflowService.approve_clo(outcome_id, user_id)

        if success:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "CLO approved successfully",
                        "outcome_id": outcome_id,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to approve CLO"}),
                500,
            )

    except Exception as e:
        return handle_api_error(e, "Approve CLO", "Failed to approve CLO")


@clo_workflow_bp.route("/<outcome_id>/request-rework", methods=["POST"])
@lazy_permission_required("audit_clo")
def request_clo_rework(outcome_id: str):
    """
    Request rework on a submitted CLO with feedback comments.

    Request body:
    - comments: Feedback explaining what needs to be fixed (required)
    - send_email: Whether to email the instructor (default: false)

    Changes status from AWAITING_APPROVAL to APPROVAL_PENDING.
    """
    try:
        # Get request data
        data = request.get_json(silent=True)
        if not data or "comments" not in data:
            return (
                jsonify({"success": False, "error": "comments field is required"}),
                400,
            )

        comments = data.get("comments", "").strip()
        if not comments:
            return jsonify({"success": False, "error": "comments cannot be empty"}), 400

        send_email = data.get("send_email", False)

        # Verify outcome exists
        outcome = get_course_outcome(outcome_id)
        if not outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Verify institution access
        institution_id = get_current_institution_id()
        course = get_course_by_id(outcome.get("course_id"))
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Get reviewer ID
        user_id = session.get("user_id")

        # Request rework
        success = CLOWorkflowService.request_rework(
            outcome_id, user_id, comments, send_email
        )

        if success:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Rework requested successfully",
                        "outcome_id": outcome_id,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to request rework"}),
                500,
            )

    except Exception as e:
        return handle_api_error(
            e, "Request CLO rework", "Failed to request CLO rework"
        )


@clo_workflow_bp.route("/<outcome_id>/audit-details", methods=["GET"])
@lazy_permission_required("audit_clo")
def get_clo_audit_details(outcome_id: str):
    """
    Get full audit details for a single CLO.

    Includes course info, instructor info, submission history, feedback history.
    """
    try:
        # Verify outcome exists
        outcome = get_course_outcome(outcome_id)
        if not outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Verify institution access
        institution_id = get_current_institution_id()
        course = get_course_by_id(outcome.get("course_id"))
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Get enriched outcome details
        details = CLOWorkflowService.get_outcome_with_details(outcome_id)

        if details:
            return jsonify({"success": True, "outcome": details}), 200
        else:
            return (
                jsonify({"success": False, "error": "Failed to load outcome details"}),
                500,
            )

    except Exception as e:
        return handle_api_error(e, "Get CLO audit details", "Failed to load CLO audit details")

