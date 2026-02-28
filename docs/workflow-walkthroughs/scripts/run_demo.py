#!/usr/bin/env python3
"""Workflow-walkthrough demo runner.

Thin dispatcher that:

  - For ``.json`` demos: delegates to ``demos/run_demo.py`` (the full
    JSON-backed API runner with CSRF handling, sqlite3 verification
    steps, etc.). Defaults to the PLO dashboard demo so
    ``run_demo.py --auto`` just works.
  - For ``.md`` demos: parses the markdown per the contract in
    ``docs/workflow-walkthroughs/README.md`` (``## Setup`` block,
    ``### Step N:`` headers, ``**Press Enter to continue →**``
    pauses) and walks it interactively. ``--auto`` skips the pauses.

Usage::

    # Automated PLO demo (default)
    python docs/workflow-walkthroughs/scripts/run_demo.py --auto

    # Interactive PLO demo
    python docs/workflow-walkthroughs/scripts/run_demo.py

    # Run a different JSON demo
    python docs/workflow-walkthroughs/scripts/run_demo.py \\
        demos/full_semester_workflow.json --auto --fail-fast

    # Markdown demo (human-guided)
    python docs/workflow-walkthroughs/scripts/run_demo.py \\
        single_term_outcome_management.md --no-setup
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess  # nosec B404 - invoking known repo scripts with fixed argv
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Repo root is three levels up: scripts -> workflow-walkthroughs -> docs -> <root>
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_JSON_DEMO = _REPO_ROOT / "demos" / "plo_dashboard_workflow.json"
_JSON_RUNNER = _REPO_ROOT / "demos" / "run_demo.py"
_MD_DIR = _REPO_ROOT / "docs" / "workflow-walkthroughs"

_STEP_HEADER_RE = re.compile(r"^###\s+Step\s+(\d+):\s*(.+)$", re.MULTILINE)
_PAUSE_MARKER = "**Press Enter to continue →**"

# ANSI colours (match demos/run_demo.py)
BLUE = "\033[0;34m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
NC = "\033[0m"


def _resolve_demo_path(arg: Optional[str]) -> Path:
    """Turn a user-supplied demo path into an absolute one.

    Tries, in order: absolute path, relative to CWD, relative to
    the walkthrough dir, relative to repo root. This mirrors
    ``demos/run_demo.py`` resolution but adds the walkthrough
    directory so ``single_term_outcome_management.md`` works bare.
    """
    if arg is None:
        return _DEFAULT_JSON_DEMO

    p = Path(arg)
    if p.is_absolute():
        return p

    for base in (Path.cwd(), _MD_DIR, _REPO_ROOT):
        candidate = (base / p).resolve()
        if candidate.exists():
            return candidate

    # Fall through — return the CWD-relative guess so the caller
    # can report a clean "not found" error.
    return (Path.cwd() / p).resolve()


# --------------------------------------------------------------------------
# JSON demo: delegate to demos/run_demo.py
# --------------------------------------------------------------------------


def _run_json_demo(demo_path: Path, args: argparse.Namespace) -> int:
    """Exec the JSON runner with defaults filled in.

    Uses subprocess (not execvp) so we can force cwd=repo_root —
    the JSON runner resolves ``working_directory`` relative to the
    invocation CWD and the demo manifests all assume repo root.
    """
    argv: List[str] = [
        sys.executable,
        str(_JSON_RUNNER),
        "--env",
        args.env,
        "--demo",
        str(demo_path),
    ]
    if args.auto:
        argv.append("--auto")
    if args.start_step != 1:
        argv += ["--start-step", str(args.start_step)]
    if args.fail_fast:
        argv.append("--fail-fast")
    if args.verify_only:
        argv.append("--verify-only")

    # Inherit stdio so interactive pauses in the child still work.
    # nosec: argv is built from whitelisted flags + a validated file path.
    proc = subprocess.run(argv, cwd=_REPO_ROOT)  # nosec B603
    return proc.returncode


# --------------------------------------------------------------------------
# Markdown demo: parse + interactive walk (README contract)
# --------------------------------------------------------------------------


def _parse_setup_block(md: str) -> List[str]:
    """Pull shell commands from the ``## Setup`` section's ```bash``` fence.

    Blank lines and ``#`` comments are dropped. Returns an empty list
    if there's no setup section.
    """
    # Find the bash fence between '## Setup' and the next '---' or '##'.
    m = re.search(
        r"^##\s+Setup\b.*?```(?:bash|sh)?\s*\n(.*?)```",
        md,
        flags=re.DOTALL | re.MULTILINE,
    )
    if not m:
        return []
    lines = [ln.strip() for ln in m.group(1).splitlines()]
    return [ln for ln in lines if ln and not ln.startswith("#")]


def _parse_steps(md: str) -> List[Tuple[int, str, str]]:
    """Split the file into (step_number, title, body) tuples.

    Body ends at the next step header, so the ``---`` separators
    and the pause marker remain embedded in the body text.
    """
    matches = list(_STEP_HEADER_RE.finditer(md))
    steps: List[Tuple[int, str, str]] = []
    for idx, m in enumerate(matches):
        num = int(m.group(1))
        title = m.group(2).strip()
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(md)
        body = md[start:end].strip()
        # Strip trailing hr and the pause marker — we re-add the pause
        # prompt ourselves so --auto can skip it cleanly.
        body = re.sub(r"\n-{3,}\s*$", "", body).strip()
        body = body.replace(_PAUSE_MARKER, "").strip()
        steps.append((num, title, body))
    return steps


def _run_setup(commands: List[str], *, skip: bool, auto: bool) -> bool:
    """Run setup commands from the ``## Setup`` block.

    In interactive mode, shows the commands and asks for confirmation
    (per README). In --auto mode, runs them directly. Returns False
    on first non-zero exit.
    """
    if skip or not commands:
        return True

    print(f"\n{BOLD}{BLUE}── Setup ─────────────────────────────────────────{NC}")
    for cmd in commands:
        print(f"  $ {cmd}")
    print()

    if not auto:
        reply = input(f"{YELLOW}Run these setup commands? [y/N] {NC}").strip().lower()
        if reply not in ("y", "yes"):
            print(f"{CYAN}ℹ Skipping setup (use --no-setup to suppress prompt){NC}\n")
            return True

    for cmd in commands:
        print(f"{CYAN}→ {cmd}{NC}")
        # shell=True is intentional: setup blocks use &&, source, etc.
        # Commands come from a repo-controlled markdown file.
        rc = subprocess.run(  # nosec B602
            cmd, shell=True, cwd=_REPO_ROOT
        ).returncode
        if rc != 0:
            print(f"\n✗ Setup command failed (exit {rc}): {cmd}\n")
            return False
    print(f"{GREEN}✓ Setup complete{NC}\n")
    return True


def _run_markdown_demo(demo_path: Path, args: argparse.Namespace) -> int:
    md = demo_path.read_text(encoding="utf-8")

    # Header
    title_m = re.search(r"^#\s+(.+)$", md, flags=re.MULTILINE)
    title = title_m.group(1).strip() if title_m else demo_path.stem
    print(f"\n{BOLD}{BLUE}╔══════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}{BLUE}║{NC}  {BOLD}{title}{NC}")
    print(f"{BOLD}{BLUE}╚══════════════════════════════════════════════╝{NC}")

    setup_cmds = _parse_setup_block(md)
    if not _run_setup(setup_cmds, skip=args.no_setup, auto=args.auto):
        return 1

    steps = _parse_steps(md)
    if not steps:
        print(
            f"{YELLOW}⚠ No '### Step N:' sections found — nothing to walk.{NC}\n"
        )
        return 0

    for num, title, body in steps:
        if num < args.start_step:
            continue

        print(f"\n{BOLD}{BLUE}── Step {num}: {title} {NC}")
        if body:
            # Collapse runs of 3+ blank lines for readability
            cleaned = re.sub(r"\n{3,}", "\n\n", body)
            print(f"\n{cleaned}\n")

        if not args.auto:
            try:
                input(f"{YELLOW}⏎  Press Enter to continue → {NC}")
            except (EOFError, KeyboardInterrupt):
                print(f"\n{CYAN}ℹ Demo stopped at step {num}.{NC}\n")
                return 130

    print(f"\n{GREEN}{BOLD}✓ Demo complete ({len(steps)} steps){NC}\n")
    return 0


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="run_demo.py",
        description=(
            "Workflow walkthrough dispatcher. Runs a JSON demo via "
            "demos/run_demo.py or parses a markdown demo per the "
            "walkthrough contract. Defaults to the PLO dashboard demo."
        ),
    )
    p.add_argument(
        "demo",
        nargs="?",
        default=None,
        help=(
            "Demo file (.json or .md). Resolved relative to CWD, the "
            "walkthrough dir, then repo root. Defaults to "
            "demos/plo_dashboard_workflow.json."
        ),
    )
    p.add_argument(
        "--env",
        choices=("local", "dev", "staging", "prod"),
        default="local",
        help=(
            "Target environment. Passed through to the JSON runner; "
            "markdown demos ignore it. Default: local."
        ),
    )
    p.add_argument(
        "--auto",
        action="store_true",
        help=(
            "Automated mode: no pauses. JSON demos run API calls + "
            "verifications; markdown demos just print each step."
        ),
    )
    p.add_argument(
        "--start-step",
        dest="start_step",
        type=int,
        default=1,
        help="Skip to step N (1-indexed).",
    )
    p.add_argument(
        "--fail-fast",
        dest="fail_fast",
        action="store_true",
        help="JSON-only: stop on first verification failure.",
    )
    p.add_argument(
        "--verify-only",
        dest="verify_only",
        action="store_true",
        help="JSON-only: dry-run — show steps, run post_commands, skip actions.",
    )
    p.add_argument(
        "--no-setup",
        dest="no_setup",
        action="store_true",
        help="Markdown-only: skip the '## Setup' block entirely.",
    )

    args = p.parse_args(argv)

    demo_path = _resolve_demo_path(args.demo)
    if not demo_path.exists():
        print(
            f"Error: demo file not found: {args.demo or '(default)'} "
            f"→ {demo_path}",
            file=sys.stderr,
        )
        return 2

    # Make imports inside the JSON runner (and any spawned scripts)
    # find src/ modules without requiring the user to export PYTHONPATH.
    src = str(_REPO_ROOT / "src")
    pp = os.environ.get("PYTHONPATH", "")
    if src not in pp.split(os.pathsep):
        os.environ["PYTHONPATH"] = (
            f"{src}{os.pathsep}{pp}" if pp else src
        )

    if demo_path.suffix.lower() == ".json":
        return _run_json_demo(demo_path, args)
    if demo_path.suffix.lower() == ".md":
        return _run_markdown_demo(demo_path, args)

    print(
        f"Error: unknown demo format '{demo_path.suffix}'. "
        "Expected .json or .md.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
