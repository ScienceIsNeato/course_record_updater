"""
Unit tests for course submission validation.

Tests the validation logic for submitting an entire course section at once,
including all CLOs and course-level data.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.services.clo_workflow_service import CLOWorkflowService


class TestValidateCourseSubmission:
    """Test course-level submission validation."""

    @patch("src.services.clo_workflow_service.db")
    def test_validate_all_clos_complete_success(self, mock_db):
        """Test validation passes when all CLOs have required fields."""
        course_id = "course-123"

        # All CLOs have students_took, students_passed, assessment_tool
        mock_db.get_course_outcomes.return_value = [
            {
                "outcome_id": "clo-1",
                "students_took": 28,
                "students_passed": 23,
                "assessment_tool": "Lab 2",
            },
            {
                "outcome_id": "clo-2",
                "students_took": 28,
                "students_passed": 25,
                "assessment_tool": "Test #3",
            },
        ]

        result = CLOWorkflowService.validate_course_submission(course_id)

        assert result["valid"] is True
        assert result["errors"] == []

    @patch("src.services.clo_workflow_service.db")
    def test_validate_missing_students_took(self, mock_db):
        """Test validation fails when students_took is missing."""
        course_id = "course-123"

        mock_db.get_course_outcomes.return_value = [
            {
                "outcome_id": "clo-1",
                "clo_number": "1",
                "students_took": None,  # Missing!
                "students_passed": 23,
                "assessment_tool": "Lab 2",
            },
        ]

        result = CLOWorkflowService.validate_course_submission(course_id)

        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert "clo-1" in result["errors"][0]["outcome_id"]
        assert "students_took" in result["errors"][0]["field"]

    @patch("src.services.clo_workflow_service.db")
    def test_validate_missing_students_passed(self, mock_db):
        """Test validation fails when students_passed is missing."""
        course_id = "course-123"

        mock_db.get_course_outcomes.return_value = [
            {
                "outcome_id": "clo-1",
                "clo_number": "1",
                "students_took": 28,
                "students_passed": None,  # Missing!
                "assessment_tool": "Lab 2",
            },
        ]

        result = CLOWorkflowService.validate_course_submission(course_id)

        assert result["valid"] is False
        assert any("students_passed" in e["field"] for e in result["errors"])

    @patch("src.services.clo_workflow_service.db")
    def test_validate_missing_assessment_tool(self, mock_db):
        """Test validation fails when assessment_tool is missing."""
        course_id = "course-123"

        mock_db.get_course_outcomes.return_value = [
            {
                "outcome_id": "clo-1",
                "clo_number": "1",
                "students_took": 28,
                "students_passed": 23,
                "assessment_tool": "",  # Empty string = missing
            },
        ]

        result = CLOWorkflowService.validate_course_submission(course_id)

        assert result["valid"] is False
        assert any("assessment_tool" in e["field"] for e in result["errors"])

    @patch("src.services.clo_workflow_service.db")
    def test_validate_students_passed_exceeds_took(self, mock_db):
        """Test validation fails when students_passed > students_took."""
        course_id = "course-123"

        mock_db.get_course_outcomes.return_value = [
            {
                "outcome_id": "clo-1",
                "clo_number": "1",
                "students_took": 20,
                "students_passed": 25,  # More than took!
                "assessment_tool": "Lab 2",
            },
        ]

        result = CLOWorkflowService.validate_course_submission(course_id)

        assert result["valid"] is False
        assert any("exceed" in e["message"].lower() for e in result["errors"])

    @patch("src.services.clo_workflow_service.db")
    def test_validate_multiple_clo_errors(self, mock_db):
        """Test validation returns errors for multiple incomplete CLOs."""
        course_id = "course-123"

        mock_db.get_course_outcomes.return_value = [
            {
                "outcome_id": "clo-1",
                "clo_number": "1",
                "students_took": None,
                "students_passed": None,
                "assessment_tool": "",
            },
            {
                "outcome_id": "clo-2",
                "clo_number": "2",
                "students_took": 28,
                "students_passed": 25,
                "assessment_tool": "Test #3",
            },
            {
                "outcome_id": "clo-3",
                "clo_number": "3",
                "students_took": None,
                "students_passed": 10,
                "assessment_tool": "Final",
            },
        ]

        result = CLOWorkflowService.validate_course_submission(course_id)

        assert result["valid"] is False
        # clo-1 has 3 errors, clo-3 has 1 error
        assert len(result["errors"]) >= 4

    @patch("src.services.clo_workflow_service.db")
    def test_validate_empty_course(self, mock_db):
        """Test validation fails for course with no CLOs."""
        course_id = "course-123"
        mock_db.get_course_outcomes.return_value = []

        result = CLOWorkflowService.validate_course_submission(course_id)

        assert result["valid"] is False
        assert any("no clos" in e["message"].lower() for e in result["errors"])

    @patch("src.services.clo_workflow_service.db")
    def test_validate_database_error(self, mock_db):
        """Test validation handles database errors gracefully."""
        mock_db.get_course_outcomes.side_effect = Exception("Database error")

        result = CLOWorkflowService.validate_course_submission("course-123")

        assert result["valid"] is False
        assert any("error" in e["message"].lower() for e in result["errors"])


class TestSubmitCourseForApproval:
    """Test submitting entire course for approval."""

    @patch(
        "src.services.clo_workflow_service.CLOWorkflowService.validate_course_submission"
    )
    @patch(
        "src.services.clo_workflow_service.CLOWorkflowService.submit_clo_for_approval"
    )
    @patch("src.services.clo_workflow_service.db")
    def test_submit_course_success(self, mock_db, mock_submit_clo, mock_validate):
        """Test successful course submission."""
        course_id = "course-123"
        user_id = "user-456"

        mock_validate.return_value = {"valid": True, "errors": []}
        mock_db.get_course_outcomes.return_value = [
            {"outcome_id": "clo-1"},
            {"outcome_id": "clo-2"},
        ]
        mock_submit_clo.return_value = True

        result = CLOWorkflowService.submit_course_for_approval(course_id, user_id)

        assert result["success"] is True
        assert mock_submit_clo.call_count == 2

    @patch(
        "src.services.clo_workflow_service.CLOWorkflowService.validate_course_submission"
    )
    def test_submit_course_validation_fails(self, mock_validate):
        """Test course submission fails when validation fails."""
        mock_validate.return_value = {
            "valid": False,
            "errors": [
                {"outcome_id": "clo-1", "field": "students_took", "message": "Required"}
            ],
        }

        result = CLOWorkflowService.submit_course_for_approval("course-123", "user-456")

        assert result["success"] is False
        assert len(result["errors"]) == 1
