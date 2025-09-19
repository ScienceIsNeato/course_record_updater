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
                "accessible_programs": ["prog-1"],
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
        assert len(data["courses"]) == 1
        assert data["courses"][0]["course_id"] == "c1"
        assert data["teaching_assignments"][0]["course_id"] == "c1"
        assert len(data["assessment_tasks"]) == 1
        assert data["programs"]
        assert data["summary"]["sections"] == 1


class TestDashboardServiceFailures:
    def test_missing_user(self, service):
        with pytest.raises(DashboardServiceError):
            service.get_dashboard_data(None)

    def test_missing_institution_for_admin(self, service):
        with pytest.raises(DashboardServiceError):
            service.get_dashboard_data({"role": "institution_admin"})
