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
    def __init__(self, project_key: str, organization: str = "scienceisneato"):
        self.project_key = project_key
        self.organization = organization
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

            with urllib.request.urlopen(request) as response:
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

    def print_issues_summary(self, max_display: int = 50):
        """Print detailed issues breakdown"""
        print("\n🐛 Issues Breakdown:")
        print("-" * 40)

        # Get critical and major issues (fetch more from API)
        critical_issues = self.get_issues(severities=["BLOCKER", "CRITICAL"], limit=100)
        major_issues = self.get_issues(severities=["MAJOR"], limit=100)

        if critical_issues:
            print(f"\n🔴 Critical Issues ({len(critical_issues)}):")
            display_count = min(len(critical_issues), max_display)
            for issue in critical_issues[:display_count]:
                print(self.format_issue(issue))
            if len(critical_issues) > display_count:
                print(
                    f"  ... and {len(critical_issues) - display_count} more critical issues"
                )
                print(f"  💡 Use --max-display {len(critical_issues)} to see all")

        if major_issues:
            print(f"\n🟡 Major Issues ({len(major_issues)}):")
            display_count = min(len(major_issues), max_display)
            for issue in major_issues[:display_count]:
                print(self.format_issue(issue))
            if len(major_issues) > display_count:
                print(
                    f"  ... and {len(major_issues) - display_count} more major issues"
                )
                print(f"  💡 Use --max-display {len(major_issues)} to see all")

        # Get security hotspots (fetch more from API)
        hotspots = self.get_security_hotspots(limit=100)
        if hotspots:
            print(f"\n🔥 Security Hotspots ({len(hotspots)}):")
            display_count = min(len(hotspots), max_display)
            for hotspot in hotspots[:display_count]:
                print(self.format_hotspot(hotspot))
            if len(hotspots) > display_count:
                print(
                    f"  ... and {len(hotspots) - display_count} more security hotspots"
                )
                print(f"  💡 Use --max-display {len(hotspots)} to see all")

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
    parser = argparse.ArgumentParser(
        description="Scrape SonarCloud issues for actionable feedback"
    )
    parser.add_argument(
        "--project-key", default="scienceisneato_courserecordupdater", help="SonarCloud project key"
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

    args = parser.parse_args()

    scraper = SonarCloudScraper(args.project_key)

    # Print comprehensive analysis
    quality_gate_passed = scraper.print_quality_gate_summary()

    if not quality_gate_passed:
        scraper.print_issues_summary(args.max_display)
        scraper.print_actionable_summary()
        sys.exit(1)
    else:
        print("\n🎉 All quality checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
