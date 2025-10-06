"""
Unit tests for Generic CSV Adapter

Tests the export and import functionality of the generic CSV adapter
using a test-driven development (TDD) approach.
"""

import csv
import json
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest

from adapters.generic_csv_adapter import CSV_COLUMNS, EXPORT_ORDER, GenericCSVAdapter


@pytest.mark.unit
class TestGenericCSVAdapterMetadata:
    """Test adapter metadata and info methods."""

    def test_get_adapter_info_returns_required_fields(self):
        """Adapter info should contain all required metadata fields."""
        adapter = GenericCSVAdapter()
        info = adapter.get_adapter_info()

        # Required fields
        assert info["id"] == "generic_csv_v1"
        assert info["name"] == "Generic CSV Format (ZIP)"
        assert info["institution_id"] is None  # Generic adapter
        assert ".zip" in info["supported_formats"]
        assert info["is_bidirectional"] is True
        assert info["version"] == "1.0"

    def test_adapter_supports_all_entity_types(self):
        """Adapter should declare support for all core entity types."""
        adapter = GenericCSVAdapter()
        info = adapter.get_adapter_info()

        expected_types = [
            "institutions",
            "programs",
            "users",
            "courses",
            "terms",
            "course_offerings",
            "course_sections",
        ]

        for entity_type in expected_types:
            assert entity_type in info["data_types"]


@pytest.mark.unit
class TestGenericCSVAdapterValidation:
    """Test file validation functionality."""

    def test_validate_non_zip_file_fails(self, tmp_path):
        """Non-ZIP files should fail validation."""
        adapter = GenericCSVAdapter()

        # Create a text file
        test_file = tmp_path / "test.txt"
        test_file.write_text("not a zip")

        is_valid, message = adapter.validate_file_compatibility(str(test_file))

        assert is_valid is False
        assert "Invalid file type" in message

    def test_validate_zip_without_manifest_fails(self, tmp_path):
        """ZIP without manifest.json should fail validation."""
        adapter = GenericCSVAdapter()

        # Create ZIP without manifest
        zip_file = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("institutions.csv", "id,name\n")

        is_valid, message = adapter.validate_file_compatibility(str(zip_file))

        assert is_valid is False
        assert "Missing manifest.json" in message

    def test_validate_zip_with_wrong_version_fails(self, tmp_path):
        """ZIP with incompatible version should fail validation."""
        adapter = GenericCSVAdapter()

        # Create ZIP with wrong version
        zip_file = tmp_path / "test.zip"
        manifest = {"format_version": "2.0"}

        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr("institutions.csv", "id,name\n")

        is_valid, message = adapter.validate_file_compatibility(str(zip_file))

        assert is_valid is False
        assert "Incompatible format version" in message

    def test_validate_valid_zip_succeeds(self, tmp_path):
        """Valid ZIP with correct manifest should pass validation."""
        adapter = GenericCSVAdapter()

        # Create valid ZIP
        zip_file = tmp_path / "test.zip"
        manifest = {
            "format_version": "1.0",
            "entity_counts": {"institutions": 1, "users": 5},
        }

        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr("institutions.csv", "id,name\n")

        is_valid, message = adapter.validate_file_compatibility(str(zip_file))

        assert is_valid is True
        assert "6 total records" in message


@pytest.mark.unit
class TestGenericCSVAdapterExport:
    """Test export functionality (TDD - tests written first)."""

    def test_export_empty_data_creates_valid_zip(self, tmp_path):
        """Exporting empty data should create valid ZIP with manifest."""
        adapter = GenericCSVAdapter()
        output_file = tmp_path / "export.zip"

        # Empty data for all entities
        data = {entity: [] for entity in EXPORT_ORDER}

        success, message, count = adapter.export_data(
            data, str(output_file), options={}
        )

        assert success is True
        assert count == 0
        assert output_file.exists()

        # Verify ZIP structure
        with zipfile.ZipFile(output_file, "r") as zf:
            files = zf.namelist()
            assert "manifest.json" in files

            # Read manifest
            manifest = json.loads(zf.read("manifest.json"))
            assert manifest["format_version"] == "1.0"
            assert manifest["entity_counts"]["institutions"] == 0

    def test_export_single_institution(self, tmp_path):
        """Export with single institution should create correct CSV."""
        adapter = GenericCSVAdapter()
        output_file = tmp_path / "export.zip"

        # Single institution
        data = {
            "institutions": [
                {
                    "id": "inst-1",
                    "name": "Test University",
                    "short_name": "TU",
                    "admin_email": "admin@test.edu",
                    "is_active": True,
                    "created_at": datetime(2024, 1, 1),
                    "updated_at": datetime(2024, 10, 1),
                }
            ]
        }
        # Empty for other entities
        for entity in EXPORT_ORDER:
            if entity not in data:
                data[entity] = []

        success, message, count = adapter.export_data(
            data, str(output_file), options={}
        )

        assert success is True
        assert count == 1

        # Verify institutions.csv content
        with zipfile.ZipFile(output_file, "r") as zf:
            csv_content = zf.read("institutions.csv").decode("utf-8")
            lines = csv_content.strip().split("\n")

            # Should have header + 1 data row
            assert len(lines) == 2
            assert "id,name,short_name" in lines[0]
            assert "inst-1,Test University,TU" in lines[1]

    def test_export_excludes_sensitive_user_fields(self, tmp_path):
        """User export should exclude password_hash and tokens."""
        adapter = GenericCSVAdapter()
        output_file = tmp_path / "export.zip"

        # User with sensitive fields
        data = {
            "users": [
                {
                    "id": "user-1",
                    "email": "test@example.edu",
                    "password_hash": "$2b$12$SENSITIVE_HASH",  # Should be excluded
                    "password_reset_token": "secret-token",  # Should be excluded
                    "email_verification_token": "verify-token",  # Should be excluded
                    "first_name": "John",
                    "last_name": "Doe",
                    "role": "instructor",
                    "institution_id": "inst-1",
                    "created_at": datetime(2024, 1, 1),
                    "updated_at": datetime(2024, 10, 1),
                }
            ]
        }
        # Empty for other entities
        for entity in EXPORT_ORDER:
            if entity not in data:
                data[entity] = []

        success, message, count = adapter.export_data(
            data, str(output_file), options={}
        )

        assert success is True

        # Verify sensitive fields are excluded
        with zipfile.ZipFile(output_file, "r") as zf:
            csv_content = zf.read("users.csv").decode("utf-8")
            csv_reader = csv.DictReader(csv_content.splitlines())
            rows = list(csv_reader)

            assert len(rows) == 1
            user = rows[0]

            # Should have safe fields
            assert user["email"] == "test@example.edu"
            assert user["first_name"] == "John"

            # Should NOT have sensitive fields
            assert "password_hash" not in user
            assert "password_reset_token" not in user
            assert "email_verification_token" not in user

    def test_export_serializes_json_fields(self, tmp_path):
        """Export should serialize JSON/dict fields as JSON strings."""
        adapter = GenericCSVAdapter()
        output_file = tmp_path / "export.zip"

        # Section with JSON grade_distribution
        data = {
            "course_sections": [
                {
                    "id": "section-1",
                    "offering_id": "off-1",
                    "instructor_id": "user-1",
                    "section_number": "001",
                    "enrollment": 25,
                    "status": "in_progress",
                    "grade_distribution": {"A": 10, "B": 8, "C": 5, "D": 2},  # JSON
                    "created_at": datetime(2024, 1, 1),
                    "updated_at": datetime(2024, 10, 1),
                }
            ]
        }
        # Empty for other entities
        for entity in EXPORT_ORDER:
            if entity not in data:
                data[entity] = []

        success, message, count = adapter.export_data(
            data, str(output_file), options={}
        )

        assert success is True

        # Verify JSON serialization
        with zipfile.ZipFile(output_file, "r") as zf:
            csv_content = zf.read("course_sections.csv").decode("utf-8")
            csv_reader = csv.DictReader(csv_content.splitlines())
            rows = list(csv_reader)

            section = rows[0]
            grade_dist = json.loads(section["grade_distribution"])

            assert grade_dist["A"] == 10
            assert grade_dist["B"] == 8

    def test_export_respects_entity_order(self, tmp_path):
        """Export should create CSVs in correct dependency order."""
        adapter = GenericCSVAdapter()
        output_file = tmp_path / "export.zip"

        # Data with dependencies
        data = {
            "institutions": [{"id": "inst-1", "name": "Test", "short_name": "T"}],
            "users": [
                {"id": "user-1", "email": "test@test.edu", "institution_id": "inst-1"}
            ],
            "programs": [{"id": "prog-1", "name": "CS", "institution_id": "inst-1"}],
        }
        # Empty for other entities
        for entity in EXPORT_ORDER:
            if entity not in data:
                data[entity] = []

        success, message, count = adapter.export_data(
            data, str(output_file), options={}
        )

        assert success is True

        # Verify files exist in ZIP
        with zipfile.ZipFile(output_file, "r") as zf:
            files = zf.namelist()

            # All entity CSVs should be present (even if empty)
            assert "institutions.csv" in files
            assert "users.csv" in files
            assert "programs.csv" in files

    def test_export_creates_accurate_manifest(self, tmp_path):
        """Manifest should accurately reflect entity counts."""
        adapter = GenericCSVAdapter()
        output_file = tmp_path / "export.zip"

        # Data with known counts
        data = {
            "institutions": [{"id": f"inst-{i}"} for i in range(2)],  # 2
            "users": [{"id": f"user-{i}"} for i in range(5)],  # 5
            "programs": [{"id": f"prog-{i}"} for i in range(3)],  # 3
        }
        # Empty for other entities
        for entity in EXPORT_ORDER:
            if entity not in data:
                data[entity] = []

        success, message, count = adapter.export_data(
            data, str(output_file), options={}
        )

        assert success is True
        assert count == 10  # Total records

        # Verify manifest accuracy
        with zipfile.ZipFile(output_file, "r") as zf:
            manifest = json.loads(zf.read("manifest.json"))

            assert manifest["entity_counts"]["institutions"] == 2
            assert manifest["entity_counts"]["users"] == 5
            assert manifest["entity_counts"]["programs"] == 3

    def test_export_handles_datetime_serialization(self, tmp_path):
        """Export should serialize datetime objects to ISO format."""
        adapter = GenericCSVAdapter()
        output_file = tmp_path / "export.zip"

        # Data with datetime
        test_date = datetime(2024, 10, 5, 15, 30, 45)
        data = {
            "institutions": [
                {
                    "id": "inst-1",
                    "name": "Test",
                    "created_at": test_date,
                    "updated_at": test_date,
                }
            ]
        }
        # Empty for other entities
        for entity in EXPORT_ORDER:
            if entity not in data:
                data[entity] = []

        success, message, count = adapter.export_data(
            data, str(output_file), options={}
        )

        assert success is True

        # Verify datetime format
        with zipfile.ZipFile(output_file, "r") as zf:
            csv_content = zf.read("institutions.csv").decode("utf-8")
            csv_reader = csv.DictReader(csv_content.splitlines())
            rows = list(csv_reader)

            inst = rows[0]
            # Should be ISO format
            assert "2024-10-05" in inst["created_at"]
            assert "T" in inst["created_at"]  # ISO separator
