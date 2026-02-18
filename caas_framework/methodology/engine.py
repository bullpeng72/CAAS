"""
CAAS 6-Phase Methodology Engine

CAAS's proprietary 6-phase development engine with expert agent collaboration.
Automates CrewAI multi-agent system generation from requirements to production code.

Note: This is CAAS's proprietary 6-phase methodology.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from caas_framework.agents.collaboration import ExpertAgentCollaboration
from caas_framework.automation import BootstrapResult, ProjectBootstrapper
from caas_framework.methodology.completeness_validator import (
    CompletenessReport,
    CompletenessValidator,
)
from caas_framework.methodology.gap_filler import GapFiller, GapFillingResult
from caas_framework.methodology.golden_data import GoldenDataPipeline
from caas_framework.methodology.traceability import TraceabilityMatrix
# ✅ v0.5.1: CodeGenerationEngine removed (Legacy path deleted)
from caas_framework.checkpoint.manager import CheckpointManager
from caas_framework.models.checkpoint import CheckpointPhase
from caas_framework.config.settings import LLMConstants
from caas_framework.events import Event, PhaseEvent, get_global_event_bus
from caas_framework.fixing.auto_fixer import AutoFixer
from caas_framework.models.specifications import (
    AgentSpecModel,
    ConcretizedRequirement,
    TaskSpecModel,
)
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.reporting import (
    ProgressReporter,
    ProgressReporterProtocol,
    VerbosityLevel,
)
from caas_framework.utils import ResponseParser
from caas_framework.validation.orchestrator import ValidationOrchestrator


class Phase(str, Enum):
    """CAAS 6-Phase"""

    CONCRETIZATION = "concretization"  # Phase 0: Golden Data
    DISCOVERY = "discovery"  # Phase 1: Requirement Analysis
    ARCHITECTURE = "architecture"  # Phase 2: System Design
    DESIGN = "design"  # Phase 3: Agent/Task Design
    DEVELOPMENT = "development"  # Phase 4: Spec Generation
    DELIVERY = "delivery"  # Phase 5: Code Generation


@dataclass
class MethodologyResult:
    """CAAS 6-Phase Methodology execution result"""

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
    phases_completed: List[Phase] = field(default_factory=list)
    total_duration: float = 0.0
    success: bool = True
    errors: List[str] = field(default_factory=list)

    # Bootstrap (optional)
    bootstrap_result: Optional[BootstrapResult] = None


class SixPhaseEngine:
    """
    CAAS 6-Phase Methodology Engine

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
        # ✅ v0.5.1: use_expert_agents removed - always use Expert Agent path
        progress_reporter: Optional[ProgressReporterProtocol] = None,
        verbosity: VerbosityLevel = VerbosityLevel.NORMAL,
        artifact_config: Optional[Any] = None,
        plan_mode: Optional[Any] = None,
        distributed: bool = False,
        max_workers: Optional[int] = None,
        enable_critic_pattern: bool = False,
        strict_quality_gates: bool = True,  # ✅ v0.4.1: Strict mode enabled by default (matches collaboration.py)
        # ✅ Week 5 (Task 5.3): Human Checkpoints
        enable_checkpoints: bool = False,
        checkpoint_dir: Optional[Path] = None,
        enable_auto_approve: bool = False,
        strict_checkpoint_mode: bool = False,
    ):
        """
        Initialize CAAS 6-Phase Methodology Engine.

        ✅ v0.5.1: Now exclusively uses Expert Agent Collaboration (Legacy LLM path removed)

        Args:
            llm_plugin: LLM plugin for generation
            enable_validation: Enable Golden Data validation
            enable_auto_fix: Enable automatic fixing
            progress_reporter: Optional progress reporter (Protocol-based for UI independence)
            verbosity: Verbosity level for progress reporting
            artifact_config: Optional artifact generation configuration
            plan_mode: Optional Plan Mode instance for interactive approval gates
            distributed: Enable distributed parallel execution (for large projects)
            max_workers: Maximum number of workers for distributed execution
            enable_critic_pattern: Enable Producer-Critic peer review pattern (default: False)
            strict_quality_gates: Enable strict Quality Gate mode - halt on failure (default: True)
            enable_checkpoints: Enable human checkpoint workflow (default: False)
            checkpoint_dir: Directory for checkpoint state (default: ./checkpoints)
            enable_auto_approve: Enable auto-approval based on quality thresholds (default: False)
            strict_checkpoint_mode: Require all mandatory checkpoints before proceeding (default: False)
        """
        self.llm = llm_plugin
        self.enable_validation = enable_validation
        self.enable_auto_fix = enable_auto_fix
        # ✅ v0.5.1: Always use Expert Agent path
        self.plan_mode = plan_mode
        self.distributed = distributed
        self.max_workers = max_workers
        self.enable_critic_pattern = enable_critic_pattern
        self.strict_quality_gates = strict_quality_gates

        # ✅ Week 5 (Task 5.3): Human Checkpoints
        self.enable_checkpoints = enable_checkpoints
        self.checkpoint_manager: Optional[CheckpointManager] = None
        if enable_checkpoints:
            project_name = "caas_project"  # Will be overridden in run() if provided
            self.checkpoint_manager = CheckpointManager(
                project_name=project_name,
                checkpoint_dir=checkpoint_dir or Path("./checkpoints"),
                enable_auto_approve=enable_auto_approve,
                strict_mode=strict_checkpoint_mode,
            )
            self.reporter.info(
                f"🔍 Human checkpoint workflow enabled (auto-approve: {enable_auto_approve}, strict: {strict_checkpoint_mode})"
            )

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
                strategy=ExecutionStrategy.AUTO,
                max_workers=max_workers,
                enable_monitoring=True,
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

        # ✅ v0.5.1: Artifact generator disabled in SixPhaseEngine
        # Artifacts are now generated exclusively by CLI (generate.py)
        # to prevent duplicate directories and ensure clean output structure
        #
        # Previously, initializing ArtifactGenerator here would create ./artifacts/
        # directory even when not used, causing empty folder creation.
        #
        # All artifact generation is handled by CLI at ./generated/artifacts/
        self.artifact_generator: Optional[Any] = None

        # Legacy code (disabled):
        # if artifact_config and getattr(artifact_config, "enabled", False):
        #     try:
        #         from caas_framework.artifacts import ArtifactGenerator
        #         from caas_framework.models import ArtifactGenerationConfig
        #         ...
        #         self.artifact_generator = ArtifactGenerator(config=gen_config)
        #     except ImportError as e:
        #         self.reporter.warning(f"⚠️  Could not load ArtifactGenerator: {e}")

    async def _submit_checkpoint(
        self,
        phase: CheckpointPhase,
        artifact_path: Optional[Path] = None,
        artifact_metadata: Optional[Dict] = None,
        quality_score: Optional[float] = None,
    ) -> bool:
        """
        Submit artifact for human checkpoint review.

        Args:
            phase: Checkpoint phase
            artifact_path: Optional path to artifact file
            artifact_metadata: Optional metadata about the artifact
            quality_score: Optional quality score for auto-approval

        Returns:
            True if checkpoint passed or skipped, False if blocked
        """
        if not self.checkpoint_manager:
            return True  # Checkpoints disabled, always proceed

        try:
            # Submit for review
            result = self.checkpoint_manager.submit_for_review(
                phase=phase,
                artifact_path=artifact_path,
                artifact_metadata=artifact_metadata,
                quality_score=quality_score,
            )

            # Check result status
            if result.status.value == "approved":
                self.reporter.info(
                    f"✅ Checkpoint {result.checkpoint_id} approved "
                    f"(score: {result.overall_score:.2f if result.overall_score else 'N/A'})"
                )
                return True
            elif result.status.value == "pending":
                self.reporter.warning(
                    f"⏸️  Checkpoint {result.checkpoint_id} pending review. "
                    f"Use 'caas checkpoint approve' to approve."
                )
                # If strict mode, block workflow until approved
                if self.checkpoint_manager.strict_mode:
                    return False
                # Otherwise, allow to proceed
                return True
            elif result.status.value == "skipped":
                self.reporter.info(f"⏭️  Checkpoint {result.checkpoint_id} skipped")
                return True
            else:
                # rejected or changes_requested
                self.reporter.error(
                    f"❌ Checkpoint {result.checkpoint_id} blocked: {result.status.value}"
                )
                if result.required_changes:
                    self.reporter.warning("Required changes:")
                    for change in result.required_changes:
                        self.reporter.warning(f"  - {change}")
                return False

        except Exception as e:
            self.reporter.error(f"Checkpoint submission error: {e}")
            # If checkpoints fail, allow workflow to continue (graceful degradation)
            return True

    async def run(
        self,
        requirement: str,
        domain: Optional[str] = None,
        golden_data: Optional[ConcretizedRequirement] = None,
        deployment_target: str = "docker",
        workflow_type: Optional[str] = None,
        output_dir: Optional[Path] = None,  # ✅ v0.5.1: Output directory for file generation
        enable_traceability: bool = True,
        enable_completeness_validation: bool = True,
        enable_gap_filling: bool = False,
        bootstrap_project: bool = False,
        project_name: Optional[str] = None,
        bootstrap_dir: Optional[Path] = None,
        enable_frontend: Optional[bool] = None,  # ✅ FIX #1: Add frontend override
        frontend_framework: Optional[str] = None,  # ✅ FIX #1: Add framework choice
    ) -> MethodologyResult:
        """
        Run complete CAAS 6-Phase pipeline.

        Args:
            requirement: Natural language requirement
            domain: Optional domain hint
            golden_data: Optional pre-existing Golden Data
            deployment_target: Deployment target
            workflow_type: Workflow process type - "sequential", "hierarchical", or None for auto-selection
            output_dir: Output directory for generated files (v0.5.1)
            enable_traceability: Enable feature-to-code traceability tracking (default: True)
            enable_completeness_validation: Enable completeness validation (Phase 3) (default: True)
            enable_gap_filling: Enable automatic gap filling for missing features (default: False)
            bootstrap_project: Whether to bootstrap a complete project directory (default: False)
            project_name: Name for the bootstrapped project (required if bootstrap_project=True)
            bootstrap_dir: Directory to create project in (default: current directory)
            enable_frontend: Override auto-detection and force frontend generation (default: None = auto-detect)
            frontend_framework: Force specific frontend framework - "streamlit" or "react" (default: None = auto-detect)

        Returns:
            MethodologyResult with all artifacts and optional bootstrap result

        Code Generation Path Selection:
            The CAAS 6-Phase Engine supports two code generation paths:

            1. Expert Agent Collaboration (use_expert_agents=True, DEFAULT):
               SixPhaseEngine.run()
                 → ExpertAgentCollaboration.collaborate()
                 → CodeGeneratorAgent._do_work() (Phase 5: Delivery)
                 → CodeGeneratorAgent._generate_tools_file_fallback()
                 → tool_utils.generate_fallback_tools_code()
                 Files generated: files["tools.py"]

            2. Legacy LLM-based Generation (use_expert_agents=False):
               SixPhaseEngine.run()
                 → SixPhaseEngine._phase_5_delivery()
                 → CodeGenerationEngine.generate()
                 → LLMCodeGenerator.generate_custom_tools()
                 → (on LLM failure) LLMCodeGenerator._generate_fallback_tools()
                 → tool_utils.generate_fallback_tools_code()
                 Files generated: files["src/tools.py"]

            Note: Both paths converge on tool_utils.generate_fallback_tools_code()
            for consistent stub tool generation when LLM-based generation is not used.
        """
        start_time = datetime.now()
        result = MethodologyResult()

        # ✅ FIX #1: Store frontend configuration for use in code generation
        self._enable_frontend_override = enable_frontend
        self._frontend_framework_override = frontend_framework

        # Initialize traceability matrix (Phase 2 enhancement)
        traceability = TraceabilityMatrix() if enable_traceability else None
        result.traceability_matrix = traceability

        # Start workflow reporting
        self.reporter.start_workflow(
            workflow_name="CAAS 6-Phase AI-Driven Development", total_phases=6
        )

        # Publish workflow started event
        self.event_bus.publish(
            Event(
                type=PhaseEvent.SYSTEM_READY,
                data={
                    "workflow": "CAAS_6_Phase",
                    "total_phases": 6,
                    # ✅ v0.5.1: use_expert_agents removed (Expert Agent path is the only path)
                    "enable_validation": self.enable_validation,
                },
                source="SixPhaseEngine",
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
                result.golden_data = await self._phase_0_concretization(
                    requirement, domain
                )

            self.reporter.complete_phase(
                phase_name="Phase 0: Concretization",
                duration=(datetime.now() - start_time).total_seconds(),
                success=True,
            )
            result.phases_completed.append(Phase.CONCRETIZATION)

            # ✅ Week 5 (Task 5.3): Submit checkpoint for Phase 0
            if self.enable_checkpoints and result.golden_data:
                checkpoint_passed = await self._submit_checkpoint(
                    phase=CheckpointPhase.CONCRETIZATION,
                    artifact_metadata={
                        "features_count": len(result.golden_data.features)
                        if result.golden_data.features
                        else 0,
                        "data_models_count": len(result.golden_data.data_models)
                        if result.golden_data.data_models
                        else 0,
                        "phase": "concretization",
                    },
                )
                if not checkpoint_passed:
                    result.success = False
                    result.errors.append("Concretization checkpoint failed approval")
                    return result

            # ✅ v0.5.1: Artifact generation disabled in SixPhaseEngine
            # Artifacts are now generated exclusively by CLI (generate.py)
            # to avoid duplication (previously saved to both ./artifacts/ and ./generated/artifacts/)
            # await self._generate_artifact(
            #     "PROJECT_PROPOSAL", result, "Phase 0", requirement
            # )

            # Register features in traceability matrix (Phase 2 enhancement)
            if traceability and result.golden_data:
                traceability.register_features(result.golden_data.features)
                self.reporter.info(
                    f"📊 Registered {len(result.golden_data.features)} features for traceability"
                )

            # ✅ AUTO-DETECTION: If no explicit frontend override, auto-detect from Golden Data
            if self._enable_frontend_override is None and result.golden_data:
                detected_frontend, detected_framework = self._detect_ui_requirements(result.golden_data)
                if detected_frontend:
                    self._enable_frontend_override = detected_frontend
                    self._frontend_framework_override = detected_framework
                    self.reporter.info(
                        f"🎨 UI 요구사항 자동 감지: {detected_framework.value if detected_framework else 'streamlit'}"
                    )

            # Use Expert Agent Collaboration if enabled
            # ✅ v0.5.1: Expert Agent Collaboration (single code path)
            self.reporter.info("🤖 Using Expert Agent Collaboration")

            # Initialize expert collaboration
            self.expert_collaboration = ExpertAgentCollaboration(
                llm_plugin=self.llm,
                golden_data=result.golden_data,
                output_dir=output_dir,  # ✅ v0.5.1: Pass output directory for file generation
                max_feedback_loops=3 if self.enable_auto_fix else 0,
                enable_validation=self.enable_validation,
                progress_reporter=self.reporter,
                plan_mode=self.plan_mode,
                event_bus=self.event_bus,  # Pass event bus for event-driven architecture
                enable_distributed=self.distributed,  # Enable distributed execution if configured
                max_workers=self.max_workers,  # Pass max workers for parallel execution
                enable_critic_pattern=self.enable_critic_pattern,  # Enable Producer-Critic peer review
                strict_quality_gates=self.strict_quality_gates,  # Strict Quality Gate mode
                enable_frontend=self._enable_frontend_override,  # ✅ FIX #1: Pass frontend override (now with auto-detection)
                frontend_framework=self._frontend_framework_override,  # ✅ FIX #1: Pass framework choice (now with auto-detection)
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
                            traceability,
                            result.task_specs,
                            result.golden_data.features,
                        )
                        self.reporter.info(
                            f"📊 Registered {len(result.task_specs)} tasks in traceability matrix"
                        )

                result.generated_code = ctx.code_artifacts
                result.phases_completed = ctx.phases_completed

                # ✅ Week 5 (Task 5.3): Submit checkpoints for expert collaboration phases
                if self.enable_checkpoints:
                    # Checkpoint 2: Discovery (Phase 1)
                    if ctx.requirement_analysis:
                        checkpoint_passed = await self._submit_checkpoint(
                            phase=CheckpointPhase.DISCOVERY,
                            artifact_metadata={
                                "phase": "discovery",
                                "requirement_analysis_complete": True,
                            },
                        )
                        if not checkpoint_passed:
                            result.success = False
                            result.errors.append("Discovery checkpoint failed approval")
                            return result

                    # Checkpoint 3: Architecture (Phase 2)
                    if ctx.architecture_design:
                        checkpoint_passed = await self._submit_checkpoint(
                            phase=CheckpointPhase.ARCHITECTURE,
                            artifact_metadata={
                                "phase": "architecture",
                                "architecture_design_complete": True,
                            },
                        )
                        if not checkpoint_passed:
                            result.success = False
                            result.errors.append("Architecture checkpoint failed approval")
                            return result

                    # Checkpoint 4: Design (Phase 3)
                    if ctx.agent_task_design:
                        agents_count = len(ctx.agent_task_design.get("agents", []))
                        tasks_count = len(ctx.agent_task_design.get("tasks", []))
                        checkpoint_passed = await self._submit_checkpoint(
                            phase=CheckpointPhase.DESIGN,
                            artifact_metadata={
                                "phase": "design",
                                "agents_count": agents_count,
                                "tasks_count": tasks_count,
                            },
                        )
                        if not checkpoint_passed:
                            result.success = False
                            result.errors.append("Design checkpoint failed approval")
                            return result

                    # Checkpoint 6: Delivery (Phase 5)
                    if ctx.code_artifacts:
                        files_count = len(ctx.code_artifacts)
                        checkpoint_passed = await self._submit_checkpoint(
                            phase=CheckpointPhase.DELIVERY,
                            artifact_metadata={
                                "phase": "delivery",
                                "files_count": files_count,
                            },
                        )
                        if not checkpoint_passed:
                            result.success = False
                            result.errors.append("Delivery checkpoint failed approval")
                            return result

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
                            score = result.quality_evaluation.get(
                                "overall_score", 0
                            )
                            passed = result.quality_evaluation.get("passed", False)
                            if passed:
                                self.reporter.info(
                                    f"✅ Code quality score: {score:.1f}/10"
                                )
                            else:
                                self.reporter.warning(
                                    f"⚠️  Code quality score: {score:.1f}/10 (below threshold)"
                                )

                # Convert to CAAS 6-Phase phases
                result.phases_completed = [Phase.CONCRETIZATION] + [
                    self._agent_phase_to_bmad_phase(p) for p in ctx.phases_completed
                ]

                # Generate spec YAML from agents/tasks
                if result.agent_specs and result.task_specs:
                    result.spec_yaml = await self._phase_4_development(
                        result.agent_specs, result.task_specs, result.golden_data
                    )

                    # ✅ Week 5 (Task 5.3): Submit checkpoint for Measurement (Spec Generation)
                    if self.enable_checkpoints:
                        checkpoint_passed = await self._submit_checkpoint(
                            phase=CheckpointPhase.MEASUREMENT,
                            artifact_metadata={
                                "phase": "measurement",
                                "spec_yaml_generated": bool(result.spec_yaml),
                                "agents_count": len(result.agent_specs),
                                "tasks_count": len(result.task_specs),
                            },
                        )
                        if not checkpoint_passed:
                            result.success = False
                            result.errors.append("Measurement checkpoint failed approval")
                            return result

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

                # ✅ v0.5.1: Artifact generation disabled in SixPhaseEngine
                # All artifacts are now generated exclusively by CLI (generate.py:845-910)
                # to prevent duplication - previously saved to both:
                #   - ./artifacts/ (from SixPhaseEngine, with timestamps)
                #   - ./generated/artifacts/ (from CLI, without timestamps)
                # Only CLI generation is needed for proper output structure
                # if result.requirement_analysis:
                #     await self._generate_artifact("REQUIREMENTS_SPEC", result, "Phase 1", requirement)
                # if result.architecture_design:
                #     await self._generate_artifact("ARCHITECTURE_DESIGN", result, "Phase 2", requirement)
                #     await self._generate_artifact("DATA_DESIGN", result, "Phase 2", requirement)
                # if result.agent_specs and result.task_specs:
                #     await self._generate_artifact("AGENT_DESIGN", result, "Phase 3", requirement)
                #     await self._generate_artifact("TEST_PLAN", result, "Phase 3", requirement)
                # if result.generated_code:
                #     await self._generate_artifact("CODE_REVIEW", result, "Phase 5", requirement)
                #     await self._generate_artifact("TEST_REPORT", result, "Phase 5", requirement)
                #     await self._generate_artifact("DEPLOYMENT_GUIDE", result, "Phase 5", requirement)

                # Quality Validation: Syntax/Import checks (Phase 5 Post-Generation)
                if result.generated_code:
                    await self._run_quality_validation(result)

                # Security Scanning: Vulnerability/Secret detection (Phase 5 Post-Generation)
                if result.generated_code:
                    await self._run_security_scan(result)

                # ✅ Week 5 (Task 5.3): Submit checkpoint for Quality Assurance
                if self.enable_checkpoints and result.generated_code:
                    # Extract quality scores from validation reports
                    quality_score = None
                    if result.validation_reports:
                        # Calculate average score from validation reports
                        valid_reports = [
                            r for r in result.validation_reports if r.get("is_valid", False)
                        ]
                        if valid_reports:
                            quality_score = 8.0  # Good quality if validation passed

                    checkpoint_passed = await self._submit_checkpoint(
                        phase=CheckpointPhase.QUALITY_ASSURANCE,
                        artifact_metadata={
                            "phase": "quality_assurance",
                            "validation_reports_count": len(result.validation_reports),
                            "quality_passed": bool(result.validation_reports),
                        },
                        quality_score=quality_score,
                    )
                    if not checkpoint_passed:
                        result.success = False
                        result.errors.append("Quality Assurance checkpoint failed approval")
                        return result

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


            # Phase 3 Enhancement: Completeness Validation (for legacy path)
            if (
                enable_completeness_validation
                and result.generated_code
                and result.golden_data
            ):
                await self._run_completeness_validation(
                    result, traceability, enable_gap_filling
                )

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
            self.reporter.error(f"CAAS 6-Phase Workflow failed: {str(e)}")
            # Print traceback for debugging
            import traceback
            self.reporter.error(f"Traceback:\n{traceback.format_exc()}")

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
                        self.reporter.warning(
                            f"⚠️  {unimpl_count} features remain unimplemented"
                        )

                except Exception as e:
                    self.reporter.warning(
                        f"Failed to generate traceability report: {e}"
                    )

            # Complete workflow with summary
            summary = {
                "total_duration": result.total_duration,
                "phases_completed": len(result.phases_completed),
                "validation_reports": len(result.validation_reports),
                "files_generated": len(result.generated_code)
                if result.generated_code
                else 0,
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
        self,
        requirement: str,
        golden_data: ConcretizedRequirement,
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Phase 2: System Architecture Design"""
        # Safely extract features and data models
        features = golden_data.features if golden_data and golden_data.features else []
        feature_names = [f.name for f in features] if features else []

        data_models = (
            golden_data.data_models if golden_data and golden_data.data_models else []
        )
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
        self,
        requirement: str,
        golden_data: ConcretizedRequirement,
        architecture: Dict[str, Any],
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
        return yaml.safe_dump(
            spec, default_flow_style=False, allow_unicode=True, sort_keys=False
        )

    async def _phase_5_delivery(
        self,
        input_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Execute Phase 5: Delivery (Production Code Generation).

        ✅ v0.4.2 (Bug #2): Implement complete Phase 5 execution.

        Loads design artifacts (golden_data.json, agents.json, tasks.json),
        generates production-ready code, validates syntax, and saves to output directory.

        Args:
            input_dir: Directory containing design artifacts (default: current directory)
            output_dir: Directory to save generated code (default: ./output)

        Returns:
            Dict containing:
                - files: Generated code files (Dict[str, str])
                - validation_passed: Whether Python syntax validation passed
                - file_count: Number of files generated
                - output_dir: Path where files were saved

        Raises:
            FileNotFoundError: If required design artifacts not found
            ValidationError: If generated code has syntax errors
        """
        from pathlib import Path
        import json
        from caas_framework.models.specifications import (
            ConcretizedRequirement,
            AgentSpecModel,
            TaskSpecModel,
        )
        from caas_framework.agents.code_generator import CodeGeneratorAgent
        from caas_framework.agents.base import AgentPhase

        # Set default directories
        if input_dir is None:
            input_dir = Path.cwd()
        if output_dir is None:
            output_dir = Path.cwd() / "output"

        input_dir = Path(input_dir)
        output_dir = Path(output_dir)

        self.reporter.info(f"📦 Phase 5: Delivery - Loading design artifacts from {input_dir}")

        # 1. Load design artifacts
        golden_data_path = input_dir / "golden_data.json"
        agents_path = input_dir / "agents.json"
        tasks_path = input_dir / "tasks.json"

        if not golden_data_path.exists():
            raise FileNotFoundError(f"Golden data not found: {golden_data_path}")
        if not agents_path.exists():
            raise FileNotFoundError(f"Agents design not found: {agents_path}")
        if not tasks_path.exists():
            raise FileNotFoundError(f"Tasks design not found: {tasks_path}")

        # Load JSON files
        with open(golden_data_path, "r", encoding="utf-8") as f:
            golden_data_dict = json.load(f)
        with open(agents_path, "r", encoding="utf-8") as f:
            agents_dict = json.load(f)
        with open(tasks_path, "r", encoding="utf-8") as f:
            tasks_dict = json.load(f)

        # Parse into Pydantic models
        golden_data = ConcretizedRequirement(**golden_data_dict)
        agents_list = agents_dict if isinstance(agents_dict, list) else agents_dict.get("agents", [])
        tasks_list = tasks_dict if isinstance(tasks_dict, list) else tasks_dict.get("tasks", [])
        agents = [AgentSpecModel(**a) for a in agents_list]
        tasks = [TaskSpecModel(**t) for t in tasks_list]

        self.reporter.info(
            f"✅ Loaded: {len(agents)} agents, {len(tasks)} tasks, "
            f"{len(golden_data.features)} features"
        )

        # 2. Initialize Code Generator
        code_generator = CodeGeneratorAgent(
            llm_plugin=self.llm,  # ✅ v0.5.1: Fix attribute name (self.llm not self.llm_plugin)
            golden_data=golden_data,
        )

        # 3. Generate production code
        self.reporter.info("🔧 Generating production code...")
        requirement_str = (
            golden_data.system_scope.scope_description
            or golden_data.system_scope.purpose
            or golden_data.system_scope.project_name
            or ""
        )
        code_result = await code_generator.work(
            requirement=requirement_str,
            context={"output_dir": str(output_dir)},
            previous_outputs={
                AgentPhase.DESIGN: {
                    "agents": [a.model_dump(mode="json") for a in agents],
                    "tasks": [t.model_dump(mode="json") for t in tasks],
                }
            },
        )

        if not code_result.success:
            raise ValueError(f"Code generation failed: {code_result.message}")

        # 4. Validate Python syntax
        self.reporter.info("🔍 Validating Python syntax...")
        validation_passed = True
        invalid_files = []

        files_dict = code_result.output.get("files", {})
        for file_path, content in files_dict.items():
            if file_path.endswith(".py"):
                try:
                    compile(content, file_path, "exec")
                except SyntaxError as e:
                    validation_passed = False
                    invalid_files.append(f"{file_path}: {e}")
                    self.reporter.error(f"❌ Syntax error in {file_path}: {e}")

        if not validation_passed:
            error_msg = "\n".join(invalid_files)
            raise ValueError(f"Generated code has syntax errors:\n{error_msg}")

        self.reporter.info(f"✅ Syntax validation passed for {len(files_dict)} files")

        # 5. Save files to output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        for file_path, content in files_dict.items():
            full_path = output_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            self.reporter.debug(f"💾 Saved: {full_path}")

        self.reporter.info(f"🎉 Phase 5 complete! {len(files_dict)} files saved to {output_dir}")

        # 6. Return result
        return {
            "files": files_dict,
            "validation_passed": validation_passed,
            "file_count": len(files_dict),
            "output_dir": str(output_dir),
        }

    def _agent_phase_to_bmad_phase(self, agent_phase) -> Phase:
        """Convert AgentPhase to Phase."""
        from caas_framework.agents.base import AgentPhase

        mapping = {
            AgentPhase.DISCOVERY: Phase.DISCOVERY,
            AgentPhase.ARCHITECTURE: Phase.ARCHITECTURE,
            AgentPhase.DESIGN: Phase.DESIGN,
            AgentPhase.DELIVERY: Phase.DELIVERY,
            AgentPhase.QUALITY_ASSURANCE: Phase.DELIVERY,  # Map QA to Delivery
        }

        return mapping.get(agent_phase, Phase.DELIVERY)

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
        self,
        traceability: TraceabilityMatrix,
        tasks: List[TaskSpecModel],
        features: List[Any],
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
            # Ensure content is a string (defensive coding)
            if not isinstance(content, str):
                content = str(content) if content is not None else ""

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
        result: MethodologyResult,
        traceability: Optional[TraceabilityMatrix],
        enable_gap_filling: bool,
    ) -> None:
        """
        Run completeness validation and optional gap filling

        Args:
            result: CAAS 6-Phase result to update
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
        result.completeness_text_report = validator.generate_text_report(
            completeness_report
        )

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
            from caas_framework.methodology.code_analyzer import CodeAnalyzer

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
                self.reporter.warning(
                    f"⚠️  Gap filling had {len(gap_result.errors)} errors"
                )

    async def _run_quality_validation(self, result: MethodologyResult) -> None:
        """
        Run quality validation on generated code (syntax, imports, Python 3.11 compatibility)

        Args:
            result: CAAS 6-Phase result to update with validation results
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
                        f"{error.file}:{error.line}"
                        if error.file and error.line
                        else "general"
                    )
                    self.reporter.warning(f"  ❌ [{location}] {error.message}")

                if len(errors) > 3:
                    self.reporter.warning(f"  ... and {len(errors) - 3} more errors")

        except Exception as e:
            self.reporter.warning(f"⚠️  Quality validation error: {str(e)}")
            result.validation_reports.append(
                {"type": "python311_compatibility", "error": str(e), "is_valid": False}
            )

    async def _run_security_scan(self, result: MethodologyResult) -> None:
        """
        Run security scanning on generated code (vulnerabilities, secrets, best practices)

        Args:
            result: CAAS 6-Phase result to update with security findings
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
                i
                for i in security_result.issues
                if i.severity.value in ("critical", "high")
            ]

            if critical_high:
                self.reporter.warning("  🚨 Critical/High severity issues:")
                for issue in critical_high[:5]:  # Show first 5
                    location = (
                        f"{issue.file_path}:{issue.line_number}"
                        if issue.line_number
                        else issue.file_path
                    )
                    severity_emoji = (
                        "🔴" if issue.severity.value == "critical" else "🟠"
                    )
                    self.reporter.warning(
                        f"    {severity_emoji} [{location}] {issue.issue_text}"
                    )

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
        self, artifact_type: str, result: MethodologyResult, phase: str, requirement: str = ""
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
            self.reporter.debug(
                f"Artifact generator not initialized, skipping {artifact_type}"
            )
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
                "requirement_analysis": self._convert_to_dict(
                    context.get("requirement_analysis")
                ),
                "architecture": self._convert_to_dict(
                    context.get("architecture_design")
                ),
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

    def _detect_ui_requirements(
        self, golden_data: ConcretizedRequirement
    ) -> tuple[bool, Optional[Any]]:
        """
        ✅ P1-1: Auto-detect UI requirements from Golden Data (강화된 감지 - Option A+B)

        Detects if UI generation is needed based on:
        1. ui_components field — form/dashboard/page 타입만 인정 (강화)
        2. "streamlit" or "react" in commands.run (명시적 프레임워크만)
        3. Features containing explicit UI keywords (강화된 키워드 목록)

        Option B 변경사항:
        - Check 1: component_type이 명시적 UI 타입(form/dashboard/page/input)인 경우만 감지
        - Check 3: 키워드 목록을 더 명시적인 UI 관련 용어로 한정

        Returns:
            (enable_frontend, frontend_framework)
        """
        from caas_framework.codegen.frontend_generator import FrontendFramework

        enable_frontend = False
        frontend_framework = None

        # Check 1: ui_components field — 명시적 UI 타입만 인정 (Option B)
        # 단순 table/list/chart는 데이터 출력이므로 UI로 간주하지 않음
        EXPLICIT_UI_TYPES = {'form', 'dashboard', 'page', 'input', 'modal', 'wizard', 'sidebar'}
        if hasattr(golden_data, 'ui_components') and golden_data.ui_components:
            ui_type_matched = any(
                getattr(comp, 'component_type', '').lower() in EXPLICIT_UI_TYPES
                for comp in golden_data.ui_components
            )
            if ui_type_matched:
                enable_frontend = True
                self.reporter.debug(
                    f"UI 감지: ui_components 필드에서 명시적 UI 타입 발견 "
                    f"({len(golden_data.ui_components)}개 컴포넌트)"
                )

        # Check 2: commands.run field — 명시적 프레임워크 명령어만 인정
        if hasattr(golden_data, 'commands') and golden_data.commands:
            run_cmd = (
                golden_data.commands.get('run', '')
                if isinstance(golden_data.commands, dict)
                else getattr(golden_data.commands, 'run', '')
            )
            run_cmd = run_cmd.lower() if run_cmd else ''
            if 'streamlit' in run_cmd:
                enable_frontend = True
                frontend_framework = FrontendFramework.STREAMLIT
                self.reporter.debug("UI 감지: commands.run에서 'streamlit' 발견")
            elif 'react' in run_cmd or 'npm' in run_cmd:
                enable_frontend = True
                frontend_framework = FrontendFramework.REACT
                self.reporter.debug("UI 감지: commands.run에서 'react/npm' 발견")

        # Check 3: Features with explicit UI keywords (Option B — 강화된 키워드)
        # 'form', 'button', 'interface'는 제거 — 너무 일반적 (ex: "CLI interface")
        # 명시적으로 웹/앱 UI를 의미하는 단어만 유지
        if hasattr(golden_data, 'features') and golden_data.features:
            EXPLICIT_UI_KEYWORDS = [
                'streamlit', 'react', 'gradio', 'flask', 'fastapi',
                'frontend', 'dashboard', 'web ui', 'web app',
                '웹 ui', '웹앱', '대시보드', '프론트엔드',
                '화면', '페이지', '웹 페이지',
            ]
            for feature in golden_data.features:
                feature_name = feature.name.lower() if hasattr(feature, 'name') else str(feature).lower()
                feature_desc = feature.description.lower() if hasattr(feature, 'description') else ''
                combined = feature_name + ' ' + feature_desc

                if any(kw in combined for kw in EXPLICIT_UI_KEYWORDS):
                    enable_frontend = True
                    if 'streamlit' in combined:
                        frontend_framework = FrontendFramework.STREAMLIT
                    elif 'react' in combined:
                        frontend_framework = FrontendFramework.REACT
                    self.reporter.debug(
                        f"UI 감지: feature '{getattr(feature, 'name', feature)}'에서 명시적 UI 키워드 발견"
                    )
                    break

        # Default to Streamlit if UI detected but framework not specified
        if enable_frontend and frontend_framework is None:
            frontend_framework = FrontendFramework.STREAMLIT

        return enable_frontend, frontend_framework

    def _detect_language(self, golden_data: ConcretizedRequirement) -> str:
        """
        ✅ P1-2: Auto-detect output language from Golden Data

        Detects language based on:
        1. code_style.language field
        2. Korean characters in features/description
        3. Explicit language requirements (e.g., "in Korean", "한국어로")

        Returns:
            Language code ('ko', 'en', etc.)
        """
        # Check 1: Explicit language in code_style
        if hasattr(golden_data, 'code_style') and golden_data.code_style:
            if isinstance(golden_data.code_style, dict):
                lang = golden_data.code_style.get('language', '')
                if lang:
                    self.reporter.debug(f"언어 감지: code_style.language = {lang}")
                    return lang
            elif hasattr(golden_data.code_style, 'language'):
                lang = golden_data.code_style.language
                if lang:
                    self.reporter.debug(f"언어 감지: code_style.language = {lang}")
                    return lang

        # Check 2: Korean characters in features
        if hasattr(golden_data, 'features') and golden_data.features:
            for feature in golden_data.features:
                feature_name = feature.name if hasattr(feature, 'name') else str(feature)
                feature_desc = feature.description if hasattr(feature, 'description') else ''

                # Check for Korean characters (Hangul Unicode range: 0xAC00-0xD7A3)
                if any('\uac00' <= char <= '\ud7a3' for char in feature_name + feature_desc):
                    self.reporter.debug("언어 감지: 한글 문자 발견")
                    return 'ko'

        # Check 3: Korean language keywords in description
        if hasattr(golden_data, 'description') and golden_data.description:
            korean_keywords = ['한국어', '한글', 'in korean', 'korean language']
            if any(keyword in golden_data.description.lower() for keyword in korean_keywords):
                self.reporter.debug("언어 감지: 한국어 키워드 발견")
                return 'ko'

        # Check 4: Korean characters in purpose/objective
        if hasattr(golden_data, 'purpose') and golden_data.purpose:
            if any('\uac00' <= char <= '\ud7a3' for char in golden_data.purpose):
                self.reporter.debug("언어 감지: purpose에서 한글 발견")
                return 'ko'

        # Default to English
        self.reporter.debug("언어 감지: 기본값 'en' 사용")
        return 'en'

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
