"""
Workflow State Manager

Manages workflow state with checkpoint/resume capabilities.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Checkpoint(BaseModel):
    """Checkpoint data model"""

    checkpoint_id: str
    session_id: str
    workflow_id: str
    timestamp: datetime
    phase: str
    state: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    parent_checkpoint_id: Optional[str] = None  # For rollback support


class StateHistory(BaseModel):
    """State history entry"""

    timestamp: datetime
    event: str  # "update", "checkpoint", "rollback", "restore"
    phase: str
    state_snapshot: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StateManager:
    """
    Workflow State Manager

    Features:
    - State persistence with checkpoints
    - Rollback to previous checkpoints
    - State history tracking
    - Multi-session support
    """

    def __init__(self, storage_dir: str = ".caas/state"):
        """
        Initialize state manager.

        Args:
            storage_dir: Directory for storing checkpoints
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # In-memory state cache
        self.active_states: Dict[str, Dict[str, Any]] = {}

        # State history (in-memory)
        self.history: Dict[str, List[StateHistory]] = {}

    # ========== Checkpoint Management ==========

    def save_checkpoint(
        self,
        session_id: str,
        workflow_id: str,
        phase: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        parent_checkpoint_id: Optional[str] = None,
    ) -> str:
        """
        Save a checkpoint.

        Args:
            session_id: Session ID
            workflow_id: Workflow ID
            phase: Current phase
            state: State to save
            metadata: Additional metadata
            parent_checkpoint_id: Parent checkpoint (for rollback chain)

        Returns:
            str: Checkpoint ID
        """
        timestamp = datetime.utcnow()
        checkpoint_id = f"{session_id}_{workflow_id}_{phase}_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}"

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            workflow_id=workflow_id,
            timestamp=timestamp,
            phase=phase,
            state=state,
            metadata=metadata or {},
            parent_checkpoint_id=parent_checkpoint_id,
        )

        # Save to file
        checkpoint_file = self.storage_dir / f"{checkpoint_id}.json"
        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint.model_dump(mode="json"), f, indent=2, default=str)

        # Record in history
        self._record_history(
            session_id=session_id,
            event="checkpoint",
            phase=phase,
            state=state,
            metadata={"checkpoint_id": checkpoint_id},
        )

        return checkpoint_id

    def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """
        Load a checkpoint.

        Args:
            checkpoint_id: Checkpoint ID

        Returns:
            Optional[Checkpoint]: Checkpoint data
        """
        checkpoint_file = self.storage_dir / f"{checkpoint_id}.json"

        if not checkpoint_file.exists():
            return None

        with open(checkpoint_file, "r") as f:
            data = json.load(f)

        return Checkpoint(**data)

    def list_checkpoints(
        self, session_id: Optional[str] = None, workflow_id: Optional[str] = None
    ) -> List[Checkpoint]:
        """
        List checkpoints.

        Args:
            session_id: Filter by session ID
            workflow_id: Filter by workflow ID

        Returns:
            List[Checkpoint]: List of checkpoints
        """
        checkpoints = []

        for checkpoint_file in self.storage_dir.glob("*.json"):
            try:
                with open(checkpoint_file, "r") as f:
                    data = json.load(f)
                checkpoint = Checkpoint(**data)

                # Apply filters
                if session_id and checkpoint.session_id != session_id:
                    continue
                if workflow_id and checkpoint.workflow_id != workflow_id:
                    continue

                checkpoints.append(checkpoint)
            except Exception:
                # Skip invalid checkpoints
                pass

        # Sort by timestamp (newest first)
        checkpoints.sort(key=lambda c: c.timestamp, reverse=True)
        return checkpoints

    def get_latest_checkpoint(
        self, session_id: str, workflow_id: Optional[str] = None
    ) -> Optional[Checkpoint]:
        """Get the latest checkpoint for a session/workflow"""
        checkpoints = self.list_checkpoints(session_id, workflow_id)
        return checkpoints[0] if checkpoints else None

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint"""
        checkpoint_file = self.storage_dir / f"{checkpoint_id}.json"

        if checkpoint_file.exists():
            checkpoint_file.unlink()
            return True
        return False

    # ========== State Management ==========

    def set_state(self, session_id: str, state: Dict[str, Any]):
        """Set active state for a session"""
        self.active_states[session_id] = state
        self._record_history(
            session_id=session_id,
            event="update",
            phase=state.get("current_phase", "unknown"),
            state=state,
        )

    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get active state for a session"""
        return self.active_states.get(session_id)

    def update_state(self, session_id: str, updates: Dict[str, Any]):
        """Update active state"""
        if session_id in self.active_states:
            self.active_states[session_id].update(updates)
        else:
            self.active_states[session_id] = updates

        self._record_history(
            session_id=session_id,
            event="update",
            phase=updates.get("current_phase", "unknown"),
            state=self.active_states[session_id],
        )

    def clear_state(self, session_id: str):
        """Clear active state"""
        if session_id in self.active_states:
            del self.active_states[session_id]

    # ========== Rollback Support ==========

    def rollback_to_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        Rollback to a previous checkpoint.

        Args:
            checkpoint_id: Checkpoint to rollback to

        Returns:
            Optional[Dict[str, Any]]: Restored state
        """
        checkpoint = self.load_checkpoint(checkpoint_id)
        if not checkpoint:
            return None

        # Restore state
        self.active_states[checkpoint.session_id] = checkpoint.state.copy()

        # Record rollback in history
        self._record_history(
            session_id=checkpoint.session_id,
            event="rollback",
            phase=checkpoint.phase,
            state=checkpoint.state,
            metadata={"checkpoint_id": checkpoint_id},
        )

        return checkpoint.state

    def get_rollback_chain(self, checkpoint_id: str) -> List[Checkpoint]:
        """
        Get the chain of checkpoints for rollback.

        Args:
            checkpoint_id: Starting checkpoint

        Returns:
            List[Checkpoint]: Chain of checkpoints
        """
        chain = []
        current_id = checkpoint_id

        while current_id:
            checkpoint = self.load_checkpoint(current_id)
            if not checkpoint:
                break

            chain.append(checkpoint)
            current_id = checkpoint.parent_checkpoint_id

        return chain

    # ========== History Management ==========

    def _record_history(
        self,
        session_id: str,
        event: str,
        phase: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record state change in history"""
        if session_id not in self.history:
            self.history[session_id] = []

        entry = StateHistory(
            timestamp=datetime.utcnow(),
            event=event,
            phase=phase,
            state_snapshot=state.copy(),
            metadata=metadata or {},
        )

        self.history[session_id].append(entry)

        # Keep last 1000 entries
        if len(self.history[session_id]) > 1000:
            self.history[session_id] = self.history[session_id][-1000:]

    def get_history(self, session_id: str) -> List[StateHistory]:
        """Get state history for a session"""
        return self.history.get(session_id, [])

    def get_state_at_time(
        self, session_id: str, timestamp: datetime
    ) -> Optional[Dict[str, Any]]:
        """Get state at a specific timestamp"""
        history = self.get_history(session_id)

        # Find closest entry before timestamp
        closest = None
        for entry in history:
            if entry.timestamp <= timestamp:
                if closest is None or entry.timestamp > closest.timestamp:
                    closest = entry

        return closest.state_snapshot if closest else None

    # ========== Cleanup ==========

    def cleanup_old_checkpoints(self, days: int = 7) -> int:
        """
        Clean up old checkpoints.

        Args:
            days: Delete checkpoints older than this many days

        Returns:
            int: Number of checkpoints deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted_count = 0

        for checkpoint in self.list_checkpoints():
            if checkpoint.timestamp < cutoff_date:
                self.delete_checkpoint(checkpoint.checkpoint_id)
                deleted_count += 1

        return deleted_count

    def export_session(self, session_id: str, output_path: str):
        """
        Export a session's checkpoints and history.

        Args:
            session_id: Session ID
            output_path: Output file path
        """
        checkpoints = self.list_checkpoints(session_id=session_id)
        history = self.get_history(session_id)

        export_data = {
            "session_id": session_id,
            "export_time": datetime.utcnow().isoformat(),
            "checkpoints": [c.model_dump(mode="json") for c in checkpoints],
            "history": [h.model_dump(mode="json") for h in history],
        }

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

    def import_session(self, import_path: str) -> str:
        """
        Import a session from exported data.

        Args:
            import_path: Import file path

        Returns:
            str: Imported session ID
        """
        with open(import_path, "r") as f:
            import_data = json.load(f)

        session_id = import_data["session_id"]

        # Import checkpoints
        for checkpoint_data in import_data["checkpoints"]:
            checkpoint = Checkpoint(**checkpoint_data)
            checkpoint_file = self.storage_dir / f"{checkpoint.checkpoint_id}.json"
            with open(checkpoint_file, "w") as f:
                json.dump(checkpoint.model_dump(mode="json"), f, indent=2, default=str)

        # Import history
        self.history[session_id] = [StateHistory(**h) for h in import_data["history"]]

        return session_id
