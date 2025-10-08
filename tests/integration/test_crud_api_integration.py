"""
Integration tests for CRUD API endpoints

Tests the complete CRUD workflows for all entities including:
- Users: profile updates, role changes, deactivation, deletion
- Institutions: updates, CASCADE deletion
- Courses: updates, program associations, CASCADE deletion
- Terms: updates, archiving, deletion
- Offerings: CRUD operations with term/course relationships
- Sections: CRUD operations with instructor assignment
- Outcomes: CRUD operations with assessment tracking
"""

from unittest.mock import patch

import pytest

from app import app
from tests.test_utils import CommonAuthMixin


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


class TestUsersCRUDIntegration(CommonAuthMixin):
    """Integration tests for Users CRUD endpoints"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self._login_site_admin()

    @patch("database_service.get_user_by_id")
    def test_get_user_by_id_integration(self, mock_get_user):
        """Test GET /api/users/<id> full integration"""
        mock_get_user.return_value = {
            "user_id": "user-123",
            "email": "instructor@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "instructor",
            "institution_id": "inst-1",
        }

        with patch("api_routes.login_required", lambda f: f):
            response = self.client.get("/api/users/user-123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["user"]["email"] == "instructor@example.com"
        assert data["user"]["role"] == "instructor"

    @patch("database_service.update_user_profile")
    @patch("database_service.get_user_by_id")
    def test_update_profile_integration(self, mock_get_user, mock_update):
        """Test PATCH /api/users/<id>/profile full integration"""
        mock_update.return_value = True
        mock_get_user.return_value = {
            "user_id": "user-123",
            "first_name": "Jane",
            "last_name": "Smith",
        }

        profile_data = {"first_name": "Jane", "last_name": "Smith"}

        with patch("api_routes.login_required", lambda f: f):
            response = self.client.patch(
                "/api/users/user-123/profile",
                json=profile_data,
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["user"]["first_name"] == "Jane"

    @patch("database_service.deactivate_user")
    def test_deactivate_user_integration(self, mock_deactivate):
        """Test POST /api/users/<id>/deactivate full integration"""
        mock_deactivate.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.post(
                "/api/users/user-123/deactivate",
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "suspended" in data["message"].lower()

    @patch("database_service.delete_user")
    def test_delete_user_integration(self, mock_delete):
        """Test DELETE /api/users/<id> full integration"""
        mock_delete.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.delete(
                "/api/users/user-456",
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "deleted permanently" in data["message"].lower()


class TestInstitutionsCRUDIntegration(CommonAuthMixin):
    """Integration tests for Institutions CRUD endpoints"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self._login_site_admin()

    @patch("database_service.update_institution")
    def test_update_institution_integration(self, mock_update):
        """Test PUT /institutions/<id> full integration"""
        mock_update.return_value = True

        institution_data = {
            "name": "Updated Institution",
            "short_name": "UPD",
        }

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.put(
                "/api/institutions/inst-1",
                json=institution_data,
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "updated successfully" in data["message"].lower()

    @patch("database_service.delete_institution")
    def test_delete_institution_with_confirmation_integration(self, mock_delete):
        """Test DELETE /institutions/<id> with confirmation"""
        mock_delete.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.delete(
                "/api/institutions/inst-1?confirm=i%20know%20what%20I%27m%20doing",
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("database_service.delete_institution")
    def test_delete_institution_without_confirmation_fails(self, mock_delete):
        """Test DELETE /institutions/<id> requires confirmation"""
        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.delete(
                "/api/institutions/inst-1",
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "confirmation required" in data["error"].lower()


class TestCoursesCRUDIntegration(CommonAuthMixin):
    """Integration tests for Courses CRUD endpoints"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self._login_site_admin()

    @patch("database_service.get_course_by_id")
    def test_get_course_by_id_integration(self, mock_get_course):
        """Test GET /api/courses/by-id/<id> full integration"""
        mock_get_course.return_value = {
            "course_id": "course-123",
            "course_number": "CS101",
            "course_title": "Intro to Programming",
            "credit_hours": 3,
        }

        with patch("api_routes.login_required", lambda f: f):
            response = self.client.get("/api/courses/by-id/course-123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["course"]["course_number"] == "CS101"
        assert data["course"]["credit_hours"] == 3

    @patch("database_service.update_course")
    @patch("database_service.update_course_programs")
    def test_update_course_integration(self, mock_update_programs, mock_update):
        """Test PUT /api/courses/<id> full integration"""
        mock_update.return_value = True
        mock_update_programs.return_value = True

        course_data = {
            "course_title": "Advanced Programming",
            "credit_hours": 4,
            "program_ids": ["prog-1", "prog-2"],
        }

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.put(
                "/api/courses/course-123",
                json=course_data,
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        mock_update.assert_called_once()
        mock_update_programs.assert_called_once()

    @patch("database_service.delete_course")
    def test_delete_course_integration(self, mock_delete):
        """Test DELETE /api/courses/<id> CASCADE delete"""
        mock_delete.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.delete(
                "/api/courses/course-123",
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "deleted" in data["message"].lower()


class TestTermsCRUDIntegration(CommonAuthMixin):
    """Integration tests for Terms CRUD endpoints"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self._login_site_admin()

    @patch("database_service.update_term")
    def test_update_term_integration(self, mock_update):
        """Test PUT /api/terms/<id> full integration"""
        mock_update.return_value = True

        term_data = {"term_name": "SP2025"}

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.put(
                "/api/terms/term-123",
                json=term_data,
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("database_service.archive_term")
    def test_archive_term_integration(self, mock_archive):
        """Test POST /api/terms/<id>/archive soft delete"""
        mock_archive.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.post(
                "/api/terms/term-123/archive",
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "archived" in data["message"].lower()

    @patch("database_service.delete_term")
    def test_delete_term_integration(self, mock_delete):
        """Test DELETE /api/terms/<id> CASCADE delete"""
        mock_delete.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.delete(
                "/api/terms/term-123",
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "deleted" in data["message"].lower()


class TestOfferingsCRUDIntegration(CommonAuthMixin):
    """Integration tests for Course Offerings CRUD endpoints"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self._login_site_admin()

    @patch("database_service.create_course_offering")
    def test_create_offering_integration(self, mock_create):
        """Test POST /api/offerings create"""
        # Mock returns offering_id (as per database_service.create_course_offering signature)
        mock_create.return_value = "offering-123"

        offering_data = {
            "course_id": "course-123",
            "term_id": "term-123",
            "capacity": 30,
            "enrolled": 0,
        }

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.post(
                "/api/offerings",
                json=offering_data,
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["offering_id"] == "offering-123"

    @patch("database_service.get_course_offering")
    def test_get_offering_by_id_integration(self, mock_get):
        """Test GET /api/offerings/<id> retrieve"""
        mock_get.return_value = {
            "offering_id": "offering-123",
            "course_id": "course-123",
            "capacity": 30,
        }

        with patch("api_routes.login_required", lambda f: f):
            response = self.client.get("/api/offerings/offering-123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["offering"]["offering_id"] == "offering-123"

    @patch("database_service.update_course_offering")
    def test_update_offering_integration(self, mock_update):
        """Test PUT /api/offerings/<id> update"""
        mock_update.return_value = True

        offering_data = {"capacity": 35, "enrolled": 28}

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.put(
                "/api/offerings/offering-123",
                json=offering_data,
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("database_service.delete_course_offering")
    def test_delete_offering_integration(self, mock_delete):
        """Test DELETE /api/offerings/<id> CASCADE delete"""
        mock_delete.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.delete(
                "/api/offerings/offering-123",
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True


class TestSectionsCRUDIntegration(CommonAuthMixin):
    """Integration tests for Course Sections CRUD endpoints"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self._login_site_admin()

    @patch("database_service.update_course_section")
    def test_update_section_integration(self, mock_update):
        """Test PUT /api/sections/<id> update"""
        mock_update.return_value = True

        section_data = {"capacity": 30, "enrolled": 22}

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.put(
                "/api/sections/section-123",
                json=section_data,
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("database_service.assign_instructor")
    def test_assign_instructor_integration(self, mock_assign):
        """Test PATCH /api/sections/<id>/instructor assign instructor"""
        mock_assign.return_value = True

        instructor_data = {"instructor_id": "instructor-456"}

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.patch(
                "/api/sections/section-123/instructor",
                json=instructor_data,
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "assigned" in data["message"].lower()

    @patch("database_service.delete_course_section")
    def test_delete_section_integration(self, mock_delete):
        """Test DELETE /api/sections/<id> delete"""
        mock_delete.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.delete(
                "/api/sections/section-123",
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True


class TestOutcomesCRUDIntegration(CommonAuthMixin):
    """Integration tests for Course Outcomes CRUD endpoints"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self._login_site_admin()

    @patch("database_service.create_course_outcome")
    def test_create_outcome_integration(self, mock_create):
        """Test POST /api/courses/<id>/outcomes create"""
        mock_create.return_value = "outcome-123"

        outcome_data = {
            "description": "Students will understand OOP principles",
            "outcome_type": "CLO",
        }

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.post(
                "/api/courses/course-123/outcomes",
                json=outcome_data,
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["outcome_id"] == "outcome-123"

    @patch("database_service.update_course_outcome")
    def test_update_outcome_integration(self, mock_update):
        """Test PUT /api/outcomes/<id> update description"""
        mock_update.return_value = True

        outcome_data = {"description": "Updated outcome description"}

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.put(
                "/api/outcomes/outcome-123",
                json=outcome_data,
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("database_service.update_outcome_assessment")
    def test_update_outcome_assessment_integration(self, mock_update):
        """Test PUT /api/outcomes/<id>/assessment update assessment"""
        mock_update.return_value = True

        assessment_data = {
            "assessment_status": "completed",
            "assessment_data": {"score": 85, "method": "exam"},
        }

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.put(
                "/api/outcomes/outcome-123/assessment",
                json=assessment_data,
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("database_service.delete_course_outcome")
    def test_delete_outcome_integration(self, mock_delete):
        """Test DELETE /api/outcomes/<id> delete"""
        mock_delete.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.delete(
                "/api/outcomes/outcome-123",
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True


class TestCRUDWorkflows(CommonAuthMixin):
    """Test complete end-to-end CRUD workflows"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self._login_site_admin()

    @patch("database_service.create_course_offering")
    @patch("database_service.update_course_offering")
    @patch("database_service.delete_course_offering")
    def test_offering_complete_lifecycle(self, mock_delete, mock_update, mock_create):
        """Test complete offering lifecycle: create → update → delete"""
        # Create
        mock_create.return_value = "offering-123"
        offering_data = {
            "course_id": "course-123",
            "term_id": "term-123",
            "capacity": 30,
        }

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            create_response = self.client.post(
                "/api/offerings",
                json=offering_data,
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert create_response.status_code == 201
        offering_id = create_response.get_json()["offering_id"]

        # Update
        mock_update.return_value = True
        update_data = {"capacity": 35}

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            update_response = self.client.put(
                f"/api/offerings/{offering_id}",
                json=update_data,
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert update_response.status_code == 200

        # Delete
        mock_delete.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            delete_response = self.client.delete(
                f"/api/offerings/{offering_id}",
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert delete_response.status_code == 200

    @patch("database_service.update_course")
    @patch("database_service.delete_course")
    def test_course_update_and_cascade_delete(self, mock_delete, mock_update):
        """Test course update followed by CASCADE delete"""
        # Update course
        mock_update.return_value = True
        course_data = {"course_title": "Updated Title"}

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            update_response = self.client.put(
                "/api/courses/course-123",
                json=course_data,
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert update_response.status_code == 200

        # CASCADE delete (removes offerings, sections, outcomes)
        mock_delete.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            delete_response = self.client.delete(
                "/api/courses/course-123",
                headers={"X-CSRFToken": get_csrf_token(self.client)},
            )

        assert delete_response.status_code == 200
        data = delete_response.get_json()
        assert data["success"] is True
