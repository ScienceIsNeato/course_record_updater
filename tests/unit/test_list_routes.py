"""
Unit tests for list page routes (courses, users, sections)

Tests authentication requirements and template rendering
"""

import pytest


@pytest.mark.unit
class TestCoursesListRoute:
    """Test /courses route"""

    def test_courses_list_requires_authentication(self, client):
        """Unauthenticated users should be redirected to login"""
        response = client.get("/courses", follow_redirects=False)

        # Should redirect to login
        assert response.status_code == 302
        assert "/login" in response.location

    def test_courses_list_renders_for_authenticated_user(self, authenticated_client):
        """Authenticated users should see the courses list page"""
        response = authenticated_client.get("/courses")

        assert response.status_code == 200
        # Check that we got HTML back
        assert b"html" in response.data.lower()


@pytest.mark.unit
class TestUsersListRoute:
    """Test /users route"""

    def test_users_list_requires_authentication(self, client):
        """Unauthenticated users should be redirected to login"""
        response = client.get("/users", follow_redirects=False)

        # Should redirect to login
        assert response.status_code == 302
        assert "/login" in response.location

    def test_users_list_renders_for_authenticated_user(self, authenticated_client):
        """Authenticated users should see the users list page"""
        response = authenticated_client.get("/users")

        assert response.status_code == 200
        # Check that we got HTML back
        assert b"html" in response.data.lower()


@pytest.mark.unit
class TestSectionsListRoute:
    """Test /sections route"""

    def test_sections_list_requires_authentication(self, client):
        """Unauthenticated users should be redirected to login"""
        response = client.get("/sections", follow_redirects=False)

        # Should redirect to login
        assert response.status_code == 302
        assert "/login" in response.location

    def test_sections_list_renders_for_authenticated_user(self, authenticated_client):
        """Authenticated users should see the sections list page"""
        response = authenticated_client.get("/sections")

        assert response.status_code == 200
        # Check that we got HTML back
        assert b"html" in response.data.lower()
