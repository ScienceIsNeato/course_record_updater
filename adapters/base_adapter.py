# adapters/base_adapter.py

from term_utils import get_allowed_terms, is_valid_term


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
        ),  # Now potentially required by grades
        # Optional Grades - Must be non-negative int if present
        "grade_a": (False, int, lambda g: g >= 0),
        "grade_b": (False, int, lambda g: g >= 0),
        "grade_c": (False, int, lambda g: g >= 0),
        "grade_d": (False, int, lambda g: g >= 0),
        "grade_f": (False, int, lambda g: g >= 0),
    }

    GRADE_FIELDS = ["grade_a", "grade_b", "grade_c", "grade_d", "grade_f"]

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

        # --- Grade Distribution Pre-check ---
        # Check if any grade field has a non-empty value
        any_grade_entered = any(
            raw_input_data.get(g_field) for g_field in self.GRADE_FIELDS
        )
        num_students_raw = raw_input_data.get("num_students")

        if any_grade_entered and not num_students_raw:
            errors.append(
                "Number of students is required when entering grade distribution."
            )
            # Mark num_students as effectively required for subsequent checks if needed
            # This allows failing early if num_students is missing
            # AND grades were entered

        # Fail fast if required fields (including potentially num_students) are missing
        if errors:
            raise ValidationError("; ".join(errors))

        # --- Process fields (type conversion, validation) ---
        grade_values = {}
        parsed_num_students = None

        for field, value_str in raw_input_data.items():
            if field in self.EXPECTED_FIELDS:
                config = self.EXPECTED_FIELDS[field]
                is_required_field = config[0]
                expected_type = config[1]
                validator = config[2]

                # Skip empty optional fields (unless it's num_students
                # and grades were entered)
                is_num_students_and_grades_entered = (
                    field == "num_students" and any_grade_entered
                )
                if (
                    not value_str
                    and not is_required_field
                    and not is_num_students_and_grades_entered
                ):
                    continue

                # Attempt type conversion
                processed_value = None
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
                elif field in self.GRADE_FIELDS and processed_value is not None:
                    grade_values[field] = processed_value

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

        # --- Cross-Field Validation (Grade Distribution Sum) ---
        if any_grade_entered:
            # Ensure num_students was successfully parsed if grades were entered
            if (
                parsed_num_students is None
                and "Number of students is required" not in "; ".join(errors)
            ):
                # This implies num_students was provided but failed
                # type conversion/validation
                # The specific error should already be in the errors list
                pass  # Error already captured
            elif parsed_num_students is not None:
                # Sum only the grades that were actually entered and parsed correctly
                current_grade_sum = sum(grade_values.values())
                if current_grade_sum != parsed_num_students:
                    errors.append(
                        f"Sum of grades ({current_grade_sum}) does not match "
                        f"Number of Students ({parsed_num_students})."
                    )

        # --- Final check for errors ---
        if errors:
            raise ValidationError("; ".join(errors))

        # Remove grade fields if none were entered (all were empty/optional)
        if not any_grade_entered:
            for g_field in self.GRADE_FIELDS:
                validated_data.pop(g_field, None)

        return validated_data
