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
        """User export includes password_hash (for test fixtures) but excludes active tokens."""
        adapter = GenericCSVAdapter()
        output_file = tmp_path / "export.zip"

        # User with sensitive fields
        data = {
            "users": [
                {
                    "id": "user-1",
                    "email": "test@example.edu",
                    "password_hash": "$2b$12$SENSITIVE_HASH",  # Now included for test fixtures
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

        # Verify sensitive fields handling
        with zipfile.ZipFile(output_file, "r") as zf:
            csv_content = zf.read("users.csv").decode("utf-8")
            csv_reader = csv.DictReader(csv_content.splitlines())
            rows = list(csv_reader)

            assert len(rows) == 1
            user = rows[0]

            # Should have safe fields
            assert user["email"] == "test@example.edu"
            assert user["first_name"] == "John"

            # Should have password_hash (for test fixtures)
            assert user["password_hash"] == "$2b$12$SENSITIVE_HASH"

            # Should NOT have active tokens (still sensitive)
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


@pytest.mark.unit
class TestGenericCSVAdapterImport:
    """Test import functionality (TDD - tests written first)."""

    def test_parse_file_validates_zip_format(self, tmp_path):
        """Import should reject non-ZIP files."""
        adapter = GenericCSVAdapter()

        # Create a text file
        invalid_file = tmp_path / "test.txt"
        invalid_file.write_text("not a zip")

        with pytest.raises(Exception) as exc_info:
            adapter.parse_file(str(invalid_file), options={})

        assert "not a valid zip" in str(exc_info.value).lower()

    def test_parse_file_validates_manifest_exists(self, tmp_path):
        """Import should reject ZIP without manifest."""
        adapter = GenericCSVAdapter()

        # Create ZIP without manifest
        zip_file = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("users.csv", "id,email\nuser-1,test@test.edu\n")

        with pytest.raises(Exception) as exc_info:
            adapter.parse_file(str(zip_file), options={})

        assert "manifest" in str(exc_info.value).lower()

    def test_parse_file_validates_format_version(self, tmp_path):
        """Import should reject incompatible format versions."""
        adapter = GenericCSVAdapter()

        # Create ZIP with wrong version
        zip_file = tmp_path / "test.zip"
        manifest = {"format_version": "2.0", "entity_counts": {}}

        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr("users.csv", "id,email\n")

        with pytest.raises(Exception) as exc_info:
            adapter.parse_file(str(zip_file), options={})

        assert (
            "incompatible" in str(exc_info.value).lower()
            or "version" in str(exc_info.value).lower()
        )

    def test_parse_file_parses_valid_export(self, tmp_path):
        """Import should successfully parse valid CSV export."""
        adapter = GenericCSVAdapter()

        # Create valid ZIP
        zip_file = tmp_path / "test.zip"
        manifest = {
            "format_version": "1.0",
            "entity_counts": {"institutions": 1, "users": 2},
            "import_order": ["institutions", "users"],
        }

        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr(
                "institutions.csv",
                "id,name,short_name\ninst-1,Test University,TU\n",
            )
            zf.writestr(
                "users.csv",
                "id,email,first_name,last_name,role,institution_id\n"
                "user-1,test1@test.edu,John,Doe,instructor,inst-1\n"
                "user-2,test2@test.edu,Jane,Smith,instructor,inst-1\n",
            )

        result = adapter.parse_file(str(zip_file), options={})

        # Should return dict with entity types
        assert "institutions" in result
        assert "users" in result

        # Should parse records correctly
        assert len(result["institutions"]) == 1
        assert len(result["users"]) == 2

        # Check data structure
        inst = result["institutions"][0]
        assert inst["id"] == "inst-1"
        assert inst["name"] == "Test University"

        user = result["users"][0]
        assert user["email"] == "test1@test.edu"
        assert user["first_name"] == "John"

    def test_parse_file_respects_import_order(self, tmp_path):
        """Import should parse entities in dependency order."""
        adapter = GenericCSVAdapter()

        # Create ZIP with specified import order
        zip_file = tmp_path / "test.zip"
        manifest = {
            "format_version": "1.0",
            "entity_counts": {"institutions": 1, "programs": 1, "users": 1},
            "import_order": ["institutions", "programs", "users"],
        }

        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr("institutions.csv", "id,name\ninst-1,Test\n")
            zf.writestr("programs.csv", "id,name,institution_id\nprog-1,CS,inst-1\n")
            zf.writestr("users.csv", "id,email,institution_id\nuser-1,t@t.edu,inst-1\n")

        result = adapter.parse_file(str(zip_file), options={})

        # All entities should be present
        assert "institutions" in result
        assert "programs" in result
        assert "users" in result

    def test_parse_file_deserializes_json_fields(self, tmp_path):
        """Import should deserialize JSON field strings back to dicts."""
        adapter = GenericCSVAdapter()

        # Create ZIP with JSON fields
        zip_file = tmp_path / "test.zip"
        manifest = {
            "format_version": "1.0",
            "entity_counts": {"course_sections": 1},
            "import_order": ["course_sections"],
        }

        grade_dist = {"A": 10, "B": 8, "C": 5}

        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            # Use csv.writer to properly quote JSON fields
            import io

            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(["id", "section_number", "grade_distribution"])
            writer.writerow(["section-1", "001", json.dumps(grade_dist)])
            zf.writestr("course_sections.csv", csv_buffer.getvalue())

        result = adapter.parse_file(str(zip_file), options={})

        section = result["course_sections"][0]

        # JSON field should be deserialized
        assert isinstance(section["grade_distribution"], dict)
        assert section["grade_distribution"]["A"] == 10

    def test_parse_file_deserializes_datetime_fields(self, tmp_path):
        """Import should deserialize ISO datetime strings to Python datetime objects."""
        adapter = GenericCSVAdapter()

        # Create ZIP with datetime fields
        zip_file = tmp_path / "test.zip"
        manifest = {
            "format_version": "1.0",
            "entity_counts": {"institutions": 1},
            "import_order": ["institutions"],
        }

        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr(
                "institutions.csv",
                "id,name,created_at\n" "inst-1,Test,2024-10-05T15:30:45.123456Z\n",
            )

        result = adapter.parse_file(str(zip_file), options={})

        inst = result["institutions"][0]

        # Datetime should be parsed to Python datetime object (required by SQLite)
        assert "created_at" in inst
        from datetime import datetime

        assert isinstance(inst["created_at"], datetime)
        assert inst["created_at"].year == 2024
        assert inst["created_at"].month == 10
        assert inst["created_at"].day == 5

    def test_parse_file_deserializes_boolean_fields(self, tmp_path):
        """Import should deserialize boolean strings to actual booleans."""
        adapter = GenericCSVAdapter()

        # Create ZIP with boolean fields
        zip_file = tmp_path / "test.zip"
        manifest = {
            "format_version": "1.0",
            "entity_counts": {"institutions": 2},
            "import_order": ["institutions"],
        }

        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr(
                "institutions.csv",
                "id,name,is_active\n" "inst-1,Test1,true\n" "inst-2,Test2,false\n",
            )

        result = adapter.parse_file(str(zip_file), options={})

        # Booleans should be parsed correctly
        assert result["institutions"][0]["is_active"] is True
        assert result["institutions"][1]["is_active"] is False

    def test_parse_file_handles_empty_strings_as_null(self, tmp_path):
        """Import should treat empty strings as NULL values."""
        adapter = GenericCSVAdapter()

        # Create ZIP with empty fields
        zip_file = tmp_path / "test.zip"
        manifest = {
            "format_version": "1.0",
            "entity_counts": {"users": 1},
            "import_order": ["users"],
        }

        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr(
                "users.csv",
                "id,email,display_name,oauth_provider\n"
                "user-1,test@test.edu,,\n",  # Empty display_name and oauth_provider
            )

        result = adapter.parse_file(str(zip_file), options={})

        user = result["users"][0]

        # Empty strings should be None
        assert user["display_name"] is None or user["display_name"] == ""
        assert user["oauth_provider"] is None or user["oauth_provider"] == ""

    def test_parse_file_handles_malformed_csv(self, tmp_path):
        """Import should handle malformed CSV gracefully."""
        adapter = GenericCSVAdapter()

        # Create ZIP with malformed CSV
        zip_file = tmp_path / "test.zip"
        manifest = {
            "format_version": "1.0",
            "entity_counts": {"users": 1},
            "import_order": ["users"],
        }

        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr(
                "users.csv",
                "id,email,first_name\n" "user-1,incomplete\n",  # Missing field
            )

        # Should either raise exception or handle gracefully
        try:
            result = adapter.parse_file(str(zip_file), options={})
            # If it doesn't raise, check that error handling occurred
            assert "users" in result
        except Exception as e:
            # Acceptable to raise exception for malformed data
            assert "malformed" in str(e).lower() or "invalid" in str(e).lower()

    def test_parse_file_returns_all_entity_types(self, tmp_path):
        """Import should return data for all expected entity types."""
        adapter = GenericCSVAdapter()

        # Create comprehensive export
        zip_file = tmp_path / "test.zip"
        manifest = {
            "format_version": "1.0",
            "entity_counts": {
                "institutions": 1,
                "programs": 1,
                "users": 1,
                "courses": 1,
                "terms": 1,
            },
            "import_order": [
                "institutions",
                "programs",
                "users",
                "courses",
                "terms",
            ],
        }

        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr("institutions.csv", "id,name\ninst-1,Test\n")
            zf.writestr("programs.csv", "id,name\nprog-1,CS\n")
            zf.writestr("users.csv", "id,email\nuser-1,t@t.edu\n")
            zf.writestr("courses.csv", "id,course_number\ncourse-1,CS101\n")
            zf.writestr("terms.csv", "id,term_name\nterm-1,FA2024\n")

        result = adapter.parse_file(str(zip_file), options={})

        # All entity types should be present
        expected_entities = ["institutions", "programs", "users", "courses", "terms"]
        for entity in expected_entities:
            assert entity in result
            assert len(result[entity]) > 0

    def test_comprehensive_realistic_export_import_roundtrip(self, tmp_path):
        """
        Comprehensive test with realistic data exercising all entity types,
        relationships, JSON fields, booleans, NULLs, and edge cases.
        """
        adapter = GenericCSVAdapter()
        output_file = tmp_path / "comprehensive_export.zip"

        # Create realistic mini-university dataset
        data = {
            "institutions": [
                {
                    "id": "hogwarts-001",
                    "name": "Hogwarts School of Witchcraft",
                    "short_name": "HOGW",
                    "admin_email": "dumbledore@hogwarts.edu",
                    "is_active": True,
                    "allow_self_registration": False,
                    "created_at": datetime(2024, 9, 1, 8, 0, 0),
                },
                {
                    "id": "starfleet-002",
                    "name": "Starfleet Academy",
                    "short_name": "SFA",
                    "admin_email": "picard@starfleet.edu",
                    "is_active": True,
                    "allow_self_registration": True,
                    "created_at": datetime(2024, 9, 1, 9, 0, 0),
                },
            ],
            "programs": [
                {
                    "id": "prog-gryff",
                    "name": "Gryffindor House Program",
                    "short_name": "GRYF",
                    "institution_id": "hogwarts-001",
                    "is_active": True,
                    "is_default": True,
                },
                {
                    "id": "prog-slytherin",
                    "name": "Slytherin House Program",
                    "short_name": "SLYT",
                    "institution_id": "hogwarts-001",
                    "is_active": True,
                    "is_default": False,
                },
                {
                    "id": "prog-command",
                    "name": "Command Track",
                    "short_name": "CMD",
                    "institution_id": "starfleet-002",
                    "is_active": True,
                    "is_default": True,
                },
            ],
            "users": [
                {
                    "id": "user-harry",
                    "email": "harry@hogwarts.edu",
                    "first_name": "Harry",
                    "last_name": "Potter",
                    "display_name": None,  # NULL test
                    "role": "instructor",
                    "institution_id": "hogwarts-001",
                },
                {
                    "id": "user-hermione",
                    "email": "hermione@hogwarts.edu",
                    "first_name": "Hermione",
                    "last_name": "Granger",
                    "display_name": "Prof. Granger",
                    "role": "program_admin",
                    "institution_id": "hogwarts-001",
                    "oauth_provider": "google",  # OAuth test
                },
                {
                    "id": "user-kirk",
                    "email": "kirk@starfleet.edu",
                    "first_name": "James",
                    "last_name": "Kirk",
                    "display_name": "Captain Kirk",
                    "role": "instructor",
                    "institution_id": "starfleet-002",
                },
            ],
            "user_programs": [  # Many-to-many relationships
                {"user_id": "user-harry", "program_id": "prog-gryff"},
                {
                    "user_id": "user-harry",
                    "program_id": "prog-slytherin",
                },  # Multi-program
                {"user_id": "user-hermione", "program_id": "prog-gryff"},
                {"user_id": "user-kirk", "program_id": "prog-command"},
            ],
            "courses": [
                {
                    "id": "course-potions",
                    "course_number": "POTION-101",
                    "course_title": "Introduction to Potions",
                    "department": "Potions",
                    "credit_hours": 3,
                    "institution_id": "hogwarts-001",
                    "active": True,
                },
                {
                    "id": "course-defense",
                    "course_number": "DADA-201",
                    "course_title": "Defense Against Dark Arts",
                    "department": "Defense",
                    "credit_hours": 4,
                    "institution_id": "hogwarts-001",
                    "active": True,
                },
                {
                    "id": "course-warp",
                    "course_number": "WARP-301",
                    "course_title": "Warp Core Theory",
                    "department": "Engineering",
                    "credit_hours": 3,
                    "institution_id": "starfleet-002",
                    "active": True,
                },
                {
                    "id": "course-old",
                    "course_number": "OLD-999",
                    "course_title": "Deprecated Course",
                    "department": "Old",
                    "credit_hours": 0,
                    "institution_id": "hogwarts-001",
                    "active": False,  # Inactive course test
                },
            ],
            "course_programs": [  # Many-to-many
                {"course_id": "course-potions", "program_id": "prog-gryff"},
                {"course_id": "course-defense", "program_id": "prog-gryff"},
                {
                    "course_id": "course-defense",
                    "program_id": "prog-slytherin",
                },  # Multi-program
                {"course_id": "course-warp", "program_id": "prog-command"},
            ],
            "terms": [
                {
                    "id": "term-fall24",
                    "term_name": "FA2024",
                    "name": "Fall 2024",
                    "start_date": datetime(2024, 9, 1),
                    "end_date": datetime(2024, 12, 15),
                    "active": True,
                    "institution_id": "hogwarts-001",
                },
                {
                    "id": "term-spring25",
                    "term_name": "SP2025",
                    "name": "Spring 2025",
                    "start_date": datetime(2025, 1, 15),
                    "end_date": datetime(2025, 5, 15),
                    "active": True,
                    "institution_id": "starfleet-002",
                },
            ],
            "course_offerings": [
                {
                    "id": "offer-potions-f24",
                    "course_id": "course-potions",
                    "term_id": "term-fall24",
                    "institution_id": "hogwarts-001",
                    "status": "in_progress",
                    "capacity": 30,
                    "total_enrollment": 28,
                    "section_count": 2,
                },
                {
                    "id": "offer-defense-f24",
                    "course_id": "course-defense",
                    "term_id": "term-fall24",
                    "institution_id": "hogwarts-001",
                    "status": "completed",
                    "capacity": 25,
                    "total_enrollment": 25,
                    "section_count": 1,
                },
            ],
            "course_sections": [
                {
                    "id": "section-pot-001",
                    "offering_id": "offer-potions-f24",
                    "instructor_id": "user-harry",
                    "section_number": "001",
                    "enrollment": 15,
                    "status": "in_progress",
                    "grade_distribution": {"O": 5, "E": 6, "A": 3, "P": 1},  # JSON
                },
                {
                    "id": "section-pot-002",
                    "offering_id": "offer-potions-f24",
                    "instructor_id": "user-hermione",
                    "section_number": "002",
                    "enrollment": 13,
                    "status": "in_progress",
                    "grade_distribution": {"O": 7, "E": 4, "A": 2},
                },
                {
                    "id": "section-def-001",
                    "offering_id": "offer-defense-f24",
                    "instructor_id": "user-harry",
                    "section_number": "001",
                    "enrollment": 25,
                    "status": "completed",
                    "grade_distribution": {"O": 10, "E": 10, "A": 4, "P": 1},
                },
            ],
            "course_outcomes": [
                {
                    "id": "outcome-pot-clo1",
                    "course_id": "course-potions",
                    "clo_number": "CLO1",
                    "description": "Students will brew basic potions correctly",
                    "assessment_method": "Practical Exam",
                    "active": True,
                    "assessment_data": {"pass_rate": 0.95, "avg_score": 88.5},  # JSON
                },
                {
                    "id": "outcome-def-clo1",
                    "course_id": "course-defense",
                    "clo_number": "CLO1",
                    "description": "Students will defend against dark creatures",
                    "assessment_method": "Practical Defense",
                    "active": True,
                    "assessment_data": {"pass_rate": 0.92, "avg_score": 85.0},
                },
                {
                    "id": "outcome-def-clo2",
                    "course_id": "course-defense",
                    "clo_number": "CLO2",
                    "description": "Students will recognize dark magic",
                    "assessment_method": "Written Exam",
                    "active": False,  # Inactive outcome
                    "assessment_data": None,  # NULL JSON field
                },
            ],
            "user_invitations": [
                {
                    "id": "invite-snape",
                    "email": "snape@hogwarts.edu",
                    "role": "instructor",
                    "institution_id": "hogwarts-001",
                    "invited_by": "user-hermione",
                    "invited_at": datetime(2024, 10, 1),
                    "status": "pending",
                    "personal_message": "We need your expertise in potions!",
                },
                {
                    "id": "invite-spock",
                    "email": "spock@starfleet.edu",
                    "role": "instructor",
                    "institution_id": "starfleet-002",
                    "invited_by": "user-kirk",
                    "invited_at": datetime(2024, 10, 5),
                    "status": "pending",
                    "personal_message": None,  # NULL message
                },
            ],
        }

        # Export
        success, msg, count = adapter.export_data(data, str(output_file), {})

        assert success is True
        # Total: 2 inst + 3 prog + 3 users + 4 user_prog + 4 courses + 4 course_prog + 2 terms + 2 offerings + 3 sections + 3 outcomes + 2 invites = 32
        assert count == 32

        # Import back
        result = adapter.parse_file(str(output_file), {})

        # Verify all entities imported
        assert len(result["institutions"]) == 2
        assert len(result["programs"]) == 3
        assert len(result["users"]) == 3
        assert len(result["user_programs"]) == 4
        assert len(result["courses"]) == 4
        assert len(result["course_programs"]) == 4
        assert len(result["terms"]) == 2
        assert len(result["course_offerings"]) == 2
        assert len(result["course_sections"]) == 3
        assert len(result["course_outcomes"]) == 3
        assert len(result["user_invitations"]) == 2

        # Verify data integrity - spot checks
        hogwarts = result["institutions"][0]
        assert hogwarts["name"] == "Hogwarts School of Witchcraft"
        assert hogwarts["is_active"] is True  # Boolean

        hermione = [u for u in result["users"] if u["id"] == "user-hermione"][0]
        assert hermione["display_name"] == "Prof. Granger"
        assert hermione["oauth_provider"] == "google"

        harry = [u for u in result["users"] if u["id"] == "user-harry"][0]
        assert harry["display_name"] is None  # NULL preserved

        # Verify many-to-many relationships
        harry_programs = [
            up for up in result["user_programs"] if up["user_id"] == "user-harry"
        ]
        assert len(harry_programs) == 2  # Harry in 2 programs

        # Verify JSON deserialization
        section = result["course_sections"][0]
        assert isinstance(section["grade_distribution"], dict)
        assert "O" in section["grade_distribution"]

        outcome = result["course_outcomes"][0]
        assert isinstance(outcome["assessment_data"], dict)
        assert outcome["assessment_data"]["pass_rate"] == 0.95

        # Verify NULL JSON
        inactive_outcome = [
            o for o in result["course_outcomes"] if o["id"] == "outcome-def-clo2"
        ][0]
        assert inactive_outcome["assessment_data"] is None

        # Verify inactive/active flags
        old_course = [c for c in result["courses"] if c["id"] == "course-old"][0]
        assert old_course["active"] is False


@pytest.mark.unit
class TestGenericCSVAdapterHelperFunctions:
    """Test the refactored helper functions for deserialization."""

    def test_try_parse_json_valid_json(self):
        """Should parse valid JSON strings."""
        adapter = GenericCSVAdapter()
        result = adapter._try_parse_json('{"key": "value", "num": 42}')
        assert result == {"key": "value", "num": 42}

    def test_try_parse_json_invalid_json(self):
        """Should return original string if JSON parsing fails."""
        adapter = GenericCSVAdapter()
        result = adapter._try_parse_json("not valid json")
        assert result == "not valid json"

    def test_try_parse_json_empty_string(self):
        """Should handle empty strings."""
        adapter = GenericCSVAdapter()
        result = adapter._try_parse_json("")
        assert result == ""

    def test_try_parse_datetime_iso8601(self):
        """Should parse ISO 8601 datetime strings."""
        adapter = GenericCSVAdapter()
        result = adapter._try_parse_datetime("2024-01-15T10:30:00")
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_try_parse_datetime_with_z_timezone(self):
        """Should handle 'Z' timezone indicator."""
        adapter = GenericCSVAdapter()
        result = adapter._try_parse_datetime("2024-01-15T10:30:00Z")
        assert isinstance(result, datetime)

    def test_try_parse_datetime_invalid(self):
        """Should return original string if datetime parsing fails."""
        adapter = GenericCSVAdapter()
        result = adapter._try_parse_datetime("not a datetime")
        assert result == "not a datetime"

    def test_deserialize_value_empty_string(self):
        """Should convert empty strings to None."""
        adapter = GenericCSVAdapter()
        result = adapter._deserialize_value("any_key", "")
        assert result is None

    def test_deserialize_value_none(self):
        """Should pass through None values."""
        adapter = GenericCSVAdapter()
        result = adapter._deserialize_value("any_key", None)
        assert result is None

    def test_deserialize_value_non_string(self):
        """Should pass through non-string values unchanged."""
        adapter = GenericCSVAdapter()
        result = adapter._deserialize_value("any_key", 42)
        assert result == 42

    def test_deserialize_value_json_field(self):
        """Should deserialize JSON fields."""
        adapter = GenericCSVAdapter()
        result = adapter._deserialize_value("grade_distribution", '{"A": 10, "B": 5}')
        assert result == {"A": 10, "B": 5}

    def test_deserialize_value_assessment_data_field(self):
        """Should deserialize assessment_data as JSON field."""
        adapter = GenericCSVAdapter()
        result = adapter._deserialize_value("assessment_data", '{"test": "data"}')
        assert result == {"test": "data"}

    def test_deserialize_value_extras_field(self):
        """Should deserialize extras as JSON field."""
        adapter = GenericCSVAdapter()
        result = adapter._deserialize_value("extras", '{"extra": "info"}')
        assert result == {"extra": "info"}

    def test_deserialize_value_boolean_true(self):
        """Should deserialize 'true' string to boolean True."""
        adapter = GenericCSVAdapter()
        result = adapter._deserialize_value("any_key", "true")
        assert result is True

    def test_deserialize_value_boolean_false(self):
        """Should deserialize 'false' string to boolean False."""
        adapter = GenericCSVAdapter()
        result = adapter._deserialize_value("any_key", "false")
        assert result is False

    def test_deserialize_value_boolean_case_insensitive(self):
        """Should handle boolean values case-insensitively."""
        adapter = GenericCSVAdapter()
        assert adapter._deserialize_value("key", "True") is True
        assert adapter._deserialize_value("key", "FALSE") is False
        assert adapter._deserialize_value("key", "TrUe") is True

    def test_deserialize_value_datetime_string(self):
        """Should deserialize datetime strings."""
        adapter = GenericCSVAdapter()
        result = adapter._deserialize_value("created_at", "2024-01-15T10:30:00")
        assert isinstance(result, datetime)

    def test_deserialize_value_regular_string(self):
        """Should pass through regular strings unchanged."""
        adapter = GenericCSVAdapter()
        result = adapter._deserialize_value("name", "John Doe")
        assert result == "John Doe"

    def test_deserialize_record_full_integration(self):
        """Should deserialize a complete row with mixed types."""
        adapter = GenericCSVAdapter()
        row = {
            "course_id": "CS101",
            "title": "Introduction to Computer Science",
            "credits": "3",
            "is_active": "true",
            "created_at": "2024-01-15T10:30:00",
            "grade_distribution": '{"A": 10, "B": 5}',
            "empty_field": "",
        }
        result = adapter._deserialize_record(row)

        assert result["course_id"] == "CS101"
        assert result["title"] == "Introduction to Computer Science"
        assert result["is_active"] is True
        assert isinstance(result["created_at"], datetime)
        assert result["grade_distribution"] == {"A": 10, "B": 5}
        assert result["empty_field"] is None
