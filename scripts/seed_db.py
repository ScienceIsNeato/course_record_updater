#!/usr/bin/env python3
"""
Database Seeding Script for UAT Testing

This script creates a realistic, deterministic dataset for User Acceptance Testing
of the authentication system. It creates multiple institutions, users, programs,
courses, and sections to validate multi-tenant functionality.

Usage:
    python seed_db.py                    # Seed with default data
    python seed_db.py --clear            # Clear existing data first
    python seed_db.py --minimal          # Create minimal dataset only
    python seed_db.py --help             # Show usage information
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, cast

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our services and models
import database_service as db
from constants import (
    PROGRAM_COMPUTER_SCIENCE,
    PROGRAM_DEFAULT_DESCRIPTION,
    PROGRAM_ELECTRICAL_ENGINEERING,
    SITE_ADMIN_INSTITUTION_ID,
)
from models import Course, Institution, Program, Term, User, UserInvitation
from password_service import hash_password


class DatabaseSeeder:
    """Handles database seeding operations"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.created_entities: Dict[str, List[str]] = {
            "institutions": [],
            "users": [],
            "programs": [],
            "courses": [],
            "terms": [],
            "sections": [],
            "course_outcomes": [],
            "invitations": [],
        }

    def log(self, message: str):
        """Log message if verbose mode is enabled"""
        if self.verbose:
            print(f"[SEED] {message}")

    def clear_database(self):
        """Clear existing test data (be careful in production!)"""
        self.log("🧹 Clearing existing test data...")

        collections = [
            "user_invitations",
            "course_sections",
            "course_outcomes",
            "course_offerings",
            "terms",
            "courses",
            "programs",
            "users",
            "institutions",
        ]

        for collection_name in collections:
            try:
                collection = db.db.collection(collection_name)
                docs = collection.stream()
                batch = db.db.batch()
                count = 0

                for doc in docs:
                    batch.delete(doc.reference)
                    count += 1

                    # Commit in batches of 500 (Firestore limit)
                    if count % 500 == 0:
                        batch.commit()
                        batch = db.db.batch()

                # Commit remaining
                if count % 500 != 0:
                    batch.commit()

                self.log(f"   Cleared {count} documents from {collection_name}")

            except Exception as e:
                self.log(f"   Warning: Could not clear {collection_name}: {e}")

    def create_institutions(self) -> List[str]:
        """Create test institutions (idempotent - checks for existing)"""
        self.log("🏢 Creating test institutions...")

        institutions = [
            {
                "name": "California Engineering Institute",
                "short_name": "CEI",
                "admin_email": "admin@cei.edu",
                "website_url": "https://cei.edu",
                "created_by": "system",
            },
            {
                "name": "Riverside Community College",
                "short_name": "RCC",
                "admin_email": "admin@riverside.edu",
                "website_url": "https://riverside.edu",
                "created_by": "system",
            },
            {
                "name": "Pacific Technical University",
                "short_name": "PTU",
                "admin_email": "admin@pactech.edu",
                "website_url": "https://pactech.edu",
                "created_by": "system",
            },
        ]

        institution_ids = []
        for inst_data in institutions:
            # Check if institution already exists by short_name
            existing_institution = db.get_institution_by_short_name(
                inst_data["short_name"]
            )

            if existing_institution:
                institution_id = existing_institution["institution_id"]
                institution_ids.append(institution_id)
                self.created_entities["institutions"].append(institution_id)
                self.log(
                    f"   Found existing institution: {inst_data['name']} ({inst_data['short_name']})"
                )
            else:
                # Create new institution
                schema = Institution.create_schema(
                    name=inst_data["name"],
                    short_name=inst_data["short_name"],
                    created_by=inst_data["created_by"],
                    admin_email=inst_data["admin_email"],
                    website_url=inst_data.get("website_url"),
                )
                institution_id = db.create_institution(schema)
                if institution_id:
                    institution_ids.append(institution_id)
                    self.created_entities["institutions"].append(institution_id)
                    self.log(
                        f"   Created institution: {inst_data['name']} ({inst_data['short_name']})"
                    )
                else:
                    self.log(f"   Failed to create institution: {inst_data['name']}")

        return institution_ids

    def create_site_admin(self) -> Optional[str]:
        """Create the site administrator user (idempotent - checks for existing)"""
        self.log("👑 Creating site administrator...")

        try:
            email = "siteadmin@system.local"

            # Check if site admin already exists
            existing_user = db.get_user_by_email(email)
            if existing_user:
                user_id = existing_user["user_id"]
                self.created_entities["users"].append(user_id)
                self.log(f"   Found existing site admin: {email} / SiteAdmin123!")
                return user_id

            # Create new site admin
            password_hash = hash_password("SiteAdmin123!")

            schema = User.create_schema(
                email=email,
                first_name="System",
                last_name="Administrator",
                role="site_admin",
                institution_id=SITE_ADMIN_INSTITUTION_ID,  # Site admin has wildcard access
                password_hash=password_hash,
                account_status="active",
                display_name="Site Admin",
            )

            # Override email verification for test user
            schema["email_verified"] = True
            schema["registration_completed_at"] = datetime.now(timezone.utc)

            user_id = db.create_user(schema)
            if user_id:
                self.created_entities["users"].append(user_id)
                self.log(f"   Created site admin: {email} / SiteAdmin123!")
                return user_id
            else:
                self.log("   Failed to create site admin")
                return None

        except Exception as e:
            self.log(f"   Error creating site admin: {e}")
            return None

    def create_institution_admins(self, institution_ids: List[str]) -> List[str]:
        """Create institution administrators"""
        self.log("🎓 Creating institution administrators...")

        admin_data = [
            {
                "email": "sarah.admin@cei.edu",
                "first_name": "Sarah",
                "last_name": "Johnson",
                "institution_idx": 0,  # CEI
                "display_name": "Dr. Johnson",
            },
            {
                "email": "mike.admin@riverside.edu",
                "first_name": "Mike",
                "last_name": "Rodriguez",
                "institution_idx": 1,  # RCC
                "display_name": "Mike Rodriguez",
            },
            {
                "email": "admin@pactech.edu",
                "first_name": "Jennifer",
                "last_name": "Chen",
                "institution_idx": 2,  # PTU
                "display_name": "Dr. Chen",
            },
        ]

        admin_ids = []
        for admin in admin_data:
            institution_idx = cast(int, admin["institution_idx"])
            if institution_idx < len(institution_ids):
                try:
                    # Check if admin already exists
                    email = str(admin["email"])
                    existing_user = db.get_user_by_email(email)
                    if existing_user:
                        user_id = existing_user["user_id"]
                        admin_ids.append(user_id)
                        self.created_entities["users"].append(user_id)
                        self.log(
                            f"   Found existing institution admin: {email} / InstitutionAdmin123!"
                        )
                        continue

                    # Create new admin
                    password_hash = hash_password("InstitutionAdmin123!")

                    schema = User.create_schema(
                        email=email,
                        first_name=str(admin["first_name"]),
                        last_name=str(admin["last_name"]),
                        role="institution_admin",
                        institution_id=institution_ids[institution_idx],
                        password_hash=password_hash,
                        account_status="active",
                        display_name=str(admin.get("display_name", "")),
                    )

                    # Override email verification for test user
                    schema["email_verified"] = True
                    schema["registration_completed_at"] = datetime.now(timezone.utc)

                    user_id = db.create_user(schema)
                    if user_id:
                        admin_ids.append(user_id)
                        self.created_entities["users"].append(user_id)
                        self.log(
                            f"   Created institution admin: {admin['email']} / InstitutionAdmin123!"
                        )
                    else:
                        self.log(f"   Failed to create admin: {admin['email']}")

                except Exception as e:
                    self.log(f"   Error creating admin {admin['email']}: {e}")

        return admin_ids

    def _get_programs_data(self) -> List[dict]:
        """Get program seed data"""
        return [
            # CEI Programs
            {
                "name": PROGRAM_COMPUTER_SCIENCE,
                "short_name": "CS",
                "description": "Bachelor of Science in Computer Science",
                "institution_idx": 0,
                "admin_idx": 0,
            },
            {
                "name": PROGRAM_ELECTRICAL_ENGINEERING,
                "short_name": "EE",
                "description": "Bachelor of Science in Electrical Engineering",
                "institution_idx": 0,
                "admin_idx": 0,
            },
            {
                "name": "General Studies",
                "short_name": "GEN",
                "description": "General Studies and undeclared majors at CEI",
                "institution_idx": 0,
                "admin_idx": 0,
                "is_default": True,
            },
            # RCC Programs
            {
                "name": "Liberal Arts",
                "short_name": "LA",
                "description": "Associate of Arts in Liberal Arts",
                "institution_idx": 1,
                "admin_idx": 1,
            },
            {
                "name": "Business Administration",
                "short_name": "BUS",
                "description": "Associate of Science in Business Administration",
                "institution_idx": 1,
                "admin_idx": 1,
            },
            {
                "name": "Exploratory Studies",
                "short_name": "EXPL",
                "description": "Exploratory Studies for students exploring career options at RCC",
                "institution_idx": 1,
                "admin_idx": 1,
                "is_default": True,
            },
            # PTU Programs
            {
                "name": "Mechanical Engineering",
                "short_name": "ME",
                "description": "Bachelor of Science in Mechanical Engineering",
                "institution_idx": 2,
                "admin_idx": 2,
            },
            {
                "name": "Pre-Engineering",
                "short_name": "PRE",
                "description": "Pre-Engineering program for students preparing for engineering majors at PTU",
                "institution_idx": 2,
                "admin_idx": 2,
                "is_default": True,
            },
        ]

    def _create_single_program(
        self, prog_data: dict, institution_ids: List[str], admin_ids: List[str]
    ) -> Optional[str]:
        """Create a single program"""
        institution_idx = cast(int, prog_data["institution_idx"])
        admin_idx = cast(int, prog_data["admin_idx"])

        if institution_idx >= len(institution_ids) or admin_idx >= len(admin_ids):
            return None

        try:
            institution_id = institution_ids[institution_idx]
            program_name = cast(str, prog_data["name"])

            # Check if program already exists
            existing_program = db.get_program_by_name_and_institution(
                program_name, institution_id
            )
            if existing_program:
                program_id = existing_program["id"]
                self.created_entities["programs"].append(program_id)
                self.log(
                    f"   Found existing program: {prog_data['name']} ({prog_data['short_name']})"
                )
                return program_id

            # Create new program
            schema = Program.create_schema(
                name=cast(str, prog_data["name"]),
                short_name=cast(str, prog_data["short_name"]),
                institution_id=institution_id,
                created_by=admin_ids[admin_idx],
                description=cast(str, prog_data.get("description", "")),
                is_default=cast(bool, prog_data.get("is_default", False)),
            )
            schema["id"] = schema.pop("program_id")

            program_id = db.create_program(schema)
            if program_id:
                self.created_entities["programs"].append(program_id)
                self.log(
                    f"   Created program: {prog_data['name']} ({prog_data['short_name']})"
                )
                return program_id
            else:
                self.log(f"   Failed to create program: {prog_data['name']}")
                return None

        except Exception as e:
            self.log(f"   Error creating program {prog_data['name']}: {e}")
            return None

    def create_programs(
        self, institution_ids: List[str], admin_ids: List[str]
    ) -> List[str]:
        """Create academic programs"""
        self.log("📚 Creating academic programs...")

        programs_data = self._get_programs_data()
        program_ids = []

        for prog_data in programs_data:
            program_id = self._create_single_program(
                prog_data, institution_ids, admin_ids
            )
            if program_id:
                program_ids.append(program_id)

        return program_ids

    def create_program_admins_and_instructors(
        self, institution_ids: List[str], program_ids: List[str]
    ) -> List[str]:
        """Create program administrators and instructors"""
        self.log("👥 Creating program admins and instructors...")

        users_data = [
            # CEI Users
            {
                "email": "lisa.prog@cei.edu",
                "first_name": "Lisa",
                "last_name": "Wang",
                "role": "program_admin",
                "institution_idx": 0,
                "program_ids": [0, 1],  # CS and EE programs
                "display_name": "Prof. Wang",
            },
            {
                "email": "john.instructor@cei.edu",
                "first_name": "John",
                "last_name": "Smith",
                "role": "instructor",
                "institution_idx": 0,
                "program_ids": [0],  # CS program
                "display_name": "Dr. Smith",
            },
            {
                "email": "jane.instructor@cei.edu",
                "first_name": "Jane",
                "last_name": "Davis",
                "role": "instructor",
                "institution_idx": 0,
                "program_ids": [1],  # EE program
                "display_name": "Prof. Davis",
            },
            # RCC Users
            {
                "email": "robert.prog@riverside.edu",
                "first_name": "Robert",
                "last_name": "Miller",
                "role": "program_admin",
                "institution_idx": 1,
                "program_ids": [3],  # Liberal Arts
                "display_name": "Prof. Miller",
            },
            {
                "email": "susan.instructor@riverside.edu",
                "first_name": "Susan",
                "last_name": "Brown",
                "role": "instructor",
                "institution_idx": 1,
                "program_ids": [3, 4],  # Liberal Arts and Business
                "display_name": "Susan Brown",
            },
            # PTU Users
            {
                "email": "david.instructor@pactech.edu",
                "first_name": "David",
                "last_name": "Wilson",
                "role": "instructor",
                "institution_idx": 2,
                "program_ids": [6],  # Mechanical Engineering
                "display_name": "Dr. Wilson",
            },
        ]

        user_ids = []
        for user_data in users_data:
            if user_data["institution_idx"] < len(institution_ids) and all(
                idx < len(program_ids) for idx in user_data["program_ids"]
            ):

                try:
                    # Check if user already exists
                    existing_user = db.get_user_by_email(user_data["email"])
                    if existing_user:
                        user_id = existing_user["user_id"]
                        user_ids.append(user_id)
                        self.created_entities["users"].append(user_id)
                        self.log(
                            f"   Found existing {user_data['role']}: {user_data['email']} / TestUser123!"
                        )
                        continue

                    # Create new user
                    password_hash = hash_password("TestUser123!")

                    # Map program indices to actual program IDs
                    user_program_ids = [
                        program_ids[idx] for idx in user_data["program_ids"]
                    ]

                    schema = User.create_schema(
                        email=user_data["email"],
                        first_name=user_data["first_name"],
                        last_name=user_data["last_name"],
                        role=user_data["role"],
                        institution_id=institution_ids[user_data["institution_idx"]],
                        password_hash=password_hash,
                        account_status="active",
                        program_ids=user_program_ids,
                        display_name=user_data["display_name"],
                    )

                    # Override email verification for test user
                    schema["email_verified"] = True
                    schema["registration_completed_at"] = datetime.now(timezone.utc)

                    user_id = db.create_user(schema)
                    if user_id:
                        user_ids.append(user_id)
                        self.created_entities["users"].append(user_id)
                        self.log(
                            f"   Created {user_data['role']}: {user_data['email']} / TestUser123!"
                        )
                    else:
                        self.log(f"   Failed to create user: {user_data['email']}")

                except Exception as e:
                    self.log(f"   Error creating user {user_data['email']}: {e}")

        return user_ids

    def create_terms(self, institution_ids: List[str]) -> List[str]:
        """Create academic terms"""
        self.log("📅 Creating academic terms...")

        # Create terms for current and next semester
        current_year = datetime.now().year

        terms_data = [
            # Current terms (Fall 2024/2025)
            {
                "name": f"Fall {current_year}",
                "start_date": f"{current_year}-08-15",
                "end_date": f"{current_year}-12-15",
                "assessment_due_date": f"{current_year}-12-01",
                "institution_idx": 0,  # CEI
            },
            {
                "name": f"Fall {current_year}",
                "start_date": f"{current_year}-08-20",
                "end_date": f"{current_year}-12-10",
                "assessment_due_date": f"{current_year}-11-30",
                "institution_idx": 1,  # RCC
            },
            {
                "name": f"Fall {current_year}",
                "start_date": f"{current_year}-08-25",
                "end_date": f"{current_year}-12-20",
                "assessment_due_date": f"{current_year}-12-05",
                "institution_idx": 2,  # PTU
            },
            # Future terms (Spring)
            {
                "name": f"Spring {current_year + 1}",
                "start_date": f"{current_year + 1}-01-15",
                "end_date": f"{current_year + 1}-05-15",
                "assessment_due_date": f"{current_year + 1}-05-01",
                "institution_idx": 0,  # CEI
            },
            {
                "name": f"Spring {current_year + 1}",
                "start_date": f"{current_year + 1}-01-20",
                "end_date": f"{current_year + 1}-05-10",
                "assessment_due_date": f"{current_year + 1}-04-30",
                "institution_idx": 1,  # RCC
            },
        ]

        term_ids = []
        for term_data in terms_data:
            if term_data["institution_idx"] < len(institution_ids):
                try:
                    schema = Term.create_schema(
                        name=term_data["name"],
                        start_date=term_data["start_date"],
                        end_date=term_data["end_date"],
                        assessment_due_date=term_data["assessment_due_date"],
                    )

                    # Database service expects 'term_name' field
                    schema["term_name"] = schema["name"]

                    # Add institution context
                    schema["institution_id"] = institution_ids[
                        term_data["institution_idx"]
                    ]

                    term_id = db.create_term(schema)
                    if term_id:
                        term_ids.append(term_id)
                        self.created_entities["terms"].append(term_id)
                        self.log(f"   Created term: {term_data['name']}")
                    else:
                        self.log(f"   Failed to create term: {term_data['name']}")

                except Exception as e:
                    self.log(f"   Error creating term {term_data['name']}: {e}")

        return term_ids

    def create_courses(
        self, institution_ids: List[str], program_ids: List[str]
    ) -> List[str]:
        """Create sample courses"""
        self.log("📖 Creating sample courses...")

        courses_data = [
            # CEI CS Courses
            {
                "course_number": "CS-101",
                "course_title": "Introduction to Computer Science",
                "department": "Computer Science",
                "credit_hours": 3,
                "institution_idx": 0,
                "program_ids": [0],  # CS program
            },
            {
                "course_number": "CS-201",
                "course_title": "Data Structures and Algorithms",
                "department": "Computer Science",
                "credit_hours": 4,
                "institution_idx": 0,
                "program_ids": [0],  # CS program
            },
            # CEI EE Courses
            {
                "course_number": "EE-101",
                "course_title": "Circuit Analysis",
                "department": "Electrical Engineering",
                "credit_hours": 4,
                "institution_idx": 0,
                "program_ids": [1],  # EE program
            },
            {
                "course_number": "EE-201",
                "course_title": "Digital Logic Design",
                "department": "Electrical Engineering",
                "credit_hours": 3,
                "institution_idx": 0,
                "program_ids": [1],  # EE program
            },
            {
                "course_number": "EE-301",
                "course_title": "Signals and Systems",
                "department": "Electrical Engineering",
                "credit_hours": 4,
                "institution_idx": 0,
                "program_ids": [1],  # EE program
            },
            # CEI General Studies
            {
                "course_number": "GEN-100",
                "course_title": "First Year Seminar",
                "department": "Academic Success",
                "credit_hours": 1,
                "institution_idx": 0,
                "program_ids": [2],  # General Studies
            },
            # RCC Courses
            {
                "course_number": "ENG-101",
                "course_title": "English Composition",
                "department": "English",
                "credit_hours": 3,
                "institution_idx": 1,
                "program_ids": [3],  # Liberal Arts
            },
            {
                "course_number": "ENG-102",
                "course_title": "Literature and Critical Thinking",
                "department": "English",
                "credit_hours": 3,
                "institution_idx": 1,
                "program_ids": [3],  # Liberal Arts
            },
            {
                "course_number": "BUS-101",
                "course_title": "Introduction to Business",
                "department": "Business",
                "credit_hours": 3,
                "institution_idx": 1,
                "program_ids": [4],  # Business Administration
            },
            {
                "course_number": "BUS-201",
                "course_title": "Business Ethics and Communication",
                "department": "Business",
                "credit_hours": 3,
                "institution_idx": 1,
                "program_ids": [4],  # Business Administration
            },
            {
                "course_number": "HIST-101",
                "course_title": "American History Survey",
                "department": "History",
                "credit_hours": 3,
                "institution_idx": 1,
                "program_ids": [3],  # Liberal Arts
            },
            # PTU Courses
            {
                "course_number": "ME-101",
                "course_title": "Engineering Mechanics",
                "department": "Mechanical Engineering",
                "credit_hours": 4,
                "institution_idx": 2,
                "program_ids": [6],  # Mechanical Engineering
            },
            {
                "course_number": "ME-201",
                "course_title": "Thermodynamics",
                "department": "Mechanical Engineering",
                "credit_hours": 4,
                "institution_idx": 2,
                "program_ids": [6],  # Mechanical Engineering
            },
            {
                "course_number": "MATH-201",
                "course_title": "Calculus for Engineers",
                "department": "Mathematics",
                "credit_hours": 4,
                "institution_idx": 2,
                "program_ids": [6, 7],  # ME and Pre-Engineering
            },
            {
                "course_number": "PHYS-101",
                "course_title": "Physics I: Mechanics",
                "department": "Physics",
                "credit_hours": 4,
                "institution_idx": 2,
                "program_ids": [6, 7],  # ME and Pre-Engineering
            },
        ]

        course_ids = []
        for course_data in courses_data:
            if course_data["institution_idx"] < len(institution_ids) and all(
                idx < len(program_ids) for idx in course_data["program_ids"]
            ):

                try:
                    # Map program indices to actual program IDs
                    course_program_ids = [
                        program_ids[idx] for idx in course_data["program_ids"]
                    ]

                    schema = Course.create_schema(
                        course_number=course_data["course_number"],
                        course_title=course_data["course_title"],
                        department=course_data["department"],
                        institution_id=institution_ids[course_data["institution_idx"]],
                        credit_hours=course_data["credit_hours"],
                        program_ids=course_program_ids,
                    )

                    course_id = db.create_course(schema)
                    if course_id:
                        course_ids.append(course_id)
                        self.created_entities["courses"].append(course_id)
                        self.log(
                            f"   Created course: {course_data['course_number']} - {course_data['course_title']}"
                        )
                    else:
                        self.log(
                            f"   Failed to create course: {course_data['course_number']}"
                        )

                except Exception as e:
                    self.log(
                        f"   Error creating course {course_data['course_number']}: {e}"
                    )

        return course_ids

    def create_sections(
        self, course_ids: List[str], institution_ids: List[str]
    ) -> List[str]:
        """Create course sections for the created courses"""
        self.log("📋 Creating course sections...")

        from database_service import (
            create_course_section,
            get_active_terms,
            get_users_by_role,
        )
        from models import CourseSection

        section_ids = []

        # Get instructors for each institution (use get_all_users to ensure fresh data)
        from database_service import get_all_users

        instructors_by_institution = {}
        for institution_id in institution_ids:
            all_users = get_all_users(institution_id)
            instructors = [u for u in all_users if u.get("role") == "instructor"]
            instructors_by_institution[institution_id] = instructors
            self.log(
                f"   Found {len(instructors)} instructors for institution {institution_id}"
            )

        # Get terms for each institution
        terms_by_institution = {}
        for institution_id in institution_ids:
            terms = get_active_terms(institution_id)
            terms_by_institution[institution_id] = (
                terms[:1] if terms else []
            )  # Use first term

        # Create 1-2 sections per course
        for course_id in course_ids:
            try:
                # Get course details to find institution
                from database_service import get_course_by_id

                course = get_course_by_id(course_id)
                if not course:
                    continue

                institution_id = course.get("institution_id")
                if not institution_id:
                    continue

                # Get available instructors and terms for this institution
                instructors = instructors_by_institution.get(institution_id, [])
                terms = terms_by_institution.get(institution_id, [])

                if not terms:
                    self.log(
                        f"   No terms available for course {course.get('course_number', course_id)}"
                    )
                    continue

                term_id = terms[0]["term_id"]  # Use first available term

                # Create 1-2 sections per course
                sections_to_create = 1 if len(course_ids) > 10 else 2

                for section_num in range(1, sections_to_create + 1):
                    section_number = f"{section_num:03d}"  # 001, 002, etc.

                    # Assign instructor if available
                    instructor_id = None
                    if instructors:
                        instructor_id = instructors[
                            (section_num - 1) % len(instructors)
                        ]["user_id"]

                    # Create section schema
                    section_data = {
                        "course_id": course_id,
                        "term_id": term_id,
                        "section_number": section_number,
                        "instructor_id": instructor_id,
                        "institution_id": institution_id,  # Add institution_id for filtering
                        "course_number": course.get(
                            "course_number", "Unknown"
                        ),  # Add for display
                        "enrollment": 15 + (section_num * 5),  # Vary enrollment
                        "status": "assigned" if instructor_id else "unassigned",
                    }

                    section_id = create_course_section(section_data)
                    if section_id:
                        section_ids.append(section_id)
                        self.created_entities["sections"].append(section_id)
                        instructor_name = next(
                            (
                                i["display_name"]
                                for i in instructors
                                if i["user_id"] == instructor_id
                            ),
                            "Unassigned",
                        )
                        self.log(
                            f"   Created section: {course.get('course_number', 'Unknown')}-{section_number} ({instructor_name})"
                        )
                    else:
                        self.log(
                            f"   Failed to create section for course {course.get('course_number', course_id)}"
                        )

            except Exception as e:
                self.log(f"   Error creating sections for course {course_id}: {e}")

        self.log(f"   Created {len(section_ids)} course sections")
        return section_ids

    def create_course_outcomes(self, course_ids: List[str]) -> List[str]:
        """Create course learning outcomes (CLOs) for courses"""
        self.log("🎯 Creating course learning outcomes (CLOs)...")

        from database_service import create_course_outcome, get_course_by_id
        from models import CourseOutcome

        outcome_ids = []

        # Sample CLO templates by course subject
        clo_templates = {
            "CS": [
                {
                    "clo_number": "CLO1",
                    "description": "Students will demonstrate proficiency in fundamental programming concepts including variables, control structures, and functions.",
                    "assessment_method": "Programming assignments and exams",
                },
                {
                    "clo_number": "CLO2",
                    "description": "Students will analyze and solve computational problems using appropriate algorithms and data structures.",
                    "assessment_method": "Project deliverables and practical assessments",
                },
                {
                    "clo_number": "CLO3",
                    "description": "Students will effectively communicate technical solutions through documentation and presentations.",
                    "assessment_method": "Technical reports and oral presentations",
                },
            ],
            "EE": [
                {
                    "clo_number": "CLO1",
                    "description": "Students will apply fundamental electrical engineering principles to analyze circuits and systems.",
                    "assessment_method": "Laboratory reports and circuit analysis assignments",
                },
                {
                    "clo_number": "CLO2",
                    "description": "Students will design and implement electrical systems that meet specified requirements.",
                    "assessment_method": "Design projects and practical demonstrations",
                },
                {
                    "clo_number": "CLO3",
                    "description": "Students will use industry-standard tools and measurement techniques in electrical engineering practice.",
                    "assessment_method": "Laboratory exercises and equipment proficiency tests",
                },
            ],
            "ENG": [
                {
                    "clo_number": "CLO1",
                    "description": "Students will produce clear, coherent, and well-organized written compositions.",
                    "assessment_method": "Essay assignments and portfolio review",
                },
                {
                    "clo_number": "CLO2",
                    "description": "Students will demonstrate critical thinking skills through analysis of texts and arguments.",
                    "assessment_method": "Analytical essays and discussion participation",
                },
            ],
            "BUS": [
                {
                    "clo_number": "CLO1",
                    "description": "Students will understand fundamental business concepts and their practical applications.",
                    "assessment_method": "Case study analysis and examinations",
                },
                {
                    "clo_number": "CLO2",
                    "description": "Students will analyze business problems and propose viable solutions.",
                    "assessment_method": "Business plan presentations and problem-solving exercises",
                },
            ],
            "ME": [
                {
                    "clo_number": "CLO1",
                    "description": "Students will apply principles of mechanics to analyze engineering systems.",
                    "assessment_method": "Problem sets and laboratory experiments",
                },
                {
                    "clo_number": "CLO2",
                    "description": "Students will design mechanical systems that meet specified performance criteria.",
                    "assessment_method": "Design projects and CAD modeling assignments",
                },
            ],
        }

        for course_id in course_ids:
            try:
                # Get course details
                course = get_course_by_id(course_id)
                if not course:
                    continue

                course_number = course.get("course_number", "")
                subject = (
                    course_number.split("-")[0] if "-" in course_number else "GENERAL"
                )

                # Get appropriate CLO templates
                templates = clo_templates.get(
                    subject, clo_templates["CS"][:2]
                )  # Default to 2 CS CLOs

                for template in templates:
                    try:
                        # Create CLO schema
                        outcome_schema = CourseOutcome.create_schema(
                            course_id=course_id,
                            clo_number=template["clo_number"],
                            description=template["description"],
                            assessment_method=template["assessment_method"],
                        )

                        # Create outcome in database
                        outcome_id = create_course_outcome(outcome_schema)
                        outcome_ids.append(outcome_id)
                        self.created_entities["course_outcomes"].append(outcome_id)

                        self.log(
                            f"   Created CLO: {course_number} {template['clo_number']}"
                        )

                    except Exception as e:
                        self.log(f"   Error creating CLO for {course_number}: {e}")

            except Exception as e:
                self.log(f"   Error processing course {course_id}: {e}")

        self.log(f"   Created {len(outcome_ids)} course learning outcomes")
        return outcome_ids

    def create_sample_invitations(
        self, institution_ids: List[str], admin_ids: List[str]
    ) -> List[str]:
        """Create sample pending invitations"""
        self.log("📧 Creating sample invitations...")

        invitations_data = [
            {
                "email": "newprof@cei.edu",
                "role": "instructor",
                "institution_idx": 0,
                "admin_idx": 0,
                "personal_message": "Welcome to CEI! We are excited to have you join our Computer Science department.",
            },
            {
                "email": "dept.head@riverside.edu",
                "role": "program_admin",
                "institution_idx": 1,
                "admin_idx": 1,
                "personal_message": "Please join us as the new department head for Liberal Arts.",
            },
        ]

        invitation_ids = []
        for inv_data in invitations_data:
            if inv_data["institution_idx"] < len(institution_ids) and inv_data[
                "admin_idx"
            ] < len(admin_ids):

                try:
                    schema = UserInvitation.create_schema(
                        email=inv_data["email"],
                        role=inv_data["role"],
                        institution_id=institution_ids[inv_data["institution_idx"]],
                        invited_by=admin_ids[inv_data["admin_idx"]],
                        personal_message=inv_data["personal_message"],
                    )

                    invitation_id = db.create_invitation(schema)
                    if invitation_id:
                        invitation_ids.append(invitation_id)
                        self.created_entities["invitations"].append(invitation_id)
                        self.log(
                            f"   Created invitation: {inv_data['email']} as {inv_data['role']}"
                        )
                    else:
                        self.log(f"   Failed to create invitation: {inv_data['email']}")

                except Exception as e:
                    self.log(f"   Error creating invitation {inv_data['email']}: {e}")

        return invitation_ids

    def seed_full_dataset(self):
        """Create the complete test dataset"""
        self.log("🌱 Starting full database seeding...")

        # Create institutions first
        institution_ids = self.create_institutions()
        if not institution_ids:
            self.log("❌ Failed to create institutions. Aborting.")
            return False

        # Create site admin
        site_admin_id = self.create_site_admin()
        if not site_admin_id:
            self.log("❌ Failed to create site admin. Aborting.")
            return False

        # Create institution admins
        admin_ids = self.create_institution_admins(institution_ids)
        if not admin_ids:
            self.log("❌ Failed to create institution admins. Aborting.")
            return False

        # Create programs
        program_ids = self.create_programs(institution_ids, admin_ids)
        if not program_ids:
            self.log("❌ Failed to create programs. Aborting.")
            return False

        # Create program admins and instructors
        self.create_program_admins_and_instructors(institution_ids, program_ids)

        # Create terms
        self.create_terms(institution_ids)

        # Create courses
        course_ids = self.create_courses(institution_ids, program_ids)

        # Create course sections
        if course_ids:
            self.create_sections(course_ids, institution_ids)

        # Create course outcomes (CLOs)
        if course_ids:
            self.create_course_outcomes(course_ids)

        # Create sample invitations
        self.create_sample_invitations(institution_ids, admin_ids)

        self.log("✅ Database seeding completed successfully!")
        self.print_summary()
        return True

    def seed_minimal_dataset(self):
        """Create minimal dataset for basic testing"""
        self.log("🌱 Creating minimal test dataset...")

        # Create single institution
        institution_data = Institution.create_schema(
            name="Test University",
            short_name="TU",
            created_by="system",
            admin_email="admin@test.edu",
            website_url="https://test.edu",
        )

        institution_id = db.create_institution(institution_data)
        if not institution_id:
            self.log("❌ Failed to create test institution")
            return False

        self.created_entities["institutions"].append(institution_id)

        # Create site admin
        site_admin_id = self.create_site_admin()
        if not site_admin_id:
            return False

        # Create single institution admin
        try:
            password_hash = hash_password("TestAdmin123!")
            admin_schema = User.create_schema(
                email="admin@test.edu",
                first_name="Test",
                last_name="Admin",
                role="institution_admin",
                institution_id=institution_id,
                password_hash=password_hash,
                account_status="active",
            )
            admin_schema["email_verified"] = True

            admin_id = db.create_user(admin_schema)
            if admin_id:
                self.created_entities["users"].append(admin_id)
                self.log("   Created test admin: admin@test.edu / TestAdmin123!")

        except Exception as e:
            self.log(f"   Error creating test admin: {e}")
            return False

        # Create default program
        program_schema = Program.create_schema(
            name="Unclassified",
            short_name="UNCL",
            institution_id=institution_id,
            created_by=admin_id,
            description="Default program",
            is_default=True,
        )

        # Database service expects 'id' field, not 'program_id'
        program_schema["id"] = program_schema.pop("program_id")

        program_id = db.create_program(program_schema)
        if program_id:
            self.created_entities["programs"].append(program_id)
            self.log("   Created default program")

        self.log("✅ Minimal dataset created successfully!")
        self.print_summary()
        return True

    def print_summary(self):
        """Print summary of created entities"""
        self.log("\n📊 Seeding Summary:")
        for entity_type, entities in self.created_entities.items():
            if entities:
                self.log(f"   {entity_type.title()}: {len(entities)} created")

    def print_test_accounts(self):
        """Print test account information for UAT"""
        self.log("\n🔑 Test Accounts for UAT:")
        self.log("   Site Admin:")
        self.log("     Email: siteadmin@system.local")
        self.log("     Password: SiteAdmin123!")
        self.log("     Role: Site Administrator")
        self.log("")
        self.log("   Institution Admins:")
        self.log("     CEI: sarah.admin@cei.edu / InstitutionAdmin123!")
        self.log("     RCC: mike.admin@riverside.edu / InstitutionAdmin123!")
        self.log("     PTU: admin@pactech.edu / InstitutionAdmin123!")
        self.log("")
        self.log("   Program Admins:")
        self.log("     CEI CS/EE: lisa.prog@cei.edu / TestUser123!")
        self.log("     RCC Liberal Arts: robert.prog@riverside.edu / TestUser123!")
        self.log("")
        self.log("   Instructors:")
        self.log("     CEI CS: john.instructor@cei.edu / TestUser123!")
        self.log("     CEI EE: jane.instructor@cei.edu / TestUser123!")
        self.log("     RCC: susan.instructor@riverside.edu / TestUser123!")
        self.log("     PTU ME: david.instructor@pactech.edu / TestUser123!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Database seeding script for UAT testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python seed_db.py                 # Seed with full dataset
  python seed_db.py --clear         # Clear existing data first
  python seed_db.py --minimal       # Create minimal dataset only
  python seed_db.py --clear --minimal  # Clear then create minimal dataset
        """,
    )

    parser.add_argument(
        "--clear", action="store_true", help="Clear existing test data before seeding"
    )

    parser.add_argument(
        "--minimal",
        action="store_true",
        help="Create minimal dataset instead of full dataset",
    )

    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")

    args = parser.parse_args()

    # Initialize seeder
    seeder = DatabaseSeeder(verbose=not args.quiet)

    # Check database connection
    if not db.check_db_connection():
        print(
            "❌ Database connection failed. Please check your Firestore configuration."
        )
        sys.exit(1)

    try:
        # Clear data if requested
        if args.clear:
            seeder.clear_database()

        # Seed database
        if args.minimal:
            success = seeder.seed_minimal_dataset()
        else:
            success = seeder.seed_full_dataset()

        if success:
            seeder.print_test_accounts()
            print(
                "\n🎯 Ready for UAT testing! Use the accounts above to test different user roles."
            )
        else:
            print("❌ Database seeding failed. Check the logs above for details.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ Seeding interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error during seeding: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
