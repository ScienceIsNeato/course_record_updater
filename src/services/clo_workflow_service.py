"""
CLO Workflow Service

Manages the submission, review, and approval workflow for Course Learning Outcomes (CLOs).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.database.database_service import db
from src.utils.constants import CLOApprovalStatus, CLOStatus
from src.utils.logging_config import get_logger
from src.utils.time_utils import get_current_time

from .email_service import EmailService

logger = get_logger(__name__)


class CLOWorkflowService:
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
                    f"Section outcome not found: {logger.sanitize(section_outcome_id)}"
                )
                return False
            if outcome.get("status") in [CLOStatus.APPROVED, CLOStatus.COMPLETED]:
                logger.info(
                    "Skipping submission for approved CLO %s",
                    logger.sanitize(section_outcome_id),
                )
                return False

            # Update status and submission metadata
            update_data = {
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
                logger.error(f"Section outcome not found: {section_outcome_id}")
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
            update_data = {
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
    ) -> dict:
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
                logger.error(f"Section outcome not found: {section_outcome_id}")
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
            update_data = {
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
                logger.error(f"Section outcome not found: {section_outcome_id}")
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
                logger.error(f"Section outcome not found: {section_outcome_id}")
                return False

            # Update status to NCI
            update_data = {
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

            instructor_email = outcome_details.get("instructor_email")
            if not instructor_email:
                logger.error(f"No instructor email found for outcome {outcome_id}")
                return False

            course_number = outcome_details.get("course_number", "Unknown Course")
            clo_number = outcome_details.get("clo_number", "Unknown CLO")
            instructor_name = outcome_details.get("instructor_name", "Instructor")

            # Compose email using templates
            from urllib.parse import urljoin

            from flask import current_app, render_template

            subject = f"Feedback on CLO {clo_number} for {course_number}"

            # Build assessment URL
            base_url = current_app.config.get("BASE_URL", "http://localhost:3001")
            course_id = outcome_details.get("course_id")
            assessment_url = urljoin(base_url, f"/assessments?course={course_id}")

            template_context = {
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
                logger.error(f"Section outcome not found: {section_outcome_id}")
                return False

            current_status = outcome.get("status")

            # Only auto-mark if currently assigned or approval_pending
            if current_status not in [CLOStatus.ASSIGNED, CLOStatus.AWAITING_APPROVAL]:
                # Already in progress or submitted, don't change status
                return True

            update_data = {"status": CLOStatus.IN_PROGRESS}
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
        errors = []
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
        errors = []
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

            errors = []

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
            enriched_outcomes = []
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
                # Enrich each section outcome with template data
                section_outcome_id = so.get("id")
                if section_outcome_id:
                    details = CLOWorkflowService.get_outcome_with_details(
                        section_outcome_id
                    )
                    if details:
                        results.append(details)

            return results

        except Exception as e:
            logger.error(f"Error getting CLOs by status: {e}")
            return []

    @staticmethod
    def _expand_outcome_for_sections(outcome: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Expand a course outcome into one entry per section (fallback to course-level row)."""
        course_outcome_id = CLOWorkflowService._resolve_outcome_id(outcome)
        if not course_outcome_id:
            return []

        course_id = outcome.get("course_id")
        sections = db.get_sections_by_course(course_id) if course_id else []
        results: List[Dict[str, Any]] = []

        if sections:
            for section in sections:
                # Handle both "section_id" (from to_dict) and "id" (legacy/mock format)
                section_id = section.get("section_id") or section.get("id")
                if not section_id:
                    continue
                # Get the SECTION-SPECIFIC outcome for this course outcome + section
                section_outcome = db.get_section_outcome_by_course_outcome_and_section(
                    course_outcome_id, str(section_id)
                )

                if section_outcome:
                    # Use the SECTION outcome ID, not the course outcome ID
                    section_outcome_id = section_outcome.get("id")
                    if not section_outcome_id:
                        continue
                    # Merge essential fields from course_outcome since section_outcome
                    # only has section-specific data (it links via outcome_id)
                    # Fields like course_id, clo_number, description are on course_outcome
                    enriched_section_outcome = {
                        **section_outcome,
                        "course_id": course_id,
                        "clo_number": outcome.get("clo_number"),
                        "description": outcome.get("description"),
                        "assessment_method": outcome.get("assessment_method"),
                    }
                    details = CLOWorkflowService.get_outcome_with_details(
                        str(section_outcome_id),
                        section_data=section,
                        outcome_data=enriched_section_outcome,
                    )
                    if details:
                        results.append(details)
        else:
            # Fallback to course-level outcome if no sections
            details = CLOWorkflowService.get_outcome_with_details(
                course_outcome_id, outcome_data=outcome
            )
            if details:
                results.append(details)

        return results

    @staticmethod
    def _resolve_outcome_id(outcome: Dict[str, Any]) -> Optional[str]:
        """Return the normalized outcome ID from a dict (handles outcome_id/id)."""
        raw_id = outcome.get("outcome_id") or outcome.get("id")
        return str(raw_id) if raw_id else None

    @staticmethod
    def _get_instructor_from_outcome(
        outcome: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Get instructor details from the user who submitted the CLO.

        For multi-section courses, use the submitted_by_user_id to identify
        the correct instructor rather than picking arbitrarily from sections.
        """
        # Unassigned CLOs don't have a responsible instructor yet
        if outcome.get("status") == "unassigned":
            return None

        instructor_id = outcome.get("submitted_by_user_id")
        if instructor_id:
            return db.get_user(instructor_id)

        # Fallback: if not submitted yet, try to get instructor from first section
        # This is a best-effort attempt for assigned but unsubmitted CLOs
        course_id = outcome.get("course_id")
        if not course_id:
            return None

        sections = db.get_sections_by_course(course_id)
        if not sections:
            return None

        section = sections[0]
        instructor_id = section.get("instructor_id")
        if not instructor_id:
            return None

        return db.get_user(instructor_id)

    @staticmethod
    def _build_instructor_name(instructor: Dict[str, Any]) -> Optional[str]:
        """Build instructor full name from user data."""
        instructor_name = instructor.get("display_name")
        if instructor_name:
            return instructor_name

        first = instructor.get("first_name", "")
        last = instructor.get("last_name", "")
        return f"{first} {last}".strip() or None

    @staticmethod
    def _get_term_name_for_instructor(
        instructor_id: str, course_id: str, outcome_id: str
    ) -> Optional[str]:
        """Get term name from instructor's section for a course."""
        try:
            sections = db.get_sections_by_instructor(instructor_id)
            relevant_sections = [s for s in sections if s.get("course_id") == course_id]
            if relevant_sections:
                term_id = relevant_sections[0].get("term_id")
                if term_id:
                    term = db.get_term_by_id(term_id)
                    if term:
                        return term.get("name")
        except Exception as e:
            logger.warning(f"Failed to resolve term for outcome {outcome_id}: {e}")
        return None

    @staticmethod
    def _get_program_name_for_course(course_id: str) -> Optional[str]:
        """Get program name from course's programs."""
        programs = db.get_programs_for_course(course_id)
        if programs:
            return programs[0].get("name") or programs[0].get("program_name")
        return None

    @staticmethod
    def _enrich_outcome_with_instructor_details(
        outcome: Dict[str, Any],
        course_id: str,
        outcome_id: str,
        section_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[
        Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]
    ]:
        """Get instructor name, email, term name, instructor ID, and section ID."""
        if section_data:
            return CLOWorkflowService._resolve_section_context(section_data)

        outcome_section_id = outcome.get("section_id")
        if outcome_section_id:
            resolved = CLOWorkflowService._resolve_from_section_id(
                outcome, outcome_section_id
            )
            if resolved:
                return resolved

        return CLOWorkflowService._resolve_from_course_fallback(
            outcome, course_id, outcome_id
        )

    @staticmethod
    def _resolve_from_section_id(
        outcome: Dict[str, Any], outcome_section_id: str
    ) -> Optional[
        tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]
    ]:
        """Attempt to resolve instructor details from a section ID associated with the outcome."""
        section = db.get_section_by_id(outcome_section_id)
        if not section:
            return None

        (
            instructor_name,
            instructor_email,
            term_name,
            instructor_id,
            section_id,
        ) = CLOWorkflowService._resolve_section_context(section)

        if not instructor_name:
            instructor = CLOWorkflowService._get_instructor_from_outcome(outcome)
            if instructor:
                instructor_name = CLOWorkflowService._build_instructor_name(instructor)
                instructor_email = instructor.get("email")
                instructor_id = instructor.get("user_id") or instructor.get("id")

        return (
            instructor_name,
            instructor_email,
            term_name,
            instructor_id,
            section_id or str(outcome_section_id),
        )

    @staticmethod
    def _resolve_from_course_fallback(
        outcome: Dict[str, Any], course_id: str, outcome_id: str
    ) -> tuple[
        Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]
    ]:
        """Fallback resolution based on course and responsible instructor."""
        instructor = CLOWorkflowService._get_instructor_from_outcome(outcome)
        section_id = None

        try:
            sections = db.get_sections_by_course(course_id)
            if sections:
                if instructor:
                    inst_id = instructor.get("user_id") or instructor.get("id")
                    relevant = [
                        s for s in sections if s.get("instructor_id") == inst_id
                    ]
                    if relevant:
                        section_id = relevant[0].get("section_id") or relevant[0].get(
                            "id"
                        )

                if not section_id:
                    section_id = sections[0].get("section_id") or sections[0].get("id")
        except Exception:
            pass

        if not instructor:
            return None, None, None, None, section_id

        instructor_name = CLOWorkflowService._build_instructor_name(instructor)
        instructor_email = instructor.get("email")
        instructor_id = instructor.get("user_id") or instructor.get("id")
        term_name = (
            CLOWorkflowService._get_term_name_for_instructor(
                instructor_id, course_id, outcome_id
            )
            if instructor_id
            else None
        )

        return instructor_name, instructor_email, term_name, instructor_id, section_id

    @staticmethod
    def _resolve_section_context(
        section_data: Dict[str, Any],
    ) -> tuple[
        Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]
    ]:
        """Resolve instructor and term details for an explicit section."""
        instructor_id = section_data.get("instructor_id")
        instructor = db.get_user(instructor_id) if instructor_id else None
        instructor_name = (
            CLOWorkflowService._build_instructor_name(instructor)
            if instructor
            else None
        )
        instructor_email = instructor.get("email") if instructor else None

        term_name = None
        offering_id = section_data.get("offering_id")
        if offering_id:
            offering = db.get_course_offering(offering_id)
            if offering:
                term_id = offering.get("term_id")
                if term_id:
                    term = db.get_term_by_id(term_id)
                    if term:
                        term_name = term.get("term_name") or term.get("name")

        section_id = section_data.get("section_id") or section_data.get("id")
        return instructor_name, instructor_email, term_name, instructor_id, section_id

    @staticmethod
    def get_outcome_with_details(
        outcome_id: str,
        section_data: Optional[Dict[str, Any]] = None,
        outcome_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a section outcome with enriched course and instructor details.

        Args:
            outcome_id: The ID of the section outcome
            section_data: Optional section metadata to scope the instructor/term context
            outcome_data: Optional pre-fetched outcome dict (avoids extra query)

        Returns:
            Dictionary with outcome data plus course_number, course_title,
            instructor_name, instructor_email, etc.
        """
        try:
            outcome = outcome_data or db.get_section_outcome(outcome_id)
            if not outcome:
                return None

            # Enrich outcome with template data if needed
            enriched_outcome = CLOWorkflowService._enrich_outcome_with_template(outcome)

            # Get course information
            course = CLOWorkflowService._get_course_for_outcome(enriched_outcome)

            # Get instructor and term details
            instructor_details = CLOWorkflowService._get_instructor_details_for_outcome(
                enriched_outcome, course, outcome_id, section_data
            )

            # Get program information
            program_name = CLOWorkflowService._get_program_name_for_outcome(course)

            # Build final details
            final_details = CLOWorkflowService._build_final_outcome_details(
                enriched_outcome, course, instructor_details, program_name, section_data
            )

            # Add history
            CLOWorkflowService._add_outcome_history(final_details)

            return final_details

        except Exception as e:
            logger.error(f"Error getting outcome with details: {e}")
            return None

    @staticmethod
    def _enrich_outcome_with_template(outcome: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich outcome with template data if it's a raw section outcome."""
        raw_course_id = outcome.get("course_id")
        if not raw_course_id and outcome.get("outcome_id"):
            # Fetch the template (CourseOutcome)
            template = db.get_course_outcome(outcome["outcome_id"])
            if template:
                # Merge template data (defaults) into outcome
                # We preserve outcome's own values (status, etc) if they exist
                enriched_outcome = {
                    **template,  # Base: Template fields (clo_number, description, course_id)
                    **outcome,  # Override: Section outcome fields (status, specific assessment)
                    "id": outcome["id"],  # Ensure we keep the section outcome ID
                }
                return enriched_outcome
        return outcome

    @staticmethod
    def _get_course_for_outcome(outcome: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get course information for the outcome."""
        raw_course_id = outcome.get("course_id")
        course_id = raw_course_id if isinstance(raw_course_id, str) else None
        return db.get_course_by_id(course_id) if course_id else None

    @staticmethod
    def _get_instructor_details_for_outcome(
        outcome: Dict[str, Any],
        course: Optional[Dict[str, Any]],
        outcome_id: str,
        section_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Get instructor and term details for the outcome."""
        if not course:
            return {
                "instructor_name": None,
                "instructor_email": None,
                "instructor_id": None,
                "term_name": None,
                "section_id": outcome.get("section_id"),
            }

        course_id = (
            course.get("id")
            if isinstance(course, dict) and course.get("id")
            else course
        )
        (
            instructor_name,
            instructor_email,
            term_name,
            instructor_id,
            resolved_section_id,
        ) = CLOWorkflowService._enrich_outcome_with_instructor_details(
            outcome,
            course_id if isinstance(course_id, str) else "",
            outcome_id,
            section_data=section_data,
        )

        return {
            "instructor_name": instructor_name,
            "instructor_email": instructor_email,
            "instructor_id": instructor_id,
            "term_name": term_name,
            "section_id": resolved_section_id or outcome.get("section_id"),
        }

    @staticmethod
    def _get_program_name_for_outcome(
        course: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """Get program name for the course."""
        if not course:
            return None
        course_id = (
            course.get("id")
            if isinstance(course, dict) and course.get("id")
            else course
        )
        if not course_id or not isinstance(course_id, str):
            return None
        return CLOWorkflowService._get_program_name_for_course(course_id)

    @staticmethod
    def _build_final_outcome_details(
        enriched_outcome: Dict[str, Any],
        course: Optional[Dict[str, Any]],
        instructor_details: Dict[str, Any],
        program_name: Optional[str],
        section_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build the final outcome details dictionary."""
        final_details = enriched_outcome.copy()

        section_id = instructor_details.get("section_id")
        section_number = section_data.get("section_number") if section_data else None
        section_status = section_data.get("status") if section_data else None

        if section_id:
            section = db.get_section_by_id(section_id)
            if section:
                section_number = section_number or section.get("section_number")

        final_details.update(
            {
                "course_number": (course.get("course_number") if course else None),
                "course_title": course.get("course_title") if course else None,
                "instructor_name": instructor_details.get("instructor_name"),
                "instructor_email": instructor_details.get("instructor_email"),
                "instructor_id": instructor_details.get("instructor_id"),
                "section_id": section_id,
                "section_number": section_number,
                "section_status": section_status,
                "program_name": program_name,
                "term_name": instructor_details.get("term_name"),
            }
        )

        return final_details

    @staticmethod
    def _add_outcome_history(final_details: Dict[str, Any]) -> None:
        """Add unified history for the section outcome."""
        outcome_id_for_history = final_details.get("id")
        if outcome_id_for_history:
            history = db.get_outcome_history(outcome_id_for_history)
            final_details["history"] = history
        else:
            final_details["history"] = []

    @staticmethod
    def _notify_program_admins(section_outcome_id: str, user_id: str) -> None:
        """Send email alert to program admins about new submission."""
        try:
            from src.services.email_service import EmailService

            outcome = db.get_section_outcome(section_outcome_id)
            if not outcome:
                logger.warning(
                    f"Outcome not found for notification: {section_outcome_id}"
                )
                return

            course = db.get_course_by_id(outcome["course_id"])
            if not course:
                logger.warning(
                    f"Course not found for notification: {outcome['course_id']}"
                )
                return

            instructor = db.get_user_by_id(user_id)
            if not instructor:
                logger.warning(f"Instructor not found for notification: {user_id}")
                return

            # Get program_id (courses have program_ids array, use first one)
            program_ids = course.get("program_ids") or []
            program_id = program_ids[0] if program_ids else course.get("program_id")
            if not program_id:
                logger.warning(f"No program ID for course {course['id']}")
                return

            admins = db.get_program_admins(program_id)
            if not admins:
                logger.info(f"No program admins found for program {program_id}")
                return

            # Send email to each admin
            instructor_name = f"{instructor['first_name']} {instructor['last_name']}"

            # Fetch section data to get section_number (outcome doesn't have this field)
            section_id = outcome.get("section_id")
            section_number = "Unknown"
            if section_id:
                section_data = db.get_section_by_id(section_id)
                if section_data:
                    section_number = section_data.get("section_number", "Unknown")

            course_code = f"{course['course_number']}-{section_number}"

            for admin in admins:
                try:
                    EmailService.send_admin_submission_alert(
                        to_email=admin["email"],
                        admin_name=admin.get("first_name", "Admin"),
                        instructor_name=instructor_name,
                        course_code=course_code,
                        clo_count=1,
                    )
                except Exception as e:
                    logger.error(f"Failed to send email to {admin['email']}: {e}")

            logger.info(f"Sent admin alerts to {len(admins)} program admins")

        except Exception as e:
            logger.error(f"Failed to notify admins: {e}")
            # Don't fail submission if email fails

    @staticmethod
    def _notify_program_admins_for_course(
        course_id: str, user_id: str, clo_count: int
    ) -> tuple[bool, Optional[str]]:
        """
        Send aggregated notification to program admins after course submission.
        Returns (success, error_message)
        """
        try:
            course = db.get_course_by_id(course_id)
            if not course:
                error_msg = f"Course not found: {course_id}"
                logger.warning(error_msg)
                return False, error_msg

            instructor = db.get_user_by_id(user_id)
            if not instructor:
                error_msg = f"Instructor not found: {user_id}"
                logger.warning(error_msg)
                return False, error_msg

            # Get program_id (courses have program_ids array, use first one)
            program_ids = course.get("program_ids") or []
            program_id = program_ids[0] if program_ids else course.get("program_id")
            if not program_id:
                error_msg = f"No program ID for course {course_id}"
                logger.warning(error_msg)
                return False, error_msg

            admins = db.get_program_admins(program_id)

            # Fall back to institution admins if no program admins
            if not admins:
                logger.info(
                    f"No program admins for program {program_id}, falling back to institution admins"
                )
                institution_id = course.get("institution_id")
                if institution_id:
                    all_users = db.get_all_users(institution_id)
                    admins = [
                        u for u in all_users if u.get("role") == "institution_admin"
                    ]

            if not admins:
                error_msg = f"No program or institution admins found for notifications"
                logger.info(error_msg)
                return False, error_msg

            instructor_name = f"{instructor.get('first_name', '')} {instructor.get('last_name', '')}".strip()
            if not instructor_name:
                instructor_name = instructor.get("email", "Instructor")

            course_code = course.get("course_number") or course_id

            for admin in admins:
                try:
                    EmailService.send_admin_submission_alert(
                        to_email=admin["email"],
                        admin_name=admin.get("first_name", "Admin"),
                        instructor_name=instructor_name,
                        course_code=course_code,
                        clo_count=clo_count,
                    )
                except Exception as e:
                    logger.error(f"Failed to send email to {admin['email']}: {e}")

            logger.info(f"Sent admin submission alerts to {len(admins)} program admins")
            return True, None
        except Exception as e:
            error_msg = f"Failed to notify admins: {e}"
            logger.error(error_msg)
            return False, str(e)
