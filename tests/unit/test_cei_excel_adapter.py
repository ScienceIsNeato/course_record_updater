"""Unit tests for CEI Excel adapter."""

import pandas as pd
import pytest

from adapters.cei_excel_adapter import (
    _extract_department_from_course,
    _generate_email,
    _parse_name,
    parse_cei_excel_row,
    parse_cei_term,
)


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

    def test_generate_email(self):
        """Test email generation."""
        assert _generate_email("John", "Doe") == "john.doe@cei.edu"
        assert _generate_email("Mary Jane", "Smith") == "maryjane.smith@cei.edu"
        assert _generate_email("Test", "User Name") == "test.username@cei.edu"


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

        # Check user data
        assert result["user"] is not None
        assert result["user"]["email"] == "john.smith@cei.edu"
        assert result["user"]["first_name"] == "John"
        assert result["user"]["last_name"] == "Smith"

        # Check term data
        assert result["term"] is not None
        assert result["term"]["name"] == "Fall 2024"
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
