"""Integration tests exercising SQLite-backed database interactions."""

import os

import pytest

import src.database.database_service as database_service

pytestmark = pytest.mark.integration


def test_database_file_created(isolated_integration_db):
    """Ensure the configured SQLite database file exists on disk."""
    # isolated_integration_db fixture returns the database path
    db_path = isolated_integration_db
    assert os.path.exists(db_path)


def test_full_institution_user_flow():
    """Exercise institution + user creation end-to-end."""
    institution_id = database_service.create_institution(
        {
            "name": "Integration College",
            "short_name": "IC",
            "admin_email": "integration@ic.edu",
            "created_by": "integration-test",
        }
    )
    assert institution_id

    user_id = database_service.create_user(
        {
            "email": "admin@ic.edu",
            "first_name": "Integration",
            "last_name": "Admin",
            "role": "institution_admin",
            "institution_id": institution_id,
            "account_status": "active",
        }
    )
    assert user_id

    active_count = database_service.calculate_and_update_active_users(institution_id)
    assert active_count == 1

    users = database_service.get_all_users(institution_id)
    assert len(users) == 1
    assert users[0]["email"] == "admin@ic.edu"


def test_program_course_assignment_flow():
    """Assign courses to programs and verify aggregation functions."""
    inst_id = database_service.create_institution(
        {
            "name": "Integration STEM",
            "short_name": "IST",
            "admin_email": "admin@ist.edu",
            "created_by": "integration-test",
        }
    )
    program_id = database_service.create_program(
        {
            "name": "Physics",
            "short_name": "PHY",
            "institution_id": inst_id,
        }
    )
    course_ids = []
    for number in ("PHY101", "PHY201"):
        course_ids.append(
            database_service.create_course(
                {
                    "course_number": number,
                    "course_title": f"Physics {number}",
                    "department": "Physics",
                    "institution_id": inst_id,
                }
            )
        )

    database_service.bulk_add_courses_to_program(course_ids, program_id)

    assigned = database_service.get_courses_by_program(program_id)
    assert {course["course_number"] for course in assigned} == {"PHY101", "PHY201"}

    unassigned = database_service.get_unassigned_courses(inst_id)
    assert not any(
        course["course_number"] in {"PHY101", "PHY201"} for course in unassigned
    )
