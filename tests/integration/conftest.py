"""
Integration test configuration and fixtures.

This module provides common fixtures for integration tests,
including database setup and institution creation.
"""

import os

import pytest


@pytest.fixture
def client():
    """Create a Flask test client for integration tests."""
    import src.app as app

    # Configure the app for testing
    app.app.config["TESTING"] = True

    with app.app.test_client() as client:
        with app.app.app_context():
            yield client


@pytest.fixture(scope="class", autouse=True)
def setup_integration_test_data():
    """
    Set up integration test data including default MockU institution.

    This fixture runs once per test class and ensures that:
    1. A baseline MockU institution exists for historical test data
    2. Basic test data is available for integration tests
    3. Database connection is properly established
    """
    try:
        # Import and run the database seeder to create full test dataset
        import sys
        from pathlib import Path

        # Add scripts directory to path
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        from seed_db import DatabaseSeeder

        import src.database.database_service as database_service
        import src.database.database_service as db

        # Check if data already exists to avoid duplicate seeding
        institutions = db.get_all_institutions() or []
        mocku_exists = any(
            "California Engineering Institute" in inst.get("name", "")
            for inst in institutions
        )

        if not mocku_exists:
            # Create full seeded dataset for integration tests
            seeder = DatabaseSeeder(verbose=False)  # Reduce noise in test output
            seeder.seed_full_dataset()
            print("✅ Seeded full database for integration tests")
        else:
            print("✅ Integration test data already exists")

    except Exception as e:
        print(f"⚠️  Warning: Could not seed database for integration tests: {e}")
        # Don't fail the tests if this setup fails - let individual tests handle it


@pytest.fixture(scope="session", autouse=True)
def setup_integration_test_database(tmp_path_factory):
    """
    Set up integration test database with email whitelist configuration.

    This runs once per test session and:
    1. Creates a temporary database for integration tests
    2. Configures email whitelist to allow test emails
    3. Sets up environment variables for integration testing
    """
    # Set up email whitelist for integration tests to allow test emails
    # Use wildcard to allow all test emails
    os.environ["EMAIL_WHITELIST"] = (
        "*@inst.test,*@example.com,*@testu.edu,*@eu.edu,*@mocku.test,*@ethereal.email"
    )

    # Create temporary database for integration tests
    db_path = tmp_path_factory.mktemp("data") / "integration_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["DATABASE_TYPE"] = "sqlite"

    # Initialize database - must call refresh_connection() to update module-level singleton
    import src.database.database_service as database_service

    database_service.refresh_connection()
    database_service.reset_database()

    yield db_path

    # Cleanup email whitelist after tests
    if "EMAIL_WHITELIST" in os.environ:
        del os.environ["EMAIL_WHITELIST"]


@pytest.fixture(scope="function", autouse=True)
def clean_database_between_tests():
    """
    Clean database between integration tests to prevent pollution.

    This ensures each test starts with a fresh database state and seeds
    essential data (MockU institution, site admin) that tests depend on.
    """
    import src.database.database_service as database_service
    from src.database.database_service import (
        create_default_mocku_institution,
        create_user,
        get_programs_by_institution,
    )
    from src.models.models import User

    # Reset database to clean state
    database_service.reset_database()

    # Seed essential data that integration tests depend on
    # 1. Create test institutions
    from src.database.database_service import create_institution, create_program
    from src.models.models import Institution, Program

    mocku_id = create_default_mocku_institution()

    # Create test programs for MockU
    if mocku_id:
        mocku_programs = {
            "Computer Science": "CS",
            "Electrical Engineering": "EE",
            "Business Administration": "BUS",
        }
        for program_name, short_name in mocku_programs.items():
            program_schema = Program.create_schema(
                name=program_name,
                short_name=short_name,
                institution_id=mocku_id,
                created_by="system",
            )
            create_program(program_schema)

    # Create Coastal State College for import tests
    coastal_schema = Institution.create_schema(
        name="Coastal State College",
        short_name="CSC",
        admin_email="admin@coastal.edu",
        created_by="system",
    )
    coastal_schema["institution_id"] = "coastal-state-college"
    coastal_id = create_institution(coastal_schema)

    # Create default programs for coastal for course-program linking
    if coastal_id:
        programs = {
            "General Program": "GEN",
            "Mathematics": "MATH",
            "English": "ENG",
            "Biology": "BIO",
        }
        for program_name, short_name in programs.items():
            program_schema = Program.create_schema(
                name=program_name,
                short_name=short_name,
                institution_id=coastal_id,
                created_by="system",
            )
            create_program(program_schema)

    # Create RCC (Riverside Community College)
    rcc_schema = Institution.create_schema(
        name="Riverside Community College",
        short_name="RCC",
        admin_email="admin@rcc.edu",
        created_by="system",
    )
    rcc_schema["institution_id"] = "rcc"
    rcc_id = create_institution(rcc_schema)

    if rcc_id:
        rcc_programs = {
            "Liberal Arts": "LA",
            "Sciences": "SCI",
        }
        for program_name, short_name in rcc_programs.items():
            program_schema = Program.create_schema(
                name=program_name,
                short_name=short_name,
                institution_id=rcc_id,
                created_by="system",
            )
            create_program(program_schema)

    # Create PTU (Pacific Technical University)
    ptu_schema = Institution.create_schema(
        name="Pacific Technical University",
        short_name="PTU",
        admin_email="admin@ptu.edu",
        created_by="system",
    )
    ptu_schema["institution_id"] = "ptu"
    ptu_id = create_institution(ptu_schema)

    if ptu_id:
        ptu_programs = {
            "Engineering": "ENG",
            "Computer Science": "CS",
        }
        for program_name, short_name in ptu_programs.items():
            program_schema = Program.create_schema(
                name=program_name,
                short_name=short_name,
                institution_id=ptu_id,
                created_by="system",
            )
            create_program(program_schema)

    # 2. Create test users for integration tests
    if mocku_id:
        # Site admin
        site_admin_schema = User.create_schema(
            email="siteadmin@system.local",
            first_name="Site",
            last_name="Admin",
            role="site_admin",
            account_status="active",
            institution_id=mocku_id,
        )
        site_admin_schema["active"] = True
        site_admin_schema["password_hash"] = "hashed_password"
        create_user(site_admin_schema)

        # Institution admin
        inst_admin_schema = User.create_schema(
            email="sarah.admin@mocku.test",
            first_name="Sarah",
            last_name="Admin",
            role="institution_admin",
            account_status="active",
            institution_id=mocku_id,
        )
        inst_admin_schema["active"] = True
        inst_admin_schema["password_hash"] = "hashed_password"
        create_user(inst_admin_schema)

        # Program admin - needs to be assigned to CS program
        # First get the CS program ID
        from src.database.database_service import get_programs_by_institution

        mocku_programs = get_programs_by_institution(mocku_id)
        cs_program_id = next(
            (
                p["program_id"]
                for p in mocku_programs
                if p["name"] == "Computer Science"
            ),
            None,
        )

        prog_admin_schema = User.create_schema(
            email="bob.programadmin@mocku.test",
            first_name="Bob",
            last_name="Program Admin",
            role="program_admin",
            account_status="active",
            institution_id=mocku_id,
        )
        prog_admin_schema["active"] = True
        prog_admin_schema["password_hash"] = "hashed_password"
        if cs_program_id:
            prog_admin_schema["program_ids"] = [cs_program_id]
        create_user(prog_admin_schema)

        # Need to get CS program ID first for instructor assignment
        mocku_programs_temp = get_programs_by_institution(mocku_id)
        cs_program_id_temp = next(
            (
                p["program_id"]
                for p in mocku_programs_temp
                if p["name"] == "Computer Science"
            ),
            None,
        )

        # Instructor 1
        instructor_schema = User.create_schema(
            email="john.instructor@mocku.test",
            first_name="John",
            last_name="Instructor",
            role="instructor",
            account_status="active",
            institution_id=mocku_id,
        )
        instructor_schema["active"] = True
        instructor_schema["password_hash"] = "hashed_password"
        if cs_program_id_temp:
            instructor_schema["program_ids"] = [cs_program_id_temp]
        instructor_id = create_user(instructor_schema)

        # Instructor 2 (for faculty count)
        instructor2_schema = User.create_schema(
            email="jane.instructor@mocku.test",
            first_name="Jane",
            last_name="Instructor",
            role="instructor",
            account_status="active",
            institution_id=mocku_id,
        )
        instructor2_schema["active"] = True
        instructor2_schema["password_hash"] = "hashed_password"
        if cs_program_id_temp:
            instructor2_schema["program_ids"] = [cs_program_id_temp]
        instructor2_id = create_user(instructor2_schema)

    # 3. Create test courses, terms, offerings, and sections for dashboard tests
    from src.database.database_service import (
        create_course,
        create_course_offering,
        create_course_section,
        create_term,
    )
    from src.models.models import Course, CourseOffering, CourseSection, Term

    if mocku_id and instructor_id and instructor2_id:
        # Get program IDs for course linking
        from src.database.database_service import (
            add_course_to_program,
            get_programs_by_institution,
        )

        mocku_programs = get_programs_by_institution(mocku_id)
        cs_program_id = next(
            (
                p["program_id"]
                for p in mocku_programs
                if p["name"] == "Computer Science"
            ),
            None,
        )
        ee_program_id = next(
            (
                p["program_id"]
                for p in mocku_programs
                if p["name"] == "Electrical Engineering"
            ),
            None,
        )

        # Create courses for MockU (with hyphens for proper validation)
        cs101_id = create_course(
            Course.create_schema(
                course_number="CS-101",
                course_title="Intro to Computer Science",
                department="Computer Science",
                institution_id=mocku_id,
            )
        )
        if cs101_id and cs_program_id:
            add_course_to_program(cs101_id, cs_program_id)

        cs201_id = create_course(
            Course.create_schema(
                course_number="CS-201",
                course_title="Data Structures",
                department="Computer Science",
                institution_id=mocku_id,
            )
        )
        if cs201_id and cs_program_id:
            add_course_to_program(cs201_id, cs_program_id)

        ee101_id = create_course(
            Course.create_schema(
                course_number="EE-101",
                course_title="Intro to Electrical Engineering",
                department="Electrical Engineering",
                institution_id=mocku_id,
            )
        )
        if ee101_id and ee_program_id:
            add_course_to_program(ee101_id, ee_program_id)

        # Create term
        fall2024_schema = Term.create_schema(
            name="Fall 2024",
            start_date="2024-08-15",
            end_date="2024-12-15",
            assessment_due_date="2024-12-31",
        )
        fall2024_schema["institution_id"] = mocku_id  # Term needs institution_id
        fall2024_schema["term_name"] = (
            "2024FA"  # Add term_name for proper identification
        )
        fall2024_id = create_term(fall2024_schema)

        # Create course offerings
        if cs101_id and fall2024_id:
            cs101_offering_id = create_course_offering(
                CourseOffering.create_schema(
                    course_id=cs101_id,
                    term_id=fall2024_id,
                    institution_id=mocku_id,
                )
            )

            # Create sections with instructor assigned
            if cs101_offering_id:
                create_course_section(
                    CourseSection.create_schema(
                        offering_id=cs101_offering_id,
                        section_number="001",
                        instructor_id=instructor_id,
                        enrollment=25,
                        status="assigned",
                    )
                )

                create_course_section(
                    CourseSection.create_schema(
                        offering_id=cs101_offering_id,
                        section_number="002",
                        instructor_id=instructor_id,
                        enrollment=30,
                        status="assigned",
                    )
                )

        if cs201_id and fall2024_id:
            cs201_offering_id = create_course_offering(
                CourseOffering.create_schema(
                    course_id=cs201_id,
                    term_id=fall2024_id,
                    institution_id=mocku_id,
                )
            )

            # Create section for CS-201 with Jane as instructor (for faculty count)
            if cs201_offering_id:
                create_course_section(
                    CourseSection.create_schema(
                        offering_id=cs201_offering_id,
                        section_number="001",
                        instructor_id=instructor2_id,  # Jane teaches CS-201
                        enrollment=20,
                        status="assigned",
                    )
                )

        if ee101_id and fall2024_id:
            ee101_offering_id = create_course_offering(
                CourseOffering.create_schema(
                    course_id=ee101_id,
                    term_id=fall2024_id,
                    institution_id=mocku_id,
                )
            )

            # Create section for EE-101 with John as instructor (so he teaches 2 courses)
            if ee101_offering_id:
                create_course_section(
                    CourseSection.create_schema(
                        offering_id=ee101_offering_id,
                        section_number="001",
                        instructor_id=instructor_id,  # John teaches EE-101
                        enrollment=15,
                        status="assigned",
                    )
                )

    if coastal_id:
        # Create courses for Coastal State College (avoid MATH-101 which is used in import tests)
        create_course(
            Course.create_schema(
                course_number="BIO-101",
                course_title="Introduction to Biology",
                department="Biology",
                institution_id=coastal_id,
            )
        )

        create_course(
            Course.create_schema(
                course_number="CHEM-101",
                course_title="General Chemistry",
                department="Chemistry",
                institution_id=coastal_id,
            )
        )

    # Add one more user for site admin test (expects 6 total)
    if rcc_id:
        rcc_admin_schema = User.create_schema(
            email="admin@rcc.edu",
            first_name="RCC",
            last_name="Admin",
            role="institution_admin",
            account_status="active",
            institution_id=rcc_id,
        )
        rcc_admin_schema["active"] = True
        rcc_admin_schema["password_hash"] = "hashed_password"
        create_user(rcc_admin_schema)

    yield
