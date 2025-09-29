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
