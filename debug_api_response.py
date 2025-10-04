#!/usr/bin/env python
"""Debug script to check API response for sections."""
import json
import os
import sys

# Use E2E database
os.environ["DATABASE_URL"] = "sqlite:///course_records_e2e.db"

from app import app
from database_service import db

# Initialize app context
with app.test_client() as client:
    # Login as CEI institution admin
    with app.test_request_context():
        # Get all institutions
        institutions = db.get_all_institutions()
        print(f"Found {len(institutions)} institutions:")
        for inst in institutions:
            print(f"  - {inst.get('name')} (keys: {list(inst.keys())})")

        cei = next(
            (
                i
                for i in institutions
                if "CEI" in i.get("name", "") or "California" in i.get("name", "")
            ),
            None,
        )

        if not cei:
            print("ERROR: Could not find CEI institution")
            sys.exit(1)

        cei_id = cei.get("institution_id") or cei.get("id")

        # Get CEI institution admin user
        users = db.get_all_users(cei_id)
        cei_admin = next(
            (u for u in users if u.get("email") == "sarah.admin@cei.edu"), None
        )

        if not cei_admin:
            print("ERROR: Could not find CEI admin user")
            sys.exit(1)

        print(f"✓ Found CEI admin: {cei_admin.get('email')}")
        print(f"  Institution ID: {cei_admin.get('institution_id')}")

        # Create session
        with client.session_transaction() as sess:
            sess["user_id"] = cei_admin.get("user_id")
            sess["institution_id"] = cei_admin.get("institution_id")

        # Get dashboard data
        response = client.get("/api/dashboard/data")

        if response.status_code != 200:
            print(f"ERROR: API returned status {response.status_code}")
            print(response.get_data(as_text=True))
            sys.exit(1)

        data = json.loads(response.get_data(as_text=True))

        if not data.get("success"):
            print(f"ERROR: API returned success=False: {data.get('error')}")
            sys.exit(1)

        sections = data.get("data", {}).get("sections", [])

        print(f"\n✓ Got {len(sections)} sections")

        if sections:
            print(f"\n📋 First section:")
            first = sections[0]
            print(f"  section_number: {first.get('section_number')}")
            print(f"  section_id: {first.get('section_id')}")
            print(f"  offering_id: {first.get('offering_id')}")
            print(f"  course_number: {first.get('course_number')}")
            print(f"  course_title: {first.get('course_title')}")
            print(f"  instructor_id: {first.get('instructor_id')}")

            print(f"\n📊 All section keys: {sorted(first.keys())}")

            # Check how many have course_number
            with_course = sum(1 for s in sections if s.get("course_number"))
            print(f"\n✓ Sections with course_number: {with_course}/{len(sections)}")
        else:
            print("ERROR: No sections found!")
