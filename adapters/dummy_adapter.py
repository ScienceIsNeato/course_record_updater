# adapters/dummy_adapter.py
import docx

def parse(document: docx.document.Document):
    """
    Parses the given Word document object using dummy logic.
    Returns data as strings, simulating raw parsing before validation/conversion.

    Args:
        document: A python-docx Document object (not actually used by dummy).

    Returns:
        A dictionary containing the extracted course data as strings.
    """
    print(f"Using dummy_adapter to parse document.")

    # --- Dummy Logic Start ---
    # Return *all* fields expected by BaseAdapter, as strings
    extracted_data = {
        'course_title': 'Dummy Course Title',
        'course_number': 'DUMMY101',
        'semester': 'Dummy Semester',
        'year': '2024', # String
        'professor': 'Dr. Dummy',
        'num_students': '42' # String, optional field
        # Add other fields as strings if defined in BaseAdapter.EXPECTED_FIELDS
    }
    # --- Dummy Logic End ---

    return extracted_data 