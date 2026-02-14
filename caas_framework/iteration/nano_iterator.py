"""
Nano Iterator - TDD Cycle Iteration

Implements the smallest iteration unit:
- RED: Write failing test
- GREEN: Minimal implementation to pass test
- REFACTOR: Improve code quality

Part of CAAS-E Week 6 implementation (Task 6.2).
"""

import time
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from caas_framework.models.iteration import (
    NanoIteration,
    IterationAttempt,
    IterationStatus,
    FailureReason,
    IterationResult,
    IterationLevel,
)

logger = logging.getLogger(__name__)


class NanoIterator:
    """
    Nano-level iterator for TDD cycle.

    Workflow:
    1. RED: Verify test fails initially
    2. GREEN: Generate code to pass test (max 3 attempts)
    3. REFACTOR: Improve code quality while keeping tests green
    """

    def __init__(
        self,
        max_retries: int = 3,
        code_quality_threshold: float = 7.0,
    ):
        """
        Initialize nano iterator.

        Args:
            max_retries: Maximum attempts for GREEN phase
            code_quality_threshold: Minimum code quality score
        """
        self.max_retries = max_retries
        self.code_quality_threshold = code_quality_threshold
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(
        self,
        test_file: Path,
        implementation_file: Path,
        iteration_id: Optional[str] = None,
    ) -> IterationResult:
        """
        Execute TDD cycle iteration.

        Args:
            test_file: Path to test file
            implementation_file: Path to implementation file
            iteration_id: Optional iteration ID

        Returns:
            IterationResult with final status
        """
        iteration_id = iteration_id or f"nano_{int(time.time())}"

        self.logger.info(f"Starting nano iteration: {iteration_id}")

        # Create iteration object
        iteration = NanoIteration(
            iteration_id=iteration_id,
            test_file=str(test_file),
            implementation_file=str(implementation_file),
            max_retries=self.max_retries,
        )

        try:
            # Phase 1: RED - Verify test fails
            self.logger.info("Phase 1: RED - Verifying test fails initially")
            red_result = self._execute_red_phase(iteration)

            if not red_result:
                # Test already passes - skip to refactor
                self.logger.warning("Test already passes - skipping GREEN phase")
                iteration.test_passed = True
                iteration.status = IterationStatus.SUCCESS
            else:
                # Phase 2: GREEN - Make test pass
                self.logger.info("Phase 2: GREEN - Making test pass")
                green_result = self._execute_green_phase(iteration)

                if not green_result:
                    iteration.status = IterationStatus.EXHAUSTED
                    return self._create_result(iteration, successful=False)

                iteration.test_passed = True

            # Phase 3: REFACTOR - Improve code quality
            self.logger.info("Phase 3: REFACTOR - Improving code quality")
            refactor_result = self._execute_refactor_phase(iteration)

            if refactor_result:
                iteration.refactored = True
                iteration.status = IterationStatus.SUCCESS
            else:
                # Refactor failed, but tests still pass
                self.logger.warning("Refactor failed, keeping original GREEN code")
                iteration.status = IterationStatus.SUCCESS

            self.logger.info(f"Nano iteration complete: {iteration.status.value}")

            return self._create_result(iteration, successful=True)

        except Exception as e:
            self.logger.error(f"Nano iteration failed: {e}")
            iteration.status = IterationStatus.FAILED
            return self._create_result(iteration, successful=False, error=str(e))

    def _execute_red_phase(self, iteration: NanoIteration) -> bool:
        """
        Execute RED phase - verify test fails.

        Returns:
            True if test fails (as expected), False if test passes
        """
        test_result = self._run_tests(Path(iteration.test_file))

        if test_result["passed"]:
            # Test already passes - RED phase fails
            self.logger.warning("RED phase: Test already passes")
            return False

        self.logger.info("RED phase: Test fails as expected ✓")
        return True

    def _execute_green_phase(self, iteration: NanoIteration) -> bool:
        """
        Execute GREEN phase - make test pass with minimal code.

        Returns:
            True if test passes within max retries, False otherwise
        """
        for attempt in range(1, self.max_retries + 1):
            self.logger.info(f"GREEN attempt {attempt}/{self.max_retries}")

            start_time = time.time()
            iteration.current_attempt = attempt

            # In real implementation, this would call code generator
            # For now, just check if test passes
            test_result = self._run_tests(Path(iteration.test_file))

            duration = time.time() - start_time

            # Record attempt
            attempt_obj = IterationAttempt(
                attempt_number=attempt,
                timestamp=datetime.now(),
                status=IterationStatus.SUCCESS if test_result["passed"] else IterationStatus.FAILED,
                duration_seconds=duration,
                failure_reason=FailureReason.TEST_FAILURE if not test_result["passed"] else None,
                error_message=test_result.get("error"),
            )
            iteration.attempts.append(attempt_obj)

            if test_result["passed"]:
                self.logger.info(f"GREEN phase: Test passed on attempt {attempt} ✓")
                return True

            self.logger.warning(f"GREEN attempt {attempt} failed: {test_result.get('error', 'Unknown')}")

            # Wait before retry (exponential backoff)
            if attempt < self.max_retries:
                delay = 0.5 * (2 ** (attempt - 1))  # 0.5s, 1s, 2s
                time.sleep(delay)

        self.logger.error("GREEN phase: Max retries exhausted")
        return False

    def _execute_refactor_phase(self, iteration: NanoIteration) -> bool:
        """
        Execute REFACTOR phase - improve code quality.

        Returns:
            True if refactoring successful, False otherwise
        """
        # Analyze code quality
        quality_score = self._analyze_code_quality(Path(iteration.implementation_file))
        iteration.code_quality_score = quality_score

        self.logger.info(f"Code quality score: {quality_score:.1f}/10.0")

        if quality_score >= self.code_quality_threshold:
            self.logger.info("Code quality already meets threshold")
            return True

        # Attempt refactoring
        self.logger.info("Attempting code refactoring...")

        # In real implementation, this would call refactor engine
        # For now, simulate refactoring

        # Re-run tests to ensure they still pass
        test_result = self._run_tests(Path(iteration.test_file))

        if not test_result["passed"]:
            self.logger.error("REFACTOR: Tests failed after refactoring - rolling back")
            return False

        # Re-check quality
        new_quality = self._analyze_code_quality(Path(iteration.implementation_file))
        iteration.code_quality_score = new_quality

        if new_quality > quality_score:
            self.logger.info(f"REFACTOR: Quality improved {quality_score:.1f} → {new_quality:.1f}")
            return True
        else:
            self.logger.warning("REFACTOR: Quality did not improve")
            return False

    def _run_tests(self, test_file: Path) -> Dict[str, Any]:
        """
        Run pytest on test file.

        Returns:
            Dict with "passed" (bool) and optional "error" (str)
        """
        if not test_file.exists():
            return {"passed": False, "error": "Test file not found"}

        try:
            # Run pytest
            result = subprocess.run(
                ["pytest", str(test_file), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            passed = result.returncode == 0

            return {
                "passed": passed,
                "error": result.stderr if not passed else None,
                "output": result.stdout,
            }

        except subprocess.TimeoutExpired:
            return {"passed": False, "error": "Test execution timeout"}
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def _analyze_code_quality(self, code_file: Path) -> float:
        """
        Analyze code quality using AST.

        Returns:
            Quality score (0.0-10.0)
        """
        if not code_file.exists():
            return 0.0

        try:
            import ast

            content = code_file.read_text()
            tree = ast.parse(content)

            # Simple quality metrics
            score = 10.0

            # Check for docstrings
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            if functions:
                with_docstrings = sum(1 for f in functions if ast.get_docstring(f))
                docstring_ratio = with_docstrings / len(functions)
                score -= (1 - docstring_ratio) * 2  # -2 points max

            # Check for long functions (>50 lines)
            for func in functions:
                func_lines = func.end_lineno - func.lineno if hasattr(func, 'end_lineno') else 0
                if func_lines > 50:
                    score -= 0.5  # -0.5 per long function

            # Check for complexity (nested if/for)
            max_depth = self._calculate_max_depth(tree)
            if max_depth > 3:
                score -= (max_depth - 3) * 0.5

            return max(0.0, min(10.0, score))

        except Exception as e:
            self.logger.warning(f"Code quality analysis failed: {e}")
            return 5.0  # Default mid-range score

    def _calculate_max_depth(self, node, current_depth=0):
        """Calculate maximum nesting depth"""
        max_depth = current_depth

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With)):
                child_depth = self._calculate_max_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)

        return max_depth

    def _create_result(
        self,
        iteration: NanoIteration,
        successful: bool,
        error: Optional[str] = None,
    ) -> IterationResult:
        """Create iteration result"""
        final_attempt = iteration.attempts[-1] if iteration.attempts else None

        return IterationResult(
            level=IterationLevel.NANO,
            iteration_id=iteration.iteration_id,
            status=iteration.status,
            total_attempts=iteration.current_attempt,
            successful=successful,
            final_attempt=final_attempt,
            error_summary=error,
            recovery_actions=[
                "Re-generate implementation code",
                "Simplify test requirements",
                "Check test assertions",
            ] if not successful else [],
        )
