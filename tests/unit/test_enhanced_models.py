"""
Unit tests for enhanced authentication models

These tests validate the new authentication-focused models:
- Enhanced User model with auth fields
- UserInvitation model for invitation system
- Program model for program management
- Enhanced Institution model with auth fields

Story 1.1 Smoke Tests
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from models import (
    ACCOUNT_STATUSES,
    INVITATION_STATUSES,
    ROLES,
    Course,
    Institution,
    Program,
    User,
    UserInvitation,
    validate_email,
)


class TestEnhancedUserModel:
    """Test enhanced User model with authentication fields"""

    def test_user_model_creation_with_all_required_fields(self):
        """Test User model creation with all required fields"""
        user_data = User.create_schema(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="instructor",
            institution_id="test-institution-id",
        )

        # Verify core identity fields
        assert user_data["email"] == "test@example.com"
        assert user_data["first_name"] == "John"
        assert user_data["last_name"] == "Doe"
        assert user_data["role"] == "instructor"
        assert user_data["institution_id"] == "test-institution-id"

        # Verify authentication state defaults
        assert user_data["account_status"] == "pending"
        assert user_data["email_verified"] is False
        assert user_data["login_attempts"] == 0
        assert user_data["program_ids"] == []

        # Verify timestamps are set
        assert user_data["created_at"] is not None
        assert user_data["updated_at"] is not None

        # Verify optional fields are None
        assert user_data["password_hash"] is None
        assert user_data["email_verification_token"] is None
        assert user_data["last_login_at"] is None

    def test_user_model_with_optional_fields(self):
        """Test User model creation with optional fields"""
        user_data = User.create_schema(
            email="admin@mocku.test",
            first_name="Admin",
            last_name="User",
            role="institution_admin",
            institution_id="mocku-institution",
            password_hash="hashed_password",
            account_status="active",
            program_ids=["program1", "program2"],
            display_name="Dr. Admin",
        )

        assert user_data["password_hash"] == "hashed_password"
        assert user_data["account_status"] == "active"
        assert user_data["program_ids"] == ["program1", "program2"]
        assert user_data["display_name"] == "Dr. Admin"

    def test_user_model_role_validation(self):
        """Test User model validates role against new UserRole enum"""
        with pytest.raises(ValueError, match="Invalid role"):
            User.create_schema(
                email="test@example.com",
                first_name="Test",
                last_name="User",
                role="invalid_role",
                institution_id="test-institution",
            )

    def test_user_model_account_status_validation(self):
        """Test User model validates account_status"""
        with pytest.raises(ValueError, match="Invalid account_status"):
            User.create_schema(
                email="test@example.com",
                first_name="Test",
                last_name="User",
                role="instructor",
                institution_id="test-institution",
                account_status="invalid_status",
            )

    def test_user_model_institution_id_required(self):
        """Test User model requires institution_id for non-site_admin roles"""
        with pytest.raises(ValueError, match="institution_id is required"):
            User.create_schema(
                email="test@example.com",
                first_name="Test",
                last_name="User",
                role="instructor",
                # institution_id not provided
            )

    def test_user_model_site_admin_no_institution_required(self):
        """Test site_admin role doesn't require institution_id"""
        user_data = User.create_schema(
            email="siteadmin@system.com",
            first_name="Site",
            last_name="Admin",
            role="site_admin",
            # No institution_id provided
        )

        assert user_data["role"] == "site_admin"
        assert user_data["institution_id"] is None

    def test_user_utility_functions(self):
        """Test User utility functions"""
        # Test full_name
        full_name = User.full_name("John", "Doe")
        assert full_name == "John Doe"

        # Test is_active
        assert User.is_active("active") is True
        assert User.is_active("pending") is False
        assert User.is_active("suspended") is False

        # Test is_active with lockout
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        assert User.is_active("active", future_time) is False

        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        assert User.is_active("active", past_time) is True

    def test_user_token_generation(self):
        """Test User token generation methods"""
        verification_token = User.generate_verification_token()
        reset_token = User.generate_reset_token()

        assert isinstance(verification_token, str)
        assert isinstance(reset_token, str)
        assert len(verification_token) > 20  # URL-safe tokens should be substantial
        assert len(reset_token) > 20
        assert verification_token != reset_token  # Should be unique


class TestUserInvitationModel:
    """Test UserInvitation model for invitation system"""

    def test_user_invitation_creation_and_expiry_logic(self):
        """Test UserInvitation model creation and expiry logic"""
        invitation_data = UserInvitation.create_schema(
            email="invited@example.com",
            role="instructor",
            institution_id="test-institution",
            invited_by="admin-user-id",
            personal_message="Welcome to our team!",
        )

        # Verify core fields
        assert invitation_data["email"] == "invited@example.com"
        assert invitation_data["role"] == "instructor"
        assert invitation_data["institution_id"] == "test-institution"
        assert invitation_data["invited_by"] == "admin-user-id"
        assert invitation_data["personal_message"] == "Welcome to our team!"

        # Verify defaults
        assert invitation_data["status"] == "pending"
        assert invitation_data["accepted_at"] is None

        # Verify token generation
        assert invitation_data["token"] is not None
        assert len(invitation_data["token"]) > 20

        # Verify expiry is set (should be 7 days from now)
        expires_at = invitation_data["expires_at"]
        assert isinstance(expires_at, datetime)
        expected_expiry = datetime.now(timezone.utc) + timedelta(days=7)
        # Allow for small time differences in test execution
        assert abs((expires_at - expected_expiry).total_seconds()) < 5

    def test_user_invitation_expiry_checking(self):
        """Test UserInvitation expiry checking methods"""
        # Test non-expired invitation
        future_time = datetime.now(timezone.utc) + timedelta(days=1)
        assert UserInvitation.is_expired(future_time) is False

        # Test expired invitation
        past_time = datetime.now(timezone.utc) - timedelta(days=1)
        assert UserInvitation.is_expired(past_time) is True

        # Test can_accept logic
        future_time = datetime.now(timezone.utc) + timedelta(days=1)
        assert UserInvitation.can_accept("pending", future_time) is True
        assert UserInvitation.can_accept("accepted", future_time) is False
        assert UserInvitation.can_accept("pending", past_time) is False

    def test_user_invitation_role_validation(self):
        """Test UserInvitation validates role"""
        with pytest.raises(ValueError, match="Invalid role"):
            UserInvitation.create_schema(
                email="test@example.com",
                role="invalid_role",
                institution_id="test-institution",
                invited_by="admin-user-id",
            )

    def test_user_invitation_token_generation(self):
        """Test invitation token generation is unique"""
        token1 = UserInvitation.generate_invitation_token()
        token2 = UserInvitation.generate_invitation_token()

        assert token1 != token2
        assert len(token1) > 20
        assert len(token2) > 20


class TestProgramModel:
    """Test Program model for program management"""

    def test_program_model_creation_with_institution_association(self):
        """Test Program model creation with institution association"""
        program_data = Program.create_schema(
            name="Computer Science Department",
            short_name="CS",
            institution_id="test-institution",
            created_by="admin-user-id",
            description="Computer Science and Information Technology programs",
        )

        # Verify core fields
        assert program_data["name"] == "Computer Science Department"
        assert program_data["short_name"] == "CS"
        assert program_data["institution_id"] == "test-institution"
        assert program_data["created_by"] == "admin-user-id"
        assert (
            program_data["description"]
            == "Computer Science and Information Technology programs"
        )

        # Verify defaults
        assert program_data["is_default"] is False
        assert program_data["program_admins"] == []
        assert program_data["is_active"] is True

        # Verify timestamps
        assert program_data["created_at"] is not None
        assert program_data["updated_at"] is not None

    def test_program_model_default_program(self):
        """Test Program model creation for default program"""
        program_data = Program.create_schema(
            name="Unclassified",
            short_name="UNCL",
            institution_id="test-institution",
            created_by="system",
            is_default=True,
        )

        assert program_data["name"] == "Unclassified"
        assert program_data["is_default"] is True
        assert program_data["description"] is None

    def test_program_model_with_admins(self):
        """Test Program model with program administrators"""
        admin_ids = ["admin1", "admin2", "admin3"]
        program_data = Program.create_schema(
            name="Biology Department",
            short_name="BIO",
            institution_id="test-institution",
            created_by="admin-user-id",
            program_admins=admin_ids,
        )

        assert program_data["program_admins"] == admin_ids
        assert Program.admin_count(program_data["program_admins"]) == 3

    def test_program_admin_count_utility(self):
        """Test Program admin count utility function"""
        assert Program.admin_count([]) == 0
        assert Program.admin_count(["admin1"]) == 1
        assert Program.admin_count(["admin1", "admin2", "admin3"]) == 3


class TestEnhancedInstitutionModel:
    """Test enhanced Institution model with auth fields"""

    def test_enhanced_institution_model_with_auth_fields(self):
        """Test enhanced Institution model with auth fields"""
        institution_data = Institution.create_schema(
            name="College of Eastern Idaho",
            short_name="MockU",
            created_by="admin-user-id",
            admin_email="admin@mocku.test",
            website_url="https://mocku.test",
        )

        # Verify core fields
        assert institution_data["name"] == "College of Eastern Idaho"
        assert institution_data["short_name"] == "MOCKU"  # Model converts to uppercase
        assert institution_data["created_by"] == "admin-user-id"
        assert institution_data["admin_email"] == "admin@mocku.test"
        assert institution_data["website_url"] == "https://mocku.test"

        # Verify auth defaults
        assert institution_data["allow_self_registration"] is False
        assert institution_data["require_email_verification"] is True
        assert institution_data["is_active"] is True

        # Verify timestamps
        assert institution_data["created_at"] is not None
        assert institution_data["updated_at"] is not None

    def test_institution_model_optional_website(self):
        """Test Institution model with optional website URL"""
        institution_data = Institution.create_schema(
            name="Test University",
            short_name="TU",
            created_by="admin-user-id",
            admin_email="admin@test.edu",
            # No website_url provided
        )

        assert institution_data["website_url"] is None

    def test_institution_model_email_normalization(self):
        """Test Institution model normalizes email addresses"""
        institution_data = Institution.create_schema(
            name="Test University",
            short_name="TU",
            created_by="admin-user-id",
            admin_email="ADMIN@TEST.EDU",  # Mixed case
        )

        assert institution_data["admin_email"] == "admin@test.edu"  # Normalized


class TestEnhancedCourseModel:
    """Test Course model with program associations"""

    def test_course_model_with_program_associations(self):
        """Test Course model with program associations"""
        program_ids = ["program1", "program2"]
        course_data = Course.create_schema(
            course_number="CS-101",
            course_title="Introduction to Programming",
            department="Computer Science",
            institution_id="test-institution",
            program_ids=program_ids,
        )

        # Verify enhanced fields
        assert course_data["institution_id"] == "test-institution"
        assert course_data["program_ids"] == program_ids

        # Verify existing functionality still works
        assert course_data["course_number"] == "CS-101"
        assert course_data["course_title"] == "Introduction to Programming"
        assert course_data["department"] == "Computer Science"
        assert course_data["credit_hours"] == 3  # Default

    def test_course_model_without_program_associations(self):
        """Test Course model defaults to empty program list"""
        course_data = Course.create_schema(
            course_number="MATH-101",
            course_title="College Algebra",
            department="Mathematics",
            institution_id="test-institution",
        )

        assert course_data["program_ids"] == []  # Default empty list


class TestUserPasswordMethods:
    """Test User model password-related methods"""

    def test_create_password_hash(self):
        """Test password hashing through User model"""
        password = "TestPass123!"
        hashed = User.create_password_hash(password)

        assert isinstance(hashed, str)
        assert hashed != password
        assert hashed.startswith("$2b$")

    def test_validate_password_valid(self):
        """Test password validation with valid password"""
        # Should not raise exception
        User.validate_password("ValidPass123!")

    def test_validate_password_invalid(self):
        """Test password validation with invalid password"""
        from password_service import PasswordValidationError

        with pytest.raises(PasswordValidationError):
            User.validate_password("weak")

    def test_generate_password_reset_token(self):
        """Test password reset token generation"""
        token = User.generate_password_reset_token()

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_password_reset_data(self):
        """Test password reset data creation"""
        user_id = "user123"
        email = "test@example.com"

        reset_data = User.create_password_reset_data(user_id, email)

        assert reset_data["user_id"] == user_id
        assert reset_data["email"] == email
        assert "token" in reset_data
        assert "expires_at" in reset_data
        assert reset_data["used"] is False


class TestModelIntegration:
    """Test integration between enhanced models"""

    def test_complete_user_invitation_flow(self):
        """Test complete user invitation to registration flow"""
        # 1. Create institution
        institution_data = Institution.create_schema(
            name="Test University",
            short_name="TU",
            created_by="system-admin",
            admin_email="admin@test.edu",
        )

        # 2. Create invitation
        invitation_data = UserInvitation.create_schema(
            email="newuser@test.edu",
            role="instructor",
            institution_id=institution_data["institution_id"],
            invited_by="admin-user-id",
        )

        # 3. Create user from invitation
        user_data = User.create_schema(
            email=invitation_data["email"],
            first_name="New",
            last_name="User",
            role=invitation_data["role"],
            institution_id=invitation_data["institution_id"],
            account_status="active",  # After completing registration
        )

        # Verify the flow
        assert user_data["email"] == invitation_data["email"]
        assert user_data["role"] == invitation_data["role"]
        assert user_data["institution_id"] == invitation_data["institution_id"]
        assert user_data["account_status"] == "active"

    def test_institution_program_course_hierarchy(self):
        """Test institution → program → course hierarchy"""
        # 1. Create institution
        institution_data = Institution.create_schema(
            name="Test College",
            short_name="TC",
            created_by="admin-user",
            admin_email="admin@test.edu",
        )

        # 2. Create program in institution
        program_data = Program.create_schema(
            name="Computer Science",
            short_name="CS",
            institution_id=institution_data["institution_id"],
            created_by="admin-user",
        )

        # 3. Create course in program
        course_data = Course.create_schema(
            course_number="CS-101",
            course_title="Programming Fundamentals",
            department="Computer Science",
            institution_id=institution_data["institution_id"],
            program_ids=[program_data["program_id"]],
        )

        # Verify hierarchy
        assert course_data["institution_id"] == institution_data["institution_id"]
        assert program_data["program_id"] in course_data["program_ids"]
        assert program_data["institution_id"] == institution_data["institution_id"]

    def test_program_admin_assignment(self):
        """Test program admin assignment to programs"""
        # Create institution and program
        institution_data = Institution.create_schema(
            name="Test University",
            short_name="TU",
            created_by="system",
            admin_email="admin@test.edu",
        )

        # Create program admin user
        admin_user = User.create_schema(
            email="progadmin@test.edu",
            first_name="Program",
            last_name="Admin",
            role="program_admin",
            institution_id=institution_data["institution_id"],
            program_ids=["program1", "program2"],  # Assigned to multiple programs
        )

        # Create program with this admin
        program_data = Program.create_schema(
            name="Biology Department",
            short_name="BIO",
            institution_id=institution_data["institution_id"],
            created_by=admin_user["user_id"],
            program_admins=[admin_user["user_id"]],
        )

        # Verify assignment
        assert admin_user["user_id"] in program_data["program_admins"]
        assert "program1" in admin_user["program_ids"]
        assert "program2" in admin_user["program_ids"]
        assert Program.admin_count(program_data["program_admins"]) == 1
