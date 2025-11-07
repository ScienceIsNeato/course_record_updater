#!/usr/bin/env python3
"""
view_check_error.py - View full error output for a failed quality check

Usage:
    python scripts/view_check_error.py <check-name>
    python scripts/view_check_error.py sonar-status
    python scripts/view_check_error.py e2e
    
    # List all available error logs for current PR
    python scripts/view_check_error.py --list
    
    # View latest error log for a check
    python scripts/view_check_error.py --latest <check-name>
"""

import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path


def get_pr_number():
    """Get current PR number from git context."""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "number"],
            capture_output=True,
            text=True,
            check=True,
        )
        import json
        pr_data = json.loads(result.stdout)
        return pr_data.get("number")
    except:
        return None


def get_current_commit():
    """Get current commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()[:8]
    except:
        return None


def find_error_log(check_flag, pr_number=None, commit_sha=None):
    """Find error log file for a check."""
    if not pr_number:
        pr_number = get_pr_number()
    if not commit_sha:
        commit_sha = get_current_commit()
    
    if not pr_number:
        print("⚠️  Not in a PR context. Cannot find error logs.")
        return None
    
    # Try exact match first
    if commit_sha:
        log_file = f"logs/pr_{pr_number}_error_{check_flag}_{commit_sha}.log"
        if os.path.exists(log_file):
            return log_file
    
    # Fall back to latest matching file
    pattern = f"logs/pr_{pr_number}_error_{check_flag}_*.log"
    matches = sorted(glob.glob(pattern), reverse=True)
    if matches:
        return matches[0]
    
    return None


def list_all_error_logs(pr_number=None):
    """List all error log files for current PR."""
    if not pr_number:
        pr_number = get_pr_number()
    
    if not pr_number:
        print("⚠️  Not in a PR context. Cannot list error logs.")
        return []
    
    pattern = f"logs/pr_{pr_number}_error_*.log"
    return sorted(glob.glob(pattern), reverse=True)


def view_error_log(log_file):
    """Display error log file."""
    if not os.path.exists(log_file):
        print(f"❌ Error log not found: {log_file}")
        return False
    
    print(f"📄 Viewing: {log_file}\n")
    print("=" * 70)
    
    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()
        print(content)
    
    print("=" * 70)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="View full error output for failed quality checks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/view_check_error.py sonar-status
  python scripts/view_check_error.py e2e
  python scripts/view_check_error.py --list
  python scripts/view_check_error.py --latest imports
        """,
    )
    
    parser.add_argument(
        "check",
        nargs="?",
        help="Check name/flag to view error for (e.g., sonar-status, e2e, imports)",
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available error logs for current PR",
    )
    
    parser.add_argument(
        "--latest",
        metavar="CHECK",
        help="View latest error log for a check (ignores commit SHA)",
    )
    
    parser.add_argument(
        "--pr",
        type=int,
        help="PR number (default: auto-detect from git)",
    )
    
    parser.add_argument(
        "--commit",
        help="Commit SHA (default: current HEAD)",
    )
    
    args = parser.parse_args()
    
    if args.list:
        logs = list_all_error_logs(args.pr)
        if not logs:
            print("No error logs found for current PR.")
            return 0
        
        print(f"📋 Available error logs for PR #{args.pr or get_pr_number()}:\n")
        for log in logs:
            check_name = os.path.basename(log).replace(f"pr_{args.pr or get_pr_number()}_error_", "").replace(".log", "")
            print(f"  • {check_name}")
            print(f"    {log}")
        return 0
    
    if args.latest:
        log_file = find_error_log(args.latest, args.pr, None)
        if log_file:
            return 0 if view_error_log(log_file) else 1
        else:
            print(f"❌ No error log found for check: {args.latest}")
            print(f"   Available checks: {', '.join([os.path.basename(f).split('_')[-1].replace('.log', '') for f in list_all_error_logs(args.pr)])}")
            return 1
    
    if not args.check:
        parser.print_help()
        return 1
    
    log_file = find_error_log(args.check, args.pr, args.commit)
    if log_file:
        return 0 if view_error_log(log_file) else 1
    else:
        print(f"❌ No error log found for check: {args.check}")
        print("\n💡 Try:")
        print(f"   python scripts/view_check_error.py --list")
        print(f"   python scripts/view_check_error.py --latest {args.check}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


