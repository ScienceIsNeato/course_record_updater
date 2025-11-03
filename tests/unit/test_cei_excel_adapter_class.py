"""
Unit tests for CEI Excel Adapter class implementation
"""

import tempfile
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import pytest

from adapters.cei_excel_adapter import CEIExcelAdapter
from adapters.file_base_adapter import FileCompatibilityError


class TestCEIExcelAdapterClass:
    """Test suite for CEI Excel Adapter class"""

    def setup_method(self):
        """Set up test environment"""
        self.adapter = CEIExcelAdapter()

    def create_test_excel_file(
        self, data: Dict[str, Any], suffix: str = ".xlsx"
    ) -> str:
        """Helper to create test Excel files"""
        df = pd.DataFrame(data)
        temp_file = tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, delete=False)
        df.to_excel(temp_file.name, index=False)
        temp_file.close()
        return temp_file.name

    def test_adapter_info(self):
        """Test adapter metadata"""
        info = self.adapter.get_adapter_info()

        assert info["id"] == "cei_excel_format_v1"
        assert info["name"] == "CEI Excel Format v1.2"
        # Adapter should be tied to CEI institution by short_name (GUID-free)
        assert info["institution_short_name"] == "CEI"
        assert ".xlsx" in info["supported_formats"]
        assert ".xls" in info["supported_formats"]
        assert "courses" in info["data_types"]
        assert "faculty" in info["data_types"]
        assert "terms" in info["data_types"]
        assert "sections" in info["data_types"]
        assert info["version"] == "1.2.0"

    def test_file_size_and_record_limits(self):
        """Test custom limits for CEI adapter"""
        assert self.adapter.get_file_size_limit() == 500 * 1024 * 1024  # 500MB
        assert self.adapter.get_max_records() == 500000

    def test_validate_file_compatibility_original_format(self):
        """Test compatibility validation with original CEI format"""
        # Create test file with original format columns
        data = {
            "course": ["MATH-101", "ENG-201"],
            "Faculty Name": ["John Smith", "Jane Doe"],
            "effterm_c": ["2024FA", "2025SP"],
            "students": [25, 30],
        }

        test_file = self.create_test_excel_file(data)

        try:
            is_compatible, message = self.adapter.validate_file_compatibility(test_file)

            assert is_compatible is True
            assert "compatible with CEI Excel format (original)" in message
            assert "Found 2 sample records" in message

        finally:
            Path(test_file).unlink()

    def test_validate_file_compatibility_test_format(self):
        """Test compatibility validation with test CEI format"""
        # Create test file with test format columns
        data = {
            "course": ["MATH-101", "ENG-201"],
            "email": ["prof.smith@cei.test", "jane.doe@cei.test"],
            "Term": ["2024 Fall", "2025 Spring"],
            "students": [25, 30],
        }

        test_file = self.create_test_excel_file(data)

        try:
            is_compatible, message = self.adapter.validate_file_compatibility(test_file)

            assert is_compatible is True
            assert "compatible with CEI Excel format (test)" in message
            assert "Found 2 sample records" in message

        finally:
            Path(test_file).unlink()

    def test_validate_file_compatibility_invalid_format(self):
        """Test compatibility validation with invalid format"""
        # Create test file missing required columns
        data = {
            "wrong_column": ["value1", "value2"],
            "another_wrong": ["value3", "value4"],
        }

        test_file = self.create_test_excel_file(data)

        try:
            is_compatible, message = self.adapter.validate_file_compatibility(test_file)

            assert is_compatible is False
            assert "doesn't match CEI format" in message
            assert "Missing for original format" in message
            assert "Missing for test format" in message

        finally:
            Path(test_file).unlink()

    def test_validate_file_compatibility_invalid_course_numbers(self):
        """Test compatibility validation with invalid course numbers"""
        # Create test file with invalid course numbers
        data = {
            "course": ["invalid", "also-invalid"],
            "Faculty Name": ["John Smith", "Jane Doe"],
            "effterm_c": ["2024FA", "2025SP"],
            "students": [25, 30],
        }

        test_file = self.create_test_excel_file(data)

        try:
            is_compatible, message = self.adapter.validate_file_compatibility(test_file)

            assert is_compatible is False
            assert "No valid course numbers found" in message

        finally:
            Path(test_file).unlink()

    def test_validate_file_compatibility_invalid_term_codes(self):
        """Test compatibility validation with invalid term codes"""
        # Create test file with invalid term codes
        data = {
            "course": ["MATH-101", "ENG-201"],
            "Faculty Name": ["John Smith", "Jane Doe"],
            "effterm_c": ["INVALID", "BADTERM"],
            "students": [25, 30],
        }

        test_file = self.create_test_excel_file(data)

        try:
            is_compatible, message = self.adapter.validate_file_compatibility(test_file)

            assert is_compatible is False
            assert "No valid term codes found" in message
            assert "expected format: 2024FA, 2025SP" in message

        finally:
            Path(test_file).unlink()

    def test_validate_file_compatibility_non_excel_file(self):
        """Test compatibility validation with non-Excel file"""
        # Create a text file instead of Excel
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        temp_file.write("This is not an Excel file")
        temp_file.close()

        try:
            is_compatible, message = self.adapter.validate_file_compatibility(
                temp_file.name
            )

            assert is_compatible is False
            assert "Unsupported file extension" in message

        finally:
            Path(temp_file.name).unlink()

    def test_validate_file_compatibility_empty_file(self):
        """Test compatibility validation with empty Excel file"""
        # Create empty Excel file
        data = {}
        test_file = self.create_test_excel_file(data)

        try:
            is_compatible, message = self.adapter.validate_file_compatibility(test_file)

            assert is_compatible is False
            assert "Excel file is empty" in message

        finally:
            Path(test_file).unlink()

    def test_detect_data_types_original_format(self):
        """Test data type detection with original format"""
        # Create test file with original format
        data = {
            "course": ["MATH-101", "ENG-201"],
            "Faculty Name": ["John Smith", "Jane Doe"],
            "effterm_c": ["2024FA", "2025SP"],
            "students": [25, 30],
        }

        test_file = self.create_test_excel_file(data)

        try:
            detected_types = self.adapter.detect_data_types(test_file)

            assert "courses" in detected_types
            assert "faculty" in detected_types
            assert "terms" in detected_types
            assert "sections" in detected_types

        finally:
            Path(test_file).unlink()

    def test_detect_data_types_test_format(self):
        """Test data type detection with test format"""
        # Create test file with test format
        data = {
            "course": ["MATH-101", "ENG-201"],
            "email": ["prof.smith@cei.test", "jane.doe@cei.test"],
            "Term": ["2024 Fall", "2025 Spring"],
            "students": [25, 30],
        }

        test_file = self.create_test_excel_file(data)

        try:
            detected_types = self.adapter.detect_data_types(test_file)

            assert "courses" in detected_types
            assert "faculty" in detected_types
            assert "terms" in detected_types
            assert "sections" in detected_types

        finally:
            Path(test_file).unlink()

    def test_detect_data_types_partial_data(self):
        """Test data type detection with partial data"""
        # Create test file with only course data
        data = {"course": ["MATH-101", "ENG-201"], "other_column": ["value1", "value2"]}

        test_file = self.create_test_excel_file(data)

        try:
            detected_types = self.adapter.detect_data_types(test_file)

            assert "courses" in detected_types
            assert "faculty" not in detected_types
            assert "terms" not in detected_types
            assert "sections" not in detected_types

        finally:
            Path(test_file).unlink()

    def test_detect_data_types_unreadable_file(self):
        """Test data type detection with unreadable file"""
        # Test with non-existent file
        detected_types = self.adapter.detect_data_types("/nonexistent/file.xlsx")

        assert detected_types == []

    def test_parse_file_original_format(self):
        """Test file parsing with original format"""
        # Create test file with original format
        data = {
            "course": ["MATH-101", "ENG-201"],
            "Faculty Name": ["John Smith", "Jane Doe"],
            "effterm_c": ["2024FA", "2025SP"],
            "students": [25, 30],
        }

        test_file = self.create_test_excel_file(data)

        try:
            options = {"institution_id": "test_institution"}
            result = self.adapter.parse_file(test_file, options)

            # Check structure
            assert "courses" in result
            assert "users" in result
            assert "terms" in result
            assert "offerings" in result
            assert "sections" in result

            # Check data content
            assert len(result["courses"]) > 0
            assert len(result["users"]) > 0
            assert len(result["terms"]) > 0

            # Check data quality
            first_course = result["courses"][0]
            assert first_course["course_number"] == "MATH-101"
            assert first_course["institution_id"] == "test_institution"
            assert "created_at" in first_course

            first_user = result["users"][0]
            assert first_user["first_name"] == "John"
            assert first_user["last_name"] == "Smith"
            assert first_user["institution_id"] == "test_institution"
            assert (
                first_user["account_status"] == "needs_email"
            )  # No email in original format

        finally:
            Path(test_file).unlink()

    def test_parse_file_test_format(self):
        """Test file parsing with test format"""
        # Create test file with test format
        data = {
            "course": ["MATH-101", "ENG-201"],
            "email": ["prof.smith@cei.test", "jane.doe@cei.test"],
            "Term": ["2024 Fall", "2025 Spring"],
            "students": [25, 30],
        }

        test_file = self.create_test_excel_file(data)

        try:
            options = {"institution_id": "test_institution"}
            result = self.adapter.parse_file(test_file, options)

            # Check that users have emails in test format
            assert len(result["users"]) > 0
            first_user = result["users"][0]
            assert first_user["email"] == "prof.smith@cei.test"
            assert first_user["account_status"] == "imported"  # Has email

        finally:
            Path(test_file).unlink()

    def test_parse_file_missing_institution_id(self):
        """Test file parsing without institution_id in options"""
        data = {
            "course": ["MATH-101"],
            "Faculty Name": ["John Smith"],
            "effterm_c": ["2024FA"],
            "students": [25],
        }

        test_file = self.create_test_excel_file(data)

        try:
            options = {}  # Missing institution_id

            with pytest.raises(ValueError) as exc_info:
                self.adapter.parse_file(test_file, options)

            assert "institution_id is required" in str(exc_info.value)

        finally:
            Path(test_file).unlink()

    def test_parse_file_incompatible_file(self):
        """Test file parsing with incompatible file"""
        # Create incompatible file
        data = {"wrong_column": ["value1"], "another_wrong": ["value2"]}

        test_file = self.create_test_excel_file(data)

        try:
            options = {"institution_id": "test_institution"}

            with pytest.raises(FileCompatibilityError) as exc_info:
                self.adapter.parse_file(test_file, options)

            assert "File incompatible" in str(exc_info.value)

        finally:
            Path(test_file).unlink()

    def test_parse_file_no_valid_records(self):
        """Test file parsing with no valid records"""
        # Create file with correct structure but all empty/invalid data
        # This should pass the basic structure validation but produce no valid records
        data = {
            "course": ["", "", ""],
            "Faculty Name": ["", "", ""],
            "effterm_c": ["", "", ""],
            "students": ["", "", ""],
        }

        test_file = self.create_test_excel_file(data)

        try:
            options = {"institution_id": "test_institution"}

            with pytest.raises(FileCompatibilityError) as exc_info:
                self.adapter.parse_file(test_file, options)

            # The empty file is caught during validation, not parsing
            assert "Excel file is empty" in str(exc_info.value)

        finally:
            Path(test_file).unlink()

    def test_deduplicate_results(self):
        """Test result deduplication"""
        # Create test data with duplicates
        result = {
            "courses": [
                {
                    "course_number": "MATH-101",
                    "institution_id": "test",
                    "title": "Course 1",
                },
                {
                    "course_number": "MATH-101",
                    "institution_id": "test",
                    "title": "Course 1 Duplicate",
                },
                {
                    "course_number": "ENG-201",
                    "institution_id": "test",
                    "title": "Course 2",
                },
            ],
            "users": [
                {
                    "email": "test@example.com",
                    "first_name": "John",
                    "last_name": "Smith",
                    "institution_id": "test",
                },
                {
                    "email": "test@example.com",
                    "first_name": "John",
                    "last_name": "Smith",
                    "institution_id": "test",
                },
                {
                    "email": "jane@example.com",
                    "first_name": "Jane",
                    "last_name": "Doe",
                    "institution_id": "test",
                },
            ],
        }

        deduplicated = self.adapter._deduplicate_results(result)

        # Should have removed duplicates
        assert len(deduplicated["courses"]) == 2
        assert len(deduplicated["users"]) == 2

        # Check that the right records were kept
        course_numbers = [c["course_number"] for c in deduplicated["courses"]]
        assert "MATH-101" in course_numbers
        assert "ENG-201" in course_numbers

        emails = [u["email"] for u in deduplicated["users"]]
        assert "test@example.com" in emails
        assert "jane@example.com" in emails

    def test_export_data_success(self):
        """Test successful export of data to CEI Excel format."""
        import tempfile

        # Sample data to export
        data = {
            "courses": [{"course_number": "MATH-101", "title": "Calculus I"}],
            "users": [
                {
                    "user_id": "1",
                    "first_name": "John",
                    "last_name": "Smith",
                    "email": "john@example.com",
                    "role": "instructor",
                }
            ],
            "terms": [
                {"term_id": "1", "year": 2024, "season": "Fall", "name": "Fall 2024"}
            ],
            "offerings": [
                {
                    "course_number": "MATH-101",
                    "term_id": "1",
                    "instructor_id": "1",
                    "section_number": "01",
                    "enrollment_count": 25,
                }
            ],
        }

        options = {"institution_id": "test_institution"}

        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
            success, message, records_exported = self.adapter.export_data(
                data, tmp.name, options
            )

            assert success is True
            assert "Successfully exported" in message
            assert records_exported == 1

    def test_export_data_no_records(self):
        """Test export with no records to export."""
        import tempfile

        data = {"courses": [], "users": [], "terms": [], "offerings": []}

        options = {"institution_id": "test_institution"}

        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
            success, message, records_exported = self.adapter.export_data(
                data, tmp.name, options
            )

            assert success is False
            assert "No valid records to export" in message
            assert records_exported == 0

    def test_export_data_error(self):
        """Test export data with invalid output path."""
        # First create valid data that will generate records
        data = {
            "courses": [{"course_number": "MATH-101"}],
            "users": [
                {
                    "user_id": "1",
                    "first_name": "John",
                    "last_name": "Smith",
                    "role": "instructor",
                }
            ],
            "terms": [{"term_id": "1", "year": 2024, "season": "Fall"}],
            "offerings": [
                {"course_number": "MATH-101", "term_id": "1", "instructor_id": "1"}
            ],
        }

        options = {"institution_id": "test_institution"}

        # Use an invalid path that should cause an error
        success, message, records_exported = self.adapter.export_data(
            data, "/invalid/path/file.xlsx", options
        )

        assert success is False
        assert "Export failed:" in message
        assert records_exported == 0

    def test_format_term_for_cei_export(self):
        """Test term formatting for CEI export format (YEAR+SEASON)."""
        # Test with year and season
        term = {"year": 2024, "season": "Fall"}
        result = self.adapter._format_term_for_cei_export(term)
        assert result == "2024FA"

        # Test with different seasons
        seasons = {"Spring": "2024SP", "Summer": "2024SU", "Winter": "2024WI"}

        for season, expected in seasons.items():
            term = {"year": 2024, "season": season}
            result = self.adapter._format_term_for_cei_export(term)
            assert result == expected

        # Test with unknown season
        term = {"year": 2024, "season": "Unknown"}
        result = self.adapter._format_term_for_cei_export(term)
        assert result == "2024UN"

        # Test with fallback to name
        term = {"name": "Fall 2024"}
        result = self.adapter._format_term_for_cei_export(term)
        assert result == "2024FA"

        # Test with empty term
        result = self.adapter._format_term_for_cei_export({})
        assert result == ""

        # Test with None term
        result = self.adapter._format_term_for_cei_export(None)
        assert result == ""

    def test_supports_export(self):
        """Test that adapter supports export."""
        assert self.adapter.supports_export() is True

    def test_get_export_formats(self):
        """Test getting export formats."""
        formats = self.adapter.get_export_formats()
        assert ".xlsx" in formats
