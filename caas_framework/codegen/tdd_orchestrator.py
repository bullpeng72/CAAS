"""
TDD Orchestrator

Orchestrates test-driven code generation workflow integrating:
- Test parsing
- Code generation
- Test execution
- Iterative refinement

Part of CAAS-E Week 4 implementation (Task 4.2).
"""

from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from caas_framework.codegen.test_parser import TestParser
from caas_framework.codegen.test_driven_generator import (
    TestDrivenCodeGenerator,
    TDDGenerationResult,
)
from caas_framework.models.specifications import (
    AgentSpecModel,
    TaskSpecModel,
    ConcretizedRequirement,
)
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils.logger import get_logger


@dataclass
class TDDWorkflowConfig:
    """Configuration for TDD workflow."""

    max_iterations: int = 3
    timeout_per_test: int = 30
    require_all_tests_pass: bool = True
    generate_missing_code: bool = True


class TDDOrchestrator:
    """
    Orchestrates Test-Driven Development workflow.

    Workflow:
    1. Parse test files to understand requirements
    2. Generate code using TDD generator
    3. Run tests iteratively
    4. Refine until tests pass or max iterations reached
    5. Integrate with existing code generation pipeline
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        config: Optional[TDDWorkflowConfig] = None,
    ):
        """
        Initialize TDD Orchestrator.

        Args:
            llm_plugin: LLM plugin for code generation
            config: TDD workflow configuration
        """
        self.llm = llm_plugin
        self.config = config or TDDWorkflowConfig()
        self.logger = get_logger(__name__)

        # Initialize components
        self.test_parser = TestParser()
        self.code_generator = TestDrivenCodeGenerator(
            llm_plugin=llm_plugin,
            max_iterations=self.config.max_iterations,
            timeout_per_test=self.config.timeout_per_test,
        )

    async def generate_with_tests(
        self,
        test_dir: Path,
        output_dir: Path,
        golden_data: Optional[ConcretizedRequirement] = None,
        agents: Optional[List[AgentSpecModel]] = None,
        tasks: Optional[List[TaskSpecModel]] = None,
        specs_dir: Optional[Path] = None,
    ) -> TDDGenerationResult:
        """
        Generate code using test-driven approach.

        Args:
            test_dir: Directory containing test files
            output_dir: Directory to write generated code
            golden_data: Optional Golden Data for context
            agents: Optional agent specifications
            tasks: Optional task specifications
            specs_dir: Optional directory with YAML specs

        Returns:
            TDDGenerationResult with success status and code
        """
        self.logger.info(f"Starting TDD workflow: {test_dir} -> {output_dir}")

        # Step 1: Discover test files
        test_files = self._discover_test_files(test_dir)

        if not test_files:
            raise ValueError(f"No test files found in {test_dir}")

        self.logger.info(f"Found {len(test_files)} test files")

        # Step 2: Build context
        context = self._build_context(
            golden_data, agents, tasks, specs_dir
        )

        # Step 3: Generate code with TDD approach
        result = await self.code_generator.generate_from_tests(
            test_files=test_files,
            output_dir=output_dir,
            context=context,
        )

        # Step 4: Validate results
        if self.config.require_all_tests_pass and not result.success:
            self.logger.warning(
                f"⚠️ TDD requirement not met: "
                f"{result.failed_tests}/{result.total_tests} tests failing"
            )

        # Step 5: Generate additional files if needed
        if self.config.generate_missing_code and result.success:
            await self._generate_supporting_files(
                output_dir, golden_data, agents, tasks
            )

        return result

    def _discover_test_files(self, test_dir: Path) -> List[Path]:
        """Discover all test files in directory."""
        test_files = []

        # Find test_*.py files
        test_files.extend(test_dir.glob("test_*.py"))

        # Find *_test.py files
        test_files.extend(test_dir.glob("*_test.py"))

        # Recursively search subdirectories
        for subdir in test_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("."):
                test_files.extend(self._discover_test_files(subdir))

        return sorted(set(test_files))

    def _build_context(
        self,
        golden_data: Optional[ConcretizedRequirement],
        agents: Optional[List[AgentSpecModel]],
        tasks: Optional[List[TaskSpecModel]],
        specs_dir: Optional[Path],
    ) -> Dict:
        """Build context for code generation."""
        context = {}

        if golden_data:
            context["golden_data"] = {
                "project_name": golden_data.project_name,
                "description": golden_data.description,
                "features": [
                    {
                        "id": f.id,
                        "name": f.name,
                        "description": f.description,
                    }
                    for f in golden_data.features
                ],
            }

        if agents:
            context["agents"] = [
                {
                    "id": a.id,
                    "role": a.role,
                    "goal": a.goal,
                }
                for a in agents
            ]

        if tasks:
            context["tasks"] = [
                {
                    "id": t.id,
                    "description": t.description,
                    "agent": t.agent,
                }
                for t in tasks
            ]

        if specs_dir and specs_dir.exists():
            context["specs"] = f"YAML specifications available in {specs_dir}"

        return context

    async def _generate_supporting_files(
        self,
        output_dir: Path,
        golden_data: Optional[ConcretizedRequirement],
        agents: Optional[List[AgentSpecModel]],
        tasks: Optional[List[TaskSpecModel]],
    ):
        """Generate supporting files (requirements.txt, README, etc.)."""
        self.logger.info("Generating supporting files...")

        # Generate requirements.txt
        requirements_file = output_dir / "requirements.txt"
        if not requirements_file.exists():
            with open(requirements_file, 'w', encoding='utf-8') as f:
                f.write("# Python dependencies\n")
                f.write("pytest>=7.0.0\n")
                f.write("pytest-asyncio>=0.20.0\n")

                if agents or tasks:
                    f.write("crewai>=0.28.0\n")

        # Generate README.md
        readme_file = output_dir / "README.md"
        if not readme_file.exists() and golden_data:
            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write(f"# {golden_data.project_name}\n\n")
                f.write(f"{golden_data.description}\n\n")
                f.write("## Generated with CAAS-E TDD Workflow\n\n")
                f.write("This code was generated using Test-Driven Development.\n")
                f.write("All tests pass.\n\n")
                f.write("## Usage\n\n")
                f.write("```bash\n")
                f.write("# Run tests\n")
                f.write("pytest\n\n")
                f.write("# Run application\n")
                f.write("python generated_code.py\n")
                f.write("```\n")

        self.logger.info("✅ Supporting files generated")

    async def validate_against_tests(
        self,
        code_file: Path,
        test_files: List[Path],
    ) -> bool:
        """
        Validate existing code against tests.

        Args:
            code_file: Path to code file to validate
            test_files: List of test files

        Returns:
            True if all tests pass, False otherwise
        """
        self.logger.info(f"Validating {code_file.name} against tests...")

        # Run tests
        test_results, errors = await self.code_generator._run_tests(
            test_files, code_file.parent
        )

        passed_count = sum(1 for passed in test_results.values() if passed)
        total_count = len(test_results)

        self.logger.info(f"Test results: {passed_count}/{total_count} passed")

        if errors:
            for error in errors[:5]:  # Show first 5 errors
                self.logger.error(f"  {error}")

        return passed_count == total_count
