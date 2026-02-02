"""
CAAS Unified API

UI-independent API interface for CLI, Streamlit, VSCode Extension, and other UIs.
Provides a high-level interface to the CAAS framework with event-driven architecture.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from caas_framework.agents.base import AgentPhase
from caas_framework.agents.collaboration import ExpertAgentCollaboration
from caas_framework.events.event_bus import EventBus
from caas_framework.models.specifications import ConcretizedRequirement
from caas_framework.plugins.llm.base import LLMPlugin

logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """
    Code generation configuration.

    Controls all aspects of code generation behavior.
    """

    # LLM Configuration
    llm_provider: str = "openai"
    llm_model: str = "gpt-4"
    llm_api_key: Optional[str] = None
    llm_temperature: float = 0.7

    # Generation Features
    enable_plan_mode: bool = False
    enable_feedback_loop: bool = True
    enable_validation: bool = True
    enable_auto_fix: bool = True

    # Retry & Timeout
    max_retries: int = 3
    max_feedback_loops: int = 3
    timeout_seconds: int = 300

    # Output Configuration
    output_dir: str = "./generated"
    overwrite_existing: bool = False

    # Verbosity
    verbosity: str = "normal"  # quiet, minimal, normal, verbose, debug

    # Advanced
    use_expert_agents: bool = True
    use_bmad_workflow: bool = True
    enable_process_optimization: bool = True  # ProcessSelector


@dataclass
class GenerationResult:
    """
    Code generation result.

    UI-independent result format that all UIs can consume.
    """

    success: bool
    files: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class CAAS_API:
    """
    CAAS Unified API

    UI-independent API interface for all CAAS functionality.
    Provides high-level methods for code generation with event-driven architecture.

    Examples:
        # CLI Usage
        from caas_framework.api import CAAS_API, GenerationConfig

        config = GenerationConfig(
            llm_provider="openai",
            llm_model="gpt-4"
        )
        api = CAAS_API(config)
        result = await api.generate("Create a blog system")

        # Streamlit Usage with Plan Mode
        from caas_framework.api import CAAS_API, GenerationConfig
        from caas_framework.modes import PlanModeCore
        from streamlit_ui.review import StreamlitReviewHandler

        config = GenerationConfig(enable_plan_mode=True)
        review_handler = StreamlitReviewHandler()
        plan_mode = PlanModeCore(review_handler=review_handler)

        api = CAAS_API(config, plan_mode=plan_mode)
        result = await api.generate("Create a blog system")

        # VSCode Extension with Events
        def on_phase_start(event):
            vscode.window.showInformationMessage(f"Starting {event.phase}")

        api = CAAS_API(config)
        api.subscribe_event("phase_start", on_phase_start)
        result = await api.generate("Create a blog system")
    """

    def __init__(
        self,
        config: GenerationConfig,
        llm_plugin: Optional[LLMPlugin] = None,
        plan_mode: Optional[Any] = None,
        progress_reporter: Optional[Any] = None,
        event_bus: Optional[EventBus] = None,
    ):
        """
        Initialize CAAS API.

        Args:
            config: Generation configuration
            llm_plugin: Optional pre-configured LLM plugin
            plan_mode: Optional Plan Mode instance (PlanMode or PlanModeCore)
            progress_reporter: Optional progress reporter (ProgressReporter Protocol)
            event_bus: Optional EventBus instance
        """
        self.config = config
        self.plan_mode = plan_mode
        self.progress_reporter = progress_reporter

        # Initialize LLM
        self.llm = llm_plugin or self._init_llm()

        # Initialize EventBus
        self.event_bus = event_bus or EventBus()

        # Event subscriptions
        self._event_subscriptions: Dict[str, List[Callable]] = {}

        logger.info(f"CAAS_API initialized with config: {config}")

    async def generate(
        self, requirement: str, golden_data: Optional[ConcretizedRequirement] = None
    ) -> GenerationResult:
        """
        Generate code from natural language requirement.

        Args:
            requirement: Natural language requirement (e.g., "Create a blog system")
            golden_data: Optional pre-generated Golden Data

        Returns:
            GenerationResult with generated files and metadata

        Raises:
            Exception: If generation fails
        """
        logger.info(f"Starting code generation for: {requirement[:100]}...")

        try:
            # Step 1: Generate Golden Data if not provided
            if not golden_data:
                logger.info("Generating Golden Data...")
                golden_data = await self._generate_golden_data(requirement)

            # Step 2: Setup collaboration
            collaboration = self._create_collaboration(golden_data)

            # Step 3: Execute collaboration workflow
            logger.info("Executing collaboration workflow...")
            collab_result = await collaboration.collaborate(requirement)

            # Step 4: Format result
            result = self._format_result(collab_result)

            # Step 5: Save files if output_dir specified
            if self.config.output_dir and result.files:
                await self._save_files(result.files, self.config.output_dir)

            logger.info(f"Generation {'succeeded' if result.success else 'failed'}")
            return result

        except Exception as e:
            logger.error(f"Generation failed: {str(e)}", exc_info=True)
            return GenerationResult(success=False, errors=[str(e)])

    async def generate_from_design(
        self,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        workflow_type: str = "sequential",
    ) -> GenerationResult:
        """
        Generate code from agent/task design.

        Skips Discovery and Design phases, directly generates code.

        Args:
            agents: List of agent definitions
            tasks: List of task definitions
            workflow_type: "sequential" or "hierarchical"

        Returns:
            GenerationResult with generated code files
        """
        logger.info(f"Generating code from design: {len(agents)} agents, {len(tasks)} tasks")

        try:
            # Import here to avoid circular dependency
            import importlib
            import sys

            if "caas_framework.agents.code_generator" in sys.modules:
                importlib.reload(sys.modules["caas_framework.agents.code_generator"])
            from caas_framework.agents.code_generator import CodeGeneratorAgent

            # Create code generator
            generator = CodeGeneratorAgent(self.llm, None)

            # Execute generation
            result = await generator.work(
                requirement="Generate code from provided design",
                context=None,
                previous_outputs={
                    AgentPhase.DESIGN: {
                        "agents": agents,
                        "tasks": tasks,
                        "workflow_type": workflow_type,
                    }
                },
            )

            # Format result
            generation_result = GenerationResult(
                success=result.success,
                files=result.output.get("files", {}),
                metadata={
                    "duration": result.duration,
                    "agents_count": len(agents),
                    "tasks_count": len(tasks),
                    "workflow_type": workflow_type,
                },
                errors=result.errors,
            )

            # Save files
            if self.config.output_dir and generation_result.files:
                await self._save_files(generation_result.files, self.config.output_dir)

            logger.info(
                f"Code generation from design {'succeeded' if result.success else 'failed'}"
            )
            return generation_result

        except Exception as e:
            logger.error(f"Generation from design failed: {str(e)}", exc_info=True)
            return GenerationResult(success=False, errors=[str(e)])

    def subscribe_event(self, event_type: str, callback: Callable[[Any], None]):
        """
        Subscribe to framework events.

        Args:
            event_type: Event type (e.g., "phase_start", "phase_complete")
            callback: Callback function to invoke on event

        Examples:
            def on_phase_start(event):
                print(f"Phase started: {event.phase}")

            api.subscribe_event("phase_start", on_phase_start)
        """
        if event_type not in self._event_subscriptions:
            self._event_subscriptions[event_type] = []

        self._event_subscriptions[event_type].append(callback)

        # Subscribe to EventBus (store subscription for later)
        # Note: EventBus.subscribe expects PhaseEvent enum, but we use strings for simplicity
        # The actual event publishing will be handled by the collaboration layer
        logger.debug(f"Subscribed to event: {event_type}")

    def unsubscribe_event(self, event_type: str, callback: Callable[[Any], None]):
        """
        Unsubscribe from framework events.

        Args:
            event_type: Event type
            callback: Callback function to remove
        """
        if event_type in self._event_subscriptions:
            self._event_subscriptions[event_type].remove(callback)

        logger.debug(f"Unsubscribed from event: {event_type}")

    # ===========================================
    # Private helper methods
    # ===========================================

    def _init_llm(self) -> LLMPlugin:
        """
        Initialize LLM plugin from config.

        Returns:
            Configured LLM plugin
        """
        logger.info(f"Initializing LLM: {self.config.llm_provider}/{self.config.llm_model}")

        # Import LLM plugin based on provider
        if self.config.llm_provider == "openai":
            from caas_framework.plugins.llm.openai_plugin import OpenAIPlugin

            return OpenAIPlugin(
                api_key=self.config.llm_api_key,
                model=self.config.llm_model,
                temperature=self.config.llm_temperature,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.llm_provider}")

    async def _generate_golden_data(self, requirement: str) -> ConcretizedRequirement:
        """
        Auto-generate Golden Data from requirement.

        Args:
            requirement: Natural language requirement

        Returns:
            Generated Golden Data (ConcretizedRequirement)
        """
        logger.info("Auto-generating Golden Data...")

        from caas_framework.bmad.golden_data_pipeline import GoldenDataPipeline

        pipeline = GoldenDataPipeline(self.llm)
        golden_data = await pipeline.execute(requirement)

        logger.info("Golden Data generated successfully")
        return golden_data

    def _create_collaboration(
        self, golden_data: ConcretizedRequirement
    ) -> ExpertAgentCollaboration:
        """
        Create ExpertAgentCollaboration instance.

        Args:
            golden_data: Golden Data

        Returns:
            Configured ExpertAgentCollaboration
        """
        from caas_framework.reporting import VerbosityLevel

        # Map verbosity string to enum
        verbosity_map = {
            "quiet": VerbosityLevel.QUIET,
            "minimal": VerbosityLevel.MINIMAL,
            "normal": VerbosityLevel.NORMAL,
            "verbose": VerbosityLevel.VERBOSE,
            "debug": VerbosityLevel.DEBUG,
        }
        verbosity = verbosity_map.get(self.config.verbosity, VerbosityLevel.NORMAL)

        # Create progress reporter if not provided
        progress_reporter = self.progress_reporter
        if not progress_reporter:
            from caas_framework.reporting import ProgressReporter

            progress_reporter = ProgressReporter(verbosity=verbosity)

        # Create collaboration
        collaboration = ExpertAgentCollaboration(
            llm_plugin=self.llm,
            golden_data=golden_data,
            max_feedback_loops=self.config.max_feedback_loops,
            enable_validation=self.config.enable_validation,
            progress_reporter=progress_reporter,
            plan_mode=self.plan_mode,
        )

        return collaboration

    def _format_result(self, collab_result: Any) -> GenerationResult:
        """
        Format collaboration result to GenerationResult.

        Args:
            collab_result: CollaborationResult

        Returns:
            GenerationResult (UI-independent format)
        """
        # Extract files from code artifacts
        files = {}
        if (
            hasattr(collab_result.context, "code_artifacts")
            and collab_result.context.code_artifacts
        ):
            files = collab_result.context.code_artifacts.get("files", {})

        # Extract metadata
        metadata = {
            "duration": collab_result.total_duration,
            "phases_completed": [p.value for p in collab_result.phases_completed],
            "feedback_loops_executed": collab_result.feedback_loops_executed,
            "agents_used": (
                list(collab_result.agent_summaries.keys()) if collab_result.agent_summaries else []
            ),
        }

        return GenerationResult(
            success=collab_result.success,
            files=files,
            metadata=metadata,
            errors=collab_result.errors,
        )

    async def _save_files(self, files: Dict[str, str], output_dir: str):
        """
        Save generated files to disk.

        Args:
            files: Dictionary of filename -> content
            output_dir: Output directory path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Saving {len(files)} files to {output_dir}")

        for filename, content in files.items():
            file_path = output_path / filename

            # Check overwrite
            if file_path.exists() and not self.config.overwrite_existing:
                logger.warning(f"File exists, skipping: {filename}")
                continue

            # Write file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

            logger.debug(f"Saved: {filename}")

        logger.info(f"All files saved to {output_dir}")
