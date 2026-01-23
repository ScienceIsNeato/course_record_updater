"""
Unit tests for the data models module.

Tests unique model behaviors not covered by test_enhanced_models.py.
Duplicate tests (user creation, role validation, active status, comprehensive
section/course tests) have been consolidated into test_enhanced_models.py which
has more thorough coverage of those behaviors.
"""

from datetime import date

import pytest

from src.models.models import (
    ASSESSMENT_STATUSES,
    SECTION_STATUSES,
    Course,
    CourseOutcome,
    CourseSection,
    Term,
    User,
    validate_course_number,
    validate_email,
    validate_term_name,
)


class TestUser:
    """Test User model functionality - unique validation behaviors."""

    def test_create_user_missing_first_name_raises_error(self):
        """Test that missing first name raises ValueError"""
        with pytest.raises(ValueError, match="First name is required"):
            User.create_schema(
                email="test@mocku.test",
                first_name="",
                last_name="User",
                role="instructor",
                institution_id="test-institution",
                password_hash="$2b$12$test_hash",
            )

    def test_create_user_missing_last_name_raises_error(self):
        """Test that missing last name raises ValueError"""
        with pytest.raises(ValueError, match="Last name is required"):
            User.create_schema(
                email="test@mocku.test",
                first_name="Test",
                last_name="",
                role="instructor",
                institution_id="test-institution",
                password_hash="$2b$12$test_hash",
            )

    def test_create_user_whitespace_only_first_name_raises_error(self):
        """Test that whitespace-only first name raises ValueError"""
        with pytest.raises(ValueError, match="First name is required"):
            User.create_schema(
                email="test@mocku.test",
                first_name="   ",
                last_name="User",
                role="instructor",
                institution_id="test-institution",
                password_hash="$2b$12$test_hash",
            )

    def test_create_user_whitespace_only_last_name_raises_error(self):
        """Test that whitespace-only last name raises ValueError"""
        with pytest.raises(ValueError, match="Last name is required"):
            User.create_schema(
                email="test@mocku.test",
                first_name="Test",
                last_name="   ",
                role="instructor",
                institution_id="test-institution",
                password_hash="$2b$12$test_hash",
            )

    def test_get_permissions(self):
        """Test getting permissions for different roles using new authorization system"""
        instructor_perms = User.get_permissions("instructor")
        assert "view_section_data" in instructor_perms
        assert "submit_assessments" in instructor_perms
        assert "manage_users" not in instructor_perms

        admin_perms = User.get_permissions("site_admin")
        assert "manage_users" in admin_perms
        assert "manage_institutions" in admin_perms
        assert "view_all_data" in admin_perms


class TestCourse:
    """Test Course model functionality - unique credit hours behavior."""

    def test_create_course_with_credit_hours(self):
        """Test creating course with custom credit hours"""
        course = Course.create_schema(
            course_number="NURS-150",
            course_title="Nursing Fundamentals",
            department="Nursing",
            institution_id="test-institution",
            credit_hours=4,
        )

        assert course["credit_hours"] == 4


class TestTerm:
    """Test Term model functionality"""

    def test_create_term_schema(self):
        """Test creating a term schema"""
        term = Term.create_schema(
            name="2024 Fall",
            start_date="2024-08-26",
            end_date="2024-12-13",
            assessment_due_date="2024-12-20",
        )

        assert term["name"] == "2024 Fall"
        assert term["start_date"] == "2024-08-26"
        assert term["end_date"] == "2024-12-13"
        assert term["assessment_due_date"] == "2024-12-20"

    def test_term_status_helper(self):
        """Term status helper computes values from dates."""
        status = Term.get_status(
            "2024-01-01",
            "2024-06-01",
            reference_date=date(2024, 2, 1),
        )
        assert status == "ACTIVE"


class TestCourseSection:
    """Test CourseSection model functionality"""

    def test_create_section_schema_basic(self):
        """Test creating a basic section schema"""
        section = CourseSection.create_schema(offering_id="offering-123")

        assert section["offering_id"] == "offering-123"
        assert section["section_number"] == "001"  # Default
        assert section["status"] == "assigned"  # Default
        assert section["instructor_id"] is None
        assert "grade_distribution" in section

    def test_create_section_with_instructor(self):
        """Test creating section with instructor assigned"""
        section = CourseSection.create_schema(
            offering_id="offering-123",
            instructor_id="instructor-789",
            enrollment=25,
        )

        assert section["instructor_id"] == "instructor-789"
        assert section["enrollment"] == 25
        assert section["assigned_date"] is not None

    def test_invalid_status(self):
        """Test that invalid status raises ValueError"""
        with pytest.raises(ValueError, match="Invalid status"):
            CourseSection.create_schema(
                offering_id="offering-123", status="invalid_status"
            )


class TestCourseOutcome:
    """Test CourseOutcome model functionality"""

    def test_create_outcome_schema_basic(self):
        """Test creating a basic outcome schema"""
        outcome = CourseOutcome.create_schema(
            course_id="course-123",
            clo_number="1",
            description="Students will demonstrate understanding of...",
        )

        assert outcome["course_id"] == "course-123"
        assert outcome["clo_number"] == "1"
        assert outcome["description"] == "Students will demonstrate understanding of..."
        assert outcome["active"] is True
        assert outcome["students_took"] is None
        assert outcome["students_passed"] is None
        assert outcome["assessment_tool"] is None

    def test_update_assessment_data(self):
        """Test updating assessment data"""
        assessment = CourseOutcome.update_assessment_data(
            students_took=25,
            students_passed=22,
            assessment_tool="Test #3",
        )

        assert assessment["students_took"] == 25
        assert assessment["students_passed"] == 22
        assert assessment["assessment_tool"] == "Test #3"
        assert abs(assessment["percentage_meeting"] - 88.0) < 0.01

    def test_invalid_assessment_tool_length(self):
        """Test that assessment_tool exceeding 50 chars raises ValueError"""
        long_tool = "This is a very long assessment tool name that exceeds the 50 character limit"
        with pytest.raises(
            ValueError, match="assessment_tool must be 50 characters or less"
        ):
            CourseOutcome.update_assessment_data(assessment_tool=long_tool)


class TestValidationFunctions:
    """Test validation functions"""

    def test_validate_email(self):
        """Test email validation"""
        assert validate_email("john.doe@mocku.test") is True
        assert validate_email("test@example.com") is True
        assert validate_email("invalid.email") is False
        assert validate_email("@invalid.com") is False
        assert validate_email("invalid@") is False

    def test_validate_course_number(self):
        """Test course number validation"""
        assert validate_course_number("ACC-201") is True
        assert validate_course_number("NURS-150") is True
        assert validate_course_number("MATH-101") is True
        assert validate_course_number("ACC201") is False  # Missing hyphen
        assert validate_course_number("201-ACC") is False  # Wrong order
        assert validate_course_number("ACC-") is False  # Missing number

    def test_validate_term_name(self):
        """Test term name validation"""
        assert validate_term_name("2024 Fall") is True
        assert validate_term_name("2024 Spring") is True
        assert validate_term_name("2025 Summer") is True
        assert validate_term_name("Fall 2024") is False  # Wrong order
        assert validate_term_name("2024") is False  # Missing season
        assert validate_term_name("24 Fall") is False  # Wrong year format


class TestConstants:
    """Test that constants are properly defined"""

    def test_roles_defined(self):
        """Test that all roles are properly defined in new authorization system"""
        from src.services.auth_service import ROLE_PERMISSIONS, UserRole

        role_values = [role.value for role in UserRole]
        assert "instructor" in role_values
        assert "program_admin" in role_values
        assert "institution_admin" in role_values
        assert "site_admin" in role_values

        for role_value in role_values:
            assert role_value in ROLE_PERMISSIONS
            assert isinstance(ROLE_PERMISSIONS[role_value], list)
            assert len(ROLE_PERMISSIONS[role_value]) > 0

    def test_status_enums_defined(self):
        """Test that status enums are properly defined"""
        assert "assigned" in SECTION_STATUSES
        assert "completed" in SECTION_STATUSES

        assert "not_started" in ASSESSMENT_STATUSES
        assert "completed" in ASSESSMENT_STATUSES


class TestModelValidationEdgeCases:
    """Test model validation edge cases - comprehensive versions kept here."""

    def test_validate_course_number_edge_cases(self):
        """Test validate_course_number with various edge cases."""
        valid_numbers = ["MATH-101", "ENG-200", "HIST-300", "CS-101", "PHYS-201"]

        for course_number in valid_numbers:
            result = validate_course_number(course_number)
            assert result is True, f"Should validate {course_number}"

        invalid_numbers = [
            "MATH101",  # Missing dash
            "MATH-",  # Missing number
            "MATH-ABC",  # Non-numeric course number
            "MATH-200A",  # Letters after number
            "MATH-101L",  # Letters after number
        ]

        for course_number in invalid_numbers:
            result = validate_course_number(course_number)
            assert result is False, f"Should not validate {course_number}"

    def test_validate_term_name_edge_cases(self):
        """Test validate_term_name with various edge cases."""
        valid_terms = ["2024 Fall", "2025 Spring", "2023 Summer", "2026 Winter"]

        for term_name in valid_terms:
            result = validate_term_name(term_name)
            assert result is True, f"Should validate {term_name}"

        invalid_terms = [
            "Fall 2024",  # Wrong order
            "24 Fall",  # Two-digit year
            "2024Fall",  # No space, not MockU format
        ]

        for term_name in invalid_terms:
            result = validate_term_name(term_name)
            assert result is False, f"Should not validate {term_name}"

    def test_format_term_name_comprehensive(self):
        """Test format_term_name comprehensive functionality."""
        from src.models.models import format_term_name

        result = format_term_name("2024", "Fall")
        assert result == "2024 Fall"

        result = format_term_name("2025", "Spring")
        assert result == "2025 Spring"

    def test_parse_cei_term_comprehensive(self):
        """Test parse_cei_term comprehensive functionality."""
        from src.adapters.cei_excel_adapter import parse_cei_term

        valid_terms = ["2024FA", "2025SP", "2023SU", "2026WI"]

        expected_results = [
            ("2024", "Fall"),
            ("2025", "Spring"),
            ("2023", "Summer"),
            ("2026", "Winter"),
        ]

        for cei_term, expected in zip(valid_terms, expected_results):
            result = parse_cei_term(cei_term)
            assert result == expected, f"Expected {expected}, got {result}"


class TestCourseOfferingAdditional:
    """Test CourseOffering model additional functionality."""

    def test_create_offering_schema_basic(self):
        """Test basic course offering schema creation."""
        from src.models.models import CourseOffering

        schema = CourseOffering.create_schema(
            course_id="course123", term_id="term456", institution_id="inst789"
        )

        assert schema["course_id"] == "course123"
        assert schema["term_id"] == "term456"
        assert schema["institution_id"] == "inst789"
        assert "offering_id" in schema
        assert schema["capacity"] is None


class TestCourseOutcomeAdditional:
    """Test CourseOutcome model additional functionality."""

    def test_update_assessment_data_percentage_calculation(self):
        """Test automatic percentage calculation in assessment data update."""
        from src.models.models import CourseOutcome

        updated_data = CourseOutcome.update_assessment_data(
            students_took=30, students_passed=24
        )

        assert updated_data["students_took"] == 30
        assert updated_data["students_passed"] == 24
        assert updated_data["percentage_meeting"] == 80.0
