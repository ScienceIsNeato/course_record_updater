"""Unit tests for api/routes/management.py blueprint routes."""

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
    """Create session for site admin user (has all permissions)."""
    user_data = {
        "user_id": "site-admin-123",
        "role": "site_admin",
        "institution_id": "inst-1",
        "email": "siteadmin@example.com",
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


class TestManagementUpdateProgram:
    """Tests for PUT /api/management/programs/<program_id>."""

    def test_update_program_no_data(self, client):
        create_site_admin_session(client)
        response = client.put(
            "/api/management/programs/prog-1",
            json={},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    @patch("src.api.routes.management.db.get_program_by_id")
    def test_update_program_not_found(self, mock_get_program, client):
        create_site_admin_session(client)
        mock_get_program.return_value = None

        response = client.put(
            "/api/management/programs/prog-1",
            json={"name": "New Name"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False

    @patch("src.api.routes.management.db.get_program_by_id")
    def test_update_program_no_fields_to_update(self, mock_get_program, client):
        create_site_admin_session(client)
        mock_get_program.return_value = {"id": "prog-1", "name": "Old"}

        response = client.put(
            "/api/management/programs/prog-1",
            json={"unknown": "ignored"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    @patch("src.api.routes.management.db.update_program")
    @patch("src.api.routes.management.db.get_program_by_id")
    def test_update_program_success(self, mock_get_program, mock_update, client):
        create_site_admin_session(client)
        mock_get_program.return_value = {"id": "prog-1", "name": "Old"}
        mock_update.return_value = True

        response = client.put(
            "/api/management/programs/prog-1",
            json={"name": "New Name"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["program_id"] == "prog-1"

    @patch("src.api.routes.management.db.update_program")
    @patch("src.api.routes.management.db.get_program_by_id")
    def test_update_program_success_multiple_fields(
        self, mock_get_program, mock_update, client
    ):
        """Covers update dict building for short_name/description branches."""
        create_site_admin_session(client)
        mock_get_program.return_value = {"id": "prog-1", "name": "Old"}
        mock_update.return_value = True

        response = client.put(
            "/api/management/programs/prog-1",
            json={"short_name": "NEW", "description": "Desc"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 200
        mock_update.assert_called_once()
        _, updates = mock_update.call_args.args
        assert updates["short_name"] == "NEW"
        assert updates["description"] == "Desc"

    @patch("src.api.routes.management.db.update_program")
    @patch("src.api.routes.management.db.get_program_by_id")
    def test_update_program_update_failed(self, mock_get_program, mock_update, client):
        create_site_admin_session(client)
        mock_get_program.return_value = {"id": "prog-1", "name": "Old"}
        mock_update.return_value = False

        response = client.put(
            "/api/management/programs/prog-1",
            json={"name": "New Name"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    @patch("src.api.routes.management.db.get_program_by_id")
    def test_update_program_exception_handled(self, mock_get_program, client):
        """Covers exception handler branch."""
        create_site_admin_session(client)
        mock_get_program.side_effect = RuntimeError("boom")

        response = client.put(
            "/api/management/programs/prog-1",
            json={"name": "New Name"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False


class TestManagementDuplicateCourse:
    """Tests for POST /api/management/courses/<course_id>/duplicate."""

    def test_duplicate_course_missing_course_number(self, client):
        create_site_admin_session(client)
        response = client.post(
            "/api/management/courses/course-1/duplicate",
            json={},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    @patch("src.api.routes.management.db.get_course_by_id")
    def test_duplicate_course_source_not_found(self, mock_get_course, client):
        create_site_admin_session(client)
        mock_get_course.return_value = None

        response = client.post(
            "/api/management/courses/course-1/duplicate",
            json={"new_course_number": "COURSE-2"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False

    @patch("src.api.routes.management.db.get_course_by_number")
    @patch("src.api.routes.management.db.get_course_by_id")
    def test_duplicate_course_number_exists(
        self, mock_get_course, mock_get_by_number, client
    ):
        create_site_admin_session(client)
        mock_get_course.return_value = {
            "course_id": "course-1",
            "institution_id": "inst-1",
            "course_title": "Intro",
        }
        mock_get_by_number.return_value = {"course_id": "existing"}

        response = client.post(
            "/api/management/courses/course-1/duplicate",
            json={"new_course_number": "COURSE-2"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 409
        data = response.get_json()
        assert data["success"] is False

    @patch("src.api.routes.management.db.create_course")
    @patch("src.api.routes.management.db.get_course_by_number")
    @patch("src.api.routes.management.db.get_course_by_id")
    def test_duplicate_course_create_failed(
        self, mock_get_course, mock_get_by_number, mock_create, client
    ):
        create_site_admin_session(client)
        mock_get_course.return_value = {
            "course_id": "course-1",
            "institution_id": "inst-1",
            "course_title": "Intro",
        }
        mock_get_by_number.return_value = None
        mock_create.return_value = None

        response = client.post(
            "/api/management/courses/course-1/duplicate",
            json={"new_course_number": "COURSE-2"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    @patch("src.api.routes.management.db.add_course_to_program")
    @patch("src.api.routes.management.db.create_course")
    @patch("src.api.routes.management.db.get_course_by_number")
    @patch("src.api.routes.management.db.get_course_by_id")
    def test_duplicate_course_success_with_program_ids(
        self, mock_get_course, mock_get_by_number, mock_create, mock_add, client
    ):
        create_site_admin_session(client)
        mock_get_course.return_value = {
            "course_id": "course-1",
            "institution_id": "inst-1",
            "course_title": "Intro",
        }
        mock_get_by_number.return_value = None
        mock_create.return_value = "course-2"

        response = client.post(
            "/api/management/courses/course-1/duplicate",
            json={"new_course_number": "COURSE-2", "program_ids": ["p1", "p2"]},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["course_id"] == "course-2"
        mock_add.assert_any_call("course-2", "p1")
        mock_add.assert_any_call("course-2", "p2")

    @patch("src.api.routes.management.db.get_programs_for_course")
    @patch("src.api.routes.management.db.add_course_to_program")
    @patch("src.api.routes.management.db.create_course")
    @patch("src.api.routes.management.db.get_course_by_number")
    @patch("src.api.routes.management.db.get_course_by_id")
    def test_duplicate_course_success_copies_programs_from_source(
        self,
        mock_get_course,
        mock_get_by_number,
        mock_create,
        mock_add,
        mock_get_programs,
        client,
    ):
        create_site_admin_session(client)
        mock_get_course.return_value = {
            "course_id": "course-1",
            "institution_id": "inst-1",
            "course_title": "Intro",
        }
        mock_get_by_number.return_value = None
        mock_create.return_value = "course-2"
        mock_get_programs.return_value = [{"id": "p1"}, {"id": "p2"}]

        response = client.post(
            "/api/management/courses/course-1/duplicate",
            json={"new_course_number": "COURSE-2"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        mock_add.assert_any_call("course-2", "p1")
        mock_add.assert_any_call("course-2", "p2")

    @patch("src.api.routes.management.db.get_course_by_id")
    def test_duplicate_course_exception_handled(self, mock_get_course, client):
        """Covers exception handler branch."""
        create_site_admin_session(client)
        mock_get_course.side_effect = RuntimeError("boom")

        response = client.post(
            "/api/management/courses/course-1/duplicate",
            json={"new_course_number": "COURSE-2"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False


class TestManagementUpdateSection:
    """Tests for PUT /api/management/sections/<section_id>."""

    def test_update_section_no_data(self, client):
        create_site_admin_session(client)
        response = client.put(
            "/api/management/sections/sec-1",
            json={},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    @patch("src.api.routes.management.db.get_section_by_id")
    def test_update_section_not_found(self, mock_get_section, client):
        create_site_admin_session(client)
        mock_get_section.return_value = None

        response = client.put(
            "/api/management/sections/sec-1",
            json={"students_passed": 10},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False

    @patch("src.api.routes.management.db.get_section_by_id")
    def test_update_section_no_fields_to_update(self, mock_get_section, client):
        create_site_admin_session(client)
        mock_get_section.return_value = {"id": "sec-1"}

        response = client.put(
            "/api/management/sections/sec-1",
            json={"unknown": "ignored"},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    @patch("src.api.routes.management.db.update_course_section")
    @patch("src.api.routes.management.db.get_section_by_id")
    def test_update_section_success(self, mock_get_section, mock_update, client):
        create_site_admin_session(client)
        mock_get_section.return_value = {"id": "sec-1"}
        mock_update.return_value = True

        response = client.put(
            "/api/management/sections/sec-1",
            json={"students_passed": "10", "students_dfic": 2},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["section_id"] == "sec-1"
        mock_update.assert_called_once()
        _, updates = mock_update.call_args.args
        assert updates["students_passed"] == 10
        assert updates["students_dfic"] == 2

    @patch("src.api.routes.management.db.update_course_section")
    @patch("src.api.routes.management.db.get_section_by_id")
    def test_update_section_success_narratives(
        self, mock_get_section, mock_update, client
    ):
        """Covers narrative_* update branches."""
        create_site_admin_session(client)
        mock_get_section.return_value = {"id": "sec-1"}
        mock_update.return_value = True

        response = client.put(
            "/api/management/sections/sec-1",
            json={
                "narrative_celebrations": "good",
                "narrative_challenges": "bad",
                "narrative_changes": "change",
            },
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 200
        _, updates = mock_update.call_args.args
        assert updates["narrative_celebrations"] == "good"
        assert updates["narrative_challenges"] == "bad"
        assert updates["narrative_changes"] == "change"

    @patch("src.api.routes.management.db.update_course_section")
    @patch("src.api.routes.management.db.get_section_by_id")
    def test_update_section_update_failed(self, mock_get_section, mock_update, client):
        create_site_admin_session(client)
        mock_get_section.return_value = {"id": "sec-1"}
        mock_update.return_value = False

        response = client.put(
            "/api/management/sections/sec-1",
            json={"students_passed": 10},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

    @patch("src.api.routes.management.db.get_section_by_id")
    def test_update_section_exception_handled(self, mock_get_section, client):
        """Covers exception handler branch."""
        create_site_admin_session(client)
        mock_get_section.side_effect = RuntimeError("boom")

        response = client.put(
            "/api/management/sections/sec-1",
            json={"students_passed": 10},
            headers={"X-CSRFToken": get_csrf_token(client)},
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
