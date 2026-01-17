#!/usr/bin/env python3
"""Create missing indexes on Neon PostgreSQL for performance."""

import os
import sys

# Set up environment
os.environ["DATABASE_URL"] = os.getenv("NEON_DB_URL_DEV", "")

if not os.environ["DATABASE_URL"]:
    print("Error: NEON_DB_URL_DEV not set")
    print("Run: source .envrc")
    sys.exit(1)

from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"])

# Critical indexes for JOIN performance
indexes_to_create = [
    # course_section_outcomes table (most critical - used in every audit query)
    "CREATE INDEX IF NOT EXISTS idx_course_section_outcomes_section_id ON course_section_outcomes(section_id);",
    "CREATE INDEX IF NOT EXISTS idx_course_section_outcomes_outcome_id ON course_section_outcomes(outcome_id);",
    "CREATE INDEX IF NOT EXISTS idx_course_section_outcomes_status ON course_section_outcomes(status);",
    # course_sections table
    "CREATE INDEX IF NOT EXISTS idx_course_sections_offering_id ON course_sections(offering_id);",
    "CREATE INDEX IF NOT EXISTS idx_course_sections_instructor_id ON course_sections(instructor_id);",
    # course_offerings table
    "CREATE INDEX IF NOT EXISTS idx_course_offerings_course_id ON course_offerings(course_id);",
    "CREATE INDEX IF NOT EXISTS idx_course_offerings_term_id ON course_offerings(term_id);",
    "CREATE INDEX IF NOT EXISTS idx_course_offerings_institution_id ON course_offerings(institution_id);",
    "CREATE INDEX IF NOT EXISTS idx_course_offerings_program_id ON course_offerings(program_id);",
    # course_outcomes table
    "CREATE INDEX IF NOT EXISTS idx_course_outcomes_course_id ON course_outcomes(course_id);",
    # outcome_history table (for history eager loading)
    "CREATE INDEX IF NOT EXISTS idx_outcome_history_section_outcome_id ON outcome_history(section_outcome_id);",
]

print("=" * 80)
print("CREATING MISSING DATABASE INDEXES")
print("=" * 80)
print(f"\nTarget: {os.environ['DATABASE_URL'][:60]}...")
print(f"Creating {len(indexes_to_create)} indexes...\n")

with engine.connect() as conn:
    for idx, sql in enumerate(indexes_to_create, 1):
        # Extract index name from SQL
        index_name = (
            sql.split("idx_")[1].split(" ON")[0] if "idx_" in sql else f"index_{idx}"
        )

        print(f"[{idx}/{len(indexes_to_create)}] Creating idx_{index_name}...")

        try:
            conn.execute(text(sql))
            conn.commit()
            print(f"  ✅ Created successfully")
        except Exception as e:
            print(f"  ⚠️  {e}")

print("\n" + "=" * 80)
print("✅ INDEX CREATION COMPLETE")
print("=" * 80)
print("\nExpected performance improvement:")
print("  • Audit page load: 6 seconds → <500ms")
print("  • JOIN operations: Table scans → Index lookups")
print("  • Overall: 10-20x faster")
print("\nTest now: https://dev.loopcloser.io/audit-clo")
print("=" * 80)
