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

    def test_convert_datetime_fields_with_z_format(self):
        """Test datetime with Z suffix (UTC indicator)."""
        from import_service import _normalize_datetime_string

        # Z format with microseconds should be converted to +00:00
        result = _normalize_datetime_string("2025-09-28T17:41:27.935901Z")
        assert result == "2025-09-28T17:41:27.935901+00:00"

    def test_convert_datetime_fields_already_normalized(self):
        """Test datetime that already has UTC offset."""
        from import_service import _normalize_datetime_string

        # Already has +00:00, should be returned as-is
        result = _normalize_datetime_string("2025-09-28T17:41:27.935901+00:00")
        assert result == "2025-09-28T17:41:27.935901+00:00"


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


class TestImportServiceErrorHandling:
    """Test error handling in ImportService."""

    def test_prepare_import_adapter_registry_error(self):
        """Test _prepare_import handles AdapterRegistryError."""
        from unittest.mock import patch

        from adapters.adapter_registry import AdapterRegistryError

        service = ImportService("test_inst")
        service.reset_stats()

        # Mock get_adapter_registry to raise AdapterRegistryError
        with patch("import_service.get_adapter_registry") as mock_registry:
            mock_reg = mock_registry.return_value
            mock_reg.get_adapter_by_id.side_effect = AdapterRegistryError(
                "Registry failed"
            )

            # Use a valid temp file
            import os
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp.write(b"test")
                tmp_path = tmp.name

            try:
                result = service._prepare_import(tmp_path, "test_adapter")

                assert result is None
                assert len(service.stats["errors"]) > 0
                assert "Failed to get adapter" in service.stats["errors"][0]
                assert "Registry failed" in service.stats["errors"][0]
            finally:
                os.unlink(tmp_path)

    def test_prepare_import_file_validation_exception(self):
        """Test _prepare_import handles file validation exception."""
        from unittest.mock import Mock, patch

        service = ImportService("test_inst")
        service.reset_stats()

        # Mock adapter that raises exception during validation
        mock_adapter = Mock()
        mock_adapter.validate_file_compatibility.side_effect = RuntimeError(
            "Validation failed"
        )

        with patch("import_service.get_adapter_registry") as mock_registry:
            mock_reg = mock_registry.return_value
            mock_reg.get_adapter_by_id.return_value = mock_adapter

            import os
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp.write(b"test")
                tmp_path = tmp.name

            try:
                result = service._prepare_import(tmp_path, "test_adapter")

                assert result is None
                assert len(service.stats["errors"]) > 0
                assert "File validation failed" in service.stats["errors"][0]
                assert "Validation failed" in service.stats["errors"][0]
            finally:
                os.unlink(tmp_path)

    def test_update_progress_with_callback(self):
        """Test _update_progress calls progress_callback when set."""
        from unittest.mock import Mock

        service = ImportService("test_inst")
        service.reset_stats()

        # Set up progress callback
        mock_callback = Mock()
        service.progress_callback = mock_callback

        # Call _update_progress
        service._update_progress(50, 100, "courses")

        # Verify callback was called
        assert mock_callback.called
        call_args = mock_callback.call_args[1]
        assert call_args["percentage"] == 50
        assert call_args["records_processed"] == 50
        assert call_args["total_records"] == 100
        assert "courses" in call_args["message"]

    def test_process_single_record_offerings(self):
        """Test _process_single_record handles offerings."""
        from unittest.mock import patch

        service = ImportService("test_inst")
        service.reset_stats()

        with patch.object(service, "_process_offering_import") as mock_process:
            conflicts = service._process_single_record(
                "offerings",
                {"offering_id": "test"},
                ConflictStrategy.USE_THEIRS,
                dry_run=False,
            )

            assert conflicts == []
            assert mock_process.called

    def test_process_single_record_sections(self):
        """Test _process_single_record handles sections."""
        from unittest.mock import patch

        service = ImportService("test_inst")
        service.reset_stats()

        with patch.object(service, "_process_section_import") as mock_process:
            conflicts = service._process_single_record(
                "sections",
                {"section_id": "test"},
                ConflictStrategy.USE_THEIRS,
                dry_run=False,
            )

            assert conflicts == []
            assert mock_process.called

    def test_process_single_record_terms(self):
        """Test _process_single_record handles terms."""
        from unittest.mock import patch

        service = ImportService("test_inst")
        service.reset_stats()

        with patch.object(service, "_process_term_import") as mock_process:
            conflicts = service._process_single_record(
                "terms", {"term_id": "test"}, ConflictStrategy.USE_THEIRS, dry_run=False
            )

            assert conflicts == []
            assert mock_process.called

    def test_resolve_user_conflicts_use_theirs_dry_run(self):
        """Test _resolve_user_conflicts with USE_THEIRS strategy in dry run."""
        from unittest.mock import patch

        service = ImportService("test_inst")
        service.reset_stats()

        user_data = {"email": "test@example.com", "first_name": "Test"}
        existing_user = {"email": "test@example.com", "first_name": "Old"}
        detected_conflicts = []

        with patch("import_service.update_user") as mock_update:
            service._resolve_user_conflicts(
                ConflictStrategy.USE_THEIRS,
                detected_conflicts,
                user_data,
                existing_user,
                "test@example.com",
                dry_run=True,  # DRY RUN
                conflicts=[],
            )

            # Should not call update_user in dry run
            assert not mock_update.called
            # Should have logged dry run message (check stats)
            assert service.stats["records_updated"] == 0

    def test_import_excel_file_top_level_exception(self):
        """Test import_excel_file handles unexpected top-level exception."""
        from unittest.mock import patch

        service = ImportService("test_inst")
        service.reset_stats()

        # Mock _prepare_import to raise unexpected exception
        with patch.object(service, "_prepare_import", side_effect=RuntimeError("Boom")):
            import os
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp.write(b"test")
                tmp_path = tmp.name

            try:
                result = service.import_excel_file(tmp_path)

                assert result.success is False
                assert len(result.errors) > 0
                assert "Unexpected error during import" in result.errors[0]
                assert "Boom" in result.errors[0]
            finally:
                os.unlink(tmp_path)

    def test_process_data_records_exception_handling(self):
        """Test exception handling when processing individual records in a batch."""
        from unittest.mock import patch

        service = ImportService("test_inst")
        service.reset_stats()

        # Mock _process_single_record to raise exception
        with patch.object(
            service,
            "_process_single_record",
            side_effect=RuntimeError("Record processing failed"),
        ):
            # Call _process_data_records which should catch the exception
            conflicts = service._process_data_type_records(
                "courses",
                [{"course_number": "TEST-101"}],
                ConflictStrategy.USE_THEIRS,
                False,  # dry_run
                0,  # processed_records
                1,  # total_records
            )

            # Should catch exception and log error
            assert len(service.stats["errors"]) > 0
            assert "Error processing courses record" in service.stats["errors"][0]
            assert "Record processing failed" in service.stats["errors"][0]

    def test_process_single_record_unknown_type(self):
        """Test _process_single_record with unknown data type returns empty list."""
        service = ImportService("test_inst")
        service.reset_stats()

        conflicts = service._process_single_record(
            "unknown_type", {"data": "test"}, ConflictStrategy.USE_THEIRS, dry_run=False
        )

        assert conflicts == []

    def test_resolve_user_conflicts_use_mine_with_conflicts(self):
        """Test _resolve_user_conflicts with USE_MINE and detected conflicts."""
        service = ImportService("test_inst")
        service.reset_stats()

        # Create conflict records
        from datetime import datetime, timezone

        from import_service import ConflictRecord

        detected_conflicts = [
            ConflictRecord(
                entity_type="user",
                entity_id="test@example.com",
                field_name="first_name",
                existing_value="Old",
                import_value="New",
                resolution="pending",
                timestamp=datetime.now(timezone.utc),
            )
        ]

        service._resolve_user_conflicts(
            ConflictStrategy.USE_MINE,
            detected_conflicts,
            {"email": "test@example.com"},
            {"email": "test@example.com"},
            "test@example.com",
            dry_run=False,
            conflicts=[],
        )

        # Should mark conflict as resolved
        assert service.stats["conflicts_resolved"] == 1
        assert detected_conflicts[0].resolution == "use_mine"

    def test_resolve_course_conflicts_use_theirs_dry_run(self):
        """Test _resolve_course_conflicts with USE_THEIRS in dry run mode."""
        service = ImportService("test_inst")
        service.reset_stats()

        from datetime import datetime, timezone

        from import_service import ConflictRecord

        detected_conflicts = [
            ConflictRecord(
                entity_type="course",
                entity_id="MATH-101",
                field_name="title",
                existing_value="Algebra",
                import_value="New Algebra",
                resolution="pending",
                timestamp=datetime.now(timezone.utc),
            )
        ]

        service._resolve_course_conflicts(
            ConflictStrategy.USE_THEIRS,
            detected_conflicts,
            "MATH-101",
            dry_run=True,  # DRY RUN mode
            conflicts=[],
        )

        # Should log dry run message (line 580)
        assert service.stats["conflicts_resolved"] == 1


class TestImportServiceRolePreservation:
    """Test role preservation logic added for demo."""

    def test_should_preserve_role_site_admin_over_instructor(self):
        """Test that site_admin role is preserved over instructor."""
        service = ImportService("inst-123")
        assert service._should_preserve_role("site_admin", "instructor") is True

    def test_should_preserve_role_institution_admin_over_instructor(self):
        """Test that institution_admin role is preserved over instructor."""
        service = ImportService("inst-123")
        assert service._should_preserve_role("institution_admin", "instructor") is True

    def test_should_preserve_role_program_admin_over_instructor(self):
        """Test that program_admin role is preserved over instructor."""
        service = ImportService("inst-123")
        assert service._should_preserve_role("program_admin", "instructor") is True

    def test_should_preserve_role_same_roles(self):
        """Test that same roles don't trigger preservation."""
        service = ImportService("inst-123")
        assert service._should_preserve_role("instructor", "instructor") is False

    def test_should_preserve_role_lower_to_higher(self):
        """Test that lower roles don't override higher roles."""
        service = ImportService("inst-123")
        assert service._should_preserve_role("instructor", "site_admin") is False

    def test_should_preserve_role_institution_admin_over_program_admin(self):
        """Test role hierarchy between admin types."""
        service = ImportService("inst-123")
        assert (
            service._should_preserve_role("institution_admin", "program_admin") is True
        )

    def test_should_preserve_role_unknown_roles(self):
        """Test handling of unknown roles."""
        service = ImportService("inst-123")
        # Unknown roles get level 0, so neither is preserved
        assert service._should_preserve_role("unknown", "instructor") is False
        assert service._should_preserve_role("instructor", "unknown") is True


class TestCLOImportFeature:
    """Test NEW CLO import functionality added in this PR"""

    @patch("import_service.create_course_outcome")
    @patch("import_service.get_course_outcomes")
    @patch("import_service.get_course_by_number")
    def test_process_clo_import_success(
        self, mock_get_course, mock_get_outcomes, mock_create_outcome
    ):
        """Test successful CLO import for new CLO"""
        mock_get_course.return_value = {
            "course_id": "course-123",
            "course_number": "BIO101",
        }
        mock_get_outcomes.return_value = []  # No existing CLOs
        mock_create_outcome.return_value = "outcome-456"

        service = ImportService("inst-123")
        clo_data = {
            "course_number": "BIO101",
            "clo_number": "CLO1",
            "description": "Understand cellular biology",
            "assessment_method": "Exam",
        }

        service._process_clo_import(
            clo_data, ConflictStrategy.USE_THEIRS, dry_run=False
        )

        assert service.stats["records_created"] == 1
        mock_create_outcome.assert_called_once()
        created_schema = mock_create_outcome.call_args[0][0]
        assert created_schema["course_id"] == "course-123"
        assert created_schema["clo_number"] == "CLO1"
        assert created_schema["description"] == "Understand cellular biology"

    @patch("import_service.get_course_by_number")
    def test_process_clo_import_missing_fields(self, mock_get_course):
        """Test CLO import fails gracefully with missing required fields"""
        service = ImportService("inst-123")

        # Missing clo_number
        clo_data = {"course_number": "BIO101", "description": "Test"}
        service._process_clo_import(
            clo_data, ConflictStrategy.USE_THEIRS, dry_run=False
        )
        assert len(service.stats["errors"]) == 1
        assert "Missing required fields" in service.stats["errors"][0]

    @patch("import_service.get_course_by_number")
    def test_process_clo_import_course_not_found(self, mock_get_course):
        """Test CLO import when course doesn't exist"""
        mock_get_course.return_value = None

        service = ImportService("inst-123")
        clo_data = {
            "course_number": "NONEXISTENT",
            "clo_number": "CLO1",
            "description": "Test",
        }

        service._process_clo_import(
            clo_data, ConflictStrategy.USE_THEIRS, dry_run=False
        )

        assert len(service.stats["errors"]) == 1
        assert "Course NONEXISTENT not found" in service.stats["errors"][0]

    @patch("import_service.get_course_outcomes")
    @patch("import_service.get_course_by_number")
    def test_process_clo_import_conflict_use_mine(
        self, mock_get_course, mock_get_outcomes
    ):
        """Test CLO import skips existing CLO with USE_MINE strategy"""
        mock_get_course.return_value = {
            "course_id": "course-123",
            "course_number": "BIO101",
        }
        mock_get_outcomes.return_value = [
            {"clo_number": "CLO1", "description": "Existing"}
        ]

        service = ImportService("inst-123")
        clo_data = {
            "course_number": "BIO101",
            "clo_number": "CLO1",
            "description": "New description",
        }

        service._process_clo_import(clo_data, ConflictStrategy.USE_MINE, dry_run=False)

        assert service.stats["records_skipped"] == 1
        assert service.stats["records_created"] == 0

    @patch("import_service.get_course_outcomes")
    @patch("import_service.get_course_by_number")
    def test_process_clo_import_conflict_use_theirs(
        self, mock_get_course, mock_get_outcomes
    ):
        """Test CLO import updates existing CLO with USE_THEIRS strategy"""
        mock_get_course.return_value = {
            "course_id": "course-123",
            "course_number": "BIO101",
        }
        mock_get_outcomes.return_value = [
            {"clo_number": "CLO1", "description": "Existing"}
        ]

        service = ImportService("inst-123")
        clo_data = {
            "course_number": "BIO101",
            "clo_number": "CLO1",
            "description": "Updated description",
        }

        service._process_clo_import(
            clo_data, ConflictStrategy.USE_THEIRS, dry_run=False
        )

        assert service.stats["records_updated"] == 1

    @patch("import_service.get_course_by_number")
    def test_process_clo_import_dry_run(self, mock_get_course):
        """Test CLO import in dry run mode doesn't create records"""
        mock_get_course.return_value = {
            "course_id": "course-123",
            "course_number": "BIO101",
        }

        service = ImportService("inst-123")
        clo_data = {
            "course_number": "BIO101",
            "clo_number": "CLO1",
            "description": "Test",
        }

        service._process_clo_import(clo_data, ConflictStrategy.USE_THEIRS, dry_run=True)

        # Should not create anything in dry run
        assert service.stats["records_created"] == 0
        mock_get_course.assert_called_once()

    @patch("import_service.create_course_outcome")
    @patch("import_service.get_course_outcomes")
    @patch("import_service.get_course_by_number")
    def test_process_clo_import_create_fails(
        self, mock_get_course, mock_get_outcomes, mock_create_outcome
    ):
        """Test CLO import handles creation failure"""
        mock_get_course.return_value = {
            "course_id": "course-123",
            "course_number": "BIO101",
        }
        mock_get_outcomes.return_value = []
        mock_create_outcome.return_value = None  # Creation failed

        service = ImportService("inst-123")
        clo_data = {
            "course_number": "BIO101",
            "clo_number": "CLO1",
            "description": "Test",
        }

        service._process_clo_import(
            clo_data, ConflictStrategy.USE_THEIRS, dry_run=False
        )

        assert len(service.stats["errors"]) == 1
        assert "Failed to create CLO" in service.stats["errors"][0]

    @patch("import_service.get_course_by_number")
    def test_process_clo_import_exception_handling(self, mock_get_course):
        """Test CLO import handles unexpected exceptions"""
        mock_get_course.side_effect = Exception("Database error")

        service = ImportService("inst-123")
        clo_data = {
            "course_number": "BIO101",
            "clo_number": "CLO1",
            "description": "Test",
        }

        service._process_clo_import(
            clo_data, ConflictStrategy.USE_THEIRS, dry_run=False
        )

        assert len(service.stats["errors"]) == 1
        assert "Error processing CLO" in service.stats["errors"][0]


class TestCourseProgramLinkingFeature:
    """Test NEW course-to-program auto-linking functionality added in this PR"""

    @patch("database_service.add_course_to_program")
    @patch("database_service.get_programs_by_institution")
    @patch("database_service.get_all_courses")
    def test_link_courses_to_programs_success(
        self, mock_get_courses, mock_get_programs, mock_add_course
    ):
        """Test successful course-program linking based on prefix"""
        mock_get_courses.return_value = [
            {"id": "c1", "course_number": "BIOL-101"},
            {"id": "c2", "course_number": "BSN-202"},
            {"id": "c3", "course_number": "ZOOL-303"},
        ]
        mock_get_programs.return_value = [
            {"id": "p1", "name": "Biological Sciences"},
            {"id": "p2", "name": "Zoology"},
        ]

        service = ImportService("inst-123")
        service._link_courses_to_programs()

        # Should link BIOL and BSN to Biological Sciences, ZOOL to Zoology
        assert mock_add_course.call_count == 3
        calls = mock_add_course.call_args_list
        assert calls[0][0] == ("c1", "p1")  # BIOL → Biological Sciences
        assert calls[1][0] == ("c2", "p1")  # BSN → Biological Sciences
        assert calls[2][0] == ("c3", "p2")  # ZOOL → Zoology

    @patch("database_service.get_programs_by_institution")
    @patch("database_service.get_all_courses")
    def test_link_courses_no_courses(self, mock_get_courses, mock_get_programs):
        """Test linking handles no courses gracefully"""
        mock_get_courses.return_value = []
        mock_get_programs.return_value = [{"id": "p1", "name": "Test"}]

        service = ImportService("inst-123")
        service._link_courses_to_programs()  # Should not crash

    @patch("database_service.get_programs_by_institution")
    @patch("database_service.get_all_courses")
    def test_link_courses_no_programs(self, mock_get_courses, mock_get_programs):
        """Test linking handles no programs gracefully"""
        mock_get_courses.return_value = [{"id": "c1", "course_number": "BIOL-101"}]
        mock_get_programs.return_value = []

        service = ImportService("inst-123")
        service._link_courses_to_programs()  # Should not crash

    @patch("database_service.add_course_to_program")
    @patch("database_service.get_programs_by_institution")
    @patch("database_service.get_all_courses")
    def test_link_courses_unmapped_prefix(
        self, mock_get_courses, mock_get_programs, mock_add_course
    ):
        """Test courses with unmapped prefixes are not linked"""
        mock_get_courses.return_value = [
            {"id": "c1", "course_number": "CHEM-101"},  # CHEM not in mappings
            {"id": "c2", "course_number": "MATH-202"},  # MATH not in mappings
        ]
        mock_get_programs.return_value = [
            {"id": "p1", "name": "Chemistry"},
        ]

        service = ImportService("inst-123")
        service._link_courses_to_programs()

        # Should not link any courses
        mock_add_course.assert_not_called()

    @patch("database_service.add_course_to_program")
    @patch("database_service.get_programs_by_institution")
    @patch("database_service.get_all_courses")
    def test_link_courses_program_not_found(
        self, mock_get_courses, mock_get_programs, mock_add_course
    ):
        """Test courses skip linking if target program doesn't exist"""
        mock_get_courses.return_value = [
            {"id": "c1", "course_number": "BIOL-101"},
        ]
        # Program name doesn't match mapping
        mock_get_programs.return_value = [
            {"id": "p1", "name": "Wrong Program Name"},
        ]

        service = ImportService("inst-123")
        service._link_courses_to_programs()

        # Should not link - program name mismatch
        mock_add_course.assert_not_called()

    @patch("database_service.add_course_to_program")
    @patch("database_service.get_programs_by_institution")
    @patch("database_service.get_all_courses")
    def test_link_courses_already_linked(
        self, mock_get_courses, mock_get_programs, mock_add_course
    ):
        """Test linking handles already-linked courses gracefully"""
        mock_get_courses.return_value = [
            {"id": "c1", "course_number": "BIOL-101"},
        ]
        mock_get_programs.return_value = [
            {"id": "p1", "name": "Biological Sciences"},
        ]
        # Simulate course already linked
        mock_add_course.side_effect = Exception("Already linked")

        service = ImportService("inst-123")
        service._link_courses_to_programs()  # Should not crash

    @patch("database_service.get_all_courses")
    def test_link_courses_exception_doesnt_fail_import(self, mock_get_courses):
        """Test linking failure doesn't break the import"""
        mock_get_courses.side_effect = Exception("Database error")

        service = ImportService("inst-123")
        service._link_courses_to_programs()  # Should not crash - just log warning


class TestOfferingImportErrorPaths:
    """Test error paths and edge cases in _process_offering_import"""

    @patch("import_service.get_course_by_number")
    @patch("import_service.get_term_by_name")
    def test_offering_import_missing_course_number(
        self, mock_get_term, mock_get_course
    ):
        """Test offering import fails gracefully when course_number is missing"""
        service = ImportService("inst-123")
        service._process_offering_import(
            {"term_name": "Fall 2024"}, ConflictStrategy.USE_THEIRS, dry_run=False
        )
        assert len(service.stats["errors"]) == 1
        assert "Missing course_number or term_name" in service.stats["errors"][0]

    @patch("import_service.get_course_by_number")
    @patch("import_service.get_term_by_name")
    def test_offering_import_missing_term_name(self, mock_get_term, mock_get_course):
        """Test offering import fails gracefully when term_name is missing"""
        service = ImportService("inst-123")
        service._process_offering_import(
            {"course_number": "BIO101"}, ConflictStrategy.USE_THEIRS, dry_run=False
        )
        assert len(service.stats["errors"]) == 1
        assert "Missing course_number or term_name" in service.stats["errors"][0]

    @patch("import_service.get_term_by_name")
    @patch("import_service.get_course_by_number")
    def test_offering_import_course_not_found(self, mock_get_course, mock_get_term):
        """Test offering import when course doesn't exist"""
        mock_get_course.return_value = None
        mock_get_term.return_value = {"term_id": "term-123"}

        service = ImportService("inst-123")
        service._process_offering_import(
            {"course_number": "NONEXISTENT", "term_name": "Fall 2024"},
            ConflictStrategy.USE_THEIRS,
            dry_run=False,
        )
        assert len(service.stats["errors"]) == 1
        assert "Course NONEXISTENT not found" in service.stats["errors"][0]

    @patch("import_service.get_term_by_name")
    @patch("import_service.get_course_by_number")
    def test_offering_import_term_not_found(self, mock_get_course, mock_get_term):
        """Test offering import when term doesn't exist"""
        mock_get_course.return_value = {"course_id": "course-123"}
        mock_get_term.return_value = None

        service = ImportService("inst-123")
        service._process_offering_import(
            {"course_number": "BIO101", "term_name": "Nonexistent Term"},
            ConflictStrategy.USE_THEIRS,
            dry_run=False,
        )
        assert len(service.stats["errors"]) == 1
        assert "Term Nonexistent Term not found" in service.stats["errors"][0]

    @patch("import_service.get_course_offering_by_course_and_term")
    @patch("import_service.get_term_by_name")
    @patch("import_service.get_course_by_number")
    def test_offering_import_dry_run(
        self, mock_get_course, mock_get_term, mock_get_offering
    ):
        """Test offering import in dry run mode"""
        mock_get_course.return_value = {"course_id": "course-123"}
        mock_get_term.return_value = {"term_id": "term-123"}

        service = ImportService("inst-123")
        service._process_offering_import(
            {"course_number": "BIO101", "term_name": "Fall 2024"},
            ConflictStrategy.USE_THEIRS,
            dry_run=True,
        )
        assert service.stats["records_created"] == 0
        assert len(service.stats["errors"]) == 0

    @patch("import_service.create_course_offering")
    @patch("import_service.get_course_offering_by_course_and_term")
    @patch("import_service.get_term_by_name")
    @patch("import_service.get_course_by_number")
    def test_offering_import_creation_fails(
        self,
        mock_get_course,
        mock_get_term,
        mock_get_offering,
        mock_create_offering,
    ):
        """Test offering import handles creation failure"""
        mock_get_course.return_value = {"course_id": "course-123"}
        mock_get_term.return_value = {"term_id": "term-123"}
        mock_get_offering.return_value = None
        mock_create_offering.return_value = None

        service = ImportService("inst-123")
        service._process_offering_import(
            {"course_number": "BIO101", "term_name": "Fall 2024"},
            ConflictStrategy.USE_THEIRS,
            dry_run=False,
        )
        assert len(service.stats["errors"]) == 1
        assert "Failed to create offering" in service.stats["errors"][0]

    @patch("import_service.get_term_by_name")
    @patch("import_service.get_course_by_number")
    def test_offering_import_exception_handling(self, mock_get_course, mock_get_term):
        """Test offering import handles unexpected exceptions"""
        mock_get_course.side_effect = Exception("Database error")

        service = ImportService("inst-123")
        service._process_offering_import(
            {"course_number": "BIO101", "term_name": "Fall 2024"},
            ConflictStrategy.USE_THEIRS,
            dry_run=False,
        )
        assert len(service.stats["errors"]) == 1
        assert "Error processing offering" in service.stats["errors"][0]


class TestSectionImportErrorPaths:
    """Test error paths and edge cases in _process_section_import"""

    @patch("import_service.get_course_by_number")
    @patch("import_service.get_term_by_name")
    def test_section_import_missing_course_number(self, mock_get_term, mock_get_course):
        """Test section import fails gracefully when course_number is missing"""
        service = ImportService("inst-123")
        service._process_section_import(
            {"term_name": "Fall 2024", "section_number": "001"},
            dry_run=False,
        )
        assert len(service.stats["errors"]) == 1
        assert "Missing course_number or term_name" in service.stats["errors"][0]

    @patch("import_service.get_term_by_name")
    @patch("import_service.get_course_by_number")
    def test_section_import_course_not_found(self, mock_get_course, mock_get_term):
        """Test section import when course doesn't exist"""
        mock_get_course.return_value = None
        # Term lookup happens after course lookup, so return valid term
        # But both are called before checking, so ensure term lookup succeeds
        mock_get_term.return_value = {"term_id": "term-123"}

        service = ImportService("inst-123")
        service._process_section_import(
            {
                "course_number": "NONEXISTENT",
                "term_name": "Fall 2024",
                "section_number": "001",
            },
            dry_run=False,
        )
        # Course check happens first, so this should be the error
        assert len(service.stats["errors"]) == 1
        # Verify course lookup was called
        assert mock_get_course.called
        # Error should be about course, not term
        assert "Course NONEXISTENT not found" in service.stats["errors"][0]

    @patch("import_service.get_term_by_name")
    @patch("import_service.get_course_by_number")
    def test_section_import_term_not_found(self, mock_get_course, mock_get_term):
        """Test section import when term doesn't exist"""
        mock_get_course.return_value = {"course_id": "course-123"}
        mock_get_term.return_value = None

        service = ImportService("inst-123")
        service._process_section_import(
            {
                "course_number": "BIO101",
                "term_name": "Nonexistent Term",
                "section_number": "001",
            },
            dry_run=False,
        )
        assert len(service.stats["errors"]) == 1
        assert "Term Nonexistent Term not found" in service.stats["errors"][0]

    @patch("import_service.get_course_offering_by_course_and_term")
    @patch("import_service.get_term_by_name")
    @patch("import_service.get_course_by_number")
    def test_section_import_dry_run(
        self, mock_get_course, mock_get_term, mock_get_offering
    ):
        """Test section import in dry run mode"""
        mock_get_course.return_value = {"course_id": "course-123"}
        mock_get_term.return_value = {"term_id": "term-123"}
        mock_get_offering.return_value = None

        service = ImportService("inst-123")
        service._process_section_import(
            {
                "course_number": "BIO101",
                "term_name": "Fall 2024",
                "section_number": "001",
            },
            dry_run=True,
        )
        assert service.stats["records_created"] == 0
        assert len(service.stats["errors"]) == 0

    @patch("import_service.create_course_section")
    @patch("import_service.get_user_by_email")
    @patch("import_service.get_course_offering_by_course_and_term")
    @patch("import_service.get_term_by_name")
    @patch("import_service.get_course_by_number")
    def test_section_import_creation_fails(
        self,
        mock_get_course,
        mock_get_term,
        mock_get_offering,
        mock_get_user,
        mock_create_section,
    ):
        """Test section import handles creation failure"""
        mock_get_course.return_value = {"course_id": "course-123"}
        mock_get_term.return_value = {"term_id": "term-123"}
        mock_get_offering.return_value = {"offering_id": "offering-123"}
        mock_create_section.return_value = None

        service = ImportService("inst-123")
        service._process_section_import(
            {
                "course_number": "BIO101",
                "term_name": "Fall 2024",
                "section_number": "001",
            },
            dry_run=False,
        )
        assert len(service.stats["errors"]) == 1
        assert "Failed to create section" in service.stats["errors"][0]

    @patch("import_service.get_term_by_name")
    @patch("import_service.get_course_by_number")
    def test_section_import_exception_handling(self, mock_get_course, mock_get_term):
        """Test section import handles unexpected exceptions"""
        mock_get_course.side_effect = Exception("Database error")

        service = ImportService("inst-123")
        service._process_section_import(
            {
                "course_number": "BIO101",
                "term_name": "Fall 2024",
                "section_number": "001",
            },
            dry_run=False,
        )
        assert len(service.stats["errors"]) == 1
        assert "Error processing section" in service.stats["errors"][0]
