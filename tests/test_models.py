"""
Unit tests for the data models module.
"""

import pytest
from models import (
    User, Course, Term, CourseSection, CourseOutcome, LegacyCourse,
    ROLES, SECTION_STATUSES, ASSESSMENT_STATUSES,
    validate_email, validate_course_number, validate_term_name
)


class TestUser:
    """Test User model functionality"""
    
    def test_create_user_schema_basic(self):
        """Test creating a basic user schema"""
        user = User.create_schema(
            email="john.doe@cei.edu",
            first_name="John",
            last_name="Doe",
            role="instructor"
        )
        
        assert user['email'] == "john.doe@cei.edu"
        assert user['first_name'] == "John"
        assert user['last_name'] == "Doe"
        assert user['role'] == "instructor"
        assert user['active'] is True
        assert 'user_id' in user
        assert 'created_at' in user
    
    def test_create_user_schema_with_department(self):
        """Test creating user schema with department"""
        user = User.create_schema(
            email="jane.smith@cei.edu",
            first_name="Jane",
            last_name="Smith",
            role="program_admin",
            department="Business"
        )
        
        assert user['department'] == "Business"
        assert user['role'] == "program_admin"
    
    def test_create_user_invalid_role(self):
        """Test that invalid role raises ValueError"""
        with pytest.raises(ValueError, match="Invalid role"):
            User.create_schema(
                email="test@cei.edu",
                first_name="Test",
                last_name="User",
                role="invalid_role"
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
            department="Business"
        )
        
        assert course['course_number'] == "ACC-201"
        assert course['course_title'] == "Accounting Principles"
        assert course['department'] == "Business"
        assert course['credit_hours'] == 3  # Default
        assert course['active'] is True
        assert 'course_id' in course
    
    def test_create_course_with_credit_hours(self):
        """Test creating course with custom credit hours"""
        course = Course.create_schema(
            course_number="NURS-150",
            course_title="Nursing Fundamentals",
            department="Nursing",
            credit_hours=4
        )
        
        assert course['credit_hours'] == 4


class TestTerm:
    """Test Term model functionality"""
    
    def test_create_term_schema(self):
        """Test creating a term schema"""
        term = Term.create_schema(
            name="2024 Fall",
            start_date="2024-08-26",
            end_date="2024-12-13",
            assessment_due_date="2024-12-20"
        )
        
        assert term['name'] == "2024 Fall"
        assert term['start_date'] == "2024-08-26"
        assert term['end_date'] == "2024-12-13"
        assert term['assessment_due_date'] == "2024-12-20"
        assert term['active'] is True


class TestCourseSection:
    """Test CourseSection model functionality"""
    
    def test_create_section_schema_basic(self):
        """Test creating a basic section schema"""
        section = CourseSection.create_schema(
            course_id="course-123",
            term_id="term-456"
        )
        
        assert section['course_id'] == "course-123"
        assert section['term_id'] == "term-456"
        assert section['section_number'] == "001"  # Default
        assert section['status'] == "assigned"  # Default
        assert section['instructor_id'] is None
        assert 'grade_distribution' in section
    
    def test_create_section_with_instructor(self):
        """Test creating section with instructor assigned"""
        section = CourseSection.create_schema(
            course_id="course-123",
            term_id="term-456",
            instructor_id="instructor-789",
            enrollment=25
        )
        
        assert section['instructor_id'] == "instructor-789"
        assert section['enrollment'] == 25
        assert section['assigned_date'] is not None
    
    def test_invalid_status(self):
        """Test that invalid status raises ValueError"""
        with pytest.raises(ValueError, match="Invalid status"):
            CourseSection.create_schema(
                course_id="course-123",
                term_id="term-456",
                status="invalid_status"
            )
    
    def test_update_grade_distribution(self):
        """Test updating grade distribution"""
        grades = CourseSection.update_grade_distribution(
            grade_a=5,
            grade_b=8,
            grade_c=10,
            grade_d=2,
            grade_f=0
        )
        
        assert grades['grade_a'] == 5
        assert grades['grade_b'] == 8
        assert grades['grade_c'] == 10
        assert grades['grade_d'] == 2
        assert grades['grade_f'] == 0


class TestCourseOutcome:
    """Test CourseOutcome model functionality"""
    
    def test_create_outcome_schema_basic(self):
        """Test creating a basic outcome schema"""
        outcome = CourseOutcome.create_schema(
            course_id="course-123",
            clo_number="1",
            description="Students will demonstrate understanding of..."
        )
        
        assert outcome['course_id'] == "course-123"
        assert outcome['clo_number'] == "1"
        assert outcome['description'] == "Students will demonstrate understanding of..."
        assert outcome['active'] is True
        assert 'assessment_data' in outcome
        assert outcome['assessment_data']['assessment_status'] == 'not_started'
    
    def test_update_assessment_data(self):
        """Test updating assessment data"""
        assessment = CourseOutcome.update_assessment_data(
            students_assessed=25,
            students_meeting=22,
            assessment_status='completed',
            narrative="Most students performed well..."
        )
        
        assert assessment['assessment_data']['students_assessed'] == 25
        assert assessment['assessment_data']['students_meeting'] == 22
        assert assessment['assessment_data']['percentage_meeting'] == 88.0  # Calculated
        assert assessment['assessment_data']['assessment_status'] == 'completed'
        assert assessment['narrative'] == "Most students performed well..."
    
    def test_invalid_assessment_status(self):
        """Test that invalid assessment status raises ValueError"""
        with pytest.raises(ValueError, match="Invalid assessment_status"):
            CourseOutcome.update_assessment_data(
                assessment_status='invalid_status'
            )


class TestLegacyCourse:
    """Test LegacyCourse model functionality"""
    
    def test_from_flat_record(self):
        """Test converting flat record to legacy format"""
        flat_record = {
            'course_number': 'ACC-201',
            'course_title': 'Accounting Principles',
            'instructor_name': 'John Smith',
            'term': '2024 Fall',
            'num_students': 25,
            'grade_a': 5,
            'grade_b': 8,
            'grade_c': 10,
            'grade_d': 2,
            'grade_f': 0
        }
        
        legacy = LegacyCourse.from_flat_record(flat_record)
        
        assert legacy['course_number'] == 'ACC-201'
        assert legacy['instructor_name'] == 'John Smith'
        assert legacy['term'] == '2024 Fall'
    
    def test_to_relational_entities(self):
        """Test converting legacy flat course to relational entities"""
        flat_record = {
            'course_number': 'ACC-201',
            'course_title': 'Accounting Principles',
            'instructor_name': 'John Smith',
            'term': '2024 Fall',
            'num_students': 25,
            'grade_a': 5
        }
        
        entities = LegacyCourse.to_relational_entities(flat_record)
        
        assert 'course' in entities
        assert 'term' in entities
        assert 'user' in entities
        assert 'section' in entities
        
        assert entities['course']['course_number'] == 'ACC-201'
        assert entities['term']['name'] == '2024 Fall'
        assert entities['user']['first_name'] == 'John'
        assert entities['section']['enrollment'] == 25


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
        assert validate_course_number("ACC-") is False     # Missing number
    
    def test_validate_term_name(self):
        """Test term name validation"""
        assert validate_term_name("2024 Fall") is True
        assert validate_term_name("2024 Spring") is True
        assert validate_term_name("2025 Summer") is True
        assert validate_term_name("Fall 2024") is False   # Wrong order
        assert validate_term_name("2024") is False        # Missing season
        assert validate_term_name("24 Fall") is False     # Wrong year format


class TestConstants:
    """Test that constants are properly defined"""
    
    def test_roles_defined(self):
        """Test that all roles are properly defined"""
        assert 'instructor' in ROLES
        assert 'program_admin' in ROLES
        assert 'site_admin' in ROLES
        
        for role, config in ROLES.items():
            assert 'name' in config
            assert 'permissions' in config
            assert isinstance(config['permissions'], list)
    
    def test_status_enums_defined(self):
        """Test that status enums are properly defined"""
        assert 'assigned' in SECTION_STATUSES
        assert 'completed' in SECTION_STATUSES
        
        assert 'not_started' in ASSESSMENT_STATUSES
        assert 'completed' in ASSESSMENT_STATUSES
