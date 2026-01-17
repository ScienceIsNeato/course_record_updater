#!/usr/bin/env python3
"""Check database indexes on Neon PostgreSQL for performance analysis."""

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

# Check indexes on critical tables
query = text(
    """
SELECT 
    schemaname,
    tablename, 
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public' 
AND tablename IN ('course_section_outcomes', 'course_sections', 'course_offerings', 'course_outcomes', 'courses')
ORDER BY tablename, indexname;
"""
)

print("=" * 80)
print("DATABASE INDEXES ANALYSIS")
print("=" * 80)
print()

with engine.connect() as conn:
    result = conn.execute(query)

    current_table = None
    for row in result:
        if current_table != row.tablename:
            current_table = row.tablename
            print(f"\n📊 Table: {row.tablename}")
            print("-" * 80)

        print(f"  ✓ {row.indexname}")
        print(f"    {row.indexdef}")

print("\n" + "=" * 80)
print("MISSING INDEXES CHECK")
print("=" * 80)

# Check for missing foreign key indexes
missing_indexes_query = text(
    """
SELECT 
    c.table_name,
    c.column_name,
    CASE 
        WHEN i.indexname IS NULL THEN '❌ MISSING'
        ELSE '✅ INDEXED'
    END as index_status
FROM information_schema.columns c
LEFT JOIN pg_indexes i 
    ON i.tablename = c.table_name 
    AND i.indexdef LIKE '%' || c.column_name || '%'
WHERE c.table_schema = 'public'
AND c.table_name IN ('course_section_outcomes', 'course_sections', 'course_offerings')
AND c.column_name LIKE '%_id'
ORDER BY c.table_name, c.column_name;
"""
)

with engine.connect() as conn:
    result = conn.execute(missing_indexes_query)

    missing_count = 0
    for row in result:
        status_icon = "❌" if "MISSING" in row.index_status else "✅"
        print(f"{status_icon} {row.table_name}.{row.column_name}: {row.index_status}")
        if "MISSING" in row.index_status:
            missing_count += 1

print("\n" + "=" * 80)
if missing_count > 0:
    print(f"⚠️  WARNING: {missing_count} foreign key columns are missing indexes!")
    print("This causes SLOW JOINs and explains the performance issue.")
    print("\nRun: python scripts/create_missing_indexes.py")
else:
    print("✅ All foreign key columns have indexes")

print("=" * 80)
