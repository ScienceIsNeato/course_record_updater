"""Unit tests for dashboard program metrics calculation."""

import pytest

from dashboard_service import DashboardService


class TestDashboardProgramMetrics:
    """Test program metrics calculation in isolation."""

    def test_build_program_metrics_with_courses_and_sections(self):
        """
        Test: _build_program_metrics correctly counts courses, faculty, sections per program

        This test validates that when a program has:
        - 2 courses
        - 2 sections (1 per course)
        - 1 instructor teaching both

        The metrics should show:
        - course_count: 2
        - section_count: 2
        - faculty_count: 1
        - student_count: sum of enrollments
        """
        service = DashboardService()

        # Setup: Program with ID
        programs = [
            {
                "program_id": "prog-cs",
                "id": "prog-cs",
                "name": "Computer Science",
                "short_name": "CS",
            }
        ]

        # Setup: 2 courses in CS program
        courses = [
            {
                "course_id": "cs-101",
                "id": "cs-101",
                "course_number": "CS-101",
                "course_title": "Intro to CS",
                "program_id": "prog-cs",
                "program_ids": ["prog-cs"],
            },
            {
                "course_id": "cs-201",
                "id": "cs-201",
                "course_number": "CS-201",
                "course_title": "Data Structures",
                "program_id": "prog-cs",
                "program_ids": ["prog-cs"],
            },
        ]

        # Setup: 2 sections (1 per course), same instructor
        sections = [
            {
                "section_id": "sec-101-001",
                "course_id": "cs-101",
                "section_number": "001",
                "instructor_id": "instr-1",
                "enrollment": 25,
            },
            {
                "section_id": "sec-201-001",
                "course_id": "cs-201",
                "section_number": "001",
                "instructor_id": "instr-1",
                "enrollment": 20,
            },
        ]

        # Setup: 1 faculty member
        faculty = [
            {
                "user_id": "instr-1",
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane@example.com",
            }
        ]

        # Execute
        metrics = service._build_program_metrics(programs, courses, sections, faculty)

        # Assert: Should get metrics for 1 program
        assert len(metrics) == 1, f"Expected 1 program metric, got {len(metrics)}"

        cs_metrics = metrics[0]
        print(f"\n🔍 CS Program Metrics:")
        print(f"  Program ID: {cs_metrics.get('program_id')}")
        print(f"  Program Name: {cs_metrics.get('program_name')}")
        print(f"  Course Count: {cs_metrics.get('course_count')}")
        print(f"  Section Count: {cs_metrics.get('section_count')}")
        print(f"  Faculty Count: {cs_metrics.get('faculty_count')}")
        print(f"  Student Count: {cs_metrics.get('student_count')}")

        # Assert: Counts should match what we set up
        assert cs_metrics["program_id"] == "prog-cs"
        assert cs_metrics["program_name"] == "Computer Science"
        assert (
            cs_metrics["course_count"] == 2
        ), f"Expected 2 courses, got {cs_metrics.get('course_count')}"
        assert (
            cs_metrics["section_count"] == 2
        ), f"Expected 2 sections, got {cs_metrics.get('section_count')}"
        assert (
            cs_metrics["faculty_count"] == 1
        ), f"Expected 1 faculty, got {cs_metrics.get('faculty_count')}"
        assert (
            cs_metrics["student_count"] == 45
        ), f"Expected 45 students (25+20), got {cs_metrics.get('student_count')}"
