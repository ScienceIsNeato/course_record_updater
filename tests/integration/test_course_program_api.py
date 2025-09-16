"""
Integration tests for Course-Program Association API endpoints

Tests the complete course-program association functionality including:
- Adding and removing courses from programs
- Bulk operations for efficient course management
- Course visibility and program filtering
- Complete workflow scenarios
"""

from unittest.mock import Mock, patch

import pytest

from app import app


class TestCourseProgramAPIIntegration:
    """Test course-program association API endpoints with full Flask app context"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    @patch("api_routes.get_program_by_id")
    @patch("api_routes.get_courses_by_program")
    def test_get_program_courses_integration(self, mock_get_courses, mock_get_program):
        """Test program courses retrieval endpoint integration"""
        mock_get_program.return_value = {
            "id": "cs-program",
            "name": "Computer Science",
            "institution_id": "test-institution",
        }
        mock_get_courses.return_value = [
            {
                "id": "course1",
                "course_number": "CS101",
                "course_title": "Introduction to Computer Science",
                "program_ids": ["cs-program"],
            },
            {
                "id": "course2",
                "course_number": "CS201",
                "course_title": "Data Structures",
                "program_ids": ["cs-program", "eng-program"],
            },
        ]

        with patch("api_routes.login_required", lambda f: f):
            response = self.client.get("/api/programs/cs-program/courses")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["program_id"] == "cs-program"
        assert data["program_name"] == "Computer Science"
        assert len(data["courses"]) == 2
        assert data["count"] == 2

    @patch("api_routes.get_program_by_id")
    @patch("api_routes.get_course_by_number")
    @patch("api_routes.add_course_to_program")
    def test_add_course_to_program_integration(
        self, mock_add, mock_get_course, mock_get_program
    ):
        """Test course addition to program endpoint integration"""
        mock_get_program.return_value = {"id": "cs-program", "name": "Computer Science"}
        mock_get_course.return_value = {
            "course_id": "course1",
            "course_number": "CS101",
            "course_title": "Introduction to Computer Science",
        }
        mock_add.return_value = True

        course_data = {"course_id": "CS101"}

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.post(
                "/api/programs/cs-program/courses", json=course_data
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "CS101 added to program Computer Science" in data["message"]
        mock_add.assert_called_once_with("course1", "cs-program")

    @patch("api_routes.get_program_by_id")
    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_programs_by_institution")
    @patch("api_routes.remove_course_from_program")
    def test_remove_course_from_program_integration(
        self, mock_remove, mock_get_programs, mock_get_institution, mock_get_program
    ):
        """Test course removal from program endpoint integration"""
        mock_get_program.return_value = {"id": "cs-program", "name": "Computer Science"}
        mock_get_institution.return_value = "test-institution"
        mock_get_programs.return_value = [
            {"id": "default-program", "is_default": True},
            {"id": "cs-program", "is_default": False},
        ]
        mock_remove.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.delete("/api/programs/cs-program/courses/course1")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "course1 removed from program Computer Science" in data["message"]
        mock_remove.assert_called_once_with("course1", "cs-program", "default-program")

    @patch("api_routes.get_program_by_id")
    @patch("api_routes.bulk_add_courses_to_program")
    def test_bulk_add_courses_integration(self, mock_bulk_add, mock_get_program):
        """Test bulk course addition endpoint integration"""
        mock_get_program.return_value = {"id": "cs-program", "name": "Computer Science"}
        mock_bulk_add.return_value = {
            "success_count": 3,
            "failure_count": 1,
            "already_assigned": 0,
            "failures": [{"course_id": "course4", "error": "Course not found"}],
        }

        bulk_data = {
            "action": "add",
            "course_ids": ["course1", "course2", "course3", "course4"],
        }

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.post(
                "/api/programs/cs-program/courses/bulk", json=bulk_data
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Bulk add operation completed: 3 added" in data["message"]
        assert data["details"]["success_count"] == 3
        assert data["details"]["failure_count"] == 1

    @patch("api_routes.get_program_by_id")
    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_programs_by_institution")
    @patch("api_routes.bulk_remove_courses_from_program")
    def test_bulk_remove_courses_integration(
        self,
        mock_bulk_remove,
        mock_get_programs,
        mock_get_institution,
        mock_get_program,
    ):
        """Test bulk course removal endpoint integration"""
        mock_get_program.return_value = {"id": "cs-program", "name": "Computer Science"}
        mock_get_institution.return_value = "test-institution"
        mock_get_programs.return_value = [{"id": "default-program", "is_default": True}]
        mock_bulk_remove.return_value = {
            "success_count": 2,
            "failure_count": 0,
            "not_assigned": 1,
            "orphaned_assigned_to_default": 1,
        }

        bulk_data = {
            "action": "remove",
            "course_ids": ["course1", "course2", "course3"],
        }

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.post(
                "/api/programs/cs-program/courses/bulk", json=bulk_data
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Bulk remove operation completed: 2 removed" in data["message"]
        assert data["details"]["orphaned_assigned_to_default"] == 1

    @patch("api_routes.get_course_by_number")
    @patch("api_routes.get_program_by_id")
    def test_get_course_programs_integration(self, mock_get_program, mock_get_course):
        """Test course programs retrieval endpoint integration"""
        mock_get_course.return_value = {
            "course_id": "course1",
            "course_number": "CS101",
            "course_title": "Introduction to Computer Science",
            "program_ids": ["cs-program", "eng-program"],
        }
        mock_get_program.side_effect = [
            {"id": "cs-program", "name": "Computer Science", "short_name": "CS"},
            {"id": "eng-program", "name": "Engineering", "short_name": "ENG"},
        ]

        with patch("api_routes.login_required", lambda f: f):
            response = self.client.get("/api/courses/CS101/programs")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["course_id"] == "CS101"
        assert data["course_title"] == "Introduction to Computer Science"
        assert len(data["programs"]) == 2
        assert data["count"] == 2

    def test_bulk_manage_invalid_action_integration(self):
        """Test bulk course management with invalid action"""
        bulk_data = {"action": "invalid_action", "course_ids": ["course1"]}

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.post(
                "/api/programs/cs-program/courses/bulk", json=bulk_data
            )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid or missing action" in data["error"]

    def test_bulk_manage_missing_course_ids_integration(self):
        """Test bulk course management with missing course IDs"""
        bulk_data = {
            "action": "add"
            # Missing course_ids
        }

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            response = self.client.post(
                "/api/programs/cs-program/courses/bulk", json=bulk_data
            )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Missing or invalid course_ids array" in data["error"]

    @patch("api_routes.get_program_by_id")
    def test_program_not_found_integration(self, mock_get_program):
        """Test endpoints when program doesn't exist"""
        mock_get_program.return_value = None

        # Test get program courses
        with patch("api_routes.login_required", lambda f: f):
            response = self.client.get("/api/programs/nonexistent/courses")

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert data["error"] == "Program not found"


class TestCourseProgramWorkflow:
    """Test complete course-program association workflow"""

    def setup_method(self):
        """Set up test fixtures"""
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    @patch("api_routes.get_program_by_id")
    @patch("api_routes.get_course_by_number")
    @patch("api_routes.add_course_to_program")
    @patch("api_routes.get_courses_by_program")
    @patch("api_routes.remove_course_from_program")
    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_programs_by_institution")
    def test_complete_course_program_lifecycle(
        self,
        mock_get_programs,
        mock_get_institution,
        mock_remove,
        mock_get_courses,
        mock_add,
        mock_get_course,
        mock_get_program,
    ):
        """Test complete course-program lifecycle: add -> view -> remove"""

        # Setup mocks
        mock_get_program.return_value = {"id": "cs-program", "name": "Computer Science"}
        mock_get_course.return_value = {
            "course_id": "course1",
            "course_number": "CS101",
        }
        mock_get_institution.return_value = "test-institution"
        mock_get_programs.return_value = [{"id": "default-program", "is_default": True}]

        # Step 1: Add course to program
        mock_add.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            add_response = self.client.post(
                "/api/programs/cs-program/courses", json={"course_id": "CS101"}
            )

        assert add_response.status_code == 200
        add_data = add_response.get_json()
        assert add_data["success"] is True

        # Step 2: View courses in program
        mock_get_courses.return_value = [
            {
                "id": "course1",
                "course_number": "CS101",
                "course_title": "Introduction to CS",
                "program_ids": ["cs-program"],
            }
        ]

        with patch("api_routes.login_required", lambda f: f):
            view_response = self.client.get("/api/programs/cs-program/courses")

        assert view_response.status_code == 200
        view_data = view_response.get_json()
        assert view_data["success"] is True
        assert len(view_data["courses"]) == 1
        assert view_data["courses"][0]["course_number"] == "CS101"

        # Step 3: Remove course from program
        mock_remove.return_value = True

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            remove_response = self.client.delete(
                "/api/programs/cs-program/courses/course1"
            )

        assert remove_response.status_code == 200
        remove_data = remove_response.get_json()
        assert remove_data["success"] is True
        assert "removed from program" in remove_data["message"]

    @patch("api_routes.get_program_by_id")
    @patch("api_routes.bulk_add_courses_to_program")
    @patch("api_routes.bulk_remove_courses_from_program")
    @patch("api_routes.get_current_institution_id")
    @patch("api_routes.get_programs_by_institution")
    def test_bulk_operations_workflow(
        self,
        mock_get_programs,
        mock_get_institution,
        mock_bulk_remove,
        mock_bulk_add,
        mock_get_program,
    ):
        """Test bulk course management workflow"""

        # Setup mocks
        mock_get_program.return_value = {"id": "cs-program", "name": "Computer Science"}
        mock_get_institution.return_value = "test-institution"
        mock_get_programs.return_value = [{"id": "default-program", "is_default": True}]

        # Step 1: Bulk add courses
        mock_bulk_add.return_value = {
            "success_count": 3,
            "failure_count": 0,
            "already_assigned": 0,
            "failures": [],
        }

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            add_response = self.client.post(
                "/api/programs/cs-program/courses/bulk",
                json={"action": "add", "course_ids": ["course1", "course2", "course3"]},
            )

        assert add_response.status_code == 200
        add_data = add_response.get_json()
        assert add_data["success"] is True
        assert add_data["details"]["success_count"] == 3

        # Step 2: Bulk remove courses
        mock_bulk_remove.return_value = {
            "success_count": 2,
            "failure_count": 0,
            "not_assigned": 1,
            "orphaned_assigned_to_default": 1,
        }

        with patch("api_routes.permission_required", lambda perm: lambda f: f):
            remove_response = self.client.post(
                "/api/programs/cs-program/courses/bulk",
                json={
                    "action": "remove",
                    "course_ids": ["course1", "course2", "course3"],
                },
            )

        assert remove_response.status_code == 200
        remove_data = remove_response.get_json()
        assert remove_data["success"] is True
        assert remove_data["details"]["success_count"] == 2
        assert remove_data["details"]["orphaned_assigned_to_default"] == 1
