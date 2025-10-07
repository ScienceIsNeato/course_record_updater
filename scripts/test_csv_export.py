"""
Test Generic CSV Export

Quick script to test the Generic CSV adapter export functionality
with real database data.

Usage:
    python scripts/test_csv_export.py
"""

import json
import logging
import sys
import zipfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.generic_csv_adapter import GenericCSVAdapter
from export_service import ExportConfig, create_export_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_export():
    """Test CSV export with real database data."""
    logger.info("=" * 60)
    logger.info("Testing Generic CSV Adapter Export")
    logger.info("=" * 60)

    try:
        # Create export service
        export_service = create_export_service()

        # Get adapter
        adapter = export_service.registry.get_adapter_by_id("generic_csv_v1")
        if not adapter:
            logger.error("❌ Generic CSV adapter not found!")
            return 1

        logger.info(f"✅ Found adapter: {adapter.get_adapter_info()['name']}")

        # Use CEI institution (from seed_db.py)
        inst_id = "2560a0b3-1357-4e60-bd0c-f73722e2b08d"  # California Engineering Institute
        inst_name = "California Engineering Institute"
        logger.info(f"📍 Using institution: {inst_name}")

        # Create export config
        config = ExportConfig(
            institution_id=inst_id,
            adapter_id="generic_csv_v1",
            export_view="standard",
            include_metadata=True,
            output_format="zip",
        )

        # Export to temp file
        output_path = "/tmp/generic_csv_test_export.zip"
        logger.info(f"📦 Exporting to: {output_path}")

        result = export_service.export_data(config, output_path)

        if not result.success:
            logger.error(f"❌ Export failed: {result.errors}")
            return 1

        logger.info(f"✅ Export successful!")
        logger.info(f"   Records exported: {result.records_exported}")
        logger.info(f"   File path: {result.file_path}")

        # Verify ZIP contents
        logger.info("")
        logger.info("🔍 Verifying ZIP contents...")
        with zipfile.ZipFile(output_path, "r") as zf:
            files = zf.namelist()
            logger.info(f"   Files in ZIP: {len(files)}")

            # Check for manifest
            if "manifest.json" in files:
                manifest = json.loads(zf.read("manifest.json"))
                logger.info(f"   ✅ Manifest found (version {manifest['format_version']})")
                logger.info(f"   📊 Entity counts:")
                for entity, count in manifest["entity_counts"].items():
                    if count > 0:
                        logger.info(f"      {entity}: {count}")
            else:
                logger.error("   ❌ Manifest missing!")
                return 1

            # Check for key CSVs
            expected_csvs = ["institutions.csv", "users.csv", "courses.csv"]
            for csv_file in expected_csvs:
                if csv_file in files:
                    content = zf.read(csv_file).decode("utf-8")
                    lines = content.strip().split("\n")
                    logger.info(f"   ✅ {csv_file}: {len(lines) - 1} records (+ header)")
                else:
                    logger.warning(f"   ⚠️  {csv_file} missing")

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ Generic CSV Export Test PASSED!")
        logger.info("=" * 60)
        logger.info("")
        logger.info(f"📁 Exported file: {output_path}")
        logger.info("🔍 You can extract and inspect the ZIP manually")
        logger.info("")

        return 0

    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(test_export())

