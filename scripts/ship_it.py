#!/usr/bin/env python3

"""
ship_it.py - Course Record Updater Quality Gate Executor

A Python wrapper for the maintainability-gate.sh script that executes
quality checks in parallel to reduce total execution time.

Adapted from FogOfDog frontend quality gate for Python/Flask projects.

Usage:
    python scripts/ship_it.py                    # Fast commit validation (excludes slow checks)
    python scripts/ship_it.py --validation-type PR  # Full PR validation (all checks)
    python scripts/ship_it.py --checks format lint tests  # Run specific checks
    python scripts/ship_it.py --help             # Show help

This wrapper dispatches individual check commands to the existing bash script
in parallel threads, then collects and formats the results. Fail-fast behavior
is always enabled for rapid development cycles.
"""

import argparse
import concurrent.futures
import re
import subprocess
import sys
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
        from logging_config import setup_quality_gate_logger
        self.logger = setup_quality_gate_logger()
        self.script_path = "./scripts/maintainability-gate.sh"

        # Define all quality checks - adapted for Python/Flask
        # Ordered by importance and speed, broken down into atomic checks
        self.all_checks = [
            ("black", "🎨 Code Formatting (black)"),
            ("isort", "📚 Import Sorting (isort)"),
            ("lint", "🔍 Python Lint Check (flake8 critical errors)"),
            ("js-lint", "🔍 JavaScript Lint Check (ESLint)"),
            ("js-format", "🎨 JavaScript Format Check (Prettier)"),
            ("tests", "🧪 Test Suite Execution (pytest)"),
            ("coverage", "📊 Test Coverage Analysis (75% threshold)"),
            ("security", "🔒 Security Audit (bandit, safety)"),
            ("sonar", "🔍 SonarCloud Quality Analysis"),
            ("types", "🔧 Type Check (mypy)"),
            ("imports", "📦 Import Analysis & Organization"),
            ("duplication", "🔄 Code Duplication Check"),
            ("smoke-tests", "🔥 Smoke Tests (end-to-end validation)"),
            ("frontend-check", "🌐 Frontend Check (quick UI validation)"),
        ]

        # Fast checks for commit validation (exclude slow checks >30s)
        self.commit_checks = [
            ("black", "🎨 Code Formatting (black)"),
            ("isort", "📚 Import Sorting (isort)"),
            ("lint", "🔍 Python Lint Check (flake8 critical errors)"),
            ("js-lint", "🔍 JavaScript Lint Check (ESLint)"),
            ("js-format", "🎨 JavaScript Format Check (Prettier)"),
            ("tests", "🧪 Test Suite Execution (pytest)"),
            ("coverage", "📊 Test Coverage Analysis (75% threshold)"),
            ("types", "🔧 Type Check (mypy)"),
            ("imports", "📦 Import Analysis & Organization"),
            ("duplication", "🔄 Code Duplication Check"),
        ]

        # Full checks for PR validation (all checks)
        self.pr_checks = self.all_checks

    def run_single_check(self, check_flag: str, check_name: str) -> CheckResult:
        """Run a single quality check and return the result."""
        start_time = time.time()

        try:
            # Run the individual check
            result = subprocess.run(
                [self.script_path, f"--{check_flag}"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per check
                check=False,  # Don't raise exception on non-zero exit code
            )

            duration = time.time() - start_time

            if result.returncode == 0:
                return CheckResult(
                    name=check_name,
                    status=CheckStatus.PASSED,
                    duration=duration,
                    output=result.stdout,
                )
            else:
                return CheckResult(
                    name=check_name,
                    status=CheckStatus.FAILED,
                    duration=duration,
                    output=result.stdout,
                    error=result.stderr,
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

    def run_checks_parallel(
        self,
        checks: List[Tuple[str, str]],
        max_workers: int = None,  # Use all available CPU cores
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

                    # Fail-fast: always exit immediately on first failure
                    if result.status == CheckStatus.FAILED:
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
            executor.shutdown(wait=True)
            
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
            lines.append(f"   • {result.name}: Completed in {result.duration:.1f}s")
        lines.append("")
        return lines

    def _format_failed_checks(self, failed_checks: List[CheckResult]) -> List[str]:
        """Format failed checks section with detailed error output."""
        if not failed_checks:
            return []

        lines = [f"❌ FAILED CHECKS ({len(failed_checks)}):"]
        for result in failed_checks:
            lines.append(f"   • {result.name}")
            if result.error:
                lines.append(f"     Error: {result.error}")
            if result.output:
                # Show more detailed output for failed checks (up to 20 lines)
                output_lines = result.output.strip().split("\n")
                # Filter out empty lines and pip noise
                meaningful_lines = [
                    line
                    for line in output_lines
                    if line.strip() and not line.startswith("pip")
                ]
                display_lines = meaningful_lines[:20]  # Show up to 20 meaningful lines

                if display_lines:
                    lines.append("     Output:")
                    for line in display_lines:
                        lines.append(f"       {line}")

                if len(meaningful_lines) > 20:
                    lines.append(
                        f"       ... and {len(meaningful_lines) - 20} more lines"
                    )
                    lines.append("       Run the individual check for full details")
            lines.append("")
        return lines

    def _format_summary(self, failed_checks: List[CheckResult]) -> List[str]:
        """Format the final summary section."""
        lines = ["━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]

        if not failed_checks:
            lines.extend(
                [
                    "🎉 ALL CHECKS PASSED!",
                    "✅ Ready to commit with confidence!",
                    "",
                    "🚀 Python/Flask quality validation completed successfully!",
                ]
            )
        else:
            lines.extend(
                [
                    "❌ QUALITY GATE FAILED",
                    f"🔧 {len(failed_checks)} check(s) need attention",
                    "",
                    "💡 Run individual checks for detailed output:",
                ]
            )
            for result in failed_checks:
                check_flag = next(
                    (flag for flag, name in self.all_checks if name == result.name),
                    "unknown",
                )
                lines.append(
                    f"   • {result.name}: ./scripts/maintainability-gate.sh --{check_flag}"
                )

        return lines

    def _extract_test_failure_reason(self, output: str) -> str:
        """Extract specific failure reason from pytest output."""
        if not output:
            return "Unknown test failure"

        # Check for actual test failures first (highest priority)
        failed_match = re.search(r"(\d+)\s+failed", output)
        if failed_match:
            failed_count = failed_match.group(1)
            return f"Test failures: {failed_count} test(s) failed"

        # Check for coverage threshold failure (80% gate)
        if "coverage" in output.lower() and (
            "threshold" in output.lower()
            or "below" in output.lower()
            or "fail" in output.lower()
        ):
            # Try multiple patterns for coverage extraction
            coverage_match = re.search(
                r"(\d+\.?\d*)%.*(?:not met|below|fail).*(\d+\.?\d*)%", output
            )
            if not coverage_match:
                coverage_match = re.search(
                    r"Coverage.*?(\d+\.?\d*)%.*below.*?(\d+\.?\d*)%", output
                )
            if not coverage_match:
                # Look for pytest-cov style output
                coverage_match = re.search(r"TOTAL.*?(\d+)%", output)
                if coverage_match:
                    actual = coverage_match.group(1)
                    return f"Coverage threshold not met: {actual}% < 80%"

            if coverage_match and len(coverage_match.groups()) >= 2:
                actual, threshold = coverage_match.groups()
                return f"Coverage threshold not met: {actual}% < {threshold}%"
            else:
                return "Coverage threshold not met (below 80%)"

        # Check for coverage-related failures without explicit threshold info
        if "coverage" in output.lower() and (
            "fail" in output.lower() or "error" in output.lower()
        ):
            return "Coverage analysis failed or below 75% threshold"

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

    def execute(self, checks: List[str] = None, validation_type: ValidationType = ValidationType.COMMIT) -> int:
        """Execute quality checks in parallel with fail-fast behavior and return exit code."""
        validation_name = "COMMIT" if validation_type == ValidationType.COMMIT else "PR"
        self.logger.info(
            f"🔍 Running Course Record Updater quality checks ({validation_name} validation - PARALLEL MODE with auto-fix)..."
        )
        self.logger.info("🐍 Python/Flask enterprise validation suite")
        self.logger.info("⚡ Fail-fast mode: ALWAYS ENABLED")
        self.logger.info("")

        # Determine which checks to run
        if checks is None:
            # Default: use validation type to determine check set
            if validation_type == ValidationType.COMMIT:
                checks_to_run = self.commit_checks
                self.logger.info("📦 Running COMMIT validation (fast checks, excludes security & sonar)")
            else:
                checks_to_run = self.pr_checks
                self.logger.info("🔍 Running PR validation (all checks including security & sonar)")
        else:
            # Run only specified checks
            available_checks = {flag: (flag, name) for flag, name in self.all_checks}
            checks_to_run = []
            for check in checks:
                if check in available_checks:
                    checks_to_run.append(available_checks[check])
                else:
                    self.logger.error(f"❌ Unknown check: {check}")
                    self.logger.info(f"Available checks: {', '.join(available_checks.keys())}")
                    return 1

        start_time = time.time()

        # Run all checks in parallel with fail-fast always enabled
        self.logger.info("🚀 Running quality checks in parallel...")
        all_results = self.run_checks_parallel(checks_to_run)

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


def main():
    """Main entry point for the parallel quality gate executor."""
    parser = argparse.ArgumentParser(
        description="Course Record Updater Quality Gate - Run maintainability checks in parallel with fail-fast",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/ship_it.py                                    # Fast commit validation (excludes slow checks)
  python scripts/ship_it.py --validation-type PR              # Full PR validation (all checks)
  python scripts/ship_it.py --checks black isort lint tests   # Run only specific checks
  python scripts/ship_it.py --checks tests coverage           # Quick test + coverage check

Validation Types:
  commit - Fast checks for development cycle (excludes security & sonar, ~30s savings)
  PR     - Full validation for pull requests (all checks including security & sonar)

Available checks: black, isort, lint, js-lint, js-format, tests, coverage, security, sonar, types, imports, duplication, smoke-tests, frontend-check

By default, runs COMMIT validation for fast development cycles.
Fail-fast behavior is ALWAYS enabled - exits immediately on first failure.
        """,
    )

    parser.add_argument(
        "--validation-type",
        choices=["commit", "PR"],
        default="commit",
        help="Validation type: 'commit' for fast checks (default), 'PR' for all checks",
    )

    parser.add_argument(
        "--checks",
        nargs="+",
        help="Run specific checks only (e.g. --checks black isort lint tests). Available: black, isort, lint, tests, coverage, security, sonar, types, imports, duplication, smoke-tests, frontend-check",
    )

    args = parser.parse_args()

    # Convert validation type string to enum
    validation_type = ValidationType.COMMIT if args.validation_type == "commit" else ValidationType.PR

    # Create and run the executor
    executor = QualityGateExecutor()
    exit_code = executor.execute(checks=args.checks, validation_type=validation_type)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
