"""
Unit tests for the new adapter-based ImportService.

Tests the ImportService with the new adapter registry system.
"""

import tempfile
from datetime import datetime, timezone
from typing import Any
from unittest.mock import Mock, patch

from src.services.import_service import (
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

    def test_convert_datetime_fields_with_string_timestamps(self) -> None:
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

    def test_convert_datetime_fields_with_existing_datetime_objects(self) -> None:
        """Test that existing datetime objects are left unchanged."""
        now = datetime.now(timezone.utc)
        data = {
            "created_at": now,
            "updated_at": "2025-09-28T17:41:27.935901",
        }

        result = _convert_datetime_fields(data)

        assert result["created_at"] is now  # Same object
        assert isinstance(result["updated_at"], datetime)

    def test_convert_datetime_fields_with_invalid_strings(self) -> None:
        """Test that invalid datetime strings are left unchanged."""
        data = {
            "created_at": "not a valid datetime",
            "updated_at": "2025-09-28T17:41:27.935901",
        }

        result = _convert_datetime_fields(data)

        assert result["created_at"] == "not a valid datetime"  # Unchanged
        assert isinstance(result["updated_at"], datetime)

    def test_convert_datetime_fields_with_none_values(self) -> None:
        """Test that None values are left unchanged."""
        data = {
            "created_at": None,
            "updated_at": "2025-09-28T17:41:27.935901",
        }

        result = _convert_datetime_fields(data)

        assert result["created_at"] is None
        assert isinstance(result["updated_at"], datetime)

    def test_convert_datetime_fields_with_z_format(self) -> None:
        """Test datetime with Z suffix (UTC indicator)."""
        from src.services.import_service import _normalize_datetime_string

        # Z format with microseconds should be converted to +00:00
        result = _normalize_datetime_string("2025-09-28T17:41:27.935901Z")
        assert result == "2025-09-28T17:41:27.935901+00:00"

    def test_convert_datetime_fields_already_normalized(self) -> None:
        """Test datetime that already has UTC offset."""
        from src.services.import_service import _normalize_datetime_string

        # Already has +00:00, should be returned as-is
        result = _normalize_datetime_string("2025-09-28T17:41:27.935901+00:00")
        assert result == "2025-09-28T17:41:27.935901+00:00"


class TestEnumsAndDataClasses:
    """Test enums and data classes."""

    def test_conflict_strategy_enum(self) -> None:
        """Test ConflictStrategy enum values."""
        assert ConflictStrategy.USE_MINE.value == "use_mine"
        assert ConflictStrategy.USE_THEIRS.value == "use_theirs"
        assert ConflictStrategy.MERGE.value == "merge"
        assert ConflictStrategy.MANUAL_REVIEW.value == "manual_review"

    def test_import_mode_enum(self) -> None:
        """Test ImportMode enum values."""
        assert ImportMode.DRY_RUN.value == "dry_run"
        assert ImportMode.EXECUTE.value == "execute"

    def test_import_result_creation(self) -> None:
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

    def test_conflict_record_creation(self) -> None:
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

    def test_create_import_report_success(self) -> None:
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

    def test_create_import_report_with_errors(self) -> None:
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

    def test_process_course_import_update_existing(self) -> None:
        """Test updating existing course with USE_THEIRS strategy."""
        course_data = {
            "course_number": "CS101",
            "title": "Updated Computer Science",
            "department": "Computer Science",
            "credits": 4,
        }

        with (
            patch(
                "src.services.import_service.get_course_by_number"
            ) as mock_get_course,
            patch("src.services.import_service.create_course") as mock_create_course,
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

    def test_process_user_import_update_existing(self) -> None:
        """Test updating existing user with USE_THEIRS strategy."""
        user_data = {
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Updated",
            "role": "instructor",
        }

        with (
            patch("src.services.import_service.get_user_by_email") as mock_get_user,
            patch("src.services.import_service.update_user") as mock_update_user,
            patch("src.services.import_service.create_user") as mock_create_user,
        ):

            # Mock existing user (must have matching institution_id)
            mock_get_user.return_value = {
                "user_id": "user_123",
                "email": "test@example.com",
                "first_name": "John",
                "last_name": "Old",
                "role": "instructor",
                "institution_id": "inst_123",
            }

            service = ImportService("inst_123")
            success, conflicts = service.process_user_import(
                user_data, ConflictStrategy.USE_THEIRS, dry_run=False
            )

            assert success is True
            assert len(conflicts) > 0  # Should detect conflicts
            assert service.stats["records_updated"] == 1
            assert service.stats["conflicts_resolved"] > 0
            # Check update_user was called (email should be removed from update data)
            mock_update_user.assert_called_once()
            call_args = mock_update_user.call_args[0]
            assert call_args[0] == "user_123"
            assert "email" not in call_args[1]  # Email should NOT be in update data
            mock_create_user.assert_not_called()  # Should not create new user


class TestImportServiceHelpers:
    """Test ImportService helper methods."""

    def test_prepare_import_file_not_found(self) -> None:
        """Test _prepare_import with non-existent file."""
        service = ImportService("test_inst")
        service.reset_stats()

        result = service._prepare_import("/nonexistent/file.xlsx", "test_adapter")

        assert result is None
        assert len(service.stats["errors"]) > 0
        assert "File not found" in service.stats["errors"][0]

    def test_prepare_import_adapter_not_found(self) -> None:
        """Test _prepare_import with invalid adapter."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as temp_file:
            service = ImportService("test_inst")
            service.reset_stats()

            with patch(
                "src.services.import_service.get_adapter_registry"
            ) as mock_registry:
                mock_reg = Mock()
                mock_reg.get_adapter_by_id.return_value = None
                mock_registry.return_value = mock_reg

                result = service._prepare_import(temp_file.name, "invalid_adapter")

                assert result is None
                assert len(service.stats["errors"]) > 0
                assert "Adapter not found" in service.stats["errors"][0]

    def test_prepare_import_file_incompatible(self) -> None:
        """Test _prepare_import with incompatible file."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as temp_file:
            service = ImportService("test_inst")
            service.reset_stats()

            with patch(
                "src.services.import_service.get_adapter_registry"
            ) as mock_registry:
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

    def test_prepare_import_success(self) -> None:
        """Test _prepare_import with valid inputs."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as temp_file:
            service = ImportService("test_inst")
            service.reset_stats()

            with patch(
                "src.services.import_service.get_adapter_registry"
            ) as mock_registry:
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

    def test_parse_file_data_success(self) -> None:
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

    def test_parse_file_data_parse_error(self) -> None:
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

    def test_parse_file_data_empty_result(self) -> None:
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


class TestImportServiceRolePreservation:
    """Test role preservation logic added for demo."""

    def test_should_preserve_role_site_admin_over_instructor(self) -> None:
        """Test that site_admin role is preserved over instructor."""
        service = ImportService("inst-123")
        assert service._should_preserve_role("site_admin", "instructor") is True

    def test_should_preserve_role_institution_admin_over_instructor(self) -> None:
        """Test that institution_admin role is preserved over instructor."""
        service = ImportService("inst-123")
        assert service._should_preserve_role("institution_admin", "instructor") is True

    def test_should_preserve_role_program_admin_over_instructor(self) -> None:
        """Test that program_admin role is preserved over instructor."""
        service = ImportService("inst-123")
        assert service._should_preserve_role("program_admin", "instructor") is True

    def test_should_preserve_role_same_roles(self) -> None:
        """Test that same roles don't trigger preservation."""
        service = ImportService("inst-123")
        assert service._should_preserve_role("instructor", "instructor") is False

    def test_should_preserve_role_lower_to_higher(self) -> None:
        """Test that lower roles don't override higher roles."""
        service = ImportService("inst-123")
        assert service._should_preserve_role("instructor", "site_admin") is False

    def test_should_preserve_role_institution_admin_over_program_admin(self) -> None:
        """Test role hierarchy between admin types."""
        service = ImportService("inst-123")
        assert (
            service._should_preserve_role("institution_admin", "program_admin") is True
        )

    def test_should_preserve_role_unknown_roles(self) -> None:
        """Test handling of unknown roles."""
        service = ImportService("inst-123")
        # Unknown roles get level 0, so neither is preserved
        assert service._should_preserve_role("unknown", "instructor") is False
        assert service._should_preserve_role("instructor", "unknown") is True


class TestCLOImportFeature:
    """Test NEW CLO import functionality added in this PR"""

    @patch("src.services.import_service.create_course_outcome")
    @patch("src.services.import_service.get_course_outcomes")
    @patch("src.services.import_service.get_course_by_number")
    def test_process_clo_import_success(
        self, mock_get_course: Any, mock_get_outcomes: Any, mock_create_outcome: Any
    ) -> None:
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

    @patch("src.services.import_service.get_course_by_number")
    def test_process_clo_import_missing_fields(self, mock_get_course: Any) -> None:
        """Test CLO import fails gracefully with missing required fields"""
        service = ImportService("inst-123")

        # Missing clo_number
        clo_data = {"course_number": "BIO101", "description": "Test"}
        service._process_clo_import(
            clo_data, ConflictStrategy.USE_THEIRS, dry_run=False
        )
        assert len(service.stats["errors"]) == 1
        assert "Missing required fields" in service.stats["errors"][0]

    @patch("src.services.import_service.get_course_by_number")
    def test_process_clo_import_course_not_found(self, mock_get_course: Any) -> None:
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

    @patch("src.services.import_service.get_course_outcomes")
    @patch("src.services.import_service.get_course_by_number")
    def test_process_clo_import_conflict_use_mine(
        self, mock_get_course: Any, mock_get_outcomes: Any
    ) -> None:
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

    @patch("src.services.import_service.get_course_outcomes")
    @patch("src.services.import_service.get_course_by_number")
    def test_process_clo_import_conflict_use_theirs(
        self, mock_get_course: Any, mock_get_outcomes: Any
    ) -> None:
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

    @patch("src.services.import_service.get_course_by_number")
    def test_process_clo_import_dry_run(self, mock_get_course: Any) -> None:
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

    @patch("src.services.import_service.create_course_outcome")
    @patch("src.services.import_service.get_course_outcomes")
    @patch("src.services.import_service.get_course_by_number")
    def test_process_clo_import_create_fails(
        self, mock_get_course: Any, mock_get_outcomes: Any, mock_create_outcome: Any
    ) -> None:
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

    @patch("src.services.import_service.get_course_by_number")
    def test_process_clo_import_exception_handling(self, mock_get_course: Any) -> None:
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

    @patch("src.database.database_service.add_course_to_program")
    @patch("src.database.database_service.get_programs_by_institution")
    @patch("src.database.database_service.get_all_courses")
    def test_link_courses_to_programs_success(
        self, mock_get_courses: Any, mock_get_programs: Any, mock_add_course: Any
    ) -> None:
        """Test successful course-program linking based on prefix"""
        # Use correct primary keys: course_id for courses, program_id for programs
        mock_get_courses.return_value = [
            {"course_id": "c1", "course_number": "BIOL-101"},
            {"course_id": "c2", "course_number": "BSN-202"},
            {"course_id": "c3", "course_number": "ZOOL-303"},
        ]
        mock_get_programs.return_value = [
            {"program_id": "p1", "name": "Biological Sciences"},
            {"program_id": "p2", "name": "Zoology"},
        ]

        service = ImportService("inst-123")
        service._link_courses_to_programs()

        # Should link BIOL and BSN to Biological Sciences, ZOOL to Zoology
        assert mock_add_course.call_count == 3
        calls = mock_add_course.call_args_list
        assert calls[0][0] == ("c1", "p1")  # BIOL → Biological Sciences
        assert calls[1][0] == ("c2", "p1")  # BSN → Biological Sciences
        assert calls[2][0] == ("c3", "p2")  # ZOOL → Zoology

    @patch("src.database.database_service.get_programs_by_institution")
    @patch("src.database.database_service.get_all_courses")
    def test_link_courses_no_courses(
        self, mock_get_courses: Any, mock_get_programs: Any
    ) -> None:
        """Test linking handles no courses gracefully"""
        mock_get_courses.return_value = []
        mock_get_programs.return_value = [{"program_id": "p1", "name": "Test"}]

        service = ImportService("inst-123")
        service._link_courses_to_programs()  # Should not crash

    @patch("src.database.database_service.get_programs_by_institution")
    @patch("src.database.database_service.get_all_courses")
    def test_link_courses_no_programs(
        self, mock_get_courses: Any, mock_get_programs: Any
    ) -> None:
        """Test linking handles no programs gracefully"""
        mock_get_courses.return_value = [
            {"course_id": "c1", "course_number": "BIOL-101"}
        ]
        mock_get_programs.return_value = []

        service = ImportService("inst-123")
        service._link_courses_to_programs()  # Should not crash

    @patch("src.database.database_service.add_course_to_program")
    @patch("src.database.database_service.get_programs_by_institution")
    @patch("src.database.database_service.get_all_courses")
    def test_link_courses_unmapped_prefix(
        self, mock_get_courses: Any, mock_get_programs: Any, mock_add_course: Any
    ) -> None:
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

    @patch("src.database.database_service.add_course_to_program")
    @patch("src.database.database_service.get_programs_by_institution")
    @patch("src.database.database_service.get_all_courses")
    def test_link_courses_program_not_found(
        self, mock_get_courses: Any, mock_get_programs: Any, mock_add_course: Any
    ) -> None:
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

    @patch("src.database.database_service.add_course_to_program")
    @patch("src.database.database_service.get_programs_by_institution")
    @patch("src.database.database_service.get_all_courses")
    def test_link_courses_already_linked(
        self, mock_get_courses: Any, mock_get_programs: Any, mock_add_course: Any
    ) -> None:
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

    @patch("src.database.database_service.get_all_courses")
    def test_link_courses_exception_doesnt_fail_import(
        self, mock_get_courses: Any
    ) -> None:
        """Test linking failure doesn't break the import"""
        mock_get_courses.side_effect = Exception("Database error")

        service = ImportService("inst-123")
        service._link_courses_to_programs()  # Should not crash - just log warning


class TestOfferingImportErrorPaths:
    """Test error paths and edge cases in _process_offering_import"""

    @patch("src.services.import_service.get_course_by_number")
    @patch("src.services.import_service.get_term_by_name")
    def test_offering_import_missing_course_number(
        self, mock_get_term: Any, mock_get_course: Any
    ) -> None:
        """Test offering import fails gracefully when course_number is missing"""
        service = ImportService("inst-123")
        service._process_offering_import(
            {"term_name": "Fall 2024"}, ConflictStrategy.USE_THEIRS, dry_run=False
        )
        assert len(service.stats["errors"]) == 1
        assert "Missing course_number or term_name" in service.stats["errors"][0]

    @patch("src.services.import_service.get_course_by_number")
    @patch("src.services.import_service.get_term_by_name")
    def test_offering_import_missing_term_name(
        self, mock_get_term: Any, mock_get_course: Any
    ) -> None:
        """Test offering import fails gracefully when term_name is missing"""
        service = ImportService("inst-123")
        service._process_offering_import(
            {"course_number": "BIO101"}, ConflictStrategy.USE_THEIRS, dry_run=False
        )
        assert len(service.stats["errors"]) == 1
        assert "Missing course_number or term_name" in service.stats["errors"][0]

    @patch("src.services.import_service.get_term_by_name")
    @patch("src.services.import_service.get_course_by_number")
    def test_offering_import_course_not_found(
        self, mock_get_course: Any, mock_get_term: Any
    ) -> None:
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

    @patch("src.services.import_service.get_term_by_name")
    @patch("src.services.import_service.get_course_by_number")
    def test_offering_import_term_not_found(
        self, mock_get_course: Any, mock_get_term: Any
    ) -> None:
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

    @patch("src.services.import_service.get_course_offering_by_course_and_term")
    @patch("src.services.import_service.get_term_by_name")
    @patch("src.services.import_service.get_course_by_number")
    def test_offering_import_dry_run(
        self, mock_get_course: Any, mock_get_term: Any, mock_get_offering: Any
    ) -> None:
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

    @patch("src.services.import_service.create_course_offering")
    @patch("src.services.import_service.get_course_offering_by_course_and_term")
    @patch("src.services.import_service.get_term_by_name")
    @patch("src.services.import_service.get_course_by_number")
    def test_offering_import_creation_fails(
        self,
        mock_get_course: Any,
        mock_get_term: Any,
        mock_get_offering: Any,
        mock_create_offering: Any,
    ) -> None:
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

    @patch("src.services.import_service.get_term_by_name")
    @patch("src.services.import_service.get_course_by_number")
    def test_offering_import_exception_handling(
        self, mock_get_course: Any, mock_get_term: Any
    ) -> None:
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

    @patch("src.services.import_service.get_course_by_number")
    @patch("src.services.import_service.get_term_by_name")
    def test_section_import_missing_course_number(
        self, mock_get_term: Any, mock_get_course: Any
    ) -> None:
        """Test section import fails gracefully when course_number is missing"""
        service = ImportService("inst-123")
        service._process_section_import(
            {"term_name": "Fall 2024", "section_number": "001"},
            dry_run=False,
        )
        assert len(service.stats["errors"]) == 1
        assert "Missing course_number or term_name" in service.stats["errors"][0]

    @patch("src.services.import_service.get_term_by_name")
    @patch("src.services.import_service.get_course_by_number")
    def test_section_import_course_not_found(
        self, mock_get_course: Any, mock_get_term: Any
    ) -> None:
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

    @patch("src.services.import_service.get_term_by_name")
    @patch("src.services.import_service.get_course_by_number")
    def test_section_import_term_not_found(
        self, mock_get_course: Any, mock_get_term: Any
    ) -> None:
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

    @patch("src.services.import_service.get_course_offering_by_course_and_term")
    @patch("src.services.import_service.get_term_by_name")
    @patch("src.services.import_service.get_course_by_number")
    def test_section_import_dry_run(
        self, mock_get_course: Any, mock_get_term: Any, mock_get_offering: Any
    ) -> None:
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

    @patch("src.services.import_service.create_course_section")
    @patch("src.services.import_service.get_user_by_email")
    @patch("src.services.import_service.get_course_offering_by_course_and_term")
    @patch("src.services.import_service.get_term_by_name")
    @patch("src.services.import_service.get_course_by_number")
    def test_section_import_creation_fails(
        self,
        mock_get_course: Any,
        mock_get_term: Any,
        mock_get_offering: Any,
        mock_get_user: Any,
        mock_create_section: Any,
    ) -> None:
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

    @patch("src.services.import_service.get_term_by_name")
    @patch("src.services.import_service.get_course_by_number")
    def test_section_import_exception_handling(
        self, mock_get_course: Any, mock_get_term: Any
    ) -> None:
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
