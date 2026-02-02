"""
BMAD Engine

Breakthrough Method for Agile AI-driven Development
6-Phase development engine with expert agent collaboration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from caas_framework.agents.collaboration import ExpertAgentCollaboration
from caas_framework.automation import BootstrapResult, ProjectBootstrapper
from caas_framework.bmad.completeness_validator import CompletenessReport, CompletenessValidator
from caas_framework.bmad.gap_filler import GapFiller, GapFillingResult
from caas_framework.bmad.golden_data import GoldenDataPipeline
from caas_framework.bmad.traceability import TraceabilityMatrix
from caas_framework.codegen.engine import CodeGenerationEngine
from caas_framework.config.settings import LLMConstants
from caas_framework.events import Event, PhaseEvent, get_global_event_bus
from caas_framework.fixing.auto_fixer import AutoFixer
from caas_framework.models.specifications import (
    AgentSpecModel,
    ConcretizedRequirement,
    TaskSpecModel,
)
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.reporting import ProgressReporter, ProgressReporterProtocol, VerbosityLevel
from caas_framework.utils import ResponseParser
from caas_framework.utils.workflow_selector import get_workflow_recommendation
from caas_framework.validation.orchestrator import ValidationOrchestrator


class BMADPhase(str, Enum):
    """BMAD 6-Phase"""

    CONCRETIZATION = "concretization"  # Phase 0: Golden Data
    DISCOVERY = "discovery"  # Phase 1: Requirement Analysis
    ARCHITECTURE = "architecture"  # Phase 2: System Design
    DESIGN = "design"  # Phase 3: Agent/Task Design
    DEVELOPMENT = "development"  # Phase 4: Spec Generation
    DELIVERY = "delivery"  # Phase 5: Code Generation


@dataclass
class BMADResult:
    """BMAD execution result"""

    # Phase 0: Golden Data
    golden_data: Optional[ConcretizedRequirement] = None

    # Phase 1: Discovery
    requirement_analysis: Optional[Dict[str, Any]] = None

    # Phase 2: Architecture
    architecture_design: Optional[Dict[str, Any]] = None

    # Phase 3: Design
    agent_specs: List[AgentSpecModel] = field(default_factory=list)
    task_specs: List[TaskSpecModel] = field(default_factory=list)

    # Phase 4: Development
    spec_yaml: Optional[str] = None

    # Phase 5: Delivery
    generated_code: Optional[Dict[str, str]] = None
    boundaries_violations: List[str] = field(default_factory=list)
    quality_evaluation: Optional[Dict[str, Any]] = None
    security_report: Optional[Dict[str, Any]] = None

    # Traceability (Phase 2 Enhancement)
    traceability_matrix: Optional[TraceabilityMatrix] = None
    traceability_report: Optional[str] = None
    coverage_analysis: Optional[Dict[str, Any]] = None

    # Completeness Validation (Phase 3 Enhancement)
    completeness_report: Optional[CompletenessReport] = None
    completeness_text_report: Optional[str] = None
    gap_filling_result: Optional[GapFillingResult] = None

    # Validation results
    validation_reports: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    phases_completed: List[BMADPhase] = field(default_factory=list)
    total_duration: float = 0.0
    success: bool = True
    errors: List[str] = field(default_factory=list)

    # Bootstrap (optional)
    bootstrap_result: Optional[BootstrapResult] = None


class BMADEngine:
    """
    BMAD Engine

    Orchestrates 6-phase AI-driven development process:
    0. Concretization: Generate Golden Data
    1. Discovery: Analyze requirements
    2. Architecture: Design system architecture
    3. Design: Design agents and tasks
    4. Development: Generate spec
    5. Delivery: Generate production code
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        enable_validation: bool = True,
        enable_auto_fix: bool = True,
        use_expert_agents: bool = True,
        progress_reporter: Optional[ProgressReporterProtocol] = None,
        verbosity: VerbosityLevel = VerbosityLevel.NORMAL,
        artifact_config: Optional[Any] = None,
        plan_mode: Optional[Any] = None,
        distributed: bool = False,
        max_workers: Optional[int] = None,
    ):
        """
        Initialize BMAD Engine.

        Args:
            llm_plugin: LLM plugin for generation
            enable_validation: Enable Golden Data validation
            enable_auto_fix: Enable automatic fixing
            use_expert_agents: Use Expert Agent Collaboration (recommended)
            progress_reporter: Optional progress reporter (Protocol-based for UI independence)
            verbosity: Verbosity level for progress reporting
            artifact_config: Optional artifact generation configuration
            plan_mode: Optional Plan Mode instance for interactive approval gates
            distributed: Enable distributed parallel execution (for large projects)
            max_workers: Maximum number of workers for distributed execution
        """
        self.llm = llm_plugin
        self.enable_validation = enable_validation
        self.enable_auto_fix = enable_auto_fix
        self.use_expert_agents = use_expert_agents
        self.plan_mode = plan_mode
        self.distributed = distributed
        self.max_workers = max_workers

        # Event-Driven Architecture
        self.event_bus = get_global_event_bus()

        # Progress reporting
        self.reporter = progress_reporter or ProgressReporter(verbosity=verbosity)

        # Distributed executor (initialized if distributed mode enabled)
        self.distributed_executor: Optional[Any] = None
        if distributed:
            from caas_framework.execution.distributed_executor import (
                DistributedPhaseExecutor,
                ExecutionStrategy,
            )

            self.distributed_executor = DistributedPhaseExecutor(
                strategy=ExecutionStrategy.AUTO, max_workers=max_workers, enable_monitoring=True
            )
            self.reporter.info(
                f"🚀 Distributed execution enabled with {max_workers or 'auto'} workers"
            )

        # Pipelines
        self.golden_pipeline = GoldenDataPipeline(llm_plugin)

        # Validator and fixer (initialized per run)
        self.validator: Optional[ValidationOrchestrator] = None
        self.fixer: Optional[AutoFixer] = None

        # Expert agent collaboration (initialized per run)
        self.expert_collaboration: Optional[ExpertAgentCollaboration] = None

        # Artifact generator (optional)
        self.artifact_generator: Optional[Any] = None
        if artifact_config and getattr(artifact_config, "enabled", False):
            try:
                from caas_framework.artifacts import ArtifactGenerator
                from caas_framework.models import ArtifactGenerationConfig

                # Create ArtifactGenerationConfig from artifact_config
                gen_config = ArtifactGenerationConfig(
                    enabled=True,
                    output_directory=getattr(artifact_config, "output_dir", "./artifacts"),
                    output_format=getattr(artifact_config, "output_format", "markdown"),
                    generate_project_proposal=True,
                    generate_requirements_spec=True,
                    generate_architecture_design=True,
                    generate_data_design=True,
                    generate_agent_design=True,
                    generate_api_design=False,
                    generate_test_plan=False,
                    generate_test_report=False,
                    generate_code_review=False,
                    generate_deployment_guide=False,
                )

                self.artifact_generator = ArtifactGenerator(config=gen_config)
                self.reporter.info("📄 Artifact generation enabled")
            except ImportError as e:
                self.reporter.warning(
                    f"⚠️  Artifact generation requested but could not be loaded: {e}"
                )

    async def run(
        self,
        requirement: str,
        domain: Optional[str] = None,
        golden_data: Optional[ConcretizedRequirement] = None,
        deployment_target: str = "docker",
        workflow_type: Optional[str] = None,
        enable_traceability: bool = True,
        enable_completeness_validation: bool = True,
        enable_gap_filling: bool = False,
        bootstrap_project: bool = False,
        project_name: Optional[str] = None,
        bootstrap_dir: Optional[Path] = None,
    ) -> BMADResult:
        """
        Run complete BMAD pipeline.

        Args:
            requirement: Natural language requirement
            domain: Optional domain hint
            golden_data: Optional pre-existing Golden Data
            deployment_target: Deployment target
            workflow_type: Workflow process type - "sequential", "hierarchical", or None for auto-selection
            enable_traceability: Enable feature-to-code traceability tracking (default: True)
            enable_completeness_validation: Enable completeness validation (Phase 3) (default: True)
            enable_gap_filling: Enable automatic gap filling for missing features (default: False)
            bootstrap_project: Whether to bootstrap a complete project directory (default: False)
            project_name: Name for the bootstrapped project (required if bootstrap_project=True)
            bootstrap_dir: Directory to create project in (default: current directory)

        Returns:
            BMADResult with all artifacts and optional bootstrap result

        Code Generation Path Selection:
            The BMAD Engine supports two code generation paths:

            1. Expert Agent Collaboration (use_expert_agents=True, DEFAULT):
               BMADEngine.run()
                 → ExpertAgentCollaboration.collaborate()
                 → CodeGeneratorAgent._do_work() (Phase 5: Delivery)
                 → CodeGeneratorAgent._generate_tools_file_fallback()
                 → tool_utils.generate_fallback_tools_code()
                 Files generated: files["tools.py"]

            2. Legacy LLM-based Generation (use_expert_agents=False):
               BMADEngine.run()
                 → BMADEngine._phase_5_delivery()
                 → CodeGenerationEngine.generate()
                 → LLMCodeGenerator.generate_custom_tools()
                 → (on LLM failure) LLMCodeGenerator._generate_fallback_tools()
                 → tool_utils.generate_fallback_tools_code()
                 Files generated: files["src/tools.py"]

            Note: Both paths converge on tool_utils.generate_fallback_tools_code()
            for consistent stub tool generation when LLM-based generation is not used.
        """
        start_time = datetime.now()
        result = BMADResult()

        # Initialize traceability matrix (Phase 2 enhancement)
        traceability = TraceabilityMatrix() if enable_traceability else None
        result.traceability_matrix = traceability

        # Start workflow reporting
        self.reporter.start_workflow(workflow_name="BMAD AI-Driven Development", total_phases=6)

        # Publish workflow started event
        self.event_bus.publish(
            Event(
                type=PhaseEvent.SYSTEM_READY,
                data={
                    "workflow": "BMAD",
                    "total_phases": 6,
                    "use_expert_agents": self.use_expert_agents,
                    "enable_validation": self.enable_validation,
                },
                source="BMADEngine",
            )
        )

        try:
            # Phase 0: Concretization (Golden Data)
            self.reporter.start_phase(
                phase_name="Phase 0: Concretization",
                agent_name="Golden Data Pipeline",
                description="Generating structured requirements and Golden Data",
            )

            if golden_data:
                result.golden_data = golden_data
                self.reporter.info("Using pre-existing Golden Data")
            else:
                result.golden_data = await self._phase_0_concretization(requirement, domain)

            self.reporter.complete_phase(
                phase_name="Phase 0: Concretization",
                duration=(datetime.now() - start_time).total_seconds(),
                success=True,
            )
            result.phases_completed.append(BMADPhase.CONCRETIZATION)

            # Generate artifacts for Phase 0
            await self._generate_artifact("PROJECT_PROPOSAL", result, "Phase 0", requirement)

            # Register features in traceability matrix (Phase 2 enhancement)
            if traceability and result.golden_data:
                traceability.register_features(result.golden_data.features)
                self.reporter.info(
                    f"📊 Registered {len(result.golden_data.features)} features for traceability"
                )

            # Use Expert Agent Collaboration if enabled
            if self.use_expert_agents:
                self.reporter.info("🤖 Using Expert Agent Collaboration")

                # Initialize expert collaboration
                self.expert_collaboration = ExpertAgentCollaboration(
                    llm_plugin=self.llm,
                    golden_data=result.golden_data,
                    max_feedback_loops=3 if self.enable_auto_fix else 0,
                    enable_validation=self.enable_validation,
                    progress_reporter=self.reporter,
                    plan_mode=self.plan_mode,
                    event_bus=self.event_bus,  # Pass event bus for event-driven architecture
                    enable_distributed=self.distributed,  # Enable distributed execution if configured
                    max_workers=self.max_workers,  # Pass max workers for parallel execution
                )

                # Run collaboration
                collab_result = await self.expert_collaboration.collaborate(requirement)

                # Extract results from collaboration
                if collab_result.success:
                    ctx = collab_result.context

                    result.requirement_analysis = ctx.requirement_analysis
                    result.architecture_design = ctx.architecture_design

                    if ctx.agent_task_design:
                        result.agent_specs = ctx.agent_task_design.get("agents", [])
                        result.task_specs = ctx.agent_task_design.get("tasks", [])

                        # Register tasks in traceability (Phase 2 enhancement)
                        if traceability and result.golden_data:
                            self._register_tasks_in_traceability(
                                traceability, result.task_specs, result.golden_data.features
                            )
                            self.reporter.info(
                                f"📊 Registered {len(result.task_specs)} tasks in traceability matrix"
                            )

                    result.generated_code = ctx.code_artifacts
                    result.phases_completed = ctx.phases_completed

                    # Extract metadata from generated code (if present)
                    if isinstance(result.generated_code, dict):
                        # Extract boundaries violations
                        if "_boundaries_violations" in result.generated_code:
                            result.boundaries_violations = result.generated_code.pop(
                                "_boundaries_violations"
                            )
                            self.reporter.warning(
                                f"⚠️  {len(result.boundaries_violations)} security boundary violations detected"
                            )

                        # Extract quality evaluation
                        if "_quality_evaluation" in result.generated_code:
                            result.quality_evaluation = result.generated_code.pop(
                                "_quality_evaluation"
                            )
                            if result.quality_evaluation:
                                score = result.quality_evaluation.get("overall_score", 0)
                                passed = result.quality_evaluation.get("passed", False)
                                if passed:
                                    self.reporter.info(f"✅ Code quality score: {score:.1f}/10")
                                else:
                                    self.reporter.warning(
                                        f"⚠️  Code quality score: {score:.1f}/10 (below threshold)"
                                    )

                    # Convert to BMAD phases
                    result.phases_completed = [BMADPhase.CONCRETIZATION] + [
                        self._agent_phase_to_bmad_phase(p) for p in ctx.phases_completed
                    ]

                    # Generate spec YAML from agents/tasks
                    if result.agent_specs and result.task_specs:
                        result.spec_yaml = await self._phase_4_development(
                            result.agent_specs, result.task_specs, result.golden_data
                        )

                    # Register code in traceability (Phase 2 enhancement)
                    if (
                        traceability
                        and result.generated_code
                        and result.task_specs
                        and result.golden_data
                    ):
                        self._register_code_in_traceability(
                            traceability,
                            result.generated_code,
                            result.task_specs,
                            result.golden_data.features,
                        )
                        self.reporter.info(
                            f"📊 Registered {len(result.generated_code)} code files in traceability matrix"
                        )

                    # Generate artifacts for all phases (Expert Agent path)
                    if result.requirement_analysis:
                        await self._generate_artifact("\1", result, "\2", requirement)
                    if result.architecture_design:
                        await self._generate_artifact("\1", result, "\2", requirement)
                        await self._generate_artifact("\1", result, "\2", requirement)
                    if result.agent_specs and result.task_specs:
                        await self._generate_artifact("\1", result, "\2", requirement)
                        await self._generate_artifact("\1", result, "\2", requirement)
                    if result.generated_code:
                        await self._generate_artifact("\1", result, "\2", requirement)
                        await self._generate_artifact("\1", result, "\2", requirement)
                        await self._generate_artifact("\1", result, "\2", requirement)

                    # Quality Validation: Syntax/Import checks (Phase 5 Post-Generation)
                    if result.generated_code:
                        await self._run_quality_validation(result)

                    # Security Scanning: Vulnerability/Secret detection (Phase 5 Post-Generation)
                    if result.generated_code:
                        await self._run_security_scan(result)

                    # Phase 3 Enhancement: Completeness Validation (for expert agent path)
                    if (
                        enable_completeness_validation
                        and result.generated_code
                        and result.golden_data
                    ):
                        await self._run_completeness_validation(
                            result, traceability, enable_gap_filling
                        )

                else:
                    result.errors.extend(collab_result.errors)
                    result.success = False

            else:
                # Legacy mode: Simple LLM-based generation without expert agents
                self.reporter.warning("⚠️  Using legacy mode (without expert agents)")

                # Initialize validator and fixer
                if self.enable_validation:
                    self.validator = ValidationOrchestrator(golden_data=result.golden_data)
                if self.enable_auto_fix:
                    self.fixer = AutoFixer(golden_data=result.golden_data, llm_plugin=self.llm)

                # Phase 1: Discovery
                phase_start = datetime.now()
                self.reporter.start_phase(
                    phase_name="Phase 1: Discovery",
                    agent_name="LLM Analyzer",
                    description="Analyzing requirements",
                )
                result.requirement_analysis = await self._phase_1_discovery(
                    requirement, result.golden_data
                )
                self.reporter.complete_phase(
                    phase_name="Phase 1: Discovery",
                    duration=(datetime.now() - phase_start).total_seconds(),
                    success=True,
                )
                result.phases_completed.append(BMADPhase.DISCOVERY)

                # Generate artifacts for Phase 1
                await self._generate_artifact("\1", result, "\2", requirement)

                # Phase 2: Architecture
                phase_start = datetime.now()
                self.reporter.start_phase(
                    phase_name="Phase 2: Architecture",
                    agent_name="LLM Architect",
                    description="Designing system architecture",
                )
                result.architecture_design = await self._phase_2_architecture(
                    requirement, result.golden_data, result.requirement_analysis
                )
                self.reporter.complete_phase(
                    phase_name="Phase 2: Architecture",
                    duration=(datetime.now() - phase_start).total_seconds(),
                    success=True,
                )
                result.phases_completed.append(BMADPhase.ARCHITECTURE)

                # Generate artifacts for Phase 2
                await self._generate_artifact("\1", result, "\2", requirement)
                await self._generate_artifact("\1", result, "\2", requirement)

                # Phase 3: Design
                phase_start = datetime.now()
                self.reporter.start_phase(
                    phase_name="Phase 3: Design",
                    agent_name="LLM Designer",
                    description="Designing agents and tasks",
                )
                agents, tasks = await self._phase_3_design(
                    requirement, result.golden_data, result.architecture_design
                )

                # Validate and fix if enabled (legacy mode only)
                if self.enable_validation and self.validator:
                    self.reporter.validation_start("Design Validation", len(agents) + len(tasks))
                    validation_result = self.validator.validate_design(
                        agents=agents,
                        tasks=tasks,
                        validate_golden=True,
                        validate_ontology=True,
                        validate_dependencies=True,
                    )
                    result.validation_reports.append(
                        {"phase": "design", "result": validation_result}
                    )

                    # Check for issues
                    has_issues = (
                        validation_result.golden_result
                        and validation_result.golden_result.needs_fixing
                    )
                    issues_count = 0
                    if validation_result.golden_result:
                        issues_count = (
                            len(validation_result.golden_result.missing_items)
                            + len(validation_result.golden_result.extra_items)
                            + len(validation_result.golden_result.mismatched_items)
                        )
                    self.reporter.validation_result(
                        validator_name="Design Validator",
                        passed=not has_issues,
                        issues_count=issues_count,
                    )

                    # Auto-fix if needed
                    if self.enable_auto_fix and self.fixer and validation_result.golden_result:
                        if validation_result.golden_result.needs_fixing:
                            self.reporter.info("Running auto-fix for design issues")
                            fix_result = self.fixer.fix_design(
                                agent_specs=agents,
                                task_specs=tasks,
                                validation_report=validation_result.golden_result,
                                max_iterations=3,
                            )
                            if fix_result.success:
                                agents = [
                                    AgentSpecModel(**a) for a in fix_result.fixed_output["agents"]
                                ]
                                tasks = [
                                    TaskSpecModel(**t) for t in fix_result.fixed_output["tasks"]
                                ]
                                self.reporter.info("Auto-fix completed successfully")

                result.agent_specs = agents
                result.task_specs = tasks

                # Register tasks in traceability (Phase 2 enhancement)
                if traceability and result.golden_data:
                    self._register_tasks_in_traceability(
                        traceability, result.task_specs, result.golden_data.features
                    )
                    self.reporter.info(
                        f"📊 Registered {len(result.task_specs)} tasks in traceability matrix"
                    )

                # Determine workflow type (sequential vs hierarchical)
                if workflow_type:
                    # Use user-specified workflow type
                    final_workflow_type = workflow_type
                    self.reporter.info(
                        f"🔀 Using user-specified workflow type: {final_workflow_type}"
                    )
                else:
                    # Auto-detect based on complexity
                    agent_dicts = [a.model_dump() for a in agents]
                    task_dicts = [t.model_dump() for t in tasks]

                    recommendation = get_workflow_recommendation(
                        requirement=requirement,
                        agents=agent_dicts,
                        tasks=task_dicts,
                        domain=result.golden_data.domain if result.golden_data else domain,
                    )

                    final_workflow_type = recommendation["workflow_type"]
                    complexity_score = recommendation["complexity_score"]
                    reasons = recommendation["reasons"]

                    self.reporter.info(
                        f"🔀 Auto-selected workflow type: {final_workflow_type} (complexity: {complexity_score:.1f})"
                    )
                    if reasons:
                        self.reporter.info(f"   Reasons: {', '.join(reasons)}")

                # Store workflow type in golden data
                if result.golden_data:
                    result.golden_data.workflow_type = final_workflow_type

                self.reporter.complete_phase(
                    phase_name="Phase 3: Design",
                    duration=(datetime.now() - phase_start).total_seconds(),
                    success=True,
                )
                result.phases_completed.append(BMADPhase.DESIGN)

                # Generate artifacts for Phase 3
                await self._generate_artifact("\1", result, "\2", requirement)
                await self._generate_artifact("\1", result, "\2", requirement)

                # Phase 4: Development (Spec Generation)
                phase_start = datetime.now()
                self.reporter.start_phase(
                    phase_name="Phase 4: Development",
                    agent_name="Spec Generator",
                    description="Generating YAML specification",
                )
                result.spec_yaml = await self._phase_4_development(
                    agents, tasks, result.golden_data
                )
                self.reporter.complete_phase(
                    phase_name="Phase 4: Development",
                    duration=(datetime.now() - phase_start).total_seconds(),
                    success=True,
                )
                result.phases_completed.append(BMADPhase.DEVELOPMENT)

                # Phase 5: Delivery (Code Generation)
                phase_start = datetime.now()
                self.reporter.start_phase(
                    phase_name="Phase 5: Delivery",
                    agent_name="Code Generator",
                    description="Generating production code",
                )
                result.generated_code = await self._phase_5_delivery(
                    result.spec_yaml, result.golden_data, deployment_target
                )
                # Register code in traceability (Phase 2 enhancement)
                if (
                    traceability
                    and result.generated_code
                    and result.task_specs
                    and result.golden_data
                ):
                    self._register_code_in_traceability(
                        traceability,
                        result.generated_code,
                        result.task_specs,
                        result.golden_data.features,
                    )
                    self.reporter.info(
                        f"📊 Registered {len(result.generated_code)} code files in traceability matrix"
                    )

                self.reporter.complete_phase(
                    phase_name="Phase 5: Delivery",
                    duration=(datetime.now() - phase_start).total_seconds(),
                    success=True,
                )
                result.phases_completed.append(BMADPhase.DELIVERY)

                # Generate artifacts for Phase 5
                await self._generate_artifact("\1", result, "\2", requirement)
                await self._generate_artifact("\1", result, "\2", requirement)
                await self._generate_artifact("\1", result, "\2", requirement)

                # Quality Validation: Syntax/Import checks (Phase 5 Post-Generation)
                await self._run_quality_validation(result)

                # Security Scanning: Vulnerability/Secret detection (Phase 5 Post-Generation)
                await self._run_security_scan(result)

            # Phase 3 Enhancement: Completeness Validation (for legacy path)
            if enable_completeness_validation and result.generated_code and result.golden_data:
                await self._run_completeness_validation(result, traceability, enable_gap_filling)

            # Optional: Bootstrap Project
            if bootstrap_project and result.generated_code:
                result.bootstrap_result = await self._bootstrap_project(
                    generated_code=result.generated_code,
                    project_name=project_name or "generated_project",
                    bootstrap_dir=bootstrap_dir,
                )

            result.success = True

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            self.reporter.error(f"BMAD Workflow failed: {str(e)}")

        finally:
            end_time = datetime.now()
            result.total_duration = (end_time - start_time).total_seconds()

            # Generate traceability report (Phase 2 enhancement)
            if traceability:
                try:
                    coverage = traceability.analyze_coverage()
                    report = traceability.generate_report()

                    result.coverage_analysis = coverage
                    result.traceability_report = report

                    self.reporter.info("\n" + report)

                    # Warn about unimplemented features
                    if coverage["gaps"]["unimplemented_features"]:
                        unimpl_count = len(coverage["gaps"]["unimplemented_features"])
                        self.reporter.warning(f"⚠️  {unimpl_count} features remain unimplemented")

                except Exception as e:
                    self.reporter.warning(f"Failed to generate traceability report: {e}")

            # Complete workflow with summary
            summary = {
                "total_duration": result.total_duration,
                "phases_completed": len(result.phases_completed),
                "validation_reports": len(result.validation_reports),
                "files_generated": len(result.generated_code) if result.generated_code else 0,
                "errors": len(result.errors),
            }

            # Add traceability summary
            if result.coverage_analysis:
                summary["implementation_rate"] = result.coverage_analysis["summary"][
                    "implementation_rate"
                ]
                summary["traceability_enabled"] = True

            self.reporter.complete_workflow(success=result.success, summary=summary)

        return result

    async def _phase_0_concretization(
        self, requirement: str, domain: Optional[str]
    ) -> ConcretizedRequirement:
        """Phase 0: Generate Golden Data"""
        return await self.golden_pipeline.generate(requirement, domain)

    async def _phase_1_discovery(
        self, requirement: str, golden_data: ConcretizedRequirement
    ) -> Dict[str, Any]:
        """Phase 1: Requirement Analysis"""
        # Safely extract features
        features = golden_data.features if golden_data and golden_data.features else []
        features_data = [f.model_dump() for f in features] if features else []

        prompt = f"""다음 요구사항을 분석하여 구조화된 분석 결과를 제공하세요.

**중요: 모든 텍스트 값을 한국어로 작성하세요.**

요구사항: {requirement}

Golden Data 기능:
{features_data}

다음을 포함하여 분석을 제공하세요 (모든 값은 한국어로):
- 주요 기능 요구사항
- 비기능적 요구사항
- 기술적 제약사항
- 성공 기준

JSON으로 반환하세요 (모든 텍스트 필드는 한국어로)."""

        response = await self.llm.ainvoke(
            messages=[{"role": "user", "content": prompt}],
            response_format=LLMConstants.RESPONSE_FORMAT_JSON,
            temperature=LLMConstants.TEMPERATURE_PRECISE,
        )

        # Parse response
        return ResponseParser.parse_structured_response(
            response,
            expected_fields=["analysis", "requirements", "success_criteria"],
            fallback_factory=lambda: {"analysis": "Analysis completed"},
        )

    async def _phase_2_architecture(
        self, requirement: str, golden_data: ConcretizedRequirement, analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phase 2: System Architecture Design"""
        # Safely extract features and data models
        features = golden_data.features if golden_data and golden_data.features else []
        feature_names = [f.name for f in features] if features else []

        data_models = golden_data.data_models if golden_data and golden_data.data_models else []
        model_names = [dm.entity_name for dm in data_models] if data_models else []

        prompt = f"""다음 요구사항에 대한 시스템 아키텍처를 설계하세요.

**중요: 모든 텍스트 값을 한국어로 작성하세요.**

요구사항: {requirement}

기능: {feature_names}
데이터 모델: {model_names}

설계 내용 (모든 값은 한국어로):
- 시스템 컴포넌트
- 데이터 흐름
- 통합 지점
- 기술 스택

JSON으로 반환하세요 (모든 텍스트 필드는 한국어로)."""

        response = await self.llm.ainvoke(
            messages=[{"role": "user", "content": prompt}],
            response_format=LLMConstants.RESPONSE_FORMAT_JSON,
            temperature=LLMConstants.TEMPERATURE_PRECISE,
        )

        return ResponseParser.parse_structured_response(
            response,
            expected_fields=[
                "architecture",
                "components",
                "data_flow",
                "integration_points",
                "technology_stack",
            ],
            fallback_factory=lambda: {"architecture": "Architecture designed"},
        )

    async def _phase_3_design(
        self, requirement: str, golden_data: ConcretizedRequirement, architecture: Dict[str, Any]
    ) -> tuple[List[AgentSpecModel], List[TaskSpecModel]]:
        """Phase 3: Agent and Task Design"""

        # Design agents and tasks based on features
        agents = []
        tasks = []

        # Create default manager agent
        manager = AgentSpecModel(
            id="project_manager",
            role="manager",
            goal="Coordinate and manage project tasks",
            backstory="Experienced project manager with expertise in task coordination",
            tools=[],
        )
        agents.append(manager)

        # Safely extract features
        features = golden_data.features if golden_data and golden_data.features else []

        # Create tasks from features
        for _, feature in enumerate(features):
            task = TaskSpecModel(
                id=f"task_{feature.id.lower()}",
                description=feature.description,
                expected_output=f"Completed {feature.name}",
                agent="project_manager",
                context=[],
            )
            tasks.append(task)

        return agents, tasks

    async def _phase_4_development(
        self,
        agents: List[AgentSpecModel],
        tasks: List[TaskSpecModel],
        golden_data: ConcretizedRequirement,
    ) -> str:
        """Phase 4: Spec Generation"""

        # Generate YAML spec
        import yaml

        # Dump models with exclude_none to avoid YAML serialization issues
        spec = {
            "agents": [a.model_dump(exclude_none=True, mode="json") for a in agents],
            "tasks": [t.model_dump(exclude_none=True, mode="json") for t in tasks],
        }

        # Use safe_dump for better compatibility and add explicit handling
        return yaml.safe_dump(spec, default_flow_style=False, allow_unicode=True, sort_keys=False)

    async def _phase_5_delivery(
        self, spec_yaml: str, golden_data: ConcretizedRequirement, deployment_target: str
    ) -> Dict[str, str]:
        """Phase 5: Code Generation"""

        # Get agents and tasks from spec_yaml
        import yaml

        spec_data = yaml.safe_load(spec_yaml)

        agents = [AgentSpecModel(**a) for a in spec_data.get("agents", [])]
        tasks = [TaskSpecModel(**t) for t in spec_data.get("tasks", [])]

        # Initialize code generation engine
        code_gen_engine = CodeGenerationEngine(
            llm_plugin=self.llm,
            enable_error_handling=True,
            enable_logging=True,
            enable_tests=True,
            enable_deployment=True,
            enable_llm_generation=True,
        )

        # Generate production-ready code
        gen_result = await code_gen_engine.generate(
            golden_data=golden_data, agents=agents, tasks=tasks, deployment_target=deployment_target
        )

        return gen_result.files

    def _agent_phase_to_bmad_phase(self, agent_phase) -> BMADPhase:
        """Convert AgentPhase to BMADPhase."""
        from caas_framework.agents.base import AgentPhase

        mapping = {
            AgentPhase.DISCOVERY: BMADPhase.DISCOVERY,
            AgentPhase.ARCHITECTURE: BMADPhase.ARCHITECTURE,
            AgentPhase.DESIGN: BMADPhase.DESIGN,
            AgentPhase.DELIVERY: BMADPhase.DELIVERY,
            AgentPhase.QUALITY_ASSURANCE: BMADPhase.DELIVERY,  # Map QA to Delivery
        }

        return mapping.get(agent_phase, BMADPhase.DELIVERY)

    def _map_tasks_to_features(
        self, tasks: List[TaskSpecModel], features: List[Any]
    ) -> Dict[str, List[str]]:
        """
        Map tasks to features based on task ID patterns.

        Args:
            tasks: List of task specifications
            features: List of feature specifications

        Returns:
            Dictionary mapping task_id to list of feature_ids
        """
        task_feature_map = {}

        for task in tasks:
            implementing_features = []

            # Extract feature ID from task ID (e.g., "task_user_login" → "user_login")
            if task.id.startswith("task_"):
                potential_feature_id = task.id[5:]  # Remove "task_" prefix

                # Check if this feature exists
                for feature in features:
                    if feature.id == potential_feature_id:
                        implementing_features.append(feature.id)
                        break
                    # Also check if task description matches feature description/name
                    elif (
                        hasattr(feature, "description")
                        and feature.description
                        and task.description
                        and feature.description.lower() in task.description.lower()
                    ):
                        implementing_features.append(feature.id)
                    elif (
                        hasattr(feature, "name")
                        and feature.name
                        and task.description
                        and feature.name.lower() in task.description.lower()
                    ):
                        implementing_features.append(feature.id)

            task_feature_map[task.id] = implementing_features

        return task_feature_map

    def _register_tasks_in_traceability(
        self, traceability: TraceabilityMatrix, tasks: List[TaskSpecModel], features: List[Any]
    ) -> None:
        """Register tasks and their feature mappings in traceability matrix."""
        task_feature_map = self._map_tasks_to_features(tasks, features)

        for task in tasks:
            implementing_features = task_feature_map.get(task.id, [])
            traceability.register_task(task, implementing_features)

    def _register_code_in_traceability(
        self,
        traceability: TraceabilityMatrix,
        generated_code: Dict[str, str],
        tasks: List[TaskSpecModel],
        features: List[Any],
    ) -> None:
        """Register generated code in traceability matrix."""
        # Map tasks to features
        task_feature_map = self._map_tasks_to_features(tasks, features)

        # For each code file, determine which task generated it and which features it implements
        for file_path, content in generated_code.items():
            # Determine generating task based on file name or content
            generating_task = "unknown"

            # Simple heuristic: main.py generated by project_manager
            if "main.py" in file_path:
                generating_task = "project_manager"

            # Try to find which features are implemented in this file
            implemented_features = set()
            for task in tasks:
                # Check if task ID appears in file content
                if task.id in content or task.description.lower() in content.lower():
                    # Add all features this task implements
                    implemented_features.update(task_feature_map.get(task.id, []))

            traceability.register_code(
                file_path=file_path,
                generated_by_task=generating_task,
                implements_features=list(implemented_features),
            )

    async def _run_completeness_validation(
        self,
        result: BMADResult,
        traceability: Optional[TraceabilityMatrix],
        enable_gap_filling: bool,
    ) -> None:
        """
        Run completeness validation and optional gap filling

        Args:
            result: BMAD result to update
            traceability: Optional traceability matrix
            enable_gap_filling: Whether to enable gap filling
        """
        self.reporter.info("🔍 Phase 3: Validating completeness...")

        validator = CompletenessValidator(self.llm)
        completeness_report = await validator.validate(
            features=result.golden_data.features,
            generated_code=result.generated_code,
            traceability=traceability,
        )

        result.completeness_report = completeness_report
        result.completeness_text_report = validator.generate_text_report(completeness_report)

        self.reporter.info(
            f"✅ Completeness validation complete: {completeness_report.implementation_rate:.1f}% "
            f"(Score: {completeness_report.completeness_score:.1f}/100)"
        )

        # Phase 3 Enhancement: Gap Filling (optional)
        if enable_gap_filling and not completeness_report.is_complete:
            self.reporter.info(
                f"🔧 Phase 3: Filling gaps for {len(completeness_report.unimplemented_features)} "
                f"unimplemented features..."
            )

            gap_filler = GapFiller(self.llm)

            # Need code analyses for gap filling
            from caas_framework.bmad.code_analyzer import CodeAnalyzer

            code_analyzer = CodeAnalyzer()
            code_analyses = code_analyzer.analyze_code_base(result.generated_code)

            gap_result = await gap_filler.fill_gaps(
                completeness_report=completeness_report,
                existing_code=result.generated_code,
                code_analyses=code_analyses,
                max_features=5,  # Limit to avoid overwhelming
            )

            result.gap_filling_result = gap_result

            if gap_result.success and gap_result.updated_files:
                # Update generated code with filled gaps
                result.generated_code = gap_result.updated_files
                self.reporter.info(
                    f"✅ Gap filling complete: {len(gap_result.features_filled)} features added"
                )

                # Re-validate after gap filling
                self.reporter.info("🔍 Re-validating after gap filling...")
                completeness_report = await validator.validate(
                    features=result.golden_data.features,
                    generated_code=result.generated_code,
                    traceability=traceability,
                )
                result.completeness_report = completeness_report
                result.completeness_text_report = validator.generate_text_report(
                    completeness_report
                )

                self.reporter.info(
                    f"✅ After gap filling: {completeness_report.implementation_rate:.1f}% "
                    f"(Score: {completeness_report.completeness_score:.1f}/100)"
                )
            elif gap_result.errors:
                self.reporter.warning(f"⚠️  Gap filling had {len(gap_result.errors)} errors")

    async def _run_quality_validation(self, result: BMADResult) -> None:
        """
        Run quality validation on generated code (syntax, imports, Python 3.11 compatibility)

        Args:
            result: BMAD result to update with validation results
        """
        if not result.generated_code:
            return

        self.reporter.info("🔍 Running quality validation...")

        try:
            from caas_framework.validation.python311_validator import Python311Validator

            # Run Python 3.11 compatibility validation
            validator = Python311Validator()
            validation_result = validator.validate(result.generated_code)

            # Store in validation_reports
            validation_report = {
                "type": "python311_compatibility",
                "is_valid": validation_result.is_valid,
                "error_count": validation_result.error_count,
                "warning_count": validation_result.warning_count,
                "info_count": validation_result.info_count,
                "issues": [
                    {
                        "severity": issue.severity,
                        "issue_type": issue.issue_type,
                        "message": issue.message,
                        "file": issue.file,
                        "line": issue.line,
                        "suggested_fix": issue.suggested_fix,
                    }
                    for issue in validation_result.issues
                ],
            }

            result.validation_reports.append(validation_report)

            # Report summary
            if validation_result.is_valid:
                self.reporter.info(
                    f"✅ Quality validation passed "
                    f"({validation_result.warning_count} warnings, {validation_result.info_count} info)"
                )
            else:
                self.reporter.warning(
                    f"⚠️  Quality validation found {validation_result.error_count} errors, "
                    f"{validation_result.warning_count} warnings"
                )

                # Report first 3 errors
                errors = [i for i in validation_result.issues if i.severity == "error"]
                for error in errors[:3]:
                    location = (
                        f"{error.file}:{error.line}" if error.file and error.line else "general"
                    )
                    self.reporter.warning(f"  ❌ [{location}] {error.message}")

                if len(errors) > 3:
                    self.reporter.warning(f"  ... and {len(errors) - 3} more errors")

        except Exception as e:
            self.reporter.warning(f"⚠️  Quality validation error: {str(e)}")
            result.validation_reports.append(
                {"type": "python311_compatibility", "error": str(e), "is_valid": False}
            )

    async def _run_security_scan(self, result: BMADResult) -> None:
        """
        Run security scanning on generated code (vulnerabilities, secrets, best practices)

        Args:
            result: BMAD result to update with security findings
        """
        if not result.generated_code:
            return

        self.reporter.info("🔒 Running security scan...")

        try:
            from caas_framework.security import scan_generated_code

            # Run security scan
            security_result = scan_generated_code(
                generated_files=result.generated_code,
                use_bandit=True,  # Use Bandit if available
                fail_on_critical=False,  # Don't fail build on critical issues
            )

            # Store in security_report
            result.security_report = security_result.to_dict()

            # Report summary
            if security_result.is_safe:
                self.reporter.info(
                    f"✅ Security scan passed "
                    f"({security_result.total_issues} issues: "
                    f"{security_result.low_count}L, {security_result.medium_count}M, "
                    f"{security_result.high_count}H, {security_result.critical_count}C)"
                )
            else:
                self.reporter.warning(
                    f"⚠️  Security scan found {security_result.total_issues} issues: "
                    f"{security_result.critical_count} critical, {security_result.high_count} high, "
                    f"{security_result.medium_count} medium, {security_result.low_count} low"
                )

            # Report critical and high severity issues
            critical_high = [
                i for i in security_result.issues if i.severity.value in ("critical", "high")
            ]

            if critical_high:
                self.reporter.warning(f"  🚨 Critical/High severity issues:")
                for issue in critical_high[:5]:  # Show first 5
                    location = (
                        f"{issue.file_path}:{issue.line_number}"
                        if issue.line_number
                        else issue.file_path
                    )
                    severity_emoji = "🔴" if issue.severity.value == "critical" else "🟠"
                    self.reporter.warning(f"    {severity_emoji} [{location}] {issue.issue_text}")

                if len(critical_high) > 5:
                    self.reporter.warning(
                        f"    ... and {len(critical_high) - 5} more critical/high issues"
                    )

        except Exception as e:
            self.reporter.warning(f"⚠️  Security scan error: {str(e)}")
            result.security_report = {
                "error": str(e),
                "is_safe": True,  # Assume safe if scan fails
                "total_issues": 0,
            }

    async def _generate_artifact(
        self, artifact_type: str, result: BMADResult, phase: str, requirement: str = ""
    ) -> None:
        """
        Generate artifact if artifact generator is enabled

        Args:
            artifact_type: Type of artifact to generate (e.g., "PROJECT_PROPOSAL")
            result: Current BMAD result
            phase: Phase name for logging
            requirement: Original requirement text
        """
        if not self.artifact_generator:
            self.reporter.debug(f"Artifact generator not initialized, skipping {artifact_type}")
            return

        self.reporter.debug(f"Generating artifact {artifact_type} for {phase}")

        try:
            # Build context from result
            context = {"requirement": requirement}
            if result.golden_data:
                context["golden_data"] = result.golden_data
            if result.requirement_analysis:
                context["requirement_analysis"] = result.requirement_analysis
            if result.architecture_design:
                context["architecture_design"] = result.architecture_design
            if result.agent_specs:
                context["agents"] = result.agent_specs
            if result.task_specs:
                context["tasks"] = result.task_specs
            if result.generated_code:
                context["generated_code"] = result.generated_code

            # Generate artifact (synchronous call - no await)
            from caas_framework.models import ArtifactType

            # Prepare bmad_data with proper structure
            bmad_data = {
                "requirement": context.get("requirement", ""),
                "golden_data": self._convert_to_dict(context.get("golden_data")),
                "requirement_analysis": self._convert_to_dict(context.get("requirement_analysis")),
                "architecture": self._convert_to_dict(context.get("architecture_design")),
                "agents": self._convert_to_list(context.get("agents", [])),
                "tasks": self._convert_to_list(context.get("tasks", [])),
                "code": context.get("generated_code", {}),
            }

            artifact = self.artifact_generator.generate_artifact(
                artifact_type=getattr(ArtifactType, artifact_type), bmad_data=bmad_data
            )

            # Artifact is already saved by generate_artifact()
            output_path = artifact.file_path if artifact.file_path else "Unknown"
            self.reporter.info(f"📄 Generated {artifact_type}: {output_path}")

        except Exception as e:
            self.reporter.warning(f"⚠️  Failed to generate {artifact_type}: {e}")

    def _convert_to_dict(self, obj: Any) -> Dict[str, Any]:
        """Convert Pydantic model or object to dict"""
        if obj is None:
            return {}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        return {}

    def _convert_to_list(self, items: Any) -> List[Dict[str, Any]]:
        """Convert list of Pydantic models to list of dicts"""
        if not items:
            return []
        if not isinstance(items, list):
            return []

        result = []
        for item in items:
            if isinstance(item, dict):
                result.append(item)
            elif hasattr(item, "model_dump"):
                result.append(item.model_dump())
            elif hasattr(item, "dict"):
                result.append(item.dict())
            else:
                result.append({})
        return result

    async def _bootstrap_project(
        self,
        generated_code: Dict[str, str],
        project_name: str,
        bootstrap_dir: Optional[Path] = None,
    ) -> BootstrapResult:
        """
        Bootstrap a complete project from generated code.

        Args:
            generated_code: Dictionary of generated code files
            project_name: Name for the project directory
            bootstrap_dir: Base directory to create project in

        Returns:
            BootstrapResult with project setup details
        """
        self.reporter.info(f"\n⚙️  Bootstrapping project: {project_name}")

        bootstrapper = ProjectBootstrapper()

        result = bootstrapper.bootstrap(
            generated_files=generated_code,
            project_name=project_name,
            base_dir=bootstrap_dir,
            auto_git=True,
            auto_venv=True,
            auto_install=True,
            auto_test=False,  # Don't run tests automatically
            verbose=True,
        )

        self.reporter.info(f"✅ Project bootstrapped at: {result.project_dir}")

        return result
