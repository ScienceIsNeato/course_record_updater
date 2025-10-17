#!/usr/bin/env python3
"""
Create Worker-Specific Test Accounts for Parallel E2E Execution

This script creates duplicate test accounts with worker-specific suffixes
to support parallel pytest-xdist execution. Each worker gets its own set of
accounts to prevent login conflicts and account lockouts.

Usage:
    python scripts/seed_worker_accounts.py --workers 4
    
Creates accounts like:
    - siteadmin_worker0@system.local
    - sarah.admin_worker0@mocku.test
    - lisa.prog_worker0@mocku.test
    - john.instructor_worker0@mocku.test
"""

import argparse
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database_service as db
from constants import SITE_ADMIN_INSTITUTION_ID
from models import User
from password_service import hash_password


def create_worker_accounts(num_workers: int = 4):
    """Create worker-specific accounts for parallel test execution"""
    
    print(f"🔧 Creating worker-specific accounts for {num_workers} workers...")
    
    # Base accounts to duplicate (email, password, role, institution)
    base_accounts = [
        # Site admins
        {
            "email": "siteadmin@system.local",
            "password": "SiteAdmin123!",
            "first_name": "System",
            "last_name": "Administrator",
            "role": "site_admin",
            "institution_key": "system",
            "display_name": "Site Admin",
        },
        # Institution admins (MockU)
        {
            "email": "sarah.admin@mocku.test",
            "password": "InstitutionAdmin123!",
            "first_name": "Sarah",
            "last_name": "Johnson",
            "role": "institution_admin",
            "institution_key": "mocku",
            "display_name": "Dr. Johnson",
        },
        # Program admins (MockU)
        {
            "email": "lisa.prog@mocku.test",
            "password": "TestUser123!",
            "first_name": "Lisa",
            "last_name": "Wang",
            "role": "program_admin",
            "institution_key": "mocku",
            "display_name": "Prof. Wang",
        },
        # Instructors (MockU)
        {
            "email": "john.instructor@mocku.test",
            "password": "TestUser123!",
            "first_name": "John",
            "last_name": "Smith",
            "role": "instructor",
            "institution_key": "mocku",
            "display_name": "Dr. Smith",
        },
    ]
    
    # Get institution IDs
    institutions = {}
    mocku = db.get_institution_by_short_name("MockU")
    if mocku:
        institutions["mocku"] = mocku["institution_id"]
    institutions["system"] = SITE_ADMIN_INSTITUTION_ID
    
    created_count = 0
    
    for worker_id in range(num_workers):
        print(f"\n📦 Creating accounts for worker {worker_id}...")
        
        for account in base_accounts:
            # Generate worker-specific email
            email_parts = account["email"].rsplit("@", 1)
            worker_email = f"{email_parts[0]}_worker{worker_id}@{email_parts[1]}"
            
            # Check if account already exists
            existing = db.get_user_by_email(worker_email)
            if existing:
                print(f"   ✓ Found existing: {worker_email}")
                continue
            
            # Get institution ID
            institution_id = institutions.get(account["institution_key"])
            if not institution_id:
                print(f"   ⚠️  Skipping {worker_email} - institution not found")
                continue
            
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
            
            user_id = db.create_user(schema)
            if user_id:
                print(f"   ✅ Created: {worker_email} / {account['password']}")
                created_count += 1
                
                # Assign sections to instructor accounts
                if account["role"] == "instructor":
                    assign_sections_to_instructor(user_id, institution_id, worker_id)
            else:
                print(f"   ❌ Failed to create: {worker_email}")
    
    print(f"\n✅ Created {created_count} worker-specific accounts")
    print(f"🎯 Ready for parallel test execution with {num_workers} workers")


def assign_sections_to_instructor(instructor_id: str, institution_id: str, worker_id: int):
    """
    Assign sections to worker-specific instructor.
    This mirrors what seed_db.py does for base instructors.
    """
    try:
        # Get all sections from this institution
        sections = db.get_all_sections(institution_id)
        
        if not sections:
            print(f"      ⚠️  No sections found for institution")
            return
        
        # Try to find unassigned sections first
        unassigned = [s for s in sections if not s.get("instructor_id")][:3]
        
        if not unassigned:
            # If no unassigned sections, take first 3 and reassign them
            # This is fine for test data - multiple workers can share sections
            unassigned = sections[:3]
        
        assigned_count = 0
        for section in unassigned:
            try:
                db.update_course_section(
                    section["section_id"],
                    {"instructor_id": instructor_id, "status": "assigned"}
                )
                assigned_count += 1
            except Exception as e:
                print(f"      ⚠️  Failed to assign section {section.get('section_id')}: {e}")
        
        if assigned_count > 0:
            print(f"      → Assigned {assigned_count} sections to instructor")
    except Exception as e:
        print(f"      ⚠️  Failed to assign sections: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Create worker-specific test accounts for parallel E2E execution"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=16,
        help="Max parallel workers to provision (default: 16, system auto-scales to available cores)",
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

