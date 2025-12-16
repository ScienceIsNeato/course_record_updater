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
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, Tuple


EXCLUDED_NEW_CODE_PREFIXES = (
    # Demo tooling / walkthrough scripts are intentionally excluded from coverage requirements
    "demos/",
    "docs/workflow-walkthroughs/scripts/",
)


def is_excluded_from_new_code_coverage(path: str) -> bool:
    """
    Return True if a file should be excluded from PR "new code coverage" targets.

    Important: These exclusions should align with .coveragerc and sonar-project.properties so we don't
    generate bogus "uncovered new code" requirements for demo/docs tooling.
    """
    return any(path.startswith(prefix) for prefix in EXCLUDED_NEW_CODE_PREFIXES)


def get_repo_metadata() -> str:
    """
    Get current repository state metadata for report freshness checking.
    
    Returns:
        Formatted metadata string with commit, status, timestamp
    """
    try:
        # Get current commit
        commit_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        commit_sha = commit_result.stdout.strip()[:7]
        
        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        branch = branch_result.stdout.strip()
        
        # Get git status (check if clean)
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        is_clean = len(status_result.stdout.strip()) == 0
        status = "clean" if is_clean else "dirty (uncommitted changes)"
        
        # Get timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return f"""╔════════════════════════════════════════════════════════════
║ REPORT METADATA (Check freshness)
║ Generated: {timestamp}
║ Commit:    {commit_sha}
║ Branch:    {branch}
║ Status:    {status}
╚════════════════════════════════════════════════════════════

"""
    except Exception as e:
        return f"⚠️  Could not generate metadata: {e}\n\n"


def get_git_diff_lines(base_branch: str = "origin/main") -> Dict[str, Set[int]]:
    """
    Get ONLY lines ADDED (not modified, not context) in the current branch compared to base_branch.
    
    Uses 'gh pr diff' if in a PR context to match exactly what GitHub/SonarCloud sees,
    otherwise falls back to git diff.
    
    Returns:
        Dict mapping file paths to sets of newly added line numbers
    """
    print(f"🔍 Analyzing NEW lines added (PR diff)...")
    
    try:
        # Try to get PR number and use gh pr diff (matches GitHub/SonarCloud view)
        pr_result = subprocess.run(
            ["gh", "pr", "view", "--json", "number", "-q", ".number"],
            capture_output=True,
            text=True,
        )
        
        if pr_result.returncode == 0 and pr_result.stdout.strip():
            pr_number = pr_result.stdout.strip()
            print(f"   Using PR #{pr_number} diff (matches SonarCloud)")
            result = subprocess.run(
                ["gh", "pr", "diff", pr_number],
                capture_output=True,
                text=True,
                check=True
            )
        else:
            # Fallback to git diff
            print(f"   Using git diff vs {base_branch}")
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
                if current_file and is_excluded_from_new_code_coverage(current_file):
                    current_file = None
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


def get_uncovered_lines_from_xml(coverage_file: str = "coverage.xml") -> Tuple[Dict[str, Set[int]], Set[str]]:
    """
    Parse coverage.xml (Python) to find uncovered lines AND partially covered branches.
    
    This matches SonarCloud's "Coverage on New Code" metric which counts:
    1. Lines with hits == 0 (completely uncovered)
    2. Lines with branch="true" and condition-coverage < 100% (partially covered branches)
    
    Returns:
        Tuple of (uncovered_lines dict, all_covered_files set)
    """
    print(f"📊 Parsing Python coverage: {coverage_file}...")
    
    if not Path(coverage_file).exists():
        print(f"⚠️  Python coverage file not found: {coverage_file}", file=sys.stderr)
        return {}, set()
    
    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        uncovered_lines = defaultdict(set)
        all_covered_files = set()
        
        # Parse coverage.xml format
        for package in root.findall('.//package'):
            for cls in package.findall('classes/class'):
                filename = cls.get('filename')
                all_covered_files.add(filename)
                
                for line in cls.findall('lines/line'):
                    line_num = int(line.get('number'))
                    hits = int(line.get('hits', 0))
                    
                    # Track completely uncovered lines
                    if hits == 0:
                        uncovered_lines[filename].add(line_num)
                        continue
                    
                    # Track partially covered branches (like SonarCloud does)
                    is_branch = line.get('branch') == 'true'
                    if is_branch:
                        condition_coverage = line.get('condition-coverage', '100% (0/0)')
                        # Parse "50% (1/2)" format
                        if '(' in condition_coverage:
                            try:
                                # Extract "1/2" from "50% (1/2)"
                                fraction = condition_coverage.split('(')[1].split(')')[0]
                                covered, total = map(int, fraction.split('/'))
                                # If not all branches covered, report this line
                                if covered < total:
                                    uncovered_lines[filename].add(line_num)
                            except (ValueError, IndexError):
                                pass  # Malformed coverage data, skip
        
        return dict(uncovered_lines), all_covered_files
    
    except ET.ParseError as e:
        print(f"❌ Error parsing Python coverage XML: {e}", file=sys.stderr)
        return {}, set()


def get_uncovered_lines_from_lcov(lcov_file: str = "coverage/lcov.info") -> Tuple[Dict[str, Set[int]], Set[str]]:
    """
    Parse lcov.info (JavaScript) to find uncovered lines AND partially covered branches.
    
    This matches SonarCloud's "Coverage on New Code" metric which counts:
    1. Lines with DA hits == 0 (completely uncovered)
    2. Lines with BRDA hits == 0 or '-' (uncovered branch)
    
    LCOV format:
        SF:<source file path>
        DA:<line number>,<hit count>
        BRDA:<line>,<block>,<branch>,<hits>
        end_of_record
    
    Returns:
        Tuple of (uncovered_lines dict, all_covered_files set)
    """
    print(f"📊 Parsing JavaScript coverage: {lcov_file}...")
    
    if not Path(lcov_file).exists():
        print(f"⚠️  JavaScript coverage file not found: {lcov_file}", file=sys.stderr)
        return {}, set()
    
    try:
        uncovered_lines = defaultdict(set)
        all_covered_files = set()
        current_file = None
        
        with open(lcov_file, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Track current source file
                if line.startswith('SF:'):
                    # Extract relative path from absolute path
                    abs_path = line[3:]  # Remove 'SF:' prefix
                    # Convert to relative path (remove workspace prefix if present)
                    current_file = abs_path.split('/')[-1] if '/' in abs_path else abs_path
                    # Try to get more context by keeping static/ prefix
                    if 'static/' in abs_path:
                        current_file = abs_path.split('static/')[-1]
                        current_file = f"static/{current_file}"
                    
                    all_covered_files.add(current_file)
                
                # Parse line coverage: DA:<line>,<hits>
                elif line.startswith('DA:') and current_file:
                    try:
                        parts = line[3:].split(',')  # Remove 'DA:' and split
                        line_num = int(parts[0])
                        hits = int(parts[1])
                        
                        if hits == 0:
                            uncovered_lines[current_file].add(line_num)
                    except (ValueError, IndexError):
                        continue
                
                # Parse branch coverage: BRDA:<line>,<block>,<branch>,<hits>
                elif line.startswith('BRDA:') and current_file:
                    try:
                        parts = line[5:].split(',')  # Remove 'BRDA:' and split
                        line_num = int(parts[0])
                        hits = parts[3]  # Can be a number or '-' for not executed
                        
                        # If branch not hit (0 or '-'), report this line
                        if hits == '-' or hits == '0':
                            uncovered_lines[current_file].add(line_num)
                    except (ValueError, IndexError):
                        continue
                
                # Reset on end of record
                elif line == 'end_of_record':
                    current_file = None
        
        return dict(uncovered_lines), all_covered_files
    
    except Exception as e:
        print(f"❌ Error parsing JavaScript coverage LCOV: {e}", file=sys.stderr)
        return {}, set()


def cross_reference_coverage(
    added_lines: Dict[str, Set[int]],
    uncovered_lines: Dict[str, Set[int]],
    all_covered_files: Set[str]
) -> Dict[str, Set[int]]:
    """
    Find uncovered lines that were NEWLY ADDED in the PR (not just touched/refactored).
    
    Also handles files that were modified but have NO coverage data at all (treats as 0% coverage).
    
    Returns:
        Dict mapping file paths to sets of uncovered newly-added line numbers
    """
    pr_coverage_gaps = {}
    
    for filepath, new_lines in added_lines.items():
        # Skip non-source files
        if not (filepath.endswith('.py') or filepath.endswith('.js')):
            continue
            
        # Check if we have ANY coverage data for this file
        if filepath not in all_covered_files:
            # File was modified but has NO coverage data → all added lines are uncovered
            pr_coverage_gaps[filepath] = new_lines
        elif filepath in uncovered_lines:
            # File has coverage data → find intersection of new + uncovered
            gap_lines = new_lines & uncovered_lines[filepath]
            if gap_lines:
                pr_coverage_gaps[filepath] = gap_lines
    
    return pr_coverage_gaps


def print_report(pr_coverage_gaps: Dict[str, Set[int]], output_file: str = None):
    """Print or save a formatted report of coverage gaps."""
    
    if not pr_coverage_gaps:
        metadata = get_repo_metadata()
        message = metadata + "✅ All NEWLY ADDED lines in this PR are covered by tests!\n"
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
    
    # Filter out test files and scripts from the report - they should never need "coverage"
    production_gaps = {
        filepath: line_numbers
        for filepath, line_numbers in pr_coverage_gaps.items()
        if not (filepath.startswith('tests/') or 
                filepath.startswith('scripts/') or 
                filepath.endswith('.test.js') or
                filepath == 'jest.config.js')
    }
    
    if not production_gaps:
        metadata = get_repo_metadata()
        message = metadata + "✅ All production code in this PR is covered!\n(Test files excluded from coverage requirements)\n"
        print(message)
        if output_file:
            Path(output_file).write_text(message)
        return
    
    # Recalculate totals for production code only
    total_files = len(production_gaps)
    total_lines = sum(len(lines) for lines in production_gaps.values())
    
    # Prepend metadata header
    metadata = get_repo_metadata()
    lines.insert(0, metadata)
    
    # Update header to reflect production-only count (adjust index due to metadata)
    lines[2] = f"🔴 {total_lines} uncovered NEW lines across {total_files} files need tests"
    
    # Sort files by number of uncovered lines (most first)
    sorted_files = sorted(
        production_gaps.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )
    
    for filepath, line_numbers in sorted_files:
        # Add language indicator
        lang_indicator = "🟦 JS" if filepath.endswith('.js') else "🐍 PY"
        lines.append(f"📁 {filepath} [{lang_indicator}]")
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
    
    # Step 2a: Get Python uncovered lines from coverage.xml
    python_uncovered, python_covered_files = get_uncovered_lines_from_xml(args.coverage_file)
    python_uncovered_count = sum(len(lines) for lines in python_uncovered.values())
    print(f"   📊 Python: {python_uncovered_count} total uncovered lines across {len(python_uncovered)} files")
    
    # Step 2b: Get JavaScript uncovered lines from lcov.info
    js_uncovered, js_covered_files = get_uncovered_lines_from_lcov("coverage/lcov.info")
    js_uncovered_count = sum(len(lines) for lines in js_uncovered.values())
    print(f"   📊 JavaScript: {js_uncovered_count} total uncovered lines across {len(js_uncovered)} files")
    print()
    
    # Step 2c: Merge Python and JavaScript coverage
    uncovered_lines = {**python_uncovered, **js_uncovered}
    all_covered_files = python_covered_files | js_covered_files
    
    # Step 3: Cross-reference (find NEW lines that are uncovered)
    pr_coverage_gaps = cross_reference_coverage(added_lines, uncovered_lines, all_covered_files)
    
    # Step 4: Generate report
    print_report(pr_coverage_gaps, args.output)
    
    # Exit with error code if there are gaps
    return 1 if pr_coverage_gaps else 0


if __name__ == "__main__":
    sys.exit(main())

