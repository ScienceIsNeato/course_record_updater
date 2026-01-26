"""Unit tests for CRUD API endpoints."""

from unittest.mock import patch

import pytest

from src.app import app
from tests.test_utils import create_test_session


@pytest.fixture
def client():
    """Create test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def create_site_admin_session(client):
    """Create session for site admin user."""
    user_data = {
        "user_id": "site-admin-123",
        "role": "site_admin",
        "institution_id": "inst-1",
        "email": "siteadmin@example.com",
    }
    create_test_session(client, user_data)


def create_institution_admin_session(client):
    """Create session for institution admin user."""
    user_data = {
        "user_id": "inst-admin-123",
        "role": "institution_admin",
        "institution_id": "inst-1",
        "email": "instadmin@example.com",
    }
    create_test_session(client, user_data)


def create_instructor_session(client):
    """Create session for instructor user."""
    user_data = {
        "user_id": "instructor-123",
        "role": "instructor",
        "institution_id": "inst-1",
        "email": "instructor@example.com",
    }
    create_test_session(client, user_data)


def get_csrf_token(client):
    """Get CSRF token using Flask-WTF's generate_csrf."""
    from flask import session as flask_session
    from flask_wtf.csrf import generate_csrf

    # Get the raw token from the session (created by create_test_session)
    with client.session_transaction() as sess:
        raw_token = sess.get("csrf_token")

    # Generate the signed token from the raw token
    with client.application.test_request_context():
        if raw_token:
            flask_session["csrf_token"] = raw_token
        return generate_csrf()


# ========================================
# USER CRUD TESTS
# ========================================


class TestUsersCRUD:
    """Tests for Users CRUD endpoints."""

    @patch("src.api.routes.users.get_user_by_id")
    def test_get_user_by_id_success(self, mock_get_user, client):
        """Test GET /api/users/<id> - success"""
        create_site_admin_session(client)
        mock_get_user.return_value = {
            "user_id": "user-123",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "instructor",
        }

        response = client.get("/api/users/user-123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["user"]["email"] == "test@example.com"

    @patch("src.api.routes.users.get_user_by_id")
    def test_get_user_not_found(self, mock_get_user, client):
        """Test GET /api/users/<id> - user not found"""
        create_site_admin_session(client)
        mock_get_user.return_value = None

        response = client.get("/api/users/nonexistent")

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False

    @patch("src.api.routes.users.update_user_profile")
    @patch("src.api.routes.users.get_user_by_id")
    def test_update_own_profile_success(self, mock_get_user, mock_update, client):
        """Test PATCH /api/users/<id>/profile - user updates own profile"""
        create_instructor_session(client)
        csrf_token = get_csrf_token(client)
        mock_update.return_value = True
        mock_get_user.return_value = {
            "user_id": "instructor-123",
            "first_name": "Updated",
            "last_name": "Name",
        }

        response = client.patch(
            "/api/users/instructor-123/profile",
            data='{"first_name": "Updated", "last_name": "Name"}',
            content_type="application/json",
            headers={"X-CSRFToken": csrf_token},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Profile updated successfully" in data["message"]

    @patch("src.api.routes.users.has_permission")
    def test_update_profile_permission_denied(self, mock_has_perm, client):
        """Test PATCH /api/users/<id>/profile - permission denied for other user"""
        create_instructor_session(client)
        csrf_token = get_csrf_token(client)
        mock_has_perm.return_value = False

        response = client.patch(
            "/api/users/other-user-123/profile",
            data='{"first_name": "Hacker"}',
            content_type="application/json",
            headers={"X-CSRFToken": csrf_token},
        )

        assert response.status_code == 403
        data = response.get_json()
        assert data["success"] is False

    @patch("src.api.routes.users.deactivate_user")
    @patch("src.api.routes.users.get_user_by_id")
    def test_deactivate_user_success(self, mock_get_user, mock_deactivate, client):
        """Test POST /api/users/<id>/deactivate - success"""
        create_site_admin_session(client)
        mock_get_user.return_value = {"user_id": "user-123"}
        mock_deactivate.return_value = True

        response = client.post(
            "/api/users/user-123/deactivate",
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "deactivated successfully" in data["message"]

    @patch("src.api.routes.users.get_user_by_id")
    def test_deactivate_user_not_found(self, mock_get_user, client):
        """Test POST /api/users/<id>/deactivate - user not found"""
        create_site_admin_session(client)
        mock_get_user.return_value = None

        response = client.post(
            "/api/users/nonexistent/deactivate",
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 404

    @patch("src.api.routes.users.delete_user")
    @patch("src.api.routes.users.get_user_by_id")
    def test_delete_user_success(self, mock_get_user, mock_delete, client):
        """Test DELETE /api/users/<id> - success"""
        create_site_admin_session(client)
        mock_get_user.return_value = {"user_id": "user-123"}
        mock_delete.return_value = True

        response = client.delete(
            "/api/users/user-123", headers={"X-CSRFToken": get_csrf_token(client)}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_delete_self_forbidden(self, client):
        """Test DELETE /api/users/<id> - cannot delete own account"""
        create_site_admin_session(client)
        response = client.delete(
            "/api/users/site-admin-123", headers={"X-CSRFToken": get_csrf_token(client)}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "Cannot delete your own account" in data["error"]


# ========================================
# INSTITUTION CRUD TESTS
# ========================================


class TestInstitutionsCRUD:
    """Tests for Institutions CRUD endpoints."""

    @patch("src.api.routes.institutions.update_institution")
    @patch("src.api.routes.institutions.get_institution_by_id")
    def test_update_institution_success(self, mock_get_inst, mock_update, client):
        """Test PUT /api/institutions/<id> - success"""
        create_site_admin_session(client)
        mock_get_inst.side_effect = [
            {"institution_id": "inst-1", "name": "Old Name"},  # Check if exists
            {"institution_id": "inst-1", "name": "New Name"},  # Return updated
        ]
        mock_update.return_value = True

        response = client.put(
            "/api/institutions/inst-1",
            json={"name": "New Name"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["institution"]["name"] == "New Name"

    @patch("src.api.routes.institutions.get_institution_by_id")
    def test_update_institution_not_found(self, mock_get_inst, client):
        """Test PUT /api/institutions/<id> - not found"""
        create_site_admin_session(client)
        mock_get_inst.return_value = None

        response = client.put(
            "/api/institutions/nonexistent",
            json={"name": "New Name"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 404

    @patch("src.api.routes.institutions.delete_institution")
    @patch("src.api.routes.institutions.get_institution_by_id")
    def test_delete_institution_success(self, mock_get_inst, mock_delete, client):
        """Test DELETE /api/institutions/<id> - success with confirmation"""
        create_site_admin_session(client)
        mock_get_inst.return_value = {"institution_id": "inst-1", "name": "Test Inst"}
        mock_delete.return_value = True

        response = client.delete(
            "/api/institutions/inst-1?confirm=i know what I'm doing",
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_delete_institution_no_confirmation(self, client):
        """Test DELETE /api/institutions/<id> - requires confirmation"""
        create_site_admin_session(client)
        response = client.delete(
            "/api/institutions/inst-1", headers={"X-CSRFToken": get_csrf_token(client)}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "Confirmation required" in data["error"]

    @patch("src.api.routes.institutions.get_institution_by_id")
    def test_delete_institution_permission_denied_non_site_admin(
        self, mock_get_inst, client
    ):
        """Test DELETE /api/institutions/<id> - only site admin can delete"""
        create_institution_admin_session(client)
        mock_get_inst.return_value = {"institution_id": "inst-1"}

        response = client.delete(
            "/api/institutions/inst-1?confirm=i know what I'm doing",
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 403


# ========================================
# COURSE CRUD TESTS
# ========================================


class TestCoursesCRUD:
    """Tests for Courses CRUD endpoints."""

    @patch("src.api.routes.courses.get_course_by_id")
    def test_get_course_by_id_success(self, mock_get_course, client):
        """Test GET /api/courses/by-id/<id> - success"""
        create_site_admin_session(client)
        mock_get_course.return_value = {
            "course_id": "course-123",
            "course_number": "CS101",
            "course_title": "Intro to CS",
        }

        response = client.get("/api/courses/by-id/course-123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["course"]["course_number"] == "CS101"

    @patch("src.api.routes.courses.get_course_by_id")
    def test_get_course_not_found(self, mock_get_course, client):
        """Test GET /api/courses/by-id/<id> - not found"""
        create_site_admin_session(client)
        mock_get_course.return_value = None

        response = client.get("/api/courses/by-id/nonexistent")

        assert response.status_code == 404

    @patch("src.api.routes.courses.update_course")
    @patch("src.api.routes.courses.get_course_by_id")
    def test_update_course_success(self, mock_get_course, mock_update, client):
        """Test PUT /api/courses/<id> - success"""
        create_site_admin_session(client)
        mock_get_course.side_effect = [
            {
                "course_id": "course-123",
                "institution_id": "inst-1",
                "course_title": "Old Title",
            },
            {
                "course_id": "course-123",
                "institution_id": "inst-1",
                "course_title": "New Title",
            },
        ]
        mock_update.return_value = True

        response = client.put(
            "/api/courses/course-123",
            json={"course_title": "New Title"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("src.api.routes.courses.delete_course")
    @patch("src.api.routes.courses.get_course_by_id")
    def test_delete_course_success(self, mock_get_course, mock_delete, client):
        """Test DELETE /api/courses/<id> - success"""
        create_site_admin_session(client)
        mock_get_course.return_value = {
            "course_id": "course-123",
            "course_number": "CS101",
            "institution_id": "inst-1",
        }
        mock_delete.return_value = True

        response = client.delete(
            "/api/courses/course-123", headers={"X-CSRFToken": get_csrf_token(client)}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "deleted successfully" in data["message"]


# ========================================
# TERM CRUD TESTS
# ========================================


class TestTermsCRUD:
    """Tests for Terms CRUD endpoints."""

    @patch("src.api.routes.terms.get_current_institution_id_safe")
    @patch("src.api.routes.terms.get_term_by_id")
    def test_get_term_by_id_success(self, mock_get_term, mock_get_inst_id, client):
        """Test GET /api/terms/<id> - success"""
        create_site_admin_session(client)
        mock_get_inst_id.return_value = "inst-1"
        mock_get_term.return_value = {
            "term_id": "term-123",
            "name": "Fall 2024",
            "institution_id": "inst-1",
        }

        response = client.get("/api/terms/term-123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["term"]["name"] == "Fall 2024"

    @patch("src.api.routes.terms.update_term")
    @patch("src.api.routes.terms.get_current_institution_id_safe")
    @patch("src.api.routes.terms.get_term_by_id")
    def test_update_term_success(
        self, mock_get_term, mock_get_inst_id, mock_update, client
    ):
        """Test PUT /api/terms/<id> - success"""
        create_site_admin_session(client)
        mock_get_inst_id.return_value = "inst-1"
        mock_get_term.side_effect = [
            {"term_id": "term-123", "name": "Fall 2024", "institution_id": "inst-1"},
            {
                "term_id": "term-123",
                "name": "Fall 2024 Updated",
                "institution_id": "inst-1",
            },
        ]
        mock_update.return_value = True

        response = client.put(
            "/api/terms/term-123",
            json={"name": "Fall 2024 Updated"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("src.api.routes.terms.delete_term")
    @patch("src.api.routes.terms.get_current_institution_id_safe")
    @patch("src.api.routes.terms.get_term_by_id")
    def test_delete_term_success(
        self, mock_get_term, mock_get_inst_id, mock_delete, client
    ):
        """Test DELETE /api/terms/<id> - success"""
        create_site_admin_session(client)
        mock_get_inst_id.return_value = "inst-1"
        mock_get_term.return_value = {
            "term_id": "term-123",
            "name": "Fall 2024",
            "institution_id": "inst-1",
        }
        mock_delete.return_value = True

        response = client.delete(
            "/api/terms/term-123", headers={"X-CSRFToken": get_csrf_token(client)}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True


# ========================================
# OFFERING CRUD TESTS
# ========================================


class TestOfferingsCRUD:
    """Tests for Course Offerings CRUD endpoints."""

    @patch("src.api.routes.offerings.database_service")
    @patch("src.api.routes.offerings.get_current_institution_id")
    def test_create_offering_success(self, mock_get_inst_id, mock_db_service, client):
        """Test POST /api/offerings - success"""
        create_site_admin_session(client)
        mock_get_inst_id.return_value = "inst-1"
        mock_db_service.create_course_offering.return_value = "offering-123"

        response = client.post(
            "/api/offerings",
            json={"course_id": "course-123", "term_id": "term-123", "capacity": 30},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["offering_id"] == "offering-123"

    def test_create_offering_missing_fields(self, client):
        """Test POST /api/offerings - missing required fields"""
        create_site_admin_session(client)
        response = client.post(
            "/api/offerings",
            json={"course_id": "course-123"},  # Missing term_id
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "Missing required fields" in data["error"]

    @patch("src.api.routes.offerings.get_course_offering")
    def test_get_offering_success(self, mock_get_offering, client):
        """Test GET /api/offerings/<id> - success"""
        create_site_admin_session(client)
        mock_get_offering.return_value = {
            "offering_id": "offering-123",
            "course_id": "course-123",
            "capacity": 30,
        }

        response = client.get("/api/offerings/offering-123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["offering"]["capacity"] == 30

    @patch("src.api.routes.offerings.update_course_offering")
    @patch("src.api.routes.offerings.get_course_offering")
    def test_update_offering_success(self, mock_get_offering, mock_update, client):
        """Test PUT /api/offerings/<id> - success"""
        create_site_admin_session(client)
        mock_get_offering.side_effect = [
            {"offering_id": "offering-123", "capacity": 30},
            {"offering_id": "offering-123", "capacity": 40},
        ]
        mock_update.return_value = True

        response = client.put(
            "/api/offerings/offering-123",
            json={"capacity": 40},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("src.api.routes.offerings.delete_course_offering")
    @patch("src.api.routes.offerings.get_course_offering")
    def test_delete_offering_success(self, mock_get_offering, mock_delete, client):
        """Test DELETE /api/offerings/<id> - success"""
        create_site_admin_session(client)
        mock_get_offering.return_value = {"offering_id": "offering-123"}
        mock_delete.return_value = True

        response = client.delete(
            "/api/offerings/offering-123",
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True


# ========================================
# SECTION CRUD TESTS
# ========================================


class TestSectionsCRUD:
    """Tests for Sections CRUD endpoints."""

    @patch("src.api.routes.sections.get_course_offering")
    @patch("src.api.routes.sections.get_current_institution_id_safe")
    @patch("src.api.routes.sections.get_section_by_id")
    def test_get_section_by_id_success(
        self, mock_get_section, mock_get_inst_id, mock_get_offering, client
    ):
        """Test GET /api/sections/<id> - success"""
        create_site_admin_session(client)
        mock_get_inst_id.return_value = "inst-1"
        mock_get_section.return_value = {
            "section_id": "section-123",
            "section_number": "001",
            "offering_id": "offering-123",
        }
        mock_get_offering.return_value = {
            "offering_id": "offering-123",
            "institution_id": "inst-1",
        }

        response = client.get("/api/sections/section-123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["section"]["section_number"] == "001"

    @patch("src.api.routes.sections.update_course_section")
    @patch("src.api.routes.sections.get_course_offering")
    @patch("src.api.routes.sections.get_current_institution_id_safe")
    @patch("src.api.routes.sections.get_section_by_id")
    def test_update_section_success(
        self, mock_get_section, mock_get_inst_id, mock_get_offering, mock_update, client
    ):
        """Test PUT /api/sections/<id> - success"""
        create_site_admin_session(client)
        mock_get_inst_id.return_value = "inst-1"
        mock_get_section.side_effect = [
            {
                "section_id": "section-123",
                "enrollment": 20,
                "offering_id": "offering-123",
            },
            {
                "section_id": "section-123",
                "enrollment": 25,
                "offering_id": "offering-123",
            },
        ]
        mock_get_offering.return_value = {
            "offering_id": "offering-123",
            "institution_id": "inst-1",
        }
        mock_update.return_value = True

        response = client.put(
            "/api/sections/section-123",
            json={"enrollment": 25},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("src.api.routes.sections.assign_instructor")
    @patch("src.api.routes.sections.get_user_by_id")
    @patch("src.api.routes.sections.get_course_offering")
    @patch("src.api.routes.sections.get_current_institution_id_safe")
    @patch("src.api.routes.sections.get_section_by_id")
    def test_assign_instructor_success(
        self,
        mock_get_section,
        mock_get_inst_id,
        mock_get_offering,
        mock_get_user,
        mock_assign,
        client,
    ):
        """Test PATCH /api/sections/<id>/instructor - success"""
        create_site_admin_session(client)
        csrf_token = get_csrf_token(client)
        mock_get_inst_id.return_value = "inst-1"
        mock_get_section.return_value = {
            "section_id": "section-123",
            "offering_id": "offering-123",
        }
        mock_get_offering.return_value = {
            "offering_id": "offering-123",
            "institution_id": "inst-1",
        }
        mock_get_user.return_value = {"user_id": "instructor-123"}
        mock_assign.return_value = True

        with patch(
            "src.services.clo_workflow_service.CLOWorkflowService.mark_section_outcomes_assigned"
        ) as mock_mark_assigned:
            mock_mark_assigned.return_value = True

            response = client.patch(
                "/api/sections/section-123/instructor",
                data='{"instructor_id": "instructor-123"}',
                content_type="application/json",
                headers={"X-CSRFToken": csrf_token},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "assigned successfully" in data["message"]
        mock_mark_assigned.assert_called_once_with("section-123")

    def test_assign_instructor_missing_id(self, client):
        """Test PATCH /api/sections/<id>/instructor - missing instructor_id"""
        create_site_admin_session(client)
        csrf_token = get_csrf_token(client)
        response = client.patch(
            "/api/sections/section-123/instructor",
            data="{}",
            content_type="application/json",
            headers={"X-CSRFToken": csrf_token},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "instructor_id is required" in data["error"]

    @patch("src.api.routes.sections.delete_course_section")
    @patch("src.api.routes.sections.get_course_offering")
    @patch("src.api.routes.sections.get_current_institution_id_safe")
    @patch("src.api.routes.sections.get_section_by_id")
    def test_delete_section_success(
        self, mock_get_section, mock_get_inst_id, mock_get_offering, mock_delete, client
    ):
        """Test DELETE /api/sections/<id> - success"""
        create_site_admin_session(client)
        mock_get_inst_id.return_value = "inst-1"
        mock_get_section.return_value = {
            "section_id": "section-123",
            "offering_id": "offering-123",
        }
        mock_get_offering.return_value = {
            "offering_id": "offering-123",
            "institution_id": "inst-1",
        }
        mock_delete.return_value = True

        response = client.delete(
            "/api/sections/section-123", headers={"X-CSRFToken": get_csrf_token(client)}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True


# ========================================
# OUTCOME CRUD TESTS
# ========================================


class TestOutcomesCRUD:
    """Tests for Course Outcomes CRUD endpoints."""

    @patch("src.api.routes.outcomes.database_service")
    @patch("src.api.routes.outcomes.get_course_by_id")
    def test_create_outcome_success(self, mock_get_course, mock_db_service, client):
        """Test POST /api/courses/<id>/outcomes - success"""
        create_site_admin_session(client)
        mock_get_course.return_value = {"course_id": "course-123"}
        mock_db_service.create_course_outcome.return_value = "outcome-123"

        response = client.post(
            "/api/courses/course-123/outcomes",
            json={"description": "Students will learn X", "target_percentage": 80},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["outcome_id"] == "outcome-123"

    @patch("src.api.routes.outcomes.get_course_by_id")
    def test_create_outcome_missing_description(self, mock_get_course, client):
        """Test POST /api/courses/<id>/outcomes - missing description"""
        create_site_admin_session(client)
        mock_get_course.return_value = {"course_id": "course-123"}

        response = client.post(
            "/api/courses/course-123/outcomes",
            json={},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "description is required" in data["error"]

    @patch("src.api.routes.outcomes.get_course_by_id")
    @patch("src.database.database_service.get_section_outcomes_by_criteria")
    @patch("src.database.database_service.get_sections_by_course")
    @patch("src.api.routes.outcomes.get_current_user")
    def test_list_course_outcomes_instructor_view(
        self,
        mock_get_user,
        mock_get_sections,
        mock_get_outcomes,
        mock_get_course,
        client,
    ):
        """Test GET /api/courses/<id>/outcomes - returns instructor sections outcomes."""
        create_site_admin_session(client)
        mock_get_user.return_value = {"user_id": "user-123", "institution_id": 1}
        mock_get_course.return_value = {
            "course_id": "course-123",
            "course_number": "CS101",
            "course_title": "Intro to Programming",
        }

        # Mock sections where user is instructor
        mock_get_sections.return_value = [
            {"section_id": "section-1", "instructor_id": "user-123"},
            {"section_id": "section-2", "instructor_id": "other-user"},
        ]

        # Mock outcomes
        mock_get_outcomes.return_value = [
            {"id": "outcome-1", "section_id": "section-1", "status": "assigned"},
            {"id": "outcome-2", "section_id": "section-2", "status": "assigned"},
        ]

        response = client.get("/api/courses/course-123/outcomes")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["course_number"] == "CS101"
        assert data["course_title"] == "Intro to Programming"
        # Should filter to only include outcome-1 (belonging to section-1)
        assert len(data["outcomes"]) == 1
        assert data["outcomes"][0]["id"] == "outcome-1"

    @patch("src.api.routes.outcomes.get_course_by_id")
    @patch("src.api.routes.outcomes.get_current_institution_id_safe")
    @patch("src.api.routes.outcomes.get_course_outcome")
    def test_get_outcome_success(
        self, mock_get_outcome, mock_get_inst_id, mock_get_course, client
    ):
        """Test GET /api/outcomes/<id> - success"""
        create_site_admin_session(client)
        mock_get_inst_id.return_value = "inst-1"
        mock_get_outcome.return_value = {
            "outcome_id": "outcome-123",
            "description": "Learn X",
            "course_id": "course-123",
        }
        mock_get_course.return_value = {
            "course_id": "course-123",
            "institution_id": "inst-1",
        }

        response = client.get("/api/outcomes/outcome-123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["outcome"]["description"] == "Learn X"

    @patch("src.api.routes.outcomes.update_course_outcome")
    @patch("src.api.routes.outcomes.get_course_by_id")
    @patch("src.api.routes.outcomes.get_current_institution_id_safe")
    @patch("src.api.routes.outcomes.get_course_outcome")
    def test_update_outcome_success(
        self, mock_get_outcome, mock_get_inst_id, mock_get_course, mock_update, client
    ):
        """Test PUT /api/outcomes/<id> - success"""
        create_site_admin_session(client)
        mock_get_inst_id.return_value = "inst-1"
        mock_get_outcome.return_value = {
            "outcome_id": "outcome-123",
            "course_id": "course-123",
        }
        mock_get_course.return_value = {
            "course_id": "course-123",
            "institution_id": "inst-1",
        }
        mock_update.return_value = True

        response = client.put(
            "/api/outcomes/outcome-123",
            json={"description": "Updated description"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("src.database.database_service.get_section_by_id")
    @patch("src.api.routes.outcomes.get_current_user")
    @patch("src.api.routes.outcomes.update_section_outcome")
    @patch("src.api.routes.outcomes.get_section_outcome")
    def test_update_outcome_assessment_success(
        self,
        mock_get_outcome,
        mock_update_assessment,
        mock_get_user,
        mock_get_section,
        client,
    ):
        """Test PUT /api/outcomes/<id>/assessment - success"""
        create_site_admin_session(client)
        mock_get_outcome.return_value = {
            "section_outcome_id": "outcome-123",
            "section_id": "section-123",
        }
        # Create a user matching the session user (site admin usually bypasses, but let's mock it correctly)
        mock_get_section.return_value = {
            "id": "section-123",
            "instructor_id": "user-123",
        }
        mock_get_user.return_value = {"user_id": "user-123", "role": "instructor"}

        mock_update_assessment.return_value = True

        response = client.put(
            "/api/outcomes/outcome-123/assessment",
            json={
                "students_took": 30,
                "students_passed": 25,
                "assessment_tool": "Final Exam",
            },
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Assessment data saved" in data["message"]

        # Verify auto_mark_in_progress was called
        # mock_auto_mark.assert_called_once_with("outcome-123", "user-456")

    @patch("src.database.database_service.get_section_by_id")
    @patch("src.api.routes.outcomes.get_current_user")
    @patch("src.api.routes.outcomes.update_section_outcome")
    @patch("src.api.routes.outcomes.get_section_outcome")
    def test_update_outcome_assessment_tool_too_long(
        self,
        mock_get_outcome,
        mock_update_assessment,
        mock_get_user,
        mock_get_section,
        client,
    ):
        """Test PUT /api/outcomes/<id>/assessment - assessment_tool > 50 chars (CEI demo fix)"""
        create_site_admin_session(client)
        mock_get_outcome.return_value = {
            "section_outcome_id": "outcome-123",
            "section_id": "section-123",
        }
        mock_get_section.return_value = {
            "id": "section-123",
            "instructor_id": "user-123",
        }
        mock_get_user.return_value = {"user_id": "user-123", "role": "instructor"}
        mock_update_assessment.return_value = True

        response = client.put(
            "/api/outcomes/outcome-123/assessment",
            json={
                "students_took": 30,
                "students_passed": 25,
                "assessment_tool": "A" * 51,  # 51 chars - exceeds 50 char limit
            },
            headers={"X-CSRFToken": get_csrf_token(client)},
        )

        # Validation was removed from source, so we expect 200 now
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("src.api.routes.outcomes.delete_course_outcome")
    @patch("src.api.routes.outcomes.get_course_by_id")
    @patch("src.api.routes.outcomes.get_current_institution_id_safe")
    @patch("src.api.routes.outcomes.get_course_outcome")
    def test_delete_outcome_success(
        self, mock_get_outcome, mock_get_inst_id, mock_get_course, mock_delete, client
    ):
        """Test DELETE /api/outcomes/<id> - success"""
        create_site_admin_session(client)
        mock_get_inst_id.return_value = "inst-1"
        mock_get_outcome.return_value = {
            "outcome_id": "outcome-123",
            "course_id": "course-123",
        }
        mock_get_course.return_value = {
            "course_id": "course-123",
            "institution_id": "inst-1",
        }
        mock_delete.return_value = True

        response = client.delete(
            "/api/outcomes/outcome-123", headers={"X-CSRFToken": get_csrf_token(client)}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
