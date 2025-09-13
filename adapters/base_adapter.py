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
        validated_data = {}
        errors = []
        raw_input_data = {
            k: str(v).strip() for k, v in form_data.items()
        }  # Store stripped strings

        # --- Check for missing required fields ---
        for field, config in self.EXPECTED_FIELDS.items():
            is_required = config[0]
            # Check presence based on raw input
            if is_required and not raw_input_data.get(field):
                errors.append(f"Missing required field: {field}")

        # Grade distribution functionality removed per requirements
        # Grade distribution validation removed per requirements
        # This allows failing early if num_students is missing
        # AND grades were entered

        # Fail fast if required fields (including potentially num_students) are missing
        if errors:
            raise ValidationError("; ".join(errors))

        # --- Process fields (type conversion, validation) ---
        parsed_num_students = None

        for field, value_str in raw_input_data.items():
            if field in self.EXPECTED_FIELDS:
                config = self.EXPECTED_FIELDS[field]
                is_required_field = config[0]
                expected_type = config[1]
                validator = config[2]

                # Skip empty optional fields
                if not value_str and not is_required_field:
                    continue

                # Attempt type conversion
                processed_value: Any = None
                conversion_error = False
                if expected_type:
                    try:
                        if expected_type == int and value_str:
                            processed_value = int(value_str)
                        elif expected_type == float and value_str:
                            processed_value = float(value_str)
                        elif expected_type == str:
                            processed_value = value_str  # Already stripped
                        else:
                            # Handle case where field exists but type is
                            # None or unexpected
                            processed_value = (
                                value_str  # Pass as string if no type specified
                            )
                    except (ValueError, TypeError):
                        errors.append(
                            f"Invalid value for {field}: Cannot convert "
                            f"'{value_str}' to {expected_type.__name__}"
                        )
                        conversion_error = True
                else:  # No expected type defined, treat as string
                    processed_value = value_str

                if conversion_error:
                    continue  # Skip further validation on this field

                # Store successfully converted values needed for cross-field validation
                if field == "num_students" and processed_value is not None:
                    parsed_num_students = processed_value
                # Grade field handling removed per requirements

                # Run specific field validator if conversion succeeded
                # and validator exists
                if (
                    validator and processed_value is not None
                ):  # Check processed_value is not None
                    try:
                        if not validator(processed_value):
                            errors.append(
                                f"Invalid value for {field}: Failed validation rule."
                            )
                    except Exception as e:
                        errors.append(f"Error during validation for {field}: {e}")

                # Store the validated field if no errors occurred for it
                if field not in [
                    e.split(":")[0].split(" ")[-1] for e in errors
                ]:  # Check if field caused error
                    # Only add if it has a value or is explicitly required
                    # (avoids adding None for empty optional fields)
                    if processed_value is not None or is_required_field:
                        validated_data[field] = processed_value

        # --- Grade distribution validation removed per requirements ---

        # --- Final check for errors ---
        if errors:
            raise ValidationError("; ".join(errors))

        # Grade field processing removed per requirements

        return validated_data
