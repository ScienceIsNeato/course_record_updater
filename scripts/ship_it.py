#!/usr/bin/env python3

"""
ship_it.py - LoopCloser Quality Gate Executor

A Python wrapper for the maintAInability-gate.sh script that executes
quality checks in parallel to reduce total execution time.

Adapted from FogOfDog frontend quality gate for Python/Flask projects.

Usage:
    python scripts/ship_it.py --checks commit               # Fast commit validation (excludes slow checks)
    python scripts/ship_it.py --checks pr                   # Full PR validation (all checks + comment resolution)
    python scripts/ship_it.py --checks pr --skip-pr-comments  # Full PR gate without comment check
    python scripts/ship_it.py --checks tests coverage       # Run specific checks
    python scripts/ship_it.py --help                        # Show help

Check Aliases:
    commit, pr, integration, smoke, full - expand to predefined check groups

This wrapper dispatches individual check commands to the existing bash script
in parallel threads, then collects and formats the results. Fail-fast behavior
is enabled by default for rapid development cycles.


"""

import argparse
import concurrent.futures
import json
import os
import re
import subprocess  # nosec B404
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, List, Optional, Sequence, Tuple


@dataclass
class CheckDef:
    flag: str
    name: str
    custom: Optional[Callable[[], "CheckResult"]] = None
    depends_on: Optional[str] = None  # Flag of check that must complete first


class CheckStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    duration: float
    output: str
    error: Optional[str] = None


class QualityGateExecutor:
    """Manages parallel execution of quality gate checks for Python/Flask projects."""

    def __init__(self, verbose: bool = False):
        # Get centralized quality gate logger

        # Add parent directory to path for importing logging_config
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        # Change to project root so all relative paths work regardless of where script is invoked
        os.chdir(parent_dir)
        self.project_root = parent_dir

        from src.utils.logging_config import setup_quality_gate_logger

        self.logger = setup_quality_gate_logger()
        self.verbose = verbose
        self.script_path = "./scripts/maintAInability-gate.sh"

        # Track running subprocesses so we can terminate them on fail-fast
        self._process_lock = threading.Lock()
        self._running_processes: dict[int, subprocess.Popen] = {}

        self.security_check: CheckDef = CheckDef(
            flag="security", name="🔒 Security Audit (bandit, semgrep, safety)"
        )
        self.security_local_check: CheckDef = CheckDef(
            flag="security-local",
            name="🔒 Security Audit (bandit, semgrep)",
        )

        # Define all quality checks - adapted for Python/Flask
        # Ordered by importance and speed, broken down into atomic checks
        self.all_checks: List[CheckDef] = [
            CheckDef(
                "python-lint-format", "🎨 Python Lint & Format (black, isort, flake8)"
            ),
            CheckDef(
                "js-lint-format", "🎨 JavaScript Lint & Format (ESLint, Prettier)"
            ),
            CheckDef(
                "template-validation",
                "📄 Template Validation (Jinja2 syntax check)",
                self._run_template_validation,
            ),
            CheckDef(
                "python-static-analysis", "🔍 Python Static Analysis (mypy, imports)"
            ),
            CheckDef("python-unit-tests", "🧪 Python Unit Tests (pytest, no coverage)"),
            CheckDef(
                "python-coverage",
                "📊 Python Coverage (runs tests + 80% threshold)",
                depends_on="python-unit-tests",
            ),
            CheckDef(
                "js-tests",
                "🧪 JavaScript Tests (Jest)",
            ),
            CheckDef(
                "js-coverage",
                "📊 JavaScript Coverage Analysis (80% threshold)",
            ),
            self.security_check,
            CheckDef(
                "complexity",
                "🧠 Complexity Analysis (radon/xenon)",
                self._run_complexity_analysis,
            ),
            CheckDef("duplication", "🔄 Code Duplication Check"),
            CheckDef("e2e", "🎭 End-to-End Tests (Playwright browser automation)"),
            CheckDef("integration", "🔗 Integration Tests (component interactions)"),
            CheckDef("smoke", "🔥 Smoke Tests (end-to-end validation)"),
            CheckDef(
                "python-new-code-coverage",
                "📊 Python New Code Coverage (80% on changed files)",
                depends_on="python-unit-tests",
            ),
            CheckDef("frontend-check", "🌐 Frontend Check (quick UI validation)"),
        ]

        # Fast checks for commit validation
        # python-unit-tests runs first (generates coverage.xml), then coverage checks analyze it
        self.commit_checks: List[CheckDef] = [
            CheckDef(
                "python-lint-format", "🎨 Python Lint & Format (black, isort, flake8)"
            ),
            CheckDef(
                "js-lint-format", "🎨 JavaScript Lint & Format (ESLint, Prettier)"
            ),
            CheckDef(
                "template-validation",
                "📄 Template Validation (Jinja2 syntax check)",
                self._run_template_validation,
            ),
            CheckDef(
                "python-static-analysis", "🔍 Python Static Analysis (mypy, imports)"
            ),
            CheckDef(
                "python-unit-tests",
                "🧪 Python Unit Tests (pytest with coverage generation)",
            ),
            CheckDef(
                "python-coverage",
                "📊 Python Coverage Analysis (80% threshold)",
                depends_on="python-unit-tests",
            ),
            CheckDef(
                "python-new-code-coverage",
                "📊 Python New Code Coverage (80% on changed files)",
                depends_on="python-unit-tests",
            ),
            CheckDef(
                "js-tests",
                "🧪 JavaScript Tests (Jest)",
            ),
            CheckDef(
                "js-coverage",
                "📊 JavaScript Coverage Analysis (80% threshold)",
            ),
            CheckDef(
                "complexity",
                "🧠 Complexity Analysis (radon/xenon)",
                self._run_complexity_analysis,
            ),
        ]

        # Full checks for PR validation (all checks)
        self.pr_checks: List[CheckDef] = list(self.all_checks)

        # Integration test validation (component interactions using SQLite persistence)
        self.integration_checks: List[CheckDef] = [
            CheckDef(
                "python-lint-format", "🎨 Python Lint & Format (black, isort, flake8)"
            ),
            CheckDef("python-unit-tests", "🧪 Python Unit Tests (pytest, no coverage)"),
            CheckDef("integration", "🔗 Integration Tests (component interactions)"),
        ]

        # Smoke test validation (requires running server + browser)
        self.smoke_checks: List[CheckDef] = [
            CheckDef(
                "python-lint-format", "🎨 Python Lint & Format (black, isort, flake8)"
            ),
            CheckDef("python-unit-tests", "🧪 Python Unit Tests (pytest, no coverage)"),
            CheckDef("smoke", "🔥 Smoke Tests (end-to-end validation)"),
        ]

        # Full validation (everything)
        # Full validation prefers the full security scan over the lightweight variant
        full_commit_checks: List[CheckDef] = [
            self.security_check if check == self.security_local_check else check
            for check in self.commit_checks
        ]
        self.full_checks: List[CheckDef] = full_commit_checks + [
            check for check in self.all_checks if check not in full_commit_checks
        ]

        # Check aliases - map alias names to their check list definitions
        # These allow users to run check groups by name: --checks commit, --checks pr
        self.check_alias_lists: dict[str, List[CheckDef]] = {
            "commit": self.commit_checks,
            "pr": self.pr_checks,
            "integration": self.integration_checks,
            "smoke": self.smoke_checks,
            "full": self.full_checks,
        }

    def _run_complexity_analysis(self) -> CheckResult:
        """Run code complexity analysis using radon and xenon."""
        start_time = time.time()
        try:
            # First check if radon is installed
            try:
                subprocess.run(  # nosec B603,B607
                    ["radon", "--version"],
                    capture_output=True,
                    check=True,
                    text=True,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                return CheckResult(
                    name="complexity",
                    status=CheckStatus.FAILED,
                    duration=time.time() - start_time,
                    output="radon not installed. Install with: pip install radon",
                    error="radon not installed",
                )

            # Run radon to get complexity metrics
            radon_cmd = [
                "radon",
                "cc",
                "-j",  # JSON output for reliable parsing
                "--min",
                "D",  # Minimum rank to show (D or higher)
                "src",
                "tests",
                "scripts",
            ]
            radon_cmd_display = "radon cc --min D -s -a --md src tests scripts"

            radon_result = subprocess.run(  # nosec B603,B607
                radon_cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            try:
                radon_payload = json.loads(radon_result.stdout or "{}")
            except json.JSONDecodeError as exc:
                return CheckResult(
                    name="complexity",
                    status=CheckStatus.FAILED,
                    duration=time.time() - start_time,
                    output=(
                        "🔴 Complexity analysis failed: could not parse radon output "
                        f"({exc})"
                    ),
                    error="radon output parse error",
                )

            high_complexity = []
            for path, entries in radon_payload.items():
                for entry in entries:
                    if entry.get("rank") in {"D", "E", "F"}:
                        high_complexity.append(
                            {
                                "path": path,
                                "name": entry.get("name", "<unknown>"),
                                "rank": entry.get("rank", "?"),
                                "line": entry.get("lineno", 0),
                                "col": entry.get("col_offset", 0),
                                "complexity": entry.get("complexity", 0),
                            }
                        )

            high_complexity.sort(
                key=lambda item: (item["complexity"], item["rank"]), reverse=True
            )

            if high_complexity:
                issues = "\n".join(
                    [
                        (
                            f"{item['rank']} {item['path']}:{item['line']}:{item['col']} "
                            f"{item['name']} ({item['complexity']})"
                        )
                        for item in high_complexity[:10]
                    ]
                )
                more = len(high_complexity) - 10
                more_text = f"\n... and {more} more issues found" if more > 0 else ""

                return CheckResult(
                    name="complexity",
                    status=CheckStatus.FAILED,
                    duration=time.time() - start_time,
                    output=(
                        "🧠 Found "
                        f"{len(high_complexity)} high complexity functions/methods (D or higher):"
                        f"{more_text}\n{issues}\nTo see full complexity output, run: "
                        f"{radon_cmd_display}"
                    ),
                    error=f"Found {len(high_complexity)} high complexity functions",
                )

            return CheckResult(
                name="complexity",
                status=CheckStatus.PASSED,
                duration=time.time() - start_time,
                output="✅ No high complexity issues found (all functions have cyclomatic complexity < 10)",
            )

        except Exception as e:
            return CheckResult(
                name="complexity",
                status=CheckStatus.FAILED,
                duration=time.time() - start_time,
                output=f"🔴 Complexity analysis failed: {str(e)}",
                error=str(e),
            )

    def _run_template_validation(self) -> CheckResult:
        """Run Jinja2 template validation to catch syntax errors before runtime.

        This check compiles all templates to catch issues like:
        - Missing closing braces {{ ... }}
        - Unmatched {% ... %}
        - Invalid Jinja2 syntax

        These errors cause 500 errors at runtime, so we catch them at CI time.
        """
        start_time = time.time()
        try:
            result = subprocess.run(  # nosec B603,B607
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/integration/test_template_smoke.py::test_all_templates_compile",
                    "-v",
                    "--tb=short",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=30,
            )

            duration = time.time() - start_time

            if result.returncode == 0:
                return CheckResult(
                    name="template-validation",
                    status=CheckStatus.PASSED,
                    duration=duration,
                    output="✅ All templates compiled successfully (no Jinja2 syntax errors)",
                )
            else:
                # Extract the actual template error from pytest output
                error_lines = []
                for line in result.stdout.split("\n"):
                    if (
                        "TemplateSyntaxError" in line
                        or "FAILED" in line
                        or "ERROR" in line
                    ):
                        error_lines.append(line)

                error_summary = (
                    "\n".join(error_lines[:10]) if error_lines else result.stdout[-500:]
                )

                return CheckResult(
                    name="template-validation",
                    status=CheckStatus.FAILED,
                    duration=duration,
                    output=f"❌ Template syntax errors detected:\n{error_summary}",
                    error="Jinja2 template syntax error",
                )

        except subprocess.TimeoutExpired:
            return CheckResult(
                name="template-validation",
                status=CheckStatus.FAILED,
                duration=time.time() - start_time,
                output="❌ Template validation timed out after 30s",
                error="Timeout",
            )
        except Exception as e:
            return CheckResult(
                name="template-validation",
                status=CheckStatus.FAILED,
                duration=time.time() - start_time,
                output=f"❌ Template validation failed: {str(e)}",
                error=str(e),
            )

    def _find_contiguous_uncovered_blocks(self, file_data: dict) -> list:
        """Find contiguous blocks of uncovered lines from statement map.

        Returns list of (start_line, end_line, statement_count) tuples
        sorted by statement_count descending (biggest blocks first).
        """
        statement_map = file_data.get("statementMap", {})
        s_hits = file_data.get("s", {})

        # Collect all uncovered line numbers
        uncovered_lines = set()
        for stmt_id, loc in statement_map.items():
            if s_hits.get(stmt_id, 0) == 0:
                start = loc.get("start", {}).get("line", 0)
                end = loc.get("end", {}).get("line", start)
                for line in range(start, end + 1):
                    uncovered_lines.add(line)

        if not uncovered_lines:
            return []

        # Find contiguous blocks
        sorted_lines = sorted(uncovered_lines)
        blocks = []
        block_start = sorted_lines[0]
        prev_line = sorted_lines[0]

        for line in sorted_lines[1:]:
            if line > prev_line + 1:
                # Gap found - save current block
                blocks.append((block_start, prev_line, prev_line - block_start + 1))
                block_start = line
            prev_line = line

        # Don't forget the last block
        blocks.append((block_start, prev_line, prev_line - block_start + 1))

        # Sort by size (biggest blocks first)
        blocks.sort(key=lambda x: x[2], reverse=True)
        return blocks

    def _find_contiguous_line_blocks(self, lines: set[int]) -> list:
        """Find contiguous line blocks from a set of line numbers."""
        if not lines:
            return []

        sorted_lines = sorted(lines)
        blocks = []
        block_start = sorted_lines[0]
        prev_line = sorted_lines[0]

        for line in sorted_lines[1:]:
            if line > prev_line + 1:
                blocks.append((block_start, prev_line, prev_line - block_start + 1))
                block_start = line
            prev_line = line

        blocks.append((block_start, prev_line, prev_line - block_start + 1))
        blocks.sort(key=lambda x: x[2], reverse=True)
        return blocks

    def _parse_diff_hunk_header(self, line: str) -> Optional[int]:
        """Parse unified diff hunk header to extract new start line."""
        try:
            parts = line.split("+")[1].split("@@")[0].strip()
            if "," in parts:
                return int(parts.split(",")[0])
            return int(parts)
        except (ValueError, IndexError):
            return None

    def _normalize_repo_path(self, path: str) -> str:
        normalized = path.replace("\\", "/")
        return normalized[2:] if normalized.startswith("./") else normalized

    def _normalize_coverage_path(self, path: str, repo_root: Path) -> str:
        if os.path.isabs(path):
            try:
                path = os.path.relpath(path, repo_root)
            except ValueError:
                pass
        return self._normalize_repo_path(path)

    def _get_git_diff_output(self) -> str:
        base_candidates = ["origin/main", "main", "master"]
        for base in base_candidates:
            result = subprocess.run(  # nosec B603,B607
                ["git", "diff", "--unified=0", base],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout

        fallback = subprocess.run(  # nosec B603,B607
            ["git", "diff", "--unified=0", "HEAD~1"],
            capture_output=True,
            text=True,
        )
        return fallback.stdout if fallback.returncode == 0 else ""

    def _get_git_added_lines(self) -> dict[str, set[int]]:
        diff_text = self._get_git_diff_output()
        if not diff_text:
            return {}

        added_lines: dict[str, set[int]] = {}
        current_file = None
        current_line_number = 0

        for line in diff_text.split("\n"):
            if line.startswith("+++ b/"):
                current_file = self._normalize_repo_path(line[6:])
                current_line_number = 0
                if current_file not in added_lines:
                    added_lines[current_file] = set()
                continue

            if not current_file:
                continue

            if line.startswith("@@"):
                new_start = self._parse_diff_hunk_header(line)
                if new_start is not None:
                    current_line_number = new_start
                continue

            if line.startswith("+") and not line.startswith("+++"):
                added_lines[current_file].add(current_line_number)
                current_line_number += 1
                continue

            if line.startswith("-"):
                continue

            if current_line_number > 0:
                current_line_number += 1

        return {path: lines for path, lines in added_lines.items() if lines}

    def _get_js_uncovered_new_blocks(
        self, added_lines: Optional[dict[str, set[int]]] = None
    ) -> list:
        coverage_file = "coverage/coverage-final.json"
        if not os.path.exists(coverage_file):
            return []

        if added_lines is None:
            added_lines = self._get_git_added_lines()
        if not added_lines:
            return []

        repo_root = Path(__file__).resolve().parent.parent

        with open(coverage_file, "r") as f:
            data = json.load(f)

        all_blocks = []
        for filepath, file_data in data.items():
            short_path = self._normalize_coverage_path(filepath, repo_root)
            added_for_file = added_lines.get(short_path)
            if not added_for_file:
                continue

            statement_map = file_data.get("statementMap", {})
            s_hits = file_data.get("s", {})

            uncovered_lines = set()
            for stmt_id, loc in statement_map.items():
                if s_hits.get(stmt_id, 0) == 0:
                    start = loc.get("start", {}).get("line", 0)
                    end = loc.get("end", {}).get("line", start)
                    for line in range(start, end + 1):
                        uncovered_lines.add(line)

            uncovered_new_lines = uncovered_lines.intersection(added_for_file)
            if not uncovered_new_lines:
                continue

            blocks = self._find_contiguous_line_blocks(uncovered_new_lines)
            for start, end, count in blocks:
                all_blocks.append((short_path, start, end, count))

        all_blocks.sort(key=lambda x: x[3], reverse=True)
        return all_blocks

    def _get_js_new_code_coverage_report(self) -> list[str]:
        report_lines = [
            "📊 JavaScript Coverage Analysis:",
            (
                "Failure: Detected a decrease in JavaScript coverage in this commit that "
                "would take global coverage below acceptable levels."
            ),
            (
                "This is due to missing test coverage for code introduced in this commit. "
                "We cross-referenced the commit lines against the coverage report and "
                "identified the exact blocks to focus on."
            ),
        ]

        coverage_file = "coverage/coverage-final.json"
        if not os.path.exists(coverage_file):
            report_lines.append(f"⚠️ Coverage report file not found: {coverage_file}")
            return report_lines

        added_lines = self._get_git_added_lines()
        if not added_lines:
            report_lines.append(
                "⚠️ No added lines detected to analyze for this commit."
            )
            return report_lines

        blocks = self._get_js_uncovered_new_blocks(added_lines)
        if not blocks:
            report_lines.extend(
                [
                    "✅ No uncovered new lines were detected in this commit.",
                    (
                        "If coverage still failed, check for removed tests, "
                        "test execution failures, or changes in executed paths."
                    ),
                ]
            )
            return report_lines

        report_lines.append(
            "Uncovered code introduced in this commit (largest blocks first):"
        )
        for filepath, start, end, count in blocks:
            report_lines.append(f"{filepath} {start}-{end} ({count} lines)")

        return report_lines

    def _show_js_coverage_report(self) -> None:
        """Show JavaScript coverage report with actionable instructions.

        Shows uncovered code introduced in this commit by cross-referencing
        modified lines against coverage/coverage-final.json.
        """
        report_lines = self._get_js_new_code_coverage_report()
        self.logger.info("\n" + "\n".join(report_lines))

    def _format_js_coverage_report(self) -> List[str]:
        """Format JavaScript coverage report with actionable instructions.

        Returns lines for inclusion in output using the same new-code report
        as _show_js_coverage_report.
        """
        report_lines = self._get_js_new_code_coverage_report()
        if not report_lines:
            return ["     ⚠️  Coverage report file not found"]

        return ["     " + line if line else "     " for line in report_lines]

    def run_single_check(
        self, check_flag: str, check_name: str, verbose: bool = False
    ) -> CheckResult:
        """Run a single quality check and return the result.

        Args:
            check_flag: The check identifier
            check_name: Human-readable check name
            verbose: If True, stream output directly to console (no buffering)
        """

        start_time = time.time()

        # Map shorthand flags to maintAInability-gate.sh flags
        flag_mapping = {
            "integration": "integration-tests",
            "smoke": "smoke-tests",
            "python-lint-format": "python-lint-format",
            "js-lint-format": "js-lint-format",
            "python-static-analysis": "python-static-analysis",
        }

        # Use mapped flag if available, otherwise use original flag
        actual_flag = flag_mapping.get(check_flag, check_flag)

        try:
            # Configure timeout per check type
            # E2E: 900s (IMAP verification is slow in CI)
            # Others: 900s (default to 15m to avoid premature CI kills)
            if check_flag in ["e2e"]:
                timeout_seconds = 900
            else:
                timeout_seconds = 900

            if check_flag == "smoke":
                os.environ.setdefault("LOOPCLOSER_DEFAULT_PORT_SMOKE", "3003")

            # Build command with verbose flag if enabled
            cmd = [self.script_path, f"--{actual_flag}"]
            if verbose:
                cmd.append("--verbose")

            # Verbose mode: Stream output directly for real-time visibility
            # Normal mode: Capture for formatted output
            if verbose:
                # Stream directly - no buffering, real-time output
                process = subprocess.Popen(  # nosec
                    cmd,
                    text=True,
                )
            else:
                # Capture for formatted summary
                process = subprocess.Popen(  # nosec
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

            self._register_process(process)

            try:
                stdout, stderr = process.communicate(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate() if process.stdout else ("", "")
                duration = time.time() - start_time
                return CheckResult(
                    name=check_name,
                    status=CheckStatus.FAILED,
                    duration=duration,
                    output=stdout or "",
                    error=f"Check timed out after {timeout_seconds}s",
                )
            finally:
                self._unregister_process(process)

            duration = time.time() - start_time

            if process.returncode == 0:
                return CheckResult(
                    name=check_name,
                    status=CheckStatus.PASSED,
                    duration=duration,
                    output=stdout or "",
                )
            else:
                return CheckResult(
                    name=check_name,
                    status=CheckStatus.FAILED,
                    duration=duration,
                    output=stdout or "",
                    error=stderr or "",
                )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return CheckResult(
                name=check_name,
                status=CheckStatus.FAILED,
                duration=duration,
                output="",
                error=f"Check timed out after {duration:.1f} seconds",
            )
        except (subprocess.SubprocessError, OSError) as e:
            duration = time.time() - start_time
            return CheckResult(
                name=check_name,
                status=CheckStatus.FAILED,
                duration=duration,
                output="",
                error=f"Process error: {str(e)}",
            )

    def _register_process(self, process: subprocess.Popen) -> None:
        with self._process_lock:
            self._running_processes[process.pid] = process

    def _unregister_process(self, process: subprocess.Popen) -> None:
        with self._process_lock:
            self._running_processes.pop(process.pid, None)

    def _terminate_running_processes(self, wait_timeout: float = 1.0) -> None:
        """Terminate all running subprocesses.

        Args:
            wait_timeout: How long to wait for graceful termination before killing (default 1.0s)
        """
        with self._process_lock:
            processes = list(self._running_processes.values())
            self._running_processes.clear()

        for proc in processes:
            if proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:  # nosec B110 - Process may already be dead
                    pass
                try:
                    proc.wait(timeout=wait_timeout)
                except subprocess.TimeoutExpired:
                    try:
                        proc.kill()
                    except Exception:  # nosec B110 - Process may already be dead
                        pass

    def _is_server_running(self, port: int = 3001) -> bool:
        """Check if the dev server is running on the specified port."""
        import socket

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(("localhost", port))
                return result == 0
        except Exception:
            return False

    def _get_problem_env(self, check_flags: set[str]) -> str:
        if "smoke" in check_flags:
            return "smoke"
        if "e2e" in check_flags:
            return "e2e"
        return "dev"

    def _resolve_server_port(self, env: str) -> int:
        if env == "smoke":
            return int(os.getenv("LOOPCLOSER_DEFAULT_PORT_SMOKE", "3003"))
        if env == "e2e":
            return int(os.getenv("LOOPCLOSER_DEFAULT_PORT_E2E", "3002"))
        return int(os.getenv("LOOPCLOSER_DEFAULT_PORT_DEV", "3001"))

    def _ensure_server_running(self, checks_to_run: Sequence[CheckDef]) -> bool:
        """Ensure dev server is running if checks require it.

        Args:
            checks_to_run: List of check tuples to examine

        Returns:
            True if server is ready (or not needed), False if server failed to start
        """
        # Checks that require the dev server
        server_dependent_checks = {"frontend-check", "e2e", "smoke"}

        # Extract check flags from tuples (handles both 2 and 3 element tuples)
        check_flags = {check.flag for check in checks_to_run}

        # Check if any server-dependent checks are in the list
        needs_server = bool(check_flags & server_dependent_checks)

        if not needs_server:
            return True

        server_env = self._get_problem_env(check_flags)
        server_port = self._resolve_server_port(server_env)

        # Check if server is already running
        if self._is_server_running(server_port):
            self.logger.info(
                f"✅ Server already running on port {server_port} (env={server_env})"
            )
            return True

        # Server not running, start it
        self.logger.info(
            f"🚀 Starting {server_env} server for frontend/E2E checks on port {server_port}..."
        )

        try:
            # Start server in background
            # Note: restart_server.sh starts the Flask server in background and exits immediately
            # This is CORRECT behavior - we wait for the port to respond, not for the script to finish
            process = subprocess.Popen(  # nosec
                ["bash", "scripts/restart_server.sh", server_env],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for server to be ready (max 30 seconds)
            import time

            max_wait = 30
            start_time = time.time()

            while time.time() - start_time < max_wait:
                if self._is_server_running(server_port):
                    self.logger.info(
                        f"✅ {server_env.capitalize()} server started in {time.time() - start_time:.1f}s"
                    )
                    return True
                time.sleep(0.5)

            # Timeout - check if the restart script itself failed
            # The script exits immediately after starting background server, so poll() will be non-None
            # Only treat as script failure if it exited with non-zero code within first few seconds
            if process.poll() is not None and process.returncode != 0:
                _, stderr = process.communicate()
                self.logger.error(f"❌ Restart script failed: {stderr}")
                return False

            self.logger.error(f"❌ Server failed to start within {max_wait}s")
            self.logger.error("💡 Check logs/server.log for details")
            return False

        except Exception as e:
            self.logger.error(f"❌ Failed to start server: {e}")
            return False

    def run_checks_parallel(
        self,
        checks: List[CheckDef],
        max_workers: Optional[int] = None,  # Use all available CPU cores
        fail_fast: bool = True,
        verbose: bool = False,
    ) -> List[CheckResult]:
        """Run multiple checks in parallel using ThreadPoolExecutor.

        Checks with depends_on will wait for their dependency to complete before starting.
        All checks are submitted immediately for maximum parallelism.
        """
        results: List[CheckResult] = []
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

        # Track completed checks and their results for dependency handling
        completed_checks: dict[str, CheckResult] = {}
        dependency_events: dict[str, threading.Event] = {}

        # Create events for checks that others depend on
        for check in checks:
            dependency_events[check.flag] = threading.Event()

        def run_check_with_dependency(check: CheckDef) -> CheckResult:
            """Run a check, waiting for its dependency if needed."""
            # Wait for dependency to complete if this check has one
            if check.depends_on and check.depends_on in dependency_events:
                self.logger.info(
                    f"⏳ {check.flag} waiting for {check.depends_on} to complete..."
                )
                dependency_events[check.depends_on].wait()

                # If dependency failed, skip this check
                if check.depends_on in completed_checks:
                    dep_result = completed_checks[check.depends_on]
                    if dep_result.status == CheckStatus.FAILED:
                        return CheckResult(
                            name=check.name,
                            status=CheckStatus.SKIPPED,
                            duration=0.0,
                            output="",
                            error=f"Skipped: dependency {check.depends_on} failed",
                        )

            # Run the actual check
            if check.custom is not None:
                result = check.custom()
            else:
                result = self.run_single_check(check.flag, check.name, verbose)

            # Mark this check as completed and signal any waiting checks
            completed_checks[check.flag] = result
            if check.flag in dependency_events:
                dependency_events[check.flag].set()

            return result

        try:
            # Submit all checks immediately - dependencies handled internally
            future_to_check: dict[concurrent.futures.Future[CheckResult], CheckDef] = {}
            for check in checks:
                future = executor.submit(run_check_with_dependency, check)
                future_to_check[future] = check

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_check):
                check_info = future_to_check[future]
                check_name = check_info.name
                try:
                    result = future.result()
                    results.append(result)

                    # Print real-time status updates
                    status_icon = "✅" if result.status == CheckStatus.PASSED else "❌"
                    self.logger.info(
                        f"{status_icon} {result.name} completed in {result.duration:.1f}s"
                    )

                    # Fail-fast: exit immediately on first failure (only if enabled)
                    if fail_fast and result.status == CheckStatus.FAILED:
                        self.logger.error(
                            f"\n🚨 FAIL-FAST: {result.name} failed, terminating immediately..."
                        )
                        self.logger.info("\n📋 Failure Details:")
                        self.logger.info("━" * 60)
                        self.logger.info(result.output)
                        self.logger.info("━" * 60)

                        # If JS coverage failed, show the coverage report
                        if "JavaScript Coverage" in result.name:
                            self._show_js_coverage_report()

                        # Terminate all running processes FIRST (before canceling futures)
                        self._terminate_running_processes()

                        # Cancel all remaining futures
                        for f in future_to_check:
                            f.cancel()

                        # Shutdown executor immediately without waiting for threads
                        executor.shutdown(wait=False, cancel_futures=True)

                        # Force exit immediately - don't wait for anything
                        os._exit(1)  # More forceful than sys.exit(1), bypasses cleanup

                except (concurrent.futures.TimeoutError, RuntimeError) as exc:
                    # Handle any exceptions from the future
                    results.append(
                        CheckResult(
                            name=check_name,
                            status=CheckStatus.FAILED,
                            duration=0.0,
                            output="",
                            error=f"Thread execution failed: {exc}",
                        )
                    )
                    self.logger.error(f"❌ {check_name} failed with exception: {exc}")

        finally:
            # Ensure executor is properly cleaned up
            # If we've already aborted via sys.exit(1) in the failure block,
            # this might still run but we use wait=False if we want true fail-fast
            executor.shutdown(wait=False)

        return results

    def _format_header(self, total_duration: float) -> List[str]:
        """Format the report header."""
        return [
            "📊 Python/Flask Quality Gate Report",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            f"⏱️  Total execution time: {total_duration:.1f}s (parallel)",
            "🐍 Python/Flask project quality validation",
            "",
        ]

    def _format_passed_checks(self, passed_checks: List[CheckResult]) -> List[str]:
        """Format passed checks section."""
        if not passed_checks:
            return []

        lines = [f"✅ PASSED CHECKS ({len(passed_checks)}):"]
        for result in passed_checks:
            # Try to extract success message from bash output
            message = self._extract_success_message(result)
            if message:
                lines.append(f"   • {result.name}: {message}")
            else:
                lines.append(f"   • {result.name}: Completed in {result.duration:.1f}s")
        lines.append("")
        return lines

    def _extract_success_message(self, result: CheckResult) -> Optional[str]:
        """Extract success message from bash script output."""
        # For JavaScript coverage, extract the actual percentages from the detailed output
        if "JavaScript Coverage" in result.name:
            lines_pct = None
            statements_pct = None
            branches_pct = None
            functions_pct = None

            for line in result.output.split("\n"):
                stripped = line.strip()
                if stripped.startswith("Lines:"):
                    lines_pct = stripped.split()[1]
                elif stripped.startswith("Statements:"):
                    statements_pct = stripped.split()[1]
                elif stripped.startswith("Branches:"):
                    branches_pct = stripped.split()[1]
                elif stripped.startswith("Functions:"):
                    functions_pct = stripped.split()[1]

            if lines_pct:
                return f"Lines: {lines_pct} ✅ | Statements: {statements_pct} | Branches: {branches_pct} | Functions: {functions_pct}"

        # For other checks, look for pattern: "   • {name}: {message}"
        for line in result.output.split("\n"):
            stripped = line.strip()
            if stripped.startswith("• "):
                # Extract message after first ": "
                parts = stripped.split(": ", 1)
                if len(parts) == 2:
                    check_name = parts[0].replace("• ", "").strip()
                    message = parts[1].strip()
                    # Match if bash name is substring of result.name
                    if check_name in result.name or result.name in check_name:
                        return message
        return None

    def _filter_meaningful_lines(self, output_lines: List[str]) -> List[str]:
        """Filter out empty lines and pip noise from output."""
        return [
            line for line in output_lines if line.strip() and not line.startswith("pip")
        ]

    def _format_check_output(self, result: CheckResult) -> List[str]:
        """Format output section for a failed check."""
        if not result.output:
            return []

        lines = []
        output_lines = result.output.strip().split("\n")
        meaningful_lines = self._filter_meaningful_lines(output_lines)
        display_lines = meaningful_lines[:20]  # Show up to 20 meaningful lines

        if display_lines:
            lines.append("     Output:")
            for line in display_lines:
                lines.append(f"       {line}")

        if len(meaningful_lines) > 20:
            lines.extend(
                [
                    f"       ... and {len(meaningful_lines) - 20} more lines",
                    "       Run the individual check for full details",
                ]
            )

        return lines

    def _format_single_failed_check(self, result: CheckResult) -> List[str]:
        """Format a single failed check with error and output."""
        lines = [f"   • {result.name}"]

        if result.error:
            lines.append(f"     Error: {result.error}")

        lines.extend(self._format_check_output(result))

        # If JavaScript coverage failed, include the detailed coverage report
        if "JavaScript Coverage" in result.name:
            lines.extend(self._format_js_coverage_report())

        lines.append("")

        return lines

    def _format_failed_checks(self, failed_checks: List[CheckResult]) -> List[str]:
        """Format failed checks section with detailed error output."""
        if not failed_checks:
            return []

        lines = [f"❌ FAILED CHECKS ({len(failed_checks)}):"]
        for result in failed_checks:
            lines.extend(self._format_single_failed_check(result))
        return lines

    def _get_check_flag(self, result_name: str) -> str:
        """Get the command-line flag for a specific check result."""
        for check in self.all_checks:
            if check.name == result_name:
                return check.flag
        return "unknown"

    def _format_success_summary(self) -> List[str]:
        """Format summary section for successful validation."""
        return [
            "🎉 ALL CHECKS PASSED!",
            "✅ Ready to commit with confidence!",
            "",
            "🚀 Python/Flask quality validation completed successfully!",
        ]

    def _format_failure_summary(self, failed_checks: List[CheckResult]) -> List[str]:
        """Format summary section for failed validation."""
        lines = [
            "❌ QUALITY GATE FAILED",
            f"🔧 {len(failed_checks)} check(s) need attention",
            "",
            "💡 Run individual checks for detailed output:",
        ]

        for result in failed_checks:
            check_flag = self._get_check_flag(result.name)
            lines.append(
                f"   • {result.name}: ./scripts/maintAInability-gate.sh --{check_flag}"
            )

        return lines

    def _format_summary(self, failed_checks: List[CheckResult]) -> List[str]:
        """Format the final summary section."""
        lines = ["━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]

        if not failed_checks:
            lines.extend(self._format_success_summary())
        else:
            lines.extend(self._format_failure_summary(failed_checks))

        return lines

    def _extract_coverage_failure_reason(self, output: str) -> Optional[str]:
        """Extract coverage failure details from output."""
        output_lower = output.lower()
        if "coverage" not in output_lower:
            return None

        if (
            "threshold" in output_lower
            or "below" in output_lower
            or "fail" in output_lower
        ):
            # Try multiple patterns for coverage extraction
            coverage_match = re.search(
                r"(\d+\.?\d*)%[^%]*(?:not met|below|fail)[^%]*(\d+\.?\d*)%", output
            )
            if not coverage_match:
                coverage_match = re.search(
                    r"Coverage[^%]*(\d+\.?\d*)%[^%]*below[^%]*(\d+\.?\d*)%", output
                )
            if not coverage_match:
                # Look for pytest-cov style output
                coverage_match = re.search(r"TOTAL[^%]*(\d+)%", output)
                if coverage_match:
                    actual = coverage_match.group(1)
                    return f"Coverage threshold not met: {actual}% < 80%"

            if coverage_match and len(coverage_match.groups()) >= 2:
                actual, threshold = coverage_match.groups()
                return f"Coverage threshold not met: {actual}% < {threshold}%"

            # Specific fallback for failures without parsed numbers
            return "Coverage threshold not met (below 80%)"

        if "fail" in output_lower or "error" in output_lower:
            return "Coverage analysis failed or below 80% threshold"

        return None

    def _extract_test_failure_reason(self, output: str) -> str:
        """Extract specific failure reason from pytest output."""
        if not output:
            return "Unknown test failure"

        # Check for actual test failures first (highest priority)
        failed_match = re.search(r"(\d+)\s+failed", output)
        if failed_match:
            failed_count = failed_match.group(1)
            return f"Test failures: {failed_count} test(s) failed"

        # Check coverage issues
        coverage_reason = self._extract_coverage_failure_reason(output)
        if coverage_reason:
            return coverage_reason

        # Check for import errors
        if "import" in output.lower() and "error" in output.lower():
            return "Import errors detected"

        # Check for syntax errors
        if "syntax" in output.lower() and "error" in output.lower():
            return "Syntax errors detected"

        return "Test suite execution failed"

    def format_results(self, results: List[CheckResult], total_duration: float) -> str:
        """Format the results into a comprehensive report."""
        passed_checks = [r for r in results if r.status == CheckStatus.PASSED]
        failed_checks = [r for r in results if r.status == CheckStatus.FAILED]
        skipped_checks = [r for r in results if r.status == CheckStatus.SKIPPED]

        report = []
        report.extend(self._format_header(total_duration))
        report.extend(self._format_passed_checks(passed_checks))
        report.extend(self._format_failed_checks(failed_checks))
        report.extend(self._format_skipped_checks(skipped_checks))
        report.extend(self._format_summary(failed_checks))

        return "\n".join(report)

    def _format_skipped_checks(self, skipped_checks: List[CheckResult]) -> List[str]:
        """Format skipped checks section."""
        if not skipped_checks:
            return []

        lines = [f"⏭️  SKIPPED CHECKS ({len(skipped_checks)}):"]
        for result in skipped_checks:
            reason = result.error or "Dependency failed"
            lines.append(f"   • {result.name}: {reason}")
        lines.append("")
        return lines

    def execute(
        self,
        checks: List[str],
        fail_fast: bool = True,
    ) -> int:
        """Execute quality checks in parallel and return exit code.

        Args:
            checks: List of check names or aliases to run (required)
            fail_fast: If True, stop on first failure (default True)

        Dependencies:
            Checks with depends_on will wait for their dependency to complete.
            All checks start immediately for maximum parallelism - dependencies
            are handled via threading.Event synchronization.
        """
        self.logger.info(
            "🔍 Running LoopCloser quality checks (PARALLEL MODE with auto-fix)..."
        )
        self.logger.info("🐍 Python/Flask enterprise validation suite")
        self.logger.info("")

        try:
            checks_to_run = self._checks_for_user_selected_checks(checks)
        except ValueError:
            return 1

        # Note: Each check manages its own server/resources independently
        # No shared server startup needed - checks are self-contained

        start_time = time.time()

        # Run all checks in parallel - dependency handling is internal to run_checks_parallel
        check_names = [check.flag for check in checks_to_run]
        self.logger.info(f"🚀 Running checks in parallel: [{', '.join(check_names)}]")

        all_results = self.run_checks_parallel(
            checks_to_run, fail_fast=fail_fast, verbose=self.verbose
        )

        total_duration = time.time() - start_time

        # Format and display results
        self.logger.info("\n" + self.format_results(all_results, total_duration))

        # Return appropriate exit code
        failed_count = len([r for r in all_results if r.status == CheckStatus.FAILED])
        return 1 if failed_count > 0 else 0

    def _checks_for_user_selected_checks(self, checks: List[str]) -> List[CheckDef]:
        """Return configured checks for explicitly provided flags or aliases.

        Supports both individual check names and aliases:
        - Individual: --checks tests coverage js-tests
        - Aliases: --checks commit (expands to all commit checks)
        - Mixed: --checks commit security (commit checks + security)
        """
        available_checks: dict[str, CheckDef] = {
            check.flag: check for check in self.all_checks
        }

        # Expand aliases first - aliases return CheckDef lists directly
        expanded_check_defs: List[CheckDef] = []
        individual_checks: List[str] = []

        for check in checks:
            if check in self.check_alias_lists:
                alias_flags = [c.flag for c in self.check_alias_lists[check]]
                self.logger.info(
                    f"📦 Expanding alias '{check}' to: {', '.join(alias_flags)}"
                )
                expanded_check_defs.extend(self.check_alias_lists[check])
            else:
                individual_checks.append(check)

        # Process individual check names
        for check in individual_checks:
            if check in available_checks:
                expanded_check_defs.append(available_checks[check])
            else:
                self.logger.error(f"❌ Unknown check: {check}")
                alias_list = ", ".join(self.check_alias_lists.keys())
                check_list = ", ".join(available_checks.keys())
                self.logger.info(f"Available aliases: {alias_list}")
                self.logger.info(f"Available checks: {check_list}")
                raise ValueError(f"Unknown check: {check}")

        # Deduplicate while preserving order (by flag name)
        seen: set[str] = set()
        checks_to_run: List[CheckDef] = []
        for check_def in expanded_check_defs:
            if check_def.flag not in seen:
                seen.add(check_def.flag)
                checks_to_run.append(check_def)

        # Validate coverage check dependencies
        # python-coverage and python-new-code-coverage require python-unit-tests
        coverage_checks = {"python-coverage", "python-new-code-coverage"}
        requested_flags = {c.flag for c in checks_to_run}
        has_coverage_check = bool(requested_flags & coverage_checks)
        has_unit_tests = "python-unit-tests" in requested_flags

        if has_coverage_check and not has_unit_tests:
            missing_checks = requested_flags & coverage_checks
            self.logger.error("❌ Coverage checks require python-unit-tests")
            self.logger.error(f"   Requested: {', '.join(missing_checks)}")
            self.logger.error(
                "   These checks analyze coverage.xml which must be freshly generated."
            )
            self.logger.error(
                "   Fix: --checks python-unit-tests " + " ".join(missing_checks)
            )
            raise ValueError(
                "Coverage checks require python-unit-tests in the same execution"
            )

        return checks_to_run

    def _extract_slow_tests(self, output: str) -> List[str]:
        """Extract slow tests (>0.5s) from pytest output with --durations=0."""
        slow_tests = []

        # Look for duration lines in format: "0.52s call     tests/test_example.py::test_slow"
        duration_pattern = r"(\d+\.\d+)s\s+\w+\s+(tests/[^:]+::[^\s]+)"

        for match in re.finditer(duration_pattern, output):
            duration = float(match.group(1))
            test_name = match.group(2)

            if duration > 0.5:  # Threshold for slow tests
                slow_tests.append(f"{duration:.2f}s {test_name}")

        return sorted(slow_tests, key=lambda x: float(x.split("s")[0]), reverse=True)


def _get_pr_context() -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """
    Get PR number and repository info from environment or git context.

    Returns:
        Tuple of (pr_number, owner, name) or (None, None, None) if not in PR context
    """
    import json
    import subprocess  # nosec

    # Detect current PR number from branch or environment
    pr_number = os.getenv("PR_NUMBER")
    if not pr_number:
        # Try to get from current branch if we're in a PR
        try:
            result = subprocess.run(  # nosec
                ["gh", "pr", "view", "--json", "number,url,title"],
                capture_output=True,
                text=True,
                check=True,
            )
            pr_data = json.loads(result.stdout)
            pr_number = pr_data.get("number")
        except:
            # No PR context
            return None, None, None

    if not pr_number:
        return None, None, None

    # Get repository info
    try:
        repo_result = subprocess.run(  # nosec
            ["gh", "repo", "view", "--json", "owner,name"],
            capture_output=True,
            text=True,
            check=True,
        )
        repo_data = json.loads(repo_result.stdout)
        owner = repo_data.get("owner", {}).get("login", "")
        name = repo_data.get("name", "")
        return int(pr_number), owner, name
    except:
        print("⚠️  Could not detect repository info")
        return None, None, None


def _load_tracked_comments(pr_number: int) -> set[str]:
    """
    Load previously tracked comment IDs from file.

    Returns:
        Set of comment IDs that have been seen before
    """
    import json

    tracking_file = f"logs/pr_{pr_number}_comments_tracked.json"
    if os.path.exists(tracking_file):
        try:
            with open(tracking_file, "r") as f:
                data = json.load(f)
                return set(data.get("seen_comment_ids", []))
        except:
            return set()
    return set()


def _save_tracked_comments(pr_number: int, comment_ids: set[str]) -> None:
    """
    Save tracked comment IDs to file.

    Args:
        pr_number: PR number
        comment_ids: Set of comment IDs to track
    """
    import json

    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    tracking_file = f"logs/pr_{pr_number}_comments_tracked.json"
    data = {
        "pr_number": pr_number,
        "seen_comment_ids": list(comment_ids),
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        with open(tracking_file, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️  Could not save tracked comments: {e}")


def resolve_review_thread(thread_id: str) -> bool:
    """
    Resolve a review thread via GitHub GraphQL API.

    Args:
        thread_id: The GitHub review thread ID (e.g., "PRRT_kwDOOV6J2s5g4yRA")

    Returns:
        True if successful, False otherwise
    """
    try:
        import json
        import subprocess  # nosec

        pr_number, owner, name = _get_pr_context()
        if not pr_number:
            return False

        # GraphQL mutation to resolve a review thread
        mutation = """
        mutation($threadId: ID!) {
          resolveReviewThread(input: {threadId: $threadId}) {
            thread {
              id
              isResolved
            }
          }
        }
        """

        result = subprocess.run(  # nosec
            [
                "gh",
                "api",
                "graphql",
                "-F",
                f"owner={owner}",
                "-F",
                f"name={name}",
                "-F",
                f"number={pr_number}",
                "-f",
                f"query={mutation}",
                "-f",
                f"threadId={thread_id}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            if (
                data.get("data", {})
                .get("resolveReviewThread", {})
                .get("thread", {})
                .get("isResolved")
            ):
                return True

        return False

    except Exception as e:
        print(f"⚠️  Could not resolve review thread {thread_id}: {e}")
        return False


def reply_to_pr_comment(
    comment_id: str,
    body: str,
    thread_id: Optional[str] = None,
    resolve_thread: bool = False,
) -> bool:
    """
    Reply to a PR comment and optionally resolve the thread.

    Args:
        comment_id: The comment ID to reply to (for general comments)
        body: The reply body text
        thread_id: The review thread ID (for inline comments)
        resolve_thread: Whether to resolve the thread after replying

    Returns:
        True if successful, False otherwise
    """
    try:
        import json
        import subprocess  # nosec

        pr_number, owner, name = _get_pr_context()
        if not pr_number:
            return False

        try:
            # Try to post a comment to the PR
            comment = {"body": body}

            # Use GitHub CLI to post the comment
            result = subprocess.run(  # nosec B603,B607
                [
                    "gh",
                    "api",
                    f"repos/{owner}/{name}/issues/{pr_number}/comments",
                    "-X",
                    "POST",
                    "-H",
                    "Accept: application/vnd.github.v3+json",
                    "-f",
                    f"body={comment['body']}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            return result.returncode == 0

        except Exception as e:
            print(f"⚠️  Could not post PR comment: {e}")
            return False

    except Exception as e:
        print(f"⚠️  Could not reply to PR comment: {e}")
        return False


def check_pr_comments() -> Tuple[List[Any], List[Any]]:
    """
    Check for unresolved PR comments (both review threads and general PR comments).

    Returns:
        Tuple of (all_unresolved_comments, new_comments) where:
        - all_unresolved_comments: List of all unresolved comment dictionaries
        - new_comments: List of comments not seen before (for tracking)
    """
    try:
        import json
        import subprocess  # nosec

        pr_number, owner, name = _get_pr_context()
        if not pr_number:
            return [], []

        # Load previously tracked comments
        tracked_ids = _load_tracked_comments(pr_number)

        # GraphQL query for both review threads AND general PR comments
        graphql_query = """
        query($owner: String!, $name: String!, $number: Int!) {
          repository(owner: $owner, name: $name) {
            pullRequest(number: $number) {
              reviewThreads(first: 50) {
                nodes {
                  id
                  isResolved
                  comments(first: 1) {
                    nodes {
                      id
                      body
                      path
                      line
                      author {
                        login
                      }
                      createdAt
                    }
                  }
                }
              }
              comments(first: 50) {
                nodes {
                  id
                  body
                  author {
                    login
                  }
                  createdAt
                }
              }
            }
          }
        }
        """

        # Execute GraphQL query
        result = subprocess.run(  # nosec
            [
                "gh",
                "api",
                "graphql",
                "-F",
                f"owner={owner}",
                "-F",
                f"name={name}",
                "-F",
                f"number={pr_number}",
                "-f",
                f"query={graphql_query}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        data = json.loads(result.stdout)
        pr_data = data.get("data", {}).get("repository", {}).get("pullRequest", {})

        # Process review threads (inline code comments)
        threads = pr_data.get("reviewThreads", {}).get("nodes", [])
        unresolved_threads = []
        for thread in threads:
            if not thread.get("isResolved", True):
                comment = thread.get("comments", {}).get("nodes", [{}])[0]
                comment_id = comment.get("id")
                unresolved_threads.append(
                    {
                        "id": comment_id,
                        "thread_id": thread.get("id"),
                        "body": comment.get("body", ""),
                        "author": comment.get("author", {}).get("login", "unknown"),
                        "created_at": comment.get("createdAt", ""),
                        "path": comment.get("path"),
                        "line": comment.get("line"),
                        "type": "review_thread",
                    }
                )

        # Process general PR comments (non-inline comments)
        general_comments = pr_data.get("comments", {}).get("nodes", [])
        unresolved_general = []
        for comment in general_comments:
            comment_id = comment.get("id")
            unresolved_general.append(
                {
                    "id": comment_id,
                    "body": comment.get("body", ""),
                    "author": comment.get("author", {}).get("login", "unknown"),
                    "created_at": comment.get("createdAt", ""),
                    "path": None,
                    "line": None,
                    "type": "general_comment",
                }
            )

        # Combine all unresolved comments
        all_unresolved = unresolved_threads + unresolved_general

        # Identify new comments (not previously tracked)
        new_comments = [c for c in all_unresolved if c.get("id") not in tracked_ids]

        # Update tracking file with all current comment IDs
        current_ids: set[str] = set()
        for c in all_unresolved:
            comment_id = c.get("id")
            if comment_id is not None and isinstance(comment_id, str):
                current_ids.add(comment_id)
        if current_ids:
            _save_tracked_comments(pr_number, current_ids | tracked_ids)

        return all_unresolved, new_comments

    except Exception as e:
        print(f"⚠️  Could not check PR comments: {e}")
        return [], []


def _parse_rollup_items(
    statuses: List[Any],
) -> Tuple[List[str], List[str], List[str]]:
    """Parse statusCheckRollup items to categorize jobs."""
    failed: List[str] = []
    in_progress: List[str] = []
    pending: List[str] = []

    for status in statuses:
        state = status.get("state", "").lower() if status.get("state") else None
        conclusion = (
            status.get("conclusion", "").lower() if status.get("conclusion") else None
        )
        name = status.get("name", "Unknown")

        # For completed checks, use conclusion; for in-progress, use state
        if conclusion == "failure" or conclusion == "error":
            failed.append(name)
        elif conclusion == "cancelled":
            failed.append(name)
        elif state == "pending" or state == "queued":
            if "in progress" in name.lower() or "running" in name.lower():
                in_progress.append(name)
            else:
                pending.append(name)
        elif (
            state == "in_progress" or status.get("status", "").upper() == "IN_PROGRESS"
        ):
            in_progress.append(name)

    return failed, in_progress, pending


def _get_ci_status_from_rollup(
    pr_number: int,
) -> Optional[Any]:
    """Try to get CI status from GitHub statusCheckRollup."""
    try:
        import json
        import subprocess  # nosec

        # Use statusCheckRollup first - it gives us individual job/check names
        result = subprocess.run(  # nosec
            [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--json",
                "statusCheckRollup",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            pr_data = json.loads(result.stdout)
            statuses = pr_data.get("statusCheckRollup", [])

            failed, in_progress, pending = _parse_rollup_items(statuses)

            return {
                "all_passed": len(failed) == 0
                and len(pending) == 0
                and len(in_progress) == 0,
                "failed_jobs": failed,
                "in_progress_jobs": in_progress,
                "pending_jobs": pending,
                "workflow_runs": statuses,
            }
    except Exception:  # nosec B110 - intentional fallback, failure acceptable
        pass
    return None


def _get_ci_status_fallback(pr_number: int, owner: str, name: str) -> Optional[Any]:
    """Fallback to workflow runs API if rollup fails."""
    import json
    import subprocess  # nosec

    # Fallback to workflow runs API (less detailed, but better than nothing)
    result = subprocess.run(  # nosec
        [
            "gh",
            "api",
            f"repos/{owner}/{name}/actions/runs",
            "--jq",
            f".workflow_runs[] | select(.pull_requests[]?.number == {pr_number}) | {{id, name, status, conclusion, created_at, html_url}}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    # Parse workflow runs
    workflow_runs = []
    if result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    workflow_runs.append(json.loads(line))
                except Exception:  # nosec B110 - skip malformed JSON lines
                    pass

    # Analyze workflow run statuses
    failed = []
    in_progress = []
    pending = []

    for run in workflow_runs:
        run_name = run.get("name", "Unknown")
        status = run.get("status", "").lower()
        conclusion = run.get("conclusion", "").lower()

        if conclusion == "failure" or conclusion == "cancelled":
            failed.append(run_name)
        elif status == "in_progress":
            in_progress.append(run_name)
        elif status == "queued" or status == "pending":
            pending.append(run_name)

    return {
        "all_passed": len(failed) == 0 and len(pending) == 0 and len(in_progress) == 0,
        "failed_jobs": failed,
        "in_progress_jobs": in_progress,
        "pending_jobs": pending,
        "workflow_runs": workflow_runs,
    }


def check_ci_status() -> Optional[Any]:
    """
    Check GitHub Actions CI status for the current PR.

    Returns:
        Dictionary with CI status information.
    """
    try:
        pr_number, owner, name = _get_pr_context()
        if not pr_number or not owner or not name:
            return {
                "all_passed": None,
                "failed_jobs": [],
                "in_progress_jobs": [],
                "pending_jobs": [],
                "workflow_runs": [],
                "error": "Not in PR context",
            }

        # Try primary method
        status = _get_ci_status_from_rollup(pr_number)
        if status:
            return status

        # Try fallback method
        status = _get_ci_status_fallback(pr_number, owner, name)
        if status:
            return status

        return {
            "all_passed": None,
            "failed_jobs": [],
            "in_progress_jobs": [],
            "pending_jobs": [],
            "workflow_runs": [],
            "error": "Could not fetch CI status",
        }

    except Exception as e:
        return {
            "all_passed": None,
            "failed_jobs": [],
            "in_progress_jobs": [],
            "pending_jobs": [],
            "workflow_runs": [],
            "error": f"Error checking CI status: {str(e)}",
        }


def _get_current_commit_sha() -> Optional[str]:
    """Get the current git commit SHA."""
    import subprocess  # nosec

    try:
        result = subprocess.run(  # nosec
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except:
        return "unknown"


def _save_check_error_logs(
    failed_checks: List[CheckResult],
    pr_number: int,
    commit_sha: str,
    timestamp: str,
) -> dict[str, str]:
    """Save full error output for each failed check to log files."""
    error_log_files: dict[str, str] = {}
    for check in failed_checks:
        check_flag = _get_check_flag_for_result(check.name)
        error_log_file = f"logs/pr_{pr_number}_error_{check_flag}_{commit_sha[:8]}.log"
        error_log_files[check.name] = error_log_file

        with open(error_log_file, "w", encoding="utf-8") as f:
            f.write(f"# Full Error Output: {check.name}\n\n")
            f.write(f"**PR**: #{pr_number}\n")
            f.write(f"**Commit**: `{commit_sha}`\n")
            f.write(f"**Check**: {check.name}\n")
            f.write(f"**Duration**: {check.duration:.1f}s\n")
            f.write(f"**Generated**: {timestamp}\n\n")
            f.write("---\n\n")

            if check.error:
                f.write("## Error\n\n")
                f.write("```\n")
                f.write(check.error)
                f.write("\n```\n\n")

            if check.output:
                f.write("## Full Output\n\n")
                f.write("```\n")
                f.write(check.output)
                f.write("\n```\n")
    return error_log_files


def _write_checklist_ci_section(
    f: Any,
    ci_status: Any,
    checklist_state: Any,
    checklist_items: List[dict[str, Any]],
    item_number: int,
) -> int:
    """Write CI Status section to the checklist."""
    if ci_status.get("all_passed") is not False:
        return item_number

    f.write(f"### {item_number}. CI Status Issues\n\n")
    checklist_items.append(
        {
            "number": item_number,
            "category": "CI Status",
            "status": "pending",
            "items": [],
        }
    )

    if ci_status.get("failed_jobs"):
        f.write("**Failed Jobs:**\n")
        for job in ci_status.get("failed_jobs", []):
            item_text = f"Fix failing CI job: {job}"
            item_status = _get_item_status(checklist_state, item_text)
            checkbox = "- [x]" if item_status == "completed" else "- [ ]"
            status_icon = "✅" if item_status == "completed" else "❌"
            f.write(f"{checkbox} {status_icon} Fix failing CI job: `{job}`\n")
            checklist_items[-1]["items"].append(item_text)

    if ci_status.get("in_progress_jobs"):
        f.write("\n**In Progress:**\n")
        for job in ci_status.get("in_progress_jobs", []):
            f.write(f"- [ ] ⏳ Wait for CI job to complete: `{job}`\n")
            checklist_items[-1]["items"].append(f"Wait for CI job: {job}")

    if ci_status.get("pending_jobs"):
        f.write("\n**Pending:**\n")
        for job in ci_status.get("pending_jobs", []):
            f.write(f"- [ ] ⏸️  Wait for CI job to start: `{job}`\n")
            checklist_items[-1]["items"].append(f"Wait for CI job: {job}")

    f.write("\n")
    return item_number + 1


def _resolve_comment_location(comment: Any) -> str:
    """Resolve location string for a comment."""
    if comment.get("path") and comment.get("line"):
        return f"`{comment['path']}:{comment['line']}`"
    elif comment.get("path"):
        return f"`{comment['path']}`"
    return ""


def _write_single_comment_item(
    f: Any,
    comment: Any,
    location: str,
    is_new: bool,
    checklist_state: Any,
    checklist_items: List[Any],
) -> None:
    """Write a single comment item to the checklist."""
    author = comment["author"]
    body = comment["body"]

    item_text = f"Address comment from {author}"
    if location:
        item_text = f"Address comment from {author} at {location}"

    if is_new:
        item_status = _get_item_status(checklist_state, item_text)
        checkbox = "- [x]" if item_status == "completed" else "- [ ]"
        status_icon = "✅" if item_status == "completed" else "🆕"
        f.write(f"{checkbox} {status_icon} Address comment from `{author}`")
    else:
        f.write(f"- [ ] Address comment from `{author}`")

    if location:
        f.write(f" at {location}")
    f.write(f"\n")
    f.write(f"  > {body[:200]}...\n\n")
    checklist_items[-1]["items"].append(item_text)


def _write_checklist_comments_section(
    f: Any,
    comments_data: Tuple[List[Any], List[Any]],
    checklist_state: Any,
    checklist_items: List[Any],
    item_number: int,
) -> int:
    """Write PR Comments section to the checklist."""
    all_comments, new_comments = comments_data
    if not all_comments:
        return item_number

    f.write(f"### {item_number}. PR Review Comments\n\n")
    checklist_items.append(
        {
            "number": item_number,
            "category": "PR Comments",
            "status": "pending",
            "items": [],
        }
    )

    if new_comments:
        f.write(f"**New Comments ({len(new_comments)}):**\n\n")
        for comment in new_comments:
            location = _resolve_comment_location(comment)
            _write_single_comment_item(
                f, comment, location, True, checklist_state, checklist_items
            )

    if len(all_comments) > len(new_comments):
        f.write(
            f"**Previously Seen Comments ({len(all_comments) - len(new_comments)}):**\n\n"
        )
        new_ids = {c.get("id") for c in new_comments} if new_comments else set()

        for comment in all_comments:
            if not new_comments or comment.get("id") not in new_ids:
                location = _resolve_comment_location(comment)
                _write_single_comment_item(
                    f, comment, location, False, checklist_state, checklist_items
                )

    f.write("\n")
    return item_number + 1


def _write_checklist_quality_section(
    f: Any,
    failed_checks: List[CheckResult],
    error_log_files: dict[str, str],
    checklist_state: Any,
    checklist_items: List[Any],
    item_number: int,
) -> int:
    """Write Quality Gate Failures section to the checklist."""
    if not failed_checks:
        return item_number

    f.write(f"### {item_number}. Quality Gate Failures\n\n")
    checklist_items.append(
        {
            "number": item_number,
            "category": "Quality Gates",
            "status": "pending",
            "items": [],
        }
    )

    for check in failed_checks:
        error_log_file = error_log_files.get(check.name, "")
        item_text = f"Fix failing check: {check.name}"
        item_status = _get_item_status(checklist_state, item_text)
        checkbox = "- [x]" if item_status == "completed" else "- [ ]"
        status_icon = "✅" if item_status == "completed" else "❌"
        f.write(f"{checkbox} {status_icon} Fix failing check: **{check.name}**\n")
        if check.error:
            f.write(f"  - Error: {check.error[:200]}...\n")
        f.write(f"  - Duration: {check.duration:.1f}s\n")
        f.write(
            f"  - Run: `python scripts/ship_it.py --checks {_get_check_flag_for_result(check.name)}`\n"
        )
        if error_log_file:
            f.write(f"  - 📄 Full error log: `{error_log_file}`\n")
            f.write(
                f"  - View: `cat {error_log_file}` or `python scripts/view_check_error.py {_get_check_flag_for_result(check.name)}`\n"
            )
        f.write("\n")
        checklist_items[-1]["items"].append(f"Fix failing check: {check.name}")

    f.write("\n")
    return item_number + 1


def _write_report_summary(
    f: Any,
    checklist_items: List[Any],
    ci_status: Any,
    comments_data: Tuple[List[Any], List[Any]],
    passed_checks: List[CheckResult],
    failed_checks: List[CheckResult],
) -> None:
    """Write the report summary section."""
    all_comments, new_comments = comments_data
    f.write("---\n\n")
    f.write("## 📊 Summary\n\n")
    f.write(
        f"- **Total Checklist Items**: {sum(len(item['items']) for item in checklist_items)}\n"
    )
    f.write(
        f"- **CI Status**: {'✅ Passed' if ci_status.get('all_passed') is True else '❌ Failed' if ci_status.get('all_passed') is False else '⚠️ Unknown'}\n"
    )
    f.write(f"- **Outstanding Comments**: {len(all_comments)}\n")
    f.write(f"  - New: {len(new_comments)}\n")
    f.write(f"  - Previously Seen: {len(all_comments) - len(new_comments)}\n")
    f.write(
        f"- **Quality Checks**: {len(passed_checks)} passed, {len(failed_checks)} failed\n\n"
    )


def _write_detailed_sections(
    f: Any,
    ci_status: Any,
    failed_checks: List[CheckResult],
    error_log_files: dict[str, str],
) -> None:
    """Write the detailed information sections."""
    f.write("---\n\n")
    f.write("## 📋 Detailed Information\n\n")

    # CI Status Details
    f.write("### CI Status Details\n\n")
    if ci_status.get("error"):
        f.write(f"⚠️ Error: {ci_status.get('error')}\n\n")
    else:
        f.write(f"- **All Passed**: {ci_status.get('all_passed')}\n")
        f.write(f"- **Failed Jobs**: {len(ci_status.get('failed_jobs', []))}\n")
        f.write(f"- **In Progress**: {len(ci_status.get('in_progress_jobs', []))}\n")
        f.write(f"- **Pending**: {len(ci_status.get('pending_jobs', []))}\n\n")

    # Comments Details
    f.write("### PR Comments Details\n\n")
    f.write(f"See `pr_comments_scratch.md` for full comment analysis.\n\n")

    # Quality Check Details
    f.write("### Quality Check Details\n\n")
    if failed_checks:
        f.write("**Failed Checks:**\n\n")
        for check in failed_checks:
            error_log_file = error_log_files.get(check.name, "")
            f.write(f"#### {check.name}\n\n")
            f.write(f"- **Status**: Failed\n")
            f.write(f"- **Duration**: {check.duration:.1f}s\n")
            if check.error:
                f.write(f"- **Error**: {check.error[:200]}...\n")
            if error_log_file:
                f.write(
                    f"- **Full Error Log**: [`{error_log_file}`]({error_log_file})\n"
                )
                f.write(f"  - View with: `cat {error_log_file}`\n")
                f.write(
                    f"  - Or use: `python scripts/view_check_error.py {_get_check_flag_for_result(check.name)}`\n"
                )
            f.write(
                f"- **Quick Run**: `python scripts/ship_it.py --checks {_get_check_flag_for_result(check.name)}`\n"
            )
            f.write(
                f"- **Truncated Output** (first 500 chars):\n```\n{check.output[:500]}...\n```\n\n"
            )
    else:
        f.write("✅ All quality checks passed!\n\n")


def generate_pr_issues_report(
    ci_status: Any,
    comments_data: Tuple[List[Any], List[Any]],
    quality_check_results: List[CheckResult],
    pr_number: int,
) -> dict[str, Any]:
    """
    Generate a comprehensive PR issues report with checklist format.

    Args:
        ci_status: CI status dictionary from check_ci_status()
        comments_data: Tuple of (all_comments, new_comments) from check_pr_comments()
        quality_check_results: List of CheckResult objects from quality gate execution
        pr_number: PR number

    Returns:
        Dictionary with report data and file path
    """
    import json
    from datetime import datetime

    all_comments, new_comments = comments_data
    commit_sha = _get_current_commit_sha() or "unknown"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    report_file = f"logs/pr_{pr_number}_issues_report_{commit_sha[:8]}.md"

    # Load existing checklist state if available
    checklist_state_file = f"logs/pr_{pr_number}_checklist_state_{commit_sha[:8]}.json"
    checklist_state = {}
    if os.path.exists(checklist_state_file):
        try:
            with open(checklist_state_file, "r", encoding="utf-8") as f:
                checklist_state = json.load(f)
        except Exception:  # nosec B110 - fallback to empty state
            pass

    failed_checks = [r for r in quality_check_results if r.status == CheckStatus.FAILED]
    passed_checks = [r for r in quality_check_results if r.status == CheckStatus.PASSED]

    # Save full error output for each failed check
    error_log_files = _save_check_error_logs(
        failed_checks, pr_number, commit_sha or "unknown", timestamp
    )

    checklist_items: List[dict[str, Any]] = []

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"# Outstanding PR Issues Report\n\n")
        f.write(f"**PR**: #{pr_number}\n")
        f.write(f"**Commit**: `{commit_sha}`\n")
        f.write(f"**Generated**: {timestamp}\n\n")
        f.write("---\n\n")

        # Checklist section
        f.write("## ✅ PR Issues Checklist\n\n")
        f.write(
            "Address each item below before pushing commits. Do NOT push or re-run validation until all items are addressed.\n\n"
        )

        item_number = 1
        item_number = _write_checklist_ci_section(
            f, ci_status, checklist_state, checklist_items, item_number
        )
        item_number = _write_checklist_comments_section(
            f, comments_data, checklist_state, checklist_items, item_number
        )
        item_number = _write_checklist_quality_section(
            f,
            failed_checks,
            error_log_files,
            checklist_state,
            checklist_items,
            item_number,
        )

        _write_report_summary(
            f, checklist_items, ci_status, comments_data, passed_checks, failed_checks
        )
        _write_detailed_sections(f, ci_status, failed_checks, error_log_files)

    return {
        "file_path": report_file,
        "checklist_items": checklist_items,
        "error_log_files": error_log_files,
        "summary": {
            "total_items": sum(len(item["items"]) for item in checklist_items),
            "ci_passed": ci_status.get("all_passed"),
            "comments_count": len(all_comments),
            "new_comments_count": len(new_comments),
            "failed_checks": len(failed_checks),
            "passed_checks": len(passed_checks),
        },
        "commit_sha": commit_sha,
        "timestamp": timestamp,
    }


def _get_check_flag_for_result(result_name: str) -> str:
    """Get the command-line flag for a specific check result name."""
    # Map of result names to check flags
    executor = QualityGateExecutor()
    for check in executor.all_checks:
        flag = check.flag
        name = check.name
        if name == result_name:
            return flag
    return "unknown"


def _get_item_status(checklist_state: Any, item_text: str) -> str:
    """Get status of a checklist item from state."""
    if not checklist_state or "items" not in checklist_state:
        return "pending"

    item_text_lower = item_text.lower()
    for item_data in checklist_state["items"].values():
        if item_text_lower in item_data.get("text", "").lower():
            return item_data.get("status", "pending")

    return "pending"


def write_pr_comments_scratch(
    comments: List[Any], new_comments: Optional[List[Any]] = None
) -> None:
    """Write detailed PR comments to scratch file for AI analysis."""
    try:
        with open("pr_comments_scratch.md", "w") as f:
            f.write("# Outstanding PR Comments - Strategic Analysis Needed\n\n")
            f.write("## Strategic PR Review Protocol\n")
            f.write(
                "1. **Conceptual Grouping**: Classify by underlying concept (authentication, validation, etc.)\n"
            )
            f.write(
                "2. **Risk-First Priority**: Highest risk/surface area changes first\n"
            )
            f.write(
                "3. **Thematic Implementation**: Address entire concepts with comprehensive commits\n"
            )
            f.write(
                "4. **Cross-Reference Communication**: Reply to related comments together\n\n"
            )

            if new_comments:
                f.write(f"## 📬 New Comments ({len(new_comments)})\n\n")
                f.write("These comments have not been seen before:\n\n")
                for i, comment in enumerate(new_comments, 1):
                    comment_id = comment.get("id", f"comment-{i}")
                    author = comment.get("author", "unknown")
                    f.write(f"### 🆕 Comment #{comment_id} - {author}\n")
                    if comment.get("path") and comment.get("line"):
                        f.write(
                            f"**Location**: `{comment['path']}:{comment['line']}`\n"
                        )
                    elif comment.get("path"):
                        f.write(f"**Location**: `{comment['path']}`\n")
                    f.write(f"**Type**: {comment.get('type', 'comment')}\n")
                    f.write(f"**Created**: {comment.get('created_at', 'N/A')}\n\n")
                    body = comment.get("body", "(no content)")
                    f.write(f"**Content**:\n{body}\n\n")
                    f.write("**Conceptual Theme**: _[AI to classify]_\n")
                    f.write("**Risk Priority**: _[AI to assess]_\n")
                    f.write("**Related Comments**: _[AI to identify]_\n\n")
                    f.write("---\n\n")

                if len(comments) > len(new_comments):
                    f.write(
                        f"## 📋 All Outstanding Comments ({len(comments)} total)\n\n"
                    )
                    f.write(
                        f"({len(comments) - len(new_comments)} previously seen comments below)\n\n"
                    )

            f.write("## Comments to Address\n\n")

            for i, comment in enumerate(comments, 1):
                comment_id = comment.get("id", f"comment-{i}")
                author = comment.get("author", "unknown")
                is_new = new_comments and comment.get("id") in {
                    c.get("id") for c in new_comments
                }
                prefix = "🆕 " if is_new else ""
                f.write(f"### {prefix}Comment #{comment_id} - {author}\n")
                if comment.get("path") and comment.get("line"):
                    f.write(f"**Location**: `{comment['path']}:{comment['line']}`\n")
                elif comment.get("path"):
                    f.write(f"**Location**: `{comment['path']}`\n")
                f.write(f"**Type**: {comment.get('type', 'comment')}\n")
                f.write(f"**Created**: {comment.get('created_at', 'N/A')}\n\n")
                body = comment.get("body", "(no content)")
                f.write(f"**Content**:\n{body}\n\n")
                f.write("**Conceptual Theme**: _[AI to classify]_\n")
                f.write("**Risk Priority**: _[AI to assess]_\n")
                f.write("**Related Comments**: _[AI to identify]_\n\n")
                f.write("---\n\n")

    except Exception as e:
        print(f"⚠️  Could not write scratch file: {e}")


def _handle_pr_validation(args: Any) -> Optional[int]:
    """Handle PR validation with comprehensive batch reporting.

    Returns:
        Exit code (0 for success, 1 for failures, None to fall through)
    """
    pr_number, _, _ = _get_pr_context()
    if not pr_number:
        print("⚠️  Not in a PR context. Skipping PR-specific checks.")
        print("   Run this command from a branch with an associated PR.")
        return None  # Signal to fall through to regular validation

    # Step 1: Run all quality checks in parallel
    print("=" * 70)
    print("🔍 PR VALIDATION: Running all checks in parallel...")
    print("=" * 70)
    print()

    executor = QualityGateExecutor(verbose=args.verbose)

    # Determine which checks to run
    checks_to_run: List[CheckDef]
    if args.checks is None:
        checks_to_run = executor.pr_checks
    else:
        checks_to_run = []
        available_checks: dict[str, CheckDef] = {
            check.flag: check for check in executor.all_checks
        }

        for check_name in args.checks:
            # Check if it's an alias
            if check_name in executor.check_alias_lists:
                checks_to_run.extend(executor.check_alias_lists[check_name])
            # Check if it's a direct check flag
            elif check_name in available_checks:
                checks_to_run.append(available_checks[check_name])
            else:
                print(f"⚠️  Unknown check or alias: {check_name}")

        # Remove duplicates while preserving order
        seen = set()
        unique_checks = []
        for check in checks_to_run:
            if check.flag not in seen:
                seen.add(check.flag)
                unique_checks.append(check)
        checks_to_run = unique_checks

    fail_fast = not args.no_fail_fast

    if fail_fast:
        print(
            "🚨 Fail-fast enabled: PR validation will stop after the first failure. Use --no-fail-fast to gather all failures."
        )
    else:
        print("ℹ️ Fail-fast disabled: collecting results for all checks.")

    # Note: Each check manages its own server/resources independently
    # No shared server startup needed - checks are self-contained

    # Run checks (may exit early when fail-fast is enabled)
    start_time = time.time()
    quality_results = executor.run_checks_parallel(
        checks_to_run, fail_fast=fail_fast, verbose=args.verbose
    )
    total_duration = time.time() - start_time

    # Format and display results
    executor.logger.info(
        "\n" + executor.format_results(quality_results, total_duration)
    )

    failed_checks = [
        result for result in quality_results if result.status == CheckStatus.FAILED
    ]

    if fail_fast and failed_checks:
        print()
        print(
            "🚫 Fail-fast triggered: skipping PR context collection. Re-run with --no-fail-fast to gather a full report once issues are fixed."
        )
        return 1

    # Step 2: Collect CI status and PR comments
    print()
    print("=" * 70)
    print("📊 Collecting PR context (CI status, comments)...")
    print("=" * 70)
    print()

    ci_status = check_ci_status()
    comments_data = check_pr_comments()

    # Step 3: Generate comprehensive report
    print()
    print("=" * 70)
    print("📝 Generating PR Issues Report...")
    print("=" * 70)
    print()

    report = generate_pr_issues_report(
        ci_status, comments_data, quality_results, pr_number
    )

    # Write comments scratch file
    all_comments, new_comments = comments_data
    if all_comments:
        write_pr_comments_scratch(all_comments, new_comments)

    # Step 4: Print summary
    _print_pr_summary(report)

    return 0 if report["summary"]["total_items"] == 0 else 1


def _print_pr_summary(report: dict) -> None:
    """Print the PR validation summary."""
    print()
    print("=" * 70)
    print("📋 PR VALIDATION SUMMARY")
    print("=" * 70)
    print()
    print(f"✅ Report generated: {report['file_path']}")
    print(f"📌 Commit: {report['commit_sha'][:8]}")
    print(f"🕐 Timestamp: {report['timestamp']}")
    print()
    print("📊 Summary:")
    print(f"  - Total Checklist Items: {report['summary']['total_items']}")
    ci_status_str = (
        "✅ Passed"
        if report["summary"]["ci_passed"] is True
        else "❌ Failed" if report["summary"]["ci_passed"] is False else "⚠️ Unknown"
    )
    print(f"  - CI Status: {ci_status_str}")
    print(
        f"  - Outstanding Comments: {report['summary']['comments_count']} ({report['summary']['new_comments_count']} new)"
    )
    print(
        f"  - Quality Checks: {report['summary']['passed_checks']} passed, {report['summary']['failed_checks']} failed"
    )

    if report.get("error_log_files"):
        print(f"\n📄 Error Logs Generated ({len(report['error_log_files'])}):")
        for check_name, log_file in report["error_log_files"].items():
            check_flag = _get_check_flag_for_result(check_name)
            print(f"  • {check_name}: {log_file}")
            print(f"    View: python scripts/view_check_error.py {check_flag}")

    print()
    print("💡 Next Steps:")
    print("   1. Review the checklist in the report file")
    print("   2. View full error details:")
    print("      - Use: python scripts/view_check_error.py <check-name>")
    print("      - Or: cat logs/pr_<PR>_error_<check>_<commit>.log")
    print("   3. Address ALL items before pushing commits")
    print("   4. Do NOT push or re-run validation until all items are addressed")
    print("   5. After pushing commits and CI completes, re-run PR validation")
    print()


def main() -> None:
    """Main entry point for the parallel quality gate executor."""
    parser = argparse.ArgumentParser(
        description="LoopCloser Quality Gate - Run maintainability checks in parallel with fail-fast",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/ship_it.py --checks commit                                    # Fast commit validation
  python scripts/ship_it.py --checks pr                                        # Full PR validation
  python scripts/ship_it.py --checks pr --skip-pr-comments                     # PR checks without comment check
  python scripts/ship_it.py --checks python-unit-tests                         # Run unit tests only
  python scripts/ship_it.py --checks python-unit-tests python-coverage         # Unit tests + coverage analysis

Check Aliases (expand to predefined check groups):
  commit      - Fast checks for development (unit tests, coverage, js-tests, lint)
  pr          - Full validation for PRs (all checks including security)
  integration - Integration tests (component interactions)
  smoke       - Smoke tests (end-to-end validation)
  full        - Everything (comprehensive validation)

Individual Checks:
  python-lint-format, js-lint-format, python-static-analysis,
  python-unit-tests, python-coverage, python-new-code-coverage,
  js-tests, js-coverage, security, security-local, complexity,
  duplication, e2e, integration, smoke, frontend-check

Note: python-coverage and python-new-code-coverage require python-unit-tests.
Fail-fast is enabled by default - use --no-fail-fast to run all checks.
        """,
    )

    parser.add_argument(
        "--checks",
        nargs="+",
        required=True,
        help="Checks or aliases to run (required). Aliases: commit, pr, integration, smoke, full. Individual checks: python-unit-tests, python-coverage, python-new-code-coverage, js-tests, js-coverage, security, complexity, etc.",
    )

    parser.add_argument(
        "--no-fail-fast",
        action="store_true",
        help="Disable fail-fast so all requested checks complete even after failures",
    )

    parser.add_argument(
        "--skip-pr-comments",
        action="store_true",
        help="Skip PR comment resolution check when running 'pr' alias",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output (show full test output including passed tests)",
    )

    args = parser.parse_args()

    # Special-case: if the user requested only the `integration` check,
    # run the integration pytest suite directly instead of dispatching
    # through the parallel executor. This ensures `--checks integration`
    # behaves as a direct integration-run command as requested.
    if set(args.checks) == {"integration"}:

        def run_integration_tests(verbose: bool = False) -> int:
            """Run integration tests directly using pytest and return exit code."""
            pytest_cmd = [sys.executable, "-m", "pytest", "tests/integration"]
            if not verbose:
                pytest_cmd += ["-q"]
            print(
                "Running integration tests directly via pytest: ", " ".join(pytest_cmd)
            )
            result = subprocess.run(
                pytest_cmd, cwd=os.path.dirname(os.path.dirname(__file__))
            )
            return result.returncode

        rc = run_integration_tests(verbose=args.verbose)
        sys.exit(rc)

    # Handle PR validation with comprehensive batch reporting
    # Check if 'pr' alias is in the checks list
    if "pr" in args.checks and not args.skip_pr_comments:
        exit_code = _handle_pr_validation(args)
        if exit_code is not None:
            sys.exit(exit_code)
        # Fall through to regular validation if not in PR context

    # Create and run the executor
    executor = QualityGateExecutor(verbose=args.verbose)
    exit_code = executor.execute(checks=args.checks, fail_fast=not args.no_fail_fast)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
