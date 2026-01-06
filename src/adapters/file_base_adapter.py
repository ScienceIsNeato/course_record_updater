"""
File-Based Adapter System

This module provides the abstract base class for all file processing adapters
in the adaptive import system. Each adapter handles institution-specific data
formats with automatic file compatibility detection and data type identification.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Tuple


class FileCompatibilityError(Exception):
    """Raised when a file is incompatible with an adapter"""

    pass


class FileBaseAdapter(ABC):
    """
    Abstract base class for all file processing adapters.

    Each adapter is responsible for:
    1. Validating file compatibility before processing
    2. Automatically detecting what data types are present
    3. Parsing files into standardized data structures
    4. Providing metadata for UI display and filtering
    """

    @abstractmethod
    def validate_file_compatibility(self, file_path: str) -> Tuple[bool, str]:
        """
        Check if the uploaded file is compatible with this adapter.

        This method should validate:
        - File format (extension, MIME type)
        - Required columns/fields presence
        - Data format patterns
        - File structure expectations

        Args:
            file_path: Path to the uploaded file

        Returns:
            Tuple[bool, str]: (is_compatible, message)
                - is_compatible: True if file can be processed by this adapter
                - message: Success details or specific error description

        Example:
            (True, "File compatible. Detected 45 course records, 12 faculty records.")
            (False, "Missing required columns: course_code, instructor_email")
        """
        pass

    @abstractmethod
    def detect_data_types(self, file_path: str) -> List[str]:
        """
        Analyze file content and automatically detect what types of data are present.

        This eliminates the need for users to manually select data types.
        The adapter determines what's in the file based on column headers,
        data patterns, and content analysis.

        Args:
            file_path: Path to the file to analyze

        Returns:
            List[str]: Data types found in the file
                Common types: ['courses', 'students', 'faculty', 'enrollments',
                              'assessments', 'programs', 'terms']

        Example:
            ['courses', 'faculty', 'assessments']  # Gemini Excel file
            ['students', 'enrollments']            # Student enrollment CSV
        """
        pass

    @abstractmethod
    def get_adapter_info(self) -> Dict[str, Any]:
        """
        Return metadata about this adapter for UI display and filtering.

        This information is used for:
        - UI dropdown population
        - Institution-based filtering
        - Version management
        - User guidance

        Returns:
            Dict containing adapter metadata

        Required fields:
            - id: Unique adapter identifier
            - name: Human-readable name for UI
            - description: What this adapter handles
            - supported_formats: List of file extensions
            - institution_id: Which institution this adapter serves (None for public adapters)
            - data_types: What types of data this adapter can process
            - version: Adapter version for tracking updates
            - public: Boolean - if True, adapter is available to ALL users regardless of institution

        Example (Institution-Specific):
            {
                "id": "cei_excel_format_v1",
                "name": "Gemini Excel Format v1.2",
                "description": "Imports course, faculty, and assessment data from Gemini's Excel exports",
                "supported_formats": [".xlsx", ".xls"],
                "institution_id": "mocku_institution_id",
                "data_types": ["courses", "faculty", "assessments"],
                "version": "1.2.0",
                "public": False,
                "created_by": "System Developer",
                "last_updated": "2024-09-25"
            }

        Example (Public/Generic):
            {
                "id": "generic_csv_v1",
                "name": "Generic CSV Format",
                "description": "Institution-agnostic CSV format for all users",
                "supported_formats": [".zip"],
                "institution_id": None,
                "data_types": ["all"],
                "version": "1.0.0",
                "public": True
            }
        """
        pass

    @abstractmethod
    def parse_file(
        self, file_path: str, options: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse the file and return structured data ready for database import.

        This method should:
        1. Read and parse the file content
        2. Transform data into standardized format
        3. Perform data validation and cleaning
        4. Return organized data by type

        Args:
            file_path: Path to the file to parse
            options: Configuration options for parsing
                - institution_id: Target institution ID
                - conflict_strategy: How to handle conflicts
                - dry_run: Whether this is a simulation
                - custom_options: Adapter-specific settings

        Returns:
            Dict mapping data types to lists of records

        Example:
            {
                'courses': [
                    {
                        'course_number': 'MATH101',
                        'title': 'Calculus I',
                        'credits': 4,
                        'institution_id': 'mocku_institution_id',
                        'created_at': '2024-09-25T10:30:00Z'
                    }
                ],
                'faculty': [
                    {
                        'email': 'prof.smith@mocku.test',
                        'first_name': 'John',
                        'last_name': 'Smith',
                        'role': 'instructor',
                        'institution_id': 'mocku_institution_id',
                        'created_at': '2024-09-25T10:30:00Z'
                    }
                ]
            }

        Raises:
            FileCompatibilityError: If file cannot be processed
            ValueError: If required options are missing
            Exception: For other parsing errors
        """
        pass

    @abstractmethod
    def export_data(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        output_path: str,
        options: Dict[str, Any],
    ) -> Tuple[bool, str, int]:
        """
        Export structured data to a file in the adapter's specific format.

        This method should:
        1. Transform standardized data into adapter-specific format
        2. Generate file content (Excel, CSV, etc.)
        3. Write file to the specified output path
        4. Return success status and metadata

        Args:
            data: Structured data organized by type (courses, users, terms, etc.)
            output_path: Where to save the exported file
            options: Export configuration options
                - institution_id: Source institution ID
                - export_view: Export format variant (standard, summary, etc.)
                - include_metadata: Whether to include export metadata
                - custom_options: Adapter-specific settings

        Returns:
            Tuple[bool, str, int]: (success, message, records_exported)

        Example data format:
            {
                'courses': [
                    {
                        'course_number': 'MATH101',
                        'title': 'Calculus I',
                        'credits': 4,
                        'institution_id': 'mocku_institution_id'
                    }
                ],
                'users': [
                    {
                        'email': 'prof.smith@mocku.test',
                        'first_name': 'John',
                        'last_name': 'Smith',
                        'role': 'instructor'
                    }
                ]
            }

        Raises:
            ValueError: If required options are missing
            Exception: For export errors
        """
        pass

    def supports_export(self) -> bool:
        """
        Check if this adapter supports export functionality.

        Returns:
            bool: True if adapter can export data
        """
        return True

    def get_export_formats(self) -> List[str]:
        """
        Get list of supported export file formats.

        Returns:
            List[str]: Supported formats (e.g., ['.xlsx', '.csv'])
        """
        # By default, return the same formats as import
        adapter_info = self.get_adapter_info()
        formats = adapter_info.get("supported_formats", [".xlsx"])
        return list(formats) if isinstance(formats, list) else [".xlsx"]

    def get_file_size_limit(self) -> int:
        """
        Return the maximum file size this adapter can handle in bytes.

        Returns:
            int: Maximum file size in bytes (default: 50MB)
        """
        return 50 * 1024 * 1024  # 50MB default

    def get_max_records(self) -> int:
        """
        Return the maximum number of records this adapter can process.

        Returns:
            int: Maximum record count (default: 10000)
        """
        return 10000

    def validate_file_size(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate that file size is within acceptable limits.

        Args:
            file_path: Path to the file to check

        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        try:
            file_size = Path(file_path).stat().st_size
            max_size = self.get_file_size_limit()

            if file_size > max_size:
                max_mb = max_size / (1024 * 1024)
                actual_mb = file_size / (1024 * 1024)
                return (
                    False,
                    f"File too large: {actual_mb:.1f}MB exceeds limit of {max_mb:.1f}MB",
                )

            return True, f"File size OK: {file_size / (1024 * 1024):.1f}MB"

        except Exception as e:
            return False, f"Error checking file size: {str(e)}"

    def validate_file_exists(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate that the file exists and is readable.

        Args:
            file_path: Path to the file to check

        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return False, f"File not found: {file_path}"

            if not path.is_file():
                return False, f"Path is not a file: {file_path}"

            # Try to read the file to check permissions
            with open(file_path, "rb") as f:
                f.read(1)  # Read just one byte to test

            return True, "File exists and is readable"

        except PermissionError:
            return False, f"Permission denied reading file: {file_path}"
        except Exception as e:
            return False, f"Error accessing file: {str(e)}"

    def get_supported_extensions(self) -> List[str]:
        """
        Get list of supported file extensions for this adapter.

        Returns:
            List[str]: Supported file extensions (e.g., ['.xlsx', '.xls'])
        """
        adapter_info = self.get_adapter_info()
        formats = adapter_info.get("supported_formats", [])
        return list(formats) if isinstance(formats, list) else []

    def validate_file_extension(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate that file extension is supported by this adapter.

        Args:
            file_path: Path to the file to check

        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        path = Path(file_path)
        file_ext = path.suffix.lower()
        supported_extensions = self.get_supported_extensions()

        if not supported_extensions:
            return True, "No extension restrictions"

        if file_ext in supported_extensions:
            return True, f"File extension {file_ext} is supported"
        else:
            return (
                False,
                f"Unsupported file extension {file_ext}. Supported: {', '.join(supported_extensions)}",
            )


class AdapterValidationResult:
    """
    Container for file validation results from an adapter.

    Provides structured access to validation outcomes and user-friendly messaging.
    """

    def __init__(self, adapter_id: str, file_path: str):
        self.adapter_id = adapter_id
        self.file_path = file_path
        self.is_compatible = False
        self.compatibility_message = ""
        self.detected_data_types: List[str] = []
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []
        self.file_info: Dict[str, Any] = {}

    def add_error(self, error: str) -> None:
        """Add a validation error."""
        self.validation_errors.append(error)

    def add_warning(self, warning: str) -> None:
        """Add a validation warning."""
        self.validation_warnings.append(warning)

    def set_compatible(self, message: str, data_types: List[str]) -> None:
        """Mark file as compatible with detected data types."""
        self.is_compatible = True
        self.compatibility_message = message
        self.detected_data_types = data_types

    def set_incompatible(self, message: str) -> None:
        """Mark file as incompatible with error message."""
        self.is_compatible = False
        self.compatibility_message = message

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for API responses."""
        return {
            "adapter_id": self.adapter_id,
            "file_path": Path(self.file_path).name,  # Just filename for security
            "is_compatible": self.is_compatible,
            "compatibility_message": self.compatibility_message,
            "detected_data_types": self.detected_data_types,
            "validation_errors": self.validation_errors,
            "validation_warnings": self.validation_warnings,
            "file_info": self.file_info,
        }
