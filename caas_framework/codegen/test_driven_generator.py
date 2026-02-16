"""
Test-Driven Code Generator

Generates code that passes given tests using LLM and iterative refinement.

Part of CAAS-E Week 4 implementation (Task 4.2).
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from caas_framework.codegen.test_parser import (
    ParsedTestFile,
    TestParser,
)
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils.logger import get_logger


@dataclass
class GenerationIteration:
    """Represents one iteration of code generation."""

    iteration: int
    generated_code: str
    test_results: Dict[str, bool]  # test_name -> passed
    errors: List[str]
    passed_count: int
    failed_count: int


@dataclass
class TDDGenerationResult:
    """Result of test-driven code generation."""

    success: bool
    final_code: str
    iterations: List[GenerationIteration]
    total_tests: int
    passed_tests: int
    failed_tests: int
    generation_time: float


class TestDrivenCodeGenerator:
    """
    Generates code that passes given tests.

    Workflow:
    1. Parse test files to extract expectations
    2. Generate initial code based on test requirements
    3. Run tests
    4. If tests fail, analyze failures and regenerate (max 3 iterations)
    5. Return final code
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        max_iterations: int = 3,
        timeout_per_test: int = 30,
    ):
        """
        Initialize Test-Driven Code Generator.

        Args:
            llm_plugin: LLM plugin for code generation
            max_iterations: Maximum refinement iterations (default: 3)
            timeout_per_test: Timeout per test run in seconds (default: 30)
        """
        self.llm = llm_plugin
        self.max_iterations = max_iterations
        self.timeout_per_test = timeout_per_test
        self.logger = get_logger(__name__)
        self.test_parser = TestParser()

    async def generate_from_tests(
        self,
        test_files: List[Path],
        output_dir: Path,
        context: Optional[Dict] = None,
    ) -> TDDGenerationResult:
        """
        Generate code that passes the given tests.

        Args:
            test_files: List of test file paths
            output_dir: Directory to write generated code
            context: Optional context (specs, requirements, etc.)

        Returns:
            TDDGenerationResult with success status and code
        """
        import time

        start_time = time.time()

        self.logger.info(f"Starting TDD code generation from {len(test_files)} test files")

        # Step 1: Parse test files
        parsed_files = []
        for test_file in test_files:
            parsed = self.test_parser.parse_test_file(test_file)
            parsed_files.append(parsed)

        # Step 2: Extract requirements
        requirements = self.test_parser.extract_requirements_from_tests(parsed_files)

        self.logger.info(
            f"Extracted requirements: "
            f"{len(requirements['functions'])} functions, "
            f"{len(requirements['methods'])} methods"
        )

        # Step 3: Generate code iteratively
        iterations = []
        current_code = ""

        for iteration in range(1, self.max_iterations + 1):
            self.logger.info(f"Iteration {iteration}/{self.max_iterations}")

            # Generate code
            if iteration == 1:
                # Initial generation
                current_code = await self._generate_initial_code(
                    parsed_files, requirements, context
                )
            else:
                # Refinement based on test failures
                previous_iteration = iterations[-1]
                current_code = await self._refine_code(
                    current_code,
                    previous_iteration.errors,
                    parsed_files,
                )

            # Write code to file
            code_file = output_dir / "generated_code.py"
            code_file.parent.mkdir(parents=True, exist_ok=True)
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(current_code)

            # Run tests
            test_results, errors = await self._run_tests(test_files, output_dir)

            # Record iteration
            passed_count = sum(1 for passed in test_results.values() if passed)
            failed_count = len(test_results) - passed_count

            iteration_result = GenerationIteration(
                iteration=iteration,
                generated_code=current_code,
                test_results=test_results,
                errors=errors,
                passed_count=passed_count,
                failed_count=failed_count,
            )
            iterations.append(iteration_result)

            self.logger.info(
                f"Iteration {iteration}: "
                f"{passed_count}/{len(test_results)} tests passed"
            )

            # Check if all tests passed
            if failed_count == 0:
                self.logger.info("✅ All tests passed!")
                break

        # Step 4: Prepare result
        final_iteration = iterations[-1]
        success = final_iteration.failed_count == 0

        result = TDDGenerationResult(
            success=success,
            final_code=current_code,
            iterations=iterations,
            total_tests=len(final_iteration.test_results),
            passed_tests=final_iteration.passed_count,
            failed_tests=final_iteration.failed_count,
            generation_time=time.time() - start_time,
        )

        if success:
            self.logger.info(
                f"✅ TDD generation succeeded in {len(iterations)} iterations "
                f"({result.generation_time:.2f}s)"
            )
        else:
            self.logger.warning(
                f"⚠️ TDD generation incomplete after {len(iterations)} iterations. "
                f"{result.failed_tests}/{result.total_tests} tests still failing."
            )

        return result

    async def _generate_initial_code(
        self,
        parsed_files: List[ParsedTestFile],
        requirements: Dict[str, List[str]],
        context: Optional[Dict],
    ) -> str:
        """Generate initial code based on test requirements."""
        self.logger.info("Generating initial code from tests...")

        # Build prompt
        prompt = self._build_generation_prompt(parsed_files, requirements, context)

        # Call LLM
        response = await self.llm.ainvoke(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3000,
        )

        # Extract code from response
        code = self._extract_code_from_response(response.content)

        return code

    async def _refine_code(
        self,
        current_code: str,
        errors: List[str],
        parsed_files: List[ParsedTestFile],
    ) -> str:
        """Refine code based on test failures."""
        self.logger.info(f"Refining code based on {len(errors)} errors...")

        # Build refinement prompt
        prompt = self._build_refinement_prompt(current_code, errors, parsed_files)

        # Call LLM
        response = await self.llm.ainvoke(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3000,
        )

        # Extract refined code
        code = self._extract_code_from_response(response.content)

        return code

    def _build_generation_prompt(
        self,
        parsed_files: List[ParsedTestFile],
        requirements: Dict[str, List[str]],
        context: Optional[Dict],
    ) -> str:
        """Build prompt for initial code generation."""
        prompt_parts = []

        prompt_parts.append(
            "You are a Python code generator. Generate code that passes the given tests."
        )

        # Add context if available
        if context:
            if "specs" in context:
                prompt_parts.append(f"\nSpecifications:\n{context['specs']}")
            if "requirements" in context:
                prompt_parts.append(f"\nRequirements:\n{context['requirements']}")

        # Add test information
        prompt_parts.append("\n## Test Files\n")

        for parsed in parsed_files:
            prompt_parts.append(f"\n### {parsed.file_path.name}\n")

            # Add test functions
            for test_func in parsed.test_functions:
                prompt_parts.append(f"\n**Test**: {test_func.name}")
                if test_func.description:
                    prompt_parts.append(f"Description: {test_func.description}")

                # Add assertions
                if test_func.assertions:
                    prompt_parts.append("Assertions:")
                    for assertion in test_func.assertions:
                        prompt_parts.append(
                            f"  - {assertion.type}: {assertion.target}"
                            + (f" == {assertion.expected}" if assertion.expected else "")
                        )

        # Add requirements
        prompt_parts.append("\n## Inferred Requirements\n")
        prompt_parts.append(f"Functions to implement: {', '.join(requirements['functions'])}")
        prompt_parts.append(f"Methods to implement: {', '.join(requirements['methods'])}")

        # Instructions
        prompt_parts.append("\n## Instructions\n")
        prompt_parts.append("Generate Python code that:")
        prompt_parts.append("1. Implements all required functions and methods")
        prompt_parts.append("2. Passes all test assertions")
        prompt_parts.append("3. Follows Python best practices")
        prompt_parts.append("4. Includes docstrings")
        prompt_parts.append("\nReturn ONLY the Python code, no explanations.")

        return "\n".join(prompt_parts)

    def _build_refinement_prompt(
        self,
        current_code: str,
        errors: List[str],
        parsed_files: List[ParsedTestFile],
    ) -> str:
        """Build prompt for code refinement."""
        prompt_parts = []

        prompt_parts.append(
            "The following code was generated but some tests are failing. "
            "Fix the code to pass all tests."
        )

        # Add current code
        prompt_parts.append("\n## Current Code\n")
        prompt_parts.append(f"```python\n{current_code}\n```")

        # Add errors
        prompt_parts.append("\n## Test Errors\n")
        for i, error in enumerate(errors[:10], 1):  # Limit to first 10 errors
            prompt_parts.append(f"{i}. {error}")

        # Add test expectations
        prompt_parts.append("\n## Test Expectations\n")
        for parsed in parsed_files:
            for test_func in parsed.test_functions:
                if test_func.assertions:
                    prompt_parts.append(f"\n**{test_func.name}**:")
                    for assertion in test_func.assertions:
                        prompt_parts.append(
                            f"  - Expects: {assertion.target}"
                            + (f" == {assertion.expected}" if assertion.expected else "")
                        )

        # Instructions
        prompt_parts.append("\n## Instructions\n")
        prompt_parts.append("Fix the code to:")
        prompt_parts.append("1. Resolve all test errors")
        prompt_parts.append("2. Pass all test assertions")
        prompt_parts.append("3. Maintain code quality")
        prompt_parts.append("\nReturn ONLY the fixed Python code, no explanations.")

        return "\n".join(prompt_parts)

    def _extract_code_from_response(self, response: str) -> str:
        """Extract Python code from LLM response."""
        # Try to extract from markdown code block
        if "```python" in response:
            start = response.index("```python") + len("```python")
            end = response.index("```", start)
            return response[start:end].strip()
        elif "```" in response:
            start = response.index("```") + len("```")
            end = response.index("```", start)
            return response[start:end].strip()
        else:
            # Assume entire response is code
            return response.strip()

    async def _run_tests(
        self,
        test_files: List[Path],
        code_dir: Path,
    ) -> Tuple[Dict[str, bool], List[str]]:
        """
        Run tests and collect results.

        Args:
            test_files: List of test file paths
            code_dir: Directory containing generated code

        Returns:
            Tuple of (test_results dict, error messages list)
        """
        self.logger.info(f"Running {len(test_files)} test files...")

        test_results = {}
        errors = []

        for test_file in test_files:
            # Run pytest on this file
            try:
                result = subprocess.run(
                    ["pytest", str(test_file), "-v", "--tb=short"],
                    cwd=str(code_dir),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_per_test,
                )

                # Parse pytest output
                file_results, file_errors = self._parse_pytest_output(
                    result.stdout, result.stderr
                )

                test_results.update(file_results)
                errors.extend(file_errors)

            except subprocess.TimeoutExpired:
                self.logger.warning(f"Test timed out: {test_file.name}")
                errors.append(f"Timeout: {test_file.name}")

            except Exception as e:
                self.logger.error(f"Error running test {test_file.name}: {e}")
                errors.append(f"Error: {test_file.name}: {str(e)}")

        return test_results, errors

    def _parse_pytest_output(
        self, stdout: str, stderr: str
    ) -> Tuple[Dict[str, bool], List[str]]:
        """Parse pytest output to extract test results."""
        test_results = {}
        errors = []

        # Parse stdout for test results
        for line in stdout.split("\n"):
            # Look for test results (e.g., "test_foo.py::test_bar PASSED")
            if "PASSED" in line:
                test_name = self._extract_test_name(line)
                if test_name:
                    test_results[test_name] = True

            elif "FAILED" in line:
                test_name = self._extract_test_name(line)
                if test_name:
                    test_results[test_name] = False
                errors.append(line.strip())

            elif "ERROR" in line:
                errors.append(line.strip())

        # Add stderr if any
        if stderr.strip():
            errors.append(stderr.strip())

        return test_results, errors

    def _extract_test_name(self, line: str) -> Optional[str]:
        """Extract test name from pytest output line."""
        # Line format: "test_file.py::test_name PASSED"
        if "::" in line:
            parts = line.split("::")
            if len(parts) >= 2:
                test_name = parts[1].split()[0]
                return test_name
        return None
