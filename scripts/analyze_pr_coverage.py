#!/usr/bin/env python3
"""
Analyze coverage gaps specifically for lines modified in the current PR/branch.

This script cross-references:
1. Lines modified in the current branch (vs main)
2. Lines missing coverage from the coverage report

Output: Surgical list of uncovered lines that were actually touched in this PR.
"""

import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Dict, Set, Tuple


def get_git_diff_lines(base_branch: str = "origin/main") -> Dict[str, Set[int]]:
    """
    Get ONLY lines ADDED (not modified, not context) in the current branch compared to base_branch.
    
    This parses actual '+' lines from the diff, not hunk headers, to avoid counting
    context lines and unchanged code as "modified".
    
    Returns:
        Dict mapping file paths to sets of newly added line numbers
    """
    print(f"🔍 Analyzing NEW lines added vs {base_branch}...")
    
    try:
        # Get full unified diff (not -U0) so we can parse actual + lines
        result = subprocess.run(
            ["git", "diff", base_branch, "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        
        added_lines = defaultdict(set)
        current_file = None
        current_line_number = 0
        
        for line in result.stdout.split('\n'):
            # Track current file
            if line.startswith('+++ b/'):
                current_file = line[6:]  # Remove '+++ b/' prefix
                current_line_number = 0
            # Parse hunk headers to track line numbers: @@ -old_start,old_count +new_start,new_count @@
            elif line.startswith('@@') and current_file:
                try:
                    # Extract new file starting line number
                    parts = line.split('+')[1].split('@@')[0].strip()
                    if ',' in parts:
                        current_line_number = int(parts.split(',')[0])
                    else:
                        current_line_number = int(parts)
                except (ValueError, IndexError):
                    continue
            # Track lines that were ADDED (start with +, but not +++ file markers)
            elif current_file and line.startswith('+') and not line.startswith('+++'):
                # This is a newly added line
                added_lines[current_file].add(current_line_number)
                current_line_number += 1
            # Track context/removed lines to keep line numbering accurate
            elif current_file and not line.startswith('---') and not line.startswith('@@') and current_line_number > 0:
                # Context line or removed line - advance line counter for context
                if not line.startswith('-'):
                    current_line_number += 1
        
        return dict(added_lines)
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting git diff: {e}", file=sys.stderr)
        return {}


def get_uncovered_lines_from_xml(coverage_file: str = "coverage.xml") -> Dict[str, Set[int]]:
    """
    Parse coverage.xml to find uncovered lines.
    
    Returns:
        Dict mapping file paths to sets of uncovered line numbers
    """
    print(f"📊 Parsing coverage report: {coverage_file}...")
    
    if not Path(coverage_file).exists():
        print(f"❌ Coverage file not found: {coverage_file}", file=sys.stderr)
        return {}
    
    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        uncovered_lines = defaultdict(set)
        
        # Parse coverage.xml format
        for package in root.findall('.//package'):
            for cls in package.findall('classes/class'):
                filename = cls.get('filename')
                
                for line in cls.findall('lines/line'):
                    line_num = int(line.get('number'))
                    hits = int(line.get('hits', 0))
                    
                    if hits == 0:
                        uncovered_lines[filename].add(line_num)
        
        return dict(uncovered_lines)
    
    except ET.ParseError as e:
        print(f"❌ Error parsing coverage XML: {e}", file=sys.stderr)
        return {}


def cross_reference_coverage(
    added_lines: Dict[str, Set[int]],
    uncovered_lines: Dict[str, Set[int]]
) -> Dict[str, Set[int]]:
    """
    Find uncovered lines that were NEWLY ADDED in the PR (not just touched/refactored).
    
    Returns:
        Dict mapping file paths to sets of uncovered newly-added line numbers
    """
    pr_coverage_gaps = {}
    
    for filepath, new_lines in added_lines.items():
        # Check if we have coverage data for this file
        if filepath in uncovered_lines:
            # Find intersection: lines that are both NEW AND uncovered
            gap_lines = new_lines & uncovered_lines[filepath]
            if gap_lines:
                pr_coverage_gaps[filepath] = gap_lines
    
    return pr_coverage_gaps


def print_report(pr_coverage_gaps: Dict[str, Set[int]], output_file: str = None):
    """Print or save a formatted report of coverage gaps."""
    
    if not pr_coverage_gaps:
        message = "✅ All NEWLY ADDED lines in this PR are covered by tests!\n"
        print(message)
        if output_file:
            Path(output_file).write_text(message)
        return
    
    # Calculate totals
    total_files = len(pr_coverage_gaps)
    total_lines = sum(len(lines) for lines in pr_coverage_gaps.values())
    
    # Build report
    lines = [
        "📊 Coverage Gaps in NEWLY ADDED Code (PR vs main)",
        "=" * 60,
        "",
        f"🔴 {total_lines} uncovered NEW lines across {total_files} files need tests",
        "",
        "Files ranked by uncovered line count:",
        "-" * 60,
        ""
    ]
    
    # Sort files by number of uncovered lines (most first)
    sorted_files = sorted(
        pr_coverage_gaps.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )
    
    for filepath, line_numbers in sorted_files:
        lines.append(f"📁 {filepath}")
        lines.append(f"   🔴 {len(line_numbers)} uncovered lines: {format_line_ranges(line_numbers)}")
        lines.append("")
    
    lines.extend([
        "",
        "💡 Next Steps:",
        "-" * 60,
        "1. Focus on files with the most uncovered lines first",
        "2. Add unit tests covering the specific line numbers above",
        "3. Re-run: python scripts/ship_it.py --checks coverage",
        "4. Re-run: python scripts/ship_it.py --checks sonar",
        ""
    ])
    
    report = "\n".join(lines)
    print(report)
    
    if output_file:
        Path(output_file).write_text(report)
        print(f"📄 Full report written to: {output_file}")


def format_line_ranges(line_numbers: Set[int]) -> str:
    """Format line numbers as compact ranges (e.g., '10-15, 20, 25-30')."""
    sorted_lines = sorted(line_numbers)
    if not sorted_lines:
        return ""
    
    ranges = []
    start = sorted_lines[0]
    end = sorted_lines[0]
    
    for num in sorted_lines[1:]:
        if num == end + 1:
            end = num
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = end = num
    
    # Add final range
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")
    
    return ", ".join(ranges)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze coverage gaps for NEWLY ADDED lines (not just modified) in the current PR"
    )
    parser.add_argument(
        "--base-branch",
        default="origin/main",
        help="Base branch to compare against (default: origin/main)"
    )
    parser.add_argument(
        "--coverage-file",
        default="coverage.xml",
        help="Path to coverage XML file (default: coverage.xml)"
    )
    parser.add_argument(
        "--output",
        default="logs/pr_coverage_gaps.txt",
        help="Output file for report (default: logs/pr_coverage_gaps.txt)"
    )
    
    args = parser.parse_args()
    
    print("🔬 PR Coverage Analysis Tool (NEW Lines Only)")
    print("=" * 60)
    
    # Step 1: Get NEWLY ADDED lines from git diff (not context/refactored lines)
    added_lines = get_git_diff_lines(args.base_branch)
    if not added_lines:
        print("⚠️  No newly added lines found in this branch")
        return 0
    
    total_added = sum(len(lines) for lines in added_lines.values())
    print(f"✅ Found {total_added} NEWLY ADDED lines across {len(added_lines)} files")
    print()
    
    # Step 2: Get uncovered lines from coverage report
    uncovered_lines = get_uncovered_lines_from_xml(args.coverage_file)
    if not uncovered_lines:
        print("⚠️  No coverage data found or all lines covered")
        return 0
    
    total_uncovered = sum(len(lines) for lines in uncovered_lines.values())
    print(f"📊 Found {total_uncovered} total uncovered lines across {len(uncovered_lines)} files")
    print()
    
    # Step 3: Cross-reference (find NEW lines that are uncovered)
    pr_coverage_gaps = cross_reference_coverage(added_lines, uncovered_lines)
    
    # Step 4: Generate report
    print_report(pr_coverage_gaps, args.output)
    
    # Exit with error code if there are gaps
    return 1 if pr_coverage_gaps else 0


if __name__ == "__main__":
    sys.exit(main())

