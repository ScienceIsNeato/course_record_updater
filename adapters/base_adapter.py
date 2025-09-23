# adapters/base_adapter.py

from typing import Any

from term_utils import is_valid_term


# Define a custom exception for validation errors
class ValidationError(ValueError):
    pass


class BaseAdapter:
    """
    Base adapter for parsing and validating input data, primarily from forms.
    Does not handle file-specific logic or database interactions.
    """

    # Define fields expected from input sources and their requirements
    # Tuple: (required: bool, type: type | None, validator_func: callable | None)
    EXPECTED_FIELDS = {
        "course_title": (True, str, None),
        "course_number": (True, str, None),
        # 'semester': (True, str, None), # Replaced by term
        # 'year': (True, int, lambda y: y >= 2000), # Replaced by term
        "term": (True, str, is_valid_term),  # Dynamic term validation
        "instructor_name": (True, str, None),  # Corrected field name
        "num_students": (
            False,
            int,
            lambda n: n >= 0,
        ),
    }

    def _prepare_raw_input_data(self, form_data: dict) -> dict:
        """Prepare raw input data by stripping whitespace."""
        return {k: str(v).strip() for k, v in form_data.items()}

    def _check_required_fields(self, raw_input_data: dict) -> list:
        """Check for missing required fields and return errors."""
        errors = []
        for field, config in self.EXPECTED_FIELDS.items():
            is_required = config[0]
            if is_required and not raw_input_data.get(field):
                errors.append(f"Missing required field: {field}")
        return errors

    def _convert_field_value(
        self, field: str, value_str: str, expected_type: type
    ) -> tuple:
        """Convert field value to expected type. Returns (processed_value, error_msg)."""
        if not expected_type:
            return value_str, None

        try:
            if expected_type == int and value_str:
                return int(value_str), None
            elif expected_type == float and value_str:
                return float(value_str), None
            elif expected_type == str:
                return value_str, None
            else:
                return value_str, None
        except (ValueError, TypeError):
            return (
                None,
                f"Invalid value for {field}: Cannot convert '{value_str}' to {expected_type.__name__}",
            )

    def _validate_field_value(self, field: str, processed_value: Any, validator) -> str:
        """Validate field value using validator function. Returns error message or None."""
        if not validator or processed_value is None:
            return None

        try:
            if not validator(processed_value):
                return f"Invalid value for {field}: Failed validation rule."
        except Exception as e:
            return f"Error during validation for {field}: {e}"

        return None

    def _should_include_field(
        self, field: str, processed_value: Any, is_required_field: bool, errors: list
    ) -> bool:
        """Determine if field should be included in validated data."""
        # Check if field caused an error
        field_has_error = any(field in error for error in errors)
        if field_has_error:
            return False

        # Only add if it has a value or is explicitly required
        return processed_value is not None or is_required_field

    def _process_single_field(self, field: str, value_str: str, config: tuple) -> tuple:
        """Process a single field through validation pipeline. Returns (processed_value, errors, parsed_num_students)."""
        is_required_field, expected_type, validator = config
        errors: list[str] = []
        parsed_num_students = None

        # Skip empty optional fields
        if not value_str and not is_required_field:
            return None, errors, parsed_num_students

        # Type conversion
        processed_value, conversion_error = self._convert_field_value(
            field, value_str, expected_type
        )
        if conversion_error:
            errors.append(conversion_error)
            return None, errors, parsed_num_students

        # Store num_students for cross-field validation
        if field == "num_students" and processed_value is not None:
            parsed_num_students = processed_value

        # Field validation
        validation_error = self._validate_field_value(field, processed_value, validator)
        if validation_error:
            errors.append(validation_error)

        return processed_value, errors, parsed_num_students

    def _parse_form_data(self, form_data: dict) -> tuple:
        """Parse form data into typed values. Returns (parsed_data, conversion_errors)."""
        parsed_data = {}
        conversion_errors = []
        raw_input_data = self._prepare_raw_input_data(form_data)

        for field, value_str in raw_input_data.items():
            if field in self.EXPECTED_FIELDS:
                config = self.EXPECTED_FIELDS[field]
                is_required_field, expected_type, _ = config

                # Skip empty optional fields
                if not value_str and not is_required_field:
                    continue

                # Convert field value
                processed_value, conversion_error = self._convert_field_value(
                    field, value_str, expected_type
                )
                if conversion_error:
                    conversion_errors.append(conversion_error)
                elif processed_value is not None:
                    parsed_data[field] = processed_value

        return parsed_data, conversion_errors

    def _validate_parsed_data(self, parsed_data: dict, raw_input_data: dict) -> list:
        """Validate parsed data against field rules."""
        errors = []

        for field, processed_value in parsed_data.items():
            if field in self.EXPECTED_FIELDS:
                config = self.EXPECTED_FIELDS[field]
                _, _, validator = config

                # Validate field value
                validation_error = self._validate_field_value(
                    field, processed_value, validator
                )
                if validation_error:
                    errors.append(validation_error)

        return errors

    def parse_and_validate(self, form_data: dict):
        """
        Parses and validates data from a form-like dictionary.
        Includes logic for grade distribution validation.

        Args:
            form_data: A dictionary containing input data (e.g., request.form).

        Returns:
            A dictionary containing the standardized, validated data on success.

        Raises:
            ValidationError: If validation fails (missing required field,
                bad type, invalid value).
        """
        # Check required fields first
        raw_input_data = self._prepare_raw_input_data(form_data)
        required_errors = self._check_required_fields(raw_input_data)
        if required_errors:
            raise ValidationError("; ".join(required_errors))

        # Parse form data into typed values
        parsed_data, conversion_errors = self._parse_form_data(form_data)

        # Check for conversion errors first
        if conversion_errors:
            raise ValidationError("; ".join(conversion_errors))

        # Validate the parsed data
        validation_errors = self._validate_parsed_data(parsed_data, raw_input_data)
        if validation_errors:
            raise ValidationError("; ".join(validation_errors))

        return parsed_data
