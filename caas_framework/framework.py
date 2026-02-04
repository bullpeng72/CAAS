"""
Main CrewAI Framework Class

Single entry point for all framework functionality.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import plugins module to trigger plugin registration
import caas_framework.plugins  # noqa: F401
from caas_framework.methodology.engine import SixPhaseEngine, MethodologyResult
from caas_framework.methodology.golden_data import GoldenDataPipeline
from caas_framework.config.loader import ConfigLoader
from caas_framework.config.settings import FrameworkConfig
from caas_framework.fixing.auto_fixer import AutoFixer, FixResult
from caas_framework.models.specifications import (
    AgentSpecModel,
    ConcretizedRequirement,
    TaskSpecModel,
)
from caas_framework.plugins.base import PluginRegistry, get_plugin_registry
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils.logger import get_logger
from caas_framework.validation.orchestrator import (
    ComprehensiveValidationResult,
    ValidationOrchestrator,
)

logger = get_logger()


@dataclass
class RequirementAnalysisResult:
    """Result from requirement analysis"""

    domain: str
    subdomain: Optional[str]
    summary: str
    features: List[str]
    agents: List[AgentSpecModel]
    tasks: List[TaskSpecModel]
    workflow_type: str
    suggested_tools: List[str]
    complexity: str
    golden_data_available: bool
    validation_result: Optional[Dict[str, Any]]


class CrewAIFramework:
    """
    Main CrewAI Framework

    Provides unified interface for:
    - Project generation from requirements
    - Golden data creation
    - Multi-agent collaboration
    - Code generation with validation
    - Workflow management

    Example:
        >>> framework = CrewAIFramework(
        ...     llm_provider="openai",
        ...     graph_backend="neo4j",
        ...     config=FrameworkConfig(
        ...         validation=ValidationConfig(auto_fix=True)
        ...     )
        ... )
        >>>
        >>> result = await framework.generate_from_requirement(
        ...     requirement="Build a chatbot",
        ...     domain="CONVERSATIONAL_AI"
        ... )
    """

    def __init__(
        self,
        llm_provider: Optional[str] = None,  # Let config determine provider
        graph_backend: Optional[str] = None,  # Let config determine backend
        vectordb_backend: Optional[str] = None,
        config: Optional[FrameworkConfig] = None,
        config_file: Optional[str] = None,
        config_dict: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize framework

        Args:
            llm_provider: LLM provider name
            graph_backend: Graph database backend
            vectordb_backend: Vector database backend (optional)
            config: FrameworkConfig instance
            config_file: Path to YAML config file
            config_dict: Configuration dictionary

        Priority:
            config > config_file > config_dict > defaults
        """
        # Load configuration
        if config:
            self.config = config
        elif config_file:
            self.config = ConfigLoader.from_file(config_file)
        elif config_dict:
            self.config = ConfigLoader.from_dict(config_dict)
        else:
            self.config = ConfigLoader.from_env()

        # Override with explicit parameters
        if llm_provider:
            self.config.llm.provider = llm_provider
        if graph_backend:
            self.config.graph.backend = graph_backend
        if vectordb_backend and self.config.vectordb:
            self.config.vectordb.backend = vectordb_backend

        # Plugin registry
        self.registry: PluginRegistry = get_plugin_registry()

        # Components (initialized lazily)
        self._llm_plugin: Optional[LLMPlugin] = None
        self._graph_client = None
        self._vector_client = None
        self._bmad_engine: Optional[SixPhaseEngine] = None
        self._golden_pipeline: Optional[GoldenDataPipeline] = None
        self._validator: Optional[ValidationOrchestrator] = None
        self._auto_fixer: Optional[AutoFixer] = None
        self._initialized = False

    # Public API properties
    @property
    def llm_plugin(self) -> LLMPlugin:
        """Public accessor for LLM plugin"""
        if not self._initialized:
            raise RuntimeError(
                "Framework not initialized. Call 'await framework.initialize()' first."
            )
        return self._llm_plugin

    @property
    def validation_orchestrator(self):
        """Public accessor for validation orchestrator"""
        if not self._initialized:
            raise RuntimeError(
                "Framework not initialized. Call 'await framework.initialize()' first."
            )
        return self._validator

    @property
    def bmad_engine(self):
        """Public accessor for BMAD engine"""
        if not self._initialized:
            raise RuntimeError(
                "Framework not initialized. Call 'await framework.initialize()' first."
            )
        return self._bmad_engine

    @property
    def golden_pipeline(self):
        """Public accessor for Golden Data pipeline"""
        if not self._initialized:
            raise RuntimeError(
                "Framework not initialized. Call 'await framework.initialize()' first."
            )
        return self._golden_pipeline

    async def initialize(self) -> None:
        """
        Initialize framework components

        - Initialize plugins
        - Connect to databases
        - Load ontology
        - Setup caching
        """
        if self._initialized:
            return

        # 1. Initialize LLM plugin

        llm_config = {
            "model": self.config.llm.model,
            "temperature": self.config.llm.temperature,
            "max_tokens": self.config.llm.max_tokens,
            "api_key": self.config.llm.api_key,
            "api_base": self.config.llm.api_base,
        }

        # Convert enum to string for plugin registry
        provider_name = (
            self.config.llm.provider.value
            if hasattr(self.config.llm.provider, "value")
            else self.config.llm.provider
        )

        self._llm_plugin = await self.registry.initialize_plugin(
            name=provider_name, plugin_type="llm", config=llm_config
        )

        # 2. Initialize graph backend
        try:
            from caas_framework.knowledge.graph.factory import get_graph_client

            self._graph_client = get_graph_client()
            logger.info("Graph backend initialized successfully")
        except Exception as e:
            logger.warning(
                f"Failed to initialize graph backend: {e}. Continuing without graph support."
            )
            self._graph_client = None

        # 3. Initialize vector DB (if configured)
        # TODO: Implement vector DB plugin initialization
        # Vector DB support will be added in future releases
        self._vector_db = None

        # 4. Initialize BMAD engine
        self._bmad_engine = SixPhaseEngine(
            llm_plugin=self._llm_plugin,
            enable_validation=self.config.validation.auto_fix,
            enable_auto_fix=self.config.validation.auto_fix,
            artifact_config=self.config.artifacts,
        )

        # 5. Initialize Golden Data pipeline
        self._golden_pipeline = GoldenDataPipeline(self._llm_plugin)

        self._initialized = True

    async def generate_from_requirement(
        self,
        requirement: str,
        domain: Optional[str] = None,
        golden_data: Optional[Dict[str, Any]] = None,
        deployment_target: str = "docker",
        workflow_type: Optional[str] = None,
        enable_traceability: bool = True,
        enable_completeness_validation: bool = True,
        enable_gap_filling: bool = False,
        plan_mode: bool = False,
        verbosity: str = "normal",
        distributed: bool = False,
        max_workers: Optional[int] = None,
        progress_reporter: Optional[Any] = None,
        enable_critic_pattern: bool = False,
        strict_quality_gates: bool = True,
    ) -> MethodologyResult:
        """
        Generate complete project from natural language requirement

        Args:
            requirement: Natural language requirement
            domain: Domain classification (optional, will be auto-detected)
            golden_data: Pre-existing golden data (optional)
            deployment_target: Deployment target (docker, kubernetes, terraform)
            workflow_type: Workflow process type - "sequential", "hierarchical", or None for auto-selection
            enable_traceability: Enable Phase 2 traceability tracking (default: True)
            enable_completeness_validation: Enable Phase 3 completeness validation (default: True)
            enable_gap_filling: Enable automatic gap filling for missing features (default: False)
            plan_mode: Enable Plan Mode with interactive approval gates (default: False)
            verbosity: Progress verbosity level - quiet, minimal, normal, verbose, debug (default: normal)
            distributed: Enable distributed parallel execution (default: False)
            max_workers: Maximum number of workers for distributed execution (default: CPU count)
            progress_reporter: Custom progress reporter (optional, uses default if None)

        Returns:
            MethodologyResult with all artifacts

        Process:
            1. Phase 0: Golden Data Generation (if not provided)
            2. Phase 1: Discovery (Requirement Analysis) - Hierarchical Feature Extraction
            3. Phase 2: Architecture (System Design) - Traceability Matrix
            4. Phase 3: Design (Agent/Task Design) - Completeness Validation
            5. Phase 4: Development (Spec Generation)
            6. Phase 5: Delivery (Code Generation)
        """
        if not self._initialized:
            await self.initialize()

        # Convert golden_data if provided
        golden_req = None
        if golden_data:
            if isinstance(golden_data, dict):
                golden_req = ConcretizedRequirement(**golden_data)
            else:
                golden_req = golden_data

        # Create customized BMAD engine for this request with plan_mode and verbosity
        from caas_framework.reporting import VerbosityLevel

        # Map verbosity string to enum
        verbosity_map = {
            "quiet": VerbosityLevel.QUIET,
            "minimal": VerbosityLevel.MINIMAL,
            "normal": VerbosityLevel.NORMAL,
            "verbose": VerbosityLevel.VERBOSE,
            "debug": VerbosityLevel.DEBUG,
        }
        verbosity_level = verbosity_map.get(verbosity, VerbosityLevel.NORMAL)

        # Create or use provided progress reporter
        if progress_reporter is None:
            from caas_framework.reporting import ProgressReporter

            progress_reporter = ProgressReporter(verbosity=verbosity_level)

        # Create plan mode instance if requested
        plan_mode_instance = None
        if plan_mode:
            from caas_framework.modes.plan_mode import PlanMode

            plan_mode_instance = PlanMode(auto_approve=False)

        # Create customized BMAD engine for this specific request
        bmad_engine = SixPhaseEngine(
            llm_plugin=self._llm_plugin,
            enable_validation=self.config.validation.enabled,
            enable_auto_fix=self.config.validation.auto_fix,
            use_expert_agents=True,
            progress_reporter=progress_reporter,
            verbosity=verbosity_level,
            artifact_config=self.config.artifacts,
            plan_mode=plan_mode_instance,
            distributed=distributed,
            max_workers=max_workers,
            enable_critic_pattern=enable_critic_pattern,
            strict_quality_gates=strict_quality_gates,
        )

        # Run BMAD Pipeline with Phase 1-3 enhancements
        result = await bmad_engine.run(
            requirement=requirement,
            domain=domain,
            golden_data=golden_req,
            deployment_target=deployment_target,
            workflow_type=workflow_type,
            enable_traceability=enable_traceability,
            enable_completeness_validation=enable_completeness_validation,
            enable_gap_filling=enable_gap_filling,
        )

        return result

    async def _generate_golden_data(
        self, requirement: str, domain: Optional[str] = None
    ) -> ConcretizedRequirement:
        """
        Generate Golden Data from requirement

        Args:
            requirement: Natural language requirement
            domain: Domain hint

        Returns:
            ConcretizedRequirement (Golden Data)
        """
        if not self._initialized:
            await self.initialize()

        return await self._golden_pipeline.generate(requirement, domain)

    async def generate_golden_data(
        self, requirement: str, domain: Optional[str] = None
    ) -> ConcretizedRequirement:
        """
        Public method to generate Golden Data from requirement

        Args:
            requirement: Natural language requirement
            domain: Domain hint (optional)

        Returns:
            ConcretizedRequirement (Golden Data)
        """
        return await self._generate_golden_data(requirement, domain)

    async def analyze_requirement(
        self,
        requirement: str,
        use_golden_data: bool = False,
        domain: Optional[str] = None,
    ) -> RequirementAnalysisResult:
        """
        Analyze requirement and generate initial agent/task design

        Args:
            requirement: Natural language requirement
            use_golden_data: Whether to generate and use golden data
            domain: Domain hint (optional)

        Returns:
            RequirementAnalysisResult with domain, features, agents, tasks, etc.
        """
        if not self._initialized:
            await self.initialize()

        # Generate golden data if requested
        golden_req = None
        if use_golden_data:
            golden_req = await self._generate_golden_data(requirement, domain)

        # Run BMAD pipeline to get agents and tasks
        result = await self._bmad_engine.run(
            requirement=requirement,
            domain=domain,
            golden_data=golden_req,
            deployment_target="docker",
        )

        # Extract features from golden data or requirement analysis
        features = []
        final_domain = domain
        if result.golden_data:
            golden_features = (
                result.golden_data.features if result.golden_data.features else []
            )
            features = [f.name for f in golden_features]
            final_domain = result.golden_data.domain
            summary = result.golden_data.description
        else:
            # Extract from requirement_analysis if available
            final_domain = domain or "GENERAL"
            summary = requirement[:200]

        # Build response
        return RequirementAnalysisResult(
            domain=final_domain,
            subdomain=None,
            summary=summary,
            features=features,
            agents=result.agent_specs,
            tasks=result.task_specs,
            workflow_type=result.golden_data.workflow_type
            if result.golden_data
            else "sequential",
            suggested_tools=[],
            complexity="medium",
            golden_data_available=result.golden_data is not None,
            validation_result=None,
        )

    async def generate_agents_and_tasks(
        self, analysis_result: Dict[str, Any], customize: bool = False
    ) -> tuple[List[AgentSpecModel], List[TaskSpecModel]]:
        """
        Generate agents and tasks from analysis result

        Args:
            analysis_result: Result from analyze_requirement
            customize: Whether to apply customization

        Returns:
            Tuple of (agents, tasks)
        """
        if not self._initialized:
            await self.initialize()

        # If analysis already has agents and tasks, return them
        if "agents" in analysis_result and "tasks" in analysis_result:
            agents = analysis_result["agents"]
            tasks = analysis_result["tasks"]

            # Convert to models if they're dicts
            if agents and isinstance(agents[0], dict):
                agents = [AgentSpecModel(**a) for a in agents]
            if tasks and isinstance(tasks[0], dict):
                tasks = [TaskSpecModel(**t) for t in tasks]

            return agents, tasks

        # Otherwise, run BMAD to generate agents/tasks
        domain = analysis_result.get("domain")
        summary = analysis_result.get("summary", "")

        result = await self._bmad_engine.run(
            requirement=summary, domain=domain, deployment_target="docker"
        )

        return result.agent_specs, result.task_specs

    async def validate_design(
        self,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        golden_data: Optional[Dict[str, Any]] = None,
    ) -> ComprehensiveValidationResult:
        """
        Validate agent/task design

        Args:
            agents: Agent specifications
            tasks: Task specifications
            golden_data: Golden data for validation

        Returns:
            ComprehensiveValidationResult
        """
        if not self._initialized:
            await self.initialize()

        # Initialize validator if needed
        if not self._validator:
            golden_req = None
            if golden_data:
                # Convert dict to ConcretizedRequirement if needed
                if isinstance(golden_data, dict):
                    golden_req = ConcretizedRequirement(**golden_data)
                else:
                    golden_req = golden_data

            self._validator = ValidationOrchestrator(
                golden_data=golden_req,
                enabled_tools=list(self.registry.list_available_plugins()),
            )

        # Convert to AgentSpecModel/TaskSpecModel if needed
        agent_models = [
            AgentSpecModel(**a) if isinstance(a, dict) else a for a in agents
        ]
        task_models = [TaskSpecModel(**t) if isinstance(t, dict) else t for t in tasks]

        # Run validation
        result = self._validator.validate_design(
            agents=agent_models,
            tasks=task_models,
            validate_golden=golden_data is not None,
            validate_ontology=True,
            validate_dependencies=True,
        )

        return result

    async def auto_fix(
        self,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        validation_result: ComprehensiveValidationResult,
        golden_data: Optional[Dict[str, Any]] = None,
        max_iterations: int = 3,
    ) -> FixResult:
        """
        Auto-fix validation issues

        Args:
            agents: Agent specifications
            tasks: Task specifications
            validation_result: Comprehensive validation result
            golden_data: Golden data for fixing
            max_iterations: Maximum fix iterations (self-reflection loop)

        Returns:
            FixResult with fixed agents/tasks
        """
        if not self._initialized:
            await self.initialize()

        # Initialize auto-fixer if needed
        if not self._auto_fixer and golden_data:
            golden_req = None
            if isinstance(golden_data, dict):
                golden_req = ConcretizedRequirement(**golden_data)
            else:
                golden_req = golden_data

            self._auto_fixer = AutoFixer(
                golden_data=golden_req, llm_plugin=self._llm_plugin
            )

        if not self._auto_fixer:
            return FixResult(
                success=False,
                fixed_output={"agents": agents, "tasks": tasks},
                fixes_applied=[],
                errors=["No golden data provided for fixing"],
            )

        # Apply fixes if Golden Data validation found issues
        if (
            validation_result.golden_result
            and validation_result.golden_result.needs_fixing
        ):
            # Convert to models
            agent_models = [
                AgentSpecModel(**a) if isinstance(a, dict) else a for a in agents
            ]
            task_models = [
                TaskSpecModel(**t) if isinstance(t, dict) else t for t in tasks
            ]

            # Apply fixes
            fix_result = self._auto_fixer.fix_design(
                agent_specs=agent_models,
                task_specs=task_models,
                validation_report=validation_result.golden_result,
                max_iterations=max_iterations,
            )

            return fix_result

        # No fixing needed
        return FixResult(
            success=True,
            fixed_output={"agents": agents, "tasks": tasks},
            fixes_applied=[],
            errors=[],
        )

    async def generate_code(
        self,
        spec: Dict[str, Any],
        output_dir: Optional[str] = None,
        deployment_target: str = "docker",
        tdd_mode: bool = False,
    ) -> "CodeGenerationResult":
        """
        Generate production-ready code from spec

        Args:
            spec: CrewAI spec (must contain agents, tasks, and optionally golden_data)
            output_dir: Output directory (optional, for file writing)
            deployment_target: Deployment target
            tdd_mode: Enable Test-First Code Generation (TDD approach)

        Returns:
            CodeGenerationResult
        """
        if not self._initialized:
            await self.initialize()

        from caas_framework.codegen.engine import CodeGenerationEngine
        from caas_framework.models.specifications import (
            AgentSpecModel,
            ConcretizedRequirement,
            TaskSpecModel,
        )

        # Parse spec
        agents = [AgentSpecModel(**a) for a in spec.get("agents", [])]
        tasks = [TaskSpecModel(**t) for t in spec.get("tasks", [])]

        # Get golden_data if provided
        golden_data_dict = spec.get("golden_data")
        if golden_data_dict:
            golden_data = ConcretizedRequirement(**golden_data_dict)
        else:
            # Create minimal golden data from spec
            golden_data = ConcretizedRequirement(
                project_name=spec.get("project_name", "my_crew_project"),
                domain=spec.get("domain", "GENERAL"),
                description=spec.get("description", "Auto-generated CrewAI project"),
                features=[],
                data_models=[],
            )

        # Initialize code generation engine with LLM plugin
        code_gen_engine = CodeGenerationEngine(
            llm_plugin=self._llm_plugin,
            enable_error_handling=True,
            enable_logging=True,
            enable_tests=True,
            enable_deployment=True,
            enable_llm_generation=True,
            tdd_mode=tdd_mode,  # Enable TDD if requested
        )

        # Generate production-ready code
        gen_result = await code_gen_engine.generate(
            golden_data=golden_data,
            agents=agents,
            tasks=tasks,
            deployment_target=deployment_target,
            tdd_mode=tdd_mode,  # Pass TDD mode to generation
        )

        # Write files if output_dir specified
        if output_dir and gen_result.success:
            from pathlib import Path

            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            for file_path, content in gen_result.files.items():
                file_full_path = output_path / file_path
                file_full_path.parent.mkdir(parents=True, exist_ok=True)
                file_full_path.write_text(content)

        return gen_result

    async def close(self) -> None:
        """Close framework and cleanup resources"""
        if self.registry:
            await self.registry.close_all()

        self._initialized = False

    def __repr__(self) -> str:
        return (
            f"<CrewAIFramework("
            f"llm={self.config.llm.provider}, "
            f"graph={self.config.graph.backend}, "
            f"initialized={self._initialized})>"
        )

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


class GenerationResult:
    """Result of project generation"""

    def __init__(
        self,
        golden_data: Dict[str, Any],
        requirement_analysis: Any,
        architecture_design: Any,
        agent_design: Any,
        spec: Any,
        generated_code: Any,
        qa_report: Any,
        validation_reports: List[Any],
    ):
        self.golden_data = golden_data
        self.requirement_analysis = requirement_analysis
        self.architecture_design = architecture_design
        self.agent_design = agent_design
        self.spec = spec
        self.generated_code = generated_code
        self.qa_report = qa_report
        self.validation_reports = validation_reports

    def save_to_directory(self, output_dir: str) -> None:
        """Save all artifacts to directory"""
        import json
        from datetime import datetime

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save golden data
        if self.golden_data:
            golden_file = output_path / "golden_data.json"
            with open(golden_file, "w", encoding="utf-8") as f:
                json.dump(self.golden_data, f, indent=2, ensure_ascii=False)

        # Save requirement analysis
        if self.requirement_analysis:
            req_file = output_path / "requirement_analysis.json"
            with open(req_file, "w", encoding="utf-8") as f:
                json.dump(self.requirement_analysis, f, indent=2, ensure_ascii=False)

        # Save architecture design
        if self.architecture_design:
            arch_file = output_path / "architecture_design.json"
            with open(arch_file, "w", encoding="utf-8") as f:
                json.dump(self.architecture_design, f, indent=2, ensure_ascii=False)

        # Save agent design
        if self.agent_design:
            agent_file = output_path / "agent_design.json"
            with open(agent_file, "w", encoding="utf-8") as f:
                json.dump(self.agent_design, f, indent=2, ensure_ascii=False)

        # Save spec (YAML format)
        if self.spec:
            spec_file = output_path / "spec.yaml"
            import yaml

            with open(spec_file, "w", encoding="utf-8") as f:
                yaml.dump(self.spec, f, default_flow_style=False, allow_unicode=True)

        # Save generated code files
        if self.generated_code and hasattr(self.generated_code, "files"):
            code_dir = output_path / "generated_code"
            code_dir.mkdir(exist_ok=True)

            for file_path, content in self.generated_code.files.items():
                file_full_path = code_dir / file_path
                file_full_path.parent.mkdir(parents=True, exist_ok=True)

                with open(file_full_path, "w", encoding="utf-8") as f:
                    f.write(content)

        # Save QA report
        if self.qa_report:
            qa_file = output_path / "qa_report.json"
            with open(qa_file, "w", encoding="utf-8") as f:
                json.dump(self.qa_report, f, indent=2, ensure_ascii=False)

        # Save validation reports
        if self.validation_reports:
            validation_dir = output_path / "validation_reports"
            validation_dir.mkdir(exist_ok=True)

            for i, report in enumerate(self.validation_reports):
                report_file = validation_dir / f"validation_{i+1}.json"
                with open(report_file, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)

        # Create manifest
        manifest = {
            "generated_at": datetime.now().isoformat(),
            "artifacts": {
                "golden_data": bool(self.golden_data),
                "requirement_analysis": bool(self.requirement_analysis),
                "architecture_design": bool(self.architecture_design),
                "agent_design": bool(self.agent_design),
                "spec": bool(self.spec),
                "generated_code": bool(self.generated_code),
                "qa_report": bool(self.qa_report),
                "validation_reports": (
                    len(self.validation_reports) if self.validation_reports else 0
                ),
            },
        }

        manifest_file = output_path / "manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Artifacts saved to {output_path}")


class CodeGenerationResult:
    """Code generation result"""

    # TODO: Implement
