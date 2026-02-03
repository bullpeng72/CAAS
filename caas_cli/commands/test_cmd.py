"""
Test Command

Execute tests on generated code
"""

from pathlib import Path

import click

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_progress,
    echo_success,
    echo_warning,
    handle_keyboard_interrupt,
)


@click.group()
def test():
    """Execute tests on generated code"""
    pass


@test.command()
@click.option(
    "--test-file",
    type=click.Path(exists=True),
    required=True,
    help="Path to test file or directory",
)
@click.option(
    "--coverage/--no-coverage", default=True, help="Enable code coverage (default: enabled)"
)
@click.option("--verbose/--quiet", "-v/-q", default=True, help="Verbose output (default: verbose)")
@click.option(
    "--marker", "-m", type=str, help="Run tests with specific marker (e.g., 'unit', 'integration')"
)
@click.option(
    "--parallel", "-n", type=int, help="Run tests in parallel (specify number of workers)"
)
@click.option("--report", "-r", type=click.Path(), help="Save test report to file")
@handle_keyboard_interrupt
def run(test_file, coverage, verbose, marker, parallel, report):
    """
    Run pytest tests

    \b
    USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Run all tests:
       $ caas test run --test-file ./tests/

    \b
    2️⃣  Run specific test file:
       $ caas test run --test-file ./tests/test_agents.py

    \b
    3️⃣  Run with coverage disabled:
       $ caas test run --test-file ./tests/ --no-coverage

    \b
    4️⃣  Run unit tests only:
       $ caas test run --test-file ./tests/ --marker unit

    \b
    5️⃣  Run in parallel (4 workers):
       $ caas test run --test-file ./tests/ --parallel 4

    \b
    6️⃣  Save test report:
       $ caas test run --test-file ./tests/ --report test_report.json

    \b
    TEST MARKERS:
    ═══════════════════════════════════════════════════════════════════════════
    • unit          - Unit tests
    • integration   - Integration tests
    • slow          - Slow tests (skip for quick runs)
    • agent         - Agent-specific tests
    • task          - Task-specific tests
    """
    try:
        echo_progress(f"Running tests from: {test_file}")
        click.echo()

        # Import test executor
        from caas_framework.testing.test_executor import TestExecutor

        # Create executor
        executor = TestExecutor(working_directory=Path.cwd())

        # Prepare pytest args
        pytest_args = [test_file]

        if verbose:
            pytest_args.append("-v")
        else:
            pytest_args.append("-q")

        if coverage:
            pytest_args.extend(["--cov", "--cov-report=term-missing"])

        if marker:
            pytest_args.extend(["-m", marker])

        if parallel:
            pytest_args.extend(["-n", str(parallel)])

        if report:
            pytest_args.extend(["--json-report", f"--json-report-file={report}"])

        # Run tests
        test_path = Path(test_file)
        if test_path.is_file():
            test_code = test_path.read_text()
            result = executor.execute_pytest(
                test_file_path=test_file, test_code=test_code, coverage=coverage, verbose=verbose
            )
        else:
            # Run directory tests
            result = executor.execute_pytest_directory(
                test_directory=test_file, coverage=coverage, verbose=verbose
            )

        # Print results
        click.echo()
        click.echo(click.style("Test Results:", bold=True))
        click.echo(f"  Total tests:    {result.total_tests}")
        click.echo(f"  Passed:         {result.passed}")
        click.echo(f"  Failed:         {result.failed}")
        click.echo(f"  Skipped:        {result.skipped}")

        if hasattr(result, "duration"):
            click.echo(f"  Duration:       {result.duration:.2f}s")

        if coverage and hasattr(result, "coverage_percent"):
            click.echo(f"  Coverage:       {result.coverage_percent:.1f}%")

        # Show status
        click.echo()
        if result.failed == 0:
            echo_success("All tests passed!")
            return 0
        else:
            echo_error(f"{result.failed} test(s) failed")
            return 1

    except ImportError as e:
        echo_error(f"Failed to import test modules: {e}")
        echo_info("Make sure caas-framework is installed: pip install -e .")
        return 1
    except Exception as e:
        echo_error(f"Test execution error: {e}")
        import traceback

        if verbose:
            echo_error(traceback.format_exc())
        return 1


@test.command()
@click.option(
    "--test-file",
    type=click.Path(exists=True),
    required=True,
    help="Path to test file or directory",
)
@click.option(
    "--min-coverage", type=float, default=80.0, help="Minimum coverage percentage (default: 80.0)"
)
@handle_keyboard_interrupt
def coverage(test_file, min_coverage):
    """
    Check test coverage

    \b
    USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Check coverage:
       $ caas test coverage --test-file ./tests/

    \b
    2️⃣  Require 90% minimum coverage:
       $ caas test coverage --test-file ./tests/ --min-coverage 90.0
    """
    try:
        echo_progress("Checking test coverage...")
        click.echo()

        from caas_framework.testing.test_executor import TestExecutor

        executor = TestExecutor(working_directory=Path.cwd())

        # Run tests with coverage
        test_path = Path(test_file)
        if test_path.is_file():
            test_code = test_path.read_text()
            result = executor.execute_pytest(
                test_file_path=test_file, test_code=test_code, coverage=True, verbose=False
            )
        else:
            result = executor.execute_pytest_directory(
                test_directory=test_file, coverage=True, verbose=False
            )

        # Show coverage
        click.echo()
        click.echo(click.style("Coverage Report:", bold=True))

        if hasattr(result, "coverage_percent"):
            coverage_pct = result.coverage_percent
            click.echo(f"  Coverage: {coverage_pct:.1f}%")
            click.echo(f"  Minimum:  {min_coverage:.1f}%")

            click.echo()
            if coverage_pct >= min_coverage:
                echo_success(f"Coverage meets minimum requirement ({min_coverage}%)")
                return 0
            else:
                echo_error(f"Coverage below minimum ({coverage_pct:.1f}% < {min_coverage}%)")
                return 1
        else:
            echo_warning("Coverage data not available")
            return 1

    except ImportError as e:
        echo_error(f"Failed to import test modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Coverage check error: {e}")
        return 1


@test.command()
@click.argument("test_file", type=click.Path(exists=True))
@handle_keyboard_interrupt
def validate(test_file):
    """
    Validate test file syntax

    \b
    USAGE:
       $ caas test validate ./tests/test_agents.py
    """
    try:
        echo_progress(f"Validating test file: {test_file}")

        test_path = Path(test_file)
        test_code = test_path.read_text()

        # Check syntax
        import ast

        try:
            ast.parse(test_code)
            echo_success("Test file syntax is valid")
            return 0
        except SyntaxError as e:
            echo_error(f"Syntax error in test file: {e}")
            return 1

    except Exception as e:
        echo_error(f"Validation error: {e}")
        return 1
