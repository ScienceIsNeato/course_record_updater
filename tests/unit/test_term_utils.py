"""
Tests for term_utils module - dynamic term generation.
"""

from datetime import datetime
from unittest.mock import patch

from src.utils.term_utils import (
    TERM_STATUS_ACTIVE,
    TERM_STATUS_PASSED,
    TERM_STATUS_SCHEDULED,
    TermGenerator,
    default_term_generator,
    get_allowed_terms,
    get_current_term,
    get_term_status,
    is_term_active,
    is_valid_term,
)

# pytest import removed


class TestTermGenerator:
    """Test the TermGenerator class functionality."""

    def test_default_initialization(self):
        """Test default TermGenerator initialization."""
        generator = TermGenerator()
        assert generator.base_year == datetime.now().year
        assert generator.years_forward == 2
        assert generator.years_back == 1

    def test_custom_initialization(self):
        """Test TermGenerator with custom parameters."""
        generator = TermGenerator(base_year=2024, years_forward=1, years_back=0)
        assert generator.base_year == 2024
        assert generator.years_forward == 1
        assert generator.years_back == 0

    def test_get_valid_terms_structure(self):
        """Test that valid terms are generated correctly."""
        generator = TermGenerator(base_year=2024, years_forward=1, years_back=1)
        terms = generator.get_valid_terms()

        # Should have terms for 2023, 2024, 2025 (3 years * 3 terms = 9 terms)
        assert len(terms) == 9

        # Check some expected terms exist
        assert "FA2023" in terms
        assert "SP2024" in terms
        assert "SU2024" in terms
        assert "FA2024" in terms
        assert "SP2025" in terms

        # Check terms are sorted
        assert terms == sorted(terms)

    def test_is_valid_term(self):
        """Test term validation."""
        generator = TermGenerator(base_year=2024, years_forward=1, years_back=1)

        # Valid terms
        assert generator.is_valid_term("FA2024")
        assert generator.is_valid_term("SP2025")
        assert generator.is_valid_term("SU2023")

        # Invalid terms
        assert not generator.is_valid_term("FA2022")  # Too far back
        assert not generator.is_valid_term("SP2027")  # Too far forward
        assert not generator.is_valid_term("INVALID")  # Bad format
        assert not generator.is_valid_term("")  # Empty string

    def test_get_current_term(self):
        """Test current term detection."""
        generator = TermGenerator()
        current = generator.get_current_term()

        # Should be a valid term format
        assert len(current) == 6
        assert current[:2] in ["FA", "SP", "SU"]
        assert current[2:].isdigit()

        # Should be a valid term according to the generator
        assert generator.is_valid_term(current)

    def test_get_term_display_name(self):
        """Test human-readable term names."""
        generator = TermGenerator()

        assert generator.get_term_display_name("FA2024") == "Fall 2024"
        assert generator.get_term_display_name("SP2025") == "Spring 2025"
        assert generator.get_term_display_name("SU2023") == "Summer 2023"

        # Handle malformed input gracefully
        assert (
            generator.get_term_display_name("INVALID") == "IN VALID"
        )  # Expected behavior: splits at position 2
        assert generator.get_term_display_name("FA") == "FA"


class TestModuleFunctions:
    """Test the module-level convenience functions."""

    def test_get_allowed_terms(self):
        """Test get_allowed_terms function."""
        terms = get_allowed_terms()
        assert isinstance(terms, list)
        assert len(terms) > 0

        # Should include current year terms
        current_year = datetime.now().year
        assert f"FA{current_year}" in terms
        assert f"SP{current_year}" in terms
        assert f"SU{current_year}" in terms

    def test_is_valid_term_function(self):
        """Test is_valid_term function."""
        # Should work with current year terms
        current_year = datetime.now().year
        assert is_valid_term(f"FA{current_year}")
        assert is_valid_term(f"SP{current_year}")
        assert is_valid_term(f"SU{current_year}")

        # Invalid terms
        assert not is_valid_term("INVALID")
        assert not is_valid_term("")

    def test_get_current_term_function(self):
        """Test get_current_term function."""
        current = get_current_term()
        assert isinstance(current, str)
        assert len(current) == 6
        assert is_valid_term(current)  # Should be valid according to our validator

    def test_default_term_generator_exists(self):
        """Test that default_term_generator is properly initialized."""
        assert default_term_generator is not None
        assert isinstance(default_term_generator, TermGenerator)

        # Should work the same as module functions
        assert default_term_generator.get_valid_terms() == get_allowed_terms()
        assert default_term_generator.get_current_term() == get_current_term()


class TestBackwardCompatibility:
    """Test backward compatibility with old ALLOWED_TERMS approach."""

    def test_replaces_hardcoded_terms(self):
        """Test that dynamic terms include typical hardcoded values."""
        terms = get_allowed_terms()

        # Should include reasonable current/future terms
        current_year = datetime.now().year
        expected_terms = [
            f"FA{current_year}",
            f"SP{current_year + 1}",
            f"SU{current_year + 1}",
        ]

        for term in expected_terms:
            assert term in terms, f"Expected term {term} not found in {terms}"

    def test_validation_works_like_lambda(self):
        """Test that is_valid_term works like the old lambda: t in ALLOWED_TERMS."""
        # Get current allowed terms
        allowed = get_allowed_terms()

        # Test that validation matches membership check
        for term in allowed[:5]:  # Test first 5 terms
            assert is_valid_term(term), f"Term {term} should be valid"

        # Test invalid terms
        invalid_terms = ["INVALID", "", "XX2099", "FA1999"]
        for term in invalid_terms:
            if term not in allowed:  # Only test if actually not in allowed
                assert not is_valid_term(term), f"Term {term} should be invalid"


class TestTermGeneratorExtended:
    """Extended tests for TermGenerator class."""

    def test_term_generator_get_current_term_logic(self):
        """Test get_current_term logic with mocked datetime."""
        generator = TermGenerator()

        # Mock datetime to test different months
        with patch("src.utils.term_utils.datetime") as mock_datetime:
            # Test fall semester (September)
            mock_datetime.now.return_value = datetime(2024, 9, 15)
            current_term = generator.get_current_term()
            assert current_term is not None

            # Test spring semester (February)
            mock_datetime.now.return_value = datetime(2024, 2, 15)
            current_term = generator.get_current_term()
            assert current_term is not None

    def test_term_generator_is_valid_term_edge_cases(self):
        """Test is_valid_term with various edge cases."""
        generator = TermGenerator()

        # Test with None
        assert generator.is_valid_term(None) is False


class TestTermStatusHelpers:
    """Tests for get_term_status/is_term_active helpers."""

    def test_status_active(self):
        with patch("src.utils.term_utils.get_current_time") as mock_now:
            mock_now.return_value = datetime(2024, 1, 15)
            assert get_term_status("2024-01-01", "2024-02-01") == TERM_STATUS_ACTIVE
            assert is_term_active("2024-01-01", "2024-02-01") is True

    def test_status_scheduled(self):
        with patch("src.utils.term_utils.get_current_time") as mock_now:
            mock_now.return_value = datetime(2024, 1, 15)
            assert get_term_status("2024-02-01", "2024-05-01") == TERM_STATUS_SCHEDULED
            assert is_term_active("2024-02-01", "2024-05-01") is False

    def test_status_passed(self):
        with patch("src.utils.term_utils.get_current_time") as mock_now:
            mock_now.return_value = datetime(2024, 6, 1)
            assert get_term_status("2024-01-01", "2024-05-01") == TERM_STATUS_PASSED
            assert is_term_active("2024-01-01", "2024-05-01") is False

    def test_status_unknown_when_missing_dates(self):
        assert get_term_status(None, None) == "UNKNOWN"

        # Test with empty string
        generator = TermGenerator()
        assert generator.is_valid_term("") is False

        # Test with whitespace
        assert generator.is_valid_term("   ") is False

    def test_term_generator_get_term_display_name_invalid_input(self):
        """Test get_term_display_name with invalid input."""
        generator = TermGenerator()

        # Test with invalid inputs that won't crash
        invalid_inputs = ["", "X", "TOOLONG", "123"]

        for invalid_input in invalid_inputs:
            result = generator.get_term_display_name(invalid_input)
            # Should handle gracefully, either return original or some default
            assert result is not None


class TestModuleLevelFunctionsExtended:
    """Extended tests for module-level functions."""

    def test_get_allowed_terms_returns_list(self):
        """Test that get_allowed_terms returns a list."""
        terms = get_allowed_terms()
        assert isinstance(terms, list)
        assert len(terms) > 0

    def test_is_valid_term_function_with_various_inputs(self):
        """Test is_valid_term function with various inputs."""
        # Test with valid term
        valid_terms = get_allowed_terms()
        if valid_terms:
            first_term = valid_terms[0]
            assert is_valid_term(first_term) is True

        # Test with invalid inputs
        assert is_valid_term("INVALID") is False
        assert is_valid_term("") is False
        assert is_valid_term(None) is False

    def test_get_current_term_function_returns_string(self):
        """Test that get_current_term returns a string."""
        current_term = get_current_term()
        assert isinstance(current_term, str)
        assert len(current_term) > 0


class TestBackwardCompatibilityExtended:
    """Extended backward compatibility tests."""

    def test_validation_consistency(self):
        """Test that validation is consistent across different interfaces."""
        # Get a valid term
        valid_terms = get_allowed_terms()
        if valid_terms:
            test_term = valid_terms[0]

            # Test through different interfaces
            assert is_valid_term(test_term) is True

    def test_term_generation_parameters(self):
        """Test that term generation parameters are reasonable."""
        generator = TermGenerator()

        # Check that default parameters make sense - just test the generator works
        valid_terms = generator.get_valid_terms()
        assert isinstance(valid_terms, list)
        assert len(valid_terms) > 0

        # Check that all terms are strings
        assert all(isinstance(term, str) for term in valid_terms)
        assert all(len(term) > 0 for term in valid_terms)

    def test_term_generator_edge_cases(self):
        """Test TermGenerator edge cases."""
        generator = TermGenerator()

        # Test that methods don't crash
        assert callable(generator.is_valid_term)
        assert callable(generator.get_current_term)
        assert callable(generator.get_term_display_name)

        # Test basic functionality
        terms = generator.get_valid_terms()
        assert len(terms) > 0

        if terms:
            # Test with first valid term
            first_term = terms[0]
            assert generator.is_valid_term(first_term) is True

            # Test display name
            display = generator.get_term_display_name(first_term)
            assert isinstance(display, str)
            assert len(display) > 0


class TestTermGeneratorCustomization:
    """Test TermGenerator customization and configuration options."""

    def test_term_generator_custom_parameters(self):
        """Test TermGenerator with custom parameters."""
        generator = TermGenerator(base_year=2023, years_forward=3, years_back=2)
        assert generator.base_year == 2023
        assert generator.years_forward == 3
        assert generator.years_back == 2

        terms = generator.get_valid_terms()
        # Should generate terms from 2021 to 2026
        assert "FA2021" in terms
        assert "SP2026" in terms
        assert len(terms) >= 18  # 6 years * 3 terms per year

    def test_get_current_term_month_logic(self):
        """Test current term logic for different months."""
        generator = TermGenerator()

        # Mock different months to test logic
        from unittest.mock import Mock, patch

        with patch("src.utils.term_utils.datetime") as mock_datetime:
            # Test Spring term (January-May)
            mock_datetime.now.return_value = Mock(year=2024, month=3)
            assert generator.get_current_term() == "SP2024"

            # Test Summer term (June-August)
            mock_datetime.now.return_value = Mock(year=2024, month=7)
            assert generator.get_current_term() == "SU2024"

            # Test Fall term (September-December)
            mock_datetime.now.return_value = Mock(year=2024, month=10)
            assert generator.get_current_term() == "FA2024"

    def test_get_term_display_name_edge_cases(self):
        """Test term display name with edge cases."""
        generator = TermGenerator()

        # Test valid cases
        assert generator.get_term_display_name("FA2024") == "Fall 2024"
        assert generator.get_term_display_name("SP2025") == "Spring 2025"
        assert generator.get_term_display_name("SU2023") == "Summer 2023"

        # Test invalid/edge cases
        assert generator.get_term_display_name("FA24") == "FA24"  # Too short
        # The function may modify unknown codes, so test actual behavior
        invalid_result = generator.get_term_display_name("INVALID")
        assert isinstance(invalid_result, str)
        assert generator.get_term_display_name("") == ""

    def test_is_valid_term_edge_cases(self):
        """Test term validation with edge cases."""
        generator = TermGenerator(base_year=2024, years_forward=1, years_back=1)

        # Test boundary years
        assert generator.is_valid_term("FA2023") is True  # Back boundary
        assert generator.is_valid_term("SU2025") is True  # Forward boundary
        assert generator.is_valid_term("FA2022") is False  # Before back boundary
        assert generator.is_valid_term("SP2026") is False  # After forward boundary

        # Test invalid formats
        assert generator.is_valid_term("") is False
        assert generator.is_valid_term("INVALID") is False
        assert generator.is_valid_term("FA24") is False

    def test_get_default_terms_class_method(self):
        """Test get_default_terms class method."""
        terms = TermGenerator.get_default_terms()

        assert isinstance(terms, list)
        assert len(terms) > 0

        # Should be sorted
        assert terms == sorted(terms)

        # Should contain current year
        current_year = datetime.now().year
        current_year_terms = [term for term in terms if str(current_year) in term]
        assert len(current_year_terms) >= 3  # At least FA, SP, SU

    def test_backward_compatibility_comprehensive(self):
        """Test backward compatibility functions comprehensively."""
        # Test get_allowed_terms
        allowed_terms = get_allowed_terms()
        assert isinstance(allowed_terms, list)
        assert len(allowed_terms) > 0

        # Test is_valid_term function
        if allowed_terms:
            first_term = allowed_terms[0]
            assert is_valid_term(first_term) is True
            assert is_valid_term("INVALID_TERM") is False

        # Test get_current_term function
        current_term = get_current_term()
        assert isinstance(current_term, str)
        assert len(current_term) >= 6
        assert current_term in allowed_terms

    def test_term_generator_zero_range(self):
        """Test TermGenerator with zero forward/back range."""
        generator = TermGenerator(base_year=2024, years_forward=0, years_back=0)
        terms = generator.get_valid_terms()

        # Should only contain 2024 terms
        expected_2024_terms = ["FA2024", "SP2024", "SU2024"]
        for term in expected_2024_terms:
            assert term in terms

        # Should not contain other years
        assert all("2024" in term for term in terms)
        assert len(terms) == 3
