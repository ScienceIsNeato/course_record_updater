#!/usr/bin/env python3
"""
Baseline Database Seeding for E2E Tests

Creates minimal shared infrastructure needed across all E2E tests.
Tests create their own specific data (users, sections) via API calls.
"""

import argparse
import os
import sys
import random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class BaselineSeeder:
    """Seeds baseline shared infrastructure for E2E tests"""

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

    def create_institutions(self):
        """Create 3 test institutions"""
        self.log("🏢 Creating test institutions...")

        institutions = [
            {
                "name": "Mock University",
                "short_name": "MockU",
                "admin_email": "admin@mocku.test",
                "website_url": "https://mocku.test",
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
            existing = db.get_institution_by_short_name(inst_data["short_name"])
            if existing:
                institution_ids.append(existing["institution_id"])
                continue

            schema = Institution.create_schema(**inst_data)
            inst_id = db.create_institution(schema)
            if inst_id:
                institution_ids.append(inst_id)
                self.created["institutions"].append(inst_id)

        return institution_ids

    def create_site_admin(self):
        """Create site administrator account"""
        self.log("👑 Creating site administrator...")

        email = "siteadmin@system.local"
        password = "SiteAdmin123!"

        existing = db.get_user_by_email(email)
        if existing:
            return existing["user_id"]

        password_hash = hash_password(password)
        schema = User.create_schema(
            email=email,
            first_name="Site",
            last_name="Administrator",
            role="site_admin",
            institution_id=SITE_ADMIN_INSTITUTION_ID,
            password_hash=password_hash,
            account_status="active",
        )
        schema["email_verified"] = True

        user_id = db.create_user(schema)
        if user_id:
            self.created["users"].append(user_id)
        return user_id

    def create_institution_admins(self, institution_ids):
        """Create one institution admin per institution"""
        self.log("🎓 Creating institution administrators...")

        admins_data = [
            {"email": "sarah.admin@mocku.test", "first_name": "Sarah", "last_name": "Chen", "institution_idx": 0},
            {"email": "mike.admin@riverside.edu", "first_name": "Mike", "last_name": "Rodriguez", "institution_idx": 1},
            {"email": "admin@pactech.edu", "first_name": "Patricia", "last_name": "Kim", "institution_idx": 2},
        ]

        admin_ids = []
        for admin_data in admins_data:
            inst_id = institution_ids[admin_data["institution_idx"]]

            existing = db.get_user_by_email(admin_data["email"])
            if existing:
                admin_ids.append(existing["user_id"])
                continue

            password_hash = hash_password("InstitutionAdmin123!")
            schema = User.create_schema(
                email=admin_data["email"],
                first_name=admin_data["first_name"],
                last_name=admin_data["last_name"],
                role="institution_admin",
                institution_id=inst_id,
                password_hash=password_hash,
                account_status="active",
            )
            schema["email_verified"] = True

            user_id = db.create_user(schema)
            if user_id:
                admin_ids.append(user_id)
                self.created["users"].append(user_id)

        return admin_ids

    def create_programs(self, institution_ids):
        """Create academic programs"""
        self.log("📚 Creating academic programs...")

        programs_data = [
            {"name": "Computer Science", "code": "CS", "institution_idx": 0},
            {"name": "Electrical Engineering", "code": "EE", "institution_idx": 0},
            {"name": "Business Administration", "code": "BUS", "institution_idx": 0},
            {"name": "Liberal Arts", "code": "LA", "institution_idx": 1},
            {"name": "Nursing", "code": "NURS", "institution_idx": 1},
            {"name": "Mechanical Engineering", "code": "ME", "institution_idx": 2},
            {"name": "Computer Engineering", "code": "CE", "institution_idx": 2},
            {"name": "Civil Engineering", "code": "CIV", "institution_idx": 2},
        ]

        program_ids = []
        for prog_data in programs_data:
            inst_id = institution_ids[prog_data["institution_idx"]]

            schema = Program.create_schema(
                name=prog_data["name"],
                short_name=prog_data["code"],
                institution_id=inst_id,
                description=PROGRAM_DEFAULT_DESCRIPTION,
                created_by="system",
            )

            prog_id = db.create_program(schema)
            if prog_id:
                program_ids.append(prog_id)
                self.created["programs"].append(prog_id)

        return program_ids

    def create_terms(self, institution_ids):
        """Create academic terms"""
        self.log("📅 Creating academic terms...")

        base_date = datetime.now(timezone.utc)
        terms_data = [
            {"name": "Fall 2025", "code": "FA2025", "start_offset": -90, "end_offset": -1},
            {"name": "Spring 2026", "code": "SP2026", "start_offset": 0, "end_offset": 120},
            {"name": "Summer 2026", "code": "SU2026", "start_offset": 121, "end_offset": 180},
            {"name": "Fall 2026", "code": "FA2026", "start_offset": 181, "end_offset": 300},
            {"name": "Spring 2027", "code": "SP2027", "start_offset": 301, "end_offset": 420},
        ]

        term_ids = []
        for term_data in terms_data:
            for inst_id in institution_ids:
                start_date = base_date + timedelta(days=term_data["start_offset"])
                end_date = base_date + timedelta(days=term_data["end_offset"])

                schema = Term.create_schema(
                    name=term_data["name"],
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    assessment_due_date=end_date.isoformat(),
                    active=True,
                )
                # Database layer expects both 'name' and 'term_name'
                schema["term_name"] = term_data["name"]
                schema["term_code"] = term_data["code"]
                schema["institution_id"] = inst_id

                term_id = db.create_term(schema)
                if term_id:
                    term_ids.append(term_id)
                    self.created["terms"].append(term_id)

        return term_ids

    def create_sample_courses(self, institution_ids, program_ids):
        """Create sample courses"""
        self.log("📖 Creating sample courses...")

        courses_data = [
            {"name": "Introduction to Programming", "code": "CS101", "credits": 3, "program_idx": 0},
            {"name": "Data Structures", "code": "CS201", "credits": 4, "program_idx": 0},
            {"name": "Circuit Analysis", "code": "EE101", "credits": 4, "program_idx": 1},
            {"name": "English Composition", "code": "ENG101", "credits": 3, "program_idx": 3},
            {"name": "Thermodynamics", "code": "ME201", "credits": 3, "program_idx": 5},
        ]

        course_ids = []
        for course_data in courses_data:
            program_id = program_ids[course_data["program_idx"]]
            program = db.get_program_by_id(program_id)

            schema = Course.create_schema(
                course_number=course_data["code"],
                course_title=course_data["name"],
                department=course_data["code"][:2],  # Extract dept from code (e.g., "CS" from "CS101")
                institution_id=program["institution_id"],
                credit_hours=course_data["credits"],
                program_ids=[program_id],
                active=True,
            )

            course_id = db.create_course(schema)
            if course_id:
                course_ids.append(course_id)
                self.created["courses"].append(course_id)

        return course_ids

    def create_sample_instructors(self, institution_ids, program_ids):
        """Create sample instructors for dashboard display tests"""
        self.log("👨‍🏫 Creating sample instructors...")
        
        instructors_data = [
            {"email": "john.instructor@mocku.test", "first_name": "John", "last_name": "Smith", "institution_idx": 0, "program_idx": 0},
            {"email": "jane.instructor@mocku.test", "first_name": "Jane", "last_name": "Doe", "institution_idx": 0, "program_idx": 1},
        ]
        
        instructor_ids = []
        password_hash = hash_password("Instructor123!")
        
        for inst_data in instructors_data:
            inst_id = institution_ids[inst_data["institution_idx"]]
            
            existing = db.get_user_by_email(inst_data["email"])
            if existing:
                instructor_ids.append(existing["user_id"])
                continue
            
            schema = User.create_schema(
                email=inst_data["email"],
                first_name=inst_data["first_name"],
                last_name=inst_data["last_name"],
                role="instructor",
                institution_id=inst_id,
                password_hash=password_hash,
                account_status="active",
                program_ids=[program_ids[inst_data["program_idx"]]],
            )
            schema["email_verified"] = True
            
            user_id = db.create_user(schema)
            if user_id:
                instructor_ids.append(user_id)
                self.created["users"].append(user_id)
        
        return instructor_ids

    def create_sample_program_admins(self, institution_ids, program_ids):
        """Create sample program admin for E2E tests"""
        self.log("👔 Creating sample program admin...")
        
        # Create CS program admin
        email = "bob.programadmin@mocku.test"
        existing = db.get_user_by_email(email)
        if existing:
            return existing["user_id"]
        
        password_hash = hash_password("ProgramAdmin123!")
        schema = User.create_schema(
            email=email,
            first_name="Bob",
            last_name="ProgramAdmin",
            role="program_admin",
            institution_id=institution_ids[0],  # MockU
            password_hash=password_hash,
            account_status="active",
            program_ids=[program_ids[0]],  # CS program
        )
        schema["email_verified"] = True
        
        user_id = db.create_user(schema)
        if user_id:
            self.created["users"].append(user_id)
        
        return user_id

    def create_sample_sections(self, course_ids, term_ids, instructor_ids, institution_ids):
        """Create sample sections for dashboard display tests"""
        self.log("📝 Creating sample sections...")

        from models import CourseOffering, CourseSection

        # Create course offerings first (required for sections)
        offering_ids = []
        for course_id in course_ids[:3]:  # First 3 courses
            # Use Spring 2025 term (index 1)
            term_id = term_ids[1] if len(term_ids) > 1 else term_ids[0]
            schema = CourseOffering.create_schema(
                course_id=course_id,
                term_id=term_id,
                institution_id=institution_ids[0],  # MockU
                status="active",
            )
            offering_id = db.create_course_offering(schema)
            if offering_id:
                offering_ids.append(offering_id)
        
        # Create sections
        section_count = 0
        for i, offering_id in enumerate(offering_ids):
            instructor_id = instructor_ids[i % len(instructor_ids)]  # Rotate instructors
            
            schema = CourseSection.create_schema(
                offering_id=offering_id,
                section_number=f"00{i+1}",
                instructor_id=instructor_id,
                enrollment=0,
                status="assigned",
            )
            section_id = db.create_course_section(schema)
            if section_id:
                section_count += 1
        
        self.log(f"   ✓ Created {section_count} sections")

    def seed_baseline(self):
        """Seed baseline shared infrastructure"""
        self.log("🌱 Seeding baseline E2E infrastructure...")

        institution_ids = self.create_institutions()
        if not institution_ids:
            return False

        if not self.create_site_admin():
            return False

        admin_ids = self.create_institution_admins(institution_ids)
        if not admin_ids:
            return False

        program_ids = self.create_programs(institution_ids)
        if not program_ids:
            return False

        term_ids = self.create_terms(institution_ids)
        if not term_ids:
            return False

        course_ids = self.create_sample_courses(institution_ids, program_ids)
        
        # Create sample instructors, program admin, and sections for E2E tests
        instructor_ids = self.create_sample_instructors(institution_ids, program_ids)
        self.create_sample_program_admins(institution_ids, program_ids)
        if instructor_ids:
            self.create_sample_sections(course_ids, term_ids, instructor_ids, institution_ids)

        self.log("✅ Baseline seeding completed!")
        self.print_summary()
        return True

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
        self.log("      MockU: sarah.admin@mocku.test / InstitutionAdmin123!")
        self.log("      RCC: mike.admin@riverside.edu / InstitutionAdmin123!")
        self.log("      PTU: admin@pactech.edu / InstitutionAdmin123!")
        self.log("")
        self.log("   Program Admin (CS @ MockU):")
        self.log("      bob.programadmin@mocku.test / ProgramAdmin123!")
        self.log("")
        self.log("   Sample Instructors:")
        self.log("      john.instructor@mocku.test / Instructor123!")
        self.log("      jane.instructor@mocku.test / Instructor123!")


class DatabaseSeeder:
    """
    Compatibility wrapper for integration tests.
    
    Integration tests expect DatabaseSeeder.seed_full_dataset() but we refactored
    to BaselineSeeder.seed_baseline() for E2E tests. This provides backward compatibility.
    """

    def __init__(self, verbose=True):
        self.seeder = BaselineSeeder()
        self.verbose = verbose

    def seed_full_dataset(self):
        """Seed the full baseline dataset (compatibility method)"""
        return self.seeder.seed_baseline()


class DemoSeeder(BaselineSeeder):
    """Complete seeding for product demonstrations (2025)"""

    def __init__(self):
        super().__init__()

    def log(self, message: str):
        """Log with [SEED] prefix"""
        print(f"[SEED] {message}")

    def create_demo_institution(self):
        """Create demo institution"""
        self.log("🏢 Creating Demo University...")

        existing = db.get_institution_by_short_name("DEMO2025")
        if existing:
            return existing["institution_id"]

        schema = Institution.create_schema(
            name="Demo University",
            short_name="DEMO2025",
            admin_email="demo2025.admin@example.com",
            website_url="https://demo.example.com",
            created_by="system",
        )

        inst_id = db.create_institution(schema)
        if inst_id:
            self.created["institutions"].append(inst_id)
        return inst_id

    def create_admin_account(self, institution_id):
        """Create demo admin account"""
        self.log("👩‍💼 Creating Demo Admin (Institution Admin)...")

        email = "demo2025.admin@example.com"
        password = "Demo2025!"

        existing = db.get_user_by_email(email)
        if existing:
            return existing["user_id"]

        password_hash = hash_password(password)
        schema = User.create_schema(
            email=email,
            first_name="Leslie",
            last_name="Jernberg",
            role="institution_admin",
            institution_id=institution_id,
            password_hash=password_hash,
            account_status="active",
        )
        schema["email_verified"] = True

        user_id = db.create_user(schema)
        if user_id:
            self.created["users"].append(user_id)
        return user_id

    def create_demo_programs(self, institution_id):
        """Create sample programs for CEI"""
        self.log("📚 Creating demo programs...")

        programs_data = [
            {"name": "Biological Sciences", "code": "BIOL"},
            {"name": "Zoology", "code": "ZOOL"},
        ]

        program_ids = []
        for prog_data in programs_data:
            schema = Program.create_schema(
                name=prog_data["name"],
                short_name=prog_data["code"],
                institution_id=institution_id,
                description=PROGRAM_DEFAULT_DESCRIPTION,
                created_by="system",
            )

            prog_id = db.create_program(schema)
            if prog_id:
                program_ids.append(prog_id)
                self.created["programs"].append(prog_id)

        return program_ids

    def create_demo_courses(self, institution_id, program_ids):
        """Create demo courses for Biology and Zoology programs"""
        self.log("📖 Creating demo courses...")

        # Map: [program_idx, course_number, course_title, credits]
        courses_data = [
            # Biological Sciences courses
            {"program_idx": 0, "code": "BIOL-101", "name": "Introduction to Biology", "credits": 4},
            {"program_idx": 0, "code": "BIOL-201", "name": "Cellular Biology", "credits": 4},
            {"program_idx": 0, "code": "BIOL-301", "name": "Genetics", "credits": 3},
            # Zoology courses  
            {"program_idx": 1, "code": "ZOOL-101", "name": "Animal Diversity", "credits": 4},
            {"program_idx": 1, "code": "ZOOL-205", "name": "Vertebrate Anatomy", "credits": 4},
            {"program_idx": 1, "code": "ZOOL-310", "name": "Animal Behavior", "credits": 3},
        ]

        course_ids = []
        for course_data in courses_data:
            program_id = program_ids[course_data["program_idx"]]
            program = db.get_program_by_id(program_id)

            schema = Course.create_schema(
                course_number=course_data["code"],
                course_title=course_data["name"],
                department=course_data["code"].split("-")[0],
                institution_id=institution_id,
                credit_hours=course_data["credits"],
                program_ids=[program_id],
                active=True,
            )

            course_id = db.create_course(schema)
            if course_id:
                course_ids.append(course_id)
                self.created["courses"].append(course_id)

        return course_ids

    def create_demo_faculty(self, institution_id, program_ids):
        """Create demo faculty members"""
        self.log("👨‍🏫 Creating demo faculty...")

        faculty_data = [
            {"email": "dr.morgan@demo.example.com", "first_name": "Alex", "last_name": "Morgan", "program_idx": 0},
            {"email": "prof.chen@demo.example.com", "first_name": "Sarah", "last_name": "Chen", "program_idx": 0},
            {"email": "dr.patel@demo.example.com", "first_name": "Raj", "last_name": "Patel", "program_idx": 1},
        ]

        instructor_ids = []
        password_hash = hash_password("Instructor123!")

        for fac_data in faculty_data:
            existing = db.get_user_by_email(fac_data["email"])
            if existing:
                instructor_ids.append(existing["user_id"])
                continue

            schema = User.create_schema(
                email=fac_data["email"],
                first_name=fac_data["first_name"],
                last_name=fac_data["last_name"],
                role="instructor",
                institution_id=institution_id,
                password_hash=password_hash,
                account_status="active",
                program_ids=[program_ids[fac_data["program_idx"]]],
            )
            schema["email_verified"] = True

            user_id = db.create_user(schema)
            if user_id:
                instructor_ids.append(user_id)
                self.created["users"].append(user_id)

        return instructor_ids

    def create_demo_term(self, institution_id):
        """Create Fall 2025 term"""
        self.log("📅 Creating Fall 2025 term...")

        base_date = datetime.now(timezone.utc)
        start_date = base_date - timedelta(days=90)
        end_date = base_date + timedelta(days=30)

        schema = Term.create_schema(
            name="Fall 2025",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            assessment_due_date=end_date.isoformat(),
            active=True,
        )
        schema["term_name"] = "Fall 2025"
        schema["term_code"] = "FA2025"
        schema["institution_id"] = institution_id

        term_id = db.create_term(schema)
        if term_id:
            self.created["terms"].append(term_id)
        return term_id

    def create_demo_offerings_and_sections(self, institution_id, course_ids, term_id, instructor_ids):
        """Create course offerings and sections for demo"""
        self.log("📋 Creating demo offerings and sections...")

        from models import CourseOffering, CourseSection

        # Create offerings for all courses
        offering_ids = []
        for course_id in course_ids:
            schema = CourseOffering.create_schema(
                course_id=course_id,
                term_id=term_id,
                institution_id=institution_id,
                status="active",
            )
            offering_id = db.create_course_offering(schema)
            if offering_id:
                offering_ids.append(offering_id)

        # Create sections (one per offering, rotating through instructors)
        section_count = 0
        for i, offering_id in enumerate(offering_ids):
            instructor_id = instructor_ids[i % len(instructor_ids)]

            schema = CourseSection.create_schema(
                offering_id=offering_id,
                section_number=f"001",
                instructor_id=instructor_id,
                enrollment=random.randint(15, 35),
                status="assigned",
            )
            section_id = db.create_course_section(schema)
            if section_id:
                section_count += 1

        self.log(f"   ✅ Created {len(offering_ids)} offerings and {section_count} sections")

    def link_courses_to_programs(self, institution_id):
        """Link courses to programs based on course prefixes"""
        self.log("🔗 Linking courses to programs...")
        
        # Get all courses and programs
        courses = db.get_all_courses(institution_id)
        programs = db.get_programs_by_institution(institution_id)
        
        if not courses or not programs:
            self.log("   ⚠️  No courses or programs found to link")
            return
        
        # Build program lookup by name
        program_lookup = {p["name"]: p["id"] for p in programs}
        
        # Course prefix to program mapping
        course_mappings = {
            "BIOL": "Biological Sciences",
            "BSN": "Biological Sciences",
            "ZOOL": "Zoology",
            "CEI": "CEI Default Program",
        }
        
        linked_count = 0
        for course in courses:
            # Extract prefix from course number (e.g., "BIOL-228" -> "BIOL")
            course_number = course["course_number"]
            prefix = course_number.split("-")[0] if "-" in course_number else None
            
            if prefix and prefix in course_mappings:
                program_name = course_mappings[prefix]
                program_id = program_lookup.get(program_name)
                
                if program_id:
                    try:
                        db.add_course_to_program(course["id"], program_id)
                        linked_count += 1
                        self.log(f"   ✓ Linked {course_number} to {program_name}")
                    except Exception as e:
                        # Might already be linked, that's okay
                        pass
        
        if linked_count > 0:
            self.log(f"   ✅ Linked {linked_count} courses to programs")
        else:
            self.log("   ℹ️  No new course-program links created")

    def seed_demo(self):
        """Seed complete data for product demo - ready to showcase features!"""
        self.log("🎬 Seeding 2025 demo environment...")

        inst_id = self.create_demo_institution()
        if not inst_id:
            return False

        admin_id = self.create_admin_account(inst_id)
        if not admin_id:
            return False

        program_ids = self.create_demo_programs(inst_id)
        term_id = self.create_demo_term(inst_id)
        
        # Create complete demo data for showcasing features
        course_ids = self.create_demo_courses(inst_id, program_ids)
        instructor_ids = self.create_demo_faculty(inst_id, program_ids)
        self.create_demo_offerings_and_sections(inst_id, course_ids, term_id, instructor_ids)

        self.log("✅ Demo seeding completed!")
        self.print_summary()
        return True

    def print_summary(self):
        """Print demo seeding summary"""
        self.log("")
        self.log("📊 Demo Environment Ready (2025):")
        self.log(f"   Institution: Demo University")
        self.log(f"   Programs: {len(self.created['programs'])} created")
        self.log(f"   Terms: {len(self.created['terms'])} created")
        self.log(f"   Courses: {len(self.created['courses'])} created")
        self.log(f"   Faculty: {len([u for u in self.created['users'] if 'instructor' in str(u)])} created")
        self.log("")
        self.log("🔑 Demo Account Credentials:")
        self.log("   Email:    demo2025.admin@example.com")
        self.log("   Password: Demo2025!")
        self.log("")
        self.log("🚀 Ready to demo! The database is fully populated with:")
        self.log("   ✓ Courses across multiple programs")
        self.log("   ✓ Faculty members assigned to courses")
        self.log("   ✓ Course offerings and sections")
        self.log("")
        self.log("🎬 Next Steps:")
        self.log("   1. Start server: ./restart_server.sh dev")
        self.log("   2. Navigate to: http://localhost:3001")
        self.log("   3. Login with the credentials above")
        self.log("   4. Jump right into the killer features!")


def main():
    """Main seeding entry point"""
    parser = argparse.ArgumentParser(
        description="Seed baseline E2E test data",
        epilog="Examples:\n"
        "  python scripts/seed_db.py --demo --clear --env dev\n"
        "  python scripts/seed_db.py --clear --env e2e\n"
        "  python scripts/seed_db.py --env prod\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--clear", action="store_true", help="Clear database first")
    parser.add_argument("--demo", action="store_true", help="Seed generic demo environment for product demonstrations")
    parser.add_argument(
        "--env",
        choices=["dev", "e2e", "prod"],
        default="prod",
        help="Environment to seed (dev, e2e, or prod). Determines which database file to use.",
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
        "prod": "sqlite:///course_records.db",
    }
    
    database_url = db_mapping[args.env]
    os.environ["DATABASE_URL"] = database_url
    
    # Log which database we're using
    db_file = database_url.replace("sqlite:///", "")
    print(f"[SEED] 🗄️  Using {args.env} database: {db_file}")
    
    # CRITICAL: Import database modules AFTER setting DATABASE_URL
    # This ensures the database_service initializes with the correct database
    import database_service as db
    from constants import PROGRAM_DEFAULT_DESCRIPTION, SITE_ADMIN_INSTITUTION_ID
    from models import Course, Institution, Program, Term, User
    from password_service import hash_password

    # Inject imports into module globals so classes can use them
    globals()['db'] = db
    globals()['PROGRAM_DEFAULT_DESCRIPTION'] = PROGRAM_DEFAULT_DESCRIPTION
    globals()['SITE_ADMIN_INSTITUTION_ID'] = SITE_ADMIN_INSTITUTION_ID
    globals()['Course'] = Course
    globals()['Institution'] = Institution
    globals()['Program'] = Program
    globals()['Term'] = Term
    globals()['User'] = User
    globals()['hash_password'] = hash_password

    if args.demo:
        seeder = DemoSeeder()
        
        if args.clear:
            seeder.log("🧹 Clearing database...")
            db.reset_database()
        
        success = seeder.seed_demo()
        sys.exit(0 if success else 1)
    else:
        seeder = BaselineSeeder()

        if args.clear:
            seeder.log("🧹 Clearing database...")
            db.reset_database()

        success = seeder.seed_baseline()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
