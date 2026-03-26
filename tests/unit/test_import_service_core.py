"""Core ImportService behavior tests."""

import os
import tempfile
from typing import Any
from unittest.mock import Mock, patch

from src.services.import_service import ConflictStrategy, ImportService


class TestImportService:
    """Test the ImportService class with adapter registry integration."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.institution_id = "test-institution-id"
        self.service = ImportService(self.institution_id)

    def test_process_course_import_conflict_detection(self) -> None:
        """Test that process_course_import detects conflicts correctly."""
        course_data = {
            "course_number": "CS-101",
            "title": "Introduction to Computer Science",
            "credits": 3,
        }
        existing_course = {
            "course_number": "CS-101",
            "title": "Computer Science 101",
            "credits": 4,
        }

        with patch(
            "src.services.import_service.get_course_by_number"
        ) as mock_get_course:
            mock_get_course.return_value = existing_course

            result, conflicts = self.service.process_course_import(
                course_data, ConflictStrategy.USE_MINE, dry_run=False
            )

            assert result is True
            assert len(conflicts) > 0

    @patch("src.services.import_service.get_adapter_registry")
    def test_import_excel_file_adapter_not_found(self, mock_get_registry: Any) -> None:
        """Test import_excel_file with adapter not found."""
        mock_registry = Mock()
        mock_registry.get_adapter_by_id.return_value = None
        mock_get_registry.return_value = mock_registry

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

    @patch("src.services.import_service.get_adapter_registry")
    def test_import_excel_file_file_not_found(self, mock_get_registry: Any) -> None:
        """Test import_excel_file with non-existent file."""
        result = self.service.import_excel_file("/nonexistent/file.xlsx")

        assert result.success is False
        assert len(result.errors) == 1
        assert "File not found" in result.errors[0]

    @patch("src.services.import_service.get_adapter_registry")
    @patch("src.services.import_service.os.path.exists")
    def test_import_excel_file_file_incompatible(
        self, mock_exists: Any, mock_get_registry: Any
    ) -> None:
        """Test import_excel_file with incompatible file."""
        mock_exists.return_value = True

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

    @patch("src.services.import_service.get_adapter_registry")
    @patch("src.services.import_service.os.path.exists")
    def test_import_excel_file_successful_import(
        self, mock_exists: Any, mock_get_registry: Any
    ) -> None:
        """Test successful import with mock adapter."""
        mock_exists.return_value = True

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

        with (
            patch("src.services.import_service.get_user_by_email", return_value=None),
            patch(
                "src.services.import_service.get_course_by_number", return_value=None
            ),
            patch("src.services.import_service.get_term_by_name", return_value=None),
            patch("src.services.import_service.create_user"),
            patch("src.services.import_service.create_course"),
            patch("src.services.import_service.create_term"),
        ):
            result = self.service.import_excel_file("test.xlsx")

            assert result.success is True
            assert result.records_processed == 3
            assert result.records_created == 3

    @patch("src.services.import_service.get_adapter_registry")
    @patch("src.services.import_service.os.path.exists")
    def test_import_excel_file_dry_run(
        self, mock_exists: Any, mock_get_registry: Any
    ) -> None:
        """Test dry run mode."""
        mock_exists.return_value = True

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

        with (
            patch("src.services.import_service.get_user_by_email", return_value=None),
            patch("src.services.import_service.create_user") as mock_create_user,
        ):
            result = self.service.import_excel_file("test.xlsx", dry_run=True)

            assert result.success is True
            assert result.dry_run is True
            assert result.records_processed == 1
            mock_create_user.assert_not_called()

    @patch("src.services.import_service.get_adapter_registry")
    @patch("src.services.import_service.os.path.exists")
    def test_import_excel_file_with_conflicts(
        self, mock_exists: Any, mock_get_registry: Any
    ) -> None:
        """Test import with conflict resolution."""
        mock_exists.return_value = True

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

        existing_user = {
            "email": "existing@example.com",
            "first_name": "Original",
            "institution_id": self.institution_id,
        }

        with (
            patch(
                "src.services.import_service.get_user_by_email",
                return_value=existing_user,
            ),
            patch("src.services.import_service.update_user") as mock_update_user,
        ):
            result = self.service.import_excel_file(
                "test.xlsx", conflict_strategy=ConflictStrategy.USE_THEIRS
            )

            assert result.success is True
            assert result.conflicts_detected >= 1
            mock_update_user.assert_called()

    def test_process_course_import_new_course(self) -> None:
        """Test processing a new course import."""
        course_data = {
            "course_number": "NEW-101",
            "course_title": "New Course",
            "institution_id": self.institution_id,
        }

        with (
            patch(
                "src.services.import_service.get_course_by_number", return_value=None
            ),
            patch("src.services.import_service.create_course") as mock_create,
        ):
            success, conflicts = self.service.process_course_import(
                course_data, ConflictStrategy.USE_THEIRS, dry_run=False
            )

            assert success is True
            assert len(conflicts) == 0
            mock_create.assert_called_once()

    def test_process_course_import_dry_run(self) -> None:
        """Test processing course import in dry run mode."""
        course_data = {
            "course_number": "DRY-101",
            "course_title": "Dry Run Course",
            "institution_id": self.institution_id,
        }

        with (
            patch(
                "src.services.import_service.get_course_by_number", return_value=None
            ),
            patch("src.services.import_service.create_course") as mock_create,
        ):
            success, conflicts = self.service.process_course_import(
                course_data, ConflictStrategy.USE_THEIRS, dry_run=True
            )

            assert success is True
            mock_create.assert_not_called()
            assert self.service.stats["records_skipped"] == 1

    def test_process_user_import_new_user(self) -> None:
        """Test processing a new user import."""
        user_data = {
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
            "institution_id": self.institution_id,
        }

        with (
            patch("src.services.import_service.get_user_by_email", return_value=None),
            patch("src.services.import_service.create_user") as mock_create,
        ):
            success, conflicts = self.service.process_user_import(
                user_data, ConflictStrategy.USE_THEIRS, dry_run=False
            )

            assert success is True
            assert len(conflicts) == 0
            mock_create.assert_called_once()
