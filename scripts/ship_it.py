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

IMPORTANT: SonarCloud (--checks sonar) only analyzes 'main' branch on free tier.
It will FAIL on feature branches even with fixes. See SONAR_ANALYSIS_RESULTS.md
for the proper workflow when working with SonarCloud issues.
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
        from logging_config import setup_quality_gate_logger

        self.logger = setup_quality_gate_logger()
        self.script_path = "./scripts/maintAInability-gate.sh"

        # Define all quality checks - adapted for Python/Flask
        # Ordered by importance and speed, broken down into atomic checks
        self.all_checks = [
            ("black", "🎨 Code Formatting (black)"),
            ("isort", "📚 Import Sorting (isort)"),
            ("lint", "🔍 Python Lint Check (flake8 critical errors)"),
            ("js-lint", "🔍 JavaScript Lint Check (ESLint)"),
            ("js-format", "🎨 JavaScript Format Check (Prettier)"),
            ("tests", "🧪 Test Suite Execution (pytest)"),
            ("js-tests", "🧪 JavaScript Test Suite (Jest)"),
            ("coverage", "📊 Test Coverage Analysis (80% threshold)"),
            ("js-coverage", "📊 JavaScript Coverage Analysis (80% threshold)"),
            ("security", "🔒 Security Audit (bandit, safety)"),
            ("types", "🔧 Type Check (mypy)"),
            ("imports", "📦 Import Analysis & Organization"),
            ("duplication", "🔄 Code Duplication Check"),
            ("sonar", "🔍 SonarCloud Quality Analysis"),
            ("e2e", "🎭 End-to-End Tests (Playwright browser automation)"),
            ("integration", "🔗 Integration Tests (component interactions)"),
            ("smoke", "🔥 Smoke Tests (end-to-end validation)"),
            ("frontend-check", "🌐 Frontend Check (quick UI validation)"),
        ]

        # Fast checks for commit validation (optimized for <40s total time)
        # Key optimization: Run coverage instead of tests (coverage includes tests)
        # This saves ~28s by avoiding duplicate test execution
        self.commit_checks = [
            ("black", "🎨 Code Formatting (black)"),
            ("isort", "📚 Import Sorting (isort)"),
            ("lint", "🔍 Python Lint Check (flake8 critical errors)"),
            ("js-lint", "🔍 JavaScript Lint Check (ESLint)"),
            ("js-format", "🎨 JavaScript Format Check (Prettier)"),
            ("coverage", "📊 Test Coverage Analysis (80% threshold)"),  # Includes test execution
            ("js-tests", "🧪 JavaScript Test Suite (Jest)"),
            ("js-coverage", "📊 JavaScript Coverage Analysis (80% threshold)"),
            ("types", "🔧 Type Check (mypy)"),
            ("imports", "📦 Import Analysis & Organization"),
            # Duplication check moved to PR validation (non-critical, saves 2.2s)
            # ("duplication", "🔄 Code Duplication Check"),  # Moved to PR checks
            # ("sonar", "🔍 SonarCloud Quality Analysis"),  # Excluded from commit checks to avoid chicken-and-egg problem
        ]

        # Full checks for PR validation (all checks)
        self.pr_checks = self.all_checks
        
        # Integration test validation (component interactions using SQLite persistence)
        self.integration_checks = [
            ("black", "🎨 Code Formatting (black)"),
            ("isort", "📚 Import Sorting (isort)"),
            ("lint", "🔍 Python Lint Check (flake8 critical errors)"),
            ("tests", "🧪 Test Suite Execution (pytest)"),
            ("integration", "🔗 Integration Tests (component interactions)"),
        ]
        
        # Smoke test validation (requires running server + browser)
        self.smoke_checks = [
            ("black", "🎨 Code Formatting (black)"),
            ("isort", "📚 Import Sorting (isort)"),
            ("lint", "🔍 Python Lint Check (flake8 critical errors)"),
            ("tests", "🧪 Test Suite Execution (pytest)"),
            ("smoke", "🔥 Smoke Tests (end-to-end validation)"),
        ]
        
        # Full validation (everything)
        self.full_checks = (
            self.commit_checks +
            [check for check in self.pr_checks if check not in self.commit_checks]
        )

    def run_single_check(self, check_flag: str, check_name: str) -> CheckResult:
        """Run a single quality check and return the result."""
        start_time = time.time()

        # Map shorthand flags to maintAInability-gate.sh flags
        flag_mapping = {
            "integration": "integration-tests",
            "smoke": "smoke-tests",
        }
        
        # Use mapped flag if available, otherwise use original flag
        actual_flag = flag_mapping.get(check_flag, check_flag)

        try:
            # Configure timeout per check type
            # E2E: 600s (IMAP verification is slow in CI)
            # Sonar: 600s (SonarCloud server-side processing can be slow)
            # Others: 300s (default)
            if check_flag in ["e2e", "sonar"]:
                timeout_seconds = 600
            else:
                timeout_seconds = 300
            
            # Run the individual check
            result = subprocess.run(
                [self.script_path, f"--{actual_flag}"],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,  # Don't raise exception on non-zero exit code
            )

            duration = time.time() - start_time

            # Auto-stage files after auto-fixers run successfully
            # Only auto-stage for tools that actually modify files and need staging
            if result.returncode == 0 and check_flag in ["black", "isort"]:
                try:
                    subprocess.run(["git", "add", "."], capture_output=True, check=True)
                except subprocess.CalledProcessError:
                    # Ignore git add failures (might not be in a git repo, etc.)
                    pass

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
            
            for line in result.output.split('\n'):
                stripped = line.strip()
                if stripped.startswith('Lines:'):
                    lines_pct = stripped.split()[1]
                elif stripped.startswith('Statements:'):
                    statements_pct = stripped.split()[1]
                elif stripped.startswith('Branches:'):
                    branches_pct = stripped.split()[1]
                elif stripped.startswith('Functions:'):
                    functions_pct = stripped.split()[1]
            
            if lines_pct:
                return f"Lines: {lines_pct} ✅ | Statements: {statements_pct} | Branches: {branches_pct} | Functions: {functions_pct}"
        
        # For other checks, look for pattern: "   • {name}: {message}"
        for line in result.output.split('\n'):
            stripped = line.strip()
            if stripped.startswith('• '):
                # Extract message after first ": "
                parts = stripped.split(': ', 1)
                if len(parts) == 2:
                    check_name = parts[0].replace('• ', '').strip()
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

    def execute(
        self,
        checks: List[str] = None,
        validation_type: ValidationType = ValidationType.COMMIT,
    ) -> int:
        """Execute quality checks in parallel with fail-fast behavior and return exit code."""
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
                    "📦 Running COMMIT validation (fast checks, excludes security & sonar)"
                )
            elif validation_type == ValidationType.PR:
                checks_to_run = self.pr_checks
                self.logger.info(
                    "🔍 Running PR validation (all checks including security & sonar)"
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

        # Run all checks in parallel with fail-fast always enabled
        check_names = [flag for flag, _ in checks_to_run]
        self.logger.info(f"🚀 Running checks in parallel [{', '.join(check_names)}]")
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


def check_pr_comments():
    """
    Check for unresolved PR comment threads using GitHub GraphQL API.

    Returns:
        List of unresolved comment thread dictionaries, empty if none found
    """
    try:
        import json
        import os
        import subprocess

        # Detect current PR number from branch or environment
        pr_number = os.getenv("PR_NUMBER")
        if not pr_number:
            # Try to get from current branch if we're in a PR
            try:
                result = subprocess.run(
                    ["gh", "pr", "view", "--json", "number"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                pr_data = json.loads(result.stdout)
                pr_number = pr_data.get("number")
            except:
                # No PR context, skip check
                return []

        if not pr_number:
            return []

        # Get repository info
        try:
            repo_result = subprocess.run(
                ["gh", "repo", "view", "--json", "owner,name"],
                capture_output=True,
                text=True,
                check=True,
            )
            repo_data = json.loads(repo_result.stdout)
            owner = repo_data.get("owner", {}).get("login", "")
            name = repo_data.get("name", "")
        except:
            print("⚠️  Could not detect repository info")
            return []

        # GraphQL query for unresolved review threads
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
            }
          }
        }
        """

        # Execute GraphQL query
        result = subprocess.run(
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
        threads = (
            data.get("data", {})
            .get("repository", {})
            .get("pullRequest", {})
            .get("reviewThreads", {})
            .get("nodes", [])
        )

        # Filter for unresolved threads
        unresolved_threads = []
        for thread in threads:
            if not thread.get(
                "isResolved", True
            ):  # Default to resolved if field missing
                comment = thread.get("comments", {}).get("nodes", [{}])[0]
                unresolved_threads.append(
                    {
                        "thread_id": thread.get("id"),
                        "body": comment.get("body", ""),
                        "author": comment.get("author", {}).get("login", "unknown"),
                        "created_at": comment.get("createdAt", ""),
                        "path": comment.get("path"),
                        "line": comment.get("line"),
                        "type": "review_thread",
                    }
                )

        return unresolved_threads

    except Exception as e:
        print(f"⚠️  Could not check PR comments: {e}")
        return []


def write_pr_comments_scratch(comments):
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

            f.write("## Comments to Address\n\n")

            for i, comment in enumerate(comments, 1):
                comment_id = comment.get('id', f'comment-{i}')
                author = comment.get('author', 'unknown')
                f.write(f"### Comment #{comment_id} - {author}\n")
                if comment.get("path") and comment.get("line"):
                    f.write(f"**Location**: `{comment['path']}:{comment['line']}`\n")
                elif comment.get("path"):
                    f.write(f"**Location**: `{comment['path']}`\n")
                f.write(f"**Type**: {comment.get('type', 'comment')}\n")
                f.write(f"**Created**: {comment.get('created_at', 'N/A')}\n\n")
                body = comment.get('body', '(no content)')
                f.write(f"**Content**:\n{body}\n\n")
                f.write("**Conceptual Theme**: _[AI to classify]_\n")
                f.write("**Risk Priority**: _[AI to assess]_\n")
                f.write("**Related Comments**: _[AI to identify]_\n\n")
                f.write("---\n\n")

    except Exception as e:
        print(f"⚠️  Could not write scratch file: {e}")


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
  commit - Fast checks for development cycle (excludes security & sonar, ~30s savings)
  PR     - Full validation for pull requests (all checks including security & sonar)

Available checks: black, isort, lint, js-lint, js-format, tests, coverage, security, sonar, types, imports, duplication, integration, smoke, frontend-check

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
        "--checks",
        nargs="+",
        help="Run specific checks only (e.g. --checks black isort lint tests). Available: black, isort, lint, tests, coverage, security, sonar, types, imports, duplication, integration, smoke, frontend-check",
    )

    parser.add_argument(
        "--skip-pr-comments",
        action="store_true",
        help="Skip PR comment resolution check (run full PR gate without checking for unaddressed comments)",
    )

    args = parser.parse_args()

    # Handle PR validation with comment checking (unless skipped)
    if args.validation_type == "PR" and not args.skip_pr_comments:
        # Check for unaddressed PR comments before running quality gates
        unaddressed_comments = check_pr_comments()
        if unaddressed_comments:
            print("❌ PR VALIDATION FAILED: Unaddressed review comments found")
            print("\n📋 Outstanding PR Comments:")
            print("=" * 50)
            for i, comment in enumerate(unaddressed_comments, 1):
                location = (
                    f" ({comment['path']}:{comment['line']})"
                    if comment.get("path") and comment.get("line")
                    else ""
                )
                print(
                    f"{i}. [{comment['author']}]{location}: {comment['body'][:100]}..."
                )

            print(f"\n💡 Strategic PR Review Protocol:")
            print("1. Group comments by underlying concept (not file location)")
            print(
                "2. Prioritize by risk/surface area - lower-level changes obviate surface comments"
            )
            print("3. Address entire themes with comprehensive commits")
            print("4. Use GitHub MCP tools to reply and cross-reference related fixes")
            print(f"\n📄 Full comments written to: pr_comments_scratch.md")

            # Write detailed scratch file
            write_pr_comments_scratch(unaddressed_comments)
            sys.exit(1)

    # Convert validation type string to enum
    validation_type_map = {
        "commit": ValidationType.COMMIT,
        "PR": ValidationType.PR,
        "integration": ValidationType.INTEGRATION,
        "smoke": ValidationType.SMOKE,
        "full": ValidationType.FULL,
    }
    validation_type = validation_type_map[args.validation_type]

    # Create and run the executor
    executor = QualityGateExecutor()
    exit_code = executor.execute(checks=args.checks, validation_type=validation_type)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
