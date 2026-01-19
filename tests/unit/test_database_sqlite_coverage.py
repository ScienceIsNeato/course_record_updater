"""
Unit tests for database_sqlite.py - covering uncovered methods.

This file specifically targets methods that aren't covered by existing tests
to push coverage from 45% to 80%+.

Focus areas (from coverage report):
- Lines 136-145: create_new_institution (with admin)
- Lines 151-156: create_new_institution_simple
- Lines 984-1030: get_sections_by_instructor (HUGE block)
"""

from src.database.database_sqlite import SQLDatabase


class TestInstitutionCreationMethods:
    """Test institution creation convenience methods."""

    def test_create_new_institution_with_admin_success(self):
        """Test creating institution with admin user in one operation."""
        db = SQLDatabase()

        institution_data = {
            "name": "Coverage Test University",
            "short_name": "CTU",
            "active": True,
        }

        admin_data = {
            "email": "admin-coverage@test.edu",
            "password_hash": "hashed_password_123",
            "first_name": "Coverage",
            "last_name": "Admin",
            "role": "institution_admin",
        }

        # This method should return (institution_id, user_id) tuple
        result = db.create_new_institution(institution_data, admin_data)

        assert result is not None
        institution_id, user_id = result
        assert institution_id is not None
        assert user_id is not None

        # Verify institution exists
        institution = db.get_institution_by_id(institution_id)
        assert institution is not None
        assert institution["name"] == "Coverage Test University"

        # Verify admin exists and is linked
        user = db.get_user_by_id(user_id)
        assert user is not None
        assert user["email"] == "admin-coverage@test.edu"
        assert user["institution_id"] == institution_id
        assert user["role"] == "institution_admin"

    def test_create_new_institution_simple_success(self):
        """Test creating institution without admin (site admin workflow)."""
        db = SQLDatabase()

        # This method just creates the institution, no admin user
        institution_id = db.create_new_institution_simple(
            name="Simple Test University", short_name="STU", active=True
        )

        assert institution_id is not None

        # Verify institution exists
        institution = db.get_institution_by_id(institution_id)
        assert institution is not None
        assert institution["name"] == "Simple Test University"
        assert institution["short_name"] == "STU"
        assert institution["active"] is True


class TestSectionInstructorMethods:
    """Test section-instructor relationship methods (big uncovered block)."""

    def test_get_sections_by_instructor_with_data(self):
        """Test retrieving enriched sections for an instructor."""
        db = SQLDatabase()

        # Create minimal test data
        institution_id = db.create_institution(
            {"name": "Section Test University", "short_name": "STU"}
        )

        # Create instructor
        instructor_id = db.create_user(
            {
                "email": "instructor-sections@test.edu",
                "password_hash": "hashed",
                "first_name": "Section",
                "last_name": "Instructor",
                "role": "instructor",
                "institution_id": institution_id,
            }
        )

        # Create course
        course_id = db.create_course(
            {
                "course_number": "TEST101",
                "course_title": "Test Course",
                "institution_id": institution_id,
            }
        )

        # Create term
        term_id = db.create_term(
            {
                "term_name": "Test Fall 2024",
                "start_date": "2024-09-01",
                "end_date": "2024-12-15",
                "institution_id": institution_id,
            }
        )

        # Create offering
        offering_id = db.create_course_offering(
            {
                "course_id": course_id,
                "term_id": term_id,
                "institution_id": institution_id,
            }
        )

        # Create section assigned to instructor
        section_id = db.create_course_section(
            {
                "section_number": "001",
                "offering_id": offering_id,
                "instructor_id": instructor_id,
                "institution_id": institution_id,
            }
        )

        # NOW TEST THE UNCOVERED METHOD (lines 984-1030)
        sections = db.get_sections_by_instructor(instructor_id)

        # Verify enriched data
        assert len(sections) >= 1
        section = sections[0]
        assert section["section_number"] == "001"
        # The method enriches with course info
        assert "course_id" in section
        assert "course_number" in section
        assert "course_title" in section
        # And term info
        assert "term_id" in section
        assert "term_name" in section
        # And instructor info
        assert "instructor_name" in section
        assert "Section Instructor" in section["instructor_name"]

    def test_get_sections_by_instructor_empty(self):
        """Test retrieving sections for instructor with no assignments."""
        db = SQLDatabase()

        institution_id = db.create_institution(
            {"name": "Empty Sections University", "short_name": "ESU"}
        )

        instructor_id = db.create_user(
            {
                "email": "no-sections@test.edu",
                "password_hash": "hashed",
                "first_name": "No",
                "last_name": "Sections",
                "role": "instructor",
                "institution_id": institution_id,
            }
        )

        # Call the method with instructor who has no sections
        sections = db.get_sections_by_instructor(instructor_id)

        # Should return empty list, not fail
        assert sections == []


class TestUserUpdateMethods:
    """Test user update edge cases."""

    def test_update_user_partial_fields(self):
        """Test updating only some user fields."""
        db = SQLDatabase()

        institution_id = db.create_institution(
            {"name": "Update Test University", "short_name": "UTU"}
        )

        user_id = db.create_user(
            {
                "email": "update-test@test.edu",
                "password_hash": "original_hash",
                "first_name": "Original",
                "last_name": "Name",
                "role": "instructor",
                "institution_id": institution_id,
            }
        )

        # Update only first_name
        success = db.update_user(user_id, {"first_name": "Updated"})

        assert success is True

        # Verify change
        user = db.get_user_by_id(user_id)
        assert user["first_name"] == "Updated"
        assert user["last_name"] == "Name"  # Unchanged
        assert user["email"] == "update-test@test.edu"  # Unchanged


class TestUserCreation:
    def test_create_user_duplicate_email(self):
        """Test create_user returns None on duplicate email."""
        db = SQLDatabase()
        email = "duplicate@test.edu"

        # Setup institution first
        inst_id = db.create_new_institution_simple("Dup Inst", "DUP")

        # Create first user
        user1_id = db.create_user(
            {
                "email": email,
                "password_hash": "hash",
                "role": "instructor",
                "first_name": "User1",
                "last_name": "Test",
                "institution_id": inst_id,
            }
        )
        assert user1_id is not None

        # Try to create duplicate
        user2_id = db.create_user(
            {
                "email": email,
                "password_hash": "hash",
                "role": "instructor",
                "first_name": "User2",
                "last_name": "Test",
                "institution_id": inst_id,
            }
        )
        assert user2_id is None


#
# NOTE: status+program+term filtered outcomes live on the higher-level service in
# `database_sqlite.DatabaseService` and are exercised via `database_service.get_outcomes_by_status`
# tests (see `tests/unit/test_database_service.py`). SQLDatabase intentionally doesn't expose
# that API.
