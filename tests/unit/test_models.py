"""
Unit tests for the data models module.
"""

import pytest

from models import (
    ASSESSMENT_STATUSES,
    ROLES,
    SECTION_STATUSES,
    Course,
    CourseOutcome,
    CourseSection,
    LegacyCourse,
    Term,
    User,
    validate_course_number,
    validate_email,
    validate_term_name,
)


class TestUser:
    """Test User model functionality"""

    def test_create_user_schema_basic(self):
        """Test creating a basic user schema"""
        user = User.create_schema(
            email="john.doe@cei.edu",
            first_name="John",
            last_name="Doe",
            role="instructor",
        )

        assert user["email"] == "john.doe@cei.edu"
        assert user["first_name"] == "John"
        assert user["last_name"] == "Doe"
        assert user["role"] == "instructor"
        assert user["active"] is True
        assert "user_id" in user
        assert "created_at" in user

    def test_create_user_schema_with_department(self):
        """Test creating user schema with department"""
        user = User.create_schema(
            email="jane.smith@cei.edu",
            first_name="Jane",
            last_name="Smith",
            role="program_admin",
            department="Business",
        )

        assert user["department"] == "Business"
        assert user["role"] == "program_admin"

    def test_create_user_invalid_role(self):
        """Test that invalid role raises ValueError"""
        with pytest.raises(ValueError, match="Invalid role"):
            User.create_schema(
                email="test@cei.edu",
                first_name="Test",
                last_name="User",
                role="invalid_role",
            )

    def test_get_permissions(self):
        """Test getting permissions for different roles"""
        instructor_perms = User.get_permissions("instructor")
        assert "view_own_sections" in instructor_perms
        assert "manage_users" not in instructor_perms

        admin_perms = User.get_permissions("site_admin")
        assert "manage_users" in admin_perms
        assert "full_access" in admin_perms


class TestCourse:
    """Test Course model functionality"""

    def test_create_course_schema_basic(self):
        """Test creating a basic course schema"""
        course = Course.create_schema(
            course_number="ACC-201",
            course_title="Accounting Principles",
            department="Business",
        )

        assert course["course_number"] == "ACC-201"
        assert course["course_title"] == "Accounting Principles"
        assert course["department"] == "Business"
        assert course["credit_hours"] == 3  # Default
        assert course["active"] is True
        assert "course_id" in course

    def test_create_course_with_credit_hours(self):
        """Test creating course with custom credit hours"""
        course = Course.create_schema(
            course_number="NURS-150",
            course_title="Nursing Fundamentals",
            department="Nursing",
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
        assert term["active"] is True


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

    # Grade distribution functionality removed per requirements


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
        assert "assessment_data" in outcome
        assert outcome["assessment_data"]["assessment_status"] == "not_started"

    def test_update_assessment_data(self):
        """Test updating assessment data"""
        assessment = CourseOutcome.update_assessment_data(
            students_assessed=25,
            students_meeting=22,
            assessment_status="completed",
            narrative="Most students performed well...",
        )

        assert assessment["assessment_data"]["students_assessed"] == 25
        assert assessment["assessment_data"]["students_meeting"] == 22
        assert assessment["assessment_data"]["percentage_meeting"] == 88.0  # Calculated
        assert assessment["assessment_data"]["assessment_status"] == "completed"
        assert assessment["narrative"] == "Most students performed well..."

    def test_invalid_assessment_status(self):
        """Test that invalid assessment status raises ValueError"""
        with pytest.raises(ValueError, match="Invalid assessment_status"):
            CourseOutcome.update_assessment_data(assessment_status="invalid_status")


class TestLegacyCourse:
    """Test LegacyCourse model functionality"""

    def test_from_flat_record(self):
        """Test converting flat record to legacy format"""
        flat_record = {
            "course_number": "ACC-201",
            "course_title": "Accounting Principles",
            "instructor_name": "John Smith",
            "term": "2024 Fall",
            "num_students": 25,
            "grade_a": 5,
            "grade_b": 8,
            "grade_c": 10,
            "grade_d": 2,
            "grade_f": 0,
        }

        legacy = LegacyCourse.from_flat_record(flat_record)

        assert legacy["course_number"] == "ACC-201"
        assert legacy["instructor_name"] == "John Smith"
        assert legacy["term"] == "2024 Fall"

    def test_to_relational_entities(self):
        """Test converting legacy flat course to relational entities"""
        flat_record = {
            "course_number": "ACC-201",
            "course_title": "Accounting Principles",
            "instructor_name": "John Smith",
            "term": "2024 Fall",
            "num_students": 25,
            "grade_a": 5,
        }

        entities = LegacyCourse.to_relational_entities(flat_record)

        assert "course" in entities
        assert "term" in entities
        assert "user" in entities
        assert "section" in entities

        assert entities["course"]["course_number"] == "ACC-201"
        assert entities["term"]["name"] == "2024 Fall"
        assert entities["user"]["first_name"] == "John"
        assert entities["section"]["enrollment"] == 25


class TestValidationFunctions:
    """Test validation functions"""

    def test_validate_email(self):
        """Test email validation"""
        assert validate_email("john.doe@cei.edu") is True
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
        """Test that all roles are properly defined"""
        assert "instructor" in ROLES
        assert "program_admin" in ROLES
        assert "site_admin" in ROLES

        for role, config in ROLES.items():
            assert "name" in config
            assert "permissions" in config
            assert isinstance(config["permissions"], list)

    def test_status_enums_defined(self):
        """Test that status enums are properly defined"""
        assert "assigned" in SECTION_STATUSES
        assert "completed" in SECTION_STATUSES

        assert "not_started" in ASSESSMENT_STATUSES
        assert "completed" in ASSESSMENT_STATUSES


class TestModelValidationFunctions:
    """Test model validation functions."""

    def test_validate_course_number_valid(self):
        """Test validate_course_number with valid course numbers."""
        assert validate_course_number("CS-101") is True
        assert validate_course_number("MATH-205") is True
        assert validate_course_number("BIO-1010") is True

    def test_validate_course_number_invalid(self):
        """Test validate_course_number with invalid course numbers."""
        assert validate_course_number("invalid") is False
        assert validate_course_number("CS101") is False  # Missing dash
        assert validate_course_number("CS-") is False  # Missing number
        assert validate_course_number("") is False  # Empty string
        # Note: None handling would need to be added to the actual function

    def test_validate_term_name_basic(self):
        """Test validate_term_name with basic functionality."""
        # Test what the current function actually validates
        assert validate_term_name("2024 Fall") is True
        assert validate_term_name("2025 Spring") is True
        assert validate_term_name("2024 Summer") is True

    def test_validate_term_name_invalid_basic(self):
        """Test validate_term_name with invalid formats."""
        assert validate_term_name("Invalid Term") is False
        assert validate_term_name("Fall") is False  # Missing year
        assert validate_term_name("2024") is False  # Missing semester
        assert validate_term_name("") is False  # Empty string
        # Note: None handling would need to be added to the actual function

    def test_user_model_active_status_calculation(self):
        """Test User model's active status calculation logic."""
        from models import User

        # Test various combinations of account status and sections
        test_cases = [
            ("active", True, True),  # Active account with sections
            ("active", False, False),  # Active account without sections
            ("imported", True, False),  # Imported account with sections
            ("imported", False, False),  # Imported account without sections
            ("inactive", True, False),  # Inactive account with sections
            ("inactive", False, False),  # Inactive account without sections
        ]

        for account_status, has_sections, expected_active in test_cases:
            result = User.calculate_active_status(account_status, has_sections)
            assert (
                result == expected_active
            ), f"Failed for {account_status}, {has_sections}"

    def test_course_section_model_comprehensive(self):
        """Test CourseSection model with comprehensive data."""
        section_data = CourseSection.create_schema(
            offering_id="offering123",
            section_number="001",
            instructor_id="instructor123",
            enrollment=25,  # Correct parameter name
            status="assigned",  # Valid status from the model
        )

        # Verify all fields are present
        assert section_data["offering_id"] == "offering123"
        assert section_data["section_number"] == "001"
        assert section_data["instructor_id"] == "instructor123"
        assert section_data["enrollment"] == 25
        assert section_data["status"] == "assigned"
        assert "created_at" in section_data


class TestModelValidationEdgeCases:
    """Test model validation edge cases and comprehensive functionality."""

    def test_validate_course_number_edge_cases(self):
        """Test validate_course_number with various edge cases."""
        # Test with different valid formats (only numeric after dash)
        valid_numbers = ["MATH-101", "ENG-200", "HIST-300", "CS-101", "PHYS-201"]

        for course_number in valid_numbers:
            result = validate_course_number(course_number)
            assert result is True, f"Should validate {course_number}"

        # Test with invalid formats
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
        # Test with different valid formats
        valid_terms = ["2024 Fall", "2025 Spring", "2023 Summer", "2026 Winter"]

        for term_name in valid_terms:
            result = validate_term_name(term_name)
            assert result is True, f"Should validate {term_name}"

        # Test with invalid formats
        invalid_terms = [
            "Fall 2024",  # Wrong order
            "24 Fall",  # Two-digit year
            "2024Fall",  # No space, not CEI format
        ]

        for term_name in invalid_terms:
            result = validate_term_name(term_name)
            assert result is False, f"Should not validate {term_name}"

    def test_format_term_name_comprehensive(self):
        """Test format_term_name comprehensive functionality."""
        from models import format_term_name

        # Test format_term_name with year and season parameters
        result = format_term_name("2024", "Fall")
        assert result == "2024 Fall"

        result = format_term_name("2025", "Spring")
        assert result == "2025 Spring"

    def test_parse_cei_term_comprehensive(self):
        """Test parse_cei_term comprehensive functionality."""
        from models import parse_cei_term

        # Test valid CEI term formats
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

    def test_user_model_comprehensive_functionality(self):
        """Test comprehensive User model functionality."""
        # Test User.calculate_active_status with various combinations
        # Logic: active status requires BOTH account_status == "active" AND has_active_courses == True
        test_cases = [
            ("active", True, True),  # Active account with sections - TRUE
            ("active", False, False),  # Active account without sections - FALSE
            ("imported", True, False),  # Imported account with sections - FALSE
            ("imported", False, False),  # Imported account without sections - FALSE
            ("invited", True, False),  # Invited account with sections - FALSE
            ("invited", False, False),  # Invited account without sections - FALSE
        ]

        for account_status, has_sections, expected_active in test_cases:
            result = User.calculate_active_status(account_status, has_sections)
            assert (
                result == expected_active
            ), f"Failed for {account_status}, {has_sections}"

    def test_course_section_model_comprehensive_functionality(self):
        """Test comprehensive CourseSection model functionality."""
        # Test with various valid data combinations
        test_data_sets = [
            {
                "offering_id": "offering1",
                "section_number": "001",
                "instructor_id": "instructor1",
                "enrollment": 25,
                "status": "assigned",
            },
            {
                "offering_id": "offering2",
                "section_number": "002",
                "instructor_id": "instructor2",
                "enrollment": 30,
                "status": "in_progress",
            },
            {
                "offering_id": "offering3",
                "section_number": "003",
                "instructor_id": "instructor3",
                "enrollment": 15,
                "status": "completed",
            },
        ]

        for data in test_data_sets:
            schema = CourseSection.create_schema(**data)

            # Should create valid schema
            assert isinstance(schema, dict)
            assert schema["offering_id"] == data["offering_id"]
            assert schema["section_number"] == data["section_number"]
            assert schema["instructor_id"] == data["instructor_id"]
            assert schema["enrollment"] == data["enrollment"]
            assert schema["status"] == data["status"]


class TestModelsFinalCoverage:
    """Final push for models coverage."""

    def test_models_constants_validation(self):
        """Test model constants and validation functions."""
        from models import (
            format_term_name,
            parse_cei_term,
            validate_course_number,
            validate_term_name,
        )

        # Test validation functions
        assert validate_course_number("MATH-101") is True
        assert (
            validate_course_number("math-101") is True
        )  # Current implementation accepts lowercase

        assert validate_term_name("2024 Fall") is True

        # Test format and parse functions
        formatted = format_term_name(2024, "Fall")
        assert isinstance(formatted, str)

        result = parse_cei_term("2024FA")
        assert isinstance(result, tuple) and len(result) == 2

    def test_models_user_active_status(self):
        """Test User model active status calculation."""
        from models import User

        # Test various status combinations
        assert User.calculate_active_status("active", True) is True
        assert User.calculate_active_status("active", False) is False
        assert User.calculate_active_status("inactive", True) is False
        assert User.calculate_active_status("inactive", False) is False
