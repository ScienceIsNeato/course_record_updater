"""Unit tests for term API routes (migrated from test_api_routes.py)."""

import json
from unittest.mock import patch

from src.app import app


class TestTermEndpoints:
    """Test term management endpoints."""

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

    def _login_user(self, overrides=None):
        from tests.test_utils import create_test_session

        user_data = {**self.site_admin_user}
        if overrides:
            user_data.update(overrides)
        create_test_session(self.client, user_data)
        return user_data

    @patch("src.api.utils.get_current_institution_id")
    @patch("src.api.routes.terms.get_active_terms")
    def test_get_terms_success(self, mock_get_terms, mock_get_current_institution_id):
        """Test GET /api/terms."""
        self._login_user()

        # Mock the institution ID
        mock_get_current_institution_id.return_value = "riverside-tech-institute"
        mock_get_terms.return_value = [
            {
                "term_name": "Fall2024",
                "start_date": "2024-08-15",
                "end_date": "2024-12-15",
            },
            {
                "term_name": "Spring2025",
                "start_date": "2025-01-15",
                "end_date": "2025-05-15",
            },
        ]

        response = self.client.get("/api/terms")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "terms" in data
        assert len(data["terms"]) == 2

    def test_create_term_endpoint_exists(self):
        """Test that POST /api/terms endpoint exists."""
        self._login_user()

        response = self.client.post("/api/terms", json={})
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404
