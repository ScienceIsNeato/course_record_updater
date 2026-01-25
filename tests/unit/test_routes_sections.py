"""Unit tests for section API routes (migrated from test_api_routes.py)."""

import json
from unittest.mock import patch

from src.app import app


class TestSectionEndpoints:
    """Test section management endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = self.app.test_client()
        self.site_admin_user = {
            "user_id": "admin-456",
            "email": "admin@test.com",
            "role": "site_admin",
            "institution_id": "riverside-tech-institute",
        }

    def _login_site_admin(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    def _login_user(self, overrides=None):
        return self._login_site_admin(overrides)

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.routes.sections.get_all_sections")
    def test_get_sections_endpoint_exists(
        self, mock_get_all_sections, mock_get_current_institution_id
    ):
        """Test that GET /api/sections endpoint exists."""
        self._login_user()

        # Mock the institution ID and sections
        mock_get_current_institution_id.return_value = "riverside-tech-institute"
        mock_get_all_sections.return_value = []

        response = self.client.get("/api/sections")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "sections" in data
        assert isinstance(data["sections"], list)

    def test_create_section_endpoint_exists(self):
        """Test that POST /api/sections endpoint exists."""
        self._login_user()

        response = self.client.post("/api/sections", json={})
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
