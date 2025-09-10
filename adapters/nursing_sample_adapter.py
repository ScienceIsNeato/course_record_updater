# adapters/nursing_sample_adapter.py
from docx import Document


class NursingSampleAdapter:
    # Class attribute to provide a display name for the UI
    display_name = "Nursing Format Sample"

    # Map header names (lowercase, stripped) to standard field names
    HEADER_MAP = {
        "course number": "course_number",
        "title": "course_title",
        "instructor": "instructor_name",
        "term": "term",
        "students": "num_students",
        "grade a": "grade_a",
        "grade b": "grade_b",
        "grade c": "grade_c",
        "grade d": "grade_d",
        "grade f": "grade_f",
    }

    def parse(self, document: Document):
        """
        Parses course data from a .docx file containing a table.
        Assumes the first table contains the course data with a header row.
        """
        all_courses_data = []
        if not document.tables:
            print("Warning: No tables found in nursing doc")
            return all_courses_data

        # Assume the first table is the one we want
        table = document.tables[0]

        if not table.rows:
            print("Warning: Table found but has no rows")
            return all_courses_data

        # Extract headers and map to indices
        headers = [cell.text.strip().lower() for cell in table.rows[0].cells]
        num_headers = len(headers)  # Store header count
        field_indices = {}
        for i, header in enumerate(headers):
            if header in self.HEADER_MAP:
                field_indices[self.HEADER_MAP[header]] = i
            else:
                print(f"Warning: Unrecognized header '{header}' in nursing doc table")

        # Check if essential headers are missing (optional but good practice)
        # required_headers = ["course_number", "course_title", ...]
        # if not all(h in field_indices for h in required_headers):
        #     print("Error: Missing one or more required headers in table")
        #     return [] # Or raise an error

        # Process data rows (skip header row at index 0)
        for i, row in enumerate(table.rows):
            if i == 0:
                continue  # Skip header

            course_data = {}
            cells = row.cells
            # Check if row has enough cells using the count of headers found
            if len(cells) < num_headers:
                print(
                    f"Warning: Row {i+1} has {len(cells)} cells, expected {num_headers}. Skipping."
                )
                continue

            for field_name, index in field_indices.items():
                # Get text, stripping whitespace
                value = cells[index].text.strip()
                # Store even if empty, BaseAdapter handles validation/optionality
                course_data[field_name] = value

            # Only add if the row seemed to contain some data (e.g., course_number)
            if course_data.get("course_number"):
                all_courses_data.append(course_data)
            else:
                print(
                    f"Warning: Skipping row {i+1} as it seems empty (no course number)."
                )

        return all_courses_data
