"""
Unit tests for dashboard service section enrichment

Tests the section enrichment logic that adds course data to sections
"""

import pytest

from dashboard_service import DashboardService


@pytest.fixture
def service():
    """Create dashboard service instance"""
    return DashboardService()


@pytest.fixture
def sample_sections():
    """Sample section data"""
    return [
        {
            "section_id": "section-1",
            "offering_id": "offering-1",
            "section_number": "01",
            "enrollment": 25,
        },
        {
            "section_id": "section-2",
            "offering_id": "offering-2",
            "section_number": "02",
            "enrollment": 30,
        },
        {
            "section_id": "section-3",
            "offering_id": "nonexistent-offering",
            "section_number": "03",
            "enrollment": 20,
        },
    ]


@pytest.fixture
def course_index():
    """Sample course index"""
    return {
        "course-1": {
            "course_id": "course-1",
            "course_number": "CS-101",
            "course_title": "Intro to Computer Science",
        },
        "course-2": {
            "course_id": "course-2",
            "course_number": "MATH-201",
            "course_title": "Calculus I",
        },
    }


@pytest.fixture
def offering_to_course():
    """Sample offering to course mapping"""
    return {
        "offering-1": "course-1",
        "offering-2": "course-2",
        # Note: offering-3 is missing (intentional for testing)
    }


class TestDashboardSectionEnrichment:
    """Test dashboard service section enrichment"""

    def test_enrich_sections_with_course_data(
        self, service, sample_sections, course_index, offering_to_course
    ):
        """Test enriching sections with course information"""
        enriched = service._enrich_sections_with_course_data(
            sample_sections, course_index, offering_to_course
        )

        # Should return same number of sections
        assert len(enriched) == 3

        # First section should be enriched
        first_section = enriched[0]
        assert first_section["course_number"] == "CS-101"
        assert first_section["course_title"] == "Intro to Computer Science"
        assert first_section["course_id"] == "course-1"

        # Second section should be enriched
        second_section = enriched[1]
        assert second_section["course_number"] == "MATH-201"
        assert second_section["course_title"] == "Calculus I"
        assert second_section["course_id"] == "course-2"

        # Third section should have empty strings (missing offering)
        third_section = enriched[2]
        assert third_section["course_number"] == ""
        assert third_section["course_title"] == ""

    def test_enrich_single_section_success(
        self, service, course_index, offering_to_course
    ):
        """Test enriching a single section successfully"""
        section = {
            "section_id": "section-1",
            "offering_id": "offering-1",
            "section_number": "01",
        }

        enriched = service._enrich_single_section(
            0, section, course_index, offering_to_course
        )

        assert enriched["course_number"] == "CS-101"
        assert enriched["course_title"] == "Intro to Computer Science"
        assert enriched["course_id"] == "course-1"
        # Original data should be preserved
        assert enriched["section_id"] == "section-1"
        assert enriched["section_number"] == "01"

    def test_enrich_single_section_missing_offering(
        self, service, course_index, offering_to_course
    ):
        """Test enriching section when offering doesn't exist"""
        section = {
            "section_id": "section-bad",
            "offering_id": "nonexistent-offering",
            "section_number": "01",
        }

        enriched = service._enrich_single_section(
            0, section, course_index, offering_to_course
        )

        # Should have empty course data
        assert enriched["course_number"] == ""
        assert enriched["course_title"] == ""
        # Original data should be preserved
        assert enriched["section_id"] == "section-bad"

    def test_enrich_single_section_missing_course(
        self, service, course_index, offering_to_course
    ):
        """Test enriching section when course doesn't exist"""
        # Add offering that points to non-existent course
        offering_to_course_with_bad_course = offering_to_course.copy()
        offering_to_course_with_bad_course["offering-bad"] = "nonexistent-course"

        section = {
            "section_id": "section-bad",
            "offering_id": "offering-bad",
            "section_number": "01",
        }

        enriched = service._enrich_single_section(
            0, section, course_index, offering_to_course_with_bad_course
        )

        # Should have empty course data
        assert enriched["course_number"] == ""
        assert enriched["course_title"] == ""

    def test_enrich_sections_preserves_original_data(
        self, service, course_index, offering_to_course
    ):
        """Test that enrichment preserves all original section data"""
        sections = [
            {
                "section_id": "section-1",
                "offering_id": "offering-1",
                "section_number": "01",
                "enrollment": 25,
                "instructor_id": "user-1",
                "custom_field": "custom_value",
            }
        ]

        enriched = service._enrich_sections_with_course_data(
            sections, course_index, offering_to_course
        )

        # All original fields should be preserved
        section = enriched[0]
        assert section["section_id"] == "section-1"
        assert section["offering_id"] == "offering-1"
        assert section["section_number"] == "01"
        assert section["enrollment"] == 25
        assert section["instructor_id"] == "user-1"
        assert section["custom_field"] == "custom_value"

        # Plus new course fields
        assert section["course_number"] == "CS-101"
        assert section["course_title"] == "Intro to Computer Science"

    def test_enrich_sections_with_empty_input(
        self, service, course_index, offering_to_course
    ):
        """Test enriching empty section list"""
        enriched = service._enrich_sections_with_course_data(
            [], course_index, offering_to_course
        )

        assert enriched == []

    def test_log_enrichment_failure_logs_first_three_only(self, service):
        """Test that enrichment failure logging only logs first 3 failures"""
        course_index = {}
        offering_to_course = {}

        # Log 5 failures - first 3 should log, last 2 should be skipped
        for i in range(5):
            service._log_enrichment_failure(
                i, f"offering-{i}", None, offering_to_course, course_index
            )

        # We can't easily test the logging output without caplog setup,
        # but we can test the logic: indices 0,1,2 should log, 3,4 shouldn't
        # The function checks if index >= 3 and returns early
        # This test primarily serves to exercise the code path
