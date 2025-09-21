"""Unit tests for dashboard_service."""

from datetime import datetime
from unittest.mock import patch

import pytest

from dashboard_service import DashboardService, DashboardServiceError


@pytest.fixture
def service():
    return DashboardService()


class TestDashboardServiceSiteAdmin:
    @patch("dashboard_service.get_all_instructors")
    @patch("dashboard_service.get_all_users")
    @patch("dashboard_service.get_all_courses")
    @patch("dashboard_service.get_programs_by_institution")
    @patch("dashboard_service.get_active_terms")
    @patch("dashboard_service.get_all_sections")
    @patch("dashboard_service.get_all_institutions")
    def test_site_admin_aggregation(
        self,
        mock_institutions,
        mock_sections,
        mock_terms,
        mock_programs,
        mock_courses,
        mock_users,
        mock_instructors,
        service,
    ):
        mock_institutions.return_value = [
            {"institution_id": "inst-1", "name": "One"},
            {"institution_id": "inst-2", "name": "Two"},
        ]
        mock_programs.side_effect = [[{"id": "prog-1", "name": "Prog 1"}], []]
        mock_courses.side_effect = [[{"course_id": "c1"}], [{"course_id": "c2"}]]
        mock_users.side_effect = [[{"user_id": "u1", "role": "site_admin"}], []]
        mock_instructors.side_effect = [[{"user_id": "u1"}], []]
        mock_sections.side_effect = [[{"section_id": "s1"}], []]
        mock_terms.side_effect = [[{"term_id": "t1"}], []]

        data = service.get_dashboard_data({"role": "site_admin"})

        assert data["summary"]["institutions"] == 2
        assert data["summary"]["programs"] == 1
        assert data["summary"]["courses"] == 2
        assert data["summary"]["users"] == 1
        assert data["summary"]["faculty"] == 1
        assert data["metadata"]["data_scope"] == "system_wide"
        assert len(data["institutions"]) == 2
        assert data["institutions"][0]["name"] == "One"
        assert any(course["institution_id"] == "inst-2" for course in data["courses"])
        assert "activity" in data and len(data["activity"]) > 0
        assert "terms" in data and len(data["terms"]) == 1


class TestDashboardServiceScoped:
    @patch("dashboard_service.get_institution_by_id")
    @patch("dashboard_service.get_all_users")
    @patch("dashboard_service.get_all_courses")
    @patch("dashboard_service.get_programs_by_institution")
    @patch("dashboard_service.get_active_terms")
    @patch("dashboard_service.get_all_instructors")
    @patch("dashboard_service.get_all_sections")
    def test_institution_admin_scope(
        self,
        mock_sections,
        mock_instructors,
        mock_terms,
        mock_programs,
        mock_courses,
        mock_users,
        mock_institution,
        service,
    ):
        mock_programs.return_value = [{"id": "prog-1"}]
        mock_courses.return_value = [
            {"course_id": "course-1", "program_ids": ["prog-1"]}
        ]
        mock_users.return_value = [
            {
                "user_id": "u1",
                "role": "instructor",
                "first_name": "Ada",
                "last_name": "Lovelace",
                "program_ids": ["prog-1"],
            }
        ]
        mock_instructors.return_value = [
            {"user_id": "u1", "first_name": "Grace", "program_ids": ["prog-1"]}
        ]
        mock_sections.return_value = [
            {
                "section_id": "s1",
                "course_id": "course-1",
                "instructor_id": "u1",
                "enrollment": 10,
            }
        ]
        mock_terms.return_value = [
            {"term_id": "t1", "name": "Fall 2024", "active": True}
        ]
        mock_institution.return_value = {"institution_id": "inst-1", "name": "Inst One"}

        data = service.get_dashboard_data(
            {"role": "institution_admin", "institution_id": "inst-1"}
        )

        assert data["metadata"]["data_scope"] == "institution"
        assert data["summary"]["programs"] == 1
        assert data["programs"][0]["institution_id"] == "inst-1"
        assert data["summary"]["faculty"] == 1
        assert data["institutions"][0]["name"] == "Inst One"
        assert data["program_overview"]
        assert data["faculty"][0]["user_id"] == "u1"

    @patch("dashboard_service.get_all_instructors")
    @patch("dashboard_service.get_all_sections")
    @patch("dashboard_service.get_courses_by_program")
    @patch("dashboard_service.get_programs_by_institution")
    @patch("dashboard_service.get_all_users")
    @patch("dashboard_service.get_active_terms")
    def test_program_admin_scope(
        self,
        mock_terms,
        mock_users,
        mock_programs,
        mock_courses,
        mock_sections,
        mock_instructors,
        service,
    ):
        mock_programs.return_value = [
            {"id": "prog-1", "name": "Program 1"},
            {"id": "prog-2", "name": "Program 2"},
        ]
        mock_courses.side_effect = [[{"course_id": "c1", "course_number": "CS-101"}]]
        mock_sections.return_value = [
            {
                "section_id": "s1",
                "course_id": "c1",
                "instructor_id": "u1",
                "enrollment": 20,
            }
        ]
        mock_instructors.return_value = [
            {
                "user_id": "u1",
                "full_name": "Prof",
                "program_ids": ["prog-1"],
            }
        ]
        mock_users.return_value = [
            {
                "user_id": "u1",
                "role": "program_admin",
                "program_ids": ["prog-1"],
            }
        ]
        mock_terms.return_value = [{"term_id": "t1"}]

        data = service.get_dashboard_data(
            {
                "role": "program_admin",
                "institution_id": "inst-1",
                "program_ids": ["prog-1"],
            }
        )

        assert data["metadata"]["data_scope"] == "program"
        assert len(data["programs"]) == 1
        assert data["courses"][0]["program_id"] == "prog-1"
        assert data["program_overview"][0]["program_id"] == "prog-1"
        assert data["sections"][0]["course_id"] == "c1"
        assert data["instructors"][0]["user_id"] == "u1"

    @patch("dashboard_service.get_programs_by_institution")
    @patch("dashboard_service.get_all_courses")
    @patch("dashboard_service.get_active_terms")
    @patch("dashboard_service.get_all_sections")
    def test_instructor_scope(
        self,
        mock_sections,
        mock_terms,
        mock_courses,
        mock_programs,
        service,
    ):
        mock_sections.return_value = [
            {
                "section_id": "s1",
                "instructor_id": "u-instructor",
                "course_id": "c1",
                "status": "completed",
                "enrollment": 15,
            },
            {
                "section_id": "s2",
                "instructor_id": "someone-else",
                "course_id": "c2",
            },
        ]
        mock_courses.return_value = [
            {
                "course_id": "c1",
                "course_number": "CS-101",
                "course_title": "Intro",
                "program_ids": ["prog-1"],
            }
        ]
        mock_programs.return_value = [{"id": "prog-1", "name": "Program 1"}]
        mock_terms.return_value = [{"term_id": "t1"}]

        data = service.get_dashboard_data(
            {
                "role": "instructor",
                "institution_id": "inst-1",
                "user_id": "u-instructor",
                "program_ids": ["prog-1"],
            }
        )

        assert data["metadata"]["data_scope"] == "instructor"
        assert len(data["sections"]) == 1
        assert data["sections"][0]["institution_id"] == "inst-1"


class TestDashboardServiceCLOEnrichment:
    """Test CLO data enrichment functionality."""

    @patch("dashboard_service.get_course_outcomes")
    def test_enrich_courses_with_clo_data_success(self, mock_get_clos, service):
        """Test successful CLO data enrichment."""
        # Mock CLO data
        mock_clos = [
            {"clo_number": "CLO1", "description": "First learning outcome"},
            {"clo_number": "CLO2", "description": "Second learning outcome"},
        ]
        mock_get_clos.return_value = mock_clos

        courses = [
            {"course_id": "course-1", "course_number": "CS-101"},
            {"id": "course-2", "course_number": "CS-201"},  # Test fallback to "id"
        ]

        result = service._enrich_courses_with_clo_data(courses)

        assert len(result) == 2
        assert result[0]["clo_count"] == 2
        assert result[0]["clos"] == mock_clos
        assert result[1]["clo_count"] == 2
        assert result[1]["clos"] == mock_clos

        # Verify get_course_outcomes was called for each course
        assert mock_get_clos.call_count == 2
        mock_get_clos.assert_any_call("course-1")
        mock_get_clos.assert_any_call("course-2")

    @patch("dashboard_service.get_course_outcomes")
    def test_enrich_courses_with_clo_data_no_clos(self, mock_get_clos, service):
        """Test CLO enrichment when no CLOs exist."""
        mock_get_clos.return_value = []

        courses = [{"course_id": "course-1", "course_number": "CS-101"}]
        result = service._enrich_courses_with_clo_data(courses)

        assert result[0]["clo_count"] == 0
        assert result[0]["clos"] == []

    @patch("dashboard_service.get_course_outcomes")
    def test_enrich_courses_with_clo_data_error_handling(self, mock_get_clos, service):
        """Test CLO enrichment handles errors gracefully."""
        mock_get_clos.side_effect = Exception("Database error")

        courses = [{"course_id": "course-1", "course_number": "CS-101"}]
        result = service._enrich_courses_with_clo_data(courses)

        assert result[0]["clo_count"] == 0
        assert result[0]["clos"] == []

    def test_enrich_courses_with_clo_data_no_course_id(self, service):
        """Test CLO enrichment when course has no ID."""
        courses = [{"course_number": "CS-101"}]  # No course_id or id field
        result = service._enrich_courses_with_clo_data(courses)

        assert result[0]["clo_count"] == 0
        assert result[0]["clos"] == []


class TestDashboardServiceFailures:
    def test_missing_user(self, service):
        with pytest.raises(DashboardServiceError):
            service.get_dashboard_data(None)

    def test_missing_institution_for_admin(self, service):
        with pytest.raises(DashboardServiceError):
            service.get_dashboard_data({"role": "institution_admin"})


class TestDashboardServiceHelpers:
    """Test helper methods in DashboardService"""

    def test_get_course_id_with_course_id_field(self, service):
        """Test _get_course_id with course_id field"""
        course = {"course_id": "course-123", "name": "Test Course"}
        result = service._get_course_id(course)
        assert result == "course-123"

    def test_get_course_id_with_id_field(self, service):
        """Test _get_course_id with id field"""
        course = {"id": "course-456", "name": "Test Course"}
        result = service._get_course_id(course)
        assert result == "course-456"

    def test_get_course_id_prefers_id_over_course_id(self, service):
        """Test _get_course_id prefers id field when both exist"""
        course = {"id": "course-789", "course_id": "course-123", "name": "Test Course"}
        result = service._get_course_id(course)
        assert result == "course-789"

    def test_get_course_id_with_none_course(self, service):
        """Test _get_course_id with None course"""
        result = service._get_course_id(None)
        assert result is None

    def test_get_course_id_with_empty_course(self, service):
        """Test _get_course_id with course missing both id fields"""
        course = {"name": "Test Course"}
        result = service._get_course_id(course)
        assert result is None
