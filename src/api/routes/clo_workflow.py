# mypy: disable-error-code=no-untyped-def
"""
CLO Workflow API routes.

Provides endpoints for the CLO submission and approval workflow:
- Instructors submit CLOs for approval
- Admins review, approve, or request rework on CLOs
"""

from functools import wraps

from flask import Blueprint, jsonify, request, session

from src.api.utils import get_current_user, handle_api_error
from src.database.database_service import (
    get_all_courses,
    get_course_by_id,
    get_course_outcome,
    get_course_outcomes,
    get_section_outcome,
    get_term_by_name,
)
from src.services.auth_service import get_current_institution_id
from src.services.clo_workflow_service import CLOWorkflowService
from src.utils.constants import OUTCOME_NOT_FOUND_MSG, PERMISSION_DENIED_MSG
from src.utils.logging_config import get_logger


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
                from src.services.auth_service import (
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


def _resolve_course_id(section_outcome):
    """
    Resolve course_id from a section outcome by looking up the template.
    Section outcomes don't store course_id directly.
    """
    # Try getting from template link
    outcome_id = section_outcome.get("outcome_id")
    if outcome_id:
        course_outcome = get_course_outcome(outcome_id)
        if course_outcome:
            return course_outcome.get("course_id")

    # Fallback to course_id if it somehow exists (e.g. if enriched)
    return section_outcome.get("course_id")


@clo_workflow_bp.route("/<section_outcome_id>/submit", methods=["POST"])
@lazy_permission_required("submit_clo")
def submit_clo_for_approval(section_outcome_id: str):
    """
    Instructor submits their completed CLO for admin review.
    Changes status from IN_PROGRESS to AWAITING_APPROVAL.
    """
    try:
        # Verify section outcome exists

        section_outcome = get_section_outcome(section_outcome_id)
        if not section_outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Verify user has access (owns the course section)
        user_id = session.get("user_id")
        if not user_id or not isinstance(user_id, str):
            return jsonify({"success": False, "error": "User not authenticated"}), 401
        institution_id = get_current_institution_id()

        # Verify institution access through course
        course_id = _resolve_course_id(section_outcome)
        course = get_course_by_id(course_id) if course_id else None
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Submit for approval
        success = CLOWorkflowService.submit_clo_for_approval(
            section_outcome_id, user_id
        )

        if success:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "CLO submitted for approval successfully",
                        "section_outcome_id": section_outcome_id,
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
    - term_id: Filter by specific term (matches /api/terms IDs)
    - term_name: Optional convenience filter for term name when IDs unavailable
    """
    try:
        institution_id = get_current_institution_id()
        user = get_current_user()

        # Get query parameters (default to None = all statuses if not specified)
        status_param = request.args.get("status")
        status = None if status_param in (None, "all") else status_param
        program_id = request.args.get("program_id")
        term_id = request.args.get("term_id")
        term_name = request.args.get("term_name")
        course_id = request.args.get("course_id")

        if not term_id and term_name:
            term = get_term_by_name(term_name, institution_id)
            if term:
                term_id = term.get("term_id")

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

        # Get CLOs by status (status is already None for "all" or a specific value)
        outcomes = CLOWorkflowService.get_clos_by_status(
            status=status,
            institution_id=institution_id,
            program_id=program_id,
            term_id=term_id,
            course_id=course_id,
        )

        return (
            jsonify({"success": True, "outcomes": outcomes, "count": len(outcomes)}),
            200,
        )

    except Exception as e:
        return handle_api_error(
            e, "Get CLOs for audit", "Failed to retrieve CLOs for audit"
        )


@clo_workflow_bp.route("/<section_outcome_id>/approve", methods=["POST"])
@lazy_permission_required("audit_clo")
def approve_clo(section_outcome_id: str):
    """
    Approve a CLO that has been submitted for review.

    Changes status from AWAITING_APPROVAL (or APPROVAL_PENDING) to APPROVED.
    """
    try:
        # Verify section outcome exists

        section_outcome = get_section_outcome(section_outcome_id)
        if not section_outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Verify institution access
        institution_id = get_current_institution_id()
        course_id = _resolve_course_id(section_outcome)
        course = get_course_by_id(course_id) if course_id else None
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Get reviewer ID
        user_id = session.get("user_id")
        if not user_id or not isinstance(user_id, str):
            return jsonify({"success": False, "error": "User not authenticated"}), 401

        # Approve the CLO
        success = CLOWorkflowService.approve_clo(section_outcome_id, user_id)

        if success:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "CLO approved successfully",
                        "section_outcome_id": section_outcome_id,
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


@clo_workflow_bp.route("/<section_outcome_id>/request-rework", methods=["POST"])
@lazy_permission_required("audit_clo")
def request_clo_rework(section_outcome_id: str):
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

        # Verify section outcome exists

        section_outcome = get_section_outcome(section_outcome_id)
        if not section_outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Verify institution access
        institution_id = get_current_institution_id()
        course_id = _resolve_course_id(section_outcome)
        course = get_course_by_id(course_id) if course_id else None
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Get reviewer ID
        user_id = session.get("user_id")
        if not user_id or not isinstance(user_id, str):
            return jsonify({"success": False, "error": "User not authenticated"}), 401

        # Request rework
        success = CLOWorkflowService.request_rework(
            section_outcome_id, user_id, comments, send_email
        )

        if success:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Rework requested successfully",
                        "section_outcome_id": section_outcome_id,
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
        return handle_api_error(e, "Request CLO rework", "Failed to request CLO rework")


@clo_workflow_bp.route("/<section_outcome_id>/mark-nci", methods=["POST"])
@lazy_permission_required("audit_clo")
def mark_clo_as_nci(section_outcome_id: str):
    """
    Mark a CLO as "Never Coming In" (NCI).

    Use cases from CEI demo feedback:
    - Instructor left institution
    - Instructor non-responsive despite multiple reminders
    - Course cancelled/dropped after initial assignment

    Changes status to NEVER_COMING_IN.
    """
    try:
        data = request.get_json(silent=True)
        reason = data.get("reason") if data else None

        user = get_current_user()
        if not user:
            return jsonify({"success": False, "error": "User not authenticated"}), 401
        user_id = user.get("user_id")
        if not user_id or not isinstance(user_id, str):
            return jsonify({"success": False, "error": "User ID not found"}), 401

        # Verify section outcome exists and belongs to current institution (efficient O(1) lookup)
        section_outcome = get_section_outcome(section_outcome_id)
        if not section_outcome:
            return jsonify({"success": False, "error": "Outcome not found"}), 404

        # Verify institution access
        institution_id = get_current_institution_id()
        course_id = _resolve_course_id(section_outcome)
        course = get_course_by_id(course_id) if course_id else None
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": "Outcome not found"}), 404

        # Mark as NCI
        success = CLOWorkflowService.mark_as_nci(section_outcome_id, user_id, reason)

        if success:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "CLO marked as Never Coming In (NCI)",
                    }
                ),
                200,
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to mark CLO as NCI"}),
                500,
            )

    except Exception as e:
        return handle_api_error(e, "Mark CLO as NCI", "Failed to mark CLO as NCI")


@clo_workflow_bp.route("/<section_outcome_id>/reopen", methods=["POST"])
@lazy_permission_required("audit_clo")
def reopen_clo(section_outcome_id: str):
    """
    Reopen a finalized CLO (Approved or NCI).

    Changes status back to IN_PROGRESS.
    """
    try:
        user = get_current_user()
        if not user:
            return jsonify({"success": False, "error": "User not authenticated"}), 401
        user_id = user.get("user_id")

        # Verify section outcome exists

        section_outcome = get_section_outcome(section_outcome_id)
        if not section_outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Verify institution access
        institution_id = get_current_institution_id()
        course_id = _resolve_course_id(section_outcome)
        course = get_course_by_id(course_id) if course_id else None
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        if not user_id:
            return jsonify({"success": False, "error": "User not authenticated"}), 401

        success = CLOWorkflowService.reopen_clo(section_outcome_id, str(user_id))

        if success:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "CLO reopened successfully",
                        "section_outcome_id": section_outcome_id,
                    }
                ),
                200,
            )
        else:
            return jsonify({"success": False, "error": "Failed to reopen CLO"}), 500

    except Exception as e:
        return handle_api_error(e, "Reopen CLO", "Failed to reopen CLO")


@clo_workflow_bp.route("/<section_outcome_id>/audit-details", methods=["GET"])
@lazy_permission_required("audit_clo")
def get_clo_audit_details(section_outcome_id: str):
    """
    Get full audit details for a single section CLO.

    Includes course info, instructor info, submission history, feedback history.
    """
    try:
        # Verify section outcome exists

        section_outcome = get_section_outcome(section_outcome_id)
        if not section_outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Verify institution access
        institution_id = get_current_institution_id()
        course_id = _resolve_course_id(section_outcome)
        course = get_course_by_id(course_id) if course_id else None
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        # Get enriched outcome details
        details = CLOWorkflowService.get_outcome_with_details(section_outcome_id)

        if details:
            return jsonify({"success": True, "outcome": details}), 200
        else:
            return (
                jsonify({"success": False, "error": "Failed to load outcome details"}),
                500,
            )

    except Exception as e:
        return handle_api_error(
            e, "Get CLO audit details", "Failed to load CLO audit details"
        )
