import os
import sys
import unittest
from unittest.mock import patch

# Add src to path
sys.path.append(os.getcwd())

from src.models.models_sql import CourseOutcome, CourseSectionOutcome, to_dict
from src.services.clo_workflow_service import CLOWorkflowService


class TestCLOServiceLogic(unittest.TestCase):
    @patch("src.services.clo_workflow_service.db")
    def test_to_dict_real_model(self, mock_db):
        # Create a real model instance
        outcome = CourseSectionOutcome()
        outcome.id = "test-id"
        outcome.section_id = "sec-id"
        outcome.outcome_id = "tmpl-id"
        outcome.status = "unassigned"

        # Test to_dict directly
        d = to_dict(outcome)
        print("\nto_dict keys:", list(d.keys()))

        # Assertions
        self.assertIn("id", d)
        self.assertIn("section_id", d)

    @patch("src.services.clo_workflow_service.db")
    def test_section_id_retention(self, mock_db):
        # Setup mock behavior with a DICT (simulating what db returns)
        outcome_id = "test-outcome-id"
        section_id = "original-section-id"

        # db.get_section_outcome returns a dict WITH section_id
        mock_db.get_section_outcome.return_value = {
            "id": outcome_id,
            "section_id": section_id,
            "outcome_id": "template-id",
            "course_id": "course-id",
            "status": "unassigned",
        }

        # db.get_course returns course
        mock_db.get_course.return_value = {
            "course_number": "CS101",
            "course_title": "Intro",
        }
        mock_db.get_section_by_id.return_value = None
        mock_db.get_sections_by_course.return_value = []

        # Call the method
        result = CLOWorkflowService.get_outcome_with_details(outcome_id)

        print("\nResult section_id:", result.get("section_id"))

        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result.get("section_id"), section_id)


if __name__ == "__main__":
    unittest.main()
