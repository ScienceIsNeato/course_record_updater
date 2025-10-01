"""
Unit tests for the new adapter-based ImportService.

Tests the ImportService with the new adapter registry system.
"""

import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from import_service import (
    ConflictRecord,
    ConflictStrategy,
    ImportMode,
    ImportResult,
    ImportService,
    _convert_datetime_fields,
    create_import_report,
)


class TestDatetimeConversion:
    """Test datetime field conversion helper function."""

    def test_convert_datetime_fields_with_string_timestamps(self):
        """Test conversion of string timestamps to datetime objects."""
        data = {
            "name": "Test User",
            "created_at": "2025-09-28T17:41:27.935901",
            "updated_at": "2025-09-28T22:41:27.938209",
            "other_field": "not a datetime",
        }

        result = _convert_datetime_fields(data)

        assert isinstance(result["created_at"], datetime)
        assert isinstance(result["updated_at"], datetime)
        assert result["name"] == "Test User"
        assert result["other_field"] == "not a datetime"

    def test_convert_datetime_fields_with_existing_datetime_objects(self):
        """Test that existing datetime objects are left unchanged."""
        now = datetime.now(timezone.utc)
        data = {
            "created_at": now,
            "updated_at": "2025-09-28T17:41:27.935901",
        }

        result = _convert_datetime_fields(data)

        assert result["created_at"] is now  # Same object
        assert isinstance(result["updated_at"], datetime)

    def test_convert_datetime_fields_with_invalid_strings(self):
        """Test that invalid datetime strings are left unchanged."""
        data = {
            "created_at": "not a valid datetime",
            "updated_at": "2025-09-28T17:41:27.935901",
        }

        result = _convert_datetime_fields(data)

        assert result["created_at"] == "not a valid datetime"  # Unchanged
        assert isinstance(result["updated_at"], datetime)

    def test_convert_datetime_fields_with_none_values(self):
        """Test that None values are left unchanged."""
        data = {
            "created_at": None,
            "updated_at": "2025-09-28T17:41:27.935901",
        }

        result = _convert_datetime_fields(data)

        assert result["created_at"] is None
        assert isinstance(result["updated_at"], datetime)


class TestImportService:
    """Test the ImportService class with adapter registry integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.institution_id = "test-institution-id"
        self.service = ImportService(self.institution_id)

    def test_process_course_import_conflict_detection(self):
        """Test that process_course_import detects conflicts correctly."""
        # Test data with conflicts
        course_data = {
            "course_number": "CS-101",
            "title": "Introduction to Computer Science",
            "credits": 3,
        }

        # Mock existing course with different data
        existing_course = {
            "course_number": "CS-101",
            "title": "Computer Science 101",  # Different title
            "credits": 4,  # Different credits
        }

        with patch("import_service.get_course_by_number") as mock_get_course:
            mock_get_course.return_value = existing_course

            # Test conflict detection
            result, conflicts = self.service.process_course_import(
                course_data, ConflictStrategy.USE_MINE, dry_run=False
            )

            # Should detect conflict and skip
            assert result is True  # Skipped due to conflict
            assert len(conflicts) > 0  # Should have conflicts detected

    @patch("import_service.get_adapter_registry")
    def test_import_excel_file_adapter_not_found(self, mock_get_registry):
        """Test import_excel_file with adapter not found."""
        # Mock registry that returns None for adapter
        mock_registry = Mock()
        mock_registry.get_adapter_by_id.return_value = None
        mock_get_registry.return_value = mock_registry

        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            tmp_file.write(b"dummy content")
            tmp_file.flush()

            try:
                result = self.service.import_excel_file(
                    tmp_file.name, adapter_id="nonexistent_adapter"
                )

                assert result.success is False
                assert len(result.errors) == 1
                assert "Adapter not found: nonexistent_adapter" in result.errors[0]
            finally:
                os.unlink(tmp_file.name)

    @patch("import_service.get_adapter_registry")
    def test_import_excel_file_file_not_found(self, mock_get_registry):
        """Test import_excel_file with non-existent file."""
        result = self.service.import_excel_file("/nonexistent/file.xlsx")

        assert result.success is False
        assert len(result.errors) == 1
        assert "File not found" in result.errors[0]

    @patch("import_service.get_adapter_registry")
    @patch("import_service.os.path.exists")
    def test_import_excel_file_file_incompatible(self, mock_exists, mock_get_registry):
        """Test import_excel_file with incompatible file."""
        mock_exists.return_value = True

        # Mock adapter that says file is incompatible
        mock_adapter = Mock()
        mock_adapter.validate_file_compatibility.return_value = (
            False,
            "File format not supported",
        )

        mock_registry = Mock()
        mock_registry.get_adapter_by_id.return_value = mock_adapter
        mock_get_registry.return_value = mock_registry

        result = self.service.import_excel_file("test.xlsx")

        assert result.success is False
        assert len(result.errors) == 1
        assert "File incompatible" in result.errors[0]

    @patch("import_service.get_adapter_registry")
    @patch("import_service.os.path.exists")
    def test_import_excel_file_successful_import(self, mock_exists, mock_get_registry):
        """Test successful import with mock adapter."""
        mock_exists.return_value = True

        # Mock adapter that successfully parses file
        mock_adapter = Mock()
        mock_adapter.validate_file_compatibility.return_value = (
            True,
            "File is compatible",
        )
        mock_adapter.parse_file.return_value = {
            "users": [
                {"email": "test@example.com", "first_name": "Test", "last_name": "User"}
            ],
            "courses": [{"course_number": "TEST-101", "course_title": "Test Course"}],
            "terms": [
                {"term_name": "Fall 2024", "institution_id": self.institution_id}
            ],
        }

        mock_registry = Mock()
        mock_registry.get_adapter_by_id.return_value = mock_adapter
        mock_get_registry.return_value = mock_registry

        # Mock database operations
        with (
            patch("import_service.get_user_by_email", return_value=None),
            patch("import_service.get_course_by_number", return_value=None),
            patch("import_service.get_term_by_name", return_value=None),
            patch("import_service.create_user"),
            patch("import_service.create_course"),
            patch("import_service.create_term"),
        ):

            result = self.service.import_excel_file("test.xlsx")

            assert result.success is True
            assert result.records_processed == 3  # 1 user + 1 course + 1 term
            assert result.records_created == 3

    @patch("import_service.get_adapter_registry")
    @patch("import_service.os.path.exists")
    def test_import_excel_file_dry_run(self, mock_exists, mock_get_registry):
        """Test dry run mode."""
        mock_exists.return_value = True

        # Mock adapter
        mock_adapter = Mock()
        mock_adapter.validate_file_compatibility.return_value = (True, "Compatible")
        mock_adapter.parse_file.return_value = {
            "users": [
                {"email": "test@example.com", "first_name": "Test", "last_name": "User"}
            ]
        }

        mock_registry = Mock()
        mock_registry.get_adapter_by_id.return_value = mock_adapter
        mock_get_registry.return_value = mock_registry

        # Mock database operations
        with (
            patch("import_service.get_user_by_email", return_value=None),
            patch("import_service.create_user") as mock_create_user,
        ):

            result = self.service.import_excel_file("test.xlsx", dry_run=True)

            assert result.success is True
            assert result.dry_run is True
            assert result.records_processed == 1
            # In dry run, no actual creation should happen
            mock_create_user.assert_not_called()

    @patch("import_service.get_adapter_registry")
    @patch("import_service.os.path.exists")
    def test_import_excel_file_with_conflicts(self, mock_exists, mock_get_registry):
        """Test import with conflict resolution."""
        mock_exists.return_value = True

        # Mock adapter
        mock_adapter = Mock()
        mock_adapter.validate_file_compatibility.return_value = (True, "Compatible")
        mock_adapter.parse_file.return_value = {
            "users": [
                {
                    "email": "existing@example.com",
                    "first_name": "Updated",
                    "last_name": "User",
                }
            ]
        }

        mock_registry = Mock()
        mock_registry.get_adapter_by_id.return_value = mock_adapter
        mock_get_registry.return_value = mock_registry

        # Mock existing user
        existing_user = {"email": "existing@example.com", "first_name": "Original"}

        with (
            patch("import_service.get_user_by_email", return_value=existing_user),
            patch("import_service.update_user") as mock_update_user,
        ):

            result = self.service.import_excel_file(
                "test.xlsx", conflict_strategy=ConflictStrategy.USE_THEIRS
            )

            assert result.success is True
            assert result.conflicts_detected >= 1
            mock_update_user.assert_called()

    def test_process_course_import_new_course(self):
        """Test processing a new course import."""
        course_data = {
            "course_number": "NEW-101",
            "course_title": "New Course",
            "institution_id": self.institution_id,
        }

        with (
            patch("import_service.get_course_by_number", return_value=None),
            patch("import_service.create_course") as mock_create,
        ):

            success, conflicts = self.service.process_course_import(
                course_data, ConflictStrategy.USE_THEIRS, dry_run=False
            )

            assert success is True
            assert len(conflicts) == 0
            mock_create.assert_called_once()

    def test_process_course_import_dry_run(self):
        """Test processing course import in dry run mode."""
        course_data = {
            "course_number": "DRY-101",
            "course_title": "Dry Run Course",
            "institution_id": self.institution_id,
        }

        with (
            patch("import_service.get_course_by_number", return_value=None),
            patch("import_service.create_course") as mock_create,
        ):

            success, conflicts = self.service.process_course_import(
                course_data, ConflictStrategy.USE_THEIRS, dry_run=True
            )

            assert success is True
            mock_create.assert_not_called()
            assert self.service.stats["records_skipped"] == 1

    def test_process_user_import_new_user(self):
        """Test processing a new user import."""
        user_data = {
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
            "institution_id": self.institution_id,
        }

        with (
            patch("import_service.get_user_by_email", return_value=None),
            patch("import_service.create_user") as mock_create,
        ):

            success, conflicts = self.service.process_user_import(
                user_data, ConflictStrategy.USE_THEIRS, dry_run=False
            )

            assert success is True
            assert len(conflicts) == 0
            mock_create.assert_called_once()


class TestEnumsAndDataClasses:
    """Test enums and data classes."""

    def test_conflict_strategy_enum(self):
        """Test ConflictStrategy enum values."""
        assert ConflictStrategy.USE_MINE.value == "use_mine"
        assert ConflictStrategy.USE_THEIRS.value == "use_theirs"
        assert ConflictStrategy.MERGE.value == "merge"
        assert ConflictStrategy.MANUAL_REVIEW.value == "manual_review"

    def test_import_mode_enum(self):
        """Test ImportMode enum values."""
        assert ImportMode.DRY_RUN.value == "dry_run"
        assert ImportMode.EXECUTE.value == "execute"

    def test_import_result_creation(self):
        """Test ImportResult creation."""
        result = ImportResult(
            success=True,
            records_processed=10,
            records_created=8,
            records_updated=2,
            records_skipped=0,
            conflicts_detected=1,
            conflicts_resolved=1,
            errors=[],
            warnings=["Test warning"],
            conflicts=[],
            execution_time=2.5,
            dry_run=False,
        )

        assert result.success is True
        assert result.records_processed == 10
        assert result.execution_time == 2.5

    def test_conflict_record_creation(self):
        """Test ConflictRecord creation."""
        conflict = ConflictRecord(
            entity_type="user",
            entity_id="user-123",
            field_name="first_name",
            existing_value="John",
            import_value="Jonathan",
            resolution="use_theirs",
            timestamp=datetime.now(timezone.utc),
        )

        assert conflict.entity_type == "user"
        assert conflict.field_name == "first_name"


class TestReportGeneration:
    """Test import report generation."""

    def test_create_import_report_success(self):
        """Test creating report for successful import."""
        result = ImportResult(
            success=True,
            records_processed=5,
            records_created=5,
            records_updated=0,
            records_skipped=0,
            conflicts_detected=0,
            conflicts_resolved=0,
            errors=[],
            warnings=[],
            conflicts=[],
            execution_time=1.23,
            dry_run=False,
        )

        report = create_import_report(result)

        assert "Success: True" in report
        assert "Records Processed: 5" in report
        assert "Records Created: 5" in report
        assert "Execution Time: 1.23s" in report

    def test_create_import_report_with_errors(self):
        """Test creating report with errors and warnings."""
        result = ImportResult(
            success=False,
            records_processed=0,
            records_created=0,
            records_updated=0,
            records_skipped=0,
            conflicts_detected=0,
            conflicts_resolved=0,
            errors=["File not found", "Invalid format"],
            warnings=["Missing optional field"],
            conflicts=[],
            execution_time=0.5,
            dry_run=True,
        )

        report = create_import_report(result)

        assert "Success: False" in report
        assert "Mode: DRY RUN" in report
        assert "ERRORS:" in report
        assert "File not found" in report
        assert "WARNINGS:" in report
        assert "Missing optional field" in report

    def test_process_course_import_update_existing(self):
        """Test updating existing course with USE_THEIRS strategy."""
        course_data = {
            "course_number": "CS101",
            "title": "Updated Computer Science",
            "department": "Computer Science",
            "credits": 4,
        }

        with (
            patch("import_service.get_course_by_number") as mock_get_course,
            patch("import_service.create_course") as mock_create_course,
        ):

            # Mock existing course
            mock_get_course.return_value = {
                "course_id": "course_123",
                "course_number": "CS101",
                "title": "Old Computer Science",
                "department": "Computer Science",
                "credits": 3,
            }

            service = ImportService("inst_123")
            success, conflicts = service.process_course_import(
                course_data, ConflictStrategy.USE_THEIRS, dry_run=False
            )

            assert success is True
            assert len(conflicts) > 0  # Should detect conflicts
            assert service.stats["records_updated"] == 1
            assert service.stats["conflicts_resolved"] > 0
            mock_create_course.assert_not_called()  # Should not create new course

    def test_process_user_import_update_existing(self):
        """Test updating existing user with USE_THEIRS strategy."""
        user_data = {
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Updated",
            "role": "instructor",
        }

        with (
            patch("import_service.get_user_by_email") as mock_get_user,
            patch("import_service.update_user") as mock_update_user,
            patch("import_service.create_user") as mock_create_user,
        ):

            # Mock existing user
            mock_get_user.return_value = {
                "user_id": "user_123",
                "email": "test@example.com",
                "first_name": "John",
                "last_name": "Old",
                "role": "instructor",
            }

            service = ImportService("inst_123")
            success, conflicts = service.process_user_import(
                user_data, ConflictStrategy.USE_THEIRS, dry_run=False
            )

            assert success is True
            assert len(conflicts) > 0  # Should detect conflicts
            assert service.stats["records_updated"] == 1
            assert service.stats["conflicts_resolved"] > 0
            mock_update_user.assert_called_once_with("user_123", user_data)
            mock_create_user.assert_not_called()  # Should not create new user


class TestImportServiceHelpers:
    """Test ImportService helper methods."""

    def test_prepare_import_file_not_found(self):
        """Test _prepare_import with non-existent file."""
        service = ImportService("test_inst")
        service.reset_stats()

        result = service._prepare_import("/nonexistent/file.xlsx", "test_adapter")

        assert result is None
        assert len(service.stats["errors"]) > 0
        assert "File not found" in service.stats["errors"][0]

    def test_prepare_import_adapter_not_found(self):
        """Test _prepare_import with invalid adapter."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as temp_file:
            service = ImportService("test_inst")
            service.reset_stats()

            with patch("import_service.get_adapter_registry") as mock_registry:
                mock_reg = Mock()
                mock_reg.get_adapter_by_id.return_value = None
                mock_registry.return_value = mock_reg

                result = service._prepare_import(temp_file.name, "invalid_adapter")

                assert result is None
                assert len(service.stats["errors"]) > 0
                assert "Adapter not found" in service.stats["errors"][0]

    def test_prepare_import_file_incompatible(self):
        """Test _prepare_import with incompatible file."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as temp_file:
            service = ImportService("test_inst")
            service.reset_stats()

            with patch("import_service.get_adapter_registry") as mock_registry:
                mock_adapter = Mock()
                mock_adapter.validate_file_compatibility.return_value = (
                    False,
                    "Incompatible",
                )

                mock_reg = Mock()
                mock_reg.get_adapter_by_id.return_value = mock_adapter
                mock_registry.return_value = mock_reg

                result = service._prepare_import(temp_file.name, "test_adapter")

                assert result is None
                assert len(service.stats["errors"]) > 0
                assert "File incompatible" in service.stats["errors"][0]

    def test_prepare_import_success(self):
        """Test _prepare_import with valid inputs."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as temp_file:
            service = ImportService("test_inst")
            service.reset_stats()

            with patch("import_service.get_adapter_registry") as mock_registry:
                mock_adapter = Mock()
                mock_adapter.validate_file_compatibility.return_value = (
                    True,
                    "Compatible",
                )

                mock_reg = Mock()
                mock_reg.get_adapter_by_id.return_value = mock_adapter
                mock_registry.return_value = mock_reg

                result = service._prepare_import(temp_file.name, "test_adapter")

                assert result is mock_adapter
                assert len(service.stats["errors"]) == 0

    def test_parse_file_data_success(self):
        """Test _parse_file_data with successful parsing."""
        service = ImportService("test_inst")
        service.reset_stats()

        mock_adapter = Mock()
        mock_adapter.parse_file.return_value = {
            "courses": [{"course_id": "CS101"}],
            "students": [],
        }

        result = service._parse_file_data(
            mock_adapter, "/fake/path.xlsx", "test_adapter"
        )

        assert result is not None
        assert "courses" in result
        mock_adapter.parse_file.assert_called_once()

    def test_parse_file_data_parse_error(self):
        """Test _parse_file_data with parsing error."""
        service = ImportService("test_inst")
        service.reset_stats()

        mock_adapter = Mock()
        mock_adapter.parse_file.side_effect = Exception("Parse failed")

        result = service._parse_file_data(
            mock_adapter, "/fake/path.xlsx", "test_adapter"
        )

        assert result is None
        assert len(service.stats["errors"]) > 0
        assert "Failed to parse file" in service.stats["errors"][0]

    def test_parse_file_data_empty_result(self):
        """Test _parse_file_data with empty parsing result."""
        service = ImportService("test_inst")
        service.reset_stats()

        mock_adapter = Mock()
        mock_adapter.parse_file.return_value = {}

        result = service._parse_file_data(
            mock_adapter, "/fake/path.xlsx", "test_adapter"
        )

        assert result is None
        assert len(service.stats["errors"]) > 0
        assert "No valid data found" in service.stats["errors"][0]
