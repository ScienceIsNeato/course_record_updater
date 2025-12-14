"""
Unit tests for Adapter API endpoints.
Tests /api/adapters and /api/export/data.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from app import app
from tests.test_utils import create_test_session


class TestAdapterEndpoints:

    def setup_method(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    @patch("adapters.adapter_registry.get_adapter_registry")
    def test_get_available_adapters_success(self, mock_get_registry):
        """Test fetching available adapters."""
        # Setup mock registry
        mock_registry = Mock()
        mock_get_registry.return_value = mock_registry

        mock_registry.get_adapters_for_user.return_value = [
            {
                "id": "csv_v1",
                "name": "CSV Adapter",
                "description": "Exports CSV",
                "supported_formats": [".csv"],
                "data_types": ["courses"],
            }
        ]

        # Authenticate
        create_test_session(
            self.client,
            {"user_id": "u1", "role": "institution_admin", "institution_id": "i1"},
        )

        response = self.client.get("/api/adapters")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["adapters"]) == 1
        assert data["adapters"][0]["id"] == "csv_v1"
        assert data["adapters"][0]["supported_formats"] == [".csv"]

    def test_get_available_adapters_unauthorized(self):
        """Test fetching adapters without login."""
        response = self.client.get("/api/adapters")
        assert response.status_code == 401  # API returns 401, not 302

    @patch("api_routes._export_all_institutions")
    def test_export_data_site_admin(self, mock_export_all):
        """Test site admin export delegates to _export_all_institutions."""
        create_test_session(
            self.client,
            {"user_id": "admin", "role": "site_admin", "email": "admin@test.com"},
        )

        # Mock what _export_all_institutions returns (Response object or tuple)
        mock_export_all.return_value = "ZIP RESPONSE"

        response = self.client.get("/api/export/data")

        # Verify call
        mock_export_all.assert_called_once()

    @patch("api_routes.create_export_service")
    def test_export_data_institution_admin_success(self, mock_create_service):
        """Test export data for institution admin."""
        create_test_session(
            self.client,
            {
                "user_id": "u1",
                "role": "institution_admin",
                "institution_id": "i1",
                "email": "user@test.com",
            },
        )

        # Mock service and registry
        mock_service = Mock()
        mock_create_service.return_value = mock_service

        mock_adapter = Mock()
        mock_adapter.get_adapter_info.return_value = {"supported_formats": [".xlsx"]}
        mock_service.registry.get_adapter_by_id.return_value = mock_adapter

        # Mock export_data result
        mock_result = Mock()
        mock_result.success = True
        mock_result.records_exported = 10
        mock_service.export_data.return_value = mock_result

        with patch("api_routes.send_file") as mock_send_file:
            # Need to mock Path.exists/unlink or just ensure execution flow
            mock_send_file.return_value = "FILE RESPONSE"

            # Note: The code creates a temp file. Mocking send_file prevents reading it.
            # But the logic uses 'os' and 'datetime' which we might need to be careful with.
            # However, for this test, simply calling it triggers the logic paths.
            response = self.client.get(
                "/api/export/data?export_adapter=excel&export_data_type=courses"
            )

            assert response.status_code == 200

            # Verify adapter lookup
            mock_service.registry.get_adapter_by_id.assert_called_with("excel")

            # Verify export call
            mock_service.export_data.assert_called_once()

    def test_export_data_missing_institution_context(self):
        """Test export fails if user has no institution ID."""
        create_test_session(
            self.client,
            {
                "user_id": "u1",
                "role": "instructor",
                # No institution_id
                "email": "user@test.com",
            },
        )

        response = self.client.get("/api/export/data")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        # Update assertion to match actual error message
        assert "Institution context required" in data["error"]

    @patch("api_routes.create_export_service")
    def test_export_data_adapter_not_found(self, mock_create_service):
        """Test export fails if adapter is invalid."""
        create_test_session(
            self.client,
            {"user_id": "u1", "role": "institution_admin", "institution_id": "i1"},
        )

        mock_service = Mock()
        mock_create_service.return_value = mock_service
        mock_service.registry.get_adapter_by_id.return_value = None

        response = self.client.get("/api/export/data?export_adapter=bad_adapter")

        assert response.status_code == 400
        data = response.get_json()
        assert "Adapter not found" in data["error"]
