"""Unit tests for reminders API routes (migrated from test_api_routes.py)."""

from unittest.mock import patch

import pytest


class TestCourseReminderEndpoint:
    """Test /api/send-course-reminder endpoint."""

    @pytest.fixture
    def authenticated_client_and_token(self, client):
        """Create an authenticated client with CSRF properly configured."""
        from tests.test_utils import create_test_session

        # Create session with program admin user (has manage_programs permission)
        user_data = {
            "user_id": "admin-123",
            "email": "admin@example.com",
            "role": "program_admin",
            "first_name": "Admin",
            "last_name": "User",
            "institution_id": "inst-123",
        }
        create_test_session(client, user_data)

        # The global conftest.py autouse fixture handles CSRF token injection automatically
        # No need to return a token - the client's POST method is already wrapped
        return client

    @patch("src.database.database_service.get_user_by_id")
    @patch("src.database.database_service.get_course_by_id")
    @patch("src.database.database_service.get_institution_by_id")
    @patch("src.api.utils.get_current_user")
    @patch("src.services.email_service.EmailService.send_course_assessment_reminder")
    def test_send_course_reminder_success(
        self,
        mock_send_email,
        mock_get_current_user,
        mock_get_institution,
        mock_get_course,
        mock_get_instructor,
        authenticated_client_and_token,
    ):
        """Test successfully sending course reminder email."""
        client = authenticated_client_and_token
        # Setup mocks
        mock_get_instructor.return_value = {
            "user_id": "instructor-123",
            "email": "instructor@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "institution_id": "inst-123",
        }
        mock_get_course.return_value = {
            "id": "course-123",
            "course_number": "CS101",
            "course_title": "Intro to Computer Science",
        }
        mock_get_institution.return_value = {
            "id": "inst-123",
            "name": "Test University",
        }
        mock_get_current_user.return_value = {
            "user_id": "admin-123",
            "email": "admin@example.com",
            "first_name": "Admin",
            "last_name": "User",
            "institution_id": "inst-123",
        }

        # Send request
        response = client.post(
            "/api/send-course-reminder",
            json={
                "instructor_id": "instructor-123",
                "course_id": "course-123",
            },
        )

        # Verify
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Reminder sent" in data["message"]
        mock_send_email.assert_called_once()

    @patch("src.database.database_service.get_user_by_id")
    @patch("src.database.database_service.get_course_by_id")
    def test_send_course_reminder_missing_json(
        self, mock_get_course, mock_get_instructor, authenticated_client_and_token
    ):
        """Test sending reminder with no JSON data returns 400."""
        client = authenticated_client_and_token
        response = client.post(
            "/api/send-course-reminder",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "No JSON data provided" in data["error"]

    @patch("src.database.database_service.get_user_by_id")
    @patch("src.database.database_service.get_course_by_id")
    def test_send_course_reminder_missing_fields(
        self, mock_get_course, mock_get_instructor, authenticated_client_and_token
    ):
        """Test sending reminder with missing required fields returns 400."""
        client = authenticated_client_and_token
        response = client.post(
            "/api/send-course-reminder",
            json={"instructor_id": "instructor-123"},  # Missing course_id
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Missing required fields" in data["error"]

    @patch("src.database.database_service.get_user_by_id")
    @patch("src.database.database_service.get_course_by_id")
    def test_send_course_reminder_instructor_not_found(
        self, mock_get_course, mock_get_instructor, authenticated_client_and_token
    ):
        """Test sending reminder for non-existent instructor returns 404."""
        client = authenticated_client_and_token
        mock_get_instructor.return_value = None

        response = client.post(
            "/api/send-course-reminder",
            json={
                "instructor_id": "nonexistent",
                "course_id": "course-123",
            },
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "Instructor not found" in data["error"]

    @patch("src.database.database_service.get_user_by_id")
    @patch("src.database.database_service.get_course_by_id")
    def test_send_course_reminder_course_not_found(
        self, mock_get_course, mock_get_instructor, authenticated_client_and_token
    ):
        """Test sending reminder for non-existent course returns 404."""
        client = authenticated_client_and_token
        mock_get_instructor.return_value = {
            "user_id": "instructor-123",
            "email": "instructor@example.com",
        }
        mock_get_course.return_value = None

        response = client.post(
            "/api/send-course-reminder",
            json={
                "instructor_id": "instructor-123",
                "course_id": "nonexistent",
            },
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "Course not found" in data["error"]

    @patch("src.database.database_service.get_institution_by_id")
    @patch("src.database.database_service.get_course_by_id")
    @patch("src.database.database_service.get_user_by_id")
    @patch("src.api.utils.get_current_user")
    @patch("src.services.email_service.EmailService.send_course_assessment_reminder")
    def test_send_course_reminder_instructor_no_name(
        self,
        mock_send_email,
        mock_get_current_user,
        mock_get_instructor,
        mock_get_course,
        mock_get_institution,
        authenticated_client_and_token,
    ):
        """Test sending reminder when instructor has no first/last name uses email fallback."""
        client = authenticated_client_and_token
        # Instructor with no first/last name
        mock_get_instructor.return_value = {
            "user_id": "instructor-123",
            "email": "instructor@example.com",
            "first_name": "",
            "last_name": "",
            "institution_id": "inst-123",
        }
        mock_get_course.return_value = {
            "id": "course-123",
            "course_number": "CS101",
            "course_title": "Intro to CS",
        }
        mock_get_institution.return_value = {
            "id": "inst-123",
            "name": "Test University",
        }
        mock_get_current_user.return_value = {
            "user_id": "admin-123",
            "email": "admin@example.com",
            "first_name": "Admin",
            "last_name": "User",
            "institution_id": "inst-123",
        }

        response = client.post(
            "/api/send-course-reminder",
            json={"instructor_id": "instructor-123", "course_id": "course-123"},
        )

        assert response.status_code == 200
        # Verify email was called with email address as name fallback
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args[1]
        assert call_args["instructor_name"] == "instructor@example.com"

    @patch("src.database.database_service.get_user_by_id")
    @patch("src.database.database_service.get_course_by_id")
    @patch("src.database.database_service.get_institution_by_id")
    @patch("src.api.utils.get_current_user")
    @patch("src.services.email_service.EmailService.send_course_assessment_reminder")
    def test_send_course_reminder_email_exception(
        self,
        mock_send_email,
        mock_get_current_user,
        mock_get_institution,
        mock_get_course,
        mock_get_instructor,
        authenticated_client_and_token,
    ):
        """Test sending reminder handles email exceptions gracefully."""
        client = authenticated_client_and_token
        # Setup mocks
        mock_get_instructor.return_value = {
            "user_id": "instructor-123",
            "email": "instructor@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "institution_id": "inst-123",
        }
        mock_get_course.return_value = {
            "id": "course-123",
            "course_number": "CS101",
            "course_title": "Intro to Computer Science",
        }
        mock_get_institution.return_value = {
            "id": "inst-123",
            "name": "Test University",
        }
        mock_get_current_user.return_value = {
            "user_id": "admin-123",
            "email": "admin@example.com",
            "first_name": "Admin",
            "last_name": "User",
            "institution_id": "inst-123",
        }
        mock_send_email.side_effect = Exception("SMTP error")

        # Send request
        response = client.post(
            "/api/send-course-reminder",
            json={
                "instructor_id": "instructor-123",
                "course_id": "course-123",
            },
        )

        # Verify
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert "Failed to send reminder email" in data["error"]
