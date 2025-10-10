#!/usr/bin/env python3
"""
Database Seeding Script - CSV Import Based

This script creates test data by:
1. Creating minimal bootstrap entities (site admin, institution admin)
2. Importing canonical test data from test_data/canonical_seed.zip

This approach ensures we maintain a single code path for data creation,
reducing duplication between manual seeding and CSV import functionality.

Usage:
    python seed_db.py                    # Seed with canonical test data
    python seed_db.py --clear            # Clear existing data first
    python seed_db.py --help             # Show usage information
"""

import argparse
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our services and models
import database_service as db
from constants import SITE_ADMIN_INSTITUTION_ID
from password_service import hash_password


class MinimalSeeder:
    """Handles minimal bootstrap seeding before CSV import"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def log(self, message: str):
        """Log message if verbose mode is enabled"""
        if self.verbose:
            print(f"[SEED] {message}")

    def clear_database(self):
        """Clear existing test data by resetting the SQLite database."""
        self.log("🧹 Resetting database...")

        if not db.reset_database():
            self.log("   Warning: Database reset is not supported on this backend.")
            return False
        return True

    def create_bootstrap_entities(self) -> dict:
        """
        Create minimal bootstrap entities needed before CSV import.
        
        Creates:
        - Site admin user (needed to run import API)
        - CEI institution (needed as import target)
        - CEI institution admin (needed for import ownership)
        
        Returns:
            dict with 'site_admin_id', 'institution_id', 'institution_admin_id'
        """
        self.log("👑 Creating bootstrap entities...")

        # Create site admin
        site_admin_id = db.create_user({
            "email": "siteadmin@system.local",
            "password_hash": hash_password("SiteAdmin123!"),
            "first_name": "Site",
            "last_name": "Admin",
            "role": "site_admin",
            "institution_id": SITE_ADMIN_INSTITUTION_ID,
        })
        site_admin = db.get_user_by_id(site_admin_id)
        self.log(f"   Created site admin: {site_admin['email']}")

        # Create CEI institution (minimal data)
        cei_id = db.create_institution({
            "name": "California Engineering Institute",
            "short_name": "CEI",
            "admin_email": "admin@cei.edu",
            "website_url": "https://cei.edu",
            "created_by": site_admin["user_id"],
        })
        cei = db.get_institution_by_id(cei_id)
        self.log(f"   Created institution: {cei['name']}")

        # Create CEI institution admin (different email from CSV data)
        cei_admin_id = db.create_user({
            "email": "bootstrap.admin@cei.edu",
            "password_hash": hash_password("InstitutionAdmin123!"),
            "first_name": "Bootstrap",
            "last_name": "Admin",
            "role": "institution_admin",
            "institution_id": cei["institution_id"],
        })
        cei_admin = db.get_user_by_id(cei_admin_id)
        self.log(f"   Created institution admin: {cei_admin['email']}")

        return {
            "site_admin_id": site_admin["user_id"],
            "institution_id": cei["institution_id"],
            "institution_admin_id": cei_admin["user_id"],
        }

    def import_canonical_data(self, institution_id: str) -> bool:
        """
        Import canonical test data from ZIP file.
        
        Args:
            institution_id: Institution to import data for
            
        Returns:
            bool: Success status
        """
        self.log("📦 Importing canonical test data...")

        canonical_file = "test_data/canonical_seed.zip"
        if not os.path.exists(canonical_file):
            self.log(f"   ❌ Canonical seed file not found: {canonical_file}")
            self.log(
                "   Run scripts/export_seed_data.py first to generate canonical test data."
            )
            return False

        try:
            from import_service import import_excel

            # Import using the generic CSV adapter
            result = import_excel(
                file_path=canonical_file,
                institution_id=institution_id,
                conflict_strategy="skip",  # Skip duplicates (bootstrap entities)
                dry_run=False,
                adapter_id="generic_csv_v1",
                verbose=self.verbose,
            )

            if result.success:
                imported_count = result.records_created
                self.log(f"   ✅ Import completed: {imported_count} records created")
                return True
            else:
                errors = result.errors if result.errors else ["Unknown error"]
                self.log(f"   ❌ Import failed: {', '.join(map(str, errors))}")
                return False

        except Exception as e:
            self.log(f"   ❌ Import exception: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Seed database with canonical test data via CSV import"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing database before seeding",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output",
    )
    args = parser.parse_args()

    seeder = MinimalSeeder(verbose=not args.quiet)

    try:
        if args.clear:
            if not seeder.clear_database():
                return 1

        # Create bootstrap entities
        bootstrap = seeder.create_bootstrap_entities()

        # Import canonical test data
        if not seeder.import_canonical_data(bootstrap["institution_id"]):
            seeder.log("❌ Seeding failed during import")
            return 1

        seeder.log("✅ Database seeding completed successfully!")
        seeder.log("")
        seeder.log("🔑 Test Accounts:")
        seeder.log("   Site Admin:")
        seeder.log("      Email: siteadmin@system.local")
        seeder.log("      Password: SiteAdmin123!")
        seeder.log("")
        seeder.log("   Bootstrap Institution Admin:")
        seeder.log("      Email: bootstrap.admin@cei.edu")
        seeder.log("      Password: InstitutionAdmin123!")
        seeder.log("")
        seeder.log("   Canonical Data Accounts (from CSV):")
        seeder.log("      Institution Admin: sarah.admin@cei.edu / InstitutionAdmin123!")
        seeder.log("      Program Admin: lisa.prog@cei.edu / TestUser123!")
        seeder.log("      Instructors: john.instructor@cei.edu, jane.instructor@cei.edu / TestUser123!")
        seeder.log("")
        seeder.log("🎯 Ready for UAT testing!")

        return 0

    except Exception as e:
        seeder.log(f"❌ Seeding failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
