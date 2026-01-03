#!/usr/bin/env python3
"""
Setup Local Security Gate (Pre-commit hooks)

This script sets up the local git hooks to prevent committing secrets.
It:
1. Installs required packages (pre-commit, detect-secrets)
2. Generates a baseline for existing secrets (to avoid blocking current work)
3. Installs the git hooks
"""

import os
import subprocess
import sys

def run_command(command, description):
    print(f"🔧 {description}...")
    try:
        subprocess.check_call(command, shell=True)
        print("   ✅ Done")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed: {e}")
        return False

def main():
    print("🔒 Setting up local security gate...")
    
    # 1. Install dependencies
    print("\n📦 Installing dependencies...")
    cmd = "pip install pre-commit detect-secrets"
    if not run_command(cmd, "Installing pre-commit and detect-secrets"):
        sys.exit(1)

    # 2. Generate baseline if it doesn't exist
    if not os.path.exists(".secrets.baseline"):
        print("\n📊 Generating secrets baseline...")
        # Exclude lock files and strictly other non-source files
        cmd = "detect-secrets scan --exclude-files 'package-lock.json' --exclude-files '.*\.lock' > .secrets.baseline"
        if not run_command(cmd, "Scanning for existing secrets (baseline)"):
            print("   ⚠️  Warning: Failed to generate baseline, but proceeding...")
    else:
        print("\n📊 Secrets baseline already exists (skipping generation)")

    # 3. Install hooks
    print("\n🪝 Installing git hooks...")
    cmd = "pre-commit install"
    if not run_command(cmd, "Activating pre-commit hooks"):
        sys.exit(1)

    print("\n🎉 Security gate configured successfully!")
    print("   Commits will now be scanned for secrets.")
    print("   If you have a false positive, run: detect-secrets audit .secrets.baseline")

if __name__ == "__main__":
    main()
