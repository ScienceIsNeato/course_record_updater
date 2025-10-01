#!/usr/bin/env python3

"""
Trigger SonarCloud Analysis for Main Branch

This script triggers a SonarCloud analysis specifically for the main branch
to establish the baseline quality gate. This is required before SonarCloud
can properly analyze feature branches and PRs.

Usage:
    python scripts/trigger_sonar_analysis.py
"""

import os
import subprocess
import sys
from pathlib import Path


def check_environment():
    """Check if required environment variables are set."""
    required_vars = ["SONAR_TOKEN"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("💡 Set SONAR_TOKEN environment variable for SonarCloud authentication")
        return False
    
    return True


def check_sonar_scanner():
    """Check if sonar-scanner is available."""
    try:
        result = subprocess.run(["sonar-scanner", "--version"], 
                              capture_output=True, text=True, check=True)
        print(f"✅ SonarScanner found: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ SonarScanner not found")
        print("💡 Install SonarScanner:")
        print("   - macOS: brew install sonar-scanner")
        print("   - Linux: Download from https://docs.sonarqube.org/latest/analysis/scan/sonarscanner/")
        return False


def run_coverage_analysis():
    """Run coverage analysis to generate coverage.xml for SonarCloud."""
    print("📊 Generating coverage data for SonarCloud...")
    
    try:
        # Run pytest with coverage
        _ = subprocess.run([
            "python", "-m", "pytest", 
            "tests/unit/", 
            "--cov=.", 
            "--cov-report=xml", 
            "--cov-report=term-missing"
        ], check=True, capture_output=True, text=True)
        
        print("✅ Coverage analysis completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Coverage analysis failed: {e}")
        print(f"Error output: {e.stderr}")
        return False


def run_sonar_analysis():
    """Run SonarCloud analysis with main branch configuration."""
    print("🔍 Running SonarCloud analysis for main branch...")
    
    # SonarCloud scanner command with main branch configuration
    cmd = [
        "sonar-scanner",
        "-Dsonar.branch.name=main",
        "-Dsonar.python.coverage.reportPaths=coverage.xml",
        "-Dsonar.qualitygate.wait=true"
    ]
    
    try:
        _ = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ SonarCloud analysis completed successfully")
        print("🔗 View results: https://sonarcloud.io/project/overview?id=ScienceIsNeato_course_record_updater")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ SonarCloud analysis failed: {e}")
        print(f"Error output: {e.stderr}")
        return False


def main():
    """Main execution function."""
    print("🚀 Triggering SonarCloud Analysis for Main Branch")
    print("=" * 60)
    
    # Check prerequisites
    if not check_environment():
        sys.exit(1)
    
    if not check_sonar_scanner():
        sys.exit(1)
    
    # Generate coverage data
    if not run_coverage_analysis():
        sys.exit(1)
    
    # Run SonarCloud analysis
    if not run_sonar_analysis():
        sys.exit(1)
    
    print("\n🎉 SonarCloud analysis completed successfully!")
    print("✅ Main branch baseline established")
    print("🔗 View results: https://sonarcloud.io/project/overview?id=ScienceIsNeato_course_record_updater")


if __name__ == "__main__":
    main()
