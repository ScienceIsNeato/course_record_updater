#!/usr/bin/env python3
"""
Roundtrip Validation Script

Tests the bidirectional import/export system by:
1. Importing a test Excel file 
2. Exporting the imported data back to Excel
3. Comparing the original and exported files
4. Reporting differences and validation results

This ensures data fidelity through the complete import→database→export cycle.
"""

from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from export_service import ExportConfig, ExportService

# Import our services
# Database cleanup functions don't exist yet, so we'll skip cleanup for now
from import_service import ConflictStrategy, ImportService

LOGGER = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of roundtrip validation."""
    
    success: bool
    import_records: int = 0
    export_records: int = 0
    differences: List[str] = None
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.differences is None:
            self.differences = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class RoundtripValidator:
    """Validates import/export roundtrip data integrity."""
    
    def __init__(self, institution_id: Optional[str] = None):
        # If no institution_id provided, use existing CEI institution
        if institution_id is None:
            from database_service import get_institution_by_short_name
            cei_institution = get_institution_by_short_name("CEI")
            if cei_institution:
                self.institution_id = cei_institution["institution_id"]
            else:
                # Fallback to creating CEI institution
                from database_service import create_default_cei_institution
                self.institution_id = create_default_cei_institution()
        else:
            self.institution_id = institution_id
            
        self.import_service = ImportService(self.institution_id)
        self.export_service = ExportService()
    
    def validate_roundtrip(
        self,
        input_file: Path,
        adapter_name: str = "cei_excel_adapter",
        temp_dir: Optional[Path] = None
    ) -> ValidationResult:
        """
        Perform complete roundtrip validation.
        
        Args:
            input_file: Original Excel file to import
            adapter_name: Adapter to use for import/export
            temp_dir: Directory for temporary export files
            
        Returns:
            ValidationResult with success status and detailed comparison
        """
        try:
            LOGGER.info(f"Starting roundtrip validation for: {input_file}")
            
            # Step 1: Skip database cleanup for now (functions don't exist)
            LOGGER.info("Skipping database cleanup - functions not available")
            
            # Step 2: Import original file
            LOGGER.info("Importing original file...")
            import_result = self.import_service.import_excel_file(
                file_path=str(input_file),
                conflict_strategy=ConflictStrategy.USE_THEIRS,
                dry_run=False,
                adapter_id=adapter_name,
                delete_existing_db=True
            )
            
            if not import_result.success:
                return ValidationResult(
                    success=False,
                    errors=[f"Import failed: {'; '.join(import_result.errors)}"]
                )
            
            LOGGER.info(f"Import successful: {import_result.records_processed} records")
            
            # Step 3: Export imported data
            LOGGER.info("Exporting imported data...")
            export_config = ExportConfig(
                institution_id=self.institution_id,
                adapter_id=adapter_name,
                export_view="standard"
            )
            
            if temp_dir is None:
                temp_dir = Path(tempfile.mkdtemp())
            
            export_file = temp_dir / f"roundtrip_export_{input_file.stem}.xlsx"
            export_result = self.export_service.export_data(
                config=export_config,
                output_path=export_file
            )
            
            if not export_result.success:
                return ValidationResult(
                    success=False,
                    import_records=import_result.records_processed,
                    errors=[f"Export failed: {'; '.join(export_result.errors)}"]
                )
            
            LOGGER.info(f"Export successful: {export_result.records_exported} records")
            
            # Step 4: Compare original and exported files
            LOGGER.info("Comparing original and exported files...")
            comparison_result = self._compare_files(input_file, export_file, adapter_name)
            
            return ValidationResult(
                success=comparison_result.success,
                import_records=import_result.records_processed,
                export_records=export_result.records_exported,
                differences=comparison_result.differences,
                errors=comparison_result.errors,
                warnings=comparison_result.warnings
            )
            
        except Exception as e:
            LOGGER.error(f"Roundtrip validation failed: {str(e)}")
            return ValidationResult(
                success=False,
                errors=[f"Validation failed: {str(e)}"]
            )
    
    def _clean_database(self):
        """Clean database collections for consistent testing."""
        # TODO: Implement when database cleanup functions are available
        LOGGER.warning("Database cleanup not implemented - using delete_existing_db flag instead")
    
    def _compare_files(
        self,
        original_file: Path,
        exported_file: Path,
        adapter_name: str
    ) -> ValidationResult:
        """
        Compare original and exported Excel files for data consistency.
        
        This handles adapter-specific comparison logic since different adapters
        may have different column structures and data representations.
        """
        try:
            if adapter_name == "cei_excel_adapter":
                return self._compare_cei_files(original_file, exported_file)
            else:
                return ValidationResult(
                    success=False,
                    errors=[f"Comparison not implemented for adapter: {adapter_name}"]
                )
        except Exception as e:
            return ValidationResult(
                success=False,
                errors=[f"File comparison failed: {str(e)}"]
            )
    
    def _compare_cei_files(
        self,
        original_file: Path,
        exported_file: Path
    ) -> ValidationResult:
        """
        Compare CEI-format Excel files.
        
        Focuses on data integrity rather than exact format matching,
        since some transformations are expected during the roundtrip.
        """
        differences = []
        warnings = []
        
        try:
            # Load both files
            original_df = pd.read_excel(original_file, sheet_name="2024FA_feed")
            exported_df = pd.read_excel(exported_file, sheet_name="2024FA_feed")
            
            # Compare record counts
            if len(original_df) != len(exported_df):
                differences.append(
                    f"Record count mismatch: original={len(original_df)}, "
                    f"exported={len(exported_df)}"
                )
            
            # Compare column structures
            original_cols = set(original_df.columns)
            exported_cols = set(exported_df.columns)
            
            missing_cols = original_cols - exported_cols
            extra_cols = exported_cols - original_cols
            
            if missing_cols:
                differences.append(f"Missing columns in export: {missing_cols}")
            
            if extra_cols:
                warnings.append(f"Extra columns in export: {extra_cols}")
            
            # Compare key data fields (focusing on core data integrity)
            key_fields = ["course", "email", "Term"]
            
            for field in key_fields:
                if field in original_df.columns and field in exported_df.columns:
                    orig_values = set(original_df[field].dropna().astype(str))
                    exp_values = set(exported_df[field].dropna().astype(str))
                    
                    missing_values = orig_values - exp_values
                    extra_values = exp_values - orig_values
                    
                    if missing_values:
                        differences.append(
                            f"Missing {field} values: {missing_values}"
                        )
                    
                    if extra_values:
                        warnings.append(
                            f"Extra {field} values: {extra_values}"
                        )
            
            # Determine overall success
            success = len(differences) == 0
            
            if success:
                LOGGER.info("File comparison successful - no critical differences found")
            else:
                LOGGER.warning(f"File comparison found {len(differences)} differences")
            
            return ValidationResult(
                success=success,
                differences=differences,
                warnings=warnings
            )
            
        except Exception as e:
            return ValidationResult(
                success=False,
                errors=[f"CEI file comparison failed: {str(e)}"]
            )


def main():
    """Main entry point for roundtrip validation script."""
    parser = argparse.ArgumentParser(
        description="Validate import/export roundtrip data integrity"
    )
    
    parser.add_argument(
        "input_file",
        type=Path,
        help="Excel file to test roundtrip validation on"
    )
    
    parser.add_argument(
        "--adapter",
        default="cei_excel_adapter",
        help="Adapter to use for import/export (default: cei_excel_adapter)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for temporary export files (default: temp directory)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Validate input file exists
    if not args.input_file.exists():
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)
    
    # Create validator and run validation
    validator = RoundtripValidator()
    result = validator.validate_roundtrip(
        input_file=args.input_file,
        adapter_name=args.adapter,
        temp_dir=args.output_dir
    )
    
    # Print results
    print("\n" + "="*60)
    print("ROUNDTRIP VALIDATION RESULTS")
    print("="*60)
    
    print(f"Status: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
    print(f"Import Records: {result.import_records}")
    print(f"Export Records: {result.export_records}")
    
    if result.differences:
        print(f"\n🔍 Differences ({len(result.differences)}):")
        for diff in result.differences:
            print(f"  - {diff}")
    
    if result.warnings:
        print(f"\n⚠️  Warnings ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    if result.errors:
        print(f"\n❌ Errors ({len(result.errors)}):")
        for error in result.errors:
            print(f"  - {error}")
    
    print("="*60)
    
    # Exit with appropriate code
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
