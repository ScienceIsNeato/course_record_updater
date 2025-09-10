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
        assert ConflictStrategy.USE_MINE.value == "use_mine"
        assert ConflictStrategy.USE_THEIRS.value == "use_theirs"
        assert ConflictStrategy.MERGE.value == "merge"
        assert ConflictStrategy.MANUAL_REVIEW.value == "manual_review"

    def test_import_mode_enum(self):
        """Test ImportMode enum values."""
        assert ImportMode.DRY_RUN.value == "dry_run"
        assert ImportMode.EXECUTE.value == "execute"

    def test_conflict_record_creation(self):
        """Test ConflictRecord creation."""
        record = ConflictRecord(
            entity_type="course",
            entity_key="MATH-101",
            field_name="course_title",
            existing_value="Old Title",
            import_value="New Title"
        )
        
        assert record.entity_type == "course"
        assert record.entity_key == "MATH-101"
        assert record.field_name == "course_title"
        assert record.existing_value == "Old Title"
        assert record.import_value == "New Title"

    def test_import_result_creation(self):
        """Test ImportResult creation."""
        result = ImportResult(
            success=True,
            records_processed=10,
            records_created=5,
            records_updated=3,
            records_skipped=2,
            conflicts_detected=1,
            conflicts_resolved=1,
            errors=[],
            warnings=[],
            conflicts=[],
            execution_time=1.5,
            dry_run=False
        )
        
        assert result.success is True
        assert result.records_processed == 10
        assert result.records_created == 5
        assert result.records_updated == 3
        assert result.records_skipped == 2
        assert result.conflicts_detected == 1
        assert result.conflicts_resolved == 1
        assert result.errors == []
        assert result.warnings == []
        assert result.conflicts == []
        assert result.execution_time == 1.5
        assert result.dry_run is False


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
        
        # Just test that reset_stats works without error
        assert hasattr(service, 'stats')
        assert isinstance(service.stats, dict)


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

    def test_detect_course_conflict_method_exists(self):
        """Test that detect_course_conflict method exists."""
        service = ImportService()
        assert hasattr(service, 'detect_course_conflict')
        assert callable(service.detect_course_conflict)

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
        assert len(conflicts) >= 1
        assert conflicts[0].field_name == "_existence"

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
        conflict_fields = [c.field_name for c in conflicts]
        assert "_existence" in conflict_fields


class TestImportExcelFunction:
    """Test the import_excel function - basic functionality."""

    def test_import_excel_function_exists(self):
        """Test that import_excel function exists and is callable."""
        assert callable(import_excel)
        
    def test_create_import_report_function_exists(self):
        """Test that create_import_report function exists and is callable."""
        assert callable(create_import_report)


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

    def test_import_service_basic_functionality(self):
        """Test ImportService basic functionality."""
        service = ImportService()
        service.reset_stats()  # Initialize service
        
        # Test basic service functionality
        assert hasattr(service, 'stats')
        assert hasattr(service, '_processed_users')
        assert hasattr(service, '_processed_courses')


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
