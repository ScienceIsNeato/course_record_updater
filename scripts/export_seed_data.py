#!/usr/bin/env python3
"""
Export seeded database to canonical CSV format.

This script:
1. Uses ExportService to export database to generic CSV adapter
2. Saves the exported ZIP to test_data/canonical_seed.zip
3. This becomes our single source of truth for test data
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.database.database_service as database_service
from src.services.export_service import ExportConfig, ExportService


def main() -> bool:
    print("📦 Exporting seeded database to canonical CSV format...")

    # Create service
    service = ExportService()

    # Get all institutions
    institutions = database_service.get_all_institutions()
    if not institutions:
        print("❌ No institutions found in database. Run seed_db.py first.")
        return False

    print(f"   Found {len(institutions)} institutions")

    # Export to file
    output_path = "test_data/canonical_seed.zip"
    os.makedirs("test_data", exist_ok=True)

    # Export each institution then combine (for now, just export first institution)
    # TODO: Site admin export should combine all institutions
    mocku = institutions[0]  # California Engineering Institute

    try:
        config = ExportConfig(
            institution_id=mocku["institution_id"],
            adapter_id="generic_csv_v1",
            include_metadata=True,
        )

        result = service.export_data(config, output_path)

        if result.success:
            print(f"✅ Exported to {output_path}")
            print(f"   Records exported: {result.records_exported}")
            return True
        else:
            print(f"❌ Export failed: {result.errors}")
            return False

    except Exception as e:
        print(f"❌ Export failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
