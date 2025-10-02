# tests/test_file_adapter_dispatcher.py
# Unused imports removed
import os
import re
from unittest.mock import MagicMock, patch

import docx
import pytest

# Also import BaseAdapter for validation mocking
from adapters.base_adapter import ValidationError

# Import the class and exception we intend to test (will fail initially)
from adapters.file_adapter_dispatcher import DispatcherError, FileAdapterDispatcher

# --- Test Setup ---

# Create dummy adapter files for discovery tests
# Use pytest fixtures to manage temporary files/directories if preferred
ADAPTERS_DIR = "adapters"


# Mock the docx.Document object
@pytest.fixture
def mock_docx_document():
    return MagicMock(spec=docx.document.Document)


# --- Tests for discover_adapters ---


def test_discover_adapters_success(mocker):
    """Test finding adapter files in the directory."""
    # Mock os.listdir to simulate finding files
    mock_files = [
        "__init__.py",
        "base_adapter.py",
        "dummy_adapter.py",
        "adapter_v1.py",
        "invalid.txt",
    ]
    mocker.patch("os.listdir", return_value=mock_files)
    mocker.patch("os.path.isfile", return_value=True)  # Assume they are all files

    dispatcher = FileAdapterDispatcher()
    adapters = dispatcher.discover_adapters()

    # Expect only .py files, excluding __init__ and base_adapter
    assert sorted(adapters) == sorted(["dummy_adapter", "adapter_v1"])
    os.listdir.assert_called_once_with(ADAPTERS_DIR)


def test_discover_adapters_no_adapters(mocker):
    """Test when only non-adapter files are present."""
    mock_files = ["__init__.py", "base_adapter.py", "notes.txt"]
    mocker.patch("os.listdir", return_value=mock_files)
    mocker.patch("os.path.isfile", return_value=True)

    dispatcher = FileAdapterDispatcher()
    adapters = dispatcher.discover_adapters()
    assert adapters == []


def test_discover_adapters_directory_not_found(mocker):
    """Test when the adapters directory doesn't exist."""
    mocker.patch("os.listdir", side_effect=FileNotFoundError)

    dispatcher = FileAdapterDispatcher()
    adapters = dispatcher.discover_adapters()
    assert adapters == []  # Should handle gracefully and return empty list


# --- Tests for process_file ---


def test_process_file_success(mocker, mock_docx_document):
    """Test successfully dispatching to a valid adapter."""
    adapter_name = "dummy_adapter"
    module_to_import = f"adapters.{adapter_name}"

    # Mock the dynamic import within the dispatcher module
    mock_module = MagicMock()
    mock_adapter_class = MagicMock()
    mock_adapter_instance = MagicMock()

    # Mock the module import and capture the mock object
    mock_import = mocker.patch(
        "adapters.file_adapter_dispatcher.importlib.import_module",
        return_value=mock_module,
    )
    # Mock hasattr and getattr to return the mock class
    mocker.patch.object(mock_module, "DummyAdapter", mock_adapter_class, create=True)
    # mocker.patch('hasattr', return_value=True) # Assume class exists
    # mocker.patch('getattr', return_value=mock_adapter_class) # Return mock class
    # Mock class instantiation to return the mock instance
    mock_adapter_class.return_value = mock_adapter_instance

    # Define the raw data the adapter's parse method should return (as a list)
    mock_parsed_data_from_adapter = [
        {
            "course_title": "Parsed Title",
            "course_number": "PARSED101",
            "semester": "Parsed Semester",
            "year": "2025",  # String initially
            "professor": "Prof. Parsed",
            "num_students": "55",  # String initially
        }
    ]
    # Explicitly create the parse attribute as a MagicMock
    mock_adapter_instance.parse = MagicMock(return_value=mock_parsed_data_from_adapter)
    # mock_adapter_instance.parse.return_value = mock_parsed_data_from_adapter # Becomes redundant
    # Ensure the parse method is seen as callable - This is now handled by MagicMock directly
    # mock_adapter_instance.parse.__call__ = MagicMock() # Becomes redundant

    # Define the final expected data after successful base validation (list containing dict)
    expected_validated_data = [
        {
            "course_title": "Parsed Title",
            "course_number": "PARSED101",
            "semester": "Parsed Semester",
            "year": 2025,
            "professor": "Prof. Parsed",
            "num_students": 55,
        }
    ]

    # Instantiate the REAL dispatcher
    dispatcher = FileAdapterDispatcher(use_base_validation=True)
    # Patch the validation method on the instance of BaseAdapter within the dispatcher
    mock_validation_method = mocker.patch.object(
        dispatcher._base_validator,
        "parse_and_validate",
        return_value=expected_validated_data[
            0
        ],  # Validator gets the dict, returns the validated dict
    )

    # Act
    result = dispatcher.process_file(mock_docx_document, adapter_name)

    # Assertions
    assert (
        result == expected_validated_data
    )  # Expect a list containing the validated dict
    # Revert to asserting on the captured mock object
    mock_import.assert_called_once_with(module_to_import)
    mock_adapter_instance.parse.assert_called_once_with(mock_docx_document)
    # Check that the validation method was called with the raw data dict
    mock_validation_method.assert_called_once_with(mock_parsed_data_from_adapter[0])


def test_process_file_adapter_not_found(mocker, mock_docx_document):
    """Test when the requested adapter module cannot be imported."""
    adapter_name = "non_existent"
    module_path = f"adapters.{adapter_name}"
    # Mock importlib.import_module to raise ImportError for the specific path
    mocker.patch(
        "adapters.file_adapter_dispatcher.importlib.import_module",
        side_effect=ImportError(f"No module named '{module_path}'"),
    )

    dispatcher = FileAdapterDispatcher()

    # Correct the expected error message to match the actual raised message
    expected_error_msg = f"Adapter module '{module_path}' not found."
    with pytest.raises(DispatcherError, match=expected_error_msg):
        dispatcher.process_file(mock_docx_document, adapter_name)


def test_process_file_adapter_missing_parse_function(mocker, mock_docx_document):
    """Test when the adapter module exists but lacks a callable parse function."""
    adapter_name = "missing_parse"
    class_name = "MissingParse"  # Calculate class name

    # Mock the module, class, and instance structure
    mock_module = MagicMock()
    mock_class = MagicMock()
    mock_instance = MagicMock()
    # Configure mocks
    mocker.patch(
        "adapters.file_adapter_dispatcher.importlib.import_module",
        return_value=mock_module,
    )
    mocker.patch.object(
        mock_module, class_name, mock_class, create=True
    )  # Mock the class lookup
    mock_class.return_value = mock_instance  # Mock instantiation

    # Make the 'parse' attribute present but not callable
    # del mock_instance.parse # Removing completely also works
    # Or make it not callable
    mock_instance.parse = "not_a_callable_attribute"

    dispatcher = FileAdapterDispatcher()

    # Update expected error message to match the code exactly, escaping regex chars
    expected_error_msg = f"Adapter '{adapter_name}' \\(class {class_name}\\) does not have a callable 'parse' method\\."
    with pytest.raises(DispatcherError, match=expected_error_msg):
        dispatcher.process_file(mock_docx_document, adapter_name)


def test_process_file_adapter_parse_error(mocker, mock_docx_document):
    """Test when the adapter's parse function raises an error."""
    adapter_name = "parse_error_adapter"
    class_name = "ParseErrorAdapter"  # Calculate class name
    error_message = "Specific parsing failed"

    # Mock the module, class, and instance structure
    mock_module = MagicMock()
    mock_class = MagicMock()
    mock_instance = MagicMock()
    # Configure mocks
    mocker.patch(
        "adapters.file_adapter_dispatcher.importlib.import_module",
        return_value=mock_module,
    )
    mocker.patch.object(mock_module, class_name, mock_class, create=True)
    mock_class.return_value = mock_instance

    # Make the parse method callable but raise an error
    mock_instance.parse.side_effect = ValueError(error_message)
    # Ensure the parse method is seen as callable before the error
    mock_instance.parse.__call__ = MagicMock(side_effect=ValueError(error_message))

    dispatcher = FileAdapterDispatcher()

    # Update expected error message based on the generic exception handler, escape regex
    expected_error_msg = (
        f"Error processing with adapter '{adapter_name}': {error_message}"
    )
    with pytest.raises(DispatcherError, match=expected_error_msg):
        dispatcher.process_file(mock_docx_document, adapter_name)


# Add test for post-parse validation failure if implemented
def test_process_file_base_validation_error(mocker, mock_docx_document):
    """Test when base validation fails after successful parsing."""
    adapter_name = "valid_parse_adapter"
    class_name = "ValidParseAdapter"

    mock_module = MagicMock()
    mock_class = MagicMock()
    mock_instance = MagicMock()  # Define mock_instance here

    mocker.patch(
        "adapters.file_adapter_dispatcher.importlib.import_module",
        return_value=mock_module,
    )
    mocker.patch.object(mock_module, class_name, mock_class, create=True)
    mock_class.return_value = mock_instance  # Ensure mock_instance is assigned

    # Adapter parse succeeds, returning a list of dicts
    mock_parsed_data_from_adapter = [
        {
            "course_title": "Valid Title",
            "course_number": "VALID101",
            "semester": "Valid Semester",
            "year": "2025",
            "professor": "Prof. Valid",
            "num_students": "bad_number",  # Invalid data for base validation
        }
    ]
    # Assign return value and callable mock to the now defined mock_instance
    mock_instance.parse.return_value = mock_parsed_data_from_adapter
    mock_instance.parse.__call__ = MagicMock()  # Make callable

    dispatcher = FileAdapterDispatcher(use_base_validation=True)
    # Mock the base validator to raise ValidationError
    validation_error_msg = "Invalid literal for int() with base 10: 'bad_number'"
    mocker.patch.object(
        dispatcher._base_validator,
        "parse_and_validate",
        side_effect=ValidationError(validation_error_msg),
    )

    # Expect the dispatcher to catch the ValidationError and re-raise as DispatcherError
    raw_error_msg = f"Error processing with adapter '{adapter_name}': Record 1: {validation_error_msg}"
    # Escape the error message for regex matching
    expected_error_msg_regex = re.escape(raw_error_msg)
    with pytest.raises(DispatcherError, match=expected_error_msg_regex):
        dispatcher.process_file(mock_docx_document, adapter_name)


class TestFileAdapterDispatcherInitialization:
    """Test FileAdapterDispatcher initialization and configuration."""

    def test_init_without_base_validation(self):
        """Test initialization without base validation."""
        dispatcher = FileAdapterDispatcher(use_base_validation=False)

        assert dispatcher._base_validator is None
        assert dispatcher._use_base_validation is False

    def test_init_with_base_validation(self):
        """Test initialization with base validation."""
        dispatcher = FileAdapterDispatcher(use_base_validation=True)

        assert dispatcher._base_validator is not None
        assert dispatcher._use_base_validation is True

    def test_discover_adapters_directory_not_found(self):
        """Test discover_adapters when adapters directory doesn't exist."""
        dispatcher = FileAdapterDispatcher()

        with patch("os.path.isdir", return_value=False):
            adapters = dispatcher.discover_adapters()
            # Should return empty list gracefully
            assert adapters == []

    def test_discover_adapters_file_not_directory(self):
        """Test discover_adapters when adapters path is a file, not directory."""
        dispatcher = FileAdapterDispatcher()

        with patch("os.path.isdir", return_value=False):
            adapters = dispatcher.discover_adapters()
            # Should return empty list gracefully
            assert adapters == []

    def test_discover_adapters_general_exception(self):
        """Test discover_adapters with general exception."""
        dispatcher = FileAdapterDispatcher()

        with (
            patch("os.path.isdir", return_value=True),
            patch("os.listdir", side_effect=OSError("Permission denied")),
        ):
            adapters = dispatcher.discover_adapters()
            # Should return empty list gracefully
            assert adapters == []

    def test_discover_adapters_with_various_file_types(self):
        """Test discover_adapters with various file types in directory."""
        dispatcher = FileAdapterDispatcher()

        # Mock directory with various files
        mock_files = [
            "__init__.py",
            "valid_adapter.py",
            "README.md",
            ".hidden_file",
            "test_file.py",
        ]

        with (
            patch("os.path.isdir", return_value=True),
            patch("os.listdir", return_value=mock_files),
            patch("os.path.isfile", return_value=True),
        ):
            adapters = dispatcher.discover_adapters()

            # Should only include .py files that aren't excluded
            expected_adapters = ["valid_adapter", "test_file"]
            assert set(adapters) == set(expected_adapters)


class TestFileAdapterDispatcherValidation:
    """Test validation-related functionality."""

    def test_apply_validation_disabled(self):
        """Test _apply_validation returns raw data when validation disabled."""
        from adapters.file_adapter_dispatcher import FileAdapterDispatcher

        dispatcher = FileAdapterDispatcher(use_base_validation=False)

        # When validation is disabled, should return data unchanged (line 156)
        test_data = [{"key": "value"}]
        result = dispatcher._apply_validation(test_data)

        assert result == test_data  # Should return raw data
