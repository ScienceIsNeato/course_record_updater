# mypy: disable-error-code=no-untyped-def
"""CLO Workflow API routes for submission and approval."""

from functools import wraps

from flask import Blueprint, jsonify, request, session

from src.api.utils import get_current_user, handle_api_error
from src.database.database_service import (
    get_course_by_id,
    get_course_outcome,
    get_section_outcome,
    get_term_by_name,
)
from src.services.auth_service import get_current_institution_id
from src.services.clo_workflow_service import CLOWorkflowService
from src.utils.constants import OUTCOME_NOT_FOUND_MSG, PERMISSION_DENIED_MSG
from src.utils.logging_config import get_logger


def lazy_permission_required(permission_name: str):
    """Resolve auth_service at runtime so tests can mock permission_required."""

    def decorator(f):
        _wrapped_function = None

        @wraps(f)
        def decorated_function(*args, **kwargs):
            nonlocal _wrapped_function

            if _wrapped_function is None:
                from src.services.auth_service import (
                    permission_required as runtime_permission_required,
                )

                _wrapped_function = runtime_permission_required(permission_name)(f)
            return _wrapped_function(*args, **kwargs)

        return decorated_function

    return decorator


clo_workflow_bp = Blueprint("clo_workflow", __name__, url_prefix="/api/outcomes")
logger = get_logger(__name__)


def _resolve_course_id(section_outcome):
    """Resolve course_id from a section outcome via its template."""
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
    """Submit a completed CLO for admin review (IN_PROGRESS → AWAITING_APPROVAL)."""
    try:
        section_outcome = get_section_outcome(section_outcome_id)
        if not section_outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        user_id = session.get("user_id")
        if not user_id or not isinstance(user_id, str):
            return jsonify({"success": False, "error": "User not authenticated"}), 401
        institution_id = get_current_institution_id()

        course_id = _resolve_course_id(section_outcome)
        course = get_course_by_id(course_id) if course_id else None
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

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
    """Get CLOs awaiting approval, filtered by status/program/term."""
    try:
        institution_id = get_current_institution_id()
        user = get_current_user()

        status_param = request.args.get("status")
        status = None if status_param in (None, "all") else status_param
        program_id = request.args.get("program_id")
        term_id = request.args.get("term_id")
        term_name = request.args.get("term_name")
        course_id = request.args.get("course_id")
        include_stats = request.args.get("include_stats", "false").lower() == "true"

        if not term_id and term_name:
            term = get_term_by_name(term_name, institution_id)
            if term:
                term_id = term.get("term_id")

        if user.get("role") == "program_admin":
            user_program_ids = user.get("program_ids", [])
            if not user_program_ids:
                return jsonify({"success": True, "outcomes": [], "count": 0}), 200

            if program_id and program_id not in user_program_ids:
                return jsonify({"success": False, "error": PERMISSION_DENIED_MSG}), 403
            if not program_id:
                program_id = user_program_ids[0]

        outcomes = CLOWorkflowService.get_clos_by_status(
            status=status,
            institution_id=institution_id,
            program_id=program_id,
            term_id=term_id,
            course_id=course_id,
        )

        response_data = {"success": True, "outcomes": outcomes, "count": len(outcomes)}

        if include_stats and status is None:
            stats_by_status = {}
            for outcome in outcomes:
                outcome_status = outcome.get("status", "unassigned")
                stats_by_status[outcome_status] = (
                    stats_by_status.get(outcome_status, 0) + 1
                )

            response_data["stats_by_status"] = stats_by_status

        return jsonify(response_data), 200

    except Exception as e:
        return handle_api_error(
            e, "Get CLOs for audit", "Failed to retrieve CLOs for audit"
        )


@clo_workflow_bp.route("/<section_outcome_id>/approve", methods=["POST"])
@lazy_permission_required("audit_clo")
def approve_clo(section_outcome_id: str):
    """Approve a submitted CLO (AWAITING_APPROVAL → APPROVED)."""
    try:
        section_outcome = get_section_outcome(section_outcome_id)
        if not section_outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        institution_id = get_current_institution_id()
        course_id = _resolve_course_id(section_outcome)
        course = get_course_by_id(course_id) if course_id else None
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        user_id = session.get("user_id")
        if not user_id or not isinstance(user_id, str):
            return jsonify({"success": False, "error": "User not authenticated"}), 401

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
            return jsonify({"success": False, "error": "Failed to approve CLO"}), 500

    except Exception as e:
        return handle_api_error(e, "Approve CLO", "Failed to approve CLO")


@clo_workflow_bp.route("/<section_outcome_id>/request-rework", methods=["POST"])
@lazy_permission_required("audit_clo")
def request_clo_rework(section_outcome_id: str):
    """Request rework on a submitted CLO with feedback comments."""
    try:
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

        section_outcome = get_section_outcome(section_outcome_id)
        if not section_outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        institution_id = get_current_institution_id()
        course_id = _resolve_course_id(section_outcome)
        course = get_course_by_id(course_id) if course_id else None
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        user_id = session.get("user_id")
        if not user_id or not isinstance(user_id, str):
            return jsonify({"success": False, "error": "User not authenticated"}), 401

        logger.info(
            f"[Rework Request] Calling CLOWorkflowService.request_rework for outcome {section_outcome_id}"
        )
        result = CLOWorkflowService.request_rework(
            section_outcome_id, user_id, comments, send_email
        )
        logger.info(f"[Rework Request] Service returned: {result}")

        if result.get("success"):
            response_data = {
                "success": True,
                "message": "Rework requested successfully",
                "section_outcome_id": section_outcome_id,
            }

            if send_email:
                email_sent = result.get("email_sent", False)
                response_data["email_sent"] = email_sent
                if email_sent:
                    logger.info(
                        f"[Rework Request] SUCCESS: Outcome {section_outcome_id} marked for rework AND email sent"
                    )
                else:
                    logger.warning(
                        f"[Rework Request] PARTIAL SUCCESS: Outcome {section_outcome_id} marked for rework BUT email failed"
                    )
                    response_data["warning"] = (
                        "Rework recorded but email notification failed to send"
                    )
            else:
                logger.info(
                    f"[Rework Request] SUCCESS: Outcome {section_outcome_id} marked for rework (no email requested)"
                )

            return jsonify(response_data), 200
        else:
            logger.error(
                f"[Rework Request] FAILED: Unable to mark outcome {section_outcome_id} for rework"
            )
            return (
                jsonify({"success": False, "error": "Failed to request rework"}),
                500,
            )

    except Exception as e:
        return handle_api_error(e, "Request CLO rework", "Failed to request CLO rework")


@clo_workflow_bp.route("/<section_outcome_id>/mark-nci", methods=["POST"])
@lazy_permission_required("audit_clo")
def mark_clo_as_nci(section_outcome_id: str):
    """Mark a CLO as Never Coming In (NCI)."""
    try:
        data = request.get_json(silent=True)
        reason = data.get("reason") if data else None

        user = get_current_user()
        if not user:
            return jsonify({"success": False, "error": "User not authenticated"}), 401
        user_id = user.get("user_id")
        if not user_id or not isinstance(user_id, str):
            return jsonify({"success": False, "error": "User ID not found"}), 401

        section_outcome = get_section_outcome(section_outcome_id)
        if not section_outcome:
            return jsonify({"success": False, "error": "Outcome not found"}), 404

        institution_id = get_current_institution_id()
        course_id = _resolve_course_id(section_outcome)
        course = get_course_by_id(course_id) if course_id else None
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": "Outcome not found"}), 404

        success = CLOWorkflowService.mark_as_nci(section_outcome_id, user_id, reason)

        if success:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Outcome marked as Never Coming In (NCI)",
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
    """Reopen a finalized CLO (Approved or NCI) back to IN_PROGRESS."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({"success": False, "error": "User not authenticated"}), 401
        user_id = user.get("user_id")

        section_outcome = get_section_outcome(section_outcome_id)
        if not section_outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

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
    """Get full audit details for a single section CLO."""
    try:
        section_outcome = get_section_outcome(section_outcome_id)
        if not section_outcome:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

        institution_id = get_current_institution_id()
        course_id = _resolve_course_id(section_outcome)
        course = get_course_by_id(course_id) if course_id else None
        if not course or course.get("institution_id") != institution_id:
            return jsonify({"success": False, "error": OUTCOME_NOT_FOUND_MSG}), 404

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
