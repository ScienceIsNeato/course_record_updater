import importlib
import os

import docx

from src.utils.logging_config import get_logger

from .base_adapter import BaseAdapter, ValidationError

# Get logger for file adapter operations
logger = get_logger("FileAdapter")


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
            self._base_validator = BaseAdapter()  # Instantiate for validation
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
                logger.warning(f"Adapter directory '{self.ADAPTER_DIR}' not found.")
                return []

            for filename in os.listdir(self.ADAPTER_DIR):
                if filename.endswith(".py") and filename not in self.EXCLUDE_FILES:
                    # Check if it's actually a file, not a directory named .py
                    filepath = os.path.join(self.ADAPTER_DIR, filename)
                    if os.path.isfile(filepath):
                        adapter_name = filename[:-3]  # Remove .py extension
                        adapter_names.append(adapter_name)
        except FileNotFoundError:
            logger.warning(
                f"Adapter directory '{self.ADAPTER_DIR}' not found during listdir."
            )
            return []  # Handle gracefully
        except Exception as e:
            logger.error(f"Error discovering adapters: {e}")
            # Log error but potentially continue or return empty
            return []

        logger.info(f"Discovered adapters: {adapter_names}")
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
        try:
            # Load and instantiate the adapter
            adapter_instance = self._load_adapter(adapter_name)

            # Parse the document
            parsed_data_list = self._parse_document(adapter_instance, document)

            # Apply validation if requested
            return self._apply_validation(parsed_data_list)

        except ImportError:
            raise DispatcherError(
                f"Adapter module 'adapters.{adapter_name}' not found."
            )
        except Exception as e:
            # Catch other potential errors during instantiation or parsing
            raise DispatcherError(
                f"Error processing with adapter '{adapter_name}': {e}"
            )

    def _load_adapter(self, adapter_name: str):
        """Load and instantiate the specified adapter."""
        # Dynamically import the adapter module
        module_path = f"adapters.{adapter_name}"
        module = importlib.import_module(module_path)  # nosemgrep

        # Convert adapter_name (snake_case) to ClassName (CamelCase)
        class_name = "".join(word.capitalize() for word in adapter_name.split("_"))

        # Get the class from the imported module
        if not hasattr(module, class_name):
            raise DispatcherError(
                f"Adapter class '{class_name}' not found in module '{module_path}'."
            )

        adapter_class = getattr(module, class_name)
        adapter_instance = adapter_class()

        # Check if the instance has a callable 'parse' method
        if not (
            hasattr(adapter_instance, "parse") and callable(adapter_instance.parse)
        ):
            raise DispatcherError(
                f"Adapter '{adapter_name}' (class {class_name}) does not have a callable 'parse' method."
            )

        return adapter_instance

    def _parse_document(self, adapter_instance, document: docx.document.Document):
        """Parse the document using the adapter instance."""
        class_name = adapter_instance.__class__.__name__
        logger.info(f"Parsing document with {class_name}...")

        parsed_data_list = adapter_instance.parse(document)
        logger.info(f"Raw parsed data count: {len(parsed_data_list)}")

        return parsed_data_list

    def _apply_validation(self, parsed_data_list):
        """Apply base validation if requested."""
        if not (self._use_base_validation and self._base_validator):
            return parsed_data_list  # Return raw parsed data

        logger.info("Applying base validation...")
        validated_data_list = []
        validation_errors = []

        for i, course_data in enumerate(parsed_data_list):
            try:
                validated = self._base_validator.parse_and_validate(course_data)
                validated_data_list.append(validated)
            except ValidationError as e:
                validation_errors.append(f"Record {i+1}: {e}")

        if validation_errors:
            # Raise a single error summarizing all validation issues for the file
            raise ValidationError("; ".join(validation_errors))

        logger.info(f"Base validation passed for {len(validated_data_list)} records.")
        return validated_data_list  # Return validated data
