# adapters/base_adapter.py

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
        'course_title': (True, str, None),
        'course_number': (True, str, None),
        'semester': (True, str, None),
        'year': (True, int, lambda y: y >= 2000), # Example validator: year >= 2000
        'professor': (True, str, None),
        'num_students': (False, int, lambda n: n >= 0) # Optional, must be non-negative int if present
        # Add other standard fields here
    }

    def parse_and_validate(self, form_data: dict):
        """
        Parses and validates data from a form-like dictionary.

        Args:
            form_data: A dictionary containing input data (e.g., request.form).

        Returns:
            A dictionary containing the standardized, validated data on success.

        Raises:
            ValidationError: If validation fails (missing required field, bad type, invalid value).
        """
        validated_data = {}
        errors = []

        # --- Check for missing required fields --- 
        for field, config in self.EXPECTED_FIELDS.items():
            is_required = config[0]
            if is_required and field not in form_data:
                errors.append(f"Missing required field: {field}")
            elif is_required and not form_data.get(field, '').strip(): # Check if required field is present but empty/whitespace
                 errors.append(f"Missing required field: {field}")

        if errors: # Fail fast if required fields are missing
            raise ValidationError("; ".join(errors))

        # --- Process present fields (type conversion, validation) --- 
        for field, value in form_data.items():
            # Only process fields we expect, ignore others
            if field in self.EXPECTED_FIELDS:
                config = self.EXPECTED_FIELDS[field]
                expected_type = config[1]
                validator = config[2]
                
                original_value = value # Keep original for error messages if needed
                processed_value = str(original_value).strip() # Strip whitespace

                # Skip empty optional fields
                if not processed_value and not config[0]: # if empty string and not required
                    continue 
                
                # Attempt type conversion
                if expected_type:
                    try:
                        if expected_type == int and processed_value:
                            processed_value = int(processed_value)
                        elif expected_type == float and processed_value: # Example if needed later
                             processed_value = float(processed_value)
                        # Add other type conversions as needed (e.g., date, bool)
                        elif expected_type == str:
                            processed_value = str(processed_value) # Already stripped

                    except (ValueError, TypeError):
                        errors.append(f"Invalid value for {field}: Cannot convert '{original_value}' to {expected_type.__name__}")
                        continue # Skip further validation for this field if type conversion failed

                # Run custom validator if conversion succeeded and validator exists
                if validator:
                    try:
                        if not validator(processed_value):
                           errors.append(f"Invalid value for {field}: Failed validation rule.")
                    except Exception as e:
                         errors.append(f"Error during validation for {field}: {e}")
                         
                # If no errors for this field so far, add it to output
                if f"Invalid value for {field}" not in " ".join(errors) and f"Error during validation for {field}" not in " ".join(errors):
                     validated_data[field] = processed_value
            
        # --- Final check for errors accumulated during processing --- 
        if errors:
            raise ValidationError("; ".join(errors))
        
        return validated_data 