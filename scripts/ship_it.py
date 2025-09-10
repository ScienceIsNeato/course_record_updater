#!/usr/bin/env python3

"""
ship_it.py - Course Record Updater Quality Gate Executor

A Python wrapper for the maintainability-gate.sh script that executes
quality checks in parallel to reduce total execution time.

Adapted from FogOfDog frontend quality gate for Python/Flask projects.

Usage:
    python scripts/ship_it.py                    # All checks in parallel
    python scripts/ship_it.py --fail-fast        # All checks, exit on first failure
    python scripts/ship_it.py --checks format lint tests  # Run specific checks
    python scripts/ship_it.py --help             # Show help

This wrapper dispatches individual check commands to the existing bash script
in parallel threads, then collects and formats the results.
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
        self.script_path = "./scripts/maintainability-gate.sh"

        # Define all quality checks - adapted for Python/Flask
        # Ordered by importance and speed
        self.all_checks = [
            ("format", "🎨 Python Format Check & Auto-Fix (black, isort)"),
            ("lint", "🔍 Python Lint Check (flake8 critical errors)"),
            ("tests", "🧪 Test Suite & Coverage (pytest)"),
            ("security", "🔒 Security Audit (bandit, safety)"),
            ("types", "🔧 Type Check (mypy)"),
            ("imports", "📦 Import Analysis & Organization"),
            ("duplication", "🔄 Code Duplication Check"),
        ]

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
        fail_fast: bool = False,
    ) -> List[CheckResult]:
        """Run multiple checks in parallel using ThreadPoolExecutor."""
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
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
                    print(
                        f"{status_icon} {result.name} completed in {result.duration:.1f}s"
                    )

                    # Fail-fast: exit immediately on first failure
                    if fail_fast and result.status == CheckStatus.FAILED:
                        # Enhanced error reporting for test failures
                        if "Test Suite" in result.name:
                            failure_reason = self._extract_test_failure_reason(
                                result.output
                            )
                            print(
                                f"\n🚨 FAIL-FAST: {result.name} failed, terminating immediately..."
                            )
                            print(f"   Reason: {failure_reason}")
                        else:
                            print(
                                f"\n🚨 FAIL-FAST: {result.name} failed, terminating immediately..."
                            )
                        # Force shutdown executor to kill running processes
                        executor.shutdown(wait=False, cancel_futures=True)
                        # Exit immediately without waiting
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
                    print(f"❌ {check_name} failed with exception: {exc}")

        return results

    def _format_header(self, total_duration: float) -> List[str]:
        """Format the report header."""
        return [
            "📊 Python/Flask Quality Gate Report",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            f"⏱️  Total execution time: {total_duration:.1f}s (parallel)",
            f"🐍 Python/Flask project quality validation",
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
                    lines.append(f"       Run the individual check for full details")
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
            return "Coverage analysis failed or below 80% threshold"

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

    def execute(self, checks: List[str] = None, fail_fast: bool = False) -> int:
        """Execute all quality checks in parallel and return exit code."""
        print(
            "🔍 Running Course Record Updater quality checks (PARALLEL MODE with auto-fix)..."
        )
        print("🐍 Python/Flask enterprise validation suite")
        print("")

        # Determine which checks to run
        if checks is None:
            # Default: run the most important checks for development
            checks_to_run = [
                check for check in self.all_checks 
                if check[0] in ["format", "lint", "tests"]
            ]
        else:
            # Run only specified checks
            available_checks = {flag: (flag, name) for flag, name in self.all_checks}
            checks_to_run = []
            for check in checks:
                if check in available_checks:
                    checks_to_run.append(available_checks[check])
                else:
                    print(f"❌ Unknown check: {check}")
                    print(f"Available checks: {', '.join(available_checks.keys())}")
                    return 1

        start_time = time.time()

        # Run all checks in parallel
        print("🚀 Running all quality checks in parallel...")
        all_results = self.run_checks_parallel(checks_to_run, fail_fast=fail_fast)

        total_duration = time.time() - start_time

        # Format and display results
        print("\n" + self.format_results(all_results, total_duration))

        # Return appropriate exit code
        failed_count = len([r for r in all_results if r.status == CheckStatus.FAILED])
        return 1 if failed_count > 0 else 0


def main():
    """Main entry point for the parallel quality gate executor."""
    parser = argparse.ArgumentParser(
        description="Course Record Updater Quality Gate - Run maintainability checks in parallel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/ship_it.py                              # All checks in parallel
  python scripts/ship_it.py --fail-fast                  # All checks, exit on first failure
  python scripts/ship_it.py --checks format lint tests  # Run only specific checks
  python scripts/ship_it.py --checks tests --fail-fast  # Quick test-only check
  
Available checks: format, lint, tests, security, types, imports, duplication
  
By default, runs the essential checks (format, lint, tests) for fast development.
Use specific --checks for comprehensive validation before major commits.
        """,
    )

    parser.add_argument(
        "--checks",
        nargs="+",
        help="Run specific checks only (e.g. --checks format lint tests). Available: format, lint, tests, security, types, imports, duplication",
    )

    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Exit immediately on first check failure (for rapid development cycles)",
    )

    args = parser.parse_args()

    # Create and run the executor
    executor = QualityGateExecutor()
    exit_code = executor.execute(checks=args.checks, fail_fast=args.fail_fast)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
