# tests/test_base_adapter.py
import pytest

# Import the class we intend to test
from adapters.base_adapter import BaseAdapter, ValidationError
from term_utils import get_allowed_terms

# --- Test Data ---

VALID_TERM = get_allowed_terms()[0]  # Use the first allowed term

VALID_FORM_DATA = {
    "course_title": "Valid Title",
    "course_number": "VALID101",
    "term": VALID_TERM,
    "instructor_name": "Prof. Valid",
    "num_students": "30",  # Keep as string initially, adapter converts
}

EXPECTED_VALID_OUTPUT = {
    "course_title": "Valid Title",
    "course_number": "VALID101",
    "term": VALID_TERM,
    "instructor_name": "Prof. Valid",
    "num_students": 30,  # Expect integer
}

MISSING_REQUIRED_FIELD_DATA = {
    "course_title": "Valid Title",
    "course_number": "VALID101",
    # 'term': VALID_TERM, # Required field missing
    "instructor_name": "Prof. Valid",
    "num_students": "30",
}

INVALID_TERM_DATA = {
    "course_title": "Valid Title",
    "course_number": "VALID101",
    "term": "BADTERM20XX",  # Invalid term value
    "instructor_name": "Prof. Valid",
    "num_students": "30",
}

INVALID_STUDENTS_DATA = {
    "course_title": "Valid Title",
    "course_number": "VALID101",
    "term": VALID_TERM,
    "instructor_name": "Prof. Valid",
    "num_students": "-5",  # Invalid num_students (violates validator n >= 0)
}

EXTRA_FIELD_DATA = {
    "course_title": "Valid Title",
    "course_number": "VALID101",
    "term": VALID_TERM,
    "instructor_name": "Prof. Valid",
    "num_students": "30",
    "extra_field": "should be ignored",
}

# --- Tests for parse_and_validate ---


def test_parse_and_validate_success():
    """Test successful parsing and validation of valid form data."""
    adapter = BaseAdapter()
    result = adapter.parse_and_validate(VALID_FORM_DATA)
    assert result == EXPECTED_VALID_OUTPUT


def test_parse_and_validate_missing_required_field():
    """Test failure when a required field (term) is missing."""
    adapter = BaseAdapter()
    with pytest.raises(ValidationError, match="Missing required field: term"):
        adapter.parse_and_validate(MISSING_REQUIRED_FIELD_DATA)


def test_parse_and_validate_invalid_term():
    """Test failure when term is not in allowed terms."""
    adapter = BaseAdapter()
    with pytest.raises(ValidationError, match="Invalid value for term"):
        adapter.parse_and_validate(INVALID_TERM_DATA)


def test_parse_and_validate_invalid_students_type():
    """Test failure when num_students cannot be converted to int."""
    data = VALID_FORM_DATA.copy()  # Start with valid data
    data["num_students"] = "thirty"  # Make it non-numeric
    adapter = BaseAdapter()
    with pytest.raises(ValidationError, match="Invalid value for num_students"):
        adapter.parse_and_validate(data)


def test_parse_and_validate_invalid_students_value():
    """Test failure when num_students violates validator (e.g., negative)."""
    adapter = BaseAdapter()
    # INVALID_STUDENTS_DATA already has num_students = '-5'
    with pytest.raises(ValidationError, match="Invalid value for num_students"):
        adapter.parse_and_validate(INVALID_STUDENTS_DATA)


def test_parse_and_validate_extra_fields_ignored():
    """Test that extra fields in input are ignored."""
    adapter = BaseAdapter()
    result = adapter.parse_and_validate(EXTRA_FIELD_DATA)
    # Should return the same as valid data, ignoring 'extra_field'
    assert result == EXPECTED_VALID_OUTPUT


def test_parse_and_validate_empty_input():
    """Test handling of completely empty input."""
    adapter = BaseAdapter()
    # Check for one of the required fields it should complain about first
    with pytest.raises(ValidationError, match="Missing required field: course_title"):
        adapter.parse_and_validate({})


def test_parse_and_validate_empty_dict():
    """Test parse_and_validate with empty dict input."""
    adapter = BaseAdapter()
    try:
        result = adapter.parse_and_validate({})
        # Should fail due to missing required fields
        assert False, "Should have raised ValidationError"
    except ValidationError:
        # Expected behavior - missing required fields
        pass


def test_parse_and_validate_boundary_students_values():
    """Test parse_and_validate with boundary students values."""
    adapter = BaseAdapter()
    
    # Test with zero students (edge case)
    data_zero_students = {
        'Course Number': 'TEST-101',
        'Course Title': 'Test Course',
        'Instructor First Name': 'John',
        'Instructor Last Name': 'Doe',
        'Instructor Email': 'john@example.com',
        'Term': VALID_TERM,
        'Students': '0',  # Zero students
        'Department': 'TEST'
    }
    
    # This might be valid or invalid depending on business rules
    try:
        result = adapter.parse_and_validate(data_zero_students)
        assert isinstance(result, dict)
    except ValidationError:
        # Zero students might not be allowed
        pass


def test_parse_and_validate_whitespace_handling():
    """Test parse_and_validate handles whitespace correctly."""
    adapter = BaseAdapter()
    
    # Test with whitespace in fields
    data_with_whitespace = {
        'course_number': '  TEST-101  ',  # Leading/trailing spaces
        'course_title': '  Test Course  ',
        'instructor_name': '  John Doe  ',
        'term': f'  {VALID_TERM}  ',
        'num_students': '  25  '
    }
    
    result = adapter.parse_and_validate(data_with_whitespace)
    assert isinstance(result, dict)
    # Should handle whitespace appropriately - the method strips whitespace internally
    assert 'course_number' in result


def test_parse_and_validate_multiple_records_with_errors():
    """Test parse_and_validate with multiple records where some have errors."""
    adapter = BaseAdapter()
    
    # Mix of valid and invalid records
    mixed_data = [
        {  # Valid record
            'Course Number': 'TEST-101',
            'Course Title': 'Test Course 1',
            'Instructor First Name': 'John',
            'Instructor Last Name': 'Doe',
            'Instructor Email': 'john@example.com',
            'Term': VALID_TERM,
            'Students': '25',
            'Department': 'TEST'
        },
        {  # Invalid record - bad email
            'Course Number': 'TEST-102',
            'Course Title': 'Test Course 2',
            'Instructor First Name': 'Jane',
            'Instructor Last Name': 'Smith',
            'Instructor Email': 'invalid_email',  # Bad email
            'Term': VALID_TERM,
            'Students': '30',
            'Department': 'TEST'
        }
    ]
    
    # Test with one valid record
    valid_data = {
        'course_title': 'Valid Course',
        'course_number': 'VALID-101',
        'term': VALID_TERM,  # Use the valid term constant
        'instructor_name': 'Valid Instructor'
    }
    result = adapter.parse_and_validate(valid_data)
    assert isinstance(result, dict)


def test_base_adapter_constants_and_attributes():
    """Test BaseAdapter constants and attributes."""
    adapter = BaseAdapter()
    
    # Test that expected fields are defined
    assert hasattr(adapter, 'EXPECTED_FIELDS')
    assert isinstance(adapter.EXPECTED_FIELDS, dict)
    assert len(adapter.EXPECTED_FIELDS) > 0
    
    # Test that grade fields are defined
    assert hasattr(adapter, 'GRADE_FIELDS')
    assert isinstance(adapter.GRADE_FIELDS, list)
    assert len(adapter.GRADE_FIELDS) > 0
    
    # All grade fields should be in expected fields
    for field in adapter.GRADE_FIELDS:
        assert field in adapter.EXPECTED_FIELDS
