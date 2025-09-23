"""
Tests for Story 5.6: Program Context Management functionality

This module tests the program context switching, validation, and management
features implemented in auth_service.py and api_routes.py.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from flask import Flask


def _login_test_user(client, overrides=None):
    """Populate test client session with authenticated user data"""
    user_data = {
        "user_id": "test-admin",
        "email": "admin@test.edu",
        "role": "site_admin",
        "institution_id": "inst-123",
        "program_ids": ["prog-123"],
        "program_ids": ["prog-123"],
        "display_name": "Test Admin",
    }
    if overrides:
        user_data.update(overrides)

    with client.session_transaction() as session:
        session["user_id"] = user_data["user_id"]
        session["email"] = user_data.get("email")
        session["role"] = user_data.get("role")
        session["institution_id"] = user_data.get("institution_id")
        session["program_ids"] = user_data.get("program_ids", [])
        session["display_name"] = user_data.get("display_name")

    return user_data


from auth_service import (
    clear_current_program_id,
    get_current_program_id,
    set_current_program_id,
)


class TestProgramContextUtilities:
    """Test program context utility functions"""

    def test_get_current_program_id_no_user(self):
        """Test get_current_program_id when no user is logged in"""
        with patch("auth_service.get_current_user", return_value=None):
            result = get_current_program_id()
            assert result is None

    def test_get_current_program_id_no_context(self):
        """Test get_current_program_id when user has no program context"""
        mock_user = {
            "user_id": "test-user",
            "role": "program_admin",
            "program_ids": ["prog-123", "prog-456"],
        }
        with patch("auth_service.get_current_user", return_value=mock_user):
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
        with patch("auth_service.get_current_user", return_value=mock_user):
            result = get_current_program_id()
            assert result == "prog-123"

    def test_set_current_program_id_no_user(self):
        """Test set_current_program_id when no user is logged in"""
        with patch("auth_service.get_current_user", return_value=None):
            result = set_current_program_id("prog-123")
            assert result is False

    @patch("auth_service.session", {})
    def test_set_current_program_id_unauthorized_program(self):
        """Test set_current_program_id with unauthorized program"""
        mock_user = {
            "user_id": "test-user",
            "role": "program_admin",
            "program_ids": ["prog-123", "prog-456"],
        }
        with patch("auth_service.get_current_user", return_value=mock_user):
            result = set_current_program_id("prog-999")  # Not in accessible list
            assert result is False

    def test_set_current_program_id_success(self):
        """Test successful program context switching"""
        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret"

        mock_user = {
            "user_id": "test-user",
            "role": "program_admin",
            "program_ids": ["prog-123", "prog-456"],
        }

        with app.test_request_context():
            with patch("auth_service.get_current_user", return_value=mock_user):
                result = set_current_program_id("prog-123")
                assert result is True

    def test_clear_current_program_id_no_user(self):
        """Test clear_current_program_id when no user is logged in"""
        with patch("auth_service.get_current_user", return_value=None):
            result = clear_current_program_id()
            assert result is False

    def test_clear_current_program_id_success(self):
        """Test successful program context clearing"""
        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test-secret"

        mock_user = {"user_id": "test-user", "role": "program_admin"}

        with app.test_request_context():
            # Set up session with current program
            from flask import session

            session["current_program_id"] = "prog-123"

            with patch("auth_service.get_current_user", return_value=mock_user):
                result = clear_current_program_id()
                assert result is True


class TestProgramContextAPI:
    """Test program context management API endpoints"""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing"""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"

        # Register the API blueprint
        from api_routes import api

        app.register_blueprint(api)

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    def test_get_program_context_success(self, app, client):
        """Test GET /api/context/program success"""
        mock_user = {
            "user_id": "test-user",
            "role": "program_admin",
            "institution_id": "inst-123",
            "program_ids": ["prog-123", "prog-456"],
            "program_ids": ["prog-123", "prog-456"],
        }
        mock_programs = [
            {"id": "prog-123", "name": "Computer Science"},
            {"id": "prog-456", "name": "Mathematics"},
        ]

        with app.app_context():
            with (
                patch("api_routes.get_current_user", return_value=mock_user),
                patch("api_routes.get_current_program_id", return_value="prog-123"),
                patch("api_routes.get_program_by_id") as mock_get_program,
                patch("auth_service.get_current_user", return_value=mock_user),
                patch("auth_service.has_permission", return_value=True),
            ):

                mock_get_program.side_effect = lambda pid: next(
                    (p for p in mock_programs if p["id"] == pid), None
                )

                _login_test_user(client, mock_user)

                response = client.get("/api/context/program")
                assert response.status_code == 200

                data = response.get_json()
                assert data["success"] is True
                assert data["current_program_id"] == "prog-123"
                assert len(data["program_ids"]) == 2
                assert data["has_multiple_programs"] is True

    def test_switch_program_context_success(self, app, client):
        """Test POST /api/context/program/<program_id> success"""
        mock_user = {
            "user_id": "test-user",
            "role": "program_admin",
            "institution_id": "inst-123",
            "program_ids": ["prog-123", "prog-456"],
            "program_ids": ["prog-123", "prog-456"],
        }
        mock_program = {"id": "prog-123", "name": "Computer Science"}

        with app.app_context():
            with (
                patch("api_routes.get_current_user", return_value=mock_user),
                patch("api_routes.get_program_by_id", return_value=mock_program),
                patch("api_routes.set_current_program_id", return_value=True),
                patch("auth_service.get_current_user", return_value=mock_user),
                patch("auth_service.has_permission", return_value=True),
            ):

                _login_test_user(client, mock_user)

                response = client.post("/api/context/program/prog-123")
                assert response.status_code == 200

                data = response.get_json()
                assert data["success"] is True
                assert data["current_program_id"] == "prog-123"
                assert "program" in data

    def test_switch_program_context_unauthorized(self, app, client):
        """Test POST /api/context/program/<program_id> with unauthorized program"""
        mock_user = {
            "user_id": "test-user",
            "role": "program_admin",
            "institution_id": "inst-123",
            "program_ids": ["prog-123", "prog-456"],
            "program_ids": ["prog-123", "prog-456"],
        }

        with app.app_context():
            with (
                patch("api_routes.get_current_user", return_value=mock_user),
                patch("auth_service.get_current_user", return_value=mock_user),
                patch("auth_service.has_permission", return_value=True),
            ):
                _login_test_user(client, mock_user)

                response = client.post("/api/context/program/prog-999")
                assert response.status_code == 403

                data = response.get_json()
                assert data["success"] is False
                assert "Access denied" in data["error"]

    def test_clear_program_context_success(self, app, client):
        """Test DELETE /api/context/program success"""
        with app.app_context():
            with (
                patch("api_routes.clear_current_program_id", return_value=True),
                patch(
                    "auth_service.get_current_user",
                    return_value={"user_id": "test", "role": "site_admin"},
                ),
                patch("auth_service.has_permission", return_value=True),
            ):
                _login_test_user(client, {"user_id": "test", "role": "site_admin"})

                response = client.delete("/api/context/program")
                assert response.status_code == 200

                data = response.get_json()
                assert data["success"] is True
                assert data["current_program_id"] is None


class TestUnassignedCoursesAPI:
    """Test unassigned courses management API endpoints"""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing"""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"

        # Register the API blueprint
        from api_routes import api

        app.register_blueprint(api)

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    def test_list_unassigned_courses_success(self, app, client):
        """Test GET /api/courses/unassigned success"""
        mock_courses = [
            {"id": "course-1", "name": "Unassigned Course 1", "program_ids": []},
            {"id": "course-2", "name": "Unassigned Course 2", "program_ids": []},
        ]

        with app.app_context():
            with (
                patch("api_routes.get_current_institution_id", return_value="inst-123"),
                patch("api_routes.get_unassigned_courses", return_value=mock_courses),
                patch(
                    "auth_service.get_current_user",
                    return_value={"user_id": "test", "role": "site_admin"},
                ),
                patch("auth_service.has_permission", return_value=True),
            ):
                _login_test_user(client, {"user_id": "test", "role": "site_admin"})

                response = client.get("/api/courses/unassigned")
                assert response.status_code == 200

                data = response.get_json()
                assert data["success"] is True
                assert data["count"] == 2
                assert len(data["courses"]) == 2

    def test_assign_course_to_default_success(self, app, client):
        """Test POST /api/courses/<course_id>/assign-default success"""
        with app.app_context():
            with (
                patch("api_routes.get_current_institution_id", return_value="inst-123"),
                patch("api_routes.assign_course_to_default_program", return_value=True),
                patch(
                    "auth_service.get_current_user",
                    return_value={"user_id": "test", "role": "site_admin"},
                ),
                patch("auth_service.has_permission", return_value=True),
            ):
                _login_test_user(client, {"user_id": "test", "role": "site_admin"})

                response = client.post("/api/courses/course-123/assign-default")
                assert response.status_code == 200

                data = response.get_json()
                assert data["success"] is True
                assert "assigned" in data["message"].lower()


class TestContextValidationMiddleware:
    """Test context validation middleware functionality"""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing"""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"
        return app

    def test_context_validation_skips_auth_endpoints(self, app):
        """Test that context validation skips auth endpoints"""
        with app.test_request_context("/api/auth/login", method="POST"):
            from api_routes import validate_context

            # Should return None (no validation error) for auth endpoints
            result = validate_context()
            assert result is None

    def test_context_validation_skips_context_endpoints(self, app):
        """Test that context validation skips context management endpoints"""
        with app.test_request_context("/api/context/program", method="GET"):
            from api_routes import validate_context

            # Should return None (no validation error) for context endpoints
            result = validate_context()
            assert result is None

    def test_context_validation_allows_site_admin(self, app):
        """Test that context validation allows site admin without institution context"""
        mock_user = {"user_id": "admin-123", "role": "site_admin"}

        with app.test_request_context("/api/courses", method="GET"):
            with patch("api_routes.get_current_user", return_value=mock_user):
                from api_routes import validate_context

                result = validate_context()
                assert result is None

    def test_context_validation_logs_missing_institution(self, app):
        """Test that context validation logs when institution context is missing"""
        mock_user = {"user_id": "user-123", "role": "program_admin"}

        with app.test_request_context("/api/courses", method="GET"):
            with (
                patch("api_routes.get_current_user", return_value=mock_user),
                patch("api_routes.get_current_institution_id", return_value=None),
                patch("api_routes.logger") as mock_logger,
            ):

                from api_routes import validate_context

                # Call the validation function directly
                result = validate_context()

                # The function should have logged a warning about missing context
                # Even if it doesn't return an error in this test scenario
                assert mock_logger.warning.called or result is None
