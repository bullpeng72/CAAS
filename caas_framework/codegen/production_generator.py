"""
Production Code Generator

Comprehensive code generator that produces 100% production-ready code with:
- Error handling (retry logic, circuit breakers)
- Structured logging (JSON format)
- Comprehensive tests (80%+ coverage goal)
- Documentation (MkDocs/Sphinx)
- CI/CD pipelines (GitHub Actions/GitLab CI)
- Deployment files (Docker/K8s)
- Execution validation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from caas_framework.codegen.cicd_generator import CICDConfig, CICDGenerator
from caas_framework.codegen.doc_generator import DocumentationConfig, DocumentationGenerator
from caas_framework.codegen.engine import CodeGenerationEngine
from caas_framework.codegen.execution_validator import ExecutionValidationResult, ExecutionValidator
from caas_framework.codegen.injectors import ErrorHandlingInjector, LoggingInjector
from caas_framework.codegen.test_generator import TestGenerator
from caas_framework.models.specifications import (
    AgentSpecModel,
    ConcretizedRequirement,
    TaskSpecModel,
)


@dataclass
class ProductionConfig:
    """Production code generation configuration"""

    # Error handling
    enable_error_handling: bool = True
    enable_retry_logic: bool = True
    max_retries: int = 3
    enable_circuit_breaker: bool = True

    # Logging
    enable_logging: bool = True
    use_structured_logging: bool = True  # JSON format
    log_performance: bool = True

    # Testing
    enable_tests: bool = True
    target_coverage: float = 0.8  # 80% coverage goal
    generate_unit_tests: bool = True
    generate_integration_tests: bool = True

    # Documentation
    enable_docs: bool = True
    docs_format: str = "mkdocs"  # "mkdocs" or "sphinx"

    # CI/CD
    enable_cicd: bool = True
    cicd_platform: str = "github_actions"  # "github_actions", "gitlab_ci", "jenkins"
    run_linting: bool = True

    # Deployment
    enable_deployment: bool = True
    deployment_target: str = "docker"  # "docker", "kubernetes", "terraform"

    # Validation
    enable_validation: bool = True
    validate_syntax: bool = True
    validate_imports: bool = True
    validate_types: bool = True
    enable_dry_run: bool = False  # Disabled by default for safety


@dataclass
class ProductionCodeResult:
    """Production code generation result"""

    success: bool
    files: Dict[str, str] = field(default_factory=dict)
    validation_result: Optional[ExecutionValidationResult] = None
    error_handling_applied: bool = False
    logging_applied: bool = False
    tests_generated: int = 0
    docs_generated: bool = False
    cicd_generated: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ProductionCodeGenerator:
    """
    Production Code Generator

    Generates complete, production-ready projects with all best practices:
    - Comprehensive error handling with retry logic
    - Structured logging (JSON format)
    - Test suite with 80%+ coverage goal
    - Full documentation
    - CI/CD pipelines
    - Deployment configurations
    - Code validation
    """

    def __init__(self, config: Optional[ProductionConfig] = None):
        """
        Initialize production code generator.

        Args:
            config: Production generation configuration
        """
        self.config = config or ProductionConfig()

        # Initialize components
        self.base_generator = CodeGenerationEngine(
            enable_error_handling=self.config.enable_error_handling,
            enable_logging=self.config.enable_logging,
            enable_tests=self.config.enable_tests,
            enable_deployment=self.config.enable_deployment,
        )

        # Enhanced injectors
        self.error_injector = (
            ErrorHandlingInjector(
                enable_retry=self.config.enable_retry_logic, max_retries=self.config.max_retries
            )
            if self.config.enable_error_handling
            else None
        )

        self.logging_injector = (
            LoggingInjector(use_json_format=self.config.use_structured_logging)
            if self.config.enable_logging
            else None
        )

        # Additional generators
        self.doc_generator = DocumentationGenerator() if self.config.enable_docs else None
        self.cicd_generator = CICDGenerator() if self.config.enable_cicd else None
        self.validator = (
            ExecutionValidator(
                enable_syntax_check=self.config.validate_syntax,
                enable_import_check=self.config.validate_imports,
                enable_type_check=self.config.validate_types,
                enable_dry_run=self.config.enable_dry_run,
            )
            if self.config.enable_validation
            else None
        )

    def generate(
        self,
        golden_data: ConcretizedRequirement,
        agents: List[AgentSpecModel],
        tasks: List[TaskSpecModel],
        deployment_target: Optional[str] = None,
    ) -> ProductionCodeResult:
        """
        Generate complete production-ready project.

        Args:
            golden_data: Golden Data
            agents: Agent specifications
            tasks: Task specifications
            deployment_target: Deployment target override

        Returns:
            ProductionCodeResult: Complete generation result
        """
        result = ProductionCodeResult(success=True)

        try:
            # Step 1: Generate base project
            base_result = self.base_generator.generate(
                golden_data=golden_data,
                agents=agents,
                tasks=tasks,
                deployment_target=deployment_target or self.config.deployment_target,
            )

            if not base_result.success:
                result.success = False
                result.errors.extend(base_result.errors)
                return result

            result.files.update(base_result.files)

            # Step 2: Enhanced error handling injection
            if self.config.enable_error_handling and self.error_injector:
                self._inject_enhanced_error_handling(result.files)
                result.error_handling_applied = True

            # Step 3: Structured logging injection
            if self.config.enable_logging and self.logging_injector:
                self._inject_structured_logging(result.files)
                result.logging_applied = True

            # Step 4: Generate comprehensive tests
            if self.config.enable_tests:
                test_files = self._generate_comprehensive_tests(agents, tasks)
                result.files.update(test_files)
                result.tests_generated = len(test_files)

            # Step 5: Generate documentation
            if self.config.enable_docs and self.doc_generator:
                doc_config = DocumentationConfig(
                    format=self.config.docs_format,
                    project_name=golden_data.project_name or "My Project",
                    include_api_docs=True,
                    include_architecture_diagram=True,
                )
                doc_files = self.doc_generator.generate_all(golden_data, agents, tasks, doc_config)
                result.files.update(doc_files)
                result.docs_generated = True

            # Step 6: Generate CI/CD pipelines
            if self.config.enable_cicd and self.cicd_generator:
                cicd_config = CICDConfig(
                    platform=self.config.cicd_platform,
                    run_tests=self.config.enable_tests,
                    run_linting=self.config.run_linting,
                    build_docker=self.config.enable_deployment,
                    deploy_enabled=False,  # Deployment requires manual setup
                )
                cicd_files = self.cicd_generator.generate_all(cicd_config)
                result.files.update(cicd_files)
                result.cicd_generated = True

            # Step 7: Add utility files
            self._add_utility_files(result.files)

            # Step 8: Validate generated code
            if self.config.enable_validation and self.validator:
                validation_result = self.validator.validate(result.files)
                result.validation_result = validation_result

                if not validation_result.is_executable:
                    result.warnings.append(
                        f"Code validation found {validation_result.error_count} errors"
                    )

                    # Log validation issues
                    for issue in validation_result.issues[:5]:  # First 5 issues
                        result.warnings.append(f"[{issue.severity}] {issue.file}: {issue.message}")

            result.success = True

        except Exception as e:
            result.success = False
            result.errors.append(f"Generation failed: {str(e)}")

        return result

    def _inject_enhanced_error_handling(self, files: Dict[str, str]) -> None:
        """Inject enhanced error handling with retry logic"""
        if not self.error_injector:
            return

        for path, content in files.items():
            if path.endswith(".py") and not path.startswith("tests/"):
                try:
                    # Inject retry logic
                    if self.config.enable_retry_logic:
                        content = self.error_injector.inject_retry_logic(content)

                    # Inject standard error handling
                    content = self.error_injector.inject(content)

                    files[path] = content
                except Exception:
                    pass  # Keep original if injection fails

        # Add error handling utilities
        if self.config.enable_circuit_breaker:
            files["src/utils/error_handling.py"] = (
                self.error_injector.generate_error_handling_utils()
            )

    def _inject_structured_logging(self, files: Dict[str, str]) -> None:
        """Inject structured logging (JSON format)"""
        if not self.logging_injector:
            return

        for path, content in files.items():
            if path.endswith(".py") and not path.startswith("tests/"):
                try:
                    content = self.logging_injector.inject(
                        content, logger_name=path.replace("/", ".").replace(".py", "")
                    )
                    files[path] = content
                except Exception:
                    pass

        # Add logging utilities
        files["src/utils/logging.py"] = self.logging_injector.generate_structured_logging_utils()

    def _generate_comprehensive_tests(
        self, agents: List[AgentSpecModel], tasks: List[TaskSpecModel]
    ) -> Dict[str, str]:
        """Generate comprehensive test suite with 80%+ coverage goal"""
        test_gen = TestGenerator()

        files = test_gen.generate_all_tests(agents=agents, tasks=tasks, api_endpoints=[])

        # Add pytest.ini for coverage configuration
        files[
            "pytest.ini"
        ] = f"""[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts =
    -v
    --strict-markers
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-report=xml
    --cov-fail-under={int(self.config.target_coverage * 100)}
"""

        # Add .coveragerc
        files[
            ".coveragerc"
        ] = """[run]
source = src
omit =
    tests/*
    */__init__.py
    */venv/*
    */.venv/*

[report]
precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov
"""

        return files

    def _add_utility_files(self, files: Dict[str, str]) -> None:
        """Add utility and configuration files"""

        # requirements-dev.txt
        files[
            "requirements-dev.txt"
        ] = """# Development dependencies
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-asyncio>=0.21.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0
isort>=5.12.0
"""

        # Makefile for common tasks
        files[
            "Makefile"
        ] = """
.PHONY: install test lint format clean

install:
\tpip install -r requirements.txt
\tpip install -r requirements-dev.txt

test:
\tpytest tests/ -v --cov=src --cov-report=html

lint:
\tflake8 src/
\tmypy src/

format:
\tblack src/ tests/
\tisort src/ tests/

clean:
\trm -rf __pycache__ .pytest_cache .coverage htmlcov
\tfind . -type d -name __pycache__ -exec rm -rf {} +
\tfind . -type f -name "*.pyc" -delete
"""

        # .env.example
        files[
            ".env.example"
        ] = """# Environment variables
OPENAI_API_KEY=your_api_key_here
LOG_LEVEL=INFO
ENVIRONMENT=development
"""
