"""Unit tests for API routes."""

import json
from io import BytesIO
from unittest.mock import patch, MagicMock, Mock
import pytest
from flask import Flask

# Import the API blueprint and related modules
from api_routes import api
from app import app


class TestAPIBlueprint:
    """Test API blueprint setup and registration."""

    def test_api_blueprint_creation(self):
        """Test that API blueprint is created correctly."""
        assert api.name == "api"
        assert api.url_prefix == "/api"

    def test_api_blueprint_registered_in_app(self):
        """Test that API blueprint is registered in the Flask app."""
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        assert "api" in blueprint_names


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_endpoint_success(self):
        """Test health endpoint returns success."""
        with app.test_client() as client:
            response = client.get("/api/health")
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data["status"] == "healthy"
            assert data["success"] is True
            assert data["message"] == "CEI Course Management API is running"
            assert data["version"] == "2.0.0"

    def test_health_endpoint_no_auth_required(self):
        """Test health endpoint works without authentication."""
        with app.test_client() as client:
            response = client.get("/api/health")
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data["status"] == "healthy"


class TestDashboardEndpoint:
    """Test the dashboard endpoint."""

    def test_dashboard_endpoint_exists(self):
        """Test that dashboard endpoint is registered."""
        with app.test_client() as client:
            response = client.get("/api/dashboard")
            # Endpoint exists (not 404), though it may fail due to missing templates
            assert response.status_code != 404


class TestUserEndpoints:
    """Test user management endpoints."""

    def test_get_users_endpoint_exists(self):
        """Test that GET /api/users endpoint exists and returns valid JSON."""
        with app.test_client() as client:
            response = client.get("/api/users")
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert "users" in data
            assert isinstance(data["users"], list)

    def test_get_users_without_permission_stub_mode(self):
        """Test GET /api/users in stub mode (auth always passes)."""
        # In stub mode, auth service always returns True, so this will pass
        with app.test_client() as client:
            response = client.get("/api/users")
            # Should succeed in stub mode, but return empty list
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert "users" in data

    @patch('api_routes.get_users_by_role')
    @patch('api_routes.has_permission')
    def test_get_users_with_role_filter(self, mock_has_permission, mock_get_users):
        """Test GET /api/users with role filter."""
        mock_has_permission.return_value = True
        mock_get_users.return_value = [
            {"user_id": "1", "email": "instructor@example.com", "role": "instructor"}
        ]
        
        with app.test_client() as client:
            response = client.get("/api/users?role=instructor")
            assert response.status_code == 200
            
            # Verify the role filter was applied
            mock_get_users.assert_called_with("instructor")

    @patch('api_routes.has_permission')
    def test_create_user_success(self, mock_has_permission):
        """Test POST /api/users with valid data."""
        mock_has_permission.return_value = True
        
        user_data = {
            "email": "newuser@example.com",
            "role": "instructor",
            "first_name": "New",
            "last_name": "User"
        }
        
        with app.test_client() as client:
            response = client.post("/api/users", 
                                 json=user_data,
                                 content_type="application/json")
            assert response.status_code == 201
            
            data = json.loads(response.data)
            assert "message" in data
            assert "created" in data["message"].lower()

    @patch('api_routes.has_permission')
    def test_create_user_missing_required_fields(self, mock_has_permission):
        """Test POST /api/users with missing required fields."""
        mock_has_permission.return_value = True
        
        incomplete_data = {
            "email": "incomplete@example.com"
            # Missing role
        }
        
        with app.test_client() as client:
            response = client.post("/api/users", 
                                 json=incomplete_data,
                                 content_type="application/json")
            assert response.status_code == 400
            
            data = json.loads(response.data)
            assert "error" in data
            assert "required" in data["error"].lower()


class TestCourseEndpoints:
    """Test course management endpoints."""

    def test_get_courses_endpoint_exists(self):
        """Test that GET /api/courses endpoint exists and returns valid JSON."""
        with app.test_client() as client:
            response = client.get("/api/courses")
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert "courses" in data
            assert isinstance(data["courses"], list)

    @patch('api_routes.get_courses_by_department')
    def test_get_courses_with_department_filter(self, mock_get_courses):
        """Test GET /api/courses with department filter."""
        mock_get_courses.return_value = [
            {"course_number": "MATH-101", "course_title": "Algebra", "department": "MATH"}
        ]
        
        with app.test_client() as client:
            response = client.get("/api/courses?department=MATH")
            assert response.status_code == 200
            
            mock_get_courses.assert_called_with("MATH")

    @patch('api_routes.create_course')
    @patch('api_routes.has_permission')
    def test_create_course_success(self, mock_has_permission, mock_create_course):
        """Test POST /api/courses with valid data."""
        mock_has_permission.return_value = True
        mock_create_course.return_value = "course-123"
        
        course_data = {
            "course_number": "TEST-101",
            "course_title": "Test Course",
            "department": "TEST",
            "credit_hours": 3
        }
        
        with app.test_client() as client:
            response = client.post("/api/courses", 
                                 json=course_data,
                                 content_type="application/json")
            assert response.status_code == 201
            
            data = json.loads(response.data)
            assert "message" in data
            assert "course_id" in data

    def test_get_course_by_number_endpoint_exists(self):
        """Test that GET /api/courses/<course_number> endpoint exists."""
        with app.test_client() as client:
            response = client.get("/api/courses/MATH-101")
            # Endpoint exists and correctly returns 404 for non-existent course
            assert response.status_code == 404
            data = json.loads(response.data)
            assert "error" in data

    @patch('api_routes.get_course_by_number')
    def test_get_course_by_number_not_found(self, mock_get_course):
        """Test GET /api/courses/<course_number> when course doesn't exist."""
        mock_get_course.return_value = None
        
        with app.test_client() as client:
            response = client.get("/api/courses/NONEXISTENT-999")
            assert response.status_code == 404
            
            data = json.loads(response.data)
            assert "error" in data
            assert "not found" in data["error"].lower()


class TestTermEndpoints:
    """Test term management endpoints."""

    @patch('api_routes.get_active_terms')
    def test_get_terms_success(self, mock_get_terms):
        """Test GET /api/terms."""
        mock_get_terms.return_value = [
            {"term_name": "Fall2024", "start_date": "2024-08-15", "end_date": "2024-12-15"},
            {"term_name": "Spring2025", "start_date": "2025-01-15", "end_date": "2025-05-15"}
        ]
        
        with app.test_client() as client:
            response = client.get("/api/terms")
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert "terms" in data
            assert len(data["terms"]) == 2

    def test_create_term_endpoint_exists(self):
        """Test that POST /api/terms endpoint exists."""
        with app.test_client() as client:
            response = client.post("/api/terms", json={})
            # Should not be 404 (endpoint exists)
            assert response.status_code != 404


class TestSectionEndpoints:
    """Test section management endpoints."""

    def test_get_sections_endpoint_exists(self):
        """Test that GET /api/sections endpoint exists."""
        with app.test_client() as client:
            response = client.get("/api/sections?term=Fall2024")
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert "sections" in data
            assert isinstance(data["sections"], list)

    def test_create_section_endpoint_exists(self):
        """Test that POST /api/sections endpoint exists."""
        with app.test_client() as client:
            response = client.post("/api/sections", json={})
            # Should not be 404 (endpoint exists)
            assert response.status_code != 404


class TestImportEndpoints:
    """Test import functionality endpoints."""

    def test_excel_import_endpoint_exists(self):
        """Test that POST /api/import/excel endpoint exists."""
        with app.test_client() as client:
            response = client.post("/api/import/excel")
            # Should not be 404 (endpoint exists), but will be 400 due to missing file
            assert response.status_code != 404

    @patch('api_routes.has_permission')
    def test_excel_import_missing_file(self, mock_has_permission):
        """Test POST /api/import/excel without file."""
        mock_has_permission.return_value = True
        
        with app.test_client() as client:
            response = client.post("/api/import/excel",
                                 data={
                                     "conflict_strategy": "use_theirs",
                                     "dry_run": "false"
                                 })
            assert response.status_code == 400
            
            data = json.loads(response.data)
            assert "error" in data
            assert "file" in data["error"].lower()


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_method_not_allowed(self):
        """Test method not allowed responses."""
        with app.test_client() as client:
            # Try DELETE on an endpoint that doesn't support it
            response = client.delete("/api/health")
            assert response.status_code == 405

    def test_api_endpoints_return_json(self):
        """Test that API endpoints return JSON responses."""
        with app.test_client() as client:
            response = client.get("/api/health")
            assert response.status_code == 200
            assert response.content_type.startswith("application/json")


class TestRequestValidation:
    """Test request data validation."""

    @patch('api_routes.has_permission')
    def test_course_creation_validation(self, mock_has_permission):
        """Test course creation with various validation scenarios."""
        mock_has_permission.return_value = True
        
        # Test missing required field
        invalid_course = {
            "course_title": "Test Course"
            # Missing course_number
        }
        
        with app.test_client() as client:
            response = client.post("/api/courses",
                                 json=invalid_course,
                                 content_type="application/json")
            assert response.status_code == 400

    @patch('api_routes.has_permission')
    def test_term_creation_validation(self, mock_has_permission):
        """Test term creation with date validation."""
        mock_has_permission.return_value = True
        
        # Test invalid date format
        invalid_term = {
            "term_name": "InvalidTerm",
            "start_date": "invalid-date",
            "end_date": "2024-12-15"
        }
        
        with app.test_client() as client:
            response = client.post("/api/terms",
                                 json=invalid_term,
                                 content_type="application/json")
            assert response.status_code == 400


class TestAuthenticationIntegration:
    """Test authentication integration across endpoints."""

    def test_auth_service_integration(self):
        """Test that auth service is integrated with API routes."""
        # Test that auth functions are imported and available
        from api_routes import get_current_user, has_permission
        
        # In stub mode, these should work
        user = get_current_user()
        assert user is not None
        assert has_permission("any_permission") is True
