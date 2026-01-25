"""
Tests for Story 5.6: Program Context Management functionality

This module tests the program context switching, validation, and management
features implemented in auth_service.py and the institutions API routes.
"""

from unittest.mock import patch

import pytest
from flask import Flask

from src.app import app
from tests.test_utils import create_test_session


def _login_test_user(client, overrides=None):
    """Populate test client session with authenticated user data"""
    user_data = {
        "user_id": "test-admin",
        "email": "admin@test.edu",
        "role": "site_admin",
        "institution_id": "inst-123",
        "program_ids": ["prog-123"],
        "display_name": "Test Admin",
    }
    if overrides:
        user_data.update(overrides)

    create_test_session(client, user_data)
    return user_data


from src.services.auth_service import (
    clear_current_program_id,
    get_current_program_id,
    set_current_program_id,
)


class TestProgramContextUtilities:
    """Test program context utility functions"""

    def test_get_current_program_id_no_user(self):
        """Test get_current_program_id when no user is logged in"""
        with patch("src.services.auth_service.get_current_user", return_value=None):
            result = get_current_program_id()
            assert result is None

    def test_get_current_program_id_no_context(self):
        """Test get_current_program_id when user has no program context"""
        mock_user = {
            "user_id": "test-user",
            "role": "program_admin",
            "program_ids": ["prog-123", "prog-456"],
        }
        with patch(
            "src.services.auth_service.get_current_user", return_value=mock_user
        ):
            result = get_current_program_id()
            assert result is None

    def test_get_current_program_id_with_context(self):
        """Test get_current_program_id when user has active program context"""
        mock_user = {
            "user_id": "test-user",
            "role": "program_admin",
            "program_ids": ["prog-123", "prog-456"],
            "current_program_id": "prog-123",
        }
        with patch(
            "src.services.auth_service.get_current_user", return_value=mock_user
        ):
            result = get_current_program_id()
            assert result == "prog-123"

    def test_set_current_program_id_no_user(self):
        """Test set_current_program_id when no user is logged in"""
        with patch("src.services.auth_service.get_current_user", return_value=None):
            result = set_current_program_id("prog-123")
            assert result is False

    @patch("src.services.auth_service.session", {})
    def test_set_current_program_id_unauthorized_program(self):
        """Test set_current_program_id with unauthorized program"""
        mock_user = {
            "user_id": "test-user",
            "role": "program_admin",
            "program_ids": ["prog-123", "prog-456"],
        }
        with patch(
            "src.services.auth_service.get_current_user", return_value=mock_user
        ):
            result = set_current_program_id("prog-999")  # Not in accessible list
            assert result is False

    def test_set_current_program_id_success(self):
        """Test successful program context switching"""
        test_app = Flask(__name__)
        test_app.config["SECRET_KEY"] = "test-secret"

        mock_user = {
            "user_id": "test-user",
            "role": "program_admin",
            "program_ids": ["prog-123", "prog-456"],
        }

        with test_app.test_request_context():
            with patch(
                "src.services.auth_service.get_current_user", return_value=mock_user
            ):
                result = set_current_program_id("prog-123")
                assert result is True

    def test_clear_current_program_id_no_user(self):
        """Test clear_current_program_id when no user is logged in"""
        with patch("src.services.auth_service.get_current_user", return_value=None):
            result = clear_current_program_id()
            assert result is False

    def test_clear_current_program_id_success(self):
        """Test successful program context clearing"""
        test_app = Flask(__name__)
        test_app.config["SECRET_KEY"] = "test-secret"

        mock_user = {"user_id": "test-user", "role": "program_admin"}

        with test_app.test_request_context():
            # Set up session with current program
            from flask import session

            session["current_program_id"] = "prog-123"

            with patch(
                "src.services.auth_service.get_current_user", return_value=mock_user
            ):
                result = clear_current_program_id()
                assert result is True


class TestProgramContextAPI:
    """Test program context management API endpoints"""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()

    def test_get_program_context_success(self):
        """Test GET /api/context/program success"""
        mock_user = {
            "user_id": "test-user",
            "role": "program_admin",
            "institution_id": "inst-123",
            "program_ids": ["prog-123", "prog-456"],
        }
        mock_programs = [
            {"id": "prog-123", "name": "Computer Science"},
            {"id": "prog-456", "name": "Mathematics"},
        ]

        with (
            patch(
                "src.api.routes.institutions.get_current_user", return_value=mock_user
            ),
            patch(
                "src.api.routes.institutions.get_current_program_id",
                return_value="prog-123",
            ),
            patch(
                "src.api.routes.institutions.get_program_by_id"
            ) as mock_get_program,
            patch(
                "src.services.auth_service.get_current_user", return_value=mock_user
            ),
            patch("src.services.auth_service.has_permission", return_value=True),
        ):

            mock_get_program.side_effect = lambda pid: next(
                (p for p in mock_programs if p["id"] == pid), None
            )

            _login_test_user(self.client, mock_user)

            response = self.client.get("/api/context/program")
            assert response.status_code == 200

            data = response.get_json()
            assert data["success"] is True
            assert data["current_program_id"] == "prog-123"
            assert len(data["program_ids"]) == 2
            assert data["has_multiple_programs"] is True

    def test_switch_program_context_success(self):
        """Test POST /api/context/program/<program_id> success"""
        mock_user = {
            "user_id": "test-user",
            "role": "program_admin",
            "institution_id": "inst-123",
            "program_ids": ["prog-123", "prog-456"],
        }
        mock_program = {"id": "prog-123", "name": "Computer Science"}

        with (
            patch(
                "src.api.routes.institutions.get_current_user", return_value=mock_user
            ),
            patch(
                "src.api.routes.institutions.get_program_by_id",
                return_value=mock_program,
            ),
            patch(
                "src.api.routes.institutions.set_current_program_id", return_value=True
            ),
            patch(
                "src.services.auth_service.get_current_user", return_value=mock_user
            ),
            patch("src.services.auth_service.has_permission", return_value=True),
        ):

            _login_test_user(self.client, mock_user)

            response = self.client.post("/api/context/program/prog-123")
            assert response.status_code == 200

            data = response.get_json()
            assert data["success"] is True
            assert data["current_program_id"] == "prog-123"
            assert "program" in data

    def test_switch_program_context_unauthorized(self):
        """Test POST /api/context/program/<program_id> with unauthorized program"""
        mock_user = {
            "user_id": "test-user",
            "role": "program_admin",
            "institution_id": "inst-123",
            "program_ids": ["prog-123", "prog-456"],
        }

        with (
            patch(
                "src.api.routes.institutions.get_current_user", return_value=mock_user
            ),
            patch(
                "src.services.auth_service.get_current_user", return_value=mock_user
            ),
            patch("src.services.auth_service.has_permission", return_value=True),
        ):
            _login_test_user(self.client, mock_user)

            response = self.client.post("/api/context/program/prog-999")
            assert response.status_code == 403

            data = response.get_json()
            assert data["success"] is False
            assert "Access denied" in data["error"]

    def test_clear_program_context_success(self):
        """Test DELETE /api/context/program success"""
        mock_user = {"user_id": "test", "role": "site_admin"}

        with (
            patch(
                "src.api.routes.institutions.clear_current_program_id", return_value=True
            ),
            patch(
                "src.services.auth_service.get_current_user", return_value=mock_user
            ),
            patch("src.services.auth_service.has_permission", return_value=True),
        ):
            _login_test_user(self.client, mock_user)

            response = self.client.delete("/api/context/program")
            assert response.status_code == 200

            data = response.get_json()
            assert data["success"] is True
            assert data["current_program_id"] is None


class TestUnassignedCoursesAPI:
    """Test unassigned courses management API endpoints"""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()

    def test_list_unassigned_courses_success(self):
        """Test GET /api/courses/unassigned success"""
        mock_courses = [
            {"id": "course-1", "name": "Unassigned Course 1", "program_ids": []},
            {"id": "course-2", "name": "Unassigned Course 2", "program_ids": []},
        ]
        mock_user = {"user_id": "test", "role": "site_admin", "institution_id": "inst-123"}

        with (
            patch(
                "src.api.routes.courses.get_current_institution_id",
                return_value="inst-123",
            ),
            patch(
                "src.api.routes.courses.get_unassigned_courses",
                return_value=mock_courses,
            ),
            patch(
                "src.services.auth_service.get_current_user", return_value=mock_user
            ),
            patch("src.services.auth_service.has_permission", return_value=True),
        ):
            _login_test_user(self.client, mock_user)

            response = self.client.get("/api/courses/unassigned")
            assert response.status_code == 200

            data = response.get_json()
            assert data["success"] is True
            assert data["count"] == 2
            assert len(data["courses"]) == 2

    def test_assign_course_to_default_success(self):
        """Test POST /api/courses/<course_id>/assign-default success"""
        mock_user = {"user_id": "test", "role": "site_admin", "institution_id": "inst-123"}

        with (
            patch(
                "src.api.routes.courses.get_current_institution_id",
                return_value="inst-123",
            ),
            patch(
                "src.api.routes.courses.assign_course_to_default_program",
                return_value=True,
            ),
            patch(
                "src.services.auth_service.get_current_user", return_value=mock_user
            ),
            patch("src.services.auth_service.has_permission", return_value=True),
        ):
            _login_test_user(self.client, mock_user)

            response = self.client.post("/api/courses/course-123/assign-default")
            assert response.status_code == 200

            data = response.get_json()
            assert data["success"] is True
            assert "assigned" in data["message"].lower()


class TestContextValidationMiddleware:
    """Test context validation middleware functionality"""

    @pytest.mark.skip(reason="validate_context no longer exists in the new API structure")
    def test_context_validation_skips_auth_endpoints(self):
        """Test that context validation skips auth endpoints"""
        pass

    @pytest.mark.skip(reason="validate_context no longer exists in the new API structure")
    def test_context_validation_skips_context_endpoints(self):
        """Test that context validation skips context management endpoints"""
        pass

    @pytest.mark.skip(reason="validate_context no longer exists in the new API structure")
    def test_context_validation_allows_site_admin(self):
        """Test that context validation allows site admin without institution context"""
        pass

    @pytest.mark.skip(reason="validate_context no longer exists in the new API structure")
    def test_context_validation_logs_missing_institution(self):
        """Test that context validation logs when institution context is missing"""
        pass
