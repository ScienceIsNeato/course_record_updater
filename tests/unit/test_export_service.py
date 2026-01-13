"""
Unit tests for ExportService

Tests the export functionality using the adapter registry system for
bidirectional data flow.
"""

import tempfile
from unittest.mock import Mock, patch

from src.services.export_service import ExportConfig, ExportResult, ExportService


class TestExportService:
    """Test cases for ExportService functionality."""

    def test_init(self):
        """Test ExportService initialization."""
        service = ExportService()
        assert service.registry is not None
        # Check that the registry can discover adapters
        adapters = service.registry.get_all_adapters()
        assert len(adapters) >= 1  # Should have at least MockU adapter

    def test_export_config_creation(self):
        """Test ExportConfig dataclass creation."""
        config = ExportConfig(
            institution_id="test-institution",
            adapter_id="cei_excel_format_v1",
            export_view="standard",
        )
        assert config.institution_id == "test-institution"
        assert config.adapter_id == "cei_excel_format_v1"
        assert config.export_view == "standard"
        assert config.include_metadata is True  # Default value
        assert config.output_format == "xlsx"  # Default value

    def test_export_result_creation(self):
        """Test ExportResult dataclass creation."""
        result = ExportResult(success=True, records_exported=10)
        assert result.success is True
        assert result.records_exported == 10
        assert result.errors == []
        assert result.warnings == []
        assert result.export_timestamp is not None

    def test_unsupported_adapter(self):
        """Test export with unsupported adapter."""
        service = ExportService()
        config = ExportConfig(
            institution_id="test-institution", adapter_id="nonexistent_adapter"
        )

        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
            result = service.export_data(config, tmp.name)

        assert result.success is False
        assert "Adapter not found: nonexistent_adapter" in result.errors

    @patch("src.services.export_service.get_all_courses")
    @patch("src.services.export_service.get_all_users")
    @patch("src.services.export_service.get_active_terms")
    def test_fetch_export_data_empty(self, mock_terms, mock_users, mock_courses):
        """Test fetching export data when no data exists."""
        # Mock empty data
        mock_courses.return_value = []
        mock_users.return_value = []
        mock_terms.return_value = []

        service = ExportService()
        data = service._fetch_export_data("test-institution")

        assert data["courses"] == []
        assert data["users"] == []
        assert data["terms"] == []
        assert "course_offerings" in data
        assert "course_sections" in data
        assert "institutions" in data

    @patch("src.services.export_service.get_all_courses")
    @patch("src.services.export_service.get_all_users")
    @patch("src.services.export_service.get_active_terms")
    def test_fetch_export_data_with_data(self, mock_terms, mock_users, mock_courses):
        """Test fetching export data when data exists."""
        # Mock data
        mock_courses.return_value = [{"course_id": "1", "course_number": "MATH-101"}]
        mock_users.return_value = [{"user_id": "1", "email": "test@example.com"}]
        mock_terms.return_value = [{"term_id": "1", "name": "Fall 2024"}]

        service = ExportService()
        data = service._fetch_export_data("test-institution")

        assert len(data["courses"]) == 1
        assert len(data["users"]) == 1
        assert len(data["terms"]) == 1

    @patch("src.services.export_service.get_all_courses")
    @patch("src.services.export_service.get_all_users")
    @patch("src.services.export_service.get_active_terms")
    def test_export_no_data(self, mock_terms, mock_users, mock_courses):
        """Test export when no data exists."""
        # Mock empty data
        mock_courses.return_value = []
        mock_users.return_value = []
        mock_terms.return_value = []

        service = ExportService()
        config = ExportConfig(
            institution_id="test-institution", adapter_id="cei_excel_format_v1"
        )

        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
            result = service.export_data(config, tmp.name)

        assert result.success is False
        assert "No valid records to export" in result.errors


class TestExportServiceAdapterRegistry:
    """Test cases for ExportService adapter registry integration."""

    def test_validate_export_access_success(self):
        """Test successful export access validation."""
        service = ExportService()
        user = {"role": "site_admin", "institution_id": "mocku_institution_id"}

        has_access, message = service.validate_export_access(
            user, "cei_excel_format_v1"
        )

        assert has_access is True
        assert message == "Access granted"

    def test_validate_export_access_denied(self):
        """Test export access denied for invalid user."""
        service = ExportService()
        user = {"role": "instructor", "institution_id": "other_institution"}

        has_access, message = service.validate_export_access(
            user, "cei_excel_format_v1"
        )

        assert has_access is False
        assert "Access denied" in message

    def test_validate_export_access_adapter_not_found(self):
        """Test export access validation with non-existent adapter."""
        service = ExportService()
        user = {"role": "site_admin", "institution_id": "mocku_institution_id"}

        has_access, message = service.validate_export_access(
            user, "nonexistent_adapter"
        )

        assert has_access is False
        assert "Access denied" in message  # Access check happens first

    @patch("src.services.export_service.get_all_courses")
    @patch("src.services.export_service.get_all_users")
    @patch("src.services.export_service.get_active_terms")
    def test_export_with_adapter_supports_export_false(
        self, mock_terms, mock_users, mock_courses
    ):
        """Test export when adapter doesn't support export."""
        # Mock some data
        mock_courses.return_value = [{"course_id": "1", "course_number": "TEST-101"}]
        mock_users.return_value = [{"user_id": "1", "email": "test@example.com"}]
        mock_terms.return_value = [{"term_id": "1", "term_name": "Fall 2024"}]

        service = ExportService()

        # Mock the adapter registry to return an adapter that doesn't support export
        with patch.object(service.registry, "get_adapter_by_id") as mock_get_adapter:
            mock_adapter = Mock()
            mock_adapter.supports_export.return_value = False
            mock_get_adapter.return_value = mock_adapter

            config = ExportConfig(
                institution_id="test-institution", adapter_id="no_export_adapter"
            )

            with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
                result = service.export_data(config, tmp.name)

            assert result.success is False
            assert "does not support export functionality" in result.errors[0]

    @patch("src.services.export_service.get_all_courses")
    @patch("src.services.export_service.get_all_users")
    @patch("src.services.export_service.get_active_terms")
    def test_export_with_adapter_success(self, mock_terms, mock_users, mock_courses):
        """Test successful export with adapter."""
        # Mock some data
        mock_courses.return_value = [{"course_id": "1", "course_number": "TEST-101"}]
        mock_users.return_value = [{"user_id": "1", "email": "test@example.com"}]
        mock_terms.return_value = [{"term_id": "1", "term_name": "Fall 2024"}]

        service = ExportService()

        # Mock the adapter registry to return a working adapter
        with patch.object(service.registry, "get_adapter_by_id") as mock_get_adapter:
            mock_adapter = Mock()
            mock_adapter.supports_export.return_value = True
            mock_adapter.export_data.return_value = (True, "Export successful", 5)
            mock_get_adapter.return_value = mock_adapter

            config = ExportConfig(
                institution_id="test-institution", adapter_id="test_adapter"
            )

            with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
                result = service.export_data(config, tmp.name)

            assert result.success is True
            assert result.records_exported == 5
            assert result.file_path == tmp.name

    def test_export_data_with_registry_error(self):
        """Test export_data when adapter registry throws an error."""
        service = ExportService()

        # Mock the registry to throw an error
        with patch.object(service.registry, "get_adapter_by_id") as mock_get_adapter:
            from src.adapters.adapter_registry import AdapterRegistryError

            mock_get_adapter.side_effect = AdapterRegistryError("Registry error")

            config = ExportConfig(
                institution_id="test-institution", adapter_id="test_adapter"
            )

            with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
                result = service.export_data(config, tmp.name)

            assert result.success is False
            assert "Failed to get adapter test_adapter: Registry error" in result.errors


class TestCreateExportService:
    """Test the factory function."""

    def test_create_export_service(self):
        """Test the factory function creates a service."""
        from src.services.export_service import create_export_service

        service = create_export_service()
        assert isinstance(service, ExportService)
        assert service.registry is not None
