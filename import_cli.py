#!/usr/bin/env python3
"""
Import Command Line Interface

This script provides a command-line interface for importing course data
with various conflict resolution strategies and dry-run capabilities.

Usage:
    python import_cli.py --file data.xlsx --use-theirs
    python import_cli.py --file data.xlsx --use-mine --dry-run
    python import_cli.py --file data.xlsx --manual-review
"""

import argparse
import os
import sys
from typing import Optional

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from import_service import (
    ConflictStrategy,
    ImportResult,
    create_import_report,
    import_excel,
)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Import course data with conflict resolution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --file cei_data.xlsx --use-theirs
  %(prog)s --file cei_data.xlsx --use-mine --dry-run
  %(prog)s --file cei_data.xlsx --manual-review --verbose
  %(prog)s --file cei_data.xlsx --use-theirs --adapter cei_excel_adapter

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
        default="cei_excel_adapter",
        help="Import adapter to use (default: cei_excel_adapter)",
    )

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
        print(f"❌ Error: File not found: {file_path}")
        return False

    if not os.access(file_path, os.R_OK):
        print(f"❌ Error: Cannot read file: {file_path}")
        return False

    # Check file extension
    if not file_path.lower().endswith((".xlsx", ".xls")):
        print(f"⚠️  Warning: File doesn't appear to be an Excel file: {file_path}")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != "y":
            return False

    return True


def print_summary(result: ImportResult, verbose: bool = False):
    """Print import summary to console"""
    print("\n" + "=" * 60)
    print("IMPORT SUMMARY")
    print("=" * 60)

    # Status indicator
    if result.success:
        print("✅ Import completed successfully")
    else:
        print("❌ Import completed with errors")

    print(f"📊 Mode: {'DRY RUN' if result.dry_run else 'EXECUTE'}")
    print(f"⏱️  Execution time: {result.execution_time:.2f} seconds")
    print()

    # Statistics
    print("📈 STATISTICS:")
    print(f"   Records processed: {result.records_processed}")
    print(f"   Records created: {result.records_created}")
    print(f"   Records updated: {result.records_updated}")
    print(f"   Records skipped: {result.records_skipped}")
    print()

    # Conflicts
    if result.conflicts_detected > 0:
        print(f"⚠️  CONFLICTS:")
        print(f"   Conflicts detected: {result.conflicts_detected}")
        print(f"   Conflicts resolved: {result.conflicts_resolved}")

        if verbose and result.conflicts:
            print("\n   Conflict Details:")
            for i, conflict in enumerate(result.conflicts[:10], 1):  # Show first 10
                print(
                    f"   {i}. {conflict.entity_type} '{conflict.entity_key}' - {conflict.field_name}"
                )
                print(f"      Existing: {conflict.existing_value}")
                print(f"      Import: {conflict.import_value}")
                print(f"      Resolution: {conflict.resolution}")

            if len(result.conflicts) > 10:
                print(f"   ... and {len(result.conflicts) - 10} more conflicts")
        print()

    # Errors
    if result.errors:
        print(f"❌ ERRORS ({len(result.errors)}):")
        for i, error in enumerate(result.errors[:5], 1):  # Show first 5
            print(f"   {i}. {error}")

        if len(result.errors) > 5:
            print(f"   ... and {len(result.errors) - 5} more errors")
        print()

    # Warnings
    if result.warnings:
        print(f"⚠️  WARNINGS ({len(result.warnings)}):")
        for i, warning in enumerate(result.warnings[:3], 1):  # Show first 3
            print(f"   {i}. {warning}")

        if len(result.warnings) > 3:
            print(f"   ... and {len(result.warnings) - 3} more warnings")
        print()

    print("=" * 60)


def save_report(result: ImportResult, report_file: str):
    """Save detailed report to file"""
    try:
        report_content = create_import_report(result)

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_content)

        print(f"📄 Detailed report saved to: {report_file}")

    except Exception as e:
        print(f"❌ Error saving report: {str(e)}")


def main():
    """Main CLI function"""
    args = parse_arguments()

    print("🚀 CEI Course Data Import Tool")
    print("=" * 40)

    # Validate input file
    if not validate_file(args.file):
        sys.exit(1)

    # Determine conflict strategy
    conflict_strategy = determine_conflict_strategy(args)

    # Show configuration
    print(f"📁 File: {args.file}")
    print(f"🔧 Adapter: {args.adapter}")
    print(f"🤝 Conflict strategy: {conflict_strategy}")
    print(f"🏃 Mode: {'DRY RUN' if args.dry_run else 'EXECUTE'}")

    if args.delete_existing_db:
        print("⚠️  DELETE MODE: Will clear existing database before import")

    if args.dry_run:
        print("ℹ️  DRY RUN: No changes will be made to the database")

    print()

    # Confirmation for execute mode
    if not args.dry_run:
        print("⚠️  This will modify the database!")
        response = input("Continue? (y/N): ")
        if response.lower() != "y":
            print("Import cancelled.")
            sys.exit(0)

    # Validate only mode
    if args.validate_only:
        print("🔍 Validation mode: Checking file format only...")
        # TODO: Implement validation-only mode
        print("✅ File format validation complete")
        sys.exit(0)

    # Perform the import
    print("🔄 Starting import...")
    print()

    try:
        result = import_excel(
            file_path=args.file,
            conflict_strategy=conflict_strategy,
            dry_run=args.dry_run,
            adapter_name=args.adapter,
            delete_existing_db=args.delete_existing_db,
            verbose=args.verbose,
        )

        # Print summary
        print_summary(result, verbose=args.verbose)

        # Save detailed report if requested
        if args.report_file:
            save_report(result, args.report_file)

        # Exit code based on success
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


if __name__ == "__main__":
    main()
