"""Unit tests for CEI Excel adapter."""

import pandas as pd
import pytest

from adapters.cei_excel_adapter import (
    _extract_department_from_course,
    _extract_name_from_email,
    _parse_name,
    parse_cei_excel_row,
    parse_cei_term,
    validate_cei_term_name,
)


class TestValidateCeiTermName:
    """Test CEI term validation function."""

    def test_validate_cei_term_standard_format(self):
        """Test validation with standard space-separated format."""
        assert validate_cei_term_name("2024 Fall") is True
        assert validate_cei_term_name("2025 Spring") is True
        assert validate_cei_term_name("2023 Summer") is True
        assert validate_cei_term_name("2026 Winter") is True

    def test_validate_cei_term_abbreviated_format(self):
        """Test validation with CEI abbreviated format."""
        assert validate_cei_term_name("FA2024") is True
        assert validate_cei_term_name("SP2025") is True
        assert validate_cei_term_name("SU2023") is True
        assert validate_cei_term_name("WI2026") is True

    def test_validate_cei_term_invalid_formats(self):
        """Test validation with invalid formats."""
        assert validate_cei_term_name("Fall 2024") is False  # Wrong order
        assert validate_cei_term_name("2024") is False  # Missing season
        assert validate_cei_term_name("Fall") is False  # Missing year
        assert validate_cei_term_name("XX2024") is False  # Invalid season
        assert validate_cei_term_name("FA24") is False  # Wrong year length
        assert validate_cei_term_name("2024FA") is False  # Wrong format (year first)
        assert validate_cei_term_name("") is False  # Empty string
        assert validate_cei_term_name("invalid") is False  # Completely invalid


class TestParseCeiTerm:
    """Test CEI term parsing function."""

    def test_parse_cei_term_valid_formats(self):
        """Test parse_cei_term with valid formats."""
        assert parse_cei_term("FA2024") == ("2024", "Fall")
        assert parse_cei_term("SP2025") == ("2025", "Spring")
        assert parse_cei_term("SU2023") == ("2023", "Summer")
        assert parse_cei_term("WI2026") == ("2026", "Winter")

    def test_parse_cei_term_invalid_length(self):
        """Test parse_cei_term with invalid length."""
        with pytest.raises(ValueError, match="Invalid effterm_c format"):
            parse_cei_term("FA24")
        with pytest.raises(ValueError, match="Invalid effterm_c format"):
            parse_cei_term("FALL2024")
        with pytest.raises(ValueError, match="Invalid effterm_c format"):
            parse_cei_term("")

    def test_parse_cei_term_invalid_season(self):
        """Test parse_cei_term with invalid season code."""
        with pytest.raises(ValueError, match="Invalid season code"):
            parse_cei_term("XX2024")


class TestHelperFunctions:
    """Test CEI adapter helper functions."""

    def test_extract_department_from_course(self):
        """Test department extraction from course numbers."""
        assert _extract_department_from_course("MATH-101") == "Mathematics"
        assert _extract_department_from_course("ENG-201") == "English"
        assert _extract_department_from_course("NURS-301") == "Nursing"
        assert _extract_department_from_course("UNKNOWN-999") == "UNKNOWN"
        assert _extract_department_from_course("INVALID") == "General Studies"

    def test_parse_name(self):
        """Test name parsing."""
        assert _parse_name("John Doe") == ("John", "Doe")
        assert _parse_name("Mary Jane Smith") == ("Mary", "Jane Smith")
        assert _parse_name("SingleName") == ("SingleName", "Name")
        assert _parse_name("") == ("Unknown", "Instructor")
        assert _parse_name("   ") == ("Unknown", "Instructor")

    def test_extract_name_from_email(self):
        """Test name extraction from email."""
        assert _extract_name_from_email("john.doe@cei.edu") == ("John", "Doe")
        assert _extract_name_from_email("mary.jane.smith@cei.edu") == (
            "Mary",
            "Jane.Smith",
        )
        assert _extract_name_from_email("singlename@cei.edu") == (
            "Unknown",
            "Singlename",
        )
        assert _extract_name_from_email("invalid-email") == ("Unknown", "Instructor")
        assert _extract_name_from_email("") == ("Unknown", "Instructor")


class TestParseCeiExcelRow:
    """Test CEI Excel row parsing."""

    def test_parse_cei_excel_row_complete_data(self):
        """Test parsing with complete row data."""
        row = pd.Series(
            {
                "course": "MATH-101",
                "Faculty Name": "John Smith",
                "effterm_c": "FA2024",
                "students": "25",
            }
        )

        result = parse_cei_excel_row(row, "test-institution")

        # Check course data
        assert result["course"] is not None
        assert result["course"]["course_number"] == "MATH-101"
        assert result["course"]["department"] == "Mathematics"
        assert result["course"]["institution_id"] == "test-institution"

        # Check user data - Faculty Name format should NOT generate fake emails
        assert result["user"] is not None
        assert result["user"]["email"] is None  # No fake email generation!
        assert result["user"]["first_name"] == "John"
        assert result["user"]["last_name"] == "Smith"
        assert (
            result["user"]["account_status"] == "needs_email"
        )  # Flagged for manual email entry

        # Check term data
        assert result["term"] is not None
        assert result["term"]["name"] == "Fall 2024"
        assert result["term"]["year"] == 2024
        assert result["term"]["season"] == "Fall"

    def test_parse_cei_excel_row_with_email_format(self):
        """Test parsing with email-based format (test data format)."""
        row = pd.Series(
            {
                "course": "MATH-101",
                "email": "matthew.taylor@cei.edu",
                "Term": "2024 Fall",
            }
        )

        result = parse_cei_excel_row(row, "test-institution")

        # Check course data
        assert result["course"] is not None
        assert result["course"]["course_number"] == "MATH-101"
        assert result["course"]["department"] == "Mathematics"
        assert result["course"]["institution_id"] == "test-institution"

        # Check user data - email format should preserve real email
        assert result["user"] is not None
        assert (
            result["user"]["email"] == "matthew.taylor@cei.edu"
        )  # Real email preserved!
        assert result["user"]["first_name"] == "Matthew"
        assert result["user"]["last_name"] == "Taylor"
        assert result["user"]["account_status"] == "imported"  # Normal import status

        # Check term data - standard format
        assert result["term"] is not None
        assert result["term"]["name"] == "2024 Fall"
        assert result["term"]["year"] == 2024
        assert result["term"]["season"] == "Fall"

    def test_parse_cei_excel_row_minimal_data(self):
        """Test parsing with minimal data."""
        row = pd.Series({"course": "ENG-101"})

        result = parse_cei_excel_row(row, "test-institution")

        # Should have course data only
        assert result["course"] is not None
        assert result["user"] is None
        assert result["term"] is None
        assert result["offering"] is None
        assert result["section"] is None

    def test_parse_cei_excel_row_exception_handling(self):
        """Test exception handling in row parsing."""
        row = pd.Series(
            {
                "course": None,  # This might cause issues
                "effterm_c": "invalid",  # Invalid term format
            }
        )

        result = parse_cei_excel_row(row, "test-institution")

        # Should handle errors gracefully
        assert result["course"] is None
        assert result["user"] is None
        assert result["term"] is None
        assert result["offering"] is None
        assert result["section"] is None


class TestCEIExcelAdapterErrorHandling:
    """Test error handling in CEI Excel Adapter."""

    def test_validate_file_general_exception(self):
        """Test validate_file_compatibility handles general exceptions."""
        from unittest.mock import patch

        from adapters.cei_excel_adapter import CEIExcelAdapter

        adapter = CEIExcelAdapter()

        # Mock _validate_basic_file_properties to raise exception
        with patch.object(
            adapter,
            "_validate_basic_file_properties",
            side_effect=RuntimeError("Unexpected error"),
        ):
            is_valid, error_msg = adapter.validate_file_compatibility("/fake/file.xlsx")

            assert is_valid is False
            assert "Error validating file" in error_msg
            assert "Unexpected error" in error_msg

    def test_validate_basic_file_properties_file_not_found(self):
        """Test file validation when file doesn't exist."""
        from adapters.cei_excel_adapter import CEIExcelAdapter

        adapter = CEIExcelAdapter()
        is_valid, error_msg = adapter._validate_basic_file_properties(
            "/nonexistent/file.xlsx"
        )

        assert is_valid is False
        assert "File not found" in error_msg

    def test_read_excel_sample_exception(self):
        """Test _read_excel_sample handles pandas exceptions."""
        import os
        import tempfile

        from adapters.cei_excel_adapter import CEIExcelAdapter

        adapter = CEIExcelAdapter()

        # Create invalid Excel file (just text)
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(b"not an excel file")
            tmp_path = tmp.name

        try:
            result = adapter._read_excel_sample(tmp_path)

            assert isinstance(result, tuple)
            assert result[0] is False
            assert "Cannot read Excel file" in result[1]
        finally:
            os.unlink(tmp_path)

    def test_validate_course_column_no_valid_courses(self):
        """Test _validate_course_column when no valid course numbers found."""
        import pandas as pd

        from adapters.cei_excel_adapter import CEIExcelAdapter

        adapter = CEIExcelAdapter()

        # DataFrame with invalid course numbers
        df = pd.DataFrame({"course": ["INVALID", "BADFORMAT", "WRONG"]})

        error = adapter._validate_course_column(df)

        assert error is not None
        assert "No valid course numbers found" in error

    def test_validate_term_column_no_valid_terms(self):
        """Test _validate_term_column when no valid term codes found."""
        import pandas as pd

        from adapters.cei_excel_adapter import CEIExcelAdapter

        adapter = CEIExcelAdapter()

        # DataFrame with invalid term codes
        df = pd.DataFrame({"effterm_c": ["INVALID", "BADTERM", "WRONG"]})

        error = adapter._validate_term_column(df)

        assert error is not None
        assert "No valid term codes found" in error

    def test_validate_student_count_column_invalid_data(self):
        """Test _validate_student_count_column with invalid data."""
        import pandas as pd

        from adapters.cei_excel_adapter import CEIExcelAdapter

        adapter = CEIExcelAdapter()

        # DataFrame with non-numeric student counts
        df = pd.DataFrame({"Enrolled Students": ["text", "invalid", "bad"]})

        error = adapter._validate_student_count_column(df)

        assert error is not None
        assert "invalid data" in error

    def test_validate_student_count_column_no_valid_numbers_string(self):
        """Test _validate_student_count_column with strings that look numeric but aren't."""
        import pandas as pd

        from adapters.cei_excel_adapter import CEIExcelAdapter

        adapter = CEIExcelAdapter()

        # DataFrame with values that are present but can't be converted to int
        df = pd.DataFrame({"Enrolled Students": ["", "  ", "-"]})

        error = adapter._validate_student_count_column(df)

        # This should hit line 628 (no valid numbers) or 630 (invalid data)
        assert error is not None

    def test_check_format_compatibility_hybrid(self):
        """Test _check_format_compatibility returns hybrid format."""
        import pandas as pd

        from adapters.cei_excel_adapter import CEIExcelAdapter

        adapter = CEIExcelAdapter()

        # Hybrid format needs course, email, Term + student col, but NOT all test format requirements
        # Test format = course, email, Term, students (all 4 exact)
        # Hybrid = course, email, Term + any student col variant
        # Use "Enrolled Students" to trigger hybrid instead of test
        df = pd.DataFrame(columns=["course", "email", "Term", "Enrolled Students"])

        is_compatible, format_type = adapter._check_format_compatibility(df)

        assert is_compatible is True
        assert format_type == "hybrid"

    def test_validate_data_patterns_term_error(self):
        """Test _validate_data_patterns returns term validation error."""
        import pandas as pd

        from adapters.cei_excel_adapter import CEIExcelAdapter

        adapter = CEIExcelAdapter()

        # Create DataFrame with invalid terms
        df = pd.DataFrame(
            {
                "course": ["MATH-101"],
                "effterm_c": ["BADTERM"],
                "Enrolled Students": [25],
            }
        )

        errors = adapter._validate_data_patterns(df, "original")

        # Should have term validation error (line 581, 588, 603)
        assert len(errors) > 0
        term_errors = [e for e in errors if "term" in e.lower()]
        assert len(term_errors) > 0

    def test_validate_student_count_column_no_column(self):
        """Test _validate_student_count_column when column doesn't exist."""
        import pandas as pd

        from adapters.cei_excel_adapter import CEIExcelAdapter

        adapter = CEIExcelAdapter()

        # DataFrame without student count column
        df = pd.DataFrame({"course": ["MATH-101"]})

        error = adapter._validate_student_count_column(df)

        # Should return None when no student column exists (line 622)
        assert error is None

    def test_validate_student_count_column_has_error(self):
        """Test _validate_student_count_column returns error for invalid data."""
        import pandas as pd

        from adapters.cei_excel_adapter import CEIExcelAdapter

        adapter = CEIExcelAdapter()

        # DataFrame with student column but all invalid values
        df = pd.DataFrame({"Enrolled Students": ["", "  ", "invalid"]})

        error = adapter._validate_student_count_column(df)

        # Should return error (line 628, 581)
        assert error is not None
        assert "student" in error.lower()

    def test_validate_course_column_no_column(self):
        """Test _validate_course_column returns None when column doesn't exist."""
        import pandas as pd

        from adapters.cei_excel_adapter import CEIExcelAdapter

        adapter = CEIExcelAdapter()

        # DataFrame without course column
        df = pd.DataFrame({"other": ["DATA"]})

        error = adapter._validate_course_column(df)

        # Should return None (line 588)
        assert error is None

    def test_validate_term_column_no_column(self):
        """Test _validate_term_column returns None when column doesn't exist."""
        import pandas as pd

        from adapters.cei_excel_adapter import CEIExcelAdapter

        adapter = CEIExcelAdapter()

        # DataFrame without effterm_c column
        df = pd.DataFrame({"other": ["DATA"]})

        error = adapter._validate_term_column(df)

        # Should return None (line 603)
        assert error is None
