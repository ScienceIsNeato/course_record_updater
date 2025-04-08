# tests/test_base_adapter.py
import pytest

# Import the class we intend to test (will fail initially)
from adapters.base_adapter import BaseAdapter, ValidationError

# --- Test Data ---

VALID_FORM_DATA = {
    'course_title': 'Valid Title',
    'course_number': 'VALID101',
    'semester': 'Spring',
    'year': '2024',
    'professor': 'Prof. Valid',
    'num_students': '30'
}

EXPECTED_VALID_OUTPUT = {
    'course_title': 'Valid Title',
    'course_number': 'VALID101',
    'semester': 'Spring',
    'year': 2024, # Expect integer
    'professor': 'Prof. Valid',
    'num_students': 30 # Expect integer
}

MISSING_REQUIRED_FIELD_DATA = {
    'course_title': 'Valid Title',
    # 'course_number': 'MISSING', # Required field missing
    'semester': 'Spring',
    'year': '2024',
    'professor': 'Prof. Valid',
    'num_students': '30'
}

INVALID_YEAR_DATA = {
    'course_title': 'Valid Title',
    'course_number': 'VALID101',
    'semester': 'Spring',
    'year': 'TwentyTwentyFour', # Invalid integer
    'professor': 'Prof. Valid',
    'num_students': '30'
}

INVALID_STUDENTS_DATA = {
    'course_title': 'Valid Title',
    'course_number': 'VALID101',
    'semester': 'Spring',
    'year': '2024',
    'professor': 'Prof. Valid',
    'num_students': '-5' # Example of a logical error, could also be non-numeric
}

EXTRA_FIELD_DATA = {
    'course_title': 'Valid Title',
    'course_number': 'VALID101',
    'semester': 'Spring',
    'year': '2024',
    'professor': 'Prof. Valid',
    'num_students': '30',
    'extra_field': 'should be ignored'
}

# --- Tests for parse_and_validate ---

def test_parse_and_validate_success():
    """Test successful parsing and validation of valid form data."""
    adapter = BaseAdapter()
    result = adapter.parse_and_validate(VALID_FORM_DATA)
    assert result == EXPECTED_VALID_OUTPUT

def test_parse_and_validate_missing_required_field():
    """Test failure when a required field is missing."""
    adapter = BaseAdapter()
    with pytest.raises(ValidationError, match="Missing required field: course_number"):
        adapter.parse_and_validate(MISSING_REQUIRED_FIELD_DATA)

def test_parse_and_validate_invalid_year_type():
    """Test failure when year cannot be converted to int."""
    adapter = BaseAdapter()
    with pytest.raises(ValidationError, match="Invalid value for year"):
        adapter.parse_and_validate(INVALID_YEAR_DATA)

def test_parse_and_validate_invalid_students_type():
    """Test failure when num_students cannot be converted to int."""
    # Assuming num_students is optional for requirement, but mandatory for type
    # Let's make it non-numeric for this test
    data = INVALID_STUDENTS_DATA.copy()
    data['num_students'] = 'thirty'
    adapter = BaseAdapter()
    with pytest.raises(ValidationError, match="Invalid value for num_students"):
        adapter.parse_and_validate(data)

# Optional: Add a test for negative student numbers if that's a business rule
# def test_parse_and_validate_negative_students():
#     adapter = BaseAdapter()
#     with pytest.raises(ValidationError, match="Number of students cannot be negative"):
#         adapter.parse_and_validate(INVALID_STUDENTS_DATA)

def test_parse_and_validate_extra_fields_ignored():
    """Test that extra fields in input are ignored."""
    adapter = BaseAdapter()
    result = adapter.parse_and_validate(EXTRA_FIELD_DATA)
    # Should return the same as valid data, ignoring 'extra_field'
    assert result == EXPECTED_VALID_OUTPUT

def test_parse_and_validate_empty_input():
    """Test handling of completely empty input."""
    adapter = BaseAdapter()
    with pytest.raises(ValidationError, match="Missing required field"):
         # It should fail on the first missing required field
        adapter.parse_and_validate({}) 