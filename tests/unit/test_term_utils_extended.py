"""
Extended unit tests for term_utils.py - targeting missing coverage

This file focuses on testing term_utils functionality that wasn't covered
in the basic test suite.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from term_utils import TermGenerator, get_allowed_terms, is_valid_term, get_current_term


class TestTermGeneratorExtended:
    """Extended tests for TermGenerator class."""

    def test_term_generator_get_current_term_logic(self):
        """Test get_current_term logic."""
        generator = TermGenerator()
        
        # Mock datetime to test different months
        with patch('term_utils.datetime') as mock_datetime:
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
        
        # Test with empty string
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
