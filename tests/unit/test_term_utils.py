"""
Tests for term_utils module - dynamic term generation.
"""
import pytest
from datetime import datetime

from term_utils import (
    TermGenerator, 
    get_allowed_terms, 
    is_valid_term, 
    get_current_term,
    default_term_generator
)


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
        assert not generator.is_valid_term("INVALID") # Bad format
        assert not generator.is_valid_term("")        # Empty string
    
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
        assert generator.get_term_display_name("INVALID") == "IN VALID"  # Expected behavior: splits at position 2
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
