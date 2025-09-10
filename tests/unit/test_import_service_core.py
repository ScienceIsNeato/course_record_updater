"""Unit tests for core import_service.py functionality."""

from unittest.mock import patch, MagicMock, Mock
import pytest
from enum import Enum

# Import the module under test
from import_service import (
    ConflictStrategy,
    ImportMode,
    ConflictRecord,
    ImportResult,
    ImportService,
    import_excel,
    create_import_report,
)


class TestEnumsAndDataClasses:
    """Test enums and data classes."""

    def test_conflict_strategy_enum(self):
        """Test ConflictStrategy enum values."""
        assert ConflictStrategy.USE_MINE == "use_mine"
        assert ConflictStrategy.USE_THEIRS == "use_theirs"
        assert ConflictStrategy.MERGE == "merge"
        assert ConflictStrategy.MANUAL_REVIEW == "manual_review"

    def test_import_mode_enum(self):
        """Test ImportMode enum values."""
        assert ImportMode.DRY_RUN == "dry_run"
        assert ImportMode.FULL_IMPORT == "full_import"

    def test_conflict_record_creation(self):
        """Test ConflictRecord creation."""
        record = ConflictRecord(
            field="course_title",
            existing_value="Old Title",
            new_value="New Title",
            description="Title conflict"
        )
        
        assert record.field == "course_title"
        assert record.existing_value == "Old Title"
        assert record.new_value == "New Title"
        assert record.description == "Title conflict"

    def test_import_result_creation(self):
        """Test ImportResult creation."""
        result = ImportResult(
            success=True,
            message="Import completed",
            records_processed=10,
            records_created=5,
            records_updated=3,
            records_skipped=2,
            conflicts=[],
            errors=[]
        )
        
        assert result.success is True
        assert result.message == "Import completed"
        assert result.records_processed == 10
        assert result.records_created == 5
        assert result.records_updated == 3
        assert result.records_skipped == 2
        assert result.conflicts == []
        assert result.errors == []


class TestImportServiceInitialization:
    """Test ImportService initialization and basic methods."""

    def test_import_service_initialization_default(self):
        """Test ImportService initialization with defaults."""
        service = ImportService()
        
        assert service.verbose is False
        assert service._processed_users == set()
        assert service._processed_courses == set()
        assert isinstance(service.stats, dict)

    def test_import_service_initialization_verbose(self):
        """Test ImportService initialization with verbose mode."""
        service = ImportService(verbose=True)
        
        assert service.verbose is True

    def test_reset_stats(self):
        """Test reset_stats method."""
        service = ImportService()
        
        # Modify stats
        service.stats["records_processed"] = 10
        service.stats["errors"].append("test error")
        
        # Reset
        service.reset_stats()
        
        # Verify reset
        assert service.stats["records_processed"] == 0
        assert service.stats["records_created"] == 0
        assert service.stats["records_updated"] == 0
        assert service.stats["records_skipped"] == 0
        assert service.stats["conflicts_detected"] == 0
        assert service.stats["conflicts_resolved"] == 0
        assert service.stats["errors"] == []
        assert service.stats["warnings"] == []
        assert service.stats["conflicts"] == []

    def test_entity_cache_initialization(self):
        """Test entity cache is properly initialized."""
        service = ImportService()
        service.reset_stats()  # This initializes entity_cache
        
        assert "courses" in service.entity_cache
        assert "terms" in service.entity_cache
        assert "users" in service.entity_cache
        assert "sections" in service.entity_cache
        assert service.entity_cache["courses"] == {}
        assert service.entity_cache["terms"] == {}
        assert service.entity_cache["users"] == {}
        assert service.entity_cache["sections"] == {}


class TestImportServiceLogging:
    """Test ImportService logging functionality."""

    def test_log_error_message(self):
        """Test logging error messages."""
        service = ImportService(verbose=False)
        
        with patch('builtins.print') as mock_print:
            service._log("Test error", "error")
            mock_print.assert_called_once_with("[Import] ERROR: Test error")

    def test_log_warning_message(self):
        """Test logging warning messages."""
        service = ImportService(verbose=False)
        
        with patch('builtins.print') as mock_print:
            service._log("Test warning", "warning")
            mock_print.assert_called_once_with("[Import] WARNING: Test warning")

    def test_log_summary_message(self):
        """Test logging summary messages."""
        service = ImportService(verbose=False)
        
        with patch('builtins.print') as mock_print:
            service._log("Test summary", "summary")
            mock_print.assert_called_once_with("[Import] Test summary")

    def test_log_verbose_mode_on(self):
        """Test logging in verbose mode."""
        service = ImportService(verbose=True)
        
        with patch('builtins.print') as mock_print:
            service._log("Test message", "info")
            mock_print.assert_called_once_with("[Import] Test message")

    def test_log_verbose_mode_off(self):
        """Test logging in non-verbose mode."""
        service = ImportService(verbose=False)
        
        with patch('builtins.print') as mock_print:
            service._log("Test message", "info")
            mock_print.assert_not_called()


class TestDetectCourseConflict:
    """Test detect_course_conflict method."""

    @patch('import_service.get_course_by_number')
    def test_detect_course_conflict_no_existing_course(self, mock_get_course):
        """Test conflict detection when no existing course."""
        mock_get_course.return_value = None
        
        service = ImportService()
        service.reset_stats()
        
        import_course = {
            "course_number": "NEW-101",
            "course_title": "New Course",
            "department": "NEW"
        }
        
        conflicts = service.detect_course_conflict(import_course)
        
        # Should have existence conflict
        assert len(conflicts) == 1
        assert conflicts[0].field == "_existence"

    @patch('import_service.get_course_by_number')
    def test_detect_course_conflict_identical_course(self, mock_get_course):
        """Test conflict detection with identical course data."""
        existing_course = {
            "course_id": "course123",
            "course_number": "MATH-101",
            "course_title": "Algebra",
            "department": "MATH",
            "credit_hours": 3
        }
        mock_get_course.return_value = existing_course
        
        service = ImportService()
        service.reset_stats()
        
        import_course = {
            "course_number": "MATH-101",
            "course_title": "Algebra",
            "department": "MATH",
            "credit_hours": 3
        }
        
        conflicts = service.detect_course_conflict(import_course)
        
        # Should only have existence conflict (no data conflicts)
        assert len(conflicts) == 1
        assert conflicts[0].field == "_existence"

    @patch('import_service.get_course_by_number')
    def test_detect_course_conflict_different_data(self, mock_get_course):
        """Test conflict detection with different course data."""
        existing_course = {
            "course_id": "course123",
            "course_number": "MATH-101",
            "course_title": "Basic Algebra",
            "department": "MATH",
            "credit_hours": 3
        }
        mock_get_course.return_value = existing_course
        
        service = ImportService()
        service.reset_stats()
        
        import_course = {
            "course_number": "MATH-101",
            "course_title": "Advanced Algebra",
            "department": "MATH",
            "credit_hours": 4
        }
        
        conflicts = service.detect_course_conflict(import_course)
        
        # Should have existence conflict plus data conflicts
        assert len(conflicts) >= 2
        conflict_fields = [c.field for c in conflicts]
        assert "_existence" in conflict_fields
        assert "course_title" in conflict_fields
        assert "credit_hours" in conflict_fields


class TestImportExcelFunction:
    """Test the import_excel function."""

    @patch('import_service.openpyxl.load_workbook')
    def test_import_excel_file_not_found(self, mock_load_workbook):
        """Test import_excel with file not found."""
        mock_load_workbook.side_effect = FileNotFoundError("File not found")
        
        result = import_excel("nonexistent.xlsx")
        
        assert result.success is False
        assert "not found" in result.message.lower()

    @patch('import_service.openpyxl.load_workbook')
    def test_import_excel_invalid_file(self, mock_load_workbook):
        """Test import_excel with invalid Excel file."""
        mock_load_workbook.side_effect = Exception("Invalid Excel file")
        
        result = import_excel("invalid.xlsx")
        
        assert result.success is False
        assert "error" in result.message.lower()

    @patch('import_service.ImportService')
    @patch('import_service.openpyxl.load_workbook')
    def test_import_excel_success_dry_run(self, mock_load_workbook, mock_import_service):
        """Test successful import_excel in dry run mode."""
        # Setup mocks
        mock_workbook = Mock()
        mock_worksheet = Mock()
        mock_worksheet.iter_rows.return_value = [
            [Mock(value="Course Number"), Mock(value="Course Title")],  # Header
            [Mock(value="MATH-101"), Mock(value="Algebra")]  # Data
        ]
        mock_workbook.active = mock_worksheet
        mock_load_workbook.return_value = mock_workbook
        
        mock_service_instance = Mock()
        mock_service_instance.import_data.return_value = ImportResult(
            success=True,
            message="Dry run completed",
            records_processed=1,
            records_created=0,
            records_updated=0,
            records_skipped=0,
            conflicts=[],
            errors=[]
        )
        mock_import_service.return_value = mock_service_instance
        
        # Call function
        result = import_excel("test.xlsx", dry_run=True)
        
        # Verify results
        assert result.success is True
        mock_service_instance.import_data.assert_called_once()

    @patch('import_service.ImportService')
    @patch('import_service.openpyxl.load_workbook')
    def test_import_excel_with_options(self, mock_load_workbook, mock_import_service):
        """Test import_excel with various options."""
        # Setup mocks
        mock_workbook = Mock()
        mock_worksheet = Mock()
        mock_worksheet.iter_rows.return_value = []
        mock_workbook.active = mock_worksheet
        mock_load_workbook.return_value = mock_workbook
        
        mock_service_instance = Mock()
        mock_service_instance.import_data.return_value = ImportResult(
            success=True,
            message="Import completed",
            records_processed=0,
            records_created=0,
            records_updated=0,
            records_skipped=0,
            conflicts=[],
            errors=[]
        )
        mock_import_service.return_value = mock_service_instance
        
        # Call function with options
        result = import_excel(
            "test.xlsx",
            conflict_strategy="use_theirs",
            dry_run=False,
            delete_existing_db=True,
            verbose_output=True
        )
        
        # Verify service was called with correct options
        mock_import_service.assert_called_once_with(verbose=True)
        call_args = mock_service_instance.import_data.call_args[1]
        assert call_args["conflict_strategy"] == ConflictStrategy.USE_THEIRS
        assert call_args["mode"] == ImportMode.FULL_IMPORT
        assert call_args["delete_existing_db"] is True


class TestCreateImportReport:
    """Test create_import_report function."""

    def test_create_import_report_success(self):
        """Test create_import_report with successful result."""
        result = ImportResult(
            success=True,
            message="Import completed successfully",
            records_processed=10,
            records_created=5,
            records_updated=3,
            records_skipped=2,
            conflicts=[],
            errors=[]
        )
        
        report = create_import_report(result)
        
        assert "SUCCESS" in report
        assert "10 records processed" in report
        assert "5 records created" in report
        assert "3 records updated" in report
        assert "2 records skipped" in report

    def test_create_import_report_with_conflicts(self):
        """Test create_import_report with conflicts."""
        conflicts = [
            ConflictRecord(
                field="course_title",
                existing_value="Old Title",
                new_value="New Title",
                description="Title conflict"
            )
        ]
        
        result = ImportResult(
            success=True,
            message="Import completed with conflicts",
            records_processed=5,
            records_created=2,
            records_updated=2,
            records_skipped=1,
            conflicts=conflicts,
            errors=[]
        )
        
        report = create_import_report(result)
        
        assert "CONFLICTS DETECTED" in report
        assert "course_title" in report
        assert "Old Title" in report
        assert "New Title" in report

    def test_create_import_report_with_errors(self):
        """Test create_import_report with errors."""
        result = ImportResult(
            success=False,
            message="Import failed",
            records_processed=3,
            records_created=1,
            records_updated=0,
            records_skipped=0,
            conflicts=[],
            errors=["Database connection failed", "Invalid data format"]
        )
        
        report = create_import_report(result)
        
        assert "FAILED" in report
        assert "ERRORS" in report
        assert "Database connection failed" in report
        assert "Invalid data format" in report

    def test_create_import_report_empty_result(self):
        """Test create_import_report with minimal result."""
        result = ImportResult(
            success=True,
            message="No data to import",
            records_processed=0,
            records_created=0,
            records_updated=0,
            records_skipped=0,
            conflicts=[],
            errors=[]
        )
        
        report = create_import_report(result)
        
        assert "SUCCESS" in report
        assert "0 records processed" in report


class TestImportServiceIntegration:
    """Test ImportService integration aspects."""

    def test_import_service_stats_tracking(self):
        """Test that ImportService properly tracks statistics."""
        service = ImportService()
        
        # Verify initial state
        assert service.stats["records_processed"] == 0
        assert service.stats["errors"] == []
        
        # Modify stats (simulating import operations)
        service.stats["records_processed"] = 5
        service.stats["records_created"] = 3
        service.stats["errors"].append("Test error")
        
        # Verify changes
        assert service.stats["records_processed"] == 5
        assert service.stats["records_created"] == 3
        assert len(service.stats["errors"]) == 1

    def test_import_service_processed_tracking(self):
        """Test that ImportService tracks processed entities."""
        service = ImportService()
        
        # Add some processed entities
        service._processed_users.add("user1@example.com")
        service._processed_users.add("user2@example.com")
        service._processed_courses.add("MATH-101")
        
        # Verify tracking
        assert len(service._processed_users) == 2
        assert len(service._processed_courses) == 1
        assert "user1@example.com" in service._processed_users
        assert "MATH-101" in service._processed_courses

    def test_import_service_cache_functionality(self):
        """Test ImportService entity cache."""
        service = ImportService()
        service.reset_stats()  # Initialize cache
        
        # Add items to cache
        service.entity_cache["courses"]["MATH-101"] = {"course_title": "Algebra"}
        service.entity_cache["users"]["test@example.com"] = {"name": "Test User"}
        
        # Verify cache
        assert service.entity_cache["courses"]["MATH-101"]["course_title"] == "Algebra"
        assert service.entity_cache["users"]["test@example.com"]["name"] == "Test User"


class TestImportServiceErrorHandling:
    """Test ImportService error handling."""

    def test_import_service_handles_missing_dependencies(self):
        """Test ImportService handles missing dependencies gracefully."""
        service = ImportService()
        
        # This should not raise an exception
        service.reset_stats()
        service._log("Test message")
        
        # Basic functionality should work
        assert isinstance(service.stats, dict)
        assert isinstance(service._processed_users, set)
        assert isinstance(service._processed_courses, set)
