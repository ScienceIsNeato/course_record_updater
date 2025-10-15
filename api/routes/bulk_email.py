"""
Bulk Email API routes.

Provides endpoints for sending bulk emails (reminders, invitations) with progress tracking.
Admin only.
"""

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import Session

from api.utils import handle_api_error
from auth_service import get_current_user, permission_required
from bulk_email_service import BulkEmailService
from database_factory import get_database_service
from logging_config import get_logger

# Create blueprint
bulk_email_bp = Blueprint("bulk_email", __name__, url_prefix="/api/bulk-email")

# Initialize logger
logger = get_logger(__name__)

# Constants
ERROR_AUTH_REQUIRED = "Authentication required"


def get_db() -> Session:
    """Get database session"""
    db_service = get_database_service()
    return db_service.sqlite.get_session()  # type: ignore[attr-defined,return-value]


@bulk_email_bp.route("/send-instructor-reminders", methods=["POST"])
@permission_required("manage_programs")  # Program admin or higher
def send_instructor_reminders():
    """
    Send reminder emails to multiple instructors.

    Request Body:
        {
            "instructor_ids": ["id1", "id2", ...],  # List of instructor user IDs
            "personal_message": "Optional message",  # Optional
            "term": "Fall 2024",  # Optional
            "deadline": "2024-12-31"  # Optional
        }

    Returns:
        202: Job created and started
            {
                "success": true,
                "job_id": "uuid",
                "message": "Bulk reminder job started",
                "recipient_count": 5
            }
        400: Invalid request
        403: Insufficient permissions
        500: Server error
    """
    try:
        # Get request data (silent=True to handle empty/invalid JSON)
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"success": False, "error": "Request body is required"}), 400

        # Validate required fields
        instructor_ids = data.get("instructor_ids", [])
        if not instructor_ids or not isinstance(instructor_ids, list):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "instructor_ids must be a non-empty list",
                    }
                ),
                400,
            )

        # Get optional fields
        personal_message = data.get("personal_message")
        term = data.get("term")
        deadline = data.get("deadline")

        # Get current user
        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": ERROR_AUTH_REQUIRED}), 401

        # Permission check: The @permission_required("manage_program_users") decorator
        # ensures user has appropriate permissions to send reminders to instructors.
        # Scope validation (institution/program boundaries) is handled by the decorator.

        # Get database session
        db = get_db()

        try:
            # Start bulk email job
            job_id = BulkEmailService.send_instructor_reminders(
                db=db,
                instructor_ids=instructor_ids,
                created_by_user_id=current_user["user_id"],
                personal_message=personal_message,
                term=term,
                deadline=deadline,
            )

            logger.info(
                f"[BulkEmailAPI] User {current_user['user_id']} started bulk reminder "
                f"job {job_id} for {len(instructor_ids)} instructors"
            )

            return (
                jsonify(
                    {
                        "success": True,
                        "job_id": job_id,
                        "message": "Bulk reminder job started",
                        "recipient_count": len(instructor_ids),
                    }
                ),
                202,
            )

        finally:
            db.close()

    except ValueError as e:
        logger.error(
            f"Send instructor reminders failed with {type(e).__name__}", exc_info=True
        )
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:  # pylint: disable=broad-except
        return handle_api_error(
            e, "Send instructor reminders", "Failed to start bulk reminder job"
        )


@bulk_email_bp.route("/job-status/<job_id>", methods=["GET"])
@permission_required("manage_programs")  # Program admin or higher
def get_job_status(job_id: str):
    """
    Get status of a bulk email job.

    Path Parameters:
        job_id: UUID of the bulk email job

    Returns:
        200: Job status
            {
                "success": true,
                "job": {
                    "id": "uuid",
                    "job_type": "instructor_reminder",
                    "status": "running",  # pending, running, completed, failed, cancelled
                    "recipient_count": 5,
                    "emails_sent": 3,
                    "emails_failed": 0,
                    "emails_pending": 2,
                    "progress_percentage": 60,
                    "created_at": "2024-10-14T12:00:00Z",
                    "started_at": "2024-10-14T12:00:05Z",
                    "completed_at": null,
                    "personal_message": "Please submit by Friday",
                    "failed_recipients": [],
                    "error_message": null
                }
            }
        404: Job not found
        403: Insufficient permissions
        500: Server error
    """
    try:
        # Get current user
        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": ERROR_AUTH_REQUIRED}), 401

        # Get database session
        db = get_db()

        try:
            # Get job status
            job_status = BulkEmailService.get_job_status(db, job_id)

            if not job_status:
                return jsonify({"success": False, "error": "Job not found"}), 404

            # Permission check: Verify user can view this job
            # Allow if: user created the job, OR user is site_admin, OR
            # user is institution_admin and job creator is in same institution
            job_creator_id = job_status.get("created_by_user_id")
            user_role = current_user.get("role")
            user_id = current_user.get("user_id")

            if job_creator_id != user_id and user_role != "site_admin":
                # For institution_admin, would need to check if job creator
                # is in same institution (requires additional query)
                # For now, only allow job creator or site_admin
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "You do not have permission to view this job",
                        }
                    ),
                    403,
                )

            logger.debug(
                f"[BulkEmailAPI] User {current_user['user_id']} retrieved status "
                f"for job {job_id}"
            )

            return jsonify({"success": True, "job": job_status}), 200

        finally:
            db.close()

    except Exception as e:  # pylint: disable=broad-except
        return handle_api_error(e, "Get job status", "Failed to retrieve job status")


@bulk_email_bp.route("/recent-jobs", methods=["GET"])
@permission_required("manage_programs")  # Program admin or higher
def get_recent_jobs():
    """
    Get recent bulk email jobs for the current user.

    Query Parameters:
        limit: Maximum number of jobs to return (default: 50, max: 100)

    Returns:
        200: Recent jobs
            {
                "success": true,
                "jobs": [
                    {
                        "id": "uuid",
                        "job_type": "instructor_reminder",
                        "status": "completed",
                        "recipient_count": 5,
                        "emails_sent": 5,
                        "emails_failed": 0,
                        "created_at": "2024-10-14T12:00:00Z",
                        ...
                    },
                    ...
                ],
                "total": 10
            }
        403: Insufficient permissions
        500: Server error
    """
    try:
        # Get query parameters
        limit = min(int(request.args.get("limit", 50)), 100)

        # Get current user
        current_user = get_current_user()
        if not current_user:
            return jsonify({"success": False, "error": ERROR_AUTH_REQUIRED}), 401

        # Get database session
        db = get_db()

        try:
            # Get recent jobs for this user
            jobs = BulkEmailService.get_recent_jobs(
                db=db, user_id=current_user["user_id"], limit=limit
            )

            logger.debug(
                f"[BulkEmailAPI] User {current_user['user_id']} retrieved "
                f"{len(jobs)} recent jobs"
            )

            return jsonify({"success": True, "jobs": jobs, "total": len(jobs)}), 200

        finally:
            db.close()

    except ValueError as e:
        logger.error(f"Get recent jobs failed with {type(e).__name__}", exc_info=True)
        return jsonify({"success": False, "error": "Invalid parameter"}), 400
    except Exception as e:  # pylint: disable=broad-except
        return handle_api_error(e, "Get recent jobs", "Failed to retrieve recent jobs")
