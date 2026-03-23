"""
CLO Workflow Service

Manages the submission, review, and approval workflow for Course Learning Outcomes (CLOs).
"""

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

from src.database.database_service import db
from src.utils.constants import CLOApprovalStatus, CLOStatus
from src.utils.logging_config import get_logger
from src.utils.time_utils import get_current_time

from .clo_workflow_details import CLOWorkflowDetailsMixin
from .email_service import EmailService

logger = get_logger(__name__)

SECTION_OUTCOME_NOT_FOUND_MSG = "Section outcome not found: {section_outcome_id}"


class CLOWorkflowService(CLOWorkflowDetailsMixin):
    """Service for managing CLO submission and approval workflows."""

    @staticmethod
    def submit_clo_for_approval(
        section_outcome_id: str, user_id: str, notify_admins: bool = False
    ) -> bool:
        """
        Submit a section-level CLO for approval review.

        Args:
            section_outcome_id: The ID of the section outcome to submit
            user_id: The ID of the user submitting (instructor)

        Returns:
            bool: True if submission successful, False otherwise
        """
        try:
            outcome = db.get_section_outcome(section_outcome_id)
            if not outcome:
                logger.error(
                    SECTION_OUTCOME_NOT_FOUND_MSG.format(
                        section_outcome_id=logger.sanitize(section_outcome_id)
                    )
                )
                return False
            if outcome.get("status") in [CLOStatus.APPROVED, CLOStatus.COMPLETED]:
                logger.info(
                    "Skipping submission for approved CLO %s",
                    logger.sanitize(section_outcome_id),
                )
                return False

            # Update status and submission metadata
            update_data: Dict[str, Any] = {
                "status": CLOStatus.AWAITING_APPROVAL,
                "submitted_at": datetime.now(timezone.utc),
                "submitted_by": user_id,
                "approval_status": CLOApprovalStatus.PENDING,
            }

            success = db.update_section_outcome(section_outcome_id, update_data)
            if success:
                logger.info(
                    f"Section CLO {logger.sanitize(section_outcome_id)} submitted for approval by user {logger.sanitize(user_id)}"
                )
                # Send admin notification if requested
                if notify_admins:
                    CLOWorkflowService._notify_program_admins(
                        section_outcome_id, user_id
                    )
            else:
                logger.error(
                    f"Failed to update section CLO {logger.sanitize(section_outcome_id)} status"
                )

            return success

        except Exception as e:
            logger.error(f"Error submitting CLO for approval: {e}")
            return False

    @staticmethod
    def approve_clo(section_outcome_id: str, reviewer_id: str) -> bool:
        """
        Approve a section-level CLO that has been submitted for review.

        Args:
            section_outcome_id: The ID of the section outcome to approve
            reviewer_id: The ID of the reviewing admin

        Returns:
            bool: True if approval successful, False otherwise
        """
        try:
            outcome = db.get_section_outcome(section_outcome_id)
            if not outcome:
                logger.error(
                    SECTION_OUTCOME_NOT_FOUND_MSG.format(
                        section_outcome_id=section_outcome_id
                    )
                )
                return False

            # Verify CLO is in a state that can be approved
            # Both awaiting_approval and approval_pending (needs rework) can be approved
            if outcome.get("status") not in [
                CLOStatus.AWAITING_APPROVAL,
                "approval_pending",  # Needs Rework status - can be approved after fixes
            ]:
                logger.warning(
                    f"Section CLO {section_outcome_id} is in {outcome.get('status')} state, "
                    f"cannot approve"
                )
                return False

            # Update status and review metadata
            # Note: Preserve feedback_comments and feedback_provided_at for audit trail
            update_data: Dict[str, Any] = {
                "status": CLOStatus.APPROVED,
                "approval_status": CLOApprovalStatus.APPROVED,
                "reviewed_at": datetime.now(timezone.utc),
                "reviewed_by": reviewer_id,
            }

            success = db.update_section_outcome(section_outcome_id, update_data)
            if success:
                logger.info(
                    f"Section CLO {section_outcome_id} approved by reviewer {reviewer_id}"
                )
            else:
                logger.error(f"Failed to approve section CLO {section_outcome_id}")

            return success

        except Exception as e:
            logger.error(f"Error approving CLO: {e}")
            return False

    @staticmethod
    def request_rework(
        section_outcome_id: str,
        reviewer_id: str,
        comments: str,
        send_email: bool = False,
    ) -> dict[str, Any]:
        """
        Request rework on a submitted section-level CLO with feedback comments.

        Args:
            section_outcome_id: The ID of the section outcome needing rework
            reviewer_id: The ID of the reviewing admin
            comments: Feedback comments explaining what needs to be fixed
            send_email: Whether to send email notification to the instructor

        Returns:
            dict: {"success": bool, "email_sent": bool} - success indicates if rework was recorded, email_sent indicates if notification was delivered
        """
        try:
            outcome = db.get_section_outcome(section_outcome_id)
            if not outcome:
                logger.error(
                    SECTION_OUTCOME_NOT_FOUND_MSG.format(
                        section_outcome_id=section_outcome_id
                    )
                )
                return {"success": False, "email_sent": False}

            # Verify CLO is in a state that can be sent back for rework
            if outcome.get("status") not in [
                CLOStatus.AWAITING_APPROVAL,
                "approval_pending",  # Already in rework, allow re-rework
            ]:
                logger.warning(
                    f"Section CLO {section_outcome_id} is in {outcome.get('status')} state, "
                    f"cannot request rework"
                )
                return {"success": False, "email_sent": False}

            # Update status and feedback
            # NOTE: Using "approval_pending" string because the UI expects this for
            # displaying the "Needs Rework" badge. CLOStatus.AWAITING_APPROVAL would
            # display as "Awaiting Approval" which is incorrect after rework is requested.
            update_data: Dict[str, Any] = {
                "status": "approval_pending",  # UI badge for "Needs Rework"
                "approval_status": CLOApprovalStatus.NEEDS_REWORK,
                "reviewed_at": datetime.now(timezone.utc),
                "reviewed_by": reviewer_id,
                "feedback_comments": comments,
            }

            success = db.update_section_outcome(section_outcome_id, update_data)
            if not success:
                logger.error(
                    f"Failed to request rework for section CLO {section_outcome_id}"
                )
                return {"success": False, "email_sent": False}

            logger.info(
                f"Section CLO {section_outcome_id} sent back for rework by reviewer {reviewer_id}"
            )

            # Send email notification if requested
            email_sent = False
            if send_email:
                email_sent = CLOWorkflowService._send_rework_notification(
                    section_outcome_id, comments
                )
                if not email_sent:
                    logger.warning(
                        f"Rework recorded for {section_outcome_id} but email notification failed"
                    )

            return {"success": True, "email_sent": email_sent}

        except Exception as e:
            logger.error(f"Error requesting rework for CLO: {e}")
            return {"success": False, "email_sent": False}

    @staticmethod
    def reopen_clo(section_outcome_id: str, reviewer_id: str) -> bool:
        """
        Reopen a finalized CLO (Approved or NCI).

        Changes status back to IN_PROGRESS and approval_status to PENDING.

        Args:
            section_outcome_id: The ID of the section outcome to reopen
            reviewer_id: The ID of the admin reopening

        Returns:
            bool: True if successful
        """
        try:
            outcome = db.get_section_outcome(section_outcome_id)
            if not outcome:
                logger.error(
                    SECTION_OUTCOME_NOT_FOUND_MSG.format(
                        section_outcome_id=section_outcome_id
                    )
                )
                return False

            # Allow reopening from Approved or NCI
            if outcome.get("status") not in [
                CLOStatus.APPROVED,
                CLOStatus.NEVER_COMING_IN,
            ]:
                logger.warning(
                    f"Section CLO {section_outcome_id} status {outcome.get('status')} cannot be reopened"
                )
                return False

            update_data = {
                "status": CLOStatus.AWAITING_APPROVAL,  # Ready for re-approval after reopen
                "approval_status": CLOApprovalStatus.PENDING,
                # Note: Keeps existing assessment data and history for audit trail
            }

            success = db.update_section_outcome(section_outcome_id, update_data)
            if success:
                logger.info(
                    f"Section CLO {section_outcome_id} reopened by {reviewer_id}"
                )

            return success

        except Exception as e:
            logger.error(f"Error reopening CLO: {e}")
            return False

    @staticmethod
    def mark_as_nci(
        section_outcome_id: str, reviewer_id: str, reason: Optional[str] = None
    ) -> bool:
        """
        Mark a section-level CLO as "Never Coming In" (NCI).

        Use cases:
        - Instructor left institution
        - Instructor non-responsive despite multiple reminders
        - Course cancelled/dropped after initial assignment

        Args:
            section_outcome_id: The ID of the section outcome to mark as NCI
            reviewer_id: The ID of the admin marking as NCI
            reason: Optional reason/note for NCI designation

        Returns:
            bool: True if successfully marked as NCI, False otherwise
        """
        try:
            outcome = db.get_section_outcome(section_outcome_id)
            if not outcome:
                logger.error(
                    SECTION_OUTCOME_NOT_FOUND_MSG.format(
                        section_outcome_id=section_outcome_id
                    )
                )
                return False

            # Update status to NCI
            update_data: Dict[str, Any] = {
                "status": CLOStatus.NEVER_COMING_IN,
                "approval_status": CLOApprovalStatus.NEVER_COMING_IN,
                "reviewed_at": datetime.now(timezone.utc),
                "reviewed_by": reviewer_id,
                "feedback_comments": reason or "Marked as Never Coming In (NCI)",
            }

            success = db.update_section_outcome(section_outcome_id, update_data)
            if not success:
                logger.error(f"Failed to mark section CLO {section_outcome_id} as NCI")
                return False

            logger.info(
                f"Section CLO {section_outcome_id} marked as NCI by reviewer {reviewer_id}"
                + (f" - Reason: {reason}" if reason else "")
            )

            return True

        except Exception as e:
            logger.error(f"Error marking CLO as NCI: {e}")
            return False

    @staticmethod
    def _send_rework_notification(outcome_id: str, feedback: str) -> bool:
        """
        Send email notification to instructor about rework request.

        Args:
            outcome_id: The ID of the course outcome
            feedback: The feedback comments

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Get outcome with related course/instructor details
            outcome_details = CLOWorkflowService.get_outcome_with_details(outcome_id)
            if not outcome_details:
                logger.error(f"Could not load outcome details for {outcome_id}")
                return False
            outcome_data = cast(Dict[str, Any], outcome_details)

            instructor_email = outcome_data.get("instructor_email")
            if not instructor_email:
                logger.error(f"No instructor email found for outcome {outcome_id}")
                return False

            course_number = outcome_data.get("course_number", "Unknown Course")
            clo_number = outcome_data.get("clo_number", "Unknown CLO")
            instructor_name = outcome_data.get("instructor_name", "Instructor")

            # Compose email using templates
            from urllib.parse import urljoin

            from flask import current_app, render_template

            subject = f"Feedback on CLO {clo_number} for {course_number}"

            # Build assessment URL
            app_config = cast(Mapping[str, Any], current_app.config)
            base_url = str(app_config.get("BASE_URL", "http://localhost:3001"))
            course_id = outcome_data.get("course_id")
            if course_id:
                assessment_url = urljoin(base_url, f"/assessments?course={course_id}")
            else:
                # Fallback to general assessments page if no course_id
                assessment_url = urljoin(base_url, "/assessments")

            template_context: Dict[str, Any] = {
                "clo_number": clo_number,
                "course_number": course_number,
                "course_code": course_number,
                "feedback": feedback,
                "assessment_url": assessment_url,
                "instructor_name": instructor_name,
                "to_email": instructor_email,
                "current_year": get_current_time().year,
            }

            text_body = render_template(  # nosemgrep
                "emails/clo_rework_notification.txt", **template_context
            )
            html_body = render_template(
                "emails/clo_rework_notification.html", **template_context
            )

            # Send email using existing email service
            success = EmailService._send_email(
                to_email=instructor_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )

            if success:
                logger.info(f"Rework notification sent to {instructor_email}")
            else:
                logger.error(
                    f"Failed to send rework notification to {instructor_email}"
                )

            return success

        except Exception as e:
            logger.error(f"Error sending rework notification: {e}")
            return False

    @staticmethod
    def auto_mark_in_progress(section_outcome_id: str, user_id: str) -> bool:
        """
        Automatically mark a section CLO as in_progress when an instructor starts editing.

        Args:
            section_outcome_id: The ID of the section outcome
            user_id: The ID of the user editing

        Returns:
            bool: True if status updated, False otherwise
        """
        try:
            outcome = db.get_section_outcome(section_outcome_id)
            if not outcome:
                logger.error(
                    SECTION_OUTCOME_NOT_FOUND_MSG.format(
                        section_outcome_id=section_outcome_id
                    )
                )
                return False

            current_status = outcome.get("status")

            # Only auto-mark if currently assigned or approval_pending
            if current_status not in [CLOStatus.ASSIGNED, CLOStatus.AWAITING_APPROVAL]:
                # Already in progress or submitted, don't change status
                return True

            update_data: Dict[str, Any] = {"status": CLOStatus.IN_PROGRESS}
            success = db.update_section_outcome(section_outcome_id, update_data)

            if success:
                logger.info(
                    f"Section CLO {section_outcome_id} automatically marked as in_progress"
                )

            return success

        except Exception as e:
            logger.error(f"Error auto-marking CLO in progress: {e}")
            return False

    @staticmethod
    def mark_section_outcomes_assigned(section_id: str) -> bool:
        """
        When a section receives an instructor assignment, ensure all related section
        outcomes move out of the 'unassigned' bucket so the audit UI reflects the new
        ownership immediately.
        """
        try:
            section_outcomes = db.get_section_outcomes_by_section(section_id)
            for outcome in section_outcomes:
                outcome_id = outcome.get("id")
                if not outcome_id:
                    continue
                if outcome.get("status") != CLOStatus.UNASSIGNED:
                    continue
                success = db.update_section_outcome(
                    outcome_id, {"status": CLOStatus.ASSIGNED}
                )
                if not success:
                    logger.error(
                        "Failed to update status for section outcome %s",
                        logger.sanitize(outcome_id),
                    )
                    return False
            return True
        except Exception as e:
            logger.error(
                "Error marking section outcomes assigned for section %s: %s",
                logger.sanitize(section_id),
                e,
            )
            return False

    @staticmethod
    def _validate_clo_fields(outcome: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate required fields for a single CLO."""
        errors: List[Dict[str, Any]] = []
        outcome_id = outcome.get("outcome_id") or outcome.get("id")
        clo_number = outcome.get("clo_number", "?")

        students_took = outcome.get("students_took")
        students_passed = outcome.get("students_passed")
        assessment_tool = outcome.get("assessment_tool") or ""

        # Check required fields
        if students_took is None:
            errors.append(
                {
                    "outcome_id": outcome_id,
                    "field": "students_took",
                    "message": f"CLO {clo_number}: Students Took is required",
                }
            )

        if students_passed is None:
            errors.append(
                {
                    "outcome_id": outcome_id,
                    "field": "students_passed",
                    "message": f"CLO {clo_number}: Students Passed is required",
                }
            )

        if not assessment_tool.strip():
            errors.append(
                {
                    "outcome_id": outcome_id,
                    "field": "assessment_tool",
                    "message": f"CLO {clo_number}: Assessment Tool is required",
                }
            )

        # Check logical constraint: passed can't exceed took
        if (
            students_took is not None
            and students_passed is not None
            and students_passed > students_took
        ):
            errors.append(
                {
                    "outcome_id": outcome_id,
                    "field": "students_passed",
                    "message": f"CLO {clo_number}: Students Passed cannot exceed Students Took",
                }
            )

        return errors

    @staticmethod
    def _validate_section_data(section_id: str) -> List[Dict[str, Any]]:
        """Validate course-level section data."""
        errors: List[Dict[str, Any]] = []
        section = db.get_section_by_id(section_id)

        if section:
            if section.get("students_passed") is None:
                errors.append(
                    {
                        "outcome_id": None,
                        "field": "course_students_passed",
                        "message": "Course: Students Passed (A/B/C) is required",
                    }
                )
            if section.get("students_dfic") is None:
                errors.append(
                    {
                        "outcome_id": None,
                        "field": "course_students_dfic",
                        "message": "Course: Students D/F/Incomplete is required",
                    }
                )

        return errors

    @staticmethod
    def validate_course_submission(
        course_id: str, section_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate CLOs and course-level data for the specified section before submission.

        Args:
            course_id: The course ID to validate
            section_id: Section ID to validate (REQUIRED for scoped validation)
            user_id: Optional user ID to determine appropriate sections to check

        Returns:
            Dict with 'valid' bool and 'errors' list of error details
        """
        try:
            # If section_id provided, validate ONLY that section
            # This supports per-section submission workflow
            section_outcomes: List[Dict[str, Any]]
            if section_id:
                logger.info(
                    f"DEBUG: Validating ONLY section {section_id} for course {course_id}"
                )
                section_outcomes = db.get_section_outcomes_by_section(section_id)
                logger.info(
                    f"DEBUG: Section {section_id} has {len(section_outcomes)} outcomes"
                )
            else:
                # No section_id: validate ALL sections (legacy behavior for batch submission)
                if user_id:
                    # Get user info to determine role
                    from src.database.database_service import get_user_by_id

                    user = get_user_by_id(user_id)
                    if user and user.get("role") == "instructor":
                        # Instructors can only see their own sections
                        sections = db.get_sections_by_instructor(user_id)
                        # Filter to only sections for this course
                        sections = [
                            s for s in sections if s.get("course_id") == course_id
                        ]
                    else:
                        # Admins and other roles can see all sections
                        sections = db.get_sections_by_course(course_id)
                else:
                    # Fallback to all sections
                    sections = db.get_sections_by_course(course_id)

                # Get all section outcomes for this course
                section_outcomes = []
                logger.info(
                    f"DEBUG: Found {len(sections)} sections for course {course_id}"
                )
                for section in sections:
                    sect_id = section.get("section_id")
                    logger.info(f"DEBUG: Processing section {sect_id}")
                    if sect_id:
                        outcomes = db.get_section_outcomes_by_section(sect_id)
                        logger.info(
                            f"DEBUG: Section {sect_id} has {len(outcomes)} outcomes"
                        )
                        section_outcomes.extend(outcomes)

            if not section_outcomes:
                return {
                    "valid": False,
                    "errors": [
                        {
                            "outcome_id": None,
                            "field": "course",
                            "message": "No section outcomes found for this course",
                        }
                    ],
                }

            errors: List[Dict[str, Any]] = []

            # Validate each section outcome
            for section_outcome in section_outcomes:
                errors.extend(CLOWorkflowService._validate_clo_fields(section_outcome))

            # Validate course-level section data if section provided
            if section_id:
                errors.extend(CLOWorkflowService._validate_section_data(section_id))

            return {"valid": len(errors) == 0, "errors": errors}

        except Exception as e:
            logger.error(f"Error validating course submission: {e}")
            return {
                "valid": False,
                "errors": [
                    {
                        "outcome_id": None,
                        "field": "system",
                        "message": f"Error validating submission: {str(e)}",
                    }
                ],
            }

    @staticmethod
    def get_section_assessment_status(section_id: str) -> str:
        """
        Calculate overall assessment status for a section based on its CLO states.

        This mirrors the frontend JavaScript logic in templates/assessments.html
        and follows a strict precedence order to determine the section's status.

        Precedence (highest to lowest priority):
        1. NEEDS_REWORK - if ANY CLO is in approval_pending status
        2. NCI - if ALL CLOs are never_coming_in
        3. APPROVED - if ALL CLOs are approved
        4. SUBMITTED - if ALL CLOs are awaiting_approval
        5. IN_PROGRESS - if at least one CLO has assessment data OR is in_progress status
        6. NOT_STARTED - if all CLOs are unassigned/assigned with NO data
        7. UNKNOWN - fallback for edge cases

        Args:
            section_id: The ID of the course section

        Returns:
            str: One of the SectionAssessmentStatus constants
        """
        from src.utils.constants import SectionAssessmentStatus

        try:
            outcomes = db.get_section_outcomes_by_section(section_id)

            if not outcomes or len(outcomes) == 0:
                return SectionAssessmentStatus.NOT_STARTED

            statuses = [o.get("status", "assigned") for o in outcomes]

            # 1. NEEDS_REWORK - highest priority (any CLO needs rework)
            if any(s == "approval_pending" for s in statuses):
                return SectionAssessmentStatus.NEEDS_REWORK

            # 2. NCI - all CLOs marked as never coming in
            if all(s == "never_coming_in" for s in statuses):
                return SectionAssessmentStatus.NCI

            # 3. APPROVED - all CLOs approved
            if all(s == "approved" for s in statuses):
                return SectionAssessmentStatus.APPROVED

            # 4. SUBMITTED - all CLOs awaiting approval
            if all(s == "awaiting_approval" for s in statuses):
                return SectionAssessmentStatus.SUBMITTED

            # 5. IN_PROGRESS - check both explicit status AND populated data
            # A CLO is "in progress" if it has a status of 'in_progress' OR
            # if it has assessment data populated (students_took, students_passed, assessment_tool)
            def has_assessment_data(outcome: Dict[str, Any]) -> bool:
                return bool(
                    outcome.get("students_took") is not None
                    or outcome.get("students_passed") is not None
                    or (
                        outcome.get("assessment_tool")
                        and len(outcome.get("assessment_tool", "").strip()) > 0
                    )
                )

            if any(
                o.get("status") == "in_progress" or has_assessment_data(o)
                for o in outcomes
            ):
                return SectionAssessmentStatus.IN_PROGRESS

            # 6. NOT_STARTED - all CLOs unassigned or assigned with no data
            if all(s in ("assigned", "unassigned") for s in statuses):
                return SectionAssessmentStatus.NOT_STARTED

            # 7. UNKNOWN - fallback for mixed/unexpected states
            return SectionAssessmentStatus.UNKNOWN

        except Exception as e:
            logger.error(f"Error calculating section assessment status: {e}")
            return SectionAssessmentStatus.UNKNOWN

    @staticmethod
    def submit_course_for_approval(
        course_id: str,
        user_id: str,
        section_id: Optional[str] = None,
        notify_admins: bool = False,
    ) -> Dict[str, Any]:
        """
        Submit all CLOs for a course for approval after validation.

        Args:
            course_id: The course ID to submit
            user_id: The ID of the submitting user (instructor)
            section_id: Optional section ID for course-level data validation

        Returns:
            Dict with 'success' bool and 'errors' list if validation fails
        """
        # First validate
        logger.info(
            f"DEBUG: Validating course submission for course {course_id}, user {user_id}"
        )
        validation = CLOWorkflowService.validate_course_submission(
            course_id, section_id, user_id
        )
        logger.info(
            f"DEBUG: Validation result: valid={validation['valid']}, errors={len(validation['errors'])}"
        )
        if not validation["valid"]:
            for error in validation["errors"]:
                logger.info(f"DEBUG: Validation error: {error}")
            return {"success": False, "errors": validation["errors"]}

        try:
            # If section_id provided, only submit outcomes for that section
            # Otherwise, submit all sections (legacy behavior)
            section_outcomes: List[Dict[str, Any]]
            if section_id:
                logger.info(
                    f"DEBUG: Submitting ONLY section {section_id} for course {course_id}"
                )
                section_outcomes = db.get_section_outcomes_by_section(section_id)
            else:
                # Get sections for this course (same logic as validation)
                if user_id:
                    # Get user info to determine role
                    from src.database.database_service import get_user_by_id

                    user = get_user_by_id(user_id)
                    if user and user.get("role") == "instructor":
                        # Instructors can only see their own sections
                        sections = db.get_sections_by_instructor(user_id)
                        # Filter to only sections for this course
                        sections = [
                            s for s in sections if s.get("course_id") == course_id
                        ]
                    else:
                        # Admins and other roles can see all sections
                        sections = db.get_sections_by_course(course_id)
                else:
                    # Fallback to all sections
                    sections = db.get_sections_by_course(course_id)

                # Get all section outcomes for this course
                section_outcomes = []
                for section in sections:
                    sect_id = section.get("section_id")
                    if sect_id:
                        outcomes = db.get_section_outcomes_by_section(sect_id)
                        section_outcomes.extend(outcomes)

            # Submit each section outcome
            submitted_count = 0
            for section_outcome in section_outcomes:
                section_outcome_id = section_outcome.get("id")
                if section_outcome.get("status") in [
                    CLOStatus.APPROVED,
                    CLOStatus.COMPLETED,
                ]:
                    continue
                if section_outcome_id and CLOWorkflowService.submit_clo_for_approval(
                    str(section_outcome_id), user_id
                ):
                    submitted_count += 1

            admin_alert_sent = False
            admin_alert_error = None
            if notify_admins and submitted_count > 0:
                admin_alert_sent, admin_alert_error = (
                    CLOWorkflowService._notify_program_admins_for_course(
                        course_id, user_id, submitted_count
                    )
                )

            return {
                "success": True,
                "submitted_count": submitted_count,
                "errors": [],
                "admin_alert_sent": admin_alert_sent,
                "admin_alert_error": admin_alert_error,
            }

        except Exception as e:
            logger.error(f"Error submitting course for approval: {e}")
            return {
                "success": False,
                "errors": [
                    {
                        "outcome_id": None,
                        "field": "system",
                        "message": f"Error submitting course: {str(e)}",
                    }
                ],
                "admin_alert_sent": False,
                "admin_alert_error": None,
            }

    @staticmethod
    def get_clos_awaiting_approval(
        institution_id: str, program_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all CLOs awaiting approval, optionally filtered by program.

        Args:
            institution_id: The institution ID to filter by
            program_id: Optional program ID to filter by

        Returns:
            List of CLO dictionaries with enriched course/instructor data
        """
        try:
            # Get outcomes by status
            outcomes = db.get_outcomes_by_status(
                institution_id=institution_id,
                status=CLOStatus.AWAITING_APPROVAL,
                program_id=program_id,
            )

            # Enrich with course and instructor details
            enriched_outcomes: List[Dict[str, Any]] = []
            for outcome in outcomes:
                details = CLOWorkflowService.get_outcome_with_details(
                    outcome["outcome_id"]
                )
                if details:
                    enriched_outcomes.append(details)

            return enriched_outcomes

        except Exception as e:
            logger.error(f"Error getting CLOs awaiting approval: {e}")
            return []

    @staticmethod
    def get_clos_by_status(
        status: Optional[str],
        institution_id: str,
        program_id: Optional[str] = None,
        term_id: Optional[str] = None,
        course_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get CLOs filtered by status.

        Now queries Section Outcomes directly, as status is tracked per section.

        Args:
            status: The CLO status to filter by, or None to get all statuses
            institution_id: The institution ID to filter by
            program_id: Optional program ID to filter by
            term_id: Optional term ID to filter by
            course_id: Optional course ID to filter by

        Returns:
            List of CLO dictionaries with enriched data
        """
        try:
            # Query Section Outcomes directly
            section_outcomes = db.get_section_outcomes_by_criteria(
                institution_id=institution_id,
                status=status,
                program_id=program_id,
                term_id=term_id,
                course_id=course_id,
            )

            results: List[Dict[str, Any]] = []
            for so in section_outcomes:
                # Enrich using already-fetched data (avoids re-querying)
                section_outcome_id = so.get("id")
                if section_outcome_id:
                    # Pass the outcome data we already fetched to avoid re-querying
                    details = CLOWorkflowService.get_outcome_with_details(
                        section_outcome_id, outcome_data=so  # Use eager-loaded data!
                    )
                    if details:
                        results.append(details)

            return results

        except Exception as e:
            logger.error(f"Error getting CLOs by status: {e}")
            return []
