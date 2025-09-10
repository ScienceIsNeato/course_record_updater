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
