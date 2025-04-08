# tests/test_file_adapter_dispatcher.py
import pytest
import os
import importlib
from unittest.mock import MagicMock, patch, call
import docx

# Import the class and exception we intend to test (will fail initially)
from adapters.file_adapter_dispatcher import FileAdapterDispatcher, DispatcherError
# Also import BaseAdapter for validation mocking
from adapters.base_adapter import BaseAdapter, ValidationError 

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
    mock_files = ['__init__.py', 'base_adapter.py', 'dummy_adapter.py', 'adapter_v1.py', 'invalid.txt']
    mocker.patch('os.listdir', return_value=mock_files)
    mocker.patch('os.path.isfile', return_value=True) # Assume they are all files

    dispatcher = FileAdapterDispatcher()
    adapters = dispatcher.discover_adapters()

    # Expect only .py files, excluding __init__ and base_adapter
    assert sorted(adapters) == sorted(['dummy_adapter', 'adapter_v1'])
    os.listdir.assert_called_once_with(ADAPTERS_DIR)

def test_discover_adapters_no_adapters(mocker):
    """Test when only non-adapter files are present."""
    mock_files = ['__init__.py', 'base_adapter.py', 'notes.txt']
    mocker.patch('os.listdir', return_value=mock_files)
    mocker.patch('os.path.isfile', return_value=True)

    dispatcher = FileAdapterDispatcher()
    adapters = dispatcher.discover_adapters()
    assert adapters == []

def test_discover_adapters_directory_not_found(mocker):
    """Test when the adapters directory doesn't exist."""
    mocker.patch('os.listdir', side_effect=FileNotFoundError)

    dispatcher = FileAdapterDispatcher()
    adapters = dispatcher.discover_adapters()
    assert adapters == [] # Should handle gracefully and return empty list

# --- Tests for process_file --- 

def test_process_file_success(mocker, mock_docx_document):
    """Test successfully dispatching to a valid adapter."""
    adapter_name = 'dummy_adapter'
    module_to_import = f"adapters.{adapter_name}"

    # Mock the dynamic import within the dispatcher module
    mock_adapter_module = MagicMock()
    mock_parsed_data_from_adapter = {
        'course_title': 'Parsed Title',
        'course_number': 'PARSED101',
        'semester': 'Parsed Semester',
        'year': '2025',
        'professor': 'Prof. Parsed',
        'num_students': '55'
    }
    mock_adapter_module.parse.return_value = mock_parsed_data_from_adapter
    mock_import = mocker.patch('adapters.file_adapter_dispatcher.importlib.import_module', return_value=mock_adapter_module)

    # Define the final expected data after successful base validation
    expected_validated_data = {
        'course_title': 'Parsed Title',
        'course_number': 'PARSED101',
        'semester': 'Parsed Semester',
        'year': 2025,
        'professor': 'Prof. Parsed',
        'num_students': 55
    }
    
    # Instantiate the REAL dispatcher
    dispatcher = FileAdapterDispatcher(use_base_validation=True)
    # Now, patch the method on the *instance* of BaseAdapter created within the dispatcher
    mock_validation_method = mocker.patch.object(
        dispatcher._base_validator, 
        'parse_and_validate', 
        return_value=expected_validated_data
    )

    # Act
    result = dispatcher.process_file(mock_docx_document, adapter_name)

    # Assertions
    assert result == expected_validated_data
    mock_import.assert_called_with(module_to_import)
    mock_adapter_module.parse.assert_called_once_with(mock_docx_document)
    # Check that the patched validation method on the instance was called
    mock_validation_method.assert_called_once_with(mock_parsed_data_from_adapter)

def test_process_file_adapter_not_found(mocker, mock_docx_document):
    """Test when the requested adapter module cannot be imported."""
    mocker.patch('importlib.import_module', side_effect=ImportError("No module named adapters.non_existent"))

    dispatcher = FileAdapterDispatcher()
    adapter_name = 'non_existent'

    with pytest.raises(DispatcherError, match="Adapter module 'adapters.non_existent' not found or failed to import."):
        dispatcher.process_file(mock_docx_document, adapter_name)

def test_process_file_adapter_missing_parse_function(mocker, mock_docx_document):
    """Test when the adapter module exists but lacks a parse function."""
    mock_adapter_module = MagicMock()
    del mock_adapter_module.parse # Remove the parse attribute
    mocker.patch('importlib.import_module', return_value=mock_adapter_module)

    dispatcher = FileAdapterDispatcher()
    adapter_name = 'missing_parse'

    # Update expected error message to include "callable"
    with pytest.raises(DispatcherError, match="Adapter 'missing_parse' does not have a callable 'parse' function."):
        dispatcher.process_file(mock_docx_document, adapter_name)

def test_process_file_adapter_parse_error(mocker, mock_docx_document):
    """Test when the adapter's parse function raises an error."""
    mock_adapter_module = MagicMock()
    mock_adapter_module.parse.side_effect = ValueError("Specific parsing failed")
    mocker.patch('importlib.import_module', return_value=mock_adapter_module)

    dispatcher = FileAdapterDispatcher()
    adapter_name = 'parse_error_adapter'

    with pytest.raises(DispatcherError, match="Error during parsing with adapter 'parse_error_adapter'"):
        dispatcher.process_file(mock_docx_document, adapter_name)

# Add test for post-parse validation failure if implemented
# def test_process_file_post_parse_validation_error(mocker, mock_docx_document):
#     ... 