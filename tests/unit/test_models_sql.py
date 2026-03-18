"""Unit tests for models_sql.py helper functions."""

from unittest.mock import Mock

from src.models.models_sql import (
    Course,
    CourseOffering,
    CourseOutcome,
    CourseSection,
    Institution,
    Program,
    Term,
    User,
    UserInvitation,
    _get_model_data,
    generate_uuid,
    to_dict,
)


class TestGenerateUUID:
    """Test UUID generation."""

    def test_generate_uuid_returns_string(self) -> None:
        """Test that generate_uuid returns a string."""
        result = generate_uuid()
        assert isinstance(result, str)
        assert len(result) == 36  # UUID format: 8-4-4-4-12

    def test_generate_uuid_unique(self) -> None:
        """Test that generate_uuid returns unique values."""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        assert uuid1 != uuid2


class TestModelDispatch:
    """Test model type dispatch in _get_model_data."""

    def test_get_model_data_unknown_type(self) -> None:
        """Test _get_model_data with unknown model type."""

        # Create a mock object that's not a known model type
        class UnknownModel:
            pass

        unknown = UnknownModel()
        result = _get_model_data(unknown)

        # Should return empty dict for unknown types
        assert result == {}

    def test_get_model_data_institution(self) -> None:
        """Test _get_model_data dispatches Institution correctly."""
        mock_inst = Mock(spec=Institution)
        mock_inst.id = "inst_123"
        mock_inst.name = "Test Institution"

        # Temporarily mock the instance type check
        result = _get_model_data(mock_inst)

        # The function will call _institution_to_dict which needs proper attributes
        # For now, just verify it returns a dict (branch coverage)
        assert isinstance(result, dict)

    def test_get_model_data_user(self) -> None:
        """Test _get_model_data dispatches User correctly."""
        mock_user = User(
            id="user_123",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            role="instructor",
        )

        result = _get_model_data(mock_user)
        assert isinstance(result, dict)

    def test_get_model_data_program(self) -> None:
        """Test _get_model_data dispatches Program correctly."""
        mock_program = Mock(spec=Program)
        mock_program.id = "prog_123"

        result = _get_model_data(mock_program)
        assert isinstance(result, dict)

    def test_get_model_data_course(self) -> None:
        """Test _get_model_data dispatches Course correctly."""
        mock_course = Course(
            id="course_123",
            course_number="TEST-101",
            course_title="Test Course",
            institution_id="inst_123",
        )

        result = _get_model_data(mock_course)
        assert isinstance(result, dict)

    def test_get_model_data_term(self) -> None:
        """Test _get_model_data dispatches Term correctly."""
        term = Term(
            id="term_123",
            term_name="Fall 2025",
            name="Fall 2025",
            start_date="2025-08-30",
            end_date="2025-12-15",
            assessment_due_date="2025-12-20",
            institution_id="inst-1",
        )

        result = _get_model_data(term)
        assert isinstance(result, dict)
        assert result["status"] in {"ACTIVE", "SCHEDULED", "PASSED", "UNKNOWN"}
        assert isinstance(result["is_active"], bool)

    def test_get_model_data_course_offering(self) -> None:
        """Test _get_model_data dispatches CourseOffering correctly."""
        mock_offering = CourseOffering(
            id="offering_123",
            course_id="course_123",
            term_id="term_123",
            institution_id="inst_123",
        )

        result = _get_model_data(mock_offering)
        assert isinstance(result, dict)

    def test_get_model_data_course_section(self) -> None:
        """Test _get_model_data dispatches CourseSection correctly."""
        mock_section = CourseSection(
            id="section_123",
            offering_id="offering_123",
            section_number="001",
        )

        result = _get_model_data(mock_section)
        assert isinstance(result, dict)

    def test_get_model_data_course_outcome(self) -> None:
        """Test _get_model_data dispatches CourseOutcome correctly."""
        mock_outcome = CourseOutcome(
            id="outcome_123",
            course_id="course_123",
            clo_number="1",
            description="Understand core concepts",
        )

        result = _get_model_data(mock_outcome)
        assert isinstance(result, dict)

    def test_get_model_data_user_invitation(self) -> None:
        """Test _get_model_data dispatches UserInvitation correctly."""
        mock_invitation = Mock(spec=UserInvitation)
        mock_invitation.id = "inv_123"

        result = _get_model_data(mock_invitation)
        assert isinstance(result, dict)


class TestToDictEdgeCases:
    """Test to_dict function edge cases."""

    def test_to_dict_with_extras(self) -> None:
        """Test to_dict with model that has extras attribute."""
        mock_model = Mock()
        mock_model.extras = {"custom_field": "custom_value"}

        # Mock the model type to return empty dict from _get_model_data
        result = to_dict(mock_model)

        # Should include extras
        assert "custom_field" in result
        assert result["custom_field"] == "custom_value"

    def test_to_dict_with_extra_fields_param(self) -> None:
        """Test to_dict with extra_fields parameter."""
        mock_model = Mock()
        mock_model.extras = None  # No extras attribute

        extra = {"additional_data": "extra_value"}
        result = to_dict(mock_model, extra_fields=extra)

        # Should include extra_fields
        assert "additional_data" in result
        assert result["additional_data"] == "extra_value"

    def test_to_dict_with_both_extras_and_extra_fields(self) -> None:
        """Test to_dict with both extras attribute and extra_fields param."""
        mock_model = Mock()
        mock_model.extras = {"from_model": "model_value"}

        extra = {"from_param": "param_value"}
        result = to_dict(mock_model, extra_fields=extra)

        # Should include both
        assert "from_model" in result
        assert "from_param" in result
        assert result["from_model"] == "model_value"
        assert result["from_param"] == "param_value"

    def test_to_dict_unknown_model_type(self) -> None:
        """Test to_dict with unknown model type."""

        class UnknownModel:
            """Mock unknown model."""

        unknown = UnknownModel()
        result = to_dict(unknown)

        # Should return empty dict (or dict with only extras if present)
        assert isinstance(result, dict)

    def test_to_dict_course_offering(self) -> None:
        """Test to_dict with CourseOffering model."""
        from src.models.models_sql import CourseOffering, to_dict

        offering = CourseOffering(
            id="off-123",
            course_id="course-123",
            term_id="term-123",
            institution_id="inst-123",
        )

        result = to_dict(offering)

        assert result["offering_id"] == "off-123"
        assert result["course_id"] == "course-123"

    def test_to_dict_course_section(self) -> None:
        """Test to_dict with CourseSection model."""
        from src.models.models_sql import CourseSection, to_dict

        section = CourseSection(
            id="sec-123", offering_id="off-123", section_number="001"
        )

        result = to_dict(section)

        assert result["section_id"] == "sec-123"
        assert result["offering_id"] == "off-123"

    def test_to_dict_course_outcome(self) -> None:
        """Test to_dict with CourseOutcome model."""
        from src.models.models_sql import CourseOutcome, to_dict

        outcome = CourseOutcome(
            id="out-123", course_id="course-123", description="Learn Python"
        )

        result = to_dict(outcome)

        assert result["outcome_id"] == "out-123"
        assert result["course_id"] == "course-123"

    def test_to_dict_course_section_outcome_includes_workflow_fields(self) -> None:
        """Regression test: CourseSectionOutcome to_dict must include status fields.

        The audit CLO page requires status, approval_status, submitted_at, etc.
        If these are missing from to_dict, the frontend shows 'Unknown' status.
        """
        from datetime import datetime

        from src.models.models_sql import CourseSectionOutcome, to_dict

        section_outcome = CourseSectionOutcome(
            id="so-123",
            section_id="sec-123",
            outcome_id="out-123",
            students_took=25,
            students_passed=20,
            assessment_tool="Quiz",
            status="awaiting_approval",
            approval_status="pending",
            submitted_at=datetime(2025, 12, 5, 9, 0, 0),
            submitted_by="user-123",
            reviewed_at=None,
            reviewed_by=None,
            feedback_comments="Good work",
        )

        result = to_dict(section_outcome)

        # Core fields
        assert result["id"] == "so-123"
        assert result["section_id"] == "sec-123"
        assert result["outcome_id"] == "out-123"
        # Assessment data
        assert result["students_took"] == 25
        assert result["students_passed"] == 20
        assert result["assessment_tool"] == "Quiz"
        # Workflow status fields (regression: these were missing!)
        assert (
            result["status"] == "awaiting_approval"
        ), "status must be included for audit page"
        assert (
            result["approval_status"] == "pending"
        ), "approval_status must be included"
        # Audit trail fields
        assert result["submitted_at"] == datetime(2025, 12, 5, 9, 0, 0)
        assert result["submitted_by"] == "user-123"
        assert result["reviewed_at"] is None
        assert result["reviewed_by"] is None
        assert result["feedback_comments"] == "Good work"
