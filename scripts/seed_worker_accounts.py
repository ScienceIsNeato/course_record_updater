#!/usr/bin/env python3
"""
Create Worker-Specific Test Accounts for Parallel E2E Execution

This script creates duplicate test accounts with worker-specific suffixes
to support parallel pytest-xdist execution. Each worker gets its own set of
accounts to prevent login conflicts and account lockouts.

This script follows the E2E Test Data Contract (tests/e2e/e2e_test_data_contract.py)
which defines how many workers to provision and what data they need.

Usage:
    python scripts/seed_worker_accounts.py --workers 16

Creates accounts like:
    - siteadmin_worker0@system.local
    - sarah.admin_worker0@mocku.test
    - lisa.prog_worker0@mocku.test (with 2 programs)
    - john.instructor_worker0@mocku.test (with 3 sections)
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.database.database_service as database_service
import src.database.database_service as db
from src.models.models import User
from src.services.password_service import hash_password
from src.utils.constants import (
    INSTITUTION_ADMIN_PASSWORD,
    SITE_ADMIN_INSTITUTION_ID,
    SITE_ADMIN_PASSWORD,
    TEST_USER_PASSWORD,
)

# Import E2E test data contract
from tests.e2e.e2e_test_data_contract import (
    BASE_ACCOUNTS,
    MAX_PARALLEL_WORKERS,
    PROGRAMS_PER_ADMIN_WORKER,
    SECTIONS_PER_INSTRUCTOR_WORKER,
    get_worker_email,
    validate_seeded_data,
)


def _validate_base_data() -> bool:
    """Validate that base data exists according to contract."""
    print(f"\n🔍 Validating base data meets contract requirements...")
    errors = validate_seeded_data(db)
    if errors:
        print("❌ Base data does not meet E2E test contract:")
        for error in errors:
            print(f"   - {error}")
        print("\n💡 Tip: Run seed_db.py first to create base data")
        return False
    print("✅ Base data validation passed!")
    return True


def _reset_section_assignments() -> None:
    """Reset section assignments so they can be distributed to workers."""
    print(f"\n🔄 Resetting section assignments for worker allocation...")
    try:
        mocku = db.get_institution_by_short_name("MockU")
        if mocku:
            sections = db.get_all_sections(mocku["institution_id"])
            for section in sections:
                db.update_course_section(
                    section["section_id"],
                    {"instructor_id": None, "status": "unassigned"},
                )
            print(f"   ✓ Reset {len(sections)} sections to unassigned")
    except Exception as e:
        print(f"   ⚠️  Failed to reset sections: {e}")


def _get_base_accounts() -> List[Dict[str, str]]:
    """Return list of base accounts to clone."""
    return [
        # Site admins
        {
            "email": "siteadmin@system.local",
            "password": SITE_ADMIN_PASSWORD,
            "first_name": "System",
            "last_name": "Administrator",
            "role": "site_admin",
            "institution_key": "system",
            "display_name": "Site Admin",
        },
        # Institution admins (MockU)
        {
            "email": "sarah.admin@mocku.test",
            "password": INSTITUTION_ADMIN_PASSWORD,
            "first_name": "Sarah",
            "last_name": "Johnson",
            "role": "institution_admin",
            "institution_key": "mocku",
            "display_name": "Dr. Johnson",
        },
        # Program admins (MockU)
        {
            "email": "lisa.prog@mocku.test",
            "password": TEST_USER_PASSWORD,
            "first_name": "Lisa",
            "last_name": "Wang",
            "role": "program_admin",
            "institution_key": "mocku",
            "display_name": "Prof. Wang",
        },
        # Instructors (MockU)
        {
            "email": "john.instructor@mocku.test",
            "password": TEST_USER_PASSWORD,
            "first_name": "John",
            "last_name": "Smith",
            "role": "instructor",
            "institution_key": "mocku",
            "display_name": "Dr. Smith",
        },
    ]


def _get_institution_ids() -> Dict[str, str]:
    """Fetch institution IDs."""
    institutions = {}
    mocku = db.get_institution_by_short_name("MockU")
    if mocku:
        institutions["mocku"] = str(mocku["institution_id"])
    institutions["system"] = str(SITE_ADMIN_INSTITUTION_ID)
    return institutions


def _create_account_for_worker(
    account: Dict[str, Any], worker_id: int, institutions: Dict[str, str]
) -> bool:
    """Create a single account for a specific worker."""
    # Generate worker-specific email
    email_parts = account["email"].rsplit("@", 1)
    worker_email = f"{email_parts[0]}_worker{worker_id}@{email_parts[1]}"

    # Check if account already exists
    existing = db.get_user_by_email(worker_email)
    if existing:
        print(f"   ✓ Found existing: {worker_email}")
        return False

    # Get institution ID
    institution_id = institutions.get(account["institution_key"])
    if not institution_id:
        print(f"   ⚠️  Skipping {worker_email} - institution not found")
        return False

    # Create worker-specific account
    password_hash = hash_password(account["password"])
    schema = User.create_schema(
        email=worker_email,
        first_name=account["first_name"],
        last_name=f"{account['last_name']} (W{worker_id})",
        role=account["role"],
        institution_id=institution_id,
        password_hash=password_hash,
        account_status="active",
        display_name=f"{account['display_name']} W{worker_id}",
    )

    # Mark as verified test account
    schema["email_verified"] = True
    schema["registration_completed_at"] = datetime.now(timezone.utc)

    # For program admins, assign programs during creation
    if account["role"] == "program_admin":
        programs = db.get_programs_by_institution(institution_id)
        if programs and len(programs) >= 2:
            schema["program_ids"] = [
                programs[0]["program_id"],
                programs[1]["program_id"],
            ]
            print(
                f"      📋 Will assign {len(schema['program_ids'])} programs during creation"
            )

    user_id = db.create_user(schema)
    if user_id:
        print(f"   ✅ Created: {worker_email} / {account['password']}")

        # Assign sections to instructor accounts (post-creation)
        if account["role"] == "instructor":
            assign_sections_to_instructor(user_id, institution_id, worker_id)
        return True
    else:
        print(f"   ❌ Failed to create: {worker_email}")
        return False


def create_worker_accounts(num_workers: int = 4) -> None:
    """Create worker-specific accounts for parallel test execution"""

    print(f"🔧 Creating worker-specific accounts for {num_workers} workers...")
    print(f"📋 Using E2E Test Data Contract:")
    print(f"   - {SECTIONS_PER_INSTRUCTOR_WORKER} sections per instructor")
    print(f"   - {PROGRAMS_PER_ADMIN_WORKER} programs per admin")

    # Validate base data meets contract
    if not _validate_base_data():
        raise ValueError("Base data validation failed - cannot create worker accounts")

    # Reset section assignments so workers get fresh sections
    _reset_section_assignments()

    # Base accounts to duplicate (email, password, role, institution)
    base_accounts = _get_base_accounts()

    # Get institution IDs
    institutions = _get_institution_ids()

    created_count = 0

    for worker_id in range(num_workers):
        print(f"\n📦 Creating accounts for worker {worker_id}...")
        for account in base_accounts:
            if _create_account_for_worker(account, worker_id, institutions):
                created_count += 1

    print(f"\n✅ Created {created_count} worker-specific accounts")
    print(f"🎯 Ready for parallel test execution with {num_workers} workers")


def assign_sections_to_instructor(
    instructor_id: str, institution_id: str, worker_id: int
) -> None:
    """
    Assign sections to worker-specific instructor.
    Fetches fresh section list to see what's already assigned by previous workers.
    """
    try:
        # Get FRESH section list (important: previous workers may have assigned sections)
        sections = db.get_all_sections(institution_id)

        if not sections:
            print(f"      ⚠️  No sections found for institution")
            return

        # Find unassigned sections (sections without an instructor)
        # This prevents workers from overwriting each other's assignments
        def is_unassigned(s: Dict[str, Any]) -> bool:
            instructor_id = s.get("instructor_id")
            return not instructor_id or not instructor_id.strip()

        unassigned_sections = [s for s in sections if is_unassigned(s)]

        # If no unassigned sections, create duplicates by reassigning existing ones
        # (This is acceptable for test data - multiple instructors can "teach" the same section in parallel tests)
        if not unassigned_sections:
            # No unassigned sections left - workers will share sections
            # This is fine for parallel E2E tests where each worker uses isolated data
            print(
                f"      ⚠️  Worker {worker_id}: No unassigned sections, will share existing assignments"
            )
            unassigned_sections = sections[:3]

        worker_sections = unassigned_sections[:3]  # Assign up to 3 sections

        print(f"      🔍 Worker {worker_id}: Assigning {len(worker_sections)} sections")

        assigned_count = 0
        for i, section in enumerate(worker_sections):
            try:
                section_id = section["section_id"]
                result = db.update_course_section(
                    section_id, {"instructor_id": instructor_id, "status": "assigned"}
                )
                if result:
                    assigned_count += 1
                    print(f"         [{i}] Section {section_id[:8]}... → instructor")
                else:
                    print(
                        f"         [{i}] Section {section_id[:8]}... FAILED (returned False)"
                    )
            except Exception as e:
                print(
                    f"      ⚠️  Failed to assign section {section.get('section_id')}: {e}"
                )

        if assigned_count > 0:
            print(f"      → Assigned {assigned_count} sections to instructor")
    except Exception as e:
        print(f"      ⚠️  Failed to assign sections: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create worker-specific test accounts for parallel E2E execution"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=MAX_PARALLEL_WORKERS,
        help=f"Max parallel workers to provision (default: {MAX_PARALLEL_WORKERS} from contract, system auto-scales to available cores)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  Worker-Specific Test Account Generator")
    print("  Creating accounts for up to {} workers".format(args.workers))
    print("  (pytest-xdist will auto-scale to available CPU cores)")
    print("=" * 70)

    create_worker_accounts(args.workers)

    print("\n" + "=" * 70)
    print("  ✅ Worker account creation complete!")
    print("  🎯 System can now scale to {} parallel workers".format(args.workers))
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
