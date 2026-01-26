"""
Unit tests for CLOWorkflowService.get_section_assessment_status()

Tests all 7 possible status states with proper precedence:
1. NEEDS_REWORK (highest priority)
2. NCI
3. APPROVED
4. SUBMITTED
5. IN_PROGRESS
6. NOT_STARTED
7. UNKNOWN
"""

from unittest.mock import patch

import pytest

from src.services.clo_workflow_service import CLOWorkflowService
from src.utils.constants import SectionAssessmentStatus


@pytest.fixture
def mock_db_service():
    """Mock the database service for testing."""
    with patch("src.services.clo_workflow_service.db") as mock_db:
        yield mock_db


class TestGetSectionAssessmentStatus:
    """Test suite for section assessment status calculation."""

    def test_not_started_all_assigned(self, mock_db_service):
        """NOT_STARTED: All CLOs are in assigned status."""
        section_id = "section-1"
        mock_db_service.get_section_outcomes_by_section.return_value = [
            {"id": "outcome-1", "status": "assigned"},
            {"id": "outcome-2", "status": "assigned"},
            {"id": "outcome-3", "status": "assigned"},
        ]

        status = CLOWorkflowService.get_section_assessment_status(section_id)

        assert status == SectionAssessmentStatus.NOT_STARTED
        mock_db_service.get_section_outcomes_by_section.assert_called_once_with(
            section_id
        )

    def test_in_progress_with_populated_data(self, mock_db_service):
        """IN_PROGRESS: CLOs have assessment data populated even if status is 'assigned'."""
        section_id = "section-1"
        mock_db_service.get_section_outcomes_by_section.return_value = [
            {
                "id": "outcome-1",
                "status": "assigned",
                "students_took": 25,
                "students_passed": 23,
                "assessment_tool": "Scientific Method",
            },
            {
                "id": "outcome-2",
                "status": "assigned",
                "students_took": 24,
                "students_passed": 21,
                "assessment_tool": "Cell Biology Analysis",
            },
            {
                "id": "outcome-3",
                "status": "assigned",
                "students_took": 25,
                "students_passed": 25,
                "assessment_tool": "Ecosystem Project",
            },
        ]

        status = CLOWorkflowService.get_section_assessment_status(section_id)

        assert status == SectionAssessmentStatus.IN_PROGRESS
        mock_db_service.get_section_outcomes_by_section.assert_called_once_with(
            section_id
        )

    def test_not_started_mix_assigned_unassigned(self, mock_db_service):
        """NOT_STARTED: Mix of assigned and unassigned."""
        section_id = "section-1"
        mock_db_service.get_section_outcomes_by_section.return_value = [
            {"id": "outcome-1", "status": "assigned"},
            {"id": "outcome-2", "status": "unassigned"},
            {"id": "outcome-3", "status": "assigned"},
        ]

        status = CLOWorkflowService.get_section_assessment_status(section_id)

        assert status == SectionAssessmentStatus.NOT_STARTED

    def test_not_started_no_outcomes(self, mock_db_service):
        """NOT_STARTED: Section has no outcomes."""
        section_id = "section-1"
        mock_db_service.get_section_outcomes_by_section.return_value = []

        status = CLOWorkflowService.get_section_assessment_status(section_id)

        assert status == SectionAssessmentStatus.NOT_STARTED

    def test_in_progress_one_clo(self, mock_db_service):
        """IN_PROGRESS: At least one CLO is in progress."""
        section_id = "section-1"
        mock_db_service.get_section_outcomes_by_section.return_value = [
            {"id": "outcome-1", "status": "in_progress"},
            {"id": "outcome-2", "status": "assigned"},
            {"id": "outcome-3", "status": "assigned"},
        ]

        status = CLOWorkflowService.get_section_assessment_status(section_id)

        assert status == SectionAssessmentStatus.IN_PROGRESS

    def test_in_progress_multiple_clos(self, mock_db_service):
        """IN_PROGRESS: Multiple CLOs in progress."""
        section_id = "section-1"
        mock_db_service.get_section_outcomes_by_section.return_value = [
            {"id": "outcome-1", "status": "in_progress"},
            {"id": "outcome-2", "status": "in_progress"},
            {"id": "outcome-3", "status": "assigned"},
        ]

        status = CLOWorkflowService.get_section_assessment_status(section_id)

        assert status == SectionAssessmentStatus.IN_PROGRESS

    def test_submitted_all_awaiting_approval(self, mock_db_service):
        """SUBMITTED: All CLOs awaiting approval."""
        section_id = "section-1"
        mock_db_service.get_section_outcomes_by_section.return_value = [
            {"id": "outcome-1", "status": "awaiting_approval"},
            {"id": "outcome-2", "status": "awaiting_approval"},
            {"id": "outcome-3", "status": "awaiting_approval"},
        ]

        status = CLOWorkflowService.get_section_assessment_status(section_id)

        assert status == SectionAssessmentStatus.SUBMITTED

    def test_approved_all_approved(self, mock_db_service):
        """APPROVED: All CLOs approved."""
        section_id = "section-1"
        mock_db_service.get_section_outcomes_by_section.return_value = [
            {"id": "outcome-1", "status": "approved"},
            {"id": "outcome-2", "status": "approved"},
            {"id": "outcome-3", "status": "approved"},
        ]

        status = CLOWorkflowService.get_section_assessment_status(section_id)

        assert status == SectionAssessmentStatus.APPROVED

    def test_nci_all_never_coming_in(self, mock_db_service):
        """NCI: All CLOs marked as never coming in."""
        section_id = "section-1"
        mock_db_service.get_section_outcomes_by_section.return_value = [
            {"id": "outcome-1", "status": "never_coming_in"},
            {"id": "outcome-2", "status": "never_coming_in"},
            {"id": "outcome-3", "status": "never_coming_in"},
        ]

        status = CLOWorkflowService.get_section_assessment_status(section_id)

        assert status == SectionAssessmentStatus.NCI

    def test_needs_rework_one_approval_pending(self, mock_db_service):
        """NEEDS_REWORK: One CLO in approval_pending (highest priority)."""
        section_id = "section-1"
        mock_db_service.get_section_outcomes_by_section.return_value = [
            {"id": "outcome-1", "status": "approval_pending"},
            {"id": "outcome-2", "status": "approved"},
            {"id": "outcome-3", "status": "approved"},
        ]

        status = CLOWorkflowService.get_section_assessment_status(section_id)

        assert status == SectionAssessmentStatus.NEEDS_REWORK

    def test_needs_rework_overrides_all_others(self, mock_db_service):
        """NEEDS_REWORK: Takes precedence even with mix of other statuses."""
        section_id = "section-1"
        mock_db_service.get_section_outcomes_by_section.return_value = [
            {"id": "outcome-1", "status": "approval_pending"},
            {"id": "outcome-2", "status": "awaiting_approval"},
            {"id": "outcome-3", "status": "approved"},
            {"id": "outcome-4", "status": "in_progress"},
        ]

        status = CLOWorkflowService.get_section_assessment_status(section_id)

        assert status == SectionAssessmentStatus.NEEDS_REWORK

    def test_unknown_mixed_states(self, mock_db_service):
        """UNKNOWN: Mixed states that don't match any defined pattern."""
        section_id = "section-1"
        mock_db_service.get_section_outcomes_by_section.return_value = [
            {"id": "outcome-1", "status": "approved"},
            {"id": "outcome-2", "status": "awaiting_approval"},
            {"id": "outcome-3", "status": "assigned"},
        ]

        status = CLOWorkflowService.get_section_assessment_status(section_id)

        assert status == SectionAssessmentStatus.UNKNOWN

    def test_unknown_on_exception(self, mock_db_service):
        """UNKNOWN: Returns unknown status on database error."""
        section_id = "section-1"
        mock_db_service.get_section_outcomes_by_section.side_effect = Exception(
            "Database error"
        )

        status = CLOWorkflowService.get_section_assessment_status(section_id)

        assert status == SectionAssessmentStatus.UNKNOWN

    def test_precedence_needs_rework_over_nci(self, mock_db_service):
        """Precedence: NEEDS_REWORK beats NCI."""
        section_id = "section-1"
        mock_db_service.get_section_outcomes_by_section.return_value = [
            {"id": "outcome-1", "status": "approval_pending"},
            {"id": "outcome-2", "status": "never_coming_in"},
            {"id": "outcome-3", "status": "never_coming_in"},
        ]

        status = CLOWorkflowService.get_section_assessment_status(section_id)

        assert status == SectionAssessmentStatus.NEEDS_REWORK

    def test_precedence_nci_over_approved(self, mock_db_service):
        """Precedence: NCI beats APPROVED (all must be one or the other)."""
        section_id = "section-1"
        # This would be UNKNOWN in practice since it's a mix
        mock_db_service.get_section_outcomes_by_section.return_value = [
            {"id": "outcome-1", "status": "never_coming_in"},
            {"id": "outcome-2", "status": "approved"},
        ]

        status = CLOWorkflowService.get_section_assessment_status(section_id)

        # Mixed states = UNKNOWN
        assert status == SectionAssessmentStatus.UNKNOWN

    def test_default_status_when_none_provided(self, mock_db_service):
        """Defaults to 'assigned' when status is None."""
        section_id = "section-1"
        mock_db_service.get_section_outcomes_by_section.return_value = [
            {"id": "outcome-1"},  # No status field
            {"id": "outcome-2", "status": "assigned"},
        ]

        status = CLOWorkflowService.get_section_assessment_status(section_id)

        assert status == SectionAssessmentStatus.NOT_STARTED
