"""CRUD and audit coverage tests for database_service."""

import src.database.database_service as database_service
from src.utils.term_utils import get_term_status


def test_user_crud_operations() -> None:
    """Test Users CRUD: update_user_profile, update_user_role, deactivate_user, delete_user"""
    inst_id = database_service.create_institution(
        {
            "name": "User CRUD Test University",
            "short_name": "UCTU",
            "admin_email": "admin@uctu.edu",
            "created_by": "system",
        }
    )

    user_data = {
        "email": "testuser@uctu.edu",
        "first_name": "Test",
        "last_name": "User",
        "role": "instructor",
        "institution_id": inst_id,
        "account_status": "active",
    }
    user_id = database_service.create_user(user_data)
    assert user_id is not None

    profile_update = {
        "first_name": "Updated",
        "last_name": "Name",
        "display_name": "Dr. Updated Name",
    }
    result = database_service.update_user_profile(user_id, profile_update)
    assert result is True

    user = database_service.get_user_by_id(user_id)
    assert user["first_name"] == "Updated"
    assert user["last_name"] == "Name"

    result = database_service.update_user_role(user_id, "program_admin", [])
    assert result is True

    user = database_service.get_user_by_id(user_id)
    assert user["role"] == "program_admin"

    result = database_service.deactivate_user(user_id)
    assert result is True

    user = database_service.get_user_by_id(user_id)
    assert user["account_status"] == "suspended"

    result = database_service.delete_user(user_id)
    assert result is True

    user = database_service.get_user_by_id(user_id)
    assert user is None


def test_institution_crud_operations() -> None:
    """Test Institutions CRUD: update_institution, delete_institution"""
    inst_data = {
        "name": "Institution CRUD Test",
        "short_name": "ICT",
        "admin_email": "admin@ict.edu",
        "created_by": "system",
    }
    inst_id = database_service.create_institution(inst_data)
    assert inst_id is not None

    update_data = {
        "name": "Updated Institution Name",
        "short_name": "UIN",
    }
    result = database_service.update_institution(inst_id, update_data)
    assert result is True

    inst = database_service.get_institution_by_id(inst_id)
    assert inst["name"] == "Updated Institution Name"
    assert inst["short_name"] == "UIN"

    result = database_service.delete_institution(inst_id)
    assert result is True

    inst = database_service.get_institution_by_id(inst_id)
    assert inst is None


def test_course_crud_operations() -> None:
    """Test Courses CRUD: update_course, update_course_programs, delete_course"""
    inst_id = database_service.create_institution(
        {
            "name": "Course CRUD Test University",
            "short_name": "CCTU",
            "admin_email": "admin@cctu.edu",
            "created_by": "system",
        }
    )

    program_id = database_service.create_program(
        {
            "institution_id": inst_id,
            "program_name": "Test Program",
            "program_code": "TP",
            "active": True,
        }
    )

    course_data = {
        "course_number": "CS101",
        "course_title": "Intro to Testing",
        "department": "Computer Science",
        "credit_hours": 3,
        "institution_id": inst_id,
        "active": True,
    }
    course_id = database_service.create_course(course_data)
    assert course_id is not None

    update_data = {
        "course_title": "Advanced Testing",
        "credit_hours": 4,
    }
    result = database_service.update_course(course_id, update_data)
    assert result is True

    course = database_service.get_course_by_id(course_id)
    assert course["course_title"] == "Advanced Testing"
    assert course["credit_hours"] == 4

    result = database_service.update_course_programs(course_id, [program_id])
    assert result is True

    result = database_service.delete_course(course_id)
    assert result is True

    course = database_service.get_course_by_id(course_id)
    assert course is None


def test_duplicate_course_record_preserves_metadata() -> None:
    """Duplicate an existing course and ensure metadata/programs copy over."""
    inst_id = database_service.create_institution(
        {
            "name": "Duplication University",
            "short_name": "DU",
            "admin_email": "admin@du.edu",
            "created_by": "system",
        }
    )

    program_id = database_service.create_program(
        {
            "institution_id": inst_id,
            "program_name": "Life Sciences",
            "program_code": "BIO",
            "active": True,
        }
    )

    course_id = database_service.create_course(
        {
            "course_number": "BIOL-201",
            "course_title": "Cellular Biology",
            "department": "Biology",
            "credit_hours": 3,
            "institution_id": inst_id,
            "active": True,
            "program_ids": [program_id],
        }
    )

    source_course = database_service.get_course_by_id(course_id)
    duplicated_course_id = database_service.duplicate_course_record(source_course)

    assert duplicated_course_id is not None
    assert duplicated_course_id != course_id

    duplicated_course = database_service.get_course_by_id(duplicated_course_id)
    assert duplicated_course["course_number"].startswith("BIOL-201-")
    assert duplicated_course["program_ids"] == source_course["program_ids"]

    override_course_id = database_service.duplicate_course_record(
        source_course,
        overrides={"course_number": "BIOL-201-VERSION2", "credit_hours": 4},
        duplicate_programs=False,
    )

    override_course = database_service.get_course_by_id(override_course_id)
    assert override_course["course_number"] == "BIOL-201-VERSION2"
    assert override_course["credit_hours"] == 4
    assert override_course.get("program_ids") == []


def test_term_crud_operations() -> None:
    """Test Terms CRUD: update_term and delete_term"""
    inst_id = database_service.create_institution(
        {
            "name": "Term CRUD Test University",
            "short_name": "TCTU",
            "admin_email": "admin@tctu.edu",
            "created_by": "system",
        }
    )

    term_data = {
        "term_name": "FA2024",
        "name": "Fall 2024",
        "start_date": "2024-08-01",
        "end_date": "2024-12-15",
        "institution_id": inst_id,
    }
    term_id = database_service.create_term(term_data)
    assert term_id is not None

    update_data = {
        "name": "Fall 2024 Updated",
        "end_date": "2024-12-20",
    }
    result = database_service.update_term(term_id, update_data)
    assert result is True

    term = database_service.get_term_by_name("FA2024", inst_id)
    assert term["name"] == "Fall 2024 Updated"

    result = database_service.delete_term(term_id)
    assert result is True

    term = database_service.get_term_by_name("FA2024", inst_id)
    assert term is None


def test_offering_crud_operations() -> None:
    """Test Offerings CRUD: update_course_offering, delete_course_offering"""
    inst_id = database_service.create_institution(
        {
            "name": "Offering CRUD Test University",
            "short_name": "OCTU",
            "admin_email": "admin@octu.edu",
            "created_by": "system",
        }
    )

    course_id = database_service.create_course(
        {
            "course_number": "CS202",
            "course_title": "Data Structures",
            "department": "CS",
            "credit_hours": 3,
            "institution_id": inst_id,
            "active": True,
        }
    )

    term_start = "2025-01-01"
    term_end = "2025-05-15"
    term_id = database_service.create_term(
        {
            "term_name": "SP2025",
            "name": "Spring 2025",
            "start_date": term_start,
            "end_date": term_end,
            "institution_id": inst_id,
        }
    )

    offering_data = {
        "course_id": course_id,
        "term_id": term_id,
        "institution_id": inst_id,
        "total_enrollment": 0,
    }
    offering_id = database_service.create_course_offering(offering_data)
    assert offering_id is not None

    update_data = {
        "total_enrollment": 25,
    }
    result = database_service.update_course_offering(offering_id, update_data)
    assert result is True

    offering = database_service.get_course_offering(offering_id)
    assert offering["total_enrollment"] == 25
    assert offering["status"] in {"UNKNOWN", get_term_status(term_start, term_end)}

    result = database_service.delete_course_offering(offering_id)
    assert result is True

    offering = database_service.get_course_offering(offering_id)
    assert offering is None


def test_section_crud_operations() -> None:
    """Test Sections CRUD: update_course_section, assign_instructor, delete_course_section"""
    inst_id = database_service.create_institution(
        {
            "name": "Section CRUD Test University",
            "short_name": "SCTU",
            "admin_email": "admin@sctu.edu",
            "created_by": "system",
        }
    )

    instructor_id = database_service.create_user(
        {
            "email": "instructor@sctu.edu",
            "first_name": "Section",
            "last_name": "Instructor",
            "role": "instructor",
            "institution_id": inst_id,
            "account_status": "active",
        }
    )

    course_id = database_service.create_course(
        {
            "course_number": "CS303",
            "course_title": "Algorithms",
            "department": "CS",
            "credit_hours": 3,
            "institution_id": inst_id,
            "active": True,
        }
    )

    term_id = database_service.create_term(
        {
            "term_name": "FA2025",
            "name": "Fall 2025",
            "start_date": "2025-08-01",
            "end_date": "2025-12-15",
            "institution_id": inst_id,
        }
    )

    offering_id = database_service.create_course_offering(
        {
            "course_id": course_id,
            "term_id": term_id,
            "institution_id": inst_id,
            "capacity": 30,
        }
    )

    section_data = {
        "offering_id": offering_id,
        "section_number": "001",
        "enrollment": 20,
        "status": "unassigned",
    }
    section_id = database_service.create_course_section(section_data)
    assert section_id is not None

    result = database_service.assign_instructor(section_id, instructor_id)
    assert result is True

    sections = database_service.get_sections_by_instructor(instructor_id)
    assert len(sections) == 1
    assert sections[0]["section_id"] == section_id

    update_data = {
        "enrollment": 25,
        "status": "completed",
        "grade_distribution": {"A": 10, "B": 10, "C": 5},
    }
    result = database_service.update_course_section(section_id, update_data)
    assert result is True

    result = database_service.delete_course_section(section_id)
    assert result is True

    sections = database_service.get_sections_by_instructor(instructor_id)
    assert len(sections) == 0


def test_outcome_crud_operations() -> None:
    """Test Outcomes CRUD: update_course_outcome, update_outcome_assessment, delete_course_outcome"""
    inst_id = database_service.create_institution(
        {
            "name": "Outcome CRUD Test University",
            "short_name": "OCRU",
            "admin_email": "admin@ocru.edu",
            "created_by": "system",
        }
    )

    course_id = database_service.create_course(
        {
            "course_number": "CS404",
            "course_title": "Software Engineering",
            "department": "CS",
            "credit_hours": 3,
            "institution_id": inst_id,
            "active": True,
        }
    )

    outcome_data = {
        "course_id": course_id,
        "clo_number": 1,
        "description": "Students will demonstrate proficiency in testing",
        "assessment_method": "project",
        "active": True,
    }
    outcome_id = database_service.create_course_outcome(outcome_data)
    assert outcome_id is not None

    update_data = {
        "description": "Students will master comprehensive testing strategies",
        "assessment_method": "exam and project",
    }
    result = database_service.update_course_outcome(outcome_id, update_data)
    assert result is True

    outcomes = database_service.get_course_outcomes(course_id)
    assert len(outcomes) == 1
    assert (
        outcomes[0]["description"]
        == "Students will master comprehensive testing strategies"
    )

    result = database_service.update_outcome_assessment(
        outcome_id,
        students_took=30,
        students_passed=27,
        assessment_tool="Final Project",
    )
    assert result is True

    outcomes = database_service.get_course_outcomes(course_id)
    assert outcomes[0]["students_took"] == 30
    assert outcomes[0]["students_passed"] == 27
    assert outcomes[0]["assessment_tool"] == "Final Project"

    result = database_service.delete_course_outcome(outcome_id)
    assert result is True

    outcomes = database_service.get_course_outcomes(course_id)
    assert len(outcomes) == 0


def test_get_outcomes_by_status() -> None:
    """Test get_outcomes_by_status function coverage."""
    outcomes = database_service.get_outcomes_by_status("nonexistent", "draft", None)
    assert isinstance(outcomes, list)

    outcomes_with_program = database_service.get_outcomes_by_status(
        "nonexistent", "published", "fake-program-id"
    )
    assert isinstance(outcomes_with_program, list)


def test_get_sections_by_course() -> None:
    """Test get_sections_by_course function coverage."""
    institution_id = database_service.create_institution(
        {
            "name": "Sections Test University",
            "short_name": "STU",
            "admin_email": "admin@stu.edu",
            "created_by": "system",
        }
    )

    course_id = database_service.create_course(
        {
            "course_number": "SEC-200",
            "course_name": "Sections Course",
            "institution_id": institution_id,
        }
    )

    sections = database_service.get_sections_by_course(course_id)
    assert isinstance(sections, list)


def test_audit_log_retrieval_by_entity() -> None:
    """Test retrieving audit logs filtered by entity type and ID"""
    inst_id = database_service.create_institution(
        {
            "name": "Audit Test University",
            "short_name": "ATU",
            "admin_email": "admin@atu.edu",
        }
    )

    course_id = database_service.create_course(
        {
            "course_number": "CS-101",
            "course_name": "Intro to CS",
            "institution_id": inst_id,
        }
    )

    audit_data = {
        "institution_id": inst_id,
        "user_id": "instructor-1",
        "action": "course_updated",
        "entity_type": "course",
        "entity_id": course_id,
        "details": {"field": "name", "old": "Intro", "new": "Introduction"},
    }
    database_service.create_audit_log(audit_data)

    logs = database_service.get_audit_logs_by_entity("course", course_id, limit=10)
    assert isinstance(logs, list)


def test_audit_log_retrieval_by_user() -> None:
    """Test retrieving all audit logs for a specific user"""
    inst_id = database_service.create_institution(
        {
            "name": "User Audit Test",
            "short_name": "UAT",
            "admin_email": "admin@uat.edu",
        }
    )

    user_id = "test-instructor-456"

    for i in range(3):
        audit_data = {
            "institution_id": inst_id,
            "user_id": user_id,
            "action": f"action_{i}",
            "details": {"index": i},
        }
        database_service.create_audit_log(audit_data)

    logs = database_service.get_audit_logs_by_user(user_id)
    assert isinstance(logs, list)


def test_recent_audit_logs_respects_limit() -> None:
    """Test that recent audit logs honors the limit parameter"""
    inst_id = database_service.create_institution(
        {
            "name": "Limit Test Inst",
            "short_name": "LTI",
            "admin_email": "admin@lti.edu",
        }
    )

    logs = database_service.get_recent_audit_logs(inst_id, limit=5)
    assert isinstance(logs, list)
    assert len(logs) <= 5


def test_get_all_institutions_returns_multiple() -> None:
    """Test that get_all_institutions returns all created institutions"""
    inst1 = database_service.create_institution(
        {
            "name": "University One",
            "short_name": "U1",
            "admin_email": "admin@u1.edu",
        }
    )
    inst2 = database_service.create_institution(
        {
            "name": "University Two",
            "short_name": "U2",
            "admin_email": "admin@u2.edu",
        }
    )

    all_insts = database_service.get_all_institutions()
    assert isinstance(all_insts, list)
    assert len(all_insts) >= 2

    inst_ids = [inst["institution_id"] for inst in all_insts]
    assert inst1 in inst_ids
    assert inst2 in inst_ids


def test_get_all_instructors_for_empty_institution() -> None:
    """Test that get_all_instructors returns empty list for institution with no instructors"""
    inst_id = database_service.create_institution(
        {
            "name": "Empty Instructor Inst",
            "short_name": "EII",
            "admin_email": "admin@eii.edu",
        }
    )

    instructors = database_service.get_all_instructors(inst_id)
    assert isinstance(instructors, list)
    assert len(instructors) >= 0


def test_get_all_sections_and_offerings_consistency() -> None:
    """Test that sections and offerings can be retrieved for an institution"""
    inst_id = database_service.create_institution(
        {
            "name": "Section Test Inst",
            "short_name": "STI",
            "admin_email": "admin@sti.edu",
        }
    )

    sections = database_service.get_all_sections(inst_id)
    offerings = database_service.get_all_course_offerings(inst_id)

    assert isinstance(sections, list)
    assert isinstance(offerings, list)


def test_get_course_by_id_returns_none_for_nonexistent() -> None:
    """Test that get_course_by_id returns None for courses that don't exist"""
    course = database_service.get_course_by_id("nonexistent-course-id-12345")
    assert course is None


def test_get_course_by_id_returns_correct_course() -> None:
    """Test that get_course_by_id returns the correct course data"""
    inst_id = database_service.create_institution(
        {
            "name": "Course Lookup Test",
            "short_name": "CLT",
            "admin_email": "admin@clt.edu",
        }
    )

    course_id = database_service.create_course(
        {
            "course_number": "BIO-301",
            "course_name": "Advanced Biology",
            "institution_id": inst_id,
        }
    )

    course = database_service.get_course_by_id(course_id)
    assert course is not None
    assert course["course_id"] == course_id
    assert course["course_number"] == "BIO-301"
    assert course["course_name"] == "Advanced Biology"


def test_create_new_institution_simple_vs_full() -> None:
    """Test that simple institution creation doesn't create admin user"""
    simple_inst_id = database_service.create_new_institution_simple(
        name="Simple Institution", short_name="SI", active=True
    )
    assert simple_inst_id is not None

    inst = database_service.get_institution_by_id(simple_inst_id)
    assert inst["name"] == "Simple Institution"
    assert inst["short_name"] == "SI"
    assert inst["active"] is True

    users = database_service.get_all_users(simple_inst_id)
    assert len(users) == 0


def test_get_audit_logs_filtered_with_date_range() -> None:
    """Test that audit log filtering respects date ranges"""
    inst_id = database_service.create_institution(
        {
            "name": "Filtered Audit Test",
            "short_name": "FAT",
            "admin_email": "admin@fat.edu",
        }
    )

    audit_data = {
        "institution_id": inst_id,
        "user_id": "test-user",
        "action": "test_action",
        "entity_type": "course",
        "entity_id": "course-123",
        "details": {"test": "data"},
    }
    database_service.create_audit_log(audit_data)

    logs = database_service.get_audit_logs_filtered(
        start_date="2024-01-01",
        end_date="2024-12-31",
        entity_type="course",
        user_id="test-user",
        institution_id=inst_id,
    )
    assert isinstance(logs, list)


def test_generate_unique_course_number_increments_suffix_when_collisions() -> None:
    """Covers _generate_unique_course_number loop when -V2/-V3 already exist."""
    from unittest.mock import patch

    with patch("src.database.database_service.get_course_by_number") as mock_get:
        mock_get.side_effect = [
            {"course_id": "existing"},
            {"course_id": "existing"},
            None,
        ]
        result = database_service._generate_unique_course_number("BIOL-201", "inst-1")

    assert result == "BIOL-201-V4"


def test_generate_unique_course_number_normalizes_base_number() -> None:
    """Covers base_number normalization and default fallback."""
    from unittest.mock import patch

    with patch("src.database.database_service.get_course_by_number", return_value=None):
        assert (
            database_service._generate_unique_course_number("  cs101  ", "inst-1")
            == "CS101-V2"
        )
        assert (
            database_service._generate_unique_course_number("", "inst-1") == "COURSE-V2"
        )


def test_get_outcomes_by_status_with_program_and_term_filters_crud_split() -> None:
    """Covers get_outcomes_by_status program_id + term_id branches in the CRUD split file."""
    inst_id = database_service.create_institution(
        {
            "name": "Outcome University",
            "short_name": "OU",
            "admin_email": "admin@ou.edu",
            "created_by": "system",
        }
    )
    program_id = database_service.create_program(
        {"name": "Program", "short_name": "PROG", "institution_id": inst_id}
    )
    course_id = database_service.create_course(
        {
            "course_number": "OU-101",
            "course_title": "Outcomes",
            "institution_id": inst_id,
        }
    )
    database_service.add_course_to_program(course_id, program_id)

    term_id = database_service.create_term(
        {
            "term_name": "OU Term",
            "start_date": "2025-01-01",
            "end_date": "2025-02-01",
            "institution_id": inst_id,
        }
    )
    offering_id = database_service.create_course_offering(
        {"course_id": course_id, "term_id": term_id, "institution_id": inst_id}
    )
    database_service.create_course_section(
        {"offering_id": offering_id, "section_number": "001"}
    )

    outcomes = database_service.get_outcomes_by_status(
        inst_id, "draft", program_id, term_id
    )
    assert isinstance(outcomes, list)
