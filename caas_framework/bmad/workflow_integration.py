"""
BMAD Workflow Integration

Integrates BMAD engine with workflow orchestrator for state management,
checkpoints, and resumption capabilities.
"""

from typing import Any, Dict, Optional

from caas_framework.bmad.engine import BMADEngine, BMADResult
from caas_framework.session.manager import Session
from caas_framework.workflow.orchestrator import WorkflowOrchestrator, WorkflowPhase, WorkflowResult
from caas_framework.workflow.version_control import GitIntegration


class BMADWorkflowEngine:
    """
    BMAD Workflow Engine

    Enhances BMAD with workflow management features:
    - Automatic checkpointing after each phase
    - Pause/Resume support
    - Rollback to previous phases
    - Git integration for version control
    - Multi-session management
    """

    def __init__(
        self,
        bmad_engine: BMADEngine,
        enable_checkpoints: bool = True,
        enable_git: bool = False,
        git_auto_commit: bool = False,
    ):
        """
        Initialize BMAD workflow engine.

        Args:
            bmad_engine: Base BMAD engine
            enable_checkpoints: Enable automatic checkpointing
            enable_git: Enable Git integration
            git_auto_commit: Auto-commit checkpoints to Git
        """
        self.bmad = bmad_engine
        self.orchestrator = WorkflowOrchestrator(
            auto_checkpoint=enable_checkpoints, checkpoint_every_phase=enable_checkpoints
        )

        self.enable_git = enable_git
        self.git: Optional[GitIntegration] = None

        if enable_git:
            self.git = GitIntegration(auto_commit=git_auto_commit)
            if not self.git.repo_initialized:
                self.git.init_repo()

    # ========== Workflow Execution ==========

    async def run_with_workflow(
        self,
        requirement: str,
        session_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> tuple[BMADResult, WorkflowResult]:
        """
        Run BMAD with workflow management.

        Args:
            requirement: User requirement
            session_name: Human-readable session name
            metadata: Additional metadata

        Returns:
            tuple[BMADResult, WorkflowResult]: BMAD result and workflow result
        """
        # Create workflow session
        workflow_id = f"bmad_{requirement[:30]}"
        session = await self.orchestrator.start_workflow(
            workflow_id=workflow_id,
            initial_state={"requirement": requirement},
            session_name=session_name or f"BMAD: {requirement[:50]}",
            metadata=metadata,
        )

        try:
            # Execute BMAD with phase tracking
            bmad_result = await self._execute_bmad_with_tracking(session, requirement)

            # Complete workflow
            workflow_result = await self.orchestrator.complete_workflow(
                session.session_id, success=bmad_result.success
            )

            # Git commit if enabled
            if self.enable_git and self.git and bmad_result.success:
                self.git.commit_checkpoint(
                    checkpoint_id=(
                        workflow_result.checkpoints[-1] if workflow_result.checkpoints else "final"
                    ),
                    phase="complete",
                    metadata={"requirement": requirement},
                )

            return bmad_result, workflow_result

        except Exception as e:
            # Complete workflow with failure
            workflow_result = await self.orchestrator.complete_workflow(
                session.session_id, success=False
            )

            raise

    async def _execute_bmad_with_tracking(self, session: Session, requirement: str) -> BMADResult:
        """Execute BMAD with phase tracking"""

        # Phase 0: Concretization
        async def phase_0_concretization(state, **kwargs):
            golden_data = await self.bmad._phase_0_concretization(requirement)
            return {"golden_data": golden_data}

        await self.orchestrator.execute_phase(
            session_id=session.session_id,
            phase=WorkflowPhase.CONCRETIZATION,
            phase_function=phase_0_concretization,
        )

        # Get state
        state = self.orchestrator.state_manager.get_state(session.session_id)
        golden_data = state.get("golden_data")

        # Phase 1: Discovery
        async def phase_1_discovery(state, **kwargs):
            spec_yaml = await self.bmad._phase_1_discovery(golden_data)
            return {"spec_yaml": spec_yaml}

        await self.orchestrator.execute_phase(
            session_id=session.session_id,
            phase=WorkflowPhase.DISCOVERY,
            phase_function=phase_1_discovery,
        )

        state = self.orchestrator.state_manager.get_state(session.session_id)
        spec_yaml = state.get("spec_yaml")

        # Phase 2: Architecture
        async def phase_2_architecture(state, **kwargs):
            arch_result = await self.bmad._phase_2_architecture(spec_yaml, golden_data)
            return {"arch_result": arch_result}

        await self.orchestrator.execute_phase(
            session_id=session.session_id,
            phase=WorkflowPhase.ARCHITECTURE,
            phase_function=phase_2_architecture,
        )

        # Phase 3: Design
        async def phase_3_design(state, **kwargs):
            agents, tasks = await self.bmad._phase_3_design(spec_yaml, golden_data)
            return {"agents": agents, "tasks": tasks}

        await self.orchestrator.execute_phase(
            session_id=session.session_id, phase=WorkflowPhase.DESIGN, phase_function=phase_3_design
        )

        state = self.orchestrator.state_manager.get_state(session.session_id)
        agents = state.get("agents")
        tasks = state.get("tasks")

        # Phase 4: Development (Testing/Validation)
        async def phase_4_development(state, **kwargs):
            # Validation phase
            validation_result = self.bmad.validator.validate_all(agents, tasks, golden_data)
            return {"validation_result": validation_result}

        await self.orchestrator.execute_phase(
            session_id=session.session_id,
            phase=WorkflowPhase.DEVELOPMENT,
            phase_function=phase_4_development,
        )

        # Phase 5: Delivery (Code Generation)
        async def phase_5_delivery(state, **kwargs):
            generated_code = await self.bmad._phase_5_delivery(
                spec_yaml, golden_data, self.bmad.deployment_target
            )
            return {"generated_code": generated_code}

        await self.orchestrator.execute_phase(
            session_id=session.session_id,
            phase=WorkflowPhase.DELIVERY,
            phase_function=phase_5_delivery,
        )

        # Get final state
        final_state = self.orchestrator.state_manager.get_state(session.session_id)

        # Build BMAD result
        bmad_result = BMADResult(
            success=True,
            golden_data=final_state.get("golden_data"),
            agents=final_state.get("agents", []),
            tasks=final_state.get("tasks", []),
            generated_code=final_state.get("generated_code", {}),
            errors=final_state.get("errors", []),
        )

        return bmad_result

    # ========== Resume & Rollback ==========

    async def resume_from_checkpoint(
        self, checkpoint_id: str, create_new_session: bool = False
    ) -> tuple[Session, Dict[str, Any]]:
        """
        Resume BMAD workflow from a checkpoint.

        Args:
            checkpoint_id: Checkpoint to resume from
            create_new_session: Create new session or reuse

        Returns:
            tuple[Session, Dict[str, Any]]: Session and resumed state
        """
        session = await self.orchestrator.resume_from_checkpoint(checkpoint_id, create_new_session)

        state = self.orchestrator.state_manager.get_state(session.session_id)

        return session, state

    def rollback_to_phase(self, session_id: str, phase: WorkflowPhase) -> Optional[Dict[str, Any]]:
        """
        Rollback to a specific phase.

        Args:
            session_id: Session ID
            phase: Phase to rollback to

        Returns:
            Optional[Dict[str, Any]]: Restored state
        """
        # Find checkpoint for phase
        checkpoints = self.orchestrator.list_checkpoints(session_id=session_id)

        for checkpoint in checkpoints:
            if checkpoint.phase == phase.value:
                return self.orchestrator.rollback_to_checkpoint(
                    session_id, checkpoint.checkpoint_id
                )

        return None

    # ========== Session Management ==========

    def pause_session(self, session_id: str) -> bool:
        """Pause a BMAD session"""
        success = self.orchestrator.pause_workflow(session_id)

        if success and self.enable_git and self.git:
            self.git.commit_all("Paused BMAD session")

        return success

    def resume_session(self, session_id: str) -> bool:
        """Resume a paused BMAD session"""
        return self.orchestrator.resume_workflow(session_id)

    def list_active_sessions(self):
        """List all active BMAD sessions"""
        return self.orchestrator.get_active_workflows()

    def switch_session(self, session_id: str) -> Optional[Session]:
        """Switch to a different BMAD session"""
        return self.orchestrator.switch_to_workflow(session_id)

    # ========== Git Integration ==========

    def create_git_branch(self, session_id: str, branch_name: Optional[str] = None) -> bool:
        """
        Create a Git branch for a session.

        Args:
            session_id: Session ID
            branch_name: Branch name (default: session_id)

        Returns:
            bool: Success
        """
        if not self.enable_git or not self.git:
            return False

        branch = branch_name or f"bmad-{session_id[:8]}"
        return self.git.create_branch(branch)

    def commit_session_state(self, session_id: str, message: Optional[str] = None) -> Optional[str]:
        """
        Commit current session state to Git.

        Args:
            session_id: Session ID
            message: Commit message

        Returns:
            Optional[str]: Commit hash
        """
        if not self.enable_git or not self.git:
            return None

        state = self.orchestrator.state_manager.get_state(session_id)
        if not state:
            return None

        commit_message = message or f"BMAD session checkpoint: {session_id}"
        return self.git.commit_all(commit_message)

    def tag_successful_run(
        self, session_id: str, tag_name: str, message: Optional[str] = None
    ) -> bool:
        """
        Tag a successful BMAD run in Git.

        Args:
            session_id: Session ID
            tag_name: Tag name
            message: Tag message

        Returns:
            bool: Success
        """
        if not self.enable_git or not self.git:
            return False

        tag_message = message or f"Successful BMAD run: {session_id}"
        return self.git.create_tag(tag_name, tag_message)

    # ========== Workflow Utilities ==========

    def get_session_progress(self, session_id: str) -> Dict[str, Any]:
        """Get detailed progress for a session"""
        return self.orchestrator.get_workflow_progress(session_id)

    def export_session(self, session_id: str, output_path: str):
        """Export session with all checkpoints and history"""
        self.orchestrator.state_manager.export_session(session_id, output_path)

    def import_session(self, import_path: str) -> str:
        """Import a previously exported session"""
        return self.orchestrator.state_manager.import_session(import_path)

    def get_session_history(self, session_id: str):
        """Get complete history for a session"""
        return self.orchestrator.state_manager.get_history(session_id)

    def get_git_info(self) -> Dict[str, Any]:
        """Get Git repository information"""
        if not self.enable_git or not self.git:
            return {"enabled": False}

        return {"enabled": True, **self.git.get_repository_info()}
