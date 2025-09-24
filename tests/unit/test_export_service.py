"""
Unit tests for ExportService

Tests the export functionality including adapter pattern, data formatting,
and Excel file generation.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from export_service import ExportConfig, ExportResult, ExportService


class TestExportService:
    """Test cases for ExportService functionality."""

    def test_init(self):
        """Test ExportService initialization."""
        service = ExportService()
        assert service.supported_adapters is not None
        assert "cei_excel_adapter" in service.supported_adapters
        assert "default_adapter" in service.supported_adapters

    def test_export_config_creation(self):
        """Test ExportConfig dataclass creation."""
        config = ExportConfig(
            institution_id="test-institution",
            adapter_name="cei_excel_adapter",
            export_view="standard",
        )
        assert config.institution_id == "test-institution"
        assert config.adapter_name == "cei_excel_adapter"
        assert config.export_view == "standard"
        assert config.include_metadata is True  # Default value
        assert config.output_format == "xlsx"  # Default value

    def test_export_result_creation(self):
        """Test ExportResult dataclass creation."""
        result = ExportResult(success=True, records_exported=5)
        assert result.success is True
        assert result.records_exported == 5
        assert result.errors == []  # Default empty list
        assert result.warnings == []  # Default empty list
        assert result.export_timestamp is not None  # Auto-generated

    def test_unsupported_adapter(self):
        """Test export with unsupported adapter."""
        service = ExportService()
        config = ExportConfig(
            institution_id="test-institution", adapter_name="nonexistent_adapter"
        )

        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
            result = service.export_data(config, tmp.name)

        assert result.success is False
        assert "Unsupported adapter: nonexistent_adapter" in result.errors

    @patch("export_service.get_all_courses")
    @patch("export_service.get_all_users")
    @patch("export_service.get_active_terms")
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
        assert "offerings" in data
        assert "sections" in data

    @patch("export_service.get_all_courses")
    @patch("export_service.get_all_users")
    @patch("export_service.get_active_terms")
    def test_fetch_export_data_with_data(self, mock_terms, mock_users, mock_courses):
        """Test fetching export data when data exists."""
        # Mock data
        mock_courses.return_value = [
            {"course_number": "MATH-101", "department": "MATH"}
        ]
        mock_users.return_value = [{"email": "test@example.com", "role": "instructor"}]
        mock_terms.return_value = [
            {"name": "Fall 2024", "year": 2024, "season": "Fall"}
        ]

        service = ExportService()
        data = service._fetch_export_data("test-institution")

        assert len(data["courses"]) == 1
        assert len(data["users"]) == 1
        assert len(data["terms"]) == 1
        assert data["courses"][0]["course_number"] == "MATH-101"
        assert data["users"][0]["email"] == "test@example.com"

    @patch("export_service.get_all_courses")
    @patch("export_service.get_all_users")
    @patch("export_service.get_active_terms")
    def test_export_no_data(self, mock_terms, mock_users, mock_courses):
        """Test export when no data is available."""
        # Mock empty data
        mock_courses.return_value = []
        mock_users.return_value = []
        mock_terms.return_value = []

        service = ExportService()
        config = ExportConfig(
            institution_id="test-institution", adapter_name="cei_excel_adapter"
        )

        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
            result = service.export_data(config, tmp.name)

        assert result.success is False
        assert "No valid records to export" in result.errors

    def test_build_cei_record_empty_course(self):
        """Test building CEI record with empty course data."""
        service = ExportService()
        record = service._build_cei_record(None, None, None)
        assert record is None

    def test_build_cei_record_with_course(self):
        """Test building CEI record with course data."""
        service = ExportService()
        course = {"course_number": "MATH-101"}
        instructor = {"email": "test@example.com"}
        term = {"year": 2024, "season": "Fall"}

        record = service._build_cei_record(course, instructor, term)

        assert record is not None
        assert record["course"] == "MATH-101"
        assert record["email"] == "test@example.com"
        assert record["Term"] == "2024 Fall"
        assert record["cannot reconcile (y/n)"] == "n"
        assert "Enrolled Students" in record
        assert "celebrations" in record

    def test_format_term_for_cei_empty(self):
        """Test formatting empty term for CEI."""
        service = ExportService()
        result = service._format_term_for_cei(None)
        assert result == ""

    def test_format_term_for_cei_with_data(self):
        """Test formatting term with data for CEI."""
        service = ExportService()
        term = {"year": 2024, "season": "Fall"}
        result = service._format_term_for_cei(term)
        assert result == "2024 Fall"

    def test_format_term_for_cei_fallback(self):
        """Test formatting term with fallback to name."""
        service = ExportService()
        term = {"name": "Spring 2025"}
        result = service._format_term_for_cei(term)
        assert result == "Spring 2025"

    def test_find_instructor_for_course_empty(self):
        """Test finding instructor when no users exist."""
        service = ExportService()
        course = {"course_number": "MATH-101"}
        users = []

        result = service._find_instructor_for_course(course, users)
        assert result is None

    def test_find_instructor_for_course_found(self):
        """Test finding instructor when instructors exist."""
        service = ExportService()
        course = {"course_number": "MATH-101"}
        users = [
            {"role": "student", "email": "student@example.com"},
            {"role": "instructor", "email": "instructor@example.com"},
        ]

        result = service._find_instructor_for_course(course, users)
        assert result is not None
        assert result["email"] == "instructor@example.com"

    def test_find_term_for_course_empty(self):
        """Test finding term when no terms exist."""
        service = ExportService()
        course = {"course_number": "MATH-101"}
        terms = []

        result = service._find_term_for_course(course, terms)
        assert result is None

    def test_find_term_for_course_found(self):
        """Test finding term when terms exist."""
        service = ExportService()
        course = {"course_number": "MATH-101"}
        terms = [
            {"year": 2023, "season": "Fall"},
            {"year": 2024, "season": "Spring"},  # Should pick this one (most recent)
        ]

        result = service._find_term_for_course(course, terms)
        assert result is not None
        assert result["year"] == 2024

    def test_default_adapter_not_implemented(self):
        """Test that default adapter export is not yet implemented."""
        service = ExportService()
        config = ExportConfig(
            institution_id="test-institution", adapter_name="default_adapter"
        )

        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
            # Mock some data so we don't fail on empty data
            with patch.object(service, "_fetch_export_data") as mock_fetch:
                mock_fetch.return_value = {
                    "courses": [{"course_number": "TEST-101"}],
                    "users": [{"role": "instructor"}],
                    "terms": [{"year": 2024}],
                    "offerings": [],
                    "sections": [],
                }

                result = service.export_data(config, tmp.name)

        assert result.success is False
        assert "Default adapter export not yet implemented" in result.errors


class TestCreateExportService:
    """Test the factory function."""

    def test_create_export_service(self):
        """Test the factory function creates a service."""
        from export_service import create_export_service

        service = create_export_service()
        assert isinstance(service, ExportService)
        assert service.supported_adapters is not None
