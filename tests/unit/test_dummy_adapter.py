# tests/test_dummy_adapter.py
from unittest.mock import MagicMock

import docx
import pytest

# Import the function/module to test
from adapters.dummy_adapter import parse


@pytest.fixture
def mock_docx_document():
    """Provides a mock docx.Document object for tests."""
    return MagicMock(spec=docx.document.Document)


def test_dummy_adapter_parse(mock_docx_document):
    """Test that the dummy adapter returns the expected dictionary structure."""
    # Act
    result = parse(mock_docx_document)

    # Assert
    assert isinstance(result, dict)
    # Check for expected keys and that values are strings initially
    expected_keys = [
        "course_title",
        "course_number",
        "semester",
        "year",
        "professor",
        "num_students",
    ]
    assert all(key in result for key in expected_keys)
    assert all(isinstance(result[key], str) for key in expected_keys if key in result)

    # Check specific dummy values
    assert result["course_number"] == "DUMMY101"
    assert result["year"] == "2024"
    assert result["num_students"] == "42"
