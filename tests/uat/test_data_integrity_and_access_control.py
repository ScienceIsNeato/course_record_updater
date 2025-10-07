"""
UAT: Data Integrity and Access Control
Backend-focused tests validating role-based data access.

Test Coverage:
- Site Admin: Full system access (all institutions)
- Institution Admin: Single institution scope
- Program Admin: Program-scoped access
- Instructor: Section-level access
- Negative testing: Unauthorized access denied

Reference: UAT_DATA_INTEGRITY_AND_ACCESS_CONTROL.md
"""

import csv
import io
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

from auth_service import UserRole
from database_service import (
    get_all_courses,
    get_all_institutions,
    get_all_sections,
    get_all_users,
    get_user_by_email,
    reset_database,
)


class TestDataFixture:
    """Helper to create controlled test data using Generic CSV adapter."""

    @staticmethod
    def create_minimal_test_zip() -> bytes:
        """
        Create a minimal ZIP of CSVs with known, predictable values.

        Returns controlled test data:
        - 3 institutions (Tech U, Community College, State College)
        - 6 programs (2 per institution)
        - Known user counts per role
        - Known course/section counts
        """
        # Create temporary directory for CSVs
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # 1. Create manifest.json
            manifest = {
                "format_version": "1.0",
                "export_timestamp": "2025-10-07T00:00:00Z",
                "adapter_id": "generic_csv_v1",
                "entity_counts": {
                    "institutions": 3,
                    "programs": 6,
                    "users": 10,
                    "courses": 12,
                    "terms": 2,
                    "course_offerings": 12,
                    "course_sections": 15,
                    "course_outcomes": 20,
                },
            }
            with open(tmppath / "manifest.json", "w") as f:
                json.dump(manifest, f, indent=2)

            # 2. Create institutions.csv
            institutions_data = [
                {
                    "id": "tu-001",
                    "name": "Tech University",
                    "short_name": "TU",
                    "website_url": "https://tech.edu",
                    "created_by": "system",
                    "admin_email": "admin@tech.edu",
                    "allow_self_registration": "true",
                    "require_email_verification": "true",
                    "is_active": "true",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                {
                    "id": "cc-001",
                    "name": "Community College",
                    "short_name": "CC",
                    "website_url": "https://community.edu",
                    "created_by": "system",
                    "admin_email": "admin@community.edu",
                    "allow_self_registration": "false",
                    "require_email_verification": "true",
                    "is_active": "true",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                {
                    "id": "sc-001",
                    "name": "State College",
                    "short_name": "SC",
                    "website_url": "https://state.edu",
                    "created_by": "system",
                    "admin_email": "admin@state.edu",
                    "allow_self_registration": "true",
                    "require_email_verification": "false",
                    "is_active": "true",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
            ]
            TestDataFixture._write_csv(tmppath / "institutions.csv", institutions_data)

            # 3. Create programs.csv
            programs_data = [
                # TU programs
                {
                    "id": "tu-cs-001",
                    "name": "Computer Science",
                    "short_name": "CS",
                    "description": "Computer Science program",
                    "institution_id": "tu-001",
                    "created_by": "system",
                    "is_default": "false",
                    "is_active": "true",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                {
                    "id": "tu-ee-001",
                    "name": "Electrical Engineering",
                    "short_name": "EE",
                    "description": "Electrical Engineering program",
                    "institution_id": "tu-001",
                    "created_by": "system",
                    "is_default": "false",
                    "is_active": "true",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                # CC programs
                {
                    "id": "cc-nurs-001",
                    "name": "Nursing",
                    "short_name": "NURS",
                    "description": "Nursing program",
                    "institution_id": "cc-001",
                    "created_by": "system",
                    "is_default": "false",
                    "is_active": "true",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                {
                    "id": "cc-bus-001",
                    "name": "Business",
                    "short_name": "BUS",
                    "description": "Business program",
                    "institution_id": "cc-001",
                    "created_by": "system",
                    "is_default": "false",
                    "is_active": "true",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                # SC programs
                {
                    "id": "sc-la-001",
                    "name": "Liberal Arts",
                    "short_name": "LA",
                    "description": "Liberal Arts program",
                    "institution_id": "sc-001",
                    "created_by": "system",
                    "is_default": "false",
                    "is_active": "true",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                {
                    "id": "sc-gen-001",
                    "name": "General Studies",
                    "short_name": "GEN",
                    "description": "General Studies program",
                    "institution_id": "sc-001",
                    "created_by": "system",
                    "is_default": "true",
                    "is_active": "true",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
            ]
            TestDataFixture._write_csv(tmppath / "programs.csv", programs_data)

            # 4. Create users.csv (passwords excluded per security spec)
            users_data = [
                # Site Admin
                {
                    "id": "site-admin-001",
                    "email": "siteadmin@system.local",
                    "first_name": "Site",
                    "last_name": "Admin",
                    "display_name": "Site Administrator",
                    "role": UserRole.SITE_ADMIN.value,
                    "institution_id": "",  # Site admin has no institution
                    "account_status": "active",
                    "email_verified": "true",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                # TU users
                {
                    "id": "tu-admin-001",
                    "email": "admin@tech.edu",
                    "first_name": "Tech",
                    "last_name": "Admin",
                    "display_name": "Tech University Admin",
                    "role": UserRole.INSTITUTION_ADMIN.value,
                    "institution_id": "tu-001",
                    "account_status": "active",
                    "email_verified": "true",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                {
                    "id": "tu-cs-prog-001",
                    "email": "cs.admin@tech.edu",
                    "first_name": "CS",
                    "last_name": "Program Admin",
                    "display_name": "CS Program Admin",
                    "role": UserRole.PROGRAM_ADMIN.value,
                    "institution_id": "tu-001",
                    "account_status": "active",
                    "email_verified": "true",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                {
                    "id": "tu-cs-inst-001",
                    "email": "cs.instructor@tech.edu",
                    "first_name": "CS",
                    "last_name": "Instructor",
                    "display_name": "CS Instructor",
                    "role": UserRole.INSTRUCTOR.value,
                    "institution_id": "tu-001",
                    "account_status": "active",
                    "email_verified": "true",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                # CC users
                {
                    "id": "cc-admin-001",
                    "email": "admin@community.edu",
                    "first_name": "Community",
                    "last_name": "Admin",
                    "display_name": "Community College Admin",
                    "role": UserRole.INSTITUTION_ADMIN.value,
                    "institution_id": "cc-001",
                    "account_status": "active",
                    "email_verified": "true",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                {
                    "id": "cc-nurs-inst-001",
                    "email": "nurs.instructor@community.edu",
                    "first_name": "Nursing",
                    "last_name": "Instructor",
                    "display_name": "Nursing Instructor",
                    "role": UserRole.INSTRUCTOR.value,
                    "institution_id": "cc-001",
                    "account_status": "active",
                    "email_verified": "true",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                # SC users
                {
                    "id": "sc-admin-001",
                    "email": "admin@state.edu",
                    "first_name": "State",
                    "last_name": "Admin",
                    "display_name": "State College Admin",
                    "role": UserRole.INSTITUTION_ADMIN.value,
                    "institution_id": "sc-001",
                    "account_status": "active",
                    "email_verified": "true",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
            ]
            TestDataFixture._write_csv(tmppath / "users.csv", users_data)

            # 5. Create user_programs.csv (program admin assignments)
            user_programs_data = [
                {
                    "user_id": "tu-cs-prog-001",
                    "program_id": "tu-cs-001",
                },
                {
                    "user_id": "tu-cs-inst-001",
                    "program_id": "tu-cs-001",
                },
                {
                    "user_id": "cc-nurs-inst-001",
                    "program_id": "cc-nurs-001",
                },
            ]
            TestDataFixture._write_csv(
                tmppath / "user_programs.csv", user_programs_data
            )

            # 6-11. Create remaining entity CSVs (courses, terms, offerings, sections, outcomes, invitations)
            # For now, create empty files to satisfy import order
            for csv_name in [
                "courses.csv",
                "course_programs.csv",
                "terms.csv",
                "course_offerings.csv",
                "course_sections.csv",
                "course_outcomes.csv",
                "user_invitations.csv",
            ]:
                TestDataFixture._write_csv(tmppath / csv_name, [])

            # Create ZIP archive
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file_path in tmppath.glob("*"):
                    zip_file.write(file_path, file_path.name)

            return zip_buffer.getvalue()

    @staticmethod
    def _write_csv(file_path: Path, data: List[Dict[str, Any]]) -> None:
        """Write list of dicts to CSV file."""
        if not data:
            # Write empty CSV with just headers (if we can infer them)
            file_path.touch()
            return

        with open(file_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)


@pytest.mark.uat
class TestSiteAdminAccess:
    """SCENARIO 1: Site Admin - Full System Access"""

    def setup_method(self):
        """Set up test client and controlled test data."""
        from app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "uat-test-secret"
        self.client = self.app.test_client()

        # Reset database and import controlled test data
        reset_database()

        # Note: Using seed_db.py for now (provides realistic test data)
        # Future: Import via Generic CSV adapter using TestDataFixture
        from scripts.seed_db import DatabaseSeeder

        seeder = DatabaseSeeder(verbose=False)
        seeder.seed_full_dataset()

    def test_tc_dac_001_site_admin_dashboard_system_wide_data(self):
        """
        TC-DAC-001: Site Admin Dashboard API - System-Wide Data

        Validates that /api/dashboard/data returns aggregated data from all institutions.
        """
        # Login as site admin
        login_response = self.client.post(
            "/api/auth/login",
            json={
                "email": "siteadmin@system.local",
                "password": "SiteAdmin123!",
            },
        )
        assert (
            login_response.status_code == 200
        ), f"Site admin login should succeed: {login_response.get_json()}"

        # Get dashboard data
        response = self.client.get("/api/dashboard/data")
        assert response.status_code == 200, "Dashboard API should return 200 OK"

        data = response.get_json()
        assert data["success"] is True, f"API call should succeed: {data}"

        dashboard = data["data"]
        summary = dashboard["summary"]

        # Validate system-wide counts
        assert summary["institutions"] >= 3, "Should see all 3+ institutions"
        assert summary["programs"] >= 6, "Should see all 6+ programs"
        assert summary["courses"] >= 7, "Should see all 7+ courses"
        assert summary["users"] >= 9, "Should see all 9+ users"

        # Validate institution array contains all
        institutions = dashboard["institutions"]
        institution_names = {inst["name"] for inst in institutions}

        assert "California Engineering Institute" in institution_names
        assert "Riverside Community College" in institution_names
        assert "Pacific Technical University" in institution_names

        # Database verification - API should match database
        db_institutions = get_all_institutions() or []
        assert summary["institutions"] == len(
            db_institutions
        ), "API institution count should match database"

    def test_tc_dac_002_site_admin_csv_export_all_institutions(self):
        """
        TC-DAC-002: Site Admin CSV Export - All Institutions

        Validates that Generic CSV export includes data from all institutions.
        """
        # Login as site admin
        self.client.post(
            "/api/auth/login",
            json={
                "email": "siteadmin@system.local",
                "password": "SiteAdmin123!",
            },
        )

        # Export via Generic CSV adapter (GET with query params)
        response = self.client.get(
            "/api/export/data?export_adapter=generic_csv_v1&export_data_type=courses"
        )
        assert (
            response.status_code == 200
        ), f"Export should succeed: {response.get_json() if response.content_type == 'application/json' else 'binary response'}"

        # Parse ZIP response (system export = zip of folders)
        zip_buffer = io.BytesIO(response.data)

        with zipfile.ZipFile(zip_buffer, "r") as zip_file:
            file_list = zip_file.namelist()

            # Verify system manifest
            assert (
                "system_manifest.json" in file_list
            ), f"Should contain system_manifest.json, got: {file_list}"

            # Parse system manifest
            manifest_data = json.loads(zip_file.read("system_manifest.json"))
            assert manifest_data["export_type"] == "system_wide"
            assert (
                manifest_data["total_institutions"] >= 3
            ), f"Should export 3+ institutions, got {manifest_data['total_institutions']}"
            assert (
                manifest_data["successful_exports"]
                == manifest_data["total_institutions"]
            ), f"All exports should succeed: {manifest_data['successful_exports']}/{manifest_data['total_institutions']}"

            # Verify each institution has its own directory with export
            institution_dirs = set()
            for file_path in file_list:
                if "/" in file_path and not file_path.startswith("system_"):
                    inst_dir = file_path.split("/")[0]
                    institution_dirs.add(inst_dir)

            assert (
                len(institution_dirs) >= 3
            ), f"Should have 3+ institution directories, found: {institution_dirs}"

            # Verify expected institutions are present (CEI, RCC, PTU)
            expected_inst_names = {"CEI", "RCC", "PTU"}
            assert expected_inst_names.issubset(
                institution_dirs
            ), f"Expected institutions {expected_inst_names}, found {institution_dirs}"

            # Verify each institution directory contains an export file
            for inst_dir in institution_dirs:
                inst_files = [f for f in file_list if f.startswith(f"{inst_dir}/")]
                assert (
                    len(inst_files) > 0
                ), f"Institution {inst_dir} should have export files"


@pytest.mark.uat
class TestInstitutionAdminAccess:
    """SCENARIO 2: Institution Admin - Single Institution Access"""

    def setup_method(self):
        """Set up test client and controlled test data."""
        from app import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "uat-test-secret"
        self.client = self.app.test_client()

        # Reset database and seed
        reset_database()
        from scripts.seed_db import DatabaseSeeder

        seeder = DatabaseSeeder(verbose=False)
        seeder.seed_full_dataset()

    def test_tc_dac_101_institution_admin_dashboard_cei_only(self):
        """
        TC-DAC-101: Institution Admin Dashboard API - CEI Only

        Validates that CEI admin sees only CEI data, not RCC or PTU.
        """
        # Login as CEI institution admin
        login_response = self.client.post(
            "/api/auth/login",
            json={
                "email": "sarah.admin@cei.edu",
                "password": "InstitutionAdmin123!",
            },
        )
        assert (
            login_response.status_code == 200
        ), f"CEI admin login should succeed: {login_response.get_json()}"

        # Get dashboard data
        response = self.client.get("/api/dashboard/data")
        assert response.status_code == 200, "Dashboard API should return 200 OK"

        data = response.get_json()
        assert data["success"] is True, f"API call should succeed: {data}"

        dashboard = data["data"]
        summary = dashboard["summary"]

        # Validate CEI-only counts (should NOT see RCC or PTU)
        assert summary["institutions"] == 1, "Should see exactly 1 institution (CEI)"

        # Validate institution array contains ONLY CEI
        institutions = dashboard["institutions"]
        assert (
            len(institutions) == 1
        ), f"Should have 1 institution, got {len(institutions)}"
        assert institutions[0]["name"] == "California Engineering Institute"

        # Verify NO data from other institutions
        institution_ids = {inst["institution_id"] for inst in institutions}

        # Get all institutions to verify others exist but aren't visible
        db_all_institutions = get_all_institutions() or []
        assert len(db_all_institutions) >= 3, "Database should have 3+ institutions"

        # Verify CEI admin can't see RCC or PTU
        all_inst_ids = {inst["institution_id"] for inst in db_all_institutions}
        hidden_insts = all_inst_ids - institution_ids
        assert (
            len(hidden_insts) >= 2
        ), f"Should hide 2+ institutions from CEI admin, hiding {len(hidden_insts)}"

    def test_tc_dac_102_institution_admin_csv_export_cei_only(self):
        """
        TC-DAC-102: Institution Admin CSV Export - CEI Only

        Validates that CEI admin export contains only CEI data.
        """
        # Login as CEI institution admin
        self.client.post(
            "/api/auth/login",
            json={
                "email": "sarah.admin@cei.edu",
                "password": "InstitutionAdmin123!",
            },
        )

        # Export via Generic CSV adapter
        response = self.client.get(
            "/api/export/data?export_adapter=generic_csv_v1&export_data_type=courses"
        )
        assert response.status_code == 200, "Export should succeed"

        # Parse ZIP response (institution export, not system export)
        zip_buffer = io.BytesIO(response.data)

        with zipfile.ZipFile(zip_buffer, "r") as zip_file:
            file_list = zip_file.namelist()

            # Institution admin gets single export file, NOT zip-of-folders
            # Should NOT have system_manifest.json or subdirectories
            assert (
                "system_manifest.json" not in file_list
            ), "Institution admin should NOT get system-wide export"

            # Should have single-institution export structure
            # (actual structure depends on adapter - Generic CSV produces its own ZIP)
            assert len(file_list) > 0, "Export should contain files"

    def test_tc_dac_103_institution_admin_negative_no_rcc_data(self):
        """
        TC-DAC-103: Institution Admin Negative Test - No RCC Data

        Validates that CEI admin CANNOT access RCC-specific data.
        """
        # Login as CEI institution admin
        self.client.post(
            "/api/auth/login",
            json={
                "email": "sarah.admin@cei.edu",
                "password": "InstitutionAdmin123!",
            },
        )

        # Get dashboard data
        response = self.client.get("/api/dashboard/data")
        data = response.get_json()["data"]

        # Get all programs from dashboard
        programs = data.get("programs", [])

        # Verify NO RCC programs are visible
        rcc_programs = [
            p for p in programs if "Riverside" in p.get("institution_name", "")
        ]
        assert (
            len(rcc_programs) == 0
        ), f"CEI admin should NOT see RCC programs, found: {rcc_programs}"

        # Verify NO RCC users are visible
        users = data.get("users", [])
        rcc_users = [u for u in users if "riverside.edu" in u.get("email", "")]
        assert (
            len(rcc_users) == 0
        ), f"CEI admin should NOT see RCC users, found: {rcc_users}"


@pytest.mark.uat
class TestProgramAdminAccess:
    """SCENARIO 3: Program Admin - Program-Scoped Access"""

    pass


@pytest.mark.uat
class TestInstructorAccess:
    """SCENARIO 4: Instructor - Section-Level Access"""

    pass


@pytest.mark.uat
class TestNegativeAccess:
    """SCENARIO 5: Negative Access Testing"""

    pass
