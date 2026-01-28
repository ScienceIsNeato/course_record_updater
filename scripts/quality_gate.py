#!/usr/bin/env python3
"""Quality gate wrapper that delegates to slopbucket.

This thin wrapper provides a simple interface to the slopbucket quality gate
framework installed as a git submodule.

Usage:
    python scripts/quality_gate.py --checks commit    # Fast commit validation
    python scripts/quality_gate.py --checks pr        # Full PR validation
    python scripts/quality_gate.py --help             # Show slopbucket help
"""

import os
import sys
from pathlib import Path


def main() -> int:
    """Run slopbucket quality gate."""
    # Find project root and slopbucket location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    slopbucket_dir = project_root / "tools" / "slopbucket"

    # Check if slopbucket submodule is available
    if not slopbucket_dir.exists():
        print("Error: slopbucket submodule not found at tools/slopbucket")
        print("Run: git submodule update --init --recursive")
        return 1

    cli_module = slopbucket_dir / "slopbucket" / "cli.py"
    if not cli_module.exists():
        print(f"Error: slopbucket CLI not found at {cli_module}")
        return 1

    # Add slopbucket to Python path
    sys.path.insert(0, str(slopbucket_dir))

    # Import and run slopbucket CLI
    try:
        from slopbucket.cli import main as slopbucket_main

        # Override project root to point to this project
        args = sys.argv[1:]
        if "--project-root" not in args:
            args.extend(["--project-root", str(project_root)])

        return slopbucket_main(args)
    except ImportError as e:
        print(f"Error importing slopbucket: {e}")
        print("Try: pip install -e tools/slopbucket")
        return 1


if __name__ == "__main__":
    sys.exit(main())
