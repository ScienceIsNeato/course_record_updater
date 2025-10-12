"""Integration test for dashboard program metrics with real DB."""

import pytest

import database_service
from dashboard_service import DashboardService


@pytest.mark.integration
def test_institution_admin_dashboard_program_metrics_from_db():
    """
    Integration Test: Institution Admin Dashboard Returns Program Metrics from DB

    This test validates the full chain:
    1. Create institution, programs, courses, sections in DB
    2. Call DashboardService.get_dashboard_data()
    3. Verify program_overview contains non-zero metrics

    Bug reproduction: Program metrics show 0 for courses/faculty/sections
    even though data exists in DB.
    """
    # Setup: Create test data
    inst_id = database_service.create_institution(
        {
            "name": "Test University",
            "short_name": "TU",
            "admin_email": "admin@test.edu",
            "created_by": "test",
        }
    )

    # Create CS program
    cs_program_id = database_service.create_program(
        {
            "name": "Computer Science",
            "short_name": "CS",
            "institution_id": inst_id,
        }
    )

    # Create courses WITH program_id
    cs101_id = database_service.create_course(
        {
            "course_number": "CS-101",
            "course_title": "Intro to CS",
            "institution_id": inst_id,
            "program_id": cs_program_id,  # Single program_id
            "credits": 3,
        }
    )

    cs201_id = database_service.create_course(
        {
            "course_number": "CS-201",
            "course_title": "Data Structures",
            "institution_id": inst_id,
            "program_id": cs_program_id,
            "credits": 4,
        }
    )

    # Create instructor
    instructor_id = database_service.create_user(
        {
            "email": "prof@test.edu",
            "first_name": "Jane",
            "last_name": "Prof",
            "role": "instructor",
            "institution_id": inst_id,
            "account_status": "active",
        }
    )

    # Create term
    term_id = database_service.create_term(
        {
            "term_code": "FA2025",
            "term_name": "Fall 2025",
            "institution_id": inst_id,
            "start_date": "2025-09-01",
            "end_date": "2025-12-15",
        }
    )

    # Create offerings
    offering_101 = database_service.create_course_offering(
        {
            "course_id": cs101_id,
            "term_id": term_id,
            "institution_id": inst_id,
        }
    )

    offering_201 = database_service.create_course_offering(
        {
            "course_id": cs201_id,
            "term_id": term_id,
            "institution_id": inst_id,
        }
    )

    # Create sections
    section_101 = database_service.create_course_section(
        {
            "offering_id": offering_101,
            "section_number": "001",
            "instructor_id": instructor_id,
            "enrollment": 25,
        }
    )

    section_201 = database_service.create_course_section(
        {
            "offering_id": offering_201,
            "section_number": "001",
            "instructor_id": instructor_id,
            "enrollment": 20,
        }
    )

    # Execute: Get dashboard data for institution admin
    service = DashboardService()
    user = {
        "role": "institution_admin",
        "institution_id": inst_id,
    }

    dashboard_data = service.get_dashboard_data(user)

    # Debug: Print what we got
    print(f"\n🔍 Dashboard Data Summary:")
    print(f"  Summary: {dashboard_data.get('summary')}")
    print(f"  Program Overview: {dashboard_data.get('program_overview')}")

    # Assert: Summary should show counts
    # Note: Institution auto-creates a default program, so we have 2 total (CS + default)
    summary = dashboard_data.get("summary", {})
    assert (
        summary["programs"] == 2
    ), f"Expected 2 programs in summary (CS + default), got {summary.get('programs')}"
    assert (
        summary["courses"] == 2
    ), f"Expected 2 courses in summary, got {summary.get('courses')}"
    assert (
        summary["sections"] == 2
    ), f"Expected 2 sections in summary, got {summary.get('sections')}"

    # Assert: Program overview should have metrics
    program_overview = dashboard_data.get("program_overview", [])
    assert (
        len(program_overview) == 1
    ), f"Expected 1 program in overview, got {len(program_overview)}"

    cs_metrics = program_overview[0]
    print(f"\n📊 CS Program Metrics from DB:")
    print(f"  Program ID: {cs_metrics.get('program_id')}")
    print(f"  Program Name: {cs_metrics.get('program_name')}")
    print(f"  Course Count: {cs_metrics.get('course_count')}")
    print(f"  Section Count: {cs_metrics.get('section_count')}")
    print(f"  Faculty Count: {cs_metrics.get('faculty_count')}")
    print(f"  Student Count: {cs_metrics.get('student_count')}")

    # THIS IS WHERE THE BUG SHOULD SHOW UP:
    # If courses don't have program_ids properly set, these will be 0
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
    ), f"Expected 45 students, got {cs_metrics.get('student_count')}"
