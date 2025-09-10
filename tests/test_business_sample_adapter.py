# tests/test_business_sample_adapter.py
import io

import pytest
from docx import Document

# Import the adapter we intend to test
from adapters.business_sample_adapter import BusinessSampleAdapter

# Test data matching the expected RAW output structure AFTER parsing
# Type conversion happens in BaseAdapter
EXPECTED_BUSINESS_RAW_OUTPUT = [
    {
        "course_number": "BUS-101",
        "course_title": "Introduction to Business",
        "instructor_name": "Prof. Smith",
        "term": "FA2024",
        "num_students": "30",
        "grade_a": "5",
        "grade_b": "15",
        "grade_c": "8",
        "grade_d": "1",
        "grade_f": "1",
    },
    {
        "course_number": "ACCT-110",
        "course_title": "Principles of Accounting I",
        "instructor_name": "Prof. Ledger",
        "term": "FA2024",
        "num_students": "25",
        "grade_a": "4",
        "grade_b": "10",
        "grade_c": "6",
        "grade_d": "3",
        "grade_f": "2",
    },
    {
        "course_number": "MKTG-201",
        "course_title": "Marketing Principles",
        "instructor_name": "Prof. Adwell",
        "term": "SP2025",
        "num_students": "35",
    },  # Grades N/A, should not be present
    {
        "course_number": "BUS-250",
        "course_title": "Business Law",
        "instructor_name": "Prof. Gavel",
        "term": "SP2025",
        "num_students": "28",
        "grade_a": "7",
        "grade_b": "12",
        "grade_c": "5",
        "grade_d": "4",
        "grade_f": "0",
    },
    {
        "course_number": "ECON-201",
        "course_title": "Principles of Macroeconomics",
        "instructor_name": "Prof. Keynes",
        "term": "FA2024",
        "num_students": "40",
        "grade_a": "8",
        "grade_b": "18",
        "grade_c": "10",
        "grade_d": "3",
        "grade_f": "1",
    },
]


@pytest.fixture
def business_doc():
    """Provides a Document object loaded from the generated business_sample.docx"""
    try:
        return Document("business_sample.docx")
    except Exception as e:
        pytest.fail(f"Failed to load business_sample.docx: {e}")


def test_business_sample_adapter_parse(business_doc):
    """Test that the adapter correctly parses the business text block format."""
    adapter = BusinessSampleAdapter()
    parsed_data = adapter.parse(business_doc)
    # Note: This expects the raw parsed output BEFORE BaseAdapter validation/conversion
    assert parsed_data == EXPECTED_BUSINESS_RAW_OUTPUT
    # pytest.skip("BusinessSampleAdapter not yet implemented") # Removed skip


# TODO: Add tests for edge cases (missing fields, variations in spacing/keywords, etc.)
