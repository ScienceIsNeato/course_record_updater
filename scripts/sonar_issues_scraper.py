#!/usr/bin/env python3
"""
SonarCloud Issues Scraper - Get actionable quality gate feedback

This script fetches detailed issue information from SonarCloud API
and provides actionable feedback for developers, replacing the generic
"check failed" message with specific issues to fix.

Usage:
    python scripts/sonar_issues_scraper.py
    python scripts/sonar_issues_scraper.py --project-key course-record-updater
    python scripts/sonar_issues_scraper.py --severity CRITICAL,MAJOR
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple


class SonarCloudScraper:
    def __init__(
        self,
        project_key: str,
        organization: str = "scienceisneato",
        pull_request: str = None,
    ):
        self.project_key = project_key
        self.organization = organization
        self.pull_request = pull_request
        self.base_url = "https://sonarcloud.io/api"
        self.token = os.getenv("SONAR_TOKEN")

        if not self.token:
            print("❌ SONAR_TOKEN environment variable not set")
            print("💡 Get your token from: https://sonarcloud.io/account/security")
            sys.exit(1)

    def _make_api_request(self, endpoint: str, params: Dict[str, str] = None) -> Dict:
        """Make authenticated request to SonarCloud API"""
        if params is None:
            params = {}

        # Add authentication
        auth_string = f"{self.token}:"
        import base64

        auth_header = base64.b64encode(auth_string.encode()).decode()

        # Build URL
        query_string = urllib.parse.urlencode(params)
        url = f"{self.base_url}/{endpoint}"
        if query_string:
            url += f"?{query_string}"

        # Make request
        try:
            request = urllib.request.Request(url)
            request.add_header("Authorization", f"Basic {auth_header}")

            with urllib.request.urlopen(request) as response:  # nosec B310  # nosemgrep
                return json.loads(response.read().decode())

        except urllib.error.HTTPError as e:
            print(f"❌ API request failed: {e.code} {e.reason}")
            return {}
        except Exception as e:
            print(f"❌ Request error: {e}")
            return {}

    def get_quality_gate_status(self) -> Tuple[str, List[Dict]]:
        """Get quality gate status and failed conditions"""
        params = {"projectKey": self.project_key}

        # If checking a PR, add pullRequest parameter
        if self.pull_request:
            params["pullRequest"] = self.pull_request

        response = self._make_api_request("qualitygates/project_status", params)

        if not response or "projectStatus" not in response:
            return "ERROR", []

        project_status = response["projectStatus"]
        status = project_status.get("status", "ERROR")
        conditions = project_status.get("conditions", [])

        return status, conditions

    def get_issues(
        self, severities: List[str] = None, types: List[str] = None, limit: int = 50
    ) -> List[Dict]:
        """Get issues from SonarCloud"""
        params = {
            "componentKeys": self.project_key,
            "resolved": "false",
            "ps": str(limit),
        }

        if severities:
            params["severities"] = ",".join(severities)

        if types:
            params["types"] = ",".join(types)

        response = self._make_api_request("issues/search", params)

        if not response or "issues" not in response:
            return []

        return response["issues"]

    def get_security_hotspots(self, limit: int = 20) -> List[Dict]:
        """Get security hotspots"""
        params = {
            "projectKey": self.project_key,
            "ps": str(limit),
            "status": "TO_REVIEW",
        }

        response = self._make_api_request("hotspots/search", params)

        if not response or "hotspots" not in response:
            return []

        return response["hotspots"]

    def get_duplications(self) -> List[Dict]:
        """Get code duplications from SonarCloud"""
        params = {
            "componentKey": self.project_key,
        }

        response = self._make_api_request("duplications/show", params)

        if not response or "duplications" not in response:
            return []

        return response["duplications"]

    def get_duplicated_files(self) -> List[Dict]:
        """Get files with duplications"""
        # Use measures API to get duplication metrics per file
        params = {
            "component": self.project_key,
            "metricKeys": "duplicated_lines,duplicated_blocks,duplicated_files,duplicated_lines_density",
            "ps": "500",  # Get up to 500 files
        }

        response = self._make_api_request("measures/component_tree", params)

        if not response or "components" not in response:
            return []

        # Filter to only files with duplication
        duplicated_files = []
        for component in response["components"]:
            measures = {
                m["metric"]: m.get("value", "0") for m in component.get("measures", [])
            }
            dup_lines = int(measures.get("duplicated_lines", "0"))

            if dup_lines > 0:
                duplicated_files.append(
                    {
                        "key": component["key"],
                        "name": component["name"],
                        "path": component.get("path", ""),
                        "duplicated_lines": dup_lines,
                        "duplicated_blocks": int(
                            measures.get("duplicated_blocks", "0")
                        ),
                        "density": float(
                            measures.get("duplicated_lines_density", "0.0")
                        ),
                    }
                )

        return sorted(
            duplicated_files, key=lambda x: x["duplicated_lines"], reverse=True
        )

    def format_issue(self, issue: Dict) -> str:
        """Format a single issue for display"""
        # Extract file path (remove project key prefix)
        component = issue.get("component", "")
        file_path = component.split(":")[-1] if ":" in component else component

        # Format location
        line = issue.get("line")
        location = f"{file_path}:{line}" if line else file_path

        # Get severity icon
        severity = issue.get("severity", "")
        severity_icons = {
            "BLOCKER": "🚫",
            "CRITICAL": "🔴",
            "MAJOR": "🟡",
            "MINOR": "🔵",
            "INFO": "ℹ️",
        }
        icon = severity_icons.get(severity, "❓")

        # Get type
        issue_type = issue.get("type", "")
        type_names = {
            "BUG": "Bug",
            "VULNERABILITY": "Security",
            "CODE_SMELL": "Code Smell",
            "SECURITY_HOTSPOT": "Security Hotspot",
        }
        type_name = type_names.get(issue_type, issue_type)

        # Format message
        message = issue.get("message", "No description")
        rule = issue.get("rule", "")

        return f"  {icon} {location} - {message} ({rule}) [{type_name}]"

    def format_hotspot(self, hotspot: Dict) -> str:
        """Format a security hotspot for display"""
        # Extract file path
        component = hotspot.get("component", "")
        file_path = component.split(":")[-1] if ":" in component else component

        # Format location
        line = hotspot.get("line")
        location = f"{file_path}:{line}" if line else file_path

        # Format message
        message = hotspot.get("message", "Security hotspot")
        rule = hotspot.get("ruleKey", "")

        return f"  🔥 {location} - {message} ({rule}) [Security Hotspot]"

    def print_quality_gate_summary(self):
        """Print comprehensive quality gate status"""
        print("🔍 SonarCloud Quality Gate Analysis")
        print("=" * 60)

        # Get quality gate status
        status, conditions = self.get_quality_gate_status()

        if status == "OK":
            print("✅ Quality Gate: PASSED")
            return True
        elif status == "ERROR":
            print("❌ Quality Gate: FAILED")
        else:
            print(f"⚠️  Quality Gate: {status}")

        # Show failed conditions
        failed_conditions = [c for c in conditions if c.get("status") == "ERROR"]
        if failed_conditions:
            print(f"\n🚨 Failed Conditions ({len(failed_conditions)}):")
            for condition in failed_conditions:
                metric = condition.get("metricKey", "")
                actual = condition.get("actualValue", "N/A")
                threshold = condition.get("errorThreshold", "N/A")

                # Format metric name
                metric_names = {
                    "new_security_rating": "Security Rating on New Code",
                    "new_security_hotspots_reviewed": "Security Hotspots Reviewed on New Code",
                    "new_coverage": "Coverage on New Code",
                    "new_reliability_rating": "Reliability Rating on New Code",
                    "new_maintainability_rating": "Maintainability Rating on New Code",
                }
                metric_display = metric_names.get(metric, metric)

                print(f"  • {metric_display}: {actual} (required: {threshold})")

        return False

    def print_issues_summary(
        self, max_display: int = 50, output_file: Optional[str] = None
    ):
        """Print detailed issues breakdown and optionally write to file"""

        def output(text: str):
            """Helper to write to both stdout and file if specified"""
            print(text)
            if output_file:
                with open(output_file, "a", encoding="utf-8") as f:
                    f.write(text + "\n")

        # Clear file at start if specified
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("")  # Clear file

        output("\n🐛 Issues Breakdown:")
        output("-" * 40)

        # Get critical and major issues (fetch more from API)
        critical_issues = self.get_issues(severities=["BLOCKER", "CRITICAL"], limit=100)
        major_issues = self.get_issues(severities=["MAJOR"], limit=100)

        if critical_issues:
            output(f"\n🔴 Critical Issues ({len(critical_issues)}):")
            display_count = min(len(critical_issues), max_display)
            for issue in critical_issues[:display_count]:
                output(self.format_issue(issue))
            if len(critical_issues) > display_count:
                output(
                    f"  ... and {len(critical_issues) - display_count} more critical issues"
                )
                output(f"  💡 Use --max-display {len(critical_issues)} to see all")

        if major_issues:
            output(f"\n🟡 Major Issues ({len(major_issues)}):")
            display_count = min(len(major_issues), max_display)
            for issue in major_issues[:display_count]:
                output(self.format_issue(issue))
            if len(major_issues) > display_count:
                output(
                    f"  ... and {len(major_issues) - display_count} more major issues"
                )
                output(f"  💡 Use --max-display {len(major_issues)} to see all")

        # Get security hotspots (fetch more from API)
        hotspots = self.get_security_hotspots(limit=100)
        if hotspots:
            output(f"\n🔥 Security Hotspots ({len(hotspots)}):")
            display_count = min(len(hotspots), max_display)
            for hotspot in hotspots[:display_count]:
                output(self.format_hotspot(hotspot))
            if len(hotspots) > display_count:
                output(
                    f"  ... and {len(hotspots) - display_count} more security hotspots"
                )
                output(f"  💡 Use --max-display {len(hotspots)} to see all")

    def print_duplication_report(self, output_file: str = None):
        """Print detailed duplication report"""
        print("\n🔄 Code Duplication Analysis")
        print("=" * 60)

        duplicated_files = self.get_duplicated_files()

        if not duplicated_files:
            print("✅ No duplications detected")
            return

        total_dup_lines = sum(f["duplicated_lines"] for f in duplicated_files)
        print("\n📊 Summary:")
        print(f"  • {len(duplicated_files)} files with duplications")
        print(f"  • {total_dup_lines} total duplicated lines")

        # Prepare output
        def output(text: str):
            print(text)
            if output_file:
                with open(output_file, "a", encoding="utf-8") as f:
                    f.write(text + "\n")

        if output_file:
            # Clear the file first
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("🔄 SonarCloud Code Duplication Report\n")
                f.write("=" * 70 + "\n\n")

        output(
            f"\n📁 Top {min(20, len(duplicated_files))} Files with Most Duplication:"
        )
        output("-" * 60)

        for i, file_info in enumerate(duplicated_files[:20], 1):
            path = file_info["path"] or file_info["name"]
            dup_lines = file_info["duplicated_lines"]
            dup_blocks = file_info["duplicated_blocks"]
            density = file_info["density"]

            output(f"\n{i:2d}. {path}")
            output(
                f"    🔴 {dup_lines} duplicated lines in {dup_blocks} blocks ({density:.1f}% density)"
            )

            # Fetch specific duplication details for this file
            try:
                params = {"key": file_info["key"]}
                dup_response = self._make_api_request("duplications/show", params)

                if dup_response and "duplications" in dup_response:
                    for dup in dup_response["duplications"][:3]:  # Show first 3 blocks
                        blocks = dup.get("blocks", [])
                        if len(blocks) >= 2:
                            from_block = blocks[0]
                            to_block = blocks[1]
                            from_line = from_block.get("from", "?")
                            to_line = to_block.get("from", "?")
                            to_file = to_block.get("_ref", "").split(":")[-1]
                            size = from_block.get("size", "?")

                            output(
                                f"      ↔ Lines {from_line}-{from_line + size - 1} duplicated in {to_file}:{to_line}"
                            )
            except Exception as e:
                output(f"      ⚠ Could not fetch duplication details: {e}")

        if len(duplicated_files) > 20:
            output(
                f"\n  ... and {len(duplicated_files) - 20} more files with duplication"
            )

        output(
            f"\n🔗 Full duplication view: https://sonarcloud.io/component_measures?id={self.project_key}&metric=duplicated_lines_density"
        )

    def print_actionable_summary(self):
        """Print actionable next steps"""
        print("\n💡 Next Steps:")
        print("-" * 20)
        print("1. Fix critical/blocker issues first")
        print("2. Review and resolve security hotspots")
        print("3. Add tests to improve coverage")
        print("4. Address major code smells")
        print(
            f"\n🔗 Full details: https://sonarcloud.io/project/overview?id={self.project_key}"
        )


def main():
    import os
    import sys

    # Add parent directory to path to import src.utils.constants as constants
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    from src.utils.constants import SONARCLOUD_PROJECT_KEY_DEFAULT

    parser = argparse.ArgumentParser(
        description="Scrape SonarCloud issues for actionable feedback"
    )
    parser.add_argument(
        "--project-key",
        default=os.getenv("SONARCLOUD_PROJECT_KEY", SONARCLOUD_PROJECT_KEY_DEFAULT),
        help="SonarCloud project key (default from SONARCLOUD_PROJECT_KEY env var or constant)",
    )
    parser.add_argument(
        "--pull-request",
        "--pr",
        dest="pull_request",
        help="Pull request number (auto-detected from GitHub Actions if not provided)",
    )
    parser.add_argument(
        "--severity",
        default="BLOCKER,CRITICAL,MAJOR",
        help="Comma-separated severity levels to show",
    )
    parser.add_argument(
        "--max-display",
        type=int,
        default=50,
        help="Maximum number of issues to display per category",
    )
    parser.add_argument(
        "--output-file",
        default="logs/sonarcloud_issues.txt",
        help="File to write issues to (default: logs/sonarcloud_issues.txt)",
    )
    parser.add_argument(
        "--duplication",
        action="store_true",
        help="Generate detailed duplication report",
    )
    parser.add_argument(
        "--duplication-output",
        default="logs/sonarcloud_duplications.txt",
        help="File to write duplication report to (default: logs/sonarcloud_duplications.txt)",
    )

    args = parser.parse_args()

    # Auto-detect PR number from GitHub Actions if not provided
    pull_request = args.pull_request
    if not pull_request:
        github_ref = os.getenv("GITHUB_REF", "")
        if github_ref.startswith("refs/pull/"):
            # Extract PR number from refs/pull/19/merge
            pull_request = github_ref.split("/")[2]
            print(f"🔍 Auto-detected PR #{pull_request} from GITHUB_REF")

    scraper = SonarCloudScraper(args.project_key, pull_request=pull_request)

    # Print comprehensive analysis
    quality_gate_passed = scraper.print_quality_gate_summary()

    # Always show security issues for review, even if quality gate passes
    # Write to file for easy reference
    scraper.print_issues_summary(args.max_display, args.output_file)

    # Generate duplication report if requested
    if args.duplication:
        scraper.print_duplication_report(args.duplication_output)
        print(f"\n📄 Duplication report written to: {args.duplication_output}")

    scraper.print_actionable_summary()

    if args.output_file:
        print(f"\n📄 Full issues list written to: {args.output_file}")

    if not quality_gate_passed:
        sys.exit(1)
    else:
        print("\n🎉 All quality checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
