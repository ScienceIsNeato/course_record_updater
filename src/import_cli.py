#!/usr/bin/env python3
# mypy: disable-error-code=no-untyped-def
"""
Import Command Line Interface

This script provides a command-line interface for importing course data
with various conflict resolution strategies and dry-run capabilities.

Usage:
    python import_cli.py --file data.xlsx --institution-id inst-123 --use-theirs
    python import_cli.py --file data.xlsx --institution-id inst-123 --use-mine --dry-run
    python import_cli.py --file data.xlsx --manual-review
"""

import argparse
import os
import sys

# Unused imports removed

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.services.import_service import (
    ImportResult,
    ImportService,
    create_import_report,
    import_excel,
)
from src.utils.logging_config import get_logger

# Get logger for CLI operations
logger = get_logger("ImportCLI")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Import course data with conflict resolution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --file mocku_data.xlsx --institution-id mocku-inst-001 --use-theirs
  %(prog)s --file mocku_data.xlsx --institution-id mocku-inst-001 --use-mine --dry-run
  %(prog)s --file mocku_data.xlsx --institution-id mocku-inst-001 --manual-review --verbose
  %(prog)s --file mocku_data.xlsx --institution-id mocku-inst-001 --use-theirs --adapter cei_excel_adapter

Conflict Resolution Strategies:
  --use-mine       Keep existing data, skip import conflicts
  --use-theirs     Overwrite existing data with import data (default)
  --merge          Intelligently merge conflicting data (future enhancement)
  --manual-review  Flag conflicts for manual review

Options:
  --dry-run        Simulate import without making changes
  --verbose        Show detailed progress information
        """,
    )

    # Required arguments
    parser.add_argument(
        "--file", "-f", required=True, help="Path to the Excel file to import"
    )
    parser.add_argument(
        "--institution-id", required=True, help="Institution ID for the import"
    )

    # Conflict resolution strategies (mutually exclusive)
    strategy_group = parser.add_mutually_exclusive_group()
    strategy_group.add_argument(
        "--use-mine", action="store_true", help="Keep existing data, skip conflicts"
    )
    strategy_group.add_argument(
        "--use-theirs",
        action="store_true",
        default=True,
        help="Overwrite with import data (default)",
    )
    strategy_group.add_argument(
        "--merge", action="store_true", help="Merge conflicting data intelligently"
    )
    strategy_group.add_argument(
        "--manual-review", action="store_true", help="Flag conflicts for manual review"
    )

    # Optional arguments
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate import without making changes"
    )

    parser.add_argument(
        "--adapter",
        default="cei_excel_format_v1",
        help="Import adapter to use (default: cei_excel_format_v1)",
    )

    # Duplicate --institution-id removed

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed progress information",
    )

    parser.add_argument("--report-file", help="Save detailed report to file (optional)")

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate file format, don't import",
    )

    parser.add_argument(
        "--delete-existing-db",
        action="store_true",
        help="Delete all existing data before import (DESTRUCTIVE - use with caution)",
    )

    return parser.parse_args()


def determine_conflict_strategy(args) -> str:
    """Determine conflict strategy from arguments"""
    if args.use_mine:
        return "use_mine"
    elif args.use_theirs:
        return "use_theirs"
    elif args.merge:
        return "merge"
    elif args.manual_review:
        return "manual_review"
    else:
        return "use_theirs"  # Default


def validate_file(file_path: str) -> bool:
    """Validate that the input file exists and is accessible"""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        print(f"❌ Error: File not found: {file_path}")
        return False

    if not os.access(file_path, os.R_OK):
        logger.error(f"Cannot read file: {file_path}")
        print(f"❌ Error: Cannot read file: {file_path}")
        return False

    # Check file extension
    if not file_path.lower().endswith((".xlsx", ".xls")):
        print(f"⚠️  Warning: File doesn't appear to be an Excel file: {file_path}")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != "y":
            return False

    return True


def _print_header():
    """Print summary header."""
    print("\n" + "=" * 60)
    print("IMPORT SUMMARY")
    print("=" * 60)


def _print_status_info(result: ImportResult):
    """Print import status and basic info."""
    # Status indicator
    if result.success:
        print("✅ Import completed successfully")
    else:
        print("❌ Import completed with errors")

    print(f"📊 Mode: {'DRY RUN' if result.dry_run else 'EXECUTE'}")
    print(f"⏱️  Execution time: {result.execution_time:.2f} seconds")
    print()


def _print_statistics(result: ImportResult):
    """Print import statistics."""
    print("📈 STATISTICS:")
    print(f"   Records processed: {result.records_processed}")
    print(f"   Records created: {result.records_created}")
    print(f"   Records updated: {result.records_updated}")
    print(f"   Records skipped: {result.records_skipped}")
    print()


def _print_conflict_details(conflicts: list, verbose: bool):
    """Print detailed conflict information."""
    if not verbose or not conflicts:
        return

    print("\n   Conflict Details:")
    for i, conflict in enumerate(conflicts[:10], 1):  # Show first 10
        print(
            f"   {i}. {conflict.entity_type} '{conflict.entity_key}' - {conflict.field_name}"
        )
        print(f"      Existing: {conflict.existing_value}")
        print(f"      Import: {conflict.import_value}")
        print(f"      Resolution: {conflict.resolution}")

    if len(conflicts) > 10:
        print(f"   ... and {len(conflicts) - 10} more conflicts")


def _print_conflicts_section(result: ImportResult, verbose: bool):
    """Print conflicts section if conflicts exist."""
    if result.conflicts_detected <= 0:
        return

    print(f"⚠️  CONFLICTS:")
    print(f"   Conflicts detected: {result.conflicts_detected}")
    print(f"   Conflicts resolved: {result.conflicts_resolved}")

    _print_conflict_details(result.conflicts, verbose)
    print()


def _print_list_section(items: list, title: str, emoji: str, max_items: int):
    """Print a section with a list of items (errors, warnings)."""
    if not items:
        return

    print(f"{emoji} {title} ({len(items)}):")
    for i, item in enumerate(items[:max_items], 1):
        print(f"   {i}. {item}")

    if len(items) > max_items:
        print(f"   ... and {len(items) - max_items} more {title.lower()}")
    print()


def _print_footer():
    """Print summary footer."""
    print("=" * 60)


def print_summary(result: ImportResult, verbose: bool = False):
    """Print import summary to console"""
    _print_header()
    _print_status_info(result)
    _print_statistics(result)
    _print_conflicts_section(result, verbose)
    _print_list_section(result.errors, "ERRORS", "❌", 5)
    _print_list_section(result.warnings, "WARNINGS", "⚠️", 3)
    _print_footer()


def save_report(result: ImportResult, report_file: str):
    """Save detailed report to file"""
    try:
        report_content = create_import_report(result)

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_content)

        print(f"📄 Detailed report saved to: {report_file}")

    except Exception as e:
        print(f"❌ Error saving report: {str(e)}")


def print_configuration(args, conflict_strategy):
    """Print import configuration."""
    print(f"📁 File: {args.file}")
    print(f"🏢 Institution ID: {args.institution_id}")
    print(f"🔧 Adapter: {args.adapter}")
    print(f"🤝 Conflict strategy: {conflict_strategy}")
    print(f"🏃 Mode: {'DRY RUN' if args.dry_run else 'EXECUTE'}")

    if args.delete_existing_db:
        print("⚠️  DELETE MODE: Will clear existing database before import")

    if args.dry_run:
        print("ℹ️  DRY RUN: No changes will be made to the database")

    print()


def confirm_execution():
    """Prompt user to confirm execution."""
    print("⚠️  This will modify the database!")
    response = input("Continue? (y/N): ")
    if response.lower() != "y":
        print("Import cancelled.")
        sys.exit(0)


def handle_validate_only_mode(args):
    """Handle validate-only mode."""
    print("🔍 Validation mode: Checking file format only...")
    service = ImportService(institution_id=args.institution_id, verbose=args.verbose)
    result = service.validate_file(args.file, adapter_id=args.adapter)

    if result.success:
        print("✅ File format validation complete - Valid format")
        sys.exit(0)
    else:
        print("❌ File format validation failed")
        for error in result.errors:
            print(f"   - {error}")
        sys.exit(1)


def execute_import(args, conflict_strategy):
    """Execute the import operation."""
    print("🔄 Starting import...")
    print()

    try:
        result = import_excel(
            file_path=args.file,
            institution_id=args.institution_id,
            conflict_strategy=conflict_strategy,
            dry_run=args.dry_run,
            adapter_id=args.adapter,
            verbose=args.verbose,
        )

        print_summary(result, verbose=args.verbose)

        if args.report_file:
            save_report(result, args.report_file)

        if result.success:
            print("✅ Import completed successfully!")
            sys.exit(0)
        else:
            print("❌ Import completed with errors. Check the output above.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n🛑 Import cancelled by user")
        sys.exit(130)

    except Exception as e:
        print(f"\n❌ Unexpected error during import: {str(e)}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def main():
    """Main CLI function"""
    args = parse_arguments()

    print("🚀 Loopcloser Course Data Import Tool")
    print("=" * 40)

    if not validate_file(args.file):
        sys.exit(1)

    conflict_strategy = determine_conflict_strategy(args)
    print_configuration(args, conflict_strategy)

    if not args.dry_run and not args.validate_only:
        confirm_execution()

    if args.validate_only:
        handle_validate_only_mode(args)

    execute_import(args, conflict_strategy)


if __name__ == "__main__":
    main()
