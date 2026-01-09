#!/usr/bin/env python3
"""
Baseline Database Seeding for E2E Tests

Creates minimal shared infrastructure needed across all E2E tests.
Tests create their own specific data (users, sections) via API calls.
"""

import argparse
import json
import math
import os
import random
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import src.database.database_service as database_service
from src.models.models import (
    Course,
    CourseOffering,
    CourseSection,
    Institution,
    Program,
    Term,
    User,
)
from src.services.password_service import hash_password

# Constants
SITE_ADMIN_INSTITUTION_ID = 1
PROGRAM_DEFAULT_DESCRIPTION = "A sample academic program."

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class BaselineSeeder(ABC):
    """
    Abstract base class for database seeding operations.

    Provides shared utilities for manifest loading, logging, and database interaction.
    Subclasses implement specific seeding strategies (test vs demo vs production).

    TODO (Future - Phase 2): Move all hardcoded data from subclasses to JSON manifests.
    See SEED_DB_REFACTOR_PLAN.md for migration strategy.
    """

    def __init__(self):
        self.created = {
            "institutions": [],
            "users": [],
            "programs": [],
            "terms": [],
            "courses": [],
        }

    def log(self, message: str):
        """Log with [SEED] prefix"""
        print(f"[SEED] {message}")

    def load_manifest(self, manifest_path: Optional[str]) -> Dict[str, Any]:
        """Load and parse manifest JSON file (shared utility)"""
        if not manifest_path:
            return {}

        try:
            manifest_file = Path(manifest_path)
            if manifest_file.exists():
                self.log(f"📋 Loading manifest from {manifest_path}")
                with open(manifest_file, "r") as f:
                    return json.load(f)
            else:
                self.log(f"⚠️  Manifest not found at {manifest_path}, using defaults")
                return {}
        except Exception as e:
            self.log(f"⚠️  Failed to load manifest: {e}")
            return {}

    def create_institutions_from_manifest(
        self, institutions_data: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Create institutions from manifest data.

        Args:
            institutions_data: List of institution dictionaries

        Returns:
            List of created/existing institution IDs
        """
        institution_ids = []
        for inst_data in institutions_data:
            short_name = inst_data.get("short_name", "")

            # Check if already exists
            existing = database_service.db.get_institution_by_short_name(short_name)
            if existing:
                institution_ids.append(existing["institution_id"])
                continue

            schema = Institution.create_schema(
                name=inst_data.get("name", short_name),
                short_name=short_name,
                admin_email=inst_data.get(
                    "admin_email", f"admin@{short_name.lower()}.test"
                ),
                website_url=inst_data.get(
                    "website_url", f"https://{short_name.lower()}.test"
                ),
                created_by="system",
            )
            if inst_data.get("logo_path"):
                schema["logo_path"] = inst_data["logo_path"]

            inst_id = database_service.db.create_institution(schema)
            if inst_id:
                institution_ids.append(inst_id)
                self.created["institutions"].append(inst_id)
                self.log(f"   ✓ Created institution: {inst_data.get('name')}")

        return institution_ids

    def create_terms_from_manifest(
        self, institution_ids: List[str], terms_data: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Create terms from manifest data.

        Args:
            institution_ids: List of institution IDs to create terms for
            terms_data: List of term dictionaries with name, code, and offset days

        Returns:
            List of created term IDs
        """
        term_ids = []
        base_date = datetime.now(timezone.utc)

        for term_data in terms_data:
            for inst_id in institution_ids:
                # Calculate dates from offsets
                start_offset = term_data.get("start_offset_days", 0)
                end_offset = term_data.get("end_offset_days", 120)
                start_date = base_date + timedelta(days=start_offset)
                end_date = base_date + timedelta(days=end_offset)

                schema = Term.create_schema(
                    name=term_data.get("name", "Default Term"),
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    assessment_due_date=end_date.isoformat(),
                )
                schema["term_name"] = term_data.get("name")
                schema["term_code"] = term_data.get("code", "")
                schema["institution_id"] = inst_id

                term_id = database_service.db.create_term(schema)
                if term_id:
                    term_ids.append(term_id)
                    self.created["terms"].append(term_id)

        self.log(
            f"   ✓ Created {len(term_ids)} terms across {len(institution_ids)} institutions"
        )
        return term_ids

    def create_programs_from_manifest(
        self,
        institution_id_or_ids,
        programs_data: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Create programs from manifest data.

        Args:
            institution_id_or_ids: Single institution ID or list of institution IDs
            programs_data: List of program dictionaries with 'name', optional 'code', 'description', 'institution_idx'

        Returns:
            List of created program IDs
        """
        # Normalize to list
        institution_ids = (
            institution_id_or_ids
            if isinstance(institution_id_or_ids, list)
            else [institution_id_or_ids]
        )

        program_ids = []
        for prog_data in programs_data:
            # Determine institution - use institution_idx if provided, else first institution
            inst_idx = prog_data.get("institution_idx", 0)
            if inst_idx < len(institution_ids):
                institution_id = institution_ids[inst_idx]
            else:
                institution_id = institution_ids[0]

            schema = Program.create_schema(
                name=prog_data["name"],
                short_name=prog_data.get("code", prog_data["name"][:4].upper()),
                institution_id=institution_id,
                description=prog_data.get("description", PROGRAM_DEFAULT_DESCRIPTION),
                created_by="system",
            )

            prog_id = database_service.db.create_program(schema)
            if prog_id:
                program_ids.append(prog_id)
                self.created["programs"].append(prog_id)
                self.log(f"   ✓ Created program: {prog_data['name']}")

        return program_ids

    def create_courses_from_manifest(
        self,
        institution_id_or_ids,
        courses_data: List[Dict[str, Any]],
        program_ids_or_map,
    ) -> List[str]:
        """
        Create courses from manifest data.

        Args:
            institution_id_or_ids: Single institution ID or list of institution IDs
            courses_data: List of course dictionaries with 'code', 'name', 'credits', 'program_code' or 'program_idx'
            program_ids_or_map: Either a Dict mapping program codes to IDs, or a List of program IDs

        Returns:
            List of created course IDs
        """
        # Normalize institutions
        institution_ids = (
            institution_id_or_ids
            if isinstance(institution_id_or_ids, list)
            else [institution_id_or_ids]
        )

        # Normalize program reference - can be dict (code->id) or list (by index)
        program_map = (
            program_ids_or_map if isinstance(program_ids_or_map, dict) else None
        )
        program_list = (
            program_ids_or_map if isinstance(program_ids_or_map, list) else None
        )

        course_ids = []
        for course_data in courses_data:
            # Resolve program ID
            program_id = None
            if "program_code" in course_data and program_map:
                program_id = program_map.get(course_data["program_code"])
            elif "program_idx" in course_data and program_list:
                idx = course_data["program_idx"]
                if idx < len(program_list):
                    program_id = program_list[idx]

            if not program_id:
                self.log(
                    f"   ⚠️  No program found for course {course_data.get('code')}, skipping"
                )
                continue

            # Get institution from program if we have multiple
            program = database_service.db.get_program_by_id(program_id)
            institution_id = (
                program.get("institution_id") if program else institution_ids[0]
            )

            schema = Course.create_schema(
                course_number=course_data["code"],
                course_title=course_data["name"],
                department=(
                    course_data["code"].split("-")[0]
                    if "-" in course_data["code"]
                    else course_data["code"][:4]
                ),
                institution_id=institution_id,
                credit_hours=course_data.get("credits", 3),
                program_ids=[program_id],
                active=True,
            )

            course_id = database_service.db.create_course(schema)
            if course_id:
                course_ids.append(course_id)
                self.created["courses"].append(course_id)
                self.log(
                    f"   ✓ Created course: {course_data['code']} - {course_data['name']}"
                )

        return course_ids

    def create_users_from_manifest(
        self,
        institution_id: str,
        users_data: List[Dict[str, Any]],
        program_map: Dict[str, str],
        default_password_hash: str,
    ) -> List[str]:
        """
        Create users from manifest data.

        Args:
            institution_id: The institution to create users for
            users_data: List of user dictionaries with email, first_name, last_name, role, program_code
            program_map: Dict mapping program codes to program IDs
            default_password_hash: Hashed password to use for all users

        Returns:
            List of created user IDs
        """
        user_ids = []
        for user_data in users_data:
            email = user_data.get("email")
            if not email:
                continue

            # Skip if user already exists
            existing = database_service.db.get_user_by_email(email)
            if existing:
                user_ids.append(existing["user_id"])
                continue

            # Resolve program IDs
            program_code = user_data.get("program_code", "")
            program_ids = []
            if program_code and program_code in program_map:
                program_ids = [program_map[program_code]]

            schema = User.create_schema(
                email=email,
                first_name=user_data.get("first_name", ""),
                last_name=user_data.get("last_name", ""),
                role=user_data.get("role", "instructor"),
                institution_id=institution_id,
                password_hash=default_password_hash,
                account_status="active",
                program_ids=program_ids,
            )
            schema["email_verified"] = True

            user_id = database_service.db.create_user(schema)
            if user_id:
                user_ids.append(user_id)
                self.created["users"].append(user_id)
                self.log(
                    f"   ✓ Created user: {user_data.get('first_name')} {user_data.get('last_name')} ({user_data.get('role')})"
                )

        return user_ids

    def create_offerings_from_manifest(
        self,
        institution_id: str,
        term_id: str,
        offerings_data: List[Dict[str, Any]],
        course_map: Dict[str, str],
        instructor_ids: List[str],
        assessment_due_date: str = "2025-12-15T23:59:59",
    ) -> Dict[str, Any]:
        """
        Create offerings and sections from manifest data.

        Args:
            institution_id: The institution to create offerings for
            term_id: The term to create offerings for
            offerings_data: List of offering dicts with 'course_code' and 'sections'
            course_map: Dict mapping course codes to course IDs
            instructor_ids: List of instructor IDs for assignment
            assessment_due_date: Default due date for sections

        Returns:
            Dict with 'offering_ids' and 'section_count'
        """
        offering_ids = []
        section_count = 0

        for offering_data in offerings_data:
            course_code = offering_data.get("course_code", "")
            course_id = course_map.get(course_code)

            if not course_id:
                self.log(
                    f"   ⚠️  No course found for code '{course_code}', skipping offering"
                )
                continue

            # Create offering
            offering_schema = CourseOffering.create_schema(
                course_id=course_id,
                term_id=term_id,
                institution_id=institution_id,
            )
            offering_id = database_service.db.create_course_offering(offering_schema)
            if not offering_id:
                continue

            offering_ids.append(offering_id)

            # Create sections for this offering
            sections = offering_data.get("sections", [])
            for section_data in sections:
                instructor_idx = section_data.get("instructor_idx")
                instructor_id = None
                if instructor_idx is not None and instructor_idx < len(instructor_ids):
                    instructor_id = instructor_ids[instructor_idx]

                section_schema = CourseSection.create_schema(
                    offering_id=offering_id,
                    section_number=section_data.get("section_number", "001"),
                    instructor_id=instructor_id,
                    enrollment=section_data.get("enrollment", 0),
                    status=section_data.get("status", "assigned"),
                    assessment_due_date=assessment_due_date,
                )
                if database_service.db.create_course_section(section_schema):
                    section_count += 1

            self.log(
                f"   ✓ Created offering for {course_code} with {len(sections)} section(s)"
            )

        return {"offering_ids": offering_ids, "section_count": section_count}

    @abstractmethod
    def seed(self):
        """Implement seeding logic in subclasses"""
        pass


class BaselineTestSeeder(BaselineSeeder):
    """
    Seeds baseline test infrastructure for E2E/integration tests.

    Uses tests/fixtures/baseline_test_manifest.json for all data.
    Extends BaselineSeeder and uses its generic manifest methods.
    """

    DEFAULT_MANIFEST_PATH = "tests/fixtures/baseline_test_manifest.json"

    def __init__(self, manifest_path=None):
        super().__init__()
        self.manifest_path = manifest_path

    def seed(self):
        """Implementation of abstract seed method - calls seed_baseline()"""
        return self.seed_baseline()

    def _get_manifest_path(self):
        """Get the manifest path, relative to project root"""
        if self.manifest_path:
            return self.manifest_path

        # Find project root (where tests/ directory is)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        return os.path.join(project_root, self.DEFAULT_MANIFEST_PATH)

    def seed_baseline(self, manifest_data=None):
        """Seed baseline data from manifest"""
        self.log("🌱 Seeding baseline E2E infrastructure...")

        # Load manifest
        if manifest_data is None:
            manifest_path = self._get_manifest_path()
            manifest_data = self.load_manifest(manifest_path)

        # Create site admin first (special user, not from manifest)
        self.create_site_admin()

        # Create institutions
        self.log("🏢 Creating test institutions...")
        institutions_data = manifest_data.get("institutions", [])
        inst_ids = self.create_institutions_from_manifest(institutions_data)

        # Create programs
        self.log("📚 Creating academic programs...")
        programs_data = manifest_data.get("programs", [])
        prog_ids = self.create_programs_from_manifest(inst_ids, programs_data)

        # Create terms
        self.log("📅 Creating academic terms...")
        terms_data = manifest_data.get("terms", [])
        term_ids = self.create_terms_from_manifest(inst_ids, terms_data)

        # Create courses
        self.log("📖 Creating sample courses...")
        courses_data = manifest_data.get("courses", [])
        course_ids = self.create_courses_from_manifest(inst_ids, courses_data, prog_ids)

        # Create users (instructors, program admins, institution admins)
        self.log("👥 Creating users...")
        instructor_ids = self._create_test_users(inst_ids, prog_ids, manifest_data)

        # Create sections
        self.log("📝 Creating sample sections...")
        offerings_data = manifest_data.get("offerings", [])
        if offerings_data:
            self._create_sections_from_manifest(
                offerings_data, course_ids, term_ids, instructor_ids, inst_ids
            )
        else:
            self._create_default_sections(
                course_ids, term_ids, instructor_ids, inst_ids
            )

        self.log("✅ Baseline seeding completed!")
        self.print_summary()
        return True

    def create_site_admin(self):
        """Create site administrator account (special bootstrap user)"""
        self.log("👑 Creating site administrator...")

        from tests.test_credentials import SITE_ADMIN_EMAIL, SITE_ADMIN_PASSWORD

        existing = database_service.db.get_user_by_email(SITE_ADMIN_EMAIL)
        if existing:
            return existing["user_id"]

        password_hash = hash_password(SITE_ADMIN_PASSWORD)
        schema = User.create_schema(
            email=SITE_ADMIN_EMAIL,
            first_name="Site",
            last_name="Administrator",
            role="site_admin",
            institution_id=SITE_ADMIN_INSTITUTION_ID,
            password_hash=password_hash,
            account_status="active",
        )
        schema["email_verified"] = True

        user_id = database_service.db.create_user(schema)
        if user_id:
            self.created["users"].append(user_id)
        return user_id

    def _create_test_users(self, inst_ids, prog_ids, manifest_data):
        """Create test users from manifest (instructors, admins, etc.)"""
        from tests.test_credentials import (
            INSTITUTION_ADMIN_EMAIL,
            INSTRUCTOR_EMAIL,
            INSTRUCTOR_PASSWORD,
            PROGRAM_ADMIN_EMAIL,
            PROGRAM_ADMIN_PASSWORD,
        )

        password_hash = hash_password(INSTRUCTOR_PASSWORD)
        instructor_ids = []

        # Get users from manifest
        users_data = manifest_data.get("users", [])
        institution_admins = manifest_data.get("institution_admins", [])

        # Process regular users (instructors, program admins)
        for user_data in users_data:
            user_id = self._create_single_test_user(
                user_data, inst_ids, prog_ids, password_hash
            )
            if user_id and user_data.get("role") == "instructor":
                instructor_ids.append(user_id)

        # Process institution admins
        for admin_data in institution_admins:
            self._create_single_test_user(
                admin_data,
                inst_ids,
                prog_ids,
                password_hash,
                default_role="institution_admin",
            )

        return instructor_ids

    def _create_single_test_user(
        self,
        user_data,
        inst_ids,
        prog_ids,
        default_password_hash,
        default_role="instructor",
    ):
        """Create a single user from manifest data"""
        # Resolve email (may be from env var)
        email = user_data.get("email")
        if not email and user_data.get("email_env_var"):
            from tests import test_credentials

            email = getattr(test_credentials, user_data["email_env_var"], None)

        if not email:
            return None

        # Skip if exists
        existing = database_service.db.get_user_by_email(email)
        if existing:
            return existing["user_id"]

        # Resolve institution
        inst_idx = user_data.get("institution_idx", 0)
        inst_id = inst_ids[inst_idx] if inst_idx < len(inst_ids) else inst_ids[0]

        # Resolve password
        password_hash = default_password_hash
        if user_data.get("password_env_var"):
            from tests import test_credentials

            pwd = getattr(test_credentials, user_data["password_env_var"], None)
            if pwd:
                password_hash = hash_password(pwd)

        # Resolve program
        program_ids = []
        if "program_idx" in user_data and prog_ids:
            prog_idx = user_data["program_idx"]
            if prog_idx < len(prog_ids):
                program_ids = [prog_ids[prog_idx]]

        role = user_data.get("role", default_role)

        schema = User.create_schema(
            email=email,
            first_name=user_data.get("first_name", "Test"),
            last_name=user_data.get("last_name", "User"),
            role=role,
            institution_id=inst_id,
            password_hash=password_hash,
            account_status="active",
            program_ids=program_ids,
        )
        schema["email_verified"] = True

        user_id = database_service.db.create_user(schema)
        if user_id:
            self.created["users"].append(user_id)
            self.log(
                f"   ✓ Created user: {user_data.get('first_name')} {user_data.get('last_name')} ({role})"
            )
        return user_id

    def _create_sections_from_manifest(
        self, offerings_data, course_ids, term_ids, instructor_ids, inst_ids
    ):
        """Create offerings and sections from manifest data"""
        section_count = 0
        for offering_data in offerings_data:
            course_idx = offering_data.get("course_idx", 0)
            term_idx = offering_data.get("term_idx", 0)

            if course_idx >= len(course_ids) or term_idx >= len(term_ids):
                continue

            course_id = course_ids[course_idx]
            term_id = term_ids[term_idx]

            # Create offering
            offering_schema = CourseOffering.create_schema(
                course_id=course_id,
                term_id=term_id,
                institution_id=inst_ids[0],
            )
            offering_id = database_service.db.create_course_offering(offering_schema)
            if not offering_id:
                continue

            # Create sections
            for section_data in offering_data.get("sections", []):
                instructor_idx = section_data.get("instructor_idx")
                instructor_id = None
                if instructor_idx is not None and instructor_idx < len(instructor_ids):
                    instructor_id = instructor_ids[instructor_idx]

                section_schema = CourseSection.create_schema(
                    offering_id=offering_id,
                    section_number=section_data.get("section_number", "001"),
                    instructor_id=instructor_id,
                    enrollment=section_data.get("enrollment", 0),
                    status=section_data.get("status", "assigned"),
                )
                if database_service.db.create_course_section(section_schema):
                    section_count += 1

        self.log(f"   ✓ Created {section_count} sections")

    def _create_default_sections(self, course_ids, term_ids, instructor_ids, inst_ids):
        """Create default sections when no manifest offerings provided"""
        offering_ids = []
        for course_id in course_ids[:3]:
            term_id = term_ids[1] if len(term_ids) > 1 else term_ids[0]
            schema = CourseOffering.create_schema(
                course_id=course_id,
                term_id=term_id,
                institution_id=inst_ids[0],
            )
            offering_id = database_service.db.create_course_offering(schema)
            if offering_id:
                offering_ids.append(offering_id)

        section_count = 0
        for i, offering_id in enumerate(offering_ids):
            instructor_id = (
                instructor_ids[i % len(instructor_ids)] if instructor_ids else None
            )

            schema = CourseSection.create_schema(
                offering_id=offering_id,
                section_number=f"00{i+1}",
                instructor_id=instructor_id,
                enrollment=0,
                status="assigned",
            )
            if database_service.db.create_course_section(schema):
                section_count += 1

        self.log(f"   ✓ Created {section_count} sections")

    def print_summary(self):
        """Print seeding summary"""
        self.log("")
        self.log("📊 Summary:")
        self.log(f"   Institutions: {len(self.created['institutions'])} created")
        self.log(f"   Users: {len(self.created['users'])} created")
        self.log(f"   Programs: {len(self.created['programs'])} created")
        self.log(f"   Terms: {len(self.created['terms'])} created")
        self.log(f"   Courses: {len(self.created['courses'])} created")
        self.log("")
        self.log("🔑 Bootstrap Accounts:")
        self.log("   Site Admin: siteadmin@system.local / SiteAdmin123!")
        self.log("")
        self.log("   Institution Admins:")
        self.log("      (See console output for created generic admins)")
        self.log("      Default Password: InstitutionAdmin123!")


class DatabaseSeeder:
    """
    Compatibility wrapper for integration tests.

    Integration tests expect DatabaseSeeder.seed_full_dataset() but we refactored
    to BaselineTestSeeder.seed_baseline() for E2E tests. This provides backward compatibility.
    """

    def __init__(self, verbose=True):
        self.seeder = BaselineTestSeeder()
        self.verbose = verbose

    def seed_full_dataset(self):
        """Seed the full baseline dataset (compatibility method)"""
        return self.seeder.seed_baseline()


class DemoSeeder(BaselineTestSeeder):
    """
    Complete seeding for product demonstrations (2025).

    Uses demos/full_semester_manifest.json for all data configuration.
    Extends BaselineTestSeeder and uses BaselineSeeder's generic manifest methods.
    Demo-specific logic (CLO scenarios, date override, historical data) is kept here.
    """

    DEFAULT_MANIFEST_PATH = "demos/full_semester_manifest.json"

    def __init__(self, manifest_path=None):
        super().__init__()
        self.manifest_path = manifest_path
        self._manifest_cache = None

    def seed(self):
        """Implementation of abstract seed method - calls seed_demo()"""
        return self.seed_demo()

    def log(self, message: str):
        """Log with [SEED] prefix"""
        print(f"[SEED] {message}")

    def load_demo_manifest(self):
        """Load demo data from external JSON (cached)"""
        if self._manifest_cache is not None:
            return self._manifest_cache

        try:
            if self.manifest_path:
                manifest_path = os.path.abspath(self.manifest_path)
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                manifest_path = os.path.join(
                    script_dir, "..", self.DEFAULT_MANIFEST_PATH
                )

            if os.path.exists(manifest_path):
                self.log(f"📋 Loading demo data from {manifest_path}")
                with open(manifest_path, "r") as f:
                    self._manifest_cache = json.load(f)
                    return self._manifest_cache
            else:
                self.log(f"⚠️  Manifest not found at {manifest_path}, using defaults")
                self._manifest_cache = {}
                return {}
        except Exception as e:
            self.log(f"⚠️  Failed to load manifest: {e}")
            self._manifest_cache = {}
            return {}

    def create_demo_institution(self, manifest_institutions):
        """Create demo institution from manifest - REQUIRED"""
        self.log("🏢 Creating demo institution...")

        if not manifest_institutions or len(manifest_institutions) == 0:
            self.log("❌ 'institutions' with at least one entry required in manifest")
            return None

        inst_manifest = manifest_institutions[0]
        short_name = inst_manifest.get("short_name")
        if not short_name:
            self.log("❌ 'institutions[0].short_name' required in manifest")
            return None

        existing = database_service.db.get_institution_by_short_name(short_name)
        if existing:
            return existing["institution_id"]

        inst_data = {
            "name": inst_manifest.get("name", short_name),
            "short_name": short_name,
            "admin_email": inst_manifest.get("admin_email", f"admin@{short_name.lower()}.example.com"),
            "website_url": inst_manifest.get("website_url", f"https://{short_name.lower()}.example.com"),
            "created_by": "system",
        }

        if inst_manifest.get("logo_path"):
            inst_data["logo_path"] = inst_manifest["logo_path"]
            self.log(f"   ✓ Using logo from manifest: {inst_data['logo_path']}")

        schema = Institution.create_schema(**inst_data)
        inst_id = database_service.db.create_institution(schema)
        if inst_id:
            self.created["institutions"].append(inst_id)
            self.log(f"   ✓ Created institution: {inst_data['name']}")
        return inst_id

    def create_admin_account(self, institution_id, manifest=None):
        """Create demo admin account from manifest"""
        self.log("👩‍💼 Creating Demo Admin (Institution Admin)...")

        if manifest is None:
            manifest = self.load_demo_manifest()

        admin_data = manifest.get("demo_admin", {})
        if not admin_data:
            self.log("❌ 'demo_admin' required in manifest")
            return None

        email = admin_data.get("email")
        if not email:
            self.log("❌ 'demo_admin.email' required in manifest")
            return None

        existing = database_service.db.get_user_by_email(email)
        if existing:
            return existing["user_id"]

        # Get password from env var if specified
        from tests.test_credentials import DEMO_PASSWORD

        password = DEMO_PASSWORD
        if admin_data.get("password_env_var"):
            from tests import test_credentials

            password = getattr(test_credentials, admin_data["password_env_var"], DEMO_PASSWORD)

        password_hash = hash_password(password)
        schema = User.create_schema(
            email=email,
            first_name=admin_data.get("first_name", "Demo"),
            last_name=admin_data.get("last_name", "Admin"),
            role="institution_admin",
            institution_id=institution_id,
            password_hash=password_hash,
            account_status="active",
        )
        schema["email_verified"] = True

        user_id = database_service.db.create_user(schema)
        if user_id:
            self.created["users"].append(user_id)
        return user_id

    def create_demo_term(self, institution_id, manifest_terms):
        """Create term from manifest - REQUIRED"""
        self.log("📅 Creating term...")

        if not manifest_terms or len(manifest_terms) == 0:
            self.log("❌ 'terms' with at least one entry required in manifest")
            return None

        # Use first term in manifest
        term_data = manifest_terms[0]

        if not term_data.get("name"):
            self.log("❌ 'terms[0].name' required in manifest")
            return None

        schema = Term.create_schema(
            name=term_data["name"],
            start_date=term_data["start_date"],
            end_date=term_data["end_date"],
            assessment_due_date=term_data["end_date"] + "T23:59:59",
        )
        schema["term_name"] = term_data["name"]
        schema["term_code"] = term_data.get("term_code", term_data["name"][:2].upper())
        schema["active"] = term_data.get("active", True)
        schema["institution_id"] = institution_id

        term_id = database_service.db.create_term(schema)
        if term_id:
            self.created["terms"].append(term_id)
            self.log(
                f"   ✓ Created term: {term_data['name']} ({term_data['start_date']} to {term_data['end_date']})"
            )
        return term_id

    def seed_demo(self):
        """Seed complete data for product demo - manifest required."""
        self.log("🎬 Seeding demo environment...")

        # Load manifest - REQUIRED
        manifest = self.load_demo_manifest()
        if not manifest:
            self.log("❌ Manifest is required for demo seeding")
            return False

        # Create site admin
        self.create_site_admin()

        # Create demo institution from manifest
        manifest_institutions = manifest.get("institutions")
        if not manifest_institutions:
            self.log("❌ 'institutions' required in manifest")
            return False
        inst_id = self.create_demo_institution(manifest_institutions)
        if not inst_id:
            return False

        # Create demo admin from manifest
        admin_id = self.create_admin_account(inst_id, manifest)
        if not admin_id:
            return False

        # Create programs from manifest - REQUIRED
        self.log("📚 Creating demo programs...")
        programs_data = manifest.get("programs")
        if not programs_data:
            self.log("❌ 'programs' required in manifest")
            return False
        program_ids = self.create_programs_from_manifest(inst_id, programs_data)

        # Build program_map
        program_map = {}
        for i, prog in enumerate(programs_data):
            if i < len(program_ids):
                program_map[prog.get("code", "")] = program_ids[i]

        # Create term from manifest - REQUIRED
        terms_data = manifest.get("terms")
        if not terms_data:
            self.log("❌ 'terms' required in manifest")
            return False
        term_id = self.create_demo_term(inst_id, terms_data)

        # Create courses from manifest - REQUIRED
        self.log("📖 Creating demo courses...")
        courses_data = manifest.get("courses")
        if not courses_data:
            self.log("❌ 'courses' required in manifest")
            return False
        course_ids = self.create_courses_from_manifest(inst_id, courses_data, program_map)

        # Build course_map
        course_map = {}
        for i, course in enumerate(courses_data):
            if i < len(course_ids):
                course_map[course.get("code", "")] = course_ids[i]

        # Link any additional course-program mappings
        self.link_courses_to_programs(inst_id)

        # Create faculty from manifest - REQUIRED
        self.log("👨‍🏫 Creating demo faculty...")
        users_data = manifest.get("users")
        if not users_data:
            self.log("❌ 'users' required in manifest")
            return False
        faculty_data = [u for u in users_data if u.get("role") == "instructor"]

        from tests.test_credentials import INSTRUCTOR_PASSWORD

        password_hash = hash_password(INSTRUCTOR_PASSWORD)
        instructor_ids = self.create_users_from_manifest(
            inst_id, faculty_data, program_map, password_hash
        )

        # Create offerings from manifest - REQUIRED
        self.log("📋 Creating demo offerings and sections...")
        offerings_data = manifest.get("offerings")
        if not offerings_data:
            self.log("❌ 'offerings' required in manifest")
            return False
        result = self.create_offerings_from_manifest(
            institution_id=inst_id,
            term_id=term_id,
            offerings_data=offerings_data,
            course_map=course_map,
            instructor_ids=instructor_ids,
        )
        self.log(
            f"   ✅ Created {len(result['offering_ids'])} offerings and {result['section_count']} sections"
        )

        # Create CLOs from manifest
        self.create_demo_clos(course_ids, manifest)
        self.create_scenario_specific_clos(course_ids, instructor_ids)
        self._apply_demo_clo_completion(course_ids, manifest)

        # Set demo date override
        self.set_admin_date_override()

        # Create historical data
        self.create_historical_data(
            inst_id, program_ids, manifest.get("historical_data")
        )

        self.log("✅ Demo seeding completed!")
        self.print_summary()
        return True

    def create_demo_clos(self, course_ids, manifest=None):
        """Create Course Learning Outcomes (CLOs) from manifest - REQUIRED"""
        self.log("🎯 Creating Course Learning Outcomes...")

        from src.models.models import CourseOutcome
        from src.utils.constants import CLOStatus

        if manifest is None:
            manifest = self.load_demo_manifest()

        clo_templates = manifest.get("clo_templates")
        if not clo_templates:
            self.log("❌ 'clo_templates' required in manifest")
            return

        # Get course info to match CLOs to courses
        courses = []
        for cid in course_ids:
            course = database_service.db.get_course_by_id(cid)
            if course:
                courses.append(course)

        clo_count = 0
        for course in courses:
            course_num = course.get("course_number", "")
            prefix = course_num.split("-")[0] if "-" in course_num else ""

            templates = clo_templates.get(prefix, [])
            course_id = course.get("id") or course.get("course_id")

            for template in templates:
                existing = database_service.db.get_course_outcomes(course_id)
                already_exists = any(
                    str(clo.get("clo_number")) == str(template["num"])
                    for clo in (existing or [])
                )

                if already_exists:
                    continue

                schema = CourseOutcome.create_schema(
                    course_id=course_id,
                    clo_number=str(template["num"]),
                    description=template["desc"],
                    assessment_method=template["method"],
                )
                schema["status"] = CLOStatus.ASSIGNED
                schema["active"] = True

                outcome_id = database_service.db.create_course_outcome(schema)
                if outcome_id:
                    clo_count += 1

        self.log(f"   ✅ Created {clo_count} CLOs across demo courses")

        # Create special CLOs from manifest demo_clos section
        demo_clos = manifest.get("demo_clos", [])
        for clo_data in demo_clos:
            target_course_idx = clo_data.get("course_idx", 0)
            if target_course_idx < len(course_ids):
                target_course_id = course_ids[target_course_idx]
                schema = CourseOutcome.create_schema(
                    course_id=target_course_id,
                    clo_number=str(clo_data.get("clo_number", "99")),
                    description=clo_data.get("description", "Bonus outcome"),
                    assessment_method=clo_data.get("assessment_method", "Project"),
                )
                status_str = clo_data.get("status", "unassigned")
                schema["status"] = (
                    CLOStatus.UNASSIGNED
                    if status_str == "unassigned"
                    else CLOStatus.ASSIGNED
                )
                schema["active"] = True

                if database_service.db.create_course_outcome(schema):
                    self.log(
                        f"   ✓ Created {status_str} CLO #{clo_data.get('clo_number')}"
                    )

    def create_scenario_specific_clos(self, course_ids, instructor_ids):
        """Create specific CLO scenarios for the narrative (Rework, NCI)"""
        self.log("🎭 Creating narrative-specific CLO scenarios...")

        manifest = self.load_demo_manifest()
        scenarios = manifest.get("demo_scenarios", {})

        from src.models.models import CourseOutcome
        from src.utils.constants import CLOApprovalStatus, CLOStatus

        # Helper to map string status to Enum if needed
        def get_status(status_str):
            mapping = {
                "submitted": CLOStatus.AWAITING_APPROVAL,
                "awaiting_approval": CLOStatus.AWAITING_APPROVAL,
                "needs_rework": CLOStatus.APPROVAL_PENDING,
                "never_coming_in": CLOStatus.NEVER_COMING_IN,
                "approved": CLOStatus.APPROVED,
            }
            return mapping.get(status_str, CLOStatus.ASSIGNED)

        # 1. "Needs Rework" Scenario
        rework_data = scenarios.get("needs_rework")
        if rework_data:
            course_num = rework_data.get("course_number")
            # Find course ID
            course_id = None
            for cid in course_ids:
                c = database_service.db.get_course_by_id(cid)
                if c and c.get("course_number") == course_num:
                    course_id = cid
                    break

            if course_id:
                schema = CourseOutcome.create_schema(
                    course_id=course_id,
                    clo_number=rework_data.get("clo_number"),
                    description=rework_data.get("description"),
                    assessment_method=rework_data.get("assessment_method"),
                )
                schema["status"] = get_status(rework_data.get("status"))
                schema["active"] = True

                if schema["status"] == CLOStatus.APPROVAL_PENDING:
                    schema["approval_status"] = CLOApprovalStatus.NEEDS_REWORK
                if database_service.db.create_course_outcome(schema):
                    self.log(
                        f"   ✓ Created 'Needs Rework' scenario (CLO #{rework_data.get('clo_number')})"
                    )

        # 2. "NCI" Scenario
        nci_data = scenarios.get("nci")
        if nci_data:
            course_num = nci_data.get("course_number")
            # Find course ID
            course_id = None
            for cid in course_ids:
                c = database_service.db.get_course_by_id(cid)
                if c and c.get("course_number") == course_num:
                    course_id = cid
                    break

            if course_id:
                schema = CourseOutcome.create_schema(
                    course_id=course_id,
                    clo_number=nci_data.get("clo_number"),
                    description=nci_data.get("description"),
                    assessment_method=nci_data.get("assessment_method"),
                )
                schema["status"] = get_status(nci_data.get("status"))
                schema["active"] = True

                if schema["status"] == CLOStatus.NEVER_COMING_IN:
                    schema["approval_status"] = CLOApprovalStatus.NEVER_COMING_IN

                if database_service.db.create_course_outcome(schema):
                    self.log(
                        f"   ✓ Created 'NCI' scenario (CLO #{nci_data.get('clo_number')})"
                    )

    def _apply_demo_clo_completion(self, course_ids, manifest):
        """Apply automatic CLO completion markers based on manifest target."""
        progress_settings = manifest.get("system_settings", {}).get("auto_progress", {})
        target_percent = progress_settings.get("clo_completion_target_percent")
        if target_percent is None:
            return

        try:
            percent_value = float(target_percent)
        except (TypeError, ValueError):
            self.log(
                f"   ⚠️ Invalid CLO completion percent '{target_percent}' - skipping automated progress"
            )
            return

        percent_value = max(0.0, min(100.0, percent_value))
        if percent_value <= 0 or not course_ids:
            return

        enrollment_clos = []
        for course_id in course_ids:
            outcomes = database_service.db.get_course_outcomes(course_id)
            for clo in outcomes:
                clo_number = clo.get("clo_number")
                if not clo_number or not str(clo_number).isdigit():
                    continue
                num = int(clo_number)
                if 1 <= num <= 3:
                    enrollment_clos.append(clo)

        total_clos = len(enrollment_clos)
        if not total_clos:
            return

        target_count = min(total_clos, math.ceil(total_clos * (percent_value / 100.0)))
        enrollment_clos.sort(
            key=lambda clo: (
                clo.get("course_number", ""),
                int(clo.get("clo_number") or 0),
            )
        )

        tools = ["Final Exam", "Capstone Project", "Lab Report", "Portfolio Review"]

        updated = 0
        status_updates = 0
        from src.utils.constants import CLOApprovalStatus, CLOStatus
        from src.utils.time_utils import get_current_time

        now_value = get_current_time()

        for idx, clo in enumerate(enrollment_clos[:target_count]):
            took = 22 + (idx % 4) * 3
            pass_delta = idx % 3
            passed = max(1, took - pass_delta)
            if passed > took:
                passed = took

            tool = tools[idx % len(tools)]
            if database_service.update_outcome_assessment(
                clo["outcome_id"],
                students_took=took,
                students_passed=passed,
                assessment_tool=tool,
            ):
                updated += 1
                if database_service.update_course_outcome(
                    clo["outcome_id"],
                    {
                        "status": CLOStatus.APPROVED,
                        "approval_status": CLOApprovalStatus.APPROVED,
                        "submitted_at": now_value,
                    },
                ):
                    status_updates += 1

        if status_updates:
            self.log(
                f"   ✅ Marked {status_updates} CLOs as approved ({percent_value}% target)"
            )

        if enrollment_clos[target_count:]:
            first_pending = enrollment_clos[target_count]
            database_service.update_course_outcome(
                first_pending["outcome_id"],
                {
                    "status": CLOStatus.AWAITING_APPROVAL,
                    "approval_status": CLOApprovalStatus.PENDING,
                },
            )

    def set_admin_date_override(self):
        """Set system date override for the demo admin"""
        self.log("⏰ Setting initial date override for admin...")

        manifest = self.load_demo_manifest()
        date_str = manifest.get("system_settings", {}).get("admin_date_override")

        if not date_str:
            self.log("   Info: No date override found in manifest system_settings")
            return

        admin_email = "demo2025.admin@example.com"
        user = database_service.db.get_user_by_email(admin_email)

        if user:
            try:
                override_date = datetime.fromisoformat(date_str)
                database_service.db.update_user(
                    user["user_id"], {"system_date_override": override_date}
                )
                self.log(f"   ✓ Set {admin_email} date to {date_str}")
            except ValueError:
                self.log(f"   ⚠️ Invalid date format in manifest: {date_str}")
        else:
            self.log(f"   ⚠️ Could not find {admin_email} to set date override")

    def link_courses_to_programs(self, institution_id):
        """Link courses to programs based on manifest mappings or course prefixes"""
        self.log("🔗 Linking courses to programs...")

        manifest = self.load_demo_manifest()

        # Get mappings from manifest or use empty dict (courses already linked during creation)
        course_mappings = manifest.get("system_settings", {}).get(
            "course_program_mappings", {}
        )

        if not course_mappings:
            self.log("   ℹ️  No additional course-program mappings in manifest")
            return

        # Get all courses and programs
        courses = database_service.db.get_all_courses(institution_id)
        programs = database_service.db.get_programs_by_institution(institution_id)

        if not courses or not programs:
            self.log("   ⚠️  No courses or programs found to link")
            return

        # Build program lookup by name
        program_lookup = {
            p.get("name"): (p.get("program_id") or p.get("id")) for p in programs
        }

        linked_count = 0
        for course in courses:
            course_number = course.get("course_number", "")
            prefix = course_number.split("-")[0] if "-" in course_number else None

            if prefix and prefix in course_mappings:
                program_name = course_mappings[prefix]
                program_id = program_lookup.get(program_name)

                if program_id:
                    try:
                        database_service.db.add_course_to_program(
                            course["id"], program_id
                        )
                        linked_count += 1
                    except Exception:  # nosec B110 - might already be linked
                        pass

        if linked_count > 0:
            self.log(f"   ✅ Linked {linked_count} courses to programs")
        else:
            self.log("   ℹ️  No new course-program links created")

    def create_historical_data(self, institution_id, program_ids, historical_data=None):
        """Create historical data from manifest"""
        self.log("📜 Creating historical data...")

        if not historical_data:
            self.log("   ⏭️  No historical data in manifest, skipping.")
            return

        from src.models.models import Course, CourseOffering, CourseOutcome, CourseSection, Term

        # 1. Create Term
        term_data = historical_data.get("term", {})
        if not term_data:
            return

        schema_term = Term.create_schema(
            name=term_data.get("name", "Historical Term"),
            start_date=term_data.get("start_date", "2025-01-01"),
            end_date=term_data.get("end_date", "2025-05-01"),
            assessment_due_date=term_data.get("end_date", "2025-05-01"),
        )
        schema_term["term_name"] = term_data.get("name")
        schema_term["term_code"] = term_data.get("term_code", "HIST")
        schema_term["institution_id"] = institution_id

        existing = database_service.db.get_term_by_name(
            term_data.get("name"), institution_id
        )
        if existing:
            term_id = existing.get("id") or existing.get("term_id")
        else:
            term_id = database_service.db.create_term(schema_term)
            if term_id:
                self.created["terms"].append(term_id)

        if not term_id:
            return

        # 2. Create Courses from manifest
        courses_data = historical_data.get("courses", [])
        course_map = {}  # code -> id

        for course_data in courses_data:
            program_id = None
            if "program_idx" in course_data and program_ids:
                idx = course_data["program_idx"]
                if idx < len(program_ids):
                    program_id = program_ids[idx]

            schema_course = Course.create_schema(
                course_title=course_data.get("name", "Historical Course"),
                course_number=course_data.get("code", "HIST-001"),
                department=course_data.get("department", "History"),
                institution_id=institution_id,
                credit_hours=course_data.get("credits", 3),
                program_ids=[program_id] if program_id else [],
            )

            course_id = database_service.db.create_course(schema_course)
            if course_id:
                self.created["courses"].append(course_id)
                course_map[course_data.get("code")] = course_id

                # Link to program if specified
                if program_id:
                    try:
                        database_service.db.add_course_to_program(course_id, program_id)
                    except Exception:  # nosec
                        pass

        # 3. Create CLOs from manifest
        clos_data = historical_data.get("clos", [])
        for clo_data in clos_data:
            course_code = clo_data.get("course_code")
            course_id = course_map.get(course_code)

            if not course_id:
                continue

            schema_clo = CourseOutcome.create_schema(
                course_id=course_id,
                clo_number=str(clo_data.get("clo_number", 1)),
                description=clo_data.get("description", "Historical outcome"),
                assessment_method=clo_data.get("assessment_method", "Essay"),
            )
            schema_clo["active"] = True
            database_service.db.create_course_outcome(schema_clo)

        # 4. Create Offerings and Sections from manifest
        offerings_data = historical_data.get("offerings", [])
        for offering_data in offerings_data:
            course_code = offering_data.get("course_code")
            course_id = course_map.get(course_code)

            if not course_id:
                continue

            offering_schema = CourseOffering.create_schema(
                course_id=course_id,
                term_id=term_id,
                institution_id=institution_id,
            )
            offering_id = database_service.db.create_course_offering(offering_schema)

            if offering_id:
                # Create sections
                for section_data in offering_data.get("sections", []):
                    section_schema = CourseSection.create_schema(
                        offering_id=offering_id,
                        section_number=section_data.get("section_number", "001"),
                        instructor_id=None,
                        enrollment=section_data.get("enrollment", 0),
                        status=section_data.get("status", "completed"),
                    )
                    database_service.db.create_course_section(section_schema)

        course_count = len(course_map)
        clo_count = len(clos_data)
        self.log(
            f"   ✓ Created '{term_data.get('name')}' term with {course_count} course(s) and {clo_count} CLO(s)"
        )

    def print_summary(self):
        """Print demo seeding summary"""
        self.log("")
        self.log("📊 Demo Environment Ready (2025):")
        self.log("   Institution: Demo University")
        self.log(f"   Programs: {len(self.created['programs'])} created")
        self.log(f"   Terms: {len(self.created['terms'])} created")
        self.log(f"   Courses: {len(self.created['courses'])} created")
        self.log(f"   Users: {len(self.created['users'])} created")
        self.log("")
        self.log("🔑 Demo Account Credentials:")
        self.log("   Email:    demo2025.admin@example.com")
        self.log("   Password: Demo2025!")
        self.log("")
        self.log("🎬 Next Steps:")
        self.log("   1. Start server: ./restart_server.sh dev")
        self.log("   2. Navigate to: http://localhost:3001")
        self.log("   3. Login with the credentials above")


def main():
    """Main seeding entry point"""
    parser = argparse.ArgumentParser(
        description="Seed baseline E2E test data",
        epilog="Examples:\n"
        "  python scripts/seed_database_service.db.py --demo --clear --env dev\n"
        "  python scripts/seed_database_service.db.py --clear --env e2e\n"
        "  python scripts/seed_database_service.db.py --env prod\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--clear", action="store_true", help="Clear database first")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Seed generic demo environment for product demonstrations",
    )
    parser.add_argument(
        "--env",
        choices=["dev", "e2e", "ci", "prod"],
        default="prod",
        help="Environment to seed (dev, e2e, ci, or prod). Determines which database file to use.",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        help="Path to JSON manifest file for custom seeding (overrides generic defaults)",
    )

    # Parse arguments and catch errors
    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code != 0:
            print("\n❌ ERROR: Invalid arguments provided")
            print("💡 TIP: Use --env dev (not just 'dev')")
            print("Run with -h or --help for usage information\n")
        raise

    # Map environment to database file
    db_mapping = {
        "dev": "sqlite:///course_records_dev.db",
        "e2e": "sqlite:///course_records_e2e.db",
        "ci": "sqlite:///course_records_ci.db",
        "prod": "sqlite:///course_records.db",
    }

    database_url = db_mapping[args.env]
    os.environ["DATABASE_URL"] = database_url

    # Log which database we're using
    db_file = database_url.replace("sqlite:///", "")
    print(f"[SEED] 🗄️  Using {args.env} database: {db_file}")

    # CRITICAL: Import database modules AFTER setting DATABASE_URL
    # This ensures the database_service initializes with the correct database
    import src.database.database_service as database_service

    db = database_service.refresh_connection()
    from src.models.models import Course, Institution, Program, Term, User
    from src.services.password_service import hash_password
    from src.utils.constants import (
        PROGRAM_DEFAULT_DESCRIPTION,
        SITE_ADMIN_INSTITUTION_ID,
    )

    # Inject imports into module globals so classes can use them
    globals()["db"] = db
    globals()["PROGRAM_DEFAULT_DESCRIPTION"] = PROGRAM_DEFAULT_DESCRIPTION
    globals()["SITE_ADMIN_INSTITUTION_ID"] = SITE_ADMIN_INSTITUTION_ID
    globals()["Course"] = Course
    globals()["Institution"] = Institution
    globals()["Program"] = Program
    globals()["Term"] = Term
    globals()["User"] = User
    globals()["hash_password"] = hash_password

    if args.demo:
        seeder = DemoSeeder(manifest_path=args.manifest)

        if args.clear:
            seeder.log("🧹 Clearing database...")
            from src.database.database_service import reset_database

            reset_database()

        success = seeder.seed_demo()
        sys.exit(0 if success else 1)
    else:
        seeder = BaselineTestSeeder()

        if args.clear:
            seeder.log("🧹 Clearing database...")
            from src.database.database_service import reset_database

            reset_database()

        # Load manifest if provided
        manifest_data = None
        if args.manifest:
            try:
                with open(args.manifest, "r") as f:
                    manifest_data = json.load(f)
                seeder.log(f"📄 Loaded custom manifest: {args.manifest}")
            except Exception as e:
                print(f"❌ Failed to load manifest: {e}")
                sys.exit(1)

        success = seeder.seed_baseline(manifest_data)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
