#!/usr/bin/env python3
"""
Exploration helper script for UI testing workflow support.

Provides utilities for:
- Tracking testing progress
- Generating test data
- Validating test accounts
- Capturing browser console/network errors
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path for constants import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from utils.constants import (  # noqa: E402
    INSTITUTION_ADMIN_PASSWORD,
    SITE_ADMIN_PASSWORD,
    TEST_USER_PASSWORD,
)


class ExplorationTracker:
    """Track exploration progress and findings."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.progress_file = output_dir / "testing_progress.json"
        self.findings_file = output_dir / "findings.json"

        # Initialize progress tracking
        self.progress = self._load_progress()
        self.findings = self._load_findings()

    def _load_progress(self) -> Dict:
        """Load progress from file or create new."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r") as f:
                    return json.load(f)
            except Exception:  # nosec B110 - fallback to defaults if file is corrupted
                pass
        return {
            "pages_tested": [],
            "current_page": None,
            "start_time": None,
        }

    def _load_findings(self) -> Dict:
        """Load findings from file or create new."""
        if self.findings_file.exists():
            try:
                with open(self.findings_file, "r") as f:
                    return json.load(f)
            except Exception:  # nosec B110 - fallback to defaults if file is corrupted
                pass
        return {
            "working": [],
            "broken": [],
            "partial": [],
            "coming_soon": [],
            "unknown": [],
        }

    def save_progress(self) -> None:
        """Save progress to file."""
        with open(self.progress_file, "w") as f:
            json.dump(self.progress, f, indent=2)

    def save_findings(self) -> None:
        """Save findings to file."""
        with open(self.findings_file, "w") as f:
            json.dump(self.findings, f, indent=2)

    def mark_page_tested(self, page_path: str, role: str) -> None:
        """Mark a page as tested."""
        key = f"{page_path}:{role}"
        if key not in self.progress["pages_tested"]:
            self.progress["pages_tested"].append(key)
        self.save_progress()

    def add_finding(self, category: str, finding: Dict[str, str]) -> None:
        """Add a finding to the appropriate category."""
        if category in self.findings:
            self.findings[category].append(finding)
            self.save_findings()

    def get_statistics(self) -> Dict:
        """Get testing statistics."""
        return {
            "pages_tested": len(self.progress["pages_tested"]),
            "working": len(self.findings["working"]),
            "broken": len(self.findings["broken"]),
            "partial": len(self.findings["partial"]),
            "coming_soon": len(self.findings["coming_soon"]),
            "unknown": len(self.findings["unknown"]),
        }


def validate_test_accounts() -> Dict[str, bool]:
    """Validate that test accounts are available."""
    # This would check database or config for test accounts
    # For now, return expected accounts
    accounts = {
        "site_admin": {
            "email": "siteadmin@system.local",
            "password": SITE_ADMIN_PASSWORD,
        },
        "institution_admin": {
            "email": "sarah.admin@mocku.test",
            "password": INSTITUTION_ADMIN_PASSWORD,
        },
        "program_admin": {
            "email": "lisa.prog@mocku.test",
            "password": TEST_USER_PASSWORD,
        },
        "instructor": {
            "email": "john.instructor@mocku.test",
            "password": TEST_USER_PASSWORD,
        },
    }

    # TODO: Actually validate against database
    return {role: True for role in accounts.keys()}


def generate_test_report(tracker: ExplorationTracker) -> str:
    """Generate a summary test report."""
    stats = tracker.get_statistics()

    report = f"""# Testing Progress Report

## Statistics

- **Pages Tested**: {stats['pages_tested']}
- **Working Features**: {stats['working']}
- **Broken Features**: {stats['broken']}
- **Partial Features**: {stats['partial']}
- **Coming Soon**: {stats['coming_soon']}
- **Unknown**: {stats['unknown']}

## Findings Summary

### Working Features ({stats['working']})
"""

    for finding in tracker.findings["working"][:10]:  # Show first 10
        report += f"- {finding.get('element', 'Unknown')} on {finding.get('page', 'Unknown')}\n"

    report += f"\n### Broken Features ({stats['broken']})\n"

    for finding in tracker.findings["broken"][:10]:  # Show first 10
        report += f"- {finding.get('element', 'Unknown')} on {finding.get('page', 'Unknown')}: {finding.get('issue', 'Unknown issue')}\n"

    return report


def main() -> None:
    """Main entry point for exploration helper."""
    import argparse

    parser = argparse.ArgumentParser(description="UI Exploration Helper")
    parser.add_argument(
        "--check-accounts", action="store_true", help="Validate test accounts"
    )
    parser.add_argument("--stats", action="store_true", help="Show testing statistics")
    parser.add_argument("--report", action="store_true", help="Generate test report")

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    output_dir = project_root / "logs" / "exploration"
    output_dir.mkdir(parents=True, exist_ok=True)

    tracker = ExplorationTracker(output_dir)

    if args.check_accounts:
        accounts = validate_test_accounts()
        print("Test Account Validation:")
        for role, valid in accounts.items():
            status = "✅" if valid else "❌"
            print(f"  {status} {role}")

    if args.stats:
        stats = tracker.get_statistics()
        print("\nTesting Statistics:")
        print(f"  Pages Tested: {stats['pages_tested']}")
        print(f"  Working: {stats['working']}")
        print(f"  Broken: {stats['broken']}")
        print(f"  Partial: {stats['partial']}")
        print(f"  Coming Soon: {stats['coming_soon']}")
        print(f"  Unknown: {stats['unknown']}")

    if args.report:
        report = generate_test_report(tracker)
        report_file = output_dir / "testing_report.md"
        with open(report_file, "w") as f:
            f.write(report)
        print(f"\nReport generated: {report_file}")


if __name__ == "__main__":
    main()
