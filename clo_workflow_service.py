"""
CLO Workflow Service

Manages the submission, review, and approval workflow for Course Learning Outcomes (CLOs).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from constants import CLOApprovalStatus, CLOStatus
from database_service import db
from email_service import EmailService
from logging_config import get_logger

logger = get_logger(__name__)


class CLOWorkflowService:
    """Service for managing CLO submission and approval workflows."""

    @staticmethod
    def submit_clo_for_approval(outcome_id: str, user_id: str) -> bool:
        """
        Submit a CLO for approval review.

        Args:
            outcome_id: The ID of the course outcome to submit
            user_id: The ID of the user submitting (instructor)

        Returns:
            bool: True if submission successful, False otherwise
        """
        try:
            outcome = db.get_course_outcome(outcome_id)
            if not outcome:
                logger.error(f"CLO not found: {logger.sanitize(outcome_id)}")
                return False

            # Update status and submission metadata
            update_data = {
                "status": CLOStatus.AWAITING_APPROVAL,
                "submitted_at": datetime.now(timezone.utc),
                "submitted_by_user_id": user_id,
                "approval_status": CLOApprovalStatus.PENDING,
            }

            success = db.update_course_outcome(outcome_id, update_data)
            if success:
                logger.info(
                    f"CLO {logger.sanitize(outcome_id)} submitted for approval by user {logger.sanitize(user_id)}"
                )
            else:
                logger.error(
                    f"Failed to update CLO {logger.sanitize(outcome_id)} status"
                )

            return success

        except Exception as e:
            logger.error(f"Error submitting CLO for approval: {e}")
            return False

    @staticmethod
    def approve_clo(outcome_id: str, reviewer_id: str) -> bool:
        """
        Approve a CLO that has been submitted for review.

        Args:
            outcome_id: The ID of the course outcome to approve
            reviewer_id: The ID of the reviewing admin

        Returns:
            bool: True if approval successful, False otherwise
        """
        try:
            outcome = db.get_course_outcome(outcome_id)
            if not outcome:
                logger.error(f"CLO not found: {outcome_id}")
                return False

            # Verify CLO is in a state that can be approved
            if outcome.get("status") not in [
                CLOStatus.AWAITING_APPROVAL,
                CLOStatus.APPROVAL_PENDING,
            ]:
                logger.warning(
                    f"CLO {outcome_id} is in {outcome.get('status')} state, "
                    f"cannot approve"
                )
                return False

            # Update status and review metadata
            # Note: Preserve feedback_comments and feedback_provided_at for audit trail
            update_data = {
                "status": CLOStatus.APPROVED,
                "approval_status": CLOApprovalStatus.APPROVED,
                "reviewed_at": datetime.now(timezone.utc),
                "reviewed_by_user_id": reviewer_id,
            }

            success = db.update_course_outcome(outcome_id, update_data)
            if success:
                logger.info(f"CLO {outcome_id} approved by reviewer {reviewer_id}")
            else:
                logger.error(f"Failed to approve CLO {outcome_id}")

            return success

        except Exception as e:
            logger.error(f"Error approving CLO: {e}")
            return False

    @staticmethod
    def request_rework(
        outcome_id: str, reviewer_id: str, comments: str, send_email: bool = False
    ) -> bool:
        """
        Request rework on a submitted CLO with feedback comments.

        Args:
            outcome_id: The ID of the course outcome needing rework
            reviewer_id: The ID of the reviewing admin
            comments: Feedback comments explaining what needs to be fixed
            send_email: Whether to send email notification to the instructor

        Returns:
            bool: True if rework request successful, False otherwise
        """
        try:
            outcome = db.get_course_outcome(outcome_id)
            if not outcome:
                logger.error(f"CLO not found: {outcome_id}")
                return False

            # Verify CLO is in a state that can be sent back for rework
            if outcome.get("status") not in [
                CLOStatus.AWAITING_APPROVAL,
                CLOStatus.APPROVAL_PENDING,
            ]:
                logger.warning(
                    f"CLO {outcome_id} is in {outcome.get('status')} state, "
                    f"cannot request rework"
                )
                return False

            # Update status and feedback
            update_data = {
                "status": CLOStatus.APPROVAL_PENDING,
                "approval_status": CLOApprovalStatus.NEEDS_REWORK,
                "reviewed_at": datetime.now(timezone.utc),
                "reviewed_by_user_id": reviewer_id,
                "feedback_comments": comments,
                "feedback_provided_at": datetime.now(timezone.utc),
            }

            success = db.update_course_outcome(outcome_id, update_data)
            if not success:
                logger.error(f"Failed to request rework for CLO {outcome_id}")
                return False

            logger.info(
                f"CLO {outcome_id} sent back for rework by reviewer {reviewer_id}"
            )

            # Send email notification if requested
            if send_email:
                CLOWorkflowService._send_rework_notification(outcome_id, comments)

            return True

        except Exception as e:
            logger.error(f"Error requesting rework for CLO: {e}")
            return False

    @staticmethod
    def mark_as_nci(outcome_id: str, reviewer_id: str, reason: str = None) -> bool:
        """
        Mark a CLO as "Never Coming In" (NCI) - added from CEI demo feedback.

        Use cases:
        - Instructor left institution
        - Instructor non-responsive despite multiple reminders
        - Course cancelled/dropped after initial assignment

        Args:
            outcome_id: The ID of the course outcome to mark as NCI
            reviewer_id: The ID of the admin marking as NCI
            reason: Optional reason/note for NCI designation

        Returns:
            bool: True if successfully marked as NCI, False otherwise
        """
        try:
            outcome = db.get_course_outcome(outcome_id)
            if not outcome:
                logger.error(f"CLO not found: {outcome_id}")
                return False

            # Update status to NCI
            update_data = {
                "status": CLOStatus.NEVER_COMING_IN,
                "approval_status": CLOApprovalStatus.NEVER_COMING_IN,
                "reviewed_at": datetime.now(timezone.utc),
                "reviewed_by_user_id": reviewer_id,
                "feedback_comments": reason or "Marked as Never Coming In (NCI)",
                "feedback_provided_at": datetime.now(timezone.utc),
            }

            success = db.update_course_outcome(outcome_id, update_data)
            if not success:
                logger.error(f"Failed to mark CLO {outcome_id} as NCI")
                return False

            logger.info(
                f"CLO {outcome_id} marked as NCI by reviewer {reviewer_id}"
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

            # Compose email using templates
            from flask import render_template

            subject = f"Feedback on CLO {clo_number} for {course_number}"

            template_context = {
                "clo_number": clo_number,
                "course_number": course_number,
                "feedback": feedback,
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
    def auto_mark_in_progress(outcome_id: str, user_id: str) -> bool:
        """
        Automatically mark a CLO as in_progress when an instructor starts editing.

        Args:
            outcome_id: The ID of the course outcome
            user_id: The ID of the user editing

        Returns:
            bool: True if status updated, False otherwise
        """
        try:
            outcome = db.get_course_outcome(outcome_id)
            if not outcome:
                logger.error(f"CLO not found: {outcome_id}")
                return False

            current_status = outcome.get("status")

            # Only auto-mark if currently assigned or approval_pending
            if current_status not in [CLOStatus.ASSIGNED, CLOStatus.APPROVAL_PENDING]:
                # Already in progress or submitted, don't change status
                return True

            update_data = {"status": CLOStatus.IN_PROGRESS}
            success = db.update_course_outcome(outcome_id, update_data)

            if success:
                logger.info(f"CLO {outcome_id} automatically marked as in_progress")

            return success

        except Exception as e:
            logger.error(f"Error auto-marking CLO in progress: {e}")
            return False

    @staticmethod
    def validate_course_submission(
        course_id: str, section_id: str = None
    ) -> Dict[str, Any]:
        """
        Validate all CLOs and course-level data are complete before submission.

        Args:
            course_id: The course ID to validate
            section_id: Optional section ID to validate course-level data

        Returns:
            Dict with 'valid' bool and 'errors' list of error details
        """
        try:
            outcomes = db.get_course_outcomes(course_id)

            if not outcomes:
                return {
                    "valid": False,
                    "errors": [
                        {
                            "outcome_id": None,
                            "field": "course",
                            "message": "No CLOs found for this course",
                        }
                    ],
                }

            errors = []

            # Validate each CLO
            for outcome in outcomes:
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

            # Validate course-level section data if section provided
            if section_id:
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
    def submit_course_for_approval(
        course_id: str, user_id: str, section_id: str = None
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
        validation = CLOWorkflowService.validate_course_submission(
            course_id, section_id
        )
        if not validation["valid"]:
            return {"success": False, "errors": validation["errors"]}

        try:
            # Get all CLOs for this course
            outcomes = db.get_course_outcomes(course_id)

            # Submit each CLO
            submitted_count = 0
            for outcome in outcomes:
                outcome_id = outcome.get("outcome_id") or outcome.get("id")
                if CLOWorkflowService.submit_clo_for_approval(outcome_id, user_id):
                    submitted_count += 1

            return {
                "success": True,
                "submitted_count": submitted_count,
                "errors": [],
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
    ) -> List[Dict[str, Any]]:
        """
        Get CLOs filtered by status.

        Args:
            status: The CLO status to filter by, or None to get all statuses
            institution_id: The institution ID to filter by
            program_id: Optional program ID to filter by
            term_id: Optional term ID to filter by

        Returns:
            List of CLO dictionaries with enriched data
        """
        try:
            outcomes = db.get_outcomes_by_status(
                institution_id=institution_id,
                status=status,
                program_id=program_id,
                term_id=term_id,
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
            logger.error(f"Error getting CLOs by status: {e}")
            return []

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
    def get_outcome_with_details(outcome_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a course outcome with enriched course and instructor details.

        Args:
            outcome_id: The ID of the course outcome

        Returns:
            Dictionary with outcome data plus course_number, course_title,
            instructor_name, instructor_email, etc.
        """
        try:
            outcome = db.get_course_outcome(outcome_id)
            if not outcome:
                return None

            # Get related course
            course_id = outcome.get("course_id")
            course = db.get_course(course_id) if course_id else None

            # Get instructor from CLO submission (multi-section aware)
            instructor = None
            instructor_name = None
            instructor_email = None
            program_name = None
            if course:
                instructor = CLOWorkflowService._get_instructor_from_outcome(outcome)
                if instructor:
                    instructor_name = CLOWorkflowService._build_instructor_name(
                        instructor
                    )
                    instructor_email = instructor.get("email")

                # Get program name from course's programs
                programs = db.get_programs_for_course(course_id)
                if programs:
                    program_name = programs[0].get("name") or programs[0].get(
                        "program_name"
                    )

            # Build enriched result
            result = {
                **outcome,
                "course_number": course.get("course_number") if course else None,
                "course_title": course.get("course_title") if course else None,
                "instructor_name": instructor_name,
                "instructor_email": instructor_email,
                "program_name": program_name,
            }

            return result

        except Exception as e:
            logger.error(f"Error getting outcome with details: {e}")
            return None
