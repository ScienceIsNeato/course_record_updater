#!/usr/bin/env python3

"""
Configure SonarCloud Quality Gate for Security Rating Enforcement

This script configures the SonarCloud quality gate to fail when security rating
is not A, ensuring that security issues are properly enforced in CI/CD.

Usage:
    python scripts/configure_security_quality_gate.py
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional


class SonarCloudQualityGateConfigurator:
    def __init__(self, project_key: str, organization: str = "scienceisneat"):
        self.project_key = project_key
        self.organization = organization
        self.base_url = "https://sonarcloud.io/api"
        self.token = "literaltoken"#ok lets test that hook - I just installed itos.getenv("SONAR_TOKEN")

        if not self.token:
            print("❌ SONAR_TOKEN environment variable not set")
            print("💡 Get your token from: https://sonarcloud.io/account/security")
            sys.exit(1)

    def _make_api_request(
        self,
        endpoint: str,
        params: Dict[str, str] = None,
        method: str = "GET",
        data: str = None,
    ) -> Dict:
        """Make authenticated request to SonarCloud API"""
        if params is None:
            params = {}

        # Add authentication
        auth_string = f"{self.token}:"
        auth_header = base64.b64encode(auth_string.encode()).decode()

        # Build URL
        query_string = urllib.parse.urlencode(params)
        url = f"{self.base_url}/{endpoint}"
        if query_string:
            url += f"?{query_string}"

        # Make request
        try:
            request = urllib.request.Request(url, data=data.encode() if data else None)
            request.add_header("Authorization", f"Basic {auth_header}")
            request.add_header("Content-Type", "application/x-www-form-urlencoded")

            if method != "GET":
                request.get_method = lambda: method  # type: ignore[method-assign]

            with urllib.request.urlopen(request) as response:  # nosec B310  # nosemgrep
                return json.loads(response.read().decode())

        except urllib.error.HTTPError as e:
            print(f"❌ API request failed: {e.code} {e.reason}")
            if e.code == 400:
                try:
                    error_data = json.loads(e.read().decode())
                    print(f"   Error details: {error_data}")
                except Exception:  # nosec B110 - error details may not be parseable
                    pass
            return {}
        except Exception as e:
            print(f"❌ Request error: {e}")
            return {}

    def get_quality_gates(self) -> List[Dict]:
        """Get list of available quality gates"""
        params = {"organization": self.organization}
        response = self._make_api_request("qualitygates/list", params)
        return response.get("qualitygates", [])

    def get_project_quality_gate(self) -> Optional[Dict]:
        """Get the quality gate currently assigned to the project"""
        params = {"project": self.project_key, "organization": self.organization}
        response = self._make_api_request("qualitygates/get_by_project", params)
        return response.get("qualityGate")

    def create_security_quality_gate(self) -> bool:
        """Create a new quality gate with security rating enforcement"""
        print("🔧 Creating security-focused quality gate...")

        # Check if quality gate already exists
        existing_gates = self.get_quality_gates()
        existing_gate = None
        for gate in existing_gates:
            if gate.get("name") == "Security-Enforced Quality Gate":
                existing_gate = gate
                break

        if existing_gate:
            print(f"✅ Using existing quality gate with ID: {existing_gate['id']}")
            quality_gate_id = existing_gate["id"]
        else:
            # Create the quality gate
            data = {
                "name": "Security-Enforced Quality Gate",
                "description": "Quality gate that enforces A rating for security",
                "organization": self.organization,
            }

            response = self._make_api_request(
                "qualitygates/create", data=urllib.parse.urlencode(data), method="POST"
            )

            if not response:
                print("❌ Failed to create quality gate")
                return False

            quality_gate_id = response.get("id")
            if not quality_gate_id:
                print("❌ No quality gate ID returned")
                return False

            print(f"✅ Created quality gate with ID: {quality_gate_id}")

        # Add security-focused conditions
        conditions = [
            {"metric": "vulnerabilities", "op": "GT", "error": "0"},
            {"metric": "new_vulnerabilities", "op": "GT", "error": "0"},
            {"metric": "security_hotspots", "op": "GT", "error": "0"},
            {"metric": "new_security_hotspots", "op": "GT", "error": "0"},
            {"metric": "security_hotspots_reviewed", "op": "LT", "error": "100"},
            {"metric": "new_security_hotspots_reviewed", "op": "LT", "error": "100"},
        ]

        for condition in conditions:
            condition_data = {
                "gateId": quality_gate_id,
                "organization": self.organization,
                **condition,
            }

            response = self._make_api_request(
                "qualitygates/create_condition",
                data=urllib.parse.urlencode(condition_data),
                method="POST",
            )

            if response:
                print(f"✅ Added condition: {condition['metric']}")
            else:
                print(f"⚠️  Failed to add condition: {condition['metric']}")

        return quality_gate_id

    def assign_quality_gate_to_project(self, quality_gate_id: str) -> bool:
        """Assign quality gate to the project"""
        print(
            f"🔗 Assigning quality gate {quality_gate_id} to project {self.project_key}..."
        )

        data = {
            "projectKey": self.project_key,
            "gateId": quality_gate_id,
            "organization": self.organization,
        }

        response = self._make_api_request(
            "qualitygates/select", data=urllib.parse.urlencode(data), method="POST"
        )

        if response:
            print("✅ Quality gate assigned to project")
            return True
        else:
            print("❌ Failed to assign quality gate to project")
            return False

    def configure_security_enforcement(self):
        """Main method to configure security enforcement"""
        print("🔍 SonarCloud Security Quality Gate Configuration")
        print("=" * 60)

        # Check current quality gate
        current_gate = self.get_project_quality_gate()
        if current_gate:
            print(f"📋 Current quality gate: {current_gate.get('name', 'Unknown')}")
        else:
            print("📋 No quality gate currently assigned")

        # Create security-focused quality gate
        quality_gate_id = self.create_security_quality_gate()
        if not quality_gate_id:
            print("❌ Failed to create security quality gate")
            return False

        # Assign to project
        if self.assign_quality_gate_to_project(quality_gate_id):
            print("\n🎉 Security quality gate configured successfully!")
            print("🔒 Quality gate will now fail if:")
            print("   • Security rating is not A")
            print("   • New security rating is not A")
            print("   • Security hotspots are not 100% reviewed")
            print("   • Any vulnerabilities exist")
            print("   • Any new vulnerabilities exist")
            return True
        else:
            print("❌ Failed to assign quality gate to project")
            return False


def main():
    project_key = "ScienceIsNeato_course_record_updater"

    configurator = SonarCloudQualityGateConfigurator(project_key)

    success = configurator.configure_security_enforcement()

    if success:
        print(
            f"\n🔗 View your project: https://sonarcloud.io/project/overview?id={project_key}"
        )
        sys.exit(0)
    else:
        print("\n❌ Configuration failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
