"""
Unit tests for the new adapter-based ImportService

Tests the ImportService with the new adapter registry system.
"""

import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from import_service import (
    ConflictRecord,
    ConflictStrategy,
    ImportMode,
    ImportResult,
    ImportService,
    create_import_report,
    import_excel,
)


class TestImportService:
    """Test the new adapter-based ImportService functionality."""

    def setup_method(self):
        """Set up each test."""
        self.institution_id = "test-institution"
        self.service = ImportService(self.institution_id, verbose=True)

    def test_import_service_initialization(self):
        """Test ImportService initialization."""
        assert self.service.institution_id == self.institution_id
        assert self.service.verbose is True
        assert self.service.progress_callback is None
        assert len(self.service.stats["errors"]) == 0

    def test_import_service_initialization_requires_institution_id(self):
        """Test ImportService requires institution_id."""
        with pytest.raises(ValueError, match="institution_id is required"):
            ImportService(None)

    def test_reset_stats(self):
        """Test reset_stats functionality."""
        # Add some dummy stats
        self.service.stats["errors"].append("test error")
        self.service.stats["records_processed"] = 5

        # Reset stats
        self.service.reset_stats()

        assert self.service.stats["records_processed"] == 0
        assert len(self.service.stats["errors"]) == 0
        assert len(self.service.stats["warnings"]) == 0

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
            patch("import_service.create_user"),
            patch("import_service.create_course"),
            patch("import_service.create_term"),
            patch("database_service.db") as mock_db,
        ):

            # Mock Firestore query for terms
            mock_collection = Mock()
            mock_collection.where.return_value.where.return_value.get.return_value = []
            mock_db.collection.return_value = mock_collection

            result = self.service.import_excel_file("test.xlsx")

            assert result.success is True
            assert result.records_processed == 3  # 1 user + 1 course + 1 term
            assert result.records_created == 3
            assert len(result.errors) == 0

    @patch("import_service.get_adapter_registry")
    @patch("import_service.os.path.exists")
    def test_import_excel_file_dry_run_mode(self, mock_exists, mock_get_registry):
        """Test import in dry run mode."""
        mock_exists.return_value = True

        # Mock adapter
        mock_adapter = Mock()
        mock_adapter.validate_file_compatibility.return_value = (
            True,
            "File is compatible",
        )
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
    def test_import_excel_file_with_progress_callback(
        self, mock_exists, mock_get_registry
    ):
        """Test import with progress callback."""
        mock_exists.return_value = True

        # Create service with progress callback
        progress_callback = Mock()
        service = ImportService(
            self.institution_id, progress_callback=progress_callback
        )

        # Mock adapter with multiple records
        mock_adapter = Mock()
        mock_adapter.validate_file_compatibility.return_value = (
            True,
            "File is compatible",
        )
        mock_adapter.parse_file.return_value = {
            "users": [
                {
                    "email": "user1@example.com",
                    "first_name": "User",
                    "last_name": "One",
                },
                {
                    "email": "user2@example.com",
                    "first_name": "User",
                    "last_name": "Two",
                },
                {
                    "email": "user3@example.com",
                    "first_name": "User",
                    "last_name": "Three",
                },
            ]
        }

        mock_registry = Mock()
        mock_registry.get_adapter_by_id.return_value = mock_adapter
        mock_get_registry.return_value = mock_registry

        # Mock database operations
        with (
            patch("import_service.get_user_by_email", return_value=None),
            patch("import_service.create_user"),
        ):

            result = service.import_excel_file("test.xlsx")

            assert result.success is True
            assert progress_callback.called
            # Should be called at least once for progress updates
            assert progress_callback.call_count >= 1

    def test_process_course_import_new_course(self):
        """Test processing a new course import."""
        course_data = {
            "course_number": "TEST-101",
            "course_title": "Test Course",
            "department": "Test Department",
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
            mock_create.assert_called_once_with(course_data)
            assert self.service.stats["records_created"] == 1

    def test_process_course_import_existing_course_use_mine(self):
        """Test processing existing course with USE_MINE strategy."""
        course_data = {"course_number": "TEST-101", "course_title": "Test Course"}

        existing_course = {
            "course_number": "TEST-101",
            "course_title": "Existing Course",
        }

        with (
            patch("import_service.get_course_by_number", return_value=existing_course),
            patch("import_service.create_course") as mock_create,
        ):

            success, conflicts = self.service.process_course_import(
                course_data, ConflictStrategy.USE_MINE, dry_run=False
            )

            assert success is True
            mock_create.assert_not_called()
            assert self.service.stats["records_skipped"] == 1

    def test_process_user_import_new_user(self):
        """Test processing a new user import."""
        user_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
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
            mock_create.assert_called_once_with(user_data)
            assert self.service.stats["records_created"] == 1

    def test_process_user_import_missing_email(self):
        """Test processing user import with missing email."""
        user_data = {
            "first_name": "Test",
            "last_name": "User",
            # Missing email
        }

        success, conflicts = self.service.process_user_import(
            user_data, ConflictStrategy.USE_THEIRS, dry_run=False
        )

        assert success is False
        assert "User missing email" in self.service.stats["errors"]

    def test_process_term_import_new_term(self):
        """Test processing a new term import."""
        term_data = {
            "term_name": "Fall 2024",
            "institution_id": self.institution_id,
            "start_date": "2024-08-01",
            "end_date": "2024-12-15",
        }

        with (
            patch("database_service.db") as mock_db,
            patch("import_service.create_term") as mock_create,
        ):

            # Mock empty query result (term doesn't exist)
            mock_collection = Mock()
            mock_collection.where.return_value.where.return_value.get.return_value = []
            mock_db.collection.return_value = mock_collection

            self.service._process_term_import(term_data, dry_run=False)

            mock_create.assert_called_once_with(term_data)
            assert self.service.stats["records_created"] == 1

    def test_process_term_import_existing_term(self):
        """Test processing existing term import."""
        term_data = {"term_name": "Fall 2024", "institution_id": self.institution_id}

        with (
            patch("database_service.db") as mock_db,
            patch("import_service.create_term") as mock_create,
        ):

            # Mock query result with existing term
            mock_doc = Mock()
            mock_collection = Mock()
            mock_collection.where.return_value.where.return_value.get.return_value = [
                mock_doc
            ]
            mock_db.collection.return_value = mock_collection

            self.service._process_term_import(term_data, dry_run=False)

            mock_create.assert_not_called()
            assert self.service.stats["records_skipped"] == 1

    @patch("import_service.get_adapter_registry")
    @patch("import_service.os.path.exists")
    def test_import_excel_file_delete_existing_db(self, mock_exists, mock_get_registry):
        """Test import with delete_existing_db option."""
        mock_exists.return_value = True

        # Mock adapter
        mock_adapter = Mock()
        mock_adapter.validate_file_compatibility.return_value = (
            True,
            "File is compatible",
        )
        mock_adapter.parse_file.return_value = {"users": []}

        mock_registry = Mock()
        mock_registry.get_adapter_by_id.return_value = mock_adapter
        mock_get_registry.return_value = mock_registry

        with patch.object(self.service, "_delete_all_data") as mock_delete:
            result = self.service.import_excel_file(
                "test.xlsx", delete_existing_db=True
            )

            mock_delete.assert_called_once()

    def test_delete_all_data(self):
        """Test _delete_all_data functionality."""
        with patch("database_service.db") as mock_db:
            # Mock collections and documents
            mock_doc = Mock()
            mock_collection = Mock()
            mock_collection.stream.return_value = [mock_doc]
            mock_db.collection.return_value = mock_collection

            self.service._delete_all_data()

            # Should delete from all collections
            expected_collections = [
                "courses",
                "users",
                "terms",
                "course_offerings",
                "course_sections",
                "institutions",
                "programs",
            ]

            assert mock_db.collection.call_count == len(expected_collections)
            mock_doc.reference.delete.assert_called()


class TestConvenienceFunction:
    """Test the import_excel convenience function."""

    @patch("import_service.ImportService")
    def test_import_excel_convenience_function(self, mock_service_class):
        """Test import_excel convenience function."""
        # Mock service instance
        mock_service = Mock()
        mock_result = ImportResult(
            success=True,
            records_processed=1,
            records_created=1,
            records_updated=0,
            records_skipped=0,
            conflicts_detected=0,
            conflicts_resolved=0,
            errors=[],
            warnings=[],
            conflicts=[],
            execution_time=1.0,
            dry_run=False,
        )
        mock_service.import_excel_file.return_value = mock_result
        mock_service_class.return_value = mock_service

        result = import_excel(
            file_path="test.xlsx",
            institution_id="test-institution",
            conflict_strategy="use_theirs",
            dry_run=False,
            adapter_id="cei_excel_format_v1",
        )

        assert result.success is True
        mock_service_class.assert_called_once_with(
            institution_id="test-institution", verbose=False, progress_callback=None
        )
        mock_service.import_excel_file.assert_called_once()


class TestDataClasses:
    """Test the data classes and enums."""

    def test_conflict_record_creation(self):
        """Test ConflictRecord creation."""
        conflict = ConflictRecord(
            entity_type="course",
            entity_id="TEST-101",
            field_name="course_title",
            existing_value="Old Title",
            import_value="New Title",
            resolution="use_theirs",
            timestamp=datetime.now(timezone.utc),
        )

        assert conflict.entity_type == "course"
        assert conflict.entity_id == "TEST-101"
        assert conflict.field_name == "course_title"

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

        assert "IMPORT REPORT" in report
        assert "Success: True" in report
        assert "Records Processed: 5" in report
        assert "Execution Time: 1.23s" in report

    def test_create_import_report_with_errors(self):
        """Test creating report with errors."""
        result = ImportResult(
            success=False,
            records_processed=2,
            records_created=1,
            records_updated=0,
            records_skipped=0,
            conflicts_detected=1,
            conflicts_resolved=0,
            errors=["File not found", "Invalid data format"],
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
