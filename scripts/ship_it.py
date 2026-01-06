#!/usr/bin/env python3

"""
ship_it.py - Course Record Updater Quality Gate Executor

A Python wrapper for the maintAInability-gate.sh script that executes
quality checks in parallel to reduce total execution time.

Adapted from FogOfDog frontend quality gate for Python/Flask projects.

Usage:
    python scripts/ship_it.py                               # Fast commit validation (excludes slow checks)
    python scripts/ship_it.py --validation-type PR          # Full PR validation (all checks + comment resolution)
    python scripts/ship_it.py --validation-type PR --skip-pr-comments  # Full PR gate without comment check
    python scripts/ship_it.py --checks format lint tests    # Run specific checks
    python scripts/ship_it.py --help                        # Show help

This wrapper dispatches individual check commands to the existing bash script
in parallel threads, then collects and formats the results. Fail-fast behavior
is always enabled for rapid development cycles.


"""

import argparse
import concurrent.futures
import re
import subprocess  # nosec B404
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class CheckStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ValidationType(Enum):
    COMMIT = "commit"
    PR = "PR"
    INTEGRATION = "integration"
    SMOKE = "smoke"
    FULL = "full"


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    duration: float
    output: str
    error: Optional[str] = None


class QualityGateExecutor:
    """Manages parallel execution of quality gate checks for Python/Flask projects."""

    def __init__(self):
        # Get centralized quality gate logger
        import os

        # Add parent directory to path for importing logging_config
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        # Change to project root so all relative paths work regardless of where script is invoked
        os.chdir(parent_dir)
        
        from src.utils.logging_config import setup_quality_gate_logger

        self.logger = setup_quality_gate_logger()
        self.script_path = "./scripts/maintAInability-gate.sh"

        # Track running subprocesses so we can terminate them on fail-fast
        self._process_lock = threading.Lock()
        self._running_processes: dict[int, subprocess.Popen] = {}

        self.security_check = (
            "security",
            "🔒 Security Audit (bandit, semgrep, safety)",
        )
        self.security_local_check = (
            "security-local",
            "🔒 Security Audit (bandit, semgrep)",
        )

        # Define all quality checks - adapted for Python/Flask
        # Ordered by importance and speed, broken down into atomic checks
        self.all_checks = [
            ("python-lint-format", "🎨 Python Lint & Format (black, isort, flake8)"),
            ("js-lint-format", "🎨 JavaScript Lint & Format (ESLint, Prettier)"),
            ("python-static-analysis", "🔍 Python Static Analysis (mypy, imports)"),
            ("tests", "🧪 Test Suite Execution (pytest)"),
            ("js-tests", "🧪 JavaScript Test Suite (Jest)"),
            ("coverage", "📊 Test Coverage Analysis (80% threshold)"),
            ("js-coverage", "📊 JavaScript Coverage Analysis (80% threshold)"),
            self.security_check,
            ("complexity", "🧠 Complexity Analysis (radon/xenon)"),
            ("duplication", "🔄 Code Duplication Check"),
            ("e2e", "🎭 End-to-End Tests (Playwright browser automation)"),
            ("integration", "🔗 Integration Tests (component interactions)"),
            ("smoke", "🔥 Smoke Tests (end-to-end validation)"),
            (
                "coverage-new-code",
                "📊 Coverage on New Code (80% threshold on PR changes)",
            ),
            ("frontend-check", "🌐 Frontend Check (quick UI validation)"),
        ]

        # Fast checks for commit validation (optimized for <40s total time)
        # Key optimization: Run coverage instead of tests (coverage includes tests)
        # This saves ~28s by avoiding duplicate test execution
        # Security runs in parallel, so doesn't add to total time
        self.commit_checks = [
            ("python-lint-format", "🎨 Python Lint & Format (black, isort, flake8)"),
            ("js-lint-format", "🎨 JavaScript Lint & Format (ESLint, Prettier)"),
            ("python-static-analysis", "🔍 Python Static Analysis (mypy, imports)"),
            (
                "coverage",
                "🧪 Python Unit Tests & 📊 Coverage Analysis (80% threshold)",
            ),  # Includes test execution
            ("js-tests", "🧪 JavaScript Test Suite (Jest)"),
            ("js-coverage", "📊 JavaScript Coverage Analysis (80% threshold)"),
            # Zero tolerance (safety skipped for speed)
            # Security checks moved to PR-only as requested by user
            # Duplication, complexity excluded from commit (slower or PR-level)
        ]

        # Full checks for PR validation (all checks)
        self.pr_checks = list(self.all_checks)

        # Integration test validation (component interactions using SQLite persistence)
        self.integration_checks = [
            ("python-lint-format", "🎨 Python Lint & Format (black, isort, flake8)"),
            ("tests", "🧪 Test Suite Execution (pytest)"),
            ("integration", "🔗 Integration Tests (component interactions)"),
        ]

        # Smoke test validation (requires running server + browser)
        self.smoke_checks = [
            ("python-lint-format", "🎨 Python Lint & Format (black, isort, flake8)"),
            ("tests", "🧪 Test Suite Execution (pytest)"),
            ("smoke", "🔥 Smoke Tests (end-to-end validation)"),
        ]

        # Full validation (everything)
        # Full validation prefers the full security scan over the lightweight variant
        full_commit_checks = [
            self.security_check if check == self.security_local_check else check
            for check in self.commit_checks
        ]
        self.full_checks = full_commit_checks + [
            check for check in self.all_checks if check not in full_commit_checks
        ]

    def run_single_check(self, check_flag: str, check_name: str) -> CheckResult:
        """Run a single quality check and return the result."""
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
            # E2E: 600s (IMAP verification is slow in CI)
            # Others: 300s (default)
            if check_flag in ["e2e"]:
                timeout_seconds = 600
            else:
                timeout_seconds = 300

            process = subprocess.Popen(  # nosec
                [self.script_path, f"--{actual_flag}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self._register_process(process)

            try:
                stdout, stderr = process.communicate(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                duration = time.time() - start_time
                return CheckResult(
                    name=check_name,
                    status=CheckStatus.FAILED,
                    duration=duration,
                    output=stdout,
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
                    output=stdout,
                )
            else:
                return CheckResult(
                    name=check_name,
                    status=CheckStatus.FAILED,
                    duration=duration,
                    output=stdout,
                    error=stderr,
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

    def _terminate_running_processes(self) -> None:
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
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        proc.kill()
                    except Exception:  # nosec B110 - Process may already be dead
                        pass

    def run_checks_parallel(
        self,
        checks: List[Tuple[str, str]],
        max_workers: int = None,  # Use all available CPU cores
        fail_fast: bool = True,
    ) -> List[CheckResult]:
        """Run multiple checks in parallel using ThreadPoolExecutor."""
        results = []
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

        try:
            # Submit all checks
            future_to_check = {
                executor.submit(self.run_single_check, check_flag, check_name): (
                    check_flag,
                    check_name,
                )
                for check_flag, check_name in checks
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_check):
                _, check_name = future_to_check[future]
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

                        # Cancel all remaining futures and shutdown immediately
                        for f in future_to_check:
                            f.cancel()
                        self._terminate_running_processes()
                        executor.shutdown(wait=False)
                        sys.exit(1)

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
        for flag, name in self.all_checks:
            if name == result_name:
                return flag
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

    def _extract_coverage_failure_reason(self, output: str) -> str:
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

        report = []
        report.extend(self._format_header(total_duration))
        report.extend(self._format_passed_checks(passed_checks))
        report.extend(self._format_failed_checks(failed_checks))
        report.extend(self._format_summary(failed_checks))

        return "\n".join(report)

    def execute(
        self,
        checks: List[str] = None,
        validation_type: ValidationType = ValidationType.COMMIT,
        fail_fast: bool = True,
    ) -> int:
        """Execute quality checks in parallel and return exit code."""
        validation_name_map = {
            ValidationType.COMMIT: "COMMIT",
            ValidationType.PR: "PR",
            ValidationType.INTEGRATION: "INTEGRATION",
            ValidationType.SMOKE: "SMOKE",
            ValidationType.FULL: "FULL",
        }
        validation_name = validation_name_map[validation_type]
        self.logger.info(
            f"🔍 Running Course Record Updater quality checks ({validation_name} validation - PARALLEL MODE with auto-fix)..."
        )
        self.logger.info("🐍 Python/Flask enterprise validation suite")
        self.logger.info("")

        # Determine which checks to run
        if checks is None:
            # Default: use validation type to determine check set
            if validation_type == ValidationType.COMMIT:
                checks_to_run = self.commit_checks
                self.logger.info(
                    "📦 Running COMMIT validation (fast checks, excludes security)"
                )
            elif validation_type == ValidationType.PR:
                checks_to_run = self.pr_checks
                self.logger.info(
                    "🔍 Running PR validation (all checks including security)"
                )
            elif validation_type == ValidationType.INTEGRATION:
                checks_to_run = self.integration_checks
                self.logger.info(
                    "🔗 Running INTEGRATION validation (component interactions against SQLite persistence)"
                )
            elif validation_type == ValidationType.SMOKE:
                checks_to_run = self.smoke_checks
                self.logger.info(
                    "🔥 Running SMOKE validation (end-to-end tests, requires running server + browser)"
                )
            elif validation_type == ValidationType.FULL:
                checks_to_run = self.full_checks
                self.logger.info(
                    "🚀 Running FULL validation (comprehensive validation, all dependencies required)"
                )
        else:
            # Run only specified checks
            available_checks = {flag: (flag, name) for flag, name in self.all_checks}
            checks_to_run = []
            for check in checks:
                if check in available_checks:
                    checks_to_run.append(available_checks[check])
                else:
                    self.logger.error(f"❌ Unknown check: {check}")
                    self.logger.info(
                        f"Available checks: {', '.join(available_checks.keys())}"
                    )
                    return 1

        start_time = time.time()

        # Run all checks in parallel (with or without fail-fast)
        check_names = [flag for flag, _ in checks_to_run]
        if fail_fast:
            self.logger.info(
                f"🚀 Running checks in parallel with fail-fast [{', '.join(check_names)}]"
            )
        else:
            self.logger.info(
                f"🚀 Running all checks in parallel (no fail-fast) [{', '.join(check_names)}]"
            )
        all_results = self.run_checks_parallel(checks_to_run, fail_fast=fail_fast)

        total_duration = time.time() - start_time

        # Format and display results
        self.logger.info("\n" + self.format_results(all_results, total_duration))

        # Return appropriate exit code
        failed_count = len([r for r in all_results if r.status == CheckStatus.FAILED])
        return 1 if failed_count > 0 else 0

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


def _get_pr_context():
    """
    Get PR number and repository info from environment or git context.

    Returns:
        Tuple of (pr_number, owner, name) or (None, None, None) if not in PR context
    """
    import json
    import os
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
        return pr_number, owner, name
    except:
        print("⚠️  Could not detect repository info")
        return None, None, None


def _load_tracked_comments(pr_number):
    """
    Load previously tracked comment IDs from file.

    Returns:
        Set of comment IDs that have been seen before
    """
    import json
    import os

    tracking_file = f"logs/pr_{pr_number}_comments_tracked.json"
    if os.path.exists(tracking_file):
        try:
            with open(tracking_file, "r") as f:
                data = json.load(f)
                return set(data.get("seen_comment_ids", []))
        except:
            return set()
    return set()


def _save_tracked_comments(pr_number, comment_ids):
    """
    Save tracked comment IDs to file.

    Args:
        pr_number: PR number
        comment_ids: Set of comment IDs to track
    """
    import json
    import os

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


def resolve_review_thread(thread_id):
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


def reply_to_pr_comment(comment_id, body, thread_id=None, resolve_thread=False):
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

        # For review threads, add a reply to the thread
        if thread_id:
            # GraphQL mutation to add a reply to a review thread
            mutation = """
            mutation($threadId: ID!, $body: String!) {
              addPullRequestReviewThreadComment(input: {
                pullRequestReviewThreadId: $threadId
                body: $body
              }) {
                comment {
                  id
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
                    "-f",
                    f"body={body}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                # Optionally resolve the thread
                if resolve_thread:
                    resolve_review_thread(thread_id)
                return True

        # For general comments, use REST API
        else:
            result = subprocess.run(  # nosec
                [
                    "gh",
                    "api",
                    f"repos/{owner}/{name}/pulls/{pr_number}/comments/{comment_id}/replies",
                    "-X",
                    "POST",
                    "-f",
                    f"body={body}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            return result.returncode == 0

        return False

    except Exception as e:
        print(f"⚠️  Could not reply to PR comment: {e}")
        return False


def check_pr_comments():
    """
    Check for unresolved PR comments (both review threads and general PR comments).

    Returns:
        Tuple of (all_unresolved_comments, new_comments) where:
        - all_unresolved_comments: List of all unresolved comment dictionaries
        - new_comments: List of comments not seen before (for tracking)
    """
    try:
        import json
        import os
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
        current_ids = {c.get("id") for c in all_unresolved if c.get("id")}
        if current_ids:
            _save_tracked_comments(pr_number, current_ids | tracked_ids)

        return all_unresolved, new_comments

    except Exception as e:
        print(f"⚠️  Could not check PR comments: {e}")
        return [], []


def _parse_rollup_items(statuses):
    """Parse statusCheckRollup items to categorize jobs."""
    failed = []
    in_progress = []
    pending = []

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


def _get_ci_status_from_rollup(pr_number):
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


def _get_ci_status_fallback(pr_number, owner, name):
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


def check_ci_status():
    """
    Check GitHub Actions CI status for the current PR.

    Returns:
        Dictionary with CI status information.
    """
    try:
        pr_number, owner, name = _get_pr_context()
        if not pr_number:
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


def _get_current_commit_sha():
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


def _save_check_error_logs(failed_checks, pr_number, commit_sha, timestamp):
    """Save full error output for each failed check to log files."""
    error_log_files = {}
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
    f, ci_status, checklist_state, checklist_items, item_number
):
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


def _resolve_comment_location(comment):
    """Resolve location string for a comment."""
    if comment.get("path") and comment.get("line"):
        return f"`{comment['path']}:{comment['line']}`"
    elif comment.get("path"):
        return f"`{comment['path']}`"
    return ""


def _write_single_comment_item(
    f, comment, location, is_new, checklist_state, checklist_items
):
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
    f, comments_data, checklist_state, checklist_items, item_number
):
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
    f, failed_checks, error_log_files, checklist_state, checklist_items, item_number
):
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
    f, checklist_items, ci_status, comments_data, passed_checks, failed_checks
):
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


def _write_detailed_sections(f, ci_status, failed_checks, error_log_files):
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
    ci_status, comments_data, quality_check_results, pr_number
):
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
    import os
    from datetime import datetime

    all_comments, new_comments = comments_data
    commit_sha = _get_current_commit_sha()
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
        failed_checks, pr_number, commit_sha, timestamp
    )

    checklist_items = []

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
    for flag, name in executor.all_checks:
        if name == result_name:
            return flag
    return "unknown"


def _get_item_status(checklist_state, item_text):
    """Get status of a checklist item from state."""
    if not checklist_state or "items" not in checklist_state:
        return "pending"

    item_text_lower = item_text.lower()
    for item_data in checklist_state["items"].values():
        if item_text_lower in item_data.get("text", "").lower():
            return item_data.get("status", "pending")

    return "pending"


def write_pr_comments_scratch(comments, new_comments=None):
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


def _handle_pr_validation(args) -> int:
    """Handle PR validation with comprehensive batch reporting.

    Returns:
        Exit code (0 for success, 1 for failures)
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

    executor = QualityGateExecutor()

    # Determine which checks to run
    if args.checks is None:
        checks_to_run = executor.pr_checks
    else:
        available_checks = {flag: (flag, name) for flag, name in executor.all_checks}
        checks_to_run = [
            available_checks[c] for c in args.checks if c in available_checks
        ]

    fail_fast = not args.no_fail_fast

    if fail_fast:
        print(
            "🚨 Fail-fast enabled: PR validation will stop after the first failure. Use --no-fail-fast to gather all failures."
        )
    else:
        print("ℹ️ Fail-fast disabled: collecting results for all checks.")

    # Run checks (may exit early when fail-fast is enabled)
    start_time = time.time()
    quality_results = executor.run_checks_parallel(checks_to_run, fail_fast=fail_fast)
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


def main():
    """Main entry point for the parallel quality gate executor."""
    parser = argparse.ArgumentParser(
        description="Course Record Updater Quality Gate - Run maintainability checks in parallel with fail-fast",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/ship_it.py                                    # Fast commit validation (excludes slow checks)
  python scripts/ship_it.py --validation-type PR              # Full PR validation (fails if unaddressed comments)
  python scripts/ship_it.py --checks black isort lint tests   # Run only specific checks
  python scripts/ship_it.py --checks tests coverage           # Quick test + coverage check

Validation Types:
  commit - Fast checks for development cycle (~40s savings)
  PR     - Full validation for pull requests (all checks including security)

Available checks: python-lint-format, js-lint-format, python-static-analysis, tests, js-tests, coverage, js-coverage, security, duplication, e2e, integration, smoke, frontend-check

By default, runs COMMIT validation for fast development cycles.
Fail-fast behavior is ALWAYS enabled - exits immediately on first failure.
        """,
    )

    parser.add_argument(
        "--validation-type",
        choices=["commit", "PR", "integration", "smoke", "full"],
        default="commit",
        help="Validation type: 'commit' for fast checks (default), 'PR' for all checks, 'integration' for integration tests, 'smoke' for end-to-end tests, 'full' for everything",
    )

    parser.add_argument(
        "--no-fail-fast",
        action="store_true",
        help="Disable fail-fast so all requested checks complete even after failures",
    )

    parser.add_argument(
        "--checks",
        nargs="+",
        help="Run specific checks only (e.g. --checks python-lint-format tests). Available: python-lint-format, js-lint-format, python-static-analysis, tests, js-tests, coverage, js-coverage, security, duplication, e2e, integration, smoke, frontend-check",
    )

    parser.add_argument(
        "--skip-pr-comments",
        action="store_true",
        help="Skip PR comment resolution check (run full PR gate without checking for unaddressed comments)",
    )

    args = parser.parse_args()

    # Handle PR validation with comprehensive batch reporting
    if args.validation_type == "PR" and not args.skip_pr_comments:
        exit_code = _handle_pr_validation(args)
        if exit_code is not None:
            sys.exit(exit_code)
        # Fall through to regular validation if not in PR context

    # Convert validation type string to enum
    validation_type_map = {
        "commit": ValidationType.COMMIT,
        "PR": ValidationType.PR,
        "integration": ValidationType.INTEGRATION,
        "smoke": ValidationType.SMOKE,
        "full": ValidationType.FULL,
    }
    validation_type = validation_type_map[args.validation_type]

    # Create and run the executor (for non-PR validation or PR with --skip-pr-comments)
    executor = QualityGateExecutor()
    exit_code = executor.execute(checks=args.checks, validation_type=validation_type)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
