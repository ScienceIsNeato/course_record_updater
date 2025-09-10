from docx import Document

# Mapping from keywords in the docx to the standard field names
KEYWORD_MAP = {
    "Number": "course_number",
    "Title": "course_title",
    "Instructor": "instructor_name",
    "Term": "term",
    "Student Count": "num_students",
    "Grades": "grades_str",  # Special handling needed for grades
}

# Grade parsing keywords
GRADE_KEYS = {
    "A": "grade_a",
    "B": "grade_b",
    "C": "grade_c",
    "D": "grade_d",
    "F": "grade_f",
}


class BusinessSampleAdapter:
    # Class attribute to provide a display name for the UI
    display_name = "Business Format Sample"

    def parse(self, document: Document):
        """
        Parses course data from a .docx file with text blocks.
        Assumes each course starts after a 'COURSE DATA' heading or paragraph
        and fields are identified by keywords.
        """
        all_courses_data = []
        current_course = {}
        capture_mode = False

        for para in document.paragraphs:
            text = para.text.strip()
            if not text:
                continue  # Skip empty paragraphs

            # Check if it's the start of a new course block
            # Using style check might be more robust if available
            if text == "COURSE DATA":
                # If we were capturing a previous course, save it
                if current_course:
                    # Process collected grades string before saving
                    self._parse_grades_string(current_course)
                    all_courses_data.append(current_course)
                # Start a new course
                current_course = {}
                capture_mode = True  # Should we check for style instead?
                continue  # Skip the heading itself

            if capture_mode:
                # Attempt to parse keyword: value format
                parts = text.split(":", 1)
                if len(parts) == 2:
                    keyword = parts[0].strip()
                    value = parts[1].strip()

                    if keyword in KEYWORD_MAP:
                        field_name = KEYWORD_MAP[keyword]
                        current_course[field_name] = value
                    else:
                        print(
                            f"Warning: Unrecognized keyword '{keyword}' in business doc"
                        )
                elif (
                    text == "---"
                ):  # Separator marks end of block data (or start of next header)
                    pass  # Data already captured, wait for next COURSE DATA or end of doc
                    # If separator definitively marks the end, could save here

        # Save the last captured course after the loop ends
        if current_course:
            self._parse_grades_string(current_course)
            all_courses_data.append(current_course)

        return all_courses_data

    def _parse_grades_string(self, course_data):
        """
        Parses the 'grades_str' field (e.g., "A=5, B=15, C=8, D=1, F=1" or "N/A")
        and adds individual grade fields (grade_a, grade_b, etc.) to the dict.
        Removes the original 'grades_str'.
        """
        grades_str = course_data.pop("grades_str", None)
        if not grades_str or grades_str.upper() == "N/A":
            return  # No grades to parse

        try:
            grade_pairs = grades_str.split(",")
            for pair in grade_pairs:
                parts = pair.split("=")
                if len(parts) == 2:
                    grade_letter = parts[0].strip().upper()
                    grade_count = parts[1].strip()
                    if grade_letter in GRADE_KEYS:
                        field_name = GRADE_KEYS[grade_letter]
                        # Keep as string, base adapter handles conversion/validation
                        course_data[field_name] = grade_count
                    else:
                        print(f"Warning: Unrecognized grade letter '{grade_letter}'")
        except Exception as e:
            print(f"Warning: Failed to parse grades string '{grades_str}': {e}")
            # Optionally add an error indicator to the course_data?
            pass
