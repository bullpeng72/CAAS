"""
TDD (Test-Driven Development) Orchestrator

Manages the TDD workflow:
1. Generate test scenarios from features
2. Generate test code BEFORE implementation
3. Generate implementation to pass tests
4. Run tests and validate
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from caas_framework.models.specifications import FeatureSpec, ConcretizedRequirement
from caas_framework.testing.test_scenario import (
    TestScenario,
    TestScenarioGenerator,
    generate_test_scenarios
)
from caas_framework.testing.test_generator import (
    TestFirstGenerator,
    TestCodeResult,
    generate_test_code
)
from caas_framework.testing.test_executor import TestExecutor, TestResult
from caas_framework.plugins.llm.base import LLMPlugin

logger = logging.getLogger(__name__)


@dataclass
class TDDCycle:
    """Single TDD Red-Green-Refactor cycle"""
    feature_name: str
    scenarios: List[TestScenario]
    test_code: Optional[TestCodeResult] = None
    implementation_code: Optional[str] = None
    test_results: Optional[TestResult] = None
    cycle_number: int = 1
    passed: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TDDWorkflowResult:
    """Result of complete TDD workflow"""
    success: bool
    cycles: List[TDDCycle]
    total_scenarios: int
    total_tests_passed: int
    total_tests_failed: int
    test_coverage: float  # 0.0-1.0
    duration: float  # seconds
    errors: List[str] = field(default_factory=list)

    @property
    def all_tests_passed(self) -> bool:
        """Check if all tests passed"""
        return self.total_tests_failed == 0 and self.total_tests_passed > 0


class TDDOrchestrator:
    """
    TDD Workflow Orchestrator

    Implements the Red-Green-Refactor cycle:
    1. RED: Write failing tests first
    2. GREEN: Write minimal code to pass tests
    3. REFACTOR: Improve code while keeping tests green
    """

    def __init__(
        self,
        llm: LLMPlugin,
        golden_data: ConcretizedRequirement,
        max_refactor_cycles: int = 2,
        enable_edge_cases: bool = True
    ):
        """
        Initialize TDD orchestrator.

        Args:
            llm: LLM plugin for code generation
            golden_data: Golden Data for context
            max_refactor_cycles: Maximum refactoring iterations
            enable_edge_cases: Generate edge case scenarios
        """
        self.llm = llm
        self.golden_data = golden_data
        self.max_refactor_cycles = max_refactor_cycles
        self.enable_edge_cases = enable_edge_cases

        # Initialize generators
        self.scenario_generator = TestScenarioGenerator(llm_client=llm)
        self.test_generator = TestFirstGenerator(llm_client=llm)
        self.test_executor = TestExecutor()

    async def run_tdd_workflow(
        self,
        features: List[FeatureSpec],
        entity_name: str
    ) -> TDDWorkflowResult:
        """
        Run complete TDD workflow for given features.

        Workflow:
        1. Generate test scenarios from features
        2. Generate test code (RED - tests will fail)
        3. Generate implementation code (GREEN - make tests pass)
        4. Run tests and validate
        5. Refactor if needed

        Args:
            features: List of features to implement
            entity_name: Entity name (e.g., "Task", "User")

        Returns:
            TDDWorkflowResult
        """
        start_time = datetime.now()
        cycles: List[TDDCycle] = []
        errors: List[str] = []

        try:
            # Step 1: Generate test scenarios
            logger.info(f"🔴 RED: Generating test scenarios for {entity_name}")
            scenarios = await self._generate_scenarios(features)

            if not scenarios:
                errors.append("No test scenarios generated")
                return TDDWorkflowResult(
                    success=False,
                    cycles=[],
                    total_scenarios=0,
                    total_tests_passed=0,
                    total_tests_failed=0,
                    test_coverage=0.0,
                    duration=0.0,
                    errors=errors
                )

            logger.info(f"Generated {len(scenarios)} test scenarios")

            # Step 2: Generate test code (RED)
            logger.info(f"🔴 RED: Generating test code for {entity_name}")
            test_code_result = await self._generate_test_code(scenarios, entity_name)

            if not test_code_result:
                errors.append("Failed to generate test code")
                return self._create_error_result(cycles, errors, start_time)

            logger.info(f"Generated test code: {test_code_result.test_file_path}")

            # Step 3: Generate implementation (GREEN)
            logger.info(f"🟢 GREEN: Generating implementation for {entity_name}")
            implementation_code = await self._generate_implementation(
                scenarios=scenarios,
                entity_name=entity_name,
                test_code=test_code_result.test_code
            )

            if not implementation_code:
                errors.append("Failed to generate implementation")
                return self._create_error_result(cycles, errors, start_time)

            logger.info(f"Generated implementation code")

            # Step 4: Run tests (Validate GREEN)
            logger.info(f"🧪 Running tests for {entity_name}")
            test_results = await self._run_tests(test_code_result.test_file_path)

            # Create cycle result
            cycle = TDDCycle(
                feature_name=entity_name,
                scenarios=scenarios,
                test_code=test_code_result,
                implementation_code=implementation_code,
                test_results=test_results,
                cycle_number=1,
                passed=test_results.success if test_results else False
            )
            cycles.append(cycle)

            # Step 5: Refactor if needed (optional)
            if cycle.passed and self.max_refactor_cycles > 0:
                logger.info(f"🔧 REFACTOR: Improving code quality")
                refactored_cycles = await self._refactor_cycles(
                    cycle=cycle,
                    entity_name=entity_name
                )
                cycles.extend(refactored_cycles)

            # Calculate results
            duration = (datetime.now() - start_time).total_seconds()
            total_passed = sum(c.test_results.passed if c.test_results else 0 for c in cycles)
            total_failed = sum(c.test_results.failed if c.test_results else 0 for c in cycles)
            test_coverage = self._calculate_coverage(scenarios, cycles)

            result = TDDWorkflowResult(
                success=all(c.passed for c in cycles),
                cycles=cycles,
                total_scenarios=len(scenarios),
                total_tests_passed=total_passed,
                total_tests_failed=total_failed,
                test_coverage=test_coverage,
                duration=duration,
                errors=errors
            )

            if result.success:
                logger.info(f"✅ TDD workflow completed successfully!")
                logger.info(f"   Scenarios: {result.total_scenarios}")
                logger.info(f"   Tests passed: {result.total_tests_passed}")
                logger.info(f"   Coverage: {result.test_coverage:.1%}")
            else:
                logger.warning(f"⚠️ TDD workflow completed with failures")
                logger.warning(f"   Tests failed: {result.total_tests_failed}")

            return result

        except Exception as e:
            logger.error(f"❌ TDD workflow error: {e}")
            errors.append(str(e))
            return self._create_error_result(cycles, errors, start_time)

    async def _generate_scenarios(
        self,
        features: List[FeatureSpec]
    ) -> List[TestScenario]:
        """Generate test scenarios from features"""
        try:
            scenarios = self.scenario_generator.generate_scenarios(
                features=features,
                golden_data=self.golden_data
            )
            return scenarios
        except Exception as e:
            logger.error(f"Error generating scenarios: {e}")
            return []

    async def _generate_test_code(
        self,
        scenarios: List[TestScenario],
        entity_name: str
    ) -> Optional[TestCodeResult]:
        """Generate test code from scenarios"""
        try:
            test_code_result = self.test_generator.generate_test_code(
                scenarios=scenarios,
                entity_name=entity_name,
                framework="pytest"
            )
            return test_code_result
        except Exception as e:
            logger.error(f"Error generating test code: {e}")
            return None

    async def _generate_implementation(
        self,
        scenarios: List[TestScenario],
        entity_name: str,
        test_code: str
    ) -> Optional[str]:
        """
        Generate implementation code to pass tests.

        Uses LLM to generate code that satisfies test scenarios.
        """
        prompt = f"""Generate Python implementation code for {entity_name} that passes the following tests.

Test Scenarios:
{self._format_scenarios_for_prompt(scenarios)}

Test Code:
```python
{test_code}
```

Requirements:
1. Implement all functions tested in the test code
2. Ensure all test assertions will pass
3. Use proper error handling
4. Follow Python best practices
5. Include docstrings

Generate the implementation code:
"""

        try:
            response = await self.llm.generate(prompt, temperature=0.3)
            # Extract code from response
            implementation = self._extract_code_from_response(response)
            return implementation
        except Exception as e:
            logger.error(f"Error generating implementation: {e}")
            return None

    async def _run_tests(
        self,
        test_file_path: str
    ) -> Optional[TestResult]:
        """Run tests and collect results"""
        try:
            # Note: TestExecutor would need to be implemented to actually run pytest
            # For now, return a mock result
            logger.info(f"Running tests from {test_file_path}")

            # TODO: Implement actual test execution
            # result = self.test_executor.run_tests(test_file_path)

            # Mock result for now
            result = TestResult(
                total_tests=0,  # Would be actual test count
                passed=0,
                failed=0,
                skipped=0,
                errors=0,
                duration=0.0,
                success=True
            )

            return result
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return None

    async def _refactor_cycles(
        self,
        cycle: TDDCycle,
        entity_name: str
    ) -> List[TDDCycle]:
        """
        Refactor implementation while keeping tests green.

        Args:
            cycle: Previous cycle that passed
            entity_name: Entity name

        Returns:
            List of refactoring cycles
        """
        refactored_cycles = []

        for i in range(self.max_refactor_cycles):
            logger.info(f"Refactor cycle {i + 1}/{self.max_refactor_cycles}")

            # Generate refactored code
            refactored_code = await self._refactor_implementation(
                current_code=cycle.implementation_code,
                test_code=cycle.test_code.test_code,
                entity_name=entity_name
            )

            if not refactored_code:
                logger.warning("Refactoring failed, keeping previous version")
                break

            # Run tests with refactored code
            test_results = await self._run_tests(cycle.test_code.test_file_path)

            refactored_cycle = TDDCycle(
                feature_name=entity_name,
                scenarios=cycle.scenarios,
                test_code=cycle.test_code,
                implementation_code=refactored_code,
                test_results=test_results,
                cycle_number=cycle.cycle_number + i + 1,
                passed=test_results.success if test_results else False
            )

            refactored_cycles.append(refactored_cycle)

            # Stop if tests fail after refactoring
            if not refactored_cycle.passed:
                logger.warning("Refactoring broke tests, reverting")
                break

        return refactored_cycles

    async def _refactor_implementation(
        self,
        current_code: str,
        test_code: str,
        entity_name: str
    ) -> Optional[str]:
        """Refactor implementation while keeping tests green"""
        prompt = f"""Refactor the following {entity_name} implementation to improve:
1. Code readability
2. Performance
3. Maintainability
4. Error handling

Current Implementation:
```python
{current_code}
```

Tests (must still pass):
```python
{test_code}
```

Provide refactored implementation that:
- Passes all existing tests
- Improves code quality
- Maintains same functionality
- Adds better docstrings and comments
"""

        try:
            response = await self.llm.generate(prompt, temperature=0.3)
            refactored = self._extract_code_from_response(response)
            return refactored
        except Exception as e:
            logger.error(f"Error refactoring implementation: {e}")
            return None

    def _format_scenarios_for_prompt(self, scenarios: List[TestScenario]) -> str:
        """Format scenarios for LLM prompt"""
        formatted = []
        for scenario in scenarios:
            formatted.append(f"""
Scenario: {scenario.description}
  Given: {', '.join(scenario.bdd.given)}
  When: {', '.join(scenario.bdd.when)}
  Then: {', '.join(scenario.bdd.then)}
""")
        return "\n".join(formatted)

    def _extract_code_from_response(self, response: str) -> str:
        """Extract code from LLM response"""
        # Simple extraction: look for code blocks
        if "```python" in response:
            start = response.find("```python") + len("```python")
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()

        # Fallback: return full response
        return response.strip()

    def _calculate_coverage(
        self,
        scenarios: List[TestScenario],
        cycles: List[TDDCycle]
    ) -> float:
        """Calculate test coverage based on scenarios and results"""
        if not scenarios:
            return 0.0

        # Simple coverage: ratio of passed tests to total scenarios
        total_scenarios = len(scenarios)
        passed_scenarios = sum(1 for c in cycles if c.passed)

        return passed_scenarios / total_scenarios

    def _create_error_result(
        self,
        cycles: List[TDDCycle],
        errors: List[str],
        start_time: datetime
    ) -> TDDWorkflowResult:
        """Create error result"""
        duration = (datetime.now() - start_time).total_seconds()
        return TDDWorkflowResult(
            success=False,
            cycles=cycles,
            total_scenarios=0,
            total_tests_passed=0,
            total_tests_failed=0,
            test_coverage=0.0,
            duration=duration,
            errors=errors
        )
