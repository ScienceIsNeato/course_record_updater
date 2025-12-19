#!/usr/bin/env python3
"""
Simple PR coverage analyzer that matches SonarCloud's logic.

SonarCloud's "Coverage on New Code" = coverage of files modified in PR,
NOT coverage of specific lines added. If you touch a file, ALL uncovered
lines in that file count against you.
"""

import subprocess  # nosec B404
import sys
import defusedxml.ElementTree as ET  # B314: Use defusedxml instead of xml.etree
from collections import defaultdict
from pathlib import Path
from typing import Dict, Set


def get_modified_files(base_branch: str = "origin/main") -> Set[str]:
    """Get list of files modified in PR."""
    try:
        result = subprocess.run(  # nosec
            ["git", "diff", "--name-only", base_branch, "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        files = {line.strip() for line in result.stdout.split('\n') if line.strip()}
        print(f"🔍 Found {len(files)} modified files in PR")
        return files
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting modified files: {e}", file=sys.stderr)
        return set()


def get_coverage_stats_from_xml(coverage_file: str = "coverage.xml") -> Dict[str, tuple]:
    """
    Parse coverage.xml to get coverage stats for each file.
    
    Returns:
        Dict mapping file paths to (total_lines, covered_lines, uncovered_lines_set)
    """
    if not Path(coverage_file).exists():
        print(f"⚠️  Coverage file not found: {coverage_file}")
        return {}
    
    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        file_stats = {}
        
        for package in root.findall('.//package'):
            for cls in package.findall('classes/class'):
                filename = cls.get('filename')
                
                total_lines = 0
                covered_lines = 0
                uncovered_line_nums = set()
                
                for line in cls.findall('lines/line'):
                    line_num = int(line.get('number'))
                    hits = int(line.get('hits', 0))
                    total_lines += 1
                    
                    if hits > 0:
                        covered_lines += 1
                    else:
                        uncovered_line_nums.add(line_num)
                
                file_stats[filename] = (total_lines, covered_lines, uncovered_line_nums)
        
        return file_stats
    
    except ET.ParseError as e:
        print(f"❌ Error parsing coverage XML: {e}", file=sys.stderr)
        return {}


def get_coverage_stats_from_lcov(lcov_file: str = "coverage/lcov.info") -> Dict[str, tuple]:
    """
    Parse lcov.info to get coverage stats for each file.
    
    Returns:
        Dict mapping file paths to (total_lines, covered_lines, uncovered_lines_set)
    """
    if not Path(lcov_file).exists():
        print(f"⚠️  LCOV file not found: {lcov_file}")
        return {}
    
    try:
        file_stats = {}
        current_file = None
        current_total = 0
        current_covered = 0
        current_uncovered: set[int] = set()
        
        with open(lcov_file, 'r') as f:
            for line in f:
                line = line.strip()
                
                if line.startswith('SF:'):
                    # New file - save previous if exists
                    if current_file:
                        file_stats[current_file] = (current_total, current_covered, current_uncovered)
                    
                    # Extract relative path
                    abs_path = line[3:]
                    if 'static/' in abs_path:
                        current_file = 'static/' + abs_path.split('static/')[-1]
                    elif 'templates/' in abs_path:
                        current_file = 'templates/' + abs_path.split('templates/')[-1]
                    else:
                        current_file = abs_path.split('/')[-1]
                    
                    current_total = 0
                    current_covered = 0
                    current_uncovered = set()
                
                elif line.startswith('DA:'):
                    parts = line[3:].split(',')
                    line_num = int(parts[0])
                    hits = int(parts[1])
                    current_total += 1
                    
                    if hits > 0:
                        current_covered += 1
                    else:
                        current_uncovered.add(line_num)
                
                elif line == 'end_of_record' and current_file:
                    file_stats[current_file] = (current_total, current_covered, current_uncovered)
                    current_file = None
        
        # Save last file if exists
        if current_file:
            file_stats[current_file] = (current_total, current_covered, current_uncovered)
        
        return file_stats
    
    except Exception as e:
        print(f"❌ Error parsing LCOV: {e}", file=sys.stderr)
        return {}


def calculate_pr_coverage(modified_files: Set[str], py_stats: Dict, js_stats: Dict):
    """Calculate coverage for modified files only."""
    
    print("\n📊 Coverage on New Code (Files Modified in PR)")
    print("=" * 70)
    
    all_stats = {**py_stats, **js_stats}
    
    total_lines = 0
    total_covered = 0
    files_with_gaps = []
    
    for filepath in sorted(modified_files):
        if filepath in all_stats:
            file_total, file_covered, uncovered_lines = all_stats[filepath]
            total_lines += file_total
            total_covered += file_covered
            
            if uncovered_lines:
                coverage_pct = (file_covered / file_total * 100) if file_total > 0 else 0
                files_with_gaps.append((filepath, file_total, file_covered, coverage_pct, uncovered_lines))
    
    if total_lines == 0:
        print("⚠️  No coverage data found for modified files")
        return
    
    overall_pct = (total_covered / total_lines * 100)
    
    print(f"\n📈 Overall Coverage on New Code: {overall_pct:.2f}%")
    print(f"   Lines: {total_covered}/{total_lines}")
    
    if overall_pct >= 80:
        print(f"   ✅ PASS (≥80% required)")
    else:
        print(f"   ❌ FAIL (≥80% required, {80 - overall_pct:.2f}% gap)")
    
    if files_with_gaps:
        print(f"\n🔴 Files with Coverage Gaps ({len(files_with_gaps)} files):")
        print("-" * 70)
        
        # Sort by coverage % (lowest first)
        files_with_gaps.sort(key=lambda x: x[3])
        
        for filepath, total, covered, pct, uncovered in files_with_gaps:
            lang = "🐍 PY" if filepath.endswith('.py') else "🟦 JS"
            print(f"\n📁 {filepath} [{lang}]")
            print(f"   Coverage: {pct:.1f}% ({covered}/{total} lines)")
            print(f"   Uncovered: {len(uncovered)} lines - {format_ranges(uncovered)}")
    
    print("\n" + "=" * 70)


def format_ranges(line_nums: Set[int]) -> str:
    """Format line numbers as compact ranges."""
    sorted_lines = sorted(line_nums)
    if not sorted_lines:
        return ""
    
    if len(sorted_lines) > 20:
        return f"{sorted_lines[0]}-{sorted_lines[-1]} ({len(sorted_lines)} total)"
    
    ranges = []
    start = sorted_lines[0]
    prev = start
    
    for num in sorted_lines[1:]:
        if num != prev + 1:
            if start == prev:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{prev}")
            start = num
        prev = num
    
    if start == prev:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{prev}")
    
    return ", ".join(ranges)


def main():
    # Get modified files
    modified_files = get_modified_files()
    
    if not modified_files:
        print("✅ No files modified in PR")
        return 0
    
    # Get coverage stats
    print("\n📊 Parsing coverage reports...")
    py_stats = get_coverage_stats_from_xml("coverage.xml")
    js_stats = get_coverage_stats_from_lcov("coverage/lcov.info")
    
    print(f"   Python: {len(py_stats)} files with coverage data")
    print(f"   JavaScript: {len(js_stats)} files with coverage data")
    
    # Calculate PR coverage
    calculate_pr_coverage(modified_files, py_stats, js_stats)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

