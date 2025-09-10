# tests/test_nursing_sample_adapter.py
import io

import pytest
from docx import Document

# Import the adapter we intend to test
from adapters.nursing_sample_adapter import NursingSampleAdapter

# Test data matching the expected output structure from base_adapter validation
EXPECTED_NURSING_OUTPUT = [
    # Raw parsed strings first, BaseAdapter will handle type conversion
    {
        "course_number": "NUR-101",
        "course_title": "Fundamentals of Nursing",
        "instructor_name": "Prof. Nightingale",
        "term": "FA2024",
        "num_students": "45",
        "grade_a": "10",
        "grade_b": "20",
        "grade_c": "10",
        "grade_d": "3",
        "grade_f": "2",
    },
    {
        "course_number": "NUR-105",
        "course_title": "Medical Terminology",
        "instructor_name": "Prof. Caduceus",
        "term": "FA2024",
        "num_students": "50",
        "grade_a": "",
        "grade_b": "",
        "grade_c": "",
        "grade_d": "",
        "grade_f": "",
    },
    {
        "course_number": "NUR-210",
        "course_title": "Pharmacology for Nurses",
        "instructor_name": "Prof. Nightingale",
        "term": "SP2025",
        "num_students": "40",
        "grade_a": "15",
        "grade_b": "15",
        "grade_c": "8",
        "grade_d": "2",
        "grade_f": "0",
    },
]


@pytest.fixture
def nursing_doc():
    """Provides a Document object loaded from the generated nursing_sample.docx"""
    try:
        return Document("nursing_sample.docx")
    except Exception as e:
        pytest.fail(f"Failed to load nursing_sample.docx: {e}")


def test_nursing_sample_adapter_parse(nursing_doc):
    """Test that the adapter correctly parses the nursing table format."""
    adapter = NursingSampleAdapter()
    parsed_data = adapter.parse(nursing_doc)
    # Note: This expects the raw parsed output BEFORE BaseAdapter validation/conversion
    assert parsed_data == EXPECTED_NURSING_OUTPUT


# TODO: Add tests for edge cases (empty table, missing columns, extra columns, etc.)
