"""
Unit tests for CEI Excel adapter export builder methods

Tests the refactored export record building methods:
- _build_records_from_sections
- _build_records_from_offerings
- _build_synthesized_records
"""

import pytest

from src.adapters.cei_excel_adapter import CEIExcelAdapter


@pytest.fixture
def adapter():
    """Create CEI Excel adapter instance"""
    return CEIExcelAdapter()


@pytest.fixture
def sample_courses():
    """Sample course data"""
    return [
        {
            "course_id": "course-1",
            "id": "course-1",
            "course_number": "CS-101",
            "course_title": "Intro to Computer Science",
        },
        {
            "course_id": "course-2",
            "id": "course-2",
            "course_number": "MATH-201",
            "course_title": "Calculus I",
        },
    ]


@pytest.fixture
def sample_users():
    """Sample user data"""
    return [
        {
            "user_id": "user-1",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "role": "instructor",
        },
        {
            "user_id": "user-2",
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@example.com",
            "role": "instructor",
        },
    ]


@pytest.fixture
def sample_terms():
    """Sample term data"""
    return [
        {"term_id": "term-1", "term_code": "FA2024", "term_name": "Fall 2024"},
        {"term_id": "term-2", "term_code": "SP2025", "term_name": "Spring 2025"},
    ]


@pytest.fixture
def sample_offerings():
    """Sample course offering data"""
    return [
        {
            "offering_id": "offering-1",
            "id": "offering-1",
            "course_id": "course-1",
            "term_id": "term-1",
            "section_number": "01",
        },
        {
            "offering_id": "offering-2",
            "id": "offering-2",
            "course_id": "course-2",
            "term_id": "term-1",
            "section_number": "01",
        },
    ]


@pytest.fixture
def sample_sections():
    """Sample section data"""
    return [
        {
            "section_id": "section-1",
            "offering_id": "offering-1",
            "section_number": "01",
            "instructor_id": "user-1",
            "enrollment": 25,
        },
        {
            "section_id": "section-2",
            "offering_id": "offering-2",
            "section_number": "01",
            "instructor_id": "user-2",
            "enrollment": 30,
        },
    ]


class TestCEIAdapterExportBuilders:
    """Test CEI adapter export builder methods"""

    def test_build_records_from_sections(
        self,
        adapter,
        sample_courses,
        sample_users,
        sample_terms,
        sample_offerings,
        sample_sections,
    ):
        """Test building export records from sections (preferred path)"""
        data = {
            "courses": sample_courses,
            "users": sample_users,
            "terms": sample_terms,
            "offerings": sample_offerings,
            "sections": sample_sections,
        }

        records = adapter._build_records_from_sections(data)

        # Should return records for each section
        assert len(records) == 2

        # Verify record structure
        first_record = records[0]
        assert "course" in first_record
        assert "section" in first_record
        assert "effterm_c" in first_record
        assert "students" in first_record
        assert "Faculty Name" in first_record
        assert "email" in first_record

        # Verify data correctness
        assert first_record["course"] == "CS-101"
        assert first_record["section"] == "01"
        assert first_record["students"] == 25
        assert "John" in first_record["Faculty Name"]
        assert "Doe" in first_record["Faculty Name"]

    def test_build_records_from_sections_handles_missing_offering(
        self, adapter, sample_courses, sample_users, sample_terms, sample_offerings
    ):
        """Test that sections with missing offerings are skipped"""
        sections_with_bad_offering = [
            {
                "section_id": "section-bad",
                "offering_id": "nonexistent-offering",
                "section_number": "01",
                "instructor_id": "user-1",
                "enrollment": 25,
            }
        ]

        data = {
            "courses": sample_courses,
            "users": sample_users,
            "terms": sample_terms,
            "offerings": sample_offerings,
            "sections": sections_with_bad_offering,
        }

        records = adapter._build_records_from_sections(data)

        # Should skip section with missing offering
        assert len(records) == 0

    def test_build_records_from_offerings(
        self, adapter, sample_courses, sample_users, sample_terms
    ):
        """Test building export records from offerings (fallback path)"""
        offerings = [
            {
                "offering_id": "offering-1",
                "course_number": "CS-101",
                "term_id": "term-1",
                "instructor_id": "user-1",
                "section_number": "01",
                "enrollment_count": 25,
            }
        ]

        data = {
            "courses": sample_courses,
            "users": sample_users,
            "terms": sample_terms,
            "offerings": offerings,
        }

        records = adapter._build_records_from_offerings(data)

        # Should return records for each offering
        assert len(records) == 1

        # Verify record structure
        record = records[0]
        assert record["course"] == "CS-101"
        assert record["section"] == "01"
        assert record["students"] == 25
        assert "John" in record["Faculty Name"]

    def test_build_synthesized_records(
        self, adapter, sample_courses, sample_users, sample_terms
    ):
        """Test building synthesized export records (last resort)"""
        data = {
            "courses": sample_courses,
            "users": sample_users,
            "terms": sample_terms,
        }

        records = adapter._build_synthesized_records(data)

        # Should create records for each course-instructor combination
        # 2 courses × 2 instructors = 4 records
        assert len(records) == 4

        # Verify record structure
        record = records[0]
        assert "course" in record
        assert "section" in record
        assert "effterm_c" in record
        assert "students" in record
        assert "Faculty Name" in record

        # Verify defaults
        assert record["section"] == "01"  # Default section
        assert record["students"] == 25  # Default enrollment

    def test_build_synthesized_records_with_empty_terms(
        self, adapter, sample_courses, sample_users
    ):
        """Test synthesized records with no terms available"""
        data = {
            "courses": sample_courses,
            "users": sample_users,
            "terms": [],  # No terms
        }

        records = adapter._build_synthesized_records(data)

        # Should still create records
        assert len(records) == 4

        # Term should be empty or default
        record = records[0]
        assert "effterm_c" in record

    def test_build_cei_export_records_delegates_correctly(
        self,
        adapter,
        sample_courses,
        sample_users,
        sample_terms,
        sample_offerings,
        sample_sections,
    ):
        """Test that main method delegates to correct builder"""
        # Test sections path
        data_with_sections = {
            "courses": sample_courses,
            "users": sample_users,
            "terms": sample_terms,
            "offerings": sample_offerings,
            "sections": sample_sections,
        }

        records = adapter._build_cei_export_records(data_with_sections, {})
        assert len(records) == 2  # Should use sections builder

        # Test offerings path
        data_with_offerings = {
            "courses": sample_courses,
            "users": sample_users,
            "terms": sample_terms,
            "offerings": [
                {
                    "offering_id": "off-1",
                    "course_number": "CS-101",
                    "term_id": "term-1",
                    "instructor_id": "user-1",
                    "section_number": "01",
                    "enrollment_count": 25,
                }
            ],
            "sections": [],  # Empty sections
        }

        records = adapter._build_cei_export_records(data_with_offerings, {})
        assert len(records) == 1  # Should use offerings builder

        # Test synthesis path
        data_minimal = {
            "courses": sample_courses,
            "users": sample_users,
            "terms": sample_terms,
            "offerings": [],
            "sections": [],
        }

        records = adapter._build_cei_export_records(data_minimal, {})
        assert len(records) == 4  # Should use synthesis builder
