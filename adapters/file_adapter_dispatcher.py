import os
import importlib
import docx
from .base_adapter import BaseAdapter, ValidationError

# Define a custom exception for dispatcher errors
class DispatcherError(Exception):
    pass

class FileAdapterDispatcher:
    """
    Discovers available file adapters and dispatches parsing tasks.
    Optionally uses BaseAdapter for post-parsing validation.
    """
    ADAPTER_DIR = "adapters"
    # Files to exclude during discovery
    EXCLUDE_FILES = ["__init__.py", "base_adapter.py", "file_adapter_dispatcher.py"]

    def __init__(self, use_base_validation=True):
        """
        Initializes the dispatcher.

        Args:
            use_base_validation: If True, use BaseAdapter().parse_and_validate
                                 on the data returned by the specific file adapter.
        """
        self._use_base_validation = use_base_validation
        if use_base_validation:
            self._base_validator = BaseAdapter() # Instantiate for validation
        else:
             self._base_validator = None
        # Cache discovered adapters maybe?
        # self._available_adapters = self.discover_adapters()

    def discover_adapters(self):
        """
        Finds available adapter modules in the adapter directory.

        Returns:
            A list of adapter names (filenames without .py).
        """
        adapter_names = []
        try:
            # Ensure ADAPTER_DIR is relative to this file's location or use absolute path
            # For simplicity, assume it's relative to project root where app runs
            if not os.path.isdir(self.ADAPTER_DIR):
                 print(f"Warning: Adapter directory '{self.ADAPTER_DIR}' not found.")
                 return []
                 
            for filename in os.listdir(self.ADAPTER_DIR):
                if filename.endswith(".py") and filename not in self.EXCLUDE_FILES:
                    # Check if it's actually a file, not a directory named .py
                    filepath = os.path.join(self.ADAPTER_DIR, filename)
                    if os.path.isfile(filepath):
                        adapter_name = filename[:-3] # Remove .py extension
                        adapter_names.append(adapter_name)
        except FileNotFoundError:
            print(f"Warning: Adapter directory '{self.ADAPTER_DIR}' not found during listdir.")
            return [] # Handle gracefully
        except Exception as e:
            print(f"Error discovering adapters: {e}")
            # Log error but potentially continue or return empty
            return []
        
        print(f"Discovered adapters: {adapter_names}")
        return adapter_names

    def process_file(self, document: docx.document.Document, adapter_name: str):
        """
        Loads the specified adapter, calls its parse function, and optionally validates.

        Args:
            document: A python-docx Document object.
            adapter_name: The name of the adapter module to use (e.g., 'dummy_adapter').

        Returns:
            A dictionary containing the validated data on success.

        Raises:
            DispatcherError: If the adapter cannot be found/imported, lacks a parse function,
                             or if parsing/validation fails.
        """
        module_name = f"adapters.{adapter_name}"
        try:
            print(f"Attempting to import adapter module: {module_name}")
            adapter_module = importlib.import_module(module_name)
            print(f"Successfully imported {module_name}")
        except ImportError as e:
            print(f"ImportError for {module_name}: {e}")
            raise DispatcherError(f"Adapter module '{module_name}' not found or failed to import.") from e

        if not hasattr(adapter_module, 'parse') or not callable(adapter_module.parse):
            raise DispatcherError(f"Adapter '{adapter_name}' does not have a callable 'parse' function.")

        try:
            print(f"Calling parse function for adapter: {adapter_name}")
            # Call the specific adapter's parse function
            parsed_data = adapter_module.parse(document)
            print(f"Adapter {adapter_name} returned: {parsed_data}")
            
            if not isinstance(parsed_data, dict):
                 raise DispatcherError(f"Adapter '{adapter_name}' did not return a dictionary.")

        except Exception as e:
            # Catch broad exceptions from the parse function itself
            print(f"Error during {adapter_name}.parse(): {e}")
            raise DispatcherError(f"Error during parsing with adapter '{adapter_name}': {e}") from e

        # Optional: Post-parsing validation using BaseAdapter
        if self._use_base_validation and self._base_validator:
            try:
                print(f"Performing base validation on data from {adapter_name}")
                # Validate the data structure and types using BaseAdapter logic
                # Note: BaseAdapter.parse_and_validate expects form-like string data.
                # We might need a different validation method or adapt BaseAdapter
                # if parsed_data contains non-string types already.
                # For now, assume it can handle the dictionary from parse.
                validated_data = self._base_validator.parse_and_validate(parsed_data) # This might need adjustment!
                print(f"Base validation successful for {adapter_name}")
                return validated_data
            except ValidationError as e:
                print(f"Base validation failed for data from {adapter_name}: {e}")
                raise DispatcherError(f"Validation failed for data parsed by '{adapter_name}': {e}") from e
            except Exception as e:
                 print(f"Unexpected error during base validation for {adapter_name}: {e}")
                 raise DispatcherError(f"Unexpected validation error for '{adapter_name}': {e}") from e
        else:
            # If not using base validation, return the directly parsed data
            print(f"Skipping base validation for {adapter_name}")
            return parsed_data 