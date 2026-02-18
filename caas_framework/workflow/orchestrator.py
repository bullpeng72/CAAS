"""
Workflow Orchestrator

High-level orchestrator for managing BMAD workflows with state persistence,
checkpoints, and session management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from caas_framework.session.manager import Session, SessionManager
from caas_framework.workflow.persistence import (
    FilePersistenceBackend,
    PersistenceBackend,
)
from caas_framework.workflow.state_manager import Checkpoint, StateManager


class WorkflowPhase(str, Enum):
    """BMAD workflow phases"""

    CONCRETIZATION = "concretization"  # Phase 0
    DISCOVERY = "discovery"  # Phase 1
    ARCHITECTURE = "architecture"  # Phase 2
    DESIGN = "design"  # Phase 3
    DEVELOPMENT = "development"  # Phase 4
    DELIVERY = "delivery"  # Phase 5


@dataclass
class WorkflowResult:
    """Workflow execution result"""

    success: bool
    session_id: str
    workflow_id: str
    phases_completed: List[str] = field(default_factory=list)
    current_phase: Optional[str] = None
    state: Dict[str, Any] = field(default_factory=dict)
    checkpoints: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0


class WorkflowOrchestrator:
    """
    Workflow Orchestrator

    Manages workflow execution with:
    - State persistence
    - Checkpoint/Resume
    - Rollback support
    - Multi-session management
    - Context switching
    """

    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        session_manager: Optional[SessionManager] = None,
        persistence_backend: Optional[PersistenceBackend] = None,
        auto_checkpoint: bool = True,
        checkpoint_every_phase: bool = True,
    ):
        """
        Initialize orchestrator.

        Args:
            state_manager: State manager instance
            session_manager: Session manager instance
            persistence_backend: Persistence backend
            auto_checkpoint: Auto-create checkpoints
            checkpoint_every_phase: Checkpoint after each phase
        """
        self.state_manager = state_manager or StateManager()
        self.session_manager = session_manager or SessionManager()
        self.persistence = persistence_backend or FilePersistenceBackend()

        self.auto_checkpoint = auto_checkpoint
        self.checkpoint_every_phase = checkpoint_every_phase

    # ========== Workflow Execution ==========

    async def start_workflow(
        self,
        workflow_id: str,
        initial_state: Optional[Dict[str, Any]] = None,
        session_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        Start a new workflow execution.

        Args:
            workflow_id: Workflow identifier
            initial_state: Initial state
            session_name: Human-readable session name
            metadata: Additional metadata

        Returns:
            Session: Created session
        """
        # Create session
        session = self.session_manager.create_session(
            workflow_id=workflow_id,
            name=session_name,
            description=f"Workflow: {workflow_id}",
            metadata=metadata or {},
        )

        # Initialize state
        state = initial_state or {}
        state.update(
            {
                "workflow_id": workflow_id,
                "session_id": session.session_id,
                "start_time": datetime.utcnow().isoformat(),
                "current_phase": None,
                "phases_completed": [],
                "errors": [],
            }
        )

        self.state_manager.set_state(session.session_id, state)

        # Create initial checkpoint if auto-checkpoint enabled
        if self.auto_checkpoint:
            checkpoint_id = self.state_manager.save_checkpoint(
                session_id=session.session_id,
                workflow_id=workflow_id,
                phase="init",
                state=state,
                metadata={"event": "workflow_start"},
            )
            self.session_manager.add_checkpoint(session.session_id, checkpoint_id)

        return session

    async def execute_phase(
        self,
        session_id: str,
        phase: WorkflowPhase,
        phase_function: Any,  # Callable that executes the phase
        phase_inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a workflow phase with automatic checkpointing.

        Args:
            session_id: Session ID
            phase: Phase to execute
            phase_function: Function to execute
            phase_inputs: Inputs for the phase

        Returns:
            Dict[str, Any]: Phase result
        """
        # Get current state
        state = self.state_manager.get_state(session_id)
        if not state:
            raise ValueError(f"No state found for session: {session_id}")

        # Update phase
        state["current_phase"] = phase.value
        self.session_manager.set_session_phase(session_id, phase.value)

        # Execute phase
        try:
            result = await phase_function(state, **(phase_inputs or {}))

            # Update state with result
            state.update(result)
            state["phases_completed"].append(phase.value)

            self.state_manager.set_state(session_id, state)

            # Checkpoint after phase completion
            if self.checkpoint_every_phase:
                checkpoint_id = self.state_manager.save_checkpoint(
                    session_id=session_id,
                    workflow_id=state["workflow_id"],
                    phase=phase.value,
                    state=state,
                    metadata={"phase_result": "success"},
                )
                self.session_manager.add_checkpoint(session_id, checkpoint_id)

            return result

        except Exception as e:
            # Record error
            error_msg = f"Error in {phase.value}: {str(e)}"
            state["errors"].append(error_msg)
            self.state_manager.set_state(session_id, state)

            # Checkpoint error state
            if self.auto_checkpoint:
                checkpoint_id = self.state_manager.save_checkpoint(
                    session_id=session_id,
                    workflow_id=state["workflow_id"],
                    phase=phase.value,
                    state=state,
                    metadata={"phase_result": "error", "error": error_msg},
                )
                self.session_manager.add_checkpoint(session_id, checkpoint_id)

            raise

    async def complete_workflow(
        self, session_id: str, success: bool = True
    ) -> WorkflowResult:
        """
        Complete a workflow execution.

        Args:
            session_id: Session ID
            success: Whether workflow completed successfully

        Returns:
            WorkflowResult: Workflow result
        """
        # Get final state
        state = self.state_manager.get_state(session_id)
        if not state:
            raise ValueError(f"No state found for session: {session_id}")

        # Calculate duration
        start_time_str = state.get("start_time")
        start_time = datetime.fromisoformat(start_time_str) if start_time_str else None
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds() if start_time else 0.0

        # Create final checkpoint
        if self.auto_checkpoint:
            checkpoint_id = self.state_manager.save_checkpoint(
                session_id=session_id,
                workflow_id=state["workflow_id"],
                phase="complete",
                state=state,
                metadata={"event": "workflow_complete", "success": success},
            )
            self.session_manager.add_checkpoint(session_id, checkpoint_id)

        # Complete session
        self.session_manager.complete_session(session_id, success=success)

        # Build result
        result = WorkflowResult(
            success=success,
            session_id=session_id,
            workflow_id=state["workflow_id"],
            phases_completed=state.get("phases_completed", []),
            current_phase=state.get("current_phase"),
            state=state,
            checkpoints=self.session_manager.get_checkpoints(session_id),
            errors=state.get("errors", []),
            start_time=start_time,
            end_time=end_time,
            duration=duration,
        )

        return result

    # ========== Checkpoint Management ==========

    def create_checkpoint(
        self,
        session_id: str,
        checkpoint_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a manual checkpoint.

        Args:
            session_id: Session ID
            checkpoint_name: Human-readable checkpoint name
            metadata: Additional metadata

        Returns:
            str: Checkpoint ID
        """
        state = self.state_manager.get_state(session_id)
        if not state:
            raise ValueError(f"No state found for session: {session_id}")

        session = self.session_manager.get_session(session_id)
        workflow_id = session.workflow_id if session else "unknown"

        checkpoint_metadata = metadata or {}
        if checkpoint_name:
            checkpoint_metadata["name"] = checkpoint_name

        checkpoint_id = self.state_manager.save_checkpoint(
            session_id=session_id,
            workflow_id=workflow_id,
            phase=state.get("current_phase", "unknown"),
            state=state,
            metadata=checkpoint_metadata,
        )

        self.session_manager.add_checkpoint(session_id, checkpoint_id)

        return checkpoint_id

    def list_checkpoints(
        self, session_id: Optional[str] = None, workflow_id: Optional[str] = None
    ) -> List[Checkpoint]:
        """List checkpoints"""
        return self.state_manager.list_checkpoints(session_id, workflow_id)

    # ========== Resume & Rollback ==========

    async def resume_from_checkpoint(
        self, checkpoint_id: str, create_new_session: bool = False
    ) -> Session:
        """
        Resume workflow from a checkpoint.

        Args:
            checkpoint_id: Checkpoint to resume from
            create_new_session: Create new session or reuse existing

        Returns:
            Session: Resumed or created session
        """
        checkpoint = self.state_manager.load_checkpoint(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")

        if create_new_session:
            # Create new session with checkpoint state
            session = self.session_manager.create_session(
                workflow_id=checkpoint.workflow_id,
                name=f"Resumed from {checkpoint.checkpoint_id}",
                metadata={
                    "resumed_from": checkpoint_id,
                    "original_session": checkpoint.session_id,
                },
            )

            # Copy state to new session
            self.state_manager.set_state(session.session_id, checkpoint.state.copy())

        else:
            # Reuse existing session
            session = self.session_manager.get_session(checkpoint.session_id)
            if not session:
                raise ValueError(f"Original session not found: {checkpoint.session_id}")

            # Restore state
            self.state_manager.set_state(checkpoint.session_id, checkpoint.state.copy())

            # Resume session if paused
            if session.status.value == "paused":
                self.session_manager.resume_session(checkpoint.session_id)

        return session

    def rollback_to_checkpoint(
        self, session_id: str, checkpoint_id: str
    ) -> Dict[str, Any]:
        """
        Rollback session to a previous checkpoint.

        Args:
            session_id: Session ID
            checkpoint_id: Checkpoint to rollback to

        Returns:
            Dict[str, Any]: Restored state
        """
        # Verify checkpoint belongs to session
        checkpoint = self.state_manager.load_checkpoint(checkpoint_id)
        if not checkpoint or checkpoint.session_id != session_id:
            raise ValueError(f"Invalid checkpoint for session: {checkpoint_id}")

        # Rollback
        restored_state = self.state_manager.rollback_to_checkpoint(checkpoint_id)
        if not restored_state:
            raise ValueError(f"Failed to rollback to checkpoint: {checkpoint_id}")

        # Update session phase
        self.session_manager.set_session_phase(
            session_id, restored_state.get("current_phase", "unknown")
        )

        return restored_state

    # ========== Session Management ==========

    def pause_workflow(self, session_id: str) -> bool:
        """Pause a workflow"""
        return self.session_manager.pause_session(session_id)

    def resume_workflow(self, session_id: str) -> bool:
        """Resume a paused workflow"""
        return self.session_manager.resume_session(session_id)

    def get_active_workflows(self) -> List[Session]:
        """Get all active workflow sessions"""
        from caas_framework.session.manager import SessionStatus

        return self.session_manager.list_sessions(status=SessionStatus.ACTIVE)

    def list_workflows(self, status: Optional[str] = None) -> List[Session]:
        """List workflows, optionally filtered by status"""
        if status is None:
            return self.session_manager.list_sessions()
        from caas_framework.session.manager import SessionStatus
        try:
            session_status = SessionStatus(status)
        except ValueError:
            return self.session_manager.list_sessions()
        return self.session_manager.list_sessions(status=session_status)

    def switch_to_workflow(self, session_id: str) -> Optional[Session]:
        """Switch active workflow"""
        return self.session_manager.switch_to(session_id)

    # ========== Persistence ==========

    def save_workflow_state(self, session_id: str) -> bool:
        """Save workflow state to persistence backend"""
        state = self.state_manager.get_state(session_id)
        if not state:
            return False

        return self.persistence.save(session_id, state)

    def load_workflow_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load workflow state from persistence backend"""
        return self.persistence.load(session_id)

    # ========== Utilities ==========

    def get_workflow_progress(self, session_id: str) -> Dict[str, Any]:
        """
        Get workflow progress information.

        Args:
            session_id: Session ID

        Returns:
            Dict[str, Any]: Progress information
        """
        state = self.state_manager.get_state(session_id)
        session = self.session_manager.get_session(session_id)

        if not state or not session:
            return {}

        total_phases = len(WorkflowPhase)
        completed_phases = len(state.get("phases_completed", []))
        progress_percentage = (completed_phases / total_phases) * 100

        return {
            "session_id": session_id,
            "workflow_id": session.workflow_id,
            "status": session.status,
            "current_phase": state.get("current_phase"),
            "phases_completed": completed_phases,
            "total_phases": total_phases,
            "progress_percentage": progress_percentage,
            "errors": len(state.get("errors", [])),
            "checkpoints": len(session.checkpoint_ids),
        }
